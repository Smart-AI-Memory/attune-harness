"""Proposed fixed-local NTFS byte/lease boundary for the common saved owner.

External source draft: no native qualification or application has occurred.
"""
from contextlib import contextmanager
import ctypes
from pathlib import Path, PureWindowsPath
import time
from uuid import uuid4

from .memory_saved import SavedError, MAX_STATE, LOCK_SECONDS
from .features import FeatureUnavailable
from .windows_effects import Native, leaf

_COLLISION = 0xC0000035


def root_path(value):
    """Preserve spelling until retained-handle canonical-name admission."""
    path = PureWindowsPath(value)
    if (not path.is_absolute() or len(path.anchor) != 3
            or path.anchor[1:] != ':\\' or not path.drive[0].isascii()
            or not path.drive[0].isalpha() or len(path.parts) < 2):
        raise SavedError('Saved storage requires an absolute local drive path', code='unsupported')
    try:
        for part in path.parts[1:]:
            leaf(part)
            if part.casefold() in ('.git', '.hg', '.svn'):
                raise SavedError('Saved root cannot be repository metadata')
    except (ValueError, UnicodeError) as exc:
        raise SavedError('Saved root must contain exact Windows path leaves') from exc
    return Path(str(path))


def _normal(value):
    if (not isinstance(value, tuple) or len(value) != 2
            or any(type(item) is not int or item != 0 for item in value)):
        raise OSError('Native saved operation did not return two final success statuses')


def _has_exact(native, directory, name):
    matches = [item for item in native.api.iter_names(directory)
               if item.casefold() == name.casefold()]
    if not matches:
        return False
    if matches != [name]:
        raise OSError('Saved entry has an ambiguous or noncanonical case alias')
    return True


