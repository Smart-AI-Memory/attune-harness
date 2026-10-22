"""Concurrent source partitions preserve every case and refuse incomplete evidence."""

import copy
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

import pytest

from test_source_suite_runner import RUNNER, project  # noqa: F401


def partition_project(project, *, assertion='True', rendezvous=False):
    # These module paths have distinct SHA-256 owners, 0 and 1 respectively.
    for name in ('test_first.py', 'test_right.py'):
        barrier = '''
    marker = Path(__file__).with_suffix('.ready')
    marker.write_text('started')
    other = marker.with_name('test_right.ready' if marker.stem == 'test_first' else 'test_first.ready')
    deadline = time.monotonic() + 15
    while not other.exists() and time.monotonic() < deadline:
        time.sleep(.01)
    assert other.exists(), 'partitions were not concurrent'
''' if rendezvous else ''
        (project / name).write_text(
            'import time, os, tempfile, json\nfrom pathlib import Path\nimport pytest\n'
            '@pytest.mark.parametrize("value", [1, 2])\n'
            'def test_case(value, tmp_path, request):\n'
            '    observed = {key: os.environ.get(key) for key in '
            '("TMP", "TEMP", "TMPDIR", "PYTEST_DEBUG_TEMPROOT", "RUNNER_TEMP")}\n'
            '    observed.update(tempdir=tempfile.gettempdir(), fixture=str(tmp_path), '
            'basetemp=str(request.config._tmp_path_factory.getbasetemp()))\n'
            '    Path(__file__).with_suffix(".temp.json").write_text(json.dumps(observed))\n'
            '    if os.name == "nt":\n'
            '        from attune_harness.windows_effects import Native\n'
            '        api = Native()\n'
            '        with api.root({"root": str(tmp_path)}, check=False) as parent:\n'
            '            with api.owned(api.child(parent, "created", create=True, '
            'directory=True, writable=True)) as child:\n'
            '                entry, size, inherited = api.metadata(child)\n'
            '        assert inherited, "partition fixtures lost inherited Windows permissions"\n'
            + barrier + '    assert ' + assertion + '\n')


def test_actual_partitions_run_concurrently_and_cover_every_case(tmp_path, project, monkeypatch):
    temporary_base = tmp_path / 'workers'
    temporary_base.mkdir()
    monkeypatch.setattr(RUNNER.tempfile, 'gettempdir', lambda: str(temporary_base))
    monkeypatch.setenv('RUNNER_TEMP', str(project / 'different-hosted-runner-base'))
    partition_project(project, rendezvous=True)
    output = tmp_path / 'evidence'
    assert RUNNER.run_suite(output, 40, root=project, shards=2) == 0
    receipt = json.loads((output / 'source-suite.json').read_text())
    assert receipt['status'] == 'passed' and receipt['shard_exits'] == [0, 0]
    assert receipt['coverage'] == {'collected_cases': 4, 'executed_cases': 4}
    manifests = [json.loads((output / f'shard-{index}' / 'collection.json').read_text())
                 for index in range(2)]
    assert len(manifests[0]['collected']) == 4
    assert set(manifests[0]['collected']) == set(manifests[1]['collected'])
    selections = [set(item['selected']) for item in manifests]
    assert len(selections[0]) == len(selections[1]) == 2
    assert not selections[0] & selections[1]
    assert selections[0] | selections[1] == set(manifests[0]['collected'])
    assert all((output / f'shard-{index}' / 'tests.xml').is_file() for index in range(2))
    observed = [json.loads((project / f'{name}.temp.json').read_text())
                for name in ('test_first', 'test_right')]
    assert observed[0]['tempdir'] != observed[1]['tempdir']
    assert receipt['temporary_roots'] == [item['tempdir'] for item in observed]
    for item in observed:
        temporary = Path(item['tempdir']).resolve()
        assert temporary.parent == temporary_base.resolve()
        assert all(Path(item[key]).resolve() == temporary for key in
                   ('TMP', 'TEMP', 'TMPDIR', 'PYTEST_DEBUG_TEMPROOT', 'RUNNER_TEMP'))
        assert Path(item['basetemp']).resolve() == temporary / 'pytest'
        assert Path(item['fixture']).resolve().is_relative_to(temporary / 'pytest')
        assert not temporary.is_relative_to(project)


