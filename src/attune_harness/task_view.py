"""Bounded, read-only feature-work snapshots; the saved owner keeps authority."""

import copy
from datetime import datetime, timezone
import base64
import hashlib
import html
import json
from pathlib import Path

from .spec_presenter import _literal, _plain
from .task_contract import read_task
from .task_continuation import read_continuation
from .work_cli import present

MAX_VIEW_BYTES = 512 * 1024
SNAPSHOT_NOTE = (
    "Snapshot: this page does not refresh. Capture time identifies this inspection, "
    "not a guarantee that files or task state remain unchanged. Inspect again before acting."
)
EXTERNAL_NOTE = (
    "External artifacts are not recorded execution. Explicit continuation notes "
    "are attributed reports; their references are not checked or opened. "
    "No task completion or acceptance is inferred from them."
)


def inspect(directory, *, continuation=None):
    """Read and validate one record, then project existing status without dispatch."""
    record = read_task(directory)
    if record["task_profile"] != "feature-work-v1":
        raise ValueError("Human-readable snapshots require feature-work-v1; use --format json for this task")
    status = present(directory, inspect_only=True, _record=record)
    fields = (
        "task_id", "revision", "checkpoint_digest", "authority", "status", "phase",
        "completed", "preserved_completion", "missing", "summary", "blocking",
        "next_action", "note", "intent", "tasks", "controls", "evidence", "record_path",
    )
    view = {name: copy.deepcopy(status[name]) for name in fields}
    view.update(
        schema_version=1,
        view="feature-work-snapshot-v1",
        captured_at=datetime.now(timezone.utc).isoformat(),
        project_root=record["request"]["project_root"],
        continuation=read_continuation(continuation, record) if continuation is not None else None,
        choices=copy.deepcopy(record["request"]["choices"]),
        execution_recorded=any(name in record for name in ("planning", "build")),
        advisory=[],
        runs=[
            {key: run[key] for key in ("phase", "run_pointer", "request_pointer")}
            for run in status["execution_evidence"]["runs"]
        ],
    )
    phase = "build" if "build" in record else "planning"
    for index, advice in enumerate(status["advisory"]):
        # Optional control results can contain full output; retain a reference instead.
        item = {k: v for k, v in advice.items() if k in ("id", "status", "source", "kind", "count", "pointer")}
        item.setdefault("pointer", f"/{phase}/advisory/{index}")
        view["advisory"].append(item)
    for name in ("freshness_error", "readiness_error", "run_error"):
        if name in status:
            view[name] = copy.deepcopy(status[name])
    _check_size(view)
    return view


def _check_size(view):
    if len(json.dumps(view, ensure_ascii=False, allow_nan=False).encode("utf-8")) > MAX_VIEW_BYTES:
        raise ValueError("Task snapshot exceeds the 512 KiB view limit; use --format json to inspect the full status")


