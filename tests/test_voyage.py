"""Real local LanceDB, injected paid providers. These tests do not measure model quality."""

import copy
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from attune_harness import voyage_provider as provider_module
from attune_harness import voyage_retrieval as retrieval
from attune_harness.cli import main
from attune_harness.features import FeatureUnavailable
from attune_harness.review_contract import digest, load_registry, review_form
from attune_harness.review_store import PersistenceError, read_record
from attune_harness.voyage_index import (build_index, check_generation, index_plan, read_generation, selection)
from attune_harness.voyage_provider import PaidStageUnresolved, StageJournal, embeddings, ranking
from attune_harness.voyage_sources import collect, config, sha, snapshot


def git(root, *args):
    subprocess.run(['git', '-C', str(root), '-c', 'commit.gpgsign=false',
                    '-c', 'core.hooksPath=' + str(root / '.no-hooks'), *args], check=True, capture_output=True)


def repository(root, files):
    root.mkdir()
    git(root, 'init')
    for path, content in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode('utf-8'))
    git(root, 'add', '.')
    git(root, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-m', 'fixture')
    return root


class FakeProvider:
    """Finite deterministic fixtures for contracts only, not a semantic baseline."""
    def __init__(self):
        self.calls = []

    def embed(self, texts, input_type):
        self.calls.append(('embed', input_type, texts))
        return {'vectors': [[1.0] + [0.0] * 1023 for _ in texts], 'total_tokens': 100 * len(texts)}

    def rerank(self, query, documents, k):
        self.calls.append(('rerank', query, documents))
        order = sorted(range(len(documents)), key=lambda i: (query not in documents[i], i))[:k]
        return {'ranking': [{'index': i, 'score': 1.0 - rank / 100} for rank, i in enumerate(order)], 'total_tokens': 500 * len(documents)}


@pytest.fixture
def corpus(tmp_path):
    root = repository(tmp_path / 'app', {'app.py': '# café 💡\r\n\r\ndef login_user():\r\n    return "authenticated"\r\n\r\ndef save_cart():\r\n    return "persisted"\r\n',
                                       'README.md': '# App\n\nSelected application conventions.\n',
                                       'ledger.json': '{"status":"passed"}'})
    cfg = config({'schema_version': 1, 'roots': [{'repo_id': 'app', 'path': str(root)}],
                  'index_dir': str(tmp_path / 'index'), 'allow_overlays': True}, tmp_path)
    return root, cfg, FakeProvider()


@pytest.fixture
def built(corpus):
    root, cfg, provider = corpus
    built = build_index(cfg, allow_provider=True, provider=provider)
    return root, selection(cfg, built['generation']), provider


def test_offline_plan_and_byte_exact_symbol_passages(corpus):
    root, cfg, provider = corpus
    plan = index_plan(cfg)
    manifest, passages = collect(cfg)
    assert plan['provider_calls'] == 0 and not Path(cfg['index_dir']).exists()
    assert {f['path'] for f in manifest['files']} == {'app.py', 'README.md'}
    source = (root / 'app.py').read_bytes()
    found = next(p for p in passages if p['excerpt'].startswith('def login_user'))
    assert found['start_byte'] == source.index(b'def login_user')
    assert found['chunk_method'] == 'python-symbol' and '\r\n' in found['excerpt']
    for p in passages:
        raw = (root / p['path']).read_bytes()
        assert raw[p['start_byte']:p['end_byte']].decode() == p['excerpt']
        assert sha(p['excerpt'].encode()) == p['passage_sha256']


def test_markdown_fence_and_long_unicode_lines(corpus):
    root, cfg, _ = corpus
    (root / 'README.md').write_text('# Heading\n```python\n# not a heading\n```\n' + '💡' * 1100, encoding='utf-8')
    _, passages = collect(cfg)
    selected = [p for p in passages if p['path'] == 'README.md']
    assert '# not a heading' in selected[0]['excerpt']
    assert all(len(p['excerpt'].encode()) <= cfg['passage_bytes'] for p in selected)
    assert ''.join(p['excerpt'] for p in selected).encode() == (root / 'README.md').read_bytes()


@pytest.mark.parametrize('change', [lambda c: c.update(max_files=True), lambda c: c.update(embedding_model='other'),
                                  lambda c: c.update(allow_untracked=1), lambda c: c.update(include=['../*.py']),
                                  lambda c: c.update(roots=c['roots'] * 2)])
def test_invalid_config(corpus, change):
    _, cfg, _ = corpus
    change(cfg)
    with pytest.raises(ValueError):
        config(cfg, Path.cwd())


def test_overlays_untracked_and_symlink_selection(corpus):
    root, cfg, _ = corpus
    (root / 'new.py').write_text('untracked = True')
    assert not any(f['path'] == 'new.py' for f in snapshot(cfg)[0]['files'])
    cfg['allow_untracked'] = True
    assert any(f['selection'] == 'untracked' for f in snapshot(cfg)[0]['files'])
    (root / 'app.py').write_text('changed = True')
    cfg['allow_overlays'] = False
    with pytest.raises(ValueError, match='allow_overlays'):
        snapshot(cfg)
    cfg['allow_overlays'] = True
    (root / 'new.py').unlink()
    try:
        (root / 'new.py').symlink_to(root / 'app.py')
    except OSError:
        pytest.skip('Platform does not permit symlink creation')
    with pytest.raises(ValueError, match='symlink'):
        snapshot(cfg)


def test_real_index_reopen_retrieval_and_same_run_reuse(built, tmp_path):
    root, selected, provider = built
    provider.calls.clear()
    first = retrieval.retrieve_voyage(selected, 'save_cart', k=2, work_dir=tmp_path / 'run', allow_provider=True, provider=provider)
    assert 'save_cart' in first['sources'][0]['excerpt']
    assert [c[0] for c in provider.calls] == ['embed', 'rerank']
    assert first['usage']['new_provider_calls'] == 2
    second = retrieval.retrieve_voyage(selected, 'save_cart', k=2, work_dir=tmp_path / 'run')
    assert second['sources'] == first['sources']
    assert second['usage'] == {'new_provider_calls': 0, 'new_tokens': 0, 'new_cost_usd': 0.0}
    assert second['replay']['original_request_id'] == first['request_id']
    assert not second['replay']['provider_health_checked']
    (root / 'app.py').write_text('changed = True')
    with pytest.raises(ValueError, match='Stale index'):
        retrieval.retrieve_voyage(selected, 'save_cart', k=2, work_dir=tmp_path / 'run')
    assert len(provider.calls) == 2


def test_updates_reuse_unchanged_inputs_and_remove_deleted_passages(built):
    root, selected, provider = built
    cfg, base = selected['config'], selected['generation']
    provider.calls.clear()
    same = build_index(cfg, base_generation=base)
    assert same['generation'] == base and same['provider_calls'] == 0
    (root / 'README.md').unlink()
    (root / 'app.py').write_bytes((root / 'app.py').read_bytes().replace(b'persisted', b'saved'))
    new = build_index(cfg, base_generation=base, allow_provider=True, provider=provider)
    assert new['generation'] != base and new['reused_embeddings'] >= 1
    sent = ''.join(t for call in provider.calls for t in call[2])
    assert 'saved' in sent and 'authenticated' not in sent
    old_dir, old = read_generation(cfg, base)
    new_dir, current = read_generation(cfg, new['generation'])
    assert any(p['path'] == 'README.md' for p in old['passages'])
    assert all(p['path'] != 'README.md' for p in current['passages'])


def test_repository_and_path_filters_apply_before_rerank(corpus, tmp_path):
    root, cfg, provider = corpus
    other = repository(tmp_path / 'other', {'app.py': 'def forbidden_secret():\n    return 1\n'})
    cfg['roots'].append({'repo_id': 'other', 'path': str(other)})
    built = build_index(cfg, allow_provider=True, provider=provider)
    selected = selection(cfg, built['generation'])
    selected['scope'] = {'repo_ids': ['app'], 'exclude_paths': [{'repo_id': 'app', 'path': 'README.md'}]}
    provider.calls.clear()
    result = retrieval.retrieve_voyage(selected, 'forbidden_secret', work_dir=tmp_path / 'run', allow_provider=True, provider=provider)
    assert all(p['repo_id'] == 'app' and p['path'] == 'app.py' for p in result['sources'])
    assert all('forbidden_secret' not in d for d in provider.calls[-1][2])


def test_empty_scope_never_calls_provider(built, tmp_path):
    _, selected, provider = built
    selected['scope']['exclude_paths'] = [{'repo_id': 'app', 'path': p} for p in ('app.py', 'README.md')]
    provider.calls.clear()
    result = retrieval.retrieve_voyage(selected, 'save_cart', work_dir=tmp_path / 'empty')
    assert result['status'] == 'no_results' and result['usage']['new_provider_calls'] == 0


def test_provider_selection_explicit_and_budgeted(built, tmp_path):
    _, selected, provider = built
    provider.calls.clear()
    with pytest.raises(FeatureUnavailable, match='allow-provider'):
        retrieval.retrieve_voyage(selected, 'save_cart', work_dir=tmp_path / 'no-permission', provider=provider)
    assert not provider.calls
    cfg = {**selected['config'], 'max_provider_calls': 1}
    journal = StageJournal(tmp_path / 'stages', cfg, allow_provider=True, provider=provider)
    journal.perform('embed', {'texts': ['one'], 'input_type': 'query'}, lambda v: embeddings(v, 1))
    with pytest.raises(PermissionError, match='budget'):
        journal.perform('embed', {'texts': ['two'], 'input_type': 'query'}, lambda v: embeddings(v, 1))
    assert len(provider.calls) == 1


@pytest.mark.parametrize('spent', [False, True])
def test_retrieval_reserves_rerank_budget_before_embedding(corpus, tmp_path, spent):
    _, cfg, provider = corpus
    cfg['max_provider_calls'] = 3 if spent else 1
    index = build_index(cfg, allow_provider=True, provider=provider)
    selected = selection(cfg, index['generation'])
    work = tmp_path / 'run'
    if spent:
        retrieval.retrieve_voyage(selected, 'save_cart', work_dir=work,
                                 allow_provider=True, provider=provider)
    provider.calls.clear()
    with pytest.raises(PermissionError, match='budget'):
        retrieval.retrieve_voyage(selected, 'login_user', work_dir=work,
                                 allow_provider=True, provider=provider)
    assert provider.calls == []
    assert len(read_record(work / 'stages')['stages']) == (2 if spent else 0)


def test_prepared_embedding_reserves_rerank_before_continuation(corpus, tmp_path, monkeypatch):
    _, cfg, provider = corpus
    cfg['max_provider_calls'] = 1
    index = build_index(cfg, allow_provider=True, provider=provider)
    selected = selection(cfg, index['generation'])
    work = tmp_path / 'run'
    work.mkdir()
    journal = StageJournal(work / 'stages', cfg, allow_provider=True)
    def unavailable():
        raise FeatureUnavailable('provider unavailable before dispatch')
    monkeypatch.setattr(provider_module, 'VoyageProvider', unavailable)
    with pytest.raises(FeatureUnavailable):
        journal.perform('embed', {'texts': ['save_cart'], 'input_type': 'query'},
                        lambda value: embeddings(value, 1))
    provider.calls.clear()
    with pytest.raises(PermissionError, match='budget'):
        retrieval.retrieve_voyage(selected, 'save_cart', work_dir=work,
                                 allow_provider=True, provider=provider)
    assert provider.calls == []
    stages = read_record(work / 'stages')['stages']
    assert len(stages) == 1 and read_record(work / 'stages' / stages[0])['status'] == 'prepared'


def test_full_budget_completed_stages_replay_without_final_cache(corpus, tmp_path):
    _, cfg, provider = corpus
    cfg['max_provider_calls'] = 2
    index = build_index(cfg, allow_provider=True, provider=provider)
    selected = selection(cfg, index['generation'])
    work = tmp_path / 'run'
    provider.calls.clear()
    first = retrieval.retrieve_voyage(selected, 'save_cart', k=2, work_dir=work,
                                     allow_provider=True, provider=provider)
    assert [call[0] for call in provider.calls] == ['embed', 'rerank']
    cache = work / (digest({'selection': selected, 'query': 'save_cart', 'k': 2}) + '.json')
    cache.unlink()  # Completed stage receipts must survive a lost final cache.
    provider.calls.clear()
    replay = retrieval.retrieve_voyage(selected, 'save_cart', k=2, work_dir=work)
    assert replay['sources'] == first['sources']
    assert replay['usage']['new_provider_calls'] == 0 and provider.calls == []
    assert all(stage['replayed'] for stage in replay['stages'])


def test_completed_embedding_reused_after_local_failure(built, tmp_path, monkeypatch):
    _, selected, provider = built
    provider.calls.clear()
    original = retrieval.candidates
    monkeypatch.setattr(retrieval, 'candidates', lambda *a: (_ for _ in ()).throw(ValueError('local search failed')))
    with pytest.raises(ValueError, match='local search'):
        retrieval.retrieve_voyage(selected, 'save_cart', work_dir=tmp_path / 'resume', allow_provider=True, provider=provider)
    monkeypatch.setattr(retrieval, 'candidates', original)
    result = retrieval.retrieve_voyage(selected, 'save_cart', work_dir=tmp_path / 'resume', allow_provider=True, provider=provider)
    assert [c[0] for c in provider.calls] == ['embed', 'rerank']
    assert result['stages'][0]['replayed'] and result['usage']['new_provider_calls'] == 1


def test_unknown_paid_effect_never_retried(built, tmp_path, monkeypatch):
    _, selected, provider = built
    provider.calls.clear()
    def lost(*args):
        provider.calls.append(('lost',))
        raise TimeoutError('sensitive provider response must not leak')
    monkeypatch.setattr(provider, 'rerank', lost)
    for _ in range(2):
        with pytest.raises(PaidStageUnresolved):
            retrieval.retrieve_voyage(selected, 'save_cart', work_dir=tmp_path / 'unknown', allow_provider=True, provider=provider)
    assert [c[0] for c in provider.calls] == ['embed', 'lost']
    records = [read_record(p) for p in (tmp_path / 'unknown/stages').iterdir() if p.is_dir()]
    assert any(r['status'] == 'unresolved' for r in records)
    assert 'sensitive' not in json.dumps(records)


@pytest.mark.parametrize('value', [[], [[0.0]*1024], [[1.0]*1023], [[True]*1024], [[float('nan')]*1024]])
def test_invalid_vectors_rejected(value):
    with pytest.raises(ValueError):
        embeddings({'vectors': value, 'total_tokens': 1}, 1)


@pytest.mark.parametrize('rows', [[{'index': True, 'score': .9}], [{'index': -1, 'score': .9}],
                                [{'index': 2, 'score': .9}], [{'index': 0, 'score': float('inf')}],
                                [{'index': 0, 'score': .9}, {'index': 0, 'score': .8}]])
def test_invalid_rerank_rejected(rows):
    with pytest.raises(ValueError):
        ranking({'ranking': rows, 'total_tokens': 1}, 2, len(rows))


def test_missing_usage_remains_unknown(corpus, tmp_path):
    _, cfg, provider = corpus
    provider.embed = lambda *a: {'vectors': [[1.] + [0.] * 1023]}
    result, receipt = StageJournal(tmp_path / 'stage', cfg, allow_provider=True, provider=provider).perform(
        'embed', {'texts': ['text'], 'input_type': 'query'}, lambda v: embeddings(v, 1))
    assert receipt['new_tokens'] is None and receipt['new_cost_usd'] is None
    assert receipt['usage_status'] == 'unknown'


def test_sdk_request_contract_indices_retries_and_truncation(monkeypatch):
    monkeypatch.setenv('VOYAGE_API_KEY', 'test-placeholder')
    provider = provider_module.VoyageProvider()
    observed = []
    def embed(**kwargs):
        from voyageai.api_resources import api_requestor
        observed.append(kwargs)
        assert api_requestor._thread_context.session.adapters['https://'].max_retries.total == 0
        return {'data': [{'index': 1, 'embedding': [0., 1.] + [0.] * 1022},
                         {'index': 0, 'embedding': [1.] + [0.] * 1023}]}
    monkeypatch.setattr(provider.sdk.Embedding, 'create', embed)
    result = provider.embed(['one', 'two'], 'document')
    assert result['vectors'][0][0] == 1 and result['vectors'][1][1] == 1
    assert observed[0]['truncation'] is False and observed[0]['output_dimension'] == 1024
    assert observed[0]['model'] == 'voyage-code-4' and observed[0]['request_timeout'] == 60
    assert result['total_tokens'] is None


def test_coding_session_reuses_evidence_and_enforces_grants(built, tmp_path, monkeypatch):
    from attune_harness.mcp_server import RetrievalSession
    from attune_harness.retrieval_task import task_template
    _, selected, provider = built
    monkeypatch.setattr(provider_module, 'VoyageProvider', lambda: provider)
    task = task_template(selected['config'], selected['generation'], 'Find persistence code', max_calls=2)
    task['accepted'] = True
    request = tmp_path / 'request.json'
    request.write_text(json.dumps(task))
    provider.calls.clear()
    scope = RetrievalSession(request, None, 'coding-agent', tmp_path / 'mcp', allow_provider=True)
    with scope.store.lease():
        scope.save()
        first = scope.invoke('harness.retrieve', {'query': 'save_cart', 'k': 3})
        second = scope.invoke('harness.retrieve', {'query': 'save_cart', 'k': 3})
        with pytest.raises(PermissionError):
            scope.invoke('harness.retrieve', {'query': 'save_cart', 'k': 3})
        scope.finish()
    assert len(provider.calls) == 2 and second['replay']['reused']
    assert scope.record['status'] == 'completed'


def test_cli_offline_plan_and_legacy_retrieval(corpus, tmp_path, capsys):
    root, cfg, _ = corpus
    path = tmp_path / 'config.json'
    path.write_text(json.dumps(cfg))
    assert main(['index', 'plan', '--config', str(path)]) == 0
    assert json.loads(capsys.readouterr().out)['provider_calls'] == 0
    assert main(['retrieve', 'selected application conventions', '--corpus', str(root)]) == 0
    assert json.loads(capsys.readouterr().out)['retriever'] == 'KeywordRetriever'


def test_index_publish_failure_reuses_paid_batches(corpus, monkeypatch):
    from attune_harness import voyage_index
    _, cfg, provider = corpus
    real = voyage_index.database
    monkeypatch.setattr(voyage_index, 'database', lambda *a: (_ for _ in ()).throw(OSError('local disk failure')))
    with pytest.raises(OSError, match='disk'):
        build_index(cfg, allow_provider=True, provider=provider)
    paid = len(provider.calls)
    monkeypatch.setattr(voyage_index, 'database', real)
    result = build_index(cfg, allow_provider=True, provider=provider)
    assert result['provider_calls'] == 0 and len(provider.calls) == paid
    check_generation(cfg, result['generation'])


def test_dispatch_receipt_failure_stops_before_provider(corpus, tmp_path, monkeypatch):
    _, cfg, provider = corpus
    from attune_harness.review_store import RunStore
    original = RunStore.save
    def broken(self, record):
        if record.get('status') == 'dispatching':
            raise PersistenceError('disk failed')
        original(self, record)
    monkeypatch.setattr(RunStore, 'save', broken)
    journal = StageJournal(tmp_path / 'stages', cfg, allow_provider=True, provider=provider)
    with pytest.raises(PersistenceError):
        journal.perform('embed', {'texts': ['one'], 'input_type': 'query'}, lambda v: embeddings(v, 1))
    assert not provider.calls


def test_source_drift_after_paid_rerank_retains_receipts(built, tmp_path, monkeypatch):
    root, selected, provider = built
    real = provider.rerank
    def changed(*args):
        result = real(*args)
        (root / 'app.py').write_text('changed = True')
        return result
    monkeypatch.setattr(provider, 'rerank', changed)
    with pytest.raises(ValueError, match='Stale index'):
        retrieval.retrieve_voyage(selected, 'save_cart', work_dir=tmp_path / 'run', allow_provider=True, provider=provider)
    assert all(read_record(p)['status'] == 'completed' for p in (tmp_path / 'run/stages').iterdir() if p.is_dir())
    assert not list((tmp_path / 'run').glob('*.json')) == []  # Invocation remains inspectable.


def test_index_table_tampering_refused_before_provider(built, tmp_path):
    from attune_harness.voyage_index import database
    _, selected, provider = built
    cfg = selected['config']
    directory, metadata = read_generation(cfg, selected['generation'])
    table = database(directory / 'db').open_table('passages')
    table.update(values={'text': 'tampered'})
    provider.calls.clear()
    with pytest.raises(ValueError, match='table contents changed'):
        retrieval.retrieve_voyage(selected, 'save_cart', work_dir=tmp_path / 'run', allow_provider=True, provider=provider)
    assert not provider.calls


@pytest.mark.parametrize('k', [0, True, 21])
def test_invalid_query_bounds_never_create_work(built, tmp_path, k):
    _, selected, provider = built
    provider.calls.clear()
    with pytest.raises(ValueError, match='k must'):
        retrieval.retrieve_voyage(selected, 'query', k=k, work_dir=tmp_path / 'run', allow_provider=True, provider=provider)
    assert not provider.calls and not (tmp_path / 'run').exists()


def test_oversized_and_invalid_utf8_source_refused(corpus):
    root, cfg, _ = corpus
    (root / 'app.py').write_bytes(b'x' * (cfg['max_file_bytes'] + 1))
    with pytest.raises(ValueError, match='exceeds'):
        index_plan(cfg)
    (root / 'app.py').write_bytes(b'\xff')
    with pytest.raises(UnicodeDecodeError):
        index_plan(cfg)


def test_same_length_source_change_invalidates_generation(built):
    root, selected, _ = built
    path = root / 'README.md'
    path.write_bytes(path.read_bytes().replace(b'Selected', b'Rejected'))
    with pytest.raises(ValueError, match='Stale index'):
        check_generation(selected['config'], selected['generation'])


def test_large_heading_context_is_bounded_without_truncating_evidence(corpus):
    root, cfg, _ = corpus
    raw = ('# ' + '💡' * 10000 + '\n\nDetails.\n').encode()
    (root / 'README.md').write_bytes(raw)
    _, passages = collect(cfg)
    selected = [p for p in passages if p['path'] == 'README.md']
    assert all(len(p['embedding_text'].encode()) < 2600 for p in selected)
    assert ''.join(p['excerpt'] for p in selected).encode() == raw


def test_index_cannot_shadow_the_entire_selected_repository(corpus):
    root, cfg, _ = corpus
    cfg['index_dir'] = str(root)
    with pytest.raises(ValueError, match='contain a selected repository'):
        config(cfg, root)


def test_public_selection_validation_returns_same_object_and_checks_generation(built, monkeypatch):
    from attune_harness import voyage_index as index
    root, selected, _ = built
    original, checked = index.check_generation, []

    def tracked(*args):
        checked.append(args)
        return original(*args)

    monkeypatch.setattr(index, 'check_generation', tracked)
    assert index.load_selection(selected) is selected
    assert checked == [(selected['config'], selected['generation'])]
    (root / 'README.md').write_bytes((root / 'README.md').read_bytes().replace(b'Selected', b'Rejected'))
    with pytest.raises(ValueError, match='Stale index'):
        index.load_selection(selected)


@pytest.mark.parametrize('change', [
    lambda s: s.update(extra='unsupported'),
    lambda s: s.update(config_digest='0' * 64),
    lambda s: s['config'].update(index_dir=s['config']['index_dir'] + '/.'),
    lambda s: s.update(generation='../generation'),
    lambda s: s['scope'].update(repo_ids=['outside']),
])
def test_invalid_selection_rejected_before_work_or_provider(built, tmp_path, change):
    _, selected, provider = built
    change(selected)
    provider.calls.clear()
    with pytest.raises(ValueError):
        retrieval.retrieve_voyage(selected, 'save_cart', work_dir=tmp_path / 'refused', allow_provider=True, provider=provider)
    assert not provider.calls and not (tmp_path / 'refused').exists()


def alter_index_fixture(root, selected, kind):
    """Faults target independent source, publication and database guards."""
    from attune_harness.voyage_index import database, write_json
    if kind == 'source':
        # Unrelated to the returned save_cart excerpt; preserves file length.
        path = root / 'README.md'
        path.write_bytes(path.read_bytes().replace(b'Selected', b'Rejected'))
    elif kind == 'revision':
        git(root, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
            'commit', '--allow-empty', '-m', 'revision only')
    elif kind == 'added':
        (root / 'new.py').write_text('new_value = 1\n', encoding='utf-8')
        git(root, 'add', 'new.py')
    elif kind == 'deleted':
        (root / 'README.md').unlink()
    else:
        directory, metadata = read_generation(selected['config'], selected['generation'])
        if kind == 'metadata':
            metadata['passages'][0]['excerpt'] += 'changed'
            write_json(directory / 'manifest.json', metadata)
        elif kind == 'publication':
            publication = json.loads((directory / 'published.json').read_text())
            publication['receipt_digest'] = '0' * 64
            write_json(directory / 'published.json', publication)
        else:
            table = database(directory / 'db').open_table('passages')
            table.update(values={'vector': [0.0, 1.0] + [0.0] * 1022} if kind == 'vector' else {'text': 'altered'})


@pytest.mark.parametrize('cached', [False, True])
@pytest.mark.parametrize('kind', ['source', 'revision', 'added', 'deleted', 'metadata', 'publication', 'text', 'vector'])
def test_retrieval_revalidates_all_integrity_inputs_on_every_call(built, tmp_path, cached, kind):
    root, selected, provider = built
    work = tmp_path / 'run'
    if cached:
        result = retrieval.retrieve_voyage(selected, 'save_cart', k=1, work_dir=work, allow_provider=True, provider=provider)
        assert result['sources'][0]['path'] == 'app.py'
    alter_index_fixture(root, selected, kind)
    provider.calls.clear()
    with pytest.raises(ValueError):
        retrieval.retrieve_voyage(selected, 'save_cart', k=1, work_dir=work, allow_provider=True, provider=provider)
    assert not provider.calls
    if not cached:
        assert not work.exists()


@pytest.mark.parametrize('boundary', ['embed', 'candidates', 'rerank'])
@pytest.mark.parametrize('kind', ['source', 'vector', 'metadata'])
def test_retained_boundary_stops_mutation_before_next_effect_or_evidence(built, tmp_path, monkeypatch, boundary, kind):
    root, selected, provider = built
    target = retrieval if boundary == 'candidates' else provider
    original = getattr(target, boundary)

    def changed(*args):
        result = original(*args)
        alter_index_fixture(root, selected, kind)
        return result

    monkeypatch.setattr(target, boundary, changed)
    provider.calls.clear()
    work = tmp_path / 'run'
    with pytest.raises(ValueError):
        retrieval.retrieve_voyage(selected, 'save_cart', k=1, work_dir=work, allow_provider=True, provider=provider)
    assert [c[0] for c in provider.calls] == (['embed', 'rerank'] if boundary == 'rerank' else ['embed'])
    key = digest({'selection': selected, 'query': 'save_cart', 'k': 1})
    assert not (work / (key + '.json')).exists()
    assert read_record(work)['invocations'][-1]['state'] == 'prepared'
    assert all(read_record(p)['status'] == 'completed' for p in (work / 'stages').iterdir() if p.is_dir())


@pytest.mark.parametrize('kind', ['source', 'vector', 'metadata'])
def test_cached_evidence_still_checks_changes_after_entry(built, tmp_path, monkeypatch, kind):
    root, selected, provider = built
    work = tmp_path / 'run'
    retrieval.retrieve_voyage(selected, 'save_cart', k=1, work_dir=work, allow_provider=True, provider=provider)
    key = digest({'selection': selected, 'query': 'save_cart', 'k': 1})
    cached = work / (key + '.json')
    original = retrieval.read_json

    def changed(path):
        result = original(path)
        if path == cached:
            alter_index_fixture(root, selected, kind)
        return result

    monkeypatch.setattr(retrieval, 'read_json', changed)
    provider.calls.clear()
    with pytest.raises(ValueError):
        retrieval.retrieve_voyage(selected, 'save_cart', k=1, work_dir=work, provider=provider)
    assert not provider.calls
    assert read_record(work)['invocations'][-1]['state'] == 'prepared'


def test_portable_offline_probe_in_fresh_directory_and_no_overwrite(tmp_path):
    import os
    import sys
    script = Path(__file__).resolve().parents[1] / 'experiments/voyage/profile_validation.py'
    source = script.parents[2]
    fixture, output = tmp_path / 'fixture', tmp_path / 'samples'
    command = [sys.executable, str(script)]
    env = {k: v for k, v in os.environ.items() if k not in ('VOYAGE_API_KEY', 'PYTHONPATH')}
    prepare = command + ['prepare', '--source', str(source), '--workspace', str(fixture), '--files', '1', '--symbols', '2']
    run = subprocess.run(prepare, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)['live_provider_calls'] == 0
    measure = command + ['measure', '--source', str(source), '--workspace', str(fixture), '--output', str(output)]
    run = subprocess.run(measure, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, run.stderr
    result = json.loads((output / 'result.json').read_text())
    assert result['live_provider_calls'] == 0 and result['fixture']['passages'] == 2
    assert {mode: summary['full_check_counts'] for mode, summary in result['summary'].items()} == {
        'direct_recompute': [4], 'direct_cached': [3], 'session_setup': [1],
        'session_recompute': [6], 'session_cached': [5]}
    before = (output / 'result.json').read_bytes()
    assert subprocess.run(measure, cwd=tmp_path, env=env, capture_output=True, timeout=60).returncode != 0
    assert subprocess.run(prepare, cwd=tmp_path, env=env, capture_output=True, timeout=60).returncode != 0
    assert (output / 'result.json').read_bytes() == before
