"""Proposed inert storage fault controls; no native constructor is invoked."""
from contextlib import contextmanager
import copy
import ctypes
import json
from types import SimpleNamespace

import pytest

from attune_harness.memory_saved import SavedError, SavedStore
from attune_harness import memory_saved_windows as backend


class FakeAPI:
    def __init__(self, owner):
        self.owner = owner

    def metadata(self, handle):
        item = self.owner.objects[handle]
        if item.get('reparse'):
            raise ValueError('reparse refused')
        entry = {'kind': item['kind'], 'links': item.get('links', 1),
                 'identity': {'file_id': handle}, 'private': item.get('private', True)}
        return entry, len(item.get('raw', b'')), False

    def iter_names(self, directory):
        assert directory == 1
        return iter(tuple(self.owner.names))

    def read(self, handle, size, *, limit):
        assert size <= limit
        raw = self.owner.objects[handle]['raw']
        return b'changed' if self.owner.read_mismatch else raw

    def rename(self, prepared, parent, target):
        assert parent == 1 and target == 'state.json'
        self.owner.events.append(('rename', prepared))
        if self.owner.rename_before_error:
            raise OSError('dispatch has no returned result')
        self.owner.names[target] = prepared
        if self.owner.rename_after_error:
            raise OSError('dispatch completed then wrapper raised')
        return copy.deepcopy(self.owner.rename_result)


class FakeNative:
    def __init__(self):
        self.api = FakeAPI(self)
        self.objects = {1: {'kind': 'directory'}, 2: {'kind': 'file', 'raw': b'old'}}
        self.names = {'state.json': 2}
        self.events = []
        self.next_handle = 3
        self.statuses = {}
        self.flushes = 0
        self.short_write = False
        self.read_mismatch = False
        self.rename_before_error = self.rename_after_error = False
        self.rename_result = {'returned_ntstatus': 0, 'io_status_block_status': 0}
        self.close_error = None

    def private(self, handle):
        if not self.objects[handle].get('private', True):
            raise OSError('private owner or ACL refused')

    def child(self, parent, name, **kwargs):
        assert parent == 1
        if kwargs.get('create'):
            assert name not in self.names
            handle = self.next_handle
            self.next_handle += 1
            self.objects[handle] = {'kind': 'file', 'raw': b''}
            self.names[name] = handle
            self.events.append(('create', handle))
            return handle
        self.events.append(('open', name))
        return self.names[name]

    def write_all(self, handle, payload):
        self.events.append(('write', handle))
        written = payload[:-1] if self.short_write else payload
        self.objects[handle]['raw'] = written
        return len(written)

    def flush(self, handle):
        self.flushes += 1
        self.events.append(('flush', handle))
        return self.statuses.get(self.flushes, (0, 0))

    def remove_prepared(self, handle):
        self.events.append(('remove', handle))
        for name in list(self.names):
            if self.names[name] == handle:
                del self.names[name]

    def close(self, handle):
        self.events.append(('close', handle))
        if self.close_error == handle:
            raise OSError('close refused')


def session():
    native = FakeNative()
    return native, backend._Session(native, 1)


def test_commit_has_complete_ordered_barriers_and_afterimage():
    native, lease = session()
    lease.commit_payload(b'new')
    assert native.events == [('create', 3), ('write', 3), ('flush', 3),
                             ('rename', 3), ('flush', 3), ('flush', 1),
                             ('open', 'state.json'), ('close', 3), ('close', 3)]
    assert native.objects[native.names['state.json']]['raw'] == b'new'
    assert lease.dispatched


@pytest.mark.parametrize('bad', [(1, 0), (0, 1), (0x103, 0), (0, 0x103),
                                (False, 0), (0, False), [0, 0], (0,), None])
def test_bad_prepared_flush_refuses_before_namespace_dispatch(bad):
    native, lease = session()
    native.statuses[1] = bad
    with pytest.raises(SavedError) as error:
        lease.commit_payload(b'new')
    assert error.value.code == 'persistence'
    assert error.value.outcome == 'not_committed'
    assert native.names == {'state.json': 2}
    assert ('rename', 3) not in native.events
    assert ('remove', 3) in native.events


@pytest.mark.parametrize('position', [2, 3])
@pytest.mark.parametrize('bad', [(1, 0), (0, 1), (0x103, 0), (0, 0x103)])
def test_bad_postdispatch_barrier_is_uncertain_and_never_deletes(position, bad):
    native, lease = session()
    native.statuses[position] = bad
    with pytest.raises(SavedError) as error:
        lease.commit_payload(b'new')
    assert error.value.outcome == 'uncertain'
    assert native.names['state.json'] == 3
    assert ('remove', 3) not in native.events