def _sections(view):
    """One content outline for both renderers; values remain literal text."""
    yield "Snapshot identity", [
        ("Project", view["project_root"]), ("Task", view["task_id"]),
        ("Revision", view["revision"]), ("Checkpoint", view["checkpoint_digest"]),
        ("Captured at (UTC)", view["captured_at"]), ("Record", view["record_path"]),
        ("Freshness", view.get("freshness_error", "Checked during this inspection")),
        ("Status", view["status"]), ("Phase", view["phase"]),
        ("Authority", view["authority"]), ("Blocking", "yes" if view["blocking"] else "no"),
    ]
    if view["continuation"] is not None:
        yield "Continuation source", [("File", view["continuation"]["path"]),
                                      ("SHA-256", view["continuation"]["sha256"]),
                                      ("Trust", "Identity and revision association checked; authorship and claims are not authenticated.")]
    intent = view["intent"]
    for key, heading in (("context", "Context"), ("scope", "Scope"),
                         ("constraints", "Constraints"), ("acceptance", "Acceptance criteria")):
        yield heading, [(str(i + 1), value) for i, value in enumerate(intent[key])] or [("Status", "Not supplied")]
    questions = []
    for question in intent["questions"]:
        questions.extend([
            (question["id"], question["question"]),
            ("Answer", question["answer"] or "Unanswered"),
            ("Material", "Yes" if question["material"] else "No"),
        ])
    yield "Questions", questions or [("Status", "No questions recorded")]
    choices = []
    for choice in view["choices"]:
        choices.extend([
            (choice["id"], choice["question"]),
            ("Selection", f'{choice["selected"]} (saved selection)' if choice["selected"] else "Not selected"),
        ])
        for option in choice["options"]:
            choices.extend([
                ("Option " + option["id"], option["proposal"]),
                ("Rationale", option["rationale"]),
                ("Counter-case", option["counter_case"]),
                ("Evidence", "; ".join(option["evidence"]) or "Not supplied"),
                ("Uncertainty", "; ".join(option["uncertainty"]) or "None stated"),
            ])
    yield "Choices", choices or [("Status", "No choices recorded")]
    rows = []
    for task in view["tasks"]:
        checked = task["id"] in view["completed"]
        rows.extend([
            (task["id"], task["objective"]),
            ("Recorded completion", "Protected check passed" if checked else "Not established"),
            ("Dependencies", ", ".join(task["dependencies"]) or "None"),
            ("Outputs", ", ".join(task["outputs"]) or "None"),
        ])
        rows.extend(("Check", check) for check in task["checks"])
    yield "Planned tasks", rows or [("Status", "No tasks staged")]
    yield "Completion evidence", [
        ("Current revision", ", ".join(view["completed"]) or "No task completion established"),
        ("Preserved prior completion", ", ".join(view["preserved_completion"]) or "None"),
        ("Meaning", "These are recorded passing checks. Stale evidence does not establish current completion; planning completion does not establish build completion."),
    ]
    labels = {"goal": "Goal", "scope": "Scope", "acceptance": "Acceptance criteria"}
    labels.update({"question:" + q["id"]: q["question"] for q in intent["questions"]})
    labels.update({"choice:" + c["id"]: c["question"] for c in view["choices"]})
    yield "Missing information", [("Required", labels.get(value, value)) for value in view["missing"]] or [("Status", "None reported")]
    yield "Execution evidence", [
        ("Current revision", "Recorded execution; inspect the references below" if view["execution_recorded"] else "No recorded execution"),
        ("Request", "/request"), ("Checkpoint", "/checkpoint_digest"),
        *[(run["phase"], f'{run["run_pointer"]} (request: {run["request_pointer"]})') for run in view["runs"]],
        ("References", "JSON pointers resolve within the saved record; historical runs are labeled by their /history/ path."),
    ]
    yield "Host checks", [
        (check["operation"], f'{"Passed" if check["passed"] else "Failed"} · {check["failure"] or "no failure recorded"} · {check["pointer"]}')
        for check in view["evidence"]["checks"]
    ] or [("Status", "No recorded host checks")]
    yield "Reviewer findings", [
        (review["source"], f'{review["blocking_findings"]} blocking, {review["other_findings"]} other · {review["pointer"]}')
        for review in view["evidence"]["reviews"]
    ] or [("Status", "No recorded reviewer findings")]
    yield "Optional advice", [
        (advice.get("source", advice.get("id", "Advice")), " · ".join(f"{key}: {value}" for key, value in advice.items() if key not in ("source", "id")))
        for advice in view["advisory"]
    ] or [("Status", "No optional advice recorded")]
    errors = [(name.replace("_", " ").capitalize(), view[name]) for name in ("readiness_error", "run_error") if name in view]
    if "rejected_reply" in view["evidence"]:
        errors.append(("Rejected reply", view["evidence"]["rejected_reply"]))
    if errors:
        yield "Details requiring attention", [(label, json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value) for label, value in errors]
    yield "Inspection limits", [("Snapshot", SNAPSHOT_NOTE), ("Artifacts", EXTERNAL_NOTE), ("Authority", view["note"])]


