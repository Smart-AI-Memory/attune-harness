"""Proposed real Windows saved-store journeys; unexecuted in this packet."""
# qualify: platform
import ctypes
from contextlib import contextmanager
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading

import pytest

from attune_harness.memory_saved import MAX_STATE, SavedError, SavedStore
from test_review import case  # existing offline registry fixture; no participant execution

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Real local NTFS saved-store operations')


@pytest.fixture
def canonical_tmp(tmp_path):
    # Resolve the trusted test producer's OS temp alias, never a SavedStore input.
    return tmp_path.resolve(strict=True)


def request(request_id='first', *, kind='memory'):
    value = {'request_id': request_id, 'kind': kind, 'scope': {'kind': 'global'},
             'title': 'Résumé 雪', 'content': 'Explicit retained content',
             'source': {'author': 'caller', 'reference': 'explicit test request'}}
    if kind == 'task':
        value['next_action'] = 'Review saved intent'
    return value


def test_native_memory_task_lifecycle_utf8_and_spaces(canonical_tmp):
    root = canonical_tmp / 'Private space 雪 🧭'
    store = SavedStore(root)
    memory = store.save(request())
    identifier = memory['record']['id']
    assert store.save(request()) == memory
    assert store.get(identifier, {'kind': 'global'})['title'] == 'Résumé 雪'
    assert len(store.list({'kind': 'global'})) == 1
    revised = store.revise(identifier, {'content': 'Revised 雪'}, {'kind': 'global'}, 'revision', 1)
    assert revised['record']['revision'] == 2
    assert store.save(request())['record']['revision'] == 1
    forgotten = store.forget(identifier, {'kind': 'global'}, 'withdrawal', 2)
    assert forgotten['record']['status'] == 'withdrawn'
    with pytest.raises(SavedError) as missing:
        store.get(identifier, {'kind': 'global'})
    assert missing.value.code == 'not_found'
    assert len(store.get(identifier, {'kind': 'global'}, include_withdrawn=True)['history']) == 3
    task = store.save(request('task', kind='task'))['record']
    completed = store.complete(task['id'], {'kind': 'global'}, 'complete', 1)
    assert completed['record']['status'] == 'completed'
    assert len(store.search('retained', {'kind': 'global'})) == 1
    assert store.reindex({'kind': 'global'})['index_status'] == 'disabled'
    raw = (root / 'state.json').read_bytes()
    assert 'Résumé 雪'.encode() in raw
    assert json.loads(raw)['schema_version'] == 1


_SAVE = """
import json, sys
from pathlib import Path
from attune_harness.memory_saved import SavedStore
result = SavedStore(Path(sys.argv[1])).save(json.loads(sys.argv[2]))
print(json.dumps(result, ensure_ascii=True, allow_nan=False), flush=True)
"""


def writers(root, requests):
    children = []
    try:
        for value in requests:
            children.append(subprocess.Popen([sys.executable, '-I', '-c', _SAVE, str(root),
                json.dumps(value, ensure_ascii=True)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True))
        results = []
        for child in children:
            stdout, stderr = child.communicate(timeout=30)
            assert child.returncode == 0, stderr
            results.append(json.loads(stdout))
        return results
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=10)


def test_native_cross_process_independent_and_identical_requests(canonical_tmp):
    root = canonical_tmp / 'Concurrent fresh 雪' / 'Private store'
    assert not root.parent.exists()
    independent = writers(root, [request('independent-' + str(i)) for i in range(8)])
    assert len({row['record']['id'] for row in independent}) == 8
    identical = writers(root, [request('identical')] * 8)
    assert all(row == identical[0] for row in identical)
    store = SavedStore(root)
    assert len(store.list({'kind': 'global'})) == 9
    state = json.loads((root / 'state.json').read_bytes())
    assert len(state['operations']) == 9
    assert all(record['revision'] == 1 and len(record['history']) == 1
               for record in state['records'].values())


