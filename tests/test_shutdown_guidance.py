"""Host fault controls for shutdown uncertainty; never native Windows evidence."""

import json
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from attune_harness import process, test_cli
from attune_harness.cli import main
from attune_harness.review_store import read_record
from test_test_change import create, project  # Reuse the existing disposable Git fixture.


class FakeProcess:
    def __init__(self, returncode):
        self.returncode = returncode

    def poll(self):
        return self.returncode


class FakeJob:
    def __init__(self, error, returncode):
        self.error = error
        self.process = FakeProcess(returncode)
        self.calls = []

    def __enter__(self):
        self.calls.append('enter')
        return self

    def __exit__(self, *args):
        self.calls.append('close')

    def launch(self, argv, **kwargs):
        self.calls.append('launch')
        kwargs['stdout'].write(b'child-started\n')
        return self.process

    def stop(self, child):
        assert child is self.process
        self.calls.append('stop')
        if self.error is not None:
            raise self.error

    def launch_failure(self):
        self.calls.append('launch_failure')
        return None


def windows_backend(monkeypatch, error, returncode=0):
    from attune_harness import windows

    job = FakeJob(error, returncode)
    monkeypatch.setattr(windows, 'WindowsJob', lambda: job)
    # Replace only this module's view; pathlib and tempfile remain on the host OS.
    monkeypatch.setattr(process, 'os', SimpleNamespace(name='nt', fstat=os.fstat))
    clock = iter((0.0, 2.0))
    monkeypatch.setattr(process, 'time', SimpleNamespace(monotonic=lambda: next(clock)))
    return job


@pytest.mark.parametrize('kind', ['termination_denied', 'wait_oserror', 'wait_timeout'])
@pytest.mark.parametrize('returncode', [None, 0])
def test_shutdown_failure_preserves_cause_and_never_returns_success(
    tmp_path, monkeypatch, kind, returncode
):
    original = {
        'termination_denied': PermissionError('controlled job termination denial'),
        'wait_oserror': OSError('controlled wait failure'),
        'wait_timeout': subprocess.TimeoutExpired(['synthetic-child'], 5),
    }[kind]
    job = windows_backend(monkeypatch, original, returncode)
    with pytest.raises(OSError) as caught:
        process.invoke(('synthetic-child',), '', cwd=tmp_path, timeout=1)
    error = caught.value
    assert type(error).__name__ == 'ProcessShutdownError'
    assert error.__cause__ is original
    assert str(original) in str(error) and type(original).__name__ in str(error)
    assert 'shutdown' in str(error).lower() and 'unknown' in str(error).lower()
    assert 'unconfirmed' in str(error).lower()
    assert 'attune-harness status TASK_DIR' in error.next_action
    assert 'record.json' in error.next_action
    assert 'do not retry automatically' in error.next_action.lower()
    assert job.calls == ['enter', 'launch', 'stop', 'close']
    assert job.process.returncode is returncode


@pytest.mark.parametrize('kind', [KeyboardInterrupt, SystemExit])
def test_shutdown_baseexception_is_not_reclassified(tmp_path, monkeypatch, kind):
    original = kind('controlled interruption')
    job = windows_backend(monkeypatch, original)
    with pytest.raises(kind) as caught:
        process.invoke(('synthetic-child',), '', cwd=tmp_path)
    assert caught.value is original
    assert job.calls == ['enter', 'launch', 'stop', 'close']


def test_successful_job_shutdown_keeps_original_result(tmp_path, monkeypatch):
    job = windows_backend(monkeypatch, None)
    result = process.invoke(('synthetic-child',), '', cwd=tmp_path)
    assert result.returncode == 0 and result.failure is None
    assert result.stdout == 'child-started\n' and result.stderr == ''
    assert job.calls == ['enter', 'launch', 'stop', 'launch_failure', 'close']


def test_posix_cleanup_error_keeps_original_identity(tmp_path, monkeypatch):
    original = PermissionError('controlled POSIX group denial')
    child = FakeProcess(0)
    monkeypatch.setattr(process, 'subprocess', SimpleNamespace(Popen=lambda *a, **k: child))
    monkeypatch.setattr(process, 'os', SimpleNamespace(name='posix', fstat=os.fstat))
    def fail(_child):
        raise original
    monkeypatch.setattr(process, '_kill_group', fail)
    with pytest.raises(PermissionError) as caught:
        process.invoke(('synthetic-child',), '', cwd=tmp_path)
    assert caught.value is original


