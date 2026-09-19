"""Execute only the separately approved, frozen Task 8 role screen."""

import argparse
import importlib.util
import json
from pathlib import Path
import random
import tempfile
import time
from unittest.mock import patch

from attune_harness import review_participants, work_build, work_runtime
from attune_harness.review_contract import canonical, digest, parse_json

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


comparison = load("frozen_plan_build", ROOT / "experiments/plan_build/comparison.py")
base = load("qualified_meter", ROOT / "experiments/assessment_quality/trial.py")
read, write = base.read, base.write
PREPARATION = ROOT / "docs/receipts/plan-build-task8-2026-09-18"
BOUND_FILES = [
    Path(__file__),
    ROOT / "experiments/assessment_quality/trial.py",
    ROOT / "experiments/task_execution/campaign.py",
]


def verify(output):
    admission = read(output / "authorization.json")
    if admission["approved"] is not True:
        raise ValueError("Native comparison requires explicit allocation approval")
    for relative, expected in admission["runner_sha256"].items():
        if comparison.file_hash(ROOT / relative) != expected:
            raise ValueError("Admitted runner changed")
    manifest = read(PREPARATION / "manifest.json")["sha256"]
    for relative, expected in manifest.items():
        if comparison.file_hash(PREPARATION / relative) != expected:
            raise ValueError("Frozen preparation receipt changed")
    for relative, expected in read(PREPARATION / "decision-binding.json")[
        "artifacts"
    ].items():
        if comparison.file_hash(ROOT / relative) != expected:
            raise ValueError("Approved decision material changed")
    protocol = comparison.verify(Path(admission["prepared_path"]))
    if (
        comparison.file_hash(PREPARATION / "protocol.json")
        != admission["protocol_sha256"]
    ):
        raise ValueError("Approved protocol changed")
    if read(PREPARATION / "protocol.json") != protocol:
        raise ValueError("Working packet differs from approved preparation")
    if (
        base.helpers.modules()
        != read(PREPARATION / "preparation-result.json")["module_sha256"]
    ):
        raise ValueError("Loaded Harness differs from qualified source and wheel")
    return protocol


def admit(output):
    output.mkdir(parents=True, exist_ok=False)
    result = read(PREPARATION / "preparation-result.json")
    write(
        output / "authorization.json",
        {
            "approved": True,
            "user_reply": "a",
            "date": "2026-09-18",
            "decision": "A — Run the bounded comparison (Recommended)",
            "scope": "24 native calls; Luna 8, Astra 8, Fable 8; 100-credit planning ceiling; "
            "existing Claude Max; no new API dollars, Task 8 acceptance or release",
            "prepared_path": result["prepared_path"],
            "protocol_sha256": comparison.file_hash(PREPARATION / "protocol.json"),
            "runner_sha256": {
                str(p.relative_to(ROOT)): comparison.file_hash(p) for p in BOUND_FILES
            },
        },
    )
    protocol = verify(output)
    # Per-call mapping is kept out of the blinded semantic scoring packets.
    trials = list(protocol["trials"])
    random.Random(918024).shuffle(trials)
    write(
        output / "blind-key.json",
        {row["id"]: f"sample-{i:02d}" for i, row in enumerate(trials, 1)},
    )
    write(
        output / "ledger.json",
        {"calls": [], "status": "authorized", "new_api_dollars": 0},
    )
    return protocol


def meter_protocol(protocol):
    budget = protocol["budget"]
    return {
        "max_calls": budget["max_calls"],
        "max_calls_by_model": budget["max_calls_by_model"],
        "reservations": budget["reserve_before_next_call"],
        "budget_credits": budget["codex_credit_planning_ceiling"],
    }


def validate_payload(role, payload):
    name = "plan" if role == "planner" else "build"
    request = read(PREPARATION / f"{name}-record.json")["request"]
    if role == "planner":
        work_runtime.validate_reply(payload, request, role)
    else:
        work_build.decode(
            {"kind": "final", "text": canonical(payload)},
            request,
            role,
            request["tasks"][0],
        )


