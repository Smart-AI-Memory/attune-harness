"""Replay a source-inspected native proposal through the existing local build owner.

This is a controlled role evaluation with a fixed CLI and synthetic Spec choice,
not an autonomous native end-to-end journey or independent native review.
"""

import argparse
import asyncio
import importlib.util
import json
from pathlib import Path
import tempfile
import time

from attune_harness import work_effects
from attune_harness.review_contract import canonical
from attune_harness.spec_bridge import WorkSpecBridge
from attune_harness.task_handoff import completed_source
from attune_harness.work_contract import SIGNALS, create_work
from attune_harness.work_runtime import build_work

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "frozen_comparison", ROOT / "experiments/plan_build/comparison.py"
)
comparison = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(comparison)


def evaluate(sample, output):
    payload = json.loads(sample.read_text())["payload"]
    output.mkdir(parents=True, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix="plan-build-scoring-", dir="/private/tmp"))
    root = comparison.prep.fixture(scratch)
    original = json.loads(comparison.EVALUATION_TEMPLATE.read_text())
    cli = next(f for f in original["files"] if f["path"] == comparison.DOCUMENTATION)
    (root / cli["path"]).write_text(cli["text"])
    (root / "plan.md").write_text(
        "Evaluate only the inspected exporter against the protected oracle.\n"
    )
    config = scratch / "participants.json"
    comparison.prep.write(
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
    control = {
        "id": "baseline",
        "kind": "check",
        "owner": "frozen-oracle",
        "version": 1,
        "required": True,
        "phases": ["build"],
    }
    directory = scratch / "work"
    effects = work_effects.freeze(
        root,
        [comparison.EXPORT],
        [],
        [
            "plan.md",
            comparison.DOCUMENTATION,
            "acceptance.py",
            "samples/api.py",
            "samples/empty.py",
        ],
        [
            {
                "control": work_effects.identity(control),
                "probe": comparison.probe(["acceptance.py", "--baseline"]),
            }
        ],
        directory,
        verification=[
            {"task_id": task, "probe": comparison.probe(["acceptance.py"])}
            for task in ("export", "final")
        ],
    )
    record = create_work(
        root,
        config,
        directory=directory,
        intent={
            "goal": "Evaluate the frozen native exporter proposal with the fixed CLI",
            "context": ["Role screen; not a native complete journey"],
            "scope": [comparison.EXPORT],
            "constraints": ["Keep fixed inputs and dirty work"],
            "acceptance": comparison.CRITERIA,
            "questions": [],
        },
        signals={**dict.fromkeys(SIGNALS, False), "existing_artifact": None},
        assignments=[
            {
                "role": name,
                "participant": name,
                "budgets": comparison.BUDGET,
                "output_contract": "Retained proposal or explicitly labeled fixed review fixture",
            }
            for name in ("planner", "worker", "reviewer")
        ],
        controls=[control],
        tasks=[
            {
                "id": "export",
                "objective": "Evaluate json_lines(document)",
                "dependencies": [],
                "outputs": [comparison.EXPORT],
                "checks": comparison.CRITERIA,
            }
        ],
        inputs=[comparison.DOCUMENTATION],
        artifact="plan.md",
        budget=comparison.BUDGET,
        effects=effects,
    )

    async def approve():
        bridge = WorkSpecBridge(
            directory, supported_controls=[work_effects.identity(control)]
        )
        view = await bridge.open(
            detail="Synthetic fixture choice under the approved native evaluation; no product activation."
        )
        response = {
            "__elicitation_response__": True,
            "title": view.record.view.title,
            "view": view.record.view.id.value,
            "action": "approve_task",
            "confirmed": False,
            **view.record.binding.to_payload(),
        }
        result, accepted = await bridge.collect(response)
        comparison.prep.write(
            output / "collector.json",
            {"response": response, "result": dict(result.result)},
        )
        (output / "decision-form.md").write_text(view.render.markdown)
        return accepted

    record = asyncio.run(approve())

    class Retained:
        def __init__(self, configuration, cwd, *, profile):
            self.last_identity = None

        def __call__(self, raw):
            request = json.loads(raw)
            result = (
                payload
                if request["turn"]["role"] == "worker"
                else {
                    "kind": "critique",
                    "findings": [],
                    "notes": [
                        "Fixed local fixture. This is not an independent native review."
                    ],
                }
            )
            self.last_identity = {"adapter": "retained-proposal-fixture", "model": None}
            return canonical(
                {
                    "schema_version": 1,
                    "request_digest": request["request_digest"],
                    "action": {"kind": "final", "text": canonical(result)},
                }
            )

    started = time.perf_counter()
    record = build_work(directory, exchange_factory=Retained)
    elapsed = time.perf_counter() - started
    comparison.prep.write(output / "work-record.json", record)
    probes = {
        e["operation_key"]: e["result"]
        for e in record["build"]["events"]
        if e["kind"] == "acceptance_probe" and e["state"] == "completed"
    }
    for path in directory.rglob("*"):
        if path.is_file() and path.name != "record.json":
            dest = output / "artifacts" / path.relative_to(directory)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(path.read_bytes())
    preserved = all(
        comparison.file_hash(root / path) == effects["before"][path]["sha256"]
        for path in effects["protected"]
    )
    assert (
        preserved
        and (root / "unrelated.txt").read_text()
        == "Unrelated dirty work must survive.\n"
    )
    stale = None
    if record["build"]["status"] == "completed":
        completed_source(directory)
        target = root / comparison.EXPORT
        target.write_text(target.read_text() + "\n# Later synthetic change.\n")
        try:
            completed_source(directory)
        except ValueError as error:
            stale = str(error)
        else:
            raise AssertionError("Stale source accepted")
    result = {
        "sample": sample.stem,
        "status": record["build"]["status"],
        "probes": probes,
        "evaluation_seconds": elapsed,
        "protected_inputs_preserved": preserved,
        "stale_handoff_rejected": stale,
        "scratch": str(scratch),
        "native_calls": 0,
        "limits": "Fixed CLI and review fixture; actual Spec/effect/check owners; not a native full journey",
    }
    comparison.prep.write(output / "result.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source-inspected", action="store_true", required=True)
    args = parser.parse_args()
    result = evaluate(args.sample, args.output)
    print(
        json.dumps(
            {k: result[k] for k in ("sample", "status", "evaluation_seconds")}, indent=2
        )
    )
