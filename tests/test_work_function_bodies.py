"""Production function-body edit boundary and response contract 3."""

import copy
import json
import subprocess
import sys

import pytest

import test_work_build as builds
import test_work_contract as contracts
from attune_harness import repair, work_build, work_effects
from attune_harness.work_contract import response_contract
from attune_harness.review_contract import canonical
from attune_harness.review_store import PersistenceError, RunStore
from attune_harness.recovery import UnresolvedOperation
from attune_harness.task_contract import read_task
from attune_harness.work_contract import create_work, revise_work
from attune_harness.work_runtime import build_work, reconcile_work_effect
from attune_harness.work_cli import _evidence

work = contracts.work


SOURCE = (
    "# café\nVALUE = 7\n\n@decorator\ndef target(value: int = 3) -> int:\n"
    "    # leading body comment\n    return value - 1\n"
    "    # trailing body comment\n\n# untouched tail\ndef other():\n    return VALUE\n"
)


def body_plan(tmp_path, source=SOURCE, *, symbol="target"):
    root = tmp_path / "checkout"
    state = tmp_path / "state"
    root.mkdir()
    state.mkdir()
    (root / ".git").mkdir()
    (root / "subject.py").write_bytes(source.encode("utf-8"))
    return root, work_effects.freeze(
        root,
        ["subject.py"],
        [],
        ["subject.py.guard"],
        [],
        state,
        function_bodies={"subject.py": symbol},
    )


@pytest.fixture
def bounded(tmp_path):
    root = tmp_path / "checkout"
    state = tmp_path / "state"
    root.mkdir()
    state.mkdir()
    (root / ".git").mkdir()
    (root / "subject.py").write_bytes(SOURCE.encode())
    (root / "guard.txt").write_text("fixed\n")
    plan = work_effects.freeze(
        root,
        ["subject.py"],
        [],
        ["guard.txt"],
        [],
        state,
        function_bodies={"subject.py": "target"},
    )
    return root, plan


def proposal(body="    return value + 1\n"):
    return {"schema_version": 3, "bodies": [{"path": "subject.py", "body": body}]}


class BodyWorker:
    body = "    return 42\n"
    bodies = {}
    calls = 0

    def __init__(self, config, cwd, *, profile):
        self.profile = profile
        self.last_identity = None

    def __call__(self, raw):
        wire = json.loads(raw)
        turn = wire["turn"]
        type(self).calls += 1
        payload = (
            {"kind": "critique", "findings": [], "notes": []}
            if turn["role"] == "reviewer"
            else {
                "schema_version": 3,
                "bodies": [
                    {
                        "path": path,
                        "body": type(self).bodies.get(path, type(self).body),
                    }
                    for path in turn["step"]["outputs"]
                ],
            }
        )
        self.last_identity = {"adapter": "scripted-local", "profile": self.profile}
        return canonical(
            {
                "schema_version": 1,
                "request_digest": wire["request_digest"],
                "action": {"kind": "final", "text": canonical(payload)},
            }
        )


