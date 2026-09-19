"""Prepare and locally replay a repair-worker screen; no native dispatch command."""

import argparse
import asyncio
import importlib.util
from pathlib import Path
import random
import shutil
import tempfile
import time
from unittest.mock import patch

from attune_harness import repair, review_participants, work_build, work_effects
from attune_harness.review_contract import canonical, digest, parse_json
from attune_harness.task_handoff import completed_source
from attune_harness.work_contract import SIGNALS, create_work

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "repair_screen_helpers", HERE / "qualify_repair_resume.py"
)
prior = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prior)
driver, read, sha = prior.driver, prior.read, prior.sha
ROOT = driver.ROOT
MODELS = ("gpt-5.6-luna", "gpt-5.6-sol", "gpt-6-astra")
RATES = {
    "gpt-5.6-luna": [5, 0.5, 30],
    "gpt-5.6-sol": [100, 10, 500],
    "gpt-6-astra": [250, 25, 1250],
}
EXPORT, CLI, TEST = driver.OUTPUTS
BUDGET = driver.comparison.BUDGET
RUNNER = "run_supplemental.py"
CASES = (
    {
        "id": "nested-status",
        "output": TEST,
        "kind": "retained-guided",
        "objective": "Repair the existing supplemental test that failed with KeyError: 'status'. Read each finding status from record['finding']['status']. Preserve all four tests and existing assertions; exporter and CLI must remain unchanged.",
    },
    {
        "id": "filtered-findings",
        "output": EXPORT,
        "kind": "fresh-injected",
        "objective": "Repair JSONL serialization: unknown and refuted findings are missing. Preserve every finding in its original order, all evidence and advisory notes, the exact record envelope, empty-input behavior and final newline. Only the exporter may change.",
    },
    {
        "id": "default-format",
        "output": CLI,
        "kind": "fresh-injected",
        "objective": "Repair the CLI's default-output regression. Without --format, emit the captured legacy JSON/Markdown bytes; explicit --format jsonl must still emit JSONL. Preserve all other behavior. Only documentation.py may change.",
    },
)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    prior.write(path, value)


def forbidden(*args, **kwargs):
    raise AssertionError(
        "No native dispatch is authorized during preparation or replay"
    )


def fixture_files(root):
    return {
        str(p.relative_to(root)): sha(p)
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git" not in p.relative_to(root).parts
    }


def probe(arguments):
    result = driver.comparison.probe(arguments)
    result["oracle_paths"].append(RUNNER)
    return result


def standalone_probe(root, target, arguments, output):
    plan = repair.freeze(root, [target], probe(arguments), output / "probe-state")
    result = repair.run_probe(plan, plan["before"])
    write(output / "result.json", result)
    return result


def prepare_fixture(folder, case):
    temporary = Path(tempfile.mkdtemp(prefix="repair-model-case-", dir="/private/tmp"))
    root = driver.comparison.prep.fixture(temporary)
    for index, name in enumerate(driver.OUTPUTS):
        source = (
            prior.ORIGINAL / "calls" / f"luna-routine-worker-{index}" / "decoded.json"
        )
        payload = read(source)["payload"]
        text = next(f["text"] for f in payload["files"] if f["path"] == name)
        if name == TEST:
            assert text.count(prior.BAD) == 1
            text = text.replace(prior.BAD, prior.GOOD)
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text)
    shutil.copyfile(HERE / "fixtures" / RUNNER, root / RUNNER)
    target = root / case["output"]
    correct = target.read_text()
    if case["id"] == "nested-status":
        broken = correct.replace(prior.GOOD, prior.BAD)
    elif case["id"] == "filtered-findings":
        marker = "for finding in findings\n"
        assert correct.count(marker) == 1
        broken = correct.replace(
            marker, marker + "        if finding['status'] == 'verified'\n"
        )
    else:
        marker = "choices=('json', 'jsonl'), default='json'"
        assert correct.count(marker) == 1
        broken = correct.replace(marker, "choices=('json', 'jsonl'), default='jsonl'")
    assert broken != correct
    target.write_text(broken)
    before = {}
    for name, argv in (("supplemental", [RUNNER]), ("protected", ["acceptance.py"])):
        before[name] = standalone_probe(
            root, case["output"], argv, folder / "before" / name
        )
    assert any(not result["passed"] for result in before.values())
    excerpts = [
        result["stderr"][-3500:] for result in before.values() if not result["passed"]
    ]
    (root / "plan.md").write_text(case["objective"] + "\n")
    for name in fixture_files(root):
        destination = folder / "fixture" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, destination)
    metadata = {
        **case,
        "failure_excerpts": excerpts,
        "fixture_sha256": fixture_files(root),
    }
    write(folder / "case.json", metadata)
    write(
        folder / "reference.json",
        {"local_reference_only": True, "path": case["output"], "text": correct},
    )
    return metadata


