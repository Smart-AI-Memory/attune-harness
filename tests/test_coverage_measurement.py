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
def test_successful_child_with_postrun_input_drift_retains_incompatible_receipt(tmp_path, monkeypatch, changed, suite):
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

    def successful_child(argv, **kwargs):
        assert ('--coverage-instrumented' in argv) == (suite == 'platform')
        assert kwargs['timeout'] == (1080 if suite == 'platform' else 1200)
        if changed == 'checkout_test':
            test.write_text('def test_example(): assert False\n', encoding='utf-8')
        else:
            (installed / '__init__.py').write_text('VALUE = 2\n', encoding='utf-8')
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(measurement, 'subprocess', SimpleNamespace(
        run=successful_child, check_output=subprocess.check_output,
        CalledProcessError=subprocess.CalledProcessError, STDOUT=subprocess.STDOUT))
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
def test_platform_timeout_preserves_qualification_boundary(tmp_path, monkeypatch, instrumented, timed_out):
    import attune_harness
    spec = importlib.util.spec_from_file_location('qualifier', SCRIPT.with_name('qualify_platform.py'))
    qualifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qualifier)
    installed = tmp_path / 'installed'
    installed.mkdir()
    (installed / '__init__.py').write_text('')
    monkeypatch.setattr(attune_harness, '__file__', str(installed / '__init__.py'))
    output = tmp_path / 'result'
    calls = []
    expected_timeout = 900

    def child(argv, **kwargs):
        calls.append(argv)
        if '-m' in argv:
            assert kwargs['timeout'] == expected_timeout
            assert 'faulthandler_timeout=0' in argv
            assert 'harness_qualification_stacks' in argv
            assert kwargs['env']['PYTHONPATH'] == str(qualifier.ROOT / 'scripts')
            (output / 'plugin-probe.json').write_text(json.dumps({'steps': {
                step: {'outcome': 'passed'} for step in qualifier.PROBE_STEPS}}))
            if timed_out:
                raise subprocess.TimeoutExpired(argv, kwargs['timeout'])
            return subprocess.CompletedProcess(argv, 0)
        (output / 'memory-redis.json').write_text(json.dumps({
            'memory': {'native_reader': 'available' if os.name == 'posix' else 'posix-only refusal',
                       'tiers_read': ['raw', 'personal', 'curated'] if os.name == 'posix' else [],
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
    assert len(calls) == 2
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
        failed = {**measurement.identity(), 'test_exit': 124, 'input_drift': False}
        with pytest.raises(ValueError, match='unfinished'):
            measurement.compatible([failed], measurement.identity())


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
            subprocess.run([sys.executable, '-m', 'pytest', '-vv',
                            '-p', 'harness_qualification_stacks',
                            '-o', 'faulthandler_timeout=0',
                            '-o', 'harness_stack_timeout=0.1', str(test)],
                           cwd=tmp_path, stdout=stream, stderr=subprocess.STDOUT,
                           timeout=10, env={**os.environ, 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
                                            'PYTHONPATH': str(SCRIPT.parent),
                                            'HARNESS_QUALIFICATION_OUTPUT': str(tmp_path)})
    transcript = (tmp_path / 'slow-stacks.txt').read_text()
    assert 'Slow test Python stacks:' in transcript
    assert str(test) in transcript
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
    time.sleep(0.02)
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
    test.write_text('''import faulthandler, threading, time, types
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
    try: time.sleep(0.3)
    finally:
        stop.set()
        worker.join()
    captured = capsys.readouterr()
    assert 'Slow test Python stacks:' not in captured.out + captured.err
''' + ('    assert False, "intentional failure remains a failure"\n' if fails else '') +
                    '\ndef test_fast(): pass\n')
    log = tmp_path / 'tests.txt'
    with log.open('wb') as stream:
        run = subprocess.run([sys.executable, '-m', 'pytest', '-vv',
                              '-p', 'harness_qualification_stacks',
                              '-o', 'faulthandler_timeout=0',
                              '-o', 'harness_stack_timeout=0.1', str(test)],
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
