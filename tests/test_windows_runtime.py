"""Real Windows Job Object and file-lock probes; never simulated as a native pass."""
import os
import json
from pathlib import Path
import subprocess
import sys
from threading import Event, Timer
import time

import pytest

from attune_harness.process import invoke
from attune_harness.review_store import RunStore,PersistenceError

pytestmark=pytest.mark.skipif(os.name!='nt',reason='Requires a native Windows runner')


def command(code):return (sys.executable,'-c',code)


def explicit_environment():
    return {'SystemRoot': os.environ['SystemRoot'], 'ATTUNE_EXPLICIT': 'café',
            'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1'}


def test_windows_explicit_environment_reaches_target_exactly(tmp_path, monkeypatch):
    monkeypatch.setenv('ATTUNE_AMBIENT_CANARY', 'must-not-leak')
    environment = explicit_environment()
    keys = sorted(k.upper() for k in environment)
    code = ('import json,os;print(json.dumps({"keys":sorted(os.environ),'
            f'"values":{{k:os.environ.get(k) for k in {keys!r}}}}}))')
    result = invoke(command(code), '',
                    cwd=tmp_path, environment=environment)
    assert result.failure is None, result
    assert json.loads(result.stdout) == {'keys': keys,
                                       'values': {k.upper(): v for k, v in environment.items()}}
    assert environment == explicit_environment()


def test_windows_default_environment_still_inherits(tmp_path, monkeypatch):
    monkeypatch.setenv('ATTUNE_DEFAULT_CANARY', 'inherited')
    result = invoke(command('import os;print(os.environ["ATTUNE_DEFAULT_CANARY"])'), '',
                    cwd=tmp_path)
    assert result.failure is None and result.stdout.strip() == 'inherited'


def test_windows_ambiguous_environment_is_rejected_before_job(tmp_path, monkeypatch):
    from attune_harness.windows import WindowsJob
    monkeypatch.setattr(WindowsJob, '__enter__', lambda self: pytest.fail('job created'))
    with pytest.raises(ValueError, match='distinct ignoring case'):
        invoke(command('raise SystemExit(99)'), '', cwd=tmp_path,
               environment={'Path': 'first', 'PATH': 'second'})


def test_windows_explicit_environment_keeps_descendant_cleanup(tmp_path):
    marker = tmp_path / 'escaped'
    child = f'import time,pathlib;time.sleep(6);pathlib.Path({str(marker)!r}).write_text("bad")'
    parent = ('import subprocess,sys,time;'
              f'subprocess.Popen([sys.executable,"-c",{child!r}]);'
              'print("spawned",flush=True);time.sleep(20)')
    result = invoke(command(parent), '', cwd=tmp_path, timeout=5,
                    environment=explicit_environment())
    assert result.failure == 'timeout_effects_unknown' and 'spawned' in result.stdout
    time.sleep(6.2)
    assert not marker.exists()


def test_windows_success_failure_unicode_and_spaced_cwd(tmp_path):
    work=tmp_path/'space café';work.mkdir()
    r=invoke(command('import sys;sys.stdout.buffer.write(sys.stdin.buffer.read());print("detail",file=sys.stderr)'),
             'café $(not-a-shell)',cwd=work)
    assert r.failure is None and r.stdout=='café $(not-a-shell)' and r.stderr.strip()=='detail'
    assert invoke(command('raise SystemExit(3)'),'',cwd=work).returncode==3
    assert invoke((str(work/'absent.exe'),),'',cwd=work).failure=='not_found'


def test_windows_timeout_and_cancel_are_effects_unknown(tmp_path):
    r=invoke(command('import time;print("partial",flush=True);time.sleep(20)'),'',cwd=tmp_path,timeout=5)
    assert r.failure=='timeout_effects_unknown' and 'partial' in r.stdout
    cancel=Event();timer=Timer(2,cancel.set);timer.start()
    try:r=invoke(command('import time;time.sleep(20)'),'',cwd=tmp_path,cancel=cancel)
    finally:timer.cancel();timer.join()
    assert r.failure=='cancelled_effects_unknown'


def test_windows_output_limits_and_invalid_encoding(tmp_path):
    r=invoke(command('import sys;sys.stdout.buffer.write(b"x"*100000)'),'',cwd=tmp_path,max_output_bytes=100)
    assert r.failure=='output_limit' and len(r.stdout.encode())+len(r.stderr.encode())==100
    assert invoke(command('import sys;sys.stdout.buffer.write(bytes([255]))'),'',cwd=tmp_path).failure=='invalid_utf8'


