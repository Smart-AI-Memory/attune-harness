"""Explicit, attributed pause notes; no storage, discovery or execution authority."""

from datetime import datetime
import hashlib
from pathlib import Path

from .features import read_text
from .review_contract import bounded_text, fields, parse_json, versioned

MAX_NOTE_BYTES = 32 * 1024


def _list(value, name, limit):
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError(f"{name} must be a list of at most {limit} items")
    return value


def read_continuation(path, record):
    """Associate the declared revision with validated history, not with trust."""
    path = Path(path)
    raw = read_text(path, MAX_NOTE_BYTES)
    note = parse_json(raw, MAX_NOTE_BYTES)
    fields(note, ("schema_version", "task_id", "revision", "recorded_at", "source",
                  "stopped_after", "progress", "next_step",
                  *(key for key in ("briefing", "design_review") if isinstance(note, dict) and key in note)))
    versioned(note)
    request = record["request"]
    if note["task_id"] != request["task_id"]:
        raise ValueError("Continuation note belongs to another task")
    revision = note["revision"]
    if type(revision) is not int or not 1 <= revision <= request["revision"]:
        raise ValueError("Continuation revision must exist in this task's retained history")
    for name in ("source", "recorded_at", "stopped_after"):
        bounded_text(note[name], name, 2048)
    # Python 3.10 needs an explicit offset for the common UTC "Z" spelling.
    timestamp = note["recorded_at"]
    recorded = datetime.fromisoformat(timestamp[:-1] + "+00:00" if timestamp.endswith("Z") else timestamp)
    if recorded.utcoffset() is None:
        raise ValueError("Continuation recorded_at must include a timezone")
    for item in _list(note["progress"], "progress", 6):
        fields(item, ("summary", "references"))
        bounded_text(item["summary"], "progress summary", 2048)
        for reference in _list(item["references"], "references", 6):
            bounded_text(reference, "evidence reference", 2048)
    if note["next_step"] is not None:
        fields(note["next_step"], ("action", "reason"))
        for name, value in note["next_step"].items():
            bounded_text(value, name, 2048)
    if "briefing" in note:
        fields(note["briefing"], ("title", "context", "goal", "desired_end_state",
                                 "current_focus", "done_when"))
        for name, value in note["briefing"].items():
            bounded_text(value, "briefing " + name, 2048)
    if "design_review" in note:
        review = note["design_review"]
        fields(review, ("presentation_revision", "next_question", "feedback"))
        bounded_text(review["presentation_revision"], "presentation revision", 64)
        if review["next_question"] is not None:
            bounded_text(review["next_question"], "next question", 2048)
        for item in _list(review["feedback"], "feedback", 6):
            fields(item, ("criterion", "status", "observation", "references"))
            for key in ("criterion", "observation"):
                bounded_text(item[key], "feedback " + key, 2048)
            if item["status"] not in ("observed", "partial", "unverified"):
                raise ValueError("Feedback status must be observed, partial or unverified")
            for reference in _list(item["references"], "feedback references", 6):
                bounded_text(reference, "feedback reference", 2048)
    baseline = (request if revision == request["revision"]
                else record["history"][revision - 1]["request"])
    return {
        **note, "path": str(path.resolve()),
        "sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "current_revision": revision == request["revision"],
        "changes": _changes(baseline, request),
    }


def _changes(before, after):
    """Compare only saved scope; a revision is not a timestamped run baseline."""
    changes = []
    for name, label in (("goal", "Goal"), ("context", "Context"), ("scope", "File scope"),
                        ("constraints", "Constraints"), ("acceptance", "Success criteria"),
                        ("questions", "Questions and answers")):
        if before["intent"][name] != after["intent"][name]:
            changes.append(
                f'Goal changed: {before["intent"][name] or "Not supplied"} → {after["intent"][name] or "Not supplied"}'
                if name == "goal" else f"{label} changed."
            )
    for name, label in (("choices", "Choices"), ("tasks", "Planned work"),
                        ("evidence", "Captured input evidence"), ("inputs", "Input selection"),
                        ("artifact", "Plan artifact"), ("controls", "Required controls and guidance"),
                        ("assignments", "Participants"), ("budgets", "Budgets"),
                        ("effects", "File effects"), ("signals", "Authoring requirements"),
                        ("config", "Participant configuration"), ("registry", "Participant registry"),
                        ("legacy", "Imported plan"), ("review_handoff", "Review handoff")):
        if before.get(name) != after.get(name):
            changes.append(f"{label} changed.")
    previous = {choice["id"]: choice for choice in before["choices"]}
    for choice in after["choices"]:
        old = previous.get(choice["id"])
        if old is not None and old["selected"] != choice["selected"]:
            changes.append(f'{choice["question"]} {old["selected"] or "Not selected"} → {choice["selected"] or "Not selected"}')
    return changes
