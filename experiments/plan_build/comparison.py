"""Disposable offline preparation; this module has no native dispatch entry point."""

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys

from attune_harness import work_build, work_effects, work_runtime
from attune_harness.review_contract import canonical
from attune_harness.work_contract import SIGNALS, create_work

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location(
    "plan_build_preparation", HERE / "prepare.py"
)
prep = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prep)
EXPORT = "src/attune_harness/documentation_export.py"
DOCUMENTATION = "src/attune_harness/documentation.py"
GENERATED = "tests/generated/test_export.py"
EVALUATION_TEMPLATE = (
    ROOT / "docs/receipts/plan-build-task4-2026-09-18/journey-proposal.json"
)
MODELS = ("gpt-5.6-luna", "gpt-6-astra", "claude-fable-5-1")
RATES = {"gpt-5.6-luna": [5, 0.5, 30], "gpt-6-astra": [250, 25, 1250]}
BUDGET = {"max_operations": 30, "max_attempts": 1, "max_output_bytes": 32768}
BASELINE = {
    "planner": "Return a plan for work.intent using output_schema. Include tasks, "
    "criterion coverage, choices and notes. Use the supplied source evidence. "
    "A plan is a proposal and grants no execution authority.",
    "worker": "Implement the supplied step. Return schema_version 1, task_id, "
    "dependencies and files with path, before_sha256 and text. A new file has "
    "before_sha256 null. Return only this step's outputs. Proposals grant no authority.",
}
CRITERIA = [
    "Preserve every finding, including unknown and refuted, and all advisory notes.",
    "Emit one JSONL header then one record per finding, with a final newline.",
    "Keep default JSON unchanged; empty input emits one unknown header.",
    "Protected behavioral checks must pass; generated tests only supplement them.",
]


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def profile(model):
    value = {
        "adapter": "claude" if model.startswith("claude") else "codex",
        "model": model,
        "timeout": 300,
        "tools": [],
        "max_turns": 1,
        "max_tool_calls": 0,
    }
    if value["adapter"] == "codex":
        value.update(reasoning_effort="high", skills_context_tokens=1000)
    return value


