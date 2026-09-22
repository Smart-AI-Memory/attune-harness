"""The four names the Spec workspace needs from Attune AI's spec intake.

Carried from Attune AI (branch ``codex/shared-memory-adoption`` at
``b89f7953f``): ``attune/elicitation/spec_intake.py``, step 3.2 of the spec
authority's Task 3 (D14). Only what ``spec/workspace.py`` imports is here:
``OTHER``, ``existing_spec_slugs``, ``area_candidates`` and
``compose_spec_contract``. The intake form template, its provider
registration, the command-line seam and the line that wrote the template
into a global registry at import time stay behind; Task 1 named that write
as the module's seam, and the four names never needed it.

One seam is reworked. The original's ``area_candidates`` looked only under
``src/attune/``, Attune AI's own package. Here it looks at every package
under ``src/``: a package's subpackages are the candidates, and a package
with no subpackages is a candidate itself, so the Harness tree and the Attune
AI tree both yield sensible areas. Both path functions also accept the root
as a string, where the original required a ``Path``.

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

#: Free-text sentinel offered alongside derived options.
OTHER = "other (name an area)"

_SKIP_DIRS = frozenset({"__pycache__", ".pytest_cache", ".git"})


def existing_spec_slugs(repo_root: Path) -> list[str]:
    """Slugs already taken under ``docs/specs/`` (collision check)."""
    specs_dir = Path(repo_root) / "docs" / "specs"
    if not specs_dir.is_dir():
        return []
    return sorted(d.name for d in specs_dir.iterdir() if d.is_dir() and d.name not in _SKIP_DIRS)


def _is_package(directory: Path) -> bool:
    return (
        directory.is_dir()
        and directory.name not in _SKIP_DIRS
        and (directory / "__init__.py").is_file()
    )


def area_candidates(repo_root: Path, limit: int = 6) -> list[str]:
    """Likely primary code areas: the packages under ``src/``.

    A directory with an ``__init__.py`` is a package. Each top-level
    package's subpackages are candidates; a top-level package without any is
    a candidate itself. Sorted, and capped at ``limit``; the form always
    offers a free-text escape, so the cap bounds noise, not reach.
    """
    src = Path(repo_root) / "src"
    if not src.is_dir():
        return []
    areas: list[str] = []
    for package in sorted(src.iterdir()):
        if not _is_package(package):
            continue
        subpackages = [child for child in sorted(package.iterdir()) if _is_package(child)]
        if subpackages:
            areas.extend(f"src/{package.name}/{child.name}" for child in subpackages)
        else:
            areas.append(f"src/{package.name}")
    return areas[:limit]


def compose_spec_contract(answers: dict[str, Any], taken_slugs: list[str]) -> str:
    """Render answers as the session-contract block Stage 1 consumes.

    A slug collision is surfaced as a WARNING line rather than an error: the
    existing spec may be exactly where the work belongs, and that call is the
    user's.
    """
    outcome = str(answers.get("outcome", "")).strip()
    done_when = str(answers.get("done_when", "")).strip()
    area = str(answers.get("area", "")).strip()
    slug = str(answers.get("slug", "")).strip()
    lines = [
        "## Session contract",
        "",
        f"- **Outcome:** {outcome}",
        f"- **Done when:** {done_when}",
    ]
    if area and area != OTHER:
        lines.append(f"- **Scope:** {area}")
    if slug:
        lines.append(f"- **Spec:** docs/specs/{slug}/")
        if slug in taken_slugs:
            lines.append(
                f"- **WARNING:** docs/specs/{slug}/ already exists — "
                "amend that spec or pick a new slug."
            )
    return "\n".join(lines) + "\n"
