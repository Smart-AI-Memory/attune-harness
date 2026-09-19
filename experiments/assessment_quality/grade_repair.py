"""Grading-only amendment; preserve and charge every original native call."""

import argparse
import copy
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "quality_trial", Path(__file__).with_name("trial.py")
)
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)
read, write, digest = base.read, base.write, base.digest


def supplied_item(parent, row, case):
    """Use assessor-visible evidence, omitting objective/criteria that reveal arm."""
    envelope = read(parent / "calls" / row["id"] / "request.json")
    native = json.loads(envelope["prompt"].split("\n", 1)[1])
    evidence = json.loads(native["attempt"]["task"]["objective"])
    expected_document = (
        case["document"] + "\n\n[Cedar reference](references/cedar-source.md)\n"
    )
    if evidence["document"]["text"] != expected_document:
        raise ValueError("Retained document differs from frozen case")
    refs = evidence["references"]
    if len(refs) != 1 or refs[0]["text"] != base.reference(case):
        raise ValueError("Retained reference differs from frozen case")
    if not evidence["limited_tool_checks"]:
        raise ValueError("Missing retained host-check context")
    return {
        "id": row["id"],
        "document": {"path": "guide.md", "text": expected_document},
        "references": refs,
        "limited_tool_checks": evidence["limited_tool_checks"],
        "judgment_scope": evidence["judgment_scope"],
        "requirements": case["requirements"],
        "assessment": row["text"],
    }


def pair_rows(trials, family):
    remaining = sorted(
        (t for t in trials if t["family"] == family), key=lambda t: (t["case"], t["id"])
    )
    pairs = []
    while remaining:
        first = remaining.pop(0)
        index = next(i for i, t in enumerate(remaining) if t["case"] != first["case"])
        pairs.append([first, remaining.pop(index)])
    return pairs


def prepare(parent, output):
    protocol = base.verify(parent)
    base.audit(parent)  # Bind original raw/request/result/grade/usage receipts first.
    ledger = read(parent / "ledger.json")
    if len(ledger["assessments"]) != 32 or any(
        c["state"] != "observed" for c in ledger["calls"]
    ):
        raise ValueError("Need complete assessments and reconciled original calls")
    rows = {r["id"]: r for r in ledger["assessments"]}
    cases = {c["id"]: c for c in protocol["fixture"]["cases"]}
    batches = []
    for family in ("claude", "codex"):
        for pair in pair_rows(protocol["trials"], family):
            samples = [
                supplied_item(parent, rows[t["id"]], cases[t["case"]]) for t in pair
            ]
            controls = base.grade_items(cases[pair[0]["case"]], "unused")[1:]
            batches.append(
                {
                    "id": f"r{len(batches) + 1:02d}",
                    "profile": protocol["grader_for"][family],
                    "samples": samples,
                    "items": samples + controls,
                }
            )
    amended = copy.deepcopy(protocol)
    amended.update(
        parent=str(parent),
        parent_ledger_sha256=base.file_hash(parent / "ledger.json"),
        inherited_calls_sha256=digest(ledger["calls"]),
        inherited_calls=len(ledger["calls"]),
        batches=batches,
        amendment="Complete assessor-visible evidence; two distinct cases per independent grader call. Initial 11 grades excluded.",
    )
    amended["files"][str(Path(__file__).relative_to(base.ROOT))] = base.file_hash(
        __file__
    )
    amended["grader_rule"] += (
        " Some items include full document text, source paths/hashes and limited host checks. "
        "Those are supplied evidence, not invented by the assessment. Attribute each tool claim "
        "only to the checks actually shown. Grade each item separately; do not compare items "
        "or infer which are controls. No earlier grades or assessment instructions are supplied."
    )
    if len(ledger["calls"]) + len(batches) > amended["max_calls"]:
        raise ValueError("Amendment exceeds original call ceiling")
    for name, maximum in amended["max_calls_by_model"].items():
        planned = sum(c["model"] == name for c in ledger["calls"]) + sum(
            amended["profiles"][b["profile"]]["model"] == name for b in batches
        )
        if planned > maximum:
            raise ValueError("Amendment exceeds original model allocation")
    output.mkdir(parents=True, exist_ok=False)
    write(output / "protocol.json", amended)
    write(
        output / "admission.json",
        {"protocol_sha256": digest(amended), "authorization": amended["authorization"]},
    )
    return amended


