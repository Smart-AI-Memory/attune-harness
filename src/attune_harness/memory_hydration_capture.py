"""Complete, read-only source observations for the approved hydration writer.

The yielded private snapshot is provisional until every observation context exits
successfully. No publication or public success may occur inside this context.
Apply must compare a fresh complete observation before its later Redis switch.
"""

from contextlib import ExitStack, contextmanager
from copy import deepcopy
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat

from .memory_hydration_contract import validate_sources
from .memory_reader import (
    FILE_LIMIT, SIDECARS, SNAPSHOT_BYTES, SNAPSHOT_FILES, NativeReader, _windows, roots_config,
)
from .review_contract import digest


def _identity(detail):
    return (detail.st_dev, detail.st_ino, detail.st_mode)


def _state(detail):
    return (*_identity(detail), detail.st_nlink, detail.st_size,
            detail.st_mtime_ns, detail.st_ctime_ns)


def _normalized(source):
    value = dict(source)
    path = PurePosixPath(value['path'].replace('\\', '/')).as_posix()
    value['path'] = '' if path == '.' else path
    if value['layer'] == 'lesson' and not path.endswith('.md'):
        raise ValueError('Hydration lessons require one explicit Markdown file')
    return value


def _matches(source, name):
    base = source['path']
    if source['layer'] == 'lesson':
        return name == base
    if not name.endswith('.md'):
        return False
    if source['layer'] == 'rule':
        return not base or name.startswith(base + '/')
    return name.rpartition('/')[0] == base


def _descend(sources, name):
    for source in sources:
        base = (source['path'].rpartition('/')[0] if source['layer'] == 'lesson'
                else source['path'])
        if (name == base or base.startswith(name + '/')
                or (source['layer'] == 'rule' and (not base or name.startswith(base + '/')))):
            return True
    return False


