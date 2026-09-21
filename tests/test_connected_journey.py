"""Real command peers, repair/test provenance, and existing Spec controls.

No provider calls. Synthetic human submissions qualify the collector contract,
not a user's acceptance; the executor still owns the Spec result publication.
"""

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from attune_harness.cli import main
from attune_harness.review_store import RunStore
from attune_harness.task_contract import read_task
from attune_harness.task_policies import execute_task, inspect_task
from attune_harness.test_change import accept_test_task, create_test_task


@pytest.fixture
def journey(tmp_path):
    root = tmp_path / "checkout"
    root.mkdir()
    files = {
        "app.py": "def add(a,b):\n    return a-b\n",
        "probe.py": "from app import add\nassert add(2,3)==5\n",
        "tests/test_app.py": "from app import add\ndef test_add():\n    assert add(2,3)==5\n",
        ".gitignore": "__pycache__/\n.pytest_cache/\n",
        "guide.md": "Addition must satisfy 2+3=5.\n",
    }
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    (root / "unrelated.txt").write_text("Preserve this user's dirty work.\n")
    (tmp_path / "context.json").write_text(
        '{"schema_version":1,"project_root":"checkout"}'
    )
    peer = tmp_path / "peer.py"
    peer.write_text(
        """import json,sys
from pathlib import Path
p=json.load(sys.stdin);t=p['turn'];e=t.get('repair');fault=sys.argv[2]
with open(sys.argv[1],'a') as f:f.write(json.dumps(p)+'\\n')
if e is None and t.get('result_profile')=='assessment-findings-v1':
    finding=({'id':'addition-direction','severity':'high','text':'Addition subtracts its operands.','evidence':['checkout/app.py returns a-b','probe.py expects 2+3=5']} if t['role']=='assessor' else None)
    v=json.dumps({'schema_version':1,'kind':'assessment-findings-v1','findings':([finding] if finding else []),'notes':['Independent reviewer found no additional repair candidates.']})
elif e is None:v='Inspect app.py: addition subtracts; validate against probe.py.'
elif t['role']=='worker':
    v=json.dumps({'schema_version':1,'replacements':[{'path':'app.py','before_sha256':e['before_hashes']['app.py'],'text':'def add(a,b):\\n    return '+('0' if fault=='wrong' else 'a+b')+'\\n'}]})
else:
    if fault=='missing-review':sys.exit(7)
    v=json.dumps({'schema_version':1,'artifact_digest':e['artifact_digest'],'probe_digest':e['probe_digest'],'verdict':'approve','findings':(['Unresolved defect'] if fault=='findings' else [])})
print(json.dumps({'schema_version':1,'request_digest':p['request_digest'],'action':{'kind':'final','text':v}}))
"""
    )
    registry = tmp_path / "registry.json"

    def configure(fault="good"):
        registry.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "participants": {
                        name: {
                            "adapter": "command",
                            "command": [
                                sys.executable,
                                "-I",
                                str(peer),
                                str(tmp_path / "calls.jsonl"),
                                fault,
                            ],
                            "timeout": 10,
                            "tools": [],
                            "max_turns": 1,
                            "max_tool_calls": 0,
                        }
                        for name in ("worker", "reviewer")
                    },
                }
            )
        )

    configure()
    probe = tmp_path / "probe.json"
    probe.write_text(
        json.dumps(
            {
                "argv": [sys.executable, "-B", "probe.py"],
                "cwd": ".",
                "timeout": 10,
                "max_output_bytes": 4096,
                "environment": {
                    "PATH": "/usr/bin:/bin",
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONNOUSERSITE": "1",
                },
                "oracle_paths": ["probe.py"],
            }
        )
    )
    return tmp_path, root, registry, probe, configure


