"""Proposed real Windows saved-store journeys; unexecuted in this packet."""
# qualify: platform
import ctypes
from contextlib import contextmanager
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading

import pytest

from attune_harness.memory_saved import MAX_STATE, SavedError, SavedStore
from test_review import case  # existing offline registry fixture; no participant execution

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Real local NTFS saved-store operations')


@pytest.fixture
def canonical_tmp(tmp_path):
    # Resolve the trusted test producer's OS temp alias, never a SavedStore input.
    return tmp_path.resolve(strict=True)


def request(request_id='first', *, kind='memory'):
    value = {'request_id': request_id, 'kind': kind, 'scope': {'kind': 'global'},
             'title': 'Résumé 雪', 'content': 'Explicit retained content',
             'source': {'author': 'caller', 'reference': 'explicit test request'}}
    if kind == 'task':
        value['next_action'] = 'Review saved intent'
    return value


def test_native_memory_task_lifecycle_utf8_and_spaces(canonical_tmp):
    root = canonical_tmp / 'Private space 雪 🧭'
    store = SavedStore(root)
    memory = store.save(request())
    identifier = memory['record']['id']
    assert store.save(request()) == memory
    assert store.get(identifier, {'kind': 'global'})['title'] == 'Résumé 雪'
    assert len(store.list({'kind': 'global'})) == 1
    revised = store.revise(identifier, {'content': 'Revised 雪'}, {'kind': 'global'}, 'revision', 1)
    assert revised['record']['revision'] == 2
    assert store.save(request())['record']['revision'] == 1
    forgotten = store.forget(identifier, {'kind': 'global'}, 'withdrawal', 2)
    assert forgotten['record']['status'] == 'withdrawn'
    with pytest.raises(SavedError) as missing:
        store.get(identifier, {'kind': 'global'})
    assert missing.value.code == 'not_found'
    assert len(store.get(identifier, {'kind': 'global'}, include_withdrawn=True)['history']) == 3
    task = store.save(request('task', kind='task'))['record']
    completed = store.complete(task['id'], {'kind': 'global'}, 'complete', 1)
    assert completed['record']['status'] == 'completed'
    assert len(store.search('retained', {'kind': 'global'})) == 1
    assert store.reindex({'kind': 'global'})['index_status'] == 'disabled'
    raw = (root / 'state.json').read_bytes()
    assert 'Résumé 雪'.encode() in raw
    assert json.loads(raw)['schema_version'] == 1


