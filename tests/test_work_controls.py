"""Real Spec collector and work-owner steering with disposable local fixtures."""

import asyncio
import copy
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import test_work_contract as contracts
import test_work_build as builds

from attune_harness.review_store import PersistenceError, RunStore
from attune_harness.spec_bridge import (
    WorkSpecBridge,
    import_plan,
    legacy_plan,
    reimport_plan,
    SPEC_APPROVAL,
)
from attune_harness.task_contract import read_task
from attune_harness.work_contract import create_work, revise_work, check_work_fresh
from attune_harness.work_runtime import completed_steps, work_status

work = contracts.work
reset_worker = builds.reset_worker


def response(view, action="approve_task", confirmed=False):
    return {
        "__elicitation_response__": True,
        "title": view.record.view.title,
        "view": view.record.view.id.value,
        "action": action,
        "confirmed": confirmed,
        **view.record.binding.to_payload(),
    }


def draft(work):
    root, config, data = work
    return create_work(root, config, **data)


def test_actual_collector_grants_current_intent_once(work):
    record = draft(work)

    async def run():
        bridge = WorkSpecBridge(work[2]["directory"])
        view = await bridge.open(probes=["Local fixture only"])
        assert read_task(bridge.directory)["status"] == "draft"
        assert record["request"]["intent"]["goal"] in view.render.markdown
        reply = response(view)
        receipt, accepted = await bridge.collect(reply)
        assert accepted["status"] == "accepted"
        assert receipt.result["disposition"] == "approve_task"
        assert accepted["acceptance"]["decision"]["source"]["owner"] == "spec"
        with pytest.raises(ValueError):
            await bridge.collect(reply)

    asyncio.run(run())


@pytest.mark.parametrize(
    "field,value",
    [
        ("action_nonce", "foreign"),
        ("contract_hash", "0" * 64),
        ("revision", 99),
        ("workspace_id", "foreign"),
        ("title", "foreign"),
        ("action", "start_execution"),
    ],
)
def test_collector_rejects_foreign_or_changed_action(work, field, value):
    draft(work)

    async def run():
        bridge = WorkSpecBridge(work[2]["directory"])
        view = await bridge.open()
        with pytest.raises(ValueError):
            await bridge.collect({**response(view), field: value})
        assert read_task(bridge.directory)["status"] == "draft"

    asyncio.run(run())


@pytest.mark.parametrize("change", ["intent", "source", "config"])
def test_changed_work_invalidates_displayed_decision(work, change):
    record = draft(work)

    async def run():
        bridge = WorkSpecBridge(work[2]["directory"])
        view = await bridge.open()
        if change == "intent":
            revise_work(
                bridge.directory,
                checkpoint=record["checkpoint_digest"],
                changes={"intent": {"goal": "Different outcome"}},
            )
        elif change == "source":
            (work[0] / "source.py").write_text("Changed evidence")
        else:
            work[1].write_text(work[1].read_text() + "\n")
        with pytest.raises(ValueError):
            await bridge.collect(response(view))
        assert read_task(bridge.directory)["status"] == "draft"

    asyncio.run(run())


@pytest.mark.parametrize(
    "action,confirmed,granted",
    [
        ("auto_run_remaining", False, False),
        ("auto_run_remaining", True, True),
        ("redo_task", False, False),
    ],
)
def test_autorun_requires_explicit_choice(work, action, confirmed, granted):
    draft(work)

    async def run():
        bridge = WorkSpecBridge(work[2]["directory"])
        view = await bridge.open()
        if action == "auto_run_remaining" and not confirmed:
            with pytest.raises(ValueError):
                await bridge.collect(response(view, action, confirmed))
        else:
            _, accepted = await bridge.collect(response(view, action, confirmed))
            assert bool(accepted) == granted
        assert (read_task(bridge.directory)["status"] == "accepted") == granted

    asyncio.run(run())


