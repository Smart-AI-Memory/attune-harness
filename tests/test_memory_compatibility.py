"""Characterize existing Attune memory services using disposable on-disk data.

These are compatibility probes, not qualification of a new worker or adapter.
Run with the optional Attune AI and RAG packages; the portable base may skip.
"""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import socket
import time

import pytest


FIXTURE = Path(__file__).parent / 'fixtures' / 'memory_compatibility.json'


@pytest.fixture(autouse=True)
def isolated_services(tmp_path, monkeypatch):
    pytest.importorskip('attune')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('ATTUNE_HOME', str(tmp_path / 'attune-home'))
    monkeypatch.setenv('ATTUNE_USAGE_PING', '0')
    monkeypatch.setenv('ATTUNE_MEMORY_TELEMETRY', '1')
    monkeypatch.delenv('DO_NOT_TRACK', raising=False)
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append('network or provider')
        raise AssertionError('Compatibility probe attempted network/provider access')

    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(socket.socket, 'connect_ex', forbidden)
    from attune.memory import personal
    monkeypatch.setattr(personal, '_load_author', forbidden)
    monkeypatch.setattr(personal, '_GLOBAL_ROOT', tmp_path / 'unused-global')
    yield
    assert attempts == []


@pytest.fixture
def legacy():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')


def seed_raw(root, legacy):
    root.mkdir(parents=True)
    records = [dict(id=r['id'], text=r['text'], session_id='synthetic-session',
                    topics=[f"type:{r['type']}", f"cwd:{r['cwd']}"],
                    cwd=r['cwd'], ts=time.time(), future_field={'keep': True})
               for r in legacy['raw']]
    source = root / 'findings.jsonl'
    source.write_text(''.join(json.dumps(r) + '\n' for r in records), encoding='utf-8')
    return source


def seed_documents(tmp_path, legacy):
    sources = {}
    for entry in legacy['documents']:
        path = tmp_path / entry['root'] / entry['path']
        path.parent.mkdir(parents=True, exist_ok=True)
        body = (entry['body'] + '\n\n') * entry.get('repeat', 1) + entry.get('tail', '')
        path.write_text('# Aurora\n\n' + body, encoding='utf-8')
        sources[(entry['root'], entry['path'])] = path.read_bytes()
    return sources


def reader(root):
    from attune.memory.personal import PersonalMemory
    # Same explicit root suppresses implicit cwd/project discovery in this API.
    return PersonalMemory(global_root=root, project_root=root)


def test_raw_legacy_recall_keeps_evidence_and_bytes(tmp_path, legacy):
    from attune.memory.file_stash import FileStashBackend
    from attune.memory.session_stash import recall_entries
    source = seed_raw(tmp_path / 'raw', legacy)
    before = source.read_bytes()
    hits = recall_entries('Aurora', top_k=20, cwd='project-a',
                          backend=FileStashBackend(base_dir=source.parent))
    assert {h['id']: h['text'] for h in hits} == {r['id']: r['text'] for r in legacy['raw']}
    assert all(h['provenance']['tier'] == 'raw' for h in hits)
    assert {t for h in hits for t in h['topics'] if t.startswith('type:')} == {
        f"type:{r['type']}" for r in legacy['raw']}
    assert source.read_bytes() == before  # Includes unknown stored fields.
    # Existing cwd filtering is ordering, not access isolation.
    assert hits[-1]['cwd'] == 'project-b'


def test_raw_legacy_read_does_not_apply_new_entry_length_limit(tmp_path, legacy):
    from attune.memory.file_stash import FileStashBackend
    from attune.memory.session_stash import SessionStashEntry, recall_entries
    legacy['raw'][0]['text'] = 'Aurora long source. ' * 100 + 'FINAL_DETAIL'
    source = seed_raw(tmp_path / 'raw', legacy)
    hits = recall_entries('Aurora', top_k=20, backend=FileStashBackend(base_dir=source.parent))
    assert next(h['text'] for h in hits if h['id'] == 'N1') == legacy['raw'][0]['text']
    entry = SessionStashEntry.create('synthetic', 'project-a', 'note', legacy['raw'][0]['text'])
    assert len(entry.content) == 500  # Re-authoring through this API would lose evidence.


