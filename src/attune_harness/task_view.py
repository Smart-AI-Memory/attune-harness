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


# Fixed assets contain no task text. CSP hashes bind exactly these bytes.
_CSS = """
:root{color-scheme:light dark;--bg:#f7f6f2;--paper:#fffefb;--ink:#253332;
--muted:#586865;--line:#d6ddd8;--accent:#246656;--wash:#edf3ee}
@media(prefers-color-scheme:dark){:root{--bg:#17201f;--paper:#202b29;--ink:#eef3ef;
--muted:#b0bfb7;--line:#485650;--accent:#a7d6bd;--wash:#263a32}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.5 system-ui,sans-serif}
main{max-width:1060px;margin:auto;padding:32px 24px}h1{font-size:32px;line-height:1.2;margin:12px 0}
h2{font-size:21px;margin:0 0 10px}p{margin:8px 0}a{color:var(--accent);text-underline-offset:3px}
header{margin:20px 0}.eyebrow,.label{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:700}
.muted{font-size:13px;color:var(--muted)}.brief{background:var(--paper);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.brief>section,.destination{padding:22px 26px;border-bottom:1px solid var(--line)}.brief>section:last-child{border:0}
.destination{display:grid;grid-template-columns:1fr 1.2fr;gap:26px}.goal{font-size:24px;line-height:1.35;font-weight:600}.focus{background:var(--wash)}
details{border-top:1px solid var(--line);padding:16px 0}summary{font-weight:600;cursor:pointer}details[open] summary{margin-bottom:14px}
dl{display:grid;grid-template-columns:160px minmax(0,1fr);gap:10px 16px}dt{color:var(--muted)}dd{margin:0}
button,textarea{font:inherit}button{padding:10px 14px;min-height:44px;border:1px solid var(--line);border-radius:7px;background:var(--paper);color:var(--ink);cursor:pointer}
button[aria-pressed=true]{border:2px solid var(--accent);background:var(--wash)}button:disabled{opacity:.5;cursor:default}
textarea{width:100%;display:block;resize:vertical;min-height:100px;background:var(--paper);color:var(--ink);border:1px solid var(--line);border-radius:7px;padding:10px;font-size:15px}
textarea[readonly]{background:var(--wash);min-height:150px}.controls{display:flex;flex-wrap:wrap;gap:10px;margin:16px 0}label{display:block;font-size:14px;font-weight:600;margin:14px 0 8px}
:focus-visible{outline:3px solid var(--accent);outline-offset:3px}h1,h2,p,dt,dd,li{overflow-wrap:anywhere}
.task-card{border-top:1px solid var(--line);padding:24px 0}.task-card a{display:inline-block;padding:10px 0;min-height:44px}
.saved-task{display:none}.saved-task:target{display:block}.saved-task:target~#saved-tasks{display:none}
@media(max-width:650px){main{padding:22px 16px}.destination{grid-template-columns:1fr}.brief>section,.destination{padding:18px}dl{grid-template-columns:1fr;gap:3px}dd{margin-bottom:10px}.controls button{flex:1 1 100%}}
@media print{.saved-task{display:block}.controls{display:none}}
"""
_REPLY_SCRIPT = """
'use strict';
document.querySelectorAll('[data-reply]').forEach(panel => {
 const reply=panel.querySelector('[data-text]'), notes=panel.querySelector('[data-notes]');
 const status=panel.querySelector('[role=status]'), copy=panel.querySelector('[data-copy]');
 const original=reply.value;
 const requests={continue:'Please help me follow the current next-action guidance within existing authorization.',
 correct:'Please review my correction to the context before continuing; do not treat it as a change to accepted scope.',
 question:'Please answer my question before continuing.'};
 let selected='continue'; const drafts={continue:'',correct:'',question:''};
 function update(){drafts[selected]=notes.value;reply.value=original+'\\n\\n'+requests[selected]+(notes.value.trim()?'\\n\\n'+notes.value:'');
  copy.disabled=selected==='question'&&!notes.value.trim();
  status.textContent=copy.disabled?'Write your question above.':'';}
 panel.querySelectorAll('[data-choice]').forEach(button=>button.addEventListener('click',()=>{
  selected=button.dataset.choice;
  panel.querySelectorAll('[data-choice]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
  notes.value=drafts[selected];notes.required=selected==='question';update();
 }));
 notes.addEventListener('input',update);
 copy.addEventListener('click',async()=>{try{
  if(!navigator.clipboard?.writeText)throw new Error('Clipboard unavailable');
  await navigator.clipboard.writeText(reply.value);status.textContent='Copied. Paste into your conversation to send your reply.';
 }catch{reply.focus();reply.select();status.textContent='Copy the selected reply with Command+C or Ctrl+C, then paste into your conversation.';}});
 update();
});
"""


def _escape(value):
    return html.escape(_plain(value), quote=True)


def _handoff(view):
    return (f'Help me continue the saved task at {Path(view["record_path"]).parent}. '
            f'Task ID: {view["task_id"]}. The snapshot showed revision {view["revision"]}. '
            'Inspect its current status before acting, then follow its next-action guidance '
            'within existing authorization. This reply is not a checkpoint acceptance.')


