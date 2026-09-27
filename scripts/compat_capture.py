"""Prepare byte-preserved compatibility captures from an installed wheel.

This is capture infrastructure, not a 1.0 fixture writer. Call it from the
environment where the selected wheel is installed. It never runs Harness.
"""

from __future__ import annotations

import argparse
import copy
from email.parser import BytesParser
import hashlib
from importlib import metadata, util
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import zipfile


PACKAGE_ROOTS = ("attune_harness/", "attune_voyage_plugin/")
COMMIT_SHA = re.compile(r"[0-9a-f]{40}\Z")


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or str(path) != name or
            any(part in ("", ".", "..") for part in path.parts) or "\\" in name):
        raise ValueError(f"Capture path must be canonical and relative: {name!r}")
    return path


def _regular_under(root: Path, name: str) -> Path:
    relative = _relative(name)
    path = root
    for part in relative.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f"Capture path crosses a symlink: {name}")
    if not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f"Capture path is not a regular file: {name}")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Capture path escapes its root: {name}")
    return path


def _git_head(repo: Path) -> str:
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()
    if not COMMIT_SHA.fullmatch(head):
        raise ValueError("Source checkout has no full commit SHA")
    dirty = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                           check=True, capture_output=True, text=True).stdout
    if dirty:
        raise ValueError("Source checkout must be clean for capture provenance")
    return head


def wheel_provenance(wheel: Path, repo: Path) -> dict:
    """Verify the installed package and checked-out writer bytes against a wheel."""
    commit = _git_head(repo)
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1 or len(names) != len(set(names)):
            raise ValueError("Wheel has ambiguous metadata or duplicate entries")
        message = BytesParser().parsebytes(archive.read(metadata_names[0]))
        name, version = message.get("Name"), message.get("Version")
        if name != "attune-harness" or not version:
            raise ValueError("Expected an attune-harness wheel with a version")
        installed = metadata.distribution("attune-harness")
        if installed.version != version:
            raise ValueError("Installed distribution version differs from the wheel")
        direct_url = installed.read_text("direct_url.json")
        if direct_url is not None:
            try:
                origin = json.loads(direct_url)
            except (TypeError, ValueError) as exc:
                raise ValueError("Installed distribution has invalid origin metadata") from exc
            if not isinstance(origin, dict) or not isinstance(origin.get("dir_info", {}), dict):
                raise ValueError("Installed distribution has invalid origin metadata")
            if origin.get("dir_info", {}).get("editable") is True:
                raise ValueError("Editable install cannot establish wheel provenance")
        for package in ("attune_harness", "attune_voyage_plugin"):
            entry = f"{package}/__init__.py"
            if entry not in names:
                raise ValueError(f"Wheel lacks package origin: {entry}")
            expected = installed.locate_file(entry)
            if expected.resolve().is_relative_to(repo.resolve()):
                raise ValueError(f"Installed package resolves into source checkout: {package}")
            spec = util.find_spec(package)
            if spec is None or spec.origin is None or Path(spec.origin).resolve() != expected.resolve():
                raise ValueError(f"Imported package is shadowed or absent: {package}")
        checked = []
        for entry in names:
            if not entry.startswith(PACKAGE_ROOTS) or entry.endswith("/"):
                continue
            relative = _relative(entry)
            raw = archive.read(entry)
            installed_path = installed.locate_file(entry)
            if not installed_path.is_file() or installed_path.read_bytes() != raw:
                raise ValueError(f"Installed package differs from wheel: {entry}")
            source = repo / "src" / Path(*relative.parts)
            if not source.is_file() or source.read_bytes() != raw:
                raise ValueError(f"Source checkout differs from wheel: {entry}")
            checked.append(entry)
        if not checked or not any(name.startswith("attune_harness/") for name in checked):
            raise ValueError("Wheel contains no verified Harness package files")
    return {"distribution": name, "version": version, "wheel_sha256": file_digest(wheel),
            "writer_source_commit": commit, "verified_package_files": len(checked)}


def capture(root: Path, names: list[str], output: Path, provenance: dict) -> dict:
    """Copy an explicit file list; preserve bytes and record their SHA-256."""
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Capture root must be a real directory")
    if not names or len(names) != len(set(names)):
        raise ValueError("Capture requires a nonempty list of distinct files")
    sources = {name: _regular_under(root, name) for name in names}
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    files = {}
    for name, source in sorted(sources.items()):
        destination = output / "files" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        raw = source.read_bytes()
        destination.write_bytes(raw)
        files[name] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    manifest = {"schema_version": 1, "capture": "unpublished_candidate_preparation",
                "provenance": provenance, "files": files}
    (output / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n",
                                           encoding="utf-8")
    return manifest


def _at_pointer(value: dict, pointer: str):
    if not pointer.startswith("/") or pointer == "/":
        raise ValueError(f"Invalid JSON pointer: {pointer!r}")
    raw_parts = pointer[1:].split("/")
    if any(re.search(r"~(?![01])", part) for part in raw_parts):
        raise ValueError(f"Invalid JSON pointer escape: {pointer!r}")
    parts = [part.replace("~1", "/").replace("~0", "~") for part in raw_parts]
    def index(part: str) -> int:
        if not re.fullmatch(r"0|[1-9][0-9]*", part):
            raise ValueError(f"Noncanonical JSON pointer array index: {pointer!r}")
        return int(part)
    current = value
    for part in parts[:-1]:
        current = current[index(part)] if isinstance(current, list) else current[part]
    last = index(parts[-1]) if isinstance(current, list) else parts[-1]
    return current, last


def relocate_paths(value: dict, *, allowed: set[str], requested: set[str],
                   old_root: Path, new_root: Path) -> dict:
    """Move only approved path fields in a copy; format-specific digests come later."""
    if not requested or not requested <= allowed:
        raise ValueError("Unknown or empty relocation pointer set")
    old, new = str(old_root), str(new_root)
    if not Path(old).is_absolute() or not Path(new).is_absolute() or old == new:
        raise ValueError("Relocation roots must be distinct absolute paths")
    result = copy.deepcopy(value)
    for pointer in sorted(requested):
        try:
            container, key = _at_pointer(result, pointer)
            original = container[key]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ValueError(f"Missing relocation pointer: {pointer}") from exc
        if not isinstance(original, str) or not Path(original).is_absolute():
            raise ValueError(f"Relocation field is not an absolute path: {pointer}")
        relative = Path(original).relative_to(old_root) if Path(original).is_relative_to(old_root) else None
        if relative is None or ".." in relative.parts:
            raise ValueError(f"Relocation field escapes capture root: {pointer}")
        container[key] = str(new_root / relative)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--capture-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--file", action="append", required=True, dest="files")
    args = parser.parse_args()
    provenance = wheel_provenance(args.wheel, args.repo)
    capture(args.capture_root, args.files, args.output, provenance)


if __name__ == "__main__":
    main()
