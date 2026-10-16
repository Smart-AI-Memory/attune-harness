"""Portable causal controls; these fakes do not qualify native Windows behavior."""
# qualify: platform

import ctypes
from dataclasses import asdict
import os
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest

from attune_harness import process as runner
from attune_harness import windows


class Clock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, delay):
        assert 0 <= delay <= 0.01
        self.sleeps.append(delay)
        self.now += delay


def job_control(monkeypatch, active=(1, 0), fault=None):
    clock = Clock()
    counts = iter(active)
    calls = []

    def terminate(handle, exit_code):
        calls.append(('terminate', handle, exit_code))
        return fault != 'terminate'

    def query(handle, information_class, buffer, size, returned):
        calls.append(('query', handle, information_class, size, returned))
        if fault == 'query':
            return False
        if fault == 'late_zero':
            clock.now = 5.25
            ctypes.cast(buffer, ctypes.POINTER(windows.BasicAccounting)).contents.active_processes = 0
            return True
        ctypes.cast(buffer, ctypes.POINTER(windows.BasicAccounting)).contents.active_processes = (
            1 if fault == 'active' else next(counts))
        return True

    def checked(value):
        if not value:
            raise OSError(5, 'synthetic API refusal')
        return value

    class Bootstrap:
        def wait(self, *, timeout):
            calls.append(('wait', timeout))
            assert timeout == 5
            clock.now += 2
            if fault == 'bootstrap':
                raise runner.subprocess.TimeoutExpired(('owned-bootstrap',), timeout)
            return 0

    monkeypatch.setattr(windows, 'kernel', lambda: SimpleNamespace(
        TerminateJobObject=terminate, QueryInformationJobObject=query))
    monkeypatch.setattr(windows, 'time', clock)
    monkeypatch.setattr(windows, 'checked', checked)
    job = windows.WindowsJob()
    job.handle = 71
    return job, Bootstrap(), clock, calls


def test_stop_observes_whole_job_after_bootstrap_exit(monkeypatch):
    job, bootstrap, clock, calls = job_control(monkeypatch, active=(2, 1, 0))
    job.stop(bootstrap)
    assert [call[0] for call in calls] == ['terminate', 'wait', 'query', 'query', 'query']
    assert len(clock.sleeps) == 2 and clock.now < 5
    assert all(call[1:] == (71, 1, 48, None) for call in calls if call[0] == 'query')
    # A bootstrap-only wait never observes the two live associations and fails above.


def test_stop_refuses_zero_returned_after_same_deadline(monkeypatch):
    job, bootstrap, clock, calls = job_control(monkeypatch, fault='late_zero')
    with pytest.raises(TimeoutError, match='within five seconds'):
        job.stop(bootstrap)
    assert clock.now == 5.25
    assert [call[0] for call in calls] == ['terminate', 'wait', 'query']
    assert not clock.sleeps


@pytest.mark.parametrize('fault', ['terminate', 'bootstrap', 'query', 'active'])
def test_stop_errors_and_one_shared_deadline_refuse(monkeypatch, fault):
    job, bootstrap, clock, calls = job_control(monkeypatch, fault=fault)
    expected = (TimeoutError if fault == 'active' else
                runner.subprocess.TimeoutExpired if fault == 'bootstrap' else OSError)
    with pytest.raises(expected):
        job.stop(bootstrap)
    assert clock.now <= 5.000001
    assert sum(call[0] == 'wait' for call in calls) <= 1
    if fault == 'active':
        assert clock.sleeps and clock.now >= 5
    if fault in ('terminate', 'bootstrap'):
        assert not any(call[0] == 'query' for call in calls)


