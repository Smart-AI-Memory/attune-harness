"""Disposable T2 experiment; never a production saved-storage backend.

Run from an installed wheel: python -I windows_saved_store_proof.py --output DIR.
The observation runner may succeed while durability equivalence remains blocked.
No network, provider, repository configuration or existing store is accessed.
"""

import argparse
from contextlib import contextmanager, nullcontext
import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from uuid import uuid4

LIMIT = 8 * 1024 * 1024
PROCESS_SECONDS = 120
LOCK_SECONDS = 2.0
STAGES = ('prepared', 'file_flushed', 'renamed', 'namespace_flushed', 'before_response')
STATUS_MISSING = 0xC0000034
STATUS_COLLISION = 0xC0000035
STATUS_SHARING = 0xC0000043
SCRIPT = Path(__file__).resolve()


def encode(value):
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False,
                     sort_keys=True, separators=(',', ':')).encode('utf-8')
    if len(raw) > LIMIT:
        raise ValueError('Proof state exceeds 8 MiB')
    return raw


def save_json(path, value):
    path.write_bytes(encode(value) + b'\n')


def read_json(path):
    with path.open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError('Proof receipt exceeds 8 MiB')
    return json.loads(raw)


def assert_state(state):
    if (set(state) != {'proof_schema', 'records', 'history', 'operations'}
            or type(state['proof_schema']) is not int or state['proof_schema'] != 1):
        raise ValueError('Not a synthetic proof state')
    keys = list(state['operations'])
    if set(state['records']) != set(keys) or len(state['history']) != len(keys):
        raise ValueError('Synthetic state/history/replay disagree')
    if set(state['history']) != set(keys) or len(set(state['history'])) != len(keys):
        raise ValueError('Synthetic history has duplicate or missing operations')
    for key in keys:
        if state['records'][key] != state['operations'][key]:
            raise ValueError('Synthetic replay result differs')


def receipt_gate(observations):
    """An observation is never a self-issued production durability approval."""
    failures = [row['where'] for row in observations
                if row['returned_ntstatus'] != 0 or row['io_status'] != 0]
    return {'status': 'blocked' if failures else 'requires_semantic_review',
            'native_flush_refusals': failures,
            'documented_equivalence': 'not_established_by_experiment',
            'power_loss_tested': False, 'production_port_allowed': False}


def validate_token(facts):
    if (facts['administrators_enabled'] or facts['integrity_sid'] != 'S-1-16-8192'
            or set(facts['enabled_privileges']) - {'SeChangeNotifyPrivilege'}):
        raise ValueError('The proof did not run with its restricted primary-token profile')


def validate_receipt(result):
    if result['status'] != 'observations_complete' or result['proof_schema'] != 1:
        raise ValueError('Native proof observations are incomplete')
    validate_token(result['token'])
    if result['token_profile'] != 'restricted-primary-medium-v1':
        raise ValueError('Unknown native proof token profile')
    if result['platform']['filesystem'] != 'NTFS':
        raise ValueError('Native proof did not admit NTFS')
    if result['paid_model_calls'] != 0 or result['provider_network_calls'] != 0:
        raise ValueError('This proof does not authorize network or model calls')
    if result['production_source_changed'] is not False:
        raise ValueError('A disposable proof cannot change production storage')
    flushes = result['flush_observations']
    if {row['where'] for row in flushes} != {
            'prepared_file', 'replaced_file', 'parent_namespace', 'store_creation_parent'}:
        raise ValueError('Missing required native file or namespace flush observations')
    if result['durability_gate'] != receipt_gate(flushes):
        raise ValueError('Native durability conclusion differs from its observations')
    locks = result['locking']
    if (locks['held_contender_acquired'] or not locks['released_contender_acquired']
            or locks['delete_access_ntstatus'] != STATUS_SHARING
            or not LOCK_SECONDS <= locks['bounded_contender_seconds'] < LOCK_SECONDS + 5):
        raise ValueError('Native lock ownership or bounded contention failed')
    cases = result['concurrency']
    if len(cases) != 2 or {case['identical_requests'] for case in cases} != {False, True}:
        raise ValueError('Missing concurrent writer/replay cases')
    for case in cases:
        if (case['writers'] != 8 or case['history_count_including_seed'] != (2 if case['identical_requests'] else 9)
                or case['replayed_count'] != (7 if case['identical_requests'] else 0)):
            raise ValueError('Native concurrent requests duplicated or lost commits')
        for token in case['tokens']:
            validate_token(token)
        if len(case['tokens']) != 8:
            raise ValueError('Missing native child token observations')
    crashes = result['process_crashes']
    if len(crashes) != len(STAGES) or {case['stage'] for case in crashes} != set(STAGES):
        raise ValueError('Missing native process-crash boundary')
    for case in crashes:
        if (case['power_loss_tested'] is not False or case['history_count_after_retry'] != 2
                or case['observed_after'] != (case['stage'] in STAGES[2:])):
            raise ValueError('Native process-crash/replay observation is inconsistent')


