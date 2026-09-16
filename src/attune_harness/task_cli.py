"""Task intake and unbound form templates; no participant execution lives here."""

import copy
import json
from pathlib import Path
import sys
import time

from .review_contract import parse_json
from .task_contract import (accept_task, answer_names, check_fresh, create_task,
                            clear_template_cache, form_revision, read_task, task_template)

def present_task(directory, *, bypass=False):
    started = time.perf_counter_ns()
    record = read_task(directory)
    loaded = time.perf_counter_ns()
    check_fresh(record)
    validated = time.perf_counter_ns()
    request = record['request']
    template, metrics = task_template(request, bypass=bypass)
    metrics['reused_answer_fields'] = sum(v is not None for v in request['answers'].values())
    metrics['record_validation_ms'] = (loaded - started) / 1e6
    metrics['source_validation_ms'] = (validated - loaded) / 1e6
    submission = None
    if record['status'] == 'draft':
        submission = {'schema_version': 1, 'task_id': request['task_id'], 'revision': request['revision'],
                      'form_revision': form_revision(request, template['definition']),
                      'checkpoint_digest': record['checkpoint_digest'],
                      'accepted': False, 'answers': copy.deepcopy(request['answers']),
                      'permissions': {'external': False, 'provider': False}}
    return {'schema_version': 1, 'operation': 'task-intake', 'status': record['status'],
            'task_id': request['task_id'], 'revision': request['revision'],
            'task_directory': str(Path(record['record_path']).parent),
            'answers': copy.deepcopy(request['answers']),
            'definition': template['definition'], 'markdown': template['markdown'],
            'submission': submission, 'defaults_origin': request['defaults_origin'],
            'intake_metrics': metrics, 'execution_status': record['status'] if 'execution' in record else 'not_started',
            'note': ('Saved execution exists; use status for its evidence.' if 'execution' in record else
                     'Intake only: no assessment or participant invocation has occurred.')}


def add_arguments(parser):
    parser.add_argument('--pause-after', type=int, help='Pause after this many new durable operations')
    parser.add_argument('--intake-only', action='store_true', help='Prepare/accept without executing')
    parser.add_argument('--goal', help='Start task-oriented assessment intake instead of legacy review JSON')
    parser.add_argument('--project', type=Path, help='Task project root (default: current directory)')
    parser.add_argument('--plan', choices=('solo', 'independent-review'))
    parser.add_argument('--task-dir', type=Path, help='Explicit new task directory outside the selected corpus')
    parser.add_argument('--task-response', type=Path, help='Submit the bound intake response for --task-dir')
    parser.add_argument('--profile', type=Path, help='Explicit saved non-sensitive project defaults')
    for name in ('criteria', 'query', 'document', 'context', 'corpus', 'assessor', 'reviewer'):
        parser.add_argument('--' + name)
    parser.add_argument('--accept', action='store_true', help='Explicitly accept the current complete intake')
    parser.add_argument('--bypass-intake-cache', action='store_true')
    parser.add_argument('--clear-intake-cache', action='store_true')


def validate_mode(args, parser):
    task = args.goal is not None or args.task_response is not None
    names = ('project', 'plan', 'task_dir', 'profile', 'criteria', 'query', 'document',
             'context', 'corpus', 'assessor', 'reviewer', 'accept',
             'bypass_intake_cache', 'clear_intake_cache', 'intake_only', 'pause_after')
    if task:
        if args.request is not None or args.run_dir is not None or args.max_operations is not None:
            parser.error('Task intake and legacy request/--run-dir/--max-operations are mutually exclusive')
        if args.goal is not None and args.task_response is not None:
            parser.error('--goal and --task-response are mutually exclusive')
        if args.task_response is not None:
            forbidden = tuple(n for n in names if n not in ('task_dir', 'bypass_intake_cache', 'clear_intake_cache', 'intake_only', 'pause_after'))
            if args.task_dir is None or any(getattr(args, n) is not None and getattr(args, n) is not False for n in forbidden):
                parser.error('--task-response requires --task-dir and cannot be combined with intake overrides')
            if args.allow_external or args.allow_provider:
                parser.error('A task response must carry its own explicit permissions')
            if args.config is not None:
                parser.error('A task response uses its saved registry; --config cannot override it')
    else:
        if args.request is None or args.run_dir is None:
            parser.error('Legacy review requires request and --run-dir; new intake requires --goal')
        if any(getattr(args, n) is not None and getattr(args, n) is not False for n in names):
            parser.error('Task intake options require --goal or --task-response')
    args.config = args.config or Path('participants.json')
    return task


