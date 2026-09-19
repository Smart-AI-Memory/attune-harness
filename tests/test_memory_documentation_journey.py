"""Bounded offline qualification with the unmet Spec criterion kept visible."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "memory_doc_preparation",
    ROOT / "experiments/memory_documentation_journey/prepare.py",
)
prep = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prep)


@pytest.fixture(scope="module")
def preparation(tmp_path_factory):
    output = tmp_path_factory.mktemp("memory-doc-tests") / "evidence"
    return output, prep.run(output)


def test_bounded_repair_control_and_actual_adapter_receipt(preparation):
    output, summary = preparation
    assert summary["provider_calls"] == 0
    assert summary["scripted_participant_calls"] == 6
    assert summary["only_repaired_file"] == ["guide.md"]
    assert summary["control_preserved"] and summary["unrelated_dirty_work_preserved"]
    record = json.loads((output / "work/tested/record.json").read_text())
    assert record["execution"]["result"]["outcome"] == "passed"
    assert record["request"]["source_task"]["task_id"]
    assert record["request"]["selection"]["selected"] == [
        "tests/test_project_filtering.py"
    ]


def test_reference_and_current_evidence_protections(preparation):
    _, summary = preparation
    assert "Stale source evidence" in summary["assessment_reference_change_rejected"]
    assert summary["spec"]["source_change_blocks_test_reuse"]
    assert summary["spec"]["current_blocked_publication_rejects_approval"]
    assert summary["spec"]["replay_rejected"]
    assert summary["spec"]["fresh_receipt_persisted"]


def test_source_change_invalidates_already_rendered_spec_decision(preparation):
    _, summary = preparation
    assert not summary["spec"]["old_spec_form_accepted_after_source_change"]


def test_example_probe_fails_bad_ids_and_allows_valid_paraphrase(tmp_path):
    root, _ = prep.prepare_fixture(tmp_path / "example")

    def probe():
        return subprocess.run(
            [sys.executable, "-B", "probe.py"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=15,
        )

    before = probe()
    assert before.returncode == 1
    assert "example contradicts actual adapter results" in before.stderr
    corrected = (prep.FIXTURES / "corrected.md").read_text()
    (root / "guide.md").write_text(
        corrected.replace(
            "Other projects can still appear.",
            "Results may include records from another project.",
        )
    )
    after = probe()
    assert after.returncode == 0, after.stdout + after.stderr
    assert (
        json.loads(after.stdout)["documentation_semantics"]
        == "not certified by this probe"
    )


def test_behavior_tests_detect_removed_ranking_bonus(tmp_path):
    root, _ = prep.prepare_fixture(tmp_path / "mutation")
    source = root / "adapter/file_stash.py"
    original = source.read_text()
    assert original.count("score += 1.0") == 1
    source.write_text(original.replace("score += 1.0", "score += 0.0"))
    identity_path = root / "adapter/identity.json"
    identity = json.loads(identity_path.read_text())
    identity["sha256"] = prep.sha(source)
    prep.write(identity_path, identity)
    result = subprocess.run(
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
            "tests/test_project_filtering.py",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
        env={
            **os.environ,
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "1 failed, 2 passed" in result.stdout
    assert "test_project_preference_keeps_foreign_records[search]" in result.stdout
