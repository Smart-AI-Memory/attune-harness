"""Human-readable task presentation for spec-driven development.

Formats tasks from plan files into markdown tables,
detail views, and progress indicators for the ``/spec``
command's review and execute stages.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import html
import re
import unicodedata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .spec_state import SpecState
    from .spec_tasks import DecomposedTask


def _plain(value: str) -> str:
    text = ''.join(' ' if ch.isspace() else ch for ch in str(value)
                   if ch.isspace() or unicodedata.category(ch) not in {'Cc', 'Cf', 'Cs'})
    return ' '.join(text.split())


def _literal(value: str) -> str:
    """Render repository text as one literal line, never terminal/Markdown syntax."""
    text = html.escape(_plain(value), quote=False)
    return re.sub(r'([\\`*_{}\[\]()#+.!|~=$-])', r'\\\1', text)


def present_tasks(
    tasks: list[DecomposedTask],
    state: SpecState | None = None,
) -> str:
    """Format all tasks as a human-readable markdown table.

    Args:
        tasks: List of DecomposedTask from read_spec().
        state: Optional execution state for status markers.

    Returns:
        Markdown table with Status, ID, Name, and Objective.

    """
    completed = set(state.completed) if state else set()
    current = state.current if state else None

    lines = [
        "| Status | ID | Name | Objective |",
        "|--------|----|------|-----------|",
    ]

    for task in tasks:
        if task.task_id in completed:
            status = "done"
        elif task.task_id == current:
            status = ">>>"
        else:
            status = "..."
        objective = _plain(task.objective)
        objective = objective[:60] + ("..." if len(objective) > 60 else "")
        lines.append(f"| {status} | {_literal(task.task_id)} | {_literal(task.name)} | {_literal(objective)} |")

    return "\n".join(lines)


def present_task_detail(task: DecomposedTask) -> str:
    """Format a single task with full details.

    Args:
        task: DecomposedTask to display.

    Returns:
        Markdown-formatted detail view.

    """
    lines = [
        f"### Task {_literal(task.task_id)}: {_literal(task.name)}",
        "",
        f"**Objective:** {_literal(task.objective)}",
    ]

    if task.files_to_create:
        lines.append("")
        lines.append("**Files to create:**")
        for f in task.files_to_create:
            lines.append(f"- {_literal(f.get('path', 'unknown'))} — {_literal(f.get('description', ''))}")

    if task.files_to_modify:
        lines.append("")
        lines.append("**Files to modify:**")
        for f in task.files_to_modify:
            lines.append(f"- {_literal(f.get('path', 'unknown'))} — {_literal(f.get('description', ''))}")

    if task.validation_checks:
        lines.append("")
        lines.append("**Validation:**")
        for check in task.validation_checks:
            lines.append(f"- {_literal(check)}")

    if task.risks:
        lines.append("")
        lines.append("**Risks:**")
        for risk in task.risks:
            severity = risk.get("severity", "unknown")
            desc = risk.get("description", "")
            lines.append(f"- \\[{_literal(severity)}\\] {_literal(desc)}")

    if task.dependencies:
        lines.append("")
        lines.append(f"**Depends on:** {', '.join(_literal(item) for item in task.dependencies)}")

    return "\n".join(lines)


def present_task_result(task: DecomposedTask, evidence: dict) -> str:
    """Render a checked Harness test binding, never a legacy model quality score."""
    from .spec_handoff import check_test_evidence
    check_test_evidence(evidence)
    return (f"### Result: Task {_literal(task.task_id)} — {_literal(task.name)}\n\n"
            f"Tests: **{_literal(evidence['outcome'].upper())}**\n"
            f"Evidence: {_literal(evidence['record_path'])}\n"
            "Model quality review: not performed by this receipt")


def format_progress_bar(completed: int, total: int) -> str:
    """Visual progress indicator for task execution.

    Args:
        completed: Number of completed tasks.
        total: Total number of tasks.

    Returns:
        Progress bar string like ``[####....] 4/8 tasks``.

    """
    if total <= 0:
        return "[........] 0/0 tasks"

    filled = int(8 * completed / total)
    empty = 8 - filled
    return f"[{'#' * filled}{'.' * empty}] {completed}/{total} tasks"
