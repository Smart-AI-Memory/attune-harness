"""Signed offline subprocess receipts for the host-owned Voyage stage journal."""
# ruff: noqa: F811 -- imported pytest fixtures are injected by name.

import copy
import json
from pathlib import Path
import zipfile

import pytest

from attune_harness import extensions as ext, plugin_runtime
from attune_harness.features import FeatureUnavailable
from attune_harness.review_contract import digest
from attune_harness.review_store import RunStore, read_record
from attune_harness.voyage_index import build_index
from attune_harness.voyage_provider import PaidStageUnresolved, StageJournal, embeddings, ranking
from attune_harness.voyage_retrieval import retrieve_voyage
from attune_harness.voyage_sources import config
from test_extensions import bundle  # noqa: F401
from test_plugin_signing import base_signer, signers, signer, sign_bundle  # noqa: F401
from test_review import change
from test_voyage import corpus  # noqa: F401

EMBED = {'texts': ['offline passage'], 'input_type': 'document'}
RERANK = {'query': 'offline', 'documents': ['first', 'second'], 'k': 2}
VECTOR = [1.0] + [0.0] * 1023
GRANT = {'secrets': ['VOYAGE_API_KEY'], 'scratch': True, 'time': 2,
         'output': {'result': 65536, 'diagnostics': 8192}}
TOOL = {'binding': 'run', 'entry': 'main', 'input_schema': {'type': 'object'},
        'output_schema': {'type': 'object'}}
SCRIPT = '''import json, os, sys
from pathlib import Path
request = json.loads(Path(sys.argv[1]).read_text())
assert os.environ.get('VOYAGE_API_KEY') == 'offline-test-not-a-real-key'
assert request['paths'] == {}  # Host ledger and stage paths are never granted.
args = request['arguments']
if 'texts' in args:
    result = {'vectors': [[1.0] + [0.0] * 1023 for _ in args['texts']], 'total_tokens': 7}
else:
    result = {'ranking': [{'index': 1, 'score': 0.9}, {'index': 0, 'score': 0.8}], 'total_tokens': 11}
Path(sys.argv[2]).write_text(json.dumps(result))
'''


@pytest.fixture
def signed_stage(corpus, bundle, signer, tmp_path, monkeypatch):
    root, cfg, _ = corpus
    monkeypatch.setenv('VOYAGE_API_KEY', 'offline-test-not-a-real-key')
    closure = {'versions': {'voyageai': '0.5.0', 'lancedb': '0.38.0'},
               'top_levels': ['voyageai', 'lancedb'], 'roots': [], 'files': [], 'metadata': {}}
    monkeypatch.setattr(plugin_runtime, 'resolve_imports', lambda _: copy.deepcopy(closure))

    def prepare(script=SCRIPT, *, time=2):
        with zipfile.ZipFile(bundle.parent / 'plugin.zip', 'w') as stream:
            stream.writestr('main.py', script)
        grant = {**GRANT, 'time': time}
        change(bundle, lambda d: d.update(id='voyage', code='plugin.zip',
            tools={role: copy.deepcopy(TOOL) for role in ('embed', 'rerank', 'index')},
            grants=copy.deepcopy(grant),
            declares={'imports': ['voyageai', 'lancedb'], 'network': ['api.voyageai.com']}))
        artifact = sign_bundle(bundle, signer)
        state_dir = tmp_path / 'plugin-state'
        state = ext.install(bundle, state_dir)
        section = {'voyage': {'state_dir': str(state_dir), 'artifact_digest': artifact,
                               'grant': copy.deepcopy(grant)}, 'signers': [signer.entry]}
        registry = tmp_path / 'registry.json'
        registry.write_text(json.dumps({'extensions': section}), encoding='utf-8')
        state = ext.mutate(state_dir, state['state_digest'], 'enable', registry=registry)
        chosen = copy.deepcopy(cfg)
        chosen['voyage_plugin'] = {'registry': str(registry),
                                   'registry_digest': digest(ext._registry_section(registry)),
                                   'extension_id': 'voyage',
                                   'tools': {'embed': 'embed', 'rerank': 'rerank', 'index': 'index'}}
        return config(chosen, root.parent), registry, section, state_dir, state
    return prepare


