"""Actual retained-handle reads; native skips are never Windows success evidence.

# qualify: platform
"""

from contextlib import ExitStack
import ctypes
import hashlib
import os
from pathlib import Path
import subprocess
import time
from threading import Event, RLock, Thread, current_thread

import pytest

from attune_harness import windows_effects as native, windows_reads as reads
from attune_harness.features import FeatureUnavailable
from attune_harness.recovery import UnresolvedOperation

windows_only = pytest.mark.skipif(os.name != 'nt', reason='Requires actual local-NTFS handles')


def test_import_and_unsupported_host_are_inert():
    if os.name != 'nt':
        with pytest.raises(FeatureUnavailable):
            with reads.open_read_root(r'C:\source'):
                pytest.fail('Unsupported host admitted a Windows source')


@pytest.fixture
def source(tmp_path):
    root = tmp_path / 'Owned ancestor' / 'Source α'
    (root / 'nested').mkdir(parents=True)
    (root / 'nested' / 'note.md').write_bytes(b'current source')
    (root / 'empty').write_bytes(b'')
    return root


def junction(path, target):
    command = Path(os.environ['SystemRoot']) / 'System32' / 'cmd.exe'
    result = subprocess.run([str(command), '/d', '/c', 'mklink', '/J', str(path), str(target)],
                            capture_output=True, check=False)
    assert result.returncode == 0, (result.stdout, result.stderr)


@windows_only
def test_read_observes_bytes_identity_times_and_never_requests_writes(source, monkeypatch):
    calls = []
    original = native.Native.child

    def child(self, *args, **kwargs):
        calls.append(kwargs)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(native.Native, 'child', child)
    with reads.open_read_root(source) as root:
        entry = root.entry
        observed = root.read('nested/note.md', max_bytes=14)
        assert observed.data == b'current source'
        assert observed.size == 14 and observed.sha256 == hashlib.sha256(observed.data).hexdigest()
        assert observed.entry['kind'] == 'file' and observed.entry['links'] == 1
        assert observed.entry['identity']['volume'] == entry['identity']['volume']
        assert observed.mtime_ns == (source / 'nested/note.md').stat().st_mtime_ns
        assert set(observed.times) == {'creation', 'last_write', 'change'}
        assert all(type(value) is int and value > 0 for value in observed.times.values())
        entry['identity']['file_id'] = 'caller mutation'
        assert root.entry['identity']['file_id'] != 'caller mutation'
        assert root.read('empty', max_bytes=0).data == b''
        with pytest.raises(ValueError, match='byte budget'):
            root.read('nested/note.md', max_bytes=13)
    assert calls and all(call.get('writable') is False and not call.get('create') for call in calls)
    assert (source / 'nested/note.md').read_bytes() == b'current source'
    with pytest.raises(ValueError, match='closed'):
        root.read('empty', max_bytes=0)


@windows_only
@pytest.mark.parametrize('limit', [-1, True, None, 0xFFFFFFFF])
def test_read_requires_a_real_finite_byte_allowance(source, limit):
    with reads.open_read_root(source) as root:
        with pytest.raises(ValueError, match='byte bound'):
            root.read('empty', max_bytes=limit)


@windows_only
@pytest.mark.parametrize('name', ['../outside', r'nested\note.md', 'nested//note.md',
                                 'nested/NOTE.md', 'empty:stream', 'empty.', 'CON'])
def test_unsafe_relative_names_and_case_aliases_refuse(source, name):
    with reads.open_read_root(source) as root:
        with pytest.raises((ValueError, OSError)):
            root.read(name, max_bytes=1024)


@windows_only
@pytest.mark.parametrize('name', ['C:\\', r'\\server\share\root', r'\\?\C:\root',
                                 r'C:\root\..\source', r'C:\root\.\source', 'C:/root//source'])
def test_root_spelling_is_not_resolved_past_unsafe_components(name):
    with pytest.raises(ValueError):
        with reads.open_read_root(name):
            pytest.fail('Unsafe root was admitted')


@windows_only
def test_missing_sidecar_is_not_cached_and_case_alias_is_not_missing(source):
    with reads.open_read_root(source) as root:
        with pytest.raises(FileNotFoundError):
            root.read('summaries_by_path.json', max_bytes=100)
        (source / 'summaries_by_path.json').write_bytes(b'{}')
        assert root.read('summaries_by_path.json', max_bytes=100).data == b'{}'
        with pytest.raises(ValueError, match='alias'):
            root.read('SUMMARIES_BY_PATH.JSON', max_bytes=100)
        with pytest.raises(FileNotFoundError):
            root.read('absent/sidecar.json', max_bytes=100)


