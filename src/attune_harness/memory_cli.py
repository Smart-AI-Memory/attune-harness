"""Optional scoped memory reads and offline shared-worker qualification."""

import argparse
import json
import os
from pathlib import Path
import sys

from .features import read_text
from .review_contract import parse_json


def configure_process():
    """Disable the usage-ping uploader; preserve accounting and team transports."""
    os.environ['ATTUNE_USAGE_PING'] = '0'
    # RAG diagnostics must not corrupt JSON or MCP stdout. Do this at host
    # startup, never via process-wide stdout redirection during concurrent calls.
    try:
        import structlog
    except ImportError:
        return
    structlog.configure(logger_factory=structlog.PrintLoggerFactory(file=sys.stderr))


def add_arguments(parser):
    parser.add_argument('--config', type=Path, required=True, help='Explicit authorized memory roots JSON')
    parser.add_argument('--jobs', type=Path, help='Existing job directory, separate from all memory roots')
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


def add_commands(subparsers):
    add_arguments(subparsers.add_parser('memory', help='Scoped existing memories and offline worker; optional AI adapter'))


def read_json(path):
    return parse_json(read_text(path, 4 * 1024 * 1024), 4 * 1024 * 1024)


def execute(args):
    configure_process()
    try:
        if os.environ.get('ATTUNE_MEMORY_WORKER') == '0':
            result = dict(status='disabled', detail='Optional memory worker route is disabled')
        else:
            from .memory_context import MemoryHost
            host = MemoryHost(read_json(args.config), args.jobs)
            names = {'capabilities': (), 'recall': ('query', 'k', 'max_chars'),
                     'resolve': ('handle',), 'refresh': ('context',),
                     'create': ('run_id', 'envelope', 'policy'),
                     'replay': ('run_id', 'job_id', 'replies'), 'inspect': ('run_id', 'job_id')}
            arguments = {key: getattr(args, key) for key in names[args.memory_operation]}
            for key in ('handle', 'context', 'envelope', 'policy', 'replies'):
                if key in arguments:
                    arguments[key] = read_json(arguments[key])
            result = host.invoke(args.memory_operation, arguments)
    except ImportError as error:
        result = dict(status='unavailable', detail='Optional current-memory adapter dependencies are unavailable',
                      error=str(error))
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
