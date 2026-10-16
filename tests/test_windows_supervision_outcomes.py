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


def _runner_terminal_diagnostic(first_wait, deadline, wait, clock, last_error):
    """Diagnostic-only finite handle observation; never a qualification verdict."""
    row = {'first_wait': first_wait, 'deadline': deadline, 'wait_calls': 0,
           'qualification': False}
    begin = clock()
    row['begin'] = begin
    if first_wait == 0:
        row['classification'] = 'already_terminal_at_original_return'
        return row
    if first_wait != 258:
        row['classification'] = 'original_wait_not_timeout'
        return row
    remaining = deadline - begin
    if remaining <= 0:
        row['classification'] = 'no_original_budget_remaining'
        return row
    milliseconds = int(remaining * 1000)
    row['requested_ms'] = milliseconds
    if milliseconds == 0:
        row['classification'] = 'less_than_one_millisecond_remaining'
        return row
    try:
        row['wait_calls'] = 1
        result = int(wait(milliseconds))
        # Read an error immediately; the following clock call must not replace it.
        if result == 0xFFFFFFFF:
            row['winerror'] = int(last_error())
        end = clock()
        row.update(wait_result=result, end=end)
        if end < begin:
            classification = 'invalid_clock_order'
        elif result == 0 and end <= deadline:
            classification = 'known_terminal_within_original_budget'
        elif result == 0:
            classification = 'terminal_observed_after_original_budget'
        elif result == 258:
            classification = 'not_confirmed_in_single_bounded_wait'
        elif result == 0xFFFFFFFF:
            classification = 'native_wait_failed'
        else:
            classification = 'unexpected_native_wait_result'
        row['classification'] = classification
    except Exception as error:
        row.update(classification='observation_error',
                   error_type=type(error).__name__)
    return row


@pytest.mark.parametrize('initial,begin,result,end,expected', [
    (0, 1.0, None, None, 'already_terminal_at_original_return'),
    (258, 5.0, None, None, 'no_original_budget_remaining'),
    (258, 4.9995, None, None, 'less_than_one_millisecond_remaining'),
    (258, 1.0, 0, 4.0, 'known_terminal_within_original_budget'),
    (258, 1.0, 0, 5.01, 'terminal_observed_after_original_budget'),
    (258, 1.0, 258, 5.0, 'not_confirmed_in_single_bounded_wait'),
    (258, 1.0, 0xFFFFFFFF, 1.0, 'native_wait_failed'),
    (258, 1.0, 128, 1.0, 'unexpected_native_wait_result'),
])
def test_runner_terminal_probe_causal_controls(initial, begin, result, end, expected):
    clock = Clock()
    clock.now = begin
    calls = []

    def wait(milliseconds):
        assert result is not None, 'control forbids any diagnostic wait'
        assert 0 < milliseconds <= int((5.0 - begin) * 1000)
        calls.append(milliseconds)
        clock.now = end
        return result

    row = _runner_terminal_diagnostic(initial, 5.0, wait, clock.monotonic, lambda: 6)
    assert row['classification'] == expected
    assert row['qualification'] is False
    assert row['wait_calls'] == len(calls) <= 1
    if result == 0xFFFFFFFF:
        assert row['winerror'] == 6


def test_runner_terminal_probe_api_exception_is_not_terminal_evidence():
    def refused(_milliseconds):
        raise OSError(5, 'synthetic wait refusal')

    row = _runner_terminal_diagnostic(258, 5.0, refused, lambda: 1.0, lambda: 0)
    assert row['classification'] == 'observation_error'
    assert row['qualification'] is False and row['wait_calls'] == 1


def _runner_terminal_call_stop(original, job, process, clock, row):
    """Ancillary samples cannot prevent or replace the one original stop."""
    def observe(key):
        try:
            value = clock()
            row[key] = value
            if key == 'entered':
                row['deadline'] = value + 5.0
        except BaseException as error:
            try:
                row.setdefault('clock_errors', []).append({
                    'sample': key, 'error_type': type(error).__name__})
            except BaseException:
                pass  # A reporting failure cannot replace original stop.

    observe('entered')
    try:
        return original(job, process)
    finally:
        observe('returned_or_raised')


def _runner_terminal_dispose(handles, controller_stopped, wait, terminate,
                             close, native_error):
    """Return disposal facts and errors; never use a live controller's handles."""
    observed = list(handles)
    row = {'controller_stopped': controller_stopped,
           'observed_handle_count': len(observed), 'closed_confirmed_count': 0,
           'terminal_confirmed_count': 0, 'qualification': False}
    errors = []
    if not controller_stopped:
        errors.append(TimeoutError('diagnostic controller did not stop'))
    else:
        for handle in observed:
            try:
                result = int(wait(handle, 0))
                if result == 0xFFFFFFFF:
                    raise native_error()
                if result == 258:
                    if not terminate(handle, 1):
                        raise native_error()
                    result = int(wait(handle, 5000))
                    if result == 0xFFFFFFFF:
                        raise native_error()
                if result != 0:
                    raise TimeoutError('diagnostic child cleanup unconfirmed')
                row['terminal_confirmed_count'] += 1
            except BaseException as error:
                errors.append(error)
            finally:
                try:
                    if close(handle):
                        row['closed_confirmed_count'] += 1
                    else:
                        errors.append(native_error())
                except BaseException as error:
                    errors.append(error)
    row['unclosed_observed_count'] = len(observed) - row['closed_confirmed_count']
    row['resources_unconfirmed'] = bool(
        not controller_stopped or row['unclosed_observed_count'] or
        row['terminal_confirmed_count'] != len(observed))
    row['errors'] = [type(error).__name__ for error in errors]
    return row, errors


