"""Ordinary-run diagnostic prefix; no storage operation or retry is added."""
import time as _held_clock

from attune_harness import memory_saved_windows as _held_backend
from attune_harness.memory_saved import SavedStore as _HeldStore

_held_rows = []
_held_limit = 32
_held_dropped = 0
_held_failed = False
_held_clock_failures = 0
_held_acquired = None
try:
    _held_info = _held_clock.get_clock_info('perf_counter')
    _held_clock_info = dict(implementation=_held_info.implementation,
                            resolution=_held_info.resolution,
                            monotonic=_held_info.monotonic, adjustable=_held_info.adjustable)
except BaseException:
    _held_failed = True
    _held_clock_info = None


# Resource observations are advisory and remain in memory until confirmed release.
import ctypes as _held_ctypes
import os as _held_os
import sys as _held_sys

_held_resource_rows = []
_held_resource_limit = 4
_held_resource_dropped = 0
_held_resource_captured = 0
_held_resource_errors = []
_held_resource_api = None
_held_resource_columns = ['sample_begin_ns', 'sample_end_ns', 'thread_cpu_ns',
    'process_cpu_ns', 'read_ops', 'write_ops', 'other_ops', 'read_bytes',
    'write_bytes', 'other_bytes', 'system_idle_100ns', 'system_kernel_100ns',
    'system_user_100ns']
_held_resource_info = dict(schema_version=1, windows_api=False,
    system_cpu_scope='primary processor group above 64 processors; kernel includes idle',
    interpretation='process I/O accounting and CPU clocks; not disk service or scheduling events')


def _held_resource_error(stage):
    try:
        if not isinstance(stage, str) or len(stage) > 32:
            stage = 'unknown'
        if stage not in _held_resource_errors and len(_held_resource_errors) < 8:
            _held_resource_errors.append(stage)
    except BaseException:
        pass


try:
    _held_resource_info.update(pid=_held_os.getpid(), logical_processors=_held_os.cpu_count(),
        image_os=_held_os.environ.get('ImageOS', '')[:80],
        image_version=_held_os.environ.get('ImageVersion', '')[:80])
    for _held_name in ('thread_time', 'process_time'):
        _held_info = _held_clock.get_clock_info(_held_name)
        _held_resource_info[_held_name] = dict(implementation=_held_info.implementation[:160],
            resolution=_held_info.resolution, monotonic=_held_info.monotonic)
    if _held_os.name == 'nt':
        from ctypes import wintypes as _held_w
        _held_resource_info['windows_build'] = list(_held_sys.getwindowsversion()[:3])

        class _HeldIoCounters(_held_ctypes.Structure):
            _fields_ = [(name, _held_ctypes.c_ulonglong) for name in
                ('read_ops', 'write_ops', 'other_ops', 'read_bytes', 'write_bytes', 'other_bytes')]

        _held_k = _held_ctypes.WinDLL('kernel32', use_last_error=True)
        _held_k.GetCurrentProcess.argtypes, _held_k.GetCurrentProcess.restype = [], _held_w.HANDLE
        _held_k.GetProcessIoCounters.argtypes = [_held_w.HANDLE, _held_ctypes.POINTER(_HeldIoCounters)]
        _held_k.GetProcessIoCounters.restype = _held_w.BOOL
        _held_k.GetSystemTimes.argtypes = [_held_ctypes.POINTER(_held_w.FILETIME)] * 3
        _held_k.GetSystemTimes.restype = _held_w.BOOL
        _held_k.GetVolumePathNameW.argtypes = [_held_w.LPCWSTR, _held_w.LPWSTR, _held_w.DWORD]
        _held_k.GetVolumePathNameW.restype = _held_w.BOOL
        _held_k.GetVolumeNameForVolumeMountPointW.argtypes = [_held_w.LPCWSTR, _held_w.LPWSTR, _held_w.DWORD]
        _held_k.GetVolumeNameForVolumeMountPointW.restype = _held_w.BOOL
        _held_k.GetVolumeInformationW.argtypes = [_held_w.LPCWSTR, _held_w.LPWSTR, _held_w.DWORD,
            _held_ctypes.POINTER(_held_w.DWORD), _held_ctypes.POINTER(_held_w.DWORD),
            _held_ctypes.POINTER(_held_w.DWORD), _held_w.LPWSTR, _held_w.DWORD]
        _held_k.GetVolumeInformationW.restype = _held_w.BOOL
        _held_resource_api = _held_k
        _held_resource_info['windows_api'] = True
