"""Narrow local-NTFS, handle-relative file effects. Import is inert off Windows.

The accepted scope owns its checkout exclusively. This module deliberately does
not claim power-loss durability or isolation from a hostile concurrent writer.
"""

import copy
import ctypes
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path, PureWindowsPath
import re
from uuid import uuid4

from .effect_limits import MAX_ENTRIES
from .features import FeatureUnavailable
from .recovery import UnresolvedOperation

REPAIR_PROFILE = "windows-existing-utf8-v1"
FEATURE_PROFILE = "windows-feature-effects-v1"
SNAPSHOT_VERSION = 1
MAX_FILE = 65536
MAX_TREE = 16 * 1024 * 1024

READ_CONTROL = 0x00020000
SYNCHRONIZE = 0x00100000
DELETE = 0x00010000
FILE_READ_DATA = 0x0001
FILE_WRITE_DATA = 0x0002
FILE_LIST_DIRECTORY = 0x0001
FILE_ADD_FILE = 0x0002
FILE_ADD_SUBDIRECTORY = 0x0004
FILE_TRAVERSE = 0x0020
FILE_READ_ATTRIBUTES = 0x0080
FILE_SHARE_ALL = 7
FILE_OPEN = 1
FILE_CREATE = 2
FILE_DIRECTORY_FILE = 1
FILE_NON_DIRECTORY_FILE = 0x40
FILE_SYNCHRONOUS_IO_NONALERT = 0x20
FILE_OPEN_REPARSE_POINT = 0x00200000
FILE_ATTRIBUTE_DIRECTORY = 0x10
FILE_ATTRIBUTE_ARCHIVE = 0x20
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
OBJ_CASE_INSENSITIVE = 0x40
OBJ_DONT_REPARSE = 0x1000
STATUS_PENDING = 0x103
ERROR_HANDLE_EOF = 38
ERROR_NO_MORE_FILES = 18
FILE_RENAME_INFORMATION_EX = 65
FILE_RENAME_REPLACE_POSIX = 3
SE_DACL_PROTECTED = 0x1000
INHERITED_ACE = 0x10


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require_platform():
    if os.name != "nt":
        raise FeatureUnavailable("Windows effects require the qualified local-NTFS handle profile")


def absolute_path(value):
    if not isinstance(value, str):
        return False
    path = PureWindowsPath(value)
    anchor = path.anchor
    return path.is_absolute() and len(anchor) == 3 and anchor[1:] == ':\\'


def leaf(value):
    """The leaf is passed directly to NtCreateFile, never to a path resolver."""
    if (not isinstance(value, str) or not value or value in (".", "..")
            or len(value.encode("utf-16-le")) > 510 or value.endswith((" ", "."))
            or any(ord(c) < 32 or c in '\\/:<>"|?*' for c in value)
            or re.fullmatch(r"(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|CLOCK\$|COM[0-9¹²³]|LPT[0-9¹²³])(?:\..*)?", value, re.I)):
        raise ValueError("Not an exact Windows file leaf")
    return value


def relative(value):
    if not isinstance(value, str) or not value or value.startswith("/"):
        raise ValueError("Not a canonical Windows effect path")
    for part in value.split("/"):
        leaf(part)
    return value


def editable_relative(value):
    relative(value)
    from .repair import PROTECTED
    if any(part.casefold() in PROTECTED for part in value.split('/')):
        raise ValueError('Protected Windows state cannot be an effect path')
    return value


def _identity(value):
    return {"volume": int(value.VolumeSerialNumber), "file_id": bytes(value.FileId).hex()}


