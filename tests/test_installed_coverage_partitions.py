"""Installed coverage must prove identity, admission, completion and owned stopping."""

# qualify: platform

from contextlib import contextmanager
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import venv
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_qualifier(path=None):
    spec = importlib.util.spec_from_file_location('installed_partition_control', path or ROOT / 'scripts/qualify_platform.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PosixJobControl:
    """Local process-group adapter; this never qualifies Windows Job behavior."""
    def __enter__(self):
        self.process = None
        return self

    def launch(self, argv, *, stdin, stdout, stderr, cwd, environment):
        self.process = subprocess.Popen(argv, stdin=stdin, stdout=stdout, stderr=stderr,
                                        cwd=cwd, env=environment, start_new_session=True)
        return self.process

    def launch_failure(self):
        return None

    def stop(self, process):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)

    def __exit__(self, *_args):
        if self.process is not None:
            self.stop(self.process)


def native_job_factory():
    if os.name == 'nt':
        from attune_harness.windows import WindowsJob
        return WindowsJob
    return PosixJobControl


@pytest.fixture
def fixture_project(tmp_path):
    """A real noneditable RECORD and isolated interpreter, with no package install."""
    project = tmp_path / 'project'
    scripts, tests = project / 'scripts', project / 'tests'
    scripts.mkdir(parents=True)
    tests.mkdir()
    for name in ('qualify_platform.py', 'measure_coverage.py', 'harness_qualification_stacks.py'):
        shutil.copyfile(ROOT / 'scripts' / name, scripts / name)
    runtime = tmp_path / 'runtime'
    venv.EnvBuilder(with_pip=False).create(runtime)
    python = runtime / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    site = Path(subprocess.check_output([str(python), '-c', 'import sysconfig; print(sysconfig.get_path("purelib"))'], text=True).strip())
    # Only test dependencies are shared. The fixture's package/metadata take precedence.
    (site / 'fixture_dependencies.pth').write_text(str(Path(pytest.__file__).resolve().parent.parent) + '\n')
    metadata = site / 'attune_harness-1.0.dist-info'
    package = site / 'attune_harness'
    metadata.mkdir()
    package.mkdir()
    source = project / 'src/attune_harness'
    source.mkdir(parents=True)
    records = []
    for name in ('__init__.py', 'worker.py'):
        raw = b'VALUE = 1\n'
        (package / name).write_bytes(raw)
        (source / name).write_bytes(raw)
        digest = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip('=')
        records.append(f'attune_harness/{name},sha256={digest},{len(raw)}')
    raw = b'SYNTHETIC asset\n'
    (package / 'data.txt').write_bytes(raw)
    (source / 'data.txt').write_bytes(raw)
    digest = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip('=')
    records.append(f'attune_harness/data.txt,sha256={digest},{len(raw)}')
    (metadata / 'METADATA').write_text('Metadata-Version: 2.1\nName: attune-harness\nVersion: 1.0\n')
    (metadata / 'WHEEL').write_text('Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n')
    for name in ('METADATA', 'WHEEL'):
        raw = (metadata / name).read_bytes()
        digest = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip('=')
        records.append(f'{metadata.name}/{name},sha256={digest},{len(raw)}')
    records.append(f'{metadata.name}/RECORD,,')
    (metadata / 'RECORD').write_text('\n'.join(records) + '\n')
    (project / 'pyproject.toml').write_text('[tool.pytest.ini_options]\ntestpaths = ["tests"]\n')
    qualifier = load_qualifier(scripts / 'qualify_platform.py')
    probe_name = 'tests/test_plugin_probe.py'
    owner = qualifier._partition_owner(probe_name + '::test_probe')
    other = next(f'test_other_{i}.py' for i in range(100)
                 if qualifier._partition_owner('tests/' + f'test_other_{i}.py::test_case') != owner)
    steps = {name: {'outcome': 'passed'} for name in qualifier.PROBE_STEPS}
    (tests / 'test_plugin_probe.py').write_text(
        'import json, os\nfrom pathlib import Path\n'
        + 'def test_probe():\n    Path(os.environ["HARNESS_QUALIFICATION_OUTPUT"], "plugin-probe.json").write_text('
        + repr(json.dumps({'steps': steps})) + ')\n'
        + 'def test_actual_cli_process_through_full_adapter():\n    assert False, "-k admission must exclude this"\n')
    (tests / other).write_text(
        'import pytest\n'
        'def test_case(subtests):\n'
        '    with subtests.test(part="passed"): assert True\n'
        '    with subtests.test(part="skipped"): pytest.skip("synthetic subtest skip")\n'
        '@pytest.mark.skip(reason="synthetic ordinary skip")\ndef test_skip(): pass\n')
    empty_hooks = tmp_path / 'empty-hooks'
    empty_hooks.mkdir()
    git = ['git', '-c', 'core.hooksPath=' + str(empty_hooks), '-c', 'commit.gpgsign=false',
           '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid']
    subprocess.run([*git, 'init', '-q', str(project)], check=True)
    subprocess.run([*git, '-C', str(project), 'add', '.'], check=True)
    subprocess.run([*git, '-C', str(project), 'commit', '-qm', 'Installed control fixture'], check=True)
    environment = {**os.environ, 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
    command = [str(python), '-m', 'pytest', '-vv', '-o', 'pythonpath=', '-p', 'harness_qualification_stacks',
               '-o', 'faulthandler_timeout=0', str(tests / 'test_plugin_probe.py'), str(tests / other),
               '-k', 'not actual_cli_process_through_full_adapter']
    return dict(project=project, tests=tests, python=python, package=package, metadata=metadata,
                environment=environment, command=command, qualifier=qualifier, probe_owner=owner)


def expected_identity(fixture):
    code = ('import json,runpy,time; q=runpy.run_path(' + repr(str(fixture['project'] / 'scripts/qualify_platform.py'))
            + '); print(json.dumps(q["installed_partition_identity"](time.monotonic()+30)))')
    run = subprocess.run([str(fixture['python']), '-I', '-c', code], cwd=fixture['project'],
                         env=fixture['environment'], capture_output=True, text=True, timeout=40)
    assert run.returncode == 0, run.stdout + run.stderr
    return json.loads(run.stdout)


def execute(fixture, output, monkeypatch, *, budget=30, factory=None):
    qualifier = fixture['qualifier']
    identity = expected_identity(fixture)
    monkeypatch.setattr(qualifier, 'ROOT', fixture['project'])
    monkeypatch.setattr(qualifier, 'installed_partition_identity', lambda deadline: identity)
    monkeypatch.setattr(qualifier.os, 'environ', fixture['environment'])
    output.mkdir()
    run = qualifier.run_installed_partitions(output, fixture['command'], budget,
                                             job_factory=factory or native_job_factory())
    return run, identity


def test_real_children_retain_installed_identity_post_k_union_subtests_and_namespaces(fixture_project, tmp_path, monkeypatch):
    output = tmp_path / 'evidence'
    result, identity = execute(fixture_project, output, monkeypatch)
    supervisor = json.loads((output / 'installed-suite.json').read_text())
    assert result.returncode == 0, (supervisor, [(p.name, p.read_text()) for p in output.glob('shard-*/*err.txt')])
    assert supervisor['status'] == 'passed' and supervisor['ownership_cleanup'] == 'jobs_closed'
    assert supervisor['accounting']['admitted_cases'] == supervisor['accounting']['executed_cases'] == 3
    assert sum(row['subtests'] for row in supervisor['accounting']['junit']) == 2
    assert sum(row['skipped'] for row in supervisor['accounting']['junit']) == 2
    roots = [worker['temporary_root'] for worker in supervisor['workers']]
    assert len(set(roots)) == 2 and not any(Path(p).is_relative_to(fixture_project['project']) for p in roots)
    admissions, selected = [], []
    for index in range(2):
        folder = output / f'shard-{index}'
        witness = json.loads((folder / 'installed-identity.json').read_text())
        assert witness['before'] == witness['after'] == identity
        assert witness['status'] == 'verified' and witness['temporary_root'] == roots[index]
        collection = json.loads((folder / 'collection.json').read_text())
        admissions.append(collection['collected'])
        selected.extend(collection['selected'])
        assert all('actual_cli_process_through_full_adapter' not in node for node in collection['collected'])
        assert (folder / 'stdout.txt').is_file() and (folder / 'stderr.txt').is_file()
    assert admissions[0] == admissions[1] and sorted(selected) == sorted(admissions[0])
    assert (output / 'plugin-probe.json').read_bytes() == (
        output / f'shard-{fixture_project["probe_owner"]}' / 'plugin-probe.json').read_bytes()


@pytest.fixture
def completed_evidence(fixture_project, tmp_path, monkeypatch):
    output = tmp_path / 'valid-evidence'
    run, identity = execute(fixture_project, output, monkeypatch)
    assert run.returncode == 0, (output / 'installed-suite.json').read_text()
    context = json.loads((output / 'partition-context.json').read_text())
    context['context_sha256'] = hashlib.sha256((output / 'partition-context.json').read_bytes()).hexdigest()
    return output, context, fixture_project['qualifier']


@pytest.mark.parametrize('mutation', ['missing_identity', 'changed_identity', 'duplicate_admission', 'foreign_admission',
                                     'missing_case', 'duplicate_case', 'missing_terminal', 'terminal_foreign',
                                     'junit_skip', 'junit_subtest', 'missing_probe', 'duplicate_probe', 'failed_phase',
                                     'shared_temporary', 'shared_cwd', 'duplicate_child_pid', 'boolean_terminal',
                                     'duplicate_phase_end', 'invalid_phase_outcome', 'journal_after_deadline', 'terminal_category'])
def test_zero_exits_cannot_hide_incomplete_or_contradictory_evidence(completed_evidence, mutation):
    output, context, qualifier = completed_evidence
    folder = output / 'shard-0'
    if mutation == 'missing_identity':
        (folder / 'installed-identity.json').unlink()
    elif mutation == 'changed_identity':
        path = folder / 'installed-identity.json'
        value = json.loads(path.read_text()); value['after']['metadata_sha256']['RECORD'] = '0' * 64
        path.write_text(json.dumps(value))
    elif mutation in ('duplicate_admission', 'foreign_admission'):
        path = folder / 'collection.json'; value = json.loads(path.read_text())
        value['collected'].append(value['collected'][0] if mutation == 'duplicate_admission' else 'foreign.py::test_case')
        path.write_text(json.dumps(value))
    elif mutation in ('missing_case', 'duplicate_case', 'failed_phase', 'duplicate_phase_end',
                      'invalid_phase_outcome', 'journal_after_deadline'):
        path = folder / 'test-timings.jsonl'; lines = path.read_text().splitlines()
        if mutation == 'missing_case':
            lines = [line for line in lines if json.loads(line)['event'] != 'case_end']
        elif mutation == 'duplicate_case':
            lines.insert(-1, next(line for line in lines if json.loads(line)['event'] == 'case_end'))
        elif mutation == 'duplicate_phase_end':
            line = next(line for line in lines if json.loads(line)['event'] == 'phase_end')
            lines.insert(lines.index(line) + 1, line)
        elif mutation == 'invalid_phase_outcome':
            offset = next(i for i,line in enumerate(lines) if json.loads(line)['event'] == 'phase_end')
            value = json.loads(lines[offset]); value['outcome'] = 'not-a-pytest-outcome'; lines[offset] = json.dumps(value)
        elif mutation == 'journal_after_deadline':
            value = json.loads(lines[-1]); value['elapsed_seconds'] = 1000000.0; lines[-1] = json.dumps(value)
        else:
            value = json.loads(next(line for line in lines if json.loads(line)['event'] == 'phase_end'))
            value['outcome'] = 'failed'; lines.insert(-1, json.dumps(value))
        path.write_text('\n'.join(lines) + '\n')
    elif mutation in ('shared_temporary', 'shared_cwd'):
        field = 'temporary_root' if mutation == 'shared_temporary' else 'cwd'
        context['workers'][1][field] = context['workers'][0][field]
        stored = dict(context); stored.pop('context_sha256')
        raw = (json.dumps(stored, sort_keys=True, indent=2) + '\n').encode()
        (output / 'partition-context.json').write_bytes(raw)
        context['context_sha256'] = hashlib.sha256(raw).hexdigest()
        for index in range(2):
            path = output / f'shard-{index}/installed-identity.json'
            value = json.loads(path.read_text()); value['context_sha256'] = context['context_sha256']
            value['temporary_root' if field == 'temporary_root' else 'consumer_cwd'] = context['workers'][index][field]
            path.write_text(json.dumps(value))
    elif mutation == 'duplicate_child_pid':
        value = json.loads((folder / 'installed-identity.json').read_text())
        path = output / 'shard-1/installed-identity.json'
        other = json.loads(path.read_text()); other['pid'] = value['pid']; path.write_text(json.dumps(other))
    elif mutation == 'missing_terminal':
        (folder / 'terminal.json').unlink()
    elif mutation in ('terminal_foreign', 'boolean_terminal', 'terminal_category'):
        path = folder / 'terminal.json'; value = json.loads(path.read_text()); value['reports'][0]['nodeid'] = 'foreign.py::test_case'
        if mutation == 'boolean_terminal':
            value = json.loads(path.read_text()); value['exit_status'] = False
        elif mutation == 'terminal_category':
            value = json.loads(path.read_text()); value['reports'][0]['category'] = 'failed'
        path.write_text(json.dumps(value))
    elif mutation in ('junit_skip', 'junit_subtest'):
        import xml.etree.ElementTree as ET
        for path in output.glob('shard-*/tests.xml'):
            tree = ET.parse(path); suite = next(tree.getroot().iter('testsuite'))
            key = 'skipped' if mutation == 'junit_skip' else 'tests'; suite.set(key, str(int(suite.get(key)) + 1)); tree.write(path)
    elif mutation == 'missing_probe':
        next(output.glob('shard-*/plugin-probe.json')).unlink()
    else:
        source = next(output.glob('shard-*/plugin-probe.json'))
        other = output / ('shard-1' if source.parent.name == 'shard-0' else 'shard-0') / 'plugin-probe.json'
        other.write_bytes(source.read_bytes())
    with pytest.raises((ValueError, OSError)):
        qualifier.verify_installed_partitions(output, context, None)


@pytest.mark.parametrize('index', [0, 1])
@pytest.mark.parametrize('corruption', ['wrong-import', 'editable', 'altered', 'altered-asset'])
def test_each_child_refuses_wrong_editable_or_altered_wheel(fixture_project, tmp_path, monkeypatch, index, corruption):
    fixture = fixture_project
    wrong = tmp_path / 'wrong/attune_harness'
    wrong.mkdir(parents=True); (wrong / '__init__.py').write_text('VALUE = 2\n')
    action = {
        'wrong-import': 'sys.path.insert(0, ' + repr(str(wrong.parent)) + ')',
        'editable': ('import importlib.metadata as m\nreal=m.distribution\n'
                     'class Changed:\n def __init__(self,d): self.d=d\n'
                     ' def __getattr__(self,n): return getattr(self.d,n)\n'
                     ' def read_text(self,n): return \'{"dir_info":{"editable":true}}\' if n=="direct_url.json" else self.d.read_text(n)\n'
                     'm.distribution=lambda n: Changed(real(n)) if n=="attune-harness" else real(n)'),
        'altered': 'Path(' + repr(str(fixture['package'] / 'worker.py')) + ').write_text("VALUE = 9\\n")',
        'altered-asset': 'Path(' + repr(str(fixture['package'] / 'data.txt')) + ').write_bytes(b"CHANGED asset")',
    }[corruption]
    conftest = 'import os,sys\nfrom pathlib import Path\nif Path(os.environ.get("HARNESS_QUALIFICATION_OUTPUT", "")).name == ' + repr(f'shard-{index}') + ':\n'
    conftest += '\n'.join(' ' + line for line in action.splitlines()) + '\n'
    (fixture['tests'] / 'conftest.py').write_text(conftest)
    output = tmp_path / 'refused'
    result, _ = execute(fixture, output, monkeypatch)
    assert result.returncode != 0
    path = output / f'shard-{index}/installed-identity.json'
    assert json.loads(path.read_text())['status'] == 'refused'
    assert json.loads((output / 'installed-suite.json').read_text())['status'] == 'failed'


@pytest.mark.parametrize('phase', ['setup', 'teardown'])
def test_failed_fixture_phase_prevents_success_and_postcheck_admission(fixture_project, tmp_path, monkeypatch, phase):
    fixture = fixture_project
    code = ('import pytest\n@pytest.fixture(autouse=True)\ndef broken():\n'
            + (' raise RuntimeError("setup control")\n' if phase == 'setup' else ' yield\n raise RuntimeError("teardown control")\n'))
    (fixture['tests'] / 'conftest.py').write_text(code)
    result, _ = execute(fixture, tmp_path / 'failed-phase', monkeypatch)
    assert result.returncode != 0


def test_unpartitioned_collect_only_matches_post_k_admission(fixture_project, tmp_path, monkeypatch):
    fixture = fixture_project
    observer = fixture['project'] / 'scripts/admission_observer.py'
    observer.write_text('import json,os\nfrom pathlib import Path\n'
                        'def pytest_collection_finish(session):\n'
                        ' Path(os.environ["ADMISSION_FILE"]).write_text(json.dumps([i.nodeid for i in session.items]))\n')
    baseline = tmp_path / 'collect-only'
    baseline.mkdir()
    manifest = baseline / 'admitted.json'
    environment = {**fixture['environment'], 'PYTHONPATH': str(observer.parent),
                   'HARNESS_QUALIFICATION_OUTPUT': str(baseline), 'ADMISSION_FILE': str(manifest)}
    run = subprocess.run([*fixture['command'], '-p', 'admission_observer', '--collect-only'],
                         cwd=baseline, env=environment, capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout + run.stderr
    admitted = json.loads(manifest.read_text())
    assert len(admitted) == 3 and not (baseline / 'plugin-probe.json').exists()
    output = tmp_path / 'executed'
    result, _ = execute(fixture, output, monkeypatch)
    assert result.returncode == 0, (output / 'installed-suite.json').read_text()
    for index in range(2):
        assert json.loads((output / f'shard-{index}/collection.json').read_text())['collected'] == admitted


@pytest.mark.parametrize('scenario', ['expiry_then_zero', 'late_second_launch', 'live_sibling',
                                     'second_launch_failure', 'unknown_ownership', 'cleanup_failure',
                                     'aggregate_expiry', 'owner_setup_expiry'])
def test_shared_deadline_and_ownership_failures_stay_latched(tmp_path, monkeypatch, scenario):
    qualifier = load_qualifier()
    clock, owners = [0.0], []
    output = tmp_path / 'evidence'
    output.mkdir()
    monkeypatch.setattr(qualifier, 'installed_partition_identity', lambda deadline: {'control': True})
    def sleep(seconds):
        clock[0] += seconds
    monkeypatch.setattr(qualifier, 'time', SimpleNamespace(monotonic=lambda: clock[0], sleep=sleep))
    def verify(folder, context, deadline, *, parent_receipt):
        if scenario == 'aggregate_expiry':
            clock[0] = 2.0
        (folder / 'shard-0/plugin-probe.json').write_text('{}')
        return {'plugin_probe_owner': 0}
    monkeypatch.setattr(qualifier, 'verify_installed_partitions', verify)
    class Process:
        def __init__(self, index):
            self.pid = 1000 + index
            self.code = (2 if index == 0 else None) if scenario == 'live_sibling' else (
                None if scenario in ('expiry_then_zero', 'second_launch_failure') else 0)
        def poll(self):
            return self.code
    class Owner:
        def __enter__(self):
            self.index, self.stopped, self.closed = len(owners), False, False
            self.launched = False
            owners.append(self)
            if scenario == 'owner_setup_expiry':
                clock[0] = 2.0
            return self
        def launch(self, argv, **kwargs):
            self.launched = True
            if self.index == 1 and scenario == 'second_launch_failure':
                raise OSError('synthetic assignment failure')
            if self.index == 1 and scenario == 'late_second_launch':
                clock[0] = 2.0
            self.process = Process(self.index)
            return self.process
        def launch_failure(self):
            return 'launch_failed' if scenario == 'unknown_ownership' else None
        def stop(self, process):
            self.stopped = True
            # A late zero must never clear timeout/cancellation/nonzero evidence.
            process.code = 0
        def __exit__(self, *_args):
            self.closed = True
            if scenario == 'cleanup_failure' and self.index == 1:
                raise OSError('synthetic ownership close failure')
    run = qualifier.run_installed_partitions(output, [sys.executable, '-m', 'pytest'], 1, job_factory=Owner)
    receipt = json.loads((output / 'installed-suite.json').read_text())
    assert run.returncode != 0 and receipt['status'] == 'failed'
    assert all(owner.closed for owner in owners)
    if scenario in ('expiry_then_zero', 'late_second_launch', 'aggregate_expiry'):
        assert run.returncode == receipt['exit'] == 124
    if scenario == 'live_sibling':
        assert run.returncode == 2 and owners[1].stopped
    if scenario == 'second_launch_failure':
        assert owners[0].stopped
    if scenario == 'expiry_then_zero':
        assert all(owner.stopped for owner in owners)
        assert all(row['returncode'] == 0 for row in receipt['workers'])
    if scenario == 'owner_setup_expiry':
        assert run.returncode == 124 and not any(owner.launched for owner in owners)


def test_legitimate_teardown_skip_keeps_serial_and_partition_accounting(fixture_project, tmp_path, monkeypatch):
    fixture = fixture_project
    other = next(path for path in fixture['tests'].glob('test_other_*.py'))
    with other.open('a') as stream:
        stream.write('\n@pytest.fixture\ndef teardown_skip():\n yield\n pytest.skip("synthetic teardown skip")\n'
                     'def test_teardown_skip(teardown_skip): pass\n')
    baseline = tmp_path / 'serial-control'; baseline.mkdir()
    environment = {**fixture['environment'], 'PYTHONPATH': str(fixture['project'] / 'scripts'),
                   'HARNESS_QUALIFICATION_OUTPUT': str(baseline)}
    serial = subprocess.run([*fixture['command'], '--junitxml=' + str(baseline / 'tests.xml')],
                            cwd=baseline, env=environment, capture_output=True, text=True, timeout=30)
    assert serial.returncode == 0, serial.stdout + serial.stderr
    result, _ = execute(fixture, tmp_path / 'partitions', monkeypatch)
    assert result.returncode == 0


def test_delayed_launch_receives_only_the_remaining_shared_budget(tmp_path, monkeypatch):
    qualifier = load_qualifier()
    output = tmp_path / 'evidence'
    output.mkdir()
    clock, launches = [10.0], []
    monkeypatch.setattr(qualifier, 'time', SimpleNamespace(monotonic=lambda: clock[0], sleep=lambda _: None))
    monkeypatch.setattr(qualifier, 'installed_partition_identity', lambda deadline: {'control': True})
    def verify(folder, context, deadline, *, parent_receipt):
        (folder / 'shard-0/plugin-probe.json').write_text('{}')
        return {'plugin_probe_owner': 0}
    monkeypatch.setattr(qualifier, 'verify_installed_partitions', verify)
    class Owner:
        def __enter__(self): return self
        def launch(self, argv, **kwargs):
            launches.append(kwargs)
            clock[0] += 0.4
            return SimpleNamespace(pid=len(launches), poll=lambda: 0)
        def launch_failure(self): return None
        def __exit__(self, *_args): pass
    assert qualifier.run_installed_partitions(output, [sys.executable, '-m', 'pytest'], 1,
                                               job_factory=Owner).returncode == 0
    receipt = json.loads((output / 'installed-suite.json').read_text())
    assert receipt['deadline_monotonic'] == 11.0
    remaining = [row['remaining_at_dispatch_seconds'] for row in receipt['workers']]
    assert remaining == pytest.approx([1.0, 0.6])
    assert launches[0]['cwd'] != launches[1]['cwd']
    assert launches[0]['environment']['TMP'] != launches[1]['environment']['TMP']


@pytest.mark.parametrize('damage', [
    'parent_start_nan', 'parent_start_bool', 'parent_deadline_inf', 'finish_nan', 'finish_bool',
    'finish_before_start', 'finish_at_deadline', 'dispatch_nan', 'dispatch_before_start',
    'dispatch_after_deadline', 'reap_nan', 'reap_before_dispatch', 'reap_after_finish',
    'remaining_negative', 'remaining_inconsistent', 'remaining_bool', 'missing_reap',
    'worker_index_bool', 'worker_pid_bool', 'duplicate_bootstrap_pid', 'foreign_namespace', 'unknown_ownership'])
def test_complete_parent_clock_and_worker_contract_refuses_impossible_proof(
        fixture_project, tmp_path, monkeypatch, damage):
    output = tmp_path / 'measurement'; output.mkdir()
    result, identity = execute(fixture_project, output / 'instrumented-platform', monkeypatch, budget=2520)
    assert result.returncode == 0
    spec = importlib.util.spec_from_file_location('parent_clock_measurement', ROOT / 'scripts/measure_coverage.py')
    measurement = importlib.util.module_from_spec(spec); spec.loader.exec_module(measurement)
    assert measurement._validate_installed_aggregate(output, identity['measurement'])
    path = output / 'instrumented-platform/installed-suite.json'
    receipt = json.loads(path.read_text())
    worker = receipt['workers'][0]
    if damage == 'parent_start_nan': receipt['started_monotonic'] = float('nan')
    elif damage == 'parent_start_bool': receipt['started_monotonic'] = False
    elif damage == 'parent_deadline_inf': receipt['deadline_monotonic'] = float('inf')
    elif damage == 'finish_nan': receipt['finished_monotonic'] = float('nan')
    elif damage == 'finish_bool': receipt['finished_monotonic'] = False
    elif damage == 'finish_before_start': receipt['finished_monotonic'] = receipt['started_monotonic'] - 1
    elif damage == 'finish_at_deadline': receipt['finished_monotonic'] = receipt['deadline_monotonic']
    elif damage == 'dispatch_nan': worker['dispatched_monotonic'] = float('nan')
    elif damage == 'dispatch_before_start': worker['dispatched_monotonic'] = receipt['started_monotonic'] - 1
    elif damage == 'dispatch_after_deadline': worker['dispatched_monotonic'] = receipt['deadline_monotonic'] + 100
    elif damage == 'reap_nan': worker['reaped_monotonic'] = float('nan')
    elif damage == 'reap_before_dispatch': worker['reaped_monotonic'] = worker['dispatched_monotonic'] - 1
    elif damage == 'reap_after_finish': worker['reaped_monotonic'] = receipt['finished_monotonic'] + 1
    elif damage == 'remaining_negative': worker['remaining_at_dispatch_seconds'] = -1
    elif damage == 'remaining_inconsistent': worker['remaining_at_dispatch_seconds'] /= 2
    elif damage == 'remaining_bool': worker['remaining_at_dispatch_seconds'] = True
    elif damage == 'missing_reap': worker.pop('reaped_monotonic')
    elif damage == 'worker_index_bool': worker['index'] = False
    elif damage == 'worker_pid_bool': worker['pid'] = True
    elif damage == 'duplicate_bootstrap_pid': worker['pid'] = receipt['workers'][1]['pid']
    elif damage == 'foreign_namespace': worker['cwd'] += '/foreign'
    else: worker['ownership'] = 'unknown'
    path.write_text(json.dumps(receipt))
    with pytest.raises((ValueError, OSError)):
        measurement._validate_installed_aggregate(output, identity['measurement'])


@pytest.mark.parametrize('damage', ['reap_before_epoch', 'dispatch_after_epoch', 'finish_before_suite_end'])
def test_complete_proof_joins_child_epoch_and_suite_end_to_owned_worker(
        fixture_project, tmp_path, monkeypatch, damage):
    output = tmp_path / 'measurement'; output.mkdir()
    folder = output / 'instrumented-platform'
    result, identity = execute(fixture_project, folder, monkeypatch, budget=2520)
    assert result.returncode == 0
    spec = importlib.util.spec_from_file_location('joined_clock_measurement', ROOT / 'scripts/measure_coverage.py')
    measurement = importlib.util.module_from_spec(spec); spec.loader.exec_module(measurement)
    assert measurement._validate_installed_aggregate(output, identity['measurement'])
    path = folder / 'installed-suite.json'; receipt = json.loads(path.read_text())
    witnesses = [json.loads((folder / f'shard-{i}/installed-identity.json').read_text()) for i in range(2)]
    if damage == 'reap_before_epoch':
        receipt['workers'][0]['reaped_monotonic'] = receipt['workers'][0]['dispatched_monotonic']
    elif damage == 'dispatch_after_epoch':
        worker = receipt['workers'][1]
        worker['dispatched_monotonic'] = (witnesses[1]['timing_epoch_monotonic'] + worker['reaped_monotonic']) / 2
        worker['remaining_at_dispatch_seconds'] = receipt['deadline_monotonic'] - worker['dispatched_monotonic']
    else:
        finish = max(worker['dispatched_monotonic'] for worker in receipt['workers'])
        for worker in receipt['workers']:
            worker['reaped_monotonic'] = finish
        receipt['finished_monotonic'] = finish
    path.write_text(json.dumps(receipt))
    fixture_project['qualifier'].validate_installed_parent_receipt(
        receipt, json.loads((folder / 'partition-context.json').read_text()), successful=True)
    with pytest.raises((ValueError, OSError)):
        measurement._validate_installed_aggregate(output, identity['measurement'])


@pytest.mark.parametrize('epoch, dispatched, reaped', [
    (0.0, 0.0, 0.0), (10.0, 9.0, 10.0000006),
    (100.0, 100.0, 100.0000004), (1000000.125, 1000000.0, 1000000.125001)])
def test_join_uses_existing_six_decimal_serialization_without_clock_grace(epoch, dispatched, reaped):
    qualifier = load_qualifier()
    worker = {'dispatched_monotonic': dispatched, 'reaped_monotonic': reaped}
    last_possible = round(reaped - epoch, 6)
    qualifier._installed_child_interval(worker, epoch, last_possible)
    with pytest.raises(ValueError):
        qualifier._installed_child_interval(worker, epoch, last_possible + 0.000001)


def test_join_accepts_reverse_reap_order_and_distinct_bootstrap_pytest_pids(
        fixture_project, tmp_path, monkeypatch):
    output = tmp_path / 'measurement'; output.mkdir()
    folder = output / 'instrumented-platform'
    result, identity = execute(fixture_project, folder, monkeypatch, budget=2520)
    assert result.returncode == 0
    path = folder / 'installed-suite.json'; receipt = json.loads(path.read_text())
    # ExitStack reaps in reverse registration order; worker indexes do not
    # impose a reap order, and Windows bootstraps own different pytest PIDs.
    assert receipt['workers'][0]['reaped_monotonic'] >= receipt['workers'][1]['reaped_monotonic']
    child_pids = {json.loads((folder / f'shard-{i}/installed-identity.json').read_text())['pid'] for i in range(2)}
    for index, worker in enumerate(receipt['workers']):
        worker['pid'] = max(child_pids) + 1000000 + index
    path.write_text(json.dumps(receipt))
    spec = importlib.util.spec_from_file_location('joined_positive_measurement', ROOT / 'scripts/measure_coverage.py')
    measurement = importlib.util.module_from_spec(spec); spec.loader.exec_module(measurement)
    assert measurement._validate_installed_aggregate(output, identity['measurement'])


def represented_clock_proof(start, delay=0.0, budget=30):
    """Portable parent-receipt control; no native process or filesystem sample."""
    deadline = start + budget
    namespaces = [{'cwd': f'C:\\consumer{i}', 'temporary_root': f'C:\\temporary{i}',
                   'basetemp': f'C:\\temporary{i}\\pytest'} for i in range(2)]
    context = {'schema_version': 1, 'system': 'Windows', 'checkout': 'C:\\checkout',
               'started_monotonic': start, 'deadline_monotonic': deadline,
               'budget_seconds': budget, 'workers': namespaces}
    receipt = {'started_monotonic': start, 'deadline_monotonic': deadline,
               'shared_budget_seconds': budget, 'finished_monotonic': deadline - 1,
               'status': 'passed', 'exit': 0, 'failure': None, 'ownership_cleanup': 'jobs_closed',
               'workers': [{'index': i, **namespace, 'pid': 8000 + i, 'ownership': 'windows_job',
                            'returncode': 0, 'dispatched_monotonic': start + (delay if i else 0),
                            'remaining_at_dispatch_seconds': deadline - (start + (delay if i else 0)),
                            'reaped_monotonic': deadline - 2} for i, namespace in enumerate(namespaces)]}
    return receipt, context


@pytest.mark.parametrize('start, delay', [(501.343, 0), (503.343, 0), (509.796, 0),
                                          (0.0, 0), (10.0, .125), (1000.0, 1.0)])
def test_represented_interval_accepts_original_native_vectors_and_delayed_dispatch(start, delay):
    qualifier = load_qualifier()
    receipt, context = represented_clock_proof(start, delay)
    qualifier.validate_installed_parent_receipt(receipt, context, successful=True)


@pytest.mark.parametrize('start', [501.343, 503.343, 509.796])
def test_represented_interval_refuses_nextafter_upper_bound_without_new_epsilon(start):
    import math
    qualifier = load_qualifier()
    receipt, context = represented_clock_proof(start)
    interval = context['deadline_monotonic'] - context['started_monotonic']
    receipt['workers'][0]['remaining_at_dispatch_seconds'] = math.nextafter(interval, math.inf)
    assert math.isclose(receipt['workers'][0]['remaining_at_dispatch_seconds'], interval,
                        rel_tol=0, abs_tol=0.000001)
    with pytest.raises(ValueError, match='dispatch order or remaining budget'):
        qualifier.validate_installed_parent_receipt(receipt, context, successful=True)


@pytest.mark.parametrize('late', [False, True])
def test_represented_interval_still_refuses_exact_or_late_deadline_dispatch(late):
    import math
    qualifier = load_qualifier()
    receipt, context = represented_clock_proof(501.343)
    deadline = context['deadline_monotonic']
    dispatched = math.nextafter(deadline, math.inf) if late else deadline
    receipt['workers'][0].update(dispatched_monotonic=dispatched,
                                 remaining_at_dispatch_seconds=deadline - dispatched)
    with pytest.raises(ValueError):
        qualifier.validate_installed_parent_receipt(receipt, context, successful=True)


@pytest.mark.parametrize('start', [501.343, 503.343, 509.796])
def test_represented_interval_active_supervisor_accepts_same_coarse_clock(tmp_path, monkeypatch, start):
    qualifier = load_qualifier()
    clock, owners = [start], []
    monkeypatch.setattr(qualifier, 'time', SimpleNamespace(monotonic=lambda: clock[0], sleep=lambda delay: None))
    monkeypatch.setattr(qualifier, 'installed_partition_identity', lambda deadline: {'control': True})
    def verify(folder, context, deadline, *, parent_receipt):
        (folder / 'shard-0/plugin-probe.json').write_text('{}')
        return {'plugin_probe_owner': 0}
    monkeypatch.setattr(qualifier, 'verify_installed_partitions', verify)
    class Process:
        def __init__(self, index): self.pid = 8000 + index
        def poll(self): return 0
    class Owner:
        def __enter__(self): owners.append(self); return self
        def launch(self, *args, **kwargs): return Process(len(owners))
        def launch_failure(self): return None
        def stop(self, process): raise AssertionError('Already completed synthetic process must not be stopped')
        def __exit__(self, *args): return None
    output = tmp_path / 'evidence'; output.mkdir()
    result = qualifier.run_installed_partitions(output, [sys.executable, '-m', 'pytest'], 30, job_factory=Owner)
    assert result.returncode == 0, (output / 'installed-suite.json').read_text()
    receipt = json.loads((output / 'installed-suite.json').read_text())
    assert receipt['finished_monotonic'] < receipt['deadline_monotonic']
    assert receipt['workers'][0]['remaining_at_dispatch_seconds'] == receipt['deadline_monotonic'] - start
def external_namespace_context():
    runtime = 'C:\\runtime\\harness-installed-coverage-synthetic'
    workers = [{'cwd': runtime + f'\\consumers\\consumer-{i}',
                'temporary_root': runtime + f'\\{i}-temp',
                'basetemp': runtime + f'\\{i}-temp\\pytest'} for i in range(2)]
    return {'schema_version': 1, 'system': 'Windows', 'checkout': 'C:\\checkout',
            'started_monotonic': 10.0, 'deadline_monotonic': 40.0, 'budget_seconds': 30,
            'workers': workers, 'namespace': {
                'runtime_root': runtime, 'evidence_root': 'C:\\coverage-result\\instrumented-platform',
                'consumer_artifact_root': runtime + '\\consumers'}}


@pytest.mark.parametrize('damage', [
    'runtime_in_evidence', 'evidence_in_runtime', 'runtime_in_checkout',
    'cwd_in_evidence', 'temp_in_evidence', 'consumer_root_alias', 'worker_alias',
    'noncanonical_runtime', 'foreign_runtime_parent', 'foreign_evidence'])
def test_external_namespace_refuses_evidence_overlap_alias_and_wrong_owner(damage):
    qualifier = load_qualifier()
    context = external_namespace_context()
    qualifier.validate_installed_context(context)
    qualifier.validate_installed_namespace(
        context, evidence_root='C:\\coverage-result\\instrumented-platform', runtime_root='C:\\runtime')
    namespace = context['namespace']
    if damage == 'runtime_in_evidence':
        namespace['runtime_root'] = namespace['evidence_root'] + '\\nested'
    elif damage == 'evidence_in_runtime':
        namespace['evidence_root'] = namespace['runtime_root'] + '\\nested'
    elif damage == 'runtime_in_checkout':
        namespace['runtime_root'] = 'C:\\checkout\\runtime'
    elif damage == 'cwd_in_evidence':
        context['workers'][0]['cwd'] = namespace['evidence_root'] + '\\consumer'
    elif damage == 'temp_in_evidence':
        context['workers'][0]['temporary_root'] = namespace['evidence_root'] + '\\temp'
        context['workers'][0]['basetemp'] = namespace['evidence_root'] + '\\temp\\pytest'
    elif damage == 'consumer_root_alias':
        namespace['consumer_artifact_root'] = namespace['runtime_root'] + '\\0-temp'
    elif damage == 'worker_alias':
        context['workers'][1]['cwd'] = context['workers'][0]['cwd']
    elif damage == 'noncanonical_runtime':
        namespace['runtime_root'] += '\\..\\foreign'
    with pytest.raises(ValueError):
        qualifier.validate_installed_namespace(
            context,
            evidence_root='C:\\foreign' if damage == 'foreign_evidence' else 'C:\\coverage-result\\instrumented-platform',
            runtime_root='C:\\foreign' if damage == 'foreign_runtime_parent' else 'C:\\runtime')


def test_external_consumers_keep_real_paths_and_identical_context_for_static_readback(
        fixture_project, tmp_path, monkeypatch):
    from tempfile import mkdtemp

    external = tmp_path / 'measurement-runtime'
    external.mkdir()
    monkeypatch.setattr(fixture_project['qualifier'], 'tempfile', SimpleNamespace(
        mkdtemp=lambda **kwargs: mkdtemp(dir=external, **kwargs)))
    output = tmp_path / 'measurement'
    output.mkdir()
    folder = output / 'instrumented-platform'
    result, identity = execute(fixture_project, folder, monkeypatch, budget=2520)
    assert result.returncode == 0, (folder / 'installed-suite.json').read_text()
    raw = (folder / 'partition-context.json').read_bytes()
    context = json.loads(raw)
    namespace = context['namespace']
    runtime = Path(namespace['runtime_root'])
    consumers = Path(namespace['consumer_artifact_root'])
    assert consumers == runtime / 'consumers'
    assert (consumers / 'partition-context.json').read_bytes() == raw
    for index, worker in enumerate(context['workers']):
        assert worker['cwd'] == str(consumers / f'consumer-{index}')
        assert worker['temporary_root'] == str(runtime / f'{index}-temp')
        for field in ('cwd', 'temporary_root', 'basetemp'):
            path = Path(worker[field])
            assert not path.is_relative_to(output) and not output.is_relative_to(path)
        witness = json.loads((folder / f'shard-{index}/installed-identity.json').read_text())
        assert witness['consumer_cwd'] == worker['cwd']
        assert witness['temporary_root'] == worker['temporary_root']
    spec = importlib.util.spec_from_file_location('external_namespace_measurement', ROOT / 'scripts/measure_coverage.py')
    measurement = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(measurement)
    assert measurement._validate_installed_aggregate(output, identity['measurement'], runtime.parent)
    (consumers / 'partition-context.json').write_bytes(raw + b' ')
    with pytest.raises(ValueError, match='context'):
        measurement._validate_installed_aggregate(output, identity['measurement'], runtime.parent)


def test_external_consumer_evidence_survives_failed_child_without_after_reap_copy(
        fixture_project, tmp_path, monkeypatch):
    launches = []
    class Process:
        pid = 70001
        returncode = 1
        def poll(self):
            return self.returncode
    class Owner:
        def __enter__(self):
            return self
        def launch(self, argv, **kwargs):
            process = Process()
            process.pid += len(launches)
            cwd = Path(kwargs['cwd'])
            context_path = Path(next(arg.split('=', 1)[1] for arg in argv
                                     if arg.startswith('--harness-installed-context=')))
            retained = cwd.parent / 'partition-context.json'
            assert retained.read_bytes() == context_path.read_bytes()
            assert all(kwargs['environment'][key] == str(cwd.parent.parent / f'{len(launches)}-temp')
                       for key in ('TMP', 'TEMP', 'TMPDIR', 'PYTEST_DEBUG_TEMPROOT', 'RUNNER_TEMP'))
            (cwd / '.failure-witness').write_text('synthetic original child evidence')
            launches.append(cwd)
            return process
        def launch_failure(self):
            return None
        def stop(self, process):
            pass
        def __exit__(self, *_args):
            pass
    output = tmp_path / 'failed-evidence'
    result, _ = execute(fixture_project, output, monkeypatch, factory=Owner)
    assert result.returncode == 1
    assert len(launches) == 2
    assert all((cwd / '.failure-witness').is_file() for cwd in launches)
    assert all(not cwd.is_relative_to(output) and not output.is_relative_to(cwd) for cwd in launches)
    assert (launches[0].parent / 'partition-context.json').read_bytes() == (
        output / 'partition-context.json').read_bytes()
