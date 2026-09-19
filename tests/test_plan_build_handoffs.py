"""Actual fixture subprocesses and retained failures; no model invocations."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from attune_harness import process, work_runtime

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "experiments/plan_build/fixtures/run_supplemental.py"
NATIVE = ROOT / "docs/receipts/plan-build-connected-native-2026-09-18"


@pytest.fixture
def runner_case(tmp_path):
    root = tmp_path / "checkout"
    package = root / "src/attune_harness"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "documentation.py").write_text("VALUE = 'fixture'\n")
    (package / "documentation_export.py").write_text("VALUE = 'fixture'\n")
    tests = root / "tests/generated"
    tests.mkdir(parents=True)
    (tests / "test_export.py").write_text(
        "import unittest\n"
        "from attune_harness import documentation, documentation_export\n"
        "class Ordinary(unittest.TestCase):\n"
        "    def test_fixture(self):\n"
        "        self.assertEqual(documentation.VALUE, 'fixture')\n"
        "        self.assertEqual(documentation_export.VALUE, 'fixture')\n"
    )
    (root / RUNNER.name).write_bytes(RUNNER.read_bytes())
    shadow = tmp_path / "installed-shadow/attune_harness"
    shadow.mkdir(parents=True)
    for name in ("__init__.py", "documentation.py", "documentation_export.py"):
        (shadow / name).write_text("VALUE = 'installed'\n")
    return root, shadow


def invoke(case):
    root, shadow = case
    return subprocess.run(
        [sys.executable, "-B", RUNNER.name],
        cwd=root,
        # Test-only ambient shadow: the product probe environment stays unchanged.
        env={
            "PATH": "/usr/bin:/bin",
            "PYTHONPATH": str(shadow.parent),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        },
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_ordinary_imports_use_changed_source_instead_of_installed_shadow(runner_case):
    result = invoke(runner_case)
    assert result.returncode == 0, result.stderr
    assert "Ran 1 test" in result.stderr
    assert (
        str(runner_case[0] / "src/attune_harness/documentation_export.py")
        in result.stdout
    )
    assert (
        "acceptance"
        not in (runner_case[0] / "tests/generated/test_export.py").read_text()
    )


@pytest.mark.parametrize(
    "name", ["__init__.py", "documentation.py", "documentation_export.py"]
)
def test_foreign_origin_cannot_return_green_even_with_passing_tests(runner_case, name):
    root, shadow = runner_case
    target = root / "src/attune_harness" / name
    target.unlink()
    target.symlink_to(shadow / name)
    (root / "tests/generated/test_export.py").write_text(
        "import unittest\nclass FalseGreen(unittest.TestCase):\n"
        "    def test_claim(self): self.assertTrue(True)\n"
    )
    result = invoke(runner_case)
    assert result.returncode != 0 and "Fixture import origin mismatch" in result.stderr


@pytest.mark.parametrize("failure", ["empty", "failed_test", "missing_export"])
def test_no_success_for_empty_failed_or_unimportable_tests(runner_case, failure):
    root, _ = runner_case
    if failure == "empty":
        (root / "tests/generated/test_export.py").write_text("# No tests\n")
    elif failure == "failed_test":
        p = root / "tests/generated/test_export.py"
        p.write_text(p.read_text().replace("'fixture'", "'wrong'"))
    else:
        (root / "src/attune_harness/documentation_export.py").unlink()
    result = invoke(runner_case)
    assert result.returncode != 0
    expected = {
        "empty": "No supplemental tests",
        "failed_test": "FAILED",
        "missing_export": "ModuleNotFoundError",
    }
    assert expected[failure] in result.stderr


def test_original_luna_missing_choices_is_still_a_failure():
    payload = json.loads(
        (NATIVE / "calls/luna-routine-planner/decoded.json").read_text()
    )["payload"]
    request = json.loads((NATIVE / "journeys/luna-routine/initial.json").read_text())[
        "request"
    ]
    assert "choices" not in payload
    with pytest.raises(ValueError, match="Expected fields"):
        work_runtime.validate_reply(payload, request, "planner", contract_version=2)
    assert "choices" not in payload


def test_retained_astra_journey_uses_the_corrected_runner(tmp_path):
    path = ROOT / "experiments/plan_build/qualify_handoffs.py"
    spec = importlib.util.spec_from_file_location("local_handoff_qualification", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.qualify(tmp_path / "qualification")
    assert result["native_calls"] == 0
    assert result["replayed_native_replies"] == 5
    assert result["scripted_reviewer_replies"] == 1
    assert result["completed_replay"]["status"] == "completed"
    assert result["changed_runner_blocked"]
    assert result["original_luna_reply_rejected"]


@pytest.fixture
def confirmation(tmp_path, monkeypatch):
    path = ROOT / "experiments/plan_build/prepare_handoff_confirmation.py"
    spec = importlib.util.spec_from_file_location("handoff_confirmation", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    prepared = tmp_path / "prepared"
    module.prepare(prepared)
    monkeypatch.setattr(module.native, "PREP", prepared)
    return module.native, prepared


def test_new_packet_needs_explicit_admission_and_binds_the_actual_budget(
    confirmation, tmp_path
):
    native, prepared = confirmation
    output = tmp_path / "live"
    with pytest.raises(ValueError, match="explicit user allocation"):
        native.admit(output, None)
    assert not output.exists()
    native.admit(output, "Synthetic test admission; no native calls")
    admission = native.read(output / "authorization.json")
    assert admission["scope"]["budget"]["max_calls"] == 6
    budget = admission["scope"]["budget"]
    assert budget["codex_credit_planning_ceiling"] == 40
    assert admission["scope"]["budget"]["max_calls_by_model"] == {
        "gpt-5.6-luna": 4,
        "gpt-6-astra": 2,
    }
    assert admission["preparation"] == str(prepared)
    assert native.read(output / "ledger.json")["calls"] == []


@pytest.mark.parametrize("change", ["packet", "directory", "closed"])
def test_wrong_packet_or_closed_allocation_never_dispatches(
    confirmation, tmp_path, monkeypatch, change
):
    native, prepared = confirmation
    output = tmp_path / "live"
    native.admit(output, "Synthetic test admission; no native calls")
    monkeypatch.setattr(
        process, "invoke", lambda *a, **kw: pytest.fail("Unexpected dispatch")
    )
    if change == "packet":
        path = prepared / "decision-form.md"
        path.write_text(path.read_text() + "\nChanged budget.\n")
    elif change == "directory":
        monkeypatch.setattr(native, "PREP", tmp_path / "other")
    else:
        native.write(
            output / "ledger.json",
            {"calls": [], "status": "closed", "new_api_dollars": 0},
        )
    with pytest.raises(ValueError):
        native.dispatch(output, "blocked", "gpt-5.6-luna", {})


def test_six_call_ceiling_with_injected_native_envelopes_only(
    confirmation, tmp_path, monkeypatch
):
    native, prepared = confirmation
    captured = []

    def fake(argv, prompt, **kwargs):
        captured.append(argv)
        assert (
            'service_tier="default"' in argv and 'forced_login_method="chatgpt"' in argv
        )
        assert "OPENAI_API_KEY" not in kwargs["environment"]
        turn = json.loads(
            json.loads(prompt.split("\n", 1)[1])["attempt"]["task"]["objective"]
        )
        payload = (
            work_runtime.demonstration_reply(turn)
            if turn["role"] in ("planner", "critic")
            else {"kind": "critique", "findings": [], "notes": []}
        )
        if turn["role"] == "worker":
            payload = {
                "schema_version": 2,
                "files": [
                    {**f, "text": "# Injected output; never executed\n"}
                    for f in turn["output_schema"]["files"]
                ],
            }
        events = [
            {"type": "thread.started", "thread_id": "injected-only"},
            {"type": "turn.started"},
            {
                "type": "item.completed",
                "item": {
                    "type": "agent_message",
                    "text": json.dumps({"text": json.dumps(payload)}),
                },
            },
            {
                "type": "turn.completed",
                "usage": {
                    "input_tokens": 1000,
                    "cached_input_tokens": 0,
                    "output_tokens": 500,
                },
            },
        ]
        return process.ProcessResult(
            argv, 0, "\n".join(json.dumps(e) for e in events), ""
        )

    monkeypatch.setattr(process, "invoke", fake)
    output = tmp_path / "live"
    native.admit(output, "Synthetic test admission; injected processes only")
    turns = native.read(prepared / "qualified/luna-routine/turns.json")
    for index, turn in enumerate(turns):
        model = (
            "gpt-5.6-luna" if turn["role"] in ("planner", "worker") else "gpt-6-astra"
        )
        native.dispatch(output, f"injected-{index}", model, turn)
    assert len(captured) == 6
    with pytest.raises(ValueError):
        native.dispatch(output, "seventh", "gpt-5.6-luna", turns[0])
    assert len(captured) == 6