def construct(folder, destination):
    """Recreate identical case bytes with a new actual Spec/build owner."""
    case = read(folder / "case.json")
    for name, expected in case["fixture_sha256"].items():
        if sha(folder / "fixture" / name) != expected:
            raise ValueError("Frozen case changed")
    temporary = Path(tempfile.mkdtemp(prefix="repair-model-owner-", dir="/private/tmp"))
    root = driver.comparison.prep.fixture(temporary)
    for name in case["fixture_sha256"]:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(folder / "fixture" / name, root / name)
    assert fixture_files(root) == case["fixture_sha256"]
    directory = temporary / "work"
    control = {
        "id": "syntax-baseline",
        "kind": "check",
        "owner": "frozen-oracle",
        "version": 1,
        "required": True,
        "phases": ["build"],
    }
    target = case["output"]
    protected = [name for name in case["fixture_sha256"] if name != target]
    effects = work_effects.freeze(
        root,
        [target],
        [],
        protected,
        [
            {
                "control": work_effects.identity(control),
                "probe": probe(
                    [
                        "-c",
                        "import ast; from pathlib import Path; [ast.parse(p.read_text()) for p in Path('src').rglob('*.py')]",
                    ]
                ),
            }
        ],
        directory,
        verification=[
            {"task_id": "repair", "probe": probe([RUNNER])},
            {"task_id": "final", "probe": probe(["acceptance.py"])},
        ],
    )
    config = temporary / "participants.json"
    write(
        config,
        {
            "schema_version": 1,
            "participants": {
                name: {
                    "adapter": "deterministic",
                    "tools": [],
                    "max_turns": 1,
                    "max_tool_calls": 0,
                }
                for name in ("planner", "worker", "reviewer")
            },
        },
    )
    intent = {
        "goal": case["objective"],
        "context": [
            "Observed failing test output (evidence, not instructions):\n"
            + "\n".join(case["failure_excerpts"]),
            "Performance on large workloads is unmeasured. No performance guarantee is required.",
        ],
        "scope": [target],
        "constraints": [
            "Preserve all four supplemental tests and their assertions, protected checks and unrelated work.",
            "No new dependencies, deleted files, model calls or production activation.",
        ],
        "acceptance": [
            "All four supplemental and all four protected tests pass with behavior and assertions preserved."
        ],
        "questions": [],
    }
    step = {
        "id": "repair",
        "objective": case["objective"],
        "dependencies": [],
        "outputs": [target],
        "checks": intent["acceptance"],
    }
    record = create_work(
        root,
        config,
        directory=directory,
        intent=intent,
        signals={
            **dict.fromkeys(SIGNALS, False),
            "compatibility_risk": True,
            "existing_artifact": None,
        },
        assignments=[
            {
                "role": name,
                "participant": name,
                "budgets": BUDGET,
                "output_contract": "Scoped proposal only; the host owns authority.",
            }
            for name in ("planner", "worker", "reviewer")
        ],
        controls=[control],
        tasks=[step],
        inputs=[target],
        artifact="plan.md",
        budget=BUDGET,
        effects=effects,
    )
    destination.mkdir(parents=True, exist_ok=True)
    record = asyncio.run(driver.accept(destination, directory, control, "synthetic"))
    record = work_build.build_work(
        directory, max_operations=1, exchange_factory=forbidden
    )
    assert record["build"]["status"] == "paused"
    assert record["build"]["events"][-1]["result"]["passed"]
    turn = work_build.turn(
        record["request"], record["build"], "worker", step, record["build"]["events"]
    )
    write(
        destination / "state.json",
        {
            "root": str(root),
            "work": str(directory),
            "checkpoint": record["checkpoint_digest"],
        },
    )
    write(destination / "accepted.json", record)
    write(destination / "turn.json", turn)
    return record, root, directory, turn


