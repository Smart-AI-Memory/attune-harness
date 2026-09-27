"""Explicit saved-memory commands; independent of legacy recall and scratch."""

from pathlib import Path

from .features import read_text
from .review_contract import parse_json

INPUT_LIMIT = 128 * 1024


def add_arguments(subparsers):
    saved = subparsers.add_parser('saved', help='Save memories and task intent with retained history')
    ops = saved.add_subparsers(dest='saved_operation', required=True)
    for name in ('save', 'revise', 'forget', 'complete'):
        command = ops.add_parser(name)
        if name != 'save':
            command.add_argument('id')
        command.add_argument('--request', type=Path, required=True)
    for name in ('show', 'list', 'search', 'reindex'):
        command = ops.add_parser(name)
        if name == 'show':
            command.add_argument('id')
            command.add_argument('--history', action='store_true')
        if name == 'search':
            command.add_argument('query')
        command.add_argument('--scope', type=Path, required=True)


def _read(path):
    return parse_json(read_text(path, INPUT_LIMIT), INPUT_LIMIT)


def _store(config):
    from .memory_saved import SavedStore
    if not isinstance(config, dict) or not isinstance(config.get('saved'), dict):
        raise ValueError('Explicit saved store configuration is required')
    saved = config['saved']
    if set(saved) - {'root', 'redis'} or 'root' not in saved:
        raise ValueError('Invalid saved store configuration')
    if not isinstance(saved['root'], str) or not Path(saved['root']).is_absolute():
        raise ValueError('Saved root must be an absolute path')
    index = None
    if 'redis' in saved:
        from .memory_saved_index import RedisSavedIndex
        index = RedisSavedIndex(saved['redis'])
    return SavedStore(Path(saved['root']), index=index)


def run(args):
    """Return safe structured failures, including possible committed outcomes."""
    from .memory_saved import SavedError
    try:
        store = _store(_read(args.config))
        operation = args.saved_operation
        if operation in ('save', 'revise', 'forget', 'complete'):
            request = _read(args.request)
            if operation == 'save':
                return store.save(request)
            expected = {'scope', 'request_id', 'expected_revision'}
            if operation == 'revise':
                expected.add('changes')
            if not isinstance(request, dict) or set(request) != expected:
                raise ValueError('Invalid saved mutation request')
            common = (request['scope'], request['request_id'], request['expected_revision'])
            if operation == 'revise':
                return store.revise(args.id, request['changes'], *common)
            return getattr(store, operation)(args.id, *common)
        scope = _read(args.scope)
        if operation == 'show':
            record = store.get(args.id, scope, include_withdrawn=args.history)
            if not args.history:
                record = {key: value for key, value in record.items() if key != 'history'}
            return record
        if operation == 'list':
            return {'records': store.list(scope)}
        if operation == 'search':
            return {'records': store.search(args.query, scope)}
        return store.reindex(scope)
    except SavedError as error:
        return {'status': 'uncertain' if error.outcome == 'uncertain' else 'failed',
                'error': error.code, 'outcome': error.outcome, 'detail': str(error)}
    except Exception:
        # Filesystem/library exceptions may contain credentials or request data.
        return {'status': 'failed', 'error': 'invalid_saved_request',
                'detail': 'Saved configuration or request could not be processed'}