def validate_entry(value, *, root=False):
    if not isinstance(value, dict):
        raise ValueError("Invalid Windows snapshot entry")
    keys = {"kind", "identity", "attributes", "dacl_sha256", "security_sha256", "links"}
    if not root:
        keys.add("parent_identity")
    if value.get("kind") == "file":
        keys |= {"sha256", "size"}
    elif value.get("kind") != "directory":
        raise ValueError("Invalid Windows entry kind")
    if set(value) != keys or (root and value["kind"] != "directory"):
        raise ValueError("Invalid Windows entry fields")
    for name in ("identity", *([] if root else ["parent_identity"])):
        ident = value[name]
        if (not isinstance(ident, dict) or set(ident) != {"volume", "file_id"}
                or type(ident["volume"]) is not int or ident["volume"] < 0
                or not isinstance(ident["file_id"], str)
                or not re.fullmatch(r"[0-9a-f]{32}", ident["file_id"])):
            raise ValueError("Invalid Windows file identity")
    if (type(value["attributes"]) is not int or value["attributes"] < 0
            or type(value["links"]) is not int or value["links"] < 1
            or not isinstance(value["dacl_sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", value["dacl_sha256"])
            or not isinstance(value["security_sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", value["security_sha256"])):
        raise ValueError("Invalid Windows metadata")
    if not root and value['identity']['volume'] != value['parent_identity']['volume']:
        raise ValueError('Windows child and parent volume identities differ')
    if value["kind"] == "file" and (
        value['links'] != 1 or type(value["size"]) is not int or not 0 <= value["size"] <= MAX_TREE
        or not isinstance(value["sha256"], str)
        or not re.fullmatch(r"[0-9a-f]{64}", value["sha256"])
    ):
        raise ValueError("Invalid Windows file evidence")


class Native:
    """A fresh, fixed ABI binding; handles remain owned by the caller's scope."""

    def __init__(self):
        require_platform()
        from ctypes import wintypes as w
        self.w = w
        if ctypes.sizeof(ctypes.c_wchar) != 2:
            raise FeatureUnavailable("Windows WCHAR layout is unsupported")

        class UnicodeString(ctypes.Structure):
            _fields_ = [("Length", w.USHORT), ("MaximumLength", w.USHORT), ("Buffer", ctypes.c_void_p)]

        class ObjectAttributes(ctypes.Structure):
            _fields_ = [("Length", w.ULONG), ("RootDirectory", w.HANDLE),
                        ("ObjectName", ctypes.POINTER(UnicodeString)),
                        ("Attributes", w.ULONG), ("SecurityDescriptor", ctypes.c_void_p),
                        ("SecurityQualityOfService", ctypes.c_void_p)]

        class IoStatus(ctypes.Structure):
            _fields_ = [("Status", ctypes.c_void_p), ("Information", ctypes.c_size_t)]

        class FileId(ctypes.Structure):
            _fields_ = [("VolumeSerialNumber", ctypes.c_ulonglong), ("FileId", ctypes.c_ubyte * 16)]

        class Standard(ctypes.Structure):
            _fields_ = [("AllocationSize", ctypes.c_longlong), ("EndOfFile", ctypes.c_longlong),
                        ("NumberOfLinks", w.DWORD), ("DeletePending", w.BOOLEAN),
                        ("Directory", w.BOOLEAN)]

        class Basic(ctypes.Structure):
            _fields_ = [("CreationTime", ctypes.c_longlong), ("LastAccessTime", ctypes.c_longlong),
                        ("LastWriteTime", ctypes.c_longlong), ("ChangeTime", ctypes.c_longlong),
                        ("FileAttributes", w.DWORD)]

        class Rename(ctypes.Structure):
            _fields_ = [("Flags", w.DWORD), ("RootDirectory", w.HANDLE),
                        ("FileNameLength", w.DWORD), ("FileName", w.WCHAR * 1)]

        class FullDir(ctypes.Structure):
            _fields_ = [("NextEntryOffset", w.DWORD), ("FileIndex", w.DWORD),
                        ("CreationTime", ctypes.c_longlong), ("LastAccessTime", ctypes.c_longlong),
                        ("LastWriteTime", ctypes.c_longlong), ("ChangeTime", ctypes.c_longlong),
                        ("EndOfFile", ctypes.c_longlong), ("AllocationSize", ctypes.c_longlong),
                        ("FileAttributes", w.DWORD), ("FileNameLength", w.DWORD),
                        ("EaSize", w.DWORD), ("FileName", w.WCHAR * 1)]

        class Stream(ctypes.Structure):
            _fields_ = [("NextEntryOffset", w.DWORD), ("StreamNameLength", w.DWORD),
                        ("StreamSize", ctypes.c_longlong),
                        ("StreamAllocationSize", ctypes.c_longlong), ("StreamName", w.WCHAR * 1)]

        class Acl(ctypes.Structure):
            _fields_ = [("AclRevision", ctypes.c_ubyte), ("Sbz1", ctypes.c_ubyte),
                        ("AclSize", w.WORD), ("AceCount", w.WORD), ("Sbz2", w.WORD)]

        class AceHeader(ctypes.Structure):
            _fields_ = [("AceType", ctypes.c_ubyte), ("AceFlags", ctypes.c_ubyte),
                        ("AceSize", w.WORD)]

        self.UnicodeString, self.ObjectAttributes, self.IoStatus = UnicodeString, ObjectAttributes, IoStatus
        self.FileId, self.Standard, self.Basic, self.Rename = FileId, Standard, Basic, Rename
        self.FullDir, self.Stream, self.Acl, self.AceHeader = FullDir, Stream, Acl, AceHeader
        self.nt = ctypes.WinDLL("ntdll", use_last_error=True)
        self.k = ctypes.WinDLL("kernel32", use_last_error=True)
        self.a = ctypes.WinDLL("advapi32", use_last_error=True)
        self.nt.NtCreateFile.argtypes = [ctypes.POINTER(w.HANDLE), w.DWORD,
            ctypes.POINTER(ObjectAttributes), ctypes.POINTER(IoStatus), ctypes.c_void_p,
            w.DWORD, w.DWORD, w.DWORD, w.DWORD, ctypes.c_void_p, w.DWORD]
        self.nt.NtCreateFile.restype = ctypes.c_long
        self.nt.NtSetInformationFile.argtypes = [w.HANDLE, ctypes.POINTER(IoStatus),
            ctypes.c_void_p, w.ULONG, ctypes.c_int]
        self.nt.NtSetInformationFile.restype = ctypes.c_long
        self.k.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, ctypes.c_void_p,
            w.DWORD, w.DWORD, w.HANDLE]
        self.k.CreateFileW.restype = w.HANDLE
        self.k.CloseHandle.argtypes = [w.HANDLE]
        self.k.CloseHandle.restype = w.BOOL
        self.k.GetFileInformationByHandleEx.argtypes = [w.HANDLE, ctypes.c_int,
            ctypes.c_void_p, w.DWORD]
        self.k.GetFileInformationByHandleEx.restype = w.BOOL
        self.k.ReadFile.argtypes = [w.HANDLE, ctypes.c_void_p, w.DWORD,
            ctypes.POINTER(w.DWORD), ctypes.c_void_p]
        self.k.ReadFile.restype = w.BOOL
        self.k.SetFilePointerEx.argtypes = [w.HANDLE, ctypes.c_longlong,
            ctypes.POINTER(ctypes.c_longlong), w.DWORD]
        self.k.SetFilePointerEx.restype = w.BOOL
        self.k.WriteFile.argtypes = [w.HANDLE, ctypes.c_void_p, w.DWORD,
            ctypes.POINTER(w.DWORD), ctypes.c_void_p]
        self.k.WriteFile.restype = w.BOOL
        self.k.FlushFileBuffers.argtypes = [w.HANDLE]
        self.k.FlushFileBuffers.restype = w.BOOL
        self.k.GetVolumeInformationW.argtypes = [w.LPCWSTR, w.LPWSTR, w.DWORD,
            ctypes.POINTER(w.DWORD), ctypes.POINTER(w.DWORD), ctypes.POINTER(w.DWORD),
            w.LPWSTR, w.DWORD]
        self.k.GetVolumeInformationW.restype = w.BOOL
        self.k.GetDriveTypeW.argtypes = [w.LPCWSTR]
        self.k.GetDriveTypeW.restype = w.UINT
        self.a.GetSecurityInfo.argtypes = [w.HANDLE, w.DWORD, w.DWORD,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p)]
        self.a.GetSecurityInfo.restype = w.DWORD
        self.a.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [
            ctypes.c_void_p, w.DWORD, w.DWORD, ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(w.DWORD)]
        self.a.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype = w.BOOL
        self.a.GetSecurityDescriptorControl.argtypes = [ctypes.c_void_p,
            ctypes.POINTER(w.WORD), ctypes.POINTER(w.DWORD)]
        self.a.GetSecurityDescriptorControl.restype = w.BOOL
        self.a.GetSecurityDescriptorDacl.argtypes = [ctypes.c_void_p,
            ctypes.POINTER(w.BOOL), ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(w.BOOL)]
        self.a.GetSecurityDescriptorDacl.restype = w.BOOL
        self.a.GetAce.argtypes = [ctypes.c_void_p, w.DWORD, ctypes.POINTER(ctypes.c_void_p)]
        self.a.GetAce.restype = w.BOOL
        self.k.LocalFree.argtypes = [ctypes.c_void_p]
        self.k.LocalFree.restype = ctypes.c_void_p

    def _check(self, result, operation):
        if not result:
            raise OSError(ctypes.get_last_error(), operation)

    @contextmanager
    def owned(self, handle):
        value = ctypes.cast(handle, ctypes.c_void_p).value
        if value in (None, ctypes.c_void_p(-1).value):
            raise OSError(ctypes.get_last_error(), "Invalid Windows file handle")
        try:
            yield handle
        finally:
            self._check(self.k.CloseHandle(handle), "CloseHandle")

    def volume(self, path):
        anchor = Path(path).anchor
        if len(anchor) != 3 or anchor[1:] != ":\\" or self.k.GetDriveTypeW(anchor) != 3:
            raise FeatureUnavailable("Windows effects require a fixed local drive-letter volume")
        fs = ctypes.create_unicode_buffer(64)
        self._check(self.k.GetVolumeInformationW(anchor, None, 0, None, None, None,
                                                 fs, len(fs)), "GetVolumeInformationW")
        if fs.value.upper() != "NTFS":
            raise FeatureUnavailable("Windows effects require local NTFS")
        return anchor

    def volume_handle(self, anchor):
        return self.k.CreateFileW(anchor, FILE_READ_ATTRIBUTES | FILE_LIST_DIRECTORY |
            READ_CONTROL | SYNCHRONIZE, FILE_SHARE_ALL, None, 3,
            0x02000000 | FILE_OPEN_REPARSE_POINT, None)

    def child(self, parent, name, *, create=False, directory=None, writable=False):
        leaf(name)
        namebuf = ctypes.create_unicode_buffer(name)
        encoded = name.encode("utf-16-le")
        text = self.UnicodeString(len(encoded), ctypes.sizeof(namebuf),
                                  ctypes.cast(namebuf, ctypes.c_void_p))
        attrs = self.ObjectAttributes(ctypes.sizeof(self.ObjectAttributes), parent,
            ctypes.pointer(text), OBJ_CASE_INSENSITIVE | OBJ_DONT_REPARSE, None, None)
        result, ios = self.w.HANDLE(), self.IoStatus()
        access = FILE_READ_ATTRIBUTES | READ_CONTROL | SYNCHRONIZE
        if directory is not False:
            access |= FILE_LIST_DIRECTORY
            if directory is True:
                access |= FILE_TRAVERSE
            if writable and directory is True:
                access |= FILE_ADD_FILE | FILE_ADD_SUBDIRECTORY
        else:
            access |= FILE_READ_DATA
            if writable:
                access |= FILE_WRITE_DATA | DELETE
        options = FILE_SYNCHRONOUS_IO_NONALERT
        if create and directory is True:
            options |= FILE_DIRECTORY_FILE
        else:
            options |= FILE_OPEN_REPARSE_POINT
            if directory is False:
                options |= FILE_NON_DIRECTORY_FILE
        status = self.nt.NtCreateFile(ctypes.byref(result), access, ctypes.byref(attrs),
            ctypes.byref(ios), None, FILE_ATTRIBUTE_ARCHIVE if create and not directory else 0,
            FILE_SHARE_ALL, FILE_CREATE if create else FILE_OPEN, options, None, 0)
        if status != 0:
            if status == STATUS_PENDING or status > 0:
                raise UnresolvedOperation(f"NtCreateFile returned nonfinal status {status & 0xffffffff:08x}")
            raise OSError(status & 0xffffffff, "NtCreateFile refused exact leaf")
        return result

    def info(self, handle, kind, cls):
        value = kind()
        self._check(self.k.GetFileInformationByHandleEx(handle, cls, ctypes.byref(value),
                                                        ctypes.sizeof(value)), "GetFileInformationByHandleEx")
        return value

    def security(self, handle):
        descriptor, string = ctypes.c_void_p(), ctypes.c_void_p()
        code = self.a.GetSecurityInfo(handle, 1, 7, None, None, None, None,
                                      ctypes.byref(descriptor))
        if code:
            raise OSError(code, "GetSecurityInfo(DACL)")
        try:
            def string_for(flags):
                length = self.w.DWORD()
                self._check(self.a.ConvertSecurityDescriptorToStringSecurityDescriptorW(
                    descriptor, 1, flags, ctypes.byref(string), ctypes.byref(length)),
                    "ConvertSecurityDescriptor")
                try:
                    return ctypes.wstring_at(string)
                finally:
                    self.k.LocalFree(string)
            dacl_sddl, full_sddl = string_for(4), string_for(7)
            control, revision = self.w.WORD(), self.w.DWORD()
            self._check(self.a.GetSecurityDescriptorControl(descriptor,
                ctypes.byref(control), ctypes.byref(revision)), "GetSecurityDescriptorControl")
            present, defaulted, acl = self.w.BOOL(), self.w.BOOL(), ctypes.c_void_p()
            self._check(self.a.GetSecurityDescriptorDacl(descriptor, ctypes.byref(present),
                ctypes.byref(acl), ctypes.byref(defaulted)), "GetSecurityDescriptorDacl")
            inherited = bool(present.value and acl.value and not control.value & SE_DACL_PROTECTED)
            if inherited:
                count = ctypes.cast(acl, ctypes.POINTER(self.Acl)).contents.AceCount
                if count > 256:
                    raise ValueError("DACL exceeds bounded ACE policy")
                for index in range(count):
                    ace = ctypes.c_void_p()
                    self._check(self.a.GetAce(acl, index, ctypes.byref(ace)), "GetAce")
                    header = ctypes.cast(ace, ctypes.POINTER(self.AceHeader)).contents
                    if header.AceSize < ctypes.sizeof(self.AceHeader) or not header.AceFlags & INHERITED_ACE:
                        inherited = False
            return _sha(dacl_sddl.encode("utf-8")), _sha(full_sddl.encode("utf-8")), inherited
        finally:
            self.k.LocalFree(descriptor)

    def streams(self, handle, *, directory=False):
        # The only permitted stream is the unnamed primary data stream.
        buffer = ctypes.create_string_buffer(65536)
        if not self.k.GetFileInformationByHandleEx(handle, 7, buffer, len(buffer)):
            error = ctypes.get_last_error()
            if error == ERROR_HANDLE_EOF:
                return []
            raise OSError(error, "FileStreamInfo")
        found, offset = [], 0
        while True:
            if offset + self.Stream.StreamName.offset > len(buffer):
                raise ValueError("Malformed stream listing")
            row = self.Stream.from_buffer_copy(buffer, offset)
            end = offset + self.Stream.StreamName.offset + row.StreamNameLength
            if row.StreamNameLength % 2 or end > len(buffer):
                raise ValueError("Malformed stream name")
            found.append(buffer.raw[offset + self.Stream.StreamName.offset:end].decode("utf-16-le"))
            if row.NextEntryOffset == 0:
                break
            if row.NextEntryOffset < self.Stream.StreamName.offset or offset + row.NextEntryOffset <= offset:
                raise ValueError("Malformed stream offset")
            offset += row.NextEntryOffset
        accepted = ([], [":$I30:$INDEX_ALLOCATION"]) if directory else ([], ["::$DATA"])
        if found not in accepted:
            raise ValueError("Alternate data stream is outside Windows effect policy")
        return found

    def metadata(self, handle, parent_identity=None):
        basic = self.info(handle, self.Basic, 0)
        standard = self.info(handle, self.Standard, 1)
        ident = _identity(self.info(handle, self.FileId, 18))
        dacl, security, inherited_only = self.security(handle)
        if basic.FileAttributes & FILE_ATTRIBUTE_REPARSE_POINT or standard.DeletePending:
            raise ValueError("Reparse or delete-pending entry is not eligible")
        if not standard.Directory and standard.NumberOfLinks != 1:
            raise ValueError("Multiply linked file is outside Windows effect policy")
        self.streams(handle, directory=bool(standard.Directory))
        entry = {"kind": "directory" if standard.Directory else "file",
                 "identity": ident, "attributes": int(basic.FileAttributes),
                 "dacl_sha256": dacl, "security_sha256": security,
                 "links": int(standard.NumberOfLinks)}
        if parent_identity is not None:
            entry["parent_identity"] = parent_identity
        return entry, int(standard.EndOfFile), inherited_only

    def names(self, directory):
        result, first = [], True
        while True:
            buffer = ctypes.create_string_buffer(65536)
            cls = 15 if first else 14
            first = False
            if not self.k.GetFileInformationByHandleEx(directory, cls, buffer, len(buffer)):
                error = ctypes.get_last_error()
                if error in (ERROR_HANDLE_EOF, ERROR_NO_MORE_FILES):
                    break
                raise OSError(error, "FileFullDirectoryInfo")
            offset = 0
            while True:
                if offset + self.FullDir.FileName.offset > len(buffer):
                    raise ValueError("Malformed directory listing")
                row = self.FullDir.from_buffer_copy(buffer, offset)
                end = offset + self.FullDir.FileName.offset + row.FileNameLength
                if row.FileNameLength % 2 or end > len(buffer):
                    raise ValueError("Malformed directory name")
                name = buffer.raw[offset + self.FullDir.FileName.offset:end].decode("utf-16-le")
                if name not in (".", ".."):
                    leaf(name)
                    result.append(name)
                    if len(result) > MAX_ENTRIES:
                        raise ValueError("Directory exceeds bounded Windows profile")
                if row.NextEntryOffset == 0:
                    break
                if row.NextEntryOffset < self.FullDir.FileName.offset or offset + row.NextEntryOffset <= offset:
                    raise ValueError("Malformed directory offset")
                offset += row.NextEntryOffset
        if len({name.casefold() for name in result}) != len(result) or len(set(result)) != len(result):
            raise ValueError("Windows path alias or casefold collision")
        return sorted(result)

    def canonical_child(self, parent, name, *, directory=None, writable=False):
        if name not in self.names(parent):
            raise ValueError("Path is not an enumerated canonical long name")
        return self.child(parent, name, directory=directory, writable=writable)

    @contextmanager
    def root(self, plan, *, check=True):
        path = Path(plan["root"])
        anchor = self.volume(path)
        components = str(path)[len(anchor):].split("\\")
        if not components or any(not item for item in components):
            raise ValueError("Windows effect root must be below the volume root")
        with self.owned(self.volume_handle(anchor)) as volume:
            current = volume
            opened = []
            try:
                for index, part in enumerate(components):
                    child = self.canonical_child(current, part, directory=True,
                                                 writable=index == len(components) - 1)
                    opened.append(child)
                    current = child
                    entry, _, _ = self.metadata(current)
                    if entry["kind"] != "directory":
                        raise ValueError("Root path traverses a non-directory")
                if check and entry["identity"] != plan["root_identity"]:
                    raise UnresolvedOperation("Windows checkout identity changed")
                yield current
            finally:
                for handle in reversed(opened):
                    self._check(self.k.CloseHandle(handle), "CloseHandle")

    @contextmanager
    def parent(self, root, path):
        parts = relative(path).split("/")
        current, opened = root, []
        try:
            for index, part in enumerate(parts[:-1]):
                child = self.canonical_child(current, part, directory=True,
                                             writable=index == len(parts) - 2)
                opened.append(child)
                current = child
                entry, _, _ = self.metadata(current)
                if entry["kind"] != "directory":
                    raise ValueError("Effect parent is not a directory")
            yield current, parts[-1]
        finally:
            for handle in reversed(opened):
                self._check(self.k.CloseHandle(handle), "CloseHandle")

    def read(self, handle, size, *, limit=MAX_TREE):
        if size < 0 or size > limit:
            raise ValueError("File exceeds Windows effect byte budget")
        self._check(self.k.SetFilePointerEx(handle, 0, None, 0), "SetFilePointerEx")
        buffer, count = ctypes.create_string_buffer(size + 1), self.w.DWORD()
        self._check(self.k.ReadFile(handle, buffer, size + 1, ctypes.byref(count), None), "ReadFile")
        if count.value != size:
            raise UnresolvedOperation("File size changed while reading")
        return buffer.raw[:size]

    def write(self, handle, raw):
        offset = 0
        while offset < len(raw):
            segment = raw[offset:offset + 65536]
            buffer, count = ctypes.create_string_buffer(segment), self.w.DWORD()
            self._check(self.k.WriteFile(handle, buffer, len(segment), ctypes.byref(count), None), "WriteFile")
            if not 0 < count.value <= len(segment):
                raise UnresolvedOperation("Windows file write made no progress")
            offset += count.value
        self._check(self.k.FlushFileBuffers(handle), "FlushFileBuffers")

    def rename(self, source, parent, target):
        name = leaf(target).encode("utf-16-le")
        buffer = ctypes.create_string_buffer(ctypes.sizeof(self.Rename) + len(name))
        header = ctypes.cast(buffer, ctypes.POINTER(self.Rename)).contents
        header.Flags = FILE_RENAME_REPLACE_POSIX
        header.RootDirectory = parent
        header.FileNameLength = len(name)
        ctypes.memmove(ctypes.addressof(buffer) + self.Rename.FileName.offset, name, len(name))
        ios = self.IoStatus()
        ios.Status = 0xDEADBEEF
        status = self.nt.NtSetInformationFile(source, ctypes.byref(ios), buffer,
                                               len(buffer), FILE_RENAME_INFORMATION_EX)
        if status != 0:
            if status == STATUS_PENDING or status > 0:
                raise UnresolvedOperation(f"Windows rename returned nonfinal status {status & 0xffffffff:08x}")
            raise UnresolvedOperation(f"Windows rename refused with NTSTATUS {status & 0xffffffff:08x}")
        return {"returned_ntstatus": 0, "io_status_block_status": int(ios.Status or 0) & 0xffffffff}