@pytest.mark.parametrize('result', [None, {'returned_ntstatus': 0},
    {'returned_ntstatus': 0, 'io_status_block_status': 0x103},
    {'returned_ntstatus': 0, 'io_status_block_status': False},
    {'returned_ntstatus': 0, 'io_status_block_status': 0, 'extra': 0}])
def test_rename_requires_both_exact_final_statuses(result):
    native, lease = session()
    native.rename_result = result
    with pytest.raises(SavedError) as error:
        lease.commit_payload(b'new')
    assert error.value.outcome == 'uncertain'
    assert ('remove', 3) not in native.events


@pytest.mark.parametrize('failure', ['rename_before_error', 'rename_after_error'])
def test_wrapper_failure_is_uncertain_even_without_a_return(failure):
    native, lease = session()
    setattr(native, failure, True)
    with pytest.raises(SavedError) as error:
        lease.commit_payload(b'new')
    assert error.value.outcome == 'uncertain'
    assert lease.dispatched
    assert ('remove', 3) not in native.events


def test_short_write_cannot_replace_authoritative_state():
    native, lease = session()
    native.short_write = True
    with pytest.raises(SavedError) as error:
        lease.commit_payload(b'new')
    assert error.value.outcome == 'not_committed'
    assert native.names == {'state.json': 2}
    assert native.flushes == 0


@pytest.mark.parametrize('change', [{'links': 2}, {'reparse': True},
                                   {'private': False}, {'kind': 'directory'}])
def test_read_refuses_unsupported_state_object(change):
    native, lease = session()
    native.objects[2].update(change)
    with pytest.raises(SavedError):
        lease.read_payload()
    assert not lease.dispatched


@pytest.mark.parametrize('names', [{'STATE.JSON': 2}, {'STATE.JSON': 2, 'state.json': 2}])
def test_case_alias_does_not_become_an_empty_or_ambiguous_store(names):
    native, lease = session()
    native.names = names
    with pytest.raises(SavedError):
        lease.read_payload()
    assert native.events == []


def test_afterimage_and_close_failures_cannot_ack(monkeypatch):
    native, lease = session()
    original = native.api.read
    reads = 0
    def read(handle, size, *, limit):
        nonlocal reads
        reads += 1
        return original(handle, size, limit=limit) if reads == 1 else b'wrong'
    monkeypatch.setattr(native.api, 'read', read)
    with pytest.raises(SavedError) as error:
        lease.commit_payload(b'new')
    assert error.value.outcome == 'uncertain'
    assert native.flushes == 3
    assert ('remove', 3) not in native.events


def test_postdispatch_close_failure_is_uncertain():
    native, lease = session()
    native.close_error = 3
    with pytest.raises(SavedError) as error:
        lease.commit_payload(b'new')
    assert error.value.outcome == 'uncertain'
    assert ('remove', 3) not in native.events


def store_on(lease, index=None):
    # Bypass only filesystem construction; exercise the common owner unchanged.
    store = object.__new__(SavedStore)
    store.index = index
    @contextmanager
    def held():
        yield lease
    store._locked = held
    return store


def request():
    return {'request_id': 'first', 'kind': 'memory', 'scope': {'kind': 'global'},
            'title': 'Résumé 雪', 'content': 'Saved intent',
            'source': {'author': 'caller', 'reference': 'explicit'}}


def test_same_request_replay_adds_no_barrier_after_uncertain_visible_commit():
    native, lease = session()
    native.names.clear()
    native.statuses[3] = (0, 1)
    store = store_on(lease)
    with pytest.raises(SavedError) as error:
        store.save(request())
    assert error.value.outcome == 'uncertain'
    before = list(native.events)
    replay = store.save(request())
    assert replay['record']['revision'] == 1
    assert replay['index_status'] == 'disabled'
    assert [row for row in native.events[len(before):] if row[0] in ('flush', 'rename', 'write')] == []
    assert native.flushes == 3
    conflicting = request()
    conflicting['content'] = 'different'
    with pytest.raises(SavedError) as conflict:
        store.save(conflicting)
    assert conflict.value.code == 'conflict'


def test_replay_snapshot_and_current_index_status_remain_distinct():
    native, lease = session()
    native.names.clear()
    store = store_on(lease)
    saved = store.save(request())
    identifier = saved['record']['id']
    store.revise(identifier, {'content': 'second'}, {'kind': 'global'}, 'second', 1)
    replay = store.save(request())
    assert replay['record']['revision'] == 1
    assert store.get(identifier, {'kind': 'global'})['revision'] == 2
    assert replay['index_status'] == 'disabled'


