"""Conservative Git input capture and explainable pytest selection."""

import ast
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess

from .review_contract import digest

MAX_FILES = 20000
MAX_BYTES = 256 * 1024 * 1024


def file_hash(path: Path) -> str:
    """Hash a bounded regular file without following a leaf symlink."""
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Expected regular file: {path}")
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("File exceeds snapshot limit")
    return hashlib.sha256(data).hexdigest()


def relative_path(value: str) -> str:
    """Validate a portable repository-relative path."""
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or "\\" in value
        or "\x00" in value
        or any(p in (".", "..", ".git", ".hg", ".svn") for p in value.split("/"))
        or str(path) != value
        or value.startswith("-")
    ):
        raise ValueError(f"Invalid relative input path: {value!r}")
    return value


def git(root: Path, *args: str) -> bytes:
    """Read Git state with bounded runtime; never mutate the index."""
    result = subprocess.run(
        [
            "git",
            "--no-optional-locks",
            "-c",
            "diff.autoRefreshIndex=false",
            "-C",
            str(root),
            *args,
        ],
        capture_output=True,
        timeout=20,
    )
    if result.returncode:
        raise ValueError(
            "Git input unavailable: " + result.stderr.decode(errors="replace")[:500]
        )
    if len(result.stdout) > 8 * 1024 * 1024:
        raise ValueError("Git inventory exceeds snapshot limit")
    return result.stdout


def capture(root: Path) -> dict:
    """Capture all tracked and nonignored untracked regular working-tree inputs."""
    root = root.resolve(strict=True)
    if (
        Path(os.fsdecode(git(root, "rev-parse", "--show-toplevel")).strip()).resolve()
        != root
    ):
        raise ValueError("Project must be the Git repository root")
    head = git(root, "rev-parse", "HEAD").decode().strip()
    index = hashlib.sha256(git(root, "ls-files", "--stage", "-z")).hexdigest()
    changed = sorted(
        set(
            os.fsdecode(p)
            for p in (
                git(root, "diff", "--name-only", "HEAD", "-z")
                + git(root, "ls-files", "--others", "--exclude-standard", "-z")
            ).split(b"\0")
            if p
        )
    )
    paths = sorted(
        set(changed)
        | set(
            os.fsdecode(p)
            for p in git(
                root, "ls-files", "--cached", "--others", "--exclude-standard", "-z"
            ).split(b"\0")
            if p
        )
    )
    if len(paths) > MAX_FILES:
        raise ValueError("Too many files for the qualified snapshot profile")
    files, total = {}, 0
    for name in paths:
        relative_path(name)
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError(f"Symlink or escaped input is unsupported: {name}")
        if not path.exists():
            files[name] = None
            continue
        if not path.is_file():
            raise ValueError(f"Nonregular input/submodule is unsupported: {name}")
        size = path.stat().st_size
        total += size
        if total > MAX_BYTES:
            raise ValueError("Working-tree snapshot exceeds 256 MiB")
        files[name] = {
            "sha256": file_hash(path),
            "size": size,
            "mode": stat.S_IMODE(path.stat().st_mode),
        }
    identity = root.stat()
    return {
        "root": str(root),
        "root_identity": [identity.st_dev, identity.st_ino],
        "head": head,
        "index_sha256": index,
        "changed_paths": changed,
        "files": files,
        "bytes": total,
    }


def expand(paths: list[str], files: dict, *, required: bool = True) -> list[str]:
    """Expand explicit file/directory inputs only within the captured inventory."""
    found = set()
    for value in paths:
        name = relative_path(value)
        matches = [p for p in files if p == name or p.startswith(name + "/")]
        if required and not matches:
            raise ValueError(f"Path is absent from captured inputs: {name}")
        found.update(matches)
    return sorted(found)


def module_name(path: str) -> str:
    """Return a source-layout module hint, never a completeness claim."""
    value = path.removeprefix("src/").removesuffix(".py").replace("/", ".")
    return value.removesuffix(".__init__")