def execute(output):
    protocol = verify(output)
    ledger = read(output / "ledger.json")
    if ledger["status"] not in ("authorized", "running"):
        raise ValueError("Stopped or completed trial is not automatically resumed")
    base.RATES.update(protocol["budget"]["rates_per_million"])
    key = read(output / "blind-key.json")
    ledger["status"] = "running"
    write(output / "ledger.json", ledger)
    meter = base.Meter(output, meter_protocol(protocol), ledger)
    completed = {row["id"] for row in ledger["calls"]}
    for trial in protocol["trials"]:
        if trial["id"] in completed:
            # Invocation restart is allowed only after all prior calls were observed
            # and their decoded result was retained; otherwise never repeat a call.
            if not (output / "calls" / trial["id"] / "decoded.json").is_file():
                raise ValueError("Prior dispatch has no completed decode receipt")
            continue
        verify(output)
        call_id = trial["id"]
        config = protocol["profiles"][trial["model"]]
        turn = read(PREPARATION / f"{trial['role']}-{trial['arm']}.json")
        envelope = {"schema_version": 1, "request_digest": digest(turn), "turn": turn}
        started = time.perf_counter()
        # Native working directory contains no project context or writable fixture.
        cwd = Path(tempfile.mkdtemp(prefix="plan-build-native-", dir="/private/tmp"))
        peer = review_participants.ReviewExchange(
            config, cwd, profile=turn["operation_profile"]
        )
        result = {
            "role": trial["role"],
            "schema_valid": False,
            "semantic_correct": None,
            "presentation_seconds": None,
        }
        try:
            with (
                patch.object(base, "verify", lambda _: verify(output)),
                patch.object(
                    review_participants,
                    "NativeExchange",
                    lambda adapter, **kw: meter.native(call_id, adapter, **kw),
                ),
            ):
                raw = peer(canonical(envelope))
            action = review_participants.decode_action(raw, digest(turn))
            payload = parse_json(action["text"], 32768)
            result["payload"] = payload
            try:
                validate_payload(trial["role"], payload)
            except (ValueError, TypeError, KeyError) as error:
                result["validation_error"] = str(error)
            else:
                result["schema_valid"] = True
        except Exception as error:
            result["transport_error"] = {
                "type": type(error).__name__,
                "detail": str(error),
            }
        result["validated_output_seconds"] = time.perf_counter() - started
        call_dir = output / "calls" / call_id
        call_dir.mkdir(parents=True, exist_ok=True)
        write(call_dir / "decoded.json", {**result, "identity": peer.last_identity})
        blind = output / "blind"
        blind.mkdir(exist_ok=True)
        write(blind / (key[call_id] + ".json"), result)
        # Pricing and usage are outcomes too; unknowns prevent the next dispatch.
        row = next((r for r in ledger["calls"] if r["id"] == call_id), None)
        failed = (
            result.get("transport_error") or row is None or row["state"] != "observed"
        )
        if row and row["adapter"] == "codex" and row["estimated_credits"] is None:
            failed = True
        if row and any(
            row["usage"].get(k) is None for k in ("input_tokens", "output_tokens")
        ):
            failed = True
        if failed:
            ledger["status"] = "stopped"
            ledger["reason"] = (
                "Unresolved transport, decoding or usage; no automatic retry"
            )
            write(output / "ledger.json", ledger)
            raise ValueError(ledger["reason"])
        total = sum(r["estimated_credits"] or 0 for r in ledger["calls"])
        print(
            json.dumps(
                {
                    "observed_calls": len(ledger["calls"]),
                    "estimated_credits": total,
                    "last_schema_valid": result["schema_valid"],
                }
            ),
            flush=True,
        )
    ledger["status"] = "calls-completed-awaiting-semantic-and-artifact-scoring"
    write(output / "ledger.json", ledger)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("action", choices=("admit", "execute", "verify"))
    args = parser.parse_args()
    if args.action == "admit":
        admit(args.output)
    elif args.action == "execute":
        execute(args.output)
    else:
        verify(args.output)
