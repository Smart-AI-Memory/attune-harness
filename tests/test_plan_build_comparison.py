"""Disposable outcome-screen controls; local fixtures, never model competence."""

import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from attune_harness import review_participants, work_build, work_runtime
from attune_harness.review_contract import canonical
from attune_harness.task_contract import read_task

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "plan_build_comparison", ROOT / "experiments/plan_build/comparison.py"
)
comparison = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(comparison)


@pytest.fixture
def packet(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Offline preparation attempted model dispatch")

    monkeypatch.setattr(review_participants, "NativeExchange", forbidden)
    monkeypatch.setattr(review_participants.ReviewExchange, "__call__", forbidden)
    output = tmp_path / "comparison"
    comparison.prepare(output)
    return output


def test_preparation_freezes_matched_real_profiles_without_authority(packet):
    protocol = comparison.verify(packet)
    assert protocol["native_calls"] == 0 and len(protocol["trials"]) == 24
    for model in comparison.MODELS:
        assert sum(t["model"] == model for t in protocol["trials"]) == 8
        profile = protocol["profiles"][model]
        assert profile["tools"] == [] and "review_mode" not in profile
    for role in ("planner", "worker"):
        baseline = json.loads((packet / f"{role}-baseline.json").read_text())
        candidate = json.loads((packet / f"{role}-candidate.json").read_text())
        assert baseline.pop("protocol") != candidate.pop("protocol")
        assert baseline == candidate
    for name in ("plan-work", "build-work"):
        record = read_task(packet / name)
        assert record["status"] == "draft" and record["acceptance"] is None
    assert read_task(packet / "plan-work")["request"]["authoring"]["tier"] == "xml"


@pytest.mark.parametrize(
    "path",
    [
        "planner-candidate.json",
        "worker-baseline.json",
        "participants.json",
        "checkout/src/attune_harness/documentation.py",
        "checkout/acceptance.py",
        "protocol.json",
    ],
)
def test_changed_trial_material_invalidates_preparation(packet, path):
    target = packet / path
    target.write_text(target.read_text() + "\n")
    with pytest.raises(ValueError, match="Prepared artifact changed"):
        comparison.verify(packet)


def test_changed_host_source_invalidates_preparation(packet, tmp_path, monkeypatch):
    protocol = comparison.verify(packet)
    copied = tmp_path / "host-source"
    for path in protocol["source_sha256"]:
        target = copied / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / path, target)
    monkeypatch.setattr(comparison, "ROOT", copied)
    comparison.verify(packet)
    target = copied / "src/attune_harness/work_contract.py"
    target.write_text(target.read_text() + "\n# Later source revision.\n")
    with pytest.raises(ValueError, match="Source changed"):
        comparison.verify(packet)


@pytest.mark.parametrize(
    "problem", ["goal", "scope", "authority", "coverage", "dependency"]
)
def test_planner_host_guards_do_not_accept_invalid_authority(packet, problem):
    request = read_task(packet / "plan-work")["request"]
    turn = json.loads((packet / "planner-candidate.json").read_text())
    proposal = work_runtime.demonstration_reply(turn)
    work_runtime.validate_reply(proposal, request, "planner")
    if problem == "goal":
        proposal["goal"] = "Only export verified findings"
    elif problem == "scope":
        proposal["tasks"][0]["outputs"] = ["outside.py"]
    elif problem == "authority":
        proposal["accepted"] = True
    elif problem == "coverage":
        proposal["coverage"].pop()
    else:
        proposal["tasks"][0]["dependencies"] = ["missing"]
    with pytest.raises(ValueError):
        work_runtime.validate_reply(proposal, request, "planner")


def test_schema_success_does_not_entail_correct_human_correction(packet):
    request = read_task(packet / "plan-work")["request"]
    turn = json.loads((packet / "planner-candidate.json").read_text())
    good = work_runtime.demonstration_reply(turn)
    good["notes"] = ["Large-workload performance remains unmeasured."]
    work_runtime.validate_reply(good, request, "planner")
    wrong = copy.deepcopy(good)
    wrong["tasks"][0][
        "objective"
    ] = "Discard unknown and refuted findings before export"
    # Intentionally structurally valid: the frozen semantic rubric must reject it.
    # This test does not invent a keyword-based semantic classifier.
    work_runtime.validate_reply(wrong, request, "planner")
    assert wrong["goal"] == good["goal"]
    assert "goal_fidelity" in comparison.verify(packet)["scoring"]["dimensions"]


@pytest.mark.parametrize("wrong", [False, True])
def test_actual_oracle_rejects_wrong_worker_despite_generated_test(packet, wrong):
    request = read_task(packet / "build-work")["request"]
    retained = json.loads(
        (
            ROOT / "docs/receipts/plan-build-task4-2026-09-18/journey-proposal.json"
        ).read_text()
    )
    file = copy.deepcopy(
        next(f for f in retained["files"] if f["path"] == comparison.EXPORT)
    )
    if wrong:
        file["text"] = file["text"].replace(
            "findings = receipt.pop('findings')",
            "findings = [f for f in receipt.pop('findings') if f['status'] == 'verified']",
        )
    proposal = {
        "schema_version": 1,
        "task_id": "export",
        "dependencies": [],
        "files": [file],
    }
    work_build.decode(
        {"kind": "final", "text": canonical(proposal)},
        request,
        "worker",
        request["tasks"][0],
    )
    root = packet / "checkout"
    (root / file["path"]).write_text(file["text"])
    # Fixed integration driver from Task 4; this is not credited to the worker.
    cli = next(f for f in retained["files"] if f["path"] == comparison.DOCUMENTATION)
    (root / cli["path"]).write_text(cli["text"])
    # Explicit scratch evaluation, not a native build or permission-grant path.
    environment = {
        **os.environ,
        "PYTHONPATH": str(root / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            "acceptance.py",
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == (1 if wrong else 0), completed.stderr
    (root / "tests/test_trivial.py").write_text(
        "def test_generated():\n    assert True\n"
    )
    generated = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "pytest",
            "-q",
            "-o",
            "addopts=",
            "-p",
            "no:cacheprovider",
            "tests/test_trivial.py",
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert generated.returncode == 0, generated.stdout + generated.stderr
    assert (
        root / "unrelated.txt"
    ).read_text() == "Unrelated dirty work must survive.\n"


def test_worker_scope_and_preimage_remain_host_owned(packet):
    request = read_task(packet / "build-work")["request"]
    proposal = {
        "schema_version": 1,
        "task_id": "export",
        "dependencies": [],
        "files": [{"path": "outside.py", "before_sha256": None, "text": "pass\n"}],
    }
    with pytest.raises(ValueError, match="scope"):
        work_build.decode(
            {"kind": "final", "text": canonical(proposal)},
            request,
            "worker",
            request["tasks"][0],
        )
    proposal["files"][0].update(path=comparison.EXPORT, before_sha256="0" * 64)
    with pytest.raises(ValueError, match="preimage"):
        work_build.decode(
            {"kind": "final", "text": canonical(proposal)},
            request,
            "worker",
            request["tasks"][0],
        )
