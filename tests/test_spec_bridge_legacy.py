"""The bridge reads legacy plans with Harness's own reader, Attune AI absent.

Step 2.4 of the spec authority's Task 2. Before it, ``legacy_plan`` imported
Attune AI's reader at the point of use, so its parse path never ran in CI,
where Attune AI is not installed. These tests block the ``attune`` package
outright, so they prove that calling the path needs nothing from it. That
importing ``spec_bridge`` needs nothing from it is proved statically by
``test_no_attune_runtime_import.py``.
"""

import sys

import pytest

from attune_harness.spec_bridge import legacy_plan

TWO_TASKS = (
    '<task id="1" name="first"><objective>Do first</objective>'
    '<files-to-modify><file path="a.py">edit</file></files-to-modify></task>\n'
    '<task id="2" name="second"><objective>Do second</objective></task>\n'
)
STATE = '<!-- spec-state: {"schema_version": 2, "completed": ["1"], "current": "2"} -->\n'


@pytest.fixture(autouse=True)
def attune_absent(monkeypatch):
    """Make ``import attune`` and every submodule fail, whatever is installed."""
    for name in list(sys.modules):
        if name == "attune" or name.startswith("attune."):
            monkeypatch.delitem(sys.modules, name)
    monkeypatch.setitem(sys.modules, "attune", None)
    monkeypatch.setitem(sys.modules, "attune.pipeline", None)
    monkeypatch.setitem(sys.modules, "attune.pipeline.spec_reader", None)
    with pytest.raises(ImportError):
        import attune.pipeline.spec_reader  # noqa: F401


def test_reads_tasks_with_attune_absent(tmp_path):
    plan = tmp_path / "plan.md"
    plan.write_text("# Plan\n\n" + TWO_TASKS, encoding="utf-8")
    legacy = legacy_plan(plan)
    assert [t["task_id"] for t in legacy["tasks"]] == ["1", "2"]
    assert legacy["tasks"][0]["files_to_modify"] == [{"path": "a.py", "description": "edit"}]
    assert legacy["approval_imported"] is False
    assert legacy["unsupported"] == ["Unmapped surrounding content: # Plan"]


def test_trailing_state_comment_is_excluded_and_grants_nothing(tmp_path):
    plan = tmp_path / "plan.md"
    plan.write_text(TWO_TASKS + "\n" + STATE, encoding="utf-8")
    legacy = legacy_plan(plan)
    assert "spec-state" not in legacy["content"]
    assert legacy["content_sha256"] != legacy["source_sha256"]
    assert [t["task_id"] for t in legacy["tasks"]] == ["1", "2"]
    assert legacy["approval_imported"] is False
    assert legacy["unsupported"] == []


def test_misplaced_state_comment_is_refused(tmp_path):
    plan = tmp_path / "plan.md"
    plan.write_text(STATE + "\n" + TWO_TASKS, encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed or misplaced Spec state comment"):
        legacy_plan(plan)


def test_task_the_reader_drops_is_reported_not_lost(tmp_path):
    plan = tmp_path / "plan.md"
    plan.write_text('<task name="no id"><objective>x</objective></task>\n', encoding="utf-8")
    with pytest.raises(ValueError, match="Legacy parser omitted a malformed task"):
        legacy_plan(plan)


def test_unmapped_content_is_disclosed(tmp_path):
    plan = tmp_path / "plan.md"
    plan.write_text(
        '<task id="1" name="t" priority="high"><objective>x</objective>'
        "<notes>keep</notes></task>\n",
        encoding="utf-8",
    )
    legacy = legacy_plan(plan)
    assert legacy["tasks"][0]["objective"] == "x"
    assert any("priority" in item for item in legacy["unsupported"])
    assert any("<notes>keep</notes>" in item for item in legacy["unsupported"])


def test_prose_and_state_between_and_after_blocks_change_no_task(tmp_path):
    """Found by review: the reader once re-read the raw file, and a bare & in
    prose between blocks, or a </task> inside the state comment, dropped it to
    the regex path and changed task text. Now it sees only the blocks."""
    plan = tmp_path / "plan.md"
    plan.write_text(
        '<task id="1" name="a"><objective>a &amp; b</objective></task>\n'
        "See R&D notes.\n"
        '<task id="2" name="b"><objective>c</objective></task>\n\n'
        '<!-- spec-state: {"schema_version": 2, "current": "\\u003c/task\\u003e"} -->\n',
        encoding="utf-8",
    )
    legacy = legacy_plan(plan)
    assert [t["objective"] for t in legacy["tasks"]] == ["a & b", "c"]
    assert legacy["unsupported"] == ["Unmapped surrounding content: See R&D notes."]


def test_ill_formed_block_is_refused_with_a_next_action(tmp_path):
    plan = tmp_path / "plan.md"
    plan.write_text('<task id="1" name="a"><objective>x<bad attr></objective></task>\n', encoding="utf-8")
    with pytest.raises(ValueError, match="not well-formed XML") as info:
        legacy_plan(plan)
    assert "Fix that block" in str(info.value)
