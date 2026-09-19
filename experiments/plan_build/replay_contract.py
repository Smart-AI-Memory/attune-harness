"""Offline contract diagnostics over retained native replies; no new model calls."""

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from attune_harness import review_participants, work_build, work_runtime
from attune_harness.review_contract import canonical
from attune_harness.task_contract import read_task

ROOT = Path(__file__).resolve().parents[2]
NATIVE = ROOT / "docs/receipts/plan-build-native-2026-09-18"
PREP = ROOT / "docs/receipts/plan-build-task8-2026-09-18"
SPEC = importlib.util.spec_from_file_location(
    "worker_evaluator", ROOT / "experiments/plan_build/evaluate_worker.py"
)
evaluator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluator)


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def no_native(*args, **kwargs):
    raise AssertionError("Local correction attempted a native call")


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    for name, expected in read(NATIVE / "manifest.json")["sha256"].items():
        assert hashlib.sha256((NATIVE / name).read_bytes()).hexdigest() == expected
    requests = {
        role: read(PREP / f"{kind}-record.json")["request"]
        for role, kind in [("planner", "plan"), ("worker", "build")]
    }
    rows = []
    with patch.object(review_participants, "NativeExchange", no_native):
        for sample in sorted((NATIVE / "blind").glob("*.json")):
            packet = read(sample)
            payload = copy.deepcopy(packet["payload"])
            role = packet["role"]
            row = {
                "sample": sample.stem,
                "role": role,
                "original_schema_valid": packet["schema_valid"],
                "fresh_native_response": False,
            }
            if role == "worker":
                row["diagnostic_projection"] = (
                    "Keep file proposals byte-identical; explicitly project to the new files-only response. This is not an originally valid or newly generated native response."
                )
                row["removed_control_fields"] = {
                    k: v for k, v in payload.items() if k != "files"
                }
                projected = {"schema_version": 2, "files": payload["files"]}
                source = output / "projected" / sample.name
                write(
                    source,
                    {"payload": projected, "diagnostic": row["diagnostic_projection"]},
                )
                request = requests[role]
                decoded = work_build.decode(
                    {"kind": "final", "text": canonical(projected)},
                    request,
                    role,
                    request["tasks"][0],
                    contract_version=2,
                )
                assert decoded["files"] == payload["files"]
                result = evaluator.evaluate(source, output / "artifacts" / sample.stem)
                row.update(
                    status=result["status"],
                    protected_inputs_preserved=result["protected_inputs_preserved"],
                    stale_handoff_rejected=bool(result["stale_handoff_rejected"]),
                )
            else:
                row["diagnostic_projection"] = (
                    "Unchanged native plan interpreted under response contract 2; criteria become host-bound checks only on staging."
                )
                try:
                    work_runtime.validate_reply(
                        payload, requests[role], role, contract_version=2
                    )
                except ValueError as error:
                    row.update(status="rejected", error=str(error))
                else:
                    scratch = (
                        Path(
                            tempfile.mkdtemp(
                                prefix="plan-contract-replay-", dir="/private/tmp"
                            )
                        )
                        / "prepared"
                    )
                    evaluator.comparison.prepare(scratch)
                    directory = scratch / "plan-work"

                    class Retained:
                        last_identity = {"adapter": "retained-local-fixture"}

                        def __init__(self, *args, **kwargs):
                            pass

                        def __call__(self, raw):
                            request = json.loads(raw)
                            return canonical(
                                {
                                    "schema_version": 1,
                                    "request_digest": request["request_digest"],
                                    "action": {
                                        "kind": "final",
                                        "text": canonical(payload),
                                    },
                                }
                            )

                    result = work_runtime.plan_work(
                        directory, exchange_factory=Retained
                    )
                    assert result["planning"]["status"] == "completed", result[
                        "planning"
                    ].get("error")
                    staged = work_runtime.apply_planning_proposal(
                        directory, checkpoint=result["checkpoint_digest"]
                    )
                    assert staged["acceptance"] is None and staged["status"] == "draft"
                    assert staged == read_task(directory)
                    assert (
                        staged["history"][-1]["planning"]["participants"]["planner"][
                            "proposal"
                        ]
                        == payload
                    )
                    by_id = {t["id"]: t for t in staged["request"]["tasks"]}
                    assert all(
                        c["criterion"] in by_id[t]["checks"]
                        for c in payload["coverage"]
                        for t in c["tasks"]
                    )
                    write(output / "plans" / (sample.stem + "-staged.json"), staged)
                    (
                        scratch / "checkout" / evaluator.comparison.DOCUMENTATION
                    ).write_text("# Changed after planning\n")
                    try:
                        work_runtime.apply_planning_proposal(
                            directory, checkpoint=result["checkpoint_digest"]
                        )
                    except ValueError:
                        pass
                    else:
                        raise AssertionError("Stale planning decision reused")
                    row.update(
                        status="staged-draft",
                        original_reply_preserved=True,
                        no_acceptance_granted=True,
                    )
            rows.append(row)
    summary = {
        "native_calls": 0,
        "method": "Offline diagnostic projections, not a fresh native quality result",
        "source_unchanged": True,
        "rows": rows,
        "plans_staged": sum(r["status"] == "staged-draft" for r in rows),
        "workers_passed": sum(r["status"] == "completed" for r in rows),
        "workers_failed_oracle": sum(r["status"] == "needs_revision" for r in rows),
    }
    assert (
        summary["plans_staged"],
        summary["workers_passed"],
        summary["workers_failed_oracle"],
    ) == (8, 9, 3)
    write(output / "result.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
