"""Disposable real-Windows file-effects primitive probe; no product backend.

Run on local NTFS with Python 3.10 or 3.12. Always write --output JSON. A
successful probe establishes only the observed after-image primitives, never
power-loss durability, arbitrary ACL preservation, or task-level support.

Layouts and flags: Microsoft NtCreateFile/OBJECT_ATTRIBUTES, FILE_ID_INFO,
FILE_RENAME_INFO, and SetFileInformationByHandle documentation linked in
docs/design-windows-feature-effects.md.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import traceback
from contextlib import contextmanager
from pathlib import Path


READ_CONTROL = 0x00020000
SYNCHRONIZE = 0x00100000
DELETE = 0x00010000
FILE_READ_DATA = 0x0001
FILE_WRITE_DATA = 0x0002
FILE_LIST_DIRECTORY = 0x0001
FILE_TRAVERSE = 0x0020
FILE_ADD_FILE = 0x0002
FILE_READ_ATTRIBUTES = 0x0080
FILE_SHARE_ALL = 0x7
FILE_OPEN = 0x1
FILE_CREATE = 0x2
FILE_DIRECTORY_FILE = 0x1
FILE_NON_DIRECTORY_FILE = 0x40
FILE_SYNCHRONOUS_IO_NONALERT = 0x20
FILE_OPEN_REPARSE_POINT = 0x00200000
OBJ_CASE_INSENSITIVE = 0x40
OBJ_DONT_REPARSE = 0x1000
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
FILE_RENAME_FLAG_REPLACE_IF_EXISTS = 0x1
FILE_RENAME_FLAG_POSIX_SEMANTICS = 0x2
FILE_RENAME_INFO_EX = 22  # FILE_INFO_BY_HANDLE_CLASS, not NT FILE_INFORMATION_CLASS.
NT_FILE_RENAME_INFORMATION_EX = 65
NT_FILE_RENAME_INFORMATION = 10
STATUS_PENDING = 0x00000103
STATUS_OBJECT_NAME_NOT_FOUND = 0xC0000034
STATUS_REPARSE_POINT_ENCOUNTERED = 0xC000050B
FILE_ID_INFO_CLASS = 18
FILE_STANDARD_INFO_CLASS = 1
FILE_BASIC_INFO_CLASS = 0
DACL_SECURITY_INFORMATION = 0x4
SE_FILE_OBJECT = 1


class ProbeError(Exception):
    def __init__(self, operation: str, code: int, kind: str):
        super().__init__(f"{operation}: {kind}=0x{code & 0xffffffff:08x}")
        self.operation, self.code, self.kind = operation, code & 0xffffffff, kind


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_fingerprint(path: Path) -> dict:
    executed = path.read_bytes()
    git_bytes = executed.replace(b"\r\n", b"\n")
    if b"\r" in git_bytes:
        raise ValueError("unsupported standalone carriage return in source")
    git_header = f"blob {len(git_bytes)}\0".encode("ascii")
    return {"executed_sha256": _digest(executed),
            "git_lf_sha256": _digest(git_bytes),
            "git_blob_sha1": hashlib.sha1(git_header + git_bytes).hexdigest(),
            "crlf_lines": executed.count(b"\r\n"),
            "lf_lines": git_bytes.count(b"\n")}


def _leaf(name: str) -> str:
    # The caller must never smuggle another component or alternate stream into
    # an operation intended to be relative to an already validated directory.
    if (not name or name in {".", ".."} or any(c in name for c in "\\/:\0")
            or name.endswith((" ", "."))):
        raise ValueError("not an exact single Windows leaf")
    return name


def _environment_probe() -> dict:
    """Observe a child environment, without running a repository executable."""
    ambient = os.environ
    canary_key = "ATTUNE_WINDOWS_AMBIENT_CANARY"
    prior_canary = ambient.get(canary_key)
    ambient[canary_key] = "not-accepted-by-child"
    try:
        return _observed_environment(ambient, canary_key)
    finally:
        if prior_canary is None:
            del ambient[canary_key]
        else:
            ambient[canary_key] = prior_canary


def _observed_environment(ambient, canary_key: str) -> dict:
    system_keys = [key for key in ambient if key.casefold() == "systemroot"]
    if len(system_keys) != 1:
        raise ValueError("expected exactly one trusted host SystemRoot")
    accepted = {key: ambient[key] for key in ("PATH", "LANG", "LC_ALL") if key in ambient}
    accepted.update(PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1")
    accepted["SystemRoot"] = ambient[system_keys[0]]
    if len({key.casefold() for key in accepted}) != len(accepted):
        raise ValueError("case-insensitive environment key collision")
    observed = subprocess.run(
        [sys.executable, "-I", "-c", "import json,os;print(json.dumps(dict(os.environ)))"],
        env=accepted, check=True, capture_output=True, text=True, timeout=15,
    )
    child = json.loads(observed.stdout)
    if {k.casefold(): v for k, v in child.items()} != {k.casefold(): v for k, v in accepted.items()}:
        raise ValueError("child environment differs from proposed finite map")
    if canary_key.casefold() in {key.casefold() for key in child}:
        raise ValueError("ambient canary reached child")
    return {"keys": sorted(accepted), "systemroot_supplied": True,
            "systemroot_requirement_unproven": True,
            "exact_child_environment": True, "ambient_canary_absent": True}


def _windows_api():
    # Keep all WinDLL resolution under the native platform guard.
    from ctypes import wintypes

    if ctypes.sizeof(ctypes.c_wchar) != 2:
        raise RuntimeError("Win32 WCHAR must be UTF-16")

    class UNICODE_STRING(ctypes.Structure):
        _fields_ = [("Length", wintypes.USHORT), ("MaximumLength", wintypes.USHORT),
                    ("Buffer", ctypes.c_void_p)]

    class OBJECT_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("Length", wintypes.ULONG), ("RootDirectory", wintypes.HANDLE),
                    ("ObjectName", ctypes.POINTER(UNICODE_STRING)),
                    ("Attributes", wintypes.ULONG), ("SecurityDescriptor", ctypes.c_void_p),
                    ("SecurityQualityOfService", ctypes.c_void_p)]

    class IO_STATUS_BLOCK(ctypes.Structure):
        _fields_ = [("Status", ctypes.c_void_p), ("Information", ctypes.c_size_t)]

    class FILE_ID_INFO(ctypes.Structure):
        _fields_ = [("VolumeSerialNumber", ctypes.c_ulonglong),
                    ("FileId", ctypes.c_ubyte * 16)]

    class FILE_STANDARD_INFO(ctypes.Structure):
        _fields_ = [("AllocationSize", ctypes.c_longlong),
                    ("EndOfFile", ctypes.c_longlong), ("NumberOfLinks", wintypes.DWORD),
                    ("DeletePending", wintypes.BOOLEAN), ("Directory", wintypes.BOOLEAN)]

    class FILE_BASIC_INFO(ctypes.Structure):
        _fields_ = [("CreationTime", ctypes.c_longlong),
                    ("LastAccessTime", ctypes.c_longlong),
                    ("LastWriteTime", ctypes.c_longlong),
                    ("ChangeTime", ctypes.c_longlong),
                    ("FileAttributes", wintypes.DWORD)]

    class FILE_RENAME_INFO(ctypes.Structure):
        _fields_ = [("Flags", wintypes.DWORD), ("RootDirectory", wintypes.HANDLE),
                    ("FileNameLength", wintypes.DWORD), ("FileName", wintypes.WCHAR * 1)]

    nt = ctypes.WinDLL("ntdll", use_last_error=True)
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    a = ctypes.WinDLL("advapi32", use_last_error=True)
    nt.NtCreateFile.argtypes = [ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD,
        ctypes.POINTER(OBJECT_ATTRIBUTES), ctypes.POINTER(IO_STATUS_BLOCK),
        ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
        wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    nt.NtCreateFile.restype = ctypes.c_long
    nt.NtSetInformationFile.argtypes = [wintypes.HANDLE, ctypes.POINTER(IO_STATUS_BLOCK),
        ctypes.c_void_p, wintypes.ULONG, ctypes.c_int]
    nt.NtSetInformationFile.restype = ctypes.c_long
    k.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    k.CreateFileW.restype = wintypes.HANDLE
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    k.CloseHandle.restype = wintypes.BOOL
    k.GetFileInformationByHandleEx.argtypes = [wintypes.HANDLE, ctypes.c_int,
        ctypes.c_void_p, wintypes.DWORD]
    k.GetFileInformationByHandleEx.restype = wintypes.BOOL
    k.SetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.c_int,
        ctypes.c_void_p, wintypes.DWORD]
    k.SetFileInformationByHandle.restype = wintypes.BOOL
    k.WriteFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    k.WriteFile.restype = wintypes.BOOL
    k.ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    k.ReadFile.restype = wintypes.BOOL
    k.FlushFileBuffers.argtypes = [wintypes.HANDLE]
    k.FlushFileBuffers.restype = wintypes.BOOL
    k.GetVolumeInformationW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR,
        wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR, wintypes.DWORD]
    k.GetVolumeInformationW.restype = wintypes.BOOL
    k.GetDriveTypeW.argtypes = [wintypes.LPCWSTR]
    k.GetDriveTypeW.restype = wintypes.UINT
    a.GetSecurityInfo.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p)]
    a.GetSecurityInfo.restype = wintypes.DWORD
    a.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [
        ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.DWORD)]
    a.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype = wintypes.BOOL
    k.LocalFree.argtypes = [ctypes.c_void_p]
    k.LocalFree.restype = ctypes.c_void_p
    invalid = ctypes.c_void_p(-1).value

    def wincheck(ok, name):
        if not ok:
            raise ProbeError(name, ctypes.get_last_error(), "win32")

    @contextmanager
    def owned(handle):
        value = ctypes.cast(handle, ctypes.c_void_p).value
        if value in (None, invalid):
            raise ProbeError("handle", ctypes.get_last_error(), "win32")
        try:
            yield handle
        finally:
            wincheck(k.CloseHandle(handle), "CloseHandle")

    def directory(path):
        handle = k.CreateFileW(str(path), FILE_READ_ATTRIBUTES | FILE_LIST_DIRECTORY |
            READ_CONTROL | SYNCHRONIZE, FILE_SHARE_ALL, None, 3,
            0x02000000 | 0x00200000, None)  # BACKUP_SEMANTICS | OPEN_REPARSE_POINT.
        if ctypes.cast(handle, ctypes.c_void_p).value in (None, invalid):
            raise ProbeError("CreateFileW(root)", ctypes.get_last_error(), "win32")
        return handle

    def child(parent, name, *, directory=False, create=False, writable=False):
        _leaf(name)
        namebuf = ctypes.create_unicode_buffer(name)
        text = UNICODE_STRING(len(name.encode("utf-16-le")),
                              ctypes.sizeof(namebuf), ctypes.cast(namebuf, ctypes.c_void_p))
        attrs = OBJECT_ATTRIBUTES(ctypes.sizeof(OBJECT_ATTRIBUTES), parent,
            ctypes.pointer(text), OBJ_CASE_INSENSITIVE | OBJ_DONT_REPARSE, None, None)
        result, ios = wintypes.HANDLE(), IO_STATUS_BLOCK()
        access = (FILE_READ_ATTRIBUTES | READ_CONTROL | SYNCHRONIZE |
                  (FILE_LIST_DIRECTORY if directory else FILE_READ_DATA) |
                  (FILE_ADD_FILE | FILE_TRAVERSE if directory and writable else 0) |
                  (FILE_WRITE_DATA | DELETE if writable and not directory else 0))
        # FILE_DIRECTORY_FILE is documented as incompatible with
        # FILE_OPEN_REPARSE_POINT; inspect Directory after opening instead.
        options = ((0 if directory else FILE_NON_DIRECTORY_FILE) |
                   FILE_OPEN_REPARSE_POINT | FILE_SYNCHRONOUS_IO_NONALERT)
        status = nt.NtCreateFile(ctypes.byref(result), access, ctypes.byref(attrs),
            ctypes.byref(ios), None, 0, FILE_SHARE_ALL,
            FILE_CREATE if create else FILE_OPEN, options, None, 0)
        if status < 0:
            raise ProbeError("NtCreateFile(" + name + ")", status, "ntstatus")
        return result

    def info(handle, kind, cls):
        value = kind()
        wincheck(k.GetFileInformationByHandleEx(handle, cls, ctypes.byref(value),
                                               ctypes.sizeof(value)), "GetFileInformationByHandleEx")
        return value

    def identity(handle):
        value = info(handle, FILE_ID_INFO, FILE_ID_INFO_CLASS)
        return {"volume": value.VolumeSerialNumber, "file_id": bytes(value.FileId).hex()}

    def observed(handle):
        basic = info(handle, FILE_BASIC_INFO, FILE_BASIC_INFO_CLASS)
        standard = info(handle, FILE_STANDARD_INFO, FILE_STANDARD_INFO_CLASS)
        sd, string = ctypes.c_void_p(), ctypes.c_void_p()
        code = a.GetSecurityInfo(handle, SE_FILE_OBJECT, DACL_SECURITY_INFORMATION,
                                 None, None, None, None, ctypes.byref(sd))
        if code:
            raise ProbeError("GetSecurityInfo(DACL)", code, "win32")
        try:
            length = wintypes.DWORD()
            wincheck(a.ConvertSecurityDescriptorToStringSecurityDescriptorW(sd, 1,
                DACL_SECURITY_INFORMATION, ctypes.byref(string), ctypes.byref(length)),
                "ConvertSecurityDescriptorToStringSecurityDescriptorW")
            try:
                dacl = ctypes.wstring_at(string)
            finally:
                k.LocalFree(string)
        finally:
            k.LocalFree(sd)
        return {"identity": identity(handle), "attributes": basic.FileAttributes,
                "number_of_links": standard.NumberOfLinks,
                "is_directory": bool(standard.Directory), "size": standard.EndOfFile,
                "dacl_sddl_sha256": _digest(dacl.encode("utf-8"))}

    def require_singly_linked_file(handle):
        entry = observed(handle)
        if (entry["number_of_links"] != 1 or entry["is_directory"] or
                entry["attributes"] & FILE_ATTRIBUTE_REPARSE_POINT):
            raise ValueError("entry is not an eligible singly linked regular file")
        return entry

    def write(handle, data):
        buf = ctypes.create_string_buffer(data)
        written = wintypes.DWORD()
        wincheck(k.WriteFile(handle, buf, len(data), ctypes.byref(written), None), "WriteFile")
        if written.value != len(data):
            raise ValueError("short WriteFile")
        wincheck(k.FlushFileBuffers(handle), "FlushFileBuffers")

    def read(handle, expected_size):
        if expected_size > 4096:
            raise ValueError("scratch read exceeded probe bound")
        buf, count = ctypes.create_string_buffer(expected_size + 1), wintypes.DWORD()
        wincheck(k.ReadFile(handle, buf, expected_size + 1, ctypes.byref(count), None), "ReadFile")
        if count.value != expected_size:
            raise ValueError("scratch file length disagrees with handle snapshot")
        return buf.raw[:count.value]

    def replace(handle, parent, target, audit, case):
        name = _leaf(target).encode("utf-16-le")
        offset = FILE_RENAME_INFO.FileName.offset
        # Microsoft requires at least sizeof(FILE_RENAME_INFORMATION) plus
        # FileNameLength. The first native run allocated offset+name+NUL,
        # which was two bytes short of this minimum on x64 (Win32 error 87).
        payload = ctypes.create_string_buffer(ctypes.sizeof(FILE_RENAME_INFO) + len(name))
        native = case["api"] == "nt"
        info_class = case["class"]
        flags = case["flags"]
        root_supplied = case["root"] == "parent"
        audit.update({"api": "NtSetInformationFile" if native else "SetFileInformationByHandle",
            "class": info_class, "flags": flags,
            "root_directory_handle_supplied": root_supplied, "target_leaf": target,
            "filename_offset": offset, "struct_size": ctypes.sizeof(FILE_RENAME_INFO),
            "filename_bytes": len(name), "buffer_bytes": len(payload)})
        header = ctypes.cast(payload, ctypes.POINTER(FILE_RENAME_INFO)).contents
        header.Flags = flags
        header.RootDirectory = parent if root_supplied else None
        header.FileNameLength = len(name)
        ctypes.memmove(ctypes.addressof(payload) + offset, name, len(name))
        if not native:
            wincheck(k.SetFileInformationByHandle(handle, info_class, payload,
                                                  len(payload)), "SetFileInformationByHandle(FileRenameInfoEx)")
            audit["win32_success"] = True
            return
        ios = IO_STATUS_BLOCK()
        ios.Status = 0xDEADBEEF
        returned = nt.NtSetInformationFile(handle, ctypes.byref(ios), payload,
                                           len(payload), info_class)
        result_status = returned & 0xFFFFFFFF
        ios_status = (ios.Status or 0) & 0xFFFFFFFF
        audit.update({"returned_ntstatus": result_status, "io_status_block_status": ios_status,
                      "ntstatus_disagrees": result_status != ios_status,
                      "nonfinal": result_status != 0 and result_status >> 30 != 3})
        # Microsoft specifies the returned NTSTATUS as authoritative unless
        # it is STATUS_PENDING. An untouched IOSB on immediate error is not
        # evidence of an unknown outcome; the after-image still must match.
        if result_status != 0:
            raise ProbeError("NtSetInformationFile", result_status, "ntstatus")

    def filesystem(path):
        volume_root = Path(path).anchor
        if len(volume_root) != 3 or volume_root[1:] != ":\\":
            raise ValueError("scratch is not on a local drive-letter volume")
        if k.GetDriveTypeW(volume_root) != 3:  # DRIVE_FIXED, excludes network/removable.
            raise ValueError("scratch volume is not a fixed local drive")
        name = ctypes.create_unicode_buffer(64)
        wincheck(k.GetVolumeInformationW(volume_root, None, 0, None, None,
                                         None, name, len(name)), "GetVolumeInformationW")
        return name.value

    return locals()


def _rename_matrix(root, root_handle, api, receipt):
    cases = (
        {"id": "A", "api": "win32", "class": FILE_RENAME_INFO_EX, "flags": 3, "root": "parent", "parent_add_file": False},
        {"id": "B", "api": "nt", "class": NT_FILE_RENAME_INFORMATION_EX, "flags": 3, "root": "parent", "parent_add_file": False},
        {"id": "C", "api": "nt", "class": NT_FILE_RENAME_INFORMATION_EX, "flags": 3, "root": "parent", "parent_add_file": True},
        {"id": "D", "api": "nt", "class": NT_FILE_RENAME_INFORMATION_EX, "flags": 1, "root": "parent", "parent_add_file": True},
        {"id": "E", "api": "nt", "class": NT_FILE_RENAME_INFORMATION, "flags": 1, "root": "parent", "parent_add_file": True},
        {"id": "F", "api": "win32", "class": FILE_RENAME_INFO_EX, "flags": 3, "root": "null", "parent_add_file": False},
    )
    root_id = api["identity"](root_handle)
    receipt["rename_cases"] = []
    receipt["handle_relative_observed_cases"] = []
    old, proposed, protected = b"old synthetic\n", b"new synthetic\n", b"protected\n"
    target, sibling = "target-é.txt", "prepared-é.tmp"

    def observe_entry(parent, name):
        try:
            with api["owned"](api["child"](parent, name)) as handle:
                entry = api["observed"](handle)
                return {"metadata": entry,
                        "sha256": _digest(api["read"](handle, entry["size"]))}
        except ProbeError as exc:
            if exc.kind == "ntstatus" and exc.code == STATUS_OBJECT_NAME_NOT_FOUND:
                return None
            raise

    for case in cases:
        path = root / ("case-" + case["id"] + " é space")
        path.mkdir()
        (path / target).write_bytes(old)
        (path / "protected.txt").write_bytes(protected)
        item = {"id": case["id"], "config": case.copy(),
                "scratch_is_independent": True, "process_crash_induced": False,
                "null_root_cwd_confined_to_scratch": case["root"] == "null",
                "parent_requested_access": FILE_READ_ATTRIBUTES | READ_CONTROL |
                    SYNCHRONIZE | FILE_LIST_DIRECTORY |
                    (FILE_ADD_FILE | FILE_TRAVERSE if case["parent_add_file"] else 0)}
        receipt["rename_cases"].append(item)
        with api["owned"](api["child"](root_handle, path.name, directory=True,
                                      writable=case["parent_add_file"])) as parent:
            parent_id = api["identity"](parent)
            with api["owned"](api["child"](parent, sibling, create=True, writable=True)) as prepared:
                api["write"](prepared, proposed)
                def snapshot():
                    return {"root_metadata": api["observed"](root_handle),
                            "parent_metadata": api["observed"](parent),
                            "target": observe_entry(parent, target),
                            "sibling": observe_entry(parent, sibling),
                            "protected": observe_entry(parent, "protected.txt")}

                before = snapshot()
                item["before"] = before
                if (before["root_metadata"]["identity"] != root_id or
                    before["parent_metadata"]["identity"] != parent_id
                    or before["target"]["sha256"] != _digest(old)
                    or before["sibling"]["sha256"] != _digest(proposed)
                    or before["protected"]["sha256"] != _digest(protected)):
                    item["outcome"] = "preimage-invalid"
                    raise ValueError("independent case preimage disagrees")
                original_cwd = Path.cwd()
                try:
                    if case["root"] == "null":
                        # NULL-root control cannot write relative to the repo
                        # even if Win32 interprets the name against process CWD.
                        os.chdir(path)
                    try:
                        api["replace"](prepared, parent, target, item.setdefault("request", {}), case)
                    except ProbeError as exc:
                        item["dispatch"] = {"status": "rejected", "kind": exc.kind,
                                            "code": exc.code, "message": str(exc)}
                    except Exception as exc:
                        item["dispatch"] = {"status": "unexpected_exception",
                                            "type": type(exc).__name__, "message": str(exc)}
                    else:
                        item["dispatch"] = {"status": "completed"}
                finally:
                    os.chdir(original_cwd)
                try:
                    after = snapshot()
                except Exception as exc:
                    item["after_observation_error"] = {"type": type(exc).__name__,
                                                       "message": str(exc)}
                    item["outcome"] = "effects-unknown"
                    break
                item["after"] = after
                stable_directory_fields = ("identity", "attributes", "number_of_links",
                                           "is_directory", "dacl_sddl_sha256")
                authority_stable = (
                    all(after["root_metadata"][field] == before["root_metadata"][field]
                        for field in stable_directory_fields) and
                    all(after["parent_metadata"][field] == before["parent_metadata"][field]
                        for field in stable_directory_fields) and
                    after["protected"] == before["protected"])
                request = item.get("request", {})
                if request.get("nonfinal"):
                    item["outcome"] = "effects-unknown"
                    break
                if item["dispatch"]["status"] == "rejected":
                    if (authority_stable and after["target"] == before["target"]
                        and after["sibling"] == before["sibling"]):
                        item["outcome"] = "clean-rejection"
                        continue
                    item["outcome"] = "effects-unknown"
                    break
                if item["dispatch"]["status"] != "completed":
                    item["outcome"] = "effects-unknown"
                    break
                original = before["target"]["metadata"]
                prepared_metadata = before["sibling"]["metadata"]
                target_after = after["target"]
                verified = (authority_stable and after["sibling"] is None and
                    target_after is not None and target_after["sha256"] == _digest(proposed)
                    and target_after["metadata"]["identity"] == prepared_metadata["identity"]
                    and target_after["metadata"]["identity"] != original["identity"]
                    and target_after["metadata"]["attributes"] == original["attributes"]
                    and target_after["metadata"]["dacl_sddl_sha256"] == original["dacl_sddl_sha256"])
                if not verified:
                    item["outcome"] = "effects-unknown"
                    break
                item["outcome"] = "verified-after-image"
                if case["api"] == "nt" and case["root"] == "parent":
                    receipt["handle_relative_observed_cases"].append(case["id"])
                else:
                    item["qualification"] = "diagnostic-only"

    if any(item.get("outcome") == "effects-unknown" for item in receipt["rename_cases"]):
        raise ValueError("a diagnostic case had unknown effects")
    if not receipt["handle_relative_observed_cases"]:
        raise ValueError("no retained-parent native rename verified")
    receipt["qualification"] = "observed native primitive only; no Windows effects backend"


def _probe(receipt: dict):
    api = _windows_api()
    receipt["abi"] = {"pointer_size": ctypes.sizeof(ctypes.c_void_p),
        "rename_info_filename_offset": api["FILE_RENAME_INFO"].FileName.offset,
        "rename_info_struct_size": ctypes.sizeof(api["FILE_RENAME_INFO"]),
        "object_attributes_size": ctypes.sizeof(api["OBJECT_ATTRIBUTES"]),
        "io_status_block_size": ctypes.sizeof(api["IO_STATUS_BLOCK"]),
        "info_class": FILE_RENAME_INFO_EX,
        "nt_extended_info_class": NT_FILE_RENAME_INFORMATION_EX,
        "nt_classic_info_class": NT_FILE_RENAME_INFORMATION,
        "rename_flags": FILE_RENAME_FLAG_REPLACE_IF_EXISTS | FILE_RENAME_FLAG_POSIX_SEMANTICS,
        "nt_object_flags": OBJ_CASE_INSENSITIVE | OBJ_DONT_REPARSE,
        "nt_share_flags": FILE_SHARE_ALL,
        "nt_open_disposition": FILE_OPEN, "nt_create_disposition": FILE_CREATE,
        "nt_directory_options": FILE_OPEN_REPARSE_POINT | FILE_SYNCHRONOUS_IO_NONALERT,
        "nt_file_options": FILE_NON_DIRECTORY_FILE | FILE_OPEN_REPARSE_POINT |
                           FILE_SYNCHRONOUS_IO_NONALERT,
        "nt_directory_access": FILE_READ_ATTRIBUTES | READ_CONTROL | SYNCHRONIZE |
                               FILE_LIST_DIRECTORY,
        "nt_directory_add_file_access": FILE_READ_ATTRIBUTES | READ_CONTROL |
                                        SYNCHRONIZE | FILE_LIST_DIRECTORY |
                                        FILE_ADD_FILE | FILE_TRAVERSE,
        "nt_read_access": FILE_READ_ATTRIBUTES | READ_CONTROL | SYNCHRONIZE |
                          FILE_READ_DATA,
        "nt_write_access": FILE_READ_ATTRIBUTES | READ_CONTROL | SYNCHRONIZE |
                           FILE_READ_DATA | FILE_WRITE_DATA | DELETE}
    receipt["environment"] = _environment_probe()
    with tempfile.TemporaryDirectory(prefix="attune-windows-effects-") as folder:
        root = Path(folder)
        receipt["filesystem"] = api["filesystem"](root)
        if receipt["filesystem"].upper() != "NTFS":
            raise ValueError("scratch filesystem is not NTFS")
        parent_path = root / "Unicode é space"
        parent_path.mkdir()
        target = "target-é.txt"
        old, proposed, protected = b"old synthetic\n", b"new synthetic\n", b"protected\n"
        (parent_path / target).write_bytes(old)
        (parent_path / "protected.txt").write_bytes(protected)
        # Only the scratch root starts with a path-based bootstrap handle.
        with api["owned"](api["directory"](root)) as root_handle:
            root_before = api["identity"](root_handle)
            with api["owned"](api["child"](root_handle, parent_path.name, directory=True)) as parent:
                parent_before = api["identity"](parent)
                parent_metadata = api["observed"](parent)
                if not parent_metadata["is_directory"]:
                    raise ValueError("parent is not a directory")
                if parent_metadata["attributes"] & FILE_ATTRIBUTE_REPARSE_POINT:
                    raise ValueError("parent is a reparse point")
                with api["owned"](api["child"](parent, target)) as old_handle:
                    before = api["require_singly_linked_file"](old_handle)
                    if api["read"](old_handle, len(old)) != old:
                        raise ValueError("before bytes disagree with retained handle")
                    link = parent_path / "linked.txt"
                    os.link(parent_path / target, link)
                    try:
                        linked = api["observed"](old_handle)
                        if linked["number_of_links"] < 2:
                            raise ValueError("hardlink was not detectable")
                        try:
                            api["require_singly_linked_file"](old_handle)
                        except ValueError:
                            pass
                        else:
                            raise ValueError("eligible-file check accepted a multiply linked target")
                        receipt["hardlink_refusal"] = {"observed_links": linked["number_of_links"],
                            "rejected_before_write": True}
                    finally:
                        link.unlink()
                    if api["require_singly_linked_file"](old_handle)["number_of_links"] != 1:
                        raise ValueError("hardlink cleanup was not observed")
                # Report a missing OS symlink privilege as incomplete, not pass.
                symlink = parent_path / "link.txt"
                try:
                    os.symlink(target, symlink)
                except OSError as exc:
                    receipt["reparse_refusal"] = {"status": "unavailable",
                                                   "winerror": getattr(exc, "winerror", None)}
                    raise ValueError("reparse refusal not observed") from exc
                try:
                    with api["owned"](api["child"](parent, symlink.name)) as link_handle:
                        attributes = api["observed"](link_handle)["attributes"]
                        if not attributes & FILE_ATTRIBUTE_REPARSE_POINT:
                            raise ValueError("final reparse point was followed")
                        receipt["reparse_refusal"] = {"status": "observed",
                            "attributes": attributes, "rejected_before_write": True}
                except ProbeError as exc:
                    if exc.kind != "ntstatus" or exc.code != STATUS_REPARSE_POINT_ENCOUNTERED:
                        raise
                    # OBJ_DONT_REPARSE may reject before returning a handle.
                    receipt["reparse_refusal"] = {"status": "observed",
                        "error": {"kind": exc.kind, "code": exc.code}, "rejected_before_write": True}
                finally:
                    symlink.unlink()
                receipt["leaf_refusal"] = []
                for unsafe in ("sub\\file", "target:stream", "..", "trailing."):
                    try:
                        _leaf(unsafe)
                    except ValueError:
                        receipt["leaf_refusal"].append(unsafe)
                if len(receipt["leaf_refusal"]) != 4:
                    raise ValueError("unsafe leaf accepted")
                if (api["identity"](parent) != parent_before or
                    api["identity"](root_handle) != root_before):
                    raise ValueError("preflight ancestor identity changed")
                _rename_matrix(root, root_handle, api, receipt)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = {"schema": "windows-effects-rename-matrix-v1", "status": "unsupported",
        "os": platform.platform(), "release": platform.version(),
        "python": sys.version, "executable": str(Path(sys.executable).absolute()),
        "limits": ["No power-loss durability proof", "No nondefault ACL preservation proof",
                   "No production feature/repair integration or hostile concurrent writer proof"]}
    try:
        repo_root = Path(__file__).resolve().parents[2]
        workflow = repo_root / ".github/workflows/windows-effects-primitive.yml"
        probe_fingerprint = _source_fingerprint(Path(__file__))
        workflow_fingerprint = _source_fingerprint(workflow)
        receipt["artifacts"] = {"probe_sha256": probe_fingerprint["executed_sha256"],
            "probe_source": probe_fingerprint,
            "executable_sha256": _digest(Path(sys.executable).read_bytes()),
            "workflow_sha256": workflow_fingerprint["executed_sha256"],
            "workflow_source": workflow_fingerprint,
            "github_sha": os.environ.get("GITHUB_SHA")}
        if os.name != "nt":
            raise RuntimeError("real Windows required; no simulated result")
        _probe(receipt)
        receipt["status"] = "observed"
    except Exception as exc:
        receipt["error"] = {"type": type(exc).__name__, "message": str(exc)}
        if isinstance(exc, ProbeError):
            receipt["error"].update(kind=exc.kind, code=exc.code)
        receipt["traceback"] = traceback.format_exc(limit=5)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "receipt": str(args.output),
                      "error": receipt.get("error")}))
    return 0 if receipt["status"] == "observed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
