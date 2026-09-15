"""Real Windows Job Object and file-lock probes; never simulated as a native pass."""
import os
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


def test_windows_failed_job_assignment_never_starts_requested_code(tmp_path):
    from attune_harness.windows import WindowsJob
    marker=tmp_path/'effect'
    with WindowsJob() as job:
        job.api.AssignProcessToJobObject=lambda *_args:0
        with pytest.raises(OSError):
            job.launch(command(f'from pathlib import Path;Path({str(marker)!r}).write_text("bad")'),
                stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,cwd=tmp_path)
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