@pytest.mark.parametrize('parent_wait',[False,True])
def test_windows_descendants_stop_even_after_parent_exit(tmp_path,parent_wait):
    marker=tmp_path/'late'
    child=f'import time,pathlib;time.sleep(6);pathlib.Path({str(marker)!r}).write_text("bad")'
    parent=f'import subprocess,sys,time;subprocess.Popen([sys.executable,"-c",{child!r}]);print("spawned",flush=True)'
    if parent_wait:parent+=';time.sleep(20)'
    r=invoke(command(parent),'',cwd=tmp_path,timeout=5)
    assert 'spawned' in r.stdout
    assert r.failure==('timeout_effects_unknown' if parent_wait else None)
    time.sleep(6.2);assert not marker.exists()


@pytest.mark.parametrize('explicit', [False, True])
def test_windows_failed_job_assignment_never_starts_requested_code(tmp_path, explicit):
    from attune_harness.windows import WindowsJob
    marker=tmp_path/'effect'
    with WindowsJob() as job:
        job.api.AssignProcessToJobObject=lambda *_args:0
        with pytest.raises(OSError):
            job.launch(command(f'from pathlib import Path;Path({str(marker)!r}).write_text("bad")'),
                stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,cwd=tmp_path,
                environment=explicit_environment() if explicit else None)
    assert not marker.exists()


def test_windows_writer_lock_blocks_concurrent_owner_and_releases_after_death(tmp_path):
    directory=tmp_path/'run';RunStore(directory)
    code=('from pathlib import Path;import time;from attune_harness.review_store import RunStore;'
          f'store=RunStore(Path({str(directory)!r}),existing=True);'
          'lease=store.lease();lease.__enter__();print("locked",flush=True);time.sleep(30)')
    process=subprocess.Popen([sys.executable,'-I','-c',code],stdout=subprocess.PIPE,text=True)
    try:
        assert process.stdout.readline().strip()=='locked'
        with pytest.raises(PersistenceError):
            with RunStore(directory,existing=True).lease():pass
    finally:process.kill();process.wait(timeout=5)
    with RunStore(directory,existing=True).lease():pass


def test_windows_owner_death_closes_job_and_stops_effects(tmp_path):
    marker=tmp_path/'late';ready=tmp_path/'ready'
    child=f'import time,pathlib;pathlib.Path({str(ready)!r}).write_text("ready");time.sleep(3);pathlib.Path({str(marker)!r}).write_text("bad")'
    code=('from pathlib import Path;import sys;from attune_harness.process import invoke;'
          f'invoke((sys.executable,"-c",{child!r}),"",cwd=Path({str(tmp_path)!r}),timeout=20)')
    supervisor=subprocess.Popen([sys.executable,'-I','-c',code])
    try:
        deadline=time.monotonic()+10
        while not ready.exists() and time.monotonic()<deadline:time.sleep(0.02)
        assert ready.exists()
    finally:supervisor.kill();supervisor.wait(timeout=5)
    time.sleep(3.2);assert not marker.exists()


def test_windows_lock_reparse_point_is_rejected(tmp_path):
    store=RunStore(tmp_path/'run');target=tmp_path/'target';target.write_text('x',encoding='utf-8')
    try:(store.directory/'.writer.lock').symlink_to(target)
    except OSError as exc:pytest.skip('Runner cannot create symlinks: '+str(exc))
    with pytest.raises(OSError):
        with store.lease():pass
    assert target.read_text(encoding='utf-8')=='x'


