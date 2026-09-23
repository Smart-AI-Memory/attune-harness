"""The package's extras: the qualified ones, and `all` as their union."""

import re
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def extras():
    text = PYPROJECT.read_text(encoding="utf-8")
    block = text.split("[project.optional-dependencies]", 1)[1].split("\n[", 1)[0]
    found = {}
    # One extra per line; a quoted value may itself contain brackets, as the
    # self-referential `all` does, so the line is matched greedily.
    for name, body in re.findall(r"^([\w-]+)\s*=\s*\[(.*)\]\s*$", block, re.M):
        found[name] = re.findall(r"\"([^\"]+)\"", body)
    return found


def test_all_is_the_union_of_the_qualified_extras_and_nothing_experimental():
    found = extras()
    assert found["all"] == ["attune-harness[redis,voyage]"]
    assert found["redis"] and found["voyage"]
    assert "memory-native" in found and "memory-native" not in found["all"][0]


def test_the_retired_extras_stay_empty_until_1_0():
    found = extras()
    assert all(found[name] == [] for name in ("tokens", "verify", "rag", "review", "mcp"))
