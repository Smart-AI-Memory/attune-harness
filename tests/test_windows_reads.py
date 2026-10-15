"""Actual retained-handle reads; native skips are never Windows success evidence.

# qualify: platform
"""

import ctypes
import hashlib
import os
from pathlib import Path
import subprocess

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
def test_only_named_absence_statuses_translate_to_missing(source, monkeypatch, code):
    original = native.Native.child

    def refuse(self, parent, name, **kwargs):
        if name == 'absent.json':
            raise OSError(code, 'injected native admission failure')
        return original(self, parent, name, **kwargs)

    monkeypatch.setattr(native.Native, 'child', refuse)
    with reads.open_read_root(source) as root:
        with pytest.raises(OSError) as caught:
            root.read('absent.json', max_bytes=100)
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
def test_namespace_swaps_cannot_read_outside_sentinels(source, monkeypatch, component):
    outside = source.parent.parent / 'outside'
    outside.mkdir()
    (outside / 'note.md').write_bytes(b'OUTSIDE_SENTINEL')
    calls = []
    original = native.Native.read

    def observed(self, *args, **kwargs):
        raw = original(self, *args, **kwargs)
        calls.append(raw)
        return raw

    monkeypatch.setattr(native.Native, 'read', observed)
    with reads.open_read_root(source) as root:
        selected = {'ancestor': source.parent, 'root': source,
                    'parent': source / 'nested', 'leaf': source / 'nested/note.md'}[component]
        selected.rename(selected.with_name(selected.name + '-retained'))
        if component == 'leaf':
            os.link(outside / 'note.md', selected)
        else:
            junction(selected, outside)
        with pytest.raises((ValueError, OSError)):
            root.read('nested/note.md', max_bytes=100)
    assert b'OUTSIDE_SENTINEL' not in calls


@windows_only
@pytest.mark.parametrize('kind', ['hardlink', 'stream'])
def test_ineligible_files_refuse_before_content_reads(source, monkeypatch, kind):
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
            root.read('nested/note.md', max_bytes=100)


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
def test_full_markdown_capacity_counts_selected_files_only(tmp_path, layout):
    root = tmp_path / 'capacity'
    root.mkdir()
    expected = []
    for index in range(4096):
        parent = root if layout == 'flat' else root / f'dir-{index // 64:02}'
        parent.mkdir(exist_ok=True)
        name = parent / f'note-{index:04}.md'
        name.write_bytes(b'')
        expected.append(name.relative_to(root).as_posix())
    for index in range(2049):
        (root / f'incidental-{index:04}.txt').write_bytes(b'')
    for name in ('summaries_by_path.json', 'verification.json'):
        (root / name).write_bytes(b'{}')
    with reads.open_read_root(root) as owner:
        assert owner.files(select=lambda name: name.endswith('.md'), max_files=4096) == sorted(expected)
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
def test_parent_replacement_still_refuses_when_directory_times_are_restored(source, monkeypatch):
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
            root.read('nested/note.md', max_bytes=100)
        assert fired
