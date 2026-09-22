"""The package must not import Attune AI at runtime.

Harness replaces Attune AI, so nothing under ``src/attune_harness`` may import
the ``attune`` package. ``attune_forms``, ``attune_rag`` and ``attune_verify``
are separate libraries and stay allowed. See R2 in
docs/specs/spec-authority/README.md and D8 in its September 21 addendum.

The files that still import it are listed in ``KNOWN``. That list may only
shrink: a new offender fails, and so does an entry that no longer offends, so
the list cannot go stale.
"""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "attune_harness"

# Remove a name when its file stops importing attune, or is deleted.
KNOWN = {
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


def offenders():
    found = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        lines = attune_imports(path.read_text(encoding="utf-8"))
        if lines:
            found[path.relative_to(PACKAGE).as_posix()] = lines
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
