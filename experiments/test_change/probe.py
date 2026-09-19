"""Offline investigation of existing testing seams; no production implementation.

Run with the qualified combined candidate interpreter. Source reads come from
the isolated AI worktree; all index mutations and pytest artifacts are temporary.
"""

# Install the network guard before importing the inspected product modules.
# ruff: noqa: E402

from __future__ import annotations

import ast
import asyncio
from dataclasses import asdict
import hashlib
import importlib
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import tempfile

HARNESS = Path(__file__).resolve().parents[2]
AI = Path("/Users/patrickroebuck/attune-ai-memory-adoption")
OUT = HARNESS / "docs/receipts/test-this-change"
OUT.mkdir(parents=True, exist_ok=True)
ROOT = Path(tempfile.mkdtemp(prefix="attune-test-change-", dir="/private/tmp"))
CHANGED = ["src/attune/spec/state.py", "src/attune/spec/workspace.py"]
TESTS = ["tests/unit/spec/test_state.py", "tests/unit/spec/test_workspace.py"]
attempts = []


def deny_network(self, address):
    attempts.append(repr(address))
    raise RuntimeError("Network disabled for this investigation")


socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network
os.environ.update(
    ATTUNE_USAGE_PING="0",
    ATTUNE_VERSION_CHECK="0",
    PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
    PYTHONDONTWRITEBYTECODE="1",
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot():
    return {str(p.relative_to(ROOT)): sha(p) for p in ROOT.rglob("*.py")}


def write(relative, content):
    target = ROOT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


for relative in CHANGED + TESTS:
    write(relative, (AI / relative).read_text())
write("src/attune/unrelated.py", "def unrelated(value):\n    return value + 1\n")
write(
    "pytest.ini", "[pytest]\nasyncio_mode = auto\nasyncio_default_fixture_loop_scope = function\n"
)
# Network guard also loads in pytest subprocesses; no source-tree imports.
write(
    "guard/sitecustomize.py",
    "import socket\nfrom pathlib import Path\n"
    "def deny(self, address):\n"
    f"    with Path({str(ROOT / 'network-attempts.txt')!r}).open('a') as f:\n"
    "        f.write(repr(address) + '\\n')\n"
    "    raise RuntimeError('Network disabled for this investigation')\n"
    "socket.socket.connect = deny\nsocket.socket.connect_ex = deny\n",
)
os.environ["PYTHONPATH"] = str(ROOT / "guard")

from attune.project_index.index import ProjectIndex
from attune.workflows.test_maintenance import TestMaintenanceWorkflow
from attune.workflows.test_gen.workflow import TestGenerationWorkflow
from attune.workflows.migration import MigrationConfig, resolve_workflow_migration
from attune.workspaces.smart_test import SmartTestWorkspaceAdapter
from attune_forms import WorkspaceActionResponse, WorkspaceViewId
from attune.verification.config import VerificationConfig
from attune.verification.runner import run_verification
from attune.verification.strategies import RunTestsStrategy

result = {
    "mode": "offline installed APIs; real Spec change plus labeled synthetic cases",
    "interpreter": sys.executable,
    "python": sys.version,
    "cwd": os.getcwd(),
    "temporary_root": str(ROOT),
    "changed_files": CHANGED,
    "selected_tests": TESTS,
    "selection_method": "Lead selected existing direct tests after reading change and imports; not an automatic selector",
    "source_hashes": {p: sha(AI / p) for p in CHANGED + TESTS},
    "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=AI, text=True).strip(),
}
diff = subprocess.check_output(["git", "diff", "--", *CHANGED, *TESTS], cwd=AI, text=True)
(OUT / "selected-change.diff").write_text(diff)
result["diff_sha256"] = sha(OUT / "selected-change.diff")
module_names = [
    "attune.spec.state",
    "attune.spec.workspace",
    "attune.project_index.index",
    "attune.project_index.file_analysis",
    "attune.workflows.test_maintenance",
    "attune.workflows.migration",
    "attune.workflows.test_gen.workflow",
    "attune.workflows.test_gen_parallel",
    "attune.workspaces.smart_test",
    "attune.verification.runner",
    "attune.verification.strategies",
    "attune.mcp.server",
    "attune.mcp.workflow_handlers",
    "attune.cli_commands.workflow_commands",
]
result["module_origins"] = []
for name in module_names:
    path = Path(importlib.import_module(name).__file__)
    source = AI / "src" / (name.replace(".", "/") + ".py")
    result["module_origins"].append(
        {
            "module": name,
            "path": str(path),
            "sha256": sha(path),
            "matches_worktree": sha(path) == sha(source),
        }
    )
assert all(r["matches_worktree"] for r in result["module_origins"])

# Real scanner/planner, but on four copied case files plus one unrelated fixture.
index = ProjectIndex(str(ROOT), use_parallel=False)
maintenance = TestMaintenanceWorkflow(str(ROOT), index=index)
analysis = asyncio.run(maintenance.run({"mode": "analyze", "changed_files": CHANGED}))
result["maintenance_analysis"] = analysis
result["direct_test_mapping"] = {p: index.get_file(p).test_file_path for p in CHANGED}
before = snapshot()
executed = asyncio.run(maintenance.run({"mode": "execute", "changed_files": CHANGED}))
result["maintenance_execution"] = {
    "returned": executed,
    "python_files_unchanged": before == snapshot(),
    "unrelated_index_claims_tests_exist": index.get_file("src/attune/unrelated.py").tests_exist,
    "unrelated_test_files_on_disk": [str(p) for p in ROOT.rglob("test_unrelated.py")],
}
assert "src/attune/unrelated.py" in [item["file_path"] for item in analysis["plan"]["items"]]
assert before == snapshot() and executed["execution"]["succeeded"] > 0

# Exercise actual workspace transitions; the audit finding is synthetic, not LLM output.
adapter = SmartTestWorkspaceAdapter(ROOT)
state = adapter.create({"path": CHANGED[1], "approach": "both"})


def response(action):
    return WorkspaceActionResponse(WorkspaceViewId.EXECUTION, action, True)


auditing = adapter.apply(state, response("audit_test_gaps"))
proposal = adapter.publish(
    auditing.state,
    {
        "kind": "audit_result",
        "success": True,
        "gaps": [
            {
                "path": CHANGED[1],
                "symbol": "terminal",
                "risk": "HIGH",
                "detail": "Synthetic write-boundary probe; not a claim about current coverage",
            }
        ],
        "proposed_files": [TESTS[1]],
    },
)
generating = adapter.apply(proposal.state, response("generate_tests"))
resolved = str(ROOT / CHANGED[1])
result["smart_test_handoff"] = {
    "audit_dispatch": auditing.result,
    "generation_dispatch": generating.result,
    "generator_default_output": str(TestGenerationWorkflow._resolve_output_dir(resolved, None)),
    "generator_accepts_existing_test_directory": TestGenerationWorkflow._resolve_output_dir(
        resolved, str((ROOT / TESTS[1]).parent)
    )
    is not None,
    "provider_called": False,
    "generation_performed": False,
}
assert result["smart_test_handoff"]["generator_accepts_existing_test_directory"] is False

name, flags, migrated = resolve_workflow_migration(
    "test-gen-parallel", MigrationConfig(mode="auto")
)
method = ast.parse((AI / "src/attune/workflows/test_gen/workflow.py").read_text())
execute = next(
    n for n in ast.walk(method) if isinstance(n, ast.AsyncFunctionDef) and n.name == "execute"
)
consumed = sorted(
    {
        n.args[0].value
        for n in ast.walk(execute)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and isinstance(n.func.value, ast.Name)
        and n.func.value.id == "kwargs"
        and n.func.attr == "get"
        and n.args
        and isinstance(n.args[0], ast.Constant)
    }
)
result["parallel_alias"] = {
    "resolved": name,
    "flags": flags,
    "migrated": migrated,
    "canonical_execute_consumed_kwargs": consumed,
    "mcp_implementation": "attune.workflows.test_gen_parallel.ParallelTestGenerationWorkflow",
    "limit": "Resolution executed; engine behavior inspected in source, no native generation",
}
assert flags == {"parallel": True} and "parallel" not in consumed
alias_command = [
    sys.executable,
    "-B",
    "-m",
    "attune.cli_minimal",
    "workflow",
    "run",
    "test-gen-parallel",
]
alias_run = subprocess.run(alias_command, cwd=ROOT, capture_output=True, text=True, timeout=30)
result["parallel_alias"]["actual_cli"] = {
    "argv": alias_command,
    "cwd": str(ROOT),
    "exit_code": alias_run.returncode,
    "stdout": alias_run.stdout,
    "stderr": alias_run.stderr,
}
assert alias_run.returncode == 3 and "Workflow not found: test-gen-parallel" in alias_run.stdout

# Existing verifier executes the manually selected real tests, then negative controls.
base = [
    sys.executable,
    "-B",
    "-m",
    "pytest",
    "-c",
    str(ROOT / "pytest.ini"),
    "-p",
    "pytest_asyncio.plugin",
    "-p",
    "no:cacheprovider",
    "-q",
]
write("negative/test_failure.py", "def test_failure():\n    assert False\n")
write("empty/README.txt", "No tests here.\n")
cases = {
    "selected_spec_tests": TESTS,
    "known_failure": ["negative/test_failure.py"],
    "no_tests": ["empty"],
    "collection_only": ["--collect-only", *TESTS],
}
result["verification"] = {}
for label, arguments in cases.items():
    command = shlex.join(base + arguments)
    receipt = run_verification(
        VerificationConfig(
            command=command,
            working_directory=str(ROOT),
            max_retries=0,
            correction_enabled=False,
            timeout_seconds=60,
        ),
        RunTestsStrategy(),
        "case-study",
        None,
    )
    result["verification"][label] = asdict(receipt)
assert result["verification"]["selected_spec_tests"]["exit_code"] == 0
assert result["verification"]["known_failure"]["exit_code"] == 1
assert result["verification"]["no_tests"]["exit_code"] == 5
assert result["verification"]["collection_only"]["passed"] is True
result["network_attempts"] = attempts
result["child_network_attempts"] = (
    (ROOT / "network-attempts.txt").read_text() if (ROOT / "network-attempts.txt").exists() else ""
)
assert not attempts and not result["child_network_attempts"]
result["probe_sha256"] = sha(__file__)
(OUT / "trace.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
print(
    json.dumps(
        {
            "trace": str(OUT / "trace.json"),
            "temporary_root": str(ROOT),
            "selection": result["direct_test_mapping"],
            "verification": {
                k: {
                    "exit_code": v["exit_code"],
                    "passed": v["passed"],
                    "stdout": v["stdout"][-170:],
                }
                for k, v in result["verification"].items()
            },
            "network_attempts": len(attempts),
        },
        indent=2,
    )
)
