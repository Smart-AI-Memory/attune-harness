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
import hashlib
import os
from pathlib import Path
from threading import RLock

from .recovery import UnresolvedOperation
from .windows_effects import Native, absolute_path, relative, require_platform

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


@contextmanager
def _final_reads():
    try:
        yield
    except UnresolvedOperation as error:
        raise ValueError('Windows source observation did not complete: ' + str(error)) from error


class ReadRoot:
    """One admitted root and its retained ancestor bindings. Use open_read_root."""

    def __init__(self, api, stack, path):
        self._api, self._closed = api, False
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
            raise FileNotFoundError('Source name is absent from its admitted parent: ' + name) from error
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
    supplied = os.fspath(supplied_root)
    if not absolute_path(supplied) or not supplied[3:]:
        raise ValueError('Source root must be an absolute directory below a drive anchor')
    # Validate the supplied spelling, including dot/alias/ADS components, before
    # opening anything. Do not call resolve(), absolute(), glob() or path.open().
    relative(supplied[3:].replace('\\', '/'))
    path = Path(supplied)
    with ExitStack() as handles:
        with _final_reads():
            root = ReadRoot(Native(), handles, path)
        try:
            yield root
        finally:
            root._closed = True
