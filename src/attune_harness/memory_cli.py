"""Optional scoped reads, offline replay and proposal-only native memory work."""

import argparse
import json
import os
from pathlib import Path
import sys

from .features import FeatureUnavailable, read_text
from .memory_redis import SERVE_CHARS, SERVE_LIMIT
from .review_contract import parse_json


# The layers the hydration writes; test_memory_redis asserts this equals memory_redis.LAYERS.
REDIS_LAYERS = ('curated', 'file', 'lesson', 'rule')


class _Stderr:
    """A writer that resolves ``sys.stderr`` on every call.

    structlog's print logger keeps the stream it is given. Given ``sys.stderr``
    itself, it kept whichever object that was at configure time: under pytest a
    capture stream the fixture closes when the test ends, after which any
    later log line raised "I/O operation on closed file". This resolves the
    current stream each time instead.
    """

    def write(self, text):
        # _write owns the failure modes: a None stream is skipped, a character
        # the console cannot encode is replaced, and a broken stream is pointed
        # at the null device so the interpreter's exit flush cannot fail later.
        _write(sys.stderr, text)

    def flush(self):
        return


_STDERR = _Stderr()
_configured = False


def configure_process():
    """Disable the usage-ping uploader; bind structlog to stderr, once.

    RAG diagnostics must not corrupt JSON or MCP stdout, so structlog prints to
    stderr. The binding resolves ``sys.stderr`` on every write rather than at
    configure time, and it is made once per process: a second call rebinds
    nothing (the usage-ping variable is set every time), so the entry point
    that owns start-up (``main``) calls it and nothing else needs to (O-67).
    A stream that is ``None`` or closed drops the diagnostic; it never fails
    the command. Accounting and team transports are untouched.
    """
    global _configured
    os.environ['ATTUNE_USAGE_PING'] = '0'
    if _configured:
        return
    try:
        import structlog
    except ImportError:
        return
    structlog.configure(logger_factory=structlog.PrintLoggerFactory(file=_STDERR))
    _configured = True


def add_arguments(parser):
    parser.add_argument('--config', type=Path, required=True, help='Explicit authorized memory roots JSON')
    parser.add_argument('--jobs', type=Path, help='Existing job directory, separate from all memory roots')
    parser.add_argument('--native-config', type=Path,
                        help='Startup-owned pinned native proposal transport JSON')
    sub = parser.add_subparsers(dest='memory_operation', required=True)
    sub.add_parser('capabilities', help='Show supported reads and qualification limits')
    recall = sub.add_parser('recall', help='Get scoped memory excerpts and complete-source handles')
    recall.add_argument('query')
    recall.add_argument('--k', type=int, default=10)
    recall.add_argument('--max-chars', type=int, default=8000)
    sub.add_parser('resolve', help='Resolve a current full source').add_argument('handle', type=Path)
    sub.add_parser('refresh', help='Replace a previous receiving-agent packet').add_argument('context', type=Path)
    create = sub.add_parser('create', help='Create an offline worker run from explicit host input')
    create.add_argument('run_id')
    create.add_argument('--envelope', type=Path, required=True)
    create.add_argument('--policy', type=Path, required=True)
    for name in ('replay', 'inspect'):
        command = sub.add_parser(name, help='Replay saved responses' if name == 'replay' else 'Inspect a durable job')
        command.add_argument('run_id')
        command.add_argument('job_id')
        if name == 'replay':
            command.add_argument('--replies', type=Path, required=True)
    execute = sub.add_parser('execute', help='Run one proposal-only native job')
    execute.add_argument('run_id')
    execute.add_argument('job_id')
    redis = sub.add_parser('redis', help='Read the Redis memory a hydration keeps warm (redis extra); read-only')
    reads = redis.add_subparsers(dest='redis_operation', required=True)
    reads.add_parser('status', help='Hydration stamp, active node count and count per layer')
    digest = reads.add_parser('digest', help='The curated nodes the recall_digest function scores highest')
    digest.add_argument('--limit', type=int, default=5)
    reads.add_parser('related', help='One node and the nodes its edges reach').add_argument('id')
    reads.add_parser('node', help='One curated node by id').add_argument('id')
    search = reads.add_parser('search', help='Full-text search; pointers only, never a body')
    search.add_argument('query')
    search.add_argument('--layer', choices=REDIS_LAYERS)
    search.add_argument('--k', type=int, default=10)
    serve = sub.add_parser('serve', help='The recall digest as plain text for a session-start hook; '
                                         'stdout when Redis answers, one stderr line when not, exit 0 either way')
    serve.add_argument('--for', dest='prompt', help='Recall memory related to this prompt (at most 512 characters)')
    serve.add_argument('--limit', type=int, default=SERVE_LIMIT, help='Curated nodes to print')
    serve.add_argument('--chars', type=int, default=SERVE_CHARS, help='Bound on the text; node lines are dropped from the end')
    scratch = sub.add_parser('scratch', help='Working memory: bounded JSON under short keys; file store, or Redis with the extra')
    ops = scratch.add_subparsers(dest='scratch_operation', required=True)
    ops.add_parser('capabilities', help='Which backend is configured and what it declares')
    stash = ops.add_parser('stash', help='Store one JSON value, optionally with a time to live')
    stash.add_argument('key')
    source = stash.add_mutually_exclusive_group(required=True)
    source.add_argument('--value', help='The value as JSON text')
    source.add_argument('--value-file', type=Path, help='A file holding the value as JSON')
    stash.add_argument('--ttl', type=int, help='Seconds until the value expires')
    stash.add_argument('--expected-version', type=int,
                       help='Refuse unless the stored record is at this version (0: no record); nothing is written')
    ops.add_parser('retrieve', help='Read one value').add_argument('key')
    ops.add_parser('forget', help='Remove one value').add_argument('key')
    ops.add_parser('keys', help='List keys, optionally by a glob pattern').add_argument('pattern', nargs='?', default='*')