def test_native_process_death_releases_persistent_lock(canonical_tmp):
    from attune_harness.memory_saved_windows import locked
    root = canonical_tmp / 'Crash lock 雪'
    script = """
import sys, time
from pathlib import Path
from attune_harness.memory_saved_windows import locked
with locked(Path(sys.argv[1])):
    print('lock-acquired', flush=True)
    time.sleep(30)
"""
    child = subprocess.Popen([sys.executable, '-I', '-c', script, str(root)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    messages = queue.Queue()
    threading.Thread(target=lambda: messages.put(child.stdout.readline()), daemon=True).start()
    try:
        assert messages.get(timeout=15).strip() == 'lock-acquired'
        inode = os.stat(root / '.saved.lock').st_ino
        child.kill()
        child.wait(timeout=10)
        with locked(root):
            assert os.stat(root / '.saved.lock').st_ino == inode
        assert SavedStore(root).save(request())['record']['revision'] == 1
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=10)
    # This checks crash release, not power-loss durability or an ACKed write.


def test_native_persistent_lock_denies_delete_sharing(canonical_tmp):
    from attune_harness.memory_saved_windows import locked
    root = canonical_tmp / 'Delete sharing'
    with locked(root):
        before = os.stat(root / '.saved.lock').st_ino
        with pytest.raises(PermissionError) as denied:
            os.rename(root / '.saved.lock', root / 'replacement.lock')
        assert denied.value.winerror == 32
        assert os.stat(root / '.saved.lock').st_ino == before


def test_native_lost_ack_replay_adds_no_state_commit_barrier(canonical_tmp, monkeypatch,
                                                           record_property):
    from attune_harness import memory_saved_windows as backend
    store = SavedStore(canonical_tmp / 'Lost ACK')
    original = backend._Session.commit_payload
    original_flush = backend._Native.flush
    original_child = backend._Native.child
    committed_directory = {}
    enclosing_parents = []
    def child(native, parent, name, **kwargs):
        handle = original_child(native, parent, name, **kwargs)
        try:
            if name == store.root.name and kwargs.get('directory'):
                identity = native.api.metadata(parent)[0]['identity']
                if identity not in enclosing_parents:
                    enclosing_parents.append(identity)
        except BaseException as primary:
            try:
                native.close(handle)
            except BaseException as secondary:
                raise primary from secondary
            raise
        return handle
    monkeypatch.setattr(backend._Native, 'child', child)
    def commit_then_lose_ack(lease, payload):
        original(lease, payload)
        committed_directory.update(lease.native.api.metadata(lease.directory)[0]['identity'])
        raise SavedError('controlled acknowledgement loss', code='persistence', outcome='uncertain')
    monkeypatch.setattr(backend._Session, 'commit_payload', commit_then_lose_ack)
    with pytest.raises(SavedError) as uncertain:
        store.save(request())
    assert uncertain.value.outcome == 'uncertain'
    monkeypatch.setattr(backend._Session, 'commit_payload', original)
    identifier = store.list({'kind': 'global'})[0]['id']
    class Index:
        def upsert(self, record): pass
    store.index = Index()
    store.revise(identifier, {'content': 'Later revision'}, {'kind': 'global'}, 'later', 1)
    store.index = None
    before = (store.root / 'state.json').read_bytes()
    attempted_commit, admission = [], []
    def state_commit_barrier_still_refuses(native, handle):
        entry, _, _ = native.api.metadata(handle)
        if entry['kind'] == 'file' or entry['identity'] == committed_directory:
            attempted_commit.append(entry['identity'])
            return 0, 1
        assert entry['kind'] == 'directory' and entry['identity'] in enclosing_parents
        status = original_flush(native, handle)
        admission.append({'identity': entry['identity'], 'flags': 0,
                          'returned_ntstatus': status[0], 'io_status': status[1]})
        return status
    monkeypatch.setattr(backend._Native, 'flush', state_commit_barrier_still_refuses)
    def no_write(native, handle, payload):
        attempted_commit.append('write')
        raise OSError('replay cannot write state')
    def no_rename(api, source, parent, target):
        attempted_commit.append('rename')
        raise OSError('replay cannot rename state')
    monkeypatch.setattr(backend._Native, 'write_all', no_write)
    monkeypatch.setattr(backend.Native, 'rename', no_rename)
    try:
        replay = store.save(request())
    finally:
        record_property('saved_replay_admission_only', json.dumps({
            'commit_barriers_attempted': attempted_commit, 'enclosing_parent_admission': admission,
            'prior_commit_barrier_reestablished': False}, ensure_ascii=True, allow_nan=False))
    assert replay['record']['revision'] == 1
    assert len(replay['record']['history']) == 1
    assert replay['index_status'] == 'indexed'
    assert store.get(identifier, {'kind': 'global'})['revision'] == 2
    assert (store.root / 'state.json').read_bytes() == before
    assert attempted_commit == []
    assert admission and all(row['returned_ntstatus'] == row['io_status'] == 0 for row in admission)
    def admission_still_refuses(native, handle):
        entry, _, _ = native.api.metadata(handle)
        assert entry['kind'] == 'directory' and entry['identity'] in enclosing_parents
        return 0, 1
    monkeypatch.setattr(backend._Native, 'flush', admission_still_refuses)
    with pytest.raises(SavedError) as refused_admission:
        store.save(request())
    assert refused_admission.value.code == 'storage'
    assert refused_admission.value.outcome == 'not_committed'
    assert (store.root / 'state.json').read_bytes() == before
    assert attempted_commit == []


def test_native_inherited_nonprivate_root_refused_before_lock(canonical_tmp):
    root = canonical_tmp / 'Inherited root'
    root.mkdir()
    with pytest.raises(SavedError):
        SavedStore(root).list({'kind': 'global'})
    assert not (root / '.saved.lock').exists()
    assert not (root / 'state.json').exists()


def test_native_hardlinked_state_refused(canonical_tmp):
    root = canonical_tmp / 'Hardlink refusal'
    store = SavedStore(root)
    store.save(request())
    original = (root / 'state.json').read_bytes()
    os.link(root / 'state.json', canonical_tmp / 'external-state-alias')
    with pytest.raises(SavedError):
        store.list({'kind': 'global'})
    assert (root / 'state.json').read_bytes() == original


def test_native_alternate_stream_refused(canonical_tmp):
    root = canonical_tmp / 'ADS refusal'
    store = SavedStore(root)
    store.save(request())
    before = (root / 'state.json').read_bytes()
    Path(str(root / 'state.json') + ':extra').write_bytes(b'extra stream')
    with pytest.raises(SavedError):
        store.list({'kind': 'global'})
    assert (root / 'state.json').read_bytes() == before


def test_native_directory_link_refused_without_following(canonical_tmp):
    target = canonical_tmp / 'target'
    target.mkdir()
    link = canonical_tmp / 'link'
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError as exc:
        if os.name == 'nt' and exc.winerror == 1314:
            pytest.skip('current Windows token cannot create a symlink (WinError1314)')
        raise
    with pytest.raises(SavedError):
        SavedStore(link / 'store').list({'kind': 'global'})
    assert not (target / 'store').exists()


def test_native_oversize_and_corrupt_state_refuse_without_replacement(canonical_tmp):
    root = canonical_tmp / 'Corruption refusal'
    store = SavedStore(root)
    store.save(request())
    state = root / 'state.json'
    with state.open('r+b') as stream:
        stream.truncate(MAX_STATE + 1)
    with pytest.raises(SavedError):
        store.list({'kind': 'global'})
    state.write_bytes(b'not JSON')
    with pytest.raises(SavedError) as corrupt:
        store.save(request('different'))
    assert corrupt.value.code == 'corrupt'
    assert state.read_bytes() == b'not JSON'


def test_native_index_restart_and_old_replay_cannot_resurrect(canonical_tmp):
    class Index:
        def __init__(self):
            self.fail, self.records = True, {}
        def upsert(self, record):
            if self.fail:
                raise RuntimeError('index unavailable')
            self.records[record['id']] = record
        def remove(self, identity, scope):
            self.records.pop(identity, None)
    index = Index()
    root = canonical_tmp / 'Index boundary'
    first = SavedStore(root, index).save(request())
    assert first['index_status'] == 'pending'
    assert SavedStore(root).get(first['record']['id'], {'kind': 'global'})['index_status'] == 'pending'
    index.fail = False
    store = SavedStore(root, index)
    assert store.reindex({'kind': 'global'})['index_status'] == 'indexed'
    store.forget(first['record']['id'], {'kind': 'global'}, 'forget', 1)
    assert not index.records
    replay = store.save(request())
    assert replay['record']['revision'] == 1 and replay['index_status'] == 'indexed'
    assert not index.records
    assert store.list({'kind': 'global'}) == []


def test_native_saved_task_observes_real_owner_without_writing_it(canonical_tmp, case):
    from attune_harness.task_contract import create_task
    owner = create_task(case[0].parent, case[1], goal='Retain saved task intent', directory=case[2])
    scope = {'kind': 'project', 'project': owner['request']['project_root']}
    value = request('linked-task', kind='task')
    value.update(scope=scope, execution={'directory': str(case[2]),
                                       'task_id': owner['request']['task_id']})
    store = SavedStore(canonical_tmp / 'Linked saved intent')
    before = (case[2] / 'record.json').read_bytes()
    saved = store.save(value)['record']
    assert store.get(saved['id'], scope)['execution_status'] == 'draft'
    assert 'execution_status' not in saved
    assert (case[2] / 'record.json').read_bytes() == before
    with pytest.raises(SavedError):
        store.complete(saved['id'], scope, 'complete-linked', 1)


def parent_handle_facts(native, handle):
    """Test-only query of the actual production handle; no extra handle is opened."""
    w = native.w
    class BasicInformation(ctypes.Structure):
        _fields_ = [('Attributes', w.ULONG), ('GrantedAccess', w.ULONG),
                    ('HandleCount', w.ULONG), ('PointerCount', w.ULONG),
                    ('Reserved', w.ULONG * 10)]
    query = native.api.nt.NtQueryObject
    query.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.ULONG,
                      ctypes.POINTER(w.ULONG)]
    query.restype = ctypes.c_long
    value, returned = BasicInformation(), w.ULONG()
    value.GrantedAccess = 0xDEADBEEF
    status = query(handle, 0, ctypes.byref(value), ctypes.sizeof(value),
                   ctypes.byref(returned)) & 0xffffffff
    assert status == 0 and returned.value == ctypes.sizeof(value)
    # FILE_WRITE_DATA, READ_CONTROL, SYNCHRONIZE and read/list/attribute access.
    required = 0x00120083
    assert value.GrantedAccess & required == required
    entry, _, _ = native.api.metadata(handle)
    assert entry['kind'] == 'directory'
    return {'query_ntstatus': status, 'query_bytes': returned.value,
            'granted_access': value.GrantedAccess, 'required_access': required,
            'identity': entry['identity'], 'security_sha256': entry['security_sha256']}


