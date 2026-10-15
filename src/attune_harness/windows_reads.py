"""Read-only local-NTFS observations through retained, exact-name handles.

This module supplies bytes and native evidence, not a public version-token format.
Callers retain their own path policy, selected-file/aggregate bounds and records.
As with the effects primitives, this is not hostile-writer isolation. Namespace
and metadata changes observed during an operation refuse instead of returning a
possibly stale observation. No source handle requests write or delete access.
"""

from contextlib import ExitStack, contextmanager
from copy import deepcopy
from dataclasses import dataclass
import ctypes
import hashlib
import ntpath
import struct
import os
from pathlib import Path
from threading import RLock

from .recovery import UnresolvedOperation
from .windows_effects import (
    FILE_ATTRIBUTE_REPARSE_POINT, Native, _identity, absolute_path, leaf, relative, require_platform,
)

# NtCreateFile receives one leaf under a retained parent, never a multi-part path.
# Only these exact NTSTATUS values establish absence after a completed listing.
# https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-erref/596a1078-e883-4972-9bbc-49e60bebca55
_MISSING = frozenset({0xC000000F, 0xC0000034})  # NO_SUCH_FILE, OBJECT_NAME_NOT_FOUND
_FILETIME_EPOCH = 116444736000000000


@dataclass(frozen=True)
class FileObservation:
    """Captured bytes plus native evidence; no live handle leaves its owner."""

    data: bytes
    entry: dict
    times: dict

    @property
    def mtime_ns(self):
        # FILE_BASIC_INFO times count 100 ns intervals since 1601-01-01 UTC.
        return (self.times['last_write'] - _FILETIME_EPOCH) * 100

    @property
    def sha256(self):
        return self.entry['sha256']

    @property
    def size(self):
        return self.entry['size']


@dataclass(frozen=True)
class _State:
    entry: dict
    size: int
    times: dict


def _times(basic):
    # LastAccessTime is deliberately excluded: our own read can affect it.
    return dict(creation=int(basic.CreationTime), last_write=int(basic.LastWriteTime),
                change=int(basic.ChangeTime))


class SourceLimitExceeded(ValueError):
    """A caller-owned count, per-file or aggregate source allowance was exceeded."""

    def __init__(self, bound, message):
        super().__init__(message)
        self.bound = bound


class _ConfirmedMissing(FileNotFoundError):
    """Only an exact absent-name probe may cross the public absence boundary."""


@contextmanager
def _final_reads():
    try:
        yield
    except UnresolvedOperation as error:
        raise ValueError('Windows source observation did not complete: ' + str(error)) from error
    except _ConfirmedMissing as error:
        raise FileNotFoundError(str(error)) from error
    except FileNotFoundError as error:
        raise ValueError('Source failure is not confirmed name absence') from error


def _symlink_target(source, data):
    """Parse only the documented local symbolic-link target, never a resolver."""
    # MS-FSCC 2.1.2.4: header8, four USHORT name fields8, flags4, UTF16 buffer.
    if len(data) < 20:
        raise ValueError('Malformed symbolic-link reparse data')
    tag, size, _ = struct.unpack_from('<IHH', data)
    offset, length, printed, print_length, flags = struct.unpack_from('<HHHHI', data, 8)
    if tag != 0xA000000C or size + 8 != len(data) or flags not in (0, 1):
        raise ValueError('Only documented symbolic-link reparse data can prove absence')
    for start, count in ((offset, length), (printed, print_length)):
        if start % 2 or count % 2 or 20 + start + count > len(data):
            raise ValueError('Malformed symbolic-link target bounds')
    try:
        target = data[20 + offset:20 + offset + length].decode('utf-16-le')
    except UnicodeError as error:
        raise ValueError('Malformed symbolic-link target encoding') from error
    if not target or '\x00' in target:
        raise ValueError('Malformed symbolic-link target name')
    if flags == 0 and target.startswith('\\??\\'):
        target = target[4:]
    raw_parts = target[3:] if absolute_path(target) else target
    for part in raw_parts.replace('\\', '/').split('/'):
        if part and part not in ('.', '..'):
            leaf(part)
    if flags == 1:
        if ntpath.splitdrive(target)[0] or target.startswith(('\\', '/')):
            raise ValueError('Relative symbolic-link target is not relative')
        target = ntpath.join(str(source.parent), target)
    # Dot/dotdot in a symlink target are OS path semantics, not authority. Only
    # their lexical collapse is used; all resulting components get fresh walks.
    target = ntpath.normpath(target)
    if not absolute_path(target):
        raise ValueError('Symbolic-link absence requires a fixed local drive target')
    relative(target[3:].replace('\\', '/'))
    return Path(target)