def _observed(api, handle, parent_identity=None, *, limit=MAX_TREE):
    entry, size, inherited = api.metadata(handle, parent_identity)
    if entry["kind"] == "file":
        raw = api.read(handle, size, limit=limit)
        again, later_size, _ = api.metadata(handle, parent_identity)
        if entry != again or later_size != size:
            raise UnresolvedOperation("File metadata changed while reading")
        entry.update(size=len(raw), sha256=_sha(raw))
        return entry, raw, inherited
    return entry, None, inherited


def _snapshot(api, plan):
    result, total = {}, 0
    with api.root(plan) as root:
        root_entry, _, _ = _observed(api, root)
        result[""] = root_entry

        def walk(parent, prefix, parent_identity):
            nonlocal total
            for name in api.names(parent):
                path = prefix + name
                # This exact long name came from the retained parent's bounded
                # enumeration; reopening it under that same handle avoids a
                # quadratic second listing of every directory.
                with api.owned(api.child(parent, name)) as child:
                    entry, raw, _ = _observed(api, child, parent_identity)
                    if len(result) >= MAX_ENTRIES:
                        raise ValueError("Checkout exceeds bounded Windows effect profile")
                    result[path + "/" if entry["kind"] == "directory" else path] = entry
                    if raw is not None:
                        total += len(raw)
                        if total > MAX_TREE:
                            raise ValueError("Checkout exceeds Windows tree byte budget")
                    else:
                        walk(child, path + "/", entry["identity"])

        walk(root, "", root_entry["identity"])
    return result