def select(
    root: Path,
    snapshot: dict,
    scope: list[str],
    tests: list[str] | None,
    test_root: str = "tests",
) -> dict:
    """Show import/name associations and conservative or explicit test scope."""
    changed = sorted(
        set(expand(scope, snapshot["files"])) & set(snapshot["changed_paths"])
    )
    if not changed:
        raise ValueError(
            "Explicit scope must contain a working-tree change against HEAD"
        )
    test_root = relative_path(test_root)
    candidates = [
        p
        for p, info in snapshot["files"].items()
        if info
        and p.endswith(".py")
        and p.startswith(test_root + "/")
        and (Path(p).name.startswith("test_") or Path(p).stem.endswith("_test"))
    ]
    modules = {
        p: module_name(p)
        for p, info in snapshot["files"].items()
        if info and p.endswith(".py")
    }
    imports = {}
    uncertain = []
    for path in modules:
        try:
            tree = ast.parse((root / path).read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeError):
            uncertain.append(path)
            continue
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                prefix = node.module or ""
                if node.level:
                    parent = modules[path].split(".")[:-1]
                    prefix = ".".join(
                        parent[: len(parent) - node.level + 1]
                        + ([prefix] if prefix else [])
                    )
                names.add(prefix)
                names.update(prefix + "." + alias.name for alias in node.names)
        imports[path] = names
    impacted = set(changed)
    while True:
        changed_modules = {modules[p] for p in impacted if p in modules}
        addition = {
            p
            for p, names in imports.items()
            if any(
                name == module or name.startswith(module + ".")
                for name in names
                for module in changed_modules
            )
        }
        if addition <= impacted:
            break
        impacted.update(addition)
    stems = {Path(p).stem for p in changed}
    associations = {
        p: ("import relationship" if p in impacted else "filename hint")
        for p in candidates
        if p in impacted or Path(p).stem.removeprefix("test_") in stems
    }
    if tests:
        selected_set = set()
        for target in tests:
            relative_path(target)
            if target != test_root and not target.startswith(test_root + "/"):
                raise ValueError("Explicit tests must be under --test-root")
            if target in snapshot["files"] and target not in candidates:
                raise ValueError(
                    "An explicitly named test file must be an existing pytest candidate"
                )
            selected_set.update(
                p for p in expand([target], snapshot["files"]) if p in candidates
            )
        selected = sorted(selected_set)
        reason = "Explicit operator-selected tests; broader test coverage is excluded."
        mode = "explicit"
    else:
        selected = sorted(candidates)
        reason = f"Conservative broader fallback to {test_root}/: static associations do not prove a complete narrower set."
        mode = "broader_fallback"
    return {
        "scope": list(scope),
        "changed_files": changed,
        "mode": mode,
        "reason": reason,
        "test_root": test_root,
        "selected": selected,
        "associations": associations,
        "excluded": sorted(set(candidates) - set(selected)),
        "missing_evidence": [
            "Selection does not establish complete behavioral coverage.",
            "Discovery covers default test_*.py / *_test.py files under the named test root; custom collectors are not qualified.",
            "Git metadata, ignored files and external dependencies are not copied.",
        ]
        + ([f"Unparsed Python inputs: {len(uncertain)}"] if uncertain else []),
    }


def copy_inputs(snapshot: dict, destination: Path) -> None:
    """Materialize accepted bytes in a new directory without touching the checkout."""
    destination.mkdir()
    for name, info in snapshot["files"].items():
        if info is None:
            continue
        source = Path(snapshot["root"]) / name
        if file_hash(source) != info["sha256"]:
            raise ValueError(f"Stale input during copy: {name}")
        target = destination / relative_path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != info["sha256"]:
            raise ValueError(f"Input changed while copying: {name}")
        target.write_bytes(data)
        target.chmod(info["mode"])


def check_copy(snapshot: dict, destination: Path) -> None:
    """Check captured test/source/config bytes before trusting an execution receipt."""
    for name, info in snapshot["files"].items():
        path = destination / relative_path(name)
        if info is None:
            if path.exists():
                raise ValueError(f"Deleted input reappeared in execution tree: {name}")
        elif file_hash(path) != info["sha256"]:
            raise ValueError(f"Execution input changed: {name}")


def fresh(snapshot: dict) -> bool:
    """Return whether the original repository still has the accepted content."""
    # Git's name-only hint may include unchanged bytes after timestamps move
    # when index refresh is disabled. The complete file/HEAD/index inventory
    # already binds every input; that selection hint is not input identity.
    current = capture(Path(snapshot["root"]))
    return digest({k: v for k, v in current.items() if k != "changed_paths"}) == digest(
        {k: v for k, v in snapshot.items() if k != "changed_paths"}
    )
