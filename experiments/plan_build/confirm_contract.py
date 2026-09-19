"""Prepare or run a separately approved v2 role confirmation using the existing meter."""

import argparse
import copy
import importlib.util
from pathlib import Path
import random
import shutil

from attune_harness import work_build, work_runtime
from attune_harness.review_contract import canonical

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "bounded_native_runner", Path(__file__).with_name("run_comparison.py")
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
read, write = runner.read, runner.write
BOUND = [Path(__file__), *runner.BOUND_FILES]


def prepare(output):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    working = output / "working"
    protocol = runner.comparison.prepare(working)
    for role, kind in [("planner", "plan"), ("worker", "build")]:
        record = read(working / f"{kind}-work/record.json")
        previous = read(working / f"{role}-candidate.json")
        run = {
            "source_evidence": previous["source_evidence"],
            "participants": {},
            "response_contract": 2,
        }
        turn = (
            work_runtime._turn(record["request"], role, run)
            if role == "planner"
            else work_build.turn(
                record["request"], run, role, record["request"]["tasks"][0], []
            )
        )
        write(working / f"{role}-candidate.json", turn)
        write(output / f"{kind}-record.json", record)
    protocol.update(
        status="prepared-awaiting-separate-allocation",
        experiment="v2-candidate-only-confirmation",
        response_contract=2,
    )
    protocol["trials"] = [t for t in protocol["trials"] if t["arm"] == "candidate"]
    for i, trial in enumerate(protocol["trials"], 1):
        trial["id"] = f"pc{i:02d}"
    protocol["budget"].update(
        max_calls=12,
        max_calls_by_model=dict.fromkeys(runner.comparison.MODELS, 4),
        codex_credit_planning_ceiling=50,
        expected_credits=[25, 40],
    )
    protocol["budget"][
        "estimate_basis"
    ] = "Half of the completed 24-call screen: 29.91844 estimated credits at the same recorded token rates; range allows changed prompt/output lengths. Not an invoice or a hard per-response cap."
    protocol["budget"].pop("assumed_tokens_per_call")
    protocol["scoring"][
        "floor"
    ] = "Both candidate repetitions must pass per role/model, with zero critical or enforcement misses. No repaired-envelope result counts as an original success."
    protocol[
        "limits"
    ] += " Candidate-only confirmation: no new baseline or causal comparison. Native startup context remains a disclosed confound; no comparative latency claim. Two reported Claude internal turns previously occurred per native invocation."
    for p in BOUND:
        protocol["source_sha256"][str(p.relative_to(ROOT))] = (
            runner.comparison.file_hash(p)
        )
    for role in ("planner", "worker"):
        protocol["prompt_bytes"][f"{role}-candidate"] = len(
            canonical(read(working / f"{role}-candidate.json")).encode()
        )
    write(working / "protocol.json", protocol)
    freeze = read(working / "freeze.json")
    write(
        working / "freeze.json",
        {p: runner.comparison.file_hash(working / p) for p in freeze},
    )
    for name in ("protocol.json", "planner-candidate.json", "worker-candidate.json"):
        shutil.copy2(working / name, output / name)
    shutil.copy2(
        runner.PREPARATION / "fixed-integration-driver.json",
        output / "fixed-integration-driver.json",
    )
    write(
        output / "preparation-result.json",
        {
            "prepared_path": str(working),
            "module_sha256": runner.base.helpers.modules(),
            "native_calls": 0,
        },
    )
    write(
        output / "decision-binding.json",
        {
            "artifacts": {
                str(p.relative_to(ROOT)): runner.comparison.file_hash(p)
                for p in [*BOUND, ROOT / "docs/specs/plan-build/contract-correction.md"]
            }
        },
    )
    write(
        output / "manifest.json",
        {
            "sha256": {
                str(p.relative_to(output)): runner.comparison.file_hash(p)
                for p in sorted(output.rglob("*"))
                if p.is_file()
            }
        },
    )
    return protocol


def configured(preparation):
    runner.PREPARATION = preparation.resolve()

    def validate(role, payload):
        request = read(
            runner.PREPARATION
            / ("plan-record.json" if role == "planner" else "build-record.json")
        )["request"]
        if role == "planner":
            work_runtime.validate_reply(payload, request, role, contract_version=2)
        else:
            # The new trial specifically tests v2, while the product retains its
            # strict legacy decoder for previously configured participants.
            if payload.get("schema_version") != 2:
                raise ValueError("Confirmation requires a v2 worker reply")
            work_build.decode(
                {"kind": "final", "text": canonical(payload)},
                request,
                role,
                request["tasks"][0],
                contract_version=2,
            )

    runner.validate_payload = validate
    return runner


def admit(preparation, output, *, approval):
    if not approval or not approval.strip():
        raise ValueError("Record the separate user allocation before admission")
    runtime = configured(preparation)
    output.mkdir(parents=True, exist_ok=False)
    write(
        output / "authorization.json",
        {
            "approved": True,
            "user_reply": approval,
            "scope": "12 native invocations; Luna 4, Astra 4, Fable 4; expected 25–40 Codex credits, 50-credit planning ceiling; existing Claude Max, no new API dollars; no Task 8 acceptance or release",
            "prepared_path": str(preparation.resolve() / "working"),
            "protocol_sha256": runner.comparison.file_hash(
                preparation / "protocol.json"
            ),
            "runner_sha256": {
                str(p.relative_to(ROOT)): runner.comparison.file_hash(p) for p in BOUND
            },
        },
    )
    protocol = runtime.verify(output)
    trials = copy.deepcopy(protocol["trials"])
    random.Random(918012).shuffle(trials)
    write(
        output / "blind-key.json",
        {t["id"]: f"sample-{i:02d}" for i, t in enumerate(trials, 1)},
    )
    write(
        output / "ledger.json",
        {"calls": [], "status": "authorized", "new_api_dollars": 0},
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "admit", "execute", "verify"))
    parser.add_argument("preparation", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--approval")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.preparation)
    elif args.action == "admit":
        admit(args.preparation, args.output, approval=args.approval)
    else:
        getattr(configured(args.preparation), args.action)(args.output)
