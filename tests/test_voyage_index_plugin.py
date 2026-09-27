"""Selected signed Voyage index journey with synthetic paid outputs and real LanceDB."""
# ruff: noqa: F811 -- imported pytest fixtures are injected by name.

import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import zipfile

import pytest

from attune_harness import extensions as ext, plugin_runtime
from attune_harness.features import FeatureUnavailable
from attune_harness.review_contract import digest
from attune_harness.review_store import read_record
from attune_harness.voyage_index import (build_index, expected_rows, index_plan, read_generation,
    selected_result_bound, selection, validate_staged_tree)
from attune_harness.voyage_retrieval import retrieve_voyage
from attune_harness.voyage_sources import config
from attune_voyage_plugin.bundle import DECLARES, GRANTS, build as build_bundle
from test_plugin_signing import base_signer, signers, signer, sign_bundle  # noqa: F401
from test_voyage import corpus, git  # noqa: F401

EMBED_FAKE = '''from .common import request, result
data = request()
assert data['paths'] == {}
result({'vectors': [[1.0] + [0.0] * 1023 for _ in data['arguments']['texts']],
        'total_tokens': 100 * len(data['arguments']['texts'])})
'''
RERANK_FAKE = '''from .common import request, result
data = request()
assert data['paths'] == {}
args = data['arguments']
order = sorted(range(len(args['documents'])), key=lambda i: (args['query'] not in args['documents'][i], i))[:args['k']]
result({'ranking': [{'index': i, 'score': 1.0 - rank / 100} for rank, i in enumerate(order)],
        'total_tokens': 500 * len(args['documents'])})
'''


@pytest.fixture
def signed_index(corpus, signer, tmp_path, monkeypatch):
    root, cfg, _ = corpus
    monkeypatch.setenv('VOYAGE_API_KEY', 'offline-fixture-not-a-real-key')
    real_resolver = plugin_runtime.resolve_imports

    def prepare(*, alter_paid=True, embed_script=None, index_script=None, grant=None,
                real_closure=False):
        # Each accepted bundle must resolve the installed closure afresh, even
        # when a test invokes prepare more than once.
        monkeypatch.setattr(plugin_runtime, 'resolve_imports', real_resolver)
        bundle = tmp_path / 'bundle'
        build_bundle(bundle)
        if alter_paid or embed_script is not None or index_script is not None:
            archive = bundle / 'code.zip'
            with zipfile.ZipFile(archive) as source:
                entries = {name: source.read(name) for name in source.namelist()}
            if alter_paid:
                entries['attune_voyage_plugin/embed.py'] = EMBED_FAKE.encode()
                entries['attune_voyage_plugin/rerank.py'] = RERANK_FAKE.encode()
            if embed_script is not None:
                entries['attune_voyage_plugin/embed.py'] = embed_script.encode()
            if index_script is not None:
                entries['attune_voyage_plugin/index.py'] = index_script.encode()
            replacement = bundle / 'test-code.zip'
            with zipfile.ZipFile(replacement, 'w') as target:
                for name, content in entries.items():
                    target.writestr(name, content)
            replacement.replace(archive)
        manifest = bundle / 'manifest.json'
        accepted_grant = copy.deepcopy(GRANTS if grant is None else grant)
        if grant is not None:
            value = json.loads(manifest.read_text())
            value['grants'] = accepted_grant
            manifest.write_text(json.dumps(value), encoding='utf-8')
        artifact = sign_bundle(manifest, signer)
        state_dir = tmp_path / 'extension-state'
        state = ext.install(manifest, state_dir)
        section = {'voyage': {'state_dir': str(state_dir), 'artifact_digest': artifact,
                              'grant': accepted_grant}, 'signers': [signer.entry]}
        registry = tmp_path / 'registry.json'
        registry.write_text(json.dumps({'extensions': section}), encoding='utf-8')
        state = ext.mutate(state_dir, state['state_digest'], 'enable', registry=registry)
        if not real_closure:
            # Stage checks still verify the signed artifact, grants and
            # accepted-state equality; only repeated installed-wheel scans are
            # replaced by this bundle's real enable-time closure snapshot.
            accepted_imports = copy.deepcopy(state['plugin']['imports'])
            def accepted_closure(declarations):
                assert tuple(declarations) == tuple(DECLARES['imports'])
                return copy.deepcopy(accepted_imports)
            monkeypatch.setattr(plugin_runtime, 'resolve_imports', accepted_closure)
        chosen = copy.deepcopy(cfg)
        chosen['voyage_plugin'] = {'registry': str(registry),
            'registry_digest': digest(ext._registry_section(registry)), 'extension_id': 'voyage',
            'tools': {'embed': 'embed', 'rerank': 'rerank', 'index': 'index'}}
        return config(chosen, root.parent), registry, section, state_dir
    return prepare


