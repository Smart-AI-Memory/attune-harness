"""Real pytest outcomes cannot override captured evidence or producer identity."""

import json
import os
from pathlib import Path
from threading import Event

import pytest

from attune_harness import test_change, test_execution
from attune_harness.review_store import RunStore
from attune_harness.task_contract import read_task
from attune_harness.task_policies import execute_task, inspect_task
from test_connected_journey import complete, journey, linked  # noqa: F401
from test_test_change import accept, outcome, project, put  # noqa: F401

pytestmark = pytest.mark.skipif(os.name != 'posix', reason='Testing owns a POSIX execution profile')


def count_dispatches(monkeypatch, after=None):
    original = test_execution.process.invoke
    calls = []

    def invoke(*args, **kwargs):
        calls.append(args[0])
        result = original(*args, **kwargs)
        if after is not None:
            after()
        return result

    monkeypatch.setattr(test_execution.process, 'invoke', invoke)
    return calls


@pytest.mark.parametrize(('body', 'expected', 'returncode'), [
    ('def test_interrupt():\n    raise KeyboardInterrupt()\n', 'interrupted', 2),
    ('import pytest\ndef test_stop():\n    pytest.exit("stop fixture", returncode=3)\n', 'blocked', 3),
])
def test_real_pytest_interrupt_is_retained_without_redispatch(project, tmp_path, monkeypatch, body, expected, returncode):
    put(project, 'tests/test_logic.py', body)
    directory = accept(project, tmp_path)
    calls = count_dispatches(monkeypatch)
    result = execute_task(directory)
    observed = result['execution']['result']
    assert outcome(result) == expected
    assert observed['process']['returncode'] == returncode
    assert observed['pytest']['session_started'] is True
    assert observed['pytest']['passed'] == 0
    before = (directory / 'record.json').read_bytes()
    assert outcome(execute_task(directory)) == expected
    assert len(calls) == 1
    assert (directory / 'record.json').read_bytes() == before


def test_cancel_before_start_cannot_claim_execution_or_retry(project, tmp_path, monkeypatch):
    directory = accept(project, tmp_path)
    cancel = Event()
    cancel.set()
    calls = count_dispatches(monkeypatch)
    result = test_change.execute_test_task(directory, cancel=cancel)
    saved = result['execution']['result']
    assert outcome(result) == 'interrupted'
    assert saved['process']['failure'] == 'cancelled_before_start'
    assert saved['pytest'] is None
    assert not (directory / 'pytest.json').exists()
    before = (directory / 'record.json').read_bytes()
    cancel.clear()
    assert outcome(execute_task(directory)) == 'interrupted'
    assert len(calls) == 1 and (directory / 'record.json').read_bytes() == before


@pytest.mark.parametrize(('damage', 'detail'), [
    ('mode', 'Invalid pytest mode'),
    ('structure', 'Invalid pytest evidence structure'),
    ('calls', 'Inconsistent test call evidence'),
    ('selection', 'outside the selected test files'),
    ('session', 'does not establish this process execution'),
    ('exit', 'does not establish this process execution'),
    ('symlink', 'Invalid pytest evidence artifact'),
])
def test_successful_process_requires_valid_execution_local_observation(project, tmp_path, monkeypatch, damage, detail):
    directory = accept(project, tmp_path)

    def corrupt():
        path = directory / 'pytest.json'
        value = json.loads(path.read_text())
        assert value['passed'] == 1
        if damage == 'mode':
            value['collect_only'] = 0
        elif damage == 'structure':
            value['collected'] = [123]
        elif damage == 'calls':
            value['calls'] = 0
        elif damage == 'selection':
            value['collected'] = ['tests/foreign.py::test_pass']
        elif damage == 'session':
            value['session_started'] = False
        elif damage == 'exit':
            value['exit_code'] = 1
        elif damage == 'symlink':
            retained = directory / 'original-pytest.json'
            path.rename(retained)
            path.symlink_to(retained)
            return
        path.write_text(json.dumps(value), encoding='utf-8')

    calls = count_dispatches(monkeypatch, corrupt)
    result = execute_task(directory)
    saved = result['execution']['result']
    assert saved['process']['returncode'] == 0
    assert outcome(result) == 'blocked' and detail in saved['detail']
    before = (directory / 'record.json').read_bytes()
    assert outcome(inspect_task(directory)) == 'blocked'
    assert outcome(execute_task(directory)) == 'blocked'
    assert len(calls) == 1
    assert (directory / 'record.json').read_bytes() == before
    assert (project / 'src/demo/logic.py').read_text().endswith('    return 42\n')