def _briefing(view):
    """Authored summaries are attributed; their text never replaces owner guidance."""
    intent, note = view["intent"], view["continuation"]
    supplied = note.get("briefing") if note and note["current_revision"] else None
    pending = [t for t in view["tasks"] if t["id"] not in view["completed"] or "freshness_error" in view]
    focus = pending[0] if pending else None
    brief = supplied or {
        "title": intent["goal"] or "Untitled task",
        "context": "\n".join(intent["context"][:2]) or "No saved context was supplied.",
        "goal": intent["goal"] or "Goal not supplied",
        "desired_end_state": "\n".join(intent["acceptance"][:2]) or "Success criteria not supplied.",
        "current_focus": focus["objective"] if focus else "No remaining planned step is established by this snapshot.",
        "done_when": "\n".join(focus["checks"][:2]) if focus and focus["checks"] else "Inspect the full plan and checks below.",
    }
    attribution = (f'Briefing supplied by {note["source"]} at {note["recorded_at"]}. '
                   'This is an attributed summary, not verified progress or task authority.' if supplied else
                   'Briefing drawn from saved intent and planned checks; full wording is below.')
    position = (note["stopped_after"] if note and note["current_revision"] else
                "No current stopping point was supplied. " + view["summary"])
    return brief, attribution, position


def _document(body, *, title="Return to work"):
    digest = lambda text: base64.b64encode(hashlib.sha256(text.encode()).digest()).decode()
    csp = (f"default-src 'none'; style-src 'sha256-{digest(_CSS)}'; "
           f"script-src 'sha256-{digest(_REPLY_SCRIPT)}'; connect-src 'none'; base-uri 'none'; form-action 'none'")
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta http-equiv="Content-Security-Policy" content="{_escape(csp)}">'
            f'<title>{_escape(title)} · Attune Harness</title><style>{_CSS}</style></head>'
            f'<body><main>{body}</main><script>{_REPLY_SCRIPT}</script></body></html>')


def _reply(view, key):
    return (f'<div data-reply><p class="muted">Prepare a reply, then paste it into your conversation. '
            'Nothing is sent or accepted here. Drafts clear when you reload.</p><div class="controls">'
            '<button type="button" data-choice="continue" aria-pressed="true">Continue with guidance</button>'
            '<button type="button" data-choice="correct" aria-pressed="false">Correct context</button>'
            '<button type="button" data-choice="question" aria-pressed="false">Ask a question</button></div>'
            f'<label for="notes-{key}">Your words (required for a question)</label>'
            f'<textarea id="notes-{key}" data-notes maxlength="2000"></textarea>'
            f'<label for="reply-{key}">Your reply to the assistant</label>'
            f'<textarea id="reply-{key}" data-text readonly>{_escape(_handoff(view))}</textarea>'
            '<div class="controls"><button type="button" data-copy>Copy reply</button>'
            '<span class="muted" role="status" aria-live="polite"></span></div>'
            '<noscript><p>Select and copy the reply above. Interactive choices require JavaScript.</p></noscript></div>')


def _rows(rows):
    return '<dl>' + ''.join(f'<dt>{_escape(k)}</dt><dd>{_escape(v)}</dd>' for k, v in rows) + '</dl>'


def _body(view, key):
    brief, attribution, position = _briefing(view)
    parts = ['<header><p class="eyebrow">Attune Harness · Task briefing</p><h1>Return to work</h1>',
             f'<p>{_escape(brief["title"])}</p><p class="muted">Snapshot captured {_escape(view["captured_at"])}</p></header>',
             f'<p class="muted">{_escape(attribution)}</p><article class="brief">',
             '<section><h2 class="label">Context · why we’re here</h2>', f'<p>{_escape(brief["context"])}</p></section>',
             '<div class="destination"><section><h2 class="label">Overall goal</h2>',
             f'<p class="goal">{_escape(brief["goal"])}</p></section><section><h2 class="label">Desired end state</h2>',
             f'<p>{_escape(brief["desired_end_state"])}</p></section></div>',
             '<section class="focus"><h2 class="label">This iteration · current focus</h2>',
             f'<p>{_escape(brief["current_focus"])}</p><p><strong>Done when:</strong> {_escape(brief["done_when"])}</p></section>',
             '<section><h2 class="label">Where we are now</h2>',
             f'<p>{_escape(position)}</p><p class="muted">{_escape(view["summary"])}</p></section>',
             '<section><p class="label">Next action</p><h2>Next useful step</h2>',
             f'<p>{_escape(view["next_action"])}</p>', _reply(view, key), '</section></article>']
    for title, rows in _overview(view):
        if title != "Next useful step":
            parts.append(f'<details><summary>{title}</summary>{_rows(rows)}</details>')
    parts.append(f'<h2>Supporting detail</h2><p class="muted">{_escape(SNAPSHOT_NOTE)}</p>')
    parts.append('<details><summary>Full saved goal</summary>' + _rows([("Goal", view["intent"]["goal"])]) + '</details>')
    for title, rows in _sections(view):
        parts.append(f'<details><summary>{title}</summary>{_rows(rows)}</details>')
    return '\n'.join(parts)