@windows_only
@pytest.mark.parametrize('code', [0xC0000022, 0xC000003A, 5])
@pytest.mark.parametrize('mode', ['single', 'batch'])
def test_only_named_absence_statuses_translate_to_missing(source, monkeypatch, code, mode):
    original = native.Native.child

    def refuse(self, parent, name, **kwargs):
        if name == 'absent.json':
            raise OSError(code, 'injected native admission failure')
        return original(self, parent, name, **kwargs)

    monkeypatch.setattr(native.Native, 'child', refuse)
    with reads.open_read_root(source) as root:
        with pytest.raises(OSError) as caught:
            if mode == 'single':
                root.read('absent.json', max_bytes=100)
            else:
                root.read_many(['absent.json'], max_files=1, max_bytes=100, max_total_bytes=100)
        assert not isinstance(caught.value, FileNotFoundError)
        assert caught.value.errno == code


@windows_only
def test_enumerated_disappearance_and_nonfinal_read_are_stale_not_missing(source, monkeypatch):
    original = native.Native.child
    fired = False

    def disappear(self, parent, name, **kwargs):
        nonlocal fired
        if name == 'note.md' and not fired:
            fired = True
            (source / 'nested/note.md').rename(source / 'nested/retained.md')
        return original(self, parent, name, **kwargs)

    with reads.open_read_root(source) as root:
        monkeypatch.setattr(native.Native, 'child', disappear)
        with pytest.raises(ValueError, match='changed'):
            root.read('nested/note.md', max_bytes=100)
        assert fired
        monkeypatch.setattr(native.Native, 'child', original)

        def nonfinal(*args, **kwargs):
            raise UnresolvedOperation('injected nonfinal read')

        monkeypatch.setattr(native.Native, 'read', nonfinal)
        with pytest.raises(ValueError, match='did not complete'):
            root.read('nested/retained.md', max_bytes=100)


@windows_only
@pytest.mark.parametrize('kind', ['rewrite', 'timestamp', 'replacement', 'growth'])
def test_read_races_refuse_before_returning_observations(source, monkeypatch, kind):
    original = native.Native.read
    selected = source / 'nested/note.md'
    fired = False

    def changed(self, handle, size, **kwargs):
        nonlocal fired
        raw = original(self, handle, size, **kwargs)
        if not fired:
            fired = True
            if kind == 'timestamp':
                old = selected.stat()
                os.utime(selected, ns=(old.st_atime_ns, old.st_mtime_ns + 1_000_000_000))
            elif kind == 'replacement':
                other = selected.with_name('replacement')
                other.write_bytes(raw)
                other.replace(selected)
            else:
                selected.write_bytes(b'x' * size + (b'!' if kind == 'growth' else b''))
        return raw

    monkeypatch.setattr(native.Native, 'read', changed)
    with reads.open_read_root(source) as root:
        with pytest.raises((ValueError, OSError)):
            root.read('nested/note.md', max_bytes=100)
    assert fired


