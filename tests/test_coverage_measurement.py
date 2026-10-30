"""Measurement must reach isolated children and reject incompatible evidence."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/measure_coverage.py'
spec = importlib.util.spec_from_file_location('measurement', SCRIPT)
measurement = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measurement)


@pytest.mark.parametrize('system,suite,partitioned,timeout', [
    ('Windows', 'platform', True, 2700), ('Linux', 'platform', False, 1080),
    ('Darwin', 'platform', False, 1080), ('Linux', 'full', False, 1200)])
@pytest.mark.parametrize('code', [0, 1, 124])
def test_only_windows_installed_coverage_selects_new_topology(tmp_path, monkeypatch, system, suite, partitioned, timeout, code):
    import attune_harness
    source, installed, site = tmp_path / 'project/src/attune_harness', tmp_path / 'installed', tmp_path / 'site'
    for folder in (source, installed, site):
        folder.mkdir(parents=True)
    for folder in (source, installed):
        (folder / '__init__.py').write_text('VALUE = 1\n')
    monkeypatch.setattr(attune_harness, '__file__', str(installed / '__init__.py'))
    monkeypatch.setattr(measurement, 'ROOT', source.parents[1])
    monkeypatch.setattr(measurement, 'SOURCE', source)
    monkeypatch.setattr(measurement, 'sys', SimpleNamespace(prefix='dedicated', base_prefix='base', executable=sys.executable))
    monkeypatch.setattr(measurement, 'sysconfig', SimpleNamespace(get_path=lambda _: str(site)))
    monkeypatch.setattr(measurement.platform, 'system', lambda: system)
    frozen = {'revision': 'c' * 40, 'sources': measurement.hashes(source), 'input_hashes': {},
              'coverage_version': measurement.VERSION, 'pytest_version': '9.1.1'}
    monkeypatch.setattr(measurement, 'identity', lambda: frozen)
    calls, validation, reports = [], [], []
    def child(argv, **kwargs):
        calls.append(argv)
        assert kwargs['timeout'] == timeout
        assert ('--installed-coverage-partitions' in argv) is partitioned
        return SimpleNamespace(returncode=code)
    monkeypatch.setattr(measurement, 'subprocess', SimpleNamespace(run=child, STDOUT=subprocess.STDOUT))
    monkeypatch.setattr(measurement, '_validate_installed_aggregate', lambda *args: validation.append(args) or {'control': True})
    monkeypatch.setattr(measurement, 'report', lambda *args: reports.append(args))
    output = tmp_path / 'evidence'
    assert measurement.measure(output, suite) == code
    receipt = json.loads((output / 'manifest.json').read_text())
    assert receipt['test_exit'] == code and receipt['input_drift'] is False
    assert len(calls) == 1 and len(validation) == int(partitioned and code == 0)
    assert len(reports) == int(not partitioned or code == 0)
    assert not (site / 'harness_measure_coverage.pth').exists()
    if partitioned:
        assert receipt['shared_test_budget_seconds'] == 2520
        assert receipt['execution_topology'] == 'two_supervised_installed_module_partitions'


def test_missing_installed_aggregate_is_durably_failed_before_coverage_report(tmp_path, monkeypatch):
    import attune_harness
    source, installed, site = tmp_path / 'project/src/attune_harness', tmp_path / 'installed', tmp_path / 'site'
    for folder in (source, installed, site):
        folder.mkdir(parents=True)
    for folder in (source, installed):
        (folder / '__init__.py').write_text('VALUE = 1\n')
    monkeypatch.setattr(attune_harness, '__file__', str(installed / '__init__.py'))
    monkeypatch.setattr(measurement, 'ROOT', source.parents[1])
    monkeypatch.setattr(measurement, 'SOURCE', source)
    monkeypatch.setattr(measurement, 'sys', SimpleNamespace(prefix='dedicated', base_prefix='base', executable=sys.executable))
    monkeypatch.setattr(measurement, 'sysconfig', SimpleNamespace(get_path=lambda _: str(site)))
    monkeypatch.setattr(measurement.platform, 'system', lambda: 'Windows')
    frozen = {'revision': 'c' * 40, 'sources': measurement.hashes(source), 'input_hashes': {},
              'coverage_version': measurement.VERSION, 'pytest_version': '9.1.1'}
    monkeypatch.setattr(measurement, 'identity', lambda: frozen)
    monkeypatch.setattr(measurement, 'subprocess', SimpleNamespace(
        run=lambda *args, **kwargs: SimpleNamespace(returncode=0), STDOUT=subprocess.STDOUT))
    def forbidden(*args):
        raise AssertionError('Missing aggregate reached coverage reporting')
    monkeypatch.setattr(measurement, 'report', forbidden)
    output = tmp_path / 'evidence'
    assert measurement.measure(output, 'platform') == 1
    receipt = json.loads((output / 'manifest.json').read_text())
    assert receipt['test_exit'] == 1 and receipt['aggregate_failure'] == 'FileNotFoundError'
    with pytest.raises(ValueError, match='failed'):
        measurement.compatible([receipt], frozen)


@pytest.mark.parametrize('deadline', [True, float('nan'), float('inf')])
def test_installed_identity_deadline_rejects_nonfinite_or_boolean_values(deadline):
    with pytest.raises(ValueError, match='finite'):
        measurement.identity(deadline=deadline)


@pytest.mark.parametrize('field', ['revision', 'sources', 'input_hashes',
                                   'coverage_version', 'pytest_version', 'test_exit', 'input_drift'])
def test_incompatible_or_failed_run_cannot_be_combined(field):
    expected = {'revision': 'a' * 40, 'sources': {'module.py': 'a' * 64},
                'input_hashes': {'tests/test_example.py': 'b' * 64},
                'coverage_version': measurement.VERSION, 'pytest_version': '9.1.1'}
    receipt = {**expected, 'test_exit': 0, 'input_drift': False}
    measurement.compatible([receipt], expected)
    receipt[field] = 1 if field == 'test_exit' else True if field == 'input_drift' else 'different'
    with pytest.raises(ValueError):
        measurement.compatible([receipt], expected)


def test_legacy_receipt_without_input_binding_is_incompatible():
    expected = {'revision': 'a' * 40, 'sources': {}, 'input_hashes': {},
                'coverage_version': measurement.VERSION, 'pytest_version': '9.1.1'}
    old = {'revision': expected['revision'], 'sources': {},
           'coverage_version': measurement.VERSION, 'test_exit': 0}
    with pytest.raises(ValueError, match='executed input bytes'):
        measurement.compatible([old], expected)


@pytest.mark.parametrize('name', ['tests/test_example.py', 'tests/fixtures/data.json',
                                  'scripts/qualify_platform.py', 'scripts/measure_coverage.py',
                                  'examples/a2a/peer.py', 'experiments/voyage/evaluate.py',
                                  'docs/receipts/sample.json', 'pyproject.toml',
                                  'conftest.py', '.pytest.toml', 'README.md',
                                  'participants.json',
                                  '.github/workflows/publish-pypi.yml',
                                  'plugin/attune-harness/manifest.json',
                                  'AGENTS.md'])
def test_same_revision_changed_execution_input_refuses_compatible_receipt(tmp_path, monkeypatch, name):
    root = tmp_path / 'checkout'
    root.mkdir()
    source = root / 'src/attune_harness'
    source.mkdir(parents=True)
    (source / 'module.py').write_text('VALUE = 1\n', encoding='utf-8')
    for path in ('tests/test_example.py', 'tests/fixtures/data.json',
                 'scripts/qualify_platform.py', 'scripts/measure_coverage.py',
                 'examples/a2a/peer.py', 'experiments/voyage/evaluate.py',
                 'docs/receipts/sample.json', 'pyproject.toml', 'conftest.py',
                 '.pytest.toml', 'README.md', 'participants.json',
                 '.github/workflows/publish-pypi.yml',
                 'plugin/attune-harness/manifest.json', 'AGENTS.md'):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('original\n', encoding='utf-8')
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(root), '-c', 'maintenance.auto=false',
                    '-c', 'commit.gpgsign=false', '-c', 'user.name=Fixture',
                    '-c', 'user.email=fixture@example.invalid',
                    'commit', '-qm', 'Identity baseline'], check=True)
    monkeypatch.setattr(measurement, 'ROOT', root)
    monkeypatch.setattr(measurement, 'SOURCE', source)
    frozen = measurement.identity()
    receipt = {**frozen, 'test_exit': 0, 'input_drift': False}
    measurement.compatible([receipt], frozen)
    (root / name).write_text('changed at same HEAD\n', encoding='utf-8')
    assert measurement.identity()['revision'] == frozen['revision']
    assert measurement.inputs_stable(frozen, source) is False
    with pytest.raises(ValueError, match='executed input bytes'):
        measurement.compatible([receipt], measurement.identity())


@pytest.mark.parametrize('name', ['tests/new_test.py', 'conftest.py', 'pytest.toml',
                                  'docs/new-fixture.md',
                                  'plugin/attune-harness/new.json',
                                  '.github/workflows/other.yml', 'setup.py'])
def test_new_untracked_input_changes_identity(tmp_path, monkeypatch, name):
    root = tmp_path / 'checkout'
    (root / 'tests').mkdir(parents=True)
    (root / 'scripts').mkdir()
    (root / 'examples').mkdir()
    (root / 'experiments').mkdir()
    (root / 'docs').mkdir()
    (root / 'src/attune_harness').mkdir(parents=True)
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    monkeypatch.setattr(measurement, 'ROOT', root)
    first = measurement.input_hashes()
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('new input\n', encoding='utf-8')
    second = measurement.input_hashes()
    assert name not in first
    assert second[name]


def test_symlinked_fixture_is_refused(tmp_path, monkeypatch):
    root = tmp_path / 'checkout'
    (root / 'tests').mkdir(parents=True)
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    target = tmp_path / 'outside.py'
    target.write_text('private = True\n', encoding='utf-8')
    try:
        (root / 'tests/foreign.py').symlink_to(target)
    except OSError:
        pytest.skip('Platform does not permit symlink creation')
    monkeypatch.setattr(measurement, 'ROOT', root)
    with pytest.raises(ValueError, match='symlinks'):
        measurement.input_hashes()


@pytest.mark.parametrize('suite', ['full', 'platform'])
@pytest.mark.parametrize('changed', ['checkout_test', 'installed_package'])
@pytest.mark.parametrize('system', ['Windows', 'Linux', 'Darwin'])
def test_successful_child_with_postrun_input_drift_retains_incompatible_receipt(tmp_path, monkeypatch, changed, suite, system):
    import attune_harness

    root = tmp_path / 'checkout'
    for part in ('tests', 'scripts', 'examples', 'experiments', 'docs',
                 'src/attune_harness'):
        (root / part).mkdir(parents=True)
    test = root / 'tests/test_example.py'
    test.write_text('def test_example(): pass\n', encoding='utf-8')
    source = root / 'src/attune_harness'
    (source / '__init__.py').write_text('VALUE = 1\n', encoding='utf-8')
    installed = tmp_path / 'installed/attune_harness'
    installed.mkdir(parents=True)
    (installed / '__init__.py').write_text('VALUE = 1\n', encoding='utf-8')
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(root), '-c', 'maintenance.auto=false',
                    '-c', 'commit.gpgsign=false', '-c', 'user.name=Fixture',
                    '-c', 'user.email=fixture@example.invalid',
                    'commit', '-qm', 'Identity baseline'], check=True)
    site = tmp_path / 'site'
    site.mkdir()
    monkeypatch.setattr(measurement, 'ROOT', root)
    monkeypatch.setattr(measurement, 'SOURCE', source)
    monkeypatch.setattr(attune_harness, '__file__', str(installed / '__init__.py'))
    monkeypatch.setattr(measurement, 'sys', SimpleNamespace(prefix='dedicated',
                        base_prefix='base', executable=sys.executable))
    monkeypatch.setattr(measurement, 'sysconfig', SimpleNamespace(get_path=lambda _: str(site)))
    monkeypatch.setattr(measurement, 'report', lambda *_: None)
    monkeypatch.setattr(measurement.platform, 'system', lambda: system)
    expected_timeout = {
        'full': {'Windows': 1200, 'Linux': 1200, 'Darwin': 1500},
        'platform': {'Windows': 2700, 'Linux': 1080, 'Darwin': 1080},
    }[suite][system]

    def successful_child(argv, **kwargs):
        assert ('--coverage-instrumented' in argv) == (suite == 'platform')
        assert kwargs['timeout'] == expected_timeout
        if changed == 'checkout_test':
            test.write_text('def test_example(): assert False\n', encoding='utf-8')
        else:
            (installed / '__init__.py').write_text('VALUE = 2\n', encoding='utf-8')
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(measurement, 'subprocess', SimpleNamespace(
        run=successful_child, check_output=subprocess.check_output,
        CalledProcessError=subprocess.CalledProcessError, STDOUT=subprocess.STDOUT))
    # Keep this existing serial-producer drift control independent of scheduling.
    # New default-topology controls exercise drift through the partition producer.
    monkeypatch.setattr(measurement, '_partitioned_full', lambda suite: False)
    output = tmp_path / 'result'
    frozen = measurement.identity()
    assert measurement.measure(output, suite) == 1
    receipt = json.loads((output / 'manifest.json').read_text())
    assert receipt['test_exit'] == 0
    assert receipt['input_drift'] is True
    if changed == 'installed_package':
        assert measurement.identity() == frozen  # Only the installed bytes moved.
    assert not (site / 'harness_measure_coverage.pth').exists()
    with pytest.raises(ValueError, match='input-drifted'):
        measurement.compatible([receipt], receipt)


def test_startup_hook_measures_scrubbed_and_isolated_children(tmp_path, monkeypatch):
    coverage = pytest.importorskip('coverage')
    venv = tmp_path / 'venv'
    subprocess.run([sys.executable, '-m', 'venv', '--without-pip', str(venv)], check=True)
    python = venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    site = Path(subprocess.check_output([str(python), '-c',
        'import sysconfig; print(sysconfig.get_path("purelib"))'], text=True).strip())
    # Supply the collector only to this disposable interpreter; no shared .pth edits.
    (site / 'collector_dependency.pth').write_text(str(Path(coverage.__file__).parent.parent)
                                                  + '\n', encoding='utf-8')
    target = tmp_path / 'target'
    target.mkdir()
    source = target / 'worker.py'
    source.write_text('import sys\nif "isolated" in sys.argv:\n    value = 1\nelse:\n    value = 2\n',
                      encoding='utf-8')
    monkeypatch.setattr(measurement, 'SOURCE', target)
    config = measurement.configuration(tmp_path, [])
    hook = site / 'harness_measure_coverage.pth'
    hook.write_text(measurement.startup_hook(config), encoding='utf-8')
    clean = {key: os.environ[key] for key in ['SystemRoot'] if key in os.environ}
    for flags, argument in [([], 'normal'), (['-I'], 'isolated')]:
        run = subprocess.run([str(python), *flags, str(source), argument], env=clean, check=True,
                             capture_output=True, text=True)
        assert run.stderr == ''
    unrelated = subprocess.run([str(python), '-c', 'print(42)'], env=clean, check=True,
                               capture_output=True, text=True)
    assert unrelated.stdout == '42\n'
    assert unrelated.stderr == ''
    collector = coverage.Coverage(config_file=str(config))
    collector.combine(keep=True)
    collector.save()
    _, statements, _, missing, _ = collector.analysis2(str(source))
    assert set(statements) == {1, 2, 3, 5}
    assert missing == []
    assert len(list(tmp_path.glob('.coverage.*'))) >= 2
    assert 'COVERAGE_PROCESS_START' not in clean
    assert 'COVERAGE_PROCESS_CONFIG' not in clean


@pytest.mark.parametrize('instrumented', [False, True])
@pytest.mark.parametrize('timed_out', [False, True])
@pytest.mark.parametrize('system', ['Windows', 'Linux', 'Darwin'])
def test_platform_timeout_preserves_qualification_boundary(tmp_path, monkeypatch, instrumented, timed_out, system):
    import attune_harness
    spec = importlib.util.spec_from_file_location('qualifier', SCRIPT.with_name('qualify_platform.py'))
    qualifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qualifier)
    installed = tmp_path / 'installed'
    installed.mkdir()
    (installed / '__init__.py').write_text('')
    monkeypatch.setattr(attune_harness, '__file__', str(installed / '__init__.py'))
    # This fixture exercises timeout accounting; wheel provenance has its own guard tests.
    monkeypatch.setattr(qualifier, 'installed_source', lambda: installed)
    output = tmp_path / 'result'
    calls = []
    monkeypatch.setattr(qualifier.platform, 'system', lambda: system)
    expected_timeout = 900
    if system == 'Windows':
        expected_timeout = 2520 if instrumented else 1800
    original_xml = (b'<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0">'
                    b'<testcase name="synthetic completed case"/></testsuite></testsuites>')
    original_log = b'original pytest output retained across controller timeout\n'

    def child(argv, **kwargs):
        calls.append(argv)
        if '-m' in argv:
            assert kwargs['timeout'] == expected_timeout
            assert 'faulthandler_timeout=0' in argv
            assert 'harness_qualification_stacks' in argv
            assert kwargs['env']['PYTHONPATH'] == str(qualifier.ROOT / 'scripts')
            (output / 'tests.xml').write_bytes(original_xml)
            kwargs['stdout'].write(original_log)
            kwargs['stdout'].flush()
            (output / 'plugin-probe.json').write_text(json.dumps({'steps': {
                step: {'outcome': 'passed'} for step in qualifier.PROBE_STEPS}}))
            if timed_out:
                raise subprocess.TimeoutExpired(argv, kwargs['timeout'])
            return subprocess.CompletedProcess(argv, 0)
        (output / 'memory-redis.json').write_text(json.dumps({
            'memory': {'native_reader': 'available' if os.name in ('posix', 'nt') else 'posix-only refusal',
                       'tiers_read': ['raw', 'personal', 'curated'] if os.name in ('posix', 'nt') else [],
                       'reader_named': 'native'},
            'journey': {'accept': 'accepted', 'build': 'completed', 'review': 'completed'}}))
        return subprocess.CompletedProcess(argv, 0, stdout='', stderr='')

    monkeypatch.setattr(qualifier, 'subprocess', SimpleNamespace(
        run=child, TimeoutExpired=subprocess.TimeoutExpired, CompletedProcess=subprocess.CompletedProcess,
        STDOUT=subprocess.STDOUT))
    kwargs = {'coverage_instrumented': True} if instrumented else {}
    assert qualifier.qualify(output, **kwargs) == (124 if timed_out else 0)
    receipt = json.loads((output / 'platform.json').read_text())
    assert receipt['suite_timeout_seconds'] == expected_timeout
    assert receipt['test_timings'].startswith('test-timings.jsonl;')
    assert len(calls) == (1 if timed_out else 2)
    assert receipt['pytest_exit'] == receipt['exit'] == (124 if timed_out else 0)
    assert receipt['command'] == calls[0]
    assert (output / 'tests.xml').read_bytes() == original_xml
    assert (output / 'tests.txt').read_bytes() == original_log
    if instrumented:
        assert receipt['status'] == ('instrumented_failed' if timed_out else 'instrumented_checks_passed')
        assert receipt['native_process_and_recovery'] == 'not_qualified_instrumented'
        assert receipt['instrumentation'] == 'coverage; not platform qualification'
    else:
        assert receipt['status'] == ('failed' if timed_out else 'checks_passed')
        assert receipt['native_process_and_recovery'] == ('failed' if timed_out else 'passed')
        assert 'instrumentation' not in receipt
    if timed_out:
        assert receipt['failure'] == 'suite_timeout'
        assert all(receipt[name] == 'unrun'
                   for name in ('memory_redis', 'native_memory_reader', 'r2_journey'))
        assert not (output / 'memory-redis.json').exists()
        assert not (output / 'memory-redis.txt').exists()
        failed = {**measurement.identity(), 'test_exit': 124, 'input_drift': False}
        with pytest.raises(ValueError, match='unfinished'):
            measurement.compatible([failed], measurement.identity())


def test_installed_library_job_budget_keeps_windows_suite_headroom():
    import yaml

    workflow = SCRIPT.parents[1] / '.github/workflows/qualification.yml'
    job = yaml.safe_load(workflow.read_text())['jobs']['installed-library']
    # The hosted budget includes setup/evidence time outside the child budget.
    # Both Windows Server versions must have 30 minutes of child headroom;
    # POSIX remains at 20 minutes.
    assert job['timeout-minutes'] == "${{ startsWith(matrix.os, 'windows-') && 35 || 20 }}"
    assert set(job['strategy']['matrix']['os']) == {
        'ubuntu-latest', 'macos-latest', 'windows-2022', 'windows-2025'}
    assert job['strategy']['matrix']['python'] == ['3.12']


def test_full_suite_covers_both_windows_servers_on_supported_python():
    import yaml

    workflow = SCRIPT.parents[1] / '.github/workflows/qualification.yml'
    job = yaml.safe_load(workflow.read_text())['jobs']['full-suite']
    assert job['timeout-minutes'] == "${{ startsWith(matrix.os, 'windows-') && 55 || 15 }}"
    windows_rows = {
        (row['os'], row['python'])
        for row in job['strategy']['matrix']['include']
        if row['os'].startswith('windows-')
    }
    assert windows_rows == {
        ('windows-2022', '3.12'), ('windows-2025', '3.12'),
    }


def test_coverage_job_budget_keeps_measurement_headroom():
    import yaml

    workflow = SCRIPT.parents[1] / '.github/workflows/coverage.yml'
    job = yaml.safe_load(workflow.read_text())['jobs']['measure']
    assert job['timeout-minutes'] == (
        "${{ matrix.os == 'windows-latest' && 50 || matrix.os == 'macos-latest' && 30 || 25 }}")


def test_darwin_full_timeout_finalizes_unfinished_receipt(tmp_path, monkeypatch):
    """Exercise the actual driver finalizer without waiting for its full budget."""
    import attune_harness

    root = tmp_path / 'checkout'
    source = root / 'src/attune_harness'
    installed = tmp_path / 'installed/attune_harness'
    for package in (source, installed):
        package.mkdir(parents=True)
        (package / '__init__.py').write_text('', encoding='utf-8')
    site = tmp_path / 'site'
    site.mkdir()
    hook = site / 'harness_measure_coverage.pth'
    monkeypatch.setattr(attune_harness, '__file__', str(installed / '__init__.py'))
    monkeypatch.setattr(measurement, 'ROOT', root)
    monkeypatch.setattr(measurement, 'SOURCE', source)
    monkeypatch.setattr(measurement, 'sys', SimpleNamespace(
        prefix='dedicated', base_prefix='base', executable=sys.executable))
    monkeypatch.setattr(measurement, 'sysconfig', SimpleNamespace(get_path=lambda _: str(site)))
    monkeypatch.setattr(measurement.platform, 'system', lambda: 'Darwin')
    # Exercise the retained serial finalizer; partition cancellation has real controls.
    monkeypatch.setattr(measurement, '_partitioned_full', lambda suite: False)
    frozen = {'revision': 'a' * 40, 'sources': measurement.hashes(source),
              'input_hashes': {}, 'coverage_version': measurement.VERSION,
              'pytest_version': '9.1.1'}
    monkeypatch.setattr(measurement, 'identity', lambda: frozen)
    checked, reported, calls = [], [], []

    def stable(frozen_input, installed_input):
        assert not hook.exists()  # Hook cleanup precedes the final input check.
        checked.append((frozen_input, installed_input))
        return True

    monkeypatch.setattr(measurement, 'inputs_stable', stable)
    monkeypatch.setattr(measurement, 'report', lambda *args: reported.append(args))
    failure = subprocess.TimeoutExpired('controlled full suite', 1500)

    def timed_out_child(argv, **kwargs):
        calls.append(argv)
        assert argv[1:4] == ['-m', 'pytest', '-q']
        assert kwargs['timeout'] == 1500
        assert hook.is_file()
        raise failure

    monkeypatch.setattr(measurement, 'subprocess', SimpleNamespace(
        run=timed_out_child, STDOUT=subprocess.STDOUT))
    output = tmp_path / 'result'
    with pytest.raises(subprocess.TimeoutExpired) as raised:
        measurement.measure(output, 'full')
    assert raised.value is failure
    assert len(calls) == 1
    assert checked == [(frozen, installed.resolve())] and reported == []
    receipt = json.loads((output / 'manifest.json').read_text())
    assert receipt['system'] == 'Darwin' and receipt['suite'] == 'full'
    assert receipt['test_exit'] is None and receipt['input_drift'] is False
    assert 'instrumented run is not platform qualification' in receipt['limits']
    assert not hook.exists() and not (output / 'summary.json').exists()
    with pytest.raises(ValueError, match='unfinished'):
        measurement.compatible([receipt], frozen)


@pytest.mark.parametrize('phase', ['setup', 'call', 'teardown'])
def test_full_measurement_timeout_retains_active_phase(tmp_path, monkeypatch, phase):
    """Exercise the full driver, keeping a killed run unusable as coverage."""
    if sys.prefix == sys.base_prefix:
        # The source-suite CI invokes base Python. Satisfy the real driver's
        # disposable-venv precondition without changing its admission guard.
        venv = tmp_path / 'driver-venv'
        subprocess.run([sys.executable, '-m', 'venv', '--without-pip', str(venv)],
                       check=True, timeout=30)
        python = venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        site = Path(subprocess.check_output([str(python), '-c',
            'import sysconfig; print(sysconfig.get_path("purelib"))'],
            text=True, timeout=10).strip())
        # Reuse pytest's dependencies read-only; install nothing into either host.
        (site / 'fixture_dependencies.pth').write_text(
            str(Path(pytest.__file__).resolve().parent.parent) + '\n', encoding='utf-8')
        subprocess.run([str(python), '-I', '-B', '-m', 'pytest', '-p', 'no:cacheprovider',
                        '-q', f'{Path(__file__).resolve()}::'
                        f'test_full_measurement_timeout_retains_active_phase[{phase}]',
                        '--basetemp=' + str(tmp_path / 'child-tests')],
                       cwd=SCRIPT.parent.parent, check=True, timeout=30,
                       env={**os.environ, 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
                            'PYTHONDONTWRITEBYTECODE': '1'})
        return
    import attune_harness

    root = tmp_path / 'checkout'
    scripts = root / 'scripts'
    scripts.mkdir(parents=True)
    (scripts / 'harness_qualification_stacks.py').write_bytes(
        (SCRIPT.parent / 'harness_qualification_stacks.py').read_bytes())
    source = root / 'src/attune_harness'
    installed = tmp_path / 'installed/attune_harness'
    for package in (source, installed):
        package.mkdir(parents=True)
        (package / '__init__.py').write_text('')
    monkeypatch.setattr(attune_harness, '__file__', str(installed / '__init__.py'))
    monkeypatch.setattr(measurement, 'ROOT', root)
    monkeypatch.setattr(measurement, 'SOURCE', source)
    # Preserve this actual serial phase-watchdog control and all its assertions.
    monkeypatch.setattr(measurement, '_partitioned_full', lambda suite: False)
    frozen = {'revision': 'a' * 40, 'sources': measurement.hashes(source),
              'input_hashes': {}, 'coverage_version': measurement.VERSION,
              'pytest_version': '9.1.1'}
    monkeypatch.setattr(measurement, 'identity', lambda: frozen)
    monkeypatch.setattr(measurement, 'inputs_stable', lambda *args: True)
    # Coverage's startup hook has separate installed-child tests. This case
    # exercises the real pytest driver and journal without changing this venv.
    purelib = tmp_path / 'purelib'
    purelib.mkdir()
    monkeypatch.setattr(measurement.sysconfig, 'get_path', lambda name: str(purelib))
    test = root / 'test_wait.py'
    wait = 'time.sleep(30)' if phase == 'call' else 'pass'
    fixture = ('import pytest\n@pytest.fixture\ndef stall():\n'
               + ('    time.sleep(30)\n' if phase == 'setup' else '')
               + '    yield\n'
               + ('    time.sleep(30)\n' if phase == 'teardown' else ''))
    test.write_text(f'import time\n{fixture}\ndef test_wait(stall):\n    {wait}\n')
    (root / 'pytest.ini').write_text('[pytest]\nharness_stack_timeout = 1\n')
    monkeypatch.setenv('PYTEST_DISABLE_PLUGIN_AUTOLOAD', '1')
    real_run = subprocess.run

    def bounded_child(argv, **kwargs):
        assert kwargs['timeout'] == (1500 if measurement.platform.system() == 'Darwin' else 1200)
        kwargs['timeout'] = 3  # Only this deliberately stalled fixture is short.
        return real_run(argv, **kwargs)

    monkeypatch.setattr(measurement, 'subprocess', SimpleNamespace(
        run=bounded_child, STDOUT=subprocess.STDOUT))
    output = tmp_path / 'result'
    with pytest.raises(subprocess.TimeoutExpired):
        measurement.measure(output, 'full')
    timings = [json.loads(line) for line in
               (output / 'test-timings.jsonl').read_text().splitlines()]
    assert timings[0]['event'] == 'suite_start'
    assert timings[-1]['event'] == 'phase_start' and timings[-1]['phase'] == phase
    assert timings[-1]['nodeid'].endswith('test_wait.py::test_wait')
    stacks = (output / 'slow-stacks.txt').read_text()
    assert f'File {str(test)!r},' in stacks
    assert ('in test_wait' if phase == 'call' else 'in stall') in stacks
    receipt = json.loads((output / 'manifest.json').read_text())
    assert receipt['test_exit'] is None and receipt['input_drift'] is False
    with pytest.raises(ValueError, match='unfinished'):
        measurement.compatible([receipt], frozen)
    assert not (output / 'summary.json').exists()
    assert not (purelib / 'harness_measure_coverage.pth').exists()


@pytest.mark.parametrize('phase', ['setup', 'call', 'teardown'])
def test_platform_timeout_keeps_active_stack_in_retained_log(tmp_path, phase):
    """Retain the Python watchdog's stack before the independent outer kill."""
    test = tmp_path / 'test_wait.py'
    wait = 'time.sleep(30)' if phase == 'call' else 'pass'
    fixture = ('import pytest\n@pytest.fixture\ndef stall():\n'
               + ('    time.sleep(30)\n' if phase == 'setup' else '')
               + '    yield\n'
               + ('    time.sleep(30)\n' if phase == 'teardown' else ''))
    test.write_text(f'import time\n{fixture}\ndef test_wait(stall):\n    {wait}\n')
    log = tmp_path / 'tests.txt'
    with log.open('wb') as stream:
        with pytest.raises(subprocess.TimeoutExpired):
            # Leave time for pytest to enter the selected phase before capture.
            subprocess.run([sys.executable, '-m', 'pytest', '-vv',
                            '-p', 'harness_qualification_stacks',
                            '-o', 'faulthandler_timeout=0',
                            '-o', 'harness_stack_timeout=2', str(test)],
                           cwd=tmp_path, stdout=stream, stderr=subprocess.STDOUT,
                           timeout=10, env={**os.environ, 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
                                            'PYTHONPATH': str(SCRIPT.parent),
                                            'HARNESS_QUALIFICATION_OUTPUT': str(tmp_path)})
    transcript = (tmp_path / 'slow-stacks.txt').read_text()
    assert 'Slow test Python stacks:' in transcript
    assert f'File {str(test)!r},' in transcript
    assert ('in test_wait' if phase == 'call' else 'in stall') in transcript
    assert 'End slow-test Python stacks' in transcript
    timings = [json.loads(line) for line in (tmp_path / 'test-timings.jsonl').read_text().splitlines()]
    assert timings[0]['event'] == 'suite_start'
    starts = [record for record in timings if record['event'] == 'case_start']
    assert len(starts) == 1 and starts[0]['nodeid'].endswith('test_wait.py::test_wait')
    assert timings[-1]['event'] == 'phase_start' and timings[-1]['phase'] == phase
    assert not any(record['event'] in ('case_end', 'suite_end') for record in timings)
    assert all(record['elapsed_seconds'] >= 0 for record in timings)
    assert [record['elapsed_seconds'] for record in timings] == sorted(
        record['elapsed_seconds'] for record in timings)


