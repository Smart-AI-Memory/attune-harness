"""Read-only OS observations for the owned offline-test descendant."""

import ctypes
import errno
import os
from pathlib import Path
import select
import sys
import time


def _windows():
    from ctypes import wintypes as w
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    signatures = {
        'GetCurrentProcess': ([], w.HANDLE),
        'OpenProcess': ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
        'DuplicateHandle': ([w.HANDLE, w.HANDLE, w.HANDLE, ctypes.POINTER(w.HANDLE),
                             w.DWORD, w.BOOL, w.DWORD], w.BOOL),
        'WaitForSingleObject': ([w.HANDLE, w.DWORD], w.DWORD),
        'GetExitCodeProcess': ([w.HANDLE, ctypes.POINTER(w.DWORD)], w.BOOL),
        'GetProcessId': ([w.HANDLE], w.DWORD),
        'CloseHandle': ([w.HANDLE], w.BOOL),
    }
    for name, (args, result) in signatures.items():
        getattr(api, name).argtypes = args
        getattr(api, name).restype = result
    return api


def _posix_identity(pid):
    if sys.platform == 'darwin':
        # Public proc_bsdinfo from the macOS SDK's sys/proc_info.h. A birth
        # timestamp prevents a reused PID from being mistaken for this child.
        class BSDInfo(ctypes.Structure):
            _fields_ = [('head', ctypes.c_uint32 * 12), ('comm', ctypes.c_char * 16),
                        ('name', ctypes.c_char * 32), ('tail', ctypes.c_uint32 * 5),
                        ('nice', ctypes.c_int32), ('seconds', ctypes.c_uint64),
                        ('microseconds', ctypes.c_uint64)]
        api = ctypes.CDLL('/usr/lib/libproc.dylib', use_errno=True)
        api.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64,
                                    ctypes.c_void_p, ctypes.c_int]
        api.proc_pidinfo.restype = ctypes.c_int
        info = BSDInfo()
        ctypes.set_errno(0)
        length = api.proc_pidinfo(pid, 3, 0, ctypes.byref(info), ctypes.sizeof(info))
        if length != ctypes.sizeof(info):
            code = ctypes.get_errno() or errno.EIO
            raise OSError(code, os.strerror(code))
        assert info.head[3] == pid and info.seconds > 0
        return [info.seconds, info.microseconds], info.head[1] == 5  # SZOMB
    if sys.platform.startswith('linux'):
        text = Path(f'/proc/{pid}/stat').read_text(encoding='ascii')
        assert int(text.split('(', 1)[0]) == pid
        fields = text.rsplit(')', 1)[1].split()
        return fields[19], fields[0] == 'Z'  # Kernel starttime and state.
    raise AssertionError('No OS process identity witness for this platform')


def process_reference(process, observer_pid):
    """Capture while alive; Windows transfers the exact Popen process object."""
    assert process.poll() is None
    if os.name != 'nt':
        birth, dead = _posix_identity(process.pid)
        assert not dead
        return dict(kind=sys.platform, pid=process.pid, birth=birth)
    from ctypes import wintypes as w
    api = _windows()
    target = api.OpenProcess(0x0040, False, observer_pid)  # PROCESS_DUP_HANDLE only.
    if not target:
        raise ctypes.WinError(ctypes.get_last_error())
    handle = w.HANDLE()
    try:
        # A non-inheritable, read/synchronize-only handle; never TERMINATE.
        if not api.DuplicateHandle(api.GetCurrentProcess(), int(process._handle), target,
                                   ctypes.byref(handle), 0x101000, False, 0):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        assert api.CloseHandle(target)
    return dict(kind='windows-handle', pid=process.pid, handle=handle.value)


def wait_for_exit(reference, timeout):
    """Observe termination without sending any signal or terminating a PID."""
    if reference['kind'] == 'windows-handle':
        from ctypes import wintypes as w
        api = _windows()
        handle = reference['handle']
        assert api.GetProcessId(handle) == reference['pid']
        state = api.WaitForSingleObject(handle, int(timeout * 1000))
        assert state in (0, 258), 'Process-handle wait failed'
        code = w.DWORD()
        assert api.GetExitCodeProcess(handle, ctypes.byref(code))
        return dict(method='retained-process-handle', terminated=state == 0,
                    exit_code=code.value, pid=reference['pid'])
    pid = reference['pid']
    deadline = time.monotonic() + timeout
    while True:
        try:
            birth, dead = _posix_identity(pid)
        except OSError as error:
            if error.errno not in (errno.ESRCH, errno.ENOENT):
                raise
            return dict(method='os-process-identity', terminated=True, state='absent', pid=pid)
        if birth != reference['birth'] or dead:
            return dict(method='os-process-identity', terminated=True,
                        state='reused-pid' if birth != reference['birth'] else 'zombie', pid=pid)
        remaining = max(0, deadline - time.monotonic())
        if sys.platform.startswith('linux'):
            # Bind a handle when the original is still present. Recheck its
            # birth after opening so a reuse race cannot qualify another PID.
            try:
                fd = os.pidfd_open(pid)
            except ProcessLookupError:
                continue
            try:
                try:
                    after, _ = _posix_identity(pid)
                except OSError as error:
                    if error.errno not in (errno.ESRCH, errno.ENOENT):
                        raise
                    continue
                if after != reference['birth']:
                    continue
                ready = bool(select.select([fd], [], [], remaining)[0])
                return dict(method='pidfd', terminated=ready, pid=pid)
            finally:
                os.close(fd)
        if remaining == 0:
            return dict(method='os-process-identity', terminated=False, state='alive', pid=pid)
        time.sleep(min(0.01, remaining))


def close_reference(reference):
    if reference['kind'] == 'windows-handle':
        assert _windows().CloseHandle(reference['handle'])


def descendant_code(marker, gate, started):
    return ('import time,pathlib\n'
            f'pathlib.Path({str(started)!r}).write_bytes(b"started")\n'
            f'while not pathlib.Path({str(gate)!r}).exists(): time.sleep(0.01)\n'
            'time.sleep(0.2)\n'
            f'pathlib.Path({str(marker)!r}).write_bytes(b"escaped")')
