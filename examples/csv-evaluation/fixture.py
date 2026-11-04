"""Offline software fixture only: no human trial, model, network or provider call."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from attune_harness import work_effects
import attune_harness
from attune_harness.review_contract import canonical
from attune_harness.task_contract import read_task
from attune_harness.work_contract import (
    SIGNALS, bind_work_acceptance, create_work, decision_binding,
    missing_information, revise_work,
)
from attune_harness.work_runtime import build_work

HERE = Path(__file__).resolve().parent
BUDGET = {"max_operations": 20, "max_attempts": 1, "max_output_bytes": 32768}
SCOPES = ("current_page", "all_matching")
VARIANTS = ("correction", "simple", "fully-specified")
PROTECTED = ["oracle.py", "cases.json", "task.md"]
QUESTION = "Export the current page or all matching records?"


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def effects(root, scope):
    environment = {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"}
    if os.name == "nt":
        environment["SystemRoot"] = os.environ["SystemRoot"]
    probe = {"argv": [sys.executable, "-B", "oracle.py", scope], "cwd": ".",
             "timeout": 10, "max_output_bytes": 8192, "environment": environment,
             "oracle_paths": ["oracle.py", "cases.json"]}
    return work_effects.freeze(
        root / "app", ["exporter.py"], [], PROTECTED, [], root / "task",
        verification=[{"task_id": key, "probe": probe} for key in ("export", "final")])


def criteria(scope):
    return [f"Export scope: {scope}", "Preserve active filters and report order",
            "Exclude private-note columns and values", "Produce valid CSV including empty results"]


def steps(scope):
    return [{"id": "export", "objective": f"Implement CSV export for {scope}",
             "dependencies": [], "outputs": ["exporter.py"], "checks": criteria(scope)}]


def prepare(directory, variant="correction"):
    root = Path(directory)
    if not root.is_absolute() or root != root.resolve():
        raise ValueError("Choose an absolute canonical unused directory")
    if variant not in VARIANTS:
        raise ValueError("Unknown fixture variant")
    # No reuse, cleanup or overwrite: a failed attempt remains inspectable.
    root.mkdir(parents=True, exist_ok=False)
    app = root / "app"
    app.mkdir()
    hooks = root / "empty-hooks"
    hooks.mkdir()
    for name in ("oracle.py", "cases.json"):
        shutil.copyfile(HERE / name, app / name)
    (app / "exporter.py").write_text(
        "def export_csv(rows, *, status, page, page_size, scope):\n"
        "    raise NotImplementedError('CSV export is not implemented')\n", encoding="utf-8")
    (app / "task.md").write_text(
        "# Synthetic CSV task\n\nImplement export_csv with the supplied keyword arguments.\n"
        "Filter by status, preserving input order; pages are one-based.\n"
        "Current page applies pagination after filtering; all matching ignores pagination.\n"
        "Return id,title,status CSV with a header even for empty results.\n"
        "Never export private_notes. Do not change protected checks.\n"
        "This fixture is not a human or model performance trial.\n", encoding="utf-8")
    git = ["git", "-C", str(app), "-c", "maintenance.auto=false",
           "-c", "commit.gpgsign=false", "-c", f"core.hooksPath={hooks}",
           "-c", "user.name=CSV Fixture", "-c", "user.email=fixture@example.invalid"]
    subprocess.run([*git, "init", "-q"], check=True, capture_output=True)
    subprocess.run([*git, "add", "exporter.py", *PROTECTED], check=True, capture_output=True)
    subprocess.run([*git, "commit", "-qm", "Synthetic CSV baseline"], check=True, capture_output=True)
    config = root / "participants.json"
    local = {"adapter": "deterministic", "tools": [], "max_turns": 1, "max_tool_calls": 0}
    write_json(config, {"schema_version": 1, "participants": {"local": local, "critic": local}})
    scope = "current_page" if variant == "fully-specified" else "unresolved"
    request = {
        "intent": {"goal": "Add CSV export to reports. Keep the active filters and exclude private notes.",
                   "context": ["Synthetic fixture; no human or model trial", f"Variant: {variant}"],
                   "scope": ["exporter.py"], "constraints": ["Keep the active filters", "Exclude private notes"],
                   "acceptance": criteria(scope),
                   "questions": [] if variant == "fully-specified" else [
                       {"id": "export-scope", "question": QUESTION, "answer": None, "material": True}]},
        "signals": {**dict.fromkeys(SIGNALS, False), "existing_artifact": None},
        "assignments": [{"role": role, "participant": peer, "output_contract": contract, "budgets": BUDGET}
                        for role, peer, contract in (("planner", "local", "Bounded export plan"),
                                                    ("worker", "local", "Scoped file proposal"),
                                                    ("reviewer", "critic", "Evidence-backed critique"))],
        "tasks": steps(scope), "inputs": ["exporter.py", "cases.json"], "artifact": "task.md",
        "budget": BUDGET, "effects": effects(root, scope),
    }
    write_json(root / "request.json", request)
    record = create_work(app, config, directory=root / "task", **request)
    write_json(root / "prepared.json", {"schema_version": 1, "kind": "offline-csv-fixture",
                                        "variant": variant, "task_id": record["request"]["task_id"],
                                        "accepted": False, "model_calls": 0})
    return record


def correct(root, scope, checkpoint):
    if scope not in SCOPES:
        raise ValueError("Unknown export scope")
    root = Path(root)
    record = read_task(root / "task")
    questions = record["request"]["intent"]["questions"]
    return revise_work(root / "task", checkpoint=checkpoint, require_fresh=True, changes={
        "intent": {"questions": [{**q, "answer": scope} for q in questions],
                   "acceptance": criteria(scope)},
        "tasks": steps(scope), "effects": effects(root, scope)})


def synthetic_decision(record):
    return {**decision_binding(record), "accepted": True,
            "source": {"owner": "spec", "disposition": "approve_task",
                       "reference": "synthetic-offline-csv-fixture:not-human-acceptance"}}


class ScriptedProposal:
    """Known fixture output only; cannot configure or dispatch a participant."""

    def __init__(self, config, cwd, *, profile):
        if config["adapter"] != "deterministic":
            raise ValueError("Offline fixture admits deterministic participants only")
        self.last_identity = {"adapter": "scripted-csv-fixture", "profile": profile}

    def __call__(self, raw):
        wire = json.loads(raw)
        turn = wire["turn"]
        if turn["role"] == "reviewer":
            payload = {"kind": "critique", "findings": [],
                       "notes": ["Scripted fixture review; no independent model-quality claim"]}
        else:
            old = turn["source_evidence"]["exporter.py"]
            payload = {"schema_version": 1, "task_id": turn["step"]["id"],
                       "dependencies": turn["step"]["dependencies"],
                       "files": [{"path": "exporter.py", "before_sha256": hashlib.sha256(old.encode()).hexdigest(),
                                  "text": (HERE / "reference.py").read_text(encoding="utf-8")}]}
        return canonical({"schema_version": 1, "request_digest": wire["request_digest"],
                          "action": {"kind": "final", "text": canonical(payload)}})


def smoke(directory, variant="correction"):
    root = Path(directory)
    record = prepare(root, variant)
    trace = [{"revision": record["request"]["revision"], "checkpoint": record["checkpoint_digest"]}]
    if variant == "correction":
        record = correct(root, "all_matching", record["checkpoint_digest"])
        trace.append({"revision": record["request"]["revision"], "checkpoint": record["checkpoint_digest"]})
    if variant != "fully-specified":
        record = correct(root, "current_page", record["checkpoint_digest"])
        trace.append({"revision": record["request"]["revision"], "checkpoint": record["checkpoint_digest"]})
    bind_work_acceptance(root / "task", synthetic_decision(record))
    result = build_work(root / "task", exchange_factory=ScriptedProposal,
                        allow_external=False, allow_native=False)
    passed = result.get("build", {}).get("status") == "completed"
    receipt = {"schema_version": 1, "kind": "offline-csv-software-check", "variant": variant,
               "recorded_at": datetime.now(timezone.utc).isoformat(), "passed": passed,
               "task_directory": str(root / "task"), "task_id": result["request"]["task_id"],
               "revisions": trace, "synthetic_acceptance": True, "model_calls": 0,
               "human_performance": None, "ai_performance": None, "token_usage": None,
               "runtime": {"python": platform.python_version(), "platform": platform.platform(),
                           "executable": sys.executable, "harness_module": attune_harness.__file__,
                           "harness_source_sha256": {
                               name: hashlib.sha256((Path(attune_harness.__file__).parent / name).read_bytes()).hexdigest()
                               for name in ("work_contract.py", "work_build.py", "work_effects.py", "repair.py")}},
               "limits": ["Scripted proposals, not model performance", "No human or host UI observation",
                          "Trusted local checks, not a sandbox for hostile code"],
               "source_sha256": {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                                 for name in ("fixture.py", "reference.py", "oracle.py", "cases.json")}}
    write_json(root / "receipt.json", receipt)
    retained = [root / "request.json", root / "participants.json", root / "prepared.json", root / "receipt.json",
                *sorted(path for path in (root / "task").rglob("*") if path.is_file()),
                *[root / "app" / name for name in ["exporter.py", *PROTECTED]]]
    write_json(root / "manifest.json", {"schema_version": 1, "sha256": {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in retained}})
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "smoke"))
    parser.add_argument("directory", type=Path, help="Absolute canonical unused output directory")
    parser.add_argument("--variant", choices=VARIANTS, default="correction")
    args = parser.parse_args()
    if args.action == "smoke":
        result = smoke(args.directory, args.variant)
        code = 0 if result["passed"] else 1
    else:
        record = prepare(args.directory, args.variant)
        result = {"task_directory": str(args.directory / "task"), "status": record["status"],
                  "missing": missing_information(record["request"]), "accepted": False, "model_calls": 0}
        code = 0
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