def repair_args(journey, *, assessment=False):
    work, root, registry, probe, _ = journey
    args = [
        "fix",
        "--goal",
        "Correct addition",
        "--project",
        str(work),
        "--config",
        str(registry),
        "--checkout",
        str(root),
        "--scope",
        "app.py",
        "--probe",
        str(probe),
        "--criteria",
        "2+3=5; preserve tests",
        "--worker",
        "worker",
        "--reviewer",
        "reviewer",
        "--task-dir",
        str(work / "repair"),
        "--accept",
        "--allow-external",
    ]
    if assessment:
        args.extend([
            "--from-assessment",
            str(work / "assessment"),
            "--finding-id",
            "addition-direction",
        ])
    return args


def complete(journey, capsys):
    assert main(repair_args(journey)) == 0, capsys.readouterr().out
    capsys.readouterr()
    return journey[0] / "repair"


def linked(journey, directory=None):
    return create_test_task(
        None,
        directory or journey[0] / "tested",
        source_task=journey[0] / "repair",
        interpreter=sys.executable,
    )


def run_linked(journey):
    task = linked(journey)
    directory = Path(task["record_path"]).parent
    accept_test_task(directory, task["checkpoint_digest"])
    return execute_task(directory)


def test_real_cli_assessment_repair_test_recovery_and_spec(journey):
    work, root, registry, _, _ = journey
    commands = []

    def invoke(args, expected):
        started = time.monotonic()
        result = subprocess.run(
            [sys.executable, "-B", "-m", "attune_harness", *args],
            cwd=work,
            capture_output=True,
            text=True,
            timeout=45,
        )
        assert result.returncode == expected, result.stdout + result.stderr
        commands.append(
            {
                "argv": args,
                "exit_code": result.returncode,
                "elapsed_seconds": time.monotonic() - started,
            }
        )
        return json.loads(result.stdout)

    assessment = invoke(
        [
            "review",
            "--goal",
            "Assess addition",
            "--project",
            str(work),
            "--config",
            str(registry),
            "--task-dir",
            str(work / "assessment"),
            "--criteria",
            "Describe evidence and uncertainty",
            "--query",
            "addition",
            "--document",
            "checkout/guide.md",
            "--context",
            "context.json",
            "--corpus",
            "checkout",
            "--plan",
            "independent-review",
            "--assessor",
            "worker",
            "--reviewer",
            "reviewer",
            "--repair-findings",
            "--allow-external",
            "--accept",
        ],
        0,
    )
    assert assessment["execution"]["integration"]["acceptance_status"] == "unverified"
    # The source supplies identity only; repair authority remains explicit here.
    paused = invoke([*repair_args(journey, assessment=True), "--pause-after", "3"], 1)
    assert paused["status"] == "paused"
    source = paused["request"]["repair"]["source_assessment"]
    assert source["task_id"] == assessment["request"]["task_id"]
    assert [finding["id"] for finding in source["findings"]] == [
        "addition-direction"
    ]
    inode = (root / "app.py").stat().st_ino
    fixed = invoke(["resume", str(work / "repair")], 0)
    assert fixed["status"] == "completed"
    assert (root / "app.py").stat().st_ino == inode
    repair_bytes = (work / "repair/record.json").read_bytes()
    calls = (work / "calls.jsonl").read_bytes()
    preview = invoke(
        [
            "test",
            "--from-task",
            str(work / "repair"),
            "--interpreter",
            sys.executable,
            "--task-dir",
            str(work / "tested"),
        ],
        1,
    )
    assert preview["status"] == "draft"
    assert not (work / "tested/inputs").exists()
    saved_preview = read_task(work / "tested")
    assert (
        saved_preview["request"]["source_task"]["task_id"]
        == fixed["request"]["task_id"]
    )
    assert saved_preview["request"]["selection"]["scope"] == ["app.py"]
    invoke(
        [
            "test",
            "--task-dir",
            str(work / "tested"),
            "--checkpoint",
            preview["checkpoint_digest"],
            "--accept",
            "--pause-after",
            "1",
        ],
        1,
    )
    result = invoke(["resume", str(work / "tested")], 0)
    assert result["presentation"]["current_result"]["outcome"] == "passed"
    assert fixed["request"]["task_id"] in result["presentation"]["markdown"]
    test_bytes = (work / "tested/record.json").read_bytes()
    invoke(["resume", str(work / "tested")], 0)
    invoke(["status", str(work / "tested")], 0)
    assert test_bytes == (work / "tested/record.json").read_bytes()
    assert repair_bytes == (work / "repair/record.json").read_bytes()
    assert calls == (work / "calls.jsonl").read_bytes()
    assert len(calls.splitlines()) == 4
    assert (root / "unrelated.txt").read_text() == "Preserve this user's dirty work.\n"
    asyncio.run(
        spec_control(work / "human", inspect_task(work / "tested"), "approve_task")
    )
    (work / "journey-summary.json").write_text(
        json.dumps(
            {
                "mode": "synthetic command peers and human collector submissions; no providers",
                "commands": commands,
                "participant_calls": 4,
                "producer_record_unchanged": True,
                "test_resume_unchanged": True,
                "assessment_to_repair": "selected finding identity; separate executor-selected goal/scope/probe",
                "spec_publication": "executor-published actual test evidence; no automatic CLI bridge",
                "assessment_task_id": assessment["request"]["task_id"],
                "repair_task_id": fixed["request"]["task_id"],
                "test_task_id": saved_preview["request"]["task_id"],
                "model_cost": "not applicable to synthetic command peers; native costs unmeasured",
            },
            indent=2,
        )
        + "\n"
    )