class _Native:
    """Only storage security, byte, flush and persistent-lock operations."""

    def __init__(self):
        self.api = Native()
        self.w, self.k, self.a = self.api.w, self.api.k, self.api.a
        w = self.w

        class SidAndAttributes(ctypes.Structure):
            _fields_ = [('Sid', ctypes.c_void_p), ('Attributes', w.DWORD)]

        class Overlapped(ctypes.Structure):
            _fields_ = [('Internal', ctypes.c_size_t), ('InternalHigh', ctypes.c_size_t),
                        ('Offset', w.DWORD), ('OffsetHigh', w.DWORD), ('hEvent', w.HANDLE)]

        self.SidAndAttributes, self.Overlapped = SidAndAttributes, Overlapped
        self.k.GetCurrentProcess.argtypes = []
        self.k.GetCurrentProcess.restype = w.HANDLE
        self.a.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, ctypes.POINTER(w.HANDLE)]
        self.a.OpenProcessToken.restype = w.BOOL
        self.a.GetTokenInformation.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                              w.DWORD, ctypes.POINTER(w.DWORD)]
        self.a.GetTokenInformation.restype = w.BOOL
        self.a.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
        self.a.ConvertSidToStringSidW.restype = w.BOOL
        self.a.IsValidSid.argtypes = [ctypes.c_void_p]
        self.a.IsValidSid.restype = w.BOOL
        self.a.GetSecurityDescriptorOwner.argtypes = [ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(w.BOOL)]
        self.a.GetSecurityDescriptorOwner.restype = w.BOOL
        self.a.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [w.LPCWSTR,
            w.DWORD, ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]
        self.a.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = w.BOOL
        self.api.nt.NtFlushBuffersFileEx.argtypes = [w.HANDLE, w.ULONG, ctypes.c_void_p,
            w.ULONG, ctypes.POINTER(self.api.IoStatus)]
        self.api.nt.NtFlushBuffersFileEx.restype = ctypes.c_long
        self.k.LockFileEx.argtypes = [w.HANDLE, w.DWORD, w.DWORD, w.DWORD, w.DWORD,
                                     ctypes.POINTER(Overlapped)]
        self.k.LockFileEx.restype = w.BOOL
        self.k.UnlockFileEx.argtypes = [w.HANDLE, w.DWORD, w.DWORD, w.DWORD,
                                       ctypes.POINTER(Overlapped)]
        self.k.UnlockFileEx.restype = w.BOOL
        self.user_sid = self._current_user_sid()

    def _current_user_sid(self):
        token = self.w.HANDLE()
        self.api._check(self.a.OpenProcessToken(self.k.GetCurrentProcess(), 8,
                                                ctypes.byref(token)), 'OpenProcessToken(query)')
        with self.api.owned(token):
            size = self.w.DWORD()
            self.a.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
            if not ctypes.sizeof(self.SidAndAttributes) <= size.value <= 65536:
                raise OSError('Saved token-user information exceeds its bound')
            raw = ctypes.create_string_buffer(size.value)
            self.api._check(self.a.GetTokenInformation(token, 1, raw, len(raw),
                                                      ctypes.byref(size)), 'GetTokenInformation(user)')
            sid = self.SidAndAttributes.from_buffer_copy(raw).Sid
            start, end = ctypes.addressof(raw), ctypes.addressof(raw) + len(raw)
            if sid is None or not start <= sid <= end - 8:
                raise OSError('Saved token-user SID lies outside its buffer')
            count = ctypes.c_ubyte.from_address(sid + 1).value
            if count > 15 or sid + 8 + count * 4 > end:
                raise OSError('Saved token-user SID exceeds its bound')
            return self._sid_text(sid)

    def _sid_text(self, sid):
        self.api._check(self.a.IsValidSid(sid), 'IsValidSid')
        text = ctypes.c_void_p()
        self.api._check(self.a.ConvertSidToStringSidW(sid, ctypes.byref(text)), 'ConvertSidToStringSidW')
        try:
            return ctypes.wstring_at(text)
        finally:
            self.k.LocalFree(text)

    @contextmanager
    def _descriptor(self):
        value = ctypes.c_void_p()
        text = f'O:{self.user_sid}D:P(A;OICI;FA;;;{self.user_sid})(A;OICI;FA;;;SY)'
        self.api._check(self.a.ConvertStringSecurityDescriptorToSecurityDescriptorW(text, 1,
                       ctypes.byref(value), None), 'Saved private security descriptor')
        try:
            yield value
        finally:
            self.k.LocalFree(value)

    def child(self, parent, name, *, create=False, directory=False, writable=False, lock=False):
        leaf(name)
        namebuf = ctypes.create_unicode_buffer(name)
        encoded = name.encode('utf-16-le')
        text = self.api.UnicodeString(len(encoded), ctypes.sizeof(namebuf),
                                     ctypes.cast(namebuf, ctypes.c_void_p))
        with self._descriptor() as descriptor:
            attrs = self.api.ObjectAttributes(ctypes.sizeof(self.api.ObjectAttributes), parent,
                ctypes.pointer(text), 0x1040, descriptor if create else None, None)
            access = 0x00120081
            if directory:
                access |= 0x20  # FILE_TRAVERSE
                if writable:
                    access |= 6  # FILE_ADD_FILE | FILE_ADD_SUBDIRECTORY, plus LIST above
            elif writable or lock:
                access |= 2
                if not lock:
                    access |= 0x10000
            options = 0x20 | (1 if directory else 0x40) | (0 if create else 0x00200000)
            handle, ios = self.w.HANDLE(), self.api.IoStatus()
            ios.Status = 0xDEADBEEF
            status = self.api.nt.NtCreateFile(ctypes.byref(handle), access, ctypes.byref(attrs),
                ctypes.byref(ios), None, 0x10 if directory else 0x20,
                3 if directory or lock else 7, 2 if create else 1, options, None, 0)
        returned, observed = status & 0xffffffff, int(ios.Status or 0) & 0xffffffff
        if returned != 0 or observed != 0:
            if handle.value:
                self.k.CloseHandle(handle)
            raise OSError(returned or observed, 'Saved exact child operation refused')
        return handle

    def private(self, handle):
        if not self.is_private(handle):
            raise OSError('Saved private ownership or DACL differs from its exact profile')

    def is_private(self, handle):
        """Classify the managed descriptor; native query errors still refuse."""
        descriptor, owner = ctypes.c_void_p(), ctypes.c_void_p()
        code = self.a.GetSecurityInfo(handle, 1, 5, None, None, None, None, ctypes.byref(descriptor))
        if code:
            raise OSError(code, 'GetSecurityInfo(saved)')
        try:
            defaulted = self.w.BOOL()
            self.api._check(self.a.GetSecurityDescriptorOwner(descriptor, ctypes.byref(owner),
                           ctypes.byref(defaulted)), 'GetSecurityDescriptorOwner')
            control, revision = self.w.WORD(), self.w.DWORD()
            self.api._check(self.a.GetSecurityDescriptorControl(descriptor, ctypes.byref(control),
                           ctypes.byref(revision)), 'GetSecurityDescriptorControl')
            present, dacl = self.w.BOOL(), ctypes.c_void_p()
            self.api._check(self.a.GetSecurityDescriptorDacl(descriptor, ctypes.byref(present),
                           ctypes.byref(dacl), ctypes.byref(defaulted)), 'GetSecurityDescriptorDacl')
            if not control.value & 0x1000 or not present.value or not dacl.value:
                return False
            if self._sid_text(owner) != self.user_sid:
                return False
            acl = ctypes.cast(dacl, ctypes.POINTER(self.api.Acl)).contents
            if acl.AceCount != 2:
                return False
            principals = []
            for index in range(2):
                ace = ctypes.c_void_p()
                self.api._check(self.a.GetAce(dacl, index, ctypes.byref(ace)), 'GetAce(saved)')
                header = self.api.AceHeader.from_address(ace.value)
                if header.AceType != 0 or header.AceFlags != 3 or header.AceSize < 16:
                    return False
                count = ctypes.c_ubyte.from_address(ace.value + 9).value
                if count > 15 or 16 + count * 4 > header.AceSize:
                    raise OSError('Saved private ACE SID exceeds its bound')
                if self.w.DWORD.from_address(ace.value + 4).value != 0x1f01ff:
                    return False
                principals.append(self._sid_text(ace.value + 8))
            return len(set(principals)) == 2 and set(principals) == {self.user_sid, 'S-1-5-18'}
        finally:
            self.k.LocalFree(descriptor)

    def flush(self, handle):
        ios = self.api.IoStatus()
        ios.Status = 0xDEADBEEF
        status = self.api.nt.NtFlushBuffersFileEx(handle, 0, None, 0, ctypes.byref(ios))
        return status & 0xffffffff, int(ios.Status or 0) & 0xffffffff

    def write_all(self, handle, payload):
        offset = 0
        while offset < len(payload):
            part = payload[offset:offset + 65536]
            buffer, count = ctypes.create_string_buffer(part), self.w.DWORD()
            self.api._check(self.k.WriteFile(handle, buffer, len(part), ctypes.byref(count), None), 'WriteFile(saved)')
            if not 0 < count.value <= len(part):
                raise OSError('Saved write made no bounded progress')
            offset += count.value
        return offset

    def lock_once(self, handle):
        if self.k.LockFileEx(handle, 3, 0, 1, 0, ctypes.byref(self.Overlapped())):
            return True
        error = ctypes.get_last_error()
        if error == 33:
            return False
        raise OSError(error, 'LockFileEx(saved)')

    def unlock(self, handle):
        self.api._check(self.k.UnlockFileEx(handle, 0, 1, 0,
                       ctypes.byref(self.Overlapped())), 'UnlockFileEx(saved)')

    def remove_prepared(self, handle):
        delete = ctypes.c_ubyte(1)
        ios = self.api.IoStatus()
        ios.Status = 0xDEADBEEF
        status = self.api.nt.NtSetInformationFile(handle, ctypes.byref(ios), ctypes.byref(delete), 1, 13)
        _normal((status & 0xffffffff, int(ios.Status or 0) & 0xffffffff))

    def close(self, handle):
        self.api._check(self.k.CloseHandle(handle), 'CloseHandle(saved)')


