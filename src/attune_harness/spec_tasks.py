"""Read the ``<task>`` blocks a plan file is written in.

Carried from Attune AI (branch ``codex/shared-memory-adoption`` at
``b89f7953f``): ``DecomposedTask`` and the parser from
``attune/wizards/decomposer.py``, and ``read_spec`` from
``attune/pipeline/spec_reader.py``. The parser there was a method of the class
that decomposes work for Attune AI's wizards, reached by building that class
with no workflow; here it is a function. It uses the standard library parser in
place of ``defusedxml``. What makes that safe is the ``<r>`` wrapper: an entity
declaration is only legal before a document's root element, and the wrapper
puts the root before anything from the file, so a declaration can never take
effect; a ``DOCTYPE`` anywhere is a parse error and drops to the regex path,
which expands nothing. The hostile cases in the tests pin that. The region cut
is what lets prose and Markdown fences sit around the blocks.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

from .features import read_text
from .paths import validate_file_path

logger = logging.getLogger(__name__)

PLAN_LIMIT = 65536


@dataclass
class DecomposedTask:
    """One task from a plan: what it does, which files, how it is checked."""

    task_id: str
    name: str
    objective: str
    files_to_create: list[dict[str, str]] = field(default_factory=list)
    files_to_modify: list[dict[str, str]] = field(default_factory=list)
    validation_checks: list[str] = field(default_factory=list)
    risks: list[dict[str, str]] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe form; ``spec_bridge.legacy_plan`` consumes exactly this shape."""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "objective": self.objective,
            "files_to_create": self.files_to_create,
            "files_to_modify": self.files_to_modify,
            "validation_checks": self.validation_checks,
            "risks": self.risks,
            "dependencies": self.dependencies,
        }

    def to_xml(self) -> str:
        """Render this task in the plan schema."""
        parts = [f'<task id="{self.task_id}" name="{self.name}">']
        parts.append(f"  <objective>{self.objective}</objective>")
        for section, files in (
            ("files-to-create", self.files_to_create),
            ("files-to-modify", self.files_to_modify),
        ):
            if files:
                parts.append(f"  <{section}>")
                for f in files:
                    parts.append(f'    <file path="{f["path"]}">{f.get("description", "")}</file>')
                parts.append(f"  </{section}>")
        if self.validation_checks:
            parts.append("  <validation>")
            parts.extend(f"    <check>{check}</check>" for check in self.validation_checks)
            parts.append("  </validation>")
        if self.risks:
            parts.append("  <risks>")
            for risk in self.risks:
                severity = risk.get("severity", "medium")
                parts.append(
                    f'    <risk severity="{severity}">{risk.get("description", "")}</risk>'
                )
            parts.append("  </risks>")
        if self.dependencies:
            parts.append("  <dependencies>")
            parts.extend(f"    <dep>{dep}</dep>" for dep in self.dependencies)
            parts.append("  </dependencies>")
        parts.append("</task>")
        return "\n".join(parts)


# The span from the first <task to the last </task>. Only this is parsed, so
# prose, Markdown fences and anything else around the blocks never have to be
# well-formed, and a DOCTYPE before the first <task> is never seen.
_TASK_REGION = re.compile(r"<task[\s>].*</task\s*>", re.DOTALL)
_TASK_BLOCK = re.compile(r'<task\s+id="([^"]*)"(?:\s+name="([^"]*)")?\s*>(.*?)</task>', re.DOTALL)
# Opening tags that only appear inside a <task> body. One found between blocks
# means a task lost its wrapper and was dropped.
_ORPHAN_TAG = re.compile(r"<(objective|file|check|risk|dep)[\s>]")
# The edges of task blocks, for splitting a region into its top-level blocks.
_TASK_EDGE = re.compile(r"<task[\s>]|</task\s*>")


def parse_tasks(content: str) -> list[DecomposedTask]:
    """Parse the ``<task>`` elements in a plan file or a model's reply.

    Well-formed XML goes through the parser, so quoting style, attribute
    order and whitespace cannot drop a task. Each top-level block is parsed
    on its own, so prose between blocks is never parsed at all. A block the
    parser rejects, an unclosed tag or a ``<`` in a description, falls back
    to the regex path for that block, which warns about what it cannot see;
    a plan whose task tags do not balance falls back as a whole.
    """
    region = _TASK_REGION.search(content)
    if region is None:
        return _parse_with_regex(content)
    blocks = _top_level_blocks(region.group(0))
    if blocks is None:
        # A missing or stray </task>: parse the region as one document, as
        # before, so the fallback and its warnings describe the whole plan.
        return _parse_xml(region.group(0), content)
    # Each block on its own, so prose between blocks (a bare & or < in a
    # note between two tasks) cannot change how any task is read, and a block
    # the parser rejects drops to the regex path alone.
    tasks: list[DecomposedTask] = []
    for block in blocks:
        tasks.extend(_parse_xml(block, block))
    return tasks


