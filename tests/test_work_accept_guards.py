"""The guards in ``work_accept`` that the review's mutations walked past.

Each test here fails when one guard is removed: the single ``SPEC_APPROVAL``
in the supported controls and its copy, the freshness check at construction
against an imported plan that changed, and the symlink half of the import's
containment rule.
"""
# qualify: platform

from pathlib import Path

import pytest

pytest.importorskip("attune_forms")

from attune_harness.work_accept import SPEC_APPROVAL, WorkAcceptance, import_plan  # noqa: E402
from test_work_contract import make, work  # noqa: E402,F401
from test_work_cli_plan_import import PLAN, edit_before_the_state_comment  # noqa: E402


def drafted(work):
    record = make(work)
    return Path(record["record_path"]).parent


def test_spec_approval_is_appended_once_and_never_as_the_shared_object(work):
    directory = drafted(work)
    other = {"id": "tests", "kind": "check", "owner": "harness", "version": 1}
    # Absent from the given controls: appended exactly once, as a copy.
    given = [other]
    acceptance = WorkAcceptance(directory, supported_controls=given)
    assert acceptance.supported == [other, SPEC_APPROVAL]
    assert acceptance.supported[1] is not SPEC_APPROVAL
    assert given == [other]  # the caller's list is not mutated
    # Present already: nothing appended, and the given entries are copies.
    acceptance = WorkAcceptance(directory, supported_controls=[SPEC_APPROVAL, other])
    assert acceptance.supported == [SPEC_APPROVAL, other]
    assert acceptance.supported[0] is not SPEC_APPROVAL
    bare = WorkAcceptance(directory)
    assert bare.supported == [SPEC_APPROVAL] and bare.supported[0] is not SPEC_APPROVAL


def imported(work, tmp_path):
    root, config, data = work
    target = root / "plans" / "probe.md"
    target.parent.mkdir(exist_ok=True)
    target.write_text(PLAN, encoding="utf-8")
    intent = {**data["intent"], "scope": sorted(set(data["intent"]["scope"]) | {"alpha.py"})}
    directory = tmp_path / "imported"
    import_plan(root, config, path=target, directory=directory, intent=intent, assignments=data["assignments"])
    return target, directory


def test_an_imported_plan_that_changed_is_refused_at_construction(work, tmp_path):
    target, directory = imported(work, tmp_path)
    WorkAcceptance(directory)
    edit_before_the_state_comment(target, "<!-- edited after import -->\n")
    with pytest.raises(ValueError, match="Imported plan changed; revise and reaccept"):
        WorkAcceptance(directory)


def test_a_symlinked_plan_inside_the_project_is_refused(work, tmp_path):
    root, config, data = work
    real = root / "plans" / "real.md"
    real.parent.mkdir(exist_ok=True)
    real.write_text(PLAN, encoding="utf-8")
    link = root / "plans" / "link.md"
    try:
        link.symlink_to(real)
    except (OSError, NotImplementedError) as exc:  # no symlink privilege here
        pytest.skip(f"symlinks unavailable: {exc}")
    intent = {**data["intent"], "scope": sorted(set(data["intent"]["scope"]) | {"alpha.py"})}
    with pytest.raises(ValueError, match="Legacy plan must be a regular file inside the project"):
        import_plan(root, config, path=link, directory=tmp_path / "w", intent=intent, assignments=data["assignments"])
    assert not (tmp_path / "w").exists()