def test_high_severity_never_becomes_build_authority(work):
    draft(work)

    async def run():
        bridge = WorkSpecBridge(work[2]["directory"])
        view = await bridge.open(
            severity="high", detail="Unresolved protected oracle failure"
        )
        with pytest.raises(ValueError):
            await bridge.collect(response(view, "auto_run_remaining", True))
        _, accepted = await bridge.collect(response(view, "acknowledge_risk", True))
        assert accepted is None
        assert read_task(bridge.directory)["status"] == "draft"

    asyncio.run(run())


def test_lost_collector_grant_persistence_has_no_blind_replay(work, monkeypatch):
    draft(work)

    async def run():
        bridge = WorkSpecBridge(work[2]["directory"])
        view = await bridge.open()
        with monkeypatch.context() as patch:
            patch.setattr(
                RunStore,
                "save",
                lambda *a: (_ for _ in ()).throw(PersistenceError("injected")),
            )
            with pytest.raises(PersistenceError):
                await bridge.collect(response(view))
        assert read_task(bridge.directory)["status"] == "draft"
        with pytest.raises(ValueError):
            await bridge.collect(response(view))
        reopened = WorkSpecBridge(bridge.directory)
        view = await reopened.open()
        _, accepted = await reopened.collect(response(view))
        assert accepted["status"] == "accepted"

    asyncio.run(run())


def test_missing_intent_and_unavailable_required_control_block(work):
    record = draft(work)
    record = revise_work(
        work[2]["directory"],
        checkpoint=record["checkpoint_digest"],
        changes={"intent": {"goal": None}},
    )
    with pytest.raises(ValueError, match="complete draft"):
        WorkSpecBridge(work[2]["directory"])
    control = {
        "id": "required",
        "kind": "hook",
        "owner": "missing",
        "version": 1,
        "required": True,
        "phases": ["build"],
    }
    revise_work(
        work[2]["directory"],
        checkpoint=record["checkpoint_digest"],
        changes={"intent": {"goal": "Known goal"}, "controls": [control]},
    )

    async def run():
        bridge = WorkSpecBridge(work[2]["directory"])
        view = await bridge.open()
        with pytest.raises(ValueError, match="Unavailable required control"):
            await bridge.collect(response(view))
        assert read_task(bridge.directory)["status"] == "draft"

    asyncio.run(run())


LEGACY = """# Retain this authoring context
<tasks><task id="first" name="export"><objective>Add export</objective>
<files-to-create><file path="export.py">New module</file></files-to-create>
<validation><check>All findings survive</check></validation>
<risks><risk severity="medium">Unknown provider quality</risk></risks>
<unsupported>Retain this disclosure</unsupported></task>
<task id="second" name="wire"><objective>Wire export</objective>
<files-to-modify><file path="source.py">Connect CLI</file></files-to-modify>
<validation><check>Default output unchanged</check></validation>
<dependencies><dep>first</dep></dependencies></task></tasks>\n"""


def imported(work):
    root, config, data = work
    (root / "legacy.md").write_text(LEGACY)
    return import_plan(
        root,
        config,
        path=root / "legacy.md",
        directory=data["directory"],
        intent=data["intent"],
        assignments=data["assignments"],
    )


def test_import_preserves_fields_discloses_loss_and_never_approves(work):
    record = imported(work)
    request = record["request"]
    assert request["tasks"][1]["dependencies"] == ["first"]
    assert request["legacy"]["tasks"][0]["risks"][0]["severity"] == "medium"
    assert (
        request["legacy"]["tasks"][0]["files_to_create"][0]["description"]
        == "New module"
    )
    assert len(request["legacy"]["unsupported"]) == 2
    assert record["status"] == "draft" and record["acceptance"] is None
    check_work_fresh(record)


def test_edited_import_reaccepts_same_work_identity(work):
    record = imported(work)

    async def approve():
        bridge = WorkSpecBridge(work[2]["directory"])
        view = await bridge.open()
        return (await bridge.collect(response(view)))[1]

    record = asyncio.run(approve())
    path = work[0] / "legacy.md"
    path.write_text(path.read_text().replace("Add export", "Add complete export"))
    revised = reimport_plan(
        work[2]["directory"], checkpoint=record["checkpoint_digest"]
    )
    assert revised["status"] == "draft"
    assert revised["request"]["tasks"][0]["objective"] == "Add complete export"
    accepted = asyncio.run(approve())
    assert accepted["request"]["task_id"] == record["request"]["task_id"]
    assert accepted["history"][-1]["acceptance"] == record["acceptance"]


