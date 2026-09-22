"""The Spec adapter: creation, review, lifecycle, task gate and resume.

Carried from Attune AI's tests/unit/spec/test_workspace.py at b89f7953f: 22 of
its 23 tests, with the test that drove Attune AI's MCP server left behind, and
the three consumer-behaviour tests of tests/unit/spec/test_adaptive_review_guidance.py
(its skill-file and MCP-server tests stay behind). Changed on porting: async
tests run through asyncio.run, since the suite has no async plugin; `_repo`
gains `src/attune/__init__.py`, because Harness's area_candidates walks the
packages under `src/` rather than `src/attune/` alone; every state comment a
fixture writes carries a schema_version, because Harness's reader refuses one
without it; the `nan` corruption case now meets the resume guard, since
Harness's reader returns None for JSON it cannot use. New: the four seams.
"""
# qualify: platform

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("attune_forms")
from attune_forms import WorkspaceActionResponse, WorkspaceViewId  # noqa: E402

import attune_harness  # noqa: E402
from attune_harness import spec_workspace  # noqa: E402
from attune_harness.command_workspace import (  # noqa: E402
    CommandWorkspaceError,
    CommandWorkspaceHost,
)
from attune_harness.spec_state import SpecState, load_state, save_state  # noqa: E402
from attune_harness.spec_workspace import (  # noqa: E402
    SpecArtifactReceipt,
    SpecLifecycleReceipt,
    SpecTaskGateReceipt,
    SpecWorkspaceAdapter,
    SpecWorkspaceState,
)

_PLAN = """# Demo plan

<task id="1" name="first"><objective>First task</objective></task>
<task id="2" name="second"><objective>Second task</objective></task>
"""


def run(coroutine):
    return asyncio.run(coroutine)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src" / "attune" / "alpha").mkdir(parents=True)
    (repo / "src" / "attune" / "__init__.py").write_text("")
    (repo / "src" / "attune" / "alpha" / "__init__.py").write_text("")
    (repo / "src" / "attune" / "beta").mkdir()
    (repo / "src" / "attune" / "beta" / "__init__.py").write_text("")
    (repo / "docs" / "specs" / "existing-spec").mkdir(parents=True)
    (repo / ".claude" / "plans").mkdir(parents=True)
    (repo / ".git").mkdir()
    return repo


def _host(repo: Path) -> CommandWorkspaceHost:
    host = CommandWorkspaceHost()
    host.register(SpecWorkspaceAdapter(repo))
    return host


def _intake() -> dict[str, object]:
    return {
        "route": "new",
        "outcome": "A renderer-backed spec flow exists.",
        "done_when": "Both tasks have approved receipts.",
        "area": "src/attune/alpha",
        "slug": "existing-spec",
    }


def _payload(render, action: str, *, confirmed: bool = False) -> dict[str, object]:
    return {
        "__elicitation_response__": True,
        "title": render.record.view.title,
        "view": render.record.view.id.value,
        "action": action,
        "confirmed": confirmed,
        **render.record.binding.to_payload(),
    }


def _response(action: str, *, confirmed: bool = False) -> WorkspaceActionResponse:
    return WorkspaceActionResponse(WorkspaceViewId.EXECUTION, action, confirmed)


def _artifacts() -> dict[str, object]:
    return {
        "kind": "artifacts_created",
        "plan_path": ".claude/plans/demo.md",
        "artifacts": [
            {"path": ".claude/plans/demo.md", "kind": "plan"},
            {"path": "docs/specs/demo/requirements.md", "kind": "requirements"},
            {"path": "docs/specs/demo/tasks.md", "kind": "tasks"},
        ],
        "task_ids": ["1", "2"],
        "probes": ["pytest tests/unit/spec/test_workspace.py -q"],
    }


def _gate(boundary: str, state: str = "PASS") -> dict[str, object]:
    return {
        "kind": "lifecycle_gate",
        "boundary": boundary,
        "receipts": [
            {
                "gate_id": "symbol-reality",
                "boundary": boundary,
                "state": state,
                "detail": f"{boundary} {state.lower()} receipt",
            }
        ],
    }


def _state_comment(**fields) -> str:
    return "<!-- spec-state: " + json.dumps({"schema_version": 2, **fields}) + " -->"


async def _to_review(host: CommandWorkspaceHost):
    preview = await host.open("spec", _intake())
    creating = await host.collect(_payload(preview, "create_spec", confirmed=True))
    gate = await host.publish(creating.record.workspace_id, _artifacts())
    return await host.publish(gate.record.workspace_id, _gate("tasks"))


async def _to_execution(host: CommandWorkspaceHost):
    review = await _to_review(host)
    approval = await host.collect(_payload(review, "approve_plan"))
    gate = await host.collect(_payload(approval, "start_execution", confirmed=True))
    return await host.publish(gate.record.workspace_id, _gate("execution"))


def test_new_spec_preview_reuses_tree_derived_intake_and_collision_warning(tmp_path):
    repo = _repo(tmp_path)
    preview = run(_host(repo).open("spec", _intake()))

    state = preview.record.state
    assert state.area_options == ("src/attune/alpha", "src/attune/beta")
    assert state.taken_slugs == ("existing-spec",)
    assert "already exists" in state.contract
    assert "tree-derived area" in preview.markdown
    assert "create_spec" in preview.html
    assert "`create_spec`" in preview.markdown