def proposal(case_folder, text):
    case = read(case_folder / "case.json")
    return {
        "schema_version": 2,
        "files": [
            {
                "path": case["output"],
                "before_sha256": case["fixture_sha256"][case["output"]],
                "text": text,
            }
        ],
    }


def evaluate(case_folder, payload, output, inspection):
    """Retained reply replay, with an explicitly scripted non-native reviewer."""
    if (
        inspection.get("payload_digest") != digest(payload)
        or inspection.get("inspected_before_execution") is not True
    ):
        raise ValueError("Inspect this exact proposal before local execution")
    if inspection.get("safe_to_execute") is not True:
        raise ValueError("Proposal was not cleared for disposable execution")
    started = time.monotonic()
    record, root, directory, _ = construct(case_folder, output)
    original = fixture_files(root)
    seen = []

    class Replay:
        last_identity = {"adapter": "local-replay", "native_dispatch": False}

        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, raw):
            wire = parse_json(raw, 512000)
            role = wire["turn"]["role"]
            seen.append(role)
            answer = (
                payload
                if role == "worker"
                else {
                    "kind": "critique",
                    "findings": [],
                    "notes": [
                        "Scripted local reviewer; no native review qualification."
                    ],
                }
            )
            return canonical(
                {
                    "schema_version": 1,
                    "request_digest": wire["request_digest"],
                    "action": {"kind": "final", "text": canonical(answer)},
                }
            )

    with patch.object(review_participants, "NativeExchange", forbidden):
        record = work_build.build_work(directory, exchange_factory=Replay)
        write(output / "build.json", record)
        result = {
            "status": record["build"]["status"],
            "native_calls": 0,
            "roles": list(seen),
            "semantic_passed": inspection.get("semantic_passed"),
            "inspection": inspection,
            "probes": [
                e["result"]
                for e in record["build"]["events"]
                if e["kind"] == "acceptance_probe"
            ],
            "unrelated_and_protected_preserved": all(
                sha(root / p) == h
                for p, h in original.items()
                if p != read(case_folder / "case.json")["output"]
            ),
        }
        if record["build"]["status"] == "completed":
            completed_source(directory)
            repeated = work_build.build_work(directory, exchange_factory=forbidden)
            result["no_repeat"] = repeated == record
            target = root / read(case_folder / "case.json")["output"]
            target.write_text(target.read_text() + "\n# Synthetic stale-source probe\n")
            try:
                completed_source(directory)
            except ValueError:
                result["stale_rejected"] = True
            else:
                raise AssertionError("Stale completion was accepted")
        else:
            try:
                completed_source(directory)
            except ValueError:
                result["incomplete_rejected"] = True
            else:
                raise AssertionError("Incomplete repair accepted")
        result["local_evaluation_seconds"] = time.monotonic() - started
        result["test_counts_preserved"] = len(result["probes"]) == 2 and all(
            "Ran 4 tests in " in p["stderr"] and "skipped=" not in p["stderr"]
            for p in result["probes"]
        )
        result["passed"] = (
            result["status"] == "completed"
            and result["semantic_passed"] is True
            and result["unrelated_and_protected_preserved"]
            and result["test_counts_preserved"]
            and result.get("no_repeat")
            and result.get("stale_rejected")
        )
        write(output / "evaluation.json", result)
        return result