_CONTENTION = """
import ctypes, hashlib, json, os, struct
from attune_harness.memory_saved_windows import _Native

# One fixed eight-writer observation, never a saved-store data transport.
class ContentionCells:
    header_bytes, cell_bytes, cells, writers = 512, 512, 512, 8
    total_bytes = header_bytes + cell_bytes * cells * writers

    def __init__(self, name, nonce, *, create=False, slot=None):
        self.native = _Native()  # Fixed ABI/security setup precedes every save.
        self.k, w = self.native.k, self.native.w
        self.handle, self.view, self.closed = None, None, False
        self.slot, self.sequence, self.failed = slot, 0, False
        self.name, self.nonce = name, nonce
        class SecurityAttributes(ctypes.Structure):
            _fields_ = [('length', w.DWORD), ('descriptor', ctypes.c_void_p),
                        ('inherit', w.BOOL)]
        self.k.CreateFileMappingW.argtypes = [w.HANDLE, ctypes.POINTER(SecurityAttributes),
                                             w.DWORD, w.DWORD, w.DWORD, w.LPCWSTR]
        self.k.CreateFileMappingW.restype = w.HANDLE
        self.k.OpenFileMappingW.argtypes = [w.DWORD, w.BOOL, w.LPCWSTR]
        self.k.OpenFileMappingW.restype = w.HANDLE
        self.k.MapViewOfFile.argtypes = [w.HANDLE, w.DWORD, w.DWORD, w.DWORD, ctypes.c_size_t]
        self.k.MapViewOfFile.restype = ctypes.c_void_p
        self.k.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
        self.k.UnmapViewOfFile.restype = w.BOOL
        self.k.QueryPerformanceCounter.argtypes = [ctypes.POINTER(ctypes.c_longlong)]
        self.k.QueryPerformanceCounter.restype = w.BOOL
        self.k.QueryPerformanceFrequency.argtypes = [ctypes.POINTER(ctypes.c_longlong)]
        self.k.QueryPerformanceFrequency.restype = w.BOOL
        value = ctypes.c_longlong()
        if not self.k.QueryPerformanceFrequency(ctypes.byref(value)) or value.value <= 0:
            raise OSError('Contention QPC frequency unavailable')
        self.frequency = value.value
        try:
            ctypes.set_last_error(0)
            if create:
                with self.native._descriptor() as descriptor:
                    attributes = SecurityAttributes(ctypes.sizeof(SecurityAttributes), descriptor, False)
                    self.handle = self.k.CreateFileMappingW(ctypes.c_void_p(-1).value,
                        ctypes.byref(attributes), 4, 0, self.total_bytes, name)
                    error = ctypes.get_last_error()
                if not self.handle:
                    self.handle = None
                    raise OSError(error, 'Contention mapping creation')
                if error == 183:
                    raise OSError(error, 'Contention mapping collision')
            else:
                self.handle = self.k.OpenFileMappingW(6, False, name)  # Noncreating.
                error = ctypes.get_last_error()
                if not self.handle:
                    self.handle = None
                    raise OSError(error, 'Contention mapping unavailable')
            self.view = self.k.MapViewOfFile(self.handle, 6, 0, 0, self.total_bytes)
            error = ctypes.get_last_error()
            if not self.view:
                raise OSError(error, 'Contention mapping view unavailable')
            header = json.dumps({'schema': 1, 'nonce': nonce, 'frequency': self.frequency,
                                 'writers': 8, 'cells': 512}, sort_keys=True).encode('ascii')
            expected = self.frame(1, header)
            self.expected_header = expected
            if create:
                ctypes.memset(self.view, 0, self.total_bytes)  # Touch pages before launch.
                ctypes.memmove(self.view, expected, self.header_bytes)
            elif ctypes.string_at(self.view, self.header_bytes) != expected:
                raise ValueError('Contention header/nonce/frequency differs')
            if slot is not None:
                if not 0 <= slot < 8:
                    raise ValueError('Contention slot is outside the fixed eight writers')
                self.add('attached', pid=os.getpid(), frequency=self.frequency)
        except BaseException as primary:
            try: self.close()
            except BaseException as cleanup: raise primary from cleanup
            raise

    @classmethod
    def frame(cls, sequence, payload):
        if not 1 <= sequence <= cls.cells or len(payload) > cls.cell_bytes - 56:
            raise ValueError('Contention cell exceeds its fixed bound')
        prefix = struct.pack('<II', sequence, len(payload)) + payload
        return prefix + bytes(cls.cell_bytes - 48 - len(prefix)) + hashlib.sha256(prefix).digest() + struct.pack('<QQ', sequence, ~sequence & ((1 << 64) - 1))

    def qpc(self):
        try:
            value = ctypes.c_longlong()
            if not self.k.QueryPerformanceCounter(ctypes.byref(value)):
                raise OSError('Contention QPC sample unavailable')
            return value.value
        except BaseException:
            self.failed = True
            return None

    def add(self, event, **fields):
        try:
            if self.failed or self.closed or self.sequence >= self.cells:
                self.failed = True
                return
            payload = json.dumps({'event': event, **fields}, separators=(',', ':'),
                                 ensure_ascii=True, allow_nan=False).encode('ascii')
            frame = self.frame(self.sequence + 1, payload)
            offset = self.header_bytes + (self.slot * self.cells + self.sequence) * self.cell_bytes
            ctypes.memmove(self.view + offset, frame, self.cell_bytes)
            self.sequence += 1
        except BaseException:
            self.failed = True  # Observer faults never alter a saved-store operation.

    def read_rows(self, children):
        if len(children) > self.writers:
            raise ValueError('Contention reader exceeds eight slots')
        if any(not child.get('producer_terminal_verified') or not child.get('producer_handle_close_confirmed') for child in children):
            raise ValueError('Producer ownership/terminal gate not confirmed; no mapping read')
        if ctypes.string_at(self.view, self.header_bytes) != self.expected_header:
            raise ValueError('Contention parent header changed')
        result = []
        for index, child in enumerate(children):
            rows, raw_prefix, error, first_unverified, gap_evidence = [], [], None, None, None
            if not child.get('cleanup_wait_completed'):
                result.append({'slot': index, 'valid_prefix': [], 'incomplete': 'original wait not completed'})
                continue
            for number in range(self.cells):
                offset = self.header_bytes + (index * self.cells + number) * self.cell_bytes
                frame = ctypes.string_at(self.view + offset, self.cell_bytes)
                if frame == bytes(self.cell_bytes):
                    for later in range(number + 1, self.cells):
                        later_offset = self.header_bytes + (index * self.cells + later) * self.cell_bytes
                        later_frame = ctypes.string_at(self.view + later_offset, self.cell_bytes)
                        if later_frame != bytes(self.cell_bytes):
                            error = 'zero gap followed by later cell data'
                            first_unverified = frame.hex()
                            gap_evidence = {'zero_cell_index': number, 'zero_frame_hex': frame.hex(),
                                'later_nonzero_cell_index': later, 'later_nonzero_frame_hex': later_frame.hex()}
                            break
                    break
                try:
                    sequence, size = struct.unpack('<II', frame[:8])
                    tail, inverse = struct.unpack('<QQ', frame[-16:])
                    if sequence != number + 1 or tail != sequence or inverse != (~sequence & ((1 << 64) - 1)) or size > self.cell_bytes - 56:
                        raise ValueError('partial, reordered or oversized contention cell')
                    prefix = frame[:8 + size]
                    if hashlib.sha256(prefix).digest() != frame[-48:-16]:
                        raise ValueError('contention cell digest differs')
                    row = json.loads(frame[8:8 + size])
                    if not isinstance(row, dict) or not isinstance(row.get('event'), str):
                        raise ValueError('contention event shape differs')
                    rows.append(row)
                    raw_prefix.append(frame.hex())
                except BaseException as fault:
                    first_unverified = frame.hex()
                    error = type(fault).__name__ + ': ' + str(fault)[:160]
                    break  # Retain only the verified prefix; never skip a gap.
            if error is None and (not rows or rows[0] != {'event': 'attached', 'pid': child['producer_identity']['pid'], 'frequency': self.frequency}):
                error = 'missing or mismatched original child identity/frequency'
            if len(rows) == self.cells:
                error = 'cell capacity reached; overflow/completeness unknown'
            terminal = bool(rows and rows[-1].get('event') in ('save_returned', 'save_error'))
            result.append({'slot': index, 'pid': child['producer_identity']['pid'],
                'launcher_pid': child['pid'], 'producer_identity': child['producer_identity'], 'valid_prefix': rows,
                'raw_prefix_hex': raw_prefix, 'first_unverified_frame_hex': first_unverified,
                'zero_gap_evidence': gap_evidence,
                'incomplete': error or ('original invocation not successful; prefix only'
                    if child.get('original_invocation_status') != 'succeeded'
                    else None if terminal else 'no terminal observation'),
                'terminal_observed': terminal,
                'original_invocation_status': child.get('original_invocation_status', 'unobserved'),
                'killed_by_parent': child.get('killed_by_parent', False),
                'claim': 'prefix events are not an invocation success or complete ownership census'})
        return {'schema': 1, 'frequency': self.frequency, 'header_hex': self.expected_header.hex(),
                'writers': result,
                'claim': 'diagnostic timing and observer resources; no original-run causal claim'}

    def close(self):
        if self.closed: return
        self.closed = True  # Unknown cleanup is never retried.
        error = None
        if self.view is not None:
            view, self.view = self.view, None
            try:
                if not self.k.UnmapViewOfFile(view): raise ctypes.WinError(ctypes.get_last_error())
            except BaseException as fault: error = fault
        if self.handle is not None:
            handle, self.handle = self.handle, None
            try:
                if not self.k.CloseHandle(handle): raise ctypes.WinError(ctypes.get_last_error())
            except BaseException as fault:
                if error is None: error = fault
        if error is not None: raise error


# Producer object retention is separate from the invocation launcher.
class ProducerHandles:
    prefix = 'SAVED_PRODUCER_HANDLE '
    maximum_line = 2048

    def __init__(self, native):
        self.native, self.k, self.w = native, native.k, native.w
        k, w = self.k, self.w
        k.GetCurrentProcess.argtypes, k.GetCurrentProcess.restype = [], w.HANDLE
        k.GetProcessId.argtypes, k.GetProcessId.restype = [w.HANDLE], w.DWORD
        k.GetProcessTimes.argtypes = [w.HANDLE, ctypes.POINTER(w.FILETIME),
            ctypes.POINTER(w.FILETIME), ctypes.POINTER(w.FILETIME), ctypes.POINTER(w.FILETIME)]
        k.GetProcessTimes.restype = w.BOOL
        k.OpenProcess.argtypes, k.OpenProcess.restype = [w.DWORD, w.BOOL, w.DWORD], w.HANDLE
        k.DuplicateHandle.argtypes = [w.HANDLE, w.HANDLE, w.HANDLE,
            ctypes.POINTER(w.HANDLE), w.DWORD, w.BOOL, w.DWORD]
        k.DuplicateHandle.restype = w.BOOL
        k.WaitForSingleObject.argtypes, k.WaitForSingleObject.restype = [w.HANDLE, w.DWORD], w.DWORD
        self.parent = self.identity(k.GetCurrentProcess())

    def identity(self, handle):
        pid = self.k.GetProcessId(handle)
        error = ctypes.get_last_error()
        if not pid: raise OSError(error, 'Producer process identity unavailable')
        created, ended, kernel, user = (self.w.FILETIME() for _ in range(4))
        if not self.k.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(ended),
                                      ctypes.byref(kernel), ctypes.byref(user)):
            raise OSError(ctypes.get_last_error(), 'Producer process creation unavailable')
        creation = created.dwLowDateTime | (created.dwHighDateTime << 32)
        if creation <= 0: raise ValueError('Producer creation identity unavailable')
        return {'pid': int(pid), 'created': creation}

    @staticmethod
    def encoded(payload):
        raw = json.dumps(payload, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=True, allow_nan=False).encode('ascii')
        return json.dumps({'payload': payload, 'sha256': hashlib.sha256(raw).hexdigest()},
                          sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')

    def publish(self, nonce, slot, expected_parent):
        parent, primary = None, None
        try:
            parent = self.k.OpenProcess(0x0040 | 0x1000, False, expected_parent['pid'])
            error = ctypes.get_last_error()
            if not parent:
                parent = None
                raise OSError(error, 'Producer target parent unavailable')
            if self.identity(parent) != expected_parent:
                raise ValueError('Producer target parent identity differs')
            current, target = self.k.GetCurrentProcess(), self.w.HANDLE()
            if not self.k.DuplicateHandle(current, current, parent, ctypes.byref(target),
                                          0x00100000 | 0x1000, False, 0):
                raise OSError(ctypes.get_last_error(), 'Producer handle transfer unconfirmed')
            # From this point, interruption can leave an unpublished target handle.
            # The child never guesses or remotely closes that parent-table value.
            payload = {'schema': 1, 'nonce': nonce, 'slot': slot, 'parent': expected_parent,
                       'producer': self.parent, 'handle': int(target.value)}
            line = self.prefix.encode('ascii') + self.encoded(payload) + b'\\n'
            if len(line) > self.maximum_line:
                raise ValueError('Producer handoff exceeds fixed bound')
            if os.write(2, line) != len(line):
                raise OSError('Producer handoff write incomplete')  # No write retry/ack.
        except BaseException as error:
            primary = error
            raise
        finally:
            if parent is not None:
                try:
                    if not self.k.CloseHandle(parent):
                        raise OSError(ctypes.get_last_error(), 'Producer parent-handle close unconfirmed')
                except BaseException as cleanup:
                    if primary is not None: raise primary from cleanup
                    raise

    def decode(self, text, nonce, slot):
        lines = [line for line in text.splitlines() if line.startswith(self.prefix)]
        if len(lines) != 1 or len(lines[0].encode('ascii', errors='replace')) > self.maximum_line:
            raise ValueError('Producer handoff missing, duplicate or oversized')
        envelope = json.loads(lines[0][len(self.prefix):])
        if not isinstance(envelope, dict) or set(envelope) != {'payload', 'sha256'}:
            raise ValueError('Producer handoff envelope differs')
        value = envelope['payload']
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=True, allow_nan=False).encode('ascii')
        if hashlib.sha256(raw).hexdigest() != envelope['sha256']:
            raise ValueError('Producer handoff digest differs')
        if (not isinstance(value, dict) or set(value) != {'schema', 'nonce', 'slot', 'parent', 'producer', 'handle'}
                or type(value['schema']) is not int or value['schema'] != 1
                or type(value['slot']) is not int or value['nonce'] != nonce or value['slot'] != slot
                or value['parent'] != self.parent):
            raise ValueError('Producer invocation/slot/parent differs')
        identity = value['producer']
        if (not isinstance(identity, dict) or set(identity) != {'pid', 'created'}
                or type(identity['pid']) is not int or identity['pid'] <= 0
                or type(identity['created']) is not int or identity['created'] <= 0
                or type(value['handle']) is not int
                or not 0 < value['handle'] < (1 << (8 * ctypes.sizeof(ctypes.c_void_p))) - 2):
            raise ValueError('Producer identity/handle shape differs')
        return value

    @staticmethod
    def error_facts(error):
        return {'type': type(error).__name__, 'errno': getattr(error, 'errno', None),
                'winerror': getattr(error, 'winerror', None), 'message': str(error)[:160]}

    def observe(self, children, nonce, elapsed):
        values, known, observations, unsafe = [], {}, [], []
        # Parse every transfer before native use, preventing duplicate-value reuse.
        for slot, row in enumerate(children):
            try:
                text = row.get('stderr') if row.get('output_received') else row.get('handoff_partial_stderr')
                if not isinstance(text, str): raise ValueError('Producer output unavailable')
                value = self.decode(text, nonce, slot)
                values.append(value)
            except BaseException as error:
                values.append(None)
                unsafe.append({'slot': slot, 'stage': 'handoff', 'error': self.error_facts(error), 'ownership': 'transfer_possible_unknown'})
        counts = {}
        for value in values:
            if value is not None: counts[value['handle']] = counts.get(value['handle'], 0) + 1
        for slot, value in enumerate(values):
            if value is None: continue
            if counts[value['handle']] != 1:
                unsafe.append({'slot': slot, 'stage': 'handoff', 'error': 'duplicate target handle value',
                               'ownership': 'unknown; no native use or guessed close'})
            else:
                known[slot] = value['handle']
        try:
            if not unsafe:
                for slot, (row, value) in enumerate(zip(children, values)):
                    observation = {'slot': slot, 'launcher_pid': row['pid'],
                                   'reported_producer': value['producer'], 'known_handle': value['handle']}
                    observations.append(observation)
                    try:
                        now, deadline = elapsed(), row.get('cleanup_deadline')
                        if now is None or deadline is None or now >= deadline:
                            raise ValueError('Producer cleanup budget unavailable or exhausted')
                        actual = self.identity(value['handle'])
                        observation['actual_producer'] = actual
                        if actual != value['producer']:
                            raise ValueError('Retained producer object identity differs')
                        wait = self.k.WaitForSingleObject(value['handle'], 0)
                        error = ctypes.get_last_error() if wait == 0xffffffff else None
                        observation.update(wait=int(wait), native_error=error)
                        if wait != 0: raise OSError(error or 0, 'Producer terminal state unconfirmed')
                        row['producer_identity'] = actual
                        row['producer_terminal_verified'] = True
                    except BaseException as error:
                        unsafe.append({'slot': slot, 'stage': 'object', 'error': self.error_facts(error)})
                        break  # No later identity/wait observations after uncertainty.
        finally:
            # Disposing other independently known handles is cleanup, never a retry
            # or a new process/product observation after a failure.
            for slot, handle in known.items():
                try:
                    if not self.k.CloseHandle(handle):
                        raise OSError(ctypes.get_last_error(), 'Producer target close unconfirmed')
                    children[slot]['producer_handle_close_confirmed'] = True
                except BaseException as error:
                    unsafe.append({'slot': slot, 'stage': 'close', 'error': self.error_facts(error), 'ownership': 'unknown; never retried'})
        if not unsafe:
            now = elapsed()
            if now is None or any(now >= row['cleanup_deadline'] for row in children):
                unsafe.append({'stage': 'read', 'error': 'Remaining cleanup budget exhausted before prefix read'})
        return {'safe': not unsafe, 'observations': observations, 'unsafe': unsafe,
                'unknown_disposition': None if not unsafe else 'parent OS exit / hosted-job VM disposal; not producer quiescence'}


class _UnobservedContention:
    def qpc(self): return None
    def add(self, *args, **kwargs): pass
    def close(self): pass
"""


# Filled only after explicit early-only sequencing approval and separately
# reviewed actual-main/caller/event binding. None keeps the experiment inactive.
_CONTENTION_HOSTED_ROUTE = None