def verify(output):
    p = base.verify(output)
    parent = Path(p["parent"])
    base.verify(parent)
    if base.file_hash(parent / "ledger.json") != p["parent_ledger_sha256"]:
        raise ValueError("Original ledger changed")
    return p


def decode(text, ids):
    from attune_harness.review_contract import parse_json

    value = parse_json(text, 32768)
    if (
        not isinstance(value, dict)
        or set(value) != {"grades"}
        or not isinstance(value["grades"], list)
    ):
        raise ValueError("Invalid amended grade envelope")
    rows = value["grades"]
    if len(rows) != len(ids) + 3 or {r.get("id") for r in rows} != set(ids) | {
        "v1",
        "v2",
        "v3",
    }:
        raise ValueError("Missing/duplicate/extra amended grade identities")
    controls = [r for r in rows if r["id"] in {"v1", "v2", "v3"}]
    result = {}
    for ident in ids:
        row = next(r for r in rows if r["id"] == ident)
        normalized = {**row, "id": "sample"}
        parsed = base.decode_grade(json.dumps({"grades": [normalized] + controls}))
        result[ident] = {"sample": row, "controls_pass": base.controls_pass(parsed)}
    return result


def execute(output):
    from attune_harness import Task
    from attune_harness.adapters import Attempt, JsonParticipant

    p = verify(output)
    if (output / "ledger.json").exists():
        raise ValueError("Existing amended ledger; no automatic replay")
    original = read(Path(p["parent"]) / "ledger.json")
    ledger = {
        "protocol_sha256": digest(p),
        "status": "running",
        "calls": copy.deepcopy(original["calls"]),
        "batches": [],
        "inherited_calls": p["inherited_calls"],
        "billed_dollars": None,
    }
    write(output / "ledger.json", ledger)
    meter = base.Meter(output, p, ledger)
    try:
        for batch in p["batches"]:
            verify(output)
            if (
                digest(ledger["calls"][: p["inherited_calls"]])
                != p["inherited_calls_sha256"]
            ):
                raise ValueError("Inherited accounting changed")
            config = p["profiles"][batch["profile"]]
            task = Task(batch["id"], json.dumps(batch["items"]), (p["grader_rule"],))
            attempt = Attempt(
                task,
                batch["id"],
                digest(batch["items"]),
                "independent-grader",
                "reviewer",
                "assessment-quality-grading-amendment-v1",
            )
            work = output / "work" / batch["id"]
            work.mkdir(parents=True, exist_ok=False)
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
            write(
                work / "reply.json", {"text": text, "identity": asdict(native.identity)}
            )
            grades = decode(text, [s["id"] for s in batch["samples"]])
            ledger["batches"].append({"id": batch["id"], "grades": grades})
            write(output / "ledger.json", ledger)
            print(
                json.dumps(
                    {
                        "amended_grading_batches": len(ledger["batches"]),
                        "total": 16,
                        "controls_pass": all(
                            g["controls_pass"] for g in grades.values()
                        ),
                    }
                ),
                flush=True,
            )
        costs = [
            c["estimated_credits"] for c in ledger["calls"] if c["adapter"] == "codex"
        ]
        if any(c is None for c in costs) or sum(costs) > p["budget_credits"]:
            raise ValueError("Incomplete or over-budget final accounting")
        ledger["status"] = "completed"
    except BaseException as exc:
        ledger.update(
            status="stopped", error={"type": type(exc).__name__, "detail": str(exc)}
        )
        raise
    finally:
        write(output / "ledger.json", ledger)


