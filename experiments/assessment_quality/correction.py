"""Offline correction rehearsal and live proposal only; no dispatch entry point."""

import argparse
import copy
import importlib.util
import json
from pathlib import Path
import random
import statistics
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "retained_grade_repair", Path(__file__).with_name("grade_repair.py")
)
repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair)
base = repair.base
FIXTURE = Path(__file__).with_name("correction_v2.json")
INJECTED = "Offline injected response. No model reasoning was performed."


def controls(fixture):
    legacy = base.grade_items(fixture["cases"][0], "unused")[1:]
    return legacy + [
        {k: v for k, v in row.items() if k != "expected"}
        for row in fixture["disposition_controls"]
    ]


def decode_grades(text, sample_ids, fixture):
    expected = {c["id"]: c["expected"] for c in fixture["disposition_controls"]}
    if (
        not sample_ids
        or len(set(sample_ids)) != len(sample_ids)
        or set(sample_ids) & (set(expected) | {"v1", "v2", "v3"})
    ):
        raise ValueError("Invalid sample identities")
    decoded = repair.decode(text, list(sample_ids) + list(expected))
    passed = all(row["controls_pass"] for row in decoded.values()) and all(
        all(
            (
                bool(decoded[ident]["sample"][key])
                if key in ("unsupported_findings", "missed_defects")
                else decoded[ident]["sample"][key]
            )
            == value
            for key, value in fields.items()
        )
        for ident, fields in expected.items()
    )
    return {
        ident: {"sample": decoded[ident]["sample"], "controls_pass": passed}
        for ident in sample_ids
    }


def check_retained(parent):
    base.verify(parent)
    repair.verify(parent / "grading-amendment")
    hashes = base.read(parent / "manifest.json")["sha256"]
    if any(base.file_hash(parent / name) != sha for name, sha in hashes.items()):
        raise ValueError("Retained experiment evidence changed")
    return len(hashes)


def proposal(parent):
    retained = check_retained(parent)
    old = base.read(parent / "protocol.json")
    fixture = base.read(FIXTURE)
    if fixture["baseline"] != old["fixture"]["baseline"]:
        raise ValueError("Baseline must stay unchanged")
    trials = [
        {"case": c["id"], "family": family, "arm": arm}
        for c in fixture["cases"]
        for family in ("claude", "codex")
        for arm in ("baseline", "candidate")
    ]
    random.Random(1709202602).shuffle(trials)
    for n, row in enumerate(trials, 1):
        row["id"] = f"a{n:02d}"
    batches = [
        {"profile": old["grader_for"][family], "samples": [r["id"] for r in pair]}
        for family in ("claude", "codex")
        for pair in repair.pair_rows(trials, family)
    ]
    for n, row in enumerate(batches, 1):
        row["id"] = f"g{n:02d}"
    ledger = base.read(parent / "grading-amendment/ledger.json")
    codex_costs = [
        c["estimated_credits"] for c in ledger["calls"] if c["model"] in base.RATES
    ]
    if any(type(value) not in (int, float) or value < 0 for value in codex_costs):
        raise ValueError("Unknown retained Codex credit usage")
    # Match prior assessor calls and corrected two-sample grading calls separately.
    medians = {
        model: statistics.median(
            c["estimated_credits"]
            for c in ledger["calls"]
            if c["model"] == model and c["id"].startswith(prefix)
        )
        for model, prefix in (("gpt-6-astra", "a"), ("gpt-5.6-sol", "r"))
    }
    return {
        "schema_version": 2,
        "status": "proposal_only; no live allocation or admission",
        "fixture": fixture,
        "profiles": old["profiles"],
        "trials": trials,
        "grading_batches": batches,
        "proposed_allocation": {
            "max_calls": 24,
            "max_calls_by_model": {
                "gpt-6-astra": 8,
                "gpt-5.6-sol": 4,
                "claude-fable-5-1": 12,
            },
            "expected_codex_credits": [45, 65],
            "codex_credit_planning_ceiling": 100,
            "empirical_median_credits_by_model": medians,
            "empirical_point_estimate": 8 * medians["gpt-6-astra"]
            + 4 * medians["gpt-5.6-sol"],
            "estimate_limits": "Historical standard-tier token estimates, not billing. Extra controls, cache and response length can change cost. Admission reservations are not provider hard caps.",
            "claude_route": "existing Max subscription",
            "new_api_dollars": 0,
        },
        "previous_allocation": {
            "calls_used": len(ledger["calls"]),
            "estimated_codex_credits": sum(codex_costs),
            "reason_new_allocation_needed": "Original Astra slots exhausted (16/16); original total and per-model ceilings still bind.",
        },
        "quality_floor": "Every candidate assessment correct; no unsupported allegations or missing required corrections; no matched regression in either family; every grader control passes. Retain disagreements for lead review. No automatic production promotion.",
        "parent": str(parent),
        "retained_files_checked": retained,
        "parent_manifest_sha256": base.file_hash(parent / "manifest.json"),
        "wheel": old["wheel"],
        "wheel_sha256": old["wheel_sha256"],
        "modules": old["modules"],
        "files": {
            **old["files"],
            **{
                str(p.relative_to(base.ROOT)): base.file_hash(p)
                for p in (Path(__file__), FIXTURE, Path(repair.__file__))
            },
        },
    }