_CONTENTION_EARLY_MAIN = '4377a66522d3380c83a298c74e1ca8c826c4710c'
_CONTENTION_EARLY_SOURCES = {
    "experiments/platform/diagnose_windows_environment.py": [
        "d307550e5e7cc5e18f2c82a3c1d4aa9908b63a258b0e5c09ebc30deb54c48751",
        "b944f35296df2bf128198cee3b82f1b358f90718a0b8ade33be89395f96312ba"
    ],
    ".github/workflows/qualification.yml": [
        "cdbf2904936bc6555b28ec2e9b1bafab373032c46fb3193ea9e93a892d464d91",
        "11f062c7efe4d21587056d307dc4fdda63a03be3cf9e6ff5014ca87951468fd8"
    ],
    "src/attune_harness/process.py": [
        "0fe4b4df48f7a362205d1f3f2cac35cc053f73179ef52843eb1530ddc176a291",
        "a1ae864ed6bdcce67a6ec9113c6bd048a9dd7e22576d4b8d73db6b810a1b2822"
    ],
    "src/attune_harness/windows.py": [
        "c5abac57c88ab4fa23c851e8fce042296ddc8403d0b024d297af9beddcd90a26",
        "fc89f6c7c26c4160d9cfbd5db1de7251f600672c7e905fd9cfd9d80fe4b8b9b3"
    ],
    "src/attune_harness/_windows_worker.py": [
        "f50c5538e9af03b65105f16f68f06ce28e9350a820556b7a6aa0124255d95cff",
        "3d3d00911155bdd2de572fb64ef94a1743258de3a215eafbd0e7ec634a76da1c"
    ],
    "src/attune_harness/memory_saved.py": [
        "4568e3db073bba46e0759248587cb9cffcd269056561f211b8dc61e4c1a89b0d",
        "055311af71bd57163f2cb6a5fe678102d2d732a53dbe8fc20c8bc3322771932b"
    ],
    "src/attune_harness/memory_saved_windows.py": [
        "8d6695465bafa38739d9587f9ae52ae18da7d566f56295fcc147f61753830c80",
        "81bff1d15bfb12a19e0b9af454a046e6db758139c928a26b2fdc4c6aee666d5a"
    ],
    "src/attune_harness/windows_effects.py": [
        "85f84b58ecb862f714d0ae543144daa2121b71cd052d9db09d4d71108114b815",
        "5cfd2c044df3fb4c549e4961820d693d78cfb3b593041831fa867d163c01bf1a"
    ]
}
_CONTENTION_PYTEST_ENTRY_SHA256 = '37f8b6a3df1aef71336bce85e366db968ede153dd72ad4e60bebff79e279dc40'


class _ContentionStop:
    def __init__(self, session):
        self.session, self.unsafe, self.reason = session, False, None

    def latch(self, reason):
        self.unsafe, self.reason = True, reason
        self.session._shouldstop = reason  # Pinned Session backing state, before fallible reporting.
        self.session.shouldstop = reason  # Public setter; never a producer kill.


def _contention_loaded_profile(request, binding, root):
    """Join reviewed bytes to loaded objects without running hooks or fixtures."""
    import hashlib
    from importlib.machinery import ModuleSpec
    from types import ModuleType
    plugins = {'_pytest.main': 'main', '_pytest.runner': 'runner',
        '_pytest.tmpdir': 'tmpdir', '_pytest.pathlib': None,
        '_pytest.junitxml': 'junitxml', '_pytest.cacheprovider': 'cacheprovider',
        '_pytest.fixtures': 'fixtures', 'anyio.pytest_plugin': 'anyio',
        'langsmith.pytest_plugin': 'langsmith_plugin',
        'harness_qualification_stacks': 'harness_qualification_stacks'}
    required = {name for name in plugins if name.startswith('_pytest.')}
    if set(binding['dependency_hashes']) != set(plugins):
        raise ValueError('route dependency binding incomplete')
    manager, observed, modules = request.config.pluginmanager, {}, {}
    for name, registration in plugins.items():
        expected = binding['dependency_hashes'][name]
        if (set(expected) != {'loaded', 'registered', 'sha256'}
                or type(expected['loaded']) is not bool
                or type(expected['registered']) is not bool):
            raise ValueError('dependency expectation shape differs: ' + name)
        module = sys.modules.get(name)
        registered = manager.get_plugin(registration) if registration else None
        if module is None:
            if (name in required or registered is not None or expected['loaded']
                    or expected['registered'] or expected['sha256'] is not None):
                raise ValueError('required loaded dependency absent: ' + name)
            observed[name] = {'loaded': False, 'registered': False, 'sha256': None}
            continue
        if not isinstance(module, ModuleType):
            raise ValueError('loaded dependency is not a module: ' + name)
        state = vars(module)
        spec = state.get('__spec__')
        if (not isinstance(spec, ModuleSpec) or spec.name != name or spec.loader is None
                or state.get('__loader__') is not spec.loader or not spec.has_location
                or not isinstance(spec.origin, str) or not isinstance(state.get('__file__'), str)):
            raise ValueError('loaded dependency spec/loader differs: ' + name)
        path = Path(spec.origin)
        if (path.is_symlink() or path.suffix != '.py' or not path.is_file()
                or path.resolve(strict=True) != Path(state['__file__']).resolve(strict=True)):
            raise ValueError('loaded dependency origin/file differs: ' + name)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        is_registered = registered is module
        if (registered is not None and not is_registered
                or name in required and registration is not None and not is_registered
                or not expected['loaded'] or expected['registered'] != is_registered
                or expected['sha256'] != actual):
            raise ValueError('loaded dependency object/bytes differ: ' + name)
        if (name == 'harness_qualification_stacks'
                and (path.resolve(strict=True) != (root / 'scripts/harness_qualification_stacks.py').resolve(strict=True)
                     or actual != binding['source_hashes']['scripts/harness_qualification_stacks.py'])):
            raise ValueError('loaded stack hook is not the reviewed caller source')
        observed[name] = {'loaded': True, 'registered': is_registered, 'sha256': actual,
            'origin': str(path.resolve(strict=True)),
            'loader_type': type(spec.loader).__module__ + '.' + type(spec.loader).__qualname__}
        modules[name] = module
    distributions, seen = [], set()
    for plugin, info in manager.list_plugin_distinfo():
        name = info.project_name.lower()
        expected = {'anyio': ('anyio.pytest_plugin', '4.15.1'),
                    'langsmith': ('langsmith.pytest_plugin', '0.12.5')}.get(name)
        if (expected is None or name in seen or info.version != expected[1]
                or plugin is not modules.get(expected[0])
                or not observed[expected[0]]['registered']):
            raise ValueError('external plugin distribution/object differs')
        seen.add(name)
        distributions.append({'distribution': name, 'version': info.version,
                              'module': expected[0]})
    for distribution, module_name in (('anyio', 'anyio.pytest_plugin'),
                                       ('langsmith', 'langsmith.pytest_plugin')):
        if observed[module_name]['registered'] != (distribution in seen):
            raise ValueError('registered plugin has no matching distribution: ' + distribution)
    conftests = {}
    for module in manager._conftest_plugins:
        if not isinstance(module, ModuleType) or module not in manager.get_plugins():
            raise ValueError('conftest registration differs')
        path = Path(vars(module)['__file__'])
        expected_path = root / 'tests/conftest.py'
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if (path.is_symlink() or path.resolve(strict=True) != expected_path.resolve(strict=True)
                or actual != binding['source_hashes']['tests/conftest.py']):
            raise ValueError('active conftest source differs')
        conftests['tests/conftest.py'] = {'origin': str(path.resolve(strict=True)), 'sha256': actual}
    if set(conftests) != {'tests/conftest.py'}:
        raise ValueError('reviewed conftest is not active')
    # Read existing FixtureDef/cached-result metadata only. Do not invoke a fixture,
    # a hook or FixtureFunctionDefinition._get_wrapped_function().
    fixture_module = modules['_pytest.fixtures']
    expected_fixtures = {
        'tmp_path': (vars(modules['_pytest.tmpdir'])['tmp_path'], 'function'),
        'tmp_path_factory': (vars(modules['_pytest.tmpdir'])['tmp_path_factory'], 'session'),
        'record_property': (vars(modules['_pytest.junitxml'])['record_property'], 'function'),
        'canonical_tmp': (canonical_tmp, 'function')}
    fixtures = {}
    for name, (wrapper, scope) in expected_fixtures.items():
        definition = request._fixture_defs.get(name)
        if (type(wrapper) is not fixture_module.FixtureFunctionDefinition
                or type(definition) is not fixture_module.FixtureDef
                or definition.func is not vars(wrapper).get('_fixture_function')
                or definition.scope != scope or definition.cached_result is None
                or definition.cached_result[2] is not None):
            raise ValueError('active fixture function/result differs: ' + name)
        fixtures[name] = {'module': definition.func.__module__,
                          'qualname': definition.func.__qualname__, 'scope': scope}
    factory = request._fixture_defs['tmp_path_factory'].cached_result[0]
    state = vars(factory)
    if (type(factory) is not modules['_pytest.tmpdir'].TempPathFactory
            or request.config._tmp_path_factory is not factory
            or state.get('_retention_policy') != 'all'
            or type(state.get('_retention_count')) is not int or state['_retention_count'] < 1
            or state['_retention_count'] != int(request.config.getini('tmp_path_retention_count'))
            or state.get('_given_basetemp', 'missing') is not None):
        raise ValueError('actual temporary factory differs from reviewed retention')
    if request.node.obj is not test_native_cross_process_independent_and_identical_requests:
        raise ValueError('active item is not the reviewed native writer case')
    fixtures['active_conftests'] = conftests
    fixtures['factory'] = {'retention': state['_retention_policy'],
        'retention_count': state['_retention_count'], 'explicit_basetemp': False}
    return observed, distributions, fixtures