def stage_records(directory):
    ledger = read_record(directory)
    return ledger, [read_record(directory / key) for key in ledger['stages']]


def test_signed_embed_rerank_and_replay_without_key_or_permission(signed_stage, tmp_path, monkeypatch):
    cfg, _, _, _, _ = signed_stage()
    directory = tmp_path / 'stages'
    journal = StageJournal(directory, cfg, allow_provider=True)
    embed, first = journal.perform('embed', EMBED, lambda v: embeddings(v, 1))
    reranked, second = journal.perform('rerank', RERANK, lambda v: ranking(v, 2, 2))
    assert embed == {'vectors': [VECTOR], 'total_tokens': 7}
    assert reranked == {'ranking': [{'index': 1, 'score': 0.9}, {'index': 0, 'score': 0.8}], 'total_tokens': 11}
    assert [first['kind'], second['kind']] == ['embed', 'rerank']
    assert [first['new_tokens'], second['new_tokens']] == [7, 11]
    ledger, stages = stage_records(directory)
    assert len(ledger['stages']) == 2 and [stage['status'] for stage in stages] == ['completed', 'completed']
    assert 'offline-test-not-a-real-key' not in json.dumps({'ledger': ledger, 'stages': stages})
    legacy_cfg = copy.deepcopy(cfg)
    legacy_cfg.pop('voyage_plugin')
    class FixtureProvider:
        def embed(self, texts, input_type):
            return {'vectors': [VECTOR for _ in texts], 'total_tokens': 7}
        def rerank(self, query, documents, k):
            return {'ranking': [{'index': 1, 'score': 0.9}, {'index': 0, 'score': 0.8}], 'total_tokens': 11}
    legacy_dir = tmp_path / 'legacy-stages'
    legacy = StageJournal(legacy_dir, legacy_cfg, allow_provider=True, provider=FixtureProvider())
    legacy.perform('embed', EMBED, lambda v: embeddings(v, 1))
    legacy.perform('rerank', RERANK, lambda v: ranking(v, 2, 2))
    old_ledger, old_stages = stage_records(legacy_dir)
    assert ledger['stages'] == old_ledger['stages']
    for selected_record, old_record in zip(stages, old_stages):
        assert selected_record['status'] == old_record['status'] == 'completed'
        assert selected_record['result'] == old_record['result']
        for field in ('stage_id', 'kind', 'total_tokens', 'new_tokens', 'new_cost_usd',
                      'usage_status', 'rate_snapshot'):
            assert selected_record['receipt'][field] == old_record['receipt'][field]
    monkeypatch.delenv('VOYAGE_API_KEY')
    monkeypatch.setattr(plugin_runtime, 'run_voyage_paid', lambda *a, **kw: pytest.fail('replay launched child'))
    replay = StageJournal(directory, cfg, allow_provider=False)
    value, receipt = replay.perform('embed', EMBED, lambda v: embeddings(v, 1))
    assert value == embed and receipt['replayed'] is True
    assert receipt['new_tokens'] == 0 and receipt['new_cost_usd'] == 0.0


def test_missing_key_refuses_without_new_stage_sidecar(signed_stage, tmp_path, monkeypatch):
    cfg, _, _, _, _ = signed_stage()
    monkeypatch.delenv('VOYAGE_API_KEY')
    directory = tmp_path / 'stages'
    journal = StageJournal(directory, cfg, allow_provider=True)
    with pytest.raises(FeatureUnavailable, match='VOYAGE_API_KEY'):
        journal.perform('embed', EMBED, lambda v: embeddings(v, 1))
    assert stage_records(directory) == (read_record(directory), [])
    assert read_record(directory)['stages'] == []


