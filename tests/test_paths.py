"""Path validation: containment, system directories, and the Windows rules.

Carried from Attune AI's tests/unit/security/test_path_traversal.py and
test_path_validation_mutation_kills.py (b89f7953f). There the Windows branch was
only ever simulated on POSIX by forcing sys.platform. Here the rules are a pure
function tested with real Windows path strings on every platform, and the
end-to-end cases run for real on each platform's own CI job.
"""

import sys
from pathlib import Path

import pytest

from attune_harness import paths
from attune_harness.paths import _protected, validate_file_path

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="POSIX system directories")
windows_only = pytest.mark.skipif(sys.platform != "win32", reason="needs a real Windows filesystem")


# ---- input and containment: the same on every platform --------------------


@pytest.mark.parametrize("bad", ["", None, 123])
def test_empty_or_non_string_path_is_refused_with_the_exact_message(bad):
    with pytest.raises(ValueError) as refused:
        validate_file_path(bad)
    assert str(refused.value) == "path must be a non-empty string"


@pytest.mark.parametrize("bad", ["config\x00.json", "file.txt\x00.jpg", "\x00/etc/passwd"])
def test_null_bytes_are_refused_with_the_exact_message(bad):
    with pytest.raises(ValueError) as refused:
        validate_file_path(bad)
    assert str(refused.value) == "path contains null bytes"


@pytest.mark.parametrize("error", [OSError("boom"), RuntimeError("loop")])
def test_a_path_that_cannot_be_resolved_is_a_value_error(monkeypatch, error):
    def fail(self, *args, **kwargs):
        raise error

    monkeypatch.setattr(paths.Path, "resolve", fail)
    with pytest.raises(ValueError, match=r"^Invalid path: (boom|loop)$"):
        validate_file_path("some/relative/path")


def test_valid_paths_come_back_resolved(tmp_path):
    for name in ("config.yaml", "subdir/config.json", "data-2026-01-24.txt"):
        result = validate_file_path(str(tmp_path / name))
        assert isinstance(result, Path) and result == (tmp_path / name).resolve()


def test_allowed_dir_admits_what_is_inside_and_refuses_the_rest(tmp_path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    inside = validate_file_path(str(allowed / "file.txt"), allowed_dir=str(allowed))
    assert inside.parent == allowed.resolve()
    for outside in (
        tmp_path / "outside.txt",
        allowed / ".." / "outside.txt",
        allowed / ".." / ".." / "etc" / "passwd",
    ):
        with pytest.raises(ValueError, match="outside allowed directory") as refused:
            validate_file_path(str(outside), allowed_dir=str(allowed))
        assert "Operations are restricted to the workspace" in str(refused.value)


def test_a_sibling_whose_name_starts_like_the_allowed_dir_is_outside(tmp_path):
    (tmp_path / "allowed").mkdir()
    with pytest.raises(ValueError, match="outside allowed directory"):
        validate_file_path(
            str(tmp_path / "allowed-other" / "x"), allowed_dir=str(tmp_path / "allowed")
        )


# ---- POSIX system directories ----------------------------------------------


@pytest.mark.parametrize("directory", paths.POSIX_SYSTEM)
def test_every_posix_system_directory_is_named_exactly_and_beneath(directory):
    assert _protected(directory, windows=False) == directory
    assert _protected(directory + "/x", windows=False) == directory


@pytest.mark.parametrize(
    "safe", ["/etcetera/x", "/home/me/etc/plans/x.md", "/usr/local/bin/x", "/binary", "/devices"]
)
def test_posix_names_that_only_look_like_system_directories_are_allowed(safe):
    assert _protected(safe, windows=False) is None


@posix_only
@pytest.mark.parametrize(
    "path", ["/sys/kernel", "/proc/version", "/dev/zero", "/usr/bin/x", "/sbin/x"]
)
def test_posix_system_paths_are_refused_end_to_end(path):
    with pytest.raises(ValueError, match=r"^Cannot write to system directory: /"):
        validate_file_path(path)


# ---- Windows rules: real Windows strings, on every platform -----------------


@pytest.mark.parametrize(
    "path, named",
    [
        ("C:\\Windows\\System32\\cmd.exe", "windows\\system32"),
        ("C:\\Windows\\SysWOW64\\file.txt", "windows\\syswow64"),
        ("C:\\Windows\\System\\x", "windows\\system"),
        ("c:\\windows\\SYSTEMAPPS\\x", "windows\\systemapps"),
        ("C:\\Program Files\\app\\config.txt", "program files"),
        ("D:\\Program Files (x86)\\app\\x", "program files (x86)"),
        ("\\\\?\\C:\\Windows\\System32\\x", "windows\\system32"),
    ],
)
def test_windows_system_directories_are_refused_on_any_drive(path, named):
    assert _protected(path, windows=True) == named


@pytest.mark.parametrize("name", paths.POSIX_NAMES_ON_WINDOWS)
def test_a_posix_system_path_given_on_windows_is_refused_at_the_drive_root(name):
    # /etc/passwd resolves to C:\etc\passwd on Windows.
    assert _protected(f"C:\\{name}\\passwd", windows=True) == name
    assert _protected(f"C:\\{name}", windows=True) == name


@pytest.mark.parametrize(
    "safe",
    [
        "C:\\repo\\etc\\plans\\x.md",
        "C:\\some\\etc",
        "C:\\Users\\me\\dev\\project\\plan.md",
        "D:\\work\\sys\\proc\\dev\\x",
        "D:\\work\\Program Files\\x",
        "C:\\projects\\windows\\system32\\notes.md",
        "C:\\Windows",
        "C:\\Windows\\Temp\\x",
        "\\\\?\\C:\\repo\\etc\\x",
        "\\\\?\\UNC\\server\\share\\repo\\etc\\x",
        "\\\\server\\share\\repo\\dev\\x",
        "C:\\etcetera\\x",
        "C:\\",
    ],
)
def test_the_same_names_deeper_in_a_windows_path_are_allowed(safe):
    # The original refused all of these by substring.
    assert _protected(safe, windows=True) is None


@pytest.mark.parametrize(
    "path, named",
    [
        ("\\\\?\\GLOBALROOT\\Device\\HarddiskVolume2\\Windows\\System32\\evil.dll", "windows\\system32"),
        ("\\\\.\\GLOBALROOT\\Device\\HarddiskVolume2\\Program Files\\x", "program files"),
        ("\\\\?\\Volume{b75e2c83-0000-0000-0000-602200000000}\\Windows\\System32\\x", "windows\\system32"),
        ("\\\\?\\UNC\\server\\share\\Program Files\\x", "program files"),
        ("C:Windows\\System32\\x", "windows\\system32"),
        ("Program Files\\x", "program files"),
        ("repo\\etc\\passwd", "etc"),
    ],
)
def test_with_no_drive_root_to_count_from_a_protected_name_anywhere_refuses(path, named):
    # Device paths, drive-relative and relative strings: as strict as the original.
    assert _protected(path, windows=True) == named


@windows_only
def test_windows_refuses_system_paths_and_admits_a_repository_end_to_end(tmp_path):
    for path in ("C:\\Windows\\System32\\x.txt", "C:\\Program Files\\x.txt", "/etc/passwd"):
        with pytest.raises(ValueError, match=r"^Cannot write to system directory"):
            validate_file_path(path)
    nested = tmp_path / "repo" / "etc" / "dev" / "plan.md"
    assert validate_file_path(str(nested)) == nested.resolve()