def test_required_human_control_needs_actual_collector(work):
    root, config, data = work
    data["controls"] = [{**SPEC_APPROVAL, "required": True, "phases": ["accept"]}]
    record = draft(work)
    with pytest.raises(ValueError, match="actual collector"):
        contracts.accept(work, record, supported_controls=[SPEC_APPROVAL])

    async def run():
        bridge = WorkSpecBridge(data["directory"])
        view = await bridge.open()
        return (await bridge.collect(response(view)))[1]

    accepted = asyncio.run(run())
    assert (
        accepted["acceptance"]["collector"]["result"]["disposition"] == "approve_task"
    )
    from attune_harness.work_effects import control_runners

    assert control_runners({**accepted["request"], "effects": {"checks": []}}) == (
        [],
        [],
    )


def test_unknown_required_control_phase_stays_blocked(work):
    case = builds.prepare(work, accept=False)
    record = case[2]
    controls = copy.deepcopy(record["request"]["controls"])
    controls[0]["phases"].append("accept")
    from attune_harness.work_effects import control_runners

    with pytest.raises(ValueError, match="not qualified"):
        control_runners({**record["request"], "controls": controls})


def test_feature_and_test_evidence_flow_through_actual_spec(work):
    from attune_harness.spec_handoff import (
        bind_work_evidence,
        check_work_evidence,
        bind_test_evidence,
    )
    from attune_harness.test_change import create_test_task, accept_test_task
    from attune_harness.task_policies import execute_task

    case = builds.prepare(work)
    builds.execute(case)
    feature = bind_work_evidence(case[1])
    check_work_evidence(feature)
    with pytest.raises(ValueError, match="changed after"):
        check_work_evidence({**feature, "checkpoint_digest": "0" * 64})
    target = case[1].parent / "test-evidence"
    test = create_test_task(
        project=None,
        source_task=case[1],
        directory=target,
        interpreter=__import__("sys").executable,
        tests=[builds.GENERATED],
    )
    test = accept_test_task(target, checkpoint=test["checkpoint_digest"])
    test = execute_task(target)
    evidence = bind_test_evidence(target)
    assert evidence["outcome"] == "passed"
    # A fresh planning revision can display the completed evidence but still
    # needs the actual human collector response to receive authority.
    data = copy.deepcopy(work[2])
    data["directory"] = case[1].parent / "followup"
    data["inputs"], data["artifact"] = [], None
    create_work(work[0], work[1], **data)

    async def run():
        bridge = WorkSpecBridge(data["directory"])
        view = await bridge.open(
            probes=[evidence["record_path"]], test_evidence=evidence
        )
        assert read_task(data["directory"])["status"] == "draft"
        (work[0] / "source.py").write_text("def value():\n    return 43\n")
        with pytest.raises(ValueError, match="evidence is unavailable or stale"):
            await bridge.collect(response(view))
        with pytest.raises(ValueError):
            check_work_evidence(feature)

    asyncio.run(run())


def test_state_comment_does_not_self_invalidate_plan(work):
    from attune.spec.state import SpecState, save_state

    record = imported(work)
    path = work[0] / "legacy.md"
    save_state(SpecState(plan_path=str(path), completed=["first"], auto_run=True))
    check_work_fresh(record)
    assert (
        legacy_plan(path)["source_sha256"]
        != record["request"]["legacy"]["source_sha256"]
    )
    assert read_task(work[2]["directory"])["status"] == "draft"
    path.write_text(path.read_text().replace("Add export", "Remove findings"))
    with pytest.raises(ValueError, match="changed"):
        check_work_fresh(record)