def test_index_status_failure_keeps_committed_record_and_original_replay():
    native, lease = session()
    native.names.clear()
    native.statuses[4] = (1, 0)
    class Index:
        def __init__(self): self.calls = 0
        def upsert(self, record): self.calls += 1
    index = Index()
    store = store_on(lease, index)
    with pytest.raises(SavedError) as error:
        store.save(request())
    assert error.value.outcome == 'uncertain'
    assert 'index status durability' in str(error.value)
    assert index.calls == 1
    before = native.flushes
    replay = store.save(request())
    assert replay['record']['revision'] == 1 and replay['index_status'] == 'pending'
    assert index.calls == 1 and native.flushes == before
    raw = native.objects[native.names['state.json']]['raw']
    assert json.loads(raw)['records'][replay['record']['id']]['content'] == 'Saved intent'


def fake_locked(monkeypatch):
    native, lease = session()
    native.lock_acquired = True
    native.lock_once = lambda handle: native.lock_acquired
    native.unlock = lambda handle: native.events.append(('unlock', handle))
    monkeypatch.setattr(backend, '_Native', lambda: native)
    monkeypatch.setattr(backend, 'root_path', lambda root: root)
    def walk(api, root, handles):
        assert api is native
        handles.append(1)
        return 1
    monkeypatch.setattr(backend, '_walk', walk)
    return native


def test_created_lock_is_owned_before_initial_barrier_can_fail(monkeypatch):
    native = fake_locked(monkeypatch)
    native.statuses[1] = (0, 1)
    with pytest.raises(SavedError):
        with backend.locked('inert root'):
            pytest.fail('a failed lock-publication barrier cannot yield a lease')
    assert ('close', 3) in native.events and ('close', 1) in native.events
    assert not any(row[0] == 'unlock' for row in native.events)


def test_lock_busy_is_bounded_and_does_not_unlock_unacquired_range(monkeypatch):
    native = fake_locked(monkeypatch)
    native.lock_acquired = False
    elapsed = [0.0]
    def advance(seconds): elapsed[0] += seconds
    # Replace this module's dependency, never the shared time module API.
    monkeypatch.setattr(backend, 'time', SimpleNamespace(
        monotonic=lambda: elapsed[0], sleep=advance))
    with pytest.raises(SavedError) as error:
        with backend.locked('inert root'):
            pytest.fail('a contended lock cannot yield a lease')
    assert error.value.code == 'busy'
    assert 2.0 <= elapsed[0] < 2.02
    assert not any(row[0] == 'unlock' for row in native.events)
    assert ('close', 3) in native.events and ('close', 1) in native.events


def test_successful_lock_scope_releases_range_then_all_handles(monkeypatch):
    native = fake_locked(monkeypatch)
    with backend.locked('inert root') as lease:
        assert isinstance(lease, backend._Session)
    assert native.events[-3:] == [('unlock', 3), ('close', 3), ('close', 1)]


def test_constructor_refusal_uses_structured_storage_error(monkeypatch):
    def refuse(): raise RuntimeError('fixed volume is unavailable')
    monkeypatch.setattr(backend, '_Native', refuse)
    with pytest.raises(SavedError) as error:
        with backend.locked('inert root'):
            pytest.fail('unavailable native boundary cannot yield a lease')
    assert error.value.code == 'storage' and error.value.outcome == 'not_committed'


def writer_with_counts(counts):
    boundary = object.__new__(backend._Native)
    remaining = iter(counts)
    writes = []
    def write(handle, buffer, size, count, overlapped):
        assert overlapped is None
        actual = next(remaining)
        ctypes.cast(count, ctypes.POINTER(ctypes.c_uint32)).contents.value = actual
        writes.append(buffer.raw[:min(actual, size)])
        return 1
    def check(result, name):
        if not result:
            raise OSError(name)
    boundary.w = SimpleNamespace(DWORD=ctypes.c_uint32)
    boundary.k = SimpleNamespace(WriteFile=write)
    boundary.api = SimpleNamespace(_check=check)
    return boundary, writes


def test_actual_write_loop_retries_partial_progress_without_losing_bytes():
    boundary, writes = writer_with_counts([2, 1, 3])
    assert boundary.write_all('inert handle', b'abcdef') == 6
    assert writes == [b'ab', b'c', b'def']


@pytest.mark.parametrize('count', [0, 7])
def test_actual_write_loop_refuses_no_progress_or_excess_count(count):
    boundary, writes = writer_with_counts([count])
    with pytest.raises(OSError):
        boundary.write_all('inert handle', b'abcdef')
    assert len(writes) == 1