def test_real_child_timeout_retains_dispatching_and_blocks_retry(signed_stage, tmp_path):
    script = '''import time\ntime.sleep(10)\n'''
    cfg, _, _, _, _ = signed_stage(script, time=1)
    directory = tmp_path / 'stages'
    journal = StageJournal(directory, cfg, allow_provider=True)
    with pytest.raises(PaidStageUnresolved, match='interrupted'):
        journal.perform('embed', EMBED, lambda v: embeddings(v, 1))
    ledger, stages = stage_records(directory)
    assert len(ledger['stages']) == 1 and stages[0]['status'] == 'dispatching'
    for allowed in (False, True):
        with pytest.raises(PaidStageUnresolved, match='may have been billed'):
            StageJournal(directory, cfg, allow_provider=allowed).perform('embed', EMBED, lambda v: embeddings(v, 1))
    assert stage_records(directory)[0]['stages'] == ledger['stages']


@pytest.mark.parametrize('failure', ['timeout_effects_unknown', 'interrupted_effects_unknown',
                                     'cancelled_effects_unknown', 'output_limit'])
def test_uncertain_child_failure_classification_retains_dispatching(signed_stage, tmp_path, monkeypatch, failure):
    cfg, _, _, _, _ = signed_stage()
    def stopped(*args, **kwargs):
        raise plugin_runtime.PluginUnresolved('child stopped', {'failure': failure})
    monkeypatch.setattr(plugin_runtime, 'run_voyage_paid', stopped)
    directory = tmp_path / 'stages'
    with pytest.raises(PaidStageUnresolved, match='interrupted'):
        StageJournal(directory, cfg, allow_provider=True).perform('embed', EMBED, lambda v: embeddings(v, 1))
    assert stage_records(directory)[1][0]['status'] == 'dispatching'
    with pytest.raises(PaidStageUnresolved, match='may have been billed'):
        StageJournal(directory, cfg, allow_provider=True).perform('embed', EMBED, lambda v: embeddings(v, 1))


@pytest.mark.parametrize('script', [
    "import sys; from pathlib import Path; Path(sys.argv[2]).write_text('{}')",
    "import sys; from pathlib import Path; Path(sys.argv[2]).write_text('{invalid')",
    "raise SystemExit(3)",
    "import json,sys; from pathlib import Path; Path(sys.argv[2]).write_text(json.dumps({'vectors': [[1.0]], 'total_tokens': 7}))",
    "import json,sys; from pathlib import Path; Path(sys.argv[2]).write_text(json.dumps({'vectors': [[1.0]+[0.0]*1023], 'total_tokens': -1}))",
])
def test_invalid_child_response_records_unresolved(signed_stage, tmp_path, script):
    cfg, _, _, _, _ = signed_stage(script)
    directory = tmp_path / 'stages'
    with pytest.raises(PaidStageUnresolved, match='response unavailable or invalid'):
        StageJournal(directory, cfg, allow_provider=True).perform('embed', EMBED, lambda v: embeddings(v, 1))
    assert stage_records(directory)[1][0]['status'] == 'unresolved'


def test_invalid_rerank_indices_record_unresolved(signed_stage, tmp_path):
    script = '''import json, sys
from pathlib import Path
Path(sys.argv[2]).write_text(json.dumps({'ranking': [{'index': 0, 'score': 0.9},
    {'index': 0, 'score': 0.8}], 'total_tokens': 11}))
'''
    cfg, _, _, _, _ = signed_stage(script)
    directory = tmp_path / 'stages'
    with pytest.raises(PaidStageUnresolved, match='response unavailable or invalid'):
        StageJournal(directory, cfg, allow_provider=True).perform('rerank', RERANK, lambda v: ranking(v, 2, 2))
    assert stage_records(directory)[1][0]['status'] == 'unresolved'