def prepare_body_build(work, *, two_steps=False):
    BodyWorker.bodies = {}
    root, config, original = work
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "oracle.py").write_text("from source import value\nassert value()==42\n")
    (root / "baseline.py").write_text("from source import value\nassert value()==1\n")
    if two_steps:
        (root / "second.py").write_text("def second():\n    return 1\n")
        (root / "first_oracle.py").write_text(
            "from source import value\nassert value()==42\n"
        )
        (root / "oracle.py").write_text(
            "from source import value\nfrom second import second\n"
            "assert value()==42 and second()==42\n"
        )
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
            "baseline",
        ],
        check=True,
    )
    data = copy.deepcopy(original)
    scope = ["source.py", "second.py"] if two_steps else ["source.py"]
    data["intent"].update(scope=scope, acceptance=["selected functions return 42"])
    budget = {**contracts.BUDGET, "max_operations": 20, "max_output_bytes": 32768}
    data["budget"] = budget
    data["assignments"] = [
        {**data["assignments"][0], "budgets": budget},
        {
            "role": "worker",
            "participant": "local",
            "output_contract": "body",
            "budgets": budget,
        },
        {
            "role": "reviewer",
            "participant": "critic",
            "output_contract": "critique",
            "budgets": budget,
        },
    ]
    data["tasks"] = [
        {
            "id": "wire",
            "objective": "update value",
            "dependencies": [],
            "outputs": ["source.py"],
            "checks": ["value returns 42"],
        }
    ]
    if two_steps:
        data["tasks"].append(
            {
                "id": "second",
                "objective": "update second",
                "dependencies": ["wire"],
                "outputs": ["second.py"],
                "checks": ["both selected functions return 42"],
            }
        )
    data["controls"] = []

    def probe(script, oracle):
        return {
            "argv": [sys.executable, "-B", script],
            "cwd": ".",
            "timeout": 10,
            "max_output_bytes": 2048,
            "environment": {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"},
            "oracle_paths": [oracle],
        }

    data["effects"] = work_effects.freeze(
        root,
        scope,
        [],
        [
            "plan.md",
            "oracle.py",
            "baseline.py",
            *(["first_oracle.py"] if two_steps else []),
        ],
        [],
        data["directory"],
        verification=(
            [
                {
                    "task_id": "wire",
                    "probe": probe("first_oracle.py", "first_oracle.py"),
                },
                {"task_id": "second", "probe": probe("oracle.py", "oracle.py")},
                {"task_id": "final", "probe": probe("oracle.py", "oracle.py")},
            ]
            if two_steps
            else [
                {"task_id": name, "probe": probe("oracle.py", "oracle.py")}
                for name in ("wire", "final")
            ]
        ),
        function_bodies={
            "source.py": "value",
            **({"second.py": "second"} if two_steps else {}),
        },
    )
    record = create_work(root, config, **data)
    record = contracts.accept((root, config, data), record, supported_controls=[])
    return root, data["directory"], record


def test_materializes_only_selected_body_and_preserves_surrounding_bytes(bounded):
    root, plan = bounded
    item = work_effects.operations(
        plan, proposal("    # note\n    return value + 1\n\n")
    )[0]
    original = (root / "subject.py").read_bytes()
    work_effects.write_effect(plan, item)
    candidate = (root / "subject.py").read_bytes()
    assert candidate.startswith(original[: original.index(b"    # leading")])
    assert candidate.endswith(original[original.index(b"\n# untouched tail") :])
    assert b"return value + 1" in candidate


@pytest.mark.parametrize(
    "body",
    [
        "VALUE = 99\n    return value\n",
        "    return value + 1\nVALUE = 99\n",
        "# escaped comment\n    return value\n",
        "    break\n",
        "    return (\n",
        "    return " + "+".join(["1"] * 1000) + "\n",
        "    return value - 1\n",
    ],
)
def test_escape_compile_and_unchanged_bodies_fail_closed(bounded, body):
    _, plan = bounded
    with pytest.raises(ValueError):
        work_effects.operations(plan, proposal(body))


def test_multiline_string_column_zero_and_unicode_are_supported(bounded):
    _, plan = bounded
    text = work_effects.operations(
        plan,
        proposal('    """naïve\ncolumn zero text\n    """\n    return value + 1\n'),
    )[0]["text"]
    assert "column zero text" in text and "café" in text


@pytest.mark.parametrize(
    "source",
    [
        SOURCE.replace("\n", "\r\n"),
        SOURCE.replace("    return", "\treturn"),
        "# coding: latin-1\n" + SOURCE,
        "def target(): return 1\n",
        "def target():\n    return 1\ndef target():\n    return 2\n",
    ],
)
def test_freeze_rejects_unsupported_sources(tmp_path, source):
    root = tmp_path / "checkout"
    state = tmp_path / "state"
    root.mkdir()
    state.mkdir()
    (root / ".git").mkdir()
    (root / "subject.py").write_bytes(source.encode())
    (root / "guard.txt").write_text("fixed\n")
    with pytest.raises(ValueError):
        work_effects.freeze(
            root,
            ["subject.py"],
            [],
            ["guard.txt"],
            [],
            state,
            function_bodies={"subject.py": "target"},
        )


def test_direct_write_and_reconcile_revalidate_forged_full_files(bounded):
    _, plan = bounded
    item = work_effects.operations(plan, proposal())[0]
    forged = {**item, "text": item["text"] + "GLOBAL = 9\n"}
    with pytest.raises(ValueError):
        work_effects.write_effect(plan, forged)
    event = {
        "event_id": "e",
        "kind": "file_effect",
        "state": "pending",
        "phase": "dispatching",
        "attempts": 1,
        "item": forged,
    }
    with pytest.raises(ValueError):
        work_effects.reconcile_effect(plan, [event], "e")


def test_contract_3_turn_binds_symbol_and_decoder_materializes_host_fields(work):
    case = builds.prepare(work)
    root = case[0]
    old = case[2]["request"]
    plan = work_effects.freeze(
        root,
        ["source.py"],
        [],
        ["plan.md", "oracle.py", "pytest.ini", "baseline.py"],
        [],
        case[1],
        function_bodies={"source.py": "value"},
    )
    request = copy.deepcopy(old)
    request["effects"] = plan
    request["tasks"] = [
        {
            "id": "wire",
            "objective": "edit value",
            "dependencies": [],
            "outputs": ["source.py"],
            "checks": ["value changes"],
        }
    ]
    run = {
        "response_contract": 3,
        "source_evidence": {
            "source.py": plan["function_bodies"]["bindings"]["source.py"]["source"]
        },
    }
    turn = work_build.turn(request, run, "worker", request["tasks"][0], [])
    assert turn["function_boundaries"] == [{"path": "source.py", "symbol": "value"}]
    assert set(turn["output_schema"]["bodies"][0]) == {"path", "body"}
    action = {
        "kind": "final",
        "text": json.dumps(
            {
                "schema_version": 3,
                "bodies": [{"path": "source.py", "body": "    return 9\n"}],
            }
        ),
    }
    decoded = work_build.decode(
        action, request, "worker", request["tasks"][0], contract_version=3
    )
    assert decoded["task_id"] == "wire" and decoded["dependencies"] == []
    assert decoded["files"][0]["before_sha256"] == plan["before"]["source.py"]["sha256"]
    assert decoded["files"][0]["text"].endswith("    return 9\n")


def test_planning_contract_helper_still_rejects_version_3():
    with pytest.raises(ValueError, match="Unsupported response contract"):
        response_contract({"response_contract": 3})


def test_body_schema_version_is_strict_integer(bounded):
    _, plan = bounded
    bad = proposal()
    bad["schema_version"] = 3.0
    with pytest.raises(ValueError):
        work_effects.materialize_bodies(bad, plan)


def test_invalid_body_reply_is_retained_and_resume_never_redispatches(work):
    case = prepare_body_build(work)
    BodyWorker.calls = 0
    BodyWorker.body = "    break\n"
    failed = build_work(case[1], exchange_factory=BodyWorker)
    assert failed["build"]["status"] == "failed"
    assert len(failed["build"]["events"]) == 1
    assert (
        json.loads(failed["build"]["events"][0]["result"]["action"]["text"])["bodies"][
            0
        ]["body"]
        == "    break\n"
    )
    assert BodyWorker.calls == 1
    evidence, _ = _evidence(failed)
    assert evidence["rejected_reply"]["source"] == "worker"
    resumed = build_work(case[1], exchange_factory=BodyWorker)
    assert resumed == read_task(case[1]) and resumed["build"]["status"] == "failed"
    assert BodyWorker.calls == 1


def test_completed_body_reply_is_valid_status_evidence(work):
    case = prepare_body_build(work)
    BodyWorker.calls = 0
    BodyWorker.body = "    return 42\n"
    completed = build_work(case[1], exchange_factory=BodyWorker)
    assert completed["build"]["status"] == "completed"
    evidence, _ = _evidence(completed)
    assert "rejected_reply" not in evidence


def test_wrong_logic_is_stopped_by_protected_verification(work):
    case = prepare_body_build(work)
    BodyWorker.body = "    return 41\n"
    result = build_work(case[1], exchange_factory=BodyWorker)
    assert result["build"]["status"] == "needs_revision"
    assert result["build"]["events"][-1]["kind"] == "acceptance_probe"
    assert result["build"]["events"][-1]["result"]["passed"] is False


def test_body_build_pauses_and_resumes_without_repeating_reply(work):
    case = prepare_body_build(work)
    BodyWorker.body = "    return 42\n"
    BodyWorker.calls = 0
    paused = build_work(case[1], exchange_factory=BodyWorker, max_operations=1)
    assert paused["build"]["status"] == "paused" and BodyWorker.calls == 1
    completed = build_work(case[1], exchange_factory=BodyWorker)
    assert completed["build"]["status"] == "completed" and BodyWorker.calls == 2
    worker_events = [
        e for e in completed["build"]["events"] if e["kind"] == "participant_turn"
    ]
    assert len(worker_events) == 2  # one worker and one reviewer, each exactly once


def test_stale_actual_source_blocks_body_build_before_dispatch(work):
    case = prepare_body_build(work)
    (case[0] / "source.py").write_text("def value():\n    return 99\n")
    BodyWorker.calls = 0
    with pytest.raises((ValueError, UnresolvedOperation)):
        build_work(case[1], exchange_factory=BodyWorker)
    assert BodyWorker.calls == 0


def test_body_file_lost_ack_reconciles_without_repeating_write(work, monkeypatch):
    case = prepare_body_build(work)
    BodyWorker.body = "    return 42\n"
    original = RunStore.save

    def lose_ack(store, record):
        events = record.get("build", {}).get("events", [])
        if (
            events
            and events[-1]["kind"] == "file_effect"
            and events[-1]["state"] == "completed"
        ):
            raise PersistenceError("synthetic lost acknowledgment")
        return original(store, record)

    with monkeypatch.context() as patch:
        patch.setattr(RunStore, "save", lose_ack)
        with pytest.raises(PersistenceError):
            build_work(case[1], exchange_factory=BodyWorker)
    record = read_task(case[1])
    event = record["build"]["events"][-1]
    assert event["kind"] == "file_effect" and event["phase"] == "dispatching"
    inode = (case[0] / "source.py").stat().st_ino
    reconcile_work_effect(case[1], record["checkpoint_digest"], event["event_id"])
    completed = build_work(case[1], exchange_factory=BodyWorker)
    assert completed["build"]["status"] == "completed"
    assert (case[0] / "source.py").stat().st_ino == inode


def test_forged_saved_body_journal_is_unreadable(work):
    case = prepare_body_build(work)
    BodyWorker.body = "    return 42\n"
    result = build_work(case[1], exchange_factory=BodyWorker)
    event = next(e for e in result["build"]["events"] if e["kind"] == "file_effect")
    event["item"]["text"] += "GLOBAL = 9\n"
    store = RunStore(case[1], existing=True)
    with store.lease():
        store.save(result)
    with pytest.raises(ValueError):
        read_task(case[1])


def test_body_and_materialized_file_byte_limits(bounded):
    _, plan = bounded
    with pytest.raises(ValueError, match="byte limit"):
        work_effects.materialize_bodies(proposal("    #" + "x" * 65536 + "\n"), plan)
    body = "    return '" + "x" * 65500 + "'\n"
    assert len(body.encode()) <= repair.MAX_FILE
    with pytest.raises(ValueError, match="Materialized file exceeds"):
        work_effects.materialize_bodies(proposal(body), plan)


def test_pending_repair_retains_function_binding_and_protects_completion(work):
    case = prepare_body_build(work, two_steps=True)
    BodyWorker.bodies = {
        "source.py": "    return 42\n",
        "second.py": "    return 0\n",
    }
    failed = build_work(case[1], exchange_factory=BodyWorker)
    assert failed["build"]["status"] == "needs_revision"
    historical_build = copy.deepcopy(failed["build"])
    source_inode = (case[0] / "source.py").stat().st_ino
    tasks = copy.deepcopy(failed["request"]["tasks"])
    tasks[1]["objective"] = "repair the pending selected body"
    revised = revise_work(
        case[1],
        checkpoint=failed["checkpoint_digest"],
        changes={"tasks": tasks},
        preserve_completed=True,
    )
    plan = revised["request"]["effects"]
    assert revised["request"]["intent"]["scope"] == ["second.py"]
    assert plan["function_bodies"]["bindings"]["second.py"]["symbol"] == "second"
    assert set(plan["function_bodies"]["bindings"]) == {"second.py"}
    assert "return 0" in plan["function_bodies"]["bindings"]["second.py"]["source"]
    assert "source.py" in plan["protected"]
    with pytest.raises(ValueError, match="current accepted"):
        build_work(case[1], exchange_factory=BodyWorker)
    accepted = contracts.accept(work, revised, supported_controls=[])
    BodyWorker.bodies = {"second.py": "    return 42\n"}
    completed = build_work(
        case[1], checkpoint=accepted["checkpoint_digest"], exchange_factory=BodyWorker
    )
    assert completed["build"]["status"] == "completed"
    assert (case[0] / "source.py").stat().st_ino == source_inode
    assert completed["history"][-1]["build"] == historical_build
    assert completed["history"][-1]["build"]["status"] == "needs_revision"
