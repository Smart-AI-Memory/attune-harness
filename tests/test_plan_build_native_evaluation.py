"""Calibrate the local evaluation owner with known correct and wrong artifacts."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "plan_build_evaluator", ROOT / "experiments/plan_build/evaluate_worker.py"
)
evaluator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluator)


@pytest.mark.parametrize("wrong", [False, True])
def test_fixed_oracle_and_actual_controls_distinguish_artifact_correctness(
    tmp_path, wrong
):
    template = json.loads(evaluator.comparison.EVALUATION_TEMPLATE.read_text())
    file = next(
        f for f in template["files"] if f["path"] == evaluator.comparison.EXPORT
    )
    if wrong:
        file["text"] = file["text"].replace(
            "findings = receipt.pop('findings')",
            "findings = [f for f in receipt.pop('findings') if f['status'] == 'verified']",
        )
    sample = tmp_path / "sample.json"
    sample.write_text(
        json.dumps(
            {
                "payload": {
                    "schema_version": 1,
                    "task_id": "export",
                    "dependencies": [],
                    "files": [file],
                }
            }
        )
    )
    result = evaluator.evaluate(sample, tmp_path / "result")
    assert result["status"] == ("needs_revision" if wrong else "completed")
    assert result["native_calls"] == 0 and result["protected_inputs_preserved"]
    assert bool(result["stale_handoff_rejected"]) is (not wrong)
