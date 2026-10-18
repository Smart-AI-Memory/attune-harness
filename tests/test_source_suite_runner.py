"""CI retains failing and unfinished evidence without declaring a passing suite."""

import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('source_suite', ROOT / 'scripts/run_source_suite.py')
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


@pytest.fixture
def project(tmp_path):
    root = tmp_path / 'project'
    root.mkdir()
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(['git', '-C', str(root), '-c', 'commit.gpgsign=false',
                    '-c', 'core.hooksPath=' + str(tmp_path / 'no-hooks'),
                    '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                    'commit', '--allow-empty', '-qm', 'fixture'], check=True)
    return root


@pytest.mark.parametrize('assertion,code', [('True', 0), ('False', 1)])
def test_actual_pytest_verdict_and_phase_journal_survive(tmp_path, project, assertion, code):
    (project / 'test_case.py').write_text(
        'from pathlib import Path\ndef test_case(tmp_path):\n'
        '    Path("fixture-path").write_text(str(tmp_path))\n'
        '    (tmp_path / "retained.txt").write_text("fixture evidence")\n'
        '    assert ' + assertion + '\n')
    output = tmp_path / 'evidence'
    assert RUNNER.run_suite(output, 20, root=project) == code
    receipt = json.loads((output / 'source-suite.json').read_text())
    events = [json.loads(row) for row in (output / 'test-timings.jsonl').read_text().splitlines()]
    assert receipt['status'] == ('passed' if code == 0 else 'failed')
    assert receipt['returncode'] == code
    assert events[-1]['event'] == 'suite_end' and events[-1]['exit_status'] == code
    assert (output / 'tests.xml').is_file()
    assert 'faulthandler_timeout=0' in receipt['command']
    assert 'test_case' in (output / 'stdout.txt').read_text()
    fixture = Path((project / 'fixture-path').read_text())
    assert fixture.exists() == (code != 0)
    if code != 0:
        assert (fixture / 'retained.txt').read_text() == 'fixture evidence'


def test_real_deadline_is_failed_with_retained_output(tmp_path, project):
    (project / 'test_case.py').write_text('import time\ndef test_case():\n    time.sleep(60)\n')
    output = tmp_path / 'evidence'
    assert RUNNER.run_suite(output, 3, root=project) == 124
    receipt = json.loads((output / 'source-suite.json').read_text())
    assert receipt['status'] == 'failed' and receipt['failure'] == 'timeout_effects_unknown'
    assert (output / 'stdout.txt').is_file() and (output / 'stderr.txt').is_file()


@pytest.mark.parametrize('failure,expected', [('timeout_effects_unknown', 124),
                                             ('output_limit', 2), ('nonzero_exit', 2)])
def test_zero_process_exit_cannot_hide_supervision_failure(tmp_path, project, monkeypatch,
                                                        failure, expected):
    from attune_harness import process
    monkeypatch.setattr(process, 'invoke', lambda *a, **k:
                        process.ProcessResult(a[0], 0, 'pytest passed\n', '', failure))
    output = tmp_path / 'evidence'
    assert RUNNER.run_suite(output, 10, root=project) == expected
    assert json.loads((output / 'source-suite.json').read_text())['status'] == 'failed'


def test_existing_evidence_is_never_overwritten(tmp_path, project):
    output = tmp_path / 'evidence'
    output.mkdir()
    retained = output / 'source-suite.json'
    retained.write_bytes(b'retained')
    with pytest.raises(FileExistsError):
        RUNNER.run_suite(output, 10, root=project)
    assert retained.read_bytes() == b'retained'
