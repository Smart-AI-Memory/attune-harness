"""Actual test-owner/Spec-collector boundaries; no native participants."""

import asyncio
from contextlib import contextmanager
from dataclasses import replace
import importlib.util
import os
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

from attune_harness.review_store import RunStore
from attune_harness.spec_handoff import bind_test_evidence, check_test_evidence
from attune_harness.task_contract import read_task
from attune_harness.task_policies import execute_task
from attune_harness.test_change import accept_test_task, create_test_task
from attune_harness.test_scope import capture, fresh

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "handoff_preparation", ROOT / "experiments/memory_documentation_journey/prepare.py"
)
prep = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prep)


@pytest.fixture(scope="module")
def journey(tmp_path_factory):
    output = tmp_path_factory.mktemp("spec-handoff") / "evidence"
    assert prep.run(output)["status"] == "local_rehearsal_passed_native_pending"
    return output / "work"


@contextmanager
def saved(path):
    data = path.read_bytes()
    try:
        yield data
    finally:
        path.write_bytes(data)


def payload(view, action="approve_task", confirmed=False):
    return {
        "__elicitation_response__": True,
        "title": view.record.view.title,
        "view": view.record.view.id.value,
        "action": action,
        "confirmed": confirmed,
        **view.record.binding.to_payload(),
    }


async def opening(root, binding, severity="low", auto=False):
    from attune.elicitation.command_workspace import CommandWorkspaceHost
    from attune.spec.state import SpecState, save_state
    from attune.spec.workspace import SpecWorkspaceAdapter

    (root / ".claude/plans").mkdir(parents=True)
    (root / ".git").mkdir()
    plan = root / ".claude/plans/journey.md"
    plan.write_text(
        '<task id="1" name="first"><objective>Test</objective></task>\n'
        '<task id="2" name="next"><objective>Next</objective></task>\n'
    )
    save_state(SpecState(plan_path=str(plan), current="1", auto_run=auto))
    host = CommandWorkspaceHost()
    host.register(SpecWorkspaceAdapter(root))
    view = await host.open(
        "spec", {"route": "resume", "plan_path": ".claude/plans/journey.md"}
    )
    event = {
        "kind": "task_result",
        "task_id": "1",
        "severity": severity,
        "score": 100 if severity == "low" else 0,
        "probes": [binding["record_path"]],
        "detail": "Actual bounded test evidence; synthetic human action",
        "test_evidence": binding,
    }
    return host, view, event, plan


@pytest.mark.parametrize(
    "damage",
    [
        "source",
        "test",
        "config",
        "producer",
        "missing",
        "output",
        "checkpoint",
        "journal",
    ],
)
def test_old_spec_approval_rejects_changed_or_missing_evidence(
    journey, tmp_path, damage
):
    from attune.elicitation.command_workspace import CommandWorkspaceError

    async def run():
        tested = journey / "tested"
        binding = bind_test_evidence(tested)
        host, view, event, _ = await opening(tmp_path / "spec", binding)
        gate = await host.publish(view.record.workspace_id, event)
        paths = {
            "source": journey / "checkout/adapter/file_stash.py",
            "test": journey / "checkout/tests/test_project_filtering.py",
            "config": journey / "checkout/pytest.ini",
            "producer": journey / "repair/record.json",
            "missing": tested / "record.json",
            "output": tested / "stdout.txt",
            "checkpoint": tested / "record.json",
            "journal": tested / "record.json",
        }
        target = paths[damage]
        with saved(target) as before:
            if damage in {"missing", "producer"}:
                target.unlink()
            elif damage in {"checkpoint", "journal"}:
                task = read_task(tested)
                task["execution"]["result"]["detail"] = "changed result"
                if damage == "checkpoint":
                    task["execution"]["events"][0]["result"][
                        "detail"
                    ] = "changed result"
                RunStore(tested, existing=True).save(task)
            else:
                target.write_bytes(before + b"\n# changed evidence\n")
            with pytest.raises(
                CommandWorkspaceError, match="evidence is unavailable or stale"
            ):
                await host.collect(payload(gate))
            retry = await host.collect(payload(gate, "redo_task"))
            assert retry.result["delegate"] == "spec.retry_task"
            assert not retry.record.state.completed
        new_gate = await host.publish(retry.record.workspace_id, event)
        with pytest.raises(CommandWorkspaceError):
            await host.collect(payload(gate))
        done = await host.collect(payload(new_gate))
        assert done.record.state.completed == ("1",)
        assert done.record.state.accepted_receipts[0].receipt.test_evidence == binding

    asyncio.run(run())


