"""The four intake names the Spec workspace uses.

Carried from Attune AI's tests/unit/elicitation/test_spec_intake.py at
b89f7953f: the five tests for these names, changed only in the import and in
the fixture, which gains ``src/attune/__init__.py`` because the seam requires
the top level to be a package. The six for the form template and the
command-line seam stayed behind with them. New: the Harness-shaped tree, a
mixed tree, the cap, a root with no src, and the cases the review found
unpinned: the exact bytes of a collision block, an ``__init__.py`` that is a
directory, a skip directory inside a package, and files and unsorted names
under ``docs/specs``.
"""

from __future__ import annotations

from pathlib import Path

from attune_harness.spec_intake import (
    OTHER,
    area_candidates,
    compose_spec_contract,
    existing_spec_slugs,
)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    for pkg in ("workflows", "elicitation"):
        d = repo / "src" / "attune" / pkg
        d.mkdir(parents=True)
        (d / "__init__.py").write_text("")
    (repo / "src" / "attune" / "__init__.py").write_text("")
    (repo / "src" / "attune" / "__pycache__").mkdir()
    for slug in ("outcome-first-fix", "local-first-reports"):
        (repo / "docs" / "specs" / slug).mkdir(parents=True)
    return repo


# --- carried -----------------------------------------------------------------


def test_area_candidates_are_packages_only(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "src" / "attune" / "not_a_pkg").mkdir()
    assert area_candidates(repo) == ["src/attune/elicitation", "src/attune/workflows"]


def test_existing_spec_slugs_listed(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    assert existing_spec_slugs(repo) == ["local-first-reports", "outcome-first-fix"]
    assert existing_spec_slugs(tmp_path / "empty") == []


def test_compose_contract_full() -> None:
    block = compose_spec_contract(
        {
            "outcome": "a spec intake form ships",
            "done_when": "PR merged green",
            "area": "src/attune/elicitation",
            "slug": "spec-intake",
        },
        taken_slugs=["outcome-first-fix"],
    )
    assert "- **Outcome:** a spec intake form ships" in block
    assert "- **Done when:** PR merged green" in block
    assert "- **Scope:** src/attune/elicitation" in block
    assert "- **Spec:** docs/specs/spec-intake/" in block
    assert "WARNING" not in block


def test_compose_contract_slug_collision_warns() -> None:
    block = compose_spec_contract(
        {"outcome": "x", "done_when": "y", "slug": "outcome-first-fix"},
        taken_slugs=["outcome-first-fix"],
    )
    assert "WARNING" in block
    assert "amend that spec or pick a new slug" in block


def test_compose_contract_omits_other_area_and_blank_slug() -> None:
    block = compose_spec_contract(
        {"outcome": "x", "done_when": "y", "area": OTHER, "slug": ""}, taken_slugs=[]
    )
    assert "Scope" not in block
    assert "docs/specs/" not in block


# --- the seam: packages under src/, not src/attune/ -------------------------


def test_harness_shaped_tree_offers_its_one_package(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    pkg = repo / "src" / "attune_harness"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "paths.py").write_text("")
    (repo / "src" / "stray.txt").write_text("")
    assert area_candidates(repo) == ["src/attune_harness"]


def test_mixed_tree_lists_subpackages_and_leaf_packages_sorted(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    for path in ("src/zeta/__init__.py", "src/alpha/__init__.py", "src/alpha/one/__init__.py",
                 "src/alpha/two/__init__.py", "src/alpha/three_no_init/x.py", "src/notpkg/x.py"):
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("")
    assert area_candidates(repo) == ["src/alpha/one", "src/alpha/two", "src/zeta"]


def test_area_candidates_are_capped_and_absent_without_src(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    for name in "abcdefgh":
        d = repo / "src" / name
        d.mkdir(parents=True)
        (d / "__init__.py").write_text("")
    assert area_candidates(repo) == [f"src/{n}" for n in "abcdef"]
    assert area_candidates(repo, limit=2) == ["src/a", "src/b"]
    assert area_candidates(tmp_path / "nowhere") == []


def test_skip_dirs_never_count_as_areas_or_slugs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    for name in ("__pycache__", ".git", ".pytest_cache", "real"):
        d = repo / "src" / name
        d.mkdir(parents=True)
        (d / "__init__.py").write_text("")
        (repo / "docs" / "specs" / name).mkdir(parents=True)
    assert area_candidates(repo) == ["src/real"]
    assert existing_spec_slugs(repo) == ["real"]


def test_compose_strips_and_stringifies_answers() -> None:
    block = compose_spec_contract({"outcome": "  o  ", "done_when": 7, "area": "  ", "slug": " s "}, [])
    assert "- **Outcome:** o\n" in block
    assert "- **Done when:** 7\n" in block
    assert "Scope" not in block
    assert "- **Spec:** docs/specs/s/" in block
    assert block.endswith("\n")


# --- found by review: bugs the first ten tests let through --------------------


def test_compose_collision_block_bytes_are_exact() -> None:
    block = compose_spec_contract(
        {"outcome": "o", "done_when": "d", "area": "src/x", "slug": "taken"}, taken_slugs=["taken"]
    )
    assert block == (
        "## Session contract\n"
        "\n"
        "- **Outcome:** o\n"
        "- **Done when:** d\n"
        "- **Scope:** src/x\n"
        "- **Spec:** docs/specs/taken/\n"
        "- **WARNING:** docs/specs/taken/ already exists — amend that spec or pick a new slug.\n"
    )


def test_an_init_that_is_a_directory_is_not_a_package(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "src" / "fake" / "__init__.py").mkdir(parents=True)
    (repo / "src" / "real" / "__init__.py").parent.mkdir(parents=True)
    (repo / "src" / "real" / "__init__.py").write_text("")
    (repo / "src" / "real" / "sub" / "__init__.py").mkdir(parents=True)
    assert area_candidates(repo) == ["src/real"]


def test_skip_dirs_inside_a_package_are_not_areas(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    for name in ("__pycache__", ".pytest_cache", "keep"):
        d = repo / "src" / "pkg" / name
        d.mkdir(parents=True)
        (d / "__init__.py").write_text("")
    (repo / "src" / "pkg" / "__init__.py").write_text("")
    assert area_candidates(repo) == ["src/pkg/keep"]


def test_slugs_are_directories_only_and_sorted(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    specs = repo / "docs" / "specs"
    for name in ("zeta", "alpha", "mid"):
        (specs / name).mkdir(parents=True)
    (specs / "README.md").write_text("")
    (specs / "aaa-file").write_text("")
    assert existing_spec_slugs(repo) == ["alpha", "mid", "zeta"]


def test_a_string_root_is_accepted(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    assert existing_spec_slugs(str(repo)) == existing_spec_slugs(repo)
    assert area_candidates(str(repo)) == area_candidates(repo)