def process_control(monkeypatch, failure, *, stop_error=True, close_error=False,
                    interrupt=False, missing=False):
    clock = Clock()
    cancel = Event()
    original_stop = OSError(5, 'private path and environment must not enter diagnostics')
    original_close = PermissionError(13, 'private cleanup detail')
    seen = []

    class Bootstrap:
        returncode = None

        def poll(self):
            if interrupt:
                raise KeyboardInterrupt('original interrupt')
            if failure == 'cancelled_effects_unknown':
                cancel.set()
            elif failure == 'timeout_effects_unknown':
                clock.now = 3
            if failure is None:
                self.returncode = 0
                return 0
            return None

    class Job:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            seen.append('close')
            if close_error:
                raise original_close

        def launch(self, argv, **kwargs):
            if missing:
                raise FileNotFoundError(2, 'synthetic absent executable')
            self.process = Bootstrap()
            kwargs['stdout'].write(b'partial output')
            kwargs['stdout'].flush()
            return self.process

        def stop(self, process):
            seen.append('stop')
            process.returncode = 0
            if stop_error:
                raise original_stop

        def launch_failure(self):
            assert not stop_error, 'metadata queried after unconfirmed shutdown'
            return None

    monkeypatch.setattr(windows, 'WindowsJob', Job)
    # Do not mutate os.name globally or change pathlib/pytest platform behavior.
    monkeypatch.setattr(runner, 'os', SimpleNamespace(name='nt', fstat=os.fstat))
    monkeypatch.setattr(runner, 'time', clock)
    return cancel, original_stop, original_close, seen


@pytest.mark.parametrize('failure', [None, 'timeout_effects_unknown',
                                     'cancelled_effects_unknown', 'output_limit'])
@pytest.mark.parametrize('close_error', [False, True])
def test_windows_supervision_preserves_result_and_separate_cleanup(monkeypatch, failure, close_error):
    cancel, original_stop, original_close, seen = process_control(
        monkeypatch, failure, close_error=close_error)
    limit = 8 if failure == 'output_limit' else 64
    with pytest.raises(runner.ProcessError) as caught:
        runner.invoke(('owned-fixture',), '', cwd=Path('.'), timeout=3,
                      max_output_bytes=limit, cancel=cancel)
    error = caught.value
    assert error.result.failure == failure
    assert error.result.returncode == 0
    assert error.result.stdout == 'partial output'[:limit]
    assert error.result.stderr == ''
    assert error.failure == (failure or 'supervision_effects_unknown')
    assert error.process_stopped is False
    assert error.original_error is original_stop
    assert error.diagnostics[0] == 'supervision:OSError:errno=5'
    assert ('resource_cleanup:PermissionError:errno=13' in error.diagnostics) == close_error
    assert error.__cause__ is (original_close if close_error else original_stop)
    assert 'private' not in str(error) and 'private' not in repr(error.diagnostics)
    assert seen == ['stop', 'close']
    assert set(asdict(error.result)) == {'argv', 'returncode', 'stdout', 'stderr', 'failure'}


def test_completed_windows_result_is_retained_when_resource_close_fails(monkeypatch):
    _, _, original_close, seen = process_control(
        monkeypatch, None, stop_error=False, close_error=True)
    with pytest.raises(runner.ProcessError) as caught:
        runner.invoke(('owned-fixture',), '', cwd=Path('.'))
    error = caught.value
    assert error.result.failure is None and error.result.returncode == 0
    assert error.result.stdout == 'partial output'
    assert error.process_stopped is True
    assert error.diagnostics == ('resource_cleanup:PermissionError:errno=13',)
    assert error.original_error is original_close
    assert seen == ['stop', 'close']


def test_original_interrupt_survives_stop_and_resource_close_failure(monkeypatch):
    process_control(monkeypatch, None, close_error=True, interrupt=True)
    with pytest.raises(KeyboardInterrupt, match='original interrupt') as caught:
        runner.invoke(('owned-fixture',), '', cwd=Path('.'))
    assert caught.value.process_diagnostics == (
        'supervision:OSError:errno=5', 'resource_cleanup:PermissionError:errno=13')
    assert isinstance(caught.value.__cause__, PermissionError)


def test_missing_launch_result_survives_resource_close_failure(monkeypatch):
    _, _, _, seen = process_control(monkeypatch, None, close_error=True, missing=True)
    with pytest.raises(runner.ProcessError) as caught:
        runner.invoke(('owned-fixture',), '', cwd=Path('.'))
    assert caught.value.result.failure == 'not_found'
    assert caught.value.result.returncode is None
    assert caught.value.process_stopped is False
    assert seen == ['close']