def execute_intake(args):
    """The accepted-intake result is deliberately distinct from completed review."""
    try:
        if args.clear_intake_cache:
            clear_template_cache()
        if args.task_response is not None:
            from .features import read_text
            response = parse_json(read_text(args.task_response, 131072))
            record = accept_task(args.task_dir, response)
            directory = Path(record['record_path']).parent
        else:
            names = answer_names(args.plan or 'solo')
            if args.reviewer is not None and 'reviewer' not in names:
                raise ValueError('--reviewer requires --plan independent-review')
            answers = {n: getattr(args, n) for n in names if n != 'goal' and getattr(args, n) is not None}
            record = create_task(args.project or Path.cwd(), args.config, goal=args.goal,
                                 plan=args.plan or 'solo', directory=args.task_dir,
                                 answers=answers, profile=args.profile)
            directory = Path(record['record_path']).parent
            presented = present_task(directory, bypass=args.bypass_intake_cache)
            response = presented['submission']
            response['permissions'] = {'external': args.allow_external, 'provider': args.allow_provider}
            if sys.stdin.isatty() and not args.accept:
                print(presented['markdown'])
                for name, value in response['answers'].items():
                    if value is None:
                        response['answers'][name] = input(name + ': ').strip()
                print(json.dumps({'answers': response['answers'], 'permissions': response['permissions']}, indent=2))
                response['accepted'] = input('Accept this intake? [y/N] ').strip().lower() in ('y', 'yes')
            elif args.accept:
                response['accepted'] = True
            if response['accepted']:
                accept_task(directory, response)
        result = present_task(directory, bypass=args.bypass_intake_cache)
        if result['status'] == 'accepted' and not args.intake_only:
            from .task_policies import execute_task
            result = execute_task(directory, max_operations=args.pause_after)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
        return 0 if result['status'] in ('accepted', 'completed') else (1 if result['status'] in ('draft', 'paused') else 2)
    except Exception as exc:
        print(json.dumps({'schema_version': 1, 'operation': 'task-intake', 'status': 'failed',
                          'error': {'type': type(exc).__name__, 'detail': str(exc)}}, indent=2))
        return 2


def add_controls(sub):
    for name, help_text in (
        ('status', 'Inspect a saved task or legacy review without execution'),
        ('resume', 'Continue a task using its saved accepted request'),
        ('reconcile-task', 'Attach a correlated reply or authorize one known read-only retry'),
        ('transfer-task', 'Transfer an assessor to an already accepted identity'),
        ('cancel-task', 'Cancel stopped work while preserving uncertain effects'),
    ):
        parser = sub.add_parser(name, help=help_text)
        parser.add_argument('task_dir', type=Path)
        if name != 'status':
            parser.add_argument('--checkpoint', help='Optional expected checkpoint for scripted compare-and-set')
        if name == 'resume':
            parser.add_argument('--max-operations', type=int)
        elif name == 'reconcile-task':
            parser.add_argument('--event', required=True)
            group = parser.add_mutually_exclusive_group(required=True)
            group.add_argument('--reply', type=Path)
            group.add_argument('--retry-read-only', action='store_true')
        elif name == 'transfer-task':
            parser.add_argument('--assessor', required=True)
            parser.add_argument('--reason', required=True)
        elif name == 'cancel-task':
            parser.add_argument('--reason', required=True)


def execute_control(args):
    from .task_policies import inspect_task, execute_task, control_task
    try:
        if args.command == 'status':
            from .review_store import read_record, inspect_run
            result = (inspect_run(args.task_dir) if read_record(args.task_dir).get('operation') == 'review'
                      else inspect_task(args.task_dir))
        elif args.command == 'resume':
            result = execute_task(args.task_dir, checkpoint=args.checkpoint, max_operations=args.max_operations)
        else:
            options = {'reconcile-task': lambda: {'event_id':args.event,'reply_file':args.reply,'retry_read_only':args.retry_read_only},
                       'transfer-task': lambda: {'participant_id':args.assessor,'reason':args.reason},
                       'cancel-task': lambda: {'reason':args.reason}}
            result = control_task(args.task_dir, args.command.split('-')[0],
                                  checkpoint=args.checkpoint, **options[args.command]())
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
        if args.command == 'status':
            return 0
        return 0 if result['status'] == 'completed' else (1 if result['status'] in ('paused','cancelled') else 2)
    except Exception as exc:
        from .recovery import UnresolvedOperation
        print(json.dumps({'status':'unresolved' if isinstance(exc,UnresolvedOperation) else 'failed',
                          'error':{'type':type(exc).__name__,'detail':str(exc)}}))
        return 2
