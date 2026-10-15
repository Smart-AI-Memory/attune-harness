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


@pytest.fixture(scope='module')
def windows_process_architecture():
    """Read interpreter ISA independently of mutable architecture environment."""
    import ctypes
    from ctypes import wintypes

    # https://learn.microsoft.com/windows/win32/debug/pe-format#machine-types
    with Path(sys.executable).open('rb') as stream:
        dos = stream.read(64)
        assert len(dos) == 64 and dos[:2] == b'MZ', 'Interpreter lacks a DOS header'
        stream.seek(int.from_bytes(dos[60:64], 'little'))
        coff = stream.read(6)
    assert len(coff) == 6 and coff[:4] == b'PE\0\0', 'Interpreter lacks a PE header'
    interpreter_machine = int.from_bytes(coff[4:6], 'little')
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.GetCurrentProcess.argtypes = []
    api.GetCurrentProcess.restype = wintypes.HANDLE
    api.IsWow64Process2.argtypes = [wintypes.HANDLE,
                                  ctypes.POINTER(ctypes.c_ushort),
                                  ctypes.POINTER(ctypes.c_ushort)]
    api.IsWow64Process2.restype = wintypes.BOOL
    process_machine, native_machine = ctypes.c_ushort(), ctypes.c_ushort()
    if not api.IsWow64Process2(api.GetCurrentProcess(), ctypes.byref(process_machine),
                              ctypes.byref(native_machine)):
        raise ctypes.WinError(ctypes.get_last_error())
    # Zero means not WOW64; it does not identify the interpreter's ISA.
    return interpreter_machine, process_machine.value, native_machine.value


def test_windows_explicit_environment_reaches_target_exactly(
    tmp_path, monkeypatch, windows_process_architecture,
):
    for name in ('ATTUNE_AMBIENT_CANARY', 'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN',
                 'HTTPS_PROXY', 'PATH', 'PYTHONPATH'):
        monkeypatch.setenv(name, 'must-not-inherit-' + name)
    monkeypatch.setenv('PROCESSOR_ARCHITECTURE', 'ambient-architecture-canary')
    # Native probes witnessed this exact raw architecture tuple on Windows Arm.
    # Other profiles retain the strict supplied-map expectation.
    amd64_on_arm64 = windows_process_architecture == (0x8664, 0, 0xaa64)
    cases = [explicit_environment()]
    if amd64_on_arm64:
        cases.append({**explicit_environment(),
                      'PROCESSOR_ARCHITECTURE': 'explicit-architecture-canary'})
    for environment in cases:
        before = dict(environment)
        expected = {key.upper(): value for key, value in environment.items()}
        if amd64_on_arm64:
            expected['PROCESSOR_ARCHITECTURE'] = 'AMD64'
        keys = sorted(expected)
        # Keep all keys, but never print values of unexpected inherited secrets.
        code = ('import json,os;print(json.dumps({"keys":sorted(os.environ),'
                f'"values":{{k:os.environ.get(k) for k in {keys!r}}}}}))')
        result = invoke(command(code), '', cwd=tmp_path, environment=environment)
        assert result.failure is None, result
        assert json.loads(result.stdout) == {'keys': keys, 'values': expected}, windows_process_architecture
        assert environment == before


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
    child = f'import time,pathlib;time.sleep(3);pathlib.Path({str(marker)!r}).write_text("bad")'
    parent = ('import subprocess,sys,time;'
              f'subprocess.Popen([sys.executable,"-c",{child!r}]);'
              'print("spawned",flush=True);time.sleep(20)')
    result = invoke(command(parent), '', cwd=tmp_path, timeout=2,
                    environment=explicit_environment())
    assert result.failure == 'timeout_effects_unknown' and 'spawned' in result.stdout
    time.sleep(3.2)
    assert not marker.exists()


def test_windows_success_failure_unicode_and_spaced_cwd(tmp_path):
    work=tmp_path/'space café';work.mkdir()
    r=invoke(command('import sys;sys.stdout.buffer.write(sys.stdin.buffer.read());print("detail",file=sys.stderr)'),
             'café $(not-a-shell)',cwd=work)
    assert r.failure is None and r.stdout=='café $(not-a-shell)' and r.stderr.strip()=='detail'
    assert invoke(command('raise SystemExit(3)'),'',cwd=work).returncode==3
    assert invoke((str(work/'absent.exe'),),'',cwd=work).failure=='not_found'


def test_windows_timeout_and_cancel_are_effects_unknown(tmp_path):
    r=invoke(command('import time;print("partial",flush=True);time.sleep(20)'),'',cwd=tmp_path,timeout=2)
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
    child=f'import time,pathlib;time.sleep(3);pathlib.Path({str(marker)!r}).write_text("bad")'
    parent=f'import subprocess,sys,time;subprocess.Popen([sys.executable,"-c",{child!r}]);print("spawned",flush=True)'
    if parent_wait:parent+=';time.sleep(20)'
    r=invoke(command(parent),'',cwd=tmp_path,timeout=2)
    assert 'spawned' in r.stdout
    assert r.failure==('timeout_effects_unknown' if parent_wait else None)
    time.sleep(3.2);assert not marker.exists()


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