def _overview(view):
    """Orientation first; saved-owner guidance has precedence over any pause note."""
    handoff = (f'Help me continue the saved task at {Path(view["record_path"]).parent}. '
               f'The snapshot showed revision {view["revision"]}. Inspect its current status '
               'before acting, then follow its next-action guidance within existing authorization.')
    yield "Next useful step", [("Action", view["next_action"]), ("Why", view["summary"]),
                               ("Assistant handoff", handoff)]
    if view["intent"]["acceptance"]:
        yield "Intended result", [("Success", text) for text in view["intent"]["acceptance"][:2]] + (
            [("More", "Full success criteria are in the supporting detail.")]
            if len(view["intent"]["acceptance"]) > 2 else [])
    note = view["continuation"]
    if note is None:
        yield "Where you stopped", [("Context", "No stopping point was supplied. Saved task context is available below; it may not include work from your conversation."),
                                    *[("Saved context", text) for text in view["intent"]["context"]]]
        yield "What changed", [("Comparison", "No comparison baseline was supplied. This is current task state, not a history of activity.")]
    else:
        rows = [("Stopping point", note["stopped_after"]),
                ("Reported by", note["source"]), ("Recorded at", note["recorded_at"])]
        if not note["current_revision"]:
            rows.append(("Freshness", "Historical note: the saved task has a newer revision; the suggestion is withheld."))
        else:
            rows.append(("Freshness", "The note names the current scope revision. Its reported work and references are not checked by this inspection."))
        yield "Where you stopped", rows
        progress = []
        for item in note["progress"]:
            progress.append(("Reported progress", item["summary"]))
            progress.append(("Evidence references", "; ".join(item["references"]) or "None supplied; this claim has no attached evidence reference"))
        yield "Reported outside Harness", [*(progress or [("Progress", "No external progress reported")]),
                                            ("Evidence limit", EXTERNAL_NOTE)]
        changes = [("Comparison", f'Baseline: revision {note["revision"]}; current revision {view["revision"]}.')]
        changes.extend(("Changed", change) for change in note["changes"])
        if not note["changes"]:
            changes.append(("Saved scope", "No saved scope changes against the declared baseline."))
        changes.append(("Limit", "Compares retained request scope only. Run progress since the note and changes to external references are not compared."))
        yield "What changed", changes
        if note["next_step"] is not None:
            allowed = note["current_revision"] and not view["blocking"] and view["status"] != "completed"
            yield "Retained suggestion", (
                [("Suggestion, not authorization", note["next_step"]["action"]), ("Reason", note["next_step"]["reason"])]
                if allowed else [("Status", "The note's suggestion is withheld. Follow the current task guidance above before choosing further work.")]
            )
    attention = []
    for question in view["intent"]["questions"]:
        if question["answer"] is None and question["material"]:
            attention.append(("Answer needed", question["question"]))
    for choice in view["choices"]:
        if choice["selected"] is None:
            attention.append(("Decision needed", choice["question"]))
    if view["blocking"]:
        attention.insert(0, ("Before continuing", view["summary"]))
    if attention:
        yield "Needs your attention", attention
    checked = [task for task in view["tasks"] if task["id"] in view["completed"]]
    label = "Prior checks need revalidation" if "freshness_error" in view else "Recorded passing checks"
    progress = [(label, task["objective"]) for task in checked[:3]]
    if len(checked) > 3:
        progress.append(("More", f"{len(checked) - 3} further tasks have recorded checks; see Planned tasks below."))
    if not checked:
        progress.append(("Harness checks", "No task completion is established by the current journal. Reported external work remains separate."))
    if view["preserved_completion"]:
        progress.append(("Earlier revision", "Prior completion is retained for " + ", ".join(view["preserved_completion"]) + "; inspect Completion evidence below for its applicability."))
    yield "Recorded progress", progress
    completed = set() if "freshness_error" in view else set(view["completed"])
    remaining = [task for task in view["tasks"] if task["id"] not in completed]
    rows = [("Next planned work", task["objective"]) for task in remaining[:3]]
    if len(remaining) > 3:
        rows.append(("More", f"{len(remaining) - 3} further tasks are listed in Planned tasks below."))
    if not view["tasks"]:
        rows.append(("Plan", "No tasks have been staged."))
    elif not remaining:
        rows.append(("Verified progress", "All planned tasks have recorded passing checks; review the evidence below."))
    rows.append(("Meaning", "Remaining work is based on Harness checks. Reported external work may already cover part of it; review the references before repeating work."))
    yield "Remaining planned work", rows
    if note is not None:
        yield "Correct this understanding", [("Context", "Edit your supplied continuation file or provide a newer one. Correct task intent through plan --revise; neither action implies acceptance."),
                                             ("Note file", note["path"])]


