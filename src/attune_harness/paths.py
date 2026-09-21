"""Refuse paths that leave an allowed directory or land in a system directory.

Carried from Attune AI's ``attune/security/path_validation.py`` (branch
``codex/shared-memory-adoption`` at ``b89f7953f``), where it was the private
``_validate_file_path``. The Windows check is reworked: see ``_protected``.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import sys
from pathlib import Path, PureWindowsPath

POSIX_SYSTEM = (
    "/etc",
    "/sys",
    "/proc",
    "/dev",
    "/private/etc",  # macOS: /etc is a symlink to /private/etc
    "/private/var/root",  # macOS: root's home directory
    "/usr/bin",
    "/usr/sbin",
    "/bin",
    "/sbin",
)
WINDOWS_PROGRAMS = ("program files", "program files (x86)")
# A POSIX system path given on Windows resolves under the current drive's root:
# /etc/passwd becomes C:\etc\passwd. Refuse it there, and only there.
POSIX_NAMES_ON_WINDOWS = ("etc", "sys", "proc", "dev")


def _protected(resolved: str, *, windows: bool) -> str | None:
    """Name the system directory a resolved path is in, or return None.

    On Windows the original matched substrings anywhere in the path, so
    ``C:\\repo\\etc\\plans\\x.md`` and ``D:\\work\\Program Files\\x`` were refused.
    This compares whole components, counted from the drive's root.
    """
    if not windows:
        for directory in POSIX_SYSTEM:
            if resolved == directory or resolved.startswith(directory + "/"):
                return directory
        return None
    parts = [part.lower() for part in PureWindowsPath(resolved).parts[1:]]
    if not parts:
        return None
    if parts[0] in WINDOWS_PROGRAMS or parts[0] in POSIX_NAMES_ON_WINDOWS:
        return parts[0]
    # System, System32, SystemApps and the rest: the original's substring
    # "\windows\system" covered every name with this prefix.
    if (
        parts[0] == "windows"
        and len(parts) > 1
        and (parts[1].startswith("system") or parts[1] == "syswow64")
    ):
        return f"{parts[0]}\\{parts[1]}"
    return None


def validate_file_path(path: str, allowed_dir: str | None = None) -> Path:
    """Resolve a path, or raise ValueError if it is unsafe to read or write.

    With ``allowed_dir``, the resolved path must be inside it.
    """
    if not path or not isinstance(path, str):
        raise ValueError("path must be a non-empty string")
    if "\x00" in path:
        raise ValueError("path contains null bytes")
    try:
        resolved = Path(path).resolve()
    except (OSError, RuntimeError) as error:
        raise ValueError(f"Invalid path: {error}") from error
    if allowed_dir:
        allowed = Path(allowed_dir).resolve()
        if not resolved.is_relative_to(allowed):
            raise ValueError(
                f"Path '{resolved}' is outside allowed directory '{allowed}'. "
                "Operations are restricted to the workspace."
            )
    directory = _protected(str(resolved), windows=sys.platform == "win32")
    if directory is not None:
        raise ValueError(f"Cannot write to system directory: {directory}")
    return resolved