def test_unsigned_builder_is_deterministic_and_exclusive(tmp_path):
    first, second = tmp_path / 'first', tmp_path / 'second'
    a, b = build_bundle(first), build_bundle(second)
    assert a == b
    assert hashlib.sha256((first / 'code.zip').read_bytes()).hexdigest() == hashlib.sha256(
        (second / 'code.zip').read_bytes()).hexdigest()
    assert not (first / 'artifact.sig').exists()
    assert json.loads((first / 'manifest.json').read_text())['grants']['output']['result'] == 1_048_576
    with pytest.raises(FileExistsError):
        build_bundle(first)


def test_selected_full_build_retrieve_and_replay(signed_index, corpus, tmp_path, monkeypatch):
    cfg, _, _, _ = signed_index(real_closure=True)
    planned = index_plan(cfg)
    assert planned['acceptance'] == 'pinned' and planned['dispatch_available'] is True
    assert planned['provider_calls'] == 0
    built = build_index(cfg, allow_provider=True)
    assert built['status'] == 'completed' and built['provider_calls'] > 0
    generation = built['generation']
    directory, metadata = read_generation(cfg, generation)
    assert len(metadata['passages']) > 0
    assert (directory / 'published.json').exists() and (directory / 'db/passages.lance').is_dir()
    attempt = json.loads((directory / 'index-attempt.json').read_text())
    assert attempt['status'] == 'child_completed'
    assert attempt['plugin_receipt']['grant']['paths'] == ['index_staging']
    assert attempt['plugin_receipt']['applied_grant']['paths'] == ['index_staging']
    assert attempt['plugin_receipt']['applied_grant']['secrets'] == []
    stages = read_record(directory / 'stages')['stages']
    paid = read_record(directory / 'stages' / stages[0])
    assert paid['receipt']['plugin']['grant']['paths'] == ['index_staging']
    assert paid['receipt']['plugin']['applied_grant']['paths'] == []
    assert paid['receipt']['plugin']['applied_grant']['secrets'] == ['VOYAGE_API_KEY']
    assert 'offline-fixture-not-a-real-key' not in (directory / 'build-receipt.json').read_text()
    chosen = selection(cfg, generation)
    first = retrieve_voyage(chosen, 'save_cart', k=2, work_dir=tmp_path / 'work', allow_provider=True)
    assert first['status'] == 'retrieved' and first['usage']['new_provider_calls'] == 2
    assert 'save_cart' in first['sources'][0]['excerpt']
    monkeypatch.delenv('VOYAGE_API_KEY')
    from attune_harness import plugin_runtime
    monkeypatch.setattr(plugin_runtime, 'run_voyage_paid', lambda *a, **kw: pytest.fail('replay launched paid child'))
    monkeypatch.setattr(plugin_runtime, 'run_voyage_index', lambda *a, **kw: pytest.fail('replay launched index child'))
    reused = build_index(cfg)
    assert reused['reused_generation'] is True and reused['provider_calls'] == 0
    replay = retrieve_voyage(chosen, 'save_cart', k=2, work_dir=tmp_path / 'work')
    assert replay['replay']['reused'] is True and replay['usage']['new_provider_calls'] == 0
    assert replay['sources'] == first['sources']


def test_real_installed_closure_drift_refuses_before_selected_state(signed_index, monkeypatch):
    cfg, _, _, _ = signed_index(real_closure=True)
    real_resolver = plugin_runtime.resolve_imports
    observed = []

    def drift(declarations):
        closure = real_resolver(declarations)
        observed.append(copy.deepcopy(closure))
        closure['versions']['voyageai'] = 'drifted-test-version'
        return closure

    monkeypatch.setattr(plugin_runtime, 'resolve_imports', drift)
    monkeypatch.setattr(plugin_runtime, 'invoke', lambda *a, **kw: pytest.fail('a child ran after closure drift'))
    with pytest.raises(FeatureUnavailable, match='closure changed'):
        build_index(cfg, allow_provider=True)
    assert observed and 'voyageai' in observed[0]['versions']
    assert not Path(cfg['index_dir']).exists()


