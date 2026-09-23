"""Fail when a Markdown link is dead, or when a document has no row in the index.

Every tracked ``*.md`` file is read. Each inline link whose target is a
relative path ending in ``.md`` (an anchor may follow) must resolve to a
tracked file. Absolute URLs are not checked. A target that starts with ``/``
is taken from the repository root. A target that exists on disk but is not
tracked is reported as such: ``git add`` it, or the published tree will not
have it.

Every tracked ``docs/**/*.md`` other than the index itself must be linked
from ``docs/README.md``, so a new document cannot land unindexed.

``scripts/known_dead_links.txt`` lists the targets that were already dead when
this check began, one per line. A link to one of them does not fail. The list
may only shrink: a listed target that now exists, or that nothing links to any
more, fails the check, so the list cannot go stale. Remove the line when the
link is fixed or cut.

Exit 0 when nothing is wrong, 1 otherwise, with every finding on its own line
as ``file:line: target`` or ``docs/README.md: no row for <path>``. Run from
the repository root: ``python scripts/check_doc_links.py``.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

LINK = re.compile(r"\]\(([^)\s]+?)(?:#[^)\s]*)?\)")
KNOWN_NAME = "known_dead_links.txt"
INDEX = "docs/README.md"


def tracked(root: Path) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"], capture_output=True, check=True
    ).stdout
    return [p.decode("utf-8") for p in out.split(b"\0") if p]


def links(path: str, text: str):
    """Yield (line, target) for each relative .md link in the text."""
    base = os.path.dirname(path)
    for number, line in enumerate(text.splitlines(), 1):
        for match in LINK.finditer(line):
            raw = match.group(1)
            if "://" in raw or raw.startswith(("mailto:", "#")) or not raw.endswith(".md"):
                continue
            target = raw[1:] if raw.startswith("/") else os.path.normpath(os.path.join(base, raw))
            yield number, target.replace(os.sep, "/")


def check(root: Path) -> list[str]:
    files = tracked(root)
    present = set(files)
    KNOWN = root / "scripts" / KNOWN_NAME
    known = set()
    if KNOWN.exists():
        known = {
            line.strip()
            for line in KNOWN.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        }
    findings: list[str] = []
    seen_known: set[str] = set()
    indexed: set[str] = set()
    for path in sorted(files):
        if not path.endswith(".md"):
            continue
        text = (root / path).read_text(encoding="utf-8", errors="replace")
        for number, target in links(path, text):
            if path == INDEX:
                indexed.add(target)
            if target in present:
                continue
            if target in known:
                seen_known.add(target)
                continue
            hint = " (exists on disk but is untracked; git add it)" if (root / target).exists() else ""
            findings.append(f"{path}:{number}: dead link to {target}{hint}")
    for target in sorted(known):
        if target in present:
            findings.append(f"{KNOWN.name}: {target} exists now; remove it from the list")
        elif target not in seen_known:
            findings.append(f"{KNOWN.name}: nothing links to {target} any more; remove it from the list")
    if INDEX in present:
        for path in sorted(files):
            if path.startswith("docs/") and path.endswith(".md") and path != INDEX and path not in indexed:
                findings.append(f"{INDEX}: no row for {path}")
    return findings


def repository_root() -> Path:
    """The repository that contains the working directory, else this file's."""
    probe = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if probe.returncode == 0 and probe.stdout.strip():
        return Path(probe.stdout.strip())
    return Path(__file__).resolve().parents[1]


def main() -> int:
    root = repository_root()
    findings = check(root)
    for line in findings:
        print(line)
    if findings:
        print(f"{len(findings)} problem(s)", file=sys.stderr)
        return 1
    print("every Markdown link resolves and every document has an index row")
    return 0


if __name__ == "__main__":
    sys.exit(main())