class WalkNative:
    """Inert namespace model; tests execute the actual production _walk body."""
    def __init__(self, existing=(), shared=None):
        self.api = self
        self.nodes = shared if shared is not None else {
            0: {'children': {'External': 1}, 'private': False, 'epoch': 0},
            1: {'children': {}, 'private': False, 'epoch': 0}}
        self.handles, self.closed, self.events = {}, set(), []
        self.statuses, self.denied, self.query_error = {}, set(), None
        self.collision, self.mutate, self.flush_count = None, None, 0
        self.misbind_writable, self.collision_private = None, True
        self.change_privacy_on_upgrade = None
        self.k = SimpleNamespace(CreateFileW=self.no_os_ancestor_authority)
        parent = 1
        for name in existing:
            parent = self.add(parent, name)

    def add(self, parent, name, private=True):
        identity = max(self.nodes) + 1
        self.nodes[identity] = {'children': {}, 'private': private, 'epoch': 0}
        self.nodes[parent]['children'][name] = identity
        return identity

    def handle(self, identity, writable=False):
        value = len(self.handles) + 100
        self.handles[value] = identity, writable
        return value

    def volume(self, path):
        assert str(path).startswith('C:\\')
        return 'C:\\'

    def volume_handle(self, anchor):
        assert anchor == 'C:\\'
        return self.handle(0)

    def no_os_ancestor_authority(self, *args):
        self.events.append(('os-ancestor-write',))
        raise OSError('arbitrary OS-prefix authority is unavailable')

    def metadata(self, handle):
        identity, _ = self.handles[handle]
        node = self.nodes[identity]
        return {'kind': 'directory',
                'identity': {'file_id': str(identity) + ':' + str(node['epoch'])},
                'private': node['private']}, 0, False

    def iter_names(self, handle):
        return iter(tuple(self.nodes[self.handles[handle][0]]['children']))

    def child(self, parent, name, *, directory, writable=False, create=False):
        assert directory is True
        identity = self.handles[parent][0]
        children = self.nodes[identity]['children']
        if create:
            assert self.handles[parent][1], 'creation requires real parent authority'
            if name in children:
                raise OSError(0xC0000035, 'collision')
            selected = self.add(identity, name)
            self.events.append(('create', selected))
            if name == self.collision:
                self.collision = None
                self.nodes[selected]['private'] = self.collision_private
                raise OSError(0xC0000035, 'other initializer created the visible child')
        else:
            selected = children[name]
        self.events.append(('open', selected, writable))
        if writable and selected in self.denied:
            raise OSError('required managed-parent write authority is denied')
        if writable and selected == self.change_privacy_on_upgrade:
            self.nodes[selected]['private'] = False
        if writable and selected == self.misbind_writable:
            return self.handle(0, True)
        return self.handle(selected, writable)

    def is_private(self, handle):
        identity = self.handles[handle][0]
        if identity == self.query_error:
            raise OSError('security query failed')
        return self.nodes[identity]['private']

    def private(self, handle):
        if not self.is_private(handle):
            raise OSError('managed suffix is not private')

    def flush(self, handle):
        identity, writable = self.handles[handle]
        assert writable, 'a read-only parent is not a publication barrier'
        self.flush_count += 1
        self.events.append(('barrier', identity))
        if self.mutate is not None:
            self.mutate(self, identity)
        return self.statuses.get(self.flush_count, (0, 0))

    def close(self, handle):
        assert handle not in self.closed
        self.closed.add(handle)


def actual_walk(native):
    handles = []
    try:
        root = backend._walk(native, 'C:\\External\\Managed\\Store', handles)
        return native.handles[root][0]
    finally:
        for handle in reversed(handles):
            native.close(handle)
        assert native.closed == set(native.handles), 'all acquired handles must close'


def test_actual_walk_failed_creation_barrier_retries_through_existing_publication():
    first = WalkNative()
    first.statuses[1] = (0, 1)
    with pytest.raises(OSError):
        actual_walk(first)
    assert first.nodes[1]['children'] == {'Managed': 2}
    assert first.nodes[2]['private'] and not first.nodes[2]['children']
    assert ('barrier', 1) in first.events
    retry = WalkNative(shared=first.nodes)
    assert actual_walk(retry) == 3
    assert [row for row in retry.events if row[0] == 'barrier'] == [('barrier', 1), ('barrier', 2)]
    assert ('create', 2) not in retry.events
    assert ('create', 3) in retry.events


