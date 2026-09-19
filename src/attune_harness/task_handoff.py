"""Bind a completed repair to a separately accepted testing task."""

from pathlib import Path
import re

from .review_contract import digest, fields, parse_json


def completed_source(directory: Path) -> tuple[Path, list[str], dict]:
    """Normalize missing/uncertain producer evidence at the existing Spec boundary."""
    from .recovery import UnresolvedOperation

    try:
        return _completed_source(directory)
    except (KeyError, TypeError, UnresolvedOperation) as exc:
        raise ValueError(
            f"Invalid or stale completed producer evidence: {exc}"
        ) from exc


def _completed_source(directory: Path) -> tuple[Path, list[str], dict]:
    """Dispatch qualified repair/feature producers without inventing test authority."""
    from .task_contract import read_task, safe_storage

    directory = safe_storage(directory)
    task = read_task(directory)
    if task.get("task_profile") != "feature-work-v1":
        return completed_repair(directory)
    from .work_build import PROFILE, check_build_fresh, validate_build
    from .work_effects import expected_snapshot

    run = task.get("build", {})
    if (
        task["status"] != "accepted"
        or run.get("profile") != PROFILE
        or run.get("status") != "completed"
    ):
        raise ValueError("Testing handoff requires a completed dependent build")
    request = task["request"]
    verified = validate_build(run, request)
    check_build_fresh(task)
    artifact = digest(expected_snapshot(request["effects"], run["events"]))
    if (
        verified is None
        or not verified["probe"]["passed"]
        or verified["probe"]["artifact_digest"] != artifact
    ):
        raise ValueError("Feature handoff lacks its current protected verification")
    binding = {
        "kind": "completed-feature-v1",
        "record_path": task["record_path"],
        "task_id": request["task_id"],
        "request_digest": digest(request),
        "checkpoint_digest": task["checkpoint_digest"],
        "artifact_digest": artifact,
        "probe_digest": digest(verified["probe"]),
    }
    scope = set(request["effects"]["allowed"])
    from .work_runtime import completed_steps

    for historical in task["history"]:
        completed = completed_steps(historical)
        for step in historical["request"]["tasks"]:
            if step["id"] in completed:
                scope.update(
                    p for p in step["outputs"] if p in request["effects"]["protected"]
                )
    return Path(request["project_root"]), sorted(scope), binding


def completed_repair(directory: Path) -> tuple[Path, list[str], dict]:
    """Read current host-owned repair evidence without dispatch or new authority."""
    from .recovery import UnresolvedOperation

    try:
        return _completed_repair(directory)
    except (KeyError, TypeError, UnresolvedOperation) as exc:
        raise ValueError(f"Invalid or stale completed repair evidence: {exc}") from exc


def _completed_repair(directory: Path) -> tuple[Path, list[str], dict]:
    from .repair import expected_snapshot
    from .task_contract import PROFILE, check_fresh, read_task, safe_storage

    directory = safe_storage(directory)
    task = read_task(directory)
    request = task["request"]
    if (
        task["task_profile"] != PROFILE
        or "repair" not in request
        or task["status"] != "completed"
    ):
        raise ValueError("Testing handoff requires a completed repair task")
    check_fresh(task)
    run = task["execution"]
    integrated = run.get("integration", {})
    scope = request["repair"]["scope"]
    artifact = digest(expected_snapshot(scope, run["events"]))
    _check_probe(run, scope, "before", digest(scope["before"]))
    probe = _check_probe(run, scope, "after", artifact)
    if (
        integrated.get("acceptance_status") != "verified_within_probe_scope"
        or probe.get("passed") is not True
        or run.get("before_probe", {}).get("passed") is not False
        or integrated.get("artifact_digest") != artifact
        or integrated.get("probe_digest") != digest(probe)
        or integrated.get("review_policy") != request["repair"]["review"]
    ):
        raise ValueError(
            "Repair handoff lacks current artifact/probe acceptance evidence"
        )
    if request["repair"]["review"] != "none":
        review = run.get("review", {})
        _check_review(run, review)
        if (
            review.get("verdict") != "approve"
            or review.get("findings") != []
            or review.get("artifact_digest") != artifact
            or review.get("probe_digest") != digest(probe)
            or integrated.get("review") != review
        ):
            raise ValueError("Repair handoff lacks its accepted independent review")
    # The completed patch was host-validated and the final snapshot rechecked above.
    changed = sorted(item["path"] for item in run["patch"]["replacements"])
    if (
        not changed
        or len(changed) != len(set(changed))
        or not set(changed) <= set(scope["allowed"])
    ):
        raise ValueError("Repair handoff has invalid replacement scope")
    applied = [
        event["patch"]
        for event in run["events"]
        if event["kind"] == "replacement" and event["state"] == "completed"
    ]
    if sorted(applied, key=lambda item: item["path"]) != sorted(
        run["patch"]["replacements"], key=lambda item: item["path"]
    ):
        raise ValueError(
            "Repair handoff patch differs from completed replacement evidence"
        )
    binding = {
        "kind": "completed-repair-v1",
        "record_path": task["record_path"],
        "task_id": request["task_id"],
        "request_digest": digest(request),
        "checkpoint_digest": task["checkpoint_digest"],
        "artifact_digest": artifact,
        "probe_digest": digest(probe),
    }
    return Path(scope["root"]), changed, binding