@windows_only
@pytest.mark.parametrize('component', ['ancestor', 'root', 'parent', 'leaf'])
@pytest.mark.parametrize('mode', ['single', 'batch'])
def test_namespace_swaps_cannot_read_outside_sentinels(source, monkeypatch, component, mode):
    outside = source.parent.parent / 'outside'
    outside.mkdir()
    # Each redirected spelling must actually be able to reach outside bytes.
    # A missing target would let an unsafe path reader satisfy the broad refusal.
    for target in (outside / 'note.md', outside / 'nested/note.md',
                   outside / source.name / 'nested/note.md'):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'OUTSIDE_SENTINEL')
    calls, unsafe_followed = [], []
    original = native.Native.read

    def unsafe_follow_control():
        # Deliberately follow the path in this test-only control, using real I/O.
        unsafe_followed.append((source / 'nested/note.md').read_bytes())
        assert unsafe_followed[-1] == b'OUTSIDE_SENTINEL'

    def observed(self, *args, **kwargs):
        raw = original(self, *args, **kwargs)
        calls.append(raw)
        return raw

    def capture(root):
        if mode == 'single':
            return root.read('nested/note.md', max_bytes=100)
        return root.read_many(['nested/note.md'], max_files=1,
                              max_bytes=100, max_total_bytes=100)

    monkeypatch.setattr(native.Native, 'read', observed)
    if component == 'ancestor':
        # Windows refuses renaming an ancestor with an already-open descendant.
        # Attack after that ancestor is retained, before its child root opens.
        original_child = native.Native.child
        attack_completed = False

        def swap_ancestor(self, parent, name, **kwargs):
            nonlocal attack_completed
            if name == source.name and not attack_completed:
                selected = source.parent
                selected.rename(selected.with_name(selected.name + '-retained'))
                junction(selected, outside)
                attack_completed = True
                unsafe_follow_control()
            return original_child(self, parent, name, **kwargs)

        monkeypatch.setattr(native.Native, 'child', swap_ancestor)
        with pytest.raises((ValueError, OSError)):
            with reads.open_read_root(source) as root:
                capture(root)
        assert attack_completed, 'The ancestor attack must actually execute'
        # A control-side OSError inside pytest.raises must not become a pass.
        assert unsafe_followed == [b'OUTSIDE_SENTINEL']
        assert b'OUTSIDE_SENTINEL' not in calls
        return
    with reads.open_read_root(source) as root:
        selected = {'root': source,
                    'parent': source / 'nested', 'leaf': source / 'nested/note.md'}[component]
        selected.rename(selected.with_name(selected.name + '-retained'))
        if component == 'leaf':
            os.link(outside / 'note.md', selected)
        else:
            junction(selected, outside)
        unsafe_follow_control()
        with pytest.raises((ValueError, OSError)):
            capture(root)
    assert unsafe_followed == [b'OUTSIDE_SENTINEL']
    assert b'OUTSIDE_SENTINEL' not in calls


@windows_only
@pytest.mark.parametrize('kind', ['hardlink', 'stream'])
@pytest.mark.parametrize('mode', ['single', 'batch'])
def test_ineligible_files_refuse_before_content_reads(source, monkeypatch, kind, mode):
    selected = source / 'nested/note.md'
    if kind == 'hardlink':
        os.link(selected, source / 'twin.md')
    else:
        Path(str(selected) + ':hidden').write_bytes(b'hidden')

    def refuse(*args, **kwargs):
        pytest.fail('Ineligible file reached a content read')

    monkeypatch.setattr(native.Native, 'read', refuse)
    with reads.open_read_root(source) as root:
        with pytest.raises(ValueError):
            if mode == 'single':
                root.read('nested/note.md', max_bytes=100)
            else:
                root.read_many(['nested/note.md'], max_files=1, max_bytes=100, max_total_bytes=100)


@windows_only
def test_completed_enumeration_cannot_be_reset_by_interleaved_reads(source):
    (source / 'second.md').write_bytes(b'second')
    with reads.open_read_root(source) as root:
        names = root._api.iter_names(root._root)
        first = next(names)
        expected = root._api.names(root._root)
        assert root.read('second.md', max_bytes=100).data == b'second'
        assert [first, *names] == expected
        seen = []

        def select(name):
            seen.append(root.read(name, max_bytes=100).data)
            return name.endswith('.md')

        assert root.files(select=select, max_files=2) == ['nested/note.md', 'second.md']
        assert sorted(seen) == sorted([b'', b'current source', b'second'])


@windows_only
@pytest.mark.parametrize('layout', ['flat', 'nested'])
def test_full_markdown_capacity_counts_selected_files_only(tmp_path, layout, record_property):
    root = tmp_path / 'capacity'
    root.mkdir()
    expected, payloads = [], {}
    for index in range(4096):
        parent = root if layout == 'flat' else root / f'dir-{index // 64:02}'
        parent.mkdir(exist_ok=True)
        name = parent / f'note-{index:04}.md'
        raw = f'unique memory document {index}'.encode('ascii')
        name.write_bytes(raw)
        path = name.relative_to(root).as_posix()
        expected.append(path)
        payloads[path] = raw
    for index in range(2049):
        (root / f'incidental-{index:04}.txt').write_bytes(b'')
    for name in ('summaries_by_path.json', 'verification.json'):
        (root / name).write_bytes(b'{}')
    with reads.open_read_root(root) as owner:
        started = time.perf_counter()
        assert owner.files(select=lambda name: name.endswith('.md'), max_files=4096) == sorted(expected)
        record_property('reader_discovery_seconds', time.perf_counter() - started)
        started = time.perf_counter()
        captured = owner.read_many(expected, max_files=4096, max_bytes=8 * 1024 * 1024,
                                   max_total_bytes=4096 * 8 * 1024 * 1024)
        record_property('reader_read_all_seconds', time.perf_counter() - started)
        assert {name: observed.data for name, observed in captured.items()} == payloads
        identities = {observed.entry['identity']['file_id'] for observed in captured.values()}
        payload_hashes = {observed.sha256 for observed in captured.values()}
        record_property('reader_read_all_files', len(captured))
        record_property('reader_read_all_distinct_ids', len(identities))
        record_property('reader_read_all_distinct_payloads', len(payload_hashes))
        assert len(captured) == len(identities) == len(payload_hashes) == 4096
        # The historical effects surface retains its bound and refusal text.
        with pytest.raises(ValueError, match='Directory exceeds bounded Windows profile'):
            owner._api.names(owner._root)
        (root / 'one-too-many.md').write_bytes(b'')
        with pytest.raises(ValueError, match='selected source file limit'):
            owner.files(select=lambda name: name.endswith('.md'), max_files=4096)


