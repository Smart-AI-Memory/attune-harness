# qualify: platform
"""Saved intent persistence, process isolation and failure boundaries."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from attune_harness.memory_saved import SavedStore, SavedError
import attune_harness.memory_saved as saved
from test_review import case  # shared offline participant registry fixture

pytestmark = pytest.mark.skipif(os.name != 'posix', reason='Saved storage initial profile is POSIX')
SCOPE = {'kind': 'global'}


def request(key='one', **extra):
    return dict(request_id=key, kind='memory', scope=SCOPE, title='Context',
                content='Remember the acceptance criteria',
                source={'author': 'user', 'reference': 'explicit request'}, **extra)


def test_process_writers_preserve_all_commits(tmp_path):
    root = tmp_path / 'store'
    code = """import json,sys
sys.path.insert(0, sys.argv.pop(1))
from attune_harness.memory_saved import SavedStore
SavedStore(sys.argv[1]).save(json.loads(sys.argv[2]))
"""
    processes = [subprocess.Popen([sys.executable, '-c', code, str(Path(saved.__file__).resolve().parents[1]), str(root), json.dumps(request(str(i)))]) for i in range(8)]
    assert [p.wait(timeout=20) for p in processes] == [0] * 8
    assert len(SavedStore(root).list(SCOPE)) == 8


def test_failure_before_replace_preserves_record(tmp_path, monkeypatch):
    store = SavedStore(tmp_path / 'store')
    first = store.save(request())['record']
    before = (store.root / 'state.json').read_bytes()
    def fail(*args, **kwargs):
        raise OSError('sensitive arbitrary OS text')
    monkeypatch.setattr(saved.os, 'replace', fail)
    with pytest.raises(SavedError) as exc:
        store.revise(first['id'], {'content': 'changed'}, SCOPE, 'two', 1)
    assert exc.value.outcome == 'not_committed'
    assert 'sensitive' not in str(exc.value)
    assert (store.root / 'state.json').read_bytes() == before


def test_directory_sync_uncertain_then_replay(tmp_path, monkeypatch):
    store = SavedStore(tmp_path / 'store')
    first = store.save(request())['record']
    real = saved.os.fsync
    def fail_directory(fd):
        import stat
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError('injected durability failure')
        return real(fd)
    with monkeypatch.context() as patch:
        patch.setattr(saved.os, 'fsync', fail_directory)
        with pytest.raises(SavedError) as exc:
            store.revise(first['id'], {'content': 'committed'}, SCOPE, 'two', 1)
        assert exc.value.outcome == 'uncertain'
    result = store.revise(first['id'], {'content': 'committed'}, SCOPE, 'two', 1)
    assert result['record']['revision'] == 2


def test_index_restart_and_old_replay_never_resurrect(tmp_path):
    class Index:
        fail = True
        records = {}
        def upsert(self, record):
            if self.fail:
                raise OSError('redis://private-secret')
            self.records[record['id']] = copy.deepcopy(record)
        def remove(self, identity, scope):
            if self.fail:
                raise OSError('private-secret')
            self.records.pop(identity, None)
    index = Index()
    root = tmp_path / 'store'
    store = SavedStore(root, index)
    first = store.save(request())
    assert first['index_status'] == 'pending'
    assert SavedStore(root).get(first['record']['id'], SCOPE)['index_status'] == 'pending'
    index.fail = False
    assert SavedStore(root, index).reindex(SCOPE)['index_status'] == 'indexed'
    store.forget(first['record']['id'], SCOPE, 'forget', 1)
    assert not index.records
    assert store.save(request())['record'] == first['record']
    assert not index.records
    assert not store.list(SCOPE)


@pytest.mark.parametrize('target', ['state.json', '.saved.lock'])
@pytest.mark.parametrize('link', ['symbolic', 'hard'])
def test_store_file_links_refused(tmp_path, target, link):
    root = tmp_path / 'store'
    root.mkdir()
    outside = tmp_path / 'outside'
    outside.write_text('{}')
    if link == 'symbolic':
        (root / target).symlink_to(outside)
    else:
        os.link(outside, root / target)
    with pytest.raises(SavedError):
        SavedStore(root).save(request())
    assert outside.read_text() == '{}'


@pytest.mark.parametrize('damage', ['version', 'history', 'operation', 'extra', 'duplicate'])
def test_corrupt_state_refused(tmp_path, damage):
    store = SavedStore(tmp_path / 'store')
    first = store.save(request())['record']
    path = store.root / 'state.json'
    state = json.loads(path.read_text())
    if damage == 'version':
        state['schema_version'] = 2
    elif damage == 'history':
        state['records'][first['id']]['history'][0]['record']['content'] = 'tampered'
    elif damage == 'operation':
        state['operations']['one']['record']['content'] = 'tampered'
    elif damage == 'extra':
        state['records'][first['id']]['authority'] = 'admin'
    if damage == 'duplicate':
        path.write_text('{"schema_version":1,"schema_version":1}')
    else:
        path.write_text(json.dumps(state))
    with pytest.raises(SavedError):
        store.list(SCOPE)


def test_owner_observation_is_read_only_and_not_persisted(tmp_path, monkeypatch):
    import attune_harness.task_contract as tasks
    project = str(tmp_path.resolve())
    scope = {'kind': 'project', 'project': project}
    identity = '00000000-0000-0000-0000-000000000001'
    req = request(next_action='Inspect owner', execution={'directory': str(tmp_path / 'execution'), 'task_id': identity})
    req.update(kind='task', scope=scope)
    store = SavedStore(tmp_path / 'store')
    record = store.save(req)['record']
    monkeypatch.setattr(tasks, 'read_task', lambda path: {'request': {'task_id': identity, 'project_root': project}, 'status': 'completed'})
    before = (store.root / 'state.json').read_bytes()
    assert store.get(record['id'], scope)['execution_status'] == 'completed'
    assert 'execution_status' not in record
    assert (store.root / 'state.json').read_bytes() == before
    with pytest.raises(SavedError):
        store.complete(record['id'], scope, 'complete', 1)
    monkeypatch.setattr(tasks, 'read_task', lambda path: {'request': {'task_id': identity, 'project_root': '/different'}, 'status': 'completed'})
    assert store.get(record['id'], scope)['execution_status'] == 'unavailable'


def test_oversize_does_not_create_root(tmp_path):
    store = SavedStore(tmp_path / 'store')
    req = request()
    req['content'] = 'x' * 65537
    with pytest.raises(SavedError):
        store.save(req)
    assert not store.root.exists()


def test_root_symlink_refused(tmp_path):
    (tmp_path / 'outside').mkdir()
    (tmp_path / 'link').symlink_to(tmp_path / 'outside', target_is_directory=True)
    with pytest.raises(SavedError):
        SavedStore(tmp_path / 'link')


def test_actual_harness_owner_identity_and_project(tmp_path, case):
    from attune_harness.task_contract import create_task
    owner = create_task(case[0].parent, case[1], goal='Retain intent', directory=case[2])
    scope = {'kind': 'project', 'project': owner['request']['project_root']}
    req = request(next_action='Inspect owner', execution={
        'directory': str(case[2]), 'task_id': owner['request']['task_id']})
    req.update(kind='task', scope=scope)
    store = SavedStore(tmp_path / 'saved')
    before = (case[2] / 'record.json').read_bytes()
    record = store.save(req)['record']
    assert store.get(record['id'], scope)['execution_status'] == 'draft'
    assert (case[2] / 'record.json').read_bytes() == before
    req['request_id'] = 'mismatch'
    req['execution']['task_id'] = '00000000-0000-0000-0000-000000000001'
    other = store.save(req)['record']
    assert store.get(other['id'], scope)['execution_status'] == 'unavailable'
    (case[2] / 'record.json').write_text('{}')
    assert store.get(record['id'], scope)['execution_status'] == 'unavailable'


def test_contending_process_is_bounded_without_write(tmp_path, monkeypatch):
    store = SavedStore(tmp_path / 'store')
    store.save(request())
    before = (store.root / 'state.json').read_bytes()
    code = """import sys