class ReadRoot:
    """One admitted root and its retained ancestor bindings. Use open_read_root."""

    def __init__(self, api, stack, path):
        self._api, self._closed, self._path = api, False, path
        self._lock = RLock()
        self._bindings = []
        anchor = api.volume(path)
        current = stack.enter_context(api.owned(api.volume_handle(anchor)))
        state = self._stat(current)
        for name in path.parts[1:]:
            child, child_state = self._named(current, name, directory=True)
            stack.enter_context(api.owned(child))
            self._bindings.append((current, name, child_state))
            current, state = child, child_state
        self._root = current
        # Root evidence has the same shape as Native.metadata(root), without an
        # artificial parent identity. It is not a serialized consumer snapshot.
        self._entry = deepcopy(state.entry)
        self._entry.pop('parent_identity', None)

    @property
    def entry(self):
        self._ensure_open()
        return deepcopy(self._entry)

    def _ensure_open(self):
        if self._closed:
            raise ValueError('Windows read root is closed')

    def _close(self, handles):
        # Wait for active observations before invalidating their retained handles.
        # ExitStack must unwind under the same lock, not after it is released.
        with self._lock:
            self._closed = True
            handles.close()

    def _stat(self, handle, parent_identity=None):
        api = self._api
        before = api.info(handle, api.Basic, 0)
        entry, size, _ = api.metadata(handle, parent_identity)
        after = api.info(handle, api.Basic, 0)
        if (_times(before) != _times(after)
                or int(before.FileAttributes) != int(after.FileAttributes)
                or entry['attributes'] != int(after.FileAttributes)):
            raise ValueError('Source metadata changed while observing it')
        return _State(entry, size, _times(after))

    def _listing(self, parent):
        before = self._stat(parent)
        if before.entry['kind'] != 'directory':
            raise ValueError('Source parent is not a directory')
        names = tuple(self._api.iter_names(parent))
        if self._stat(parent) != before:
            raise ValueError('Source directory changed while enumerating it')
        # Native validates all leaves and casefold collisions before returning.
        return before, names, frozenset(names)

    def _named(self, parent, name, *, directory=None):
        state, _, names = self._listing(parent)
        present = name in names
        try:
            child = self._api.child(parent, name, directory=directory, writable=False)
        except OSError as error:
            if error.errno not in _MISSING:
                raise
            if present or self._stat(parent) != state:
                raise ValueError('Source changed while opening an enumerated name') from error
            raise _ConfirmedMissing('Source name is absent from its admitted parent: ' + name) from error
        try:
            if not present:
                raise ValueError('Source path is an alias or appeared after enumeration')
            observed = self._stat(child, state.entry['identity'])
            after, _, after_names = self._listing(parent)
            if after != state or name not in after_names:
                raise ValueError('Source directory changed while opening a child')
            if directory is True and observed.entry['kind'] != 'directory':
                raise ValueError('Source path traverses a non-directory')
            if directory is False and observed.entry['kind'] != 'file':
                raise ValueError('Source must be a regular file')
            return child, observed
        except BaseException:
            with self._api.owned(child):
                pass
            raise

    def _check_binding(self, parent, name, expected, *, file=False):
        try:
            child, current = self._named(parent, name, directory=not file)
        except FileNotFoundError as error:
            raise ValueError('Source binding disappeared during observation') from error
        with self._api.owned(child):
            # Directory contents may change between separate operations. Bind the
            # directory identity/security, and compare file timestamps as well.
            if current.entry != expected.entry or (file and current != expected):
                raise ValueError('Source binding changed during observation')

    def _check_root(self):
        self._ensure_open()
        for parent, name, expected in self._bindings:
            self._check_binding(parent, name, expected)

    def read(self, name, *, max_bytes):
        """Read one canonical relative file within the caller's byte allowance.

        FileNotFoundError means a confirmed absent name under an admitted parent.
        Unsafe names, aliases, observed disappearances and races are not absence.
        """
        relative(name)
        if type(max_bytes) is not int or not 0 <= max_bytes < 0xFFFFFFFF:
            raise ValueError('Source read requires a finite nonnegative byte bound')
        with self._lock, _final_reads(), ExitStack() as handles:
            self._check_root()
            parent, parents = self._root, []
            parts = name.split('/')
            for part in parts[:-1]:
                child, state = self._named(parent, part, directory=True)
                handles.enter_context(self._api.owned(child))
                parents.append((parent, part, state))
                parent = child
            child, before = self._named(parent, parts[-1], directory=False)
            handles.enter_context(self._api.owned(child))
            if not 0 <= before.size <= max_bytes:
                raise SourceLimitExceeded('file', 'File exceeds source per-file byte budget')
            data = self._api.read(child, before.size, limit=max_bytes)
            if self._stat(child, before.entry['parent_identity']) != before:
                raise ValueError('Source metadata changed while reading')
            self._check_binding(parent, parts[-1], before, file=True)
            for directory, part, state in parents:
                self._check_binding(directory, part, state)
            self._check_root()
            entry = deepcopy(before.entry)
            entry.update(size=len(data), sha256=hashlib.sha256(data).hexdigest())
            return FileObservation(data, entry, deepcopy(before.times))

    @contextmanager
    def _batch_child(self, parent, state, names, name, *, directory):
        # Membership is from this operation's complete scan. The retained child
        # and all parent/name bindings are checked again before any result exits.
        present = name in names
        try:
            child = self._api.child(parent, name, directory=directory, writable=False)
        except OSError as error:
            if error.errno not in _MISSING:
                raise
            if present:
                raise ValueError('Source changed while opening an enumerated name') from error
            raise _ConfirmedMissing('Source name is absent from its admitted parent: ' + name) from error
        with self._api.owned(child):
            if not present:
                raise ValueError('Source path is an alias or appeared after enumeration')
            observed = self._stat(child, state.entry['identity'])
            if observed.entry['kind'] != ('directory' if directory else 'file'):
                raise ValueError('Source child has an unexpected file type')
            yield child, observed

    def _kind(self, handle):
        # Ignored regular files need no content/stream/hardlink authority. Their
        # type must still be observed without following any reparse point.
        before = self._api.info(handle, self._api.Basic, 0)
        standard = self._api.info(handle, self._api.Standard, 1)
        after = self._api.info(handle, self._api.Basic, 0)
        if (_times(before) != _times(after)
                or before.FileAttributes != after.FileAttributes or standard.DeletePending):
            raise ValueError('Source type changed during observation')
        if before.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError('Document corpus contains symlinks or reparse points')
        return 'directory' if standard.Directory else 'file'

    def read_many(self, names, *, max_files, max_bytes, max_total_bytes):
        """Capture named files in one retained operation with independent bounds.

        FileNotFoundError is a whole-batch refusal, never per-item absence. Use
        observe(optional=...) to bind individually absent optional names instead.
        """
        with self.observe(names, max_files=max_files, max_bytes=max_bytes,
                          max_total_bytes=max_total_bytes) as result:
            return result

    @contextmanager
    def observe(self, names=(), *, select=None, optional=(), max_files,
                max_bytes, max_total_bytes):
        """Bind discovery, bytes and optional absence through a consumer operation.

        select discovers files recursively, rejecting every reparse point while
        ignoring unselected regular files, including their hardlinks/streams.
        max_files counts selected/required files; optional root leaves count only
        toward bytes. Complete namespaces and retained file/ancestor evidence are
        checked before yielding and again after the consumer finishes using bytes.
        """
        if (type(max_files) is not int or max_files < 0
                or type(max_bytes) is not int or not 0 <= max_bytes < 0xFFFFFFFF
                or type(max_total_bytes) is not int or max_total_bytes < 0
                or isinstance(names, (str, bytes))
                or (select is not None and not callable(select))
                or isinstance(optional, (str, bytes))):
            raise ValueError('Batch read requires independent file and byte bounds')
        requests = set()
        for name in names:
            relative(name)
            if name in requests:
                raise ValueError('Batch read contains duplicate source names')
            if len(requests) >= max_files:
                raise SourceLimitExceeded('files', 'Batch exceeds selected source file limit')
            requests.add(name)
        optional_names = set()
        for name in optional:
            relative(name)
            if '/' in name or name in optional_names or name in requests:
                raise ValueError('Optional sources require distinct root leaves')
            optional_names.add(name)
        prefixes = set()
        for name in requests:
            parts = name.split('/')
            for at in range(1, len(parts)):
                prefixes.add('/'.join(parts[:at]))
        if (requests | optional_names) & prefixes:
            raise ValueError('Batch source is both a file and a directory')
        with self._lock, _final_reads(), ExitStack() as handles:
            self._check_root()
            directories, bindings, selected, absent = {}, [], {}, set()
            if requests or optional_names or select is not None:
                directories[''] = (self._root, *self._listing(self._root))

            def admit(prefix, name, *, directory):
                parent, state, _, members = directories[prefix]
                child, before = handles.enter_context(
                    self._batch_child(parent, state, members, name, directory=directory))
                bindings.append((prefix, name, child, before))
                return child, before

            def directory(prefix, part):
                path = prefix + ('/' if prefix else '') + part
                if path not in directories:
                    child, before = admit(prefix, part, directory=True)
                    directories[path] = (child, *self._listing(child))
                    if self._stat(child, before.entry['parent_identity']) != before:
                        raise ValueError('Source directory changed during batch admission')
                return path

            def required(name):
                if name in selected:
                    return
                prefix, parts = '', name.split('/')
                for part in parts[:-1]:
                    prefix = directory(prefix, part)
                selected[name] = admit(prefix, parts[-1], directory=False)

            def check_types(prefix):
                parent, _, names, _ = directories[prefix]
                for name in names:
                    with self._api.owned(self._api.child(parent, name, writable=False, metadata_only=True)) as child:
                        self._kind(child)

            def verify():
                for _, _, child, before in bindings:
                    if self._stat(child, before.entry['parent_identity']) != before:
                        raise ValueError('Source metadata changed during batch observation')
                for parent, state, names, _ in directories.values():
                    after, after_names, _ = self._listing(parent)
                    if after != state or after_names != names:
                        raise ValueError('Source directory changed during batch observation')
                if select is not None:
                    for prefix in directories:
                        check_types(prefix)
                for prefix, name, _, before in bindings:
                    parent, state, _, members = directories[prefix]
                    with self._batch_child(parent, state, members, name,
                                           directory=before.entry['kind'] == 'directory') as (_, after):
                        if after != before:
                            raise ValueError('Source binding changed during batch observation')
                for name in absent:
                    parent, state, _, members = directories['']
                    try:
                        with self._batch_child(parent, state, members, name, directory=False):
                            raise ValueError('Optional source appeared during observation')
                    except _ConfirmedMissing:
                        pass
                for parent, state, names, _ in directories.values():
                    after, after_names, _ = self._listing(parent)
                    if after != state or after_names != names:
                        raise ValueError('Source directory changed during batch binding checks')
                self._check_root()

            try:
                for name in sorted(requests):
                    required(name)
                if select is not None:
                    pending = ['']
                    while pending:
                        prefix = pending.pop()
                        parent, _, names, _ = directories[prefix]
                        for name in names:
                            path = prefix + ('/' if prefix else '') + name
                            with self._api.owned(self._api.child(parent, name, writable=False, metadata_only=True)) as child:
                                kind = self._kind(child)
                            if kind == 'directory':
                                if select(path):
                                    raise ValueError('Selected source must be a regular file')
                                pending.append(directory(prefix, name))
                            elif select(path):
                                if path not in requests and len(requests) >= max_files:
                                    raise SourceLimitExceeded('files', 'Corpus exceeds selected source file limit')
                                requests.add(path)
                                required(path)
                for name in sorted(optional_names):
                    try:
                        required(name)
                    except _ConfirmedMissing:
                        absent.add(name)
            except _ConfirmedMissing:
                verify()
                raise

            if any(not 0 <= state.size <= max_bytes for _, state in selected.values()):
                raise SourceLimitExceeded('file', 'File exceeds source per-file byte budget')
            if sum(state.size for _, state in selected.values()) > max_total_bytes:
                raise SourceLimitExceeded('total', 'Batch exceeds source aggregate byte budget')
            result, captured = {}, 0
            for name, (child, before) in selected.items():
                data = self._api.read(child, before.size,
                                      limit=min(max_bytes, max_total_bytes - captured))
                captured += len(data)
                if self._stat(child, before.entry['parent_identity']) != before:
                    raise ValueError('Source metadata changed while reading batch')
                entry = deepcopy(before.entry)
                entry.update(size=len(data), sha256=hashlib.sha256(data).hexdigest())
                result[name] = FileObservation(data, entry, deepcopy(before.times))
            result.update({name: None for name in absent})
            verify()
            yield result
            verify()

    def check_path(self, name):
        """Check a pointer's exact components without reading its content.

        An absent final name or parent is permitted; observed reparse/alias/race
        failures still refuse. This does not grant content authority to pointers.
        """
        relative(name)
        with self._lock, _final_reads(), ExitStack() as handles:
            self._check_root()
            parent, bindings = self._root, []
            parts = name.split('/')
            try:
                for at, part in enumerate(parts):
                    child, before = self._named(parent, part,
                                                 directory=at < len(parts) - 1)
                    handles.enter_context(self._api.owned(child))
                    bindings.append((parent, part, before, at == len(parts) - 1))
                    parent = child
            except _ConfirmedMissing:
                pass
            for parent, part, before, file in bindings:
                self._check_binding(parent, part, before, file=file)
            self._check_root()

    def _probe_state(self, handle):
        # Metadata-only evidence for a link or its target. No target data read,
        # stream read, ACL read or security modification is authorized here.
        api = self._api
        before = api.info(handle, api.Basic, 0)
        standard = api.info(handle, api.Standard, 1)
        identity = _identity(api.info(handle, api.FileId, 18))
        after = api.info(handle, api.Basic, 0)
        if (_times(before) != _times(after)
                or before.FileAttributes != after.FileAttributes or standard.DeletePending):
            raise ValueError('Absence probe metadata changed')
        return (identity, _times(after), int(after.FileAttributes), bool(standard.Directory),
                int(standard.NumberOfLinks), int(standard.EndOfFile))

    def _reparse_data(self, handle):
        # FSCTL_GET_REPARSE_POINT reads only the retained link's reparse buffer.
        # MAXIMUM_REPARSE_DATA_BUFFER_SIZE is 16 KiB; no source content is read.
        api = self._api
        call = api.k.DeviceIoControl
        call.argtypes = [api.w.HANDLE, api.w.DWORD, ctypes.c_void_p, api.w.DWORD,
                         ctypes.c_void_p, api.w.DWORD, ctypes.POINTER(api.w.DWORD), ctypes.c_void_p]
        call.restype = api.w.BOOL
        data, used = ctypes.create_string_buffer(16384), api.w.DWORD()
        api._check(call(handle, 0x000900A8, None, 0, data, len(data),
                        ctypes.byref(used), None), 'FSCTL_GET_REPARSE_POINT')
        if not 8 <= used.value <= len(data):
            raise ValueError('Malformed symbolic-link buffer length')
        return data.raw[:used.value]

    def _target_absent(self, path, handles, checks, seen):
        """Walk target metadata only, never letting the OS follow a reparse."""
        api = self._api
        anchor = api.volume(path)
        parent = handles.enter_context(api.owned(api.volume_handle(anchor)))
        parts = path.parts[1:]
        current_path = Path(anchor)
        for at, name in enumerate(parts):
            parent_state, names, members = self._listing(parent)
            try:
                child = api.child(parent, name, writable=False, metadata_only=True)
            except OSError as error:
                if error.errno not in _MISSING or name in members:
                    raise
                def missing(parent=parent, state=parent_state, names=names, name=name):
                    after, after_names, _ = self._listing(parent)
                    if after != state or after_names != names:
                        raise ValueError('Absent target namespace changed')
                    try:
                        opened = api.child(parent, name, writable=False, metadata_only=True)
                    except OSError as probe:
                        if probe.errno in _MISSING:
                            return
                        raise
                    with api.owned(opened):
                        raise ValueError('Absent symbolic-link target appeared')
                checks.append(missing)
                missing()
                return True
            handles.enter_context(api.owned(child))
            if name not in members:
                raise ValueError('Symbolic-link target uses an alias or appeared')
            state = self._probe_state(child)
            data = self._reparse_data(child) if state[2] & FILE_ATTRIBUTE_REPARSE_POINT else None
            def binding(parent=parent, name=name, before=parent_state, names=names,
                        child=child, state=state, data=data):
                after, after_names, members = self._listing(parent)
                if after != before or after_names != names or name not in members:
                    raise ValueError('Symbolic-link target namespace changed')
                if self._probe_state(child) != state:
                    raise ValueError('Symbolic-link target metadata changed')
                with api.owned(api.child(parent, name, writable=False, metadata_only=True)) as reopened:
                    if self._probe_state(reopened) != state:
                        raise ValueError('Symbolic-link target binding changed')
                    if data is not None and self._reparse_data(reopened) != data:
                        raise ValueError('Symbolic-link target was retargeted')
            checks.append(binding)
            current_path = current_path / name
            if data is not None:
                identity = (state[0]['volume'], state[0]['file_id'])
                if identity in seen:
                    raise ValueError('Symbolic-link target cycle cannot prove absence')
                seen.add(identity)
                target = _symlink_target(current_path, data)
                if at < len(parts) - 1:
                    target = target.joinpath(*parts[at + 1:])
                return self._target_absent(target, handles, checks, seen)
            if at < len(parts) - 1 and not state[3]:
                return True  # a confirmed non-directory cannot contain the suffix
            if at < len(parts) - 1:
                directory = handles.enter_context(api.owned(
                    api.child(parent, name, directory=True, writable=False)))
                if self._probe_state(directory) != state:
                    raise ValueError('Symbolic-link target directory changed before traversal')
                parent = directory
        return False

    def read_optional(self, name, *, max_bytes, dangling_symlink_absent=False):
        """Read one optional file, with an explicit legacy dangling-link rule.

        Only this opt-in rule may inspect a symlink's target metadata. A missing
        local target is positive absence, including outside the declared root;
        no target content is read. Live/remote/unknown/unsafe targets refuse.
        """
        relative(name)
        if (type(max_bytes) is not int or not 0 <= max_bytes < 0xFFFFFFFF
                or type(dangling_symlink_absent) is not bool):
            raise ValueError('Optional read requires a finite byte bound and explicit absence policy')
        if '/' in name:
            raise ValueError('Optional absence requires a root leaf')
        if not dangling_symlink_absent:
            try:
                return self.read(name, max_bytes=max_bytes)
            except FileNotFoundError:
                return None
        with self._lock, _final_reads(), ExitStack() as handles:
            self._check_root()
            parent_state, names, members = self._listing(self._root)
            try:
                child = self._api.child(self._root, name, writable=False)
            except OSError as error:
                if error.errno not in _MISSING or name in members:
                    raise
                if self._listing(self._root)[:2] != (parent_state, names):
                    raise ValueError('Optional source namespace changed') from error
                self._check_root()
                return None
            handles.enter_context(self._api.owned(child))
            if name not in members:
                raise ValueError('Optional source is an alias or appeared')
            state = self._probe_state(child)
            if not state[2] & FILE_ATTRIBUTE_REPARSE_POINT:
                return self.read(name, max_bytes=max_bytes)
            if state[4] != 1:
                raise ValueError('Multiply linked symbolic link cannot prove absence')
            data = self._reparse_data(child)
            target = _symlink_target(self._path / name, data)
            checks = []
            identity = (state[0]['volume'], state[0]['file_id'])
            absent = self._target_absent(target, handles, checks, {identity})
            for check in reversed(checks):
                check()
            if (self._probe_state(child) != state or self._reparse_data(child) != data
                    or self._listing(self._root)[:2] != (parent_state, names)):
                raise ValueError('Optional symbolic-link source changed')
            with self._api.owned(self._api.child(self._root, name, writable=False)) as reopened:
                if self._probe_state(reopened) != state or self._reparse_data(reopened) != data:
                    raise ValueError('Optional symbolic-link binding changed')
            self._check_root()
            if not absent:
                raise ValueError('Live symbolic-link source is not authorized')
            return None

    def files(self, *, select, max_files):
        """Return selected relative files from retained directory discovery.

        The limit counts selected files only. Incidental files and directories
        have no new entry cap. Scans complete before any names reach the caller;
        no suspended iterator shares a native directory enumeration cursor.
        """
        if not callable(select) or type(max_files) is not int or max_files < 0:
            raise ValueError('Discovery requires a selector and nonnegative file bound')
        with self._lock, _final_reads(), ExitStack() as handles:
            self._check_root()
            result, pending, directories, bindings = [], [(self._root, '')], [], []
            while pending:
                parent, prefix = pending.pop()
                state, names, _ = self._listing(parent)
                directories.append((parent, state, names))
                for name in names:
                    # The exact name came from this retained parent's completed
                    # scan. Do not enumerate again per child; check the whole
                    # directory and its bindings before returning discovery.
                    with ExitStack() as opened:
                        child = opened.enter_context(self._api.owned(
                            self._api.child(parent, name, writable=False)))
                        child_state = self._stat(child, state.entry['identity'])
                        path = prefix + name
                        if child_state.entry['kind'] == 'directory':
                            handles.enter_context(opened.pop_all())
                            pending.append((child, path + '/'))
                            bindings.append((parent, name, child_state))
                        elif select(path):
                            if len(result) >= max_files:
                                raise ValueError('Corpus exceeds selected source file limit')
                            result.append(path)
            for directory, state, names in directories:
                after, after_names, _ = self._listing(directory)
                if after != state or after_names != names:
                    raise ValueError('Source directory changed during discovery')
            for parent, name, state in bindings:
                self._check_binding(parent, name, state)
            self._check_root()
            return sorted(result)


@contextmanager
def open_read_root(supplied_root):
    """Admit a supplied absolute drive path without resolving any component away.

    Fixed local NTFS is the only admitted filesystem. Unsupported platforms and
    volumes retain FeatureUnavailable; other native failures retain OSError or
    become ValueError for a nonfinal observation. The supplied root must be below
    the drive anchor. Every ancestor stays open until this context exits.
    """
    require_platform()
    path = validate_root_path(supplied_root)
    with ExitStack() as handles:
        with _final_reads():
            root = ReadRoot(Native(), handles, path)
        try:
            yield root
        finally:
            root._close(handles)


def validate_root_path(supplied_root):
    """Validate the supplied lexical spelling without resolving or opening it."""
    supplied = os.fspath(supplied_root)
    if not absolute_path(supplied) or not supplied[3:]:
        raise ValueError('Source root must be an absolute directory below a drive anchor')
    # Validate the supplied spelling, including dot/alias/ADS components, before
    # opening anything. Do not call resolve(), absolute(), glob() or path.open().
    relative(supplied[3:].replace('\\', '/'))
    return Path(supplied)