except BaseException:
    _held_resource_error('initialization')


def _held_resource_sample():
    """Bounded counters, not a disk service or thread scheduling trace."""
    saved = None
    try:
        if _held_os.name == 'nt':
            saved = _held_ctypes.get_last_error()
        begin = _held_clock.perf_counter_ns()
        thread, process = _held_clock.thread_time_ns(), _held_clock.process_time_ns()
        io, system = [None] * 6, [None] * 3
        if _held_resource_api is not None:
            counters = _HeldIoCounters()
            if _held_resource_api.GetProcessIoCounters(
                    _held_resource_api.GetCurrentProcess(), _held_ctypes.byref(counters)):
                io = [getattr(counters, name) for name, _ in counters._fields_]
            else:
                _held_resource_error('process_io')
            idle, kernel, user = _held_w.FILETIME(), _held_w.FILETIME(), _held_w.FILETIME()
            if _held_resource_api.GetSystemTimes(_held_ctypes.byref(idle),
                    _held_ctypes.byref(kernel), _held_ctypes.byref(user)):
                system = [(value.dwHighDateTime << 32) | value.dwLowDateTime
                          for value in (idle, kernel, user)]
            else:
                _held_resource_error('system_cpu')
        end = _held_clock.perf_counter_ns()
        values = [begin, end, thread, process, *io, *system]
        if end < begin or any(value is not None and (type(value) is not int or not 0 <= value <= 2**64 - 1)
                              for value in values):
            raise ValueError('Invalid resource counter')
        return values
    except BaseException:
        _held_resource_error('sample')
        return None
    finally:
        if saved is not None:
            try:
                _held_ctypes.set_last_error(saved)
            except BaseException:
                _held_resource_error('last_error_restore')


def _held_resource_safe_sample():
    # Protect the slot even when a replaced observer mutates it and raises.
    saved = None
    try:
        if _held_os.name == 'nt':
            saved = _held_ctypes.get_last_error()
        return _held_resource_sample()
    except BaseException:
        _held_resource_error('sample')
        return None
    finally:
        if saved is not None:
            try:
                _held_ctypes.set_last_error(saved)
            except BaseException:
                _held_resource_error('last_error_restore')


def _held_resource_record(begin, end, before, after):
    try:
        _held_resource_rows.append([begin, end, before, after])
    except BaseException:
        _held_resource_error('record')


def _held_resource_volume(root):
    """Read actual store-volume identity only after confirmed lock release."""
    if _held_resource_api is None:
        return dict(status='unavailable', device_cache_filter='unknown')
    saved = _held_ctypes.get_last_error()
    try:
        path = _held_ctypes.create_unicode_buffer(1024)
        guid = _held_ctypes.create_unicode_buffer(128)
        fs = _held_ctypes.create_unicode_buffer(32)
        serial, component, flags = _held_w.DWORD(), _held_w.DWORD(), _held_w.DWORD()
        if not _held_resource_api.GetVolumePathNameW(str(root), path, len(path)):
            raise OSError('Volume path unavailable')
        if not _held_resource_api.GetVolumeInformationW(path.value, None, 0,
                _held_ctypes.byref(serial), _held_ctypes.byref(component),
                _held_ctypes.byref(flags), fs, len(fs)):
            raise OSError('Volume information unavailable')
        guid_ok = bool(_held_resource_api.GetVolumeNameForVolumeMountPointW(path.value, guid, len(guid)))
        return dict(status='observed_after_release', mount=path.value, serial=serial.value,
            filesystem=fs.value, guid=guid.value if guid_ok else None,
            binding='post_release_path_only; retained_handle_binding_not_verified',
            device_cache_filter='unknown')
    except BaseException:
        _held_resource_error('volume_identity')
        return dict(status='unavailable', device_cache_filter='unknown')
    finally:
        _held_ctypes.set_last_error(saved)


