"""Explicit environment grants for command participants, not an OS sandbox."""

from contextlib import contextmanager
import copy
import os
from pathlib import Path, PureWindowsPath
import re
import tempfile
import warnings

from .features import with_deprecation
from .review_contract import digest, fields

PROFILE = 'command-env-v1'
_NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_]{0,127}')
NOTICE = {
    'surface': 'command participant configuration',
    'form': 'omitted environment policy (full parent inheritance)',
    'since': '1.6.0', 'removal': '1.7.0',
    'replacement': 'Configure environment with profile command-env-v1 and explicit passthrough names.',
}
LEGACY_MESSAGE = ('This command uses legacy full parent environment inheritance. '
                  + NOTICE['replacement']
                  + f" Notice release: {NOTICE['since']}; earliest removal: {NOTICE['removal']}.")


class CommandEnvironmentDeprecationWarning(FutureWarning):
    """The selected command still uses the compatible inheritance behavior."""


def selected_configurations(record):
    """Select retained assignments, never every available registry participant."""
    if 'contract' in record and 'configuration' in record['contract']:
        return list(record['contract']['configuration']['participants'].values())
    request = record.get('request', {})
    if isinstance(request, dict) and 'registry' in request:
        roster = request['registry']['participants']
        if 'assignments' in request:
            names = [item['participant'] for item in request['assignments']]
        elif 'execution' in record:
            names = [item['participant_id'] for item in
                     record['execution']['recovery']['assignments'].values()]
        else:
            answers = request.get('answers', {})
            names = [answers.get(role) for role in ('assessor', 'reviewer')]
        return [roster[name] for name in dict.fromkeys(names) if name in roster]
    if 'registry' in record:
        roster = record['registry']['participants']
        assignments = record.get('recovery', {}).get('assignments', {})
        return [roster[item['participant_id']] for item in assignments.values()]
    return []


def annotate(envelope, configurations):
    """Decorate a display copy. Never save the result as an owner record."""
    if any(item['adapter'] == 'command' and 'environment' not in item for item in configurations):
        return with_deprecation(copy.deepcopy(envelope), NOTICE)
    return envelope


def notice_texts(envelope):
    """Render only this registered notice; unrelated deprecations keep their owner."""
    return [LEGACY_MESSAGE for notice in envelope.get('deprecations', []) if notice == NOTICE]


def validate(policy):
    """Validate names only, without reading or normalizing the parent environment."""
    fields(policy, ('profile', 'passthrough'))
    if policy['profile'] != PROFILE:
        raise ValueError('Unsupported command environment profile')
    names = policy['passthrough']
    if (not isinstance(names, list) or len(names) > 64
            or any(not isinstance(name, str) or not _NAME.fullmatch(name) for name in names)):
        raise ValueError('Command environment requires at most 64 portable variable names')
    if len({name.casefold() for name in names}) != len(names):
        raise ValueError('Command environment names must be distinct ignoring case')
    return policy


def _value(snapshot, name, windows):
    matches = ([value for key, value in snapshot.items()
                if isinstance(key, str) and key.casefold() == name.casefold()]
               if windows else ([snapshot[name]] if name in snapshot else []))
    if len(matches) != 1:
        raise ValueError(f'Command environment variable is missing or ambiguous: {name}')
    value = matches[0]
    if not isinstance(value, str) or '\x00' in value:
        raise ValueError(f'Command environment variable has an invalid value: {name}')
    return value


def _temporary_root(snapshot, windows, system_root, excluded):
    names = ('TEMP', 'TMP') if windows else ('TMPDIR', 'TMP', 'TEMP')
    selected = next((name for name in names if any(
        isinstance(key, str) and (key.casefold() == name.casefold() if windows else key == name)
        and value for key, value in snapshot.items())), None)
    raw = (_value(snapshot, selected, windows) if selected else
           str(PureWindowsPath(system_root) / 'Temp') if windows else '/tmp')
    try:
        root = Path(raw).resolve(strict=True)
        protected = [Path(path).resolve() for path in excluded]
        # resolve() preserves case on case-insensitive POSIX filesystems. Check
        # existing ancestors by filesystem identity as well as path spelling.
        ancestors = (root, *root.parents)
        if not root.is_dir() or any(
                root.is_relative_to(path) or (path.exists() and any(
                    ancestor.samefile(path) for ancestor in ancestors)) for path in protected):
            raise ValueError
    except (OSError, ValueError, RuntimeError):
        raise ValueError('Command scratch location must be an existing directory outside the work scope') from None
    return root


