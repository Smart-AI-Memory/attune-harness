"""Installed-capable plan/build/control journeys; real local commands only."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import test_work_contract as contracts
import test_work_build as builds

from attune_harness.cli import main
from attune_harness.task_contract import read_task
from attune_harness.review_store import RunStore

work = contracts.work


def invoke(capsys, *args, code=0):
    actual = main(list(map(str, args)))
    output = capsys.readouterr().out
    assert actual == code, output
    return json.loads(output)


def prepare(work):
    root, config, data = work
    peer = root.parent / "peer.py"
    peer.write_text(
        """import json,sys,hashlib
w=json.load(sys.stdin);t=w['turn']
if t['role']=='planner':
 intent=t['work']['intent'];tasks=t['work']['tasks']
 p={'kind':'plan','goal':intent['goal'],'tasks':tasks,'coverage':[{'criterion':c,'tasks':[x['id'] for x in tasks if c in x['checks']]} for c in intent['acceptance']], 'choices':[], 'notes':['Fixed fixture']}
elif t['role'] in ('reviewer','critic'):p={'kind':'critique','findings':[],'notes':['Fixed fixture']}
else:
 texts={'pkg/export.py':'def answer():\\n    return 42\\n','source.py':'from pkg.export import answer\\ndef value():\\n    return answer()\\n','tests/generated/test_app.py':'def test_generated():\\n    assert True\\n'}
 p={'schema_version':1,'task_id':t['step']['id'],'dependencies':t['step']['dependencies'],'files':[{'path':n,'before_sha256':hashlib.sha256(t['source_evidence'][n].encode()).hexdigest() if n in t['source_evidence'] else None,'text':texts[n]} for n in t['step']['outputs']]}
