"""Retained decision displays; work and the live collector still own authority."""

import copy
import json
from pathlib import Path

from .features import read_text, write_report
from .review_contract import digest, fields, parse_json, versioned
from .review_store import PersistenceError, RunStore
from .task_contract import read_task, safe_storage
from .work_contract import check_work_fresh, decision_binding

LIMIT = 1048576


def _path(record):
    return Path(record["record_path"]).with_name("decision.json")


def _read(record):
    path = _path(record)
    if path.is_symlink():
        raise ValueError("Saved decision cannot be a symlink")
    value = parse_json(read_text(path, LIMIT), LIMIT)
    fields(value, ("schema_version", "work", "display", "response", "digest"))
    versioned(value)
    if value["digest"] != digest({k: v for k, v in value.items() if k != "digest"}):
        raise ValueError("Saved decision text changed after retention")
    fields(value["work"], decision_binding(record))
    if any(
        value["work"][k] != decision_binding(record)[k]
        for k in ("task_id", "record_path")
    ):
        raise ValueError("Saved decision belongs to another work owner")
    display = value["display"]
    if (
        not isinstance(display, dict)
        or display.get("kind") not in ("questions", "spec")
        or not isinstance(display.get("markdown"), str)
        or not display["markdown"]
    ):
        raise ValueError("Saved decision has no supported text display")
    return value


def retain_decision(record, display, *, response=None, expected=None):
    """Save before returning a form/collecting a response, without changing work."""
    store = RunStore(safe_storage(Path(record["record_path"]).parent), existing=True)
    with store.lease():
        current = read_task(store.directory)
        if current["status"] != "draft" or decision_binding(
            current
        ) != decision_binding(record):
            raise ValueError("Work changed before retaining the decision")
        check_work_fresh(current)
        if expected is not None:
            require_current_decision(current, expected)
        value = {
            "schema_version": 1,
            "work": decision_binding(current),
            "display": copy.deepcopy(display),
            "response": copy.deepcopy(response),
        }
        value["digest"] = digest(value)
        # Bound the formatted bytes written by write_report, not a compact copy.
        payload = (
            json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
        )
        if len(payload.encode("utf-8")) > LIMIT:
            raise ValueError("Saved decision exceeds the display byte limit")
        try:
            write_report(_path(current), value, protected=(store.path,))
        except OSError as exc:
            raise PersistenceError(
                f"Decision text could not be retained: {exc}"
            ) from exc
    return value


def require_current_decision(record, expected):
    """A replaced display is not silently rebound to a delayed Spec response."""
    saved = _read(record)
    if (
        saved["digest"] != expected
        or saved["work"] != decision_binding(record)
        or saved["response"] is not None
    ):
        raise ValueError(
            "Saved decision changed or was collected; reopen the current decision"
        )
    return saved


def retain_questions(record, shown):
    if not shown["missing"]:
        raise ValueError("No unanswered planning questions to retain")
    if shown["checkpoint_digest"] != record["checkpoint_digest"]:
        raise ValueError("Planning questions changed before retention")
    return retain_decision(
        record,
        {
            "kind": "questions",
            "title": shown["definition"]["title"],
            "markdown": shown["markdown"],
            "definition": shown["definition"],
            "field_map": shown["field_map"],
            "response_template": {
                "schema_version": 1,
                "checkpoint_digest": shown["checkpoint_digest"],
                "answers": {},
            },
        },
    )


def retained_decision(record, *, stale=False):
    """Read the latest text only; never recreate a view or restore its authority."""
    path = _path(record)
    if not path.exists() and not path.is_symlink():
        return None  # Work saved before this feature remains inspectable.
    try:
        value = _read(record)
    except (OSError, ValueError) as exc:
        return {"state": "unavailable", "artifact_path": str(path), "error": str(exc)}
    return {
        **value,
        "artifact_path": str(path),
        "state": (
            "historical"
            if stale or value["work"] != decision_binding(record)
            else "collected"
            if value["response"] is not None
            else "current"
        ),
        "note": (
            "Retained text is not approval or proof that its form is still active. "
            "The current collector must validate every response; reopen after host restart. "
            "Work authority is established only by the saved work record."
        ),
    }