@windows_only
def test_ancestor_and_named_reads_do_not_inherit_effects_entry_or_byte_limits(tmp_path):
    parent = tmp_path / 'wide parent'
    parent.mkdir()
    for index in range(2049):
        (parent / f'incidental-{index}').write_bytes(b'')
    source = parent / 'source'
    source.mkdir()
    data = b'x' * (native.MAX_TREE + 1)
    (source / 'large').write_bytes(data)
    with reads.open_read_root(source) as root:
        assert root.read('large', max_bytes=256 * 1024 * 1024).data == data
        assert root.read_many(['large'], max_files=1, max_bytes=256 * 1024 * 1024,
                              max_total_bytes=256 * 1024 * 1024)['large'].data == data
        with pytest.raises(ValueError, match='byte budget'):
            root.read('large', max_bytes=8 * 1024 * 1024)


class DirectoryRow(ctypes.Structure):
    """Fixed-width FILE_FULL_DIR_INFO fixture, not a native filesystem witness."""
    _fields_ = [('NextEntryOffset', ctypes.c_uint32), ('FileIndex', ctypes.c_uint32),
                ('CreationTime', ctypes.c_int64), ('LastAccessTime', ctypes.c_int64),
                ('LastWriteTime', ctypes.c_int64), ('ChangeTime', ctypes.c_int64),
                ('EndOfFile', ctypes.c_int64), ('AllocationSize', ctypes.c_int64),
                ('FileAttributes', ctypes.c_uint32), ('FileNameLength', ctypes.c_uint32),
                ('EaSize', ctypes.c_uint32), ('FileName', ctypes.c_uint16 * 1)]


def parser(monkeypatch, names):
    """Supply ABI-shaped batches to the shared parser without native pass claims."""
    batches = []
    for at in range(0, len(names), 100):
        rows = []
        for name in names[at:at + 100]:
            encoded = name.encode('utf-16-le')
            size = (DirectoryRow.FileName.offset + len(encoded) + 7) // 8 * 8
            raw = bytearray(size)
            row = DirectoryRow.from_buffer(raw)
            row.NextEntryOffset, row.FileNameLength = size, len(encoded)
            raw[DirectoryRow.FileName.offset:DirectoryRow.FileName.offset + len(encoded)] = encoded
            rows.append(raw)
        DirectoryRow.from_buffer(rows[-1]).NextEntryOffset = 0
        batches.append(b''.join(rows))

    class Kernel:
        cursor = 0

        def GetFileInformationByHandleEx(self, handle, cls, buffer, size):
            if cls == 15:
                self.cursor = 0
            if self.cursor == len(batches):
                return False
            batch = batches[self.cursor]
            self.cursor += 1
            ctypes.memmove(buffer, batch, len(batch))
            return True

    monkeypatch.setattr(ctypes, 'get_last_error', lambda: native.ERROR_NO_MORE_FILES, raising=False)
    api = object.__new__(native.Native)
    api.FullDir, api.k = DirectoryRow, Kernel()
    return api


def test_parser_keeps_effects_bound_and_completes_new_unbounded_scan(monkeypatch):
    expected = [f'note-{index:04}.md' for index in range(4096)]
    api = parser(monkeypatch, expected)
    names = api.iter_names(None)
    first = next(names)
    with pytest.raises(ValueError, match='Directory exceeds bounded Windows profile'):
        api.names(None)
    assert [first, *names] == expected
    assert list(api.iter_names(None)) == expected


@pytest.mark.parametrize('names', [['Same.md', 'same.md'], ['same.md', 'same.md'],
                                  ['file:stream'], ['name.']])
def test_shared_parser_rejects_collisions_and_invalid_names(monkeypatch, names):
    api = parser(monkeypatch, names)
    for scan in (api.names, api.iter_names):
        with pytest.raises(ValueError):
            scan(None)