def snapshot(plan):
    return _snapshot(Native(), plan)


def root_identity(root):
    api = Native()
    plan = {"root": str(root)}
    with api.root(plan, check=False) as handle:
        entry, _, _ = _observed(api, handle)
        return entry["identity"]


def file_text(plan, path):
    api = Native()
    with api.root(plan) as root:
        with api.parent(root, path) as (parent, name):
            parent_entry, _, _ = _observed(api, parent)
            with api.owned(api.canonical_child(parent, name)) as child:
                entry, raw, inherited = _observed(api, child, parent_entry["identity"], limit=MAX_FILE)
                if entry["kind"] != "file":
                    raise ValueError("Accepted Windows input must be a file")
                return raw.decode("utf-8"), entry, inherited


def inherited_at(plan, path, expected):
    """Reopen a lost-ack target under the retained parent before projection."""
    api = Native()
    with api.root(plan) as root:
        with api.parent(root, path) as (parent, name):
            parent_entry, _, _ = _observed(api, parent)
            with api.owned(api.canonical_child(parent, name)) as child:
                actual, _, inherited = _observed(api, child, parent_entry['identity'],
                                                   limit=MAX_FILE)
    if actual != expected or not inherited:
        raise UnresolvedOperation('Windows after-image metadata is not inherited and exact')