def test_timing_journal_retains_outcomes_durations_and_bypasses_capture(tmp_path):
    test = tmp_path / 'test_timing.py'
    test.write_text('''import pytest, time
@pytest.fixture
def bad_setup():
    raise RuntimeError('setup remains failed')
@pytest.fixture
def bad_teardown():
    yield
    raise RuntimeError('teardown remains failed')
def test_pass(capfd):
    # Leave margin for Python 3.10's coarse Windows monotonic clock.
    time.sleep(0.05)
    captured = capfd.readouterr()
    assert 'elapsed_seconds' not in captured.out + captured.err
def test_fail(): assert False, 'call remains failed'
def test_skip(): pytest.skip('skip remains skipped')
def test_setup(bad_setup): pass
def test_teardown(bad_teardown): pass
''')
    run = subprocess.run([sys.executable, '-m', 'pytest', '-q',
                          '-p', 'harness_qualification_stacks', '-o', 'faulthandler_timeout=0',
                          str(test)], cwd=tmp_path, capture_output=True, text=True, timeout=10,
                         env={**os.environ, 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
                              'PYTHONPATH': str(SCRIPT.parent),
                              'HARNESS_QUALIFICATION_OUTPUT': str(tmp_path)})
    assert run.returncode == 1, run.stdout + run.stderr
    timings = [json.loads(line) for line in (tmp_path / 'test-timings.jsonl').read_text().splitlines()]
    assert timings[0]['event'] == 'suite_start'
    assert timings[-1]['event'] == 'suite_end' and timings[-1]['exit_status'] == 1
    starts = [record['nodeid'] for record in timings if record['event'] == 'case_start']
    ends = [record for record in timings if record['event'] == 'case_end']
    assert len(starts) == 5 and [record['nodeid'] for record in ends] == starts
    assert all(record['duration_seconds'] >= 0 for record in ends)
    assert ends[0]['duration_seconds'] >= 0.02
    phases = {(record['nodeid'].split('::')[-1], record['phase']): record
              for record in timings if record['event'] == 'phase_end'}
    assert phases['test_pass', 'call']['outcome'] == 'passed'
    assert phases['test_pass', 'call']['duration_seconds'] >= 0.02
    assert phases['test_fail', 'call']['outcome'] == 'failed'
    assert phases['test_skip', 'call']['outcome'] == 'skipped'
    assert phases['test_setup', 'setup']['outcome'] == 'failed'
    assert phases['test_teardown', 'teardown']['outcome'] == 'failed'
    assert [record['elapsed_seconds'] for record in timings] == sorted(
        record['elapsed_seconds'] for record in timings)
    assert all(record['schema_version'] == 1 for record in timings)
    assert (tmp_path / 'slow-stacks.txt').read_bytes() == b''


