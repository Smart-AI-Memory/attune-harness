"""``plan --import-plan`` and ``plan --reimport`` through the real command line.

Task 4's first step moved the two functions behind these flags to
``work_accept``; the review found that no test drove either flag, so a
renamed import left the suite green. This file drives both, and the two
refusals that stand in front of them, with a plan written here.
"""
# qualify: platform

import json
import shutil
from pathlib import Path

import pytest

pytest.importorskip("attune_forms")

from attune_harness.cli import main  # noqa: E402
from attune_harness.task_contract import read_task  # noqa: E402
from test_work_contract import work  # noqa: E402,F401

PLAN = """# Probe plan

Two tasks, the second depending on the first.

<tasks>
<task id="1" name="alpha"><objective>Write the alpha module</objective><files-to-create><file path="alpha.py">the module</file></files-to-create><validation><check>alpha imports</check></validation></task>
<task id="2" name="beta"><objective>Wire beta to alpha</objective><files-to-modify><file path="source.py">call alpha</file></files-to-modify><validation><check>beta passes</check></validation><dependencies><dep>1</dep></dependencies></task>
</tasks>

<!-- spec-state: {"schema_version": 2, "completed": []} -->
"""


def write_plan(root):
    target = root / "plans" / "probe.md"
    target.parent.mkdir(exist_ok=True)
    target.write_text(PLAN, encoding="utf-8")
    return target


def edit_before_the_state_comment(target, line):
    lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
    target.write_text("".join(lines[:-1]) + line + lines[-1], encoding="utf-8")


def request_file(tmp_path, data):
    intent = {**data["intent"], "scope": sorted(set(data["intent"]["scope"]) | {"alpha.py"})}
    path = tmp_path / "request.json"
    path.write_text(json.dumps({"intent": intent, "assignments": data["assignments"]}), encoding="utf-8")
    return path


def run(argv, capsys):
    code = main(argv)
    out = capsys.readouterr().out
    return code, json.loads(out) if out.strip() else None


def test_import_plan_then_reimport_an_edit_through_the_cli(work, tmp_path, capsys):
    root, config, data = work
    target = write_plan(root)
    directory = tmp_path / "work"
    code, envelope = run(
        ["plan", "--task-dir", str(directory), "--project", str(root), "--config", str(config),
         "--request", str(request_file(tmp_path, data)), "--import-plan", str(target)],
        capsys,
    )
    assert code == 0, envelope
    record = read_task(directory)
    assert record["status"] == "draft"
    assert [t["id"] for t in record["request"]["tasks"]] == ["1", "2"]
    assert record["request"]["legacy"]["approval_imported"] is False
    before = record["request"]["legacy"]["content_sha256"]

    edit_before_the_state_comment(target, "<!-- edited after import -->\n")
    code, envelope = run(
        ["plan", "--task-dir", str(directory), "--reimport", "--checkpoint", record["checkpoint_digest"]],
        capsys,
    )
    assert code == 0, envelope
    after = read_task(directory)
    assert after["status"] == "draft"
    assert after["request"]["legacy"]["content_sha256"] != before
    assert after["checkpoint_digest"] != record["checkpoint_digest"]


def test_reimport_with_a_stale_checkpoint_is_refused_in_the_bridge_s_words(work, tmp_path, capsys):
    root, config, data = work
    target = write_plan(root)
    directory = tmp_path / "work"
    code, _ = run(
        ["plan", "--task-dir", str(directory), "--project", str(root), "--config", str(config),
         "--request", str(request_file(tmp_path, data)), "--import-plan", str(target)],
        capsys,
    )
    assert code == 0
    code, envelope = run(["plan", "--task-dir", str(directory), "--reimport", "--checkpoint", "0" * 64], capsys)
    assert code == 2
    assert "Reimport requires the current legacy work checkpoint" in json.dumps(envelope)
    assert read_task(directory)["request"]["legacy"]["content_sha256"] == read_task(directory)["request"]["legacy"]["content_sha256"]


def test_a_plan_outside_the_project_is_refused_before_anything_is_written(work, tmp_path, capsys):
    root, config, data = work
    outside = tmp_path / "outside.md"
    outside.write_text(PLAN, encoding="utf-8")
    directory = tmp_path / "work"
    code, envelope = run(
        ["plan", "--task-dir", str(directory), "--project", str(root), "--config", str(config),
         "--request", str(request_file(tmp_path, data)), "--import-plan", str(outside)],
        capsys,
    )
    assert code == 2
    assert "Legacy plan must be a regular file inside the project" in json.dumps(envelope)
    assert not directory.exists()
