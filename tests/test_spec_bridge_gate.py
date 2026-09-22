"""The bridge's task gate with Attune AI blocked: R1 across processes, R3 per action.

Step 3.4 of the spec authority's Task 3 (D14). Before it, ``WorkSpecBridge``
imported Attune AI's host and Spec adapter at the point of use, so nothing here
ran in CI and ``plan --accept`` needed Attune AI installed. An autouse fixture
blocks the ``attune`` package outright, as ``test_spec_bridge_legacy.py`` does,
so every test proves the gate needs nothing from it (R2). The forms package,
Harness's ``review`` extra, renders the decision and is required.

R1: the task store is the only authority, and its refusals hold across
processes. R3: every wired action passes through a human, and is refused
without its nonce, on a drifted view, when replayed, and without confirmation
where the view requires it.
"""
# qualify: platform

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("attune_forms")

import attune_harness  # noqa: E402
from attune_harness import command_workspace, spec_workspace  # noqa: E402
from attune_harness.cli import main  # noqa: E402
from attune_harness.command_workspace import CommandWorkspaceError  # noqa: E402
from attune_harness.features import FeatureUnavailable  # noqa: E402
from attune_harness.spec_bridge import WorkSpecBridge  # noqa: E402
from attune_harness.task_contract import read_task  # noqa: E402
from attune_harness.work_contract import bind_work_acceptance  # noqa: E402
from attune_harness.work_decisions import retained_decision  # noqa: E402
from test_work_contract import correction, make, work  # noqa: E402,F401

# (action, severity of the gate that offers it, needs confirmed, grants work authority).
# Only approve_task and auto_run_remaining bind acceptance; a redo, a retry and a
# risk acknowledgement are recorded and never a build grant.
GATES = [
    ("approve_task", "low", False, True),
    ("redo_task", "low", False, False),
    ("auto_run_remaining", "low", True, True),
    ("fix_retry", "high", False, False),
    ("acknowledge_risk", "high", True, False),
]
EVENTS = "workspace-events.jsonl"


@pytest.fixture(autouse=True)
def attune_absent(monkeypatch):
    """Make ``import attune`` and every submodule fail, whatever is installed."""
    for name in list(sys.modules):
        if name == "attune" or name.startswith("attune."):
            monkeypatch.delitem(sys.modules, name)
    for name in (
        "attune",
        "attune.elicitation",
        "attune.elicitation.command_workspace",
        "attune.spec",
        "attune.spec.workspace",
    ):
        monkeypatch.setitem(sys.modules, name, None)
    with pytest.raises(ImportError):
        import attune.spec.workspace  # noqa: F401


def run(coroutine):
    return asyncio.run(coroutine)


def draft(work):
    record = make(work)
    return Path(record["record_path"]).parent, record


def response(view, action, *, confirmed=False):
    return {
        "__elicitation_response__": True,
        "title": view.record.view.title,
        "view": view.record.view.id.value,
        "action": action,
        "confirmed": confirmed,
        **view.record.binding.to_payload(),
    }


def events(directory):
    text = (directory / EVENTS).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines()]


def opened(work, severity="low"):
    directory, _ = draft(work)
    bridge = WorkSpecBridge(directory)
    view = run(bridge.open(severity=severity, detail="Explicit console approval."))
    return directory, bridge, view


def test_console_approval_is_accepted_and_recorded_without_attune(work):
    directory, bridge, view = opened(work)
    assert [a.id for a in view.record.view.actions] == [
        "approve_task",
        "redo_task",
        "auto_run_remaining",
    ]
    assert read_task(directory)["status"] == "draft"  # a display grants nothing
    assert retained_decision(read_task(directory))["state"] == "current"

    receipt, accepted = run(bridge.collect(response(view, "approve_task")))
    assert receipt.result["disposition"] == "approve_task"
    assert accepted["status"] == "accepted"
    assert accepted["acceptance"]["decision"]["source"] == {
        "owner": "spec",
        "reference": accepted["acceptance"]["decision"]["source"]["reference"],
        "disposition": "approve_task",
    }
    assert accepted["acceptance"]["collector"]["result"]["disposition"] == "approve_task"
    assert read_task(directory)["status"] == "accepted"
    saved = retained_decision(read_task(directory))
    assert saved["response"]["action"] == "approve_task"

    # D14: the render and the accept are evidence beside decision.json.
    recorded = events(directory)
    assert [e["event"] for e in recorded] == ["workspace_rendered", "workspace_accepted"]
    assert {e["workspace_id"] for e in recorded} == {view.record.workspace_id}
    assert recorded[1]["action"] == "approve_task"
    assert recorded[1]["terminal"] is True
    text = (directory / EVENTS).read_text(encoding="utf-8")
    assert view.record.action_nonce not in text
    assert "action_nonce" not in text
    assert bridge.host.dropped_events == 0


