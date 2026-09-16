"""CLI surfaces for the bounded evidence-review journey."""

import json
from pathlib import Path

from .features import FeatureUnavailable, report
from .review_contract import load_registry, review_form
from .review_store import inspect_run
from .recovery import UnresolvedOperation


def add_commands(sub):
    form = sub.add_parser('review-form', help='Render the accepted-request form for a participant registry')
    form.add_argument('--config', type=Path, default=Path('participants.json'),
                      help='Trusted participant registry (default: ./participants.json)')
    command = sub.add_parser('review', help='Review Markdown evidence with a lead, reviewer and scoped tools')
    command.add_argument('request', type=Path, nargs='?', help='Submitted legacy review-form JSON')
    command.add_argument('--config', type=Path,
                         help='Trusted participant registry (default: ./participants.json)')
    command.add_argument('--run-dir', type=Path, help='New directory for the durable legacy run record')
    command.add_argument('--allow-external', action='store_true',
                         help='Explicitly enable configured commands/native models, which may use credentials and incur costs')
    command.add_argument('--max-operations', type=int, help='Pause after this many newly completed operations (1–100)')
    command.add_argument('--allow-provider', action='store_true', help='Authorize accepted Voyage retrieval uploads/calls')
    from .task_cli import add_arguments
    add_arguments(command)
    inspect = sub.add_parser('inspect-review', help='Read a saved review without resuming or invoking participants')
    inspect.add_argument('run_dir', type=Path)
    resume = sub.add_parser('resume-review', help='Continue a matching checkpoint without repeating completed work')
    resume.add_argument('run_dir', type=Path)
    resume.add_argument('--request', type=Path, required=True)
    resume.add_argument('--config', type=Path, required=True)
    resume.add_argument('--checkpoint', required=True, help='checkpoint_digest from inspect-review')
    resume.add_argument('--allow-external', action='store_true')
    resume.add_argument('--max-operations', type=int)
    resume.add_argument('--allow-provider', action='store_true')
    reconcile = sub.add_parser('reconcile-review', help='Attach a recovered reply or authorize one known read-only retry')
    reconcile.add_argument('run_dir', type=Path)
    reconcile.add_argument('--checkpoint', required=True)
    reconcile.add_argument('--event', required=True, help='Unresolved event_id')
    resolution = reconcile.add_mutually_exclusive_group(required=True)
    resolution.add_argument('--reply', type=Path, help='Correlated participant reply JSON; never executes it')
    resolution.add_argument('--retry-read-only', action='store_true')
    transfer = sub.add_parser('transfer-review', help='Assign the lead role to another accepted participant')
    transfer.add_argument('run_dir', type=Path)
    transfer.add_argument('--checkpoint', required=True)
    transfer.add_argument('--lead', required=True)
    transfer.add_argument('--reason', required=True)
    cancel = sub.add_parser('cancel-review', help='Abandon a stopped run without claiming external effects were undone')
    cancel.add_argument('run_dir', type=Path)
    cancel.add_argument('--checkpoint', required=True)
    cancel.add_argument('--reason', required=True)


def execute(args) -> int:
    try:
        if args.command == 'review-form':
            result = report('review-form', 'ready', **review_form(load_registry(args.config)))
        elif args.command == 'inspect-review':
            result = inspect_run(args.run_dir)
        elif args.command == 'resume-review':
            from .recovery import resume_review
            result = resume_review(args.run_dir, args.request, args.config, args.checkpoint,
                                   allow_external=args.allow_external, allow_provider=args.allow_provider, max_operations=args.max_operations)
        elif args.command == 'reconcile-review':
            from .recovery import reconcile_review
            result = reconcile_review(args.run_dir, args.checkpoint, args.event,
                                      reply_file=args.reply, retry_read_only=args.retry_read_only)
        elif args.command == 'transfer-review':
            from .recovery import transfer_lead
            result = transfer_lead(args.run_dir, args.checkpoint, args.lead, args.reason)
        elif args.command == 'cancel-review':
            from .recovery import cancel_review
            result = cancel_review(args.run_dir, args.checkpoint, args.reason)
        else:
            from .review import review
            result = review(args.request, args.config, args.run_dir, allow_external=args.allow_external,
                            allow_provider=args.allow_provider, max_operations=args.max_operations)
    except FeatureUnavailable as exc:
        result = report(args.command, 'unavailable', error={'type': type(exc).__name__, 'detail': str(exc)})
    except Exception as exc:
        from .voyage_provider import PaidStageUnresolved
        result = report(args.command, 'unresolved' if isinstance(exc, (UnresolvedOperation, PaidStageUnresolved)) else 'failed',
                        error={'type': type(exc).__name__, 'detail': str(exc)})
    print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    if result['status'] == 'ready':
        return 0
    if result['status'] in ('paused', 'cancelled'):
        return 1
    if result['status'] == 'completed':
        return 0 if result['document_outcome'] == 'verified' and result['retrieval_outcome'] == 'retrieved' else 1
    return 2
