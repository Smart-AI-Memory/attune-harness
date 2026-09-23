"""Actual subprocess failure probes; no native CLI or credential use."""

import os
import sys
from threading import Event, Timer

import pytest

from attune_harness.process import invoke

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX process qualification")


def command(code):
    return (sys.executable, "-c", code)


def test_success_and_nonzero_keep_streams(tmp_path):
    result = invoke(command('import sys;print(sys.stdin.read());print("detail", file=sys.stderr)'), 'literal $(echo nope)', cwd=tmp_path)
    assert result.stdout == 'literal $(echo nope)\n'
    assert result.stderr == 'detail\n'
    assert result.failure is None
    failed = invoke(command('import sys;print("error",file=sys.stderr);sys.exit(2)'), '', cwd=tmp_path)
    assert failed.failure == "nonzero_exit" and failed.returncode == 2


def test_missing_executable_and_launch_denied(tmp_path):
    assert invoke((str(tmp_path/'missing'),), '', cwd=tmp_path).failure == 'not_found'
    file = tmp_path/'not-executable'
    file.write_text('contents', encoding='utf-8')
    assert invoke((str(file),), '', cwd=tmp_path).failure == 'launch_failed'


def test_timeout_retains_partial_output_and_reaps_process(tmp_path):
    result = invoke(command('import time;print("partial",flush=True);time.sleep(10)'), '', cwd=tmp_path, timeout=0.2)
    assert result.failure == 'timeout_effects_unknown'
    assert result.stdout == 'partial\n'
    assert result.returncode == -9


def test_cancel_before_start_and_during_run(tmp_path):
    cancel = Event()
    cancel.set()
    result = invoke((str(tmp_path/'missing'),), '', cwd=tmp_path, cancel=cancel)
    assert result.failure == 'cancelled_before_start' and result.returncode is None
    cancel.clear()
    timer = Timer(0.2, cancel.set)
    timer.start()
    try:
        result = invoke(command('import time;time.sleep(10)'), '', cwd=tmp_path, cancel=cancel)
    finally:
        timer.cancel()
        timer.join()
    assert result.failure == 'cancelled_effects_unknown' and result.returncode == -9


def test_cancellation_after_completion_does_not_change_result(tmp_path):
    cancel = Event()
    result = invoke(command('print("done")'), '', cwd=tmp_path, cancel=cancel)
    cancel.set()
    assert result.failure is None and result.stdout == 'done\n'


@pytest.mark.parametrize('stream', ['stdout', 'stderr'])
def test_oversized_stream_cannot_pass_even_on_zero_exit(tmp_path, stream):
    result = invoke(command(f'import sys;sys.{stream}.write("x"*100000)'), '', cwd=tmp_path, max_output_bytes=100)
    assert result.failure == 'output_limit'
    assert len(result.stdout.encode())+len(result.stderr.encode()) == 100


@pytest.mark.parametrize('kwargs', [{'timeout':0}, {'timeout':float('inf')}, {'timeout':True}, {'max_output_bytes':0}, {'max_output_bytes':True}])
def test_bad_limits_fail_before_launch(tmp_path, kwargs):
    with pytest.raises(ValueError):
        invoke(('missing',), '', cwd=tmp_path, **kwargs)


@pytest.mark.parametrize('argv', [(), ('',), ('ok', 3)])
def test_bad_argv(tmp_path, argv):
    with pytest.raises(ValueError):
        invoke(argv, '', cwd=tmp_path)


def test_invalid_utf8_remains_failure(tmp_path):
    result = invoke(command('import sys;sys.stdout.buffer.write(bytes([255]))'), '', cwd=tmp_path)
    assert result.failure == 'invalid_utf8'


# The descendant's effect lands this long after it starts; the parent is
# stopped well before, and the check waits longer than that. A cold
# interpreter on a loaded runner can take a few hundred milliseconds to
# reach its first print, which is why the stop budget is not tighter: with
# 0.15 s the macOS 3.12 job stopped the parent before it had printed, twice
# on 2026-09-23, and reported stdout '' for a defect that was not there.
DESCENDANT_EFFECT_SECONDS = 2.0
STOP_BUDGET_SECONDS = 0.75


