"""Explicit saved intent, atomically committed with history and replay evidence.

The initial storage profile is local POSIX. Redis is only a rebuildable index.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import time
from contextlib import contextmanager
from uuid import UUID, uuid4

from .review_store import _lock_once, _LOCK_HELD

MAX_STATE = 8 * 1024 * 1024
MAX_REQUEST = 128 * 1024
LOCK_SECONDS = 2.0


class SavedError(ValueError):
    def __init__(self, message, *, code='invalid', outcome='not_committed'):
        super().__init__(message)
        self.code, self.outcome = code, outcome


def _json(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                          allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise SavedError('Saved input must be valid JSON') from exc


def _fields(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value) - set(required) - set(optional):
        raise SavedError('Saved object has missing or unsupported fields')


def _text(value, limit):
    try:
        valid = isinstance(value, str) and value.strip() and '\x00' not in value and len(value.encode('utf-8')) <= limit
    except UnicodeError:
        valid = False
    if not valid:
        raise SavedError('Saved text is empty, invalid, or exceeds its byte limit')
    return value


def _absolute(value):
    _text(value, 4096)
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts:
        raise SavedError('Saved path must be absolute without traversal')
    return str(path.resolve())


def _scope(value):
    if value == {'kind': 'global'}:
        return dict(value)
    _fields(value, ('kind', 'project'))
    if value['kind'] != 'project':
        raise SavedError('Unsupported saved scope')
    return {'kind': 'project', 'project': _absolute(value['project'])}


def _id(value):
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError()
    except (ValueError, TypeError, AttributeError) as exc:
        raise SavedError('Invalid saved identity') from exc
    return value


def _intent(value):
    _fields(value, ('kind', 'scope', 'title', 'content', 'source'), ('next_action', 'execution'))
    if value['kind'] not in ('memory', 'task'):
        raise SavedError('Unsupported saved kind')
    value['scope'] = _scope(value['scope'])
    _text(value['title'], 1024)
    _text(value['content'], 65536)
    _fields(value['source'], ('author', 'reference'))
    for item in value['source'].values():
        _text(item, 2048)
    if value['kind'] == 'task':
        _text(value.get('next_action'), 8192)
        if 'execution' in value:
            _fields(value['execution'], ('directory', 'task_id'))
            value['execution']['directory'] = _absolute(value['execution']['directory'])
            _id(value['execution']['task_id'])
            if value['scope']['kind'] != 'project':
                raise SavedError('Execution references require project scope')
    elif 'next_action' in value or 'execution' in value:
        raise SavedError('Memory cannot have task fields')
    return value


def _regular(fd):
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise SavedError('Saved files must be regular and have exactly one link')


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise SavedError('Duplicate saved JSON key')
        result[key] = value
    return result


def _record(record):
    _fields(record, ('id', 'kind', 'scope', 'title', 'content', 'source', 'revision', 'status', 'history'),
            ('next_action', 'execution'))
    _id(record['id'])
    intent = {k: copy.deepcopy(v) for k, v in record.items() if k not in ('id', 'revision', 'status', 'history')}
    if _intent(copy.deepcopy(intent)) != intent:
        raise SavedError('Noncanonical saved intent')
    statuses = ('active', 'withdrawn') if record['kind'] == 'memory' else ('open', 'completed', 'withdrawn')
    if record['status'] not in statuses or type(record['revision']) is not int or record['revision'] < 1:
        raise SavedError('Invalid saved revision or status')
    if not isinstance(record['history'], list) or len(record['history']) != record['revision']:
        raise SavedError('Invalid saved history')
    for number, item in enumerate(record['history'], 1):
        _fields(item, ('request_id', 'operation', 'record'))
        _text(item['request_id'], 256)
        if item['operation'] not in ('save', 'revise', 'forget', 'complete'):
            raise SavedError('Invalid saved history operation')
        snap = item['record']
        if (not isinstance(snap, dict) or snap.get('id') != record['id']
                or type(snap.get('revision')) is not int or snap['revision'] != number):
            raise SavedError('Invalid saved history identity')
        # Validate snapshots using a single synthetic history entry is unnecessary:
        # the same exact intent/status schema is checked directly.
        _fields(snap, ('id', 'kind', 'scope', 'title', 'content', 'source', 'revision', 'status'),
                ('next_action', 'execution'))
        snapshot_intent = {k: v for k, v in snap.items() if k not in ('id', 'revision', 'status')}
        if _intent(copy.deepcopy(snapshot_intent)) != snapshot_intent:
            raise SavedError('Noncanonical saved history intent')
        previous = record['history'][number - 2]['record'] if number > 1 else None
        op = item['operation']
        if number == 1:
            if op != 'save' or snap['status'] != ('active' if snap['kind'] == 'memory' else 'open'):
                raise SavedError('Invalid initial saved history')
        elif op == 'save' or previous['status'] == 'withdrawn':
            raise SavedError('Invalid saved history transition')
        elif op == 'revise' and snap['status'] != previous['status']:
            raise SavedError('Revision changed saved status')
        elif op in ('complete', 'forget'):
            expected_snapshot = dict(previous, revision=number, status='completed' if op == 'complete' else 'withdrawn')
            if snap != expected_snapshot:
                raise SavedError('Invalid saved status transition')
            if op == 'complete' and (previous['kind'] != 'task' or 'execution' in previous or previous['status'] != 'open'):
                raise SavedError('Invalid saved completion')
        if snap['status'] == 'completed' and 'execution' in snap:
            raise SavedError('Linked tasks cannot carry local completion')
        if snap['kind'] != record['kind'] or snap['scope'] != record['scope'] or snap['status'] not in statuses:
            raise SavedError('Saved history changes identity or scope')
    if record['history'][-1]['record'] != {k: v for k, v in record.items() if k != 'history'}:
        raise SavedError('Saved current record and history disagree')


class SavedStore:
    def __init__(self, root, index=None):
        root = Path(root)
        if not root.is_absolute() or '..' in root.parts or root.is_symlink():
            raise SavedError('Saved root must be an absolute non-link directory')
        # Resolve OS aliases such as macOS /var once, then anchor all accesses.
        for parent in root.parents:
            if parent.is_symlink() and str(parent) not in ('/var', '/tmp', '/etc'):
                raise SavedError('Saved root cannot traverse a directory link')
        self.root = root.resolve()
        if any(p in ('.git', '.hg', '.svn') for p in self.root.parts):
            raise SavedError('Saved root cannot be repository metadata')
        self.index = index

    @contextmanager
    def _locked(self):
        if os.name != 'posix':
            raise SavedError('Saved storage currently requires the local POSIX profile', code='unsupported')
        parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
        lock = None
        try:
            for component in self.root.parts[1:]:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=parent)
                    os.fsync(parent)
                except FileExistsError:
                    pass
                child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                os.close(parent)
                parent = child
            try:
                lock = os.open('.saved.lock', os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                               0o600, dir_fd=parent)
            except FileExistsError:
                # Separate creation from opening an existing lock. Concurrent
                # O_CREAT|O_NOFOLLOW opens can report ENOENT on macOS. Never
                # unlink or replace the persistent lock inode.
                lock = os.open('.saved.lock', os.O_RDWR | os.O_NOFOLLOW, dir_fd=parent)
            _regular(lock)
            deadline = time.monotonic() + LOCK_SECONDS
            while True:
                try:
                    _lock_once(lock)
                    break
                except OSError as exc:
                    if exc.errno not in _LOCK_HELD or time.monotonic() >= deadline:
                        raise SavedError('Saved store is busy or locking is unavailable', code='busy') from exc
                    time.sleep(.01)
            yield parent
        except OSError as exc:
            raise SavedError('Saved storage access failed', code='storage') from exc
        finally:
            if lock is not None:
                os.close(lock)
            os.close(parent)

    def _read(self, directory):
        try:
            fd = os.open('state.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        except FileNotFoundError:
            return {'schema_version': 1, 'records': {}, 'operations': {}, 'index': {}}
        try:
            _regular(fd)
            with os.fdopen(fd, 'rb', closefd=False) as stream:
                raw = stream.read(MAX_STATE + 1)
            if len(raw) > MAX_STATE:
                raise SavedError('Saved state exceeds 8 MiB')
            state = json.loads(raw, object_pairs_hook=_pairs)
            _fields(state, ('schema_version', 'records', 'operations', 'index'))
            if type(state['schema_version']) is not int or state['schema_version'] != 1:
                raise SavedError('Unsupported saved schema version')
            for key in ('records', 'operations', 'index'):
                if not isinstance(state[key], dict):
                    raise SavedError('Invalid saved state table')
            if set(state['index']) != set(state['records']):
                raise SavedError('Saved index metadata is incomplete')
            for key, record in state['records'].items():
                _record(record)
                if key != record['id'] or state['index'][key] not in ('pending', 'indexed', 'disabled'):
                    raise SavedError('Invalid saved state identity or indexing status')
            for key, operation in state['operations'].items():
                _text(key, 256)
                _fields(operation, ('digest', 'record'))
                if not isinstance(operation['digest'], str) or len(operation['digest']) != 64 or any(c not in '0123456789abcdef' for c in operation['digest']):
                    raise SavedError('Invalid saved operation digest')
                _record(operation['record'])
                current = state['records'].get(operation['record']['id'])
                if current is None or operation['record']['history'] != current['history'][:operation['record']['revision']]:
                    raise SavedError('Saved replay evidence disagrees with history')
            for record in state['records'].values():
                for entry in record['history']:
                    operation = state['operations'].get(entry['request_id'])
                    if operation is None or operation['record']['id'] != record['id'] or operation['record']['revision'] != entry['record']['revision']:
                        raise SavedError('Saved history has missing replay evidence')
            return state
        except (ValueError, TypeError, KeyError, UnicodeError, RecursionError) as exc:
            raise SavedError('Saved state is malformed or unsupported', code='corrupt') from exc
        finally:
            os.close(fd)

    def _write(self, directory, state):
        payload = _json(state)
        if len(payload) > MAX_STATE:
            raise SavedError('Saved state exceeds 8 MiB')
        temporary = '.saved-' + str(uuid4())
        replaced = False
        try:
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, 'state.json', src_dir_fd=directory, dst_dir_fd=directory)
            replaced = True
            os.fsync(directory)
        except OSError as exc:
            raise SavedError('Saved commit durability is uncertain; inspect and retry with the same request ID'
                             if replaced else 'Saved commit failed before replacement',
                             code='persistence', outcome='uncertain' if replaced else 'not_committed') from exc
        finally:
            if not replaced:
                try:
                    os.unlink(temporary, dir_fd=directory)
                except OSError:
                    pass

    def _index(self, directory, state, record):
        if self.index is None:
            return state['index'][record['id']]
        try:
            if record['status'] == 'withdrawn':
                self.index.remove(record['id'], copy.deepcopy(record['scope']))
            else:
                self.index.upsert(copy.deepcopy(record))
        except Exception:
            return 'pending'
        state['index'][record['id']] = 'indexed'
        try:
            self._write(directory, state)
        except SavedError as exc:
            raise SavedError('Saved record committed; index status durability is uncertain', code='persistence', outcome='uncertain') from exc
        return 'indexed'

    def _mutate(self, operation, request_id, value, identity=None, scope=None, expected=None):
        _text(request_id, 256)
        payload = {'operation': operation, 'request_id': request_id, 'value': value,
                   'id': identity, 'scope': scope, 'expected_revision': expected}
        encoded = _json(payload)
        if len(encoded) > MAX_REQUEST:
            raise SavedError('Saved request exceeds 128 KiB')
        digest = hashlib.sha256(encoded).hexdigest()
        with self._locked() as directory:
            state = self._read(directory)
            prior = state['operations'].get(request_id)
            if prior is not None:
                if prior['digest'] != digest:
                    raise SavedError('Request ID was already used for different input', code='conflict')
                return {'record': copy.deepcopy(prior['record']),
                        'index_status': state['index'][prior['record']['id']]}
            if operation == 'save':
                record = copy.deepcopy(value)
                record.update(id=str(uuid4()), revision=1, status='active' if value['kind'] == 'memory' else 'open', history=[])
            else:
                record = copy.deepcopy(state['records'].get(identity))
                if record is None or record['scope'] != scope:
                    raise SavedError('Saved record is unavailable in this scope', code='not_found')
                if type(expected) is not int or expected != record['revision']:
                    raise SavedError('Saved revision conflict', code='conflict')
                if record['status'] == 'withdrawn':
                    raise SavedError('Withdrawn records cannot be changed')
                if operation == 'revise':
                    if record['status'] == 'completed' and 'execution' in value:
                        raise SavedError('Completed tasks cannot acquire an execution owner')
                    record.update(value)
                    _intent(copy.deepcopy({k: v for k, v in record.items() if k not in ('id', 'revision', 'status', 'history')}))
                elif operation == 'forget':
                    record['status'] = 'withdrawn'
                else:
                    if record['kind'] != 'task' or 'execution' in record or record['status'] != 'open':
                        raise SavedError('Only open unlinked tasks can be completed')
                    record['status'] = 'completed'
                record['revision'] += 1
            snapshot = {k: copy.deepcopy(v) for k, v in record.items() if k != 'history'}
            record['history'].append({'operation': operation, 'request_id': request_id, 'record': snapshot})
            _record(record)
            state['records'][record['id']] = record
            state['operations'][request_id] = {'digest': digest, 'record': copy.deepcopy(record)}
            state['index'][record['id']] = 'pending' if self.index is not None else 'disabled'
            self._write(directory, state)
            status = self._index(directory, state, record)
            return {'record': copy.deepcopy(record), 'index_status': status}

    def save(self, request):
        _fields(request, ('request_id', 'kind', 'scope', 'title', 'content', 'source'), ('next_action', 'execution'))
        value = _intent(copy.deepcopy({k: v for k, v in request.items() if k != 'request_id'}))
        return self._mutate('save', request['request_id'], value)

    def revise(self, id, changes, scope, request_id, expected_revision):
        if not isinstance(changes, dict) or not changes or set(changes) - {'title', 'content', 'source', 'next_action', 'execution'}:
            raise SavedError('Unsupported saved revision fields')
        return self._mutate('revise', request_id, copy.deepcopy(changes), _id(id), _scope(scope), expected_revision)

    def forget(self, id, scope, request_id, expected_revision):
        return self._mutate('forget', request_id, {}, _id(id), _scope(scope), expected_revision)

    def complete(self, id, scope, request_id, expected_revision):
        return self._mutate('complete', request_id, {}, _id(id), _scope(scope), expected_revision)

    def _observe(self, record, index_status):
        result = copy.deepcopy(record)
        result['index_status'] = index_status
        if 'execution' in result:
            result['execution_status'] = 'unavailable'
            try:
                from .task_contract import read_task
                task = read_task(Path(result['execution']['directory']))
                if task['request']['task_id'] == result['execution']['task_id'] and task['request']['project_root'] == result['scope']['project']:
                    result['execution_status'] = task['status']
            except Exception:
                pass
        return result

    def get(self, id, scope, include_withdrawn=False):
        identity, selected = _id(id), _scope(scope)
        with self._locked() as directory:
            state = self._read(directory)
            record = state['records'].get(identity)
            if record is None or record['scope'] != selected or (record['status'] == 'withdrawn' and not include_withdrawn):
                raise SavedError('Saved record is unavailable in this scope', code='not_found')
            return self._observe(record, state['index'][identity])

    def list(self, scope):
        selected = _scope(scope)
        with self._locked() as directory:
            state = self._read(directory)
            return [self._observe(record, state['index'][key]) for key, record in sorted(state['records'].items())
                    if record['scope'] == selected and record['status'] != 'withdrawn']

    def search(self, query, scope):
        query = _text(query, 4096).casefold()
        return [record for record in self.list(scope)
                if query in '\n'.join(record.get(k, '') for k in ('title', 'content', 'next_action')).casefold()]

    def reindex(self, scope):
        selected = _scope(scope)
        with self._locked() as directory:
            state = self._read(directory)
            if self.index is None:
                return {'index_status': 'disabled', 'indexed': 0, 'pending': 0}
            records = [record for record in state['records'].values() if record['scope'] == selected]
            for record in records:
                state['index'][record['id']] = 'pending'
            self._write(directory, state)
            statuses = [self._index(directory, state, record) for record in records]
            return {'index_status': 'pending' if 'pending' in statuses else 'indexed',
                    'indexed': statuses.count('indexed'), 'pending': statuses.count('pending')}