def test_creation_review_redo_and_artifact_receipt_are_canonical(tmp_path):
    async def go():
        host = _host(_repo(tmp_path))
        preview = await host.open("spec", _intake())
        with pytest.raises(CommandWorkspaceError, match="confirmation"):
            await host.collect(_payload(preview, "create_spec"))
        creating = await host.collect(_payload(preview, "create_spec", confirmed=True))
        assert creating.result["delegate"] == "spec.create"
        gate = await host.publish(creating.record.workspace_id, _artifacts())
        assert gate.result == {"delegate": "spec.lifecycle_gate", "boundary": "tasks"}
        review = await host.publish(gate.record.workspace_id, _gate("tasks"))
        assert review.record.state.stage == "review"
        assert ".claude/plans/demo.md" in review.render.markdown
        redo = await host.collect(_payload(review, "redo_plan"))
        assert redo.record.state.stage == "creating"
        assert redo.result["delegate"] == "spec.redo"

    run(go())


def test_chair_required_is_bound_and_blocked_cannot_be_acknowledged(tmp_path):
    async def go():
        host = _host(_repo(tmp_path))
        preview = await host.open("spec", _intake())
        creating = await host.collect(_payload(preview, "create_spec", confirmed=True))
        gate = await host.publish(creating.record.workspace_id, _artifacts())
        chair = await host.publish(gate.record.workspace_id, _gate("tasks", "CHAIR_REQUIRED"))
        assert chair.record.state.stage == "chair_required"
        with pytest.raises(CommandWorkspaceError, match="confirmation"):
            await host.collect(_payload(chair, "acknowledge_gate"))
        review = await host.collect(_payload(chair, "acknowledge_gate", confirmed=True))
        assert review.record.state.stage == "review"

        approval = await host.collect(_payload(review, "approve_plan"))
        running_gate = await host.collect(_payload(approval, "start_execution", confirmed=True))
        blocked = await host.publish(
            running_gate.record.workspace_id,
            _gate("execution", "BLOCKED"),
        )
        assert blocked.record.state.stage == "blocked"
        assert [action.id for action in blocked.record.view.actions] == ["retry_gate"]
        with pytest.raises(CommandWorkspaceError, match="not allowed"):
            await host.collect(_payload(blocked, "acknowledge_gate", confirmed=True))
        rerun = await host.collect(_payload(blocked, "retry_gate"))
        executing = await host.publish(rerun.record.workspace_id, _gate("execution"))
        assert executing.record.state.stage == "executing"

    run(go())


def test_task_gates_progress_auto_run_and_terminal_artifact_receipt(tmp_path):
    async def go():
        host = _host(_repo(tmp_path))
        executing = await _to_execution(host)
        started = await host.publish(
            executing.record.workspace_id,
            {"kind": "task_started", "task_id": "1"},
        )
        progress = await host.publish(
            started.record.workspace_id,
            {"kind": "execution_progress", "detail": "tests running"},
        )
        assert progress.record.revision == started.record.revision
        assert progress.record.event_sequence == started.record.event_sequence + 1
        assert "tests running" in progress.render.markdown
        gate = await host.publish(
            progress.record.workspace_id,
            {
                "kind": "task_result",
                "task_id": "1",
                "severity": "medium",
                "score": 86,
                "probes": ["pytest task-one -q"],
                "detail": "quality gates passed",
            },
        )
        auto = await host.collect(_payload(gate, "auto_run_remaining", confirmed=True))
        assert auto.record.state.completed == ("1",)
        assert auto.record.state.auto_run is True
        assert auto.result["save_state"]["completed"] == ["1"]

        started = await host.publish(
            auto.record.workspace_id,
            {"kind": "task_started", "task_id": "2"},
        )
        terminal = await host.publish(
            started.record.workspace_id,
            {
                "kind": "task_result",
                "task_id": "2",
                "severity": "low",
                "score": 99,
                "probes": ["pytest task-two -q"],
                "detail": "clean",
            },
        )
        assert terminal.record.terminal is True
        assert terminal.record.state.completed == ("1", "2")
        assert terminal.result["disposition"] == "auto"
        assert ".claude/plans/demo.md" in terminal.render.markdown
        assert "pytest tests/unit/spec/test\\_workspace.py -q" in terminal.render.markdown

    run(go())


def test_high_severity_interrupts_auto_run_and_requires_explicit_risk_ack(tmp_path):
    async def go():
        host = _host(_repo(tmp_path))
        executing = await _to_execution(host)
        started = await host.publish(
            executing.record.workspace_id,
            {"kind": "task_started", "task_id": "1"},
        )
        first_gate = await host.publish(
            started.record.workspace_id,
            {
                "kind": "task_result",
                "task_id": "1",
                "severity": "low",
                "score": 99,
                "probes": ["pytest first -q"],
                "detail": "clean",
            },
        )
        auto = await host.collect(_payload(first_gate, "auto_run_remaining", confirmed=True))
        started = await host.publish(
            auto.record.workspace_id,
            {"kind": "task_started", "task_id": "2"},
        )
        gate = await host.publish(
            started.record.workspace_id,
            {
                "kind": "task_result",
                "task_id": "2",
                "severity": "high",
                "score": 20,
                "probes": ["pytest failing -q"],
                "detail": "security gate failed",
            },
        )
        assert gate.record.state.stage == "task_gate"
        assert [action.id for action in gate.record.view.actions] == [
            "fix_retry",
            "acknowledge_risk",
        ]
        with pytest.raises(CommandWorkspaceError, match="confirmation"):
            await host.collect(_payload(gate, "acknowledge_risk"))
        continued = await host.collect(_payload(gate, "acknowledge_risk", confirmed=True))
        assert continued.record.state.completed == ("1", "2")
        assert continued.record.terminal is True

    run(go())