def _contention_early_owner(request, binding, root):
    """Admit only the existing main early selection; flags never attest its host."""
    import hashlib
    from importlib.machinery import ModuleSpec
    from types import ModuleType
    if (binding.get('route') != 'main4377-early-installed-owner'
            or binding.get('early_caller_actual_main') != _CONTENTION_EARLY_MAIN):
        raise ValueError('early-only sequencing route is not bound')
    selected = [str(root / 'tests/test_windows_runtime.py'),
                str(root / 'tests/test_memory_saved_windows_native.py')]
    xml = str(root / 'windows-environment-diagnostic/tests.xml')
    arguments = ['-vv', '-o', 'pythonpath=', '-o', 'faulthandler_timeout=20',
                 '--junitxml=' + xml, *selected]
    if (list(sys.argv[1:]) != arguments
            or tuple(request.config.invocation_params.args) != tuple(arguments)
            or list(request.config.args) != selected
            or request.config.option.xmlpath != xml
            or request.config.option.keyword or request.config.option.markexpr
            or request.config.getini('pythonpath')
            or os.environ.get('PYTEST_DISABLE_PLUGIN_AUTOLOAD') != '1'
            or any(name in os.environ for name in ('PYTHONPATH', 'PYTEST_ADDOPTS', 'PYTEST_PLUGINS'))):
        raise ValueError('not the exact main early pytest selection/environment')
    cwd = Path.cwd().resolve(strict=True)
    if (cwd == root or root in cwd.parents or not cwd.name.startswith('attune-win-diagnostic-')
            or Path(request.config.invocation_params.dir).resolve(strict=True) != cwd):
        raise ValueError('not the early helper scratch working directory')
    main = sys.modules.get('__main__')
    package = sys.modules.get('attune_harness')
    memory = sys.modules.get('attune_harness.memory_saved')
    if not all(isinstance(module, ModuleType) for module in (main, package, memory)):
        raise ValueError('actual pytest/package objects missing')
    entry = vars(main)
    spec = entry.get('__spec__')
    if (not isinstance(spec, ModuleSpec) or spec.name != 'pytest.__main__'
            or spec.loader is None or entry.get('__loader__') is not spec.loader
            or not spec.has_location):
        raise ValueError('not the actual pytest module entrypoint')
    entry_path = Path(entry['__file__'])
    if (entry_path.is_symlink() or entry_path.resolve(strict=True) != Path(spec.origin).resolve(strict=True)
            or entry_path.resolve(strict=True) != Path(sys.argv[0]).resolve(strict=True)
            or hashlib.sha256(entry_path.read_bytes()).hexdigest() != _CONTENTION_PYTEST_ENTRY_SHA256):
        raise ValueError('loaded pytest entrypoint identity/bytes differ')
    installed = Path(vars(package)['__file__']).resolve(strict=True).parent
    if (installed != (Path(sys.prefix) / 'Lib/site-packages/attune_harness').resolve(strict=True)
            or installed == root / 'src/attune_harness' or root in installed.parents
            or entry_path.resolve(strict=True).parent != installed.parent / 'pytest'
            or Path(vars(memory)['__file__']).resolve(strict=True) != installed / 'memory_saved.py'
            or vars(memory).get('SavedStore') is not SavedStore):
        raise ValueError('not the reviewed installed source/class identity')
    observed = {}
    for name, allowed in _CONTENTION_EARLY_SOURCES.items():
        path = root / name
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if path.is_symlink() or digest not in allowed:
            raise ValueError('main early caller/library bytes differ: ' + name)
        observed[name] = digest
        if name.startswith('src/attune_harness/'):
            installed_path = installed / name.rsplit('/', 1)[-1]
            if installed_path.is_symlink() or installed_path.read_bytes() != raw:
                raise ValueError('early installed/source bytes differ: ' + name)
    return {'route': 'early-installed-owner', 'caller_actual_main': _CONTENTION_EARLY_MAIN,
        'source_hashes': observed, 'pytest_entrypoint_sha256': _CONTENTION_PYTEST_ENTRY_SHA256,
        'installed': str(installed), 'command_arguments': arguments, 'scratch_cwd': str(cwd),
        'outer_limit_seconds': 180,
        'claim': 'runtime source/invocation observations; actual helper parent, hosted job and sequencing approval remain externally verified'}


def _contention_profile(request, binding):
    """Filter the externally admitted experiment; never refuse ordinary R4."""
    import hashlib
    import importlib.metadata
    if binding is None:
        return None, 'shared main/caller/event admission not bound; ordinary R4 only'
    try:
        # Flags are only defensive profile checks. The configured lead must also
        # bind actual hosted workflow/run/job evidence before a native event go.
        if (os.name != 'nt' or os.environ.get('GITHUB_ACTIONS') != 'true'
                or os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted'
                or os.environ.get('GITHUB_EVENT_NAME') != 'pull_request'
                or os.environ.get('GITHUB_REPOSITORY') != binding['repository']):
            raise ValueError('not the externally bound hosted profile')
        root = Path(__file__).resolve().parents[1]
        early_owner = _contention_early_owner(request, binding, root)
        required_sources = {'scripts/qualify_platform.py', 'scripts/check_installed.py',
            'scripts/measure_coverage.py', 'scripts/harness_qualification_stacks.py',
            'experiments/platform/diagnose_windows_environment.py',
            '.github/workflows/qualification.yml', '.github/workflows/coverage.yml',
            'tests/conftest.py', 'pyproject.toml'}
        if set(binding['source_hashes']) != required_sources:
            raise ValueError('route source binding incomplete')
        observed_sources = {}
        for name, digest in binding['source_hashes'].items():
            path = root / name
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            observed_sources[name] = actual
            if path.is_symlink() or actual != digest:
                raise ValueError('reviewed caller/workflow source profile differs: ' + name)
        if (request.config.getini('tmp_path_retention_policy') != 'all'
                or int(request.config.getini('tmp_path_retention_count')) < 1
                or request.config.option.basetemp is not None
                or request.node.get_closest_marker('langsmith') is not None
                or 'anyio_backend' in request.fixturenames
                or request.config.getoption('--langsmith-output', default=False)):
            raise ValueError('fixture/retention/hook profile differs')
        if importlib.metadata.version('pytest') != '9.1.1':
            raise ValueError('pytest version differs')
        observed_dependencies, observed_plugins, observed_fixtures = _contention_loaded_profile(request, binding, root)
        if observed_plugins or any(row['registered'] for name, row in observed_dependencies.items()
                if not name.startswith('_pytest.')):
            raise ValueError('external/stack plugins are not the early autoload-disabled profile')
        stop = _ContentionStop(request.session)
        stop.profile = {'source_hashes': observed_sources, 'dependency_hashes': observed_dependencies,
            'plugins': observed_plugins, 'active_fixtures': observed_fixtures, 'pytest': '9.1.1', 'retention': 'all',
            'retention_count': int(request.config.getini('tmp_path_retention_count')),
            'explicit_basetemp': False, 'langsmith_marker_or_output': False,
            'anyio_backend_requested': False, 'early_owner': early_owner,
            'github_context': {name: os.environ.get(name) for name in
                ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_JOB', 'RUNNER_NAME')},
            'claim': 'source/profile observations; actual hosted event/runner admission remains separately verified by the configured lead'}
        return stop, None
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, OSError) as error:
        return None, type(error).__name__ + ': ' + str(error)[:160]


@pytest.fixture
def contention_observation(request):
    stop, reason = _contention_profile(request, _CONTENTION_HOSTED_ROUTE)
    return {'stop': stop, 'reason': reason, 'profile': None if stop is None else stop.profile}


def _contention_partial_output(row, error):
    """Retain only bytes already returned by an ORIGINAL timed communicate."""
    value = getattr(error, 'stderr', None)
    if isinstance(value, bytes):
        row['handoff_partial_stderr_hex'] = value[:65536].hex()
        try: value = value[:65536].decode('ascii')
        except UnicodeDecodeError: return
    if isinstance(value, str): row['handoff_partial_stderr'] = value[:65536]


def _new_contention_cells():
    import uuid
    namespace = {}
    exec(_CONTENTION, namespace)
    nonce = uuid.uuid4().hex
    cells = namespace['ContentionCells']('Local\\AttuneSavedContention-' + nonce, nonce, create=True)
    cells.producer_factory = namespace['ProducerHandles']
    return cells