def test_decimal_paid_vectors_round_to_frozen_float32_index_rows(signed_index, tmp_path, monkeypatch):
    decimal_embed = '''from .common import request, result
data = request()
assert data['paths'] == {}
result({'vectors': [[0.1 + i / 1000 for i in range(1024)]
    for _ in data['arguments']['texts']],
    'total_tokens': 100 * len(data['arguments']['texts'])})
'''
    cfg, _, _, _ = signed_index(embed_script=decimal_embed)
    assert index_plan(cfg)['dispatch_available'] is True
    built = build_index(cfg, allow_provider=True)
    directory, metadata = read_generation(cfg, built['generation'])
    stages = read_record(directory / 'stages')['stages']
    raw = read_record(directory / 'stages' / stages[0])['result']['vectors'][0][0]
    assert raw == 0.1
    import lancedb
    rows = lancedb.connect(str(directory / 'db')).open_table('passages').to_arrow().to_pylist()
    assert rows[0]['vector'][0] == struct.unpack('!f', struct.pack('!f', raw))[0]
    assert rows[0]['vector'][0] != raw
    assert json.loads((directory / 'build-receipt.json').read_text())['rows_digest'] == digest(
        sorted(rows, key=lambda row: row['passage_id']))
    chosen = selection(cfg, built['generation'])
    first = retrieve_voyage(chosen, 'save_cart', work_dir=tmp_path / 'decimal-retrieve', allow_provider=True)
    assert first['status'] == 'retrieved'
    monkeypatch.delenv('VOYAGE_API_KEY')
    replay = retrieve_voyage(chosen, 'save_cart', work_dir=tmp_path / 'decimal-retrieve')
    assert replay['replay']['reused'] is True and replay['usage']['new_provider_calls'] == 0
    assert metadata['passages']


def test_float32_overflow_and_underflow_refuse_before_index_staging():
    passage = {'passage_id': 'p', 'repo_id': 'r', 'path': 'f', 'embedding_text': 'text'}
    from attune_harness.voyage_index import embedding_key
    key = embedding_key(passage)
    for value, message in ((1e100, 'range'), (1e-100, 'underflowed')):
        with pytest.raises(ValueError, match=message):
            expected_rows([passage], {key: [value] * 1024})


def test_selected_index_refuses_injected_provider_before_state(signed_index, tmp_path):
    cfg, _, _, _ = signed_index()
    with pytest.raises(FeatureUnavailable, match='signed plugin tool'):
        build_index(cfg, allow_provider=True, provider=object())
    assert not Path(cfg['index_dir']).exists()


def test_local_index_tool_needs_no_key_when_paid_stages_replay(signed_index, corpus, monkeypatch):
    cfg, _, _, _ = signed_index()
    first = build_index(cfg, allow_provider=True)
    root = corpus[0]
    git(root, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
        'commit', '--allow-empty', '-m', 'new revision, same source bytes')
    monkeypatch.delenv('VOYAGE_API_KEY')
    second = build_index(cfg, base_generation=first['generation'])
    assert second['generation'] != first['generation']
    assert second['provider_calls'] == 0 and second['reused_embeddings'] > 0
    assert read_record(Path(cfg['index_dir']) / 'generations' / first['generation'] / 'stages')['stages']


def test_empty_selected_corpus_builds_and_retrieves_without_key(signed_index, tmp_path, monkeypatch):
    cfg, _, _, _ = signed_index()
    cfg['include'] = []
    monkeypatch.delenv('VOYAGE_API_KEY')
    built = build_index(cfg)
    assert built['passages'] == 0 and built['provider_calls'] == 0
    directory, _ = read_generation(cfg, built['generation'])
    assert not (directory / 'db').exists()
    result = retrieve_voyage(selection(cfg, built['generation']), 'anything', work_dir=tmp_path / 'empty')
    assert result['status'] == 'no_results' and result['usage']['new_provider_calls'] == 0