def test_resume_reads_real_xml_tasks_and_persisted_progress(tmp_path):
    repo = _repo(tmp_path)
    plan = repo / ".claude" / "plans" / "demo.md"
    plan.write_text(_PLAN)
    save_state(
        SpecState(
            plan_path=str(plan),
            completed=["1"],
            current="2",
            auto_run=True,
        )
    )
    resumed = run(
        _host(repo).open(
            "spec",
            {"route": "resume", "plan_path": ".claude/plans/demo.md"},
        )
    )

    state = resumed.record.state
    assert state.task_ids == ("1", "2")
    assert state.completed == ("1",)
    assert state.current == "2"
    assert state.auto_run is True
    assert state.area_options == ("src/attune/alpha", "src/attune/beta")
    assert ".claude/plans/demo.md" in resumed.markdown


def test_value_objects_and_state_reject_invalid_authority():
    with pytest.raises(CommandWorkspaceError, match="project-relative"):
        SpecArtifactReceipt("../escape", "plan")
    with pytest.raises(CommandWorkspaceError, match="kind"):
        SpecArtifactReceipt("plan.md", "")
    with pytest.raises(CommandWorkspaceError, match="boundary"):
        SpecLifecycleReceipt("g", "design", "PASS", "ok")
    with pytest.raises(CommandWorkspaceError, match="state"):
        SpecLifecycleReceipt("g", "tasks", "MAYBE", "ok")
    with pytest.raises(CommandWorkspaceError, match="severity"):
        SpecTaskGateReceipt("1", "critical", 10, ("pytest",), "bad")
    with pytest.raises(CommandWorkspaceError, match="between 0 and 100"):
        SpecTaskGateReceipt("1", "high", 101, ("pytest",), "bad")
    with pytest.raises(CommandWorkspaceError, match="current task cannot"):
        SpecWorkspaceState(
            outcome="x",
            done_when="y",
            area="a",
            slug="demo",
            contract="c",
            area_options=(),
            taken_slugs=(),
            task_ids=("1",),
            completed=("1",),
            current="1",
        )


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (lambda: SpecLifecycleReceipt("", "tasks", "PASS", "ok"), "gate_id"),
        (lambda: SpecLifecycleReceipt("g", "tasks", "PASS", ""), "detail"),
        (lambda: SpecTaskGateReceipt("", "low", 90, ("p",), "ok"), "task_id"),
        (lambda: SpecTaskGateReceipt("1", "low", True, ("p",), "ok"), "numeric"),
        (lambda: SpecTaskGateReceipt("1", "low", 90, (), "ok"), "exact probes"),
        (lambda: SpecTaskGateReceipt("1", "low", 90, ("p",), ""), "detail"),
    ],
)
def test_receipt_field_validation(factory, message):
    with pytest.raises(CommandWorkspaceError, match=message):
        factory()


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"outcome": ""}, "outcome"),
        ({"done_when": ""}, "done_when"),
        ({"slug": "Not a Slug"}, "kebab-case"),
        ({"stage": "missing"}, "stage"),
        ({"task_ids": ("1", "1")}, "task ids must be unique"),
        ({"completed": ("1",)}, "completed ids"),
        ({"current": "1"}, "current task must belong"),
        ({"gate_boundary": "design"}, "gate boundary"),
        ({"gate_next_stage": "missing"}, "successor stage"),
        (
            {
                "artifacts": (
                    SpecArtifactReceipt("plan.md", "plan"),
                    SpecArtifactReceipt("plan.md", "tasks"),
                )
            },
            "artifact paths must be unique",
        ),
    ],
)
def test_workspace_state_validation(changes, message):
    values: dict[str, object] = {
        "outcome": "x",
        "done_when": "y",
        "area": "a",
        "slug": "demo",
        "contract": "c",
        "area_options": (),
        "taken_slugs": (),
    }
    values.update(changes)
    with pytest.raises(CommandWorkspaceError, match=message):
        SpecWorkspaceState(**values)


def test_edit_replacement_and_approval_redo_paths(tmp_path):
    async def go():
        host = _host(_repo(tmp_path))
        preview = await host.open("spec", _intake())
        intake = await host.collect(_payload(preview, "edit_spec"))
        assert intake.record.state.stage == "intake"
        revised = _intake()
        revised["outcome"] = "Revised"
        preview = await host.open("spec", revised, workspace_id=preview.record.workspace_id)
        assert preview.record.state.outcome == "Revised"
        review = await _to_review(host)
        approval = await host.collect(_payload(review, "approve_plan"))
        redo = await host.collect(_payload(approval, "redo_plan"))
        assert redo.record.state.stage == "creating"

    run(go())