def test_native_managed_parent_publication_rights_status_identity(canonical_tmp, monkeypatch,
                                                                  record_property):
    from attune_harness import memory_saved_windows as backend
    names = ('Fresh managed suffix', 'Private saved store')
    root = canonical_tmp / names[0] / names[1]
    assert not root.parent.exists()
    phase, links, flushes = [0], {}, []
    original_child, original_flush = backend._Native.child, backend._Native.flush

    def child(native, parent, name, **kwargs):
        handle = original_child(native, parent, name, **kwargs)
        try:
            if name in names and kwargs.get('directory'):
                parent_entry, _, _ = native.api.metadata(parent)
                entry, _, _ = native.api.metadata(handle)
                links[phase[0], name] = {'name': name, 'parent_identity': parent_entry['identity'],
                    'child_identity': entry['identity'], 'child_private': native.is_private(handle),
                    'handle': handle}
        except BaseException as primary:
            try:
                native.close(handle)
            except BaseException as secondary:
                raise primary from secondary
            raise
        return handle

    def flush(native, handle):
        entry, _, _ = native.api.metadata(handle)
        if entry['kind'] != 'directory':
            return original_flush(native, handle)
        row = {'phase': phase[0], 'before': parent_handle_facts(native, handle),
               'flags': 0, 'returned_ntstatus': None, 'io_status': None,
               'after': None, 'children_after': []}
        flushes.append(row)  # Preserve the first partial row if a later check fails.
        status = original_flush(native, handle)
        row['returned_ntstatus'], row['io_status'] = status
        after, _, _ = native.api.metadata(handle)
        row['after'] = {'identity': after['identity'], 'security_sha256': after['security_sha256']}
        for (round_number, _), link in links.items():
            if round_number == phase[0] and link['parent_identity'] == entry['identity']:
                selected, _, _ = native.api.metadata(link['handle'])
                row['children_after'].append({'name': link['name'], 'identity': selected['identity'],
                                              'private': native.is_private(link['handle'])})
        return status

    monkeypatch.setattr(backend._Native, 'child', child)
    monkeypatch.setattr(backend._Native, 'flush', flush)
    try:
        for round_number in (1, 2):
            phase[0] = round_number
            with backend.locked(root):
                pass
            selected_links = [links[round_number, name] for name in names]
            required_parents = [link['parent_identity'] for link in selected_links]
            relevant = [row for row in flushes if row['phase'] == round_number
                        and row['before']['identity'] in required_parents]
            assert [row['before']['identity'] for row in relevant] == required_parents
            for link, row in zip(selected_links, relevant):
                assert link['child_private']
                assert type(row['returned_ntstatus']) is int and row['returned_ntstatus'] == 0
                assert type(row['io_status']) is int and row['io_status'] == 0
                assert row['before']['identity'] == row['after']['identity']
                assert row['before']['security_sha256'] == row['after']['security_sha256']
                assert row['children_after'] == [{'name': link['name'],
                    'identity': link['child_identity'], 'private': True}]
    finally:
        # Opaque object identities/rights/statuses only; no SID, path or environment values.
        public_links = [{'phase': key[0], **{k: v for k, v in link.items() if k != 'handle'}}
                        for key, link in links.items()]
        record_property('saved_managed_parent_publication', json.dumps({
            'external_prefix': 'canonical fixture prefix is an explicit provisioning premise',
            'links': public_links, 'flushes': flushes}, ensure_ascii=True, allow_nan=False))