async def spec_control(root, result, decision):
    """Real installed optional AI Spec host; no fake human acceptance receipt."""
    pytest.importorskip(
        "attune.spec.workspace", reason="optional AI Spec integration profile"
    )
    from attune.elicitation.command_workspace import (
        CommandWorkspaceHost,
        CommandWorkspaceError,
    )
    from attune.spec.state import SpecState, save_state, load_state
    from attune.spec.workspace import SpecWorkspaceAdapter
    from attune_harness.spec_handoff import bind_test_evidence

    (root / ".claude/plans").mkdir(parents=True)
    (root / ".git").mkdir()
    plan = root / ".claude/plans/journey.md"
    plan.write_text(
        '<task id="1" name="repair-and-test"><objective>Repair and test addition</objective></task>\n'
    )
    save_state(
        SpecState(plan_path=str(plan), current="1", completed=[], auto_run=False)
    )
    host = CommandWorkspaceHost()
    host.register(SpecWorkspaceAdapter(root))
    view = await host.open(
        "spec", {"route": "resume", "plan_path": ".claude/plans/journey.md"}
    )
    passed = result["presentation"]["current_result"]["outcome"] == "passed"
    event = {
        "kind": "task_result",
        "task_id": "1",
        "test_evidence": bind_test_evidence(Path(result["record_path"]).parent),
        "severity": "low" if passed else "high",
        "score": 100 if passed else 0,
        "probes": [result["record_path"]],
        "detail": json.dumps(
            {
                "outcome": result["presentation"]["current_result"]["outcome"],
                "checkpoint": result["checkpoint_digest"],
                "source_task": result["request"]["source_task"],
                "qualification": "synthetic collector interaction; executor-published evidence",
            }
        ),
    }
    view = await host.publish(view.record.workspace_id, event)
    payload = {
        "__elicitation_response__": True,
        "title": view.record.view.title,
        "view": view.record.view.id.value,
        "action": decision,
        "confirmed": False,
        **view.record.binding.to_payload(),
    }
    stale = dict(payload, revision=payload["revision"] - 1)
    with pytest.raises(CommandWorkspaceError):
        await host.collect(stale)
    if not passed:
        with pytest.raises(CommandWorkspaceError):
            await host.collect({**payload, "action": "approve_task"})
    done = await host.collect(payload)
    with pytest.raises(CommandWorkspaceError):
        await host.collect(payload)
    if passed:
        assert done.record.terminal
        save_state(SpecState(**{**done.result["save_state"], "plan_path": str(plan)}))
        saved = load_state(str(plan))
        assert saved.completed == ["1"]
        assert saved.task_receipts[0]["detail"] == event["detail"]
        assert saved.task_receipts[0]["disposition"] == decision
        resumed = CommandWorkspaceHost()
        resumed.register(SpecWorkspaceAdapter(root))
        with pytest.raises(CommandWorkspaceError, match="already complete"):
            await resumed.open(
                "spec", {"route": "resume", "plan_path": ".claude/plans/journey.md"}
            )
        assert result["request"]["source_task"]["task_id"] in done.render.markdown
    else:
        assert not done.record.terminal
        assert not done.record.state.completed