def test_adapter_create_validation(tmp_path):
    adapter = SpecWorkspaceAdapter(_repo(tmp_path))
    preview = adapter.create(_intake())
    with pytest.raises(CommandWorkspaceError, match="select edit_spec"):
        adapter.create(_intake(), prior_state=preview)
    intake = replace(preview, stage="intake")
    with pytest.raises(CommandWorkspaceError, match="resume cannot replace"):
        adapter.create(
            {"route": "resume", "plan_path": ".claude/plans/demo.md"},
            prior_state=intake,
        )
    with pytest.raises(CommandWorkspaceError, match="route must be"):
        adapter.create({**_intake(), "route": "import"})
    with pytest.raises(CommandWorkspaceError, match="unknown Spec intake"):
        adapter.create({**_intake(), "extra": True})


def test_artifact_and_lifecycle_event_validation(tmp_path):
    adapter = SpecWorkspaceAdapter(_repo(tmp_path))
    preview = adapter.create(_intake())
    creating = adapter.apply(preview, _response("create_spec", confirmed=True)).state
    with pytest.raises(CommandWorkspaceError, match="creation stage"):
        adapter.publish(preview, _artifacts())
    for artifacts in ("bad", [], [1]):
        event = {**_artifacts(), "artifacts": artifacts}
        with pytest.raises(CommandWorkspaceError, match="artifacts"):
            adapter.publish(creating, event)
    for field, value, message in (
        ("task_ids", "1", "must be a list"),
        ("task_ids", [], "non-empty"),
        ("task_ids", ["1", "1"], "unique"),
        ("probes", [""], "non-empty"),
        ("plan_path", "other.md", "received artifact"),
    ):
        with pytest.raises(CommandWorkspaceError, match=message):
            adapter.publish(creating, {**_artifacts(), field: value})

    gate = adapter.publish(creating, _artifacts()).state
    with pytest.raises(CommandWorkspaceError, match="gate-running stage"):
        adapter.publish(preview, _gate("tasks"))
    with pytest.raises(CommandWorkspaceError, match="does not match"):
        adapter.publish(gate, _gate("execution"))
    for receipts in ("bad", [], [1]):
        with pytest.raises(CommandWorkspaceError, match="lifecycle receipts"):
            adapter.publish(gate, {**_gate("tasks"), "receipts": receipts})
    revised = adapter.publish(gate, _gate("tasks", "REVISE"))
    assert revised.state.stage == "blocked"


def test_task_event_and_decision_validation(tmp_path):
    adapter = SpecWorkspaceAdapter(_repo(tmp_path))
    executing = SpecWorkspaceState(
        outcome="x",
        done_when="y",
        area="a",
        slug="demo",
        contract="c",
        area_options=(),
        taken_slugs=(),
        stage="executing",
        plan_path="plan.md",
        task_ids=("1", "2"),
    )
    with pytest.raises(CommandWorkspaceError, match="execution stage"):
        adapter.publish(
            replace(executing, stage="review"), {"kind": "task_started", "task_id": "1"}
        )
    with pytest.raises(CommandWorkspaceError, match="pending task"):
        adapter.publish(executing, {"kind": "task_started", "task_id": "3"})
    with pytest.raises(CommandWorkspaceError, match="plan order"):
        adapter.publish(executing, {"kind": "task_started", "task_id": "2"})
    with pytest.raises(CommandWorkspaceError, match="current execution task"):
        adapter.publish(executing, {"kind": "task_result", "task_id": "1"})
    current = adapter.publish(executing, {"kind": "task_started", "task_id": "1"}).state
    with pytest.raises(CommandWorkspaceError, match="does not match current"):
        adapter.publish(current, {"kind": "task_result", "task_id": "2"})
    with pytest.raises(CommandWorkspaceError, match="task probes must be a list"):
        adapter.publish(
            current,
            {"kind": "task_result", "task_id": "1", "probes": "bad"},
        )
    with pytest.raises(CommandWorkspaceError, match="execution stage"):
        adapter.publish(
            replace(executing, stage="review"),
            {"kind": "execution_progress", "detail": "x"},
        )

    low_receipt = SpecTaskGateReceipt("1", "low", 90, ("pytest",), "ok")
    low_gate = replace(current, stage="task_gate", task_receipt=low_receipt)
    with pytest.raises(CommandWorkspaceError, match="not legal"):
        adapter.apply(low_gate, _response("fix_retry"))
    redo = adapter.apply(low_gate, _response("redo_task"))
    assert redo.result["delegate"] == "spec.retry_task"
    empty_gate = replace(low_gate, task_receipt=None)
    with pytest.raises(CommandWorkspaceError, match="no current receipt"):
        adapter.apply(empty_gate, _response("approve_task"))

    high_receipt = SpecTaskGateReceipt("1", "high", 10, ("pytest",), "bad")
    high_gate = replace(current, stage="task_gate", task_receipt=high_receipt)
    fixed = adapter.apply(high_gate, _response("fix_retry"))
    assert fixed.result["task_id"] == "1"
    with pytest.raises(CommandWorkspaceError, match="explicit confirmation"):
        adapter.apply(high_gate, _response("acknowledge_risk"))


