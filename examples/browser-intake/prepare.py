"""Prepare the canonical synthetic browser tutorial; no participant dispatch."""
import json
from pathlib import Path
import sys

from attune_harness.work_contract import SIGNALS, create_work


def prepare(directory):
    root = Path(directory).resolve()
    root.mkdir(parents=True, exist_ok=False)
    project = root / "project"
    project.mkdir()
    (project / "source.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    (project / "plan.md").write_text("Keep saved tasks linked to their current decision.\n", encoding="utf-8")
    config = root / "participants.json"
    config.write_text(json.dumps({"schema_version": 1, "participants": {
        "local": {"adapter": "deterministic", "tools": [], "max_turns": 1,
                  "max_tool_calls": 0}}}), encoding="utf-8")
    budget = {"max_operations": 20, "max_attempts": 1, "max_output_bytes": 10000}
    return create_work(project, config, directory=root / "saved-task",
        intent={"goal": None, "context": ["Training example"], "scope": ["source.py"],
                "constraints": ["No implementation or model calls"], "acceptance": [], "questions": []},
        signals={**dict.fromkeys(SIGNALS, False), "existing_artifact": None},
        assignments=[{"role": "planner", "participant": "local",
                      "output_contract": "Bounded plan with observable checks", "budgets": budget}],
        inputs=["source.py"], artifact="plan.md", budget=budget)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Use the installed Harness interpreter: prepare.py /absolute/unused/training-directory")
    if not Path(sys.argv[1]).is_absolute():
        raise SystemExit("Choose an absolute unused training directory")
    record = prepare(sys.argv[1])
    print(json.dumps({"task_directory": str(Path(record["record_path"]).parent),
                      "status": record["status"], "accepted": False, "model_calls": 0}))