class _PosixBatch:
    """Retained namespaces plus the existing native one-file byte primitive."""

    def __init__(self, reader, root, sources, stack, files, size, check_budget):
        self.reader, self.root, self.sources = reader, root, sources
        self.stack, self.files_left, self.bytes_left = stack, files, size
        self.check_budget = check_budget
        self.bindings, self.directories, self.selected, self.absent = [], {}, {}, set()
        self.items = {}
        path = Path(root['path'])
        parent = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        stack.callback(os.close, parent)
        for part in path.parts[1:]:
            parent = self._open_directory(parent, part)
        self._remember_directory('', parent)
        for source in sources:
            if source['layer'] != 'lesson':
                self._directory(source['path'])
        for source in sources:
            if source['layer'] == 'lesson':
                self._read(source['path'])
        pending = ['']
        while pending:
            self.check_budget()
            prefix = pending.pop()
            parent, _, names = self.directories[prefix]
            for name in names:
                self.check_budget()
                relative = prefix + ('/' if prefix else '') + name
                detail = os.stat(name, dir_fd=parent, follow_symlinks=False)
                chosen = any(_matches(source, relative) for source in sources)
                descend = _descend(sources, relative)
                if stat.S_ISLNK(detail.st_mode) and (chosen or descend):
                    raise ValueError('Hydration source traverses a symbolic link')
                if stat.S_ISDIR(detail.st_mode):
                    if chosen:
                        raise ValueError('Selected hydration source must be a regular file')
                    if descend:
                        self._directory(relative)
                        pending.append(relative)
                elif chosen:
                    self._read(relative)
        for name in SIDECARS:
            self._read(name, optional=True)
        self.verify()

    def _open_directory(self, parent, name):
        self.check_budget()
        before = os.stat(name, dir_fd=parent, follow_symlinks=False)
        child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        self.stack.callback(os.close, child)
        if _identity(os.fstat(child)) != _identity(before):
            raise ValueError('Hydration source directory changed during admission')
        self.bindings.append((parent, name, child, _identity(before)))
        return child

    def _remember_directory(self, name, fd):
        before = _state(os.fstat(fd))
        members = tuple(sorted(os.listdir(fd)))
        if _state(os.fstat(fd)) != before:
            raise ValueError('Hydration source directory changed during enumeration')
        self.directories[name] = (fd, before, members)

    def _directory(self, name):
        prefix = ''
        for part in name.split('/') if name else ():
            relative = prefix + ('/' if prefix else '') + part
            if relative not in self.directories:
                fd = self._open_directory(self.directories[prefix][0], part)
                self._remember_directory(relative, fd)
            prefix = relative
        return self.directories[prefix][0]

    def _read(self, name, *, optional=False):
        self.check_budget()
        if name in self.items:
            return
        prefix, _, leaf = name.rpartition('/')
        parent = self._directory(prefix)
        try:
            before = os.stat(leaf, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            if not optional:
                raise
            self.absent.add(name)
            self.items[name] = None
            return
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ValueError('Hydration source must be a regular file without hard links')
        if len(self.selected) >= self.files_left:
            raise ValueError('Hydration source exceeds 4096 logical files')
        if before.st_size > min(FILE_LIMIT, self.bytes_left):
            raise ValueError('Hydration source exceeds file or aggregate byte limit')
        # The existing POSIX primitive requires a positive limit. At aggregate
        # zero, a one-byte probe distinguishes an empty file from added content.
        allowance = max(1, min(FILE_LIMIT, self.bytes_left))
        data, version, mtime = self.reader._capture(self.root, name, limit=allowance)
        self.check_budget()
        expected = digest(dict(sha256=hashlib.sha256(data).hexdigest(), device=before.st_dev,
                               inode=before.st_ino, mtime_ns=before.st_mtime_ns,
                               ctime_ns=before.st_ctime_ns, size=before.st_size))
        if version != expected:
            raise ValueError('Hydration source differs from its admitted file')
        if len(data) > self.bytes_left:
            raise ValueError('Hydration source exceeds aggregate byte limit')
        self.bytes_left -= len(data)
        self.selected[name] = (parent, leaf, _state(before))
        self.items[name] = (data, version, mtime)

    def verify(self):
        self.check_budget()
        for parent, name, child, identity in self.bindings:
            self.check_budget()
            if (_identity(os.fstat(child)) != identity
                    or _identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != identity):
                raise ValueError('Hydration source directory binding changed')
        for fd, before, names in self.directories.values():
            self.check_budget()
            if _state(os.fstat(fd)) != before or tuple(sorted(os.listdir(fd))) != names:
                raise ValueError('Hydration source inventory changed')
        for parent, name, before in self.selected.values():
            self.check_budget()
            if _state(os.stat(name, dir_fd=parent, follow_symlinks=False)) != before:
                raise ValueError('Hydration source file changed')
        root = self.directories[''][0]
        for name in self.absent:
            self.check_budget()
            try:
                os.stat(name, dir_fd=root, follow_symlinks=False)
            except FileNotFoundError:
                continue
            raise ValueError('Optional hydration source appeared')

    def evidence(self):
        return dict(ancestors=[list(identity) for _, _, _, identity in self.bindings],
                    directories={name: dict(state=list(before), names=list(names))
                                 for name, (_, before, names) in self.directories.items()})


@contextmanager
def capture_sources(config, sources, *, check_budget=lambda: None):
    """Yield a provisional private snapshot; every clean exit verifies all roots.

    This captures bytes, identity and complete inventories. Parsing, complete
    secret checks and projection are separate pure consumers, not Redis effects.
    Keep all consumer work read-only until the context has exited successfully.
    """
    check_budget()
    original_config, original_sources = deepcopy(config), deepcopy(sources)
    reader = NativeReader(roots_config(original_config))
    mappings = validate_sources(original_sources, {root['id'] for root in reader.config['roots']})
    mappings = sorted((_normalized(source) for source in mappings),
                      key=lambda source: tuple(source[key] for key in ('root_id', 'layer', 'corpus', 'path')))
    roots = {root['id']: root for root in reader.config['roots']}
    for source in mappings:
        if roots[source['root_id']]['tier'] not in ('personal', 'curated'):
            raise ValueError('Hydration sources require authorized personal or curated roots')
    grouped = {rid: [source for source in mappings if source['root_id'] == rid]
               for rid in sorted({source['root_id'] for source in mappings})}
    entries, observations, verifiers = {}, {}, []
    remaining_files, remaining_bytes = SNAPSHOT_FILES, SNAPSHOT_BYTES
    with ExitStack() as contexts:
        for rid, selectors in grouped.items():
            check_budget()
            root = reader._root(rid)
            if _windows():
                opened = contexts.enter_context(reader._native_root(root))
                required = [s['path'] for s in selectors if s['layer'] == 'lesson']
                directories = sorted({s['path'] for s in selectors if s['layer'] != 'lesson' and s['path']})
                def selected(name, selectors=selectors):
                    check_budget()
                    return any(_matches(source, name) for source in selectors)
                def descend(name, selectors=selectors):
                    check_budget()
                    return _descend(selectors, name)
                packet = contexts.enter_context(opened.observe(
                    names=sorted(set(required)), required_dirs=directories,
                    select=selected, descend=descend,
                    optional=SIDECARS, max_files=remaining_files, max_present_files=remaining_files,
                    max_bytes=FILE_LIMIT, max_total_bytes=remaining_bytes, checkpoint=True))
                items = {name: (reader._native_capture(value) if value is not None else None)
                         for name, value in packet.items()}
                evidence, verify = packet.evidence, packet.verify
            else:
                handles = contexts.enter_context(ExitStack())
                packet = _PosixBatch(reader, root, selectors, handles, remaining_files,
                                     remaining_bytes, check_budget)
                items, evidence, verify = packet.items, packet.evidence(), packet.verify
                contexts.callback(verify)
            present = sum(value is not None for value in items.values())
            size = sum(len(value[0]) for value in items.values() if value is not None)
            remaining_files -= present
            remaining_bytes -= size
            if remaining_files < 0 or remaining_bytes < 0:
                raise ValueError('Hydration source exceeds aggregate file or byte limit')
            observations[rid] = deepcopy(evidence)
            verifiers.append(verify)
            for name, value in items.items():
                entries[(rid, name)] = dict(root_id=rid, path=name, present=value is not None,
                                           data=value[0] if value else None,
                                           version=value[1] if value else 'absent',
                                           mtime_ns=value[2] if value else None)
        inventories = [sorted(name for rid, name in entries
                              if rid == source['root_id'] and _matches(source, name))
                       for source in mappings]
        # Explicitly recheck early roots after later roots have been captured.
        for verify in verifiers:
            check_budget()
            verify()
            check_budget()
        if config != original_config or sources != original_sources:
            raise ValueError('Hydration input configuration changed during capture')
        snapshot = dict(binding=reader.binding, roots=deepcopy(reader.config['roots']),
                        sources=mappings, inventories=inventories, entries=entries,
                        observations=observations, files=SNAPSHOT_FILES - remaining_files,
                        bytes=SNAPSHOT_BYTES - remaining_bytes)
        preserved = deepcopy(snapshot)
        yield snapshot
        check_budget()
        if snapshot != preserved or config != original_config or sources != original_sources:
            raise ValueError('Hydration captured inputs changed during use')
        for verify in verifiers:
            check_budget()
            verify()
            check_budget()
