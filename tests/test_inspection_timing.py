"""Validate measurement inputs and schedules without collecting timing samples."""

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import py_compile
import random
import subprocess
import sys
from types import ModuleType, SimpleNamespace
import zipfile

import pytest


def write_utf8(path, value):
    """Keep disposable fixture bytes identical to the wheel's LF payload."""
    path.write_text(value, encoding='utf-8', newline='')


@pytest.fixture
def helper(monkeypatch):
    path = Path(__file__).resolve().parents[1] / 'scripts/measure_inspection_timing.py'
    spec = importlib.util.spec_from_file_location('inspection_timing_controls', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # These original controls use ModuleType fixtures, rather than entry processes.
    monkeypatch.setattr(module, 'require_fresh_process', lambda: None, raising=False)
    return module


def write_wheel(path, package, files, version='0.17.0', *, include_wheel=True):
    with zipfile.ZipFile(path, 'w') as wheel:
        for name, value in files.items():
            wheel.writestr(f'{package}/{name}', value)
        metadata = f'{package}-{version}.dist-info/'
        wheel.writestr(metadata + 'METADATA',
                       f'Name: {package.replace("_", "-")}\nVersion: {version}\n')
        if include_wheel:
            wheel.writestr(metadata + 'WHEEL', 'Wheel-Version: 1.0\nTag: py3-none-any\n')


@pytest.fixture
def forms_install(helper, tmp_path, monkeypatch):
    site = tmp_path / 'site-packages'
    package = site / 'attune_forms'
    files = {'__init__.py': 'NAME = "forms"\n',
             'render.py': 'VALUE = 1\n',
             'templates/preview.html': '<p>preview</p>\n'}
    for name, value in files.items():
        path = package / name
        path.parent.mkdir(parents=True, exist_ok=True)
        write_utf8(path, value)
    metadata = site / 'attune_forms-0.17.0.dist-info'
    metadata.mkdir()
    write_utf8(metadata / 'METADATA', 'Name: attune-forms\nVersion: 0.17.0\n')
    write_utf8(metadata / 'WHEEL', 'Wheel-Version: 1.0\nTag: py3-none-any\n')
    distribution = importlib.metadata.PathDistribution(metadata)
    module = ModuleType('attune_forms')
    module.__file__ = str(package / '__init__.py')
    module.__path__ = [str(package)]
    monkeypatch.setitem(sys.modules, 'attune_forms', module)
    original = importlib.metadata.distribution
    monkeypatch.setattr(importlib.metadata, 'distribution',
                        lambda name: distribution if name == 'attune-forms' else original(name))
    wheel = tmp_path / 'forms.whl'
    write_wheel(wheel, 'attune_forms', files)
    return SimpleNamespace(package=package, metadata=metadata, distribution=distribution,
                           module=module, wheel=wheel, files=files)


def preflight_args(helper, forms_install, tmp_path, monkeypatch):
    """Provide a matching Harness artifact so refusals exercise the Forms guard."""
    monkeypatch.setattr(helper, 'validate_output', lambda *args: None, raising=False)
    baseline = tmp_path / 'baseline'
    source = baseline / 'src/attune_harness'
    installed = tmp_path / 'harness-site/attune_harness'
    for root in (source, installed):
        root.mkdir(parents=True)
        write_utf8(root / '__init__.py', 'NAME = "harness"\n')
    metadata = installed.parent / 'attune_harness-1.5.0.dist-info'
    metadata.mkdir()
    write_utf8(metadata / 'METADATA', 'Name: attune-harness\nVersion: 1.5.0\n')
    write_utf8(metadata / 'WHEEL', 'Wheel-Version: 1.0\nTag: py3-none-any\n')
    distribution = importlib.metadata.PathDistribution(metadata)
    module = ModuleType('attune_harness')
    module.__file__ = str(installed / '__init__.py')
    module.__path__ = [str(installed)]
    monkeypatch.setitem(sys.modules, 'attune_harness', module)
    monkeypatch.setattr(importlib.metadata, 'distribution',
                        lambda name: forms_install.distribution if name == 'attune-forms'
                        else distribution)
    monkeypatch.setattr(helper, 'git', lambda root, *args:
                        b'pinned-revision\n' if args[0] == 'rev-parse' else b'')
    monkeypatch.setattr(helper, 'prepare',
                        lambda *args: pytest.fail('Measurement setup must not start'))
    wheel = tmp_path / 'harness.whl'
    write_wheel(wheel, 'attune_harness', {'__init__.py': 'NAME = "harness"\n'}, '1.5.0')
    return argparse.Namespace(baseline=baseline, revision='pinned-revision', wheel=wheel,
                              forms_wheel=forms_install.wheel, output=tmp_path / 'output',
                              repetitions=20, cold_repetitions=10, seed=20261022)


def test_forms_identity_covers_import_origin_artifact_and_package_data(helper, forms_install):
    identity = helper.forms_identity(forms_install.wheel)
    assert identity['version'] == '0.17.0'
    assert identity['imported_origin'] == str((forms_install.package / '__init__.py').resolve())
    assert identity['installed_package'] == str(forms_install.package.resolve())
    assert set(identity['files']) == set(forms_install.files)
    assert identity['files']['templates/preview.html'] == hashlib.sha256(
        forms_install.files['templates/preview.html'].encode()).hexdigest()
    assert identity['wheel_sha256'] == hashlib.sha256(forms_install.wheel.read_bytes()).hexdigest()


@pytest.mark.parametrize('case', ['editable', 'no-wheel', 'modified-python', 'modified-data',
                                 'extra-file', 'missing-file', 'shadowed-origin',
                                 'mismatched-artifact', 'wrong-version', 'artifact-no-wheel'])
def test_forms_refusals_precede_output_creation(helper, forms_install, tmp_path, monkeypatch, case):
    args = preflight_args(helper, forms_install, tmp_path, monkeypatch)
    if case == 'editable':
        write_utf8(forms_install.metadata / 'direct_url.json', json.dumps(
            {'dir_info': {'editable': True}, 'url': 'file:///disposable-source'}))
    elif case == 'no-wheel':
        (forms_install.metadata / 'WHEEL').unlink()
    elif case == 'modified-python':
        write_utf8(forms_install.package / 'render.py', 'VALUE = 2\n')
    elif case == 'modified-data':
        write_utf8(forms_install.package / 'templates/preview.html', '<p>changed</p>\n')
    elif case == 'extra-file':
        write_utf8(forms_install.package / 'unrecorded.py', 'VALUE = 1\n')
    elif case == 'missing-file':
        (forms_install.package / 'render.py').unlink()
    elif case == 'shadowed-origin':
        shadow = tmp_path / 'shadow/__init__.py'
        shadow.parent.mkdir()
        write_utf8(shadow, forms_install.files['__init__.py'])
        forms_install.module.__file__ = str(shadow)
    elif case == 'mismatched-artifact':
        write_wheel(forms_install.wheel, 'attune_forms',
                    {**forms_install.files, 'render.py': 'VALUE = 2\n'})
    elif case == 'wrong-version':
        write_wheel(forms_install.wheel, 'attune_forms', forms_install.files, '0.18.0')
    else:
        write_wheel(forms_install.wheel, 'attune_forms', forms_install.files, include_wheel=False)
    with pytest.raises(ValueError, match='attune-forms'):
        helper.measure(args)
    assert not args.output.exists()


def test_forms_artifact_is_retained_and_copy_drift_is_refused(helper, forms_install, tmp_path):
    identity = helper.forms_identity(forms_install.wheel)
    output = tmp_path / 'retained'
    output.mkdir()
    retained = helper.retain_forms_wheel(forms_install.wheel, output, identity['wheel_sha256'])
    assert retained.read_bytes() == forms_install.wheel.read_bytes()
    assert helper.forms_identity(retained) == identity
    write_wheel(forms_install.wheel, 'attune_forms',
                {**forms_install.files, 'render.py': 'VALUE = 2\n'})
    with pytest.raises(ValueError, match='changed while retaining'):
        helper.retain_forms_wheel(forms_install.wheel, output, identity['wheel_sha256'])


def test_worker_refuses_identity_drift_before_loading_timed_targets(
        helper, forms_install, tmp_path, monkeypatch):
    args = preflight_args(helper, forms_install, tmp_path, monkeypatch)
    harness_package = tmp_path / 'harness-site/attune_harness'
    harness_files = {'__init__.py': 'NAME = "harness"\n'}
    harness_before = fixture_package_identity(harness_package, args.wheel,
                                              harness_files, '1.5.0')
    monkeypatch.setattr(helper, 'load_targets',
                        lambda: pytest.fail('Timed targets must not load after identity drift'))
    with pytest.raises(ValueError, match='Worker attune-forms identity'):
        helper.worker({'forms_wheel': str(forms_install.wheel), 'forms_identity_digest': 'wrong',
                       'harness_wheel': str(args.wheel),
                       'harness_sources': harness_before['files'],
                       'harness_identity_digest': fixture_digest(harness_before)})


@pytest.mark.parametrize('repetitions', [2, 3, 19, 20, 21])
def test_warm_pairs_are_balanced_separately_from_the_first_pair(helper, repetitions):
    schedule = helper.pair_schedule(repetitions, 20261022)
    assert len(schedule) == repetitions + 1
    assert all(len(pair) == 2 and set(pair) == {False, True} for pair in schedule)
    warm_first = [pair[0] for pair in schedule[1:]]
    assert abs(warm_first.count(True) - warm_first.count(False)) <= 1
    if repetitions == 20:
        assert warm_first.count(True) == warm_first.count(False) == 10
    assert schedule[0] == helper.pair_schedule(2, 20261022)[0]


def test_pair_schedule_is_seeded_without_changing_global_random_state(helper):
    before = random.getstate()
    assert helper.pair_schedule(20, 20261022) == helper.pair_schedule(20, 20261022)
    assert helper.pair_schedule(20, 0)[1:] != helper.pair_schedule(20, 1)[1:]
    assert random.getstate() == before



def fixture_digest(value):
    """Compute the coordinator's declared digest without invoking its guards."""
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def fixture_package_identity(package, wheel, files, version):
    return {'version': version,
            'imported_origin': str((package / '__init__.py').resolve()),
            'installed_package': str(package.resolve()),
            'files': {name: hashlib.sha256(value.encode()).hexdigest()
                      for name, value in files.items()},
            'wheel_sha256': hashlib.sha256(wheel.read_bytes()).hexdigest()}


def git_fixture(root, *args):
    environment = {**os.environ, 'GIT_CONFIG_NOSYSTEM': '1',
                   'GIT_AUTHOR_NAME': 'Integrity Fixture',
                   'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
                   'GIT_COMMITTER_NAME': 'Integrity Fixture',
                   'GIT_COMMITTER_EMAIL': 'fixture@example.invalid'}
    return subprocess.run(['git', '--no-optional-locks', '-C', str(root), *args],
                          env=environment, check=True, capture_output=True).stdout


def padded_source(value):
    """Allow a malicious cache to have the source's exact timestamp and size."""
    assert len(value.encode()) < 1024
    return value + '#' * (1023 - len(value.encode())) + '\n'


@pytest.fixture
def real_install(tmp_path):
    """Build only fresh disposable packages, artifacts and a real Git baseline."""
    site = tmp_path / 'site'
    site.mkdir()
    packages, wheels, files, identities, executed = {}, {}, {}, {}, {}
    for package, version in [('attune_forms', '0.17.0'), ('attune_harness', '1.5.0')]:
        executed[package] = tmp_path / (package + '-executed')
        initializer = (f'from pathlib import Path\n'
                       f'Path({str(executed[package])!r}).write_text("source", encoding="utf-8")\n'
                       'from . import render\nVALUE = 1\n')
        payload = {'__init__.py': padded_source(initializer),
                   'render.py': padded_source('VALUE = 1\n')}
        if package == 'attune_harness':
            payload['test_change.py'] = (
                'def accept_test_task(*args, **kwargs): pass\n'
                'def create_test_task(*args, **kwargs): pass\n'
                'def execute_test_task(*args, **kwargs): pass\n'
                'def present_test_task(*args, **kwargs): pass\n')
        root = site / package
        for name, value in payload.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            write_utf8(path, value)
        metadata = site / f'{package}-{version}.dist-info'
        metadata.mkdir()
        write_utf8(metadata / 'METADATA',
                   f'Name: {package.replace("_", "-")}\nVersion: {version}\n')
        write_utf8(metadata / 'WHEEL', 'Wheel-Version: 1.0\nTag: py3-none-any\n')
        wheel = tmp_path / (package + '.whl')
        write_wheel(wheel, package, payload, version)
        packages[package], wheels[package], files[package] = root, wheel, payload
        identities[package] = fixture_package_identity(root, wheel, payload, version)
    baseline = tmp_path / 'baseline'
    harness_source = baseline / 'src/attune_harness'
    harness_source.mkdir(parents=True)
    for name, value in files['attune_harness'].items():
        write_utf8(harness_source / name, value)
    write_utf8(baseline / '.gitignore', '.ignored/\n')
    git_fixture(baseline, 'init', '-q')
    git_fixture(baseline, 'add', '.')
    git_fixture(baseline, '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Disposable baseline')
    revision = git_fixture(baseline, 'rev-parse', 'HEAD').decode().strip()
    return SimpleNamespace(site=site, baseline=baseline, revision=revision,
                           packages=packages, wheels=wheels, files=files,
                           identities=identities, executed=executed,
                           output=tmp_path / 'output', tmp_path=tmp_path)


CHILD_DRIVER = r"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

fixture = json.loads(sys.argv[2])
spec = importlib.util.spec_from_file_location('inspection_timing_child', sys.argv[1])
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
for entry in reversed(fixture['paths']):
    sys.path.insert(0, entry)
if fixture.get('preload'):
    __import__(fixture['preload'])

class BeforeSampling(Exception):
    pass

seen = {'target_loads': 0, 'prepare_calls': 0, 'initial_snapshot_output_exists': []}

def refuse_timer(*args, **kwargs):
    raise AssertionError('A measurement timer must not start in an integrity control')

def stop_targets():
    seen['target_loads'] += 1
    raise BeforeSampling('before-targets')

def stop_prepare(*args, **kwargs):
    seen['prepare_calls'] += 1
    raise BeforeSampling('before-prepare')

original_identity = helper.identity

def snapshot(root):
    if root.resolve() == Path(fixture['baseline']).resolve():
        seen['initial_snapshot_output_exists'].append(Path(fixture['output']).exists())
    return original_identity(root)

helper.time.perf_counter_ns = refuse_timer
helper.load_targets = stop_targets
helper.prepare = stop_prepare
helper.identity = snapshot
try:
    if fixture['entry'] == 'worker':
        helper.worker(fixture['config'])
    else:
        helper.measure(argparse.Namespace(
            baseline=Path(fixture['baseline']), revision=fixture['revision'],
            wheel=Path(fixture['harness_wheel']), forms_wheel=Path(fixture['forms_wheel']),
            output=Path(fixture['output']), repetitions=2, cold_repetitions=2, seed=20261022))
except BeforeSampling as error:
    seen.update(outcome='reached-sentinel', error=str(error))
except Exception as error:
    seen.update(outcome='refused', error_class=type(error).__name__, error=str(error))
else:
    seen.update(outcome='returned')
seen['loaded'] = sorted(name for name in sys.modules
                        if name == 'attune_forms' or name.startswith('attune_forms.')
                        or name == 'attune_harness' or name.startswith('attune_harness.'))
print(json.dumps(seen, sort_keys=True))
"""


def run_integrity_child(fixture, *, entry='coordinator', paths=None, output=None,
                        python_flags=('-I', '-B'), preload=None, environment=None):
    """Exercise real isolated entry points and stop before targets or timers."""
    helper_path = Path(__file__).resolve().parents[1] / 'scripts/measure_inspection_timing.py'
    # A missing -B control may write caches; keep even helper caches disposable.
    child_helper = fixture.tmp_path / 'child-helper.py'
    child_helper.write_bytes(helper_path.read_bytes())
    forms_before = fixture.identities['attune_forms']
    harness_before = fixture.identities['attune_harness']
    config = {'forms_wheel': str(fixture.wheels['attune_forms']),
              'forms_identity_digest': fixture_digest(forms_before),
              'harness_wheel': str(fixture.wheels['attune_harness']),
              'harness_sources': harness_before['files'],
              'harness_identity_digest': fixture_digest(harness_before)}
    payload = {'entry': entry, 'paths': [str(p) for p in (paths or [fixture.site])],
               'baseline': str(fixture.baseline), 'revision': fixture.revision,
               'output': str(output if output is not None else fixture.output),
               'harness_wheel': str(fixture.wheels['attune_harness']),
               'forms_wheel': str(fixture.wheels['attune_forms']), 'config': config,
               'preload': preload}
    result = subprocess.run([sys.executable, *python_flags, '-c', CHILD_DRIVER,
                             str(child_helper), json.dumps(payload)],
                            cwd=fixture.tmp_path, env=environment,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, (result.stdout, result.stderr)
    return json.loads(result.stdout)


def assert_package_refusal(result, package):
    assert result['outcome'] == 'refused', result
    assert result['error_class'] == 'ValueError', result
    assert package.replace('_', '-') in result['error'], result
    assert result['target_loads'] == result['prepare_calls'] == 0, result


def physical_files(root):
    """Include ignored files and Git index bytes, independently of Git status."""
    return {path.relative_to(root).as_posix(): (path.read_bytes(), path.stat().st_mode & 0o777)
            for path in root.rglob('*') if path.is_file()}


def install_shadow(fixture):
    shadow = fixture.tmp_path / 'shadow'
    package = shadow / 'attune_harness'
    package.mkdir(parents=True)
    for name, value in fixture.files['attune_harness'].items():
        write_utf8(package / name, value)
    return shadow


def poison_timestamp_cache(fixture, package, relative):
    source = fixture.packages[package] / relative
    original = source.read_bytes()
    marker = fixture.tmp_path / (package + '-' + relative + '-cache-executed')
    malicious = padded_source(
        f'from pathlib import Path\nPath({str(marker)!r}).write_text("cached", encoding="utf-8")\n'
        + original.decode().split('#', 1)[0])
    assert len(malicious.encode()) == len(original)
    write_utf8(source, malicious)
    timestamp = 1_700_000_000
    os.utime(source, (timestamp, timestamp))
    cache = Path(py_compile.compile(str(source), doraise=True,
                                    invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP))
    cache_bytes = cache.read_bytes()
    source.write_bytes(original)
    os.utime(source, (timestamp, timestamp))
    # Timestamp caches are intentional: -B prevents writes, but still reads these.
    assert source.stat().st_size == len(malicious.encode())
    return marker, cache, cache_bytes


@pytest.mark.parametrize('installed', ['matching', 'modified'])
def test_coordinator_refuses_matching_harness_shadow_before_output(real_install, installed):
    shadow = install_shadow(real_install)
    if installed == 'modified':
        write_utf8(real_install.packages['attune_harness'] / 'render.py',
                   padded_source('VALUE = 9\n'))
    result = run_integrity_child(real_install, paths=[shadow, real_install.site])
    assert_package_refusal(result, 'attune_harness')
    assert not any(path.exists() for path in real_install.executed.values()), result
    assert not real_install.output.exists()


@pytest.mark.parametrize('change', ['installed-drift', 'shadowed-origin', 'declared-identity'])
def test_worker_refuses_harness_identity_change_before_targets(real_install, change):
    paths = [real_install.site]
    if change == 'installed-drift':
        write_utf8(real_install.packages['attune_harness'] / 'render.py',
                   padded_source('VALUE = 9\n'))
    elif change == 'shadowed-origin':
        paths.insert(0, install_shadow(real_install))
    else:
        real_install.identities['attune_harness']['version'] = '0.0.0'
    result = run_integrity_child(real_install, entry='worker', paths=paths)
    assert_package_refusal(result, 'attune_harness')
    if change != 'declared-identity':
        assert not any(path.exists() for path in real_install.executed.values()), result
    assert not real_install.output.exists()


def test_clean_but_different_baseline_source_is_refused_before_import(real_install):
    write_utf8(real_install.baseline / 'src/attune_harness/render.py', padded_source('VALUE = 9\n'))
    git_fixture(real_install.baseline, 'add', '.')
    git_fixture(real_install.baseline, '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Different source')
    real_install.revision = git_fixture(real_install.baseline, 'rev-parse', 'HEAD').decode().strip()
    result = run_integrity_child(real_install)
    assert_package_refusal(result, 'attune_harness')
    assert not any(path.exists() for path in real_install.executed.values()), result
    assert not real_install.output.exists()


@pytest.mark.parametrize('entry', ['coordinator', 'worker'])
@pytest.mark.parametrize('package', ['attune_forms', 'attune_harness'])
@pytest.mark.parametrize('relative', ['__init__.py', 'render.py'])
def test_timestamp_valid_caches_refuse_before_either_package_executes(
        real_install, entry, package, relative):
    # Worker expectations were captured by the clean fixture before poisoning.
    marker, cache, before = poison_timestamp_cache(real_install, package, relative)
    result = run_integrity_child(real_install, entry=entry)
    assert not marker.exists(), result
    assert not any(path.exists() for path in real_install.executed.values()), result
    assert cache.read_bytes() == before
    assert_package_refusal(result, package)
    assert result['loaded'] == []
    assert not real_install.output.exists()


@pytest.mark.parametrize('entry', ['coordinator', 'worker'])
@pytest.mark.parametrize('package', ['attune_forms', 'attune_harness'])
def test_wheel_bytecode_payload_is_refused_before_package_import(real_install, entry, package):
    version = real_install.identities[package]['version']
    write_wheel(real_install.wheels[package], package,
                {**real_install.files[package], 'untrusted.pyc': b'not-source'}, version)
    # Keep the declared digest consistent with the wheel supplied to this child.
    real_install.identities[package]['wheel_sha256'] = hashlib.sha256(
        real_install.wheels[package].read_bytes()).hexdigest()
    result = run_integrity_child(real_install, entry=entry)
    assert_package_refusal(result, package)
    assert result['loaded'] == []
    assert not any(path.exists() for path in real_install.executed.values())
    assert not real_install.output.exists()


@pytest.mark.parametrize('case', ['equal', 'descendant', 'ignored', 'symlink-alias', 'git-storage'])
def test_output_overlap_refuses_before_physical_baseline_writes(real_install, case):
    baseline = real_install.baseline
    if case == 'equal':
        output = baseline
    elif case == 'descendant':
        output = baseline / 'new-parent/output'
    elif case == 'ignored':
        output = baseline / '.ignored/output'
    elif case == 'symlink-alias':
        alias = real_install.tmp_path / 'baseline-alias'
        try:
            alias.symlink_to(baseline, target_is_directory=True)
        except OSError:
            if os.name == 'nt':
                pytest.skip('This Windows account cannot create directory symlinks')
            raise
        output = alias / 'new-parent/output'
    else:
        output = baseline / '.git/new-parent/output'
    before = physical_files(baseline)
    result = run_integrity_child(real_install, output=output)
    assert physical_files(baseline) == before, result
    assert result['outcome'] == 'refused', result
    assert result['error_class'] == 'ValueError', result
    assert any(word in result['error'].lower() for word in ('output', 'baseline', 'git')), result
    assert result['prepare_calls'] == result['target_loads'] == 0
    assert result['loaded'] == []


def test_separate_git_storage_is_refused_before_output_writes(real_install):
    storage = real_install.tmp_path / 'external-git-storage'
    git_fixture(real_install.baseline, 'init', '-q', '--separate-git-dir', str(storage))
    output = storage / 'new-parent/output'
    before = physical_files(real_install.baseline), physical_files(storage)
    result = run_integrity_child(real_install, output=output)
    assert (physical_files(real_install.baseline), physical_files(storage)) == before, result
    assert result['outcome'] == 'refused', result
    assert result['error_class'] == 'ValueError', result
    assert 'git' in result['error'].lower(), result
    assert result['loaded'] == []
    assert not output.exists()


@pytest.mark.parametrize('case', ['git-dir', 'git-index', 'common-dir',
                                 'alternate-objects', 'symlink-objects'])
def test_effective_git_storage_is_refused_before_output_writes(real_install, case):
    external = real_install.tmp_path / 'external'
    git_fixture(real_install.baseline, 'clone', '--no-hardlinks', str(real_install.baseline),
                str(external))
    storage = external / '.git'
    environment = {name: value for name, value in os.environ.items() if not name.startswith('GIT_')}
    if case == 'alternate-objects':
        shared = real_install.tmp_path / 'shared-baseline'
        git_fixture(real_install.baseline, 'clone', '--shared', str(external), str(shared))
        real_install.baseline = shared
        storage /= 'objects'
    elif case == 'symlink-objects':
        objects = real_install.baseline / '.git/objects'
        storage = real_install.tmp_path / 'external-objects'
        objects.rename(storage)
        try:
            objects.symlink_to(storage, target_is_directory=True)
        except OSError:
            if os.name == 'nt':
                pytest.skip('This Windows account cannot create directory symlinks')
            raise
    elif case == 'common-dir':
        write_utf8(real_install.baseline / '.git/commondir', str(storage) + '\n')
    elif case == 'git-dir':
        environment.update(GIT_DIR=str(storage), GIT_WORK_TREE=str(real_install.baseline))
    else:
        environment['GIT_INDEX_FILE'] = str(storage / 'index')
    output = storage / 'new-parent/output'
    before = physical_files(real_install.baseline), physical_files(storage)
    result = run_integrity_child(real_install, output=output, environment=environment)
    assert (physical_files(real_install.baseline), physical_files(storage)) == before, result
    assert result['outcome'] == 'refused', result
    assert result['error_class'] == 'ValueError', result
    assert 'git' in result['error'].lower(), result
    assert result['prepare_calls'] == result['target_loads'] == 0
    assert result['loaded'] == []
    assert not output.exists()


@pytest.mark.parametrize('entry', ['coordinator', 'worker'])
def test_clean_real_packages_reach_only_pre_sampling_sentinels(real_install, entry):
    before = physical_files(real_install.baseline)
    result = run_integrity_child(real_install, entry=entry)
    assert result['outcome'] == 'reached-sentinel', result
    assert result['prepare_calls'] == (entry == 'coordinator')
    assert result['target_loads'] == (entry == 'worker')
    assert real_install.executed['attune_forms'].read_text(encoding='utf-8') == 'source'
    assert all(path.read_text(encoding='utf-8') == 'source'
               for path in real_install.executed.values() if path.exists())
    assert physical_files(real_install.baseline) == before
    if entry == 'coordinator':
        assert (real_install.output / 'metadata.json').is_file()
        assert (real_install.output / 'artifacts' / real_install.wheels['attune_forms'].name).is_file()
    else:
        assert not real_install.output.exists()


def test_sibling_output_initial_snapshot_precedes_output_writes(real_install):
    result = run_integrity_child(real_install)
    assert result['outcome'] == 'reached-sentinel', result
    assert result['initial_snapshot_output_exists'] == [False], result
    assert (real_install.output / 'metadata.json').is_file()


@pytest.mark.parametrize('entry', ['coordinator', 'worker'])
@pytest.mark.parametrize('case', ['without-isolation', 'without-bytecode-write-guard',
                                 'optimized', 'pycache-prefix',
                                 'preloaded-forms', 'preloaded-harness'])
def test_entry_refuses_unsafe_process_before_targets_or_output(real_install, entry, case):
    flags, preload = ['-I', '-B'], None
    if case == 'without-isolation':
        flags = ['-B']
    elif case == 'without-bytecode-write-guard':
        flags = ['-I']
    elif case == 'optimized':
        flags.append('-O')
    elif case == 'pycache-prefix':
        flags += ['-X', 'pycache_prefix=' + str(real_install.tmp_path / 'cache-prefix')]
    else:
        preload = 'attune_forms' if case == 'preloaded-forms' else 'attune_harness'
    result = run_integrity_child(real_install, entry=entry, python_flags=flags, preload=preload)
    assert result['outcome'] == 'refused', result
    assert result['error_class'] == 'ValueError', result
    assert result['prepare_calls'] == result['target_loads'] == 0
    assert not real_install.output.exists()