print(json.dumps({'schema_version':1,'request_digest':w['request_digest'],'action':{'kind':'final','text':json.dumps(p)}}))
"""
    )
    registry = json.loads(config.read_text())
    for entry in registry["participants"].values():
        entry.update(
            adapter="command", command=[sys.executable, "-B", str(peer)], timeout=10
        )
    config.write_text(json.dumps(registry))
    _, _, record = builds.prepare(work, accept=False)
    payload = {
        k: v
        for k, v in record["request"].items()
        if k
        in (
            "intent",
            "signals",
            "choices",
            "assignments",
            "controls",
            "tasks",
            "inputs",
            "artifact",
            "effects",
        )
    }
    payload["budget"] = record["request"]["budgets"]
    request = root.parent / "request.json"
    request.write_text(json.dumps(payload))
    return request, root.parent / "cli-work"


def create(work, capsys):
    request, directory = prepare(work)
    r = invoke(
        capsys,
        "plan",
        "--request",
        request,
        "--project",
        work[0],
        "--config",
        work[1],
        "--task-dir",
        directory,
    )
    return directory, r


def test_complete_console_plan_build_status_resume(work, capsys):
    directory, draft = create(work, capsys)
    assert draft["authority"] == "draft" and draft["status"] == "draft"
    uid = draft["task_id"]
    proposal = invoke(
        capsys, "plan", "--task-dir", directory, "--run", "--allow-external"
    )
    assert proposal["status"] == "completed" and proposal["authority"] == "draft"
    assert "--stage" in proposal["next_action"]
    staged = invoke(
        capsys,
        "plan",
        "--task-dir",
        directory,
        "--stage",
        "--checkpoint",
        proposal["checkpoint_digest"],
    )
    assert staged["revision"] == 2 and staged["authority"] == "draft"
    accepted = invoke(
        capsys,
        "plan",
        "--task-dir",
        directory,
        "--accept",
        "--checkpoint",
        staged["checkpoint_digest"],
    )
    assert accepted["authority"] == "accepted" and "decision_markdown" in accepted
    assert (
        read_task(directory)["acceptance"]["collector"]["result"]["disposition"]
        == "approve_task"
    )
    paused = invoke(
        capsys, "build", directory, "--allow-external", "--max-operations", "8", code=1
    )
    assert paused["status"] == "paused" and paused["completed"] == ["export"]
    inspected = invoke(capsys, "status", directory)
    assert inspected["checkpoint_digest"] == paused["checkpoint_digest"]
    done = invoke(
        capsys,
        "resume",
        directory,
        "--checkpoint",
        paused["checkpoint_digest"],
        "--allow-external",
    )
    assert done["status"] == "completed" and done["task_id"] == uid
    assert (work[0] / "source.py").read_text().startswith("from pkg.export")
    assert (work[0] / "unrelated.txt").read_text() == "Keep my dirty work\n"
    assert (
        invoke(capsys, "build", directory, "--allow-external")["checkpoint_digest"]
        == done["checkpoint_digest"]
    )


@pytest.mark.parametrize(
    "action",
    [
        ["--accept"],
        ["--stage"],
        ["--reimport"],
        ["--preserve-completed"],
        ["--allow-native"],
        ["--project", "."],
        ["--max-operations", "0"],
    ],
)
def test_console_rejects_unbound_or_conflicting_actions(work, capsys, action):
    directory, _ = create(work, capsys)
    before = (directory / "record.json").read_bytes()
    invoke(capsys, "plan", "--task-dir", directory, *action, code=2)
    assert (directory / "record.json").read_bytes() == before


def test_console_stale_approval_and_no_implicit_dispatch(work, capsys):
    directory, draft = create(work, capsys)
    invoke(
        capsys,
        "plan",
        "--task-dir",
        directory,
        "--accept",
        "--checkpoint",
        "0" * 64,
        code=2,
    )
    invoke(capsys, "build", directory, code=2)
    accepted = invoke(
        capsys,
        "plan",
        "--task-dir",
        directory,
        "--accept",
        "--checkpoint",
        draft["checkpoint_digest"],
    )
    invoke(capsys, "build", directory, code=2)
    assert "build" not in read_task(directory)
    assert accepted["authority"] == "accepted"


def test_status_preserves_stale_draft_for_inspection(work, capsys):
    directory, _ = create(work, capsys)
    (work[0] / "source.py").write_text("changed evidence")
    result = invoke(capsys, "status", directory)
    assert result["status"] == "stale" and result["freshness_error"]
    assert read_task(directory)["status"] == "draft"


def test_commands_resume_across_real_processes(work):
    request, directory = prepare(work)

    def call(*args, code=0):
        process = subprocess.run(
            [sys.executable, "-B", "-m", "attune_harness", *map(str, args)],
            cwd=work[0].parent,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert process.returncode == code, process.stdout + process.stderr
        return json.loads(process.stdout)

    first = call(
        "plan",
        "--request",
        request,
        "--project",
        work[0],
        "--config",
        work[1],
        "--task-dir",
        directory,
    )
    accepted = call(
        "plan",
        "--task-dir",
        directory,
        "--accept",
        "--checkpoint",
        first["checkpoint_digest"],
    )
    paused = call(
        "build", directory, "--allow-external", "--max-operations", "1", code=1
    )
    assert call("status", directory)["checkpoint_digest"] == paused["checkpoint_digest"]
    done = call("resume", directory, "--allow-external")
    assert done["status"] == "completed" and done["task_id"] == accepted["task_id"]


def test_uncertain_owner_is_reported_without_implicit_resume(work, capsys):
    directory, r = create(work, capsys)
    invoke(
        capsys,
        "plan",
        "--task-dir",
        directory,
        "--accept",
        "--checkpoint",
        r["checkpoint_digest"],
    )
    invoke(
        capsys, "build", directory, "--allow-external", "--max-operations", "1", code=1
    )
    record = read_task(directory)
    record["build"]["status"] = "running"
    store = RunStore(directory, existing=True)
    with store.lease():
        store.save(record)
    r = invoke(capsys, "status", directory)
    assert r["status"] == "unresolved" and "may still be running" in r["note"]


@pytest.mark.parametrize("field,value", [("unexpected", True), ("intent", None)])
def test_bad_request_cannot_create_a_work_owner(work, capsys, field, value):
    request = work[0].parent / "bad.json"
    request.write_text(json.dumps({field: value}))
    invoke(
        capsys,
        "plan",
        "--request",
        request,
        "--project",
        work[0],
        "--config",
        work[1],
        "--task-dir",
        work[2]["directory"],
        code=2,
    )
    assert not work[2]["directory"].exists()


def test_console_answers_and_revision(work, capsys):
    root, config, data = work
    request = root.parent / "request.json"
    request.write_text(
        json.dumps(
            {
                "intent": {**data["intent"], "goal": None},
                "assignments": data["assignments"],
            }
        )
    )
    directory = data["directory"]
    draft = invoke(
        capsys,
        "plan",
        "--request",
        request,
        "--project",
        root,
        "--config",
        config,
        "--task-dir",
        directory,
    )
    assert draft["missing"] == ["goal"]
    answer = root.parent / "answer.json"
    answer.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "checkpoint_digest": draft["checkpoint_digest"],
                "answers": {"answer_0": "Keep every finding"},
            }
        )
    )
    answered = invoke(capsys, "plan", "--task-dir", directory, "--answers", answer)
    assert answered["intent"]["goal"] == "Keep every finding"
    changes = root.parent / "changes.json"
    changes.write_text(json.dumps({"intent": {"goal": "Keep every finding and note"}}))
    revised = invoke(
        capsys,
        "plan",
        "--task-dir",
        directory,
        "--revise",
        changes,
        "--checkpoint",
        answered["checkpoint_digest"],
    )
    assert revised["revision"] == 3 and revised["task_id"] == draft["task_id"]


def test_console_legacy_import_and_reimport(work, capsys):
    from test_work_controls import LEGACY

    root, config, data = work
    plan = root / "legacy.md"
    plan.write_text(LEGACY)
    request = root.parent / "request.json"
    request.write_text(
        json.dumps({"intent": data["intent"], "assignments": data["assignments"]})
    )
    r = invoke(
        capsys,
        "plan",
        "--request",
        request,
        "--import-plan",
        plan,
        "--project",
        root,
        "--config",
        config,
        "--task-dir",
        data["directory"],
    )
    assert r["import_disclosures"] and r["authority"] == "draft"
    plan.write_text(LEGACY.replace("Add export", "Add full export"))
    revised = invoke(
        capsys,
        "plan",
        "--task-dir",
        data["directory"],
        "--reimport",
        "--checkpoint",
        r["checkpoint_digest"],
    )
    assert (
        revised["revision"] == 2
        and revised["tasks"][0]["objective"] == "Add full export"
    )


@pytest.mark.parametrize(
    "command", ["--help", "--help-all", "plan", "build", "status", "resume"]
)
def test_help_needs_no_optional_packages_or_models(command):
    package = Path(__import__("attune_harness").__file__).parent.parent
    args = [command] + ([] if command.startswith("--") else ["--help"])
    code = f'import sys;sys.path.insert(0,{str(package)!r});from attune_harness.cli import main\ntry: main({args!r})\nexcept SystemExit as e: assert e.code==0\nassert not any(n in sys.modules for n in ("attune","attune_forms","attune_verify","attune_rag"))'
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", code],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert "attune-harness" in result.stdout


@pytest.mark.parametrize(
    "verb,flags",
    [
        ("cancel-task", ["--reason", "Stop"]),
        ("transfer-task", ["--assessor", "critic", "--reason", "Switch"]),
        ("reconcile-task", ["--event", "unknown", "--retry-read-only"]),
    ],
)
def test_unqualified_feature_controls_fail_visibly(work, capsys, verb, flags):
    directory, _ = create(work, capsys)
    result = invoke(capsys, verb, directory, *flags, code=2)
    assert result["error"]["detail"]