@pytest.mark.parametrize('fails', [False, True])
def test_python_watchdog_handles_frame_churn_and_preserves_test_verdict(tmp_path, fails):
    test = tmp_path / 'test_churn.py'
    test.write_text('''import faulthandler, os, threading, time, types
from pathlib import Path
def template(): return 1
def test_churn(capsys):
    # The timed native walker must not be used, even for a slow test.
    def native_dump(*args, **kwargs):
        Path('native-called').write_text('called')
        raise AssertionError('native timed walker invoked')
    faulthandler.dump_traceback_later = native_dump
    stop = threading.Event()
    def churn():
        while not stop.is_set():
            types.FunctionType(template.__code__.replace(), {})()
    worker = threading.Thread(target=churn)
    worker.start()
    stack_log = Path(os.environ['HARNESS_QUALIFICATION_OUTPUT']) / 'slow-stacks.txt'
    deadline = time.monotonic() + 3.0
    try:
        while 'End slow-test Python stacks' not in stack_log.read_text():
            if time.monotonic() >= deadline:
                raise AssertionError('slow-stack watchdog did not finish its retained dump')
            time.sleep(0.01)
    finally:
        stop.set()
        worker.join()
    captured = capsys.readouterr()
    assert 'Slow test Python stacks:' not in captured.out + captured.err
''' + ('    assert False, "intentional failure remains a failure"\n' if fails else '') +
                    '\ndef test_fast(): pass\n')
    log = tmp_path / 'tests.txt'
    with log.open('wb') as stream:
        # Let the child enter the test body before the watchdog captures it.
        run = subprocess.run([sys.executable, '-m', 'pytest', '-vv',
                              '-p', 'harness_qualification_stacks',
                              '-o', 'faulthandler_timeout=0',
                              '-o', 'harness_stack_timeout=2', str(test)],
                             cwd=tmp_path, stdout=stream, stderr=subprocess.STDOUT, timeout=10,
                             env={**os.environ, 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
                                  'PYTHONPATH': str(SCRIPT.parent),
                                  'HARNESS_QUALIFICATION_OUTPUT': str(tmp_path)})
    assert run.returncode == (1 if fails else 0), log.read_text()
    transcript = (tmp_path / 'slow-stacks.txt').read_text()
    assert 'Slow test Python stacks: test_churn.py::test_churn' in transcript
    assert 'in test_churn' in transcript
    assert 'Slow test Python stacks: test_churn.py::test_fast' not in transcript
    assert not (tmp_path / 'native-called').exists()