@pytest.mark.parametrize('output_format', ['json', 'markdown'])
def test_cli_shutdown_error_gives_inspection_not_input_correction(
    tmp_path, monkeypatch, capsys, output_format
):
    windows_backend(monkeypatch, PermissionError('controlled termination denial'))
    with pytest.raises(OSError) as caught:
        process.invoke(('synthetic-child',), '', cwd=tmp_path)
    def fail(*args, **kwargs):
        raise caught.value
    monkeypatch.setattr(test_cli, 'create_test_task', fail)
    result = main(['test', '--scope', 'a.py', '--interpreter', sys.executable,
                   '--task-dir', str(tmp_path / 'task'), '--format', output_format])
    output = capsys.readouterr().out
    assert result == 2
    assert 'unresolved' in output and 'shutdown' in output.lower()
    assert 'Correct the reported input' not in output
    assert 'attune-harness status TASK_DIR' in output and 'record.json' in output
    assert 'do not retry automatically' in output.lower()
    if output_format == 'json':
        envelope = json.loads(output)
        assert envelope['error']['type'] == 'ProcessShutdownError'


def test_cli_input_error_still_requests_input_correction(tmp_path, monkeypatch, capsys):
    def fail(*args, **kwargs):
        raise ValueError('controlled invalid input')
    monkeypatch.setattr(test_cli, 'create_test_task', fail)
    assert main(['test', '--scope', 'a.py', '--interpreter', sys.executable,
                 '--task-dir', str(tmp_path / 'task')]) == 2
    envelope = json.loads(capsys.readouterr().out)
    assert envelope['status'] == 'blocked'
    assert envelope['error']['type'] == 'ValueError'
    assert 'Correct the reported input' in envelope['next_action']


@pytest.mark.parametrize('kind', ['termination_denied', 'wait_timeout'])
def test_saved_shutdown_uncertainty_status_never_dispatches_again(
    project, tmp_path, monkeypatch, capsys, kind
):
    directory, preview = create(project, tmp_path)
    original = (PermissionError('controlled termination denial')
                if kind == 'termination_denied'
                else subprocess.TimeoutExpired(['synthetic-child'], 5))
    job = windows_backend(monkeypatch, original)
    assert main(['test', '--task-dir', str(directory), '--checkpoint',
                 preview['checkpoint_digest'], '--accept']) == 2
    shown = json.loads(capsys.readouterr().out)
    assert shown['status'] == 'unresolved'
    current = shown['presentation']['current_result']
    assert current['outcome'] == 'interrupted'
    assert 'shutdown' in current['detail'].lower() and 'unknown' in current['detail'].lower()
    assert 'Correct the reported input' not in json.dumps(shown)
    assert 'attune-harness status TASK_DIR' in shown['presentation']['next_action']
    record = read_record(directory)
    event, = record['execution']['events']
    assert event['state'] == 'failed' and event['phase'] == 'dispatching'
    assert event['effects'] == 'unknown' and event['attempts'] == 1
    assert event['error']['type'] == 'ProcessShutdownError'
    assert str(original) in event['error']['detail']
    assert str(original) in current['detail']
    assert 'result' not in event and 'result' not in record['execution']
    assert not (directory / 'stdout.txt').exists()
    assert not (directory / 'stderr.txt').exists()
    saved = (directory / 'record.json').read_bytes()
    assert main(['status', str(directory)]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status['status'] == 'unresolved'
    assert 'shutdown' in status['presentation']['current_result']['detail'].lower()
    assert (directory / 'record.json').read_bytes() == saved
    from attune_harness.task_policies import execute_task
    repeated = execute_task(directory)
    assert repeated['status'] == 'unresolved'
    assert job.calls == ['enter', 'launch', 'stop', 'close']
    repeated_event, = read_record(directory)['execution']['events']
    assert repeated_event['attempts'] == 1 and repeated_event['effects'] == 'unknown'