class _Session:
    """One held directory/lock lease; JSON and mutation remain in SavedStore."""

    def __init__(self, api, directory):
        self.native, self.directory = api, directory
        self.dispatched = False

    def _inspect(self, handle, kind):
        entry, size, _ = self.native.api.metadata(handle)
        if entry['kind'] != kind or (kind == 'file' and entry['links'] != 1):
            raise OSError('Saved entry has unsupported kind or links')
        self.native.private(handle)
        return entry, size

    def _has_exact(self, name):
        return _has_exact(self.native, self.directory, name)

    def read_payload(self):
        handle = None
        try:
            if not self._has_exact('state.json'):
                return None
            handle = self.native.child(self.directory, 'state.json')
            before, size = self._inspect(handle, 'file')
            if not 0 <= size <= MAX_STATE:
                raise OSError('Saved state exceeds its byte bound')
            raw = self.native.api.read(handle, size, limit=MAX_STATE)
            after, after_size = self._inspect(handle, 'file')
            if before != after or size != after_size or len(raw) != size:
                raise OSError('Saved state changed during its bounded read')
            return raw
        except (OSError, ValueError, RuntimeError) as exc:
            raise SavedError('Saved storage read failed', code='storage') from exc
        finally:
            if handle is not None:
                self.native.close(handle)

    def commit_payload(self, payload):
        if not isinstance(payload, bytes) or len(payload) > MAX_STATE:
            raise SavedError('Saved state exceeds 8 MiB')
        prepared = None
        dispatched = False
        failure = None
        cause = None
        try:
            # FILE_CREATE; never reuse, truncate or reopen an existing sibling.
            prepared = self.native.child(self.directory, '.saved-' + str(uuid4()),
                                         create=True, writable=True)
            made, _ = self._inspect(prepared, 'file')
            if self.native.write_all(prepared, payload) != len(payload):
                raise OSError('Saved state write is incomplete')
            ready, size = self._inspect(prepared, 'file')
            if (ready != made or size != len(payload)
                    or self.native.api.read(prepared, size, limit=MAX_STATE) != payload):
                raise OSError('Saved prepared sibling differs from its payload or authority')
            _normal(self.native.flush(prepared))
            # A wrapper can dispatch successfully then raise without returning.
            dispatched = self.dispatched = True
            result = self.native.api.rename(prepared, self.directory, 'state.json')
            if (not isinstance(result, dict)
                    or set(result) != {'returned_ntstatus', 'io_status_block_status'}):
                raise OSError('Saved replacement status is missing')
            _normal((result['returned_ntstatus'], result['io_status_block_status']))
            _normal(self.native.flush(prepared))
            _normal(self.native.flush(self.directory))
            if not self._has_exact('state.json'):
                raise OSError('Saved replacement lacks its canonical leaf')
            reopened = self.native.child(self.directory, 'state.json')
            try:
                after, size = self._inspect(reopened, 'file')
                if (after != made or size != len(payload)
                        or self.native.api.read(reopened, size, limit=MAX_STATE) != payload):
                    raise OSError('Saved replacement after-image differs')
            finally:
                self.native.close(reopened)
        except (OSError, ValueError, RuntimeError) as exc:
            failure, cause = True, exc
        finally:
            if prepared is not None:
                if not dispatched:
                    try:
                        self.native.remove_prepared(prepared)
                    except (OSError, ValueError, RuntimeError):
                        # Like the existing POSIX unlink path, cleanup is best
                        # effort before replacement; the private orphan is not
                        # authoritative state. Never delete after dispatch.
                        pass
                try:
                    self.native.close(prepared)
                except OSError as exc:
                    failure, cause = True, exc
        if failure:
            raise SavedError('Saved commit durability is uncertain; inspect and retry with the same request ID'
                             if self.dispatched else 'Saved commit failed before replacement',
                             code='persistence',
                             outcome='uncertain' if self.dispatched else 'not_committed') from cause