def assert_timeout_journal_records_failed_session(directory):
    diagnostic_spec = importlib.util.spec_from_file_location(
        'timeout_diagnostic', SCRIPT.parent / 'diagnose_qualification.py')
    diagnostic = importlib.util.module_from_spec(diagnostic_spec)
    diagnostic_spec.loader.exec_module(diagnostic)
    (directory / 'platform.json').write_text(json.dumps({
        'schema_version': 1, 'status': 'failed', 'pytest_exit': 1, 'exit': 1}))
    result = diagnostic.diagnose(directory)
    assert result['classification'] == 'pytest_session_failed'
    assert result['timing_sequence_valid'] is True
    assert result['session_end']['exit_status'] == 1
    assert result['junit_counts']['failures'] + result['junit_counts']['errors'] == 1
    assert result['evidence_issues'] == []
    assert result['qualification_authority'] is False


@pytest.mark.parametrize('phase', ['setup', 'call'])
def test_future_timeout_keeps_worker_stack_before_teardown(tmp_path, phase):
    """A future can time out before the slow-test timer ever samples it."""
    test = tmp_path / 'test_future.py'
    test.write_text("""import concurrent.futures, threading, pytest
release = threading.Event()
entered = threading.Event()
def blocked_owner():
    entered.set()
    assert release.wait(5), 'fixture worker was not released'
@pytest.fixture
def owner():
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(blocked_owner)
    assert entered.wait(2)
    try:
        yield future
    finally:
        release.set()
        executor.shutdown(wait=True)
@pytest.fixture
def boundary(owner):
    PHASE_SETUP
    yield owner
def test_timeout(boundary):
    PHASE_CALL
""".replace('PHASE_SETUP', 'owner.result(timeout=0.05)' if phase == 'setup' else 'pass')
       .replace('PHASE_CALL', 'boundary.result(timeout=0.05)' if phase == 'call' else 'pass'))
    run = subprocess.run([sys.executable, '-m', 'pytest', '-q',
                          '-p', 'harness_qualification_stacks',
                          '-o', 'faulthandler_timeout=0',
                          '--junitxml=' + str(tmp_path / 'tests.xml'), str(test)],
                         cwd=tmp_path, capture_output=True, text=True, timeout=10,
                         env={**os.environ, 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
                              'PYTHONPATH': str(SCRIPT.parent),
                              'HARNESS_QUALIFICATION_OUTPUT': str(tmp_path)})
    assert run.returncode == 1, run.stdout + run.stderr
    assert 'TimeoutError' in run.stdout
    transcript = (tmp_path / 'slow-stacks.txt').read_text()
    assert 'test_future.py::test_timeout' in transcript
    assert 'in blocked_owner' in transcript
    assert 'End slow-test Python stacks' in transcript
    timings = [json.loads(line) for line in
               (tmp_path / 'test-timings.jsonl').read_text().splitlines()]
    snapshots = [row for row in timings if row['event'] == 'timeout_snapshot']
    assert len(snapshots) == 1 and snapshots[0]['phase'] == phase
    failed = [row for row in timings if row['event'] == 'phase_end'
              and row['phase'] == phase]
    assert len(failed) == 1 and failed[0]['outcome'] == 'failed'
    assert timings[-1]['event'] == 'suite_end' and timings[-1]['exit_status'] == 1
    assert_timeout_journal_records_failed_session(tmp_path)


