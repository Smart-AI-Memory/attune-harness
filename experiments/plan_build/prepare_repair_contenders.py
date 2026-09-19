"""Prepare an expanded Luna/Sol screen using existing repair owners; offline only."""

import copy
import importlib.util
from pathlib import Path
import random
import shutil
import tempfile
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "repair_screen", HERE / "repair_models.py"
)
screen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screen)
ROOT = screen.ROOT
BASE = ROOT / "docs/receipts/plan-build-repair-model-preparation-2026-09-18"
OUT = ROOT / "docs/receipts/plan-build-repair-contenders-preparation-2026-09-18"
MODELS = ("gpt-5.6-luna", "gpt-5.6-sol")
EXPORT, CLI, TEST = screen.EXPORT, screen.CLI, screen.TEST
BAD, GOOD = screen.prior.BAD, screen.prior.GOOD
NEW = [
    (
        "empty-output",
        EXPORT,
        "Repair JSONL output for an empty document: it must contain one unknown header and a final newline. Preserve populated output and all metadata. Only the exporter may change.",
        [
            (
                '    findings = receipt.pop("findings")\n',
                '    findings = receipt.pop("findings")\n    if not findings:\n        return ""\n',
            )
        ],
    ),
    (
        "status-precedence",
        CLI,
        "Repair the aggregate documentation status: refuted findings must take precedence over unknown and verified findings. Preserve evidence, uncertainty and exact default output for unaffected inputs. Only documentation.py may change.",
        [("            return 'refuted'", "            return 'unknown'")],
    ),
    (
        "finding-envelope",
        EXPORT,
        "Repair finding records so each has schema_version 1, kind finding and the complete finding nested under finding. Preserve header, order, evidence, notes and final newline. Only the exporter may change.",
        [
            (
                '{"schema_version": 1, "kind": "finding", "finding": finding}',
                '{"schema_version": 1, "kind": "finding", **finding}',
            )
        ],
    ),
    (
        "header-data-loss",
        EXPORT,
        "Repair both observed header metadata losses: retain the exact source evidence and advisory reviewer notes from the document. Preserve findings, order and all other output. Only the exporter may change.",
        [
            (
                '    findings = receipt.pop("findings")\n',
                '    findings = receipt.pop("findings")\n    receipt["sources"] = []\n',
            ),
            (
                '    receipt["kind"] = "documentation-header"',
                '    receipt["reviewer_notes"] = None\n    receipt["kind"] = "documentation-header"',
            ),
        ],
    ),
    (
        "default-and-punctuation",
        CLI,
        "Repair both default-format selection and default Markdown punctuation regressions. Without --format, output must match captured legacy JSON/Markdown bytes; explicit JSONL must remain supported. Preserve other behavior. Only documentation.py may change.",
        [
            (
                "choices=('json', 'jsonl'), default='json'",
                "choices=('json', 'jsonl'), default='jsonl'",
            ),
            ("\\u2014", "-"),
        ],
    ),
    (
        "two-test-assertions",
        TEST,
        "Repair both failing supplemental assertions using the documented JSONL envelope and empty-input behavior. Retain all four test methods and assertion coverage; fix expected values or access paths only where contradicted by that contract. Exporter, CLI and protected tests must remain unchanged.",
        [
            (GOOD, BAD),
            ("self.assertEqual(len(records), 1)", "self.assertEqual(len(records), 2)"),
        ],
    ),
]


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError(f"Mutation anchor is not unique: {before!r}")
    return text.replace(before, after)


def clearance(payload):
    return {
        "payload_digest": screen.digest(payload),
        "inspected_before_execution": True,
        "safe_to_execute": True,
        "semantic_passed": True,
        "method": "Locally constructed known reference/partial repair; not a native grade.",
    }