@pytest.mark.parametrize('ending', ['parent_exit', 'timeout', 'cancel'])
def test_windows_return_drains_owned_cwd_before_immediate_removal(
        tmp_path, monkeypatch, record_property, ending):
    """Retain real process handles; no test-side rundown wait can make it pass."""
    import ctypes
    from ctypes import wintypes as w
    from threading import Thread
    from attune_harness.windows import WindowsJob

    work = tmp_path / 'owned cwd café'
    work.mkdir()
    ready = tmp_path / 'child-ready.json'
    parent_ready = tmp_path / 'parent-ready'
    release = tmp_path / 'release-parent'
    child = ('import json,os,pathlib,time;'
             f'assert pathlib.Path.cwd().samefile({str(work)!r});'
             f'pathlib.Path({str(ready)!r}).write_text(json.dumps({{"pid":os.getpid()}}));'
             'time.sleep(20)')
    parent = ('import pathlib,subprocess,sys,time;'
              f'subprocess.Popen([sys.executable,"-c",{child!r}]);'
              f'ready=pathlib.Path({str(ready)!r});'
              '\nwhile not ready.exists(): time.sleep(0.01)\n'
              'print("spawned",flush=True);'
              f'pathlib.Path({str(parent_ready)!r}).write_text("ready");'
              f'release=pathlib.Path({str(release)!r});'
              '\nwhile not release.exists(): time.sleep(0.01)\n')
    if ending != 'parent_exit':
        parent += 'time.sleep(20)\n'
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    signatures = {
        'OpenProcess': ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
        'WaitForSingleObject': ([w.HANDLE, w.DWORD], w.DWORD),
        'IsProcessInJob': ([w.HANDLE, w.HANDLE, ctypes.POINTER(w.BOOL)], w.BOOL),
        'TerminateProcess': ([w.HANDLE, w.UINT], w.BOOL),
        'CloseHandle': ([w.HANDLE], w.BOOL),
    }
    for name, (args, result) in signatures.items():
        function = getattr(api, name)
        function.argtypes, function.restype = args, result
    jobs, handles, observations, errors = [], [], [], []
    original_launch = WindowsJob.launch
    cancel = Event()
    controller_state = {'stage': 'startup'}

    def launch(self, *args, **kwargs):
        process = original_launch(self, *args, **kwargs)
        # Keep the bootstrap Popen handle alive through all stop observations.
        jobs.append((self, process))
        return process

    monkeypatch.setattr(WindowsJob, 'launch', launch)

    def control():
        try:
            deadline = time.monotonic() + 4.5
            while not (parent_ready.exists() and jobs) and time.monotonic() < deadline:
                time.sleep(0.01)
            assert parent_ready.exists() and jobs, 'owned child startup was not witnessed'
            controller_state['stage'] = 'open_child'
            pid = json.loads(ready.read_text())['pid']
            assert type(pid) is int and pid > 0
            handle = api.OpenProcess(0x00101001, False, pid)  # SYNCHRONIZE | QUERY_LIMITED_INFORMATION | TERMINATE.
            if not handle:
                raise ctypes.WinError(ctypes.get_last_error())
            handles.append(handle)
            controller_state['stage'] = 'membership'
            member = w.BOOL()
            if not api.IsProcessInJob(handle, jobs[0][0].handle, ctypes.byref(member)):
                raise ctypes.WinError(ctypes.get_last_error())
            assert member.value
            live_child_wait = api.WaitForSingleObject(handle, 0)
            assert live_child_wait == 258
            controller_state['stage'] = 'live_cwd_lock'
            assert not list(work.iterdir())
            try:
                work.rmdir()
            except OSError as error:
                assert error.winerror in (5, 32), error
                observations.append({'owned_pid': pid, 'live_cwd_winerror': error.winerror,
                                     'job_member': bool(member.value), 'live_child_wait': live_child_wait})
            else:
                raise AssertionError('live owned cwd did not prevent removal')
            controller_state['stage'] = 'release'
            if ending == 'cancel':
                cancel.set()
            elif ending == 'parent_exit':
                release.write_text('release')
            controller_state['stage'] = 'ready'
        except BaseException as error:
            controller_state['error_stage'] = controller_state['stage']
            controller_state['error_type'] = type(error).__name__
            code = getattr(error, 'winerror', None)
            controller_state['winerror'] = code if type(code) is int else None
            errors.append(error)
            cancel.set()
            release.write_text('release')

    controller = Thread(target=control)
    controller.start()
    try:
        result = invoke(command(parent), '', cwd=work, timeout=5, cancel=cancel)
        # Sample both immediate conditions before recording or joining anything.
        child_wait = api.WaitForSingleObject(handles[0], 0)
        cwd_error = None
        try:
            work.rmdir()
        except OSError as error:
            cwd_error = error
        record_property('owned_cwd_return_observation', json.dumps({
            'ending': ending, 'returncode': result.returncode, 'failure': result.failure,
            'stdout_bytes': len(result.stdout.encode('utf-8')),
            'stderr_bytes': len(result.stderr.encode('utf-8')),
            'child_wait': child_wait,
            'cwd_error_type': type(cwd_error).__name__ if cwd_error is not None else None,
            'cwd_winerror': getattr(cwd_error, 'winerror', None),
            'live_control': list(observations), 'controller': dict(controller_state),
            'bootstrap_references': len(jobs), 'child_references': len(handles)}))
        assert child_wait == 0
        if cwd_error is not None:
            raise cwd_error
        controller.join(timeout=5)
        assert not controller.is_alive() and not errors, errors
        assert observations and 'spawned' in result.stdout
        expected = {'parent_exit': None, 'timeout': 'timeout_effects_unknown',
                    'cancel': 'cancelled_effects_unknown'}[ending]
        assert result.failure == expected and result.returncode is not None
        record_property('owned_cwd_stop_observation', json.dumps({
            **observations[0], 'ending': ending, 'failure': result.failure,
            'immediate_child_signaled': True, 'immediate_cwd_removed': True,
            'bootstrap_handle_retained': True, 'child_handle_retained': True}))
    finally:
        cancel.set()
        release.write_text('release')
        controller.join(timeout=5)
        for handle in handles:
            try:
                # Failure-only owned-handle cleanup cannot satisfy assertions above.
                if api.WaitForSingleObject(handle, 0) != 0:
                    if not api.TerminateProcess(handle, 1):
                        raise ctypes.WinError(ctypes.get_last_error())
                    assert api.WaitForSingleObject(handle, 5000) == 0
            finally:
                if not api.CloseHandle(handle):
                    raise ctypes.WinError(ctypes.get_last_error())
