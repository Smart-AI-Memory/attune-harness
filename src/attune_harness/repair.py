"""Host-controlled existing-file replacements in an exclusively owned POSIX checkout."""
from contextlib import contextmanager
from dataclasses import asdict
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
from uuid import uuid4
from .features import FeatureUnavailable
from .review_contract import fields, parse_json, versioned, digest
from .recovery import UnresolvedOperation

PROFILE = 'posix-existing-utf8-v1'
MAX_FILE = 65536
MAX_TREE = 16 * 1024 * 1024
PROTECTED = {'.git', '.hg', '.svn', '.attune-harness', '.claude', '.codex', '.agents'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def relative(value):
    if (not isinstance(value, str) or not value or '\\' in value or '\x00' in value or
            value.startswith('/') or str(PurePosixPath(value)) != value or
            any(p in ('.', '..', '') for p in value.split('/'))):
        raise ValueError('Replacement paths must be canonical relative paths')
    return value


def identity(st):
    return {'device': st.st_dev, 'inode': st.st_ino}


@contextmanager
def root_handle(plan):
    if os.name != 'posix' or not hasattr(os, 'O_NOFOLLOW'):
        raise FeatureUnavailable('Repair effects require the qualified POSIX handle profile')
    root = Path(plan['root'])
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError('Checkout cannot traverse a symlink')
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        if identity(os.fstat(fd)) != plan['root_identity']:
            raise ValueError('Checkout identity changed')
        yield fd
    finally:
        os.close(fd)


@contextmanager
def parent_handle(root_fd, path):
    parts = relative(path).split('/')
    fd = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd, parts[-1]
    finally:
        os.close(fd)


def read_file(parent, name, *, limit=MAX_TREE):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size > limit:
            raise ValueError('Repair requires bounded regular files with one hard link')
        chunks, size = [], 0
        while True:
            block = os.read(fd, min(65536, limit + 1 - size))
            if not block:
                break
            chunks.append(block)
            size += len(block)
            if size > limit:
                raise ValueError('File exceeds repair byte limit')
        after = os.fstat(fd)
        if any(getattr(after, k) != getattr(st, k) for k in ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')):
            raise ValueError('File changed while reading')
        return b''.join(chunks), stat.S_IMODE(st.st_mode)
    finally:
        os.close(fd)


def snapshot(plan):
    result, total = {}, 0
    def walk(fd, prefix=''):
        nonlocal total
        for name in sorted(os.listdir(fd)):
            path = prefix + name
            st = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(st.st_mode):
                if len(result) >= 1000:
                    raise ValueError('Checkout exceeds bounded repair profile')
                result[path + '/'] = {'kind': 'directory', 'mode': stat.S_IMODE(st.st_mode)}
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                try:
                    walk(child, path + '/')
                finally:
                    os.close(child)
            else:
                raw, mode = read_file(fd, name)
                total += len(raw)
                if len(result) >= 1000 or total > MAX_TREE:
                    raise ValueError('Checkout exceeds bounded repair profile')
                result[path] = {'sha256': sha(raw), 'mode': mode}
    with root_handle(plan) as fd:
        walk(fd)
    return result


def validate_probe(root, allowed, probe, *, check_executable=True):
    """Shared bounded trusted-check contract; no command is run here."""
    fields(probe, ('argv', 'cwd', 'timeout', 'max_output_bytes', 'environment', 'oracle_paths'))
    argv = probe['argv']
    if (not isinstance(argv, list) or not 1 <= len(argv) <= 32 or
            any(not isinstance(v, str) or '\x00' in v or len(v) > 4096 for v in argv) or
            not Path(argv[0]).is_absolute() or (check_executable and not Path(argv[0]).is_file())):
        raise ValueError('Probe requires a bounded argv with an existing absolute executable')
    if (Path(argv[0]).resolve() if check_executable else Path(argv[0])).is_relative_to(root.resolve() if check_executable else root):
        raise ValueError('Probe executable must be outside editable checkout')
    if probe['cwd'] != '.':
        raise ValueError('Probe cwd must be the accepted checkout root')
    if type(probe['timeout']) not in (int, float) or not 0 < probe['timeout'] <= 120:
        raise ValueError('Probe timeout must be in (0,120] seconds')
    if type(probe['max_output_bytes']) is not int or not 1 <= probe['max_output_bytes'] <= 65536:
        raise ValueError('Probe output budget must be in 1..65536')
    env = probe['environment']
    if (not isinstance(env, dict) or set(env) - {'PATH', 'LANG', 'LC_ALL', 'PYTHONDONTWRITEBYTECODE', 'PYTHONNOUSERSITE'} or
            any(not isinstance(v, str) or '\x00' in v for v in env.values()) or
            env.get('PYTHONDONTWRITEBYTECODE') != '1' or env.get('PYTHONNOUSERSITE') != '1'):
        raise ValueError('Probe requires a frozen minimal environment and disabled Python bytecode/user-site')
    oracles = probe['oracle_paths']
    if not isinstance(oracles, list) or not oracles or len(oracles) > 20:
        raise ValueError('Declare protected oracle paths before worker execution')
    for name in oracles:
        relative(name)
        if name in allowed:
            raise ValueError('Acceptance oracle cannot be in replacement scope')


def freeze(root, allowed, probe, state_directory):
    root = Path(root).absolute()
    state = Path(state_directory).absolute()
    if state.is_relative_to(root) or root.is_relative_to(state):
        raise ValueError('Repair checkout and task state must be disjoint')
    if not (root / '.git').is_dir() or (root / '.git').is_symlink():
        raise ValueError('Repair requires a dedicated checkout with local .git directory')
    if not isinstance(allowed, list) or not 1 <= len(allowed) <= 20 or len(set(allowed)) != len(allowed):
        raise ValueError('Accept 1–20 distinct replacement paths')
    for name in allowed:
        relative(name)
        if any(p in PROTECTED for p in PurePosixPath(name).parts):
            raise ValueError('Protected state/metadata cannot be replaced')
    validate_probe(root, allowed, probe)
    argv, oracles = probe['argv'], probe['oracle_paths']
    plan = {'profile': PROFILE, 'root': str(root), 'root_identity': identity(root.stat()),
            'allowed': list(allowed), 'probe': copy.deepcopy(probe),
            'executable_sha256': sha(Path(argv[0]).read_bytes())}
    plan['before'] = snapshot(plan)
    for name in (*allowed, *oracles):
        if name not in plan['before']:
            raise ValueError('Accepted paths must be existing regular files')
    plan['inputs'] = {}
    with root_handle(plan) as fd:
        for name in allowed:
            with parent_handle(fd, name) as (parent, leaf):
                raw, _ = read_file(parent, leaf, limit=MAX_FILE)
                plan['inputs'][name] = raw.decode('utf-8')
    return plan


def decode_patch(raw, plan):
    value = parse_json(raw, 1048576)
    fields(value, ('schema_version', 'replacements'))
    versioned(value)
    items = value['replacements']
    if not isinstance(items, list) or not 1 <= len(items) <= 20:
        raise ValueError('Patch needs 1–20 replacements')
    seen = set()
    for item in items:
        fields(item, ('path', 'before_sha256', 'text'))
        path = relative(item['path'])
        if path not in plan['allowed'] or path in seen:
            raise ValueError('Patch path is outside accepted scope or duplicated')
        if path in plan['probe']['oracle_paths'] or any(p in PROTECTED for p in PurePosixPath(path).parts):
            raise ValueError('Patch targets protected oracle/state')
        seen.add(path)
        if not isinstance(item['text'], str) or len(item['text'].encode('utf-8')) > MAX_FILE:
            raise ValueError('Replacement must be bounded UTF-8 text')
        if item['before_sha256'] != plan['before'][path]['sha256']:
            raise ValueError('Stale patch preimage')
        if sha(item['text'].encode('utf-8')) == item['before_sha256']:
            raise ValueError('No-op replacement is not a repair')
    return value


def expected_snapshot(plan, events):
    result = copy.deepcopy(plan['before'])
    for event in events:
        if event['kind'] == 'replacement' and event['state'] == 'completed':
            item = event['patch']
            result[item['path']]['sha256'] = sha(item['text'].encode('utf-8'))
    return result


def assert_snapshot(plan, expected):
    if snapshot(plan) != expected:
        raise UnresolvedOperation('Checkout differs from accepted/journaled bytes; reconcile before continuing')


def replace_file(plan, item):
    raw = item['text'].encode('utf-8')
    with root_handle(plan) as root:
        with parent_handle(root, item['path']) as (parent, leaf):
            before, mode = read_file(parent, leaf, limit=MAX_FILE)
            if sha(before) != item['before_sha256']:
                raise UnresolvedOperation('Replacement preimage changed')
            temporary = '.harness-replace-' + uuid4().hex
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode, dir_fd=parent)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fchmod(stream.fileno(), mode)
                    os.fsync(stream.fileno())
                current, current_mode = read_file(parent, leaf, limit=MAX_FILE)
                if sha(current) != item['before_sha256'] or current_mode != mode:
                    raise UnresolvedOperation('Replacement preimage changed before commit')
                os.replace(temporary, leaf, src_dir_fd=parent, dst_dir_fd=parent)
                os.fsync(parent)
                after, after_mode = read_file(parent, leaf, limit=MAX_FILE)
                if after != raw or after_mode != mode:
                    raise UnresolvedOperation('Replacement after-image differs from requested bytes')
            finally:
                try:
                    os.unlink(temporary, dir_fd=parent)
                except FileNotFoundError:
                    pass
    return {'path': item['path'], 'before_sha256': item['before_sha256'], 'after_sha256': sha(raw), 'bytes': len(raw)}


def apply_patch(plan, patch, cursor):
    patch = decode_patch(json.dumps(patch), plan)
    assert_snapshot(plan, expected_snapshot(plan, cursor.record['events']))
    results = []
    for item in patch['replacements']:
        assert_snapshot(plan, expected_snapshot(plan, cursor.record['events']))
        results.append(cursor.perform('replace:' + item['path'], 'replacement',
            lambda item=item: replace_file(plan, item), effect_class='file_replacement',
            patch=item, plan_digest=digest(plan)))
    assert_snapshot(plan, expected_snapshot(plan, cursor.record['events']))
    return results


def run_probe(plan, expected):
    from .process import invoke
    assert_snapshot(plan, expected)
    probe = plan['probe']
    if sha(Path(probe['argv'][0]).read_bytes()) != plan['executable_sha256']:
        raise ValueError('Accepted probe executable changed')
    result = invoke(tuple(probe['argv']), '', cwd=Path(plan['root']), timeout=probe['timeout'],
                    max_output_bytes=probe['max_output_bytes'], environment=probe['environment'])
    assert_snapshot(plan, expected)
    return {**asdict(result), 'argv': list(result.argv), 'passed': result.returncode == 0 and result.failure is None,
            'plan_digest': digest(plan), 'artifact_digest': digest(expected),
            'isolation': 'Explicit environment, bounded subprocess; not a security sandbox'}


def reconcile_replacement(plan, event, *, retry_before=False):
    if event['kind'] != 'replacement' or event['phase'] != 'dispatching' or event['state'] == 'completed':
        raise ValueError('Not an unresolved replacement')
    item = event['patch']
    with root_handle(plan) as root:
        with parent_handle(root, item['path']) as (parent, leaf):
            raw, mode = read_file(parent, leaf, limit=MAX_FILE)
    if mode != plan['before'][item['path']]['mode']:
        raise UnresolvedOperation('Replacement mode changed')
    after = sha(item['text'].encode('utf-8'))
    if sha(raw) == after:
        event.update(state='completed', phase='completed', result={'path': item['path'],
            'before_sha256': item['before_sha256'], 'after_sha256': after, 'bytes': len(raw)})
    elif sha(raw) == item['before_sha256'] and retry_before and event['attempts'] < 2:
        event.update(state='pending', phase='prepared', attempts=event['attempts'] + 1)
    else:
        raise UnresolvedOperation('Unexpected bytes or known-before replacement requires explicit bounded retry')
    event.pop('error', None)
    event.pop('effects', None)
    return {'kind': 'observed_file_bytes', 'sha256': sha(raw), 'retry_before': retry_before}


def validate_scope(plan):
    """Reject unknown frozen policy fields without refreshing accepted bytes."""
    fields(plan, ('profile','root','root_identity','allowed','probe','executable_sha256','before','inputs'))
    if plan['profile'] != PROFILE or not Path(plan['root']).is_absolute():
        raise ValueError('Unsupported repair scope')
    fields(plan['root_identity'], ('device','inode'))
    fields(plan['probe'], ('argv','cwd','timeout','max_output_bytes','environment','oracle_paths'))
    if (not isinstance(plan['allowed'],list) or not 1 <= len(plan['allowed']) <= 20 or
            len(set(plan['allowed'])) != len(plan['allowed']) or set(plan['inputs']) != set(plan['allowed'])):
        raise ValueError('Invalid frozen replacement scope')
    for path in plan['allowed']:
        relative(path)
        if any(p in PROTECTED for p in PurePosixPath(path).parts) or path in plan['probe']['oracle_paths']:
            raise ValueError('Frozen scope includes protected state/oracle')
        fields(plan['before'][path], ('sha256','mode'))
        if not isinstance(plan['inputs'][path],str) or sha(plan['inputs'][path].encode('utf-8')) != plan['before'][path]['sha256']:
            raise ValueError('Frozen source text does not match accepted preimage')