def audit(output):
    from attune_harness.native import decode_claude, decode_codex

    p, ledger = verify(output), read(output / "ledger.json")
    if (
        ledger["protocol_sha256"] != digest(p)
        or digest(ledger["calls"][: p["inherited_calls"]])
        != p["inherited_calls_sha256"]
    ):
        raise ValueError("Amended accounting/protocol changed")
    base.audit(Path(p["parent"]))
    grades = {}
    for batch in ledger["batches"]:
        frozen = next(b for b in p["batches"] if b["id"] == batch["id"])
        call = next(c for c in ledger["calls"] if c["id"] == batch["id"])
        raw = read(output / "calls" / call["id"] / "raw.json")
        request = read(output / "calls" / call["id"] / "request.json")
        if (
            digest(raw) != call["raw_sha256"]
            or base.hashlib.sha256(request["prompt"].encode()).hexdigest()
            != call["request_sha256"]
        ):
            raise ValueError("Amended native receipt changed")
        native_request = json.loads(request["prompt"].split("\n", 1)[1])
        if (
            json.loads(native_request["attempt"]["task"]["objective"])
            != frozen["items"]
        ):
            raise ValueError("Grader did not receive frozen evidence")
        usage = base.helpers.native_usage(call["adapter"], raw["stdout"])
        if (
            usage != call["usage"]
            or base.estimate(call["model"], usage) != call["estimated_credits"]
        ):
            raise ValueError("Amended usage differs from raw evidence")
        decoder = decode_claude if call["adapter"] == "claude" else decode_codex
        decoded = decode(
            decoder(raw["stdout"])[0], [s["id"] for s in frozen["samples"]]
        )
        if decoded != batch["grades"] or set(decoded) & set(grades):
            raise ValueError("Amended grades differ or duplicate samples")
        grades.update(decoded)
    groups, regressions = {}, []
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
        for case in p["fixture"]["cases"]:
            pair = {
                t["arm"]: grades[t["id"]]["sample"]
                for t in p["trials"]
                if t["family"] == family
                and t["case"] == case["id"]
                and t["id"] in grades
            }
            if (
                len(pair) == 2
                and pair["baseline"]["correct"]
                and not pair["candidate"]["correct"]
            ):
                regressions.append({"family": family, "case": case["id"]})
    costs = [c["estimated_credits"] for c in ledger["calls"] if c["adapter"] == "codex"]
    result = {
        "execution": ledger["status"],
        "total_calls": len(ledger["calls"]),
        "discarded_initial_grading_calls": p["inherited_calls"] - 32,
        "amended_grading_calls": len(ledger["batches"]),
        "graded_outputs": len(grades),
        "estimated_codex_credits_including_discarded_grades": (
            round(sum(costs), 6) if all(c is not None for c in costs) else None
        ),
        "groups": groups,
        "regressions": regressions,
        "controls_passed_by_batch": sum(
            all(g["controls_pass"] for g in b["grades"].values())
            for b in ledger["batches"]
        ),
        "billed_dollars": None,
        "human_grading": None,
        "promotion": "not_authorized",
    }
    passed = (
        ledger["status"] == "completed"
        and len(grades) == 32
        and result["controls_passed_by_batch"] == 16
        and not regressions
        and all(
            v["correct"] == 8
            and v["critical_misses"] == 0
            and v["unsupported_findings"] == 0
            for k, v in groups.items()
            if k.endswith("candidate")
        )
    )
    result["model_grading_floor"] = (
        "met_pending_assistant_audit" if passed else "revise_or_arbitrate"
    )
    write(output / "audit.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "execute", "audit"))
    parser.add_argument("parent", type=Path)
    args = parser.parse_args()
    parent = args.parent.resolve()
    output = parent / "grading-amendment"
    if args.command == "prepare":
        print(digest(prepare(parent, output)))
    elif args.command == "execute":
        execute(output)
    else:
        print(json.dumps(audit(output), indent=2))
