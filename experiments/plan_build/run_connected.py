"""Meter the separately approved connected experiment; controls precede journeys."""

import argparse
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import time
from unittest.mock import patch

from attune_harness import review_participants, work_runtime
from attune_harness.review_contract import canonical, digest, parse_json

ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT / "docs/receipts/plan-build-connected-preparation-2026-09-18"
spec = importlib.util.spec_from_file_location(
    "qualified_meter", ROOT / "experiments/assessment_quality/trial.py"
)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
read, write = base.read, base.write


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(output):
    admission = read(output / "authorization.json")
    if admission["approved"] is not True:
        raise ValueError("Explicit allocation is required")
    if admission.get("preparation", str(PREP)) != str(PREP):
        raise ValueError("Approved preparation directory changed")
    if sha(PREP / "manifest.json") != admission["preparation_manifest_sha256"]:
        raise ValueError("Approved preparation manifest changed")
    for name, expected in read(PREP / "manifest.json")["sha256"].items():
        if sha(PREP / name) != expected:
            raise ValueError("Approved preparation changed")
    for name, expected in read(PREP / "decision-binding.json")["artifacts"].items():
        if sha(ROOT / name) != expected:
            raise ValueError("Approved decision material changed")
    protocol = read(PREP / "protocol.json")
    for name, expected in protocol["source_sha256"].items():
        if sha(ROOT / name) != expected:
            raise ValueError("Approved source changed")
    for name, expected in admission["runner_sha256"].items():
        if sha(ROOT / name) != expected:
            raise ValueError("Admitted runner changed")
    if base.helpers.modules() != admission["installed_modules"]:
        raise ValueError("Loaded Harness changed")
    return protocol


def admit(output, approval):
    if not approval or not approval.strip():
        raise ValueError("Record the explicit user allocation")
    protocol = read(PREP / "protocol.json")
    output.mkdir(parents=True, exist_ok=False)
    write(
        output / "authorization.json",
        {
            "approved": True,
            "user_reply": approval,
            "scope": {
                "budget": protocol["budget"],
                "journeys": protocol["journeys"],
                "limits": "Existing ChatGPT; no Task 8 acceptance or release",
            },
            "preparation": str(PREP),
            "preparation_manifest_sha256": sha(PREP / "manifest.json"),
            "installed_modules": base.helpers.modules(),
            "runner_sha256": {
                str(p.relative_to(ROOT)): sha(p)
                for p in (
                    Path(__file__),
                    ROOT / "experiments/assessment_quality/trial.py",
                    ROOT / "experiments/task_execution/campaign.py",
                )
            },
        },
    )
    verify(output)
    write(
        output / "ledger.json",
        {"calls": [], "status": "authorized", "new_api_dollars": 0},
    )


def meter(output, protocol):
    b = protocol["budget"]
    base.RATES.update(b["rates_per_million"])
    return base.Meter(
        output,
        {
            "max_calls": b["max_calls"],
            "max_calls_by_model": b["max_calls_by_model"],
            "reservations": b["reserve_before_next_call"],
            "budget_credits": b["codex_credit_planning_ceiling"],
        },
        read(output / "ledger.json"),
    )


def dispatch(output, call_id, model, turn):
    if read(output / "ledger.json")["status"].startswith(("closed", "stopped")):
        raise ValueError("Closed or stopped allocation cannot dispatch")
    protocol = verify(output)
    config = protocol["profiles"][model]
    measured = meter(output, protocol)
    envelope = {"schema_version": 1, "request_digest": digest(turn), "turn": turn}
    peer = review_participants.ReviewExchange(
        config,
        Path(tempfile.mkdtemp(prefix="connected-native-", dir="/private/tmp")),
        profile=turn["operation_profile"],
    )
    started = time.perf_counter()
    with (
        patch.object(base, "verify", lambda _: verify(output)),
        patch.object(
            review_participants,
            "NativeExchange",
            lambda adapter, **kw: measured.native(call_id, adapter, **kw),
        ),
    ):
        raw = peer(canonical(envelope))
    action = review_participants.decode_action(raw, digest(turn))
    payload = parse_json(action["text"], 32768)
    row = next(r for r in measured.ledger["calls"] if r["id"] == call_id)
    if row["state"] != "observed" or row["estimated_credits"] is None:
        raise ValueError("Unresolved dispatch or usage; no repeat")
    write(
        output / "calls" / call_id / "decoded.json",
        {
            "role": turn["role"],
            "payload": payload,
            "validated_output_seconds": time.perf_counter() - started,
            "identity": peer.last_identity,
        },
    )
    return payload


def controls(output):
    protocol = verify(output)
    ledger = read(output / "ledger.json")
    if ledger["status"] != "authorized" or ledger["calls"]:
        raise ValueError("Controls cannot be repeated or automatically resumed")
    ledger["status"] = "controls-running"
    write(output / "ledger.json", ledger)
    try:
        for case in protocol["controls_first"]:
            payload = dispatch(
                output,
                "control-" + case,
                protocol["controls_model"],
                read(PREP / "controls" / (case + ".json")),
            )
            work_runtime.validate_reply(payload, {}, "critic", contract_version=2)
            print(
                canonical({"completed_control": case, "schema_valid": True}), flush=True
            )
    except Exception as error:
        ledger = read(output / "ledger.json")
        ledger.update(status="stopped", reason=f"{type(error).__name__}: {error}")
        write(output / "ledger.json", ledger)
        raise
    ledger = read(output / "ledger.json")
    ledger["status"] = "controls-completed-awaiting-semantic-grading"
    write(output / "ledger.json", ledger)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("admit", "controls", "verify"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--approval")
    parser.add_argument("--preparation", type=Path, default=PREP)
    args = parser.parse_args()
    PREP = args.preparation.resolve()
    if args.action == "admit":
        admit(args.output, args.approval)
    else:
        globals()[args.action](args.output)
