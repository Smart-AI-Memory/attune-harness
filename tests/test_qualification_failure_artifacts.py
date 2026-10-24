"""Failed assertions must survive a later independent suite timeout."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]


def child_command(directory):
    return [sys.executable, '-m', 'pytest', '-q', '-c', os.devnull,
            '-p', 'harness_qualification_stacks', '-o', 'faulthandler_timeout=0',
            '--junitxml=' + str(directory / 'tests.xml'), str(directory / 'test_case.py')]


def child_environment(directory):
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
               PYTHONPATH=str(ROOT / 'scripts'), HARNESS_QUALIFICATION_OUTPUT=str(directory))
    for name in ('PYTEST_ADDOPTS', 'PYTEST_PLUGINS'):
        env.pop(name, None)
    return env


def run_child(directory, source, conftest=''):
    (directory / 'test_case.py').write_text(source, encoding='utf-8')
    if conftest:
        (directory / 'conftest.py').write_text(conftest, encoding='utf-8')
    run = subprocess.run(child_command(directory), cwd=directory, env=child_environment(directory),
                         capture_output=True, text=True, timeout=15)
    (directory / 'tests.txt').write_text(run.stdout + run.stderr, encoding='utf-8')
    assert run.returncode == 1, run.stdout + run.stderr
    assert 'INTERNALERROR' not in run.stdout + run.stderr
    path = directory / 'failed-phases.jsonl'
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def test_failed_assertion_survives_later_outer_kill(tmp_path):
    (tmp_path / 'test_case.py').write_text('''import time, pytest
from pathlib import Path
@pytest.fixture
def owner():
    yield
    Path('teardown-entered').write_text('yes')
    time.sleep(30)
def test_original_assertion(owner):
    assert 1 == 2, 'retained before the outer kill'
''')
    with (tmp_path / 'child.txt').open('wb') as stream:
        child = subprocess.Popen(child_command(tmp_path), cwd=tmp_path,
                                 env=child_environment(tmp_path), stdout=stream,
                                 stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline and child.poll() is None:
                if (tmp_path / 'teardown-entered').exists():
                    break
                time.sleep(0.01)
            else:
                pytest.fail('synthetic child did not reach its blocked teardown')
            records = [json.loads(line) for line in
                       (tmp_path / 'failed-phases.jsonl').read_text().splitlines()]
            assert len(records) == 1 and records[0]['phase'] == 'call'
            assert 'retained before the outer kill' in records[0]['failure']
            assert records[0]['nodeid'].endswith('::test_original_assertion')
            assert not (tmp_path / 'tests.xml').exists()
            with pytest.raises(subprocess.TimeoutExpired):
                child.wait(timeout=0.1)
        finally:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=5)
    assert records == [json.loads(line) for line in
                       (tmp_path / 'failed-phases.jsonl').read_text().splitlines()]


@pytest.mark.parametrize('phase', ['setup', 'call', 'teardown'])
def test_failed_phase_details_preserve_existing_timing_consumer(tmp_path, phase):
    assertion = "assert False, 'original failed phase'"
    source = '''import os, pytest
@pytest.fixture
def owner():
    SETUP
    yield
    TEARDOWN
def test_case(owner):
    private_local = os.environ['FAILURE_PRIVATE_CONTROL']
    print(private_local)
    CALL
'''.replace('SETUP', assertion if phase == 'setup' else 'pass')
    source = source.replace('TEARDOWN', assertion if phase == 'teardown' else 'pass')
    source = source.replace('CALL', assertion if phase == 'call' else 'pass')
    conftest = "import os\nos.environ['FAILURE_PRIVATE_CONTROL'] = 'captured-control-not-for-artifact'\n"
    records = run_child(tmp_path, source, conftest)
    assert len(records) == 1 and records[0]['phase'] == phase
    assert 'original failed phase' in records[0]['failure']
    assert 'captured-control-not-for-artifact' not in json.dumps(records)
    assert records[0]['outcome'] == 'failed'
    (tmp_path / 'platform.json').write_text(json.dumps({
        'schema_version': 1, 'status': 'failed', 'pytest_exit': 1, 'exit': 1}))
    spec = importlib.util.spec_from_file_location('failure_diagnostic', ROOT / 'scripts/diagnose_qualification.py')
    diagnostic = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(diagnostic)
    outcome = diagnostic.diagnose(tmp_path)
    assert outcome['classification'] == 'pytest_session_failed'
    assert outcome['timing_sequence_valid'] is True and outcome['evidence_issues'] == []


@pytest.mark.parametrize('phase', ['setup', 'call', 'teardown'])
def test_deep_failure_keeps_original_exception_within_text_cap(tmp_path, phase):
    functions = ''.join(f'def level_{index}():\n    level_{index + 1}()\n' for index in range(79))
    functions += "def level_79():\n    assert False, 'original exception beyond the long stack'\n"
    source = '''import pytest
FUNCTIONS
@pytest.fixture
def owner():
    SETUP
    yield
    TEARDOWN
def test_case(owner):
    CALL
'''.replace('FUNCTIONS', functions)
    source = source.replace('SETUP', 'level_0()' if phase == 'setup' else 'pass')
    source = source.replace('TEARDOWN', 'level_0()' if phase == 'teardown' else 'pass')
    source = source.replace('CALL', 'level_0()' if phase == 'call' else 'pass')
    records = run_child(tmp_path, source)
    assert len(records) == 1 and records[0]['phase'] == phase
    assert 'original exception beyond the long stack' in records[0]['failure']
    assert records[0]['failure_truncated'] is True
    assert len(records[0]['failure']) <= 4096


@pytest.mark.parametrize('fault', ['open', 'format', 'write', 'close'])
def test_failure_artifact_fault_does_not_replace_pytest_verdict(tmp_path, fault):
    conftest = '''import pytest, harness_qualification_stacks as stacks
@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    def broken(*args, **kwargs):
        raise OSError('private diagnostic control')
    if FAULT == 'format':
        stacks._failure_text = broken
        return
    original = stacks.Path.open
    class Sink:
        def __init__(self, stream): self.stream = stream
        def write(self, data):
            if FAULT == 'write': broken()
            return self.stream.write(data)
        def close(self):
            self.stream.close()
            if FAULT == 'close': broken()
    def open_path(path, *args, **kwargs):
        if path.name != 'failed-phases.jsonl':
            return original(path, *args, **kwargs)
        if FAULT == 'open': broken()
        return Sink(original(path, *args, **kwargs))
    stacks.Path.open = open_path
'''.replace('FAULT', repr(fault))
    source = "def test_case():\n    assert False, 'original verdict remains failed'\n"
    records = run_child(tmp_path, source, conftest)
    if fault in ('open', 'write'):
        assert records == []
    elif fault == 'format':
        assert records[0]['representation_error_type'] == 'OSError'
        assert 'private diagnostic control' not in json.dumps(records)
    else:
        assert 'original verdict remains failed' in records[0]['failure']


@pytest.mark.parametrize('cap', ['records', 'bytes'])
def test_failure_artifact_bounds_unicode_and_total_output(tmp_path, cap):
    source = ("import pytest\n@pytest.mark.parametrize('case', [1,2,3], ids="
              + repr(['λ' * 2000] * 3) + ")\ndef test_case(case):\n    assert False, '🔥' * 10000\n")
    conftest = ("import harness_qualification_stacks as stacks\n"
                + ('stacks.MAX_FAILURE_RECORDS = 1\n' if cap == 'records'
                   else 'stacks.MAX_FAILURE_BYTES = 1024\n'))
    records = run_child(tmp_path, source, conftest)
    assert records[-1]['event'] == 'failure_log_limit'
    if cap == 'records':
        assert len(records) == 2 and records[0]['failure_truncated'] is True
        assert records[0]['nodeid_truncated'] is True
        assert '🔥' in records[0]['failure']
        assert len((tmp_path / 'failed-phases.jsonl').read_bytes()) < 64 * 1024
    else:
        assert len(records) == 1 and records[0]['records_retained'] == 0
        assert len((tmp_path / 'failed-phases.jsonl').read_bytes()) <= 1024


@pytest.mark.skipif(os.name != 'posix', reason='existing POSIX process fixture')
def test_short_stdlib_fixture_bypasses_inherited_site_startup(tmp_path, monkeypatch):
    marker = tmp_path / 'startup.txt'
    (tmp_path / 'sitecustomize.py').write_text(
        'from pathlib import Path\nPath(' + repr(str(marker)) + ").write_text('ordinary startup hook')\n")
    monkeypatch.setenv('PYTHONPATH', str(tmp_path))
    ordinary = subprocess.run([sys.executable, '-c', 'pass'], cwd=tmp_path,
                              capture_output=True, text=True, timeout=10)
    assert ordinary.returncode == 0, ordinary.stdout + ordinary.stderr
    assert marker.read_text() == 'ordinary startup hook'
    # An ordinary sibling proves the hook was available. The unchanged timeout,
    # partial-output and reap assertions run through the actual existing fixture.
    (tmp_path / 'sitecustomize.py').write_text(
        'from pathlib import Path\nPath(' + repr(str(marker)) + ").write_text('unexpected site startup')\n")
    spec = importlib.util.spec_from_file_location('process_fixture', ROOT / 'tests/test_process.py')
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    fixture.test_timeout_retains_partial_output_and_reaps_process(tmp_path)
    assert marker.read_text() == 'ordinary startup hook'
