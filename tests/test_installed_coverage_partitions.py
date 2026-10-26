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
    def verify(folder, context, deadline):
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
    def verify(folder, context, deadline):
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