def eligible_file(entry, inherited):
    if (entry["kind"] != "file" or entry["links"] != 1
            or entry["attributes"] != FILE_ATTRIBUTE_ARCHIVE
            or entry["size"] > MAX_FILE or not inherited):
        raise ValueError("Editable file has unsupported Windows attributes or DACL")


def replace_file(plan, item):
    raw = item["text"].encode("utf-8")
    api = Native()
    with api.root(plan) as root:
        with api.parent(root, item["path"]) as (parent, name):
            parent_entry, _, _ = _observed(api, parent)
            with api.owned(api.canonical_child(parent, name)) as original:
                before, previous_raw, inherited = _observed(api, original, parent_entry["identity"], limit=MAX_FILE)
                eligible_file(before, inherited)
                if before != plan["before"][item["path"]] or _sha(previous_raw) != item["before_sha256"]:
                    raise UnresolvedOperation("Windows replacement preimage changed")
                temp = ".harness-replace-" + uuid4().hex
                with api.owned(api.child(parent, temp, create=True, directory=False,
                                         writable=True)) as prepared:
                    api.write(prepared, raw)
                    made, made_raw, made_inherited = _observed(api, prepared,
                        parent_entry["identity"], limit=MAX_FILE)
                    if (made_raw != raw or made["attributes"] != before["attributes"]
                            or made["security_sha256"] != before["security_sha256"]
                            or not made_inherited):
                        raise UnresolvedOperation("Prepared Windows sibling metadata differs; inspect orphan")
                    current, current_raw, _ = _observed(api, original,
                        parent_entry["identity"], limit=MAX_FILE)
                    if current != before or current_raw != previous_raw:
                        raise UnresolvedOperation("Windows target changed before rename")
                    status = api.rename(prepared, parent, name)
            with api.owned(api.canonical_child(parent, name)) as target:
                after, observed_raw, _ = _observed(api, target,
                    parent_entry["identity"], limit=MAX_FILE)
                if (observed_raw != raw or after["attributes"] != before["attributes"]
                        or after["security_sha256"] != before["security_sha256"]
                        or after["identity"] != made["identity"]):
                    raise UnresolvedOperation("Windows replacement after-image differs")
    return {"path": item["path"], "before_sha256": item["before_sha256"],
            "after_sha256": _sha(raw), "bytes": len(raw), "after_entry": after,
            "native_rename": status}


