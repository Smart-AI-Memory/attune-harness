"""The package must not import Attune AI at runtime.

Harness replaces Attune AI, so nothing under ``src/attune_harness`` may import
the ``attune`` package. ``attune_forms``, ``attune_rag`` and ``attune_verify``
are separate libraries and stay allowed. See R2 in
docs/specs/spec-authority/README.md and D8 in its September 21 addendum.

The files that still import it are listed in ``KNOWN``. That list may only
shrink: a new offender fails, and so does an entry that no longer offends, so
the list cannot go stale. It has been empty since Phase 2 step 2.4 (D19).

One import is allowed to remain, under ``FALLBACK``: the adapter's, inside
``MemoryHost.__init__``'s ``reader == 'adapter'`` branch. It is the fallback
that Task 9 removes, and it is allowed only there: the test checks that every
attune import in that file sits lexically inside an ``if``/``elif`` whose test
compares ``reader`` with ``'adapter'``, and a runtime test constructs the host
with the default and shows nothing from attune is loaded.
"""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "attune_harness"

# Remove a name when its file stops importing attune, or is deleted.
KNOWN = set()

# The one guarded fallback site (D19): an import allowed only inside a
# ``reader == 'adapter'`` branch. Removed with the adapter in Task 9.
FALLBACK = {
    "memory_context.py",
}

# require_feature is this package's own loader: it passes its module argument
# to import_module.
LOADERS = {"import_module", "find_spec", "__import__", "require_feature"}


def is_attune(name):
    return name == "attune" or name.startswith("attune.")


def attune_imports(source):
    """Line numbers where the source imports attune, at any depth."""
    lines = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            if any(is_attune(alias.name) for alias in node.names):
                lines.append(node.lineno)
        elif isinstance(node, ast.ImportFrom):
            # A relative import stays inside this package, whatever it is called.
            if node.level == 0 and node.module and is_attune(node.module):
                lines.append(node.lineno)
        elif isinstance(node, ast.Call) and node.args:
            called = node.func
            name = called.attr if isinstance(called, ast.Attribute) else getattr(called, "id", "")
            literals = [arg.value for arg in node.args if isinstance(arg, ast.Constant)]
            if name in LOADERS and any(
                isinstance(value, str) and is_attune(value) for value in literals
            ):
                lines.append(node.lineno)
    return sorted(lines)


def fallback_lines(source):
    """Line numbers inside an ``if``/``elif`` body whose test is ``reader == 'adapter'``."""
    allowed = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)):
            continue
        sides = [test.left, test.comparators[0]]
        names = {side.id for side in sides if isinstance(side, ast.Name)}
        values = {side.value for side in sides if isinstance(side, ast.Constant)}
        if names == {"reader"} and values == {"adapter"}:
            allowed.update(range(node.body[0].lineno, node.body[-1].end_lineno + 1))
    return allowed


def offenders():
    """Files importing attune, less the guarded fallback lines in the FALLBACK files."""
    found = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        name = path.relative_to(PACKAGE).as_posix()
        lines = attune_imports(source)
        if name in FALLBACK:
            lines = [line for line in lines if line not in fallback_lines(source)]
        if lines:
            found[name] = lines
    return found


@pytest.mark.parametrize(
    "source",
    [
        "import attune",
        "import attune.memory.personal",
        "import os, attune.spec",
        "from attune import spec",
        "from attune.spec.workspace import SpecWorkspaceAdapter",
        "def late():\n    from attune.pipeline.spec_reader import read_spec",
        "try:\n    import attune\nexcept ImportError:\n    attune = None",
        "import importlib\nimportlib.import_module('attune.mcp.server')",
        "from importlib.util import find_spec\nfind_spec('attune')",
        "__import__('attune.plugins')",
        "require_feature('attune-ai', 'attune.spec.state', VERSION, 'spec')",
    ],
)
def test_every_way_of_importing_attune_is_found(source):
    assert attune_imports(source)


@pytest.mark.parametrize(
    "source",
    [
        "import attune_forms",
        "from attune_rag import retrieve",
        "import attune_verify.claims",
        "from attune_harness.memory_contract import strings",
        "from . import attune",
        "from .attune import bridge",
        "import importlib\nimportlib.import_module('attune_forms')",
        "note = 'import attune'  # text, not an import",
        "import importlib\nimportlib.import_module(name)",
        "require_feature('attune-forms', 'attune_forms', VERSION, 'review')",
    ],
)
def test_other_libraries_and_relative_imports_are_not_mistaken_for_it(source):
    assert attune_imports(source) == []


def test_no_file_outside_the_known_list_imports_attune():
    new = {name: lines for name, lines in offenders().items() if name not in KNOWN}
    assert not new, (
        f"These files import Attune AI at runtime: {new}. Harness must run "
        "without it; do not add them to KNOWN."
    )


def test_the_known_list_has_no_stale_entries():
    stale = sorted(KNOWN - set(offenders()))
    assert not stale, (
        f"These no longer import Attune AI (or are gone): {stale}. "
        "Remove them from KNOWN so the list only shrinks."
    )


def test_the_fallback_files_still_import_attune_only_inside_the_adapter_branch():
    for name in sorted(FALLBACK):
        source = (PACKAGE / name).read_text(encoding="utf-8")
        lines = attune_imports(source)
        assert lines, f"{name} no longer imports attune anywhere; remove it from FALLBACK"
        assert set(lines) <= fallback_lines(source), (
            f"{name} imports attune outside the reader == 'adapter' branch at {lines}")


def test_fallback_lines_only_match_the_adapter_branch():
    guarded = "def f(reader):\n    if reader == 'native':\n        pass\n    elif reader == 'adapter':\n        from attune.x import Y\n        return Y\n"
    assert fallback_lines(guarded) == {5, 6}
    assert fallback_lines("if reader == 'native':\n    from attune.x import Y\n") == set()
    assert fallback_lines("if mode == 'adapter':\n    from attune.x import Y\n") == set()
    assert fallback_lines("if reader != 'adapter':\n    from attune.x import Y\n") == set()


def test_the_default_host_loads_nothing_from_attune(tmp_path, monkeypatch):
    """The runtime half of the guarantee: the default reader never touches attune."""
    import sys
    for name in [m for m in sys.modules if m == "attune" or m.startswith("attune.")]:
        monkeypatch.delitem(sys.modules, name)
    from attune_harness.memory_context import MemoryHost
    root = tmp_path / "raw"
    root.mkdir()
    config = {"schema_version": 1, "actor": "p", "owners": ["p"], "scopes": ["s"], "classifications": ["internal"],
              "profiles": ["claude"], "roots": [dict(id="r", path=str(root.resolve()), tier="raw", scope="s",
                                                     owner="p", classification="internal")]}
    host = MemoryHost(config)
    assert type(host.adapter).__name__ == "NativeReader"
    assert not any(m == "attune" or m.startswith("attune.") for m in sys.modules)