def _held_stamp():
    global _held_failed, _held_clock_failures
    try:
        value = _held_clock.perf_counter_ns()
        if type(value) is not int or value < 0:
            raise ValueError('Invalid performance-clock sample')
        return value
    except BaseException:
        _held_failed = True
        _held_clock_failures += 1
        return None


def _held_active():
    global _held_failed
    try:
        return globals().get('trace', {}).get('held', False) is True
    except BaseException:
        _held_failed = True
        return False


def _held_record(operation, begin, end, succeeded):
    global _held_dropped, _held_failed
    try:
        if len(_held_rows) >= _held_limit:
            _held_dropped += 1
        else:
            _held_rows.append([operation, begin, end, succeeded])
    except BaseException:
        _held_failed = True


def _held_wrap(operation, original):
    def observed(*args, **kwargs):
        global _held_resource_dropped, _held_resource_captured
        if not _held_active():
            return original(*args, **kwargs)
        capture = operation == 'flush' and _held_resource_captured < _held_resource_limit
        if capture:
            _held_resource_captured += 1
        if operation == 'flush' and not capture:
            _held_resource_dropped += 1
        before = _held_resource_safe_sample() if capture else None
        begin, succeeded = _held_stamp(), False
        try:
            result = original(*args, **kwargs)
            succeeded = True
            return result
        finally:
            end = _held_stamp()
            if capture:
                after = _held_resource_safe_sample()
                _held_resource_record(begin, end, before, after)
            _held_record(operation, begin, end, succeeded)
    return observed


for _held_owner, _held_method, _held_label in (
    (_held_backend._Native, 'child', 'child'),
    (_held_backend._Session, '_inspect', 'inspect'),
    (_held_backend._Native, 'write_all', 'write'),
    (_held_backend.Native, 'read', 'read'),
    (_held_backend.Native, 'rename', 'rename'),
    (_held_backend._Native, 'flush', 'flush'),
    (_held_backend._Session, 'commit_payload', 'commit'),
    (_held_backend._Native, 'unlock', 'unlock'),
):
    setattr(_held_owner, _held_method,
            _held_wrap(_held_label, getattr(_held_owner, _held_method)))

_held_original_lock = _held_backend._Native.lock_once


def _held_lock(*args, **kwargs):
    global _held_acquired
    result = _held_original_lock(*args, **kwargs)
    # Do not sample a failed poll: the existing observer captures last-error
    # immediately after this return. Successful acquisition needs no error code.
    if result:
        _held_acquired = _held_stamp()
    return result


_held_backend._Native.lock_once = _held_lock
_held_original_save = _HeldStore.save


def _held_save(*args, **kwargs):
    global _held_failed
    try:
        return _held_original_save(*args, **kwargs)
    finally:
        # The existing script alone serializes/emits, after confirmed release.
        # Unknown ownership retains that script's refusal to emit a report.
        try:
            report = globals()['trace']
            if _held_active():
                _held_failed = True
            report['held_timing'] = dict(
                clock=_held_clock_info, acquired_ns=_held_acquired,
                columns=['operation', 'begin_ns', 'end_ns', 'succeeded'],
                operations=list(_held_rows), limit=_held_limit,
                dropped=_held_dropped, clock_failures=_held_clock_failures,
                observer_failed=_held_failed)
            volume = (dict(status='release_unconfirmed', device_cache_filter='unknown')
                      if _held_active() else _held_resource_volume(getattr(args[0], 'root', None)))
            report['held_resources'] = dict(info=_held_resource_info, volume=volume,
                sample_columns=_held_resource_columns,
                span_columns=['operation_begin_ns', 'operation_end_ns', 'before', 'after'],
                flushes=list(_held_resource_rows), limit=_held_resource_limit,
                captured=_held_resource_captured, dropped=_held_resource_dropped,
                errors=list(_held_resource_errors),
                observer_failed=bool(_held_resource_errors))
            report['observer_failed'] = (report.get('observer_failed', False) or _held_failed
                                         or bool(_held_resource_errors))
        except BaseException:
            try:
                globals()['trace']['observer_failed'] = True
            except BaseException:
                pass


_HeldStore.save = _held_save