@pytest.mark.parametrize('changed', ['source', 'observer'])
def test_input_drift_after_successful_child_blocks_current_and_reused_success(project, tmp_path, monkeypatch, changed):
    worker = tmp_path / 'observer.py'
    worker.write_bytes(test_execution.WORKER.read_bytes())
    monkeypatch.setattr(test_execution, 'WORKER', worker)
    monkeypatch.setattr(test_change, 'WORKER', worker)
    directory = accept(project, tmp_path)
    target = project / 'src/demo/logic.py' if changed == 'source' else worker

    def drift():
        target.write_bytes(target.read_bytes() + b'\n# changed after child completed\n')

    calls = count_dispatches(monkeypatch, drift)
    result = execute_task(directory)
    event_result = result['execution']['events'][0]['result']
    assert event_result['process']['returncode'] == 0
    assert event_result['pytest']['passed'] == 1
    assert event_result['outcome'] == 'blocked'
    assert ('Original source' if changed == 'source' else 'observer changed') in event_result['detail']
    assert outcome(result) == 'blocked'
    before = (directory / 'record.json').read_bytes()
    with pytest.raises(ValueError, match='Stale'):
        execute_task(directory)
    assert len(calls) == 1 and (directory / 'record.json').read_bytes() == before


@pytest.mark.parametrize(('field', 'value'), [
    ('task_id', 'foreign-producer'),
    ('probe_digest', '0' * 64),
    ('scope', ['probe.py']),
])
def test_edited_handoff_binding_cannot_authorize_test_dispatch(journey, capsys, field, value):
    producer = complete(journey, capsys)
    draft = linked(journey)
    directory = Path(draft['record_path']).parent
    if field == 'scope':
        draft['request']['selection']['scope'] = value
    else:
        draft['request']['source_task'][field] = value
    RunStore(directory, existing=True).save(draft)
    edited = read_task(directory)
    before = (directory / 'record.json').read_bytes()
    producer_before = (producer / 'record.json').read_bytes()
    calls_before = (journey[0] / 'calls.jsonl').read_bytes()
    with pytest.raises(ValueError, match='Stale or overridden repair handoff'):
        test_change.accept_test_task(directory, edited['checkpoint_digest'])
    assert (directory / 'record.json').read_bytes() == before
    assert (producer / 'record.json').read_bytes() == producer_before
    assert (journey[0] / 'calls.jsonl').read_bytes() == calls_before
    assert not (directory / 'inputs').exists()
    assert (journey[1] / 'unrelated.txt').read_text() == "Preserve this user's dirty work.\n"


def test_interpreter_drift_is_detected_without_modifying_installed_python(project, tmp_path, monkeypatch):
    import shutil
    import sys

    # A disposable interpreter uses the existing environment's libraries read-only.
    environment = tmp_path / 'python-environment'
    (environment / 'bin').mkdir(parents=True)
    executable = environment / 'bin/python'
    shutil.copy2(Path(sys.executable).resolve(), executable)
    (environment / 'pyvenv.cfg').write_text(
        f'home = {Path(sys._base_executable).resolve().parent}\n'
        'include-system-site-packages = true\n', encoding='utf-8'
    )
    (environment / 'lib').symlink_to(Path(sys.prefix) / 'lib', target_is_directory=True)
    directory = tmp_path / 'task'
    draft = test_change.create_test_task(project, directory, scope=['src/demo/logic.py'],
                                        interpreter=str(executable))
    test_change.accept_test_task(directory, draft['checkpoint_digest'])

    def drift():
        with executable.open('ab') as stream:
            stream.write(b'changed after completed child')

    calls = count_dispatches(monkeypatch, drift)
    result = execute_task(directory)
    observed = result['execution']['events'][0]['result']
    assert observed['process']['returncode'] == 0
    assert observed['pytest']['passed'] == 1
    assert observed['outcome'] == 'blocked'
    assert observed['detail'] == 'Interpreter changed during execution'
    before = (directory / 'record.json').read_bytes()
    with pytest.raises(ValueError, match='Stale interpreter/observer identity'):
        execute_task(directory)
    assert len(calls) == 1 and (directory / 'record.json').read_bytes() == before
