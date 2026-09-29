"""``attune-harness init``: write a starter participant registry (first-run journey R1).

``plan``, ``review`` and ``fix`` all need a participant registry, and until
now nothing wrote one. ``init`` writes ``participants.json`` into a project
from a named profile, validated by the same reader every verb uses. It makes no
model call, reads no credentials and writes nothing outside the project.
Writing a native profile authorizes nothing: dispatch still needs
``--allow-external`` and ``--allow-native``.
"""

import json
import os
import shlex
import subprocess
from pathlib import Path

from .features import write_report
from .review_contract import validate_registry

REGISTRY = 'participants.json'
_EVIDENCE = {'tools': ['retrieve', 'verify'], 'max_turns': 3, 'max_tool_calls': 2}
_NATIVE = {**_EVIDENCE, 'review_mode': 'evidence', 'timeout': 300}

# Lead and reviewer on different models, as a required native review demands.
# The model IDs are the ones this repository's own registries use; edit the file to change them.
PROFILES = {
    'demo': {
        'lead': {'adapter': 'deterministic', **_EVIDENCE},
        'reviewer': {'adapter': 'deterministic', **_EVIDENCE},
    },
    'claude': {
        'lead': {'adapter': 'claude', 'model': 'claude-opus-5-5', **_NATIVE},
        'reviewer': {'adapter': 'claude', 'model': 'claude-fable-5-1', **_NATIVE},
    },
    'codex': {
        'lead': {'adapter': 'codex', 'model': 'gpt-6-astra', **_NATIVE},
        'reviewer': {'adapter': 'codex', 'model': 'gpt-5.6-sol', **_NATIVE},
    },
}


def quote(value) -> str:
    """One argument, quoted for the shell this platform's user types into."""
    return shlex.quote(str(value)) if os.name == 'posix' else subprocess.list2cmdline([str(value)])


def registry_next_action(project) -> str:
    """What to do when a verb has no participant registry."""
    return (f'Create one with: attune-harness init --project {quote(Path(project).absolute())} '
            f'(offline demo participants), or pass --config with an existing registry')


class RegistryMissing(ValueError):
    """A verb needs a participant registry and there is none; ``next_action`` says how to make one."""

    def __init__(self, path: Path, project: Path):
        how = ('' if Path(path).is_absolute()
               else f' (--config {str(path)!r} resolves against the working directory)')
        super().__init__(f'No participant registry at {Path(path).absolute()}{how}')
        self.next_action = registry_next_action(project)


def require_registry(path, project):
    """Refuse a missing registry in words that name ``init``; leave every other refusal to the reader."""
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        raise RegistryMissing(path, Path(project or Path.cwd()).absolute())


def add_command(sub):
    parser = sub.add_parser('init', help='Write a starter participant registry for plan, review and fix')
    parser.add_argument('--profile', choices=tuple(PROFILES), default='demo',
                        help='demo: offline deterministic participants (default); claude or codex: native models')
    parser.add_argument('--project', type=Path, help='Project directory (default: the current directory)')
    parser.add_argument('--force', action='store_true',
                        help='Replace an existing registry, keeping it as participants.json.bak')


def next_action(project: Path, target: Path, profile: str) -> str:
    command = (f'attune-harness review --goal "Check a document against project evidence" '
               f'--project {quote(project)} --config {quote(target)} --intake-only')
    if profile == 'demo':
        return f'Show the review intake form, offline: {command}'
    return (f'Show the review intake form: {command}. Running native participants needs '
            f'--allow-external (plan and build also need --allow-native), and may incur provider costs')


def execute(args) -> int:
    try:
        project = (args.project or Path.cwd()).absolute()
        if not project.is_dir():
            raise ValueError(f'Project is not a directory: {project}')
        target = project / REGISTRY
        registry = {'schema_version': 1, 'participants': PROFILES[args.profile]}
        validate_registry(registry, target)
        replaced = None
        if target.exists() or target.is_symlink():
            if not args.force:
                raise ValueError(f'A registry already exists at {target}; pass --force to replace it')
            backup = target.with_name(REGISTRY + '.bak')
            if backup.exists() or backup.is_symlink():
                raise ValueError(f'{backup} already exists; move it before replacing the registry')
            if target.is_symlink() or not target.is_file():
                raise ValueError(f'Not a regular file: {target}')
            # Copy, never move: the old registry stays in place until the new one replaces it
            # atomically, so no moment leaves the project without one. 'x' refuses a racing backup.
            with target.open('rb') as source, backup.open('xb') as copy:
                copy.write(source.read())
            replaced = str(backup)
        write_report(target, registry)
        native = args.profile != 'demo'
        print(json.dumps({
            'schema_version': 1, 'operation': 'init', 'status': 'created', 'path': str(target),
            'profile': args.profile, 'participants': sorted(registry['participants']),
            'requires': {'allow_external': native, 'allow_native': native},
            'replaced': replaced, 'next_action': next_action(project, target, args.profile),
        }, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({'schema_version': 1, 'operation': 'init', 'status': 'failed',
                          'error': {'type': type(exc).__name__, 'detail': str(exc)},
                          'next_action': 'Fix the reported problem and run attune-harness init again'}, indent=2))
        return 2