@pytest.mark.parametrize('failure', ['stack', 'journal', 'both'])
def test_failed_timeout_diagnostic_preserves_original_verdict(tmp_path, failure):
    test = tmp_path / 'test_diagnostic_failure.py'
    test.write_text("""import pytest, harness_qualification_stacks as stacks
@pytest.fixture(autouse=True)
def break_diagnostic(request, monkeypatch):
    class BrokenStack:
        def write(self, data):
            raise OSError('private diagnostic detail')
    if FAILURE in ('stack', 'both'):
        monkeypatch.setattr(request.config, '_harness_stack_log', BrokenStack())
    real = stacks._timing
    def timing(config, event, **details):
        if event.startswith('timeout_snapshot') and FAILURE in ('journal', 'both'):
            raise OSError('private diagnostic detail')
        return real(config, event, **details)
    monkeypatch.setattr(stacks, '_timing', timing)
def test_timeout():
    raise TimeoutError('original timeout remains failed')
""".replace('FAILURE', repr(failure)))
    run = subprocess.run([sys.executable, '-m', 'pytest', '-q',
                          '-p', 'harness_qualification_stacks',
                          '-o', 'faulthandler_timeout=0',
                          '--junitxml=' + str(tmp_path / 'tests.xml'), str(test)],
                         cwd=tmp_path, capture_output=True, text=True, timeout=10,
                         env={**os.environ, 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
                              'PYTHONPATH': str(SCRIPT.parent),
                              'HARNESS_QUALIFICATION_OUTPUT': str(tmp_path)})
    assert run.returncode == 1, run.stdout + run.stderr
    assert 'original timeout remains failed' in run.stdout
    assert 'INTERNALERROR' not in run.stdout + run.stderr
    timings = [json.loads(line) for line in
               (tmp_path / 'test-timings.jsonl').read_text().splitlines()]
    assert timings[-1]['event'] == 'suite_end' and timings[-1]['exit_status'] == 1
    assert_timeout_journal_records_failed_session(tmp_path)
    snapshots = [row for row in timings if row['event'].startswith('timeout_snapshot')]
    if failure == 'stack':
        assert len(snapshots) == 1
        assert snapshots[0]['event'] == 'timeout_snapshot_failed'
        assert snapshots[0]['error_type'] == 'OSError'
        assert 'private diagnostic detail' not in json.dumps(timings)
    else:
        assert snapshots == []


def test_diagnostic_options_refuse_wrong_profiles_before_runtime_or_output(tmp_path, monkeypatch):
    output = tmp_path / 'uncreated'
    monkeypatch.setattr(measurement.platform, 'system', lambda: 'Darwin')
    for options, message in [({'windows_listing_witness': tmp_path / 'listing'}, 'Windows'),
                             ({'shutdown_boundary_diagnostics': tmp_path / 'shutdown'}, 'Linux')]:
        with pytest.raises(ValueError, match=message):
            measurement.measure(output, 'full', **options)
    assert not output.exists()


def test_default_startup_hook_bytes_are_preserved(tmp_path):
    config = tmp_path / 'coverage.ini'
    code = ('import atexit, coverage\n'
            'if coverage.Coverage.current() is None:\n'
            f'    collector = coverage.Coverage(config_file={str(config)!r})\n'
            '    collector.start()\n'
            '    atexit.register(collector.save)\n')
    assert measurement.startup_hook(config) == f'import builtins; exec({code!r})\n'
    assert measurement.startup_hook(config, None) == measurement.startup_hook(config)


