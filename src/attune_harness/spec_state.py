"""Read and write the execution state a plan file carries.

Carried from Attune AI (branch ``codex/shared-memory-adoption`` at
``b89f7953f``): ``attune/spec/state.py``. The state is one HTML comment at
the end of the plan file, invisible in rendered Markdown and never parsed as a
``<task>`` block::

    <!-- spec-state: {"schema_version": 2, "completed": ["1"], ...} -->

Three seams are reworked here, from Task 1's verdict on the module:

- A ``schema_version`` this Harness does not know is refused, never loaded.
  R4, read as covering versions 1 and 2 (D13), forbids replacing a refusal
  with a guess. The original loaded any version and stored the number.
- The plans directory is an argument. The original defaulted to the relative
  path ``.claude/plans``, which depends on the working directory.
- The comment is the single trailing comment of the file. That is what
  ``spec_bridge.plan_content`` accepts, so one module never writes what the
  other refuses. The original replaced a comment wherever it found it.
  ``save_state`` also refuses to write a plan the reader would refuse for
  size. ``clear_state`` removes every state comment wherever it is, because
  removing the comment is the next action this module names for a misplaced
  or unsupported one.
- ``find_resumable_plans`` returns plans in file name order; the original
  returned them in directory order.

The payload pattern admits no ``<`` or ``>``: the writer escapes both, so a
real comment never contains them, and the bound keeps the pattern from
spanning prose between a stray marker and a later ``} -->``. The two modules
share the pattern and the JSON parser, so they refuse the same files.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .features import REPLACE_RETRY_SECONDS, read_text, replace_file
from .review_contract import parse_json
from .paths import validate_file_path
from .spec_tasks import PLAN_LIMIT, read_spec

logger = logging.getLogger(__name__)

STATE_MARKER = "<!-- spec-state:"
# The one place a state comment may live: last in the file, at most one.
# The same expression `spec_bridge.plan_content` uses.
STATE_PATTERN = re.compile(r"\n?<!-- spec-state:\s*(\{[^<>]*\})\s*-->\s*\Z", re.S)
# Any state comment, anywhere. Only `clear_state` uses it, to repair a file.
_ANY_STATE = re.compile(r"<!-- spec-state:\s*\{[^<>]*\}\s*-->")

SUPPORTED_SCHEMA_VERSIONS = (1, 2)
CURRENT_SCHEMA_VERSION = 2


@dataclass
class SpecState:
    """Execution state for a plan.

    ``plan_path`` is the file the state was read from or will be written to.
    ``completed`` holds the ids of accepted tasks, ``current`` the id being
    executed, ``task_receipts`` the accepted execution results (absent in
    older plans), ``auto_run`` whether remaining tasks skip approval,
    ``last_updated`` the ISO UTC time of the last change, and
    ``schema_version`` the on-disk format version: the current one for a new
    state, or the version a loaded payload carried.
    """

    plan_path: str
    completed: list[str] = field(default_factory=list)
    current: str | None = None
    auto_run: bool = False
    last_updated: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    schema_version: int = CURRENT_SCHEMA_VERSION
    task_receipts: list[dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """JSON-safe form, without ``plan_path``."""
        return {
            "schema_version": self.schema_version,
            "completed": self.completed,
            "task_receipts": self.task_receipts,
            "current": self.current,
            "auto_run": self.auto_run,
            "last_updated": self.last_updated,
        }


def _split(content: str, plan_path: str) -> tuple[str, str | None]:
    """The plan body and the JSON text of its state comment, if it has one.

    Raises ``ValueError`` when the comment is not the single trailing one:
    that is the case ``spec_bridge.plan_content`` refuses, and this module
    refuses it the same way rather than reading or rewriting it.
    """
    if STATE_MARKER not in content:
        return content, None
    # The count comes first: it is cheap, and a file with several markers
    # never needs the search.
    match = STATE_PATTERN.search(content) if content.count(STATE_MARKER) == 1 else None
    if match is None:
        raise ValueError(
            f"Malformed or misplaced Spec state comment in {plan_path}: the state "
            "comment must be the only one and the last thing in the file. Remove "
            "every spec-state comment to start the plan over, or keep one comment "
            "and move it to the end of the file."
        )
    return content[: match.start()], match.group(1)


def _check_schema_version(data: dict, plan_path: str) -> int:
    version = data.get("schema_version")
    if type(version) is int and version in SUPPORTED_SCHEMA_VERSIONS:
        return version
    found = "none" if "schema_version" not in data else json.dumps(version)
    supported = " and ".join(str(v) for v in SUPPORTED_SCHEMA_VERSIONS)
    if type(version) is int and version > max(SUPPORTED_SCHEMA_VERSIONS):
        raise ValueError(
            f"Unsupported Spec state comment in {plan_path}: schema_version "
            f"{version} is newer than this Harness reads ({supported}). Update "
            "Harness, or keep working on the plan with the version that wrote it."
        )
    raise ValueError(
        f"Unsupported Spec state comment in {plan_path}: schema_version {found} is "
        f"not one this Harness reads ({supported}). Remove the spec-state comment "
        f'to start the plan over, or set "schema_version": {CURRENT_SCHEMA_VERSION} '
        "if the recorded state is trusted."
    )


def load_state(plan_path: str) -> SpecState | None:
    """Read the state comment from a plan file.

    Returns ``None`` when the file does not exist, cannot be read, or has no
    state comment, and, with a warning, when the comment's JSON is malformed
    (including a duplicate key or a non-finite number, which the bridge's
    parser refuses too) or a field has the wrong type: callers can observe
    the failure even though the contract is ``None``.

    Raises ``ValueError`` when the path fails validation, the file is over
    the plan size limit, the comment is not the single trailing one, its
    ``schema_version`` is not one this Harness reads, or its receipts are
    invalid. None of those may silently reset progress.
    """
    validated = validate_file_path(plan_path)
    if not validated.is_file():
        logger.debug("No plan file at %s", plan_path)
        return None
    try:
        content = read_text(validated, PLAN_LIMIT)
    except OSError as e:
        logger.debug("Could not read plan file %s: %s", plan_path, e)
        return None

    _, payload = _split(content, plan_path)
    if payload is None:
        return None

    try:
        data = parse_json(payload, PLAN_LIMIT)
    except ValueError as e:
        logger.warning("Malformed spec-state in %s: %s", plan_path, e)
        return None

    if not isinstance(data, dict):
        logger.warning(
            "spec-state in %s is not a JSON object (got %s)",
            plan_path,
            type(data).__name__,
        )
        return None

    schema_version = _check_schema_version(data, plan_path)

    completed_raw = data.get("completed", [])
    if not isinstance(completed_raw, list) or not all(
        isinstance(item, str) for item in completed_raw
    ):
        logger.warning(
            "spec-state 'completed' in %s is not list[str]; ignoring",
            plan_path,
        )
        return None

    current_raw = data.get("current")
    if current_raw is not None and not isinstance(current_raw, str):
        logger.warning(
            "spec-state 'current' in %s is not str|None; ignoring",
            plan_path,
        )
        return None

    receipts_raw = data.get("task_receipts", [])
    if not isinstance(receipts_raw, list) or not all(
        isinstance(item, dict) for item in receipts_raw
    ):
        raise ValueError(f"Invalid spec-state task_receipts in {plan_path}")

    return SpecState(
        plan_path=plan_path,
        completed=list(completed_raw),
        task_receipts=receipts_raw,
        current=current_raw,
        auto_run=bool(data.get("auto_run", False)),
        last_updated=str(data.get("last_updated", "")),
        schema_version=schema_version,
    )


def save_state(state: SpecState) -> None:
    """Write the state comment as the last thing in the plan file.

    An existing trailing comment is replaced; a file without one gets one
    appended, using the file's own line ending. The write goes through a
    sibling temporary file and ``features.replace_file``, which on Windows
    retries for up to ``REPLACE_RETRY_SECONDS`` while a reader holds the plan
    open, so a reader never sees a
    half-written plan and a crash mid-write leaves the plan as it was. After
    a successful write ``state.last_updated`` and ``state.schema_version``
    are set to what was written; a refused save leaves the object unchanged.

    Raises ``ValueError`` when the path fails validation, the file is not a
    regular file or is over the plan size limit, an existing comment is not
    the single trailing one, or the result would be over the limit; nothing
    is written in any of those cases. Raises ``OSError`` if the write fails.
    """
    validated = validate_file_path(state.plan_path)
    content = read_text(validated, PLAN_LIMIT)
    body, _ = _split(content, state.plan_path)

    written = {
        **state.to_dict(),
        "schema_version": CURRENT_SCHEMA_VERSION,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    # Evidence may contain comment delimiters. Keep it inside the JSON comment.
    payload = json.dumps(written).replace("<", "\\u003c").replace(">", "\\u003e")
    comment = f"<!-- spec-state: {payload} -->"
    newline = "\r\n" if "\r\n" in body else "\n"
    result = body.rstrip() + f"{newline}{newline}{comment}{newline}"

    size = len(result.encode("utf-8"))
    if size > PLAN_LIMIT:
        raise ValueError(
            f"Plan {state.plan_path} with its state would be {size} bytes, over the "
            f"limit of {PLAN_LIMIT} bytes; nothing was written. Harness never "
            "shortens an input to fit. Trim the task receipts, or split the plan "
            "into smaller plan files."
        )
    _atomic_write_text(validated, result)
    state.last_updated = written["last_updated"]
    state.schema_version = CURRENT_SCHEMA_VERSION


def clear_state(plan_path: str) -> None:
    """Remove every state comment from a plan file, wherever it is.

    This is the repair for a misplaced or unsupported comment, so unlike the
    reader it does not refuse one. Does nothing when there is none.

    Raises ``ValueError`` when the path fails validation or the file is not a
    regular file or is over the plan size limit, and ``OSError`` if the write
    fails.
    """
    validated = validate_file_path(plan_path)
    content = read_text(validated, PLAN_LIMIT)

    if not _ANY_STATE.search(content):
        return

    newline = "\r\n" if "\r\n" in content else "\n"
    content = _ANY_STATE.sub("", content).rstrip() + newline
    _atomic_write_text(validated, content)


def find_resumable_plans(plans_dir: str) -> list[SpecState]:
    """The plans in a directory whose state has fewer completed tasks than tasks.

    ``plans_dir`` is required: there is no default directory. It is validated
    like any path; a path that does not exist or is not a directory gives an
    empty list. A plan whose state or tasks cannot be read is skipped with a
    warning and does not stop the scan, so one corrupt plan never hides the
    others. Results are in file name order.

    Raises ``ValueError`` only when ``plans_dir`` fails path validation.
    """
    plans_path = validate_file_path(plans_dir)
    if not plans_path.is_dir():
        return []

    resumable: list[SpecState] = []
    for md_file in sorted(plans_path.glob("*.md")):
        try:
            state = load_state(str(md_file))
            if state is None:
                continue
            tasks = read_spec(str(md_file))
        except (FileNotFoundError, ValueError) as e:
            logger.warning("skipping resumable-plan candidate %s: %s", md_file, e)
            continue

        if not tasks:
            continue

        task_ids = {t.task_id for t in tasks}
        if set(state.completed) < task_ids:
            resumable.append(state)

    return resumable


def _atomic_write_text(target: Path, content: str) -> None:
    """Write ``content`` to ``target`` through a sibling temporary file.

    ``tempfile.mkstemp`` in the same directory, then ``features.replace_file``,
    the one atomic replace, which retries for a bounded time on Windows while a
    reader holds the plan open (O-59), so a concurrent reader never sees a
    partial file and a reader does not fail the writer. Line endings are written as
    given, never translated, so a CRLF plan stays CRLF on every platform. On failure the temporary
    file is removed on a best-effort basis and the original error is raised;
    a failed removal is logged at debug level so it stays observable.
    """
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        replace_file(Path(tmp_name), target, retry_seconds=REPLACE_RETRY_SECONDS)
    except OSError:
        try:
            os.unlink(tmp_name)
        except OSError as cleanup_err:
            logger.debug(
                "Failed to unlink temp file %s after write error: %s",
                tmp_name,
                cleanup_err,
            )
        raise