def test_large_rows_use_staging_instead_of_plugin_arguments(tmp_path):
    from attune_voyage_plugin.index import materialize
    vector = [1.0] + [0.0] * 1023
    passages = [{'passage_id': f'p{i:04}', 'repo_id': 'app', 'path': f'file{i}.py',
                 'embedding_text': 'source ' + 'x' * 3900} for i in range(300)]
    def key(p):
        from attune_harness.voyage_index import embedding_key
        return embedding_key(p)
    vectors = {key(p): vector for p in passages}
    rows = expected_rows(passages, vectors)
    assert len(json.dumps(rows).encode()) > 1_048_576
    staging = tmp_path / 'index_staging'
    staging.mkdir()
    (staging / 'rows.json').write_text(json.dumps(rows), encoding='utf-8')
    args = {'generation': 'a' * 64, 'rows_digest': digest(rows), 'row_count': len(rows)}
    assert len(json.dumps(args).encode()) < 1024
    assert materialize(staging, args) == {'row_count': len(rows), 'rows_digest': digest(rows)}
    assert (staging / 'db/passages.lance').is_dir()


def test_missing_accepted_index_path_refuses_before_state(signed_index):
    grant = {key: copy.deepcopy(value) for key, value in GRANTS.items() if key != 'paths'}
    cfg, _, _, _ = signed_index(grant=grant)
    with pytest.raises(FeatureUnavailable, match='index_staging'):
        build_index(cfg, allow_provider=True)
    assert not Path(cfg['index_dir']).exists()


def test_full_batch_result_fits_signed_limit_and_smaller_grant_refuses_prepaid(signed_index, monkeypatch):
    from attune_harness import plugin_runtime
    from attune_harness.voyage_sources import PROFILE
    from attune_voyage_plugin.common import canonical

    vectors = [[float(i + 1) / 37 for _ in range(PROFILE['dimensions'])] for i in range(32)]
    payload = {'vectors': vectors, 'total_tokens': 3200}
    assert 65536 < len(canonical(payload).encode()) < GRANTS['output']['result']
    cfg, _, _, _ = signed_index(grant={**GRANTS, 'output': {'result': 4096, 'diagnostics': 8192}})
    with pytest.raises(ValueError, match='result bound'):
        selected_result_bound(cfg, [{'embedding_text': f'passage {i}'} for i in range(32)])
    monkeypatch.setattr(plugin_runtime, 'run_voyage_paid',
        lambda *a, **kw: pytest.fail('undersized result grant launched paid child'))
    with pytest.raises(ValueError, match='result bound'):
        build_index(cfg, allow_provider=True)
    assert not Path(cfg['index_dir']).exists()


def test_predictably_oversized_rows_refuse_before_paid_state(signed_index, monkeypatch):
    cfg, _, _, _ = signed_index()
    from attune_harness import voyage_index
    from attune_harness import plugin_runtime
    monkeypatch.setattr(plugin_runtime, 'run_voyage_paid',
        lambda *a, **kw: pytest.fail('oversized rows launched paid child'))
    monkeypatch.setattr(voyage_index, 'MAX_INDEX_JSON', 100)
    with pytest.raises(ValueError, match='staging bound'):
        build_index(cfg, allow_provider=True)
    assert not Path(cfg['index_dir']).exists()


def test_staging_rejects_nonregular_entries(tmp_path):
    if not hasattr(os, 'mkfifo'):
        pytest.skip('FIFO requires POSIX')
    staging = tmp_path / 'index_staging'
    staging.mkdir()
    os.mkfifo(staging / 'unexpected')
    with pytest.raises(ValueError, match='nonregular'):
        validate_staged_tree(staging)


