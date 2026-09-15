"""Lifecycle CLI for explicit, local data-only extension bundles."""

import json
from pathlib import Path

from .features import FeatureUnavailable, report


def add_commands(sub):
    command = sub.add_parser('extension', help='Inspect and manage a local skill/tool bundle')
    actions = command.add_subparsers(dest='action', required=True)
    discover = actions.add_parser('discover', help='Read a manifest without activating it')
    discover.add_argument('manifest', type=Path)
    install = actions.add_parser('install', help='Create a new disabled registration')
    install.add_argument('manifest', type=Path)
    install.add_argument('--state-dir', type=Path, required=True)
    for action in ('inspect', 'enable', 'disable', 'remove', 'replace'):
        parser = actions.add_parser(action)
        parser.add_argument('--state-dir', type=Path, required=True)
        if action != 'inspect':
            parser.add_argument('--checkpoint', required=True, help='state_digest from extension inspect')
        if action == 'replace':
            parser.add_argument('--manifest', type=Path, required=True)


def execute(args):
    from . import extensions
    try:
        if args.action == 'discover':
            result = report('extension', 'ready', bundle=extensions.discover(args.manifest))
        elif args.action == 'install':
            result = extensions.install(args.manifest, args.state_dir)
        elif args.action == 'inspect':
            result = extensions.inspect_extension(args.state_dir)
        else:
            result = extensions.mutate(args.state_dir, args.checkpoint, args.action,
                                       manifest=getattr(args, 'manifest', None))
    except Exception as exc:
        result = report('extension', 'unavailable' if isinstance(exc, FeatureUnavailable) else 'failed',
                        error={'type': type(exc).__name__, 'detail': str(exc)})
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 2 if result['status'] in ('failed', 'unavailable') else 0
