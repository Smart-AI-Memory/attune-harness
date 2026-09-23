"""One atomic replace under src/, with the Windows retry (O-59).

``features.replace_file`` retries ``os.replace`` for a bounded time on Windows
while a reader holds the target open; the run store had it, the plan state
writer and the Voyage index writer called ``os.replace`` once. Every writer
goes through it now, and this file keeps it that way.
"""
# qualify: platform

import ast
import json
import os
from pathlib import Path

import pytest

from attune_harness import features, spec_state, voyage_index

# repair.py is the one exception: the effects host replaces through directory
# descriptors (src_dir_fd/dst_dir_fd), POSIX-only by design, and Windows has
# its own windows_effects.replace_file. features.py is the implementation.
ALLOWED = {"features.py": {"os.replace"}, "repair.py": {"os.replace"}}


def _replace_calls(tree):
    """Every call that moves a file over another: os.replace, os.rename, a
    bare ``replace``/``rename`` imported from os, or a one-argument
    ``.replace(target)`` on a value, which is pathlib's, since str.replace
    takes two."""
    imported, modules = {}, {"os"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "os":
            imported.update({alias.asname or alias.name: alias.name for alias in node.names if alias.name in ("replace", "rename")})
        if isinstance(node, ast.Import):
            modules |= {alias.asname or alias.name for alias in node.names if alias.name == "os"}
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id in modules \
                and func.attr in ("replace", "rename"):
            found.append(f"os.{func.attr}")
        elif isinstance(func, ast.Name) and func.id in imported:
            found.append(f"os.{imported[func.id]}")
        elif isinstance(func, ast.Attribute) and func.attr == "replace" and len(node.args) == 1 and not node.keywords:
            found.append("Path.replace")
    return found


def test_every_replace_under_src_goes_through_replace_file():
    root = Path(features.__file__).parent
    offenders = {}
    for path in sorted(root.rglob("*.py")):
        calls = _replace_calls(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        extra = [c for c in calls if c not in ALLOWED.get(path.name, set())]
        if extra:
            offenders[str(path.relative_to(root))] = extra
    assert offenders == {}


def test_the_guard_reads_every_spelling(tmp_path):
    source = (
        "import os\nimport os as _os\nfrom os import replace as move\nfrom pathlib import Path\n"
        "os.replace(a, b)\nos . rename(a, b)\nmove(a, b)\nPath(a).replace(b)\n_os.replace(a, b)\n"
        "text.replace('x', 'y')\n"
    )
    assert _replace_calls(ast.parse(source)) == ["os.replace", "os.rename", "os.replace", "Path.replace", "os.replace"]


class _Refuses:
    """os.replace that refuses ``times`` calls with PermissionError, as Windows
    does while another handle holds the target, then succeeds with the real
    replace, captured before the monkeypatch (a rename would refuse an
    existing target on Windows, and Path.replace would recurse into this)."""

    def __init__(self, times):
        self.times, self.calls, self.real = times, 0, os.replace

    def __call__(self, source, target):
        self.calls += 1
        if self.calls <= self.times:
            raise PermissionError(32, "The process cannot access the file")
        return self.real(source, target)


@pytest.fixture
def refused_twice(monkeypatch):
    refusing = _Refuses(2)
    monkeypatch.setattr(features, "RETRY_REFUSED_REPLACE", True)
    monkeypatch.setattr(features.os, "replace", refusing)
    return refusing


def test_replace_file_retries_a_refused_replace_within_the_bound(tmp_path, refused_twice):
    source, target = tmp_path / "new", tmp_path / "old"
    source.write_text("new"); target.write_text("old")
    features.replace_file(source, target, retry_seconds=1.0)
    assert target.read_text() == "new" and refused_twice.calls == 3


def test_replace_file_gives_up_at_the_bound(tmp_path, refused_twice):
    source, target = tmp_path / "new", tmp_path / "old"
    source.write_text("new"); target.write_text("old")
    with pytest.raises(PermissionError):
        features.replace_file(source, target, retry_seconds=0)
    assert target.read_text() == "old" and refused_twice.calls == 1


def test_plan_state_survives_a_reader_holding_the_plan(tmp_path, refused_twice, monkeypatch):
    monkeypatch.setattr(spec_state, "REPLACE_RETRY_SECONDS", 1.0)
    target = tmp_path / "plan.md"
    target.write_text("old\n", encoding="utf-8")
    spec_state._atomic_write_text(target, "new\r\nline\r\n")
    assert target.read_bytes() == b"new\r\nline\r\n" and refused_twice.calls == 3
    assert [p for p in tmp_path.iterdir()] == [target]


def test_voyage_index_metadata_survives_a_reader_holding_the_file(tmp_path, refused_twice, monkeypatch):
    monkeypatch.setattr(voyage_index, "REPLACE_RETRY_SECONDS", 1.0)
    target = tmp_path / "index.json"
    voyage_index.write_json(target, {"b": 1, "a": [1, 2]})
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": [1, 2], "b": 1} and refused_twice.calls == 3
    assert [p for p in tmp_path.iterdir()] == [target]


def _recording(monkeypatch, module):
    calls = []

    def recorded(source, target, **named):
        calls.append((Path(source), Path(target), named))
        return features.replace_file(source, target, **named)

    monkeypatch.setattr(module, "replace_file", recorded)
    return calls


def test_plan_state_is_written_through_replace_file_from_a_sibling(tmp_path, monkeypatch):
    calls = _recording(monkeypatch, spec_state)
    target = tmp_path / "plan.md"
    target.write_text("old\n", encoding="utf-8")
    spec_state._atomic_write_text(target, "new\n")
    assert target.read_text(encoding="utf-8") == "new\n"
    (source, written, named), = calls
    assert written == target and source.parent == tmp_path and not source.exists()
    assert named == {"retry_seconds": spec_state.REPLACE_RETRY_SECONDS}


def test_voyage_index_metadata_is_written_through_replace_file_from_a_sibling(tmp_path, monkeypatch):
    calls = _recording(monkeypatch, voyage_index)
    target = tmp_path / "index.json"
    voyage_index.write_json(target, {"a": 1})
    (source, written, named), = calls
    assert written == target and source.parent == tmp_path and not source.exists()
    assert named == {"retry_seconds": voyage_index.REPLACE_RETRY_SECONDS}