def test_registry_change_during_child_discards_result(signed_stage, tmp_path, monkeypatch):
    cfg, registry, section, _, _ = signed_stage()
    original = plugin_runtime.invoke
    def change_after_child(*args, **kwargs):
        result = original(*args, **kwargs)
        section['revoked'] = ['a' * 64]  # Complete-section pin changes mid-call.
        registry.write_text(json.dumps({'extensions': section}), encoding='utf-8')
        return result
    monkeypatch.setattr(plugin_runtime, 'invoke', change_after_child)
    directory = tmp_path / 'stages'
    with pytest.raises(PaidStageUnresolved, match='response unavailable or invalid'):
        StageJournal(directory, cfg, allow_provider=True).perform('embed', EMBED, lambda v: embeddings(v, 1))
    assert stage_records(directory)[1][0]['status'] == 'unresolved'


@pytest.mark.parametrize('wrong', ['arguments', 'rerank', 'index'])
def test_direct_paid_runner_rejects_wrong_stage_binding_before_invoke(signed_stage, tmp_path, monkeypatch, wrong):
    cfg, _, _, _, _ = signed_stage()
    original = plugin_runtime.run_voyage_paid
    def wrong_binding(bundle, tool_name, tool, arguments, **kwargs):
        if wrong == 'arguments':
            arguments = {**arguments, 'texts': ['different paid request']}
        else:
            tool_name = wrong
            tool = bundle['declaration']['tools'][wrong]
        return original(bundle, tool_name, tool, arguments, **kwargs)
    monkeypatch.setattr(plugin_runtime, 'run_voyage_paid', wrong_binding)
    monkeypatch.setattr(plugin_runtime, 'invoke', lambda *a, **kw: pytest.fail('wrong binding launched child'))
    directory = tmp_path / 'stages'
    with pytest.raises(PaidStageUnresolved, match='response unavailable or invalid'):
        StageJournal(directory, cfg, allow_provider=True).perform('embed', EMBED, lambda v: embeddings(v, 1))
    assert stage_records(directory)[1][0]['status'] == 'unresolved'


def test_registration_change_during_child_discards_result(signed_stage, tmp_path, monkeypatch):
    cfg, _, _, state_dir, _ = signed_stage()
    original = plugin_runtime.invoke
    def change_after_child(*args, **kwargs):
        result = original(*args, **kwargs)
        state = read_record(state_dir)
        state['revision'] += 1
        state['status'] = 'disabled'
        state.pop('plugin')
        state['state_digest'] = digest({key: value for key, value in state.items() if key != 'state_digest'})
        RunStore(state_dir, existing=True).save(state)
        return result
    monkeypatch.setattr(plugin_runtime, 'invoke', change_after_child)
    directory = tmp_path / 'stages'
    with pytest.raises(PaidStageUnresolved, match='response unavailable or invalid'):
        StageJournal(directory, cfg, allow_provider=True).perform('embed', EMBED, lambda v: embeddings(v, 1))
    assert stage_records(directory)[1][0]['status'] == 'unresolved'


def test_selected_high_level_paths_still_refuse_before_fallback(signed_stage, tmp_path):
    cfg, _, _, _, _ = signed_stage()
    class Poison:
        def embed(self, *a):
            pytest.fail('builtin provider called')
        def rerank(self, *a):
            pytest.fail('builtin provider called')
    with pytest.raises(FeatureUnavailable, match='dispatch is unavailable'):
        build_index(cfg, allow_provider=True, provider=Poison())
    with pytest.raises(FeatureUnavailable, match='dispatch is unavailable'):
        retrieve_voyage({'config': cfg}, 'query', work_dir=tmp_path / 'work',
                        allow_provider=True, provider=Poison())
    assert not Path(cfg['index_dir']).exists() and not (tmp_path / 'work').exists()


def test_generic_network_run_still_refuses(signed_stage):
    cfg, registry, section, state_dir, state = signed_stage()
    bundle = ext._current(state, section['voyage']['artifact_digest'], enabled=True,
                          scope=ext._scope_for(ext._registry_section(registry), 'voyage', state_dir))
    with pytest.raises(FeatureUnavailable, match='host-owned paid-stage journal'):
        plugin_runtime.run(bundle, bundle['declaration']['tools']['embed'], EMBED,
                           paths={}, guarded_paths=(), postcheck=lambda: None)