@windows_only
def test_exact_memory_byte_bound_and_one_byte_over(source):
    data = b'x' * (8 * 1024 * 1024)
    selected = source / 'boundary'
    selected.write_bytes(data)
    with reads.open_read_root(source) as root:
        assert root.read('boundary', max_bytes=len(data)).data == data
        with selected.open('ab') as stream:
            stream.write(b'!')
        with pytest.raises(ValueError, match='byte budget'):
            root.read('boundary', max_bytes=len(data))


@windows_only
@pytest.mark.parametrize('mode', ['single', 'batch'])
def test_parent_replacement_still_refuses_when_directory_times_are_restored(source, monkeypatch, mode):
    original = native.Native.read
    with reads.open_read_root(source) as root:
        api = root._api
        before = api.info(root._root, api.Basic, 0)
        api.k.SetFileInformationByHandle.argtypes = [api.w.HANDLE, ctypes.c_int,
                                                     ctypes.c_void_p, api.w.DWORD]
        api.k.SetFileInformationByHandle.restype = api.w.BOOL
        fired = False

        def replaced(self, *args, **kwargs):
            nonlocal fired
            raw = original(self, *args, **kwargs)
            if not fired:
                fired = True
                (source / 'nested').rename(source.parent / 'retained-parent')
                (source / 'nested').mkdir()
                (source / 'nested/note.md').write_bytes(raw)
                # This writable handle belongs only to the adversarial fixture.
                # Production source handles always remain read-only.
                handle = api.k.CreateFileW(str(source), 0x0100, native.FILE_SHARE_ALL,
                                          None, 3, 0x02000000 | native.FILE_OPEN_REPARSE_POINT, None)
                with api.owned(handle):
                    api._check(api.k.SetFileInformationByHandle(handle, 0, ctypes.byref(before),
                                                               ctypes.sizeof(before)), 'restore test times')
                assert reads._times(api.info(root._root, api.Basic, 0)) == reads._times(before)
            return raw

        monkeypatch.setattr(native.Native, 'read', replaced)
        with pytest.raises((ValueError, OSError)):
            if mode == 'single':
                root.read('nested/note.md', max_bytes=100)
            else:
                root.read_many(['nested/note.md'], max_files=1, max_bytes=100, max_total_bytes=100)
        assert fired


class CloseGate:
    """Signal a closer's lock attempt, so the ownership check needs no sleep."""
    def __init__(self, progress):
        self.lock, self.progress = RLock(), progress

    def __enter__(self):
        if current_thread().name == 'closing-root':
            self.progress.set()
        self.lock.acquire()
        return self

    def __exit__(self, *error):
        self.lock.release()


def test_shutdown_waits_for_active_operations_with_causal_unsafe_control():
    """Portable lifecycle witness; no fabricated handle counts as native I/O."""
    def exercise(close):
        active, release, progress = Event(), Event(), Event()
        root = object.__new__(reads.ReadRoot)
        root._closed, root._lock = False, CloseGate(progress)
        handles, closed_while_active, errors = ExitStack(), [], []

        def record_close():
            closed_while_active.append(active.is_set())
            progress.set()

        handles.callback(record_close)

        def operation():
            with root._lock:
                active.set()
                if not release.wait(5):
                    errors.append('Operation release gate timed out')
                active.clear()

        def shutdown():
            try:
                close(root, handles)
            except BaseException as error:
                errors.append(error)

        worker = Thread(target=operation)
        closer = Thread(target=shutdown, name='closing-root')
        worker.start()
        try:
            assert active.wait(5)
            closer.start()
            assert progress.wait(5), 'Shutdown must reach the lock or close callback'
            observed = list(closed_while_active)
        finally:
            release.set()
            worker.join(5)
            if closer.ident is not None:
                closer.join(5)
        assert not worker.is_alive() and not closer.is_alive() and not errors
        assert root._closed and closed_while_active
        return observed, closed_while_active

    def unsafe_close(root, handles):
        root._closed = True
        handles.close()

    assert exercise(unsafe_close) == ([True], [True])
    assert exercise(reads.ReadRoot._close) == ([], [False])