def test_assertion_failure_in_a_partition_fails_the_whole_suite(tmp_path, project):
    partition_project(project, assertion='value != 2')
    output = tmp_path / 'evidence'
    assert RUNNER.run_suite(output, 30, root=project, shards=2) == 1
    receipt = json.loads((output / 'source-suite.json').read_text())
    assert receipt['status'] == 'failed' and 'coverage' not in receipt
    assert receipt['shard_exits'] == [1, 1]


def test_partition_deadline_is_not_cleared_by_another_passing_partition(tmp_path, project):
    partition_project(project)
    (project / 'test_first.py').write_text('import time\ndef test_case():\n    time.sleep(60)\n')
    output = tmp_path / 'evidence'
    assert RUNNER.run_suite(output, 4, root=project, shards=2) == 124
    receipt = json.loads((output / 'source-suite.json').read_text())
    assert receipt['status'] == 'failed' and 124 in receipt['shard_exits']
    assert (output / 'shard-0' / 'stdout.txt').exists()
    assert (output / 'shard-1' / 'stdout.txt').exists()


@pytest.fixture
def partition_evidence(tmp_path):
    collected = ['test_first.py::test_case[1]', 'test_first.py::test_case[2]',
                 'test_right.py::test_case[1]', 'test_right.py::test_case[2]']
    output = tmp_path / 'evidence'
    for index, module in enumerate(('test_first', 'test_right')):
        folder = output / f'shard-{index}'
        folder.mkdir(parents=True)
        selected = [node for node in collected if node.startswith(module + '.py::')]
        shard = {'index': index, 'count': 2}
        (folder / 'source-suite.json').write_text(json.dumps({
            'status': 'passed', 'exit': 0, 'returncode': 0, 'failure': None,
            'revision': 'revision', 'shard': shard}))
        (folder / 'collection.json').write_text(json.dumps({
            'schema_version': 1, 'shard': shard, 'collected': collected, 'selected': selected}))
        events = [{'event': event, 'nodeid': node}
                  for node in selected for event in ('case_start', 'case_end')]
        events.append({'event': 'suite_end', 'exit_status': 0})
        (folder / 'test-timings.jsonl').write_text('\n'.join(json.dumps(row) for row in events))
    return output


def test_complete_partition_receipts_are_accepted(partition_evidence):
    assert RUNNER.verify_partitions(partition_evidence, 'revision') == {
        'collected_cases': 4, 'executed_cases': 4}


@pytest.mark.parametrize('damage', [
    'missing-case', 'repeated-case', 'other-collection', 'duplicate-collection',
    'wrong-partition', 'empty-partition', 'wrong-index', 'stale-revision',
    'supervision-failure', 'incomplete-case', 'repeated-start', 'no-suite-end',
    'failed-suite-end', 'missing-manifest', 'missing-journal',
])
def test_zero_exits_cannot_hide_incomplete_partition_evidence(partition_evidence, damage):
    folder = partition_evidence / 'shard-0'
    manifest_path, receipt_path = folder / 'collection.json', folder / 'source-suite.json'
    journal = folder / 'test-timings.jsonl'
    manifest = json.loads(manifest_path.read_text())
    receipt = json.loads(receipt_path.read_text())
    events = [json.loads(row) for row in journal.read_text().splitlines()]
    if damage == 'missing-case': manifest['selected'].pop()
    elif damage == 'repeated-case': manifest['selected'].append(manifest['selected'][0])
    elif damage == 'other-collection': manifest['collected'].append('test_extra.py::test_case')
    elif damage == 'duplicate-collection': manifest['collected'].append(manifest['collected'][0])
    elif damage == 'wrong-partition': manifest['selected'] = manifest['collected'][2:]
    elif damage == 'empty-partition': manifest['selected'] = []
    elif damage == 'wrong-index': manifest['shard']['index'] = 1
    elif damage == 'stale-revision': receipt['revision'] = 'other'
    elif damage == 'supervision-failure': receipt['failure'] = 'timeout_effects_unknown'
    elif damage == 'incomplete-case': events.pop(1)
    elif damage == 'repeated-start': events.insert(0, copy.deepcopy(events[0]))
    elif damage == 'no-suite-end': events.pop()
    elif damage == 'failed-suite-end': events[-1]['exit_status'] = 1
    manifest_path.write_text(json.dumps(manifest))
    receipt_path.write_text(json.dumps(receipt))
    journal.write_text('\n'.join(json.dumps(row) for row in events))
    if damage == 'missing-manifest': manifest_path.rename(folder / 'unavailable-manifest')
    if damage == 'missing-journal': journal.rename(folder / 'unavailable-journal')
    with pytest.raises((ValueError, OSError)):
        RUNNER.verify_partitions(partition_evidence, 'revision')