def test_resume_validation_and_completed_plan_rejection(tmp_path):
    repo = _repo(tmp_path)
    adapter = SpecWorkspaceAdapter(repo)
    with pytest.raises(CommandWorkspaceError, match="unknown Spec resume"):
        adapter.create({"route": "resume", "plan_path": "x.md", "extra": True})
    for path in ("", "/absolute.md", "../escape.md"):
        with pytest.raises(CommandWorkspaceError, match="project-relative"):
            adapter.create({"route": "resume", "plan_path": path})
    with pytest.raises(CommandWorkspaceError, match="does not exist"):
        adapter.create({"route": "resume", "plan_path": "missing.md"})
    empty = repo / ".claude" / "plans" / "empty.md"
    empty.write_text("# No tasks\n")
    with pytest.raises(CommandWorkspaceError, match="no XML tasks"):
        adapter.create({"route": "resume", "plan_path": ".claude/plans/empty.md"})
    plan = repo / ".claude" / "plans" / "done.md"
    plan.write_text(_PLAN)
    save_state(SpecState(plan_path=str(plan), completed=["1", "2"]))
    with pytest.raises(CommandWorkspaceError, match="already complete"):
        adapter.create({"route": "resume", "plan_path": ".claude/plans/done.md"})


def test_direct_adapter_rejects_incompatible_and_illegal_transitions(tmp_path):
    adapter = SpecWorkspaceAdapter(_repo(tmp_path))
    preview = adapter.create(_intake())
    for method, args in (
        (adapter.project, (object(),)),
        (adapter.apply, (object(), _response("x"))),
        (adapter.publish, (object(), {"kind": "x"})),
    ):
        with pytest.raises(CommandWorkspaceError, match="incompatible state"):
            method(*args)
    with pytest.raises(CommandWorkspaceError, match="not legal"):
        adapter.apply(preview, _response("approve_plan"))
    with pytest.raises(CommandWorkspaceError, match="unknown Spec event"):
        adapter.publish(preview, {"kind": "missing"})


def test_publish_rejects_artifact_under_missing_top_level_directory(tmp_path):
    """A sibling-repo prefix is a valid ``_portable_path`` string (relative, no
    ``..``) that resolves to nothing here; publish must fail loudly rather than
    let the executor write to a location that never existed."""
    adapter = SpecWorkspaceAdapter(_repo(tmp_path))
    preview = adapter.create(_intake())
    creating = adapter.apply(preview, _response("create_spec", confirmed=True)).state
    event = _artifacts()
    event["artifacts"] = [
        {"path": ".claude/plans/demo.md", "kind": "plan"},
        {"path": "attune-rag/docs/specs/demo/requirements.md", "kind": "requirements"},
    ]
    with pytest.raises(CommandWorkspaceError, match="top-level directory that does not exist"):
        adapter.publish(creating, event)
    # A new directory UNDER an existing top level is the normal creation shape:
    # docs/specs/demo/ is absent from _repo() and must still be accepted.
    assert adapter.publish(creating, _artifacts()).state.stage == "gate_running"


