"""No paid calls: exercise the approved runner through the actual native decoders."""

import importlib.util
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from attune_harness import process, work_runtime

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "plan_build_native_runner", ROOT / "experiments/plan_build/run_comparison.py"
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_exact_allocation_and_decoders_with_injected_processes(tmp_path, monkeypatch):
    # A fresh offline packet exercises current code without rewriting or weakening
    # the completed native campaign's immutable source bindings.
    prepared = tmp_path / "prepared"
    runner.comparison.prepare(prepared)
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    for name in (
        "protocol.json",
        "planner-baseline.json",
        "planner-candidate.json",
        "worker-baseline.json",
        "worker-candidate.json",
    ):
        shutil.copy2(prepared / name, receipts / name)
    for role in ("plan", "build"):
        shutil.copy2(
            prepared / f"{role}-work/record.json", receipts / f"{role}-record.json"
        )
    shutil.copy2(
        runner.PREPARATION / "fixed-integration-driver.json",
        receipts / "fixed-integration-driver.json",
    )
    runner.write(
        receipts / "preparation-result.json",
        {
            "prepared_path": str(prepared),
            "module_sha256": runner.base.helpers.modules(),
        },
    )
    test_path = Path(__file__).resolve()
    runner.write(
        receipts / "decision-binding.json",
        {
            "artifacts": {
                str(test_path.relative_to(ROOT)): hashlib.sha256(
                    test_path.read_bytes()
                ).hexdigest()
            }
        },
    )
    runner.write(
        receipts / "manifest.json",
        {
            "sha256": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in receipts.iterdir()
            }
        },
    )
    monkeypatch.setattr(runner, "PREPARATION", receipts)
    captured = []

    def fake(argv, prompt, **options):
        captured.append(argv)
        assert "ANTHROPIC_API_KEY" not in options["environment"]
        assert "OPENAI_API_KEY" not in options["environment"]
        assert not str(options["cwd"]).startswith(str(ROOT))
        attempt = json.loads(prompt.split("\n", 1)[1])["attempt"]
        turn = json.loads(attempt["task"]["objective"])
        if turn["role"] == "planner":
            payload = work_runtime.demonstration_reply(turn)
        else:
            proposal = runner.read(runner.PREPARATION / "fixed-integration-driver.json")
            payload = {
                "schema_version": 1,
                "task_id": "export",
                "dependencies": [],
                "files": [
                    f
                    for f in proposal["files"]
                    if f["path"] == runner.comparison.EXPORT
                ],
            }
        answer = {"text": json.dumps(payload)}
        if argv[0] == "codex":
            assert 'service_tier="default"' in argv
            assert 'forced_login_method="chatgpt"' in argv
            raw = "\n".join(
                json.dumps(row)
                for row in [
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
            raw = json.dumps(
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
        return process.ProcessResult(argv, 0, raw, "")

    monkeypatch.setattr(process, "invoke", fake)
    out = tmp_path / "experiment"
    runner.admit(out)
    runner.execute(out)
    ledger = runner.read(out / "ledger.json")
    assert len(captured) == 24 and len(ledger["calls"]) == 24
    assert ledger["status"] == "calls-completed-awaiting-semantic-and-artifact-scoring"
    assert all(runner.read(p)["schema_valid"] for p in (out / "blind").glob("*.json"))
    with pytest.raises(ValueError, match="not automatically resumed"):
        runner.execute(out)
    assert len(captured) == 24


@pytest.mark.parametrize(
    "problem", ["unknown", "unresolved", "duplicate", "ceiling", "model_cap"]
)
def test_existing_meter_enforces_the_frozen_allocation(problem):
    protocol = runner.read(runner.PREPARATION / "protocol.json")
    meter = runner.meter_protocol(protocol)
    row = {
        "state": "observed",
        "id": "first",
        "model": "gpt-6-astra",
        "adapter": "codex",
        "estimated_credits": 1,
    }
    ledger = {"calls": [row]}
    call_id = "next"
    if problem == "unknown":
        row["estimated_credits"] = None
    elif problem == "unresolved":
        row["state"] = "dispatching"
    elif problem == "duplicate":
        call_id = "first"
    elif problem == "ceiling":
        row["estimated_credits"] = 91
    else:
        ledger["calls"] = [{**row, "id": str(i)} for i in range(8)]
    with pytest.raises(ValueError):
        runner.base.admit(meter, ledger, "gpt-6-astra", call_id)
