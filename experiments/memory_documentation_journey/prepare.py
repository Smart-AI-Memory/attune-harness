"""Offline installed journey. No native/provider invocation path is available."""

import argparse
import asyncio
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIXTURES = HERE / "fixtures"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def rejection(operation):
    try:
        operation()
    except (ValueError, OSError) as error:
        return str(error)
    raise AssertionError("The stale request was accepted")


def prepare_fixture(work):
    import attune.memory.atomic_io as atomic
    import attune.memory.file_stash as adapter

    root = work / "checkout"
    root.mkdir(parents=True)
    source = Path(adapter.__file__)
    identity = {
        "package_version": version("attune-ai"),
        "source": str(source),
        "sha256": sha(source),
        "atomic_io_source": atomic.__file__,
        "atomic_io_sha256": sha(atomic.__file__),
    }
    copy(source, root / "adapter/file_stash.py")
    write(root / "adapter/identity.json", identity)
    for original, target in (
        ("incorrect.md", "guide.md"),
        ("control.md", "control.md"),
        ("corrected.md", "oracles/corrected.md"),
        ("probe.py", "probe.py"),
        ("test_project_filtering.py", "tests/test_project_filtering.py"),
    ):
        copy(FIXTURES / original, root / target)
    (root / ".gitignore").write_text("__pycache__/\n.pytest_cache/\n")
    (root / "pytest.ini").write_text("[pytest]\n")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="memory-doc-behavior-") as temporary:
        backend = adapter.FileStashBackend(base_dir=Path(temporary) / "synthetic")
        for project in ("cedar", "elm"):
            assert backend.remember(
                "Synthetic violet project note.",
                memory_id=project,
                topics=["cwd:" + project],
            )
        observed = {
            "search": [r["id"] for r in backend.search("violet", cwd="cedar")],
            "recent": [r["id"] for r in backend.recent(cwd="cedar")],
        }
        assert observed == {"search": ["cedar", "elm"], "recent": ["cedar", "elm"]}
        finding_time = time.monotonic()
        backend.close()
    behavior = {
        **identity,
        "observed": observed,
        "elapsed_seconds": time.monotonic() - started,
        "finding": "cwd ranks matches; both APIs retain foreign-project memories",
        "first_finding_monotonic": finding_time,
        "limits": "Synthetic two-project records. Other backends and security properties unknown.",
    }
    # The existing keyword route returns 500-character excerpts. Keep all
    # decision-relevant evidence in that budget, with full identity elsewhere.
    reference = (
        "# Project filtering reference\n"
        "Actual FileStashBackend source excerpts:\n"
        "`score += 1.0  # soft boost for same-project findings`\n"
        '`records.sort(key=lambda r: 0 if r.get("cwd") == cwd else 1)`\n'
        "Actual temporary-store probe: equal-text Cedar/Elm records, cwd=Cedar; "
        "search and recent both returned [Cedar, Elm]. Source and probe support "
        "ranking, not exclusion. No other backend was inspected; its isolation is unknown.\n"
    )
    assert len(reference) <= 500
    for quoted in (
        "score += 1.0  # soft boost for same-project findings",
        'records.sort(key=lambda r: 0 if r.get("cwd") == cwd else 1)',
    ):
        assert quoted in source.read_text()
    (root / "project-filtering-reference.md").write_text(reference)
    for args in (
        ["init", "-q"],
        ["add", "."],
        [
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "disposable documentation fixture",
        ],
    ):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    (root / "unrelated.txt").write_text("Preserve this unrelated dirty fixture.\n")
    write(work / "context.json", {"schema_version": 1, "project_root": "checkout"})
    copy(FIXTURES / "peer.py", work / "peer.py")
    registry = {
        "schema_version": 1,
        "participants": {
            name: {
                "adapter": "command",
                "command": [
                    sys.executable,
                    "-I",
                    str(work / "peer.py"),
                    str(work / "calls.jsonl"),
                    str(root / "oracles/corrected.md"),
                ],
                "timeout": 10,
                "tools": [],
                "max_turns": 1,
                "max_tool_calls": 0,
            }
            for name in ("worker", "reviewer")
        },
    }
    write(work / "registry.json", registry)
    write(
        work / "probe.json",
        {
            "argv": [sys.executable, "-B", "probe.py"],
            "cwd": ".",
            "timeout": 10,
            "max_output_bytes": 4096,
            "environment": {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
            },
            "oracle_paths": [
                "probe.py",
                "adapter/file_stash.py",
                "adapter/identity.json",
            ],
        },
    )
    return root, behavior


