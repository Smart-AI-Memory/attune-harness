"""Structural controls for the independently identified Framework launcher."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

import test_memory_native_sdk as sdk_checks


@pytest.fixture
def framework_parent(monkeypatch, tmp_path):
    root = tmp_path / 'Frameworks' / 'Python.framework'
    prefix = root / 'Versions' / '3.12'
    base = prefix / 'bin' / 'python3.12'
    library = prefix / 'Python'
    bundle = prefix / 'Resources' / 'Python.app' / 'Contents' / 'MacOS' / 'Python'
    for path in (base, library, bundle):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'trusted parent runtime fixture')
    venv = tmp_path / 'venv'
    launcher = venv / 'bin' / 'python'
    launcher.parent.mkdir(parents=True)
    launcher.symlink_to(base)
    config = dict(home=str(base.parent), version='3.12.2', executable=str(base),
                  **{'include-system-site-packages': 'false'})
    config_path = venv / 'pyvenv.cfg'

    def write_config():
        config_path.write_text(''.join(f'{key} = {value}\n' for key, value in config.items()),
                               encoding='utf-8')

    write_config()
    parent = SimpleNamespace(
        platform='darwin', implementation=SimpleNamespace(name='cpython'),
        version_info=(3, 12, 2), prefix=str(venv), base_prefix=str(prefix),
        executable=str(launcher), _base_executable=str(base),
        orig_argv=[str(bundle), '-I', '-m', 'pytest'])
    build = dict(WITH_NEXT_FRAMEWORK=1, PYTHONFRAMEWORK='Python',
                 PYTHONFRAMEWORKINSTALLDIR=str(root), BINDIR=str(base.parent))
    monkeypatch.setattr(sdk_checks, 'os', SimpleNamespace(name='posix'))
    monkeypatch.setattr(sdk_checks, 'sys', parent)
    monkeypatch.setattr(sdk_checks, 'sysconfig', SimpleNamespace(get_config_var=build.get))
    requested = [str(launcher), '-I', '-B', '-c', 'trusted helper']
    runtime = {'python': str(launcher)}
    value = dict(runtime=runtime, base_executable=str(base), prefix=str(venv),
                 base_prefix=str(prefix), interpreter_argv=[str(bundle), *requested[1:]])
    return SimpleNamespace(parent=parent, build=build, base=base, library=library,
                           bundle=bundle, launcher=launcher, config=config,
                           write_config=write_config, requested=requested,
                           runtime=runtime, value=value)


def test_framework_argv_uses_parent_bundle_not_requested_launcher(framework_parent):
    case = framework_parent
    sdk_checks.validate_child_argv(case.value, case.requested, case.runtime)
    changed = deepcopy(case.value)
    changed['interpreter_argv'][0] = case.requested[0]
    with pytest.raises(AssertionError):
        sdk_checks.validate_child_argv(changed, case.requested, case.runtime)


@pytest.mark.parametrize('index', range(5))
def test_framework_argv_rejects_every_substituted_entry(framework_parent, index):
    case = framework_parent
    changed = deepcopy(case.value)
    changed['interpreter_argv'][index] = 'substituted-argv-entry'
    with pytest.raises(AssertionError):
        sdk_checks.validate_child_argv(changed, case.requested, case.runtime)


@pytest.mark.parametrize('field', ['runtime', 'base_executable', 'prefix', 'base_prefix'])
def test_framework_argv_rejects_changed_child_identity(framework_parent, field):
    case = framework_parent
    changed = deepcopy(case.value)
    changed[field] = {'python': 'other'} if field == 'runtime' else 'other'
    with pytest.raises(AssertionError):
        sdk_checks.validate_child_argv(changed, case.requested, case.runtime)


@pytest.mark.parametrize('length', [4, 6])
def test_framework_argv_rejects_changed_argument_count(framework_parent, length):
    case = framework_parent
    requested = case.requested[:length] if length == 4 else [*case.requested, 'extra']
    changed = deepcopy(case.value)
    changed['interpreter_argv'] = changed['interpreter_argv'][:length] if length == 4 else [
        *changed['interpreter_argv'], 'extra']
    with pytest.raises(AssertionError):
        sdk_checks.validate_child_argv(changed, requested, case.runtime)


@pytest.mark.parametrize('forgery', [
    'implementation', 'version', 'platform', 'framework-flag', 'framework-name',
    'framework-root', 'bindir', 'startup-argv', 'parent-executable', 'home',
    'venv-version', 'venv-executable', 'system-site', 'launcher-file',
    'launcher-target', 'base-link', 'library-link', 'bundle-link',
])
def test_framework_argv_rejects_forged_parent_or_layout(framework_parent, forgery):
    case = framework_parent
    if forgery == 'implementation':
        case.parent.implementation.name = 'pypy'
    elif forgery == 'version':
        case.parent.version_info = (3, 12, 3)
    elif forgery == 'platform':
        case.parent.platform = 'linux'
    elif forgery == 'framework-flag':
        case.build['WITH_NEXT_FRAMEWORK'] = 0
    elif forgery == 'framework-name':
        case.build['PYTHONFRAMEWORK'] = 'Other'
    elif forgery == 'framework-root':
        case.build['PYTHONFRAMEWORKINSTALLDIR'] = str(case.base.parent)
    elif forgery == 'bindir':
        case.build['BINDIR'] = str(case.bundle.parent)
    elif forgery == 'startup-argv':
        case.parent.orig_argv[0] = case.requested[0]
    elif forgery == 'parent-executable':
        case.parent.executable = str(case.base)
    elif forgery in ('home', 'venv-version', 'venv-executable', 'system-site'):
        key = {'home': 'home', 'venv-version': 'version', 'venv-executable': 'executable',
               'system-site': 'include-system-site-packages'}[forgery]
        case.config[key] = 'true' if forgery == 'system-site' else 'other'
        case.write_config()
    elif forgery == 'launcher-file':
        case.launcher.unlink()
        case.launcher.write_bytes(b'unrelated launcher')
    elif forgery == 'launcher-target':
        case.launcher.unlink()
        case.launcher.symlink_to(case.bundle)
    else:
        path = {'base-link': case.base, 'library-link': case.library,
                'bundle-link': case.bundle}[forgery]
        moved = path.with_name(path.name + '-moved')
        path.rename(moved)
        path.symlink_to(moved)
    with pytest.raises(AssertionError):
        sdk_checks.validate_child_argv(case.value, case.requested, case.runtime)
