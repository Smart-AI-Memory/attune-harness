"""The legacy plan reader: Harness's own reading of an Attune AI plan file.

``plan_content`` excludes the single trailing Spec state comment and refuses a
misplaced or unsupported one (schema versions 1 and 2 only, as R4 requires);
``legacy_plan`` reads the ``<task>`` blocks, each parsed on its own, and
discloses everything it does not map. The reader consumes exactly the shape
``spec_tasks.DecomposedTask.to_dict`` produces, and ``spec_state`` accepts and
refuses the same state comments, which ``tests/test_spec_state.py`` pins.

The work-acceptance host that used to live beside the reader moved to
``work_accept`` in Task 4's first step (D20.1, D23); this module is renamed
``spec_legacy`` in the second. Nothing here imports Attune AI.
"""

import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .features import OVERSIZE, read_text
from .review_contract import parse_json
from .spec_tasks import parse_tasks


def plan_content(raw):
    """Exclude only the single trailing state comment owned by Spec persistence."""
    marker = "<!-- spec-state:"
    if marker not in raw:
        return raw.rstrip() + "\n"
    # No < or > in the payload: the writer escapes both, and the bound keeps
    # the pattern from spanning prose. spec_state.STATE_PATTERN is identical.
    match = re.search(r"\n?<!-- spec-state:\s*(\{[^<>]*\})\s*-->\s*\Z", raw, re.S)
    if raw.count(marker) != 1 or not match:
        raise ValueError("Malformed or misplaced Spec state comment")
    state = parse_json(match[1], 65536)
    if (
        not isinstance(state, dict)
        or type(state.get("schema_version")) is not int
        or state["schema_version"] not in (1, 2)
    ):
        raise ValueError("Unsupported Spec state comment")
    return raw[: match.start()].rstrip() + "\n"


def legacy_plan(path):
    """Read a plan with Harness's own reader; retain its fields and disclose everything ignored."""
    # Read first, so an oversize plan gets the plan's own message before parsing.
    try:
        raw = read_text(Path(path), 65536)
    except ValueError as error:
        if not str(error).startswith(OVERSIZE):
            raise
        raise ValueError(
            f"{error} Split the plan into smaller plan files and import each one as its own task."
        ) from error

    content = plan_content(raw)
    blocks = re.findall(r"<task\b[^>]*>.*?</task>", content, re.S)
    if not blocks or len(blocks) != len(re.findall(r"<task\b", content)):
        raise ValueError("Legacy plan must contain complete nonempty task blocks")
    try:
        nodes = [ET.fromstring(block) for block in blocks]
    except ET.ParseError as error:
        raise ValueError(
            f"Legacy plan has a task block that is not well-formed XML ({error}). "
            "Fix that block, or split the plan and import the other tasks."
        ) from error
    # The blocks were read once, above, and each has just parsed on its own, so
    # the reader sees exactly them: no second read, and nothing outside a block
    # (prose, a state comment) can change how a task is read.
    parsed = [task.to_dict() for task in parse_tasks("".join(blocks))]
    if len(parsed) != len(nodes):
        raise ValueError("Legacy parser omitted a malformed task")
    known = {
        "objective",
        "files-to-create",
        "files-to-modify",
        "validation",
        "risks",
        "dependencies",
    }
    unsupported = []
    for node in nodes:
        for child in node:
            if child.tag not in known:
                unsupported.append(ET.tostring(child, encoding="unicode"))
        if set(node.attrib) - {"id", "name"}:
            unsupported.append("Unsupported task attributes: " + repr(node.attrib))
        nested = {
            "files-to-create": ("file", {"path"}),
            "files-to-modify": ("file", {"path"}),
            "validation": ("check", set()),
            "risks": ("risk", {"severity"}),
            "dependencies": ("dep", set()),
        }
        for group in node:
            if group.tag in nested:
                tag, attrs = nested[group.tag]
                for child in group:
                    if child.tag != tag or set(child.attrib) - attrs or list(child):
                        unsupported.append(
                            "Unmapped nested content: "
                            + ET.tostring(child, encoding="unicode")
                        )
    # Prose and ignored XML remain in the captured artifact, never silently lost.
    remainder = content
    for block in blocks:
        remainder = remainder.replace(block, "", 1)
    remainder = remainder.replace("<tasks>", "").replace("</tasks>", "").strip()
    if remainder:
        unsupported.append("Unmapped surrounding content: " + remainder)
    return {
        "path": str(Path(path).resolve()),
        "source_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
        "content": content,
        "tasks": parsed,
        "unsupported": unsupported,
        "approval_imported": False,
    }