def test_timeout_stops_descendant_effect(tmp_path):
    import time
    marker = tmp_path/'late-effect'
    child_code = f'import time,pathlib;time.sleep({DESCENDANT_EFFECT_SECONDS});pathlib.Path({str(marker)!r}).write_text("effect")'
    parent_code = f'import subprocess,sys,time;subprocess.Popen([sys.executable,"-c",{child_code!r}]);print("spawned",flush=True);time.sleep(10)'
    started = time.monotonic()
    result = invoke(command(parent_code), '', cwd=tmp_path, timeout=STOP_BUDGET_SECONDS)
    assert result.failure == 'timeout_effects_unknown'
    assert result.stdout == 'spawned\n', f'parent not heard from within {STOP_BUDGET_SECONDS} s ({time.monotonic() - started:.2f} s elapsed)'
    time.sleep(DESCENDANT_EFFECT_SECONDS + 0.5)
    assert not marker.exists()


@pytest.mark.parametrize('capture', [False, True])
def test_keyboard_interrupt_preserves_default_and_opt_in_cleanup(tmp_path, monkeypatch, capture):
    import attune_harness.process as runner
    children = []
    launch = runner.subprocess.Popen
    def tracked(*args, **kwargs):
        child = launch(*args, **kwargs)
        children.append(child)
        return child
    def interrupt(_):
        raise KeyboardInterrupt
    monkeypatch.setattr(runner.subprocess, 'Popen', tracked)
    monkeypatch.setattr(runner.time, 'sleep', interrupt)
    if capture:
        result = invoke(command('import time;time.sleep(20)'), '', cwd=tmp_path, capture_interrupt=True)
        assert result.failure == 'interrupted_effects_unknown'
    else:
        with pytest.raises(KeyboardInterrupt):
            invoke(command('import time;time.sleep(20)'), '', cwd=tmp_path)
    assert children[0].poll() is not None


def test_exit_race_reaps_then_rechecks_group_without_losing_output(tmp_path, monkeypatch):
    import attune_harness.process as runner
    real = os.killpg
    calls = []
    def denied_once(pid, sig):
        calls.append(pid)
        if len(calls) == 1:
            raise PermissionError('exit race')
        return real(pid, sig)
    monkeypatch.setattr(runner.os, 'killpg', denied_once)
    result = invoke(command('print("x"*100000)'), '', cwd=tmp_path, max_output_bytes=100)
    assert result.failure == 'output_limit' and len(result.stdout) == 100
    assert result.returncode == 0 and len(calls) == 2


def test_cleanup_denial_for_live_parent_is_bounded_and_propagated(monkeypatch):
    import subprocess
    import time
    import attune_harness.process as runner
    real = os.killpg
    child = subprocess.Popen(command('import time;time.sleep(10)'), start_new_session=True)
    def denied(*args):
        raise PermissionError('actual denial')
    monkeypatch.setattr(runner.os, 'killpg', denied)
    start = time.monotonic()
    try:
        with pytest.raises(PermissionError, match='actual denial'):
            runner._kill_group(child)
        assert time.monotonic() - start < 1
        assert child.poll() is None
    finally:
        real(child.pid, 9)
        child.wait()


def test_second_group_denial_is_not_success_after_parent_exit(tmp_path, monkeypatch):
    import attune_harness.process as runner
    calls = []
    def denied(*args):
        calls.append(args)
        raise PermissionError('group still inaccessible')
    monkeypatch.setattr(runner.os, 'killpg', denied)
    with pytest.raises(PermissionError, match='group still inaccessible'):
        invoke(command('print("done")'), '', cwd=tmp_path)
    assert len(calls) == 2


def test_exit_race_still_stops_descendant_effect(tmp_path, monkeypatch):
    import time
    import attune_harness.process as runner
    real = os.killpg
    count = 0
    def denied_once(pid, sig):
        nonlocal count
        count += 1
        if count == 1:
            raise PermissionError('exit race')
        return real(pid, sig)
    marker = tmp_path / 'late-effect'
    child_code = f'import time,pathlib;time.sleep(0.5);pathlib.Path({str(marker)!r}).write_text("effect")'
    parent_code = f'import subprocess,sys;subprocess.Popen([sys.executable,"-c",{child_code!r}]);print("spawned")'
    monkeypatch.setattr(runner.os, 'killpg', denied_once)
    result = invoke(command(parent_code), '', cwd=tmp_path)
    assert result.failure is None and result.stdout == 'spawned\n' and count == 2
    time.sleep(.6)
    assert not marker.exists()