def add_commands(subparsers):
    add_arguments(subparsers.add_parser(
        'memory', help='Scoped memories, offline replay and optional native proposals'))


def read_json(path):
    return parse_json(read_text(path, 4 * 1024 * 1024), 4 * 1024 * 1024)


def _write(stream, text):
    """Write for a hook: never a traceback, whatever the stream is.

    A stream that is ``None`` (fd closed at exec, ``pythonw.exe``) is skipped.
    A console that cannot encode a character shows a replacement. A write or
    flush that fails, a reader gone from a pipe included, is dropped, and the
    stream's descriptor is pointed at the null device so the interpreter's
    exit-time flush of what is still buffered cannot raise again and turn the
    exit code into 120.
    """
    if stream is None:
        return
    try:
        try:
            stream.write(text)
            stream.flush()
        except UnicodeEncodeError:
            encoding = getattr(stream, 'encoding', None) or 'utf-8'
            stream.write(text.encode(encoding, 'replace').decode(encoding))
            stream.flush()
    except (OSError, ValueError, LookupError):
        try:
            null = os.open(os.devnull, os.O_WRONLY)
            try:
                os.dup2(null, stream.fileno())
            finally:
                os.close(null)
        except (OSError, ValueError, AttributeError):
            pass


def serve(args):
    """``memory serve``: the digest on stdout, or one line on stderr saying why not; exit 0 always.

    A session-start hook must not block a session, so nothing here raises or
    exits non-zero: a missing config file, a refused limit, no ``redis``
    section, the extra absent, an unreachable server and an empty digest all
    become the stderr line, and stdout stays empty.
    """
    from .memory_redis import serve as digest_text
    try:
        if os.environ.get('ATTUNE_MEMORY_WORKER') == '0':
            text, reason = None, 'Optional memory worker route is disabled'
        else:
            text, reason = digest_text(read_json(args.config), limit=args.limit, chars=args.chars,
                                       config_path=args.config, prompt=args.prompt)
    except Exception as error:  # noqa: BLE001 - fail open by contract
        text, reason = None, f'{type(error).__name__}: {error}'
    if text is None:
        _write(sys.stderr, f'[attune-harness memory] skipped: {" ".join(str(reason).split())}\n')
    else:
        _write(sys.stdout, text + '\n')
    return 0


def execute(args):
    if args.memory_operation == 'serve':
        return serve(args)
    try:
        if os.environ.get('ATTUNE_MEMORY_WORKER') == '0':
            result = dict(status='disabled', detail='Optional memory worker route is disabled')
        elif args.memory_operation == 'redis':
            from .memory_redis import read
            arguments = {key: getattr(args, key) for key in ('limit', 'id', 'query', 'layer', 'k')
                         if getattr(args, key, None) is not None}
            result = read(read_json(args.config), args.redis_operation, arguments)
        elif args.memory_operation == 'scratch':
            from .memory_scratch import VALUE_LIMIT, run
            arguments = {key: getattr(args, key) for key in ('key', 'ttl', 'pattern', 'expected_version')
                         if getattr(args, key, None) is not None}
            if args.scratch_operation == 'stash':
                raw = read_text(args.value_file, VALUE_LIMIT + 4096) if args.value_file is not None else args.value
                arguments['value'] = parse_json(raw, VALUE_LIMIT + 4096)
            result = run(read_json(args.config), args.scratch_operation, arguments)
        else:
            from .memory_context import MemoryHost
            from .memory_reader import roots_config
            native = read_json(args.native_config) if args.native_config is not None else None
            config = read_json(args.config)
            reader = config.get('reader', 'native') if isinstance(config, dict) else 'native'
            host = MemoryHost(roots_config(config), args.jobs, native, reader=reader)
            names = {'capabilities': (), 'recall': ('query', 'k', 'max_chars'),
                     'resolve': ('handle',), 'refresh': ('context',),
                     'create': ('run_id', 'envelope', 'policy'),
                     'replay': ('run_id', 'job_id', 'replies'),
                     'inspect': ('run_id', 'job_id'), 'execute': ('run_id', 'job_id')}
            arguments = {key: getattr(args, key) for key in names[args.memory_operation]}
            for key in ('handle', 'context', 'envelope', 'policy', 'replies'):
                if key in arguments:
                    arguments[key] = read_json(arguments[key])
            result = host.invoke(args.memory_operation, arguments)
    except ImportError as error:
        result = dict(status='unavailable', detail='Optional current-memory adapter dependencies are unavailable',
                      error=str(error))
    except FeatureUnavailable as error:
        result = dict(status='unavailable', detail=str(error), error=type(error).__name__)
    except Exception as error:
        result = dict(status='failed', error=type(error).__name__, detail=str(error))
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 2 if result.get('status') in (
        'disabled', 'unavailable', 'failed', 'partial', 'uncertain', 'quarantined',
        'unresolved_reasoning', 'await_evidence', 'await_decision', 'stale',
        'unresolved', 'stale_stop',
    ) else 0


def main(argv=None):
    configure_process()
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    return execute(parser.parse_args(argv))


if __name__ == '__main__':
    raise SystemExit(main())