class ProofNative:
    def __init__(self, event_path=None):
        if os.name != 'nt':
            raise RuntimeError('The proof requires native Windows')
        from ctypes import wintypes as w
        from attune_harness.windows_effects import Native
        self.w, self.api = w, Native()
        self.k, self.a = self.api.k, self.api.a
        self.event_path = event_path

        class SidAndAttributes(ctypes.Structure):
            _fields_ = [('Sid', ctypes.c_void_p), ('Attributes', w.DWORD)]

        class Groups(ctypes.Structure):
            _fields_ = [('Count', w.DWORD), ('Groups', SidAndAttributes * 1)]

        class Luid(ctypes.Structure):
            _fields_ = [('LowPart', w.DWORD), ('HighPart', w.LONG)]

        class Privilege(ctypes.Structure):
            _fields_ = [('Luid', Luid), ('Attributes', w.DWORD)]

        class Privileges(ctypes.Structure):
            _fields_ = [('Count', w.DWORD), ('Privileges', Privilege * 1)]

        class Overlapped(ctypes.Structure):
            _fields_ = [('Internal', ctypes.c_size_t), ('InternalHigh', ctypes.c_size_t),
                        ('Offset', w.DWORD), ('OffsetHigh', w.DWORD), ('hEvent', w.HANDLE)]

        class Startup(ctypes.Structure):
            _fields_ = [('cb', w.DWORD), ('lpReserved', w.LPWSTR), ('lpDesktop', w.LPWSTR),
                        ('lpTitle', w.LPWSTR), ('dwX', w.DWORD), ('dwY', w.DWORD),
                        ('dwXSize', w.DWORD), ('dwYSize', w.DWORD), ('dwXCountChars', w.DWORD),
                        ('dwYCountChars', w.DWORD), ('dwFillAttribute', w.DWORD),
                        ('dwFlags', w.DWORD), ('wShowWindow', w.WORD), ('cbReserved2', w.WORD),
                        ('lpReserved2', ctypes.c_void_p), ('hStdInput', w.HANDLE),
                        ('hStdOutput', w.HANDLE), ('hStdError', w.HANDLE)]

        class Process(ctypes.Structure):
            _fields_ = [('hProcess', w.HANDLE), ('hThread', w.HANDLE),
                        ('dwProcessId', w.DWORD), ('dwThreadId', w.DWORD)]

        self.SidAndAttributes, self.Groups = SidAndAttributes, Groups
        self.Privilege, self.Privileges = Privilege, Privileges
        self.Overlapped, self.Startup, self.Process = Overlapped, Startup, Process
        ptr = ctypes.c_void_p
        self.bind(self.k.GetCurrentProcess, [], w.HANDLE)
        self.bind(self.a.OpenProcessToken, [w.HANDLE, w.DWORD, ctypes.POINTER(w.HANDLE)], w.BOOL)
        self.bind(self.a.GetTokenInformation, [w.HANDLE, ctypes.c_int, ptr, w.DWORD,
                                             ctypes.POINTER(w.DWORD)], w.BOOL)
        self.bind(self.a.ConvertSidToStringSidW, [ptr, ctypes.POINTER(ptr)], w.BOOL)
        self.bind(self.a.ConvertStringSidToSidW, [w.LPCWSTR, ctypes.POINTER(ptr)], w.BOOL)
        self.bind(self.a.LookupPrivilegeNameW, [w.LPCWSTR, ptr, w.LPWSTR,
                                               ctypes.POINTER(w.DWORD)], w.BOOL)
        self.bind(self.a.CreateRestrictedToken, [w.HANDLE, w.DWORD, w.DWORD, ptr,
                  w.DWORD, ptr, w.DWORD, ptr, ctypes.POINTER(w.HANDLE)], w.BOOL)
        self.bind(self.a.SetTokenInformation, [w.HANDLE, ctypes.c_int, ptr, w.DWORD], w.BOOL)
        self.bind(self.a.GetLengthSid, [ptr], w.DWORD)
        self.bind(self.a.CreateProcessAsUserW, [w.HANDLE, w.LPCWSTR, w.LPWSTR, ptr, ptr,
                  w.BOOL, w.DWORD, ptr, w.LPCWSTR, ctypes.POINTER(Startup),
                  ctypes.POINTER(Process)], w.BOOL)
        self.bind(self.k.WaitForSingleObject, [w.HANDLE, w.DWORD], w.DWORD)
        self.bind(self.k.TerminateProcess, [w.HANDLE, w.UINT], w.BOOL)
        self.bind(self.k.GetExitCodeProcess, [w.HANDLE, ctypes.POINTER(w.DWORD)], w.BOOL)
        self.bind(self.k.ResumeThread, [w.HANDLE], w.DWORD)
        self.bind(self.a.ConvertStringSecurityDescriptorToSecurityDescriptorW,
                  [w.LPCWSTR, w.DWORD, ctypes.POINTER(ptr), ctypes.POINTER(w.ULONG)], w.BOOL)
        self.bind(self.a.GetSecurityDescriptorOwner,
                  [ptr, ctypes.POINTER(ptr), ctypes.POINTER(w.BOOL)], w.BOOL)
        self.bind(self.k.LockFileEx, [w.HANDLE, w.DWORD, w.DWORD, w.DWORD, w.DWORD,
                                     ctypes.POINTER(Overlapped)], w.BOOL)
        self.bind(self.k.UnlockFileEx, [w.HANDLE, w.DWORD, w.DWORD, w.DWORD,
                                       ctypes.POINTER(Overlapped)], w.BOOL)
        self.bind(self.api.nt.NtFlushBuffersFileEx, [w.HANDLE, w.ULONG, ptr, w.ULONG,
                                                   ctypes.POINTER(self.api.IoStatus)], ctypes.c_long)

    @staticmethod
    def bind(function, arguments, result):
        function.argtypes, function.restype = arguments, result

    def check(self, result, name):
        self.api._check(result, name)

    def token_data(self, token, kind):
        size = self.w.DWORD()
        self.a.GetTokenInformation(token, kind, None, 0, ctypes.byref(size))
        if not 0 < size.value <= 65536:
            raise RuntimeError('Token information size is unavailable or excessive')
        buffer = ctypes.create_string_buffer(size.value)
        self.check(self.a.GetTokenInformation(token, kind, buffer, len(buffer),
                                              ctypes.byref(size)), 'GetTokenInformation')
        return buffer

    @contextmanager
    def token(self, access=8):
        token = self.w.HANDLE()
        self.check(self.a.OpenProcessToken(self.k.GetCurrentProcess(), access,
                                          ctypes.byref(token)), 'OpenProcessToken')
        with self.api.owned(token):
            yield token

    @contextmanager
    def sid(self, text):
        sid = ctypes.c_void_p()
        self.check(self.a.ConvertStringSidToSidW(text, ctypes.byref(sid)), 'ConvertStringSidToSidW')
        try:
            yield sid
        finally:
            self.k.LocalFree(sid)

    def sid_text(self, sid):
        text = ctypes.c_void_p()
        self.check(self.a.ConvertSidToStringSidW(sid, ctypes.byref(text)), 'ConvertSidToStringSidW')
        try:
            return ctypes.wstring_at(text)
        finally:
            self.k.LocalFree(text)

    def token_facts(self, token_handle=None):
        with self.token() if token_handle is None else nullcontext(token_handle) as token:
            user_buffer = self.token_data(token, 1)
            user = self.sid_text(self.SidAndAttributes.from_buffer_copy(user_buffer).Sid)
            raw = self.token_data(token, 2)
            count = self.w.DWORD.from_buffer_copy(raw).value
            offset = self.Groups.Groups.offset
            if offset + count * ctypes.sizeof(self.SidAndAttributes) > len(raw):
                raise RuntimeError('Malformed token groups')
            groups = [self.SidAndAttributes.from_buffer_copy(raw, offset + i * ctypes.sizeof(self.SidAndAttributes))
                      for i in range(count)]
            admin = [g.Attributes for g in groups if self.sid_text(g.Sid) == 'S-1-5-32-544']
            integrity_buffer = self.token_data(token, 25)
            integrity = self.sid_text(self.SidAndAttributes.from_buffer_copy(integrity_buffer).Sid)
            raw = self.token_data(token, 3)
            count = self.w.DWORD.from_buffer_copy(raw).value
            offset = self.Privileges.Privileges.offset
            if offset + count * ctypes.sizeof(self.Privilege) > len(raw):
                raise RuntimeError('Malformed token privileges')
            enabled = []
            for i in range(count):
                item = self.Privilege.from_buffer_copy(raw, offset + i * ctypes.sizeof(self.Privilege))
                if item.Attributes & 2:
                    size, name = self.w.DWORD(256), ctypes.create_unicode_buffer(256)
                    self.check(self.a.LookupPrivilegeNameW(None, ctypes.byref(item.Luid), name,
                                                           ctypes.byref(size)), 'LookupPrivilegeNameW')
                    enabled.append(name.value)
            elevated = self.w.DWORD.from_buffer_copy(self.token_data(token, 20)).value
        return {'user_sid': user, 'administrators_attributes': admin,
                'administrators_enabled': any(a & 4 and not a & 16 for a in admin),
                'integrity_sid': integrity, 'enabled_privileges': sorted(enabled),
                'token_is_elevated': bool(elevated)}

    def require_standard(self):
        facts = self.token_facts()
        validate_token(facts)
        return facts

    def restricted_run(self, output):
        """Admin setup may only reduce the child token; it performs no file proof."""
        from attune_harness.windows import WindowsJob
        with self.token(0x8B) as original, self.sid('S-1-5-32-544') as admin:
            disabled = self.SidAndAttributes(admin, 0)
            restricted = self.w.HANDLE()
            self.check(self.a.CreateRestrictedToken(original, 1, 1, ctypes.byref(disabled),
                       0, None, 0, None, ctypes.byref(restricted)), 'CreateRestrictedToken')
            with self.api.owned(restricted), self.sid('S-1-16-8192') as medium:
                label = self.SidAndAttributes(medium, 0x20)
                self.check(self.a.SetTokenInformation(restricted, 25, ctypes.byref(label),
                           ctypes.sizeof(label) + self.a.GetLengthSid(medium)), 'SetTokenInformation(Medium)')
                restricted_facts = self.token_facts(restricted)
                validate_token(restricted_facts)
                save_json(output / 'restricted-token.json', restricted_facts)
                with WindowsJob() as job:
                    start, process = self.Startup(), self.Process()
                    # NULL inherits the existing desktop. An empty string asks
                    # Windows to choose another window station, which produced
                    # STATUS_DLL_INIT_FAILED before Python on hosted runners.
                    start.cb, start.lpDesktop = ctypes.sizeof(start), None
                    args = [sys.executable, '-I', str(SCRIPT), '--child', 'run', '--output', str(output)]
                    command = ctypes.create_unicode_buffer(subprocess.list2cmdline(args))
                    # Assign the suspended child before any Python can spawn a
                    # descendant. Only this launcher owns the kill-on-close job.
                    self.check(self.a.CreateProcessAsUserW(restricted, sys.executable, command,
                               None, None, False, 0x08000004, None, str(output),
                               ctypes.byref(start), ctypes.byref(process)), 'CreateProcessAsUserW')
                    with self.api.owned(process.hProcess), self.api.owned(process.hThread):
                        try:
                            self.check(job.api.AssignProcessToJobObject(job.handle, process.hProcess),
                                       'AssignProcessToJobObject(proof)')
                            save_json(output / 'supervisor-job.json', {
                                'assigned_pid': process.dwProcessId,
                                'assigned_while_suspended': True, 'kill_on_job_close': True,
                                'breakaway_allowed': False})
                            if self.k.ResumeThread(process.hThread) == 0xffffffff:
                                raise OSError(ctypes.get_last_error(), 'ResumeThread')
                            if self.k.WaitForSingleObject(process.hProcess, PROCESS_SECONDS * 1000) != 0:
                                self.check(job.api.TerminateJobObject(job.handle, 124), 'TerminateJobObject(proof)')
                                self.k.WaitForSingleObject(process.hProcess, 10000)
                                raise TimeoutError('Restricted proof tree exceeded its bound')
                            code = self.w.DWORD()
                            self.check(self.k.GetExitCodeProcess(process.hProcess, ctypes.byref(code)), 'GetExitCodeProcess')
                            save_json(output / 'supervisor-exit.json', {
                                'exit_code': code.value, 'exit_code_hex': f'{code.value:08x}',
                                'child_python_started': (output / 'child-token.json').is_file()})
                            return code.value
                        except BaseException:
                            # Also covers assignment failure before the child
                            # belongs to the job, while it is still suspended.
                            self.k.TerminateProcess(process.hProcess, 125)
                            self.k.WaitForSingleObject(process.hProcess, 10000)
                            raise

    @contextmanager
    def descriptor(self):
        user = self.token_facts()['user_sid']
        sddl = f'O:{user}D:P(A;OICI;FA;;;{user})(A;OICI;FA;;;SY)'
        descriptor = ctypes.c_void_p()
        self.check(self.a.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1,
                   ctypes.byref(descriptor), None), 'Private security descriptor')
        try:
            yield descriptor
        finally:
            self.k.LocalFree(descriptor)

    def child(self, parent, name, *, create=False, directory=False, lock=False, delete=False):
        from attune_harness.windows_effects import leaf
        leaf(name)
        namebuf = ctypes.create_unicode_buffer(name)
        encoded = name.encode('utf-16-le')
        text = self.api.UnicodeString(len(encoded), ctypes.sizeof(namebuf),
                                      ctypes.cast(namebuf, ctypes.c_void_p))
        with self.descriptor() as sd:
            attrs = self.api.ObjectAttributes(ctypes.sizeof(self.api.ObjectAttributes), parent,
                    ctypes.pointer(text), 0x1040, sd if create else None, None)
            access = 0x00120080 | (7 if directory else 3)
            if not directory and not lock or delete:
                access |= 0x10000
            options = 0x20 | (1 if directory else 0x40) | (0 if create else 0x00200000)
            handle, ios = self.w.HANDLE(), self.api.IoStatus()
            status = self.api.nt.NtCreateFile(ctypes.byref(handle), access, ctypes.byref(attrs),
                     ctypes.byref(ios), None, 0x10 if directory else 0x20,
                     3 if lock else 7, 2 if create else 1, options, None, 0)
        if status != 0:
            raise OSError(status & 0xffffffff, 'Exact proof child open refused')
        return handle

    def private_acl(self, handle):
        descriptor, owner = ctypes.c_void_p(), ctypes.c_void_p()
        defaulted = self.w.BOOL()
        code = self.a.GetSecurityInfo(handle, 1, 5, None, None, None, None, ctypes.byref(descriptor))
        if code:
            raise OSError(code, 'GetSecurityInfo')
        try:
            self.check(self.a.GetSecurityDescriptorOwner(descriptor, ctypes.byref(owner),
                                                        ctypes.byref(defaulted)), 'GetSecurityDescriptorOwner')
            control, revision = self.w.WORD(), self.w.DWORD()
            self.check(self.a.GetSecurityDescriptorControl(descriptor, ctypes.byref(control),
                       ctypes.byref(revision)), 'GetSecurityDescriptorControl')
            present, defaulted, dacl = self.w.BOOL(), self.w.BOOL(), ctypes.c_void_p()
            self.check(self.a.GetSecurityDescriptorDacl(descriptor, ctypes.byref(present),
                       ctypes.byref(dacl), ctypes.byref(defaulted)), 'GetSecurityDescriptorDacl')
            if not present.value or not dacl.value:
                raise RuntimeError('Absent or null private DACL')
            acl = ctypes.cast(dacl, ctypes.POINTER(self.api.Acl)).contents
            user = self.token_facts()['user_sid']
            aces = []
            for i in range(acl.AceCount):
                ace = ctypes.c_void_p()
                self.check(self.a.GetAce(dacl, i, ctypes.byref(ace)), 'GetAce')
                header = self.api.AceHeader.from_address(ace.value)
                sid = self.sid_text(ace.value + 8)
                mask = self.w.DWORD.from_address(ace.value + 4).value
                aces.append({'principal': 'current_user' if sid == user else 'SYSTEM' if sid == 'S-1-5-18' else sid,
                             'type': header.AceType, 'mask': mask, 'flags': header.AceFlags})
            result = {'protected': bool(control.value & 0x1000),
                      'owner_is_current_user': self.sid_text(owner) == user, 'aces': aces}
            if (not result['protected'] or not result['owner_is_current_user'] or len(aces) != 2
                    or {a['principal'] for a in aces} != {'current_user', 'SYSTEM'}
                    or any(a['type'] != 0 or a['mask'] != 0x1F01FF for a in aces)):
                raise RuntimeError('Private ACL does not match its declared principals and rights')
            return result
        finally:
            self.k.LocalFree(descriptor)

    def flush(self, handle, where):
        ios = self.api.IoStatus()
        ios.Status = 0xDEADBEEF
        status = self.api.nt.NtFlushBuffersFileEx(handle, 0, None, 0, ctypes.byref(ios))
        observation = {'where': where, 'flags': 0, 'returned_ntstatus': status & 0xffffffff,
                       'io_status': int(ios.Status or 0) & 0xffffffff}
        if self.event_path is not None:
            # Append observations before later consistency checks can raise.
            # Each process has its own new diagnostic file, never store data.
            with self.event_path.open('ab') as stream:
                stream.write(encode({'pid': os.getpid(), **observation}) + b'\n')
                stream.flush()
                os.fsync(stream.fileno())
        return observation

    def lock_once(self, handle):
        overlap = self.Overlapped()
        if not self.k.LockFileEx(handle, 3, 0, 1, 0, ctypes.byref(overlap)):
            error = ctypes.get_last_error()
            if error == 33:
                return False
            raise OSError(error, 'LockFileEx')
        return True

    @contextmanager
    def locked(self, parent):
        try:
            handle = self.child(parent, '.saved.lock', create=True, lock=True)
        except OSError as exc:
            if exc.errno != STATUS_COLLISION:
                raise
            handle = self.child(parent, '.saved.lock', lock=True)
        with self.api.owned(handle):
            entry, _, _ = self.api.metadata(handle)
            self.private_acl(handle)
            deadline = time.monotonic() + LOCK_SECONDS
            while not self.lock_once(handle):
                if time.monotonic() >= deadline:
                    raise TimeoutError('Proof lock busy after its two-second bound')
                time.sleep(.01)
            try:
                yield handle, entry['identity']
            finally:
                self.check(self.k.UnlockFileEx(handle, 0, 1, 0, ctypes.byref(self.Overlapped())), 'UnlockFileEx')

    def write_unflushed(self, handle, raw):
        if len(raw) > LIMIT:
            raise ValueError('Proof write exceeds 8 MiB')
        for offset in range(0, len(raw), 65536):
            segment = raw[offset:offset + 65536]
            buffer, count = ctypes.create_string_buffer(segment), self.w.DWORD()
            self.check(self.k.WriteFile(handle, buffer, len(segment), ctypes.byref(count), None), 'WriteFile')
            if count.value != len(segment):
                raise RuntimeError('Short proof write')

    def read_state(self, parent):
        try:
            handle = self.child(parent, 'state.json')
        except OSError as exc:
            if exc.errno == STATUS_MISSING:
                return {'proof_schema': 1, 'records': {}, 'history': [], 'operations': {}}
            raise
        with self.api.owned(handle):
            _, size, _ = self.api.metadata(handle)
            self.private_acl(handle)
            raw = self.api.read(handle, size, limit=LIMIT)
        result = json.loads(raw)
        assert_state(result)
        return result

    def commit(self, parent, state, marker=None, stop=None):
        def checkpoint(stage):
            if stop == stage:
                save_json(marker, {'stage': stage, 'pid': os.getpid()})
                # The supervisor kills this process at a known boundary.
                time.sleep(30)
                raise TimeoutError('Crash supervisor did not terminate its child')
        raw = encode(state)
        with self.api.owned(self.child(parent, '.proof-' + str(uuid4()), create=True)) as handle:
            before, _, _ = self.api.metadata(handle)
            acl = self.private_acl(handle)
            self.write_unflushed(handle, raw)
            checkpoint('prepared')
            self.check(self.k.FlushFileBuffers(handle), 'FlushFileBuffers(prepared file)')
            flushes = [self.flush(handle, 'prepared_file')]
            checkpoint('file_flushed')
            renamed = self.api.rename(handle, parent, 'state.json')
            checkpoint('renamed')
            flushes += [self.flush(handle, 'replaced_file'), self.flush(parent, 'parent_namespace')]
            checkpoint('namespace_flushed')
            with self.api.owned(self.child(parent, 'state.json')) as reopened:
                after, size, _ = self.api.metadata(reopened)
                if after['identity'] != before['identity'] or self.api.read(reopened, size, limit=LIMIT) != raw:
                    raise RuntimeError('Replacement after-image differs')
                self.private_acl(reopened)
            checkpoint('before_response')
        return {'flushes': flushes, 'rename': renamed, 'acl': acl,
                'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


@contextmanager
def opened(api, root):
    with api.api.root({'root': str(root)}, check=False) as handle:
        yield handle


def make_store(api, base, leaf):
    root = base / leaf
    with opened(api, base) as parent:
        with api.api.owned(api.child(parent, leaf, create=True, directory=True)) as handle:
            api.api.metadata(handle)
            acl = api.private_acl(handle)
            flush = api.flush(parent, 'store_creation_parent')
    return root, acl, flush


def mutate(api, root, request_id, marker=None, stage=None):
    with opened(api, root) as parent, api.locked(parent) as (_, identity):
        state = api.read_state(parent)
        prior = state['operations'].get(request_id)
        if prior is not None:
            return {'replayed': True, 'result': prior, 'lock_identity': identity, 'flushes': []}
        result = {'request_id': request_id, 'text': 'Remember acceptance — 雪 🧭',
                  'revision': len(state['history']) + 1}
        state['records'][request_id] = result
        state['history'].append(request_id)
        state['operations'][request_id] = result
        assert_state(state)
        commit = api.commit(parent, state, marker, stage)
        return {**commit, 'replayed': False, 'result': result, 'lock_identity': identity}


def child_command(action, output, root=None, key=None, stage=None):
    args = [sys.executable, '-I', str(SCRIPT), '--child', action, '--output', str(output)]
    for option, value in (('--root', root), ('--key', key), ('--stage', stage)):
        if value is not None:
            args.extend((option, str(value)))
    return args


def run_child(action, output, root=None, key=None):
    result = subprocess.run(child_command(action, output, root, key), capture_output=True,
                            timeout=30, check=False)
    if result.returncode:
        raise RuntimeError(f'Proof subprocess failed ({result.returncode}): {result.stderr[-4096:]!r}')
    return read_json(output)


def wait_marker(process, marker):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if marker.is_file():
            return read_json(marker)
        if process.poll() is not None:
            raise RuntimeError(f'Proof child exited before marker: {process.returncode}')
        time.sleep(.02)
    raise TimeoutError('Proof child did not reach marker')


def crash_case(api, output, root, stage):
    mutate(api, root, 'seed')
    marker = output / (stage + '-marker.json')
    process = subprocess.Popen(child_command('mutate', marker, root, 'lost-ack', stage),
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        observed = wait_marker(process, marker)
        if observed['stage'] != stage:
            raise RuntimeError('Wrong crash boundary')
        process.kill()
        process.wait(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
    with opened(api, root) as parent:
        state = api.read_state(parent)
    expected_after = stage in STAGES[2:]
    if ('lost-ack' in state['operations']) != expected_after:
        raise RuntimeError('Process-kill after-image differs from its observed boundary')
    retry = mutate(api, root, 'lost-ack')
    replay = mutate(api, root, 'lost-ack')
    with opened(api, root) as parent:
        after = api.read_state(parent)
    if len(after['history']) != 2 or retry['result'] != replay['result'] or not replay['replayed']:
        raise RuntimeError('Lost acknowledgement retry duplicated or lost a record')
    return {'stage': stage, 'observed_after': expected_after, 'exit_code': process.returncode,
            'retry_replayed': retry['replayed'], 'history_count_after_retry': 2,
            'flushes': retry['flushes'], 'power_loss_tested': False}


def lock_cases(api, output, root):
    mutate(api, root, 'seed')
    with opened(api, root) as parent, api.locked(parent) as (_, identity):
        busy = run_child('try-lock', output / 'lock-busy.json', root)
        if busy['acquired']:
            raise RuntimeError('Another process entered the held writer lock')
        bounded = run_child('bounded-lock', output / 'lock-bounded.json', root)
        if bounded['acquired'] or not LOCK_SECONDS <= bounded['seconds'] < LOCK_SECONDS + 5:
            raise RuntimeError('Contending lock did not honor its acquisition bound')
        try:
            handle = api.child(parent, '.saved.lock', delete=True)
        except OSError as exc:
            sharing = exc.errno
        else:
            with api.api.owned(handle):
                raise RuntimeError('Lock handle unexpectedly shared deletion')
        if sharing != STATUS_SHARING:
            raise RuntimeError('Delete-access refusal was not a sharing violation')
    released = run_child('try-lock', output / 'lock-released.json', root)
    if not released['acquired'] or released['identity'] != identity:
        raise RuntimeError('Lock release changed persistent identity')
    marker = output / 'lock-owner-marker.json'
    owner = subprocess.Popen(child_command('hold-lock', marker, root),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_marker(owner, marker)
        owner.kill()
        owner.wait(timeout=10)
    finally:
        if owner.poll() is None:
            owner.kill()
            owner.wait(timeout=10)
    started = time.monotonic()
    with opened(api, root) as parent, api.locked(parent) as (_, after_identity):
        if identity != after_identity:
            raise RuntimeError('Process death changed lock identity')
    return {'held_contender_acquired': False, 'delete_access_ntstatus': sharing,
            'released_contender_acquired': True, 'persistent_identity': identity,
            'death_release_seconds': time.monotonic() - started,
            'bounded_contender_seconds': bounded['seconds']}


def concurrent_cases(api, output, root, identical):
    first = mutate(api, root, 'seed')
    children = []
    try:
        for i in range(8):
            path = output / f'writer-{root.name}-{i}.json'
            key = 'shared-id' if identical else f'writer-{i}'
            process = subprocess.Popen(child_command('mutate', path, root, key),
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            children.append((process, path))
        for process, _ in children:
            if process.wait(timeout=30) != 0:
                raise RuntimeError('Concurrent proof writer failed')
    finally:
        for process, _ in children:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
    results = [read_json(path) for _, path in children]
    with opened(api, root) as parent:
        state = api.read_state(parent)
    expected = 2 if identical else 9
    if len(state['history']) != expected or len({encode(r['result']) for r in results}) != (1 if identical else 8):
        raise RuntimeError('Concurrent proof lost or duplicated a commit')
    return {'writers': 8, 'identical_requests': identical, 'history_count_including_seed': expected,
            'replayed_count': sum(r['replayed'] for r in results),
            'tokens': [r['token'] for r in results],
            'flushes': first['flushes'] + [row for result in results for row in result['flushes']]}


def run_proof(output):
    api = ProofNative(output / 'native-flush-observations.jsonl')
    token = api.require_standard()
    save_json(output / 'child-token.json', token)
    from attune_harness import windows_effects
    from importlib.metadata import distribution
    package = Path(windows_effects.__file__).resolve()
    dist = distribution('attune-harness')
    direct = dist.read_text('direct_url.json')
    if (direct and json.loads(direct).get('dir_info', {}).get('editable')
            or 'site-packages' not in package.parts):
        raise RuntimeError('Proof requires a non-editable installed wheel')
    result = {'proof_schema': 1, 'experiment': 'disposable-native-saved-store-feasibility',
              'status': 'observations_in_progress', 'token': token,
              'token_profile': 'restricted-primary-medium-v1',
              'platform': {'os': platform.platform(), 'build': platform.version(),
                           'machine': platform.machine(), 'python': sys.version,
                           'executable': Path(sys.executable).as_posix(), 'filesystem': 'NTFS'},
              'identity': {'experiment_sha256': hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
                           'installed_native_sha256': hashlib.sha256(package.read_bytes()).hexdigest(),
                           'distribution_version': dist.version, 'module': package.as_posix()},
              'paid_model_calls': 0, 'provider_network_calls': 0, 'production_source_changed': False}
    flushes = []
    result['flush_observations'] = flushes
    checkpoint_number = 0
    def checkpoint(label):
        nonlocal checkpoint_number
        checkpoint_number += 1
        save_json(output / f'checkpoint-{checkpoint_number:02d}-{label}.json', result)
    save_json(output / 'receipt.json', result)
    scratch = output / ('Scratch 雪 ' + uuid4().hex[:8])
    scratch.mkdir()
    root, acl, created = make_store(api, scratch, 'Private store 🧭')
    result['private_acl'] = acl
    flushes.append(created)
    checkpoint('private-object-and-parent-flush')
    first = mutate(api, root, 'first')
    flushes += first['flushes']
    result['initial_commit'] = first
    checkpoint('initial-commit')
    result['locking'] = lock_cases(api, output, root)
    checkpoint('lock-ownership')
    result['concurrency'] = []
    for identical, name in ((False, 'Distinct writers'), (True, 'Same request')):
        store, _, created = make_store(api, scratch, name)
        observed = concurrent_cases(api, output, store, identical)
        result['concurrency'].append(observed)
        flushes += [created] + observed['flushes']
        checkpoint('identical-writers' if identical else 'distinct-writers')
    result['process_crashes'] = []
    for stage in STAGES:
        store, _, created = make_store(api, scratch, 'Crash ' + stage)
        observed = crash_case(api, output, store, stage)
        result['process_crashes'].append(observed)
        flushes += [created] + observed['flushes']
        checkpoint('crash-' + stage)
    result.update(status='observations_complete', durability_gate=receipt_gate(flushes),
                  flush_observations=flushes)
    validate_receipt(result)
    save_json(output / 'receipt.json', result)
    return result


def child_main(args):
    if args.child == 'run':
        run_proof(args.output)
        return 0
    api = ProofNative(args.output.with_name(args.output.name + '.native-flush-observations.jsonl'))
    token = api.require_standard()
    if args.child == 'mutate':
        result = mutate(api, args.root, args.key, args.output, args.stage)
        result['token'] = token
    elif args.child == 'bounded-lock':
        started = time.monotonic()
        try:
            with opened(api, args.root) as parent, api.locked(parent):
                acquired = True
        except TimeoutError:
            acquired = False
        result = {'acquired': acquired, 'seconds': time.monotonic() - started, 'token': token}
    elif args.child == 'try-lock':
        with opened(api, args.root) as parent:
            with api.api.owned(api.child(parent, '.saved.lock', lock=True)) as handle:
                entry, _, _ = api.api.metadata(handle)
                acquired = api.lock_once(handle)
                if acquired:
                    api.check(api.k.UnlockFileEx(handle, 0, 1, 0, ctypes.byref(api.Overlapped())), 'UnlockFileEx')
                result = {'acquired': acquired, 'identity': entry['identity'], 'token': token}
    else:
        with opened(api, args.root) as parent, api.locked(parent):
            save_json(args.output, {'stage': 'lock_held', 'token': token})
            time.sleep(30)
        raise TimeoutError('Crash supervisor did not kill its lock owner')
    save_json(args.output, result)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--child', choices=('run', 'mutate', 'try-lock', 'bounded-lock', 'hold-lock'))
    parser.add_argument('--root', type=Path)
    parser.add_argument('--key')
    parser.add_argument('--stage', choices=STAGES)
    args = parser.parse_args(argv)
    if args.child:
        try:
            return child_main(args)
        except Exception as exc:
            error = {'status': 'proof_failed', 'error_type': type(exc).__name__, 'detail': str(exc)}
            save_json(args.output / 'failure.json' if args.child == 'run' else args.output, error)
            return 1
    if os.name != 'nt':
        parser.error('Native Windows is required; this host cannot qualify the proof')
    # New output only: never overwrite or tune a retained experiment receipt.
    args.output = args.output.absolute()
    args.output.mkdir(parents=False, exist_ok=False)
    api = ProofNative()
    parent = api.token_facts()
    save_json(args.output / 'launcher.json', {'token': parent, 'production_port_allowed': False,
              'containment_policy': {'kill_on_job_close': True, 'assigned_while_suspended': True,
                              'breakaway_allowed': False}})
    code = api.restricted_run(args.output)
    if code:
        print(json.dumps({'status': 'proof_failed', 'exit_code': code,
                          'output': args.output.as_posix()}))
        return 1
    result = read_json(args.output / 'receipt.json')
    print(json.dumps({'status': result['status'], 'durability_gate': result['durability_gate'],
                      'output': args.output.as_posix()}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