def _check_probe(run: dict, scope: dict, phase: str, artifact: str) -> dict:
    """A summary cannot substitute for the probe actually journaled by the host."""
    probe = run[f"{phase}_probe"]
    events = [
        event for event in run["events"] if event["operation_key"] == f"probe:{phase}"
    ]
    if len(events) != 1:
        raise ValueError("Repair handoff lacks a unique journaled probe")
    event = events[0]
    passed = phase == "after"
    if (
        event["kind"] != "acceptance_probe"
        or event["state"] != "completed"
        or event["result"] != probe
        or event["plan_digest"] != digest(scope)
        or event["artifact_digest"] != artifact
        or probe["plan_digest"] != digest(scope)
        or probe["artifact_digest"] != artifact
        or probe["argv"] != scope["probe"]["argv"]
        or probe["passed"] is not passed
        or type(probe["returncode"]) is not int
        or (probe["returncode"] != 0 if passed else probe["returncode"] <= 0)
        or probe["failure"] != (None if passed else "nonzero_exit")
    ):
        raise ValueError(
            "Repair handoff probe summary contradicts its journal or outcome"
        )
    return probe


def _check_review(run: dict, review: dict) -> None:
    """Require the recorded reviewer response, projection and summary to agree."""
    assignment = run["recovery"]["assignments"]["reviewer"]
    participant = run["participants"]["reviewer"]
    events = [
        event
        for event in run["events"]
        if event["operation_key"] == assignment["attempt_id"] + ":turn:0"
    ]
    if len(events) != 1:
        raise ValueError("Repair handoff lacks its journaled reviewer response")
    event = events[0]
    if (
        event["kind"] != "participant_turn"
        or event["state"] != "completed"
        or any(
            event[name] != assignment[name] or participant[name] != assignment[name]
            for name in ("participant_id", "attempt_id")
        )
        or participant["status"] != "completed"
        or event["result"]["action"]["kind"] != "final"
        or event["result"]["action"]["text"] != participant["text"]
        or parse_json(participant["text"]) != review
    ):
        raise ValueError(
            "Repair handoff review summary contradicts its journaled response"
        )


def validate_handoff(binding: dict) -> None:
    """Validate the additive reference without reading or granting its authority."""
    fields(
        binding,
        (
            "kind",
            "record_path",
            "task_id",
            "request_digest",
            "checkpoint_digest",
            "artifact_digest",
            "probe_digest",
        ),
    )
    if (
        binding["kind"] not in ("completed-repair-v1", "completed-feature-v1")
        or not isinstance(binding["record_path"], str)
        or not Path(binding["record_path"]).is_absolute()
        or Path(binding["record_path"]).name != "record.json"
        or not isinstance(binding["task_id"], str)
        or not binding["task_id"]
    ):
        raise ValueError("Invalid repair handoff identity")
    for name in (
        "request_digest",
        "checkpoint_digest",
        "artifact_digest",
        "probe_digest",
    ):
        if not isinstance(binding[name], str) or not re.fullmatch(
            "[0-9a-f]{64}", binding[name]
        ):
            raise ValueError("Invalid repair handoff digest")


def check_handoff(request: dict) -> None:
    """Reject a changed producer or an overridden checkout/scope on every reuse."""
    if "source_task" not in request:
        return
    binding = request["source_task"]
    validate_handoff(binding)
    root, changed, current = completed_source(Path(binding["record_path"]).parent)
    if (
        current != binding
        or str(root) != request["project_root"]
        or changed != request["selection"]["scope"]
    ):
        raise ValueError(
            "Stale or overridden repair handoff; create a new accepted test task"
        )