def test_publish_rejects_artifact_that_resolves_outside_the_repo(tmp_path):
    """``..`` is rejected as a string; a symlink escapes only after resolution."""
    repo = _repo(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (repo / "escape").symlink_to(outside, target_is_directory=True)
    except OSError as exc:  # Windows without the symlink privilege
        pytest.skip(f"symlinks unavailable: {exc}")
    adapter = SpecWorkspaceAdapter(repo)
    preview = adapter.create(_intake())
    creating = adapter.apply(preview, _response("create_spec", confirmed=True)).state
    event = _artifacts()
    event["artifacts"] = [
        {"path": ".claude/plans/demo.md", "kind": "plan"},
        {"path": "escape/requirements.md", "kind": "requirements"},
    ]
    with pytest.raises(CommandWorkspaceError, match="artifact escapes the repository"):
        adapter.publish(creating, event)


@pytest.mark.parametrize(
    "decision,severity",
    [("approve_task", "low"), ("auto_run_remaining", "medium"), ("acknowledge_risk", "high")],
)
def test_completion_retains_execution_evidence_across_real_resume(tmp_path, decision, severity):
    """Persist the host's actual result and finish through a new host."""

    async def go():
        repo = _repo(tmp_path)
        plan = repo / ".claude/plans/demo.md"
        plan.write_text(_PLAN)
        host = _host(repo)
        view = await _to_execution(host)
        view = await host.publish(
            view.record.workspace_id, {"kind": "task_started", "task_id": "1"}
        )
        event = {
            "kind": "task_result",
            "task_id": "1",
            "severity": severity,
            "score": 42,
            "probes": ["Executed first proof"],
            "detail": "First actual result",
        }
        view = await host.publish(view.record.workspace_id, event)
        view = await host.collect(_payload(view, decision, confirmed=True))
        payload = view.result["save_state"]
        assert payload["task_receipts"][0] == {
            k: v for k, v in {**event, "disposition": decision}.items() if k != "kind"
        }
        save_state(SpecState(**{**payload, "plan_path": str(plan)}))
        saved = load_state(str(plan))
        assert saved.completed == ["1"]
        assert saved.task_receipts == payload["task_receipts"]
        host = _host(repo)
        view = await host.open(
            "spec", {"route": "resume", "plan_path": ".claude/plans/demo.md"}
        )
        view = await host.publish(
            view.record.workspace_id, {"kind": "task_started", "task_id": "2"}
        )
        view = await host.publish(
            view.record.workspace_id,
            {
                "kind": "task_result",
                "task_id": "2",
                "severity": "low",
                "score": 100,
                "probes": ["Executed second proof"],
                "detail": "Second actual result",
            },
        )
        if not view.record.terminal:
            view = await host.collect(_payload(view, "approve_task"))
        assert view.record.terminal
        assert len(view.result["save_state"]["task_receipts"]) == 2
        text = view.render.markdown
        for proof in [
            "2/2",
            "Executed first proof",
            "First actual result",
            "Executed second proof",
            "Second actual result",
            "42",
            "Historical planning",
        ]:
            assert proof in text
        if severity == "high":
            assert "Acknowledged risk" in text
            assert "high" in text

    run(go())


@pytest.mark.parametrize("severity,retry", [("low", "redo_task"), ("high", "fix_retry")])
def test_terminal_uses_accepted_retry_and_labels_planning_history(tmp_path, severity, retry):
    async def go():
        host = _host(_repo(tmp_path))
        view = await _to_execution(host)
        view = await host.publish(
            view.record.workspace_id, {"kind": "task_started", "task_id": "1"}
        )
        view = await host.publish(
            view.record.workspace_id,
            {
                "kind": "task_result",
                "task_id": "1",
                "severity": severity,
                "score": 10,
                "probes": ["Rejected proof"],
                "detail": "Rejected attempt",
            },
        )
        view = await host.collect(_payload(view, retry))
        view = await host.publish(
            view.record.workspace_id,
            {
                "kind": "task_result",
                "task_id": "1",
                "severity": "low",
                "score": 90,
                "probes": ["Accepted replacement proof"],
                "detail": "Repaired result",
            },
        )
        view = await host.collect(_payload(view, "auto_run_remaining", confirmed=True))
        view = await host.publish(
            view.record.workspace_id, {"kind": "task_started", "task_id": "2"}
        )
        view = await host.publish(
            view.record.workspace_id,
            {
                "kind": "task_result",
                "task_id": "2",
                "severity": "low",
                "score": 100,
                "probes": ["Final execution proof"],
                "detail": "Final actual result",
            },
        )
        text = view.render.markdown
        assert "Rejected proof" not in text
        assert "Rejected attempt" not in text
        assert "Accepted replacement proof" in text
        assert "Final execution proof" in text
        assert "Historical planning" in text
        assert text.index("Historical planning") < text.index("pytest tests/unit/spec/")
        assert [r["disposition"] for r in view.result["save_state"]["task_receipts"]] == [
            "auto_run_remaining",
            "auto",
        ]

    run(go())


def test_legacy_completed_task_is_disclosed_without_invented_evidence(tmp_path):
    async def go():
        repo = _repo(tmp_path)
        plan = repo / ".claude/plans/demo.md"
        plan.write_text(_PLAN + "\n" + _state_comment(completed=["1"], current="2", auto_run=True))
        host = _host(repo)
        view = await host.open(
            "spec", {"route": "resume", "plan_path": ".claude/plans/demo.md"}
        )
        view = await host.publish(
            view.record.workspace_id,
            {
                "kind": "task_result",
                "task_id": "2",
                "severity": "low",
                "score": 100,
                "probes": ["Current execution proof"],
                "detail": "Current result",
            },
        )
        assert "Task 1" in view.render.markdown
        assert "Execution evidence unavailable" in view.render.markdown
        assert "Current execution proof" in view.render.markdown

    run(go())


@pytest.mark.parametrize(
    "corruption",
    [
        "container",
        "element",
        "missing",
        "extra",
        "wrong_text",
        "wrong_probes",
        "nan",
        "duplicate",
        "foreign",
        "risk_auto",
        "unknown_disposition",
    ],
)
def test_invalid_persisted_receipts_cannot_be_accepted_or_reset_progress(tmp_path, corruption):
    repo = _repo(tmp_path)
    receipt = {
        "task_id": "1",
        "severity": "low",
        "score": 100,
        "probes": ["prior proof"],
        "detail": "prior result",
        "disposition": "approve_task",
    }
    receipts = [receipt]
    if corruption == "container":
        receipts = "invalid"
    elif corruption == "element":
        receipts = [None]
    elif corruption == "missing":
        receipt.pop("detail")
    elif corruption == "extra":
        receipt["invented"] = True
    elif corruption == "wrong_text":
        receipt["task_id"] = 1
    elif corruption == "wrong_probes":
        receipt["probes"] = [1]
    elif corruption == "nan":
        receipt["score"] = float("nan")
    elif corruption == "duplicate":
        receipts.append(receipt.copy())
    elif corruption == "foreign":
        receipt["task_id"] = "2"
    elif corruption == "risk_auto":
        receipt.update(severity="high", disposition="auto")
    else:
        receipt["disposition"] = "invented"
    plan = repo / ".claude/plans/demo.md"
    original = (
        _PLAN
        + "\n"
        + _state_comment(completed=["1"], current="2", task_receipts=receipts)
    )
    plan.write_text(original)
    # Harness's reader returns None for a non-finite number, so the `nan` case
    # meets the resume guard instead of the score check.
    with pytest.raises(ValueError, match="receipt|disposition|score|could not be read"):
        SpecWorkspaceAdapter(repo).create({"route": "resume", "plan_path": ".claude/plans/demo.md"})
    assert plan.read_text() == original


def test_legacy_progress_and_new_receipts_survive_a_second_resume(tmp_path):
    """The shared state format also supports writers without workspace receipts."""

    async def go():
        repo = _repo(tmp_path)
        plan = repo / ".claude/plans/demo.md"
        plan.write_text(_PLAN + '<task id="3" name="third"><objective>Third</objective></task>')
        # Existing runner.py writes this legitimate current-schema state too.
        save_state(SpecState(plan_path=str(plan), completed=["1"], auto_run=True))
        for task in ["2", "3"]:
            host = _host(repo)
            view = await host.open(
                "spec", {"route": "resume", "plan_path": ".claude/plans/demo.md"}
            )
            view = await host.publish(
                view.record.workspace_id, {"kind": "task_started", "task_id": task}
            )
            view = await host.publish(
                view.record.workspace_id,
                {
                    "kind": "task_result",
                    "task_id": task,
                    "severity": "low",
                    "score": 100,
                    "probes": ["Actual proof " + task],
                    "detail": "Actual result " + task,
                },
            )
            save_state(SpecState(**{**view.result["save_state"], "plan_path": str(plan)}))
        persisted = load_state(str(plan))
        assert persisted.completed == ["1", "2", "3"]
        assert [r["task_id"] for r in persisted.task_receipts] == ["2", "3"]
        assert view.record.terminal
        assert "Execution evidence unavailable" in view.render.markdown
        assert "Actual proof 2" in view.render.markdown
        assert "Actual proof 3" in view.render.markdown

    run(go())


# --- consumer behaviour the review-choice guidance relies on -----------------
# Carried from tests/unit/spec/test_adaptive_review_guidance.py, using this
# file's fixtures; the assertions do not depend on the intake's slug.


def test_review_stage_is_a_two_alternative_non_consequential_choice(tmp_path):
    # ASI-5's pilot premise: genuine alternatives, no manufactured approval gate.
    review = run(_to_review(_host(_repo(tmp_path))))
    actions = review.record.view.actions
    assert [a.id for a in actions] == ["redo_plan", "approve_plan"]
    assert all(not a.requires_explicit_choice for a in actions)
    assert all(not a.consequence for a in actions)


def test_markdown_skeleton_carries_the_binding_for_transcription(tmp_path):
    # The text lane the guidance names: a spoken "approve" is transcribed into
    # THIS skeleton and submitted; the skeleton must carry the bound fields.
    review = run(_to_review(_host(_repo(tmp_path))))
    md = review.render.markdown
    for key in ("workspace_id", "revision", "action_nonce", "contract_hash", "title", "view"):
        assert f'"{key}"' in md, key
    assert review.record.action_nonce in md
    assert review.record.contract_hash in md


def test_settled_choice_cannot_be_asked_again(tmp_path):
    # "Never re-ask a settled choice": once approve_plan is accepted the review
    # render is superseded, and re-submitting it is rejected rather than
    # producing a second answer to the same question.
    async def go():
        host = _host(_repo(tmp_path))
        review = await _to_review(host)
        approval = await host.collect(_payload(review, "approve_plan"))
        assert approval.record.state.stage == "approval"
        with pytest.raises(CommandWorkspaceError):
            await host.collect(_payload(review, "approve_plan"))

    run(go())


# --- the seams ----------------------------------------------------------------


def _fresh_interpreter(code: str) -> subprocess.CompletedProcess:
    """Run ``code`` in a new interpreter that sees this test's attune_harness."""
    package_parent = Path(attune_harness.__file__).resolve().parents[1]
    return subprocess.run(
        [sys.executable, "-c", code],
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(package_parent)},
    )