def _walk(native, root, handles):
    """Retain canonical ancestors; republish each admitted managed component."""
    path = PureWindowsPath(root)
    try:
        anchor = native.api.volume(Path(str(path)))
    except FeatureUnavailable as exc:
        raise SavedError('Saved storage requires a fixed local NTFS volume',
                         code='unsupported') from exc
    volume = native.api.volume_handle(anchor)
    handles.append(volume)
    current, parent, name = volume, None, None
    managed = False

    def writable(handle, previous, component, *, require_private=False):
        if previous is None:
            upgraded = native.k.CreateFileW(anchor, 0x00120087, 7, None, 3,
                                            0x02200000, None)
        else:
            upgraded = native.child(previous, component, directory=True, writable=True)
        handles.append(upgraded)
        before, _, _ = native.api.metadata(handle)
        after, _, _ = native.api.metadata(upgraded)
        if before != after or after['kind'] != 'directory':
            raise OSError('Saved parent identity changed while obtaining publication authority')
        if require_private:
            native.private(upgraded)
        return upgraded

    for part in path.parts[1:]:
        previous = current
        attempted_creation = False
        parent_writable = False
        if _has_exact(native, current, part):
            child = native.child(current, part, directory=True)
        else:
            previous = writable(current, parent, name, require_private=managed)
            parent_writable = attempted_creation = True
            try:
                child = native.child(previous, part, create=True, directory=True, writable=True)
            except OSError as exc:
                if exc.errno != _COLLISION or not _has_exact(native, previous, part):
                    raise
                child = native.child(previous, part, directory=True, writable=True)
        handles.append(child)
        entry, _, _ = native.api.metadata(child)
        if entry['kind'] != 'directory':
            raise OSError('Saved selected ancestor is not a directory')
        if managed or attempted_creation or native.is_private(child):
            native.private(child)
            if not parent_writable:
                previous = writable(current, parent, name, require_private=managed)
            parent_before, _, _ = native.api.metadata(previous)
            _normal(native.flush(previous))
            parent_after, _, _ = native.api.metadata(previous)
            child_after, _, _ = native.api.metadata(child)
            native.private(child)
            if managed:
                native.private(previous)
            if parent_after != parent_before or child_after != entry:
                raise OSError('Saved namespace authority changed during parent publication')
            managed = True
        parent, name, current = previous, part, child
    current = writable(current, parent, name, require_private=True)
    native.private(current)
    return current