@pytest.mark.parametrize(
    "action,severity",
    [
        ("approve_task", "low"),
        ("auto_run_remaining", "low"),
        ("acknowledge_risk", "high"),
    ],
)
def test_every_explicit_completion_rechecks_evidence(
    journey, tmp_path, action, severity
):
    from attune.elicitation.command_workspace import CommandWorkspaceError

    async def run():
        host, view, event, _ = await opening(
            tmp_path / "spec", bind_test_evidence(journey / "tested"), severity
        )
        gate = await host.publish(view.record.workspace_id, event)
        target = journey / "checkout/guide.md"
        with saved(target) as before:
            target.write_bytes(before + b"\nA later edit.\n")
            with pytest.raises(
                CommandWorkspaceError, match="evidence is unavailable or stale"
            ):
                await host.collect(payload(gate, action, confirmed=True))

    asyncio.run(run())


def test_auto_completion_rechecks_after_publication_validation(journey, tmp_path):
    import attune.spec.workspace as module
    from attune.elicitation.command_workspace import CommandWorkspaceError

    async def run():
        host, view, event, _ = await opening(
            tmp_path / "spec", bind_test_evidence(journey / "tested"), auto=True
        )
        original = module._check_test_evidence
        target = journey / "checkout/guide.md"
        with saved(target) as before:
            calls = []

            def check_then_change(receipt):
                original(receipt)
                calls.append(True)
                if len(calls) == 1:
                    target.write_bytes(
                        before + b"\nChanged before automatic completion.\n"
                    )

            with patch.object(module, "_check_test_evidence", check_then_change):
                with pytest.raises(
                    CommandWorkspaceError, match="evidence is unavailable or stale"
                ):
                    await host.publish(view.record.workspace_id, event)

    asyncio.run(run())


def test_accepted_binding_persists_as_history_without_revalidation(journey, tmp_path):
    from attune.elicitation.command_workspace import (
        CommandWorkspaceHost,
        CommandWorkspaceError,
    )
    from attune.spec.state import SpecState, save_state, load_state
    from attune.spec.workspace import SpecWorkspaceAdapter

    async def run():
        binding = bind_test_evidence(journey / "tested")
        host, view, event, plan = await opening(tmp_path / "spec", binding)
        gate = await host.publish(view.record.workspace_id, event)
        done = await host.collect(payload(gate))
        with pytest.raises(CommandWorkspaceError):
            await host.collect(payload(gate))
        save_state(SpecState(**{**done.result["save_state"], "plan_path": str(plan)}))
        assert load_state(str(plan)).task_receipts[0]["test_evidence"] == binding
        with saved(journey / "tested/record.json"):
            (journey / "tested/record.json").unlink()
            resumed = CommandWorkspaceHost()
            resumed.register(SpecWorkspaceAdapter(plan.parents[2]))
            view = await resumed.open(
                "spec", {"route": "resume", "plan_path": ".claude/plans/journey.md"}
            )
            assert view.record.state.completed == ("1",)
            assert (
                view.record.state.accepted_receipts[0].receipt.test_evidence == binding
            )

    asyncio.run(run())


@pytest.mark.parametrize(
    "field,value",
    [
        ("kind", "unknown-v2"),
        ("record_path", "relative/record.json"),
        ("record_path", "/tmp/not-a-record.txt"),
        ("checkpoint_digest", "bad"),
        ("outcome", "imagined"),
        ("task_id", ""),
        ("extra", "x"),
    ],
)
def test_malformed_bindings_fail_at_both_boundaries(journey, field, value):
    from attune.spec.workspace import SpecTaskGateReceipt
    from attune.elicitation.command_workspace import CommandWorkspaceError

    binding = {**bind_test_evidence(journey / "tested"), field: value}
    with pytest.raises((ValueError, TypeError)):
        check_test_evidence(binding)
    with pytest.raises(CommandWorkspaceError):
        SpecTaskGateReceipt("1", "low", 100, ("probe",), "detail", binding)