def absolute_executable(configuration, *, platform=None):
    """Return the configured executable only if it has a complete absolute path."""
    windows = (os.name if platform is None else platform) == 'nt'
    executable = configuration['command'][0]
    if not (PureWindowsPath(executable).is_absolute() if windows else Path(executable).is_absolute()):
        raise ValueError('Command environment profile requires an absolute initial executable')
    return executable


@contextmanager
def invocation(configuration, *, cwd, excluded_roots=(), parent=None, platform=None):
    """Build one invocation's map; keep scratch paths alive until its child stops.

    ``None`` remains the legacy runner's inheritance behavior. Injection points
    for parent/platform support synthetic tests; production takes a fresh copy
    only when the command is dispatched. No map or value hash is an audit field.
    """
    policy = configuration.get('environment')
    if 'environment' not in configuration:
        warnings.warn(LEGACY_MESSAGE, CommandEnvironmentDeprecationWarning, stacklevel=3)
        yield None, None
        return
    validate(policy)
    windows = (os.name if platform is None else platform) == 'nt'
    absolute_executable(configuration, platform=platform)
    snapshot = dict(os.environ if parent is None else parent)
    system_root = _value(snapshot, 'SystemRoot', True) if windows else None
    if windows and (not system_root or ';' in system_root or not PureWindowsPath(system_root).is_absolute()):
        raise ValueError('Windows command environment requires an absolute SystemRoot')
    search_path = (str(PureWindowsPath(system_root) / 'System32') + ';' + system_root
                   if windows else os.defpath)
    if windows and any(not entry or not PureWindowsPath(entry).is_absolute()
                       for entry in search_path.split(';')):
        raise ValueError('Windows command environment requires absolute baseline PATH entries')
    grants = {name: _value(snapshot, name, windows) for name in policy['passthrough']}
    root = _temporary_root(snapshot, windows, system_root, (cwd, *excluded_roots))
    try:
        temporary = tempfile.TemporaryDirectory(prefix='harness-command-', dir=root)
    except OSError:
        raise ValueError('Command scratch directories are unavailable') from None
    audit = {'profile': PROFILE, 'policy_digest': digest(policy), 'keys': []}
    try:
        directory = temporary.name
        home, scratch = Path(directory) / 'home', Path(directory) / 'tmp'
        try:
            home.mkdir()
            scratch.mkdir()
            environment = {
                'PATH': search_path,
                'HOME': str(home), 'TMPDIR': str(scratch), 'TMP': str(scratch), 'TEMP': str(scratch),
                'LANG': 'C', 'LC_ALL': 'C', 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8',
                'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1',
            }
            if windows:
                roaming, local = home / 'AppData' / 'Roaming', home / 'AppData' / 'Local'
                roaming.mkdir(parents=True)
                local.mkdir()
                environment.update(SystemRoot=system_root, WINDIR=system_root,
                                   USERPROFILE=str(home), APPDATA=str(roaming), LOCALAPPDATA=str(local))
        except OSError:
            raise ValueError('Command scratch directories are unavailable') from None
        for name, value in grants.items():
            canonical = next((key for key in environment if key.casefold() == name.casefold()), name) if windows else name
            environment[canonical] = value
        audit['keys'] = sorted(environment)
        yield environment, audit
    finally:
        # A cleanup failure cannot replace an owned child's result or exception.
        # Retain a value-free status instead of a path or the OS diagnostic.
        try:
            temporary.cleanup()
        except (OSError, RecursionError):
            audit['scratch_cleanup'] = 'failed'