_CSS = """
:root { color-scheme: light dark; --bg: #f6f5f1; --fg: #20282b; --muted: #536466;
  --card: #fff; --line: #d6dfdc; --accent: #176d5a; }
@media (prefers-color-scheme: dark) { :root { --bg: #152020; --fg: #e6efea;
  --muted: #acc1b7; --card: #1d2b2a; --line: #425853; --accent: #94d7b9; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 16px/1.6 system-ui, sans-serif; }
main { max-width: 1060px; margin: auto; padding: 40px 24px; }
.eyebrow { color: var(--accent); font-size: .8rem; font-weight: 700; letter-spacing: .13em; }
h1 { font-size: clamp(1.8rem, 4vw, 2.6rem); line-height: 1.2; margin: 18px 0; }
h2 { font-size: 1.1rem; margin: 0 0 14px; }
p { margin: 10px 0; }
.state { display: flex; flex-wrap: wrap; gap: 8px; margin: 20px 0; }
.state span { border: 1px solid var(--line); border-radius: 6px; padding: 4px 10px; }
.summary { font-size: 1.15rem; }
.muted { color: var(--muted); font-size: .9rem; }
section, details { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 22px; margin: 18px 0; }
section:first-of-type { border-left: 5px solid var(--accent); }
summary { cursor: pointer; font-weight: 650; }
summary:focus-visible { outline: 3px solid var(--accent); outline-offset: 5px; }
details[open] summary { margin-bottom: 18px; }
dl { margin: 0; display: grid; grid-template-columns: minmax(120px, 1fr) minmax(0, 4fr); gap: 10px 20px; }
dt { color: var(--muted); } dd { margin: 0; }
h1, p, dt, dd, span { overflow-wrap: anywhere; }
@media (max-width: 600px) { main { padding: 24px 14px; } section, details { padding: 16px; }
  dl { grid-template-columns: minmax(0, 1fr); gap: 4px; } dd { margin-bottom: 12px; } }
"""


def render(view, format):
    """Render literal text only. The snapshot carries no execution controls."""
    _check_size(view)
    if format not in ("markdown", "html"):
        raise ValueError("Task snapshot format must be markdown or html")
    goal = view["intent"]["goal"] or "Goal not supplied"
    overview = list(_overview(view))
    sections = list(_sections(view))
    if format == "markdown":
        lines = ["# Return to work", "", _literal(goal), "",
                 _literal("Snapshot captured " + view["captured_at"])]
        for title, rows in overview:
            lines.extend(["", "## " + title, ""])
            lines.extend(f"- **{_literal(label)}:** {_literal(value)}" for label, value in rows)
        lines.extend(["", "## Supporting detail", "", _literal(SNAPSHOT_NOTE)])
        for title, rows in sections:
            lines.extend(["", "### " + title, ""])
            lines.extend(f"- **{_literal(label)}:** {_literal(value)}" for label, value in rows)
        return "\n".join(lines) + "\n"
    def escape(value):
        return html.escape(_plain(value), quote=True)

    style_hash = base64.b64encode(hashlib.sha256(_CSS.encode()).digest()).decode()
    csp = f"default-src 'none'; style-src 'sha256-{style_hash}'; base-uri 'none'; form-action 'none'"
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f'<meta http-equiv="Content-Security-Policy" content="{html.escape(csp, quote=True)}">',
        f'<title>Return to work · Attune Harness</title><style>{_CSS}</style></head><body><main>',
        '<header><p class="eyebrow">ATTUNE HARNESS · Return to work</p>',
        f'<h1>{escape(goal)}</h1>',
        f'<p class="muted">Snapshot captured {escape(view["captured_at"])}</p></header>',
    ]
    for title, rows in overview:
        parts.append(f'<section><h2>{title}</h2><dl>')
        parts.extend(f'<dt>{escape(label)}</dt><dd>{escape(value)}</dd>' for label, value in rows)
        parts.append('</dl></section>')
    parts.append(f'<h2>Supporting detail</h2><p class="muted">{escape(SNAPSHOT_NOTE)}</p>')
    for title, rows in sections:
        parts.append(f'<details><summary>{title}</summary><dl>')
        parts.extend(f'<dt>{escape(label)}</dt><dd>{escape(value)}</dd>' for label, value in rows)
        parts.append('</dl></details>')
    return "\n".join([*parts, '</main></body></html>'])
