"""Execute the explicitly allocated correction using existing metering/contracts."""

import argparse
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "assessment_correction", Path(__file__).with_name("correction.py")
)
correction = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(correction)
base, repair = correction.base, correction.repair


def load_prepared(folder):
    p = base.read(folder / "proposal.json")
    if any(
        base.file_hash(folder / name) != sha
        for name, sha in base.read(folder / "manifest.json")["sha256"].items()
    ):
        raise ValueError("Prepared evidence changed")
    if any(base.file_hash(base.ROOT / name) != sha for name, sha in p["files"].items()):
        raise ValueError("Prepared contract or code changed")
    if (
        base.helpers.modules() != p["modules"]
        or base.file_hash(p["wheel"]) != p["wheel_sha256"]
    ):
        raise ValueError("Installed profile changed")
    correction.check_retained(Path(p["parent"]))
    return p


def prepare(folder, output, approval):
    p = load_prepared(folder)
    if (
        approval.get("proposal_sha256") != base.digest(p)
        or approval.get("allocation") != p["proposed_allocation"]
        or approval.get("answer") != "A — Run the bounded comparison (Recommended)"
    ):
        raise ValueError("Explicit allocation does not match the prepared comparison")
    p.update(
        prepared=str(folder),
        prepared_sha256=base.digest(p),
        authorization=approval,
        rates=base.RATES,
        reservations=base.RESERVATIONS,
        budget_credits=p["proposed_allocation"]["codex_credit_planning_ceiling"],
        max_calls=p["proposed_allocation"]["max_calls"],
        max_calls_by_model=p["proposed_allocation"]["max_calls_by_model"],
        grader_rule=p["fixture"]["grader_rule"],
        status="allocated; no production promotion",
    )
    p["files"][str(Path(__file__).relative_to(base.ROOT))] = base.file_hash(__file__)
    output.mkdir(parents=True, exist_ok=False)
    base.write(output / "protocol.json", p)
    base.write(
        output / "admission.json",
        {"protocol_sha256": base.digest(p), "authorization": approval},
    )
    return p


def verify(output):
    p = base.verify(output)
    if base.digest(load_prepared(Path(p["prepared"]))) != p["prepared_sha256"]:
        raise ValueError("Prepared comparison differs from allocation")
    return p


def items(p, ledger, output, batch):
    rows = {r["id"]: r for r in ledger["assessments"]}
    trials = {r["id"]: r for r in p["trials"]}
    cases = {c["id"]: c for c in p["fixture"]["cases"]}
    return [
        repair.supplied_item(output, rows[i], cases[trials[i]["case"]])
        for i in batch["samples"]
    ] + correction.controls(p["fixture"])


def execute(output, phase):
    from attune_harness import Task
    from attune_harness.adapters import Attempt, JsonParticipant

    p = verify(output)
    path = output / "ledger.json"
    if phase == "assess":
        if path.exists():
            raise ValueError("Existing ledger; no automatic replay")
        ledger = {
            "protocol_sha256": base.digest(p),
            "status": "assessing",
            "calls": [],
            "assessments": [],
            "grades": [],
            "batches": [],
            "billed_dollars": None,
            "human_grading": None,
        }
    elif phase == "grade":
        ledger = base.read(path)
        if (
            ledger["status"] != "awaiting_grading"
            or ledger["batches"]
            or len(ledger["assessments"]) != len(p["trials"])
        ):
            raise ValueError(
                "Grading requires completed assessments and no prior grade dispatch"
            )
        base.audit(output)  # Bind all retained requests/results/usage before grading.
        ledger.update(
            status="grading",
            lead_review_sha256=base.file_hash(output / "lead-review.json"),
        )
    else:
        raise ValueError("Unknown phase")
    base.subscription_environment()
    base.write(path, ledger)
    meter = base.Meter(output, p, ledger)
    try:
        if phase == "assess":
            for row in p["trials"]:
                case = next(c for c in p["fixture"]["cases"] if c["id"] == row["case"])
                text = base.assessment(
                    p, row, output / "runs" / row["id"], meter.factory(row["id"], case)
                )
                ledger["assessments"].append(
                    {
                        "id": row["id"],
                        "text": text,
                        "result_sha256": base.file_hash(
                            output / "runs" / row["id"] / "result.json"
                        ),
                    }
                )
                base.write(path, ledger)
                print(
                    json.dumps(
                        {
                            "phase": phase,
                            "done": len(ledger["assessments"]),
                            "total": len(p["trials"]),
                        }
                    ),
                    flush=True,
                )
            ledger["status"] = "awaiting_grading"
        else:
            for batch in p["grading_batches"]:
                verify(output)
                if (
                    base.file_hash(output / "lead-review.json")
                    != ledger["lead_review_sha256"]
                ):
                    raise ValueError("Frozen lead review changed")
                packet = items(p, ledger, output, batch)
                config = p["profiles"][batch["profile"]]
                task = Task(batch["id"], json.dumps(packet), (p["grader_rule"],))
                attempt = Attempt(
                    task,
                    batch["id"],
                    base.digest(packet),
                    "independent-grader",
                    "reviewer",
                    "assessment-correction-v2",
                )
                work = output / "grading-work" / batch["id"]
                work.mkdir(parents=True, exist_ok=False)
                base.write(work / "items.json", packet)
                native = meter.native(
                    batch["id"],
                    config["adapter"],
                    cwd=work,
                    model=config["model"],
                    timeout=config["timeout"],
                    **{
                        k: config[k]
                        for k in ("reasoning_effort", "skills_context_tokens")
                        if k in config
                    },
                )
                text = JsonParticipant(attempt, native).run(task).text
                base.write(
                    work / "reply.json",
                    {"text": text, "identity": asdict(native.identity)},
                )
                grades = correction.decode_grades(text, batch["samples"], p["fixture"])
                ledger["batches"].append(
                    {
                        "id": batch["id"],
                        "items_sha256": base.digest(packet),
                        "grades": grades,
                    }
                )
                base.write(path, ledger)
                print(
                    json.dumps(
                        {
                            "phase": phase,
                            "done": len(ledger["batches"]),
                            "total": len(p["grading_batches"]),
                            "controls_pass": all(
                                g["controls_pass"] for g in grades.values()
                            ),
                        }
                    ),
                    flush=True,
                )
            ledger["status"] = "completed"
        costs = [
            c["estimated_credits"] for c in ledger["calls"] if c["adapter"] == "codex"
        ]
        if any(c is None for c in costs) or sum(costs) > p["budget_credits"]:
            raise ValueError("Incomplete or over-budget accounting")
    except BaseException as exc:
        ledger.update(
            status="stopped", error={"type": type(exc).__name__, "detail": str(exc)}
        )
        raise
    finally:
        base.write(path, ledger)