def test_wrong_binding_and_missing_dependency_fail_closed(journey, tmp_path):
    from attune.elicitation.command_workspace import CommandWorkspaceError
    import builtins

    binding = bind_test_evidence(journey / "tested")
    with pytest.raises(ValueError, match="changed after"):
        check_test_evidence({**binding, "task_id": "different-task"})

    async def run():
        host, view, event, _ = await opening(tmp_path / "spec", binding)
        with pytest.raises(CommandWorkspaceError, match="displayed Spec probe"):
            await host.publish(
                view.record.workspace_id, {**event, "probes": ["a different probe"]}
            )
        gate = await host.publish(view.record.workspace_id, event)
        original = builtins.__import__

        def missing(name, *args, **kwargs):
            if name == "attune_harness.spec_handoff":
                raise ImportError("optional Harness integration missing")
            return original(name, *args, **kwargs)

        with patch("builtins.__import__", missing):
            with pytest.raises(CommandWorkspaceError, match="integration missing"):
                await host.collect(payload(gate))

    asyncio.run(run())


def test_nonpassing_evidence_requires_explicit_high_gate(journey, tmp_path):
    from attune.elicitation.command_workspace import CommandWorkspaceError

    target = journey / "checkout/tests/test_project_filtering.py"
    with saved(target) as before:
        target.write_bytes(before.replace(b'["cedar", "elm"]', b'["cedar"]'))
        directory = tmp_path / "failed-test"
        draft = create_test_task(
            journey / "checkout",
            directory,
            scope=["guide.md"],
            interpreter=sys.executable,
            tests=["tests/test_project_filtering.py"],
        )
        accept_test_task(directory, draft["checkpoint_digest"])
        assert (
            execute_task(directory)["presentation"]["current_result"]["outcome"]
            == "failed"
        )
        binding = bind_test_evidence(directory)

        async def run():
            host, view, event, _ = await opening(tmp_path / "spec", binding)
            with pytest.raises(CommandWorkspaceError, match="high-severity"):
                await host.publish(view.record.workspace_id, event)
            gate = await host.publish(
                view.record.workspace_id, {**event, "severity": "high"}
            )
            with pytest.raises(CommandWorkspaceError):
                await host.collect(payload(gate))
            with pytest.raises(CommandWorkspaceError):
                await host.collect(payload(gate, "acknowledge_risk"))
            done = await host.collect(payload(gate, "acknowledge_risk", True))
            assert (
                done.record.state.accepted_receipts[0].receipt.test_evidence["outcome"]
                == "failed"
            )

        asyncio.run(run())


def test_binding_is_part_of_form_contract(journey, tmp_path):
    from attune.spec.workspace import SpecWorkspaceAdapter

    async def run():
        host, view, event, _ = await opening(
            tmp_path / "spec", bind_test_evidence(journey / "tested")
        )
        gate = await host.publish(view.record.workspace_id, event)
        state = gate.record.state
        changed = replace(
            state.task_receipt,
            test_evidence={**event["test_evidence"], "checkpoint_digest": "0" * 64},
        )
        adapter = SpecWorkspaceAdapter(tmp_path / "spec")
        assert (
            adapter.project(state).contract_hash
            != adapter.project(replace(state, task_receipt=changed)).contract_hash
        )

    asyncio.run(run())


def test_capture_never_refreshes_index(tmp_path):
    root, _ = prep.prepare_fixture(tmp_path / "inventory")
    target = root / "guide.md"
    stamp = target.stat().st_mtime_ns + 5_000_000_000
    os.utime(target, ns=(stamp, stamp))
    before = (root / ".git/index").read_bytes()
    capture(root)
    assert (root / ".git/index").read_bytes() == before


def test_freshness_tracks_content_not_stat_only_selection_hints(tmp_path):
    root, _ = prep.prepare_fixture(tmp_path / "inventory")
    before = capture(root)
    target = root / "control.md"
    original = target.read_bytes()
    target.write_bytes(original + b"\nA changed fact.\n")
    assert not fresh(before)
    target.write_bytes(original)
    stamp = target.stat().st_mtime_ns + 5_000_000_000
    os.utime(target, ns=(stamp, stamp))
    current = capture(root)
    assert current["files"] == before["files"]
    assert fresh(before)
