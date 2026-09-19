"""Retained text and delayed responses through actual local work/Spec owners."""

import asyncio
import json
import os
import subprocess
import sys

import pytest
import test_work_cli as console
import test_work_contract as contracts
import test_work_controls as controls

from attune_harness import work_decisions
from attune_harness.review_store import PersistenceError, RunStore
from attune_harness.spec_bridge import WorkSpecBridge
from attune_harness.task_contract import read_task
from attune_harness.work_contract import revise_work

work = contracts.work


def saved(directory):
    return json.loads((directory / "decision.json").read_text())


def readonly_status(directory, capsys, monkeypatch):
    def snapshot():
        return {
            p.name: (p.read_bytes(), p.stat().st_mtime_ns)
            for p in directory.iterdir()
            if p.is_file()
        }

    def forbidden(*args, **kwargs):
        pytest.fail("Status attempted to save or recreate a decision")

    before = snapshot()
    with monkeypatch.context() as patch:
        patch.setattr(work_decisions, "write_report", forbidden)
        patch.setattr(RunStore, "save", forbidden)
        patch.setattr(WorkSpecBridge, "__init__", forbidden)
        result = console.invoke(capsys, "status", directory)
        assert console.invoke(capsys, "status", directory) == result
    assert snapshot() == before
    return result


def test_text_is_retained_before_collection_and_survives_missing_form(
    work, capsys, monkeypatch
):
    record = contracts.make(work)
    directory = work[2]["directory"]
    before = (directory / "record.json").read_bytes()

    async def run():
        bridge = WorkSpecBridge(directory)
        view = await bridge.open()
        artifact = saved(directory)
        assert artifact["display"]["markdown"] == view.render.markdown
        assert artifact["work"]["checkpoint_digest"] == record["checkpoint_digest"]
        assert artifact["response"] is None
        assert [a["id"] for a in artifact["display"]["actions"]] == [
            a.id for a in view.record.view.actions
        ]
        reply = artifact["display"]["response_template"]
        assert reply["action"] is None and reply["confirmed"] is False
        del (
            view
        )  # No widget/render object is needed to read or answer the retained text.
        status = readonly_status(directory, capsys, monkeypatch)
        assert status["decision"]["state"] == "current"
        assert (
            status["decision"]["display"]["markdown"] == artifact["display"]["markdown"]
        )
        assert (directory / "record.json").read_bytes() == before
        assert status["authority"] == "draft"  # Disappearance/silence is no answer.
        await asyncio.sleep(0)
        _, accepted = await bridge.collect({**reply, "action": "approve_task"})
        assert accepted["status"] == "accepted"
        assert saved(directory)["response"]["result"]["disposition"] == "approve_task"
        with pytest.raises(ValueError):
            await bridge.collect({**reply, "action": "approve_task"})

    asyncio.run(run())
    status = readonly_status(directory, capsys, monkeypatch)
    assert status["decision"]["state"] == "historical"
    assert status["authority"] == "accepted"