def audit(output):
    from attune_harness.native import decode_claude, decode_codex

    p, ledger = verify(output), base.read(output / "ledger.json")
    # Reuse raw/request/result/usage binding; ignore the old eight-case grading floor.
    common = base.audit(output)
    if (
        ledger.get("lead_review_sha256")
        and base.file_hash(output / "lead-review.json") != ledger["lead_review_sha256"]
    ):
        raise ValueError("Frozen lead review changed")
    grades = {}
    for row in ledger["batches"]:
        batch = next(b for b in p["grading_batches"] if b["id"] == row["id"])
        packet = items(p, ledger, output, batch)
        envelope = base.read(output / "calls" / row["id"] / "request.json")
        task = json.loads(envelope["prompt"].split("\n", 1)[1])["attempt"]["task"]
        if (
            json.loads(task["objective"]) != packet
            or task["requirements"] != [p["grader_rule"]]
            or base.digest(packet) != row["items_sha256"]
        ):
            raise ValueError("Grader evidence or rubric differs from frozen protocol")
        config = p["profiles"][batch["profile"]]
        call = next(c for c in ledger["calls"] if c["id"] == row["id"])
        if call["adapter"] != config["adapter"] or call["model"] != config["model"]:
            raise ValueError("Grader profile differs from frozen protocol")
        raw = base.read(output / "calls" / row["id"] / "raw.json")
        decoder = decode_claude if config["adapter"] == "claude" else decode_codex
        decoded = correction.decode_grades(
            decoder(raw["stdout"])[0], batch["samples"], p["fixture"]
        )
        if decoded != row["grades"] or set(grades) & set(decoded):
            raise ValueError("Grades differ or duplicate samples")
        grades.update(decoded)
    groups = {}
    for family in ("claude", "codex"):
        for arm in ("baseline", "candidate"):
            selected = [
                grades[t["id"]]["sample"]
                for t in p["trials"]
                if t["family"] == family and t["arm"] == arm and t["id"] in grades
            ]
            groups[family + "-" + arm] = {
                "graded": len(selected),
                "correct": sum(g["correct"] for g in selected),
                "critical_misses": sum(g["critical_miss"] for g in selected),
                "unsupported_findings": sum(
                    len(g["unsupported_findings"]) for g in selected
                ),
            }
    regressions = []
    for family in ("claude", "codex"):
        for case in p["fixture"]["cases"]:
            pair = {
                t["arm"]: grades[t["id"]]["sample"]["correct"]
                for t in p["trials"]
                if t["family"] == family
                and t["case"] == case["id"]
                and t["id"] in grades
            }
            if pair.get("baseline") is True and pair.get("candidate") is False:
                regressions.append({"family": family, "case": case["id"]})
    passed_controls = sum(
        all(g["controls_pass"] for g in row["grades"].values())
        for row in ledger["batches"]
    )
    passed = (
        ledger["status"] == "completed"
        and len(grades) == 16
        and passed_controls == 8
        and not regressions
        and all(
            g["correct"] == 4
            for name, g in groups.items()
            if name.endswith("candidate")
        )
    )
    result = {
        "execution": ledger["status"],
        "calls": common["calls"],
        "estimated_codex_credits": common["estimated_codex_credits"],
        "previous_calls": p["previous_allocation"]["calls_used"],
        "previous_estimated_codex_credits": p["previous_allocation"][
            "estimated_codex_credits"
        ],
        "groups": groups,
        "controls_passed_by_batch": passed_controls,
        "graded_outputs": len(grades),
        "regressions": regressions,
        "model_grading_floor": (
            "met_pending_lead_reconciliation" if passed else "revise_or_arbitrate"
        ),
        "promotion": "not_authorized",
        "billed_dollars": None,
        "human_grading": None,
    }
    base.write(output / "audit.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "assess", "grade", "audit"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--prepared", type=Path)
    parser.add_argument("--approval", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if args.command == "prepare":
        if args.prepared is None or args.approval is None:
            parser.error("prepare requires --prepared and --approval")
        print(
            base.digest(
                prepare(args.prepared.resolve(), output, base.read(args.approval))
            )
        )
    elif args.command == "audit":
        print(json.dumps(audit(output), indent=2))
    else:
        execute(output, args.command)