def test_session_start_recent_preserves_raw_content_and_soft_scope(tmp_path, legacy):
    from attune.memory.file_stash import FileStashBackend
    from attune.memory.session_stash import recent_entries
    source = seed_raw(tmp_path/'raw', legacy)
    before = source.read_bytes()
    hits = recent_entries(top_k=20, cwd='project-a', backend=FileStashBackend(base_dir=source.parent))
    assert {h['id']: h['text'] for h in hits} == {r['id']: r['text'] for r in legacy['raw']}
    assert hits[-1]['cwd'] == 'project-b'
    assert all(h['provenance']['tier'] == 'raw' and h['created_at'] for h in hits)
    assert source.read_bytes() == before


def test_legacy_recent_cannot_distinguish_missing_capability_from_empty(tmp_path):
    from attune.memory.file_stash import FileStashBackend
    from attune.memory.session_stash import recent_entries
    assert recent_entries(backend=object()) == []
    assert recent_entries(backend=FileStashBackend(base_dir=tmp_path/'empty')) == []
    # The new adapter must explicitly check capabilities before calling this seam.


@pytest.mark.parametrize('index', range(5))
def test_personal_reads_each_existing_kind_and_preserves_full_source(tmp_path, legacy, index):
    pytest.importorskip('attune_rag')
    sources = seed_documents(tmp_path, legacy)
    entry = legacy['documents'][index]
    memory = reader(tmp_path / entry['root'])
    hits = memory.query(entry['query'], k=20)
    assert entry['path'] in {h['path'] for h in hits}
    hit = next(h for h in hits if h['path'] == entry['path'])
    assert hit['provenance']['tier'] == 'curated'
    source = memory._resolve_hit_path(hit['path'])
    assert source is not None and source.read_bytes() == sources[(entry['root'], entry['path'])]
    assert all((tmp_path / root / path).read_bytes() == body for (root, path), body in sources.items())
    if entry.get('tail'):
        assert len(source.read_text()) > 500 and entry['tail'] in source.read_text()


def test_personal_combined_query_collides_but_single_roots_preserve_identity(tmp_path, legacy):
    pytest.importorskip('attune_rag')
    from attune.memory.personal import PersonalMemory
    seed_documents(tmp_path, legacy)
    combined = PersonalMemory(global_root=tmp_path/'global', project_root=tmp_path/'project')
    hits = combined.query('Aurora reminder', k=20)
    assert sum(h['path'] == 'aurora/decision.md' for h in hits) == 1
    scoped = {}
    for name in ('global', 'project'):
        memory = reader(tmp_path/name)
        hit = next(h for h in memory.query('Aurora reminder', k=20) if h['path'] == 'aurora/decision.md')
        scoped[(name, hit['path'])] = memory._resolve_hit_path(hit['path']).read_text()
    assert '09:15' in scoped[('global', 'aurora/decision.md')]
    assert '10:45' in scoped[('project', 'aurora/decision.md')]


def test_personal_query_emits_actual_local_serve_event(tmp_path, legacy):
    pytest.importorskip('attune_rag')
    seed_documents(tmp_path, legacy)
    hits = reader(tmp_path/'global').query('Aurora reminder', k=20)
    sink = tmp_path/'attune-home'/'telemetry'/'memory_events.jsonl'
    events = [json.loads(line) for line in sink.read_text().splitlines()]
    assert len(events) == 1
    assert events[0]['event'] == 'curated_recall' and events[0]['surface'] == 'personal_query'
    assert events[0]['stems'] == [Path(hit['path']).stem for hit in hits]
    assert 'decision' in events[0]['stems']


def test_curated_legacy_provenance_links_and_unknown_fields_survive(tmp_path, legacy):
    pytest.importorskip('attune_rag')
    from attune.memory.curated_audit import load_memory
    entry = legacy['curated']
    source = tmp_path / 'curated' / entry['path']
    source.parent.mkdir()
    source.write_text(entry['content'], encoding='utf-8')
    before = source.read_bytes()
    parsed = load_memory(source)
    assert parsed.mem_type == 'reference'
    assert 'reference_other' in parsed.links and 'future_rule' in parsed.deferred_links
    hits = reader(source.parent).query('Aurora preservation policy', k=10)
    assert entry['path'] in {h['path'] for h in hits}
    assert source.read_bytes() == before
    assert 'review_response_id: synthetic-review' in source.read_text()


