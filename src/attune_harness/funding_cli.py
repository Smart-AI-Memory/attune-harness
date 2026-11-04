"""Explicit profile lifecycle commands; no implicit login from execution."""

import json
import time


def add_commands(sub):
    parser = sub.add_parser('funding', help='Connect, inspect or disconnect a private plan profile')
    actions = parser.add_subparsers(dest='funding_action', required=True)
    connect = actions.add_parser('connect', help='Open explicit plan consent and save credentials to Keychain')
    connect.add_argument('--name', required=True)
    connect.add_argument('--timeout', type=float, default=180)
    for name in ('inspect', 'disconnect'):
        child = actions.add_parser(name, help=('Inspect local metadata without contacting a provider' if
                                               name == 'inspect' else 'Disable the profile and revoke its app-owned grant'))
        child.add_argument('--profile-id', required=True)
        if name == 'disconnect': child.add_argument('--timeout', type=float, default=60)


def execute(args):
    from .plan_profiles import store
    try:
        if args.funding_action != 'inspect' and not 1 <= args.timeout <= 300:
            raise ValueError('Profile timeout must be 1..300 seconds')
        profiles = store()
        if args.funding_action == 'inspect':
            result = profiles.inspect(args.profile_id)
        elif args.funding_action == 'connect':
            result = profiles.connect(args.name, time.monotonic() + args.timeout)
        else:
            result = profiles.disconnect(args.profile_id, time.monotonic() + args.timeout)
        print(json.dumps({'schema_version': 1, 'status': 'completed', **result}, allow_nan=False))
        return 0
    except Exception:
        # Callback codes, raw account IDs and credential backend errors are private.
        print(json.dumps({'schema_version': 1, 'status': 'refused',
                          'error': 'Plan profile operation refused; inspect local profile state before retrying.'}))
        return 2