def test_a_failing_event_sink_never_blocks_the_decision(work, tmp_path):
    directory, record = draft(work)
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    try:
        (directory / EVENTS).symlink_to(outside / "events.jsonl")
    except OSError as exc:  # Windows without the symlink privilege
        pytest.skip(f"symlinks unavailable: {exc}")
    bridge = WorkSpecBridge(directory)
    view = run(bridge.open())
    receipt, accepted = run(bridge.collect(response(view, "approve_task")))
    assert accepted["status"] == "accepted"
    assert bridge.host.dropped_events == 2
    assert not (outside / "events.jsonl").exists()


def test_auto_run_grants_nothing_until_explicitly_chosen(work):
    """The bridge opens every decision as a gate; nothing is accepted by display."""
    directory, bridge, view = opened(work)
    assert view.record.terminal is False
    assert dict(view.result) == {}
    assert view.record.view.actions
    assert read_task(directory)["status"] == "draft"
    receipt, accepted = run(bridge.collect(response(view, "auto_run_remaining", confirmed=True)))
    assert accepted["acceptance"]["decision"]["source"]["disposition"] == "auto_run_remaining"
    assert receipt.result["disposition"] == "auto_run_remaining"


@pytest.mark.parametrize("action,severity,needs_confirmed,grants", GATES)
def test_every_wired_action_is_refused_without_its_nonce(
    work, action, severity, needs_confirmed, grants
):
    directory, bridge, view = opened(work, severity)
    before = (directory / "record.json").read_bytes()
    payload = response(view, action, confirmed=needs_confirmed)
    del payload["action_nonce"]
    with pytest.raises(ValueError, match="does not match the retained decision"):
        run(bridge.collect(payload))
    forged = {**response(view, action, confirmed=needs_confirmed), "action_nonce": "0" * 64}
    with pytest.raises(ValueError, match="does not match the retained decision"):
        run(bridge.collect(forged))
    assert (directory / "record.json").read_bytes() == before
    assert retained_decision(read_task(directory))["state"] == "current"
    assert [e["event"] for e in events(directory)] == ["workspace_rendered"]


@pytest.mark.parametrize("action,severity,needs_confirmed,grants", GATES)
def test_every_wired_action_is_refused_on_a_drifted_view(
    work, action, severity, needs_confirmed, grants
):
    directory, bridge, view = opened(work, severity)
    payload = response(view, action, confirmed=needs_confirmed)
    correction(work, intent={"goal": "Export every finding, and count them"})
    with pytest.raises(ValueError, match="Work changed after the Spec decision was displayed"):
        run(bridge.collect(payload))
    record = read_task(directory)
    assert record["status"] == "draft"
    assert not record.get("acceptance")
    assert retained_decision(record)["state"] == "historical"
    assert [e["event"] for e in events(directory)] == ["workspace_rendered"]


@pytest.mark.parametrize("action,severity,needs_confirmed,grants", GATES)
def test_every_wired_action_is_refused_when_replayed(
    work, action, severity, needs_confirmed, grants
):
    directory, bridge, view = opened(work, severity)
    payload = response(view, action, confirmed=needs_confirmed)
    receipt, accepted = run(bridge.collect(payload))
    assert receipt.action == action
    record = read_task(directory)
    if grants:
        assert receipt.result["disposition"] == action
        assert accepted["status"] == "accepted"
        assert record["status"] == "accepted"
    else:
        assert accepted is None  # recorded, never a build grant
        assert record["status"] == "draft"
        assert not record.get("acceptance")
        assert retained_decision(record)["response"]["action"] == action
    after = (directory / "record.json").read_bytes()

    # Through the bridge: the display was consumed, or the work moved on.
    expected = (
        "Work changed after the Spec decision was displayed"
        if grants
        else "reopen the current decision"
    )
    with pytest.raises(ValueError, match=expected):
        run(bridge.collect(payload))
    # Through the host alone: the nonce was consumed with the workspace.
    with pytest.raises(CommandWorkspaceError):
        run(bridge.host.collect(payload, expected_adapter_id="spec"))
    # Through the store alone, for a grant: the store's own refusal.
    if grants:
        with pytest.raises(ValueError, match="do not replay a decision"):
            bind_work_acceptance(directory, accepted["acceptance"]["decision"])
    assert (directory / "record.json").read_bytes() == after
    assert [e["event"] for e in events(directory)] == [
        "workspace_rendered",
        "workspace_accepted",
    ]


@pytest.mark.parametrize(
    "action,severity,grants",
    [("auto_run_remaining", "low", True), ("acknowledge_risk", "high", False)],
)
def test_confirmation_is_required_where_the_view_says_so(work, action, severity, grants):
    directory, bridge, view = opened(work, severity)
    with pytest.raises(CommandWorkspaceError, match="confirmation"):
        run(bridge.collect(response(view, action)))
    record = read_task(directory)
    assert record["status"] == "draft"
    assert retained_decision(record)["state"] == "current"  # nothing was collected
    assert [e["event"] for e in events(directory)] == ["workspace_rendered"]
    receipt, accepted = run(bridge.collect(response(view, action, confirmed=True)))
    assert receipt.action == action
    assert receipt.result["disposition"] == action
    if grants:
        assert accepted["status"] == "accepted"
    else:
        assert accepted is None
        assert read_task(directory)["status"] == "draft"