def create_entry(plan, item):
    api = Native()
    path, directory = item["path"], item["kind"] == "directory"
    with api.root(plan) as root:
        with api.parent(root, path) as (parent, name):
            parent_entry, _, _ = _observed(api, parent)
            if name.casefold() in {existing.casefold() for existing in api.names(parent)}:
                raise UnresolvedOperation("Windows creation collides with existing leaf")
            with api.owned(api.child(parent, name, create=True, directory=directory,
                                     writable=True)) as created:
                if not directory:
                    api.write(created, item["text"].encode("utf-8"))
                entry, raw, inherited = _observed(api, created, parent_entry["identity"], limit=MAX_FILE)
                if directory:
                    if entry["kind"] != "directory" or not inherited:
                        raise UnresolvedOperation("Created Windows directory has unsupported metadata")
                elif (raw != item["text"].encode("utf-8") or not inherited
                        or entry["attributes"] != FILE_ATTRIBUTE_ARCHIVE):
                    raise UnresolvedOperation("Created Windows file has unsupported metadata")
    return {"path": path + ("/" if directory else ""), "entry": entry}


def observed_effect_result(item, entry):
    validate_entry(entry)
    if item["kind"] == "directory":
        if entry["kind"] != "directory":
            raise ValueError("Directory effect has a file receipt")
        path = item["path"] + "/"
    else:
        raw = item['text'].encode('utf-8')
        if (entry["kind"] != "file" or entry["sha256"] != _sha(raw)
                or entry['size'] != len(raw)):
            raise ValueError("File effect receipt differs from proposal")
        path = item["path"]
    return {"path": path, "entry": entry}