@pytest.mark.parametrize('owner', [True, False])
def test_enabled_hook_preserves_existing_save_registration_position(tmp_path, monkeypatch, owner):
    import atexit
    import importlib.util
    events = []
    original_save = lambda: events.append('actual_save')
    wrapper = lambda: original_save()
    class Collector:
        save = staticmethod(original_save)
        def __init__(self, **kwargs):
            events.append('construct')
            atexit.register(self._atexit)
        @staticmethod
        def current(): return None
        def _atexit(self): pass
        def start(self): events.append('start')
    configured = []
    helper = SimpleNamespace(_configure_child_diagnostics=lambda c: configured.append(c),
                             _wrap_coverage_save=lambda save: wrapper if save is original_save else pytest.fail('different bound save'))
    spec = SimpleNamespace(name='harness_coverage_diagnostics', loader=SimpleNamespace(exec_module=lambda m: None))
    monkeypatch.setitem(sys.modules, 'coverage', SimpleNamespace(Coverage=Collector))
    monkeypatch.setattr(atexit, 'register', lambda callback: events.append(callback))
    monkeypatch.setattr(importlib.util, 'spec_from_file_location', lambda *args: spec)
    monkeypatch.setattr(importlib.util, 'module_from_spec', lambda spec: helper)
    monkeypatch.setitem(sys.modules, 'harness_coverage_diagnostics', None)
    context = {'parent_pid': os.getppid() if owner else -1, 'child_sink': str(tmp_path / 'child'), 'token': 'fixture'}
    exec(measurement.startup_hook(tmp_path / 'coverage.ini', context), {})
    assert events[0] == 'construct' and events[1].__name__ == '_atexit' and events[2] == 'start'
    assert len(events) == 4 and events[3] is (wrapper if owner else original_save)
    assert configured == ([context] if owner else [])


def test_hook_helper_failure_falls_back_to_same_save(tmp_path, monkeypatch):
    import atexit
    import importlib.util
    saved = []
    class Collector:
        @staticmethod
        def current(): return None
        def __init__(self, **kwargs): pass
        def start(self): pass
        def save(self): pass
    monkeypatch.setitem(sys.modules, 'coverage', SimpleNamespace(Coverage=Collector))
    monkeypatch.setattr(atexit, 'register', saved.append)
    def failed(*args): raise OSError('diagnostic-only loader failure')
    monkeypatch.setattr(importlib.util, 'spec_from_file_location', failed)
    exec(measurement.startup_hook(tmp_path / 'coverage.ini', {'parent_pid': os.getppid()}), {})
    assert len(saved) == 1 and saved[0].__func__ is Collector.save


@pytest.mark.parametrize('raises', [False, True])
def test_save_observer_forwards_same_call_return_and_exception(tmp_path, monkeypatch, raises):
    target = tmp_path / 'child.jsonl'; target.touch()
    measurement._configure_child_diagnostics({'parent_pid': os.getppid(), 'child_sink': str(target), 'token': 'synthetic'})
    calls = []
    result, error = object(), ValueError('original save failure')
    def save(*args, **kwargs):
        calls.append((args, kwargs))
        if raises: raise error
        return result
    wrapped = measurement._wrap_coverage_save(save)
    if raises:
        with pytest.raises(ValueError) as caught: wrapped('original', flush=True)
        assert caught.value is error
    else:
        assert wrapped('original', flush=True) is result
    assert calls == [(('original',), {'flush': True})]
    events = [json.loads(row)['event'] for row in target.read_text().splitlines()]
    assert events == ['coverage_explicit_save_enter', 'coverage_explicit_save_error' if raises else 'coverage_explicit_save_return']
    monkeypatch.setattr(measurement, '_child_diagnostic_context', None)
    monkeypatch.setattr(measurement, '_child_diagnostic_sink', None)


def test_sink_is_bounded_secondary_and_rechecks_fork_ownership(tmp_path, monkeypatch):
    target = tmp_path / 'sink.jsonl'; target.touch()
    sink = measurement._DiagnosticSink(target, 'synthetic', 'child', max_rows=2)
    sink.emit('one'); sink.emit('two'); sink.emit('three')
    assert sink.rows == 2
    raw = target.read_bytes()
    monkeypatch.setattr(measurement.os, 'getpid', lambda: sink.creator_pid + 1)
    sink.emit('fork_child')
    assert target.read_bytes() == raw
    monkeypatch.undo()
    sink.close()
    absent = tmp_path / 'missing'
    broken = measurement._DiagnosticSink(absent, 'synthetic', 'child')
    broken.emit('absent')
    assert broken.errors == 1 and not absent.exists()


def test_cached_child_sink_rechecks_parent_and_creator_pid(tmp_path, monkeypatch):
    target = tmp_path / 'child.jsonl'; target.touch()
    measurement._configure_child_diagnostics({'parent_pid': os.getppid(), 'child_sink': str(target), 'token': 'synthetic'})
    sink = measurement._child_sink()
    assert sink is not None
    with monkeypatch.context() as patch:
        patch.setattr(measurement.os, 'getppid', lambda: -1)
        assert measurement._child_sink() is None
        measurement._child_diagnostic_event('wrong_parent')
    with monkeypatch.context() as patch:
        patch.setattr(measurement.os, 'getpid', lambda: sink.creator_pid + 1)
        assert measurement._child_sink() is None
        sink.emit('fork_direct')
    sink.close()
    assert target.read_bytes() == b''
    monkeypatch.setattr(measurement, '_child_diagnostic_context', None)
    monkeypatch.setattr(measurement, '_child_diagnostic_sink', None)


@pytest.mark.parametrize('relative', ['output/nested', 'output', '.', 'project/diagnostics'])
def test_diagnostic_directory_cannot_be_in_fixture_or_checkout_chain(tmp_path, monkeypatch, relative):
    root, output = tmp_path / 'project', tmp_path / 'output'
    root.mkdir(); output.mkdir()
    monkeypatch.setattr(measurement, 'ROOT', root)
    with pytest.raises(ValueError, match='separate'):
        measurement._prepare_diagnostic_directory(tmp_path / relative, output, ('child.jsonl',))


def test_diagnostic_retention_copies_only_selected_bounded_files(tmp_path, monkeypatch):
    monkeypatch.setattr(measurement, 'ROOT', tmp_path / 'project')
    output = tmp_path / 'output'; output.mkdir()
    directory = measurement._prepare_diagnostic_directory(tmp_path / 'diagnostic', output, ('child.jsonl', 'large.jsonl'))
    (directory / 'child.jsonl').write_bytes(b'fixed\n')
    (directory / 'large.jsonl').write_bytes(b'x' * 33)
    (directory / 'unselected').write_text('not retained')
    result = measurement._retain_diagnostics(directory, output, ('child.jsonl', 'large.jsonl'), max_bytes=32)
    assert (output / 'child.jsonl').read_bytes() == b'fixed\n'
    assert result['large.jsonl'] == {'error_type': 'ValueError'}
    assert not (output / 'large.jsonl').exists() and not (output / 'unselected').exists()


@pytest.mark.parametrize('timed_out', [False, True])
def test_parent_observer_forwards_original_run_timeout_and_exception(tmp_path, monkeypatch, timed_out):
    events = []
    sink = SimpleNamespace(emit=lambda event, **fields: events.append((event, fields)))
    error = subprocess.TimeoutExpired(['synthetic'], 1200)
    class Process:
        def __init__(self, *args, **kwargs): self.pid, self.returncode = 42, None
        def __enter__(self): return self
        def __exit__(self, *args): self.returncode = -9 if timed_out else 0
        def _communicate(self, input, endtime, orig_timeout):
            if timed_out: raise error
            self.returncode = 0
            return (None, None)
        def communicate(self, input=None, timeout=None): return self._communicate(input, 1234.5, timeout)
        def kill(self): self.returncode = -9
        def wait(self, timeout=None): return self.returncode
    original_run = measurement.subprocess.run
    original_popen = Process
    monkeypatch.setattr(measurement.subprocess, 'Popen', original_popen)
    def run(argv, **kwargs):
        assert kwargs == {'timeout': 1200}
        with measurement.subprocess.Popen(argv) as child:
            try: child.communicate(timeout=kwargs['timeout'])
            except subprocess.TimeoutExpired:
                child.kill(); child.wait()
                raise
        return SimpleNamespace(returncode=child.returncode)
    monkeypatch.setattr(measurement.subprocess, 'run', run)
    if timed_out:
        with pytest.raises(subprocess.TimeoutExpired) as caught:
            measurement._observed_run(['synthetic'], sink=sink, timeout=1200)
        assert caught.value is error
    else:
        assert measurement._observed_run(['synthetic'], sink=sink, timeout=1200).returncode == 0
    assert measurement.subprocess.Popen is original_popen and measurement.subprocess.run is run
    assert ('parent_stdlib_deadline', {'deadline_monotonic': 1234.5, 'timeout_seconds': 1200}) in events
    assert events[-1][0] == ('parent_run_error' if timed_out else 'parent_run_return')


