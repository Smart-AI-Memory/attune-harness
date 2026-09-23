"""R2, the clean-environment journey, through the real command line.

Plan, accept, build and review run as child processes with the ``attune``
package blocked, on a fixture project with a Git checkout, two command
participants (local scripts) as the build's worker and reviewer, and a
deterministic assessor for the review; no model is called anywhere (spec
authority Task 4, step c; D23 decisions 1 and 4). The effects manifest is
frozen in-process, as the build tests do, because no command line verb
freezes one. On Windows the build may refuse with the platform's own words;
the test records which of the two outcomes it saw rather than skipping.
"""

# qualify: platform

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import attune_forms  # noqa: F401  a base dependency since 0.4.0 (D15): absent is a broken install, not a skip
import attune_harness
from attune_harness import work_effects

EXPORT = "pkg/export.py"
GENERATED = "tests/generated/test_app.py"
BUDGET = {"max_operations": 30, "max_attempts": 1, "max_output_bytes": 32768}
GOAL = "Export every finding"

# The worker proposes the files each step names; the reviewer returns an
# empty critique. Read one JSON request on stdin, print one JSON reply.
PEER = (
    "import json,sys,hashlib\n"
    "w=json.load(sys.stdin);t=w['turn']\n"
    "if t['role']=='reviewer':p={'kind':'critique','findings':[],'notes':['Synthetic command fixture']}\n"
    "else:\n"
    " texts={'pkg/export.py':'def answer():\\n    return 42\\n','tests/generated/test_app.py':'def test_generated():\\n    assert True\\n','source.py':'from pkg.export import answer\\ndef value():\\n    return answer()\\n'}\n"
    " p={'schema_version':1,'task_id':t['step']['id'],'dependencies':t['step']['dependencies'],'files':[{'path':n,'before_sha256':hashlib.sha256(t['source_evidence'][n].encode()).hexdigest() if n in t['source_evidence'] else None,'text':texts[n]} for n in t['step']['outputs']]}\n"
    "print(json.dumps({'schema_version':1,'request_digest':w['request_digest'],'action':{'kind':'final','text':json.dumps(p)}}))\n"
)


def child(argv, cwd):
    """One command line invocation in a child process with ``attune`` blocked."""
    code = (
        "import sys\n"
        "sys.modules['attune'] = None\n"
        "from attune_harness.cli import main\n"
        "raise SystemExit(main(sys.argv[1:]))\n"
    )
    package_parent = str(Path(attune_harness.__file__).resolve().parents[1])
    existing = os.environ.get("PYTHONPATH")
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([package_parent, existing]) if existing else package_parent,
    }
    result = subprocess.run(
        [sys.executable, "-c", code, *[str(a) for a in argv]],
        cwd=cwd,
        text=True,
        capture_output=True,
        env=env,
        timeout=600,
    )
    payload = json.loads(result.stdout) if result.stdout.strip() else None
    return result.returncode, payload, result.stderr


def git(root, *args):
    hooks = root.parent / "no-hooks"  # an empty hooks directory, read the same by Git everywhere
    hooks.mkdir(exist_ok=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "commit.gpgsign=false",
            "-c",
            f"core.hooksPath={hooks}",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            *args,
        ],
        check=True,
        capture_output=True,
    )