_REVISE = """
import json, sys
from attune_harness.memory_saved import SavedStore, SavedError
print(json.dumps({'ready': True}), flush=True)
assert sys.stdin.readline() == 'go\\n'
value = json.loads(sys.argv[2])
try:
    result = SavedStore(sys.argv[1]).revise(value['id'], value['changes'], value['scope'],
                                           value['request_id'], value['expected_revision'])
except SavedError as error:
    if error.code != 'conflict':
        raise
    result = {'outcome': 'conflict'}
else:
    result = {'outcome': 'committed', 'result': result}
print(json.dumps(result, ensure_ascii=True), flush=True)
"""


def next_child_line(child, timeout=30):
    result = queue.Queue()
    threading.Thread(target=lambda: result.put(child.stdout.readline()), daemon=True).start()
    return result.get(timeout=timeout)


def test_native_competing_expected_revision_has_one_winner(canonical_tmp, record_property):
    root = canonical_tmp / 'Revision contenders'
    store = SavedStore(root)
    first = store.save(request())['record']
    children, outcomes, exits = [], [], []
    try:
        for label in ('A', 'B'):
            value = {'id': first['id'], 'scope': {'kind': 'global'},
                     'changes': {'content': label}, 'request_id': 'contender-' + label,
                     'expected_revision': 1}
            child = subprocess.Popen([sys.executable, '-I', '-c', _REVISE, str(root),
                json.dumps(value, ensure_ascii=True)], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            children.append(child)
        for child in children:
            assert json.loads(next_child_line(child)) == {'ready': True}
        for child in children:
            child.stdin.write('go\n')
            child.stdin.flush()
        for child in children:
            stdout, stderr = child.communicate(timeout=30)
            exits.append(child.returncode)
            assert child.returncode == 0, stderr
            outcomes.append(json.loads(stdout))
        assert sorted(row['outcome'] for row in outcomes) == ['committed', 'conflict']
        winner = next(row['result']['record'] for row in outcomes if row['outcome'] == 'committed')
        observed = store.get(first['id'], {'kind': 'global'})
        assert observed['revision'] == winner['revision'] == 2
        assert observed['content'] == winner['content']
        assert len(observed['history']) == 2
        state = json.loads((root / 'state.json').read_bytes())
        assert len(state['operations']) == 2
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=10)
        record_property('saved_expected_revision_competition', json.dumps({
            'exits': exits, 'outcomes': [row.get('outcome') for row in outcomes]}, ensure_ascii=True))