def test_importing_the_module_needs_no_forms_package():
    """Only ``project`` needs the forms package, and it reports the extra."""
    result = _fresh_interpreter(
        "import sys\n"
        "sys.modules['attune_forms'] = None\n"
        "from attune_harness import spec_workspace\n"
        "assert 'attune_forms' not in [m for m in sys.modules if sys.modules[m] is not None]\n"
        "from pathlib import Path\n"
        "state = spec_workspace.SpecWorkspaceState('o', 'd', 'a', 'slug', 'c', (), ())\n"
        "try:\n"
        "    spec_workspace.SpecWorkspaceAdapter(Path('.')).project(state)\n"
        "except Exception as error:\n"
        "    print(type(error).__name__, error)\n"
        "else:\n"
        "    print('projected')\n"
    )
    assert result.returncode == 0, result.stderr
    name, _, message = result.stdout.strip().partition(" ")
    assert name == "FeatureUnavailable"
    assert "attune-forms" in message


@pytest.mark.parametrize(
    "payload",
    [
        # A non-finite number: the reader's JSON parser refuses it.
        '{"schema_version": 2, "completed": ["1"], "task_receipts": [{"task_id": "1", '
        '"severity": "low", "score": NaN, "probes": ["p"], "detail": "d", '
        '"disposition": "approve_task"}]}',
        # A duplicate key: refused the same way.
        '{"schema_version": 2, "completed": ["1"], "completed": ["2"]}',
        # A field of the wrong type: the reader warns and returns None.
        '{"schema_version": 2, "completed": "1"}',
    ],
)
def test_resume_refuses_a_state_comment_the_reader_could_not_use(tmp_path, payload):
    """Harness's reader returns None for these; resuming would restart from zero."""
    repo = _repo(tmp_path)
    plan = repo / ".claude/plans/demo.md"
    original = _PLAN + "\n<!-- spec-state: " + payload + " -->\n"
    plan.write_text(original)
    with pytest.raises(CommandWorkspaceError, match="could not be read") as info:
        SpecWorkspaceAdapter(repo).create({"route": "resume", "plan_path": ".claude/plans/demo.md"})
    assert "remove it to start the plan over" in str(info.value)
    assert plan.read_text() == original