@pytest.mark.parametrize("fault", ["wrong", "missing-review", "findings"])
def test_failed_or_unreviewed_repair_cannot_handoff(journey, capsys, fault):
    journey[4](fault)
    assert main(repair_args(journey)) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "failed"
    with pytest.raises(ValueError, match="completed repair"):
        linked(journey)
    assert not (journey[0] / "tested").exists()


def test_unfinished_repair_cannot_handoff(journey, capsys):
    assert main([*repair_args(journey), "--intake-only"]) == 0
    capsys.readouterr()
    with pytest.raises(ValueError, match="completed repair"):
        linked(journey)


@pytest.mark.parametrize("damage", ["source", "registry", "checkpoint", "missing"])
def test_changed_producer_blocks_preview_acceptance_and_saved_success(
    journey, capsys, damage
):
    repair = complete(journey, capsys)
    preview = linked(journey)
    tested = journey[0] / "tested"
    # Execute a second task before damage to check historical success cannot be reused.
    saved = linked(journey, journey[0] / "prior")
    accept_test_task(journey[0] / "prior", saved["checkpoint_digest"])
    assert (
        execute_task(journey[0] / "prior")["presentation"]["current_result"]["outcome"]
        == "passed"
    )
    if damage == "source":
        (journey[1] / "app.py").write_text("def add(a,b):\n    return 0\n")
    elif damage == "registry":
        journey[2].write_text(journey[2].read_text() + "\n")
    elif damage == "checkpoint":
        record = read_task(repair)
        record["execution"]["integration"]["scope"] += "; later host annotation"
        RunStore(repair, existing=True).save(record)
    else:
        (repair / "record.json").unlink()
    with pytest.raises((ValueError, OSError)):
        accept_test_task(tested, preview["checkpoint_digest"])
    assert not (tested / "inputs").exists()
    assert (
        inspect_task(journey[0] / "prior")["presentation"]["current_result"]["outcome"]
        == "blocked"
    )
    with pytest.raises((ValueError, OSError)):
        execute_task(journey[0] / "prior")


@pytest.mark.parametrize(
    "damage", ["review", "probe", "artifact", "patch", "missing-patch"]
)
def test_inconsistent_host_evidence_rejected(journey, capsys, damage):
    repair = complete(journey, capsys)
    record = read_task(repair)
    run = record["execution"]
    if damage == "review":
        run["review"]["findings"] = ["Unresolved defect"]
    elif damage == "probe":
        run["after_probe"]["passed"] = False
    elif damage == "artifact":
        run["integration"]["artifact_digest"] = "0" * 64
    elif damage == "patch":
        run["patch"]["replacements"][0]["text"] = "not the applied artifact"
    else:
        del run["patch"]
    RunStore(repair, existing=True).save(record)
    with pytest.raises(ValueError):
        linked(journey)


@pytest.mark.parametrize("override", ["project", "scope"])
def test_handoff_rejects_input_overrides(journey, capsys, override):
    complete(journey, capsys)
    kw = {"project": None, "scope": None}
    kw[override] = journey[1] if override == "project" else ["app.py"]
    with pytest.raises(ValueError, match="overrides"):
        create_test_task(
            directory=journey[0] / "tested",
            source_task=journey[0] / "repair",
            interpreter=sys.executable,
            **kw,
        )
    args = [
        "test",
        "--from-task",
        str(journey[0] / "repair"),
        "--task-dir",
        str(journey[0] / "tested"),
        "--interpreter",
        sys.executable,
        "--" + override,
        str(journey[1]) if override == "project" else "app.py",
    ]
    assert main(args) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "blocked"