_KILL_REVISION = """
import json, sys
from attune_harness import memory_saved_windows as backend
from attune_harness.memory_saved import SavedStore
root, stage, value = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
prepared_identity = []
original_child = backend._Native.child
original_flush = backend._Native.flush
original_rename = backend.Native.rename
def checkpoint(facts):
    print(json.dumps({'checkpoint': stage, **facts}, ensure_ascii=True), flush=True)
    sys.stdin.readline()  # Parent terminates this process; no descendants are created.
    raise RuntimeError('the kill checkpoint must not be resumed')
def child(native, parent, name, **kwargs):
    handle = original_child(native, parent, name, **kwargs)
    if kwargs.get('create') and name.startswith('.saved-'):
        entry = native.api.metadata(handle)[0]
        prepared_identity.append(entry['identity'])
        if stage == 'preparation':
            checkpoint({'prepared_identity': entry['identity'], 'private': native.is_private(handle)})
    return handle
def flush(native, handle):
    result = original_flush(native, handle)
    entry = native.api.metadata(handle)[0]
    if stage == 'file_flush' and entry['identity'] in prepared_identity:
        assert type(result[0]) is int and result[0] == 0
        assert type(result[1]) is int and result[1] == 0
        checkpoint({'identity': entry['identity'], 'flags': 0,
                    'returned_ntstatus': result[0], 'io_status': result[1]})
    return result
def rename(api, source, parent, target):
    result = original_rename(api, source, parent, target)
    if stage == 'rename':
        assert result == {'returned_ntstatus': 0, 'io_status_block_status': 0}
        checkpoint({'rename': result, 'identity': api.metadata(source)[0]['identity']})
    return result
backend._Native.child = child
backend._Native.flush = flush
backend.Native.rename = rename
result = SavedStore(root).revise(value['id'], value['changes'], value['scope'],
                                value['request_id'], value['expected_revision'])
if stage == 'pre_response':
    checkpoint({'revision': result['record']['revision'], 'history': len(result['record']['history'])})
print(json.dumps(result, ensure_ascii=True), flush=True)
"""