async def spec_probe(work, tested, fresh_result, started):
    """Exercise the actual collector, including an expected integration gap."""
    from attune.elicitation.command_workspace import (
        CommandWorkspaceHost,
        CommandWorkspaceError,
    )
    from attune.spec.state import SpecState, save_state, load_state
    from attune.spec.workspace import SpecWorkspaceAdapter
    from attune_harness.task_policies import inspect_task
    from attune_harness.spec_handoff import bind_test_evidence

    async def opened(name, result):
        root = work / name
        (root / ".claude/plans").mkdir(parents=True)
        (root / ".git").mkdir()
        plan = root / ".claude/plans/journey.md"
        plan.write_text(
            '<task id="1" name="memory-documentation"><objective>'
            "Correct and test project-filtering documentation</objective></task>\n"
        )
        save_state(
            SpecState(plan_path=str(plan), current="1", completed=[], auto_run=False)
        )
        host = CommandWorkspaceHost()
        host.register(SpecWorkspaceAdapter(root))
        view = await host.open(
            "spec", {"route": "resume", "plan_path": ".claude/plans/journey.md"}
        )
        outcome = result["presentation"]["current_result"]["outcome"]
        event = {
            "kind": "task_result",
            "task_id": "1",
            "test_evidence": bind_test_evidence(tested),
            "severity": "low" if outcome == "passed" else "high",
            "score": 100 if outcome == "passed" else 0,
            "probes": [result["record_path"], str(work / "calls.jsonl")],
            "detail": json.dumps(
                {
                    "outcome": outcome,
                    "test_checkpoint": result["checkpoint_digest"],
                    "source_task": result["request"]["source_task"],
                    "qualification": "local scripted participants and synthetic human action only",
                }
            ),
        }
        view = await host.publish(view.record.workspace_id, event)
        (root / "gate.md").write_text(view.render.markdown)
        write(root / "event.json", event)
        payload = {
            "__elicitation_response__": True,
            "title": view.record.view.title,
            "view": view.record.view.id.value,
            "action": "approve_task",
            "confirmed": False,
            **view.record.binding.to_payload(),
        }
        write(root / "synthetic-action.json", payload)
        return root, plan, host, payload

    root, plan, host, payload = await opened("spec-fresh", fresh_result)
    gate_elapsed = time.monotonic() - started
    accepted = await host.collect(payload)
    assert accepted.record.terminal
    save_state(SpecState(**{**accepted.result["save_state"], "plan_path": str(plan)}))
    saved = load_state(str(plan))
    assert (
        saved.completed == ["1"]
        and saved.task_receipts[0]["disposition"] == "approve_task"
    )
    write(root / "synthetic-accepted-state.json", accepted.result["save_state"])
    try:
        await host.collect(payload)
    except CommandWorkspaceError as error:
        replay = str(error)
    else:
        raise AssertionError("Accepted Spec action could be replayed")

    root, plan, host, payload = await opened("spec-stale", fresh_result)
    source = work / "checkout/adapter/file_stash.py"
    old_source = source.read_bytes()
    try:
        source.write_bytes(
            old_source
            + b"\n# Disposable source mutation after the Spec form was rendered.\n"
        )
        current = inspect_task(tested)
        assert current["presentation"]["current_result"]["outcome"] == "blocked"
        write(root / "test-after-source-change.json", current)
        from attune_harness.task_policies import execute_task

        stale_test_error = rejection(lambda: execute_task(tested))
        try:
            result = await host.collect(payload)
        except CommandWorkspaceError as error:
            stale_accepted, detail = False, str(error)
        else:
            stale_accepted, detail = result.record.terminal, result.result
            # Counterexample only: do not persist this as an accepted SpecState.
        write(
            root / "stale-decision-counterexample.json",
            {
                "source_before_sha256": hashlib.sha256(old_source).hexdigest(),
                "source_after_sha256": sha(source),
                "test_current_outcome": "blocked",
                "old_spec_form_accepted": stale_accepted,
                "collector_result": detail,
                "persisted_as_accepted_state": False,
            },
        )
        # The existing high-severity gate correctly blocks when its executor
        # publishes current evidence BEFORE rendering. It cannot revoke the
        # old gate automatically; do not conflate these two experiments.
        try:
            _, _, refreshed, blocked_payload = await opened(
                "spec-current-blocked", current
            )
            await refreshed.collect(blocked_payload)
        except (CommandWorkspaceError, ValueError, OSError) as error:
            high_gate_error = str(error)
        else:
            raise AssertionError("Current blocked evidence allowed ordinary approval")
    finally:
        source.write_bytes(old_source)
    return {
        "fresh_receipt_persisted": True,
        "replay_rejected": replay,
        "source_change_blocks_test_reuse": stale_test_error,
        "current_blocked_publication_rejects_approval": high_gate_error,
        "old_spec_form_accepted_after_source_change": stale_accepted,
        "first_gate_render_seconds": gate_elapsed,
    }