# --- R1: two processes, one task directory ------------------------------------

CHILD = '''
import asyncio, json, sys
sys.modules["attune"] = None
from attune_harness.spec_bridge import WorkSpecBridge

async def main(directory):
    bridge = WorkSpecBridge(directory)
    view = await bridge.open(detail="two processes, one task directory")
    payload = {
        "__elicitation_response__": True,
        "title": view.record.view.title,
        "view": view.record.view.id.value,
        "action": "approve_task",
        "confirmed": False,
        **view.record.binding.to_payload(),
    }
    print(json.dumps({"opened": bridge.decision["digest"]}), flush=True)
    sys.stdin.readline()
    try:
        receipt, accepted = await bridge.collect(payload)
    except ValueError as error:
        print(json.dumps({"refused": str(error)}), flush=True)
    else:
        print(json.dumps({"accepted": accepted["status"] == "accepted"}), flush=True)

asyncio.run(main(sys.argv[1]))
'''


def _child(script, directory):
    return subprocess.Popen(
        [sys.executable, "-u", str(script), str(directory)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={
            **os.environ,
            "PYTHONPATH": str(Path(attune_harness.__file__).resolve().parents[1]),
        },
    )


def _read(child):
    line = child.stdout.readline()
    assert line, child.stderr.read()
    return json.loads(line)


def _go(child):
    child.stdin.write("go\n")
    child.stdin.flush()


def _finish(child):
    _, err = child.communicate(timeout=60)
    assert child.returncode == 0, err


@pytest.mark.parametrize("collects_first", ["second_opener", "first_opener"])
def test_two_processes_end_with_one_acceptance(work, tmp_path, collects_first):
    """Both open the same draft; whichever collects, the store accepts once.

    The second opener's display replaces the first's retained decision. If the
    second collects first, the first's response meets accepted work; if the
    first collects first, its display is no longer the current one. Either way
    one acceptance is recorded, and the refusals are the store's, across
    processes, not the in-process lock's.
    """
    directory, _ = draft(work)
    script = tmp_path / "opener.py"
    script.write_text(CHILD, encoding="utf-8")
    first = _child(script, directory)
    assert "opened" in _read(first)
    second = _child(script, directory)
    assert "opened" in _read(second)
    assert read_task(directory)["status"] == "draft"

    if collects_first == "second_opener":
        _go(second)
        assert _read(second) == {"accepted": True}
        _go(first)
        refused = _read(first)["refused"]
        assert "Work changed after the Spec decision was displayed" in refused
    else:
        _go(first)
        refused = _read(first)["refused"]
        assert "reopen the current decision" in refused
        assert read_task(directory)["status"] == "draft"
        _go(second)
        assert _read(second) == {"accepted": True}
    _finish(first)
    _finish(second)

    record = read_task(directory)
    assert record["status"] == "accepted"
    assert record["acceptance"]["decision"]["source"]["disposition"] == "approve_task"
    saved = retained_decision(record)
    assert saved["response"]["action"] == "approve_task"
    # Two renders (one per opener) and exactly one accept.
    kinds = [e["event"] for e in events(directory)]
    assert kinds.count("workspace_rendered") == 2
    assert kinds.count("workspace_accepted") == 1


# --- the command line ---------------------------------------------------------


def test_plan_accept_runs_without_attune(work, capsys):
    directory, record = draft(work)
    assert (
        main(
            [
                "plan",
                "--task-dir",
                str(directory),
                "--accept",
                "--checkpoint",
                record["checkpoint_digest"],
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "accepted"
    assert result["receipt"]["disposition"] == "approve_task"
    assert "approve_task" in result["decision_markdown"]
    assert read_task(directory)["status"] == "accepted"


def test_plan_accept_without_the_forms_package_reports_the_extra(work, capsys, monkeypatch):
    directory, record = draft(work)

    def missing():
        raise FeatureUnavailable("Install attune-harness[review]; attune-forms is missing")

    monkeypatch.setattr(command_workspace, "_forms", missing)
    monkeypatch.setattr(spec_workspace, "_forms", missing)
    assert (
        main(
            [
                "plan",
                "--task-dir",
                str(directory),
                "--accept",
                "--checkpoint",
                record["checkpoint_digest"],
            ]
        )
        == 2
    )
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "failed"
    assert result["error"]["type"] == "FeatureUnavailable"
    assert "attune-harness[review]" in result["error"]["detail"]
    assert read_task(directory)["status"] == "draft"