def probe(arguments):
    return {
        "argv": [sys.executable, "-B", *arguments],
        "cwd": ".",
        "timeout": 30,
        "max_output_bytes": 32768,
        "oracle_paths": ["acceptance.py", "samples/api.py", "samples/empty.py"],
        "environment": {
            "PATH": "/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        },
    }


def prepare(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    root = prep.fixture(output)
    intent = {
        "goal": "Add opt-in JSONL documentation export preserving all evidence",
        "context": [
            "Earlier idea, explicitly superseded: export only verified findings.",
            "Human correction: retain unknown/refuted findings and advisory notes.",
            "Large-workload performance is unmeasured; do not claim a guarantee.",
        ],
        "scope": [EXPORT, DOCUMENTATION, GENERATED],
        "constraints": [
            "Preserve unrelated dirty work and protected acceptance.py.",
            "No deletion, model calls, new dependencies or production activation.",
        ],
        "acceptance": CRITERIA,
        "questions": [],
    }
    (root / "plan.md").write_text(canonical(intent) + "\n")
    config = output / "participants.json"
    prep.write(
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
    step = {
        "id": "export",
        "objective": "Implement json_lines(document) serialization",
        "dependencies": [],
        "outputs": [EXPORT],
        "checks": CRITERIA[:2],
    }
    tasks = [
        step,
        {
            "id": "cli",
            "objective": "Wire --format jsonl, preserve default JSON",
            "dependencies": ["export"],
            "outputs": [DOCUMENTATION],
            "checks": CRITERIA[2:3],
        },
        {
            "id": "supplement",
            "objective": "Supplement the protected oracle",
            "dependencies": ["cli"],
            "outputs": [GENERATED],
            "checks": CRITERIA[3:],
        },
    ]
    control = {
        "id": "baseline",
        "kind": "check",
        "owner": "frozen-oracle",
        "version": 1,
        "required": True,
        "phases": ["build"],
    }
    directory = output / "build-work"
    effects = work_effects.freeze(
        root,
        intent["scope"],
        ["tests/generated"],
        ["plan.md", "acceptance.py", "samples/api.py", "samples/empty.py"],
        [
            {
                "control": work_effects.identity(control),
                "probe": probe(["acceptance.py", "--baseline"]),
            }
        ],
        directory,
        verification=[
            {
                "task_id": "export",
                "probe": probe(
                    [
                        "-m",
                        "unittest",
                        "acceptance.Feature.test_unknown_refuted_and_advisory_notes_survive",
                    ]
                ),
            },
            *[
                {"task_id": name, "probe": probe(["acceptance.py"])}
                for name in ("cli", "supplement", "final")
            ],
        ],
    )
    arguments = dict(
        intent=intent,
        signals={
            **dict.fromkeys(SIGNALS, False),
            "dependent_changes": True,
            "compatibility_risk": True,
            "existing_artifact": None,
        },
        assignments=[
            {
                "role": name,
                "participant": name,
                "budgets": BUDGET,
                "output_contract": "Bounded proposal; preserve evidence and disclose unknowns",
            }
            for name in ("planner", "worker", "reviewer")
        ],
        controls=[control],
        inputs=[DOCUMENTATION, "acceptance.py"],
        artifact="plan.md",
        budget=BUDGET,
    )
    planning = create_work(root, config, directory=output / "plan-work", **arguments)
    building = create_work(
        root, config, directory=directory, tasks=tasks, effects=effects, **arguments
    )
    work_build.preflight(building["request"])
    evidence = {
        path: (root / path).read_text()
        for path in (
            DOCUMENTATION,
            "acceptance.py",
            "plan.md",
            "samples/api.py",
            "samples/empty.py",
        )
    }
    run = {"source_evidence": evidence, "participants": {}}
    turns = {
        "planner": work_runtime._turn(planning["request"], "planner", run),
        "worker": work_build.turn(building["request"], run, "worker", step, []),
    }
    for role, turn in turns.items():
        for arm in ("baseline", "candidate"):
            current = copy.deepcopy(turn)
            if arm == "baseline":
                current["protocol"] = BASELINE[role]
            prep.write(output / f"{role}-{arm}.json", current)
    order = [
        {"model": m, "role": r, "arm": a, "repetition": n}
        for m in MODELS
        for r in turns
        for a in ("baseline", "candidate")
        for n in (1, 2)
    ]
    random.Random(18092026).shuffle(order)
    for index, item in enumerate(order, 1):
        item["id"] = f"pb{index:02d}"
    sources = [
        *sorted((ROOT / "src/attune_harness").glob("*.py")),
        Path(__file__),
        HERE / "prepare.py",
        HERE / "fixtures/acceptance.py",
        EVALUATION_TEMPLATE,
        ROOT / "tests/test_plan_build_comparison.py",
    ]
    protocol = {
        "schema_version": 1,
        "status": "prepared-unapproved",
        "native_calls": 0,
        "profiles": {model: profile(model) for model in MODELS},
        "trials": order,
        "source_sha256": {str(p.relative_to(ROOT)): file_hash(p) for p in sources},
        "interpreter": sys.executable,
        "interpreter_sha256": file_hash(sys.executable),
        "prompt_bytes": {
            f"{r}-{a}": len(
                canonical(json.loads((output / f"{r}-{a}.json").read_text())).encode()
            )
            for r in turns
            for a in ("baseline", "candidate")
        },
        "budget": {
            "max_calls": 24,
            "max_calls_by_model": dict.fromkeys(MODELS, 8),
            "codex_credit_planning_ceiling": 100,
            "new_api_dollars": 0,
            "claude_route": "existing Max; verify before dispatch",
            "expected_credits": [35, 75],
            "rates_per_million": RATES,
            "pricing_source": "https://learn.chatgpt.com/docs/pricing",
            "pricing_checked": "2026-09-18",
            "required_speed": "Standard; dispatch must verify or force it, otherwise stop",
            "assumed_tokens_per_call": {"input": [6000, 10000], "output": [2000, 5000]},
            "reserve_before_next_call": {
                "gpt-6-astra": 10,
                "gpt-5.6-luna": 1,
                "claude-fable-5-1": 0,
            },
            "limits": "Estimates, not account balance or a hard per-response spend cap",
        },
        "scoring": {
            "dimensions": [
                "schema",
                "goal_fidelity",
                "constraints",
                "artifact_behavior",
                "unsupported_claims",
                "unnecessary_blocks",
                "useful_alternatives",
                "optional_advice",
                "human_correction",
            ],
            "floor": "Zero critical/enforcement misses; candidate 2/2 per role/model; "
            "no matched baseline-correct/candidate-wrong regression. Unresolved grading stays unknown.",
            "method": "Fixed behavioral oracle plus label-blinded session-assistant semantic "
            "grading with evidence. Not an independent native grader.",
            "authoring": "Host-selected XML is frozen context, not evidence of model tier-selection skill.",
            "alternatives": "Relevant supported alternatives only; no quota for invented choices.",
            "worker_oracle": "Evaluate the export proposal with the frozen Task 4 CLI fixture "
            "and full acceptance.py. The CLI is a fixed integration driver, not native output. "
            "Only the exporter is the native worker's artifact. Preserve both sources and all logs.",
        },
        "metrics": [
            "first_validated_useful_seconds",
            "completion_seconds",
            "reported_usage",
            "calls_including_failures",
            "presentation_seconds_or_unknown",
        ],
        "stop": [
            "unknown usage or unresolved call",
            "authentication/routing ambiguity",
            "critical enforcement failure",
            "next-call reserve exceeds remaining budget",
            "call cap exhausted",
        ],
        "limits": "Role screening only; no native critic/reviewer, full journey, live installation "
        "or production reliability qualification. No retries, fallback or authority grant.",
    }
    prep.write(output / "protocol.json", protocol)
    bound = [
        "protocol.json",
        "participants.json",
        *[f"{r}-{a}.json" for r in turns for a in ("baseline", "candidate")],
    ]
    # RunStore owns its path; avoid coupling the evidence manifest to its filename.
    bound += [
        str(Path(r["record_path"]).relative_to(output)) for r in (planning, building)
    ]
    bound += [str(p.relative_to(output)) for p in root.rglob("*") if p.is_file()]
    prep.write(
        output / "freeze.json", {p: file_hash(output / p) for p in sorted(bound)}
    )
    return protocol


def verify(output):
    output = Path(output)
    for path, expected in json.loads((output / "freeze.json").read_text()).items():
        if file_hash(output / path) != expected:
            raise ValueError(f"Prepared artifact changed: {path}")
    protocol = json.loads((output / "protocol.json").read_text())
    for path, expected in protocol["source_sha256"].items():
        if file_hash(ROOT / path) != expected:
            raise ValueError(f"Source changed: {path}")
    if file_hash(protocol["interpreter"]) != protocol["interpreter_sha256"]:
        raise ValueError("Interpreter changed")
    return protocol


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    result = verify(args.output) if args.verify else prepare(args.output)
    print(
        json.dumps(
            {
                k: result[k]
                for k in ("status", "native_calls", "budget", "prompt_bytes")
            },
            indent=2,
        )
    )