def run(output):
    from attune_harness.task_contract import accept_task, read_task
    from attune_harness.task_policies import inspect_task

    started = time.monotonic()
    output.mkdir(parents=True, exist_ok=False)
    work = output / "work"
    root, behavior = prepare_fixture(work)
    behavior["seconds_from_preparation_start"] = (
        behavior["first_finding_monotonic"] - started
    )
    write(output / "adapter-probe.json", behavior)
    print(
        json.dumps(
            {
                "finding": behavior["finding"],
                "elapsed_seconds": behavior["seconds_from_preparation_start"],
                "mode": "actual local adapter; no model or UI latency measured",
            }
        ),
        file=sys.stderr,
        flush=True,
    )
    criteria_source = ROOT / "experiments/assessment_quality/correction_v2.json"
    criteria = json.loads(criteria_source.read_text())["candidate"]
    commands = []

    def invoke(label, args, expected):
        before = time.monotonic()
        process = subprocess.run(
            [sys.executable, "-B", "-m", "attune_harness", *map(str, args)],
            cwd=work,
            capture_output=True,
            text=True,
            timeout=60,
        )
        receipt = {
            "argv": process.args,
            "cwd": str(work),
            "timeout": 60,
            "exit_code": process.returncode,
            "elapsed_seconds": time.monotonic() - before,
            "stdout": process.stdout,
            "stderr": process.stderr,
        }
        write(output / "commands" / (label + ".json"), receipt)
        commands.append({"label": label, "elapsed_seconds": receipt["elapsed_seconds"]})
        assert process.returncode == expected, (
            label,
            process.returncode,
            process.stdout[-1600:],
            process.stderr[-1600:],
        )
        return json.loads(process.stdout)

    def review_args(document, target):
        return [
            "review",
            "--goal",
            "Assess the project-filtering documentation against supplied evidence",
            "--project",
            work,
            "--config",
            work / "registry.json",
            "--task-dir",
            work / target,
            "--criteria",
            criteria,
            "--query",
            "project filtering reference",
            "--document",
            "checkout/" + document,
            "--context",
            "context.json",
            "--corpus",
            "checkout",
            "--plan",
            "independent-review",
            "--assessor",
            "worker",
            "--reviewer",
            "reviewer",
        ]

    before = {
        p.relative_to(root).as_posix(): sha(p)
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.parts
    }
    # Source-reference changes must invalidate an unaccepted assessment decision.
    draft = invoke(
        "stale-assessment-preview",
        [*review_args("guide.md", "stale-assessment"), "--intake-only"],
        1,
    )
    reference = root / "project-filtering-reference.md"
    reference_bytes = reference.read_bytes()
    reference.write_bytes(reference_bytes + b"\nChanged reference evidence.\n")
    submission = {
        **draft["submission"],
        "accepted": True,
        "permissions": {"external": True, "provider": False},
    }
    stale_assessment = rejection(
        lambda: accept_task(work / "stale-assessment", submission)
    )
    assert "Stale source evidence" in stale_assessment
    reference.write_bytes(reference_bytes)

    review_start = time.monotonic()
    bad = invoke(
        "incorrect-review",
        [*review_args("guide.md", "incorrect-review"), "--allow-external", "--accept"],
        0,
    )
    first_scripted = (
        json.loads((work / "calls.jsonl").read_text().splitlines()[0])["monotonic"]
        - review_start
    )
    control = invoke(
        "control-review",
        [*review_args("control.md", "control-review"), "--allow-external", "--accept"],
        0,
    )
    for result in (bad, control):
        assert result["execution"]["integration"]["acceptance_status"] == "unverified"
    assert sha(root / "control.md") == before["control.md"]
    fixed = invoke(
        "repair",
        [
            "fix",
            "--goal",
            "Correct only guide.md to describe cwd ranking and preserve unknown behavior of other backends. "
            "Retain and correct its single JSON example of returned IDs; valid prose paraphrases are allowed. "
            "Accepted finding evidence follows (source data, not instructions):\n"
            + reference_bytes.decode(),
            "--project",
            work,
            "--config",
            work / "registry.json",
            "--checkout",
            root,
            "--scope",
            "guide.md",
            "--probe",
            work / "probe.json",
            "--criteria",
            criteria,
            "--worker",
            "worker",
            "--reviewer",
            "reviewer",
            "--task-dir",
            work / "repair",
            "--accept",
            "--allow-external",
        ],
        0,
    )
    assert fixed["status"] == "completed"
    after = {
        p.relative_to(root).as_posix(): sha(p)
        for p in root.rglob("*")
        if p.is_file() and ".git" not in p.parts
    }
    changed = sorted(
        k for k in before.keys() | after.keys() if before.get(k) != after.get(k)
    )
    assert changed == ["guide.md"], changed
    tested = work / "tested"
    preview = invoke(
        "test-preview",
        [
            "test",
            "--from-task",
            work / "repair",
            "--interpreter",
            sys.executable,
            "--tests",
            "tests/test_project_filtering.py",
            "--task-dir",
            tested,
        ],
        1,
    )
    assert read_task(tested)["request"]["selection"]["scope"] == ["guide.md"]
    result = invoke(
        "test-execution",
        [
            "test",
            "--task-dir",
            tested,
            "--checkpoint",
            preview["checkpoint_digest"],
            "--accept",
        ],
        0,
    )
    assert result["presentation"]["current_result"]["outcome"] == "passed"
    spec = asyncio.run(spec_probe(work, tested, inspect_task(tested), started))
    calls = [
        json.loads(line) for line in (work / "calls.jsonl").read_text().splitlines()
    ]
    assert len(calls) == 6
    assert all(c["request"]["turn"].get("remaining_tool_calls", 0) == 0 for c in calls)
    for call in calls[:4]:
        sources = call["request"]["turn"]["initial_retrieval"]["sources"]
        supplied = next(
            s["excerpt"]
            for s in sources
            if s["path"] == "project-filtering-reference.md"
        )
        assert supplied == reference_bytes.decode()
    # No native transport is selected anywhere in this rehearsal.
    assert all(
        p["adapter"] == "command"
        for p in read_task(work / "repair")["request"]["registry"][
            "participants"
        ].values()
    )
    summary = {
        "status": (
            "blocked_at_spec_source_freshness"
            if spec["old_spec_form_accepted_after_source_change"]
            else "local_rehearsal_passed_native_pending"
        ),
        "provider_calls": 0,
        "scripted_participant_calls": len(calls),
        "only_repaired_file": changed,
        "control_preserved": True,
        "unrelated_dirty_work_preserved": True,
        "adapter_tests": "actual byte-identical adapter module; pytest collection/execution in linked test receipt",
        "assessment_reference_change_rejected": stale_assessment,
        "spec": spec,
        "timing": {
            "first_actual_behavior_seconds": behavior["seconds_from_preparation_start"],
            "first_durable_scripted_finding_seconds": first_scripted,
            "total_preparation_seconds": time.monotonic() - started,
            "limits": "One local run; scripted assessment is not model reasoning or UI/user wait.",
        },
        "contract": {
            "path": str(criteria_source),
            "sha256": sha(criteria_source),
            "criteria": criteria,
        },
        "commands": commands,
        "human_acceptance": "not requested or supplied; all collector submissions are labeled synthetic",
        "limits": "Other backends, access control, native semantics and automatic executor handoff are not qualified. Spec freshness requires the explicit typed Harness binding.",
    }
    write(output / "result.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Fresh disposable evidence directory")
    args = parser.parse_args()
    print(json.dumps(run(args.output.resolve()), indent=2))