@pytest.mark.parametrize(
    "raw",
    [
        "no tasks",
        "<task id='x'><objective>broken</task>",
        "<task id='x'><objective>missing end",
        '<task id="x"><objective>x</objective></task><task',
        LEGACY + "<!-- spec-state: {broken} -->",
        LEGACY + '<!-- spec-state: {"schema_version":1} -->extra',
    ],
)
def test_bad_import_fails_closed(work, raw):
    path = work[0] / "legacy.md"
    path.write_text(raw)
    with pytest.raises((ValueError, ET.ParseError)):
        legacy_plan(path)


def test_pending_correction_preserves_completed_outputs_and_requires_reacceptance(work):
    case = builds.prepare(work)
    record = builds.execute(case, max_operations=8)
    assert completed_steps(record) == ["export"]
    assert record["build"]["events"][-1]["operation_key"] == "probe:export"
    tasks = copy.deepcopy(record["request"]["tasks"])
    tasks[1]["objective"] = "Wire the verified exporter, preserving all findings"
    before = (work[0] / builds.EXPORT).read_bytes()
    revised = revise_work(
        work[2]["directory"],
        checkpoint=record["checkpoint_digest"],
        changes={"tasks": tasks},
        preserve_completed=True,
    )
    assert revised["request"]["task_id"] == record["request"]["task_id"]
    assert revised["status"] == "draft" and "build" not in revised
    assert revised["history"][-1]["build"] == record["build"]
    assert work_status(work[2]["directory"])["preserved_completion"] == ["export"]
    with pytest.raises(ValueError):
        builds.execute(case)

    async def accept():
        bridge = WorkSpecBridge(
            work[2]["directory"],
            supported_controls=[
                builds.work_effects.identity(c) for c in revised["request"]["controls"]
            ],
        )
        view = await bridge.open()
        return (await bridge.collect(response(view)))[1]

    accepted = asyncio.run(accept())
    result = builds.execute(case)
    assert result["build"]["status"] == "completed"
    assert (work[0] / builds.EXPORT).read_bytes() == before
    assert all(
        e.get("item", {}).get("path") != builds.EXPORT
        for e in result["build"]["events"]
    )
    assert accepted["request"]["revision"] == 2
    from attune_harness.task_handoff import completed_source

    assert completed_source(case[1])[1] == sorted(
        [builds.EXPORT, builds.GENERATED, "source.py"]
    )


@pytest.mark.parametrize(
    "boundary,change", [(1, "pending"), (3, "pending"), (8, "completed"), (8, "goal")]
)
def test_steering_rejects_unsafe_or_completed_scope_changes(work, boundary, change):
    case = builds.prepare(work)
    record = builds.execute(case, max_operations=boundary)
    tasks = copy.deepcopy(record["request"]["tasks"])
    tasks[0 if change == "completed" else 1]["objective"] = "Changed objective"
    changes = (
        {"tasks": tasks} if change != "goal" else {"intent": {"goal": "Different goal"}}
    )
    saved = Path(record["record_path"]).read_bytes()
    with pytest.raises(ValueError):
        revise_work(
            work[2]["directory"],
            checkpoint=record["checkpoint_digest"],
            changes=changes,
            preserve_completed=True,
        )
    assert Path(record["record_path"]).read_bytes() == saved


def test_bridge_rejects_changed_work_before_collecting(work):
    record = draft(work)
    bridge = WorkSpecBridge(work[2]["directory"])
    revise_work(
        bridge.directory,
        checkpoint=record["checkpoint_digest"],
        changes={"intent": {"goal": "Corrected intent"}},
    )
    with pytest.raises(ValueError, match="changed after"):
        bridge._fresh()


def test_steering_requires_verified_boundary_after_completed_prefix(work):
    case = builds.prepare(work)
    record = builds.execute(case, max_operations=9)
    assert completed_steps(record) == ["export"]
    assert record["build"]["events"][-1]["kind"] == "participant_turn"
    tasks = copy.deepcopy(record["request"]["tasks"])
    tasks[-1]["objective"] = "Correct the pending wiring"
    with pytest.raises(ValueError, match="verified task boundary"):
        revise_work(
            case[1],
            checkpoint=record["checkpoint_digest"],
            changes={"tasks": tasks},
            preserve_completed=True,
        )