@windows_only
@pytest.mark.parametrize('mode', ['single', 'batch'])
def test_native_context_exit_waits_for_active_read_before_closing_handles(source, monkeypatch, mode):
    manager = reads.open_read_root(source)
    root = manager.__enter__()
    active, release, progress = Event(), Event(), Event()
    root._lock = CloseGate(progress)
    observed, errors, closed_while_active = [], [], []
    original_read, original_close = native.Native.read, root._api.k.CloseHandle

    def blocked_read(self, *args, **kwargs):
        raw = original_read(self, *args, **kwargs)
        active.set()
        try:
            assert release.wait(5), 'Read release gate timed out'
        finally:
            active.clear()
        return raw

    def close_handle(handle):
        if current_thread().name == 'closing-root':
            closed_while_active.append(active.is_set())
            progress.set()
        return original_close(handle)

    monkeypatch.setattr(native.Native, 'read', blocked_read)
    monkeypatch.setattr(root._api.k, 'CloseHandle', close_handle)

    def operation():
        try:
            if mode == 'single':
                observed.append(root.read('nested/note.md', max_bytes=100).data)
            else:
                batch = root.read_many(['nested/note.md'], max_files=1,
                                       max_bytes=100, max_total_bytes=100)
                observed.append(batch['nested/note.md'].data)
        except BaseException as error:
            errors.append(error)

    def shutdown():
        try:
            manager.__exit__(None, None, None)
        except BaseException as error:
            errors.append(error)

    worker = Thread(target=operation)
    closer = Thread(target=shutdown, name='closing-root')
    worker.start()
    try:
        assert active.wait(5), 'Native read must be active before context exit'
        closer.start()
        assert progress.wait(5), 'Context exit must reach the lock or handle close'
        assert not closed_while_active, 'A source handle closed during the active read'
    finally:
        release.set()
        worker.join(5)
        if closer.ident is not None:
            closer.join(5)
        else:
            manager.__exit__(None, None, None)
    assert not worker.is_alive() and not closer.is_alive()
    assert not errors and observed == [b'current source']
    assert closed_while_active and not any(closed_while_active)
    with pytest.raises(ValueError, match='closed'):
        root.read('empty', max_bytes=0)


@pytest.mark.parametrize('field,value', [
    ('max_files', -1), ('max_files', True), ('max_files', None),
    ('max_bytes', -1), ('max_bytes', True), ('max_bytes', None),
    ('max_bytes', 0xFFFFFFFF), ('max_total_bytes', -1),
    ('max_total_bytes', True), ('max_total_bytes', None),
])
def test_batch_invalid_bounds_refuse_before_touching_a_root(field, value):
    # Lifecycle-free validation only; this is not native filesystem evidence.
    root = object.__new__(reads.ReadRoot)
    bounds = dict(max_files=1, max_bytes=100, max_total_bytes=100)
    bounds[field] = value
    with pytest.raises(ValueError, match='independent file and byte bounds'):
        root.read_many(['note.md'], **bounds)


@pytest.mark.parametrize('names', [['note.md', 'note.md'], ['nested', 'nested/note.md'],
                                 ['../outside'], ['note.md:stream'], 'note.md'])
def test_batch_invalid_requests_refuse_before_touching_a_root(names):
    root = object.__new__(reads.ReadRoot)
    with pytest.raises(ValueError):
        root.read_many(names, max_files=2, max_bytes=100, max_total_bytes=100)


def test_batch_request_iterator_is_bounded_before_native_admission():
    supplied = []

    def names():
        for index in range(100):
            supplied.append(index)
            yield f'note-{index}.md'

    root = object.__new__(reads.ReadRoot)
    with pytest.raises(ValueError, match='selected source file limit'):
        root.read_many(names(), max_files=2, max_bytes=100, max_total_bytes=100)
    assert supplied == [0, 1, 2]


def test_only_confirmed_missing_crosses_the_public_absence_boundary():
    # The unsafe direct exception is an absence to callers; the real boundary
    # must prevent metadata/scanning failures from acquiring that meaning.
    with pytest.raises(FileNotFoundError):
        raise FileNotFoundError(2, 'metadata failure control')
    with pytest.raises(ValueError, match='not confirmed name absence'):
        with reads._final_reads():
            raise FileNotFoundError(2, 'metadata failure control')
    with pytest.raises(FileNotFoundError, match='confirmed absent'):
        with reads._final_reads():
            raise reads._ConfirmedMissing('confirmed absent')