@pytest.mark.parametrize('bad', [(1, 0), (0, 1), (0x103, 0), (0, False), None])
def test_actual_walk_visible_fresh_retry_cannot_yield_until_parent_success(bad):
    native = WalkNative(existing=('Managed', 'Store'))
    before = copy.deepcopy(native.nodes)
    native.statuses[1] = bad
    with pytest.raises(OSError):
        actual_walk(native)
    assert native.nodes == before
    assert [row for row in native.events if row[0] == 'barrier'] == [('barrier', 1)]
    assert not any(row[0] == 'create' for row in native.events)


def test_actual_walk_republishes_every_existing_managed_component():
    native = WalkNative(existing=('Managed', 'Store'))
    before = copy.deepcopy(native.nodes)
    assert actual_walk(native) == 3
    assert native.nodes == before
    assert [row for row in native.events if row[0] == 'barrier'] == [('barrier', 1), ('barrier', 2)]
    assert not any(row[0] in ('create', 'os-ancestor-write') for row in native.events)


@pytest.mark.parametrize('bad_position', [1, 2])
def test_actual_walk_collision_joins_same_checked_publication(bad_position):
    native = WalkNative()
    native.collision = 'Managed'
    native.statuses[bad_position] = (0, 0x103)
    with pytest.raises(OSError):
        actual_walk(native)
    assert native.nodes[1]['children']['Managed'] == 2
    barriers = [row for row in native.events if row[0] == 'barrier']
    assert barriers == [('barrier', 1), ('barrier', 2)][:bad_position]


def test_actual_walk_missing_parent_authority_refuses_without_os_prefix_fallback():
    native = WalkNative(existing=('Managed',))
    native.denied.add(1)
    before = copy.deepcopy(native.nodes)
    with pytest.raises(OSError):
        actual_walk(native)
    assert native.nodes == before
    assert not any(row[0] in ('barrier', 'create', 'os-ancestor-write') for row in native.events)


def test_actual_walk_parent_authority_upgrade_must_retain_exact_identity():
    native = WalkNative(existing=('Managed',))
    native.misbind_writable = 1
    with pytest.raises(OSError):
        actual_walk(native)
    assert not any(row[0] in ('barrier', 'create', 'os-ancestor-write') for row in native.events)


def test_actual_walk_collision_cannot_admit_nonprivate_component():
    native = WalkNative()
    native.collision, native.collision_private = 'Managed', False
    with pytest.raises(OSError):
        actual_walk(native)
    assert native.nodes[2]['private'] is False and not native.nodes[2]['children']
    assert not any(row[0] == 'barrier' for row in native.events)


def test_actual_walk_managed_parent_upgrade_rechecks_private_authority_before_create():
    native = WalkNative(existing=('Managed',))
    native.change_privacy_on_upgrade = 2
    with pytest.raises(OSError):
        actual_walk(native)
    assert native.nodes[2]['children'] == {}
    assert [row for row in native.events if row[0] == 'barrier'] == [('barrier', 1)]


@pytest.mark.parametrize('change', ['parent_identity', 'child_identity', 'child_privacy'])
def test_actual_walk_rechecks_authority_after_parent_publication(change):
    native = WalkNative(existing=('Managed', 'Store'))
    def mutate(api, identity):
        assert identity == 1
        if change == 'parent_identity':
            api.nodes[1]['epoch'] += 1
        elif change == 'child_identity':
            api.nodes[2]['epoch'] += 1
        else:
            api.nodes[2]['private'] = False
    native.mutate = mutate
    with pytest.raises(OSError):
        actual_walk(native)
    assert [row for row in native.events if row[0] == 'barrier'] == [('barrier', 1)]


def test_actual_walk_security_query_failure_is_not_an_external_prefix():
    native = WalkNative(existing=('Managed', 'Store'))
    native.query_error = 2
    with pytest.raises(OSError):
        actual_walk(native)
    assert not any(row[0] in ('barrier', 'create') for row in native.events)


def test_actual_walk_cannot_leave_managed_suffix_at_nonprivate_child():
    native = WalkNative(existing=('Managed', 'Store'))
    native.nodes[3]['private'] = False
    with pytest.raises(OSError):
        actual_walk(native)
    assert [row for row in native.events if row[0] == 'barrier'] == [('barrier', 1)]


def test_actual_private_classifier_propagates_native_security_query_error():
    native = object.__new__(backend._Native)
    native.a = SimpleNamespace(GetSecurityInfo=lambda *args: 5)
    with pytest.raises(OSError) as error:
        native.is_private('inert handle')
    assert error.value.errno == 5