def test_console_preview_and_restart_retain_text_but_do_not_revive_authority(
    work, capsys, monkeypatch
):
    record = contracts.make(work)
    directory = work[2]["directory"]
    shown = console.invoke(capsys, "plan", "--task-dir", directory, "--decision")
    assert (
        shown["authority"] == "draft"
        and shown["checkpoint_digest"] == record["checkpoint_digest"]
    )
    original = saved(directory)
    process = subprocess.run(
        [sys.executable, "-B", "-m", "attune_harness", "status", str(directory)],
        cwd=directory.parent,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    reopened = json.loads(process.stdout)
    assert reopened["decision"]["display"] == original["display"]
    assert "reopen after host restart" in reopened["decision"]["note"]

    async def run():
        bridge = WorkSpecBridge(directory)
        old = {**original["display"]["response_template"], "action": "approve_task"}
        with pytest.raises(ValueError, match="Open and retain"):
            await bridge.collect(old)
        current = await bridge.open()
        before = (directory / "record.json").read_bytes()
        with pytest.raises(ValueError):
            await bridge.collect(old)
        assert (directory / "record.json").read_bytes() == before
        _, accepted = await bridge.collect(controls.response(current))
        assert accepted["status"] == "accepted"

    asyncio.run(run())
    readonly_status(directory, capsys, monkeypatch)


@pytest.mark.parametrize("same_host", [True, False])
def test_replaced_display_does_not_rebind_a_delayed_reply(work, same_host):
    contracts.make(work)
    directory = work[2]["directory"]

    async def run():
        first = WorkSpecBridge(directory)
        old = await first.open()
        second = first if same_host else WorkSpecBridge(directory)
        current = await second.open(detail="Current decision text")
        before = (directory / "record.json").read_bytes()
        with pytest.raises(ValueError, match="decision"):
            await first.collect(controls.response(old))
        assert (directory / "record.json").read_bytes() == before
        _, accepted = await second.collect(controls.response(current))
        assert accepted["status"] == "accepted"

    asyncio.run(run())


@pytest.mark.parametrize("change", ["intent", "source", "config"])
def test_stale_text_remains_readable_without_accepting_its_answer(
    work, capsys, monkeypatch, change
):
    record = contracts.make(work)
    directory = work[2]["directory"]

    async def run():
        bridge = WorkSpecBridge(directory)
        view = await bridge.open()
        artifact = (directory / "decision.json").read_bytes()
        if change == "intent":
            revise_work(
                directory,
                checkpoint=record["checkpoint_digest"],
                changes={"intent": {"goal": "New goal"}},
            )
        elif change == "source":
            (work[0] / "source.py").write_text("changed source\n")
        else:
            work[1].write_text(work[1].read_text() + "\n")
        status = readonly_status(directory, capsys, monkeypatch)
        assert status["decision"]["state"] == "historical"
        assert status["decision"]["display"]["markdown"] == view.render.markdown
        with pytest.raises(ValueError):
            await bridge.collect(controls.response(view))
        assert (directory / "decision.json").read_bytes() == artifact
        assert read_task(directory)["status"] == "draft"

    asyncio.run(run())


def test_planning_questions_partial_answers_and_old_binding(work, capsys, monkeypatch):
    root, config, data = work
    request = root.parent / "request.json"
    request.write_text(
        json.dumps(
            {
                "intent": {**data["intent"], "goal": None},
                "assignments": data["assignments"],
                "choices": [contracts.choice()],
            }
        )
    )
    directory = data["directory"]
    initial = console.invoke(
        capsys,
        "plan",
        "--request",
        request,
        "--project",
        root,
        "--config",
        config,
        "--task-dir",
        directory,
    )
    artifact = saved(directory)
    assert artifact["display"]["kind"] == "questions"
    assert artifact["display"]["markdown"] == initial["questions"]["markdown"]
    assert "How should export stream?" in artifact["display"]["markdown"]
    assert (
        "jsonl" in artifact["display"]["markdown"]
        and "bundle" in artifact["display"]["markdown"]
    )
    assert artifact["display"]["response_template"]["answers"] == {}
    readonly_status(directory, capsys, monkeypatch)
    answer = root.parent / "answer.json"
    answer.write_text(
        json.dumps(
            {
                **artifact["display"]["response_template"],
                "answers": {"answer_0": "Keep every finding"},
            }
        )
    )
    partial = console.invoke(
        capsys, "plan", "--task-dir", directory, "--answers", answer
    )
    assert partial["missing"] == ["choice:format"]
    assert saved(directory)["work"]["checkpoint_digest"] == partial["checkpoint_digest"]
    assert saved(directory)["display"]["field_map"] == {"answer_0": "choice:format"}
    before = (directory / "record.json").read_bytes()
    console.invoke(capsys, "plan", "--task-dir", directory, "--answers", answer, code=2)
    assert (directory / "record.json").read_bytes() == before
    display = saved(directory)["display"]
    answer.write_text(
        json.dumps(
            {
                **display["response_template"],
                "answers": {
                    "answer_0": display["definition"]["fields"][0]["options"][1]
                },
            }
        )
    )
    done = console.invoke(capsys, "plan", "--task-dir", directory, "--answers", answer)
    assert done["missing"] == [] and done["authority"] == "draft"
    assert read_task(directory)["request"]["choices"][0]["selected"] == "bundle"
    assert done["decision"]["state"] == "historical"


def test_preview_questions_for_existing_work_is_explicit_and_does_not_change_checkpoint(
    work, capsys, monkeypatch
):
    work[2]["intent"]["goal"] = None
    record = contracts.make(work)
    directory = work[2]["directory"]
    assert "decision" not in readonly_status(directory, capsys, monkeypatch)
    result = console.invoke(
        capsys,
        "plan",
        "--task-dir",
        directory,
        "--decision",
        "--checkpoint",
        record["checkpoint_digest"],
    )
    assert result["checkpoint_digest"] == record["checkpoint_digest"]
    assert result["decision"]["state"] == "current"
    assert result["decision"]["display"]["kind"] == "questions"


def test_saved_high_risk_actions_keep_explicit_confirmation_and_non_grant(
    work, capsys, monkeypatch
):
    contracts.make(work)
    directory = work[2]["directory"]

    async def run():
        bridge = WorkSpecBridge(directory)
        view = await bridge.open(severity="high", detail="Unresolved failure")
        actions = saved(directory)["display"]["actions"]
        acknowledge = next(a for a in actions if a["id"] == "acknowledge_risk")
        assert acknowledge["requires_explicit_choice"] and acknowledge["consequence"]
        with pytest.raises(ValueError):
            await bridge.collect(controls.response(view, "acknowledge_risk", False))
        assert saved(directory)["response"] is None
        _, accepted = await bridge.collect(
            controls.response(view, "acknowledge_risk", True)
        )
        assert accepted is None and read_task(directory)["status"] == "draft"

    asyncio.run(run())
    result = readonly_status(directory, capsys, monkeypatch)
    assert result["decision"]["state"] == "collected"
    assert result["decision"]["response"]["action"] == "acknowledge_risk"


@pytest.mark.parametrize("failure_point", ["open", "collect"])
def test_persistence_failure_never_grants_work_authority(
    work, monkeypatch, failure_point
):
    contracts.make(work)
    directory = work[2]["directory"]

    def fail(*args, **kwargs):
        raise OSError("injected decision storage failure")

    async def run():
        bridge = WorkSpecBridge(directory)
        if failure_point == "open":
            with monkeypatch.context() as patch:
                patch.setattr(work_decisions, "write_report", fail)
                with pytest.raises(PersistenceError, match="Decision text"):
                    await bridge.open()
            assert bridge.decision is None
        else:
            view = await bridge.open()
            with monkeypatch.context() as patch:
                patch.setattr(work_decisions, "write_report", fail)
                with pytest.raises(PersistenceError, match="Decision text"):
                    await bridge.collect(controls.response(view))
            with pytest.raises(ValueError):
                await bridge.collect(controls.response(view))
        assert read_task(directory)["status"] == "draft"

    asyncio.run(run())


@pytest.mark.parametrize("bad", ["corrupt", "symlink", "foreign"])
def test_bad_display_does_not_break_status_or_authorize_a_reply(
    work, capsys, monkeypatch, bad
):
    contracts.make(work)
    directory = work[2]["directory"]

    async def run():
        bridge = WorkSpecBridge(directory)
        view = await bridge.open()
        path = directory / "decision.json"
        if bad == "corrupt":
            path.write_text("not JSON")
        elif bad == "symlink":
            copy = directory.parent / "external.json"
            copy.write_bytes(path.read_bytes())
            path.unlink()
            path.symlink_to(copy)
        else:
            from attune_harness.review_contract import digest

            value = saved(directory)
            value["work"]["task_id"] = "foreign"
            value["digest"] = digest({k: v for k, v in value.items() if k != "digest"})
            path.write_text(json.dumps(value))
        result = readonly_status(directory, capsys, monkeypatch)
        assert result["decision"]["state"] == "unavailable"
        assert result["decision"]["error"] and result["authority"] == "draft"
        with pytest.raises(ValueError):
            await bridge.collect(controls.response(view))
        assert read_task(directory)["status"] == "draft"

    asyncio.run(run())


def test_preview_does_not_approve_or_dispatch_and_keeps_json_contract(work, capsys):
    directory, draft = console.create(work, capsys)
    shown = console.invoke(capsys, "plan", "--task-dir", directory, "--decision")
    assert shown["checkpoint_digest"] == draft["checkpoint_digest"]
    assert shown["authority"] == "draft"
    assert not (work[0] / "pkg").exists()
    console.invoke(
        capsys, "plan", "--task-dir", directory, "--decision", "--allow-native", code=2
    )
    accepted = console.invoke(
        capsys,
        "plan",
        "--task-dir",
        directory,
        "--accept",
        "--checkpoint",
        shown["checkpoint_digest"],
    )
    assert accepted["authority"] == "accepted" and accepted["decision_markdown"]
    assert accepted["decision"]["response"]["result"]["disposition"] == "approve_task"
