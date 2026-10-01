"""Bounded source bytes retained for shared, offline consultation contracts.

Validation checks the retained bytes only. Editing or removing the original
checkout cannot change what a participant was asked to review.
"""

import hashlib
import os
import stat
from contextlib import ExitStack, contextmanager
from pathlib import Path, PurePosixPath, PureWindowsPath

from .review_contract import digest, fields

MAX_FILES = 32
MAX_BYTES = 131_072
_METADATA = {'.git', '.hg', '.svn', '.attune-harness'}


def _path(value):
    if not isinstance(value, str) or not value or '\\' in value or '\x00' in value:
        raise ValueError('Source paths must be explicit relative POSIX file paths')
    path = PurePosixPath(value)
    if (path.is_absolute() or PureWindowsPath(value).drive or str(path) != value
            or any(part in ('.', '..', '') for part in value.split('/'))
            or any(part.casefold() in _METADATA for part in path.parts)):
        raise ValueError('Source paths must be relative and outside repository metadata')
    return path


def _root(value):
    if not isinstance(value, str) or not value or '\x00' in value:
        raise ValueError('Snapshot root must be an absolute path')
    root = Path(value)
    if (not root.is_absolute() or str(root) != value or '..' in root.parts
            or any(part.casefold() in _METADATA for part in root.parts)):
        raise ValueError('Snapshot root must be canonical and outside repository metadata')
    return root


def _directory(parent, name):
    """Open one directory leaf relative to an already owned descriptor."""
    return os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)


def _read_posix(root, name, limit):
    parts = _path(name).parts
    with ExitStack() as stack:
        parent = root
        for part in parts[:-1]:
            parent = _directory(parent, part)
            stack.callback(os.close, parent)
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        stack.callback(os.close, fd)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError('Source must be a bounded regular file')
        chunks, total = [], 0
        while True:
            block = os.read(fd, min(65536, limit + 1 - total))
            if not block:
                break
            chunks.append(block)
            total += len(block)
            if total > limit:
                raise ValueError('Source exceeds aggregate byte bound')
        after = os.fstat(fd)
        if any(getattr(before, key) != getattr(after, key) for key in
               ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns')):
            raise ValueError('Source changed while reading')
        return b''.join(chunks)


@contextmanager
def _posix_reader(root):
    # Start at the filesystem anchor: even root's ancestors must be opened
    # without following links. All later operations use the retained root fd.
    with ExitStack() as stack:
        current = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        stack.callback(os.close, current)
        for part in root.parts[1:]:
            current = _directory(current, part)
            stack.callback(os.close, current)
        yield lambda name, limit: _read_posix(current, name, limit)


@contextmanager
def _windows_reader(root):
    """Use the existing fixed-local-NTFS, handle-relative eligibility profile."""
    from .windows_effects import Native

    native = Native()
    anchor = native.volume(root)
    with ExitStack() as stack:
        current = stack.enter_context(native.owned(native.volume_handle(anchor)))
        for part in root.parts[1:]:
            current = stack.enter_context(native.owned(
                native.canonical_child(current, part, directory=True)))
            entry, _, _ = native.metadata(current)
            if entry['kind'] != 'directory':
                raise ValueError('Source root traverses a non-directory')
        root_handle = current

        def read(name, limit):
            with ExitStack() as handles:
                parent = root_handle
                parts = _path(name).parts
                for part in parts[:-1]:
                    parent = handles.enter_context(native.owned(
                        native.canonical_child(parent, part, directory=True)))
                    entry, _, _ = native.metadata(parent)
                    if entry['kind'] != 'directory':
                        raise ValueError('Source parent is not a directory')
                handle = handles.enter_context(native.owned(
                    native.canonical_child(parent, parts[-1], directory=False)))
                before, size, _ = native.metadata(handle)
                if before['kind'] != 'file':
                    raise ValueError('Source must be a regular file')
                raw = native.read(handle, size, limit=limit)
                after, after_size, _ = native.metadata(handle)
                if before != after or size != after_size:
                    raise ValueError('Source metadata changed while reading')
                return raw

        yield read


def capture(root: Path, paths: list[str]) -> dict:
    """Capture 1–32 named regular UTF-8 files without following source symlinks."""
    if not isinstance(paths, list) or not 1 <= len(paths) <= MAX_FILES:
        raise ValueError('Select 1–32 explicit source file paths')
    for name in paths:
        _path(name)
    if len(set(paths)) != len(paths):
        raise ValueError('Source paths must be unique')
    root = Path(root).absolute()
    _root(str(root))
    if any(part.is_symlink() for part in (root, *root.parents)):
        raise ValueError('Source root cannot traverse a symlink')
    if not root.is_dir():
        raise ValueError('Source root must be an existing directory')
    files, total = {}, 0
    reader = _windows_reader if os.name == 'nt' else _posix_reader
    try:
        with reader(root) as read:
            for name in paths:
                raw = read(name, MAX_BYTES - total)
                text = raw.decode('utf-8')
                total += len(raw)
                files[name] = {'text': text, 'sha256': hashlib.sha256(raw).hexdigest()}
    except OSError as exc:
        raise ValueError(f'Source open refused (missing, symlink or ineligible entry): {exc}') from exc
    return {'root': str(root), 'files': files, 'digest': digest(files)}


def validate(snapshot: dict) -> dict:
    """Check a retained snapshot without reopening its original source files."""
    fields(snapshot, ('root', 'files', 'digest'))
    _root(snapshot['root'])
    files = snapshot['files']
    if not isinstance(files, dict) or not 1 <= len(files) <= MAX_FILES:
        raise ValueError('Snapshot requires 1–32 source files')
    total = 0
    for name, item in files.items():
        _path(name)
        fields(item, ('text', 'sha256'))
        if not isinstance(item['text'], str):
            raise ValueError('Snapshot source must be UTF-8 text')
        try:
            raw = item['text'].encode('utf-8')
        except UnicodeError as exc:
            raise ValueError('Snapshot source must be UTF-8 text') from exc
        total += len(raw)
        if total > MAX_BYTES:
            raise ValueError('Snapshot exceeds aggregate source byte bound')
        if item['sha256'] != hashlib.sha256(raw).hexdigest():
            raise ValueError(f'Snapshot source digest changed: {name}')
    if snapshot['digest'] != digest(files):
        raise ValueError('Snapshot digest changed')
    return snapshot
