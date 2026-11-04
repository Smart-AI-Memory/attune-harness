"""App-owned generic-password records; no command-line secret or fallback."""

import ctypes as C
import json
import platform

from .features import FeatureUnavailable


class _NativeKeychain:
    service = 'dev.attune.harness.plan-oauth'

    def __init__(self):
        if (platform.system(), platform.machine()) != ('Darwin', 'arm64'):
            raise FeatureUnavailable('Plan OAuth requires qualified macOS arm64 Keychain storage')
        self.cf = C.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
        self.sec = C.CDLL('/System/Library/Frameworks/Security.framework/Security')
        for name, args, result in (
            ('CFStringCreateWithCString', [C.c_void_p, C.c_char_p, C.c_uint32], C.c_void_p),
            ('CFDictionaryCreateMutable', [C.c_void_p, C.c_long, C.c_void_p, C.c_void_p], C.c_void_p),
            ('CFDictionarySetValue', [C.c_void_p, C.c_void_p, C.c_void_p], None),
            ('CFDataCreate', [C.c_void_p, C.c_void_p, C.c_long], C.c_void_p),
            ('CFDataGetLength', [C.c_void_p], C.c_long),
            ('CFDataGetBytePtr', [C.c_void_p], C.c_void_p),
            ('CFRelease', [C.c_void_p], None),
        ):
            f = getattr(self.cf, name); f.argtypes, f.restype = args, result
        for name, args in (
            ('SecItemCopyMatching', [C.c_void_p, C.POINTER(C.c_void_p)]),
            ('SecItemAdd', [C.c_void_p, C.c_void_p]),
            ('SecItemUpdate', [C.c_void_p, C.c_void_p]),
            ('SecItemDelete', [C.c_void_p]),
        ):
            f = getattr(self.sec, name); f.argtypes, f.restype = args, C.c_int32

    def _constant(self, name):
        return C.c_void_p.in_dll(self.sec, name).value

    def _dictionary(self, fields):
        result = self.cf.CFDictionaryCreateMutable(None, 0, None, None)
        owned = []
        for key, value in fields.items():
            key = self._constant(key)
            if isinstance(value, str):
                value = self.cf.CFStringCreateWithCString(None, value.encode(), 0x08000100)
                owned.append(value)
            elif isinstance(value, bytes):
                value = self.cf.CFDataCreate(None, value, len(value)); owned.append(value)
            else:
                value = value[0]
            self.cf.CFDictionarySetValue(result, key, value)
        return result, owned

    def _query(self, profile_id):
        return {'kSecClass': (self._constant('kSecClassGenericPassword'),),
                'kSecAttrService': self.service, 'kSecAttrAccount': profile_id,
                'kSecUseAuthenticationUI': (self._constant('kSecUseAuthenticationUIFail'),)}

    def _call(self, operation, fields, extra=None):
        query, owned = self._dictionary(fields)
        second = None
        try:
            if extra is not None:
                second, values = self._dictionary(extra); owned.extend(values)
                return operation(query, second)
            return operation(query)
        finally:
            for value in owned: self.cf.CFRelease(value)
            if second: self.cf.CFRelease(second)
            self.cf.CFRelease(query)

    @staticmethod
    def _require(status):
        if status:
            raise FeatureUnavailable('Protected plan credential storage is unavailable')

    def get(self, profile_id):
        query = self._query(profile_id)
        query.update(kSecReturnData=(C.c_void_p.in_dll(self.cf, 'kCFBooleanTrue').value,))
        out = C.c_void_p()
        status = self._call(lambda q: self.sec.SecItemCopyMatching(q, C.byref(out)), query)
        if status == -25300: return None
        self._require(status)
        try:
            size = self.cf.CFDataGetLength(out)
            if not 0 < size <= 131072: raise ValueError('Invalid protected plan record')
            return json.loads(C.string_at(self.cf.CFDataGetBytePtr(out), size))
        finally:
            self.cf.CFRelease(out)

    def put(self, profile_id, record):
        raw = json.dumps(record, allow_nan=False).encode()
        if len(raw) > 131072: raise ValueError('Protected plan record exceeds limit')
        fields = self._query(profile_id)
        status = self._call(self.sec.SecItemUpdate, fields, {'kSecValueData': raw})
        if status == -25300:
            fields['kSecValueData'] = raw
            fields['kSecAttrAccessible'] = (self._constant('kSecAttrAccessibleWhenUnlockedThisDeviceOnly'),)
            status = self._call(lambda q: self.sec.SecItemAdd(q, None), fields)
        self._require(status)

    def probe(self):
        """Exercise the actual protected store before obtaining consent."""
        from uuid import uuid4
        name = 'probe_' + uuid4().hex
        try:
            self.put(name, {'probe': True})
            if self.get(name) != {'probe': True}:
                raise FeatureUnavailable('Protected plan credential storage is unavailable')
        finally:
            status = self._call(self.sec.SecItemDelete, self._query(name))
            if status not in (0, -25300):
                raise FeatureUnavailable('Protected plan storage probe cleanup failed')


class Keychain:
    """Supervise each protected-store operation within the caller deadline."""

    def _run(self, operation, deadline, profile_id=None, record=None):
        import os
        from pathlib import Path
        import signal
        import subprocess
        import sys
        from .plan_oauth import remaining
        remaining(deadline)
        payload = json.dumps({'operation': operation, 'profile_id': profile_id,
                              'record': record}, allow_nan=False).encode()
        if len(payload) > 262144:
            raise FeatureUnavailable('Protected plan credential input limit')
        child = subprocess.Popen((sys.executable, '-I', '-S',
            str(Path(__file__).with_name('plan_keychain_worker.py'))),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={}, start_new_session=True)
        try:
            output, _ = child.communicate(payload, timeout=remaining(deadline))
            if child.returncode or len(output) > 262144:
                raise FeatureUnavailable('Protected plan credential storage is unavailable')
            remaining(deadline)
            return json.loads(output)
        except FeatureUnavailable:
            raise
        except Exception:
            raise FeatureUnavailable('Protected plan credential storage is unavailable') from None
        finally:
            if child.poll() is None:
                try: os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError: pass
            child.wait()

    def probe(self, deadline): return self._run('probe', deadline)
    def get(self, profile_id, deadline): return self._run('get', deadline, profile_id)
    def put(self, profile_id, record, deadline): return self._run('put', deadline, profile_id, record)