def render(view, format):
    """Render a snapshot. Local response preparation never dispatches or writes."""
    _check_size(view)
    if format not in ("markdown", "html"):
        raise ValueError("Task snapshot format must be markdown or html")
    if format == "html":
        return _document(_body(view, "task"))
    brief, attribution, position = _briefing(view)
    lines = ["# Return to work", "", _literal(brief["title"]), "",
             _literal("Snapshot captured " + view["captured_at"]), "", _literal(attribution)]
    for title, content in (("Context", brief["context"]), ("Overall goal", brief["goal"]),
                           ("Desired end state", brief["desired_end_state"]),
                           ("Current focus", brief["current_focus"]), ("Done when", brief["done_when"]),
                           ("Where we are now", position)):
        lines.extend(["", "## " + title, "", _literal(content)])
    for title, rows in _overview(view):
        lines.extend(["", "## " + title, ""])
        lines.extend(f"- **{_literal(label)}:** {_literal(value)}" for label, value in rows)
    lines.extend(["", "## Your reply to the assistant", "", _literal(_handoff(view)),
                  "", "## Supporting detail", "", _literal(SNAPSHOT_NOTE), "", "### Full saved goal", "", _literal(view["intent"]["goal"])])
    for title, rows in _sections(view):
        lines.extend(["", "### " + title, ""])
        lines.extend(f"- **{_literal(label)}:** {_literal(value)}" for label, value in rows)
    return "\n".join(lines) + "\n"


MAX_SAVED_TASKS = 20
MAX_SAVED_TASK_BYTES = 2 * 1024 * 1024


def inspect_saved_tasks(directory, additional, *, continuation=None):
    """Explicit directories only; no task discovery or side effects."""
    paths = [Path(directory), *map(Path, additional)]
    if len(paths) > MAX_SAVED_TASKS:
        raise ValueError("Saved Tasks supports at most 20 explicitly supplied directories")
    if len({path.resolve() for path in paths}) != len(paths):
        raise ValueError("Saved Tasks directories must be distinct")
    entries, identities = [], set()
    for index, path in enumerate(paths):
        try:
            view = inspect(path, continuation=continuation if index == 0 else None)
            if view["task_id"] in identities:
                raise ValueError("Duplicate saved task identity; choose one authoritative directory")
            identities.add(view["task_id"])
            entries.append({"directory": str(path.resolve()), "view": view})
        except Exception as exc:
            if index == 0:
                raise
            entries.append({"directory": str(path.resolve()), "error": str(exc)})
    if len(json.dumps(entries, ensure_ascii=False).encode()) > MAX_SAVED_TASK_BYTES:
        raise ValueError("Saved Tasks exceeds the 2 MiB collection limit")
    return entries


def render_saved_tasks(entries, format):
    """A single-file entrance retains stable local anchors and no external links."""
    if format not in ("html", "markdown"):
        raise ValueError("Saved Tasks format must be markdown or html")
    if format == "markdown":
        return "# Saved Tasks\n\n" + SNAPSHOT_NOTE + "\n\n" + "\n\n".join(
            render(entry["view"], "markdown") if "view" in entry else
            "## Unavailable task\n\n" + _literal(entry["directory"]) + "\n\n" + _literal(entry["error"])
            for entry in entries)
    bodies, cards = [], []
    for entry in entries:
        if "view" not in entry:
            cards.append('<section class="task-card"><h2>Unavailable task</h2>' +
                         f'<p>{_escape(entry["directory"])}</p><p>{_escape(entry["error"])}</p></section>')
            continue
        view = entry["view"]
        key = "task-" + hashlib.sha256(view["task_id"].encode()).hexdigest()[:24]
        brief, _, position = _briefing(view)
        cards.append(f'<section class="task-card"><h2>{_escape(brief["title"])}</h2>'
                     f'<p>{_escape(brief["goal"])}</p><p><strong>Where you left off:</strong> {_escape(position)}</p>'
                     f'<p class="muted">{_escape(view["summary"])} · Revision {_escape(view["revision"])}</p>'
                     f'<a href="#{key}">Open briefing →</a></section>')
        bodies.append(f'<div class="saved-task" id="{key}"><nav><a href="#saved-tasks">← Saved tasks</a></nav>' +
                      _body(view, key) + '</div>')
    home = ('<div id="saved-tasks"><header><p class="eyebrow">Attune Harness</p><h1>Saved Tasks</h1>'
            '<p>Choose the work you want to pick up.</p>' + f'<p class="muted">{_escape(SNAPSHOT_NOTE)}</p>'
            '<p class="muted">Only explicitly supplied task directories are shown. No background discovery.</p></header>' +
            ''.join(cards) + '</div>')
    return _document('\n'.join(bodies) + home, title="Saved Tasks")