@contextmanager
def locked(root):
    native = None
    handles, session, lock, acquired = [], None, None, False
    cleanup_failed = False
    try:
        native = _Native()
        directory = _walk(native, root_path(root), handles)
        session = _Session(native, directory)
        created = False
        if _has_exact(native, directory, '.saved.lock'):
            lock = native.child(directory, '.saved.lock', lock=True)
        else:
            try:
                lock = native.child(directory, '.saved.lock', create=True, lock=True)
                created = True
            except OSError as exc:
                if exc.errno != _COLLISION or not _has_exact(native, directory, '.saved.lock'):
                    raise
                lock = native.child(directory, '.saved.lock', lock=True)
        # Register ownership immediately, before metadata or barriers can fail.
        handles.append(lock)
        identity, _ = session._inspect(lock, 'file')
        if created:
            _normal(native.flush(lock))
            _normal(native.flush(directory))
        deadline = time.monotonic() + LOCK_SECONDS
        while not native.lock_once(lock):
            if time.monotonic() >= deadline:
                raise SavedError('Saved store is busy or locking is unavailable', code='busy')
            time.sleep(.01)
        acquired = True
        after, _ = session._inspect(lock, 'file')
        if after != identity:
            raise OSError('Saved persistent lock identity changed')
        yield session
    except SavedError:
        raise
    except (OSError, ValueError, RuntimeError) as exc:
        uncertain = session is not None and session.dispatched
        raise SavedError('Saved storage outcome is uncertain; inspect and retry with the same request ID'
                         if uncertain else 'Saved storage access failed',
                         code='persistence' if uncertain else 'storage',
                         outcome='uncertain' if uncertain else 'not_committed') from exc
    finally:
        if acquired:
            try:
                native.unlock(lock)
            except OSError:
                cleanup_failed = True
        for handle in reversed(handles):
            try:
                native.close(handle)
            except OSError:
                cleanup_failed = True
        if cleanup_failed:
            uncertain = session is not None and session.dispatched
            raise SavedError('Saved storage lease release failed',
                             code='persistence' if uncertain else 'storage',
                             outcome='uncertain' if uncertain else 'not_committed')