def prepare():
    # Refuse to overwrite any receipt or reuse an already prepared campaign.
    OUT.mkdir(parents=True, exist_ok=False)
    prior = {
        str(p.relative_to(ROOT)): screen.sha(p)
        for p in sorted((ROOT / "docs/receipts").rglob("*"))
        if p.is_file() and OUT not in p.parents
    }
    screen.write(OUT / "prior-receipts.json", prior)
    base = screen.read(BASE / "protocol.json")
    assert all(
        screen.sha(ROOT / p) == value for p, value in base["source_sha256"].items()
    )
    checks = []
    with patch.object(screen.review_participants, "NativeExchange", screen.forbidden):
        for case in screen.CASES:
            folder = OUT / "cases" / case["id"]
            shutil.copytree(BASE / "cases" / case["id"], folder)
            _, root, _, _ = screen.construct(
                folder, OUT / "anchor-baselines" / case["id"]
            )
            before_results = [
                screen.standalone_probe(
                    root,
                    case["output"],
                    [runner],
                    OUT / "anchor-baselines" / case["id"] / kind,
                )
                for kind, runner in (
                    ("supplemental", screen.RUNNER),
                    ("protected", "acceptance.py"),
                )
            ]
            assert any(not r["passed"] for r in before_results)
            payload = screen.proposal(
                folder, screen.read(folder / "reference.json")["text"]
            )
            result = screen.evaluate(
                folder, payload, OUT / "qualification" / case["id"], clearance(payload)
            )
            assert result["passed"]
            checks.append(
                {
                    "case": case["id"],
                    "stratum": "retained-anchor",
                    "broken_reproduced": True,
                    "full_repair_passed": True,
                }
            )

        for name, target, objective, changes in NEW:
            folder = OUT / "cases" / name
            temporary = Path(
                tempfile.mkdtemp(prefix="contender-case-", dir="/private/tmp")
            )
            root = screen.driver.comparison.prep.fixture(temporary)
            original = BASE / "cases/nested-status"
            for path in screen.read(original / "case.json")["fixture_sha256"]:
                (root / path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original / "fixture" / path, root / path)
            (root / TEST).write_text(screen.read(original / "reference.json")["text"])
            correct = (root / target).read_text()
            broken = correct
            for before, after in changes:
                broken = replace_once(broken, before, after)
            (root / target).write_text(broken)
            before_results = [
                screen.standalone_probe(
                    root, target, [runner], folder / "before" / kind
                )
                for kind, runner in (
                    ("supplemental", screen.RUNNER),
                    ("protected", "acceptance.py"),
                )
            ]
            assert any(not r["passed"] for r in before_results)
            (root / "plan.md").write_text(objective + "\n")
            hashes = screen.fixture_files(root)
            for path in hashes:
                destination = folder / "fixture" / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / path, destination)
            screen.write(
                folder / "case.json",
                {
                    "id": name,
                    "output": target,
                    "kind": "new-paired-defect"
                    if len(changes) == 2
                    else "new-single-defect",
                    "objective": objective,
                    "failure_excerpts": [
                        r["stderr"].encode()[-1700:].decode("utf-8", "replace")
                        for r in before_results
                        if not r["passed"]
                    ],
                    "fixture_sha256": hashes,
                },
            )
            screen.write(
                folder / "reference.json",
                {"local_reference_only": True, "path": target, "text": correct},
            )
            screen.construct(folder, folder / "owner")
            payload = screen.proposal(folder, correct)
            result = screen.evaluate(
                folder, payload, folder / "reference-evaluation", clearance(payload)
            )
            assert result["passed"], name
            partial_results = []
            if len(changes) == 2:
                for index, (before, after) in enumerate(changes):
                    # Leave exactly one defect in otherwise repaired source.
                    partial = screen.proposal(
                        folder, replace_once(correct, before, after)
                    )
                    outcome = screen.evaluate(
                        folder, partial, folder / f"partial-{index}", clearance(partial)
                    )
                    assert not outcome["passed"], (name, index)
                    assert any(not p["passed"] for p in outcome["probes"])
                    partial_results.append(
                        {"remaining_defect": index, "rejected_by_actual_tests": True}
                    )
            checks.append(
                {
                    "case": name,
                    "stratum": "new-paired-defect"
                    if len(changes) == 2
                    else "new-single-defect",
                    "broken_reproduced": True,
                    "full_repair_passed": True,
                    "partial_repairs": partial_results,
                }
            )

    trials = []
    rng = random.Random(918542)
    for repetition in (1, 2, 3):
        cases = [c["case"] for c in checks]
        rng.shuffle(cases)
        for case in cases:
            models = list(MODELS)
            rng.shuffle(models)
            for model in models:
                trials.append(
                    {
                        "id": f"ls{len(trials) + 1:02d}",
                        "case": case,
                        "repetition": repetition,
                        "model": model,
                    }
                )
    protocol = copy.deepcopy(base)
    protocol.update(
        {
            "profiles": {m: base["profiles"][m] for m in MODELS},
            "trials": trials,
            "case_turn_sha256": {
                c["case"]: screen.sha(OUT / "cases" / c["case"] / "owner/turn.json")
                for c in checks
            },
            "grading": {
                "owner": "Astra in the active session",
                "native_grader_calls": 0,
                "independent": False,
                "strictly_blinded": False,
                "basis": "Exact host contract, actual protected/supplemental tests and documented semantic preservation; no candidate self-grade",
            },
            "scoring": {
                **base["scoring"],
                "eligible_for_next_trial": "27/27 original scoped repairs; no serious preservation miss",
                "analysis": "Report each case/repetition; keep 3 retained anchors separate from 6 new cases; previous screen is historical, not pooled",
            },
            "limits": "Nine related cases in one feature, not 54 independent tasks. No complete native journey, production routing, Task 8 acceptance or release. Session review usage is outside the worker-call ledger.",
            "preparation_instruction": "C: prepare another trial; increase sample and cases; only Luna/Sol compete; Astra grades in-session; go. No new paid allocation yet.",
        }
    )
    protocol["source_sha256"][str(Path(__file__).relative_to(ROOT))] = screen.sha(
        Path(__file__)
    )
    protocol["budget"].update(
        {
            "max_calls": 54,
            "max_calls_by_model": dict.fromkeys(MODELS, 27),
            "expected_credits": [90, 180],
            "codex_credit_planning_ceiling": 200,
            "rates_per_million": {m: screen.RATES[m] for m in MODELS},
            "reserve_before_next_call": {MODELS[0]: 1, MODELS[1]: 7},
            "estimate_basis": "27 calls/model at 24–32k input and 1.5–6k output, no cache, calculates 89.505–176.58 worker credits. Rounded 90–180; 200 new planning ceiling. Prior six calls/model cost 23.679254 combined; proportional 54-call baseline 106.556643. New cases may differ. Excludes unmetered active-session review; not verified deductions or a hard invoice cap.",
            "scope": "New proposed allocation only. Previous 150-credit screen is closed; unused headroom is not transferred.",
        }
    )
    screen.write(OUT / "protocol.json", protocol)
    screen.write(
        OUT / "qualification.json",
        {
            "native_calls": 0,
            "reference_repairs_passed": len(checks),
            "partial_repairs_rejected": sum(
                len(c.get("partial_repairs", [])) for c in checks
            ),
            "checks": checks,
        },
    )
    assert all(screen.sha(ROOT / name) == value for name, value in prior.items())
    print(
        screen.canonical(
            {
                "prepared": str(OUT),
                "cases": len(checks),
                "planned_calls": len(trials),
                "native_calls": 0,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    prepare()