def rehearse_assessment(protocol, row, output):
    from attune_harness import review_participants
    from attune_harness.native import NativeExchange
    from attune_harness.process import ProcessResult

    requests = []

    def runner(argv, prompt, **options):
        requests.append(prompt)
        path = output / "calls" / row["id"]
        path.mkdir(parents=True, exist_ok=False)
        base.write(
            path / "request.json",
            {"mode": "offline injected response", "argv": list(argv), "prompt": prompt},
        )
        if argv[0] == "claude":
            response = json.dumps(
                {
                    "type": "result",
                    "subtype": "success",
                    "is_error": False,
                    "session_id": "offline",
                    "structured_output": {"text": INJECTED},
                    "modelUsage": {},
                }
            )
        else:
            response = "\n".join(
                json.dumps(event)
                for event in [
                    {"type": "thread.started", "thread_id": "offline"},
                    {"type": "turn.started"},
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "agent_message",
                            "text": json.dumps({"text": INJECTED}),
                        },
                    },
                    {"type": "turn.completed"},
                ]
            )
        return ProcessResult(argv, 0, response, "")

    class Offline(review_participants.ReviewExchange):
        def __call__(self, raw):
            with patch.object(
                review_participants,
                "NativeExchange",
                lambda adapter, **kw: NativeExchange(adapter, runner=runner, **kw),
            ):
                return super().__call__(raw)

    with patch(
        "subprocess.Popen",
        side_effect=AssertionError("Offline rehearsal attempted process dispatch"),
    ):
        text = base.assessment(protocol, row, output / "runs" / row["id"], Offline)
    if len(requests) != 1:
        raise ValueError("Expected exactly one intercepted assessment request")
    case = next(c for c in protocol["fixture"]["cases"] if c["id"] == row["case"])
    evidence = json.loads(
        json.loads(requests[0].split("\n", 1)[1])["attempt"]["task"]["objective"]
    )
    if protocol["fixture"][row["arm"]] not in evidence["objective"]:
        raise ValueError("Assessment instruction did not reach native projection")
    return repair.supplied_item(output, {"id": row["id"], "text": text}, case)


def prepare(output, parent):
    plan = proposal(parent)
    output.mkdir(parents=True, exist_ok=False)
    base.write(output / "proposal.json", plan)
    offline = output / "offline"
    samples = {
        row["id"]: rehearse_assessment(plan, row, offline) for row in plan["trials"]
    }
    batches = [
        {
            "id": b["id"],
            "items": [samples[i] for i in b["samples"]] + controls(plan["fixture"]),
        }
        for b in plan["grading_batches"]
    ]
    base.write(
        output / "offline-grading-packets.json",
        {
            "mode": "offline injected responses; no model quality measured",
            "rule": plan["fixture"]["grader_rule"],
            "batches": batches,
        },
    )
    development = copy.deepcopy(plan)
    development["fixture"]["cases"] = base.read(parent / "protocol.json")["fixture"][
        "cases"
    ]
    old_count = 0
    for case in development["fixture"]["cases"]:
        for family in ("claude", "codex"):
            old_count += 1
            row = {
                "id": f"s{old_count:02d}",
                "case": case["id"],
                "family": family,
                "arm": "candidate",
            }
            rehearse_assessment(development, row, offline)
    report = {
        "mode": "offline software checks only; semantic quality unmeasured",
        "proposal_sha256": base.digest(plan),
        "fresh_case_transport_runs": len(samples),
        "retained_case_transport_runs": old_count,
        "grading_packets": len(batches),
        "controls_per_packet": len(controls(plan["fixture"])),
        "original_files_unchanged": check_retained(parent),
        "provider_calls": 0,
    }
    base.write(output / "offline-result.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--parent",
        type=Path,
        default=base.ROOT / "docs/receipts/assessment-quality-2026-09-17",
    )
    args = parser.parse_args()
    print(json.dumps(prepare(args.output.resolve(), args.parent.resolve()), indent=2))