def test_passed_probe_failed_tests_require_existing_high_gate(journey, capsys):
    (journey[1] / "tests/test_app.py").write_text(
        "from app import add\ndef test_add():\n    assert add(2,3)==999\n"
    )
    complete(journey, capsys)
    result = run_linked(journey)
    assert result["presentation"]["current_result"]["outcome"] == "failed"
    assert result["execution"]["result"]["pytest"]["failed"] == 1
    asyncio.run(spec_control(journey[0] / "human", result, "fix_retry"))


def test_lost_producer_during_test_cannot_publish_pass(journey, capsys, monkeypatch):
    from attune_harness import test_execution

    complete(journey, capsys)
    invoke = test_execution.process.invoke

    def lose(*args, **kwargs):
        result = invoke(*args, **kwargs)
        (journey[0] / "repair/record.json").unlink()
        return result

    monkeypatch.setattr(test_execution.process, "invoke", lose)
    result = run_linked(journey)
    assert result["presentation"]["current_result"]["outcome"] == "blocked"
    assert result["execution"]["result"]["outcome"] == "blocked"


@pytest.mark.parametrize(
    "damage", ["summary", "wrong-artifact", "false-success", "before", "duplicate"]
)
def test_recomputed_summary_hashes_cannot_replace_journaled_probes(
    journey, capsys, damage
):
    from attune_harness.review_contract import digest

    repair = complete(journey, capsys)
    record = read_task(repair)
    run = record["execution"]
    event = next(e for e in run["events"] if e["operation_key"] == "probe:after")
    if damage == "before":
        run["before_probe"]["returncode"] = 0
        before = next(e for e in run["events"] if e["operation_key"] == "probe:before")
        before["result"] = dict(run["before_probe"])
    elif damage == "duplicate":
        run["events"].append(dict(event, event_id="duplicate"))
    else:
        if damage == "false-success":
            run["after_probe"]["returncode"] = 9
        else:
            run["after_probe"]["artifact_digest"] = "0" * 64
        if damage != "summary":
            event["result"] = dict(run["after_probe"])
        run["integration"]["probe_digest"] = digest(run["after_probe"])
        run["review"]["probe_digest"] = digest(run["after_probe"])
        run["integration"]["review"] = dict(run["review"])
    RunStore(repair, existing=True).save(record)
    with pytest.raises(ValueError):
        linked(journey)


def test_completed_standalone_test_is_not_a_repair_producer(journey, capsys):
    complete(journey, capsys)
    result = run_linked(journey)
    assert result["presentation"]["current_result"]["outcome"] == "passed"
    with pytest.raises(ValueError, match="completed repair"):
        create_test_task(
            None,
            journey[0] / "third",
            source_task=journey[0] / "tested",
            interpreter=sys.executable,
        )


def test_accepted_no_review_policy_remains_available(journey, capsys):
    args = repair_args(journey)
    at = args.index("--reviewer")
    del args[at : at + 2]
    assert main([*args, "--review", "none"]) == 0
    capsys.readouterr()
    result = run_linked(journey)
    assert result["presentation"]["current_result"]["outcome"] == "passed"
    assert read_task(journey[0] / "repair")["request"]["repair"]["review"] == "none"


@pytest.mark.parametrize("damage", ["reject", "missing", "identity", "projection"])
def test_review_summary_cannot_replace_journaled_participant_response(
    journey, capsys, damage
):
    repair = complete(journey, capsys)
    record = read_task(repair)
    run = record["execution"]
    event = next(
        e
        for e in run["events"]
        if e["kind"] == "participant_turn" and e["participant_id"] == "reviewer"
    )
    if damage == "reject":
        reply = json.dumps(
            {**run["review"], "verdict": "reject", "findings": ["Unresolved defect"]}
        )
        event["result"]["action"]["text"] = reply
        run["participants"]["reviewer"]["text"] = reply
    elif damage == "missing":
        run["events"].remove(event)
    elif damage == "identity":
        event["participant_id"] = "worker"
    else:
        run["participants"]["reviewer"]["text"] = "{}"
    RunStore(repair, existing=True).save(record)
    with pytest.raises(ValueError):
        linked(journey)
