"""Capture preparation refuses path and pointer widening; raw bytes survive."""

import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import zipfile

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import compat_capture  # noqa: E402
from compat_capture import capture, relocate_paths  # noqa: E402


PROVENANCE = {"distribution": "attune-harness", "version": "0.0-test",
              "wheel_sha256": "0" * 64, "writer_source_commit": "1" * 40,
              "verified_package_files": 1}


def test_capture_preserves_raw_bytes_and_hashes(tmp_path):
    root = tmp_path / "source"
    source = root / "task" / "record.json"
    source.parent.mkdir(parents=True)
    raw = b'{"schema_version":1,"text":"\xc3\xa9"}\r\n'
    source.write_bytes(raw)
    output = tmp_path / "capture"
    manifest = capture(root, ["task/record.json"], output, PROVENANCE)
    assert source.read_bytes() == raw
    assert (output / "files/task/record.json").read_bytes() == raw
    assert manifest["files"]["task/record.json"] == {
        "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    assert manifest["record_writer"] == "not_verified_by_capture_tool"
    assert json.loads((output / "manifest.json").read_text()) == manifest
    with pytest.raises(FileExistsError):
        capture(root, ["task/record.json"], output, PROVENANCE)


@pytest.mark.parametrize("name", ["../secret", "/etc/passwd", "task/../record.json",
                                      "task\\record.json", "task//record.json", "C:/x", "C:x"])
def test_capture_refuses_escape_or_noncanonical_names(tmp_path, name):
    root = tmp_path / "source"
    root.mkdir()
    with pytest.raises(ValueError):
        capture(root, [name], tmp_path / "out", PROVENANCE)
    assert not (tmp_path / "out").exists()


def test_capture_refuses_symlink_and_duplicate_files(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "outside").symlink_to(tmp_path)
    with pytest.raises(ValueError, match="symlink"):
        capture(root, ["outside/file"], tmp_path / "out", PROVENANCE)
    with pytest.raises(ValueError, match="distinct"):
        capture(root, ["a", "a"], tmp_path / "out", PROVENANCE)
    assert not (tmp_path / "out").exists()


def test_relocation_changes_only_approved_pointer_and_leaves_input_untouched(tmp_path):
    old = tmp_path / "old"
    new = tmp_path / "new"
    original = {"record_path": str(old / "task/record.json"),
                "request": {"project_root": str(old / "project"), "goal": "keep bytes"}}
    moved = relocate_paths(original, allowed={"/record_path"}, requested={"/record_path"},
                           old_root=old, new_root=new)
    assert moved == {"record_path": str(new / "task/record.json"),
                     "request": original["request"]}
    assert original["record_path"] == str(old / "task/record.json")


def test_relocation_refuses_unknown_pointer_and_path_escape(tmp_path):
    old = tmp_path / "old"
    new = tmp_path / "new"
    value = {"record_path": str(old / "task/record.json"),
             "other": str(tmp_path / "outside")}
    with pytest.raises(ValueError, match="Unknown"):
        relocate_paths(value, allowed={"/record_path"}, requested={"/other"},
                       old_root=old, new_root=new)
    with pytest.raises(ValueError, match="escapes"):
        relocate_paths(value, allowed={"/other"}, requested={"/other"},
                       old_root=old, new_root=new)
    with pytest.raises(ValueError, match="Missing"):
        relocate_paths(value, allowed={"/missing"}, requested={"/missing"},
                       old_root=old, new_root=new)
    assert value["record_path"] == str(old / "task/record.json")


@pytest.mark.parametrize("pointer", ["/paths/-1", "/paths/01", "/paths/~2", "/paths/~"])
def test_relocation_refuses_noncanonical_array_pointer(tmp_path, pointer):
    old = tmp_path / "old"
    new = tmp_path / "new"
    value = {"paths": [str(old / "one"), str(old / "two")]}
    with pytest.raises(ValueError):
        relocate_paths(value, allowed={pointer}, requested={pointer}, old_root=old, new_root=new)
    assert value["paths"] == [str(old / "one"), str(old / "two")]


def test_wheel_provenance_requires_installed_and_source_bytes(tmp_path, monkeypatch):
    wheel = tmp_path / "attune_harness-0.0_test-py3-none-any.whl"
    packages = ("attune_harness", "attune_voyage_plugin")
    for package in packages:
        source = tmp_path / "repo/src" / package / "__init__.py"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"writer = 1\n")
        installed = tmp_path / "installed" / package / "__init__.py"
        installed.parent.mkdir(parents=True)
        installed.write_bytes(source.read_bytes())
    with zipfile.ZipFile(wheel, "w") as archive:
        for package in packages:
            archive.writestr(f"{package}/__init__.py", b"writer = 1\n")
        archive.writestr("attune_harness-0.0_test.dist-info/METADATA",
                         "Name: attune-harness\nVersion: 0.0-test\n")

    class Distribution:
        version = "0.0-test"

        def read_text(self, name):
            return None

        def locate_file(self, name):
            return tmp_path / "installed" / name

    monkeypatch.setattr(compat_capture.metadata, "distribution", lambda _: Distribution())
    monkeypatch.setattr(compat_capture, "_git_head", lambda _: "a" * 40)
    monkeypatch.setattr(compat_capture.util, "find_spec", lambda package: SimpleNamespace(
        origin=str(tmp_path / "installed" / package / "__init__.py")))
    provenance = compat_capture.wheel_provenance(wheel, tmp_path / "repo")
    assert provenance["wheel_sha256"] == hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert provenance["writer_source_commit"] == "a" * 40
    assert provenance["verified_package_files"] == 2
    installed = tmp_path / "installed/attune_harness/__init__.py"
    installed.write_bytes(b"drift\n")
    with pytest.raises(ValueError, match="Installed package differs"):
        compat_capture.wheel_provenance(wheel, tmp_path / "repo")
    installed.write_bytes(source.read_bytes())
    source = tmp_path / "repo/src/attune_harness/__init__.py"
    source.write_bytes(b"different source\n")
    with pytest.raises(ValueError, match="Source checkout differs"):
        compat_capture.wheel_provenance(wheel, tmp_path / "repo")