sys.path.insert(0,sys.argv.pop(1))
from attune_harness.memory_saved import SavedStore
with SavedStore(sys.argv[1])._locked():
    print('locked', flush=True)
    sys.stdin.readline()
"""
    proc = subprocess.Popen([sys.executable, '-c', code, str(Path(saved.__file__).resolve().parents[1]), str(store.root)],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert proc.stdout.readline().strip() == 'locked'
        monkeypatch.setattr(saved, 'LOCK_SECONDS', .03)
        with pytest.raises(SavedError) as exc:
            store.save(request('second'))
        assert exc.value.code == 'busy'
        assert (store.root / 'state.json').read_bytes() == before
    finally:
        proc.communicate('\n', timeout=10)
    assert proc.returncode == 0


def test_index_metadata_failure_does_not_claim_no_commit(tmp_path, monkeypatch):
    class Index:
        def upsert(self, record):
            pass
    store = SavedStore(tmp_path / 'store', Index())
    original = store._write
    calls = 0
    def fail_second(directory, state):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise SavedError('index metadata disk failure')
        return original(directory, state)
    monkeypatch.setattr(store, '_write', fail_second)
    with pytest.raises(SavedError) as exc:
        store.save(request())
    assert exc.value.outcome == 'uncertain'
    assert len(SavedStore(store.root).list(SCOPE)) == 1
    assert SavedStore(store.root).list(SCOPE)[0]['index_status'] == 'pending'


def test_boolean_history_revision_is_not_an_integer_revision(tmp_path):
    store = SavedStore(tmp_path / 'store')
    record = store.save(request())['record']
    path = store.root / 'state.json'
    state = json.loads(path.read_text())
    state['records'][record['id']]['history'][0]['record']['revision'] = True
    path.write_text(json.dumps(state))
    with pytest.raises(SavedError) as exc:
        store.get(record['id'], SCOPE)
    assert exc.value.code == 'corrupt'


def test_completed_task_cannot_acquire_an_execution_owner(tmp_path):
    store = SavedStore(tmp_path / 'store')
    scope = {'kind': 'project', 'project': str(tmp_path.resolve())}
    req = request(next_action='Inspect owner')
    req.update(kind='task', scope=scope)
    record = store.save(req)['record']
    store.complete(record['id'], scope, 'complete', 1)
    before = (store.root / 'state.json').read_bytes()
    with pytest.raises(SavedError):
        store.revise(record['id'], {'execution': {
            'directory': str(tmp_path / 'owner'),
            'task_id': '00000000-0000-0000-0000-000000000001',
        }}, scope, 'attach', 2)
    assert (store.root / 'state.json').read_bytes() == before


def test_lock_open_uses_exclusive_creation_then_existing_inode(tmp_path, monkeypatch):
    store = SavedStore(tmp_path / 'store')
    store.save(request())
    inode = (store.root / '.saved.lock').stat().st_ino
    actual = saved.os.open
    calls = []
    def checked(path, flags, *args, **kwargs):
        if path == '.saved.lock':
            calls.append(flags)
            assert not flags & os.O_CREAT or flags & os.O_EXCL
        return actual(path, flags, *args, **kwargs)
    monkeypatch.setattr(saved.os, 'open', checked)
    store.save(request('second'))
    assert len(calls) == 2
    assert calls[0] & os.O_EXCL
    assert not calls[1] & os.O_CREAT
    assert (store.root / '.saved.lock').stat().st_ino == inode