@windows_only
def test_batch_observes_exact_bytes_identities_and_independent_exact_bounds(source, monkeypatch):
    (source / 'second.md').write_bytes(b'second')
    calls, original = [], native.Native.child

    def child(self, *args, **kwargs):
        calls.append(kwargs)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(native.Native, 'child', child)
    with reads.open_read_root(source) as root:
        captured = root.read_many(['second.md', 'nested/note.md', 'empty'], max_files=3,
                                  max_bytes=14, max_total_bytes=20)
        assert list(captured) == ['empty', 'nested/note.md', 'second.md']
        assert {name: item.data for name, item in captured.items()} == {
            'empty': b'', 'nested/note.md': b'current source', 'second.md': b'second'}
        assert len({item.entry['identity']['file_id'] for item in captured.values()}) == 3
        for name, item in captured.items():
            assert item.sha256 == hashlib.sha256(item.data).hexdigest()
            assert item.mtime_ns == (source / name).stat().st_mtime_ns
        captured['second.md'].entry['identity']['file_id'] = 'caller mutation'
        assert root.read('second.md', max_bytes=6).data == b'second'
        assert root.read_many([], max_files=0, max_bytes=0, max_total_bytes=0) == {}
    assert calls and all(call.get('writable') is False and not call.get('create') for call in calls)
    with pytest.raises(ValueError, match='closed'):
        root.read_many([], max_files=0, max_bytes=0, max_total_bytes=0)


@windows_only
@pytest.mark.parametrize('bound', ['files', 'per_file', 'aggregate'])
def test_batch_over_bounds_refuse_before_any_content_read(source, monkeypatch, bound):
    (source / 'second.md').write_bytes(b'second')
    limits = dict(max_files=2, max_bytes=14, max_total_bytes=20)
    limits[{'files': 'max_files', 'per_file': 'max_bytes', 'aggregate': 'max_total_bytes'}[bound]] -= 1

    def content_read(*args, **kwargs):
        pytest.fail('An over-budget batch reached a content read')

    with reads.open_read_root(source) as root:
        monkeypatch.setattr(native.Native, 'read', content_read)
        with pytest.raises(ValueError, match='file limit|byte budget'):
            root.read_many(['nested/note.md', 'second.md'], **limits)


@windows_only
def test_batch_missing_appearance_and_aliases_never_reuse_negative_absence(source):
    with reads.open_read_root(source) as root:
        with pytest.raises(FileNotFoundError):
            root.read_many(['sidecar.json'], max_files=1, max_bytes=100, max_total_bytes=100)
        (source / 'sidecar.json').write_bytes(b'{}')
        assert root.read_many(['sidecar.json'], max_files=1, max_bytes=2,
                              max_total_bytes=2)['sidecar.json'].data == b'{}'
        with pytest.raises(ValueError, match='alias'):
            root.read_many(['SIDECAR.JSON'], max_files=1, max_bytes=100, max_total_bytes=100)
        with pytest.raises(FileNotFoundError):
            root.read_many(['absent/sidecar.json'], max_files=1, max_bytes=100, max_total_bytes=100)