def probe(argv, oracle):
    environment = {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"}
    if os.name == "nt":  # the Windows probe contract wants one frozen SystemRoot
        environment["SystemRoot"] = os.environ.get("SystemRoot", r"C:\Windows")
    return {
        "argv": [sys.executable, "-B", *argv],
        "cwd": ".",
        "timeout": 10,
        "max_output_bytes": 2048,
        "environment": environment,
        "oracle_paths": [oracle],
    }


@pytest.fixture
def journey(tmp_path):
    """A Git checkout, a participant registry, a frozen effects manifest and the request file."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "source.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    (root / "plan.md").write_text("Preserve all findings and default JSON.\n", encoding="utf-8")
    (root / "baseline.py").write_text(
        "from source import value\nassert value()==1\n", encoding="utf-8"
    )
    (root / "oracle.py").write_text(
        "from source import value\nassert value()==42\n", encoding="utf-8"
    )
    (root / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    docs = root / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text(
        "The exporter answers 42. See [reference](reference.md).\n", encoding="utf-8"
    )
    (docs / "reference.md").write_text("# Reference\nThe exporter returns 42.\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    git(root, "add", "source.py", "plan.md", "baseline.py", "oracle.py", "pytest.ini", "docs")
    git(root, "commit", "-qm", "Fixture baseline")

    peer = tmp_path / "peer.py"
    peer.write_text(PEER, encoding="utf-8")
    command = {
        "adapter": "command",
        "command": [sys.executable, "-B", str(peer)],
        "timeout": 30,
        "tools": [],
        "max_turns": 1,
        "max_tool_calls": 0,
    }
    deterministic = {"adapter": "deterministic", "tools": [], "max_turns": 1, "max_tool_calls": 0}
    config = tmp_path / "participants.json"
    config.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "participants": {"local": command, "critic": command, "assessor": deterministic},
            }
        ),
        encoding="utf-8",
    )
    # The review intake wants its verification context inside the project.
    context = root / "context.json"
    context.write_text(json.dumps({"schema_version": 1, "project_root": "."}), encoding="utf-8")

    directory = tmp_path / "work"
    control = {
        "id": "baseline",
        "kind": "check",
        "owner": "host",
        "version": 1,
        "required": True,
        "phases": ["build"],
    }
    scope = [EXPORT, GENERATED, "source.py"]
    effects = work_effects.freeze(
        root,
        scope,
        ["pkg", "tests", "tests/generated"],
        ["baseline.py", "oracle.py", "plan.md", "pytest.ini"],
        [
            {
                "control": work_effects.identity(control),
                "probe": probe(["baseline.py"], "baseline.py"),
            }
        ],
        directory,
        verification=[
            {
                "task_id": "export",
                "probe": probe(
                    ["-c", "from pkg.export import answer;assert answer()==42"], "oracle.py"
                ),
            },
            *[
                {"task_id": n, "probe": probe(["oracle.py"], "oracle.py")}
                for n in ("wire", "final")
            ],
        ],
    )
    acceptance = ["value returns 42 without changing protected checks"]
    request = {
        "intent": {
            "goal": GOAL,
            "context": ["Default JSON must survive"],
            "scope": scope,
            "constraints": ["Preserve unknown claims"],
            "acceptance": acceptance,
            "questions": [],
        },
        "assignments": [
            {
                "role": "planner",
                "participant": "local",
                "output_contract": "Ordered task plan",
                "budgets": BUDGET,
            },
            {
                "role": "worker",
                "participant": "local",
                "output_contract": "Scoped file proposal",
                "budgets": BUDGET,
            },
            {
                "role": "reviewer",
                "participant": "critic",
                "output_contract": "Evidence-backed critique",
                "budgets": BUDGET,
            },
        ],
        "controls": [control],
        "tasks": [
            {
                "id": "export",
                "objective": "Create exporter and supplemental test",
                "dependencies": [],
                "outputs": [EXPORT, GENERATED],
                "checks": ["answer returns 42"],
            },
            {
                "id": "wire",
                "objective": "Use exporter in the existing function",
                "dependencies": ["export"],
                "outputs": ["source.py"],
                "checks": acceptance,
            },
        ],
        "inputs": ["source.py"],
        "artifact": "plan.md",
        "budget": BUDGET,
        "effects": effects,
    }
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    return {
        "root": root,
        "config": config,
        "context": context,
        "directory": directory,
        "request": request_path,
        "cwd": tmp_path,
        "review_dir": tmp_path / "review",
    }


def test_plan_accept_build_review_and_status_with_attune_absent(journey):
    cwd = journey["cwd"]
    directory = journey["directory"]

    code, envelope, err = child(
        [
            "plan",
            "--task-dir",
            directory,
            "--project",
            journey["root"],
            "--config",
            journey["config"],
            "--request",
            journey["request"],
        ],
        cwd,
    )
    assert code == 0, (envelope, err)
    assert envelope["status"] == "draft" and not envelope["questions"]["missing"]
    checkpoint = envelope["checkpoint_digest"]

    code, envelope, err = child(
        ["plan", "--task-dir", directory, "--accept", "--checkpoint", checkpoint], cwd
    )
    assert code == 0, (envelope, err)
    assert envelope["status"] == "accepted"
    assert envelope["receipt"]["disposition"] == "approve_task"

    code, envelope, err = child(["build", directory, "--allow-external"], cwd)
    error = ((envelope or {}).get("error") or {}) if code == 2 else {}
    if os.name == "nt" and error.get("type") == "FeatureUnavailable":
        # Recorded, not skipped: the Windows effects profile refused, in its own words and no other's.
        assert error["detail"].startswith(("Windows effects require", "Windows WCHAR layout")), envelope
        built = False
    else:
        assert code == 0, (envelope, err)
        assert envelope["status"] == "completed", envelope
        assert envelope["blocking"] is False and envelope["execution_evidence"]["runs"], envelope
        operations = envelope["execution_evidence"]["runs"][0]["operations"]
        assert [o["operation"] for o in operations if o["kind"] == "build_control"] == ["control:baseline"]
        turns = [
            o["participant_reported_adapter_identity"]["value"]["adapter"]
            for o in operations
            if o["kind"] == "participant_turn"
        ]
        assert len(turns) == 3 and set(turns) == {"command"}, turns
        built = True
        assert (journey["root"] / EXPORT).read_text(encoding="utf-8").startswith("def answer():")

    code, envelope, err = child(
        [
            "review",
            "--goal",
            "Check the guide against the exporter's evidence",
            "--project",
            journey["root"],
            "--config",
            journey["config"],
            "--document",
            "docs/guide.md",
            "--context",
            journey["context"],
            "--corpus",
            "docs",
            "--query",
            "exporter",
            "--criteria",
            "Identify unsupported claims and preserve uncertainty",
            "--assessor",
            "assessor",
            "--accept",
            "--task-dir",
            journey["review_dir"],
        ],
        cwd,
    )
    assert code == 0, (code, envelope, err)
    assert envelope["operation"] == "task" and envelope["status"] == "completed", envelope
    participants = envelope["execution"]["participants"]
    assert [p["adapter"] for p in participants.values()] == ["deterministic"], participants

    code, envelope, err = child(["status", directory], cwd)
    assert code == 0, (envelope, err)
    assert envelope["status"] == ("completed" if built else "accepted"), envelope
