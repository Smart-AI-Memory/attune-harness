"""The macOS coverage topology shares a budget and retains complete evidence."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import pytest

from test_coverage_measurement import measurement
from test_source_suite_runner import RUNNER, project  # noqa: F401

POSIX = pytest.mark.skipif(os.name != 'posix', reason='macOS measurement process supervision')


def sleeping_project(project, *, fail_first=False):
    for name in ('test_first.py', 'test_right.py'):
        (project / name).write_text(
            'import os, time\nfrom pathlib import Path\n'
            'def test_case():\n'
            '    Path(__file__).with_suffix(".pid").write_text(str(os.getpid()))\n'
            + ('    deadline = time.monotonic() + 15\n'
               '    while len(list(Path(__file__).parent.glob("*.pid"))) != 2:\n'
               '        assert time.monotonic() < deadline, "sibling did not launch"\n'
               '        time.sleep(.01)\n'
               '    assert False, "original partition failure"\n'
               if fail_first and name == 'test_first.py' else '    time.sleep(60)\n'))


def assert_reaped(project):
    paths = list(project.glob('*.pid'))
    assert len(paths) == 2
    for path in paths:
        with pytest.raises(ProcessLookupError):
            os.kill(int(path.read_text()), 0)


@POSIX
def test_delayed_worker_shares_deadline_and_both_processes_are_reaped(tmp_path, project, monkeypatch):
    sleeping_project(project)
    original = RUNNER._run_suite

    def delayed(*args, **kwargs):
        if kwargs['shard'] == 1:
            time.sleep(4)
        return original(*args, **kwargs)

    monkeypatch.setattr(RUNNER, '_run_suite', delayed)
    output = tmp_path / 'evidence'
    started = time.monotonic()
    assert RUNNER.run_suite(output, 12, root=project, shards=2, deadline=started + 12) == 124
    assert time.monotonic() - started < 14.5
    receipt = json.loads((output / 'source-suite.json').read_text())
    late = json.loads((output / 'shard-1/source-suite.json').read_text())
    assert receipt['status'] == 'failed' and receipt['aggregate_deadline_exceeded'] is True
    assert late['effective_timeout_seconds'] < 8
    assert 'coverage' not in receipt
    assert_reaped(project)
    for index in range(2):
        assert (output / f'shard-{index}/test-timings.jsonl').is_file()
        assert (output / f'shard-{index}/failed-phases.jsonl').is_file()


@POSIX
def test_failed_partition_cancels_and_reaps_its_running_sibling(tmp_path, project):
    sleeping_project(project, fail_first=True)
    output = tmp_path / 'evidence'
    started = time.monotonic()
    assert RUNNER.run_suite(output, 30, root=project, shards=2, deadline=started + 30) == 1
    assert time.monotonic() - started < 15
    receipt = json.loads((output / 'source-suite.json').read_text())
    assert receipt['status'] == 'failed' and 'coverage' not in receipt
    assert_reaped(project)
    failed = (output / 'shard-0/failed-phases.jsonl').read_text()
    assert 'original partition failure' in failed
    assert (output / 'shard-1/test-timings.jsonl').is_file()


def test_late_zero_exits_cannot_clear_latched_aggregate_timeout(tmp_path, project, monkeypatch):
    def late_success(*args, **kwargs):
        time.sleep(1)
        return 0

    monkeypatch.setattr(RUNNER, '_run_suite', late_success)
    output = tmp_path / 'evidence'
    assert RUNNER.run_suite(output, 10, root=project, shards=2,
                            deadline=time.monotonic() + .1) == 124
    receipt = json.loads((output / 'source-suite.json').read_text())
    assert receipt['shard_exits'] == [0, 0] and receipt['status'] == 'failed'
    assert receipt['aggregate_deadline_exceeded'] is True and 'coverage' not in receipt


@POSIX
def test_shared_partition_native_namespaces_allow_nested_unix_sockets(tmp_path, project):
    for name in ('test_first.py', 'test_right.py'):
        (project / name).write_text(
            'import socket, tempfile\nfrom pathlib import Path\n'
            'def test_case():\n'
            '    home = Path(tempfile.mkdtemp(prefix="hs-"))\n'
            '    with socket.socket(socket.AF_UNIX) as connection:\n'
            '        connection.bind(str(home / "S.gpg-agent"))\n'
            '    Path(__file__).with_suffix(".namespace").write_text(str(home.parent))\n')
    output = tmp_path / 'evidence'
    assert RUNNER.run_suite(output, 30, root=project, shards=2,
                            deadline=time.monotonic() + 30) == 0
    receipt = json.loads((output / 'source-suite.json').read_text())
    roots = [Path(value) for value in receipt['temporary_roots']]
    assert len(set(roots)) == 2
    assert all(path.name.startswith(str(index)) for index, path in enumerate(roots))
    assert {Path(path.read_text()) for path in project.glob('*.namespace')} == set(roots)
    assert receipt['coverage'] == {'collected_cases': 2, 'executed_cases': 2}


@POSIX
def test_real_partitions_contribute_both_aliases_and_retain_uploaded_evidence(tmp_path, project, monkeypatch):
    coverage = pytest.importorskip('coverage')
    root = Path(__file__).resolve().parents[1]
    scripts = project / 'scripts'
    scripts.mkdir()
    for name in ('run_source_suite.py', 'harness_qualification_stacks.py'):
        shutil.copy2(root / 'scripts' / name, scripts / name)
    source, installed = project / 'source', tmp_path / 'installed'
    source.mkdir()
    installed.mkdir()
    code = 'def left():\n    return 1\ndef right():\n    return 2\n'
    for path in (source, installed):
        (path / 'worker.py').write_text(code)
    for name, prefix, function, value in [('test_first', source, 'left', 1),
                                          ('test_right', installed, 'right', 2)]:
        (project / (name + '.py')).write_text(
            'import sys\nsys.path.insert(0, ' + repr(str(prefix)) + ')\nimport worker\n'
            + f'def test_case():\n    assert worker.{function}() == {value}\n')
    subprocess.run(['git', '-C', str(project), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(project), '-c', 'commit.gpgsign=false',
                    '-c', 'core.hooksPath=' + str(tmp_path / 'no-hooks'),
                    '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                    'commit', '-qm', 'Measured fixture'], check=True)
    venv = tmp_path / 'venv'
    subprocess.run([sys.executable, '-m', 'venv', '--without-pip', str(venv)], check=True)
    python = venv / 'bin/python'
    site = Path(subprocess.check_output([str(python), '-c',
        'import sysconfig; print(sysconfig.get_path("purelib"))'], text=True).strip())
    (site / 'test_dependencies.pth').write_text(str(Path(coverage.__file__).parent.parent) + '\n')
    output = tmp_path / 'evidence'
    output.mkdir()
    monkeypatch.setattr(measurement, 'SOURCE', source)
    config = measurement.configuration(output, [str(installed)])
    (site / 'harness_measure_coverage.pth').write_text(measurement.startup_hook(config))
    controller = tmp_path / 'controller.py'
    controller.write_text(
        'import importlib.util, json\nfrom pathlib import Path\n'
        + 'spec = importlib.util.spec_from_file_location("measurement", '
        + repr(str(root / 'scripts/measure_coverage.py')) + ')\n'
        + 'm = importlib.util.module_from_spec(spec)\nspec.loader.exec_module(m)\n'
        + 'm.ROOT = Path(' + repr(str(project)) + ')\n'
        + 'm.SOURCE = Path(' + repr(str(source)) + ')\n'
        + 'before = m.identity()\n'
        + 'result = m._darwin_full(Path(' + repr(str(output)) + '), 30)\n'
        + 'after = m.identity()\n'
        + 'Path(' + repr(str(tmp_path / 'binding.json'))
        + ').write_text(json.dumps({"before": before, "after": after, "exit": result}))\n'
        + 'raise SystemExit(result)\n')
    result = subprocess.run([str(python), str(controller)], capture_output=True, text=True, timeout=40)
    assert result.returncode == 0, result.stdout + result.stderr
    binding = json.loads((tmp_path / 'binding.json').read_text())
    assert binding['before'] == binding['after'] and binding['exit'] == 0
    assert hashlib.sha256((installed / 'worker.py').read_bytes()).hexdigest() == binding['before']['sources']['worker.py']
    evidence = output / 'instrumented-platform'
    assert RUNNER.verify_partitions(evidence, binding['before']['revision']) == {
        'collected_cases': 2, 'executed_cases': 2}
    for index in range(2):
        for name in ('tests.xml', 'collection.json', 'test-timings.jsonl',
                     'failed-phases.jsonl', 'slow-stacks.txt', 'source-suite.json'):
            assert (evidence / f'shard-{index}' / name).is_file()
    contributions = []
    for path in output.glob('.coverage.*'):
        data = coverage.CoverageData(basename=str(path))
        data.read()
        contributions.append(set().union(*(set(data.lines(name) or []) for name in data.measured_files()
                                            if Path(name).name == 'worker.py')))
    assert any(2 in lines and 4 not in lines for lines in contributions)
    assert any(4 in lines and 2 not in lines for lines in contributions)
    collector = coverage.Coverage(config_file=str(config))
    collector.combine(keep=True)
    collector.save()
    assert collector.analysis2(str(source / 'worker.py'))[3] == []


@pytest.fixture
def admitted_measurement(tmp_path, monkeypatch):
    import attune_harness

    root, installed, site = tmp_path / 'checkout', tmp_path / 'installed', tmp_path / 'site'
    source = root / 'src/attune_harness'
    for folder in (source, installed, site):
        folder.mkdir(parents=True)
    for folder in (source, installed):
        (folder / '__init__.py').write_text('VALUE = 1\n')
    monkeypatch.setattr(attune_harness, '__file__', str(installed / '__init__.py'))
    monkeypatch.setattr(measurement, 'ROOT', root)
    monkeypatch.setattr(measurement, 'SOURCE', source)
    monkeypatch.setattr(measurement, 'sys', SimpleNamespace(
        prefix='dedicated', base_prefix='base', executable=sys.executable))
    monkeypatch.setattr(measurement, 'sysconfig', SimpleNamespace(get_path=lambda _: str(site)))
    monkeypatch.setattr(measurement.platform, 'system', lambda: 'Darwin')
    frozen = {'revision': 'a' * 40, 'sources': measurement.hashes(source),
              'input_hashes': {}, 'coverage_version': measurement.VERSION, 'pytest_version': '9.1.1'}
    monkeypatch.setattr(measurement, 'identity', lambda: frozen)
    reports = []
    monkeypatch.setattr(measurement, 'report', lambda *args: reports.append(args))
    return SimpleNamespace(output=tmp_path / 'evidence', installed=installed, site=site,
                           frozen=frozen, reports=reports)


@pytest.mark.parametrize('code', [1, 124])
def test_default_topology_is_durable_and_failed_partitions_cannot_combine(admitted_measurement, monkeypatch, code):
    context = admitted_measurement

    def failed(output, budget):
        before = json.loads((output / 'manifest.json').read_text())
        assert budget == before['shared_test_budget_seconds'] == 1500
        assert before['suite'] == 'full' and before['test_exit'] is None
        assert before['input_drift'] is True
        assert before['execution_topology'] == 'two_supervised_module_partitions'
        assert before['partition_evidence'] == [f'instrumented-platform/shard-{i}' for i in range(2)]
        for index in range(2):
            folder = output / before['partition_evidence'][index]
            folder.mkdir(parents=True)
            (folder / 'failed-phases.jsonl').write_bytes(b'original partial diagnostic\n')
        return code

    monkeypatch.setattr(measurement, '_darwin_full', failed)
    assert measurement.measure(context.output, 'full') == code
    receipt = json.loads((context.output / 'manifest.json').read_text())
    assert receipt['test_exit'] == code and receipt['input_drift'] is False
    assert context.reports == [] and not (context.site / 'harness_measure_coverage.pth').exists()
    for index in range(2):
        assert (context.output / f'instrumented-platform/shard-{index}/failed-phases.jsonl').read_bytes() == b'original partial diagnostic\n'
    with pytest.raises(ValueError, match='failed, unfinished'):
        measurement.compatible([receipt], context.frozen)


def test_partition_success_with_installed_drift_cannot_report_or_combine(admitted_measurement, monkeypatch):
    context = admitted_measurement

    def changed(output, budget):
        (context.installed / '__init__.py').write_text('VALUE = 2\n')
        return 0

    monkeypatch.setattr(measurement, '_darwin_full', changed)
    assert measurement.measure(context.output, 'full') == 1
    receipt = json.loads((context.output / 'manifest.json').read_text())
    assert receipt['test_exit'] == 0 and receipt['input_drift'] is True
    assert context.reports == [] and not (context.site / 'harness_measure_coverage.pth').exists()
    with pytest.raises(ValueError, match='input-drifted'):
        measurement.compatible([receipt], context.frozen)


@pytest.mark.parametrize('damage', ['missing', 'malformed', 'failures', 'errors', 'few-cases', 'empty',
                                  'header-only', 'hidden-failure', 'hidden-error', 'skipped-count',
                                  'negative-count', 'subtests-missing', 'subtests-mismatch'])
def test_zero_partition_exit_cannot_hide_missing_or_failed_junit(tmp_path, monkeypatch, damage):
    def producer(output, budget, **kwargs):
        for index in range(2):
            folder = output / f'shard-{index}'
            folder.mkdir(parents=True)
            (folder / 'collection.json').write_text(json.dumps({'selected': ['first', 'second']}))
            text = ('<testsuites><testsuite tests="2" failures="0" errors="0" skipped="0">'
                    '<testcase name="first"/><testcase name="second"/></testsuite></testsuites>')
            transcript = '2 passed in 1.23s\n'
            if index == 0:
                if damage == 'missing':
                    continue
                if damage == 'malformed': text = '<unfinished'
                elif damage == 'failures': text = text.replace('failures="0"', 'failures="1"')
                elif damage == 'errors': text = text.replace('errors="0"', 'errors="1"')
                elif damage == 'few-cases': text = text.replace('tests="2"', 'tests="1"')
                elif damage == 'empty': text = '<testsuites/>'
                elif damage == 'header-only':
                    text = '<testsuites><testsuite tests="2" failures="0" errors="0"/></testsuites>'
                elif damage == 'hidden-failure':
                    text = text.replace('<testcase name="first"/>', '<testcase name="first"><failure/></testcase>')
                elif damage == 'hidden-error':
                    text = text.replace('<testcase name="first"/>', '<testcase name="first"><error/></testcase>')
                elif damage == 'skipped-count': text = text.replace('skipped="0"', 'skipped="1"')
                elif damage == 'negative-count': text = text.replace('skipped="0"', 'skipped="-1"')
                elif damage.startswith('subtests-'):
                    text = text.replace('tests="2"', 'tests="4"')
                    if damage == 'subtests-mismatch': transcript = '2 passed, 1 subtests passed in 1.23s\n'
            (folder / 'tests.xml').write_text(text)
            (folder / 'stdout.txt').write_text(transcript)
        return 0

    loader = SimpleNamespace(exec_module=lambda module: None)
    fake_util = SimpleNamespace(spec_from_file_location=lambda *args: SimpleNamespace(loader=loader),
                                module_from_spec=lambda spec: SimpleNamespace(run_suite=producer))
    monkeypatch.setattr(measurement, 'importlib', SimpleNamespace(util=fake_util))
    with pytest.raises((OSError, ValueError, ET.ParseError)):
        measurement._darwin_full(tmp_path, 1500)


@pytest.mark.parametrize('subtests', [0, 2])
def test_successful_partition_junit_retains_real_cases_and_matching_subtests(tmp_path, monkeypatch, subtests):
    def producer(output, budget, **kwargs):
        for index in range(2):
            folder = output / f'shard-{index}'
            folder.mkdir(parents=True)
            (folder / 'collection.json').write_text(json.dumps({'selected': ['first', 'second']}))
            (folder / 'tests.xml').write_text(
                f'<testsuites><testsuite tests="{2 + subtests}" failures="0" errors="0" skipped="1">'
                '<testcase name="first"/><testcase name="second"><skipped/></testcase></testsuite></testsuites>')
            (folder / 'stdout.txt').write_text(f'1 passed, 1 skipped, {subtests} subtests passed in 1.23s\n')
        return 0

    loader = SimpleNamespace(exec_module=lambda module: None)
    fake_util = SimpleNamespace(spec_from_file_location=lambda *args: SimpleNamespace(loader=loader),
                                module_from_spec=lambda spec: SimpleNamespace(run_suite=producer))
    monkeypatch.setattr(measurement, 'importlib', SimpleNamespace(util=fake_util))
    assert measurement._darwin_full(tmp_path, 1500) == 0


def test_existing_workflow_uploads_both_live_partition_diagnostic_trees():
    import yaml

    root = Path(__file__).resolve().parents[1]
    steps = yaml.safe_load((root / '.github/workflows/coverage.yml').read_text())['jobs']['measure']['steps']
    upload = next(step for step in steps if step.get('uses', '').startswith('actions/upload-artifact@'))
    assert upload['if'] == 'always()'
    assert '${{ runner.temp }}/coverage-result/instrumented-platform/' in upload['with']['path'].splitlines()