@pytest.mark.parametrize('wrong', ['arguments', 'embed', 'path'])
def test_index_context_rejects_wrong_request_role_or_path_before_child(signed_index, tmp_path, monkeypatch, wrong):
    cfg, _, _, _ = signed_index()
    from attune_harness import plugin_runtime
    from dataclasses import replace
    original = plugin_runtime.run_voyage_index
    def incorrect(bundle, tool_name, tool, arguments, **kwargs):
        if wrong == 'arguments':
            arguments = {**arguments, 'rows_digest': 'a' * 64}
        elif wrong == 'embed':
            tool_name = 'embed'
            tool = bundle['declaration']['tools']['embed']
        else:
            kwargs['context'] = replace(kwargs['context'], staging=tmp_path / 'other')
        return original(bundle, tool_name, tool, arguments, **kwargs)
    monkeypatch.setattr(plugin_runtime, 'run_voyage_index', incorrect)
    original_invoke = plugin_runtime.invoke
    def invoke(argv, *args, **kwargs):
        if json.loads(Path(argv[-1]).read_text())['entry'].endswith('.index'):
            pytest.fail('invalid index context launched child')
        return original_invoke(argv, *args, **kwargs)
    monkeypatch.setattr(plugin_runtime, 'invoke', invoke)
    with pytest.raises(FeatureUnavailable, match='index|context'):
        build_index(cfg, allow_provider=True)
    generation_dir = next((Path(cfg['index_dir']) / 'generations').iterdir())
    assert not (generation_dir / 'published.json').exists()
    assert (generation_dir / 'index-error.json').exists()


def test_index_child_without_fts_never_publishes(signed_index):
    script = '''import json, sys
from pathlib import Path
from .common import request, result, digest
import lancedb
data = request()
staging = Path(data['paths']['index_staging'])
rows = json.loads((staging / 'rows.json').read_text())
db = lancedb.connect(str(staging / 'db'))
db.create_table('passages', rows, mode='create')
result({'row_count': len(rows), 'rows_digest': digest(rows)})
'''
    cfg, _, _, _ = signed_index(index_script=script)
    with pytest.raises(ValueError):
        build_index(cfg, allow_provider=True)
    generation_dir = next((Path(cfg['index_dir']) / 'generations').iterdir())
    assert not (generation_dir / 'published.json').exists()
    assert (generation_dir / 'index-error.json').exists()


def test_wrong_fts_tokenizer_is_rejected_even_when_search_works(signed_index):
    script = '''import json
from pathlib import Path
from .common import request, result, digest
import lancedb
from lancedb.index import FTS
data = request()
staging = Path(data['paths']['index_staging'])
rows = json.loads((staging / 'rows.json').read_text())
db = lancedb.connect(str(staging / 'db'))
table = db.create_table('passages', rows, mode='create')
table.create_index('text', config=FTS())
result({'row_count': len(rows), 'rows_digest': digest(rows)})
'''
    cfg, _, _, _ = signed_index(index_script=script)
    with pytest.raises(ValueError, match='FTS profile'):
        build_index(cfg, allow_provider=True)
    generation_dir = next((Path(cfg['index_dir']) / 'generations').iterdir())
    assert (generation_dir / 'index-error.json').exists()
    with pytest.raises(ValueError, match='Retained index error'):
        build_index(cfg, allow_provider=True)
    assert not (generation_dir / 'published.json').exists()


def test_equal_value_float64_vectors_fail_frozen_arrow_schema(signed_index):
    script = '''import json
from pathlib import Path
from .common import request, result, digest
import lancedb
import pyarrow as pa
from lancedb.index import FTS
data = request()
staging = Path(data['paths']['index_staging'])
rows = json.loads((staging / 'rows.json').read_text())
schema = pa.schema([pa.field(name, pa.string()) for name in
    ('embedding_key', 'passage_id', 'path', 'repo_id', 'text')] +
    [pa.field('vector', pa.list_(pa.float64(), 1024))])
db = lancedb.connect(str(staging / 'db'))
table = db.create_table('passages', rows, schema=schema, mode='create')
assert table.to_arrow().to_pylist() == rows
table.create_index('text', config=FTS(stem=False, remove_stop_words=False,
    ascii_folding=False, max_token_length=256))
result({'row_count': len(rows), 'rows_digest': digest(rows)})
'''
    cfg, _, _, _ = signed_index(index_script=script)
    with pytest.raises(ValueError, match='schema'):
        build_index(cfg, allow_provider=True)
    directory = next((Path(cfg['index_dir']) / 'generations').iterdir())
    assert (directory / 'index-error.json').exists()
    assert not (directory / 'published.json').exists()


