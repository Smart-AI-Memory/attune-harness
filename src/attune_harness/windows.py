"""Windows process-tree ownership and non-following lock-file opens, loaded lazily."""
import ctypes
from ctypes import wintypes as w
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def kernel():
    if os.name != 'nt':
        raise NotImplementedError('Windows native primitives require Windows')
    dll=ctypes.WinDLL('kernel32',use_last_error=True)
    signatures={
        'CreateJobObjectW':([w.LPVOID,w.LPCWSTR],w.HANDLE),
        'SetInformationJobObject':([w.HANDLE,ctypes.c_int,w.LPVOID,w.DWORD],w.BOOL),
        'OpenProcess':([w.DWORD,w.BOOL,w.DWORD],w.HANDLE),
        'AssignProcessToJobObject':([w.HANDLE,w.HANDLE],w.BOOL),
        'TerminateJobObject':([w.HANDLE,w.UINT],w.BOOL),
        'CloseHandle':([w.HANDLE],w.BOOL),
        'CreateFileW':([w.LPCWSTR,w.DWORD,w.DWORD,w.LPVOID,w.DWORD,w.DWORD,w.HANDLE],w.HANDLE),
        'GetFileInformationByHandleEx':([w.HANDLE,ctypes.c_int,w.LPVOID,w.DWORD],w.BOOL),
    }
    for name,(args,result) in signatures.items():
        function=getattr(dll,name);function.argtypes=args;function.restype=result
    return dll


def checked(value):
    if not value:
        raise ctypes.WinError(ctypes.get_last_error())
    return value


class BasicLimits(ctypes.Structure):
    _fields_=[('process_time',ctypes.c_int64),('job_time',ctypes.c_int64),('flags',w.DWORD),
              ('minimum_working_set',ctypes.c_size_t),('maximum_working_set',ctypes.c_size_t),
              ('active_process_limit',w.DWORD),('affinity',ctypes.c_size_t),
              ('priority',w.DWORD),('scheduling',w.DWORD)]


class ExtendedLimits(ctypes.Structure):
    _fields_=[('basic',BasicLimits),('io_counters',ctypes.c_uint64*6),
              ('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),
              ('peak_process_memory',ctypes.c_size_t),('peak_job_memory',ctypes.c_size_t)]


class WindowsJob:
    def __init__(self):
        self.api=kernel();self.handle=None;self.temporary=None

    def __enter__(self):
        self.handle=checked(self.api.CreateJobObjectW(None,None))
        try:
            limits=ExtendedLimits();limits.basic.flags=0x2000  # KILL_ON_JOB_CLOSE, no breakaway.
            checked(self.api.SetInformationJobObject(self.handle,9,ctypes.byref(limits),ctypes.sizeof(limits)))
            self.temporary=tempfile.TemporaryDirectory(prefix='harness-windows-job-')
            self.directory=Path(self.temporary.name)
            return self
        except BaseException:
            self.__exit__(None,None,None);raise

    def __exit__(self,*_args):
        try:
            if self.handle is not None:
                handle,self.handle=self.handle,None
                checked(self.api.CloseHandle(handle))
        finally:
            if self.temporary is not None:self.temporary.cleanup()

    def launch(self,argv,*,stdin,stdout,stderr,cwd):
        bootstrap=Path(__file__).with_name('_windows_worker.py')
        process=subprocess.Popen([sys.executable,'-I',str(bootstrap),str(self.directory),*argv],
            stdin=stdin,stdout=stdout,stderr=stderr,cwd=cwd,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        handle=None
        try:
            handle=checked(self.api.OpenProcess(0x0101,False,process.pid))  # SET_QUOTA | TERMINATE
            checked(self.api.AssignProcessToJobObject(self.handle,handle))
            # This is the only path that permits the bootstrap to launch user code.
            (self.directory/'start').write_bytes(b'start')
            return process
        except BaseException:
            process.kill();process.wait(timeout=5);raise
        finally:
            if handle is not None:checked(self.api.CloseHandle(handle))

    def stop(self,process):
        checked(self.api.TerminateJobObject(self.handle,1))
        process.wait(timeout=5)

    def launch_failure(self):
        path=self.directory/'launch-error.json'
        if not path.exists():return None
        value=json.loads(path.read_text(encoding='utf-8'))
        return 'not_found' if value['not_found'] else 'launch_failed'


def open_lock(path):
    """Open the file itself and reject reparse points; returned fd owns the handle."""
    import msvcrt
    api=kernel()
    handle=api.CreateFileW(str(path),0xC0000000,3,None,4,0x00200000,None)
    if handle==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
    try:
        attributes=(w.DWORD*2)()
        checked(api.GetFileInformationByHandleEx(handle,9,ctypes.byref(attributes),ctypes.sizeof(attributes)))
        if attributes[0] & (0x400|0x10):raise OSError('Writer lock cannot be a reparse point or directory')
        return msvcrt.open_osfhandle(handle,os.O_RDWR|os.O_BINARY)
    except BaseException:
        checked(api.CloseHandle(handle));raise