_SAVE = """
import ctypes, json, sys, time
from pathlib import Path
from attune_harness import memory_saved_windows as backend
from attune_harness.memory_saved import SavedStore
clock = time.get_clock_info('monotonic')
trace = {'schema_version': 1, 'clock': {'implementation': clock.implementation,
    'resolution': clock.resolution, 'monotonic': clock.monotonic, 'adjustable': clock.adjustable},
    'events': [], 'events_dropped': 0, 'observer_failed': False,
    'lock': {'attempts': 0, 'identity_observations': []}, 'flushes': [],
    'held': False, 'lock_closed': False}
lock_key = None
cells = (ContentionCells(sys.argv[3], sys.argv[4], slot=int(sys.argv[5]))
         if sys.argv[3] else _UnobservedContention())
if sys.argv[3]:
    try:
        ProducerHandles(cells.native).publish(sys.argv[4], int(sys.argv[5]), json.loads(sys.argv[6]))
    except BaseException as primary:
        try: cells.close()
        except BaseException as cleanup: raise primary from cleanup
        raise
original_backend_time = backend.time

class DeadlineTime:
    first = None
    def monotonic(self):
        begin = cells.qpc()
        value = original_backend_time.monotonic()
        end = cells.qpc()
        if self.first is None:
            self.first = value
            cells.add('deadline_start', begin=begin, end=end, value=value,
                      deadline=value + backend.LOCK_SECONDS)
        elif value >= self.first + backend.LOCK_SECONDS:
            cells.add('deadline_expired', begin=begin, end=end, value=value,
                      deadline=self.first + backend.LOCK_SECONDS)
        return value
    def sleep(self, seconds):
        return original_backend_time.sleep(seconds)

backend.time = DeadlineTime()

def stamp():
    try: return time.monotonic_ns()
    except BaseException:
        trace['observer_failed'] = True
        return None

def facts(error):
    return {'type': type(error).__name__, 'errno': getattr(error, 'errno', None),
            'winerror': getattr(error, 'winerror', None), 'code': getattr(error, 'code', None),
            'outcome': getattr(error, 'outcome', None)}

def note(event, **value):
    try:
        if len(trace['events']) == 64:
            del trace['events'][0]
            trace['events_dropped'] += 1
        trace['events'].append({'event': event, **value})
    except BaseException:
        trace['observer_failed'] = True

original_child, original_inspect = backend._Native.child, backend._Session._inspect
original_lock, original_unlock = backend._Native.lock_once, backend._Native.unlock
original_close, original_flush = backend._Native.close, backend._Native.flush
original_commit = backend._Session.commit_payload

def child(native, parent, name, **kwargs):
    global lock_key
    result = original_child(native, parent, name, **kwargs)
    if kwargs.get('lock'):
        lock_key = id(result)
        trace['lock']['opened_ns'] = stamp()
    return result

def inspect(session, handle, kind):
    result = original_inspect(session, handle, kind)
    if id(handle) == lock_key:
        entry, size = result
        try:
            trace['lock']['identity_observations'].append({
                'at_ns': stamp(), 'identity': entry['identity'], 'held': trace['held']})
            cells.add('identity', at=cells.qpc(), identity=entry['identity'], held=trace['held'])
        except BaseException:
            trace['observer_failed'] = True
    return result

def lock_once(native, handle):
    begin, qpc_begin = stamp(), cells.qpc()
    trace['lock'].setdefault('first_attempt_ns', begin)
    trace['lock']['attempts'] += 1
    try:
        result = original_lock(native, handle)
        error = ctypes.get_last_error() if not result else None
    except BaseException as primary:
        error = facts(primary)  # Original native error precedes clock/event observations.
        trace['lock']['native_exception'] = error
        cells.add('lock_exception', begin=qpc_begin, end=cells.qpc(), error=error)
        note('lock_exception', begin_ns=begin, end_ns=stamp(), error=error)
        raise
    qpc_end, end = cells.qpc(), stamp()
    cells.add('lock_attempt', begin=qpc_begin, end=qpc_end, acquired=bool(result), native_error=error)
    trace['lock'].update(last_attempt_begin_ns=begin, last_attempt_end_ns=end,
                         last_native_error=error)
    if result:
        trace['held'] = True
        trace['lock']['acquired_ns'] = end
    note('lock_attempt', begin_ns=begin, end_ns=end, acquired=bool(result), native_error=error)
    return result

def unlock(native, handle):
    begin = stamp()
    cells.add('unlock_begin', at=cells.qpc())
    try:
        result = original_unlock(native, handle)
    except BaseException as primary:
        error = facts(primary)
        trace['unlock'] = {'begin_ns': begin, 'end_ns': stamp(), 'error': error}
        cells.add('unlock_error', at=cells.qpc(), error=error)
        raise
    trace['held'] = False
    trace['unlock'] = {'begin_ns': begin, 'end_ns': stamp(), 'success': True}
    cells.add('unlock_returned', at=cells.qpc())
    return result

def close(native, handle):
    selected, begin = id(handle) == lock_key, stamp()
    if selected: cells.add('lock_close_begin', at=cells.qpc())
    try:
        result = original_close(native, handle)
    except BaseException as primary:
        error = facts(primary)
        if selected:
            trace['lock_close'] = {'begin_ns': begin, 'end_ns': stamp(), 'error': error}
            cells.add('lock_close_error', at=cells.qpc(), error=error)
        else: note('other_close_error', error=error, at_ns=stamp())
        raise
    if selected:
        trace['lock_closed'], trace['held'] = True, False
        trace['lock_close'] = {'begin_ns': begin, 'end_ns': stamp(), 'success': True}
        cells.add('lock_close_returned', at=cells.qpc())
    return result

def flush(native, handle):
    row = {'begin_ns': stamp(), 'held': trace['held'], 'is_lock': id(handle) == lock_key}
    cells.add('flush_begin', at=cells.qpc(), held=trace['held'], is_lock=row['is_lock'])
    try:
        result = original_flush(native, handle)
    except BaseException as primary:
        error = facts(primary)
        row.update(end_ns=stamp(), error=error)
        cells.add('flush_error', at=cells.qpc(), held=trace['held'], error=error)
        raise
    else:
        row.update(end_ns=stamp(), statuses=result)
        cells.add('flush_returned', at=cells.qpc(), held=trace['held'], statuses=result)
        return result
    finally:
        try:
            if len(trace['flushes']) == 16:
                trace['flushes_dropped'] = trace.get('flushes_dropped', 0) + 1
                del trace['flushes'][0]
            trace['flushes'].append(row)
        except BaseException:
            trace['observer_failed'] = True

def commit(session, payload):
    trace['commit'] = {'begin_ns': stamp(), 'held': trace['held'], 'payload_bytes': len(payload)}
    cells.add('commit_begin', at=cells.qpc(), held=trace['held'])
    try:
        return original_commit(session, payload)
    finally:
        try:
            trace['commit'].update(end_ns=stamp(), dispatched=session.dispatched)
            cells.add('commit_end', at=cells.qpc(), held=trace['held'], dispatched=session.dispatched)
        except BaseException:
            trace['observer_failed'] = True

backend._Native.child, backend._Session._inspect = child, inspect
backend._Native.lock_once, backend._Native.unlock = lock_once, unlock
backend._Native.close, backend._Native.flush = close, flush
backend._Session.commit_payload = commit
trace['configured_lock_seconds'] = backend.LOCK_SECONDS
trace['save_begin_ns'], primary = stamp(), None
try:
    result = SavedStore(Path(sys.argv[1])).save(json.loads(sys.argv[2]))
except BaseException as error:
    primary = error
    trace['outcome'] = facts(error)
    cells.add('save_error', at=cells.qpc(), error=trace['outcome'])
    raise
else:
    trace['outcome'] = {'type': 'returned', 'record_id': result['record']['id'],
                        'revision': result['record']['revision']}
    cells.add('save_returned', at=cells.qpc())
finally:
    backend.time = original_backend_time
    trace['save_end_ns'] = stamp()
    try:
        # Existing pipe report stays after confirmed saved-lock release.
        if not trace['held']:
            try:
                encoded = json.dumps(trace, ensure_ascii=True, allow_nan=False)
                if len(encoded) > 32768: raise ValueError('bounded diagnostic report exceeded')
                print('SAVED_CONCURRENCY_DIAGNOSTIC ' + encoded, file=sys.stderr, flush=True)
            except BaseException:
                if primary is None: raise
    finally:
        active = sys.exc_info()[1]
        try: cells.close()
        except BaseException as cleanup:
            if active is not None: raise active from cleanup
            raise
print(json.dumps(result, ensure_ascii=True, allow_nan=False), flush=True)
"""


def _concurrency_outputs(row):
    """Parse retained child output only after original ownership cleanup."""
    if not row.get('output_received'):
        row['diagnostic_unobserved'] = True
        return
    stdout, stderr = row.pop('stdout'), row.pop('stderr')
    row['stdout'], row['stderr'] = stdout[:32768], stderr[:65536]
    row['output_truncated'] = len(stdout) > 32768 or len(stderr) > 65536
    reports = [line[len('SAVED_CONCURRENCY_DIAGNOSTIC '):] for line in stderr.splitlines()
               if line.startswith('SAVED_CONCURRENCY_DIAGNOSTIC ')]
    try:
        if len(reports) == 1 and len(reports[0]) <= 32768:
            decoded = json.loads(reports[0])
            if not isinstance(decoded, dict):
                raise ValueError('diagnostic report is not an object')
            row['diagnostic'] = decoded
        else:
            row['diagnostic_unobserved'] = True
    except BaseException as error:
        row['diagnostic_parse_error'] = _kill_error_facts(error)
        row['diagnostic_unobserved'] = True


def _ordinary_saved_program():
    import base64
    import zlib
    timing = (Path(__file__).parent / 'helpers' / 'windows_saved_held_timing.py').read_text(encoding='utf-8')
    source = _CONTENTION + timing + '\n' + _SAVE
    # The original inline program is already near CreateProcessW's command-line
    # limit. Decode trusted test source before storage starts, keeping argv fixed.
    encoded = base64.b64encode(zlib.compress(source.encode('utf-8'))).decode('ascii')
    return 'import base64,zlib\nexec(zlib.decompress(base64.b64decode(' + repr(encoded) + ')))'