def expected_revision_bytes(before, value):
    """Use the unchanged common owner to produce the atomic byte after-image."""
    class Bytes:
        raw = before
        def read_payload(self): return self.raw
        def commit_payload(self, payload): self.raw = payload
    memory = Bytes()
    owner = object.__new__(SavedStore)
    owner.index = None
    @contextmanager
    def held(): yield memory
    owner._locked = held
    owner.revise(value['id'], value['changes'], value['scope'],
                 value['request_id'], value['expected_revision'])
    return memory.raw


@pytest.mark.parametrize('stage', ['preparation', 'file_flush', 'rename', 'pre_response'])
def test_native_kill_boundary_whole_state_and_same_id_recovery(canonical_tmp, stage, record_property):
    root = canonical_tmp / ('Kill ' + stage)
    store = SavedStore(root)
    first = store.save(request())['record']
    before = (root / 'state.json').read_bytes()
    value = {'id': first['id'], 'scope': {'kind': 'global'},
             'changes': {'content': 'Recovered revision 雪'}, 'request_id': 'kill-' + stage,
             'expected_revision': 1}
    after = expected_revision_bytes(before, value)
    child = subprocess.Popen([sys.executable, '-I', '-c', _KILL_REVISION, str(root), stage,
        json.dumps(value, ensure_ascii=True)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True)
    checkpoint, exit_code = None, None
    try:
        checkpoint = json.loads(next_child_line(child))
        assert checkpoint['checkpoint'] == stage
        child.kill()
        child.wait(timeout=10)
        exit_code = child.returncode
        assert exit_code != 0
        observed = (root / 'state.json').read_bytes()
        expected = before if stage in ('preparation', 'file_flush') else after
        assert observed == expected
        # The real common decoder must accept the whole persisted state.
        visible = store.get(first['id'], {'kind': 'global'})
        assert visible['revision'] == (1 if expected == before else 2)
        recovered = store.revise(value['id'], value['changes'], value['scope'],
                                 value['request_id'], value['expected_revision'])
        assert recovered['record']['revision'] == 2
        assert len(recovered['record']['history']) == 2
        replay = store.revise(value['id'], value['changes'], value['scope'],
                              value['request_id'], value['expected_revision'])
        assert replay == recovered
        assert (root / 'state.json').read_bytes() == after
        assert sum(row['request_id'] == value['request_id']
                   for row in replay['record']['history']) == 1
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=10)
        stdout, stderr = child.communicate(timeout=10)
        record_property('saved_native_kill_boundary', json.dumps({
            'stage': stage, 'checkpoint': checkpoint, 'exit_code': exit_code,
            'remaining_stdout': stdout, 'stderr': stderr,
            'claim': 'process termination only; no power-loss or new replay durability claim'},
            ensure_ascii=True, allow_nan=False))