def _top_level_blocks(region: str) -> list[str] | None:
    """Split a task region into its top-level ``<task>…</task>`` blocks.

    A ``<task>`` inside another's body (an example in a description) stays in
    its block. Returns None when the tags do not balance, a missing or a stray
    ``</task>``, so the caller keeps the whole-region path and its warnings.
    """
    blocks: list[str] = []
    depth, start = 0, 0
    for match in _TASK_EDGE.finditer(region):
        if match.group(0).startswith("</"):
            if depth == 0:
                return None
            depth -= 1
            if depth == 0:
                blocks.append(region[start : match.end()])
        else:
            if depth == 0:
                start = match.start()
            depth += 1
    return blocks if depth == 0 else None


def _parse_xml(xml: str, fallback: str) -> list[DecomposedTask]:
    """Parse ``xml`` wrapped in one root; on rejection, regex-parse ``fallback``."""
    try:
        root = ET.fromstring(f"<r>{xml}</r>")
    except (ET.ParseError, ValueError) as exc:
        # ValueError covers what the parser raises for text it cannot encode,
        # such as a lone surrogate, when a caller passes a string directly.
        logger.warning("Task XML is not well-formed (%s) - falling back to regex extraction", exc)
        return _parse_with_regex(fallback)
    # Direct children only: a <task> nested inside a description is an
    # example, not a task.
    tasks = [_task_from_element(element) for element in root.findall("task")]
    return [task for task in tasks if task is not None]


def _task_from_element(element: ET.Element) -> DecomposedTask | None:
    task_id = (element.get("id") or "").strip()
    if not task_id:
        logger.warning("Skipping a <task> element with no id attribute")
        return None
    nested = sum(1 for _ in element.iter("task")) - 1
    if nested:
        logger.warning(
            "Task %s: %d nested <task> element(s) kept as body text, not parsed "
            "as tasks - check for a misplaced </task>",
            task_id,
            nested,
        )
    files_to_create = _files_from_element(element, "files-to-create")
    files_to_modify = _files_from_element(element, "files-to-modify")
    risks_seen = list(element.iterfind("risks/risk"))
    risks = [
        {"severity": risk.get("severity"), "description": _inner_xml(risk)}
        for risk in risks_seen
        if risk.get("severity")
    ]
    files_seen = len(element.findall("files-to-create/file")) + len(
        element.findall("files-to-modify/file")
    )
    _warn_dropped(task_id, "<file", files_seen, len(files_to_create) + len(files_to_modify))
    _warn_dropped(task_id, "<risk", len(risks_seen), len(risks))
    objective = element.find("objective")
    return DecomposedTask(
        task_id=task_id,
        name=(element.get("name") or "").strip() or task_id,
        objective=_inner_xml(objective) if objective is not None else "",
        files_to_create=files_to_create,
        files_to_modify=files_to_modify,
        validation_checks=[_inner_xml(c) for c in element.iterfind("validation/check")],
        risks=risks,
        dependencies=[_inner_xml(d) for d in element.iterfind("dependencies/dep")],
    )


def _files_from_element(element: ET.Element, section: str) -> list[dict[str, str]]:
    return [
        {"path": node.get("path"), "description": _inner_xml(node)}
        for node in element.iterfind(f"{section}/file")
        if node.get("path")
    ]


def _inner_xml(element: ET.Element) -> str:
    """Text of an element with inline child tags kept, as plain text.

    ``.text`` alone would drop ``<code>x</code>`` from "use <code>x</code>".
    Child tags are rebuilt verbatim around their content; every text node is
    what the parser decoded, once, so ``->`` never comes back as ``-&gt;``.
    The result is prose for a reader, not XML for a parser.
    """
    return _text_with_tags(element).strip()


def _text_with_tags(element: ET.Element) -> str:
    """Rebuild inline child tags around their content, without recursion.

    Iterative, so a plan nested thousands of elements deep, which fits in the
    size limit, cannot exhaust the stack. As in the original, a child whose
    content comes out empty is rendered ``<tag />``; any other is rendered
    ``<tag>content</tag>``.
    """
    # Each frame collects one element's inner text; when its children are
    # exhausted the frame closes and its text is appended to the parent frame.
    frames: list[tuple[ET.Element, list, list[str]]] = [(element, list(element), [element.text or ""])]
    while True:
        node, remaining, parts = frames[-1]
        if remaining:
            child = remaining.pop(0)
            frames.append((child, list(child), [child.text or ""]))
            continue
        inner = "".join(parts)
        if len(frames) == 1:
            return inner
        frames.pop()
        # A double quote inside a decoded value is the only character that
        # would break the rebuilt tag's own quoting.
        attrs = "".join(
            f' {key}="{value.replace(chr(34), "&quot;")}"' for key, value in node.attrib.items()
        )
        parent_parts = frames[-1][2]
        parent_parts.append(f"<{node.tag}{attrs}>{inner}</{node.tag}>" if inner else f"<{node.tag}{attrs} />")
        parent_parts.append(node.tail or "")


