"""Offline planning and explicitly authorized index/retrieval commands."""

import json
from pathlib import Path

from .features import report
from .review_contract import digest


def add_commands(sub):
    code = sub.add_parser('code-config', help='Prepare repository-first retrieval; documentation is optional')
    code.add_argument('--repo', type=Path, required=True)
    code.add_argument('--repo-id', default='app')
    code.add_argument('--index-dir', type=Path, required=True)
    code.add_argument('--include-docs', action='store_true')
    code.add_argument('--structured-path', action='append', default=[],
                      help='Explicit repo-relative schema/config file; repeat as needed')
    index = sub.add_parser('index', help='Plan, build, update or inspect a selected application index')
    commands = index.add_subparsers(dest='index_command', required=True)
    for name in ('plan', 'build', 'update', 'inspect'):
        command = commands.add_parser(name)
        command.add_argument('--config', type=Path, required=True)
        if name == 'inspect':
            command.add_argument('--generation', required=True)
        if name == 'update':
            command.add_argument('--base-generation', required=True)
        if name in ('build', 'update'):
            command.add_argument('--allow-provider', action='store_true', help='Authorize selected source uploads and bounded paid Voyage calls')
    task = sub.add_parser('retrieval-task', help='Prepare coding-agent retrieval intake; review and set accepted=true')
    task.add_argument('--config', type=Path, required=True)
    task.add_argument('--generation', required=True)
    task.add_argument('--objective', required=True)
    task.add_argument('--participant', default='coding-agent')
    task.add_argument('--max-calls', type=int, default=8)


def execute(args):
    from .voyage_sources import load_config
    from .voyage_index import index_plan, build_index, inspect_index
    try:
        if args.command == 'code-config':
            from .voyage_sources import code_config
            result = code_config(args.repo, args.index_dir, repo_id=args.repo_id,
                                 include_docs=args.include_docs, structured_paths=args.structured_path)
            print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
            return 0
        cfg = load_config(args.config)
        if args.command == 'retrieval-task':
            from .retrieval_task import task_template
            result = task_template(cfg, args.generation, args.objective, args.participant, args.max_calls)
        elif args.index_command == 'plan':
            result = index_plan(cfg)
        elif args.index_command == 'inspect':
            result = inspect_index(cfg, args.generation)
        else:
            result = build_index(cfg, base_generation=getattr(args, 'base_generation', None), allow_provider=args.allow_provider)
    except Exception as exc:
        result = report(args.command, 'failed', error={'type': type(exc).__name__, 'detail': str(exc)})
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 2 if result.get('status') == 'failed' else 0
