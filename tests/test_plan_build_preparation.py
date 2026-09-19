"""Preparation evidence tests; no production build or native model claim."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "plan_build_preparation", ROOT / "experiments/plan_build/prepare.py"
)
prep = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prep)


def test_actual_baseline_gaps_and_recovery_are_disclosed(tmp_path):
    result = prep.run(tmp_path / "evidence")
    assert result["native_calls"] == 0
    assert result["baseline"]["returncode"] == 0
    assert result["feature_before"]["returncode"] == 1
    for role in ("planner", "critic"):
        assert result["roles"][role]["attempt"] == []
        assert "role must be" in result["roles"][role]["error"]["detail"]
    for role in ("worker", "reviewer"):
        assert (
            result["roles"][role]["attempt"][0]["adapter_version"]
            == "harness-review-v1"
        )
    assert result["legacy_import"]["unknown_information_silently_ignored"]
    assert result["legacy_import"]["non_task_document_returns_empty"]
    assert result["scratch_creation"]["observed_result_reused_without_second_write"]
    assert (
        result["scratch_creation"]["collision_rejected"]["error"] == "FileExistsError"
    )
    assert (
        result["scratch_creation"]["blind_resume_rejected"]["error"]
        == "UnresolvedOperation"
    )
    root = tmp_path / "evidence/checkout"
    assert (
        root / "unrelated.txt"
    ).read_text() == "Unrelated dirty work must survive.\n"
    assert prep.sha(root / "src/attune_harness/documentation.py") == prep.sha(
        ROOT / "src/attune_harness/documentation.py"
    )