@pytest.mark.parametrize('as_bytes', [False, True])
def test_digest_parser_and_emitter_preserve_derived_node(tmp_path, legacy, as_bytes):
    from attune.memory.recall_digest import fetch_digest_nodes
    node = legacy['digest_node']
    calls = []

    class InjectedClient:
        def fcall(self, *args):
            calls.append(args)
            encoded = json.dumps(node)
            return [encoded.encode('utf-8') if as_bytes else encoded]

    assert fetch_digest_nodes(count=3, client=InjectedClient()) == [node]
    assert calls == [('recall_digest', 0, '3')]
    event = json.loads((tmp_path/'attune-home'/'telemetry'/'memory_events.jsonl').read_text())
    assert event['event'] == 'curated_recall' and event['surface'] == 'recall_digest'
    assert event['stems'] == [node['name']]
    # Real parsing and local emitters; source hydration and Redis are not exercised.


def test_existing_keyed_session_reopens_without_rewriting(tmp_path, legacy):
    from attune.memory.file_session import FileSessionConfig, FileSessionMemory
    entry = legacy['working']
    now = time.time()
    data = dict(session_id='synthetic-session', user_id='synthetic-owner',
                started_at=now, last_updated=now, metadata={'future_field': True},
                working_memory={entry['key']: dict(key=entry['key'], value=entry['value'],
                                                  agent_id='synthetic-owner', stashed_at=now,
                                                  expires_at=None)}, future_field='keep')
    source = tmp_path / 'working' / 'sessions' / 'current.json'
    write_json(source, data)
    before = source.read_bytes()
    for _ in range(2):
        memory = FileSessionMemory('synthetic-owner', FileSessionConfig(base_dir=str(source.parent.parent)))
        assert memory.retrieve(entry['key']) == entry['value']
        assert memory.get_context('missing') is None
    assert source.read_bytes() == before


def test_existing_keyed_stash_reopens_without_rewriting(tmp_path, legacy):
    from attune.memory.file_stash import FileStashBackend
    entry = legacy['working']
    source = tmp_path / 'keyed' / 'kv.json'
    write_json(source, {entry['key']: entry['value']})
    before = source.read_bytes()
    for _ in range(2):
        assert FileStashBackend(base_dir=source.parent).retrieve(entry['key']) == entry['value']
    assert source.read_bytes() == before


def pattern_service(tmp_path):
    from attune.memory.long_term_integration import SecureMemDocsIntegration
    return SecureMemDocsIntegration(storage_dir=str(tmp_path/'patterns'),
                                    audit_log_dir=str(tmp_path/'audit'), enable_encryption=False)


def seed_pattern(tmp_path, legacy):
    record = copy.deepcopy(legacy['pattern'])
    record['metadata']['created_at'] = datetime.now(timezone.utc).isoformat()
    source = tmp_path / 'patterns' / (record['pattern_id'] + '.json')
    write_json(source, record)
    return source, record


def test_persisted_pattern_uses_governed_reader_and_keeps_metadata(tmp_path, legacy):
    source, record = seed_pattern(tmp_path, legacy)
    before = source.read_bytes()
    found = pattern_service(tmp_path).retrieve_pattern(record['pattern_id'], 'synthetic-owner')
    assert found == {'content': record['content'], 'metadata': record['metadata']}
    assert source.read_bytes() == before
    assert list((tmp_path/'audit').rglob('*.jsonl'))  # Audit is distinct from optional usage telemetry.