@windows_only
@pytest.mark.parametrize('mode', ['single', 'batch'])
def test_native_metadata_file_not_found_is_a_refusal_not_absence(source, monkeypatch, mode):
    original = native.Native.metadata

    def missing_metadata(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        if result[0]['kind'] == 'file':
            raise FileNotFoundError(2, 'Injected metadata failure on an existing file')
        return result

    with reads.open_read_root(source) as root:
        monkeypatch.setattr(native.Native, 'metadata', missing_metadata)
        with pytest.raises(ValueError, match='not confirmed name absence'):
            if mode == 'single':
                root.read('nested/note.md', max_bytes=100)
            else:
                root.read_many(['nested/note.md'], max_files=1, max_bytes=100, max_total_bytes=100)


@windows_only
@pytest.mark.parametrize('kind', ['rewrite', 'growth', 'replacement', 'late_rewrite'])
def test_batch_mutations_refuse_including_files_already_read(source, monkeypatch, kind):
    (source / 'tail.md').write_bytes(b'tail')
    target = source / 'nested/note.md'
    original, observed, fired = native.Native.read, [], False

    def changed(self, *args, **kwargs):
        nonlocal fired
        raw = original(self, *args, **kwargs)
        observed.append(raw)
        if not fired and (kind != 'late_rewrite' or len(observed) == 2):
            fired = True
            if kind == 'replacement':
                target.rename(target.with_name('retained.md'))
                target.write_bytes(b'current source')
            else:
                target.write_bytes(b'changed source' + (b'!' if kind == 'growth' else b''))
        return raw

    with reads.open_read_root(source) as root:
        monkeypatch.setattr(native.Native, 'read', changed)
        if kind == 'late_rewrite':
            # Real unsafe composition control: separate successful reads cannot
            # revalidate the first file after the second read changes it.
            unsafe = {name: root.read(name, max_bytes=100).data
                      for name in ['nested/note.md', 'tail.md']}
            assert unsafe == {'nested/note.md': b'current source', 'tail.md': b'tail'}
            assert target.read_bytes() == b'changed source'
            target.write_bytes(b'current source')
            observed.clear()
            fired = False
        with pytest.raises((ValueError, OSError)):
            root.read_many(['nested/note.md', 'tail.md'], max_files=2,
                           max_bytes=100, max_total_bytes=200)
    assert fired and observed[0] == b'current source'
    if kind == 'late_rewrite':
        assert observed == [b'current source', b'tail']
    assert target.read_bytes() == (b'current source' if kind == 'replacement' else
                                   b'changed source' + (b'!' if kind == 'growth' else b''))


@windows_only
def test_batch_full_directory_scans_do_not_grow_with_selected_file_count(source, monkeypatch):
    for index in range(8):
        (source / f'item-{index}.md').write_bytes(str(index).encode('ascii'))
    original, scans = native.Native.iter_names, []
    with reads.open_read_root(source) as root:
        def counted(self, handle):
            if handle == root._root:
                scans.append(handle)
            return original(self, handle)

        monkeypatch.setattr(native.Native, 'iter_names', counted)
        counts = []
        for count in (2, 8):
            scans.clear()
            result = root.read_many([f'item-{index}.md' for index in range(count)],
                                    max_files=8, max_bytes=1, max_total_bytes=8)
            assert [item.data for item in result.values()] == [str(i).encode('ascii') for i in range(count)]
            counts.append(len(scans))
        assert counts[0] > 0 and counts[0] == counts[1]


@windows_only
def test_batch_checkpoint_admits_empty_directories_and_prunes_explicit_scope(source):
    (source / 'notes' / 'nested').mkdir(parents=True)
    (source / 'notes' / 'direct.md').write_bytes(b'direct')
    (source / 'notes' / 'nested' / 'ignored.md').write_bytes(b'ignored')
    (source / 'rules' / 'deep').mkdir(parents=True)
    (source / 'rules' / 'deep' / 'rule.md').write_bytes(b'rule')
    (source / 'selected-empty').mkdir()
    (source / 'unrelated').mkdir()
    (source / 'unrelated' / 'ignored.md').write_bytes(b'ignored')
    def selected(name):
        return name.endswith('.md') and (name.rpartition('/')[0] == 'notes' or name.startswith('rules/'))
    def descend(name):
        return name in ('notes', 'rules', 'selected-empty') or name.startswith('rules/')
    with reads.open_read_root(source) as root:
        with root.observe(select=selected, descend=descend, required_dirs=['notes', 'rules', 'selected-empty'],
                          max_files=2, max_bytes=100, max_total_bytes=100, checkpoint=True) as observed:
            assert set(observed) == {'notes/direct.md', 'rules/deep/rule.md'}
            observed.verify()
            assert set(observed.evidence['directories']) == {'', 'notes', 'rules', 'rules/deep', 'selected-empty'}
        with pytest.raises(ValueError, match='closed'):
            observed.verify()
        # Existing readers still get an ordinary dict and recursive discovery.
        with root.observe(select=lambda name: name.endswith('.md'), max_files=20,
                          max_bytes=100, max_total_bytes=1000) as plain:
            assert type(plain) is dict
            assert 'notes/nested/ignored.md' in plain and 'unrelated/ignored.md' in plain


@windows_only
def test_batch_all_present_limit_includes_optional_empty_sidecar_before_content_read(source, monkeypatch):
    (source / 'optional.json').write_bytes(b'')
    calls = []
    original = native.Native.read
    def read(self, *args, **kwargs):
        calls.append(True)
        return original(self, *args, **kwargs)
    monkeypatch.setattr(native.Native, 'read', read)
    with reads.open_read_root(source) as root:
        with pytest.raises(reads.SourceLimitExceeded) as caught:
            with root.observe(names=['nested/note.md'], optional=['optional.json'], max_files=1,
                              max_present_files=1, max_bytes=100, max_total_bytes=100, checkpoint=True):
                pytest.fail('Optional present file exceeded the complete file allowance')
        assert caught.value.bound == 'files'
    assert calls == []


@windows_only
def test_batch_missing_required_directory_cannot_look_like_an_empty_selection(source):
    with reads.open_read_root(source) as root:
        with pytest.raises((ValueError, FileNotFoundError)):
            with root.observe(required_dirs=['missing-empty'], max_files=0,
                              max_bytes=0, max_total_bytes=0, checkpoint=True):
                pytest.fail('Missing required directory was admitted')