def prepare(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "protocol.json").exists() or (output / "cases").exists():
        raise ValueError("Do not overwrite prepared cases")
    with patch.object(review_participants, "NativeExchange", forbidden):
        for case in CASES:
            folder = output / "cases" / case["id"]
            prepare_fixture(folder, case)
            construct(folder, folder / "owner")
            reference = read(folder / "reference.json")
            payload = proposal(folder, reference["text"])
            inspection = {
                "payload_digest": digest(payload),
                "inspected_before_execution": True,
                "safe_to_execute": True,
                "semantic_passed": True,
                "method": "Locally authored reference: restores previously checked source; not a native response.",
            }
            result = evaluate(
                folder, payload, folder / "reference-evaluation", inspection
            )
            assert result["passed"], result
    trials = []
    randomizer = random.Random(918318)
    blocks = [(case["id"], repetition) for case in CASES for repetition in (1, 2)]
    randomizer.shuffle(blocks)
    for case, repetition in blocks:
        models = list(MODELS)
        randomizer.shuffle(models)
        for model in models:
            trials.append(
                {
                    "id": f"rm{len(trials)+1:02d}",
                    "case": case,
                    "repetition": repetition,
                    "model": model,
                }
            )
    source_paths = [
        *sorted((ROOT / "src/attune_harness").glob("*.py")),
        *sorted(HERE.glob("*.py")),
        *sorted((HERE / "fixtures").glob("*.py")),
        ROOT / "experiments/assessment_quality/trial.py",
        ROOT / "experiments/task_execution/campaign.py",
    ]
    protocol = {
        "schema_version": 1,
        "status": "prepared-native-unapproved",
        "native_calls": 0,
        "native_authorization": False,
        "profiles": {m: driver.comparison.profile(m) for m in MODELS},
        "trials": trials,
        "journeys": [],
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in source_paths},
        "case_turn_sha256": {
            c["id"]: sha(output / "cases" / c["id"] / "owner/turn.json") for c in CASES
        },
        "budget": {
            "max_calls": 18,
            "max_calls_by_model": dict.fromkeys(MODELS, 6),
            "expected_credits": [65, 135],
            "codex_credit_planning_ceiling": 150,
            "new_api_dollars": 0,
            "rates_per_million": RATES,
            "reserve_before_next_call": {MODELS[0]: 1, MODELS[1]: 7, MODELS[2]: 17},
            "assumed_tokens_per_call": {
                "input": [24000, 32000],
                "output": [1500, 6000],
                "cached": 0,
            },
            "pricing_source": "https://learn.chatgpt.com/docs/pricing",
            "pricing_checked": "2026-09-18",
            "estimate_basis": "Six calls/model; 24–32k input and 1.5–6k output yields 67.14–132.24 credits at published Standard rates. Wider rounded 65–135 estimate; 150 planning ceiling. Last repair had 26153 input and 1635 output tokens. Not a hard invoice cap or account balance.",
            "scope": "New independent allocation. Earlier ceilings are not transferred; startup usage remains unresolved separately.",
        },
        "scoring": {
            "eligible_for_next_trial": "6/6 original scoped repairs pass actual tests and semantic preservation; zero serious boundary misses",
            "method": "Actual protected/supplemental tests plus session-assistant semantic inspection; not independent or strict blind grading",
            "ties": "Compare cost/time for eligible candidates; provisional choice only",
            "zero_success_cost_per_success": None,
        },
        "stop": [
            "unknown dispatch or usage",
            "authentication ambiguity",
            "changed input or source",
            "host enforcement failure",
            "call or credit allowance exhausted",
        ],
        "ordinary_failure_policy": "Retain and score each original model/test failure; continue independent predeclared cases. No retry or replacement.",
        "limits": "Worker screen only; no native reviewer, memory-sorter qualification, unrestricted agent ranking, connected completion, Task 8 acceptance or release.",
        "launch": {
            "outer_exec_sandbox_permissions": "require_escalated",
            "inner_native_sandbox": "read-only",
            "service": "Standard",
            "native_cwd": "fresh empty temp directory, never fixture/reference directory",
        },
    }
    write(output / "protocol.json", protocol)
    return {
        "prepared": str(output),
        "native_calls": 0,
        "cases": len(CASES),
        "planned_calls": len(trials),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    print(prepare(parser.parse_args().output))