def test_resume_without_a_state_comment_starts_the_plan(tmp_path):
    """The guard fires only when a comment exists: no comment, no progress to lose."""
    repo = _repo(tmp_path)
    plan = repo / ".claude/plans/demo.md"
    plan.write_text(_PLAN)
    state = SpecWorkspaceAdapter(repo).create(
        {"route": "resume", "plan_path": ".claude/plans/demo.md"}
    )
    assert state.completed == ()
    assert state.current == ""
    assert state.auto_run is False


def test_resume_passes_the_readers_own_refusals_through(tmp_path):
    """A comment the reader refuses itself keeps the reader's error and words."""
    repo = _repo(tmp_path)
    plan = repo / ".claude/plans/demo.md"
    original = _PLAN + '\n<!-- spec-state: {"completed": ["1"], "current": "2"} -->\n'
    plan.write_text(original)
    with pytest.raises(ValueError, match="schema_version none") as info:
        SpecWorkspaceAdapter(repo).create({"route": "resume", "plan_path": ".claude/plans/demo.md"})
    assert not isinstance(info.value, CommandWorkspaceError)
    assert plan.read_text() == original


def _evidence(tmp_path: Path) -> dict[str, str]:
    return {
        "kind": "harness-test-v1",
        "record_path": str((tmp_path / "run" / "record.json").resolve()),
        "task_id": "1",
        "checkpoint_digest": "0" * 64,
        "outcome": "passed",
    }


def _executing() -> SpecWorkspaceState:
    return SpecWorkspaceState(
        outcome="x",
        done_when="y",
        area="a",
        slug="demo",
        contract="c",
        area_options=(),
        taken_slugs=(),
        stage="executing",
        plan_path="plan.md",
        task_ids=("1",),
        current="1",
    )


def test_test_evidence_is_checked_by_harness_own_policy(tmp_path, monkeypatch):
    """The check is spec_handoff's, bound at import; its refusal is reported as stale."""
    seen = []

    def stale(binding):
        seen.append(dict(binding))
        raise ValueError("Harness test evidence changed after the Spec gate was bound")

    monkeypatch.setattr(spec_workspace, "check_test_evidence", stale)
    adapter = SpecWorkspaceAdapter(_repo(tmp_path))
    evidence = _evidence(tmp_path)
    event = {
        "kind": "task_result",
        "task_id": "1",
        "severity": "low",
        "score": 100,
        "probes": [evidence["record_path"]],
        "detail": "ran",
        "test_evidence": evidence,
    }
    with pytest.raises(CommandWorkspaceError, match="unavailable or stale.*changed after"):
        adapter.publish(_executing(), event)
    assert seen == [evidence]

    monkeypatch.setattr(spec_workspace, "check_test_evidence", lambda binding: None)
    gate = adapter.publish(_executing(), event)
    assert gate.state.stage == "task_gate"
    assert gate.state.task_receipt.test_evidence == evidence
    # The two structural checks come before the policy and need no policy call.
    with pytest.raises(CommandWorkspaceError, match="displayed Spec probe"):
        adapter.publish(_executing(), {**event, "probes": ["other"]})
    with pytest.raises(CommandWorkspaceError, match="high-severity gate"):
        adapter.publish(
            _executing(), {**event, "test_evidence": {**evidence, "outcome": "failed"}}
        )


def test_state_marker_is_the_readers():
    """The guard looks for exactly the marker the reader owns."""
    assert spec_workspace.STATE_MARKER == "<!-- spec-state:"


@pytest.mark.parametrize(
    "size,tasks,expected",
    [
        (65536, True, "resumes"),
        (65537, True, "Input exceeds its limit of 65536 bytes"),
        # No task block: only the resume's own read can refuse this by size.
        # Without the limit on that read, the answer would be "no XML tasks".
        (65537, False, "Input exceeds its limit of 65536 bytes"),
    ],
)
def test_resume_enforces_the_plan_limit_on_its_own_read(tmp_path, size, tasks, expected):
    """The one read in ``_resume`` carries ``PLAN_LIMIT``; the reviewer found nothing pinned it."""
    repo = _repo(tmp_path)
    plan = repo / ".claude/plans/demo.md"
    head = _PLAN if tasks else "# No tasks\n"
    plan.write_bytes((head + "x" * (size - len(head))).encode("ascii"))
    assert plan.stat().st_size == size
    adapter = SpecWorkspaceAdapter(repo)
    if expected == "resumes":
        state = adapter.create({"route": "resume", "plan_path": ".claude/plans/demo.md"})
        assert state.task_ids == ("1", "2")
    else:
        with pytest.raises(ValueError, match=expected):
            adapter.create({"route": "resume", "plan_path": ".claude/plans/demo.md"})