@pytest.mark.parametrize('hook,keyword', [('pytest_configure', 'config'), ('pytest_unconfigure', 'config'), ('pytest_sessionfinish', 'session')])
def test_shutdown_owner_preserves_keyword_calls(tmp_path, monkeypatch, hook, keyword):
    plugin_spec = importlib.util.spec_from_file_location('owner_keyword_control', SCRIPT.with_name('harness_qualification_stacks.py'))
    plugin = importlib.util.module_from_spec(plugin_spec); plugin_spec.loader.exec_module(plugin)
    path = tmp_path / 'child.jsonl'; path.touch()
    measurement._configure_child_diagnostics({'parent_pid': os.getppid(), 'child_sink': str(path), 'token': 'synthetic'})
    monkeypatch.setitem(sys.modules, 'harness_coverage_diagnostics', measurement)
    value, seen = object(), []
    def owner(**kwargs): seen.append(kwargs); return value
    owner.__name__ = hook
    config = SimpleNamespace(_harness_timing_epoch=1)
    subject = SimpleNamespace(config=config) if keyword == 'session' else config
    assert plugin._shutdown_owner(owner)(**{keyword: subject}) is value
    assert seen == [{keyword: subject}]
    measurement._child_diagnostic_sink.close()
    monkeypatch.setattr(measurement, '_child_diagnostic_context', None)
    monkeypatch.setattr(measurement, '_child_diagnostic_sink', None)


@pytest.mark.parametrize('fault', ['lookup', 'clock', 'emit'])
@pytest.mark.parametrize('raises', [False, True])
def test_shutdown_observation_failure_never_replaces_original_owner(tmp_path, monkeypatch, fault, raises):
    spec = importlib.util.spec_from_file_location('owner_failure_control', SCRIPT.with_name('harness_qualification_stacks.py'))
    plugin = importlib.util.module_from_spec(spec); spec.loader.exec_module(plugin)
    def broken(*args, **kwargs): raise OSError('synthetic observer failure')
    helper = SimpleNamespace(_child_sink=lambda: object(), _diagnostic_clock_ns=lambda: 10,
                             _child_diagnostic_event=lambda *args, **kwargs: None)
    setattr(helper, {'lookup': '_child_sink', 'clock': '_diagnostic_clock_ns', 'emit': '_child_diagnostic_event'}[fault], broken)
    monkeypatch.setitem(sys.modules, 'harness_coverage_diagnostics', helper)
    original_error, original_result, seen = ValueError('original owner refusal'), object(), []
    def owner(config):
        seen.append(config)
        if raises: raise original_error
        return original_result
    owner.__name__ = 'pytest_configure'
    config = SimpleNamespace()
    wrapped = plugin._shutdown_owner(owner)
    if raises:
        with pytest.raises(ValueError) as caught: wrapped(config)
        assert caught.value is original_error
    else:
        assert wrapped(config) is original_result
    assert seen == [config]


@pytest.mark.parametrize('refuses', [False, True])
def test_save_cleanup_diagnostic_lookup_cannot_replace_original_outcome(tmp_path, monkeypatch, refuses):
    target = tmp_path / 'child.jsonl'; target.touch()
    measurement._configure_child_diagnostics({'parent_pid': os.getppid(), 'child_sink': str(target), 'token': 'synthetic'})
    sink = measurement._child_sink()
    result, original_error, calls = object(), ValueError('original save refusal'), []
    def broken(): raise OSError('diagnostic cleanup lookup failed')
    def save():
        calls.append('save')
        monkeypatch.setattr(measurement, '_child_sink', broken)
        if refuses: raise original_error
        return result
    wrapped = measurement._wrap_coverage_save(save)
    try:
        if refuses:
            with pytest.raises(ValueError) as caught: wrapped()
            assert caught.value is original_error
        else:
            assert wrapped() is result
        assert calls == ['save']
    finally:
        sink.close()
        monkeypatch.setattr(measurement, '_child_diagnostic_context', None)
        monkeypatch.setattr(measurement, '_child_diagnostic_sink', None)


@pytest.mark.parametrize('refuses', [False, True])
def test_save_cleanup_diagnostic_close_cannot_replace_original_outcome(tmp_path, monkeypatch, refuses):
    target = tmp_path / 'child.jsonl'; target.touch()
    measurement._configure_child_diagnostics({'parent_pid': os.getppid(), 'child_sink': str(target), 'token': 'synthetic'})
    sink = measurement._child_sink(); original_close = sink.close
    result, original_error, calls = object(), ValueError('original save refusal'), []
    def broken(): raise OSError('diagnostic close failed')
    monkeypatch.setattr(sink, 'close', broken)
    def save():
        calls.append('save')
        if refuses: raise original_error
        return result
    wrapped = measurement._wrap_coverage_save(save)
    try:
        if refuses:
            with pytest.raises(ValueError) as caught: wrapped()
            assert caught.value is original_error
        else:
            assert wrapped() is result
        assert calls == ['save']
    finally:
        original_close()
        monkeypatch.setattr(measurement, '_child_diagnostic_context', None)
        monkeypatch.setattr(measurement, '_child_diagnostic_sink', None)


@pytest.mark.parametrize('event,scenario', [('parent_launch_return', 'normal'), ('parent_kill_enter', 'timeout'),
    ('parent_context_exit_enter', 'owner_error'), ('parent_run_return', 'normal'), ('parent_communicate_error', 'timeout')])
@pytest.mark.parametrize('fault', ['lookup', 'call'])
def test_parent_diagnostic_failure_preserves_original_action_map_and_identity(tmp_path, monkeypatch, event, scenario, fault):
    import threading
    real_run = measurement.subprocess.run
    original_error = subprocess.TimeoutExpired(['synthetic'], 1200) if scenario == 'timeout' else ValueError('original owner refusal')
    actions, captured, observations = [], {}, []
    class Owner:
        def __init__(self, argv, **kwargs): self.args, self.pid, self.returncode = argv, 41, None; actions.append('launch')
        def __enter__(self): actions.append('enter'); return self
        def communicate(self, input=None, timeout=None):
            actions.append('communicate')
            endtime = None if timeout is None else 10 + timeout
            return self._communicate(input, endtime, timeout)
        def _communicate(self, input, endtime, orig_timeout):
            actions.append('communicate_impl')
            if self.returncode is not None:
                return None, None
            if scenario != 'normal': raise original_error
            self.returncode = 0
            return None, None
        def poll(self): actions.append('poll'); return self.returncode
        def kill(self): actions.append('kill'); self.returncode = -9
        def wait(self, timeout=None): actions.append('wait'); return self.returncode
        def __exit__(self, *args): actions.append('exit'); self.wait()
    class Sink:
        def __getattribute__(self, key):
            if key == 'emit' and fault == 'lookup': raise OSError('diagnostic attribute failure')
            return object.__getattribute__(self, key)
        def emit(self, label, **fields):
            observations.append(label)
            if fault == 'call' and label == event: raise OSError('diagnostic event failure')
    monkeypatch.setattr(measurement.subprocess, 'Popen', Owner)
    try:
        baseline = real_run(['synthetic'], timeout=1200)
    except BaseException as error:
        assert error is original_error
    baseline_actions = list(actions); actions.clear()
    def original_spy(*args, **kwargs):
        try: returned = real_run(*args, **kwargs)
        except BaseException as error:
            captured['error'] = error
            raise
        captured['result'] = returned
        return returned
    monkeypatch.setattr(measurement.subprocess, 'run', original_spy)
    monkeypatch.setattr(measurement, '_diagnostic_run_lock', threading.Lock())
    if scenario != 'normal':
        with pytest.raises(type(original_error)) as caught:
            measurement._observed_run(['synthetic'], sink=Sink(), timeout=1200)
        assert caught.value is original_error and captured['error'] is original_error
    else:
        result = measurement._observed_run(['synthetic'], sink=Sink(), timeout=1200)
        assert result is captured['result'] and result.returncode == baseline.returncode
    assert actions == baseline_actions
    assert measurement.subprocess.Popen is Owner and measurement.subprocess.run is original_spy
    assert not measurement._diagnostic_run_lock.locked()


def test_parent_diagnostic_field_construction_is_inside_best_effort_boundary(monkeypatch):
    called = []
    def broken_fields(): raise OSError('synthetic optional field lookup failed')
    sink = SimpleNamespace(emit=lambda *args, **kwargs: called.append((args, kwargs)))
    assert measurement._diagnostic_call(sink, 'emit', event='synthetic', details=broken_fields) is None
    assert called == []
    original = KeyboardInterrupt('original interruption')
    def interrupted(*args, **kwargs): raise original
    with pytest.raises(KeyboardInterrupt) as caught:
        measurement._diagnostic_call(SimpleNamespace(emit=interrupted), 'emit', event='synthetic')
    assert caught.value is original


