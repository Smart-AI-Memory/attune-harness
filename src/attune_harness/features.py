"""Optional local feature contracts; importing this module needs no extras."""

import importlib
import json
import os
import tempfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from uuid import uuid4


class FeatureUnavailable(RuntimeError):
    """A selected optional capability is absent or not the qualified version."""


def require_feature(distribution: str, module: str, expected: str, extra: str):
    """Load only the explicitly selected, version-qualified integration."""
    try:
        installed = version(distribution)
    except PackageNotFoundError as exc:
        raise FeatureUnavailable(f"Install attune-harness[{extra}]; {distribution} is missing") from exc
    if installed != expected:
        raise FeatureUnavailable(f"{distribution} {installed} is unsupported; install {distribution}=={expected}")
    try:
        return importlib.import_module(module)
    except ImportError as exc:
        raise FeatureUnavailable(f"{distribution} cannot load: {exc}") from exc


def report(operation: str, status: str, **fields) -> dict:
    """Tool-operation envelope, separate from model task completion receipts."""
    return {"schema_version": 1, "request_id": str(uuid4()),
            "operation": operation, "status": status, **fields}


def read_text(path: Path, limit: int = 4 * 1024 * 1024) -> str:
    """Read bounded, regular UTF-8 input; never truncate it into valid evidence."""
    if not path.is_file():
        raise ValueError(f"Not a regular input file: {path}")
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError(f"Input exceeds {limit} bytes: {path}")
    return raw.decode('utf-8')


def output_path(path: Path, protected: tuple[Path, ...] = ()) -> Path:
    """Refuse destructive destinations before running a feature or writing."""
    if path.is_symlink():
        raise ValueError("Output cannot be a symlink")
    target = path.resolve()
    if target.suffix.lower() != '.json':
        raise ValueError("Output must be a .json report")
    if any(part in {'.git', '.hg', '.svn'} for part in target.parts):
        raise ValueError("Output cannot target repository metadata")
    if target in {item.resolve() for item in protected}:
        raise ValueError("Output must not overwrite an input")
    if not target.parent.is_dir() or (target.exists() and not target.is_file()):
        raise ValueError("Output requires an existing directory and regular file destination")
    return target


def write_report(path: Path, value: dict, protected: tuple[Path, ...] = ()) -> None:
    """Atomically publish JSON locally; caller explicitly chooses the path."""
    target = output_path(path, protected)
    payload = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n'
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent, delete=False) as stream:
            name = stream.name
            stream.write(payload)
        os.replace(name, target)
    finally:
        if name is not None and Path(name).exists():
            Path(name).unlink()
