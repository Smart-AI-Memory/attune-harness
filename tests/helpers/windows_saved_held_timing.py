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
        if not _held_active():
            return original(*args, **kwargs)
        begin, succeeded = _held_stamp(), False
        try:
            result = original(*args, **kwargs)
            succeeded = True
            return result
        finally:
            _held_record(operation, begin, _held_stamp(), succeeded)
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
            report['observer_failed'] = report.get('observer_failed', False) or _held_failed
        except BaseException:
            try:
                globals()['trace']['observer_failed'] = True
            except BaseException:
                pass


_HeldStore.save = _held_save