def test_wheel_provenance_refuses_editable_and_shadowed_import(tmp_path, monkeypatch):
    wheel = tmp_path / "attune_harness-0.0_test-py3-none-any.whl"
    for package in ("attune_harness", "attune_voyage_plugin"):
        source = tmp_path / "repo/src" / package / "__init__.py"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"same bytes\n")
        installed = tmp_path / "installed" / package / "__init__.py"
        installed.parent.mkdir(parents=True)
        installed.write_bytes(source.read_bytes())
    with zipfile.ZipFile(wheel, "w") as archive:
        for package in ("attune_harness", "attune_voyage_plugin"):
            archive.writestr(f"{package}/__init__.py", b"same bytes\n")
        archive.writestr("attune_harness-0.0_test.dist-info/METADATA",
                         "Name: attune-harness\nVersion: 0.0-test\n")

    class Distribution:
        version = "0.0-test"
        editable = False

        def read_text(self, name):
            return '{"dir_info":{"editable":true}}' if self.editable else None

        def locate_file(self, name):
            return tmp_path / "installed" / name

    distribution = Distribution()
    monkeypatch.setattr(compat_capture.metadata, "distribution", lambda _: distribution)
    monkeypatch.setattr(compat_capture, "_git_head", lambda _: "a" * 40)
    monkeypatch.setattr(compat_capture.util, "find_spec", lambda package: SimpleNamespace(
        origin=str(tmp_path / "installed" / package / "__init__.py")))
    distribution.editable = True
    with pytest.raises(ValueError, match="Editable"):
        compat_capture.wheel_provenance(wheel, tmp_path / "repo")
    distribution.editable = False
    monkeypatch.setattr(compat_capture.util, "find_spec", lambda package: SimpleNamespace(
        origin=str(tmp_path / "repo/src" / package / "__init__.py")))
    with pytest.raises(ValueError, match="shadowed"):
        compat_capture.wheel_provenance(wheel, tmp_path / "repo")
