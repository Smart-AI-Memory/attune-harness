"""Captured pre-change CLI output is independent of the candidate implementation."""

import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "default_compatibility_fixture", ROOT / "experiments/plan_build/prepare.py"
)
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
OLD = ROOT / "docs/receipts/plan-build-connected-native-2026-09-18/calls"
FRESH = ROOT / "docs/receipts/plan-build-handoff-confirmation-native-2026-09-18/calls"


def apply_original(root, calls, arm):
    for index in (0, 1):
        payload = json.loads(
            (calls / f"{arm}-worker-{index}/decoded.json").read_text()
        )["payload"]
        for output in payload["files"]:
            (root / output["path"]).write_text(output["text"])


def check(root, baseline=False):
    return subprocess.run(
        [sys.executable, "-B", "acceptance.py", *(["--baseline"] if baseline else [])],
        cwd=root,
        env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_captured_baseline_and_unchanged_passing_native_artifacts(tmp_path):
    root = prepare.fixture(tmp_path)
    original_oracle = (root / "acceptance.py").read_bytes()
    result = check(root, baseline=True)
    assert result.returncode == 0, result.stderr
    apply_original(root, OLD, "astra-reference")
    result = check(root)
    assert result.returncode == 0, result.stderr
    assert (root / "acceptance.py").read_bytes() == original_oracle


@pytest.mark.parametrize("baseline", [False, True])
def test_unchanged_original_luna_default_regression_is_rejected(tmp_path, baseline):
    root = prepare.fixture(tmp_path)
    apply_original(root, FRESH, "luna-routine")
    result = check(root, baseline=baseline)
    assert result.returncode == 1
    assert "AssertionError" in result.stderr and "FAILED" in result.stderr
    assert "CAPTURED_DEFAULT_OUTPUTS[module]" in result.stderr


def test_default_empty_output_is_bound_too(tmp_path):
    root = prepare.fixture(tmp_path)
    apply_original(root, OLD, "astra-reference")
    module = root / "src/attune_harness/documentation.py"
    old = module.read_text()
    marker = "    args = parser.parse_args()\n"
    assert old.count(marker) == 1
    module.write_text(
        old.replace(
            marker,
            marker
            + "    if args.module == 'samples/empty.py' and args.format == 'json':\n"
            "        print('{}')\n        return\n",
        )
    )
    result = check(root)
    assert result.returncode == 1 and "samples/empty.py" in result.stderr


def test_missing_prechange_capture_cannot_pass(tmp_path):
    root = prepare.fixture(tmp_path)
    oracle = root / "acceptance.py"
    text, count = re.subn(
        r"^CAPTURED_DEFAULT_OUTPUTS = .+$",
        "CAPTURED_DEFAULT_OUTPUTS = {}",
        oracle.read_text(),
        flags=re.MULTILINE,
    )
    assert count == 1
    oracle.write_text(text)
    result = check(root, baseline=True)
    assert result.returncode == 1 and "not found in {}" in result.stderr


def test_removing_baseline_comparison_recreates_the_false_green(tmp_path):
    root = prepare.fixture(tmp_path)
    apply_original(root, FRESH, "luna-routine")
    assert check(root).returncode == 1
    oracle = root / "acceptance.py"
    text = oracle.read_text()
    guard = "                self.assertEqual(result.stdout, CAPTURED_DEFAULT_OUTPUTS[module])\n"
    assert text.count(guard) == 1
    oracle.write_text(text.replace(guard, ""))
    result = check(root)
    assert result.returncode == 0, result.stderr
