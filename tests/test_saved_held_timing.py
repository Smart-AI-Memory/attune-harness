"""Portable controls for the ordinary Windows diagnostic prefix.

# qualify: platform
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from attune_harness import memory_saved, memory_saved_windows

PREFIX = Path(__file__).parent / 'helpers' / 'windows_saved_held_timing.py'


@pytest.fixture
def timing(monkeypatch):
    events, failure = [], {}
    result, argument = object(), object()
    scope = {'trace': {'held': False, 'observer_failed': False}}

    def original(label):
        def called(*args, **kwargs):
            events.append((label, args, kwargs))
            if label in failure:
                raise failure[label]
            return result
        return called

    native_type = type('FakeNative', (), {})
    session_type = type('FakeSession', (), {})
    api_type = type('FakeAPI', (), {})
    methods = [(native_type, name) for name in ('child', 'write_all', 'flush', 'unlock')]
    methods += [(session_type, name) for name in ('_inspect', 'commit_payload')]
    methods += [(api_type, name) for name in ('read', 'rename')]
    for owner, name in methods:
        setattr(owner, name, original(name))
    native_type.lock_once = lambda *args, **kwargs: True
    native, session, api = native_type(), session_type(), api_type()

    def scenario(*args, **kwargs):
        assert native.lock_once(argument) is True
        scope['trace']['held'] = True
        try:
            assert native.child(argument, argument, writable=True) is result
            assert session._inspect(argument, 'file') is result
            assert native.write_all(argument, b'payload') is result
            assert api.read(argument, 7, limit=7) is result
            assert api.rename(argument, argument, 'state.json') is result
            assert native.flush(argument) is result
            assert session.commit_payload(b'payload') is result
            assert native.unlock(argument) is result
        finally:
            scope['trace']['held'] = False
        return result

    store_type = type('FakeStore', (), {'save': scenario})
    monkeypatch.setattr(memory_saved_windows, '_Native', native_type)
    monkeypatch.setattr(memory_saved_windows, '_Session', session_type)
    monkeypatch.setattr(memory_saved_windows, 'Native', api_type)
    monkeypatch.setattr(memory_saved, 'SavedStore', store_type)

    def install():
        exec(compile(PREFIX.read_text(encoding='utf-8'), str(PREFIX), 'exec'), scope)

    return SimpleNamespace(install=install, scope=scope, events=events, failure=failure,
                           result=result, argument=argument, native=native,
                           native_type=native_type, store=store_type())


def test_timing_preserves_storage_call_order_arguments_and_result_identity(timing):
    assert timing.store.save(timing.argument) is timing.result
    baseline = timing.events[:]
    timing.events.clear()
    timing.install()
    assert timing.store.save(timing.argument) is timing.result
    assert timing.events == baseline
    report = timing.scope['trace']['held_timing']
    assert [row[0] for row in report['operations']] == [
        'child', 'inspect', 'write', 'read', 'rename', 'flush', 'commit', 'unlock']
    assert all(type(row[1]) is int and row[2] >= row[1] and row[3] is True
               for row in report['operations'])
    assert report['acquired_ns'] is not None
    assert report['clock']['monotonic'] is True
    assert report['observer_failed'] is False
    assert timing.scope['trace']['held'] is False


@pytest.mark.parametrize('fault', ['none', 'clock', 'recorder', 'full-buffer'])
def test_timing_preserves_original_error_even_when_observer_fails(timing, fault):
    error = OSError('original native failure')
    timing.failure['read'] = error
    timing.install()
    if fault == 'clock':
        def broken():
            raise RuntimeError('clock failure')
        timing.scope['_held_clock'] = SimpleNamespace(perf_counter_ns=broken)
    elif fault == 'recorder':
        class BrokenRows(list):
            def append(self, value):
                raise RuntimeError('recorder failure')
        timing.scope['_held_rows'] = BrokenRows()
    elif fault == 'full-buffer':
        timing.scope['_held_rows'] = [['child', 1, 2, True]] * timing.scope['_held_limit']
    with pytest.raises(OSError) as observed:
        timing.store.save(timing.argument)
    assert observed.value is error
    assert [row[0] for row in timing.events] == ['child', '_inspect', 'write_all', 'read']
    report = timing.scope['trace']['held_timing']
    if fault in ('clock', 'recorder'):
        assert report['observer_failed'] is True
    if fault == 'clock':
        assert report['clock_failures'] > 0
    if fault == 'full-buffer':
        assert report['dropped'] == 4
    if fault == 'none':
        assert report['operations'][-1][0] == 'read'
        assert report['operations'][-1][3] is False


def test_failed_lock_poll_preserves_last_error_without_clock_access(timing):
    error_slot = []
    def busy(*args, **kwargs):
        error_slot[:] = [33]
        return False
    timing.native_type.lock_once = busy
    timing.install()
    def forbidden():
        error_slot[:] = ['overwritten by observer']
        pytest.fail('Failed lock poll must not sample a clock')
    timing.scope['_held_clock'] = SimpleNamespace(perf_counter_ns=forbidden)
    assert timing.native.lock_once(timing.argument) is False
    assert error_slot == [33]


def test_unheld_operation_does_not_sample_or_record(timing):
    timing.install()
    def forbidden():
        pytest.fail('Unheld operation must not sample a clock')
    timing.scope['_held_clock'] = SimpleNamespace(perf_counter_ns=forbidden)
    assert timing.native.child(timing.argument, timing.argument) is timing.result
    assert timing.scope['_held_rows'] == []


def test_unknown_release_preserves_error_and_held_flag(timing):
    error = OSError('release unconfirmed')
    def unknown(*args, **kwargs):
        timing.scope['trace']['held'] = True
        raise error
    type(timing.store).save = unknown
    timing.install()
    with pytest.raises(OSError) as observed:
        timing.store.save(timing.argument)
    assert observed.value is error
    assert timing.scope['trace']['held'] is True
    assert timing.scope['trace']['observer_failed'] is True


def test_complete_diagnostic_report_fits_original_bound_at_all_caps(timing):
    timing.install()
    huge = 2**63 - 1
    timing.scope['_held_rows'] = [['inspect', huge, huge, False]] * timing.scope['_held_limit']
    assert timing.store.save(timing.argument) is timing.result
    report = timing.scope['trace']
    assert report['held_timing']['dropped'] == 8
    assert len(report['held_timing']['operations']) == timing.scope['_held_limit']
    resources = report['held_resources']
    resources['flushes'] = [[2**64 - 1, 2**64 - 1, [2**64 - 1] * 13,
                             [2**64 - 1] * 13]] * resources['limit']
    resources['volume'] = dict(status='observed_after_release', mount='x' * 1023,
        serial=2**32 - 1, filesystem='x' * 31, guid='x' * 127,
        binding='post_release_path_only; retained_handle_binding_not_verified',
        device_cache_filter='unknown')
    resources['errors'] = ['x' * 32] * 8
    facts = dict(type='UnresolvedOperation', errno=0xC0000034, winerror=33,
                 code='persistence', outcome='not_committed')
    report['events'] = [dict(event='lock_exception', begin_ns=huge, end_ns=huge,
                             error=facts)] * 64
    report['flushes'] = [dict(begin_ns=huge, end_ns=huge, held=True,
                              is_lock=False, error=facts)] * 16
    report['outcome'] = facts
    report.update(schema_version=1, clock=report['held_timing']['clock'],
                  events_dropped=huge, flushes_dropped=huge, lock_closed=True,
                  configured_lock_seconds=2.0, save_begin_ns=huge, save_end_ns=huge)
    report['lock'] = dict(attempts=huge, opened_ns=huge, first_attempt_ns=huge,
                          last_attempt_begin_ns=huge, last_attempt_end_ns=huge,
                          last_native_error=33, acquired_ns=huge,
                          identity_observations=[dict(at_ns=huge, held=True,
                              identity=dict(volume=huge, file_id='f' * 32))] * 2)
    report['commit'] = dict(begin_ns=huge, end_ns=huge, held=True,
                            payload_bytes=8 * 1024 * 1024, dispatched=True)
    report['unlock'] = report['lock_close'] = dict(begin_ns=huge, end_ns=huge, success=True)
    assert len(json.dumps(report, ensure_ascii=True, allow_nan=False)) <= 32768


@pytest.mark.parametrize('name,digest', [
    ('_CONTENTION', 'ac79891abd5cf17c813a2edb861b2e1e8f66f5c0862de727d4d45caf5f4fd55a'),
    ('_SAVE', '99c192eb3d1acc9e98d7dba37f1e531b490e598501401fb49699111cbba3355a'),
])
def test_existing_single_attempt_and_campaign_programs_remain_byte_identical(name, digest):
    tree = ast.parse((Path(__file__).parent / 'test_memory_saved_windows_native.py').read_text(encoding='utf-8'))
    value = next(ast.literal_eval(node.value) for node in tree.body
                 if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets))
    assert hashlib.sha256(value.encode()).hexdigest() == digest
    compile(value if name == '_CONTENTION' else PREFIX.read_text(encoding='utf-8') + '\n' + value,
            '<native diagnostic program>', 'exec')


def test_ordinary_program_round_trips_exact_source_below_windows_command_limit():
    from test_memory_saved_windows_native import _CONTENTION, _SAVE, _ordinary_saved_program, request
    program, decoded = _ordinary_saved_program(), []
    exec(program, {'exec': decoded.append})
    assert decoded == [(_CONTENTION + PREFIX.read_text(encoding='utf-8') + '\n' + _SAVE).encode('utf-8')]
    root = 'C:\\Users\\runneradmin\\AppData\\Local\\Temp\\' + 'Owned space 雪 🧭\\' * 8 + 'Private store'
    argv = [r'D:\a\_temp\attune-full-suite-venv\Scripts\python.exe', '-I', '-c',
            program, root, json.dumps(request('independent-0'), ensure_ascii=True), '', '', '0', '']
    # CreateProcessW counts UTF-16 code units, including its terminating NUL.
    assert len(subprocess.list2cmdline(argv).encode('utf-16-le')) // 2 + 1 < 32767


def test_resource_samples_bind_flush_span_without_changing_calls(timing):
    timing.install()
    assert timing.store.save(timing.argument) is timing.result
    report = timing.scope['trace']['held_resources']
    assert report['captured'] == 1 and report['dropped'] == 0
    begin, end, before, after = report['flushes'][0]
    assert before[0] <= before[1] <= begin <= end <= after[0] <= after[1]
    assert len(before) == len(after) == len(report['sample_columns']) == 13
    assert before[2] <= after[2] and before[3] <= after[3]
    assert [row[0] for row in timing.events] == [
        'child', '_inspect', 'write_all', 'read', 'rename', 'flush', 'commit_payload', 'unlock']
    assert report['volume']['device_cache_filter'] == 'unknown'


@pytest.mark.parametrize('original_fails', [False, True])
def test_resource_sampler_failure_preserves_exact_original_outcome(timing, original_fails):
    error = OSError('native flush failure')
    if original_fails:
        timing.failure['flush'] = error
    timing.install()
    def broken():
        raise RuntimeError('observer failure must not replace native outcome')
    timing.scope['_held_resource_sample'] = broken
    if original_fails:
        with pytest.raises(OSError) as observed:
            timing.store.save(timing.argument)
        assert observed.value is error
    else:
        assert timing.store.save(timing.argument) is timing.result
    assert sum(row[0] == 'flush' for row in timing.events) == 1
    report = timing.scope['trace']['held_resources']
    assert report['flushes'][0][2:] == [None, None]
    assert report['errors'] == ['sample'] and report['observer_failed'] is True


@pytest.mark.parametrize('recording_fails', [False, True])
def test_resource_sampling_attempts_are_bounded_even_when_recording_fails(timing, recording_fails):
    timing.install()
    samples = []
    def sample():
        samples.append(True)
        return [0] * 13
    timing.scope['_held_resource_sample'] = sample
    if recording_fails:
        class BrokenRows(list):
            def append(self, value):
                raise OSError('cannot retain sample')
        timing.scope['_held_resource_rows'] = BrokenRows()
    timing.scope['trace']['held'] = True
    for _ in range(9):
        assert timing.native.flush(timing.argument) is timing.result
    assert len(samples) == 8
    assert timing.scope['_held_resource_captured'] == 4
    assert timing.scope['_held_resource_dropped'] == 5
    assert sum(row[0] == 'flush' for row in timing.events) == 9
    assert len(timing.scope['_held_resource_rows']) == (0 if recording_fails else 4)
    if recording_fails:
        assert timing.scope['_held_resource_errors'] == ['record']


def test_resource_apis_never_run_for_failed_lock_or_unheld_operation(timing):
    timing.native_type.lock_once = lambda *args, **kwargs: False
    timing.install()
    calls = []
    def forbidden():
        calls.append('resource_sample')
        raise RuntimeError('Resource observer must not run at this boundary')
    timing.scope['_held_resource_sample'] = forbidden
    errors_before = list(timing.scope['_held_resource_errors'])
    assert timing.native.lock_once(timing.argument) is False
    assert timing.native.flush(timing.argument) is timing.result
    assert calls == []
    assert timing.scope['_held_resource_errors'] == errors_before
    assert timing.scope['_held_resource_captured'] == 0


@pytest.fixture
def resource_api(timing, monkeypatch):
    import ctypes
    timing.install()
    slot, calls = [33], []
    class Counters(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in
            ('read_ops', 'write_ops', 'other_ops', 'read_bytes', 'write_bytes', 'other_bytes')]
    class FileTime(ctypes.Structure):
        _fields_ = [('dwLowDateTime', ctypes.c_uint32), ('dwHighDateTime', ctypes.c_uint32)]
    class API:
        fail = None
        def GetCurrentProcess(self):
            slot[:] = [99]
            return -1
        def GetProcessIoCounters(self, process, pointer):
            calls.append(('process_io', process))
            slot[:] = [100]
            if self.fail == 'process_io': return 0
            if self.fail == 'exception': raise OSError('unavailable')
            for name, _ in pointer._obj._fields_:
                setattr(pointer._obj, name, 2**64 - 1)
            return 1
        def GetSystemTimes(self, *pointers):
            calls.append(('system_cpu',))
            slot[:] = [101]
            if self.fail == 'system_cpu': return 0
            for pointer in pointers:
                pointer._obj.dwLowDateTime = pointer._obj.dwHighDateTime = 2**32 - 1
            return 1
    monkeypatch.setattr(ctypes, 'get_last_error', lambda: slot[0], raising=False)
    monkeypatch.setattr(ctypes, 'set_last_error', lambda value: slot.__setitem__(0, value), raising=False)
    api = API()
    # This fake models the counter ABI only; volume queries have separate native coverage.
    timing.scope['_held_resource_volume'] = lambda root: dict(
        status='unavailable', device_cache_filter='unknown')
    timing.scope.update(_held_os=SimpleNamespace(name='nt'), _held_resource_api=api,
                        _HeldIoCounters=Counters, _held_w=SimpleNamespace(FILETIME=FileTime))
    return SimpleNamespace(timing=timing, slot=slot, calls=calls, api=api)


@pytest.mark.parametrize('fault', [None, 'process_io', 'system_cpu', 'exception'])
def test_resource_api_results_and_unknowns_preserve_ctypes_last_error(resource_api, fault):
    control = resource_api
    control.api.fail = fault
    row = control.timing.scope['_held_resource_sample']()
    assert control.slot == [33]
    if fault == 'exception':
        assert row is None
        assert control.timing.scope['_held_resource_errors'] == ['sample']
    else:
        assert row[4:10] == ([None] * 6 if fault == 'process_io' else [2**64 - 1] * 6)
        assert row[10:] == ([None] * 3 if fault == 'system_cpu' else [2**64 - 1] * 3)
        assert control.timing.scope['_held_resource_errors'] == ([] if fault is None else [fault])


def test_resource_initialization_failure_is_advisory(timing, monkeypatch):
    import os
    def broken():
        raise OSError('processor query unavailable')
    monkeypatch.setattr(os, 'cpu_count', broken)
    timing.install()
    assert timing.store.save(timing.argument) is timing.result
    report = timing.scope['trace']['held_resources']
    assert report['errors'] == ['initialization']
    assert report['observer_failed'] is True


def test_unknown_release_never_queries_volume(timing):
    error = OSError('release unconfirmed')
    def unknown(*args, **kwargs):
        timing.scope['trace']['held'] = True
        raise error
    type(timing.store).save = unknown
    timing.install()
    def forbidden(*args):
        pytest.fail('Volume query while lock may be held')
    timing.scope['_held_resource_volume'] = forbidden
    with pytest.raises(OSError) as observed:
        timing.store.save(timing.argument)
    assert observed.value is error
    assert timing.scope['trace']['held_resources']['volume']['status'] == 'release_unconfirmed'


def test_resource_errors_are_bounded_tags(timing):
    timing.install()
    note = timing.scope['_held_resource_error']
    note('x' * 1000)
    for number in range(30):
        note('sample-' + str(number))
    assert len(timing.scope['_held_resource_errors']) == 8
    assert all(len(tag) <= 32 for tag in timing.scope['_held_resource_errors'])


def test_native_resource_apis_return_typed_counters_and_preserve_last_error(timing, tmp_path):
    import ctypes
    import os
    if os.name != 'nt':
        pytest.skip('Windows counter APIs run only on native Windows')
    timing.install()
    assert timing.scope['_held_resource_info']['windows_api'] is True
    ctypes.set_last_error(33)
    row = timing.scope['_held_resource_sample']()
    assert ctypes.get_last_error() == 33
    assert len(row) == 13 and all(type(value) is int and value >= 0 for value in row)
    volume = timing.scope['_held_resource_volume'](tmp_path)
    assert ctypes.get_last_error() == 33
    assert volume['status'] == 'observed_after_release'
    assert type(volume['serial']) is int and 0 <= volume['serial'] <= 2**32 - 1
    assert volume['binding'] == 'post_release_path_only; retained_handle_binding_not_verified'
    assert volume['device_cache_filter'] == 'unknown'
    assert timing.scope['_held_resource_errors'] == []


@pytest.mark.parametrize('original_fails', [False, True])
def test_replaced_resource_sampler_cannot_change_original_last_error(resource_api, original_fails):
    control = resource_api
    timing = control.timing
    error = OSError('original flush failure')
    if original_fails:
        timing.failure['flush'] = error
    def broken():
        control.slot[:] = [444]
        raise RuntimeError('replaced observer')
    timing.scope['_held_resource_sample'] = broken
    if original_fails:
        with pytest.raises(OSError) as observed:
            timing.store.save(timing.argument)
        assert observed.value is error
    else:
        assert timing.store.save(timing.argument) is timing.result
    assert control.slot == [33]
    assert sum(row[0] == 'flush' for row in timing.events) == 1
    assert timing.scope['trace']['held_resources']['errors'] == ['sample']