def validate_repair_result(item, result):
    if not isinstance(result, dict) or set(result) != {
        'path', 'before_sha256', 'after_sha256', 'bytes', 'after_entry', 'native_rename'
    }:
        raise ValueError('Invalid Windows repair receipt')
    entry = result['after_entry']
    validate_entry(entry)
    raw = item['text'].encode('utf-8')
    if (entry['kind'] != 'file' or entry['sha256'] != _sha(raw)
            or entry['size'] != len(raw)
            or result['path'] != item['path']
            or result['before_sha256'] != item['before_sha256']
            or result['after_sha256'] != _sha(raw) or result['bytes'] != len(raw)):
        raise ValueError('Windows repair receipt differs from proposal')
    rename = result['native_rename']
    observed = rename == {'transmission': 'unknown', 'observation_only': True}
    direct = (isinstance(rename, dict) and set(rename) == {
        'returned_ntstatus', 'io_status_block_status'}
        and type(rename['returned_ntstatus']) is int and rename['returned_ntstatus'] == 0
        and type(rename['io_status_block_status']) is int
        and 0 <= rename['io_status_block_status'] <= 0xffffffff)
    if not (observed or direct):
        raise ValueError('Invalid Windows rename evidence')
    return result


def expected_snapshot(plan, events, *, kind):
    expected = copy.deepcopy(plan["before"])
    for event in events:
        if event["kind"] != kind or event["state"] != "completed":
            continue
        if kind == "replacement":
            item, result = event["patch"], event["result"]
            validate_repair_result(item, result)
            entry = result['after_entry']
            before = expected[item['path']]
            if (entry['identity'] == before['identity']
                    or entry['parent_identity'] != before['parent_identity']
                    or any(entry[k] != before[k] for k in ('attributes', 'security_sha256'))):
                raise ValueError('Windows repair receipt changed accepted metadata')
            expected[item["path"]] = copy.deepcopy(entry)
        else:
            item, result = event["item"], event["result"]
            if result != observed_effect_result(item, result.get("entry", {})):
                raise ValueError("Windows feature result differs from proposal")
            parent_path = item['path'].rsplit('/', 1)[0] + '/' if '/' in item['path'] else ''
            parent = expected[parent_path]
            entry = result['entry']
            if entry['parent_identity'] != parent['identity']:
                raise ValueError('Windows effect receipt changed parent identity')
            prior = expected.get(result['path'])
            if item['kind'] == 'replacement' and (
                prior is None or entry['identity'] == prior['identity']
                or any(entry[k] != prior[k] for k in ('attributes', 'security_sha256'))
            ):
                raise ValueError('Windows replacement receipt changed accepted metadata')
            if item['kind'] == 'creation' and (
                prior is not None or entry['attributes'] != FILE_ATTRIBUTE_ARCHIVE
            ):
                raise ValueError('Windows creation receipt is not a new ordinary file')
            if item['kind'] == 'directory' and prior is not None:
                raise ValueError('Windows directory receipt is not a new directory')
            expected[result["path"]] = copy.deepcopy(result["entry"])
    return expected