@pytest.mark.parametrize('scenario', ['normal', 'timeout'])
@pytest.mark.parametrize('fault', ['close_lookup', 'close_call', 'retention'])
def test_parent_optional_cleanup_cannot_block_original_measurement_finalizer(tmp_path, monkeypatch, scenario, fault):
    import attune_harness
    source, installed, site = tmp_path / 'project/src/attune_harness', tmp_path / 'installed', tmp_path / 'site'
    for folder in (source, installed, site): folder.mkdir(parents=True)
    for folder in (source, installed): (folder / '__init__.py').write_text('VALUE = 1\n')
    monkeypatch.setattr(attune_harness, '__file__', str(installed / '__init__.py'))
    monkeypatch.setattr(measurement, 'ROOT', source.parents[1]); monkeypatch.setattr(measurement, 'SOURCE', source)
    monkeypatch.setattr(measurement, 'sys', SimpleNamespace(prefix='dedicated', base_prefix='base', executable=sys.executable))
    monkeypatch.setattr(measurement, 'sysconfig', SimpleNamespace(get_path=lambda _: str(site)))
    monkeypatch.setattr(measurement.platform, 'system', lambda: 'Linux')
    frozen = {'revision': 'synthetic', 'sources': measurement.hashes(source)}
    monkeypatch.setattr(measurement, 'identity', lambda: frozen)
    actions, opened = [], []
    monkeypatch.setattr(measurement, 'inputs_stable', lambda *args: actions.append('stability') or True)
    monkeypatch.setattr(measurement, 'report', lambda *args: actions.append('report'))
    timeout = subprocess.TimeoutExpired(['synthetic'], 1200)
    def owner(argv, **kwargs):
        actions.append('owner')
        assert kwargs['timeout'] == 1200
        if scenario == 'timeout': raise timeout
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(measurement, '_observed_run', owner)
    original = measurement._DiagnosticSink
    class Sink:
        def __init__(self, *args, **kwargs): self.backing = original(*args, **kwargs); opened.append(self.backing)
        def __getattribute__(self, name):
            if name == 'close' and fault == 'close_lookup': raise OSError('diagnostic close lookup')
            return object.__getattribute__(self, name)
        def close(self):
            if fault == 'close_call': raise OSError('diagnostic close call')
            self.backing.close()
    monkeypatch.setattr(measurement, '_DiagnosticSink', Sink)
    if fault == 'retention':
        def broken(*args, **kwargs): raise OSError('diagnostic retention failed')
        monkeypatch.setattr(measurement, '_retain_diagnostics', broken)
    output = tmp_path / 'output'
    try:
        if scenario == 'timeout':
            with pytest.raises(subprocess.TimeoutExpired) as caught:
                measurement.measure(output, 'full', shutdown_boundary_diagnostics=tmp_path / 'external')
            assert caught.value is timeout
        else:
            assert measurement.measure(output, 'full', shutdown_boundary_diagnostics=tmp_path / 'external') == 0
        assert not (site / 'harness_measure_coverage.pth').exists()
        receipt = json.loads((output / 'manifest.json').read_text())
        assert receipt['input_drift'] is False and receipt['test_exit'] == (None if scenario == 'timeout' else 0)
        assert actions == (['owner', 'stability'] if scenario == 'timeout' else ['owner', 'stability', 'report'])
        if fault == 'retention': assert receipt['shutdown_diagnostic_files'] == {'retention_error_type': 'OSError'}
    finally:
        for sink in opened: sink.close()
@pytest.mark.parametrize('system,suite,code', [
    ('Windows', 'platform', 0), ('Windows', 'platform', 1),
    ('Linux', 'platform', 0), ('Darwin', 'platform', 0), ('Linux', 'full', 0)])
def test_measurement_runtime_namespace_is_external_only_for_windows_partitions(
        tmp_path, monkeypatch, system, suite, code):
    import attune_harness

    source, installed, site = tmp_path / 'checkout/src/attune_harness', tmp_path / 'installed', tmp_path / 'site'
    for folder in (source, installed, site):
        folder.mkdir(parents=True)
    for folder in (source, installed):
        (folder / '__init__.py').write_text('VALUE = 1\n')
    monkeypatch.setattr(attune_harness, '__file__', str(installed / '__init__.py'))
    monkeypatch.setattr(measurement, 'ROOT', source.parents[1])
    monkeypatch.setattr(measurement, 'SOURCE', source)
    monkeypatch.setattr(measurement, 'sys', SimpleNamespace(
        prefix='dedicated', base_prefix='base', executable=sys.executable))
    monkeypatch.setattr(measurement, 'sysconfig', SimpleNamespace(get_path=lambda _: str(site)))
    monkeypatch.setattr(measurement.platform, 'system', lambda: system)
    frozen = {'revision': 'c' * 40, 'sources': measurement.hashes(source), 'input_hashes': {},
              'coverage_version': measurement.VERSION, 'pytest_version': '9.1.1'}
    monkeypatch.setattr(measurement, 'identity', lambda: frozen)
    calls, verdicts = [], []
    def launch(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=code)
    monkeypatch.setattr(measurement, 'subprocess', SimpleNamespace(run=launch, STDOUT=subprocess.STDOUT))
    monkeypatch.setattr(measurement, '_validate_installed_aggregate', lambda *args: verdicts.append(args) or {})
    monkeypatch.setattr(measurement, 'report', lambda *args: None)
    output = tmp_path / 'coverage-result'
    assert measurement.measure(output, suite) == code
    receipt = json.loads((output / 'manifest.json').read_text())
    external = system == 'Windows' and suite == 'platform'
    expected = output.with_name(output.name + '-runtime') if external else output / 'tmp'
    assert expected.is_dir()
    assert all(calls[0][1]['env'][name] == str(expected) for name in ('TMP', 'TEMP', 'TMPDIR'))
    assert ('installed_runtime_root' in receipt) is external
    if external:
        assert not (output / 'tmp').exists()
        assert receipt['installed_runtime_root'] == str(expected)
        assert not expected.is_relative_to(output) and not output.is_relative_to(expected)
        if code == 0:
            assert verdicts[0][2] == expected
    else:
        assert not output.with_name(output.name + '-runtime').exists()


@pytest.mark.parametrize('existing', ['directory', 'file'])
def test_installed_runtime_root_refuses_reused_namespace(tmp_path, monkeypatch, existing):
    monkeypatch.setattr(measurement, 'ROOT', tmp_path / 'checkout')
    output = tmp_path / 'coverage-result'
    output.mkdir()
    runtime = output.with_name(output.name + '-runtime')
    if existing == 'directory':
        runtime.mkdir()
    else:
        runtime.write_text('retained evidence')
    with pytest.raises((ValueError, FileExistsError)):
        measurement._prepare_installed_runtime(output)
    assert runtime.exists()


def test_installed_runtime_root_refuses_checkout_ancestry_before_creation(tmp_path, monkeypatch):
    monkeypatch.setattr(measurement, 'ROOT', tmp_path)
    output = tmp_path / 'coverage-result'
    output.mkdir()
    with pytest.raises(ValueError, match='outside'):
        measurement._prepare_installed_runtime(output)
    assert not output.with_name(output.name + '-runtime').exists()


def test_windows_consumer_upload_preserves_primary_artifact_and_excludes_fixture_trees(tmp_path):
    import yaml

    workflow = yaml.safe_load((SCRIPT.parents[1] / '.github/workflows/coverage.yml').read_text())
    uploads = [step for step in workflow['jobs']['measure']['steps']
               if step.get('uses', '').startswith('actions/upload-artifact@')]
    assert len(uploads) == 2
    primary, consumers = uploads
    assert primary['if'] == 'always()'
    assert primary['with']['name'] == 'coverage-${{ matrix.os }}'
    assert primary['with']['path'].splitlines() == [
        '${{ runner.temp }}/coverage-result/.coverage*', '${{ runner.temp }}/coverage-result/*.json',
        '${{ runner.temp }}/coverage-result/*.jsonl', '${{ runner.temp }}/coverage-result/*.ini',
        '${{ runner.temp }}/coverage-result/*.txt', '${{ runner.temp }}/coverage-result/*.xml',
        '${{ runner.temp }}/coverage-result/html/', '${{ runner.temp }}/coverage-result/instrumented-platform/']
    assert consumers['uses'] == primary['uses']
    assert consumers['if'] == "always() && runner.os == 'Windows'"
    assert consumers['with'] == {
        'name': 'coverage-consumers-${{ matrix.os }}',
        'path': '${{ runner.temp }}/coverage-result-runtime/harness-installed-coverage-*/consumers/',
        'include-hidden-files': True, 'if-no-files-found': 'error'}
    namespace = tmp_path / 'coverage-result-runtime/harness-installed-coverage-synthetic'
    expected = ['partition-context.json', 'consumer-0/.hidden', 'consumer-1/nested/retained.txt']
    for relative in [*('consumers/' + name for name in expected), '0-temp/pytest/private', 'bootstrap/private']:
        path = namespace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('synthetic evidence')
    pattern = consumers['with']['path'].replace('${{ runner.temp }}/', '')
    matched = list(tmp_path.glob(pattern))
    assert matched == [namespace / 'consumers']
    retained = sorted(path.relative_to(matched[0]).as_posix() for path in matched[0].rglob('*') if path.is_file())
    assert retained == sorted(expected)