def _parse_with_regex(content: str) -> list[DecomposedTask]:
    """Fallback for task XML the parser rejects. Warns about what it drops."""
    tasks: list[DecomposedTask] = []
    # One scan, reused for the orphan check below: the pattern is quadratic
    # on an unclosed block, and one pass halves the cost.
    matches = list(_TASK_BLOCK.finditer(content))
    for match in matches:
        task_id, name, body = match.group(1), match.group(2) or match.group(1), match.group(3)
        files_to_create = _extract_files(body, "files-to-create")
        files_to_modify = _extract_files(body, "files-to-modify")
        validation_checks = _extract_list(body, "validation", "check")
        risks = _extract_risks(body)
        dependencies = _extract_list(body, "dependencies", "dep")
        # A missing </task> lets the non-greedy span run through the next
        # task's closing tag, so the swallowed task sits inside this body.
        if re.search(r"<task[\s>]", body):
            logger.warning(
                "Task %s: body contains another <task> opening - a missing "
                "</task> merged the following task(s) into this one",
                task_id,
            )
        for tag, extracted in (
            ("<file", len(files_to_create) + len(files_to_modify)),
            ("<check", len(validation_checks)),
            ("<risk", len(risks)),
            ("<dep", len(dependencies)),
        ):
            # A space or '>' after the name, so '<files-to-modify>' is not
            # counted as a '<file>'.
            seen = len(re.findall(re.escape(tag) + r"[\s>]", body))
            _warn_dropped(task_id, tag, seen, extracted)
        tasks.append(
            DecomposedTask(
                task_id=task_id,
                name=name,
                objective=_extract_tag(body, "objective"),
                files_to_create=files_to_create,
                files_to_modify=files_to_modify,
                validation_checks=validation_checks,
                risks=risks,
                dependencies=dependencies,
            )
        )
    if not tasks:
        logger.warning("No <task> elements found in decomposition response")
    # Runs even when nothing parsed: a lone task with a single-quoted
    # attribute is exactly the case this warning exists for.
    leftovers, cursor = [], 0
    for match in matches:
        leftovers.append(content[cursor : match.start()])
        cursor = match.end()
    leftovers.append(content[cursor:])
    orphaned = sorted(
        {f"<{m.group(1)}>" for chunk in leftovers for m in _ORPHAN_TAG.finditer(chunk)}
    )
    if orphaned:
        logger.warning(
            "Found task content outside any <task> block (%s) - "
            "%d task(s) parsed; check for a malformed or unclosed <task> tag",
            ", ".join(orphaned),
            len(tasks),
        )
    return tasks


def _warn_dropped(task_id: str, tag: str, seen: int, extracted: int) -> None:
    if seen > extracted:
        logger.warning(
            "Task %s: %d %s tag(s) present but %d parsed - "
            "check for a missing or malformed attribute",
            task_id,
            seen,
            tag,
            extracted,
        )


def _extract_tag(xml: str, tag: str) -> str:
    match = re.search(rf"<{tag}>(.*?)</{tag}>", xml, re.DOTALL)
    return match.group(1).strip() if match else ""


def _section(xml: str, section_tag: str) -> str | None:
    match = re.search(rf"<{section_tag}>(.*?)</{section_tag}>", xml, re.DOTALL)
    return match.group(1) if match else None


def _extract_files(xml: str, section_tag: str) -> list[dict[str, str]]:
    section = _section(xml, section_tag)
    if section is None:
        return []
    pattern = re.compile(r'<file\s+path="([^"]*)">(.*?)</file>', re.DOTALL)
    return [
        {"path": m.group(1), "description": m.group(2).strip()} for m in pattern.finditer(section)
    ]


def _extract_list(xml: str, section_tag: str, item_tag: str) -> list[str]:
    section = _section(xml, section_tag)
    if section is None:
        return []
    return [
        m.group(1).strip()
        for m in re.finditer(rf"<{item_tag}>(.*?)</{item_tag}>", section, re.DOTALL)
    ]


def _extract_risks(xml: str) -> list[dict[str, str]]:
    section = _section(xml, "risks")
    if section is None:
        return []
    pattern = re.compile(r'<risk\s+severity="([^"]*)">(.*?)</risk>', re.DOTALL)
    return [
        {"severity": m.group(1), "description": m.group(2).strip()}
        for m in pattern.finditer(section)
    ]


def read_spec(plan_path: str) -> list[DecomposedTask]:
    """Read a plan file and return its tasks, in order; empty if it has none.

    Raises ``ValueError`` for an empty, unsafe or oversize path, and
    ``FileNotFoundError`` if the file does not exist.
    """
    if not plan_path:
        raise ValueError("plan_path must be a non-empty string")
    path = validate_file_path(plan_path)
    if not path.exists():
        raise FileNotFoundError(f"Plan file not found: {plan_path}")
    tasks = parse_tasks(read_text(path, PLAN_LIMIT))
    logger.info("Read %d tasks from %s", len(tasks), plan_path)
    return tasks