def test_stamped_foreign_pattern_is_denied_but_unstamped_legacy_is_not(tmp_path, legacy):
    from attune.memory.long_term_types import PermissionError
    source, record = seed_pattern(tmp_path, legacy)
    service = pattern_service(tmp_path)
    assert service.retrieve_pattern(record['pattern_id'], 'different-owner')['content'] == record['content']
    record['metadata']['workspace'] = str(tmp_path/'foreign-project')
    write_json(source, record)
    before = source.read_bytes()
    with pytest.raises(PermissionError):
        service.retrieve_pattern(record['pattern_id'], 'different-owner')
    assert source.read_bytes() == before


def test_uncertain_legacy_upgrade_can_duplicate_into_fallback(tmp_path, monkeypatch):
    from attune.memory import file_stash, session_stash
    original = file_stash.FileStashBackend
    first = original(base_dir=tmp_path/'upgrade')
    fallback = original(base_dir=tmp_path/'fallback')

    class LostAcknowledgment:
        def remember(self, *args, **kwargs):
            assert first.remember(*args, **kwargs)
            return False

    monkeypatch.setattr(file_stash, 'FileStashBackend', lambda: fallback)
    entry = session_stash.SessionStashEntry.create('synthetic', 'project-a', 'note', 'Aurora receipt uncertainty')
    assert session_stash.stash_entry(entry, backend=LostAcknowledgment())
    assert first.search('Aurora')[0]['id'] == fallback.search('Aurora')[0]['id'] == entry.id


def test_sanitizer_refuses_secret_before_backend_write(tmp_path):
    from attune.memory.file_stash import FileStashBackend
    from attune.memory.session_stash import SessionStashEntry, stash_entry
    backend = FileStashBackend(base_dir=tmp_path/'raw')
    fake_key = 'sk-' + 'abc123def456ghi789jkl'  # Synthetic detector canary.
    entry = SessionStashEntry.create('synthetic', 'project-a', 'note', 'api_key=' + fake_key)
    assert stash_entry(entry, backend=backend) is False
    assert not (tmp_path/'raw'/'findings.jsonl').exists()


def test_local_serving_and_feedback_keep_working_without_upload(tmp_path):
    from attune.memory.serve_telemetry import log_curated_recall, serve_counts
    from attune.telemetry.memory_events import log_memory_event
    assert log_curated_recall(['reference_policy'], surface='compatibility-probe')
    log_memory_event('memory_feedback', source='compatibility-probe', count=1)
    sink = tmp_path/'attune-home'/'telemetry'/'memory_events.jsonl'
    events = [json.loads(line) for line in sink.read_text().splitlines()]
    assert [event['event'] for event in events] == ['curated_recall', 'memory_feedback']
    assert serve_counts(events_path=sink) == {'reference_policy': 1}


def test_local_cost_accounting_uses_explicit_instance_without_upload_hook(tmp_path, monkeypatch):
    import atexit
    from attune.telemetry.usage_tracker import UsageTracker
    registrations = []
    monkeypatch.setattr(atexit, 'register', lambda *args, **kwargs: registrations.append(args))
    tracker = UsageTracker(telemetry_dir=tmp_path/'usage')
    tracker.track_llm_call(workflow='synthetic-accounting', stage=None, tier='CHEAP',
                           model='synthetic-no-model-call', provider='synthetic', cost=0.0123,
                           tokens={'input': 100, 'output': 20}, cache_hit=False,
                           cache_type=None, duration_ms=10, user_id='synthetic-owner')
    tracker.flush()
    event = json.loads((tmp_path/'usage'/'usage.jsonl').read_text())
    assert event['tokens'] == {'input': 100, 'output': 20}
    assert event['cost'] == 0.0123
    assert registrations == []  # The singleton path has different shutdown behavior.


@pytest.mark.parametrize('setting', ['ATTUNE_MEMORY_TELEMETRY', 'DO_NOT_TRACK'])
def test_local_telemetry_opt_out_preserves_recall(tmp_path, legacy, monkeypatch, setting):
    pytest.importorskip('attune_rag')
    seed_documents(tmp_path, legacy)
    monkeypatch.setenv(setting, '0' if setting == 'ATTUNE_MEMORY_TELEMETRY' else '1')
    assert reader(tmp_path/'global').query('Aurora reminder')
    assert not (tmp_path/'attune-home'/'telemetry'/'memory_events.jsonl').exists()