@pytest.mark.skipif(os.name != 'posix', reason='symlink/FIFO creation is POSIX-specific')
@pytest.mark.parametrize('entry', ['symlink', 'fifo'])
def test_signed_child_staged_special_entry_cannot_publish(signed_index, entry):
    from attune_voyage_plugin import index as runner_index
    original = Path(runner_index.__file__).read_text()
    create = ("(staging / 'db' / 'surprise').symlink_to(staging / 'rows.json')" if entry == 'symlink'
              else "os.mkfifo(staging / 'db' / 'surprise')")
    assert "result(materialize(Path(data['paths']['index_staging']), data['arguments']))" in original
    script = 'import os\n' + original.replace(
        "result(materialize(Path(data['paths']['index_staging']), data['arguments']))",
        "staging = Path(data['paths']['index_staging'])\n"
        "    summary = materialize(staging, data['arguments'])\n"
        f"    {create}\n    result(summary)")
    cfg, _, _, _ = signed_index(index_script=script)
    with pytest.raises(ValueError, match='symlink|nonregular'):
        build_index(cfg, allow_provider=True)
    directory = next((Path(cfg['index_dir']) / 'generations').iterdir())
    assert (directory / 'index-error.json').exists()
    assert not (directory / 'published.json').exists()


def test_bad_child_summary_cannot_be_laundered_on_second_build(signed_index, monkeypatch):
    from attune_voyage_plugin import index as runner_index
    original = Path(runner_index.__file__).read_text()
    script = original.replace("result(materialize(Path(data['paths']['index_staging']), data['arguments']))",
        "materialize(Path(data['paths']['index_staging']), data['arguments'])\n"
        "    result({'row_count': -1, 'rows_digest': data['arguments']['rows_digest']})")
    assert script != original
    cfg, _, _, _ = signed_index(index_script=script)
    with pytest.raises(ValueError, match='summary'):
        build_index(cfg, allow_provider=True)
    generation_dir = next((Path(cfg['index_dir']) / 'generations').iterdir())
    assert (generation_dir / 'index_staging/db/passages.lance').exists()
    assert (generation_dir / 'index-error.json').exists()
    from attune_harness import plugin_runtime
    monkeypatch.setattr(plugin_runtime, 'run_voyage_index',
        lambda *a, **kw: pytest.fail('rejected child relaunched'))
    with pytest.raises(ValueError, match='Retained index error'):
        build_index(cfg, allow_provider=True)
    assert not (generation_dir / 'published.json').exists()


def test_index_child_tampering_with_host_rows_is_rejected(signed_index):
    script = '''import sys
from pathlib import Path
from .common import request, result
data = request()
rows = Path(data['paths']['index_staging']) / 'rows.json'
rows.write_text('[]')
result({'row_count': 0, 'rows_digest': data['arguments']['rows_digest']})
'''
    cfg, _, _, _ = signed_index(index_script=script)
    with pytest.raises(Exception):
        build_index(cfg, allow_provider=True)
    generation_dir = next((Path(cfg['index_dir']) / 'generations').iterdir())
    assert not (generation_dir / 'published.json').exists()
    assert (generation_dir / 'index-error.json').exists()


def test_index_child_extra_database_row_never_publishes(signed_index):
    script = '''import json
from pathlib import Path
from .common import request, result, digest
import lancedb
from lancedb.index import FTS
data = request()
staging = Path(data['paths']['index_staging'])
rows = json.loads((staging / 'rows.json').read_text())
extra = dict(rows[0]); extra['passage_id'] = 'unexpected-passage'
db = lancedb.connect(str(staging / 'db'))
table = db.create_table('passages', rows + [extra], mode='create')
table.create_index('text', config=FTS(stem=False, remove_stop_words=False,
    ascii_folding=False, max_token_length=256))
result({'row_count': len(rows), 'rows_digest': digest(rows)})
'''
    cfg, _, _, _ = signed_index(index_script=script)
    with pytest.raises(ValueError, match='rows differ'):
        build_index(cfg, allow_provider=True)
    generation_dir = next((Path(cfg['index_dir']) / 'generations').iterdir())
    assert not (generation_dir / 'published.json').exists()
    assert (generation_dir / 'index-error.json').exists()