@pytest.mark.parametrize('shards', [0, 3, True, 2.0])
def test_invalid_partition_count_refuses_before_output(tmp_path, project, shards):
    with pytest.raises(ValueError, match='one or two'):
        RUNNER.run_suite(tmp_path / 'evidence', 10, root=project, shards=shards)
    assert not (tmp_path / 'evidence').exists()


def test_zero_worker_exits_without_evidence_fail_the_aggregate(tmp_path, project, monkeypatch):
    monkeypatch.setattr(RUNNER, '_run_suite', lambda *args, **kwargs: 0)
    output = tmp_path / 'evidence'
    assert RUNNER.run_suite(output, 10, root=project, shards=2) == 2
    receipt = json.loads((output / 'source-suite.json').read_text())
    assert receipt['status'] == 'failed' and receipt['shard_exits'] == [0, 0]


def test_temporary_namespace_inside_checkout_refuses_before_dispatch(tmp_path, project, monkeypatch):
    temporary = project / 'temporary'
    temporary.mkdir()
    monkeypatch.setattr(RUNNER.tempfile, 'gettempdir', lambda: str(temporary))
    monkeypatch.setattr(RUNNER, '_run_suite', lambda *args, **kwargs:
                        pytest.fail('Unsafe temporary namespace dispatched'))
    output = tmp_path / 'evidence'
    assert RUNNER.run_suite(output, 10, root=project, shards=2) == 2
    receipt = json.loads((output / 'source-suite.json').read_text())
    assert receipt['status'] == 'failed' and 'outside the source checkout' in receipt['error']
    assert 'temporary_roots' not in receipt


def test_workflow_command_runs_actual_partition_driver(tmp_path, project):
    """Execute the extracted command against a tiny source project, including -I."""
    import yaml

    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / '.github/workflows/qualification.yml').read_text())
    steps = workflow['jobs']['full-suite']['steps']
    step = next(step for step in steps if step.get('name') == 'Run the complete Windows source suite')
    command = shlex.split(step['run'])
    assert command[:3] == ['python', '-I', 'scripts/run_source_suite.py']
    # Use the actual driver, plugin and workflow arguments; keep the tiny tests
    # instead of dispatching a hosted run. The installed interpreter is required.
    scripts = project / 'scripts'
    scripts.mkdir()
    for name in ('run_source_suite.py', 'harness_qualification_stacks.py'):
        shutil.copy2(root / 'scripts' / name, scripts / name)
    partition_project(project)
    result = subprocess.run([sys.executable, *command[1:]], cwd=project,
                            capture_output=True, text=True, timeout=40)
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads((project / 'full-suite' / 'source-suite.json').read_text())
    assert receipt['shard_count'] == 2 and receipt['timeout_seconds'] == 2700
    assert receipt['coverage'] == {'collected_cases': 4, 'executed_cases': 4}