def test_native_saved_task_opportunity_review_lifecycle(canonical_tmp):
    store = SavedStore(canonical_tmp / 'Review checkpoint task')
    pending = {'status': 'pending', 'goal': 'Preserve the task', 'progress': 'Intent saved',
               'evidence': ['explicit caller reference'], 'reason': 'Review remains',
               'next_action': 'Review the retained checkpoint'}
    value = request('review-save', kind='task')
    value['opportunity_review'] = pending
    first = store.save(value)['record']
    assert store.get(first['id'], {'kind': 'global'})['opportunity_review'] == pending
    completed = {'status': 'completed', 'goal': 'Preserve the task', 'progress': 'Reviewed',
                 'evidence': ['explicit caller reference'],
                 'outcome': {'kind': 'no_change', 'summary': 'No new opportunity'}}
    revised = store.revise(first['id'], {'opportunity_review': completed},
                           {'kind': 'global'}, 'review-complete', 1)['record']
    assert revised['revision'] == 2 and revised['opportunity_review'] == completed
    assert value['opportunity_review'] == pending
    assert 'completed' in store.get(first['id'], {'kind': 'global'})['opportunity_review_notice']
    store.forget(first['id'], {'kind': 'global'}, 'review-withdraw', 2)
    withdrawn = store.get(first['id'], {'kind': 'global'}, include_withdrawn=True)
    assert withdrawn['revision'] == 3 and withdrawn['opportunity_review'] == completed
    assert 'withdrawn' in withdrawn['opportunity_review_notice']
    assert len(withdrawn['history']) == 3
