"""Qualification evidence must come from a wheel and retain every failed gate."""

# qualify: platform

import base64
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    path = ROOT/'scripts'/f'{name}.py'
    spec = importlib.util.spec_from_file_location('review_'+name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def wheel_install(tmp_path, monkeypatch):
    """Real distribution metadata and RECORD parsing, without invoking an installer."""
    import attune_harness
    site = tmp_path/'site-packages'
    source = site/'attune_harness'
    source.mkdir(parents=True)
    metadata = site/'attune_harness-1.3.0.dist-info'
    metadata.mkdir()
    (metadata/'METADATA').write_text('Name: attune-harness\nVersion: 1.3.0\n')
    (metadata/'WHEEL').write_text('Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n')
    rows = []
    for name in ('__init__.py', 'worker.py'):
        path = source/name
        path.write_text('VALUE = 1\n')
        digest = base64.urlsafe_b64encode(hashlib.sha256(path.read_bytes()).digest()).decode().rstrip('=')
        rows.append(f'attune_harness/{name},sha256={digest},{path.stat().st_size}')
    (metadata/'RECORD').write_text('\n'.join(rows)+'\n')
    distribution = importlib.metadata.PathDistribution(metadata)
    monkeypatch.setattr(importlib.metadata, 'distribution', lambda _: distribution)
    monkeypatch.setattr(attune_harness, '__file__', str(source/'__init__.py'))
    return source, metadata


def test_noneditable_wheel_sources_are_accepted(wheel_install):
    source, metadata = wheel_install
    qualifier = load('qualify_platform')
    assert qualifier.installed_source() == source
    # A normal local-wheel URL is allowed; only editable directory provenance refuses.
    (metadata/'direct_url.json').write_text(json.dumps({'url': 'file:///candidate.whl'}))
    assert qualifier.installed_source() == source


@pytest.mark.parametrize('case', ['other-source', 'editable', 'no-wheel', 'changed',
                                 'unrecorded', 'missing-hash', 'symlink'])
def test_invalid_install_is_refused_before_output_or_dispatch(wheel_install, tmp_path, monkeypatch, case):
    import attune_harness
    source, metadata = wheel_install
    qualifier = load('qualify_platform')
    if case == 'other-source':
        other = tmp_path/'second-checkout'/'src'/'attune_harness'
        other.mkdir(parents=True)
        (other/'__init__.py').write_text('VALUE = 1\n')
        monkeypatch.setattr(attune_harness, '__file__', str(other/'__init__.py'))
    elif case == 'editable':
        (metadata/'direct_url.json').write_text(json.dumps({'url': 'file:///second-checkout',
                                                         'dir_info': {'editable': True}}))
    elif case == 'no-wheel':
        (metadata/'WHEEL').unlink()
    elif case == 'changed':
        (source/'worker.py').write_text('VALUE = 2\n')
    elif case == 'unrecorded':
        (source/'extra.py').write_text('VALUE = 1\n')
    elif case == 'missing-hash':
        text = (metadata/'RECORD').read_text().splitlines()
        text[1] = 'attune_harness/worker.py,,'
        (metadata/'RECORD').write_text('\n'.join(text)+'\n')
    else:
        target = tmp_path/'worker.py'
        target.write_text((source/'worker.py').read_text())
        (source/'worker.py').unlink()
        try:
            (source/'worker.py').symlink_to(target)
        except OSError:
            pytest.skip('Platform cannot create symlinks')

    def forbidden(*args, **kwargs):
        raise AssertionError('Qualification dispatched before refusing the install')

    monkeypatch.setattr(qualifier.subprocess, 'run', forbidden)
    output = tmp_path/'uncreated-output'
    with pytest.raises(ValueError):
        qualifier.qualify(output)
    assert not output.exists()


@pytest.mark.parametrize('pytest_exit,memory_exit,probe,expected', [
    (0, 0, 'passed', 0), (0, 3, 'passed', 3),
    (0, 0, 'missing', 1), (0, 0, 'failed', 1),
    (5, 0, 'passed', 5), (5, 3, 'missing', 5),
])
def test_receipt_exit_matches_final_verdict(tmp_path, monkeypatch, pytest_exit, memory_exit, probe, expected):
    qualifier = load('qualify_platform')
    source = tmp_path/'installed'
    source.mkdir()
    monkeypatch.setattr(qualifier, 'installed_source', lambda: source)
    monkeypatch.setattr(qualifier.importlib.metadata, 'version', lambda _: '1.3.0')
    output = tmp_path/'qualification'

    def run(argv, **kwargs):
        if '-m' in argv and 'pytest' in argv:
            if probe != 'missing':
                steps = {name: {'outcome': 'passed'} for name in qualifier.PROBE_STEPS}
                if probe == 'failed':
                    steps['bootstrap']['outcome'] = 'failed: injected'
                (output/'plugin-probe.json').write_text(json.dumps({'steps': steps}))
            return subprocess.CompletedProcess(argv, pytest_exit)
        if memory_exit == 0:
            memory = {'native_reader': 'available' if os.name == 'posix' else 'posix-only refusal',
                      'tiers_read': ['raw', 'personal', 'curated'] if os.name == 'posix' else [],
                      'reader_named': 'native'}
            journey = {'accept': 'accepted', 'build': 'completed', 'review': 'completed'}
            (output/'memory-redis.json').write_text(json.dumps({'memory': memory, 'journey': journey}))
        return subprocess.CompletedProcess(argv, memory_exit, stdout='injected', stderr='')

    monkeypatch.setattr(qualifier.subprocess, 'run', run)
    observed = qualifier.qualify(output)
    receipt = json.loads((output/'platform.json').read_text())
    assert observed == receipt['exit'] == expected
    assert receipt['pytest_exit'] == pytest_exit
    assert receipt['status'] == ('checks_passed' if expected == 0 else 'failed')


@pytest.mark.parametrize('name', ['check_installed', 'qualify_platform'])
@pytest.mark.parametrize('optimization,flag', [(1, 0), (0, 1)])
def test_optimized_driver_function_refuses_before_effects(tmp_path, name, optimization, flag):
    path = ROOT/'scripts'/f'{name}.py'
    namespace = {'__name__': 'optimized_guard_test', '__file__': str(path)}
    exec(compile(path.read_text(), str(path), 'exec', optimize=optimization), namespace)
    namespace['sys'] = SimpleNamespace(flags=SimpleNamespace(optimize=flag))

    def forbidden(*args, **kwargs):
        raise AssertionError('Optimized checks performed an effect')

    namespace['gui_release_checks'] = forbidden
    namespace['installed_source'] = forbidden
    output = tmp_path/'uncreated-output'
    with pytest.raises(ValueError, match='unoptimized Python'):
        if name == 'check_installed':
            namespace['check'](Path(sys.executable), 'core')
        else:
            namespace['qualify'](output)
    assert not output.exists()


@pytest.mark.parametrize('name', ['check_installed', 'qualify_platform'])
@pytest.mark.parametrize('selection', ['flag', 'environment'])
def test_optimized_cli_refuses_without_receipt(tmp_path, name, selection):
    output = tmp_path/'uncreated-output'
    options = (['--output', str(output)] if name == 'qualify_platform' else
               ['--python', str(tmp_path/'missing-python'), '--mode', 'core', '--report', str(output)])
    flags = ['-O'] if selection == 'flag' else []
    env = dict(os.environ, PYTHONOPTIMIZE='1' if selection == 'environment' else '0')
    result = subprocess.run([sys.executable, *flags, str(ROOT/'scripts'/f'{name}.py'), *options],
                            cwd=tmp_path, env=env, text=True, capture_output=True,
                            timeout=30 if sys.platform == 'win32' else 10)
    assert result.returncode != 0
    assert 'require' in result.stderr and 'unoptimized Python' in result.stderr
    assert not result.stdout and not output.exists()


@pytest.mark.parametrize('platform,expected_timeout', [('win32', 30), ('linux', 10), ('darwin', 10)])
@pytest.mark.parametrize('name', ['check_installed', 'qualify_platform'])
@pytest.mark.parametrize('selection', ['flag', 'environment'])
def test_optimized_cli_deadline_is_platform_specific(tmp_path, monkeypatch, platform,
                                                    expected_timeout, name, selection):
    calls = []

    def child(argv, **kwargs):
        calls.append(argv)
        assert kwargs['timeout'] == expected_timeout
        assert kwargs['cwd'] == tmp_path
        assert kwargs['text'] is True and kwargs['capture_output'] is True
        assert kwargs['env']['PYTHONOPTIMIZE'] == ('1' if selection == 'environment' else '0')
        assert ('-O' in argv) == (selection == 'flag')
        return SimpleNamespace(returncode=1, stderr='requires unoptimized Python', stdout='')

    # Replace this test module's bindings, not the host interpreter's platform.
    monkeypatch.setitem(globals(), 'sys', SimpleNamespace(executable=sys.executable, platform=platform))
    monkeypatch.setitem(globals(), 'subprocess', SimpleNamespace(run=child))
    test_optimized_cli_refuses_without_receipt(tmp_path, name, selection)
    assert len(calls) == 1
