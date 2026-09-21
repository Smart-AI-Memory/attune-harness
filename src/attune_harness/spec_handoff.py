"""Bind existing test receipts to Spec without granting model or write authority."""

from pathlib import Path
import re

from .review_contract import digest, fields
from .review_store import RunStore
from .task_contract import read_task, safe_storage
from .test_change import PROFILE, check_test_fresh
from .test_execution import validate_artifacts

OUTCOMES = frozenset({"passed", "failed", "no_tests", "interrupted", "blocked"})


def validate_test_evidence(binding: dict) -> None:
    """Validate the portable reference without reading historical source state."""
    fields(binding, ("kind", "record_path", "task_id", "checkpoint_digest", "outcome"))
    if (
        binding["kind"] != "harness-test-v1"
        or not isinstance(binding["record_path"], str)
        or not Path(binding["record_path"]).is_absolute()
        or Path(binding["record_path"]).name != "record.json"
        or not isinstance(binding["task_id"], str)
        or not binding["task_id"]
        or not isinstance(binding["checkpoint_digest"], str)
        or not re.fullmatch(r"[0-9a-f]{64}", binding["checkpoint_digest"])
        or not isinstance(binding["outcome"], str)
        or binding["outcome"] not in OUTCOMES
    ):
        raise ValueError("Invalid Harness test evidence binding")


def bind_test_evidence(directory: Path) -> dict:
    """Capture current completed evidence through the existing task owner.

    The checkout freshness check is a cooperating-owner snapshot boundary, not
    an adversarial filesystem transaction spanning later Spec persistence.
    """
    directory = safe_storage(directory)
    with RunStore(directory, existing=True).lease():
        task = read_task(directory)
        if task["task_profile"] != PROFILE or task["status"] != "completed":
            raise ValueError("Spec handoff requires a completed Harness testing task")
        run = task["execution"]
        result = run["result"]
        if (
            len(run["events"]) != 1
            or run["events"][0]["state"] != "completed"
            or run["events"][0]["result"] != result
            or result.get("request_digest") != digest(task["request"])
            or result.get("outcome") not in OUTCOMES
        ):
            raise ValueError(
                "Testing result differs from its completed execution journal"
            )
        check_test_fresh(task)
        validate_artifacts(directory, result)
        binding = {
            "kind": "harness-test-v1",
            "record_path": task["record_path"],
            "task_id": task["request"]["task_id"],
            "checkpoint_digest": task["checkpoint_digest"],
            "outcome": result["outcome"],
        }
        validate_test_evidence(binding)
        return binding


def check_test_evidence(binding: dict) -> None:
    """Reject changed/missing evidence immediately before Spec acceptance."""
    validate_test_evidence(binding)
    current = bind_test_evidence(Path(binding["record_path"]).parent)
    if current != binding:
        raise ValueError("Harness test evidence changed after the Spec gate was bound")


def bind_work_evidence(directory: Path) -> dict:
    """Export completed feature evidence through its existing producer owner."""
    from .task_handoff import completed_source

    _, _, binding = completed_source(directory)
    if binding["kind"] != "completed-feature-v1":
        raise ValueError("Expected a completed feature producer")
    return binding


def check_work_evidence(binding: dict) -> None:
    """Source drift invalidates feature evidence without changing human history."""
    if bind_work_evidence(Path(binding["record_path"]).parent) != binding:
        raise ValueError("Feature evidence changed after the Spec handoff")