def reconcile(plan, event, events, *, kind, retry_before=False):
    """Record the independent whole-tree observation, never synthesize IDs."""
    if event["phase"] != "dispatching" or event["state"] == "completed":
        raise ValueError("Only an unresolved Windows effect can be reconciled")
    prior = expected_snapshot(plan, events, kind=kind)
    actual = snapshot(plan)
    item = event["patch"] if kind == "replacement" else event["item"]
    path = item["path"] + ("/" if item.get("kind") == "directory" else "")
    candidate = actual.get(path)
    after = copy.deepcopy(prior)
    if candidate is not None:
        after[path] = candidate
    non_target_equal = {k: v for k, v in actual.items() if k != path} == {
        k: v for k, v in prior.items() if k != path}
    if not non_target_equal:
        raise UnresolvedOperation("Windows effect changed a non-target entry")
    original = prior.get(path)
    if actual == prior and retry_before and event["attempts"] < 2:
        event.update(state="pending", phase="prepared", attempts=event["attempts"] + 1)
        event.pop("runtime_origin", None)
        result = {"status": "explicit_before_retry"}
    elif candidate is not None and after == actual:
        validate_entry(candidate)
        parent_path = item['path'].rsplit('/', 1)[0] + '/' if '/' in item['path'] else ''
        if candidate['parent_identity'] != prior[parent_path]['identity']:
            raise UnresolvedOperation('Windows effect parent identity differs')
        inherited_at(plan, item['path'], candidate)
        if original is not None and candidate["identity"] == original["identity"]:
            raise UnresolvedOperation("Windows target identity did not change")
        if kind == "replacement":
            if (original is None or candidate["kind"] != "file"
                    or candidate["sha256"] != _sha(item["text"].encode("utf-8"))
                    or any(candidate[k] != original[k] for k in ("attributes", "security_sha256", "parent_identity"))):
                raise UnresolvedOperation("Windows replacement after-image is not accepted")
            raw = item["text"].encode("utf-8")
            receipt = {"path": path, "before_sha256": item["before_sha256"],
                       "after_sha256": _sha(raw), "bytes": len(raw),
                       "after_entry": candidate,
                       "native_rename": {"transmission": "unknown", "observation_only": True}}
            validate_repair_result(item, receipt)
        else:
            receipt = observed_effect_result(item, candidate)
            if original is not None and (candidate["attributes"] != original["attributes"]
                                         or candidate["security_sha256"] != original["security_sha256"]):
                raise UnresolvedOperation("Windows effect metadata changed unexpectedly")
            if item['kind'] == 'creation' and candidate['attributes'] != FILE_ATTRIBUTE_ARCHIVE:
                raise UnresolvedOperation('Created Windows file has unsupported attributes')
        event.update(state="completed", phase="completed", result=receipt)
        result = {"status": "observed_after_image"}
    else:
        raise UnresolvedOperation("Windows effect requires explicit before retry or exact after-image")
    event.pop("error", None)
    event.pop("effects", None)
    return {**result, "snapshot_sha256": _sha(str(sorted(actual.items())).encode("utf-8")),
            "retry_before": retry_before}