def _runner_terminal_poison(state, session, row):
    if row['resources_unconfirmed']:
        reason = 'Runner diagnostic resources unconfirmed; external disposal required'
        state['poison'] = reason  # Guard remains effective if session signalling fails.
        session.shouldstop = reason


def _runner_terminal_guard(state):
    if state.get('poison'):
        raise RuntimeError(state['poison'])


def _runner_terminal_raise(primary, traceback, cleanup):
    if primary is not None:
        if cleanup:
            raise primary.with_traceback(traceback) from cleanup[0]
        raise primary.with_traceback(traceback)
    if cleanup:
        raise cleanup[0]


@pytest.mark.parametrize('fault', ['none', 'enter', 'exit', 'both'])
@pytest.mark.parametrize('fails', [False, True])
def test_runner_terminal_actual_stop_wrapper_preserves_once_and_primary(fault, fails):
    calls, samples, row = [], [], {}
    original_error = OSError(5, 'original stop failure')
    returned = object()

    def original(job, process):
        calls.append((job, process))
        if fails:
            raise original_error
        return returned

    def clock():
        phase = 'enter' if not samples else 'exit'
        samples.append(phase)
        if fault in (phase, 'both'):
            raise RuntimeError('ancillary clock failure')
        return 1.0 if phase == 'enter' else 2.0

    if fails:
        with pytest.raises(OSError) as caught:
            _runner_terminal_call_stop(original, 71, 72, clock, row)
        assert caught.value is original_error
        traceback = caught.value.__traceback__
        names = []
        while traceback is not None:
            names.append(traceback.tb_frame.f_code.co_name)
            traceback = traceback.tb_next
        assert 'original' in names
    else:
        assert _runner_terminal_call_stop(original, 71, 72, clock, row) is returned
    assert calls == [(71, 72)] and samples == ['enter', 'exit']
    if fault in ('enter', 'both'):
        assert 'deadline' not in row
    else:
        assert row['deadline'] == 6.0


@pytest.mark.parametrize('fault,closed,terminal', [
    ('live_controller', 0, 0), ('close_false', 0, 1),
    ('close_raises', 0, 1), ('wait_failed', 1, 0),
    ('terminate_false', 1, 0), ('none', 1, 1),
])
def test_runner_terminal_actual_disposal_poison_prevents_next_dispatch(fault, closed, terminal):
    calls, state = [], {}
    session = SimpleNamespace(shouldstop=False)

    def wait(handle, milliseconds):
        calls.append(('wait', handle, milliseconds))
        return 0xFFFFFFFF if fault == 'wait_failed' else (258 if fault == 'terminate_false' else 0)

    def terminate(handle, code):
        calls.append(('terminate', handle, code))
        return False

    def close(handle):
        calls.append(('close', handle))
        if fault == 'close_raises':
            raise OSError(6, 'synthetic close refusal')
        return fault != 'close_false'

    def native_error():
        calls.append(('error',))
        return OSError(6, 'synthetic native refusal')

    row, errors = _runner_terminal_dispose(
        [91], fault != 'live_controller', wait, terminate, close, native_error)
    assert row['closed_confirmed_count'] == closed
    assert row['unclosed_observed_count'] == 1 - closed
    assert row['terminal_confirmed_count'] == terminal
    _runner_terminal_poison(state, session, row)
    dispatched = []
    if fault == 'none':
        assert not errors and not session.shouldstop
        _runner_terminal_guard(state)
        dispatched.append('next native child')
    else:
        assert errors and session.shouldstop and row['resources_unconfirmed']
        with pytest.raises(RuntimeError, match='external disposal required'):
            _runner_terminal_guard(state)
            dispatched.append('next native child')
        assert not dispatched
    if fault == 'live_controller':
        assert calls == []
    if fault in ('wait_failed', 'close_false'):
        bad_call = 'wait' if fault == 'wait_failed' else 'close'
        index = next(i for i, call in enumerate(calls) if call[0] == bad_call)
        assert calls[index + 1] == ('error',)


def test_runner_terminal_actual_final_raise_keeps_original_over_cleanup():
    original = AssertionError('original immediate child wait')
    cleanup = OSError(6, 'cleanup close refusal')
    state, session = {}, SimpleNamespace(shouldstop=False)

    def original_predicate():
        raise original

    try:
        original_predicate()
    except AssertionError as error:
        primary, traceback = error, error.__traceback__
    disposal, errors = _runner_terminal_dispose(
        [91], True, lambda handle, milliseconds: 0,
        lambda handle, code: pytest.fail('terminal child must not be terminated'),
        lambda handle: False, lambda: cleanup)
    _runner_terminal_poison(state, session, disposal)
    assert disposal['closed_confirmed_count'] == 0
    assert disposal['unclosed_observed_count'] == 1 and session.shouldstop
    with pytest.raises(RuntimeError, match='external disposal required'):
        _runner_terminal_guard(state)
    with pytest.raises(AssertionError) as caught:
        _runner_terminal_raise(primary, traceback, errors)
    assert caught.value is original and caught.value.__cause__ is cleanup
    names = []
    traceback = caught.value.__traceback__
    while traceback is not None:
        names.append(traceback.tb_frame.f_code.co_name)
        traceback = traceback.tb_next
    assert 'original_predicate' in names