def test_index_child_guessing_and_tampering_with_host_ledger_is_detected(signed_index):
    script = '''from pathlib import Path
from .common import request, result
data = request()
staging = Path(data['paths']['index_staging'])
assert set(data['paths']) == {'index_staging'}
ledger = staging.parent / 'stages' / 'record.json'
ledger.write_text(ledger.read_text() + ' ')
result({'row_count': data['arguments']['row_count'],
        'rows_digest': data['arguments']['rows_digest']})
'''
    cfg, _, _, _ = signed_index(index_script=script)
    with pytest.raises(Exception):
        build_index(cfg, allow_provider=True)
    generation_dir = next((Path(cfg['index_dir']) / 'generations').iterdir())
    assert not (generation_dir / 'published.json').exists()
    assert (generation_dir / 'index-error.json').exists()


def test_registry_change_during_index_child_blocks_publication(signed_index, monkeypatch):
    cfg, registry, section, _ = signed_index()
    from attune_harness import plugin_runtime
    original = plugin_runtime.invoke
    def changed_after_index(argv, *args, **kwargs):
        result = original(argv, *args, **kwargs)
        if json.loads(Path(argv[-1]).read_text())['entry'].endswith('.index'):
            section['revoked'] = ['a' * 64]
            registry.write_text(json.dumps({'extensions': section}), encoding='utf-8')
        return result
    monkeypatch.setattr(plugin_runtime, 'invoke', changed_after_index)
    with pytest.raises(plugin_runtime.PluginUnresolved):
        build_index(cfg, allow_provider=True)
    generation_dir = next((Path(cfg['index_dir']) / 'generations').iterdir())
    assert not (generation_dir / 'published.json').exists()
    assert (generation_dir / 'index-error.json').exists()


def test_interrupted_local_index_retains_staging_and_never_automatically_relaunches(signed_index, monkeypatch):
    cfg, _, _, _ = signed_index()
    from attune_harness import plugin_runtime
    def interrupted(*a, **kw):
        raise plugin_runtime.PluginUnresolved('interrupted', {'failure': 'output_limit'})
    monkeypatch.setattr(plugin_runtime, 'run_voyage_index', interrupted)
    with pytest.raises(plugin_runtime.PluginUnresolved):
        build_index(cfg, allow_provider=True)
    generation_dir = next((Path(cfg['index_dir']) / 'generations').iterdir())
    assert not (generation_dir / 'published.json').exists()
    assert (generation_dir / 'index_staging/rows.json').is_file()
    monkeypatch.setattr(plugin_runtime, 'run_voyage_index', lambda *a, **kw: pytest.fail('restarted local child'))
    with pytest.raises(ValueError, match='Retained index error'):
        build_index(cfg, allow_provider=True)


@pytest.mark.parametrize('tamper_manifest', [False, True])
def test_completed_child_interruption_recovers_only_with_unchanged_host_evidence(
        signed_index, monkeypatch, tamper_manifest):
    cfg, _, _, _ = signed_index()
    from attune_harness import plugin_runtime
    original = plugin_runtime.run_voyage_index
    def interrupted_after_completion(*args, **kwargs):
        original(*args, **kwargs)
        raise KeyboardInterrupt('simulated host interruption after child completion')
    monkeypatch.setattr(plugin_runtime, 'run_voyage_index', interrupted_after_completion)
    with pytest.raises(KeyboardInterrupt):
        build_index(cfg, allow_provider=True)
    directory = next((Path(cfg['index_dir']) / 'generations').iterdir())
    assert (directory / 'index_staging/db/passages.lance').exists()
    assert not (directory / 'index-error.json').exists()
    if tamper_manifest:
        manifest = directory / 'manifest.json'
        manifest.write_text(manifest.read_text() + ' ', encoding='utf-8')
    monkeypatch.setattr(plugin_runtime, 'run_voyage_index',
        lambda *a, **kw: pytest.fail('interrupted index child relaunched'))
    if tamper_manifest:
        with pytest.raises(ValueError, match='Retained index attempt changed'):
            build_index(cfg, allow_provider=True)
        assert not (directory / 'published.json').exists()
    else:
        built = build_index(cfg, allow_provider=True)
        assert built['status'] == 'completed' and built['provider_calls'] == 0
        assert (directory / 'published.json').exists()