def writers(root, requests, record_property, phase, observation=None):
    import time
    children, rows, primary, cleanup_error, cells = [], [], None, None, None
    stop = None if observation is None else observation['stop']
    owners, producer_report, unsafe = None, None, False
    clock = time.get_clock_info('monotonic')
    def stamp():
        try: return time.monotonic_ns()
        except BaseException: return None
    def elapsed():
        try: return time.monotonic()
        except BaseException: return None
    try:
        if stop is not None:
            cells = _new_contention_cells()
            owners = cells.producer_factory(cells.native)
        # Ordinary R4 outside the admitted route adds no producer-object/mapping APIs.
        script = _CONTENTION + _SAVE
        if stop is None:
            # Ordinary diagnostics only. Retained-cell admission and its frozen
            # script remain unchanged; no additional workload or retry is run.
            script = _ordinary_saved_program()
        for value in requests:
            row = {'request_id': value['request_id'], 'launch_begin_ns': stamp(),
                   'output_received': False, 'killed_by_parent': False}
            if stop is not None: unsafe = True  # Until all actual producer objects are confirmed.
            child = subprocess.Popen([sys.executable, '-I', '-c', script, str(root),
                json.dumps(value, ensure_ascii=True), '' if cells is None else cells.name,
                '' if cells is None else cells.nonce, str(len(children)),
                '' if owners is None else json.dumps(owners.parent, sort_keys=True)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True)
            children.append(child)
            rows.append(row)
            row['launch_end_ns'], row['pid'] = stamp(), child.pid
        results = []
        for child, row in zip(children, rows):
            try:
                stdout, stderr = child.communicate(timeout=30)
            except BaseException as error:
                row['communicate_error'] = _kill_error_facts(error)
                try: _contention_partial_output(row, error)
                except BaseException: pass  # Observation cannot replace the original error.
                if primary is None:
                    primary = error
                break
            row.update(stdout=stdout, stderr=stderr, output_received=True,
                       observed_exit=child.returncode, observed_ns=stamp())
            if child.returncode == 0:
                try:
                    result = json.loads(stdout)
                except Exception as error:
                    row['result_parse_error'] = _kill_error_facts(error)
                    if primary is None:
                        primary = error
                else:
                    results.append(result)
                    row['result_accepted'] = True
            try:
                assert child.returncode == 0, stderr
            except AssertionError as error:
                if primary is None:
                    primary = error
        if primary is not None:
            raise primary
        return results
    except BaseException as error:
        primary = error
        raise
    finally:
        for child, row in zip(children, rows):
            cleanup_begin = elapsed()
            row['cleanup_deadline'] = None if cleanup_begin is None else cleanup_begin + 10
            try:
                row['cleanup_poll'] = child.poll()
                if row['cleanup_poll'] is None:
                    row['killed_by_parent'] = True
                    row['kill_ns'] = stamp()
                    child.kill()
                child.wait(timeout=10)
                row['cleanup_exit'], row['cleanup_end_ns'] = child.returncode, stamp()
            except BaseException as error:
                row['cleanup_error'] = _kill_error_facts(error)
                if cleanup_error is None: cleanup_error = error
            else:
                row['cleanup_wait_completed'] = True
        # Complete every original kill/wait decision before collecting any new
        # output. A drain cannot delay the next original cleanup action.
        for child, row in zip(children, rows):
            if row.get('cleanup_wait_completed') and not row['output_received']:
                now, deadline = elapsed(), row['cleanup_deadline']
                if now is None or deadline is None:
                    row['post_cleanup_drain_unobserved'] = 'cleanup clock unavailable'
                    continue
                remaining = max(0.0, deadline - now)
                if remaining == 0:
                    row['post_cleanup_drain_unobserved'] = 'cleanup budget exhausted'
                    continue
                try:
                    stdout, stderr = child.communicate(timeout=remaining)
                    row.update(stdout=stdout, stderr=stderr, output_received=True)
                except BaseException as error:
                    row['post_cleanup_drain_error'] = _kill_error_facts(error)
                    try: _contention_partial_output(row, error)
                    except BaseException: pass
        try:
            for row in rows:
                row['original_invocation_status'] = ('succeeded' if row.get('result_accepted')
                    else 'failed' if 'observed_exit' in row else 'unobserved')
                try:
                    _concurrency_outputs(row)
                except BaseException as error:
                    row['diagnostic_parse_error'] = _kill_error_facts(error)
                    row['diagnostic_unobserved'] = True
            if stop is None:
                retained = {'incomplete': 'targeted route unadmitted; original R4 executed',
                            'reason': None if observation is None else observation['reason']}
            else:
                producer_report = (owners.observe(rows, cells.nonce, elapsed)
                    if owners is not None else {'safe': False, 'unsafe': ['observer setup/launch disposition unknown']})
                unsafe = not producer_report['safe'] or len(rows) != len(requests)
                if unsafe:
                    stop.latch('SavedStore producer ownership unknown; stop relevant dispatch until hosted-job disposal')
                    retained = {'incomplete': 'producer ownership/terminal gate refused', 'mapping_prefix_read': False}
                    if cleanup_error is None: cleanup_error = RuntimeError('SavedStore producer ownership unconfirmed')
                else:
                    retained = cells.read_rows(rows)
            encoded = json.dumps({
                'clock': {'implementation': clock.implementation, 'resolution': clock.resolution,
                          'monotonic': clock.monotonic, 'adjustable': clock.adjustable},
                'claim': 'diagnostic observations affect timing; no original-run causal claim',
                'children': rows, 'retained_cells': retained, 'producer_objects': producer_report,
                'experiment_profile': None if observation is None else observation.get('profile')}, ensure_ascii=True, allow_nan=False)
            if len(encoded) > 8 * 1024 * 1024:
                raise ValueError('Bounded contention parent report exceeded')
            record_property('saved_native_concurrency_' + phase, encoded)
        except BaseException as error:
            if primary is None and cleanup_error is None: cleanup_error = error
        if cells is not None:
            try: cells.close()
            except BaseException as error:
                unsafe = True
                if cleanup_error is None: cleanup_error = error
        if stop is not None and unsafe:
            # This backing state is pinned to pytest9.1.1 and is set even if a
            # reporting/callback/public-setter fault occurred above. No next item.
            stop.unsafe = True
            stop.session._shouldstop = 'SavedStore producer/resource disposition unknown; hosted job quarantined'
            if cleanup_error is None: cleanup_error = RuntimeError('SavedStore observer cleanup unknown')
        if primary is not None and cleanup_error is not None:
            raise primary from cleanup_error
        if primary is None and cleanup_error is not None:
            raise cleanup_error


def test_native_cross_process_independent_and_identical_requests(canonical_tmp, record_property, contention_observation):
    root = canonical_tmp / 'Concurrent fresh 雪' / 'Private store'
    assert not root.parent.exists()
    independent = writers(root, [request('independent-' + str(i)) for i in range(8)],
                          record_property, 'independent', contention_observation)
    assert len({row['record']['id'] for row in independent}) == 8
    identical = writers(root, [request('identical')] * 8, record_property, 'identical', contention_observation)
    assert all(row == identical[0] for row in identical)
    store = SavedStore(root)
    assert len(store.list({'kind': 'global'})) == 9
    state = json.loads((root / 'state.json').read_bytes())
    assert len(state['operations']) == 9
    assert all(record['revision'] == 1 and len(record['history']) == 1
               for record in state['records'].values())


def test_native_process_death_releases_persistent_lock(canonical_tmp):
    from attune_harness.memory_saved_windows import locked
    root = canonical_tmp / 'Crash lock 雪'
    script = """
import sys, time
from pathlib import Path
from attune_harness.memory_saved_windows import locked
with locked(Path(sys.argv[1])):
    print('lock-acquired', flush=True)
    time.sleep(30)
"""
    child = subprocess.Popen([sys.executable, '-I', '-c', script, str(root)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    messages = queue.Queue()
    threading.Thread(target=lambda: messages.put(child.stdout.readline()), daemon=True).start()
    try:
        assert messages.get(timeout=15).strip() == 'lock-acquired'
        inode = os.stat(root / '.saved.lock').st_ino
        child.kill()
        child.wait(timeout=10)
        with locked(root):
            assert os.stat(root / '.saved.lock').st_ino == inode
        assert SavedStore(root).save(request())['record']['revision'] == 1
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=10)
    # This checks crash release, not power-loss durability or an ACKed write.


def test_native_persistent_lock_denies_delete_sharing(canonical_tmp):
    from attune_harness.memory_saved_windows import locked
    root = canonical_tmp / 'Delete sharing'
    with locked(root):
        before = os.stat(root / '.saved.lock').st_ino
        with pytest.raises(PermissionError) as denied:
            os.rename(root / '.saved.lock', root / 'replacement.lock')
        assert denied.value.winerror == 32
        assert os.stat(root / '.saved.lock').st_ino == before


def test_native_lost_ack_replay_adds_no_state_commit_barrier(canonical_tmp, monkeypatch,
                                                           record_property):
    from attune_harness import memory_saved_windows as backend
    store = SavedStore(canonical_tmp / 'Lost ACK')
    original = backend._Session.commit_payload
    original_flush = backend._Native.flush
    original_child = backend._Native.child
    committed_directory = {}
    enclosing_parents = []
    def child(native, parent, name, **kwargs):
        handle = original_child(native, parent, name, **kwargs)
        try:
            if name == store.root.name and kwargs.get('directory'):
                identity = native.api.metadata(parent)[0]['identity']
                if identity not in enclosing_parents:
                    enclosing_parents.append(identity)
        except BaseException as primary:
            try:
                native.close(handle)
            except BaseException as secondary:
                raise primary from secondary
            raise
        return handle
    monkeypatch.setattr(backend._Native, 'child', child)
    def commit_then_lose_ack(lease, payload):
        original(lease, payload)
        committed_directory.update(lease.native.api.metadata(lease.directory)[0]['identity'])
        raise SavedError('controlled acknowledgement loss', code='persistence', outcome='uncertain')
    monkeypatch.setattr(backend._Session, 'commit_payload', commit_then_lose_ack)
    with pytest.raises(SavedError) as uncertain:
        store.save(request())
    assert uncertain.value.outcome == 'uncertain'
    monkeypatch.setattr(backend._Session, 'commit_payload', original)
    identifier = store.list({'kind': 'global'})[0]['id']
    class Index:
        def upsert(self, record): pass
    store.index = Index()
    store.revise(identifier, {'content': 'Later revision'}, {'kind': 'global'}, 'later', 1)
    store.index = None
    before = (store.root / 'state.json').read_bytes()
    attempted_commit, admission = [], []
    def state_commit_barrier_still_refuses(native, handle):
        entry, _, _ = native.api.metadata(handle)
        if entry['kind'] == 'file' or entry['identity'] == committed_directory:
            attempted_commit.append(entry['identity'])
            return 0, 1
        assert entry['kind'] == 'directory' and entry['identity'] in enclosing_parents
        status = original_flush(native, handle)
        admission.append({'identity': entry['identity'], 'flags': 0,
                          'returned_ntstatus': status[0], 'io_status': status[1]})
        return status
    monkeypatch.setattr(backend._Native, 'flush', state_commit_barrier_still_refuses)
    def no_write(native, handle, payload):
        attempted_commit.append('write')
        raise OSError('replay cannot write state')
    def no_rename(api, source, parent, target):
        attempted_commit.append('rename')
        raise OSError('replay cannot rename state')
    monkeypatch.setattr(backend._Native, 'write_all', no_write)
    monkeypatch.setattr(backend.Native, 'rename', no_rename)
    try:
        replay = store.save(request())
    finally:
        record_property('saved_replay_admission_only', json.dumps({
            'commit_barriers_attempted': attempted_commit, 'enclosing_parent_admission': admission,
            'prior_commit_barrier_reestablished': False}, ensure_ascii=True, allow_nan=False))
    assert replay['record']['revision'] == 1
    assert len(replay['record']['history']) == 1
    assert replay['index_status'] == 'indexed'
    assert store.get(identifier, {'kind': 'global'})['revision'] == 2
    assert (store.root / 'state.json').read_bytes() == before
    assert attempted_commit == []
    assert admission and all(row['returned_ntstatus'] == row['io_status'] == 0 for row in admission)
    def admission_still_refuses(native, handle):
        entry, _, _ = native.api.metadata(handle)
        assert entry['kind'] == 'directory' and entry['identity'] in enclosing_parents
        return 0, 1
    monkeypatch.setattr(backend._Native, 'flush', admission_still_refuses)
    with pytest.raises(SavedError) as refused_admission:
        store.save(request())
    assert refused_admission.value.code == 'storage'
    assert refused_admission.value.outcome == 'not_committed'
    assert (store.root / 'state.json').read_bytes() == before
    assert attempted_commit == []


def test_native_inherited_nonprivate_root_refused_before_lock(canonical_tmp):
    root = canonical_tmp / 'Inherited root'
    root.mkdir()
    with pytest.raises(SavedError):
        SavedStore(root).list({'kind': 'global'})
    assert not (root / '.saved.lock').exists()
    assert not (root / 'state.json').exists()


def test_native_hardlinked_state_refused(canonical_tmp):
    root = canonical_tmp / 'Hardlink refusal'
    store = SavedStore(root)
    store.save(request())
    original = (root / 'state.json').read_bytes()
    os.link(root / 'state.json', canonical_tmp / 'external-state-alias')
    with pytest.raises(SavedError):
        store.list({'kind': 'global'})
    assert (root / 'state.json').read_bytes() == original


def test_native_alternate_stream_refused(canonical_tmp):
    root = canonical_tmp / 'ADS refusal'
    store = SavedStore(root)
    store.save(request())
    before = (root / 'state.json').read_bytes()
    Path(str(root / 'state.json') + ':extra').write_bytes(b'extra stream')
    with pytest.raises(SavedError):
        store.list({'kind': 'global'})
    assert (root / 'state.json').read_bytes() == before


def test_native_directory_link_refused_without_following(canonical_tmp):
    target = canonical_tmp / 'target'
    target.mkdir()
    link = canonical_tmp / 'link'
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError as exc:
        if os.name == 'nt' and exc.winerror == 1314:
            pytest.skip('current Windows token cannot create a symlink (WinError1314)')
        raise
    with pytest.raises(SavedError):
        SavedStore(link / 'store').list({'kind': 'global'})
    assert not (target / 'store').exists()


def test_native_oversize_and_corrupt_state_refuse_without_replacement(canonical_tmp):
    root = canonical_tmp / 'Corruption refusal'
    store = SavedStore(root)
    store.save(request())
    state = root / 'state.json'
    with state.open('r+b') as stream:
        stream.truncate(MAX_STATE + 1)
    with pytest.raises(SavedError):
        store.list({'kind': 'global'})
    state.write_bytes(b'not JSON')
    with pytest.raises(SavedError) as corrupt:
        store.save(request('different'))
    assert corrupt.value.code == 'corrupt'
    assert state.read_bytes() == b'not JSON'


def test_native_index_restart_and_old_replay_cannot_resurrect(canonical_tmp):
    class Index:
        def __init__(self):
            self.fail, self.records = True, {}
        def upsert(self, record):
            if self.fail:
                raise RuntimeError('index unavailable')
            self.records[record['id']] = record
        def remove(self, identity, scope):
            self.records.pop(identity, None)
    index = Index()
    root = canonical_tmp / 'Index boundary'
    first = SavedStore(root, index).save(request())
    assert first['index_status'] == 'pending'
    assert SavedStore(root).get(first['record']['id'], {'kind': 'global'})['index_status'] == 'pending'
    index.fail = False
    store = SavedStore(root, index)
    assert store.reindex({'kind': 'global'})['index_status'] == 'indexed'
    store.forget(first['record']['id'], {'kind': 'global'}, 'forget', 1)
    assert not index.records
    replay = store.save(request())
    assert replay['record']['revision'] == 1 and replay['index_status'] == 'indexed'
    assert not index.records
    assert store.list({'kind': 'global'}) == []


def test_native_saved_task_observes_real_owner_without_writing_it(canonical_tmp, case):
    from attune_harness.task_contract import create_task
    owner = create_task(case[0].parent, case[1], goal='Retain saved task intent', directory=case[2])
    scope = {'kind': 'project', 'project': owner['request']['project_root']}
    value = request('linked-task', kind='task')
    value.update(scope=scope, execution={'directory': str(case[2]),
                                       'task_id': owner['request']['task_id']})
    store = SavedStore(canonical_tmp / 'Linked saved intent')
    before = (case[2] / 'record.json').read_bytes()
    saved = store.save(value)['record']
    assert store.get(saved['id'], scope)['execution_status'] == 'draft'
    assert 'execution_status' not in saved
    assert (case[2] / 'record.json').read_bytes() == before
    with pytest.raises(SavedError):
        store.complete(saved['id'], scope, 'complete-linked', 1)


def parent_handle_facts(native, handle):
    """Test-only query of the actual production handle; no extra handle is opened."""
    w = native.w
    class BasicInformation(ctypes.Structure):
        _fields_ = [('Attributes', w.ULONG), ('GrantedAccess', w.ULONG),
                    ('HandleCount', w.ULONG), ('PointerCount', w.ULONG),
                    ('Reserved', w.ULONG * 10)]
    query = native.api.nt.NtQueryObject
    query.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.ULONG,
                      ctypes.POINTER(w.ULONG)]
    query.restype = ctypes.c_long
    value, returned = BasicInformation(), w.ULONG()
    value.GrantedAccess = 0xDEADBEEF
    status = query(handle, 0, ctypes.byref(value), ctypes.sizeof(value),
                   ctypes.byref(returned)) & 0xffffffff
    assert status == 0 and returned.value == ctypes.sizeof(value)
    # FILE_WRITE_DATA, READ_CONTROL, SYNCHRONIZE and read/list/attribute access.
    required = 0x00120083
    assert value.GrantedAccess & required == required
    entry, _, _ = native.api.metadata(handle)
    assert entry['kind'] == 'directory'
    return {'query_ntstatus': status, 'query_bytes': returned.value,
            'granted_access': value.GrantedAccess, 'required_access': required,
            'identity': entry['identity'], 'security_sha256': entry['security_sha256']}


def test_native_managed_parent_publication_rights_status_identity(canonical_tmp, monkeypatch,
                                                                  record_property):
    from attune_harness import memory_saved_windows as backend
    names = ('Fresh managed suffix', 'Private saved store')
    root = canonical_tmp / names[0] / names[1]
    assert not root.parent.exists()
    phase, links, flushes = [0], {}, []
    original_child, original_flush = backend._Native.child, backend._Native.flush

    def child(native, parent, name, **kwargs):
        handle = original_child(native, parent, name, **kwargs)
        try:
            if name in names and kwargs.get('directory'):
                parent_entry, _, _ = native.api.metadata(parent)
                entry, _, _ = native.api.metadata(handle)
                links[phase[0], name] = {'name': name, 'parent_identity': parent_entry['identity'],
                    'child_identity': entry['identity'], 'child_private': native.is_private(handle),
                    'handle': handle}
        except BaseException as primary:
            try:
                native.close(handle)
            except BaseException as secondary:
                raise primary from secondary
            raise
        return handle

    def flush(native, handle):
        entry, _, _ = native.api.metadata(handle)
        if entry['kind'] != 'directory':
            return original_flush(native, handle)
        row = {'phase': phase[0], 'before': parent_handle_facts(native, handle),
               'flags': 0, 'returned_ntstatus': None, 'io_status': None,
               'after': None, 'children_after': []}
        flushes.append(row)  # Preserve the first partial row if a later check fails.
        status = original_flush(native, handle)
        row['returned_ntstatus'], row['io_status'] = status
        after, _, _ = native.api.metadata(handle)
        row['after'] = {'identity': after['identity'], 'security_sha256': after['security_sha256']}
        for (round_number, _), link in links.items():
            if round_number == phase[0] and link['parent_identity'] == entry['identity']:
                selected, _, _ = native.api.metadata(link['handle'])
                row['children_after'].append({'name': link['name'], 'identity': selected['identity'],
                                              'private': native.is_private(link['handle'])})
        return status

    monkeypatch.setattr(backend._Native, 'child', child)
    monkeypatch.setattr(backend._Native, 'flush', flush)
    try:
        for round_number in (1, 2):
            phase[0] = round_number
            with backend.locked(root):
                pass
            selected_links = [links[round_number, name] for name in names]
            required_parents = [link['parent_identity'] for link in selected_links]
            relevant = [row for row in flushes if row['phase'] == round_number
                        and row['before']['identity'] in required_parents]
            assert [row['before']['identity'] for row in relevant] == required_parents
            for link, row in zip(selected_links, relevant):
                assert link['child_private']
                assert type(row['returned_ntstatus']) is int and row['returned_ntstatus'] == 0
                assert type(row['io_status']) is int and row['io_status'] == 0
                assert row['before']['identity'] == row['after']['identity']
                assert row['before']['security_sha256'] == row['after']['security_sha256']
                assert row['children_after'] == [{'name': link['name'],
                    'identity': link['child_identity'], 'private': True}]
    finally:
        # Opaque object identities/rights/statuses only; no SID, path or environment values.
        public_links = [{'phase': key[0], **{k: v for k, v in link.items() if k != 'handle'}}
                        for key, link in links.items()]
        record_property('saved_managed_parent_publication', json.dumps({
            'external_prefix': 'canonical fixture prefix is an explicit provisioning premise',
            'links': public_links, 'flushes': flushes}, ensure_ascii=True, allow_nan=False))


_REVISE = """
import json, sys
from attune_harness.memory_saved import SavedStore, SavedError
print(json.dumps({'ready': True}), flush=True)
assert sys.stdin.readline() == 'go\\n'
value = json.loads(sys.argv[2])
try:
    result = SavedStore(sys.argv[1]).revise(value['id'], value['changes'], value['scope'],
                                           value['request_id'], value['expected_revision'])
except SavedError as error:
    if error.code != 'conflict':
        raise
    result = {'outcome': 'conflict'}
else:
    result = {'outcome': 'committed', 'result': result}
print(json.dumps(result, ensure_ascii=True), flush=True)
"""


def next_child_line(child, timeout=30):
    result = queue.Queue()
    threading.Thread(target=lambda: result.put(child.stdout.readline()), daemon=True).start()
    return result.get(timeout=timeout)


def test_native_competing_expected_revision_has_one_winner(canonical_tmp, record_property):
    root = canonical_tmp / 'Revision contenders'
    store = SavedStore(root)
    first = store.save(request())['record']
    children, outcomes, exits = [], [], []
    try:
        for label in ('A', 'B'):
            value = {'id': first['id'], 'scope': {'kind': 'global'},
                     'changes': {'content': label}, 'request_id': 'contender-' + label,
                     'expected_revision': 1}
            child = subprocess.Popen([sys.executable, '-I', '-c', _REVISE, str(root),
                json.dumps(value, ensure_ascii=True)], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            children.append(child)
        for child in children:
            assert json.loads(next_child_line(child)) == {'ready': True}
        for child in children:
            child.stdin.write('go\n')
            child.stdin.flush()
        for child in children:
            stdout, stderr = child.communicate(timeout=30)
            exits.append(child.returncode)
            assert child.returncode == 0, stderr
            outcomes.append(json.loads(stdout))
        assert sorted(row['outcome'] for row in outcomes) == ['committed', 'conflict']
        winner = next(row['result']['record'] for row in outcomes if row['outcome'] == 'committed')
        observed = store.get(first['id'], {'kind': 'global'})
        assert observed['revision'] == winner['revision'] == 2
        assert observed['content'] == winner['content']
        assert len(observed['history']) == 2
        state = json.loads((root / 'state.json').read_bytes())
        assert len(state['operations']) == 2
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.wait(timeout=10)
        record_property('saved_expected_revision_competition', json.dumps({
            'exits': exits, 'outcomes': [row.get('outcome') for row in outcomes]}, ensure_ascii=True))


_KILL_REVISION = """
import json, sys
from attune_harness import memory_saved_windows as backend
from attune_harness.memory_saved import SavedStore
root, stage, value = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
prepared_identity = []
original_child = backend._Native.child
original_flush = backend._Native.flush
original_rename = backend.Native.rename
def checkpoint(facts):
    print(json.dumps({'checkpoint': stage, **facts}, ensure_ascii=True), flush=True)
    sys.stdin.readline()  # Parent terminates this process; no descendants are created.
    raise RuntimeError('the kill checkpoint must not be resumed')
def child(native, parent, name, **kwargs):
    handle = original_child(native, parent, name, **kwargs)
    if kwargs.get('create') and name.startswith('.saved-'):
        entry = native.api.metadata(handle)[0]
        prepared_identity.append(entry['identity'])
        if stage == 'preparation':
            checkpoint({'prepared_identity': entry['identity'], 'private': native.is_private(handle)})
    return handle
def flush(native, handle):
    result = original_flush(native, handle)
    entry = native.api.metadata(handle)[0]
    if stage == 'file_flush' and entry['identity'] in prepared_identity:
        assert type(result[0]) is int and result[0] == 0
        assert type(result[1]) is int and result[1] == 0
        checkpoint({'identity': entry['identity'], 'flags': 0,
                    'returned_ntstatus': result[0], 'io_status': result[1]})
    return result
def rename(api, source, parent, target):
    result = original_rename(api, source, parent, target)
    if stage == 'rename':
        assert result == {'returned_ntstatus': 0, 'io_status_block_status': 0}
        checkpoint({'rename': result, 'identity': api.metadata(source)[0]['identity']})
    return result
backend._Native.child = child
backend._Native.flush = flush
backend.Native.rename = rename
result = SavedStore(root).revise(value['id'], value['changes'], value['scope'],
                                value['request_id'], value['expected_revision'])
if stage == 'pre_response':
    checkpoint({'revision': result['record']['revision'], 'history': len(result['record']['history'])})
print(json.dumps(result, ensure_ascii=True), flush=True)
"""


def expected_revision_bytes(before, value):
    """Use the unchanged common owner to produce the atomic byte after-image."""
    class Bytes:
        raw = before
        def read_payload(self): return self.raw
        def commit_payload(self, payload): self.raw = payload
    memory = Bytes()
    owner = object.__new__(SavedStore)
    owner.index = None
    @contextmanager
    def held(): yield memory
    owner._locked = held
    owner.revise(value['id'], value['changes'], value['scope'],
                 value['request_id'], value['expected_revision'])
    return memory.raw


def _kill_error_facts(error):
    """Bound the retained exception chain; preserve native numbers, not paths."""
    facts, seen = [], set()
    for _ in range(4):
        if error is None or id(error) in seen:
            break
        seen.add(id(error))
        facts.append({'type': type(error).__name__, 'errno': getattr(error, 'errno', None),
                      'winerror': getattr(error, 'winerror', None),
                      'code': getattr(error, 'code', None),
                      'outcome': getattr(error, 'outcome', None)})
        cause = error.__cause__
        error = (cause if cause is not None else
                 None if error.__suppress_context__ else error.__context__)
    return facts


def _kill_read_failure_diagnostic(root, store, first, value, before, after):
    """Observe only after the original raw read failed; this cannot qualify it."""
    from attune_harness.memory_saved_windows import locked
    from attune_harness.windows_effects import Native
    import hashlib

    def bytes_facts(raw):
        return {'length': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                'matches_before': raw == before, 'matches_after': raw == after}

    report = {'claim': 'post-failure diagnostic; ordered observations change timing; '
                        'no immediate-read, power-loss or restored durability claim',
              'native_open_attempts': [], 'product_recovery': {}}
    try:
        api = Native()
    except BaseException as error:
        report['native_setup_error'] = _kill_error_facts(error)
        return report
    # Same requested read/query access and OPEN_EXISTING; only sharing differs.
    # Both are single acquisitions AFTER the failed CRT read, never its retries.
    for share in (3, 7):
        row = {'desired_access': 0x00120081, 'share': share,
               'creation_disposition': 3, 'flags': 0x00200000,
               'open_success': False, 'open_winerror': None, 'close_success': None}
        report['native_open_attempts'].append(row)
        handle = None
        try:
            ctypes.set_last_error(0)
            handle = api.k.CreateFileW(str(root / 'state.json'), row['desired_access'],
                                      share, None, 3, row['flags'], None)
            if handle in (None, ctypes.c_void_p(-1).value):
                row['open_winerror'] = ctypes.get_last_error()
                handle = None
                continue
            row['open_success'] = True
            standard = api.info(handle, api.Standard, 1)
            row['standard'] = {'delete_pending': bool(standard.DeletePending),
                               'directory': bool(standard.Directory),
                               'links': int(standard.NumberOfLinks),
                               'size': int(standard.EndOfFile)}
            entry, size, _ = api.metadata(handle)
            row['before_metadata'] = entry
            if not 0 <= size <= MAX_STATE:
                raise ValueError('diagnostic state exceeds existing bound')
            raw = api.read(handle, size, limit=MAX_STATE)
            later, later_size, _ = api.metadata(handle)
            row['after_metadata'] = later
            row['metadata_stable'] = entry == later and size == later_size
            row['bytes'] = bytes_facts(raw)
        except BaseException as error:
            row['error'] = _kill_error_facts(error)
        finally:
            if handle is not None:
                try:
                    ctypes.set_last_error(0)
                    row['close_success'] = bool(api.k.CloseHandle(handle))
                    if not row['close_success']:
                        row['close_winerror'] = ctypes.get_last_error()
                except BaseException as error:
                    row['close_success'] = False
                    row['close_error'] = _kill_error_facts(error)
        if handle is not None and row['close_success'] is not True:
            report['stopped_after_unconfirmed_close'] = True
            report['unobserved'] = {'remaining_native_share_modes': [7] if share == 3 else [],
                                    'production_reads': True}
            return report  # No close retry or operation after the unresolved handle.
    # Production admission may flush enclosing parents and takes the real lock.
    # Record it separately; it cannot establish the earlier raw-read predicate.
    recovery = report['product_recovery']
    recovery['admission_may_republish_parents'] = True
    try:
        with locked(root) as lease:
            raw = lease.read_payload()
        recovery['before_retry_bytes'] = bytes_facts(raw)
        visible = store.get(first['id'], {'kind': 'global'})
        recovery['visible_revision'] = visible['revision']
        recovery['same_id_write_and_replay_observed'] = False
    except BaseException as error:
        recovery['error'] = _kill_error_facts(error)
    return report


def _prepare_kill_state_oracle(root):
    """Prepare one read-only observer before the writer reaches its checkpoint."""
    from attune_harness.windows_effects import Native
    api = Native()  # Bind the fixed ABI before starting the writer, never on failure.
    state_path = ctypes.create_unicode_buffer(str(root / 'state.json'))
    buffer, count = ctypes.create_string_buffer(MAX_STATE + 1), api.w.DWORD()
    invalid = ctypes.c_void_p(-1).value
    report = {'claim': 'first post-wait independent native whole-byte observation; '
                       'no production admission, retry, barrier or power-loss claim',
              'desired_access': 0x00120081, 'share': 7, 'creation_disposition': 3,
              'flags': 0x00200000, 'open_attempts': 0, 'close_success': None}

    def read(stage, checkpoint):
        handle, primary = None, None
        try:
            report['open_attempts'] += 1
            assert report['open_attempts'] == 1
            ctypes.set_last_error(0)
            handle = api.k.CreateFileW(state_path, report['desired_access'], report['share'],
                                      None, 3, report['flags'], None)
            if handle in (None, invalid):
                code, handle = ctypes.get_last_error(), None
                raise ctypes.WinError(code)
            # metadata() rejects reparse/delete-pending/ADS and multiply linked files;
            # it queries kind, identity, attributes and complete owner/DACL security.
            entry, size, _ = api.metadata(handle)
            report['before_metadata'], report['before_size'] = entry, size
            assert entry['kind'] == 'file' and entry['links'] == 1
            assert not entry['attributes'] & 0x400
            assert 0 <= size <= MAX_STATE
            if stage == 'rename':
                assert entry['identity'] == checkpoint['identity']
            # The newly acquired synchronous handle starts at byte zero. One bounded
            # read includes an extra byte to detect growth; there is no short-read retry.
            count.value = 0
            ctypes.set_last_error(0)
            if not api.k.ReadFile(handle, buffer, size + 1, ctypes.byref(count), None):
                raise ctypes.WinError(ctypes.get_last_error())
            report['read_requested_bytes'], report['read_bytes'] = size + 1, count.value
            assert count.value == size
            raw = buffer.raw[:size]
            later, later_size, _ = api.metadata(handle)
            report['after_metadata'], report['after_size'] = later, later_size
            assert later == entry and later_size == size
            return raw
        except BaseException as error:
            primary = error
            report['error'] = _kill_error_facts(error)
            raise
        finally:
            if handle is not None:
                try:
                    ctypes.set_last_error(0)
                    report['close_success'] = bool(api.k.CloseHandle(handle))
                    if not report['close_success']:
                        raise ctypes.WinError(ctypes.get_last_error())
                except BaseException as error:
                    report['close_success'] = False
                    report['close_error'] = _kill_error_facts(error)
                    if primary is not None:
                        raise primary from error
                    raise  # No second close, acquisition or recovery after uncertainty.
    return read, report


@pytest.mark.parametrize('stage', ['preparation', 'file_flush', 'rename', 'pre_response'])
def test_native_kill_boundary_whole_state_and_same_id_recovery(canonical_tmp, stage, record_property):
    root = canonical_tmp / ('Kill ' + stage)
    store = SavedStore(root)
    first = store.save(request())['record']
    before = (root / 'state.json').read_bytes()
    value = {'id': first['id'], 'scope': {'kind': 'global'},
             'changes': {'content': 'Recovered revision 雪'}, 'request_id': 'kill-' + stage,
             'expected_revision': 1}
    after = expected_revision_bytes(before, value)
    first_read, oracle_report = _prepare_kill_state_oracle(root)
    child = subprocess.Popen([sys.executable, '-I', '-c', _KILL_REVISION, str(root), stage,
        json.dumps(value, ensure_ascii=True)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True)
    checkpoint, exit_code = None, None
    try:
        checkpoint = json.loads(next_child_line(child))
        assert checkpoint['checkpoint'] == stage
        child.kill()
        child.wait(timeout=10)
        exit_code = child.returncode
        assert exit_code != 0
        try:
            observed = first_read(stage, checkpoint)
        except BaseException:
            try:
                record_property('saved_native_kill_first_oracle', json.dumps(
                    oracle_report, ensure_ascii=True, allow_nan=False))
            except BaseException:
                pass  # Reporting must not replace the first oracle failure.
            raise
        record_property('saved_native_kill_first_oracle', json.dumps(
            oracle_report, ensure_ascii=True, allow_nan=False))
        expected = before if stage in ('preparation', 'file_flush') else after
        assert observed == expected
        # The real common decoder must accept the whole persisted state.
        visible = store.get(first['id'], {'kind': 'global'})
        assert visible['revision'] == (1 if expected == before else 2)
        recovered = store.revise(value['id'], value['changes'], value['scope'],
                                 value['request_id'], value['expected_revision'])
        assert recovered['record']['revision'] == 2
        assert len(recovered['record']['history']) == 2
        replay = store.revise(value['id'], value['changes'], value['scope'],
                              value['request_id'], value['expected_revision'])
        assert replay == recovered
        assert (root / 'state.json').read_bytes() == after
        assert sum(row['request_id'] == value['request_id']
                   for row in replay['record']['history']) == 1
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=10)
        stdout, stderr = child.communicate(timeout=10)
        record_property('saved_native_kill_boundary', json.dumps({
            'stage': stage, 'checkpoint': checkpoint, 'exit_code': exit_code,
            'remaining_stdout': stdout, 'stderr': stderr,
            'claim': 'process termination only; no power-loss or new replay durability claim'},
            ensure_ascii=True, allow_nan=False))


def test_native_saved_task_opportunity_review_lifecycle(canonical_tmp):
    store = SavedStore(canonical_tmp / 'Review checkpoint task')
    pending = {'status': 'pending', 'goal': 'Preserve the task', 'progress': 'Intent saved',
               'evidence': ['explicit caller reference'], 'reason': 'Review remains',
               'next_action': 'Review the retained checkpoint'}
    value = request('review-save', kind='task')
    value['opportunity_review'] = pending
    first = store.save(value)['record']
    assert store.get(first['id'], {'kind': 'global'})['opportunity_review'] == pending
    completed = {'status': 'completed', 'goal': 'Preserve the task', 'progress': 'Reviewed',
                 'evidence': ['explicit caller reference'],
                 'outcome': {'kind': 'no_change', 'summary': 'No new opportunity'}}
    revised = store.revise(first['id'], {'opportunity_review': completed},
                           {'kind': 'global'}, 'review-complete', 1)['record']
    assert revised['revision'] == 2 and revised['opportunity_review'] == completed
    assert value['opportunity_review'] == pending
    assert 'completed' in store.get(first['id'], {'kind': 'global'})['opportunity_review_notice']
    store.forget(first['id'], {'kind': 'global'}, 'review-withdraw', 2)
    withdrawn = store.get(first['id'], {'kind': 'global'}, include_withdrawn=True)
    assert withdrawn['revision'] == 3 and withdrawn['opportunity_review'] == completed
    assert 'withdrawn' in withdrawn['opportunity_review_notice']
    assert len(withdrawn['history']) == 3
