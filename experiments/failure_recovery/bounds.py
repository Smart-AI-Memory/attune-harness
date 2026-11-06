"""Finite regular-file collection for the owned synthetic fixture."""

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat

from attune_harness.review_contract import parse_json

MAX_FILE = 32768
MAX_TREE = 262144
MAX_ENTRIES = 32
MAX_DEPTH = 4
MAX_EVENTS = 128
MAX_JOURNAL = 131072
MAX_BLOBS = 4194304
MAX_SECONDS = 120
MAX_SAMPLES = 8192
MAX_EVIDENCE = 131072
MAX_RETAINED_FILE = 2097152
MAX_RUN_FILES = 4096
MAX_RUN_BYTES = 67108864


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def directory(path, *, create=False):
    path = Path(path)
    if not path.is_absolute() or path != path.resolve():
        raise ValueError("Choose an absolute canonical directory without links")
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Directory ancestors must not be links")
    if create:
        path.mkdir(exist_ok=False)
    elif not path.is_dir():
        raise ValueError("Directory is missing")
    return path


def relative(name):
    if (not isinstance(name, str) or len(name) > 200 or any(c in name for c in ("\\", ":", "\x00"))
            or not name or PurePosixPath(name).is_absolute()
            or any(p in ("", ".", "..") for p in name.split("/"))):
        raise ValueError("Invalid relative collection path")
    return name


def external_directory(path, app, *, create=False):
    path, app = Path(path), directory(app)
    if path.is_relative_to(app) or app.is_relative_to(path):
        raise ValueError("Collection storage must be disjoint from the checkout")
    return directory(path, create=create)


def read_bytes(path, maximum=MAX_FILE):
    path = Path(path)
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Collection refuses links")
    ancestors = [(parent, parent.lstat()) for parent in path.parents]
    directory_identity = lambda s: (s.st_dev, s.st_ino, s.st_mode)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    directory_fds = []
    try:
        if os.open in os.supports_dir_fd and hasattr(os, "O_DIRECTORY") and hasattr(os, "O_NOFOLLOW"):
            absolute = path.absolute()
            directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            directory_fds.append(os.open(absolute.anchor, directory_flags))
            for part in absolute.parts[1:-1]:
                directory_fds.append(os.open(part, directory_flags, dir_fd=directory_fds[-1]))
            fd = os.open(absolute.name, flags, dir_fd=directory_fds[-1])
        else:
            # Windows uses before/after identity checks, not a race-proof OS fence.
            fd = os.open(path, flags)
    finally:
        for directory_fd in reversed(directory_fds):
            os.close(directory_fd)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
            raise ValueError("Collection requires a bounded regular file with one link")
        chunks = []
        size = 0
        while size <= maximum:
            chunk = os.read(fd, maximum + 1 - size)
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        data = b"".join(chunks)
        after = os.fstat(fd)
        current = path.lstat()
        identity = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_nlink)
        if (len(data) != before.st_size or len(data) > maximum or identity(before) != identity(after)
                or identity(after) != identity(current)
                or any(directory_identity(parent.lstat()) != directory_identity(previous) for parent, previous in ancestors)):
            raise ValueError("File changed during collection")
        return data
    finally:
        os.close(fd)


def read_json(path, maximum=MAX_FILE):
    return parse_json(read_bytes(path, maximum).decode("utf-8"), maximum)


def write_bytes(path, data, maximum=MAX_FILE):
    if len(data) > maximum:
        raise ValueError("Collection output exceeds its bound")
    with Path(path).open("xb") as stream:
        stream.write(data)


def write_json(path, value, maximum=MAX_FILE):
    write_bytes(path, encoded(value), maximum)


def capture(root):
    """Snapshot bounded files/directories; Git internals are explicitly unobserved."""
    root = directory(root)
    facts, contents = {}, {}
    total = 0

    def walk(folder, depth):
        nonlocal total
        if depth > MAX_DEPTH:
            raise ValueError("Collection depth exhausted")
        with os.scandir(folder) as entries:
            names = []
            for entry in entries:
                if folder == root and entry.name == ".git":
                    continue
                names.append(entry.name)
                if len(facts) + len(names) > MAX_ENTRIES:
                    raise ValueError("Collection entry count exhausted")
        for name in sorted(names):
            path = folder / name
            key = relative(path.relative_to(root).as_posix())
            metadata = path.lstat()
            if stat.S_ISDIR(metadata.st_mode):
                facts[key] = {"kind": "directory", "mode": stat.S_IMODE(metadata.st_mode)}
                walk(path, depth + 1)
            else:
                data = read_bytes(path)
                total += len(data)
                if total > MAX_TREE:
                    raise ValueError("Collection byte budget exhausted")
                facts[key] = {"kind": "file", "mode": stat.S_IMODE(metadata.st_mode),
                              "bytes": len(data), "sha256": sha(data)}
                contents[key] = data
            if len(facts) > MAX_ENTRIES:
                raise ValueError("Collection entry count exhausted")

    walk(root, 0)
    return facts, contents


def seal(root):
    """Hash retained collection files without following links or Git internals."""
    root = directory(root)
    hashes = {}
    total = 0
    entries_seen = 0

    def walk(folder, depth):
        nonlocal total, entries_seen
        if depth > 16:
            raise ValueError("Retention depth exhausted")
        with os.scandir(folder) as entries:
            for entry in entries:
                path = folder / entry.name
                if entry.name == ".git" and folder.name == "app":
                    continue
                entries_seen += 1
                if entries_seen > MAX_RUN_FILES:
                    raise ValueError("Retention entry budget exhausted")
                if entry.is_dir(follow_symlinks=False):
                    walk(path, depth + 1)
                else:
                    data = read_bytes(path, MAX_RETAINED_FILE)
                    total += len(data)
                    if total > MAX_RUN_BYTES or len(hashes) >= MAX_RUN_FILES:
                        raise ValueError("Retention budget exhausted")
                    hashes[path.relative_to(root).as_posix()] = sha(data)
    walk(root, 0)
    write_json(root / "retained.json", {"sha256": hashes, "bytes": total}, maximum=MAX_RETAINED_FILE)
    return hashes
