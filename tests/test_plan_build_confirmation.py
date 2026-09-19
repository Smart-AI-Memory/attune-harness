"""New allocation preparation and real decoder rehearsal with injected processes."""

import importlib.util
import json
from pathlib import Path

import pytest

from attune_harness import process, work_runtime

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "contract_confirmation", ROOT / "experiments/plan_build/confirm_contract.py"
)
confirmation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(confirmation)


@pytest.fixture
def prepared(tmp_path):
    path = tmp_path / "prepared"
    confirmation.prepare(path)
    return path


def test_preparation_freezes_twelve_v2_candidates_without_admission(prepared):
    protocol = confirmation.read(prepared / "protocol.json")
    assert protocol["status"] == "prepared-awaiting-separate-allocation"
    assert protocol["native_calls"] == 0 and len(protocol["trials"]) == 12
    assert protocol["budget"]["codex_credit_planning_ceiling"] == 50
    for model in confirmation.runner.comparison.MODELS:
        for role in ("planner", "worker"):
            assert (
                sum(
                    t["model"] == model and t["role"] == role
                    for t in protocol["trials"]
                )
                == 2
            )
    worker = confirmation.read(prepared / "worker-candidate.json")
    assert worker["response_contract"] == 2
    assert worker["output_schema"]["files"][0]["before_sha256"] is None
    assert not (prepared / "authorization.json").exists()


def test_admission_needs_a_separate_recorded_allocation(prepared, tmp_path):
    output = tmp_path / "live"
    with pytest.raises(ValueError, match="separate user allocation"):
        confirmation.admit(prepared, output, approval=None)
    assert not output.exists()


def test_twelve_calls_and_v2_decoders_use_injected_processes_only(
    prepared, tmp_path, monkeypatch
):
    captured = []

    def fake(argv, prompt, **kwargs):
        captured.append(argv)
        assert not any(
            k in kwargs["environment"] for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY")
        )
        attempt = json.loads(prompt.split("\n", 1)[1])["attempt"]
        turn = json.loads(attempt["task"]["objective"])
        assert turn["response_contract"] == 2
        if turn["role"] == "planner":
            payload = work_runtime.demonstration_reply(turn)
        else:
            fixed = confirmation.read(prepared / "fixed-integration-driver.json")
            payload = {
                "schema_version": 2,
                "files": [
                    f
                    for f in fixed["files"]
                    if f["path"] == confirmation.runner.comparison.EXPORT
                ],
            }
        answer = {"text": json.dumps(payload)}
        if argv[0] == "codex":
            result = "\n".join(
                json.dumps(e)
                for e in [
                    {"type": "thread.started", "thread_id": "synthetic"},
                    {"type": "turn.started"},
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": json.dumps(answer)},
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
            )
        else:
            result = json.dumps(
                {
                    "type": "result",
                    "subtype": "success",
                    "is_error": False,
                    "session_id": "synthetic",
                    "structured_output": answer,
                    "usage": {"input_tokens": 1000, "output_tokens": 500},
                    "modelUsage": {"claude-fable-5-1": {}},
                }
            )
        return process.ProcessResult(argv, 0, result, "")

    monkeypatch.setattr(process, "invoke", fake)
    output = tmp_path / "synthetic-execution"
    confirmation.admit(
        prepared, output, approval="Synthetic offline fixture only; no real allocation"
    )
    runtime = confirmation.configured(prepared)
    runtime.execute(output)
    assert len(captured) == 12
    assert all(
        confirmation.read(p)["schema_valid"] for p in (output / "blind").glob("*.json")
    )
    with pytest.raises(ValueError, match="not automatically resumed"):
        runtime.execute(output)
    assert len(captured) == 12


def test_changed_prepared_prompt_stops_before_dispatch(prepared, tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Stale packet dispatched")

    monkeypatch.setattr(process, "invoke", forbidden)
    output = tmp_path / "synthetic-execution"
    confirmation.admit(prepared, output, approval="Synthetic offline fixture only")
    target = prepared / "worker-candidate.json"
    target.write_text(target.read_text() + "\n")
    with pytest.raises(ValueError, match="Frozen preparation receipt changed"):
        confirmation.configured(prepared).execute(output)
