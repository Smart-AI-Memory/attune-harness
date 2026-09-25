"""Dependent work uses actual files and protected checks, with scripted proposals."""

import copy
import json
import subprocess
import sys

import pytest
import test_work_contract as contracts

from attune_harness import repair, work_effects
from attune_harness.features import FeatureUnavailable
from attune_harness.review_contract import canonical
from attune_harness.review_store import RunStore, PersistenceError
from attune_harness.recovery import UnresolvedOperation
from attune_harness.task_contract import read_task
from attune_harness.task_policies import execute_task
from attune_harness.work_contract import create_work, revise_work
from attune_harness.work_runtime import build_work, reconcile_work_effect

work = contracts.work
EXPORT = "pkg/export.py"
GENERATED = "tests/generated/test_app.py"


class Worker:
    seen = []
    mutation = None

    def __init__(self, config, cwd, *, profile):
        self.config, self.cwd, self.profile = config, cwd, profile
        self.last_identity = None

    def __call__(self, raw):
        wire = json.loads(raw)
        turn = wire["turn"]
        self.seen.append(copy.deepcopy(turn))
        if turn["role"] == "reviewer":
            payload = {
                "kind": "critique",
                "findings": [],
                "notes": ["Synthetic review; no model quality claim."],
            }
        else:
            texts = {
                EXPORT: "def answer():\n    return 42\n",
                GENERATED: "def test_generated():\n    assert True\n",
                "source.py": "from pkg.export import answer\ndef value():\n    return answer()\n",
            }
            payload = {
                "schema_version": 1,
                "task_id": turn["step"]["id"],
                "dependencies": turn["step"]["dependencies"],
                "files": [
                    {
                        "path": p,
                        "before_sha256": (
                            repair.sha(turn["source_evidence"][p].encode())
                            if p in turn["source_evidence"]
                            else None
                        ),
                        "text": texts[p],
                    }
                    for p in turn["step"]["outputs"]
                ],
            }
        if type(self).mutation:
            type(self).mutation(payload, turn, self)
        self.last_identity = {"adapter": "scripted-local", "profile": self.profile}
        return canonical(
            {
                "schema_version": 1,
                "request_digest": wire["request_digest"],
                "action": {"kind": "final", "text": canonical(payload)},
            }
        )


@pytest.fixture(autouse=True)
def reset_worker():
    Worker.seen = []
    Worker.mutation = None


def prepare(work, *, accept=True):
    root, config, data = work
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "baseline.py").write_text("from source import value\nassert value()==1\n")
    (root / "oracle.py").write_text("from source import value\nassert value()==42\n")
    (root / "pytest.ini").write_text("[pytest]\n")
    subprocess.run(
        [
            "git",
            "-c",
            "maintenance.auto=false",
            "-C",
            str(root),
            "add",
            "source.py",
            "plan.md",
            "baseline.py",
            "oracle.py",
            "pytest.ini",
        ],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-c",
            "maintenance.auto=false",
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
            "Fixture baseline",
        ],
        check=True,
    )
    data = copy.deepcopy(data)
    data["intent"]["scope"] = [EXPORT, GENERATED, "source.py"]
    data["intent"]["acceptance"] = [
        "value returns 42 without changing protected checks"
    ]
    budget = {**contracts.BUDGET, "max_operations": 30, "max_output_bytes": 32768}
    data["budget"] = budget
    data["assignments"] = [
        {**data["assignments"][0], "budgets": budget},
        {
            "role": "worker",
            "participant": "local",
            "output_contract": "Scoped file proposal",
            "budgets": budget,
        },
        {
            "role": "reviewer",
            "participant": "critic",
            "output_contract": "Evidence-backed critique",
            "budgets": budget,
        },
    ]
    data["tasks"] = [
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
            "checks": data["intent"]["acceptance"],
        },
    ]
    control = {
        "id": "baseline",
        "kind": "check",
        "owner": "host",
        "version": 1,
        "required": True,
        "phases": ["build"],
    }
    data["controls"] = [control]

    def probe(argv, oracle):
        return {
            "argv": [sys.executable, "-B", *argv],
            "cwd": ".",
            "timeout": 10,
            "max_output_bytes": 2048,
            "environment": {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"},
            "oracle_paths": [oracle],
        }

    data["effects"] = work_effects.freeze(
        root,
        data["intent"]["scope"],
        ["pkg", "tests", "tests/generated"],
        ["baseline.py", "oracle.py", "plan.md", "pytest.ini"],
        [
            {
                "control": work_effects.identity(control),
                "probe": probe(["baseline.py"], "baseline.py"),
            }
        ],
        data["directory"],
        verification=[
            {
                "task_id": "export",
                "probe": probe(
                    ["-c", "from pkg.export import answer;assert answer()==42"],
                    "oracle.py",
                ),
            },
            *[
                {"task_id": n, "probe": probe(["oracle.py"], "oracle.py")}
                for n in ("wire", "final")
            ],
        ],
    )
    record = create_work(root, config, **data)
    if accept:
        record = contracts.accept(
            (root, config, data),
            record,
            supported_controls=[work_effects.identity(control)],
        )
    return root, data["directory"], record


def execute(case, **kwargs):
    return build_work(case[1], exchange_factory=Worker, **kwargs)


def test_dependent_build_uses_previous_outputs_actual_checks_and_one_owner(work):
    case = prepare(work)
    result = execute_task(case[1], exchange_factory=Worker)
    assert result["build"]["status"] == "completed", result["build"].get("error")
    assert result == read_task(case[1])
    assert len(Worker.seen) == 3
    assert Worker.seen[1]["source_evidence"][EXPORT].endswith("return 42\n")
    assert Worker.seen[1]["step"]["dependencies"] == ["export"]
    assert (case[0] / "unrelated.txt").read_text() == "Keep my dirty work\n"
    assert [
        e["result"]["passed"]
        for e in result["build"]["events"]
        if e["kind"] == "acceptance_probe"
    ] == [True] * 3
    assert execute(case) == result and len(Worker.seen) == 3


def test_wrong_implementation_is_blocked_even_when_generated_test_passes(work):
    case = prepare(work)

    def wrong(payload, turn, peer):
        if turn["role"] == "worker" and turn["step"]["id"] == "wire":
            payload["files"][0]["text"] = "def value():\n    return 43\n"

    Worker.mutation = wrong
    result = execute(case)
    assert result["build"]["status"] == "needs_revision"
    assert len(Worker.seen) == 2  # No clean reviewer result can erase a failing oracle.
    from attune_harness.test_change import (
        create_test_task,
        accept_test_task,
        execute_test_task,
    )

    directory = case[1].parent / "supplemental-test"
    test = create_test_task(
        case[0],
        directory,
        scope=["source.py"],
        interpreter=sys.executable,
        tests=[GENERATED],
    )
    accept_test_task(directory, test["checkpoint_digest"])
    tested = execute_test_task(directory)
    assert tested["execution"]["result"]["outcome"] == "passed"
    assert (
        execute(case)["build"]["status"] == "needs_revision" and len(Worker.seen) == 2
    )


@pytest.mark.parametrize("boundary", range(1, 14))
def test_every_saved_boundary_resumes_without_repeating_calls_or_effects(
    work, boundary
):
    case = prepare(work)
    result = execute(case, max_operations=boundary)
    assert result["build"]["status"] in ("paused", "completed"), result["build"].get(
        "error"
    )
    completed = [e for e in result["build"]["events"] if e["state"] == "completed"]
    inodes = {
        e["item"]["path"]: (case[0] / e["item"]["path"]).stat().st_ino
        for e in completed
        if e["kind"] == "file_effect"
    }
    done = execute(case)
    assert done["build"]["status"] == "completed", done["build"].get("error")
    assert len(Worker.seen) == 3
    assert all((case[0] / p).stat().st_ino == i for p, i in inodes.items())
    assert done == read_task(case[1])


@pytest.mark.parametrize(
    "bad", ["dependency", "scope", "omitted_output", "task_identity", "approval"]
)
def test_wrong_worker_response_never_gets_file_authority(work, bad):
    case = prepare(work)

    def wrong(p, t, peer):
        if t["step"]["id"] != "export":
            return
        if bad == "dependency":
            p["dependencies"] = ["invented"]
        elif bad == "scope":
            p["files"][0]["path"] = "source.py"
        elif bad == "omitted_output":
            p["files"].pop()
        elif bad == "task_identity":
            p["task_id"] = "wire"
        else:
            p["approved"] = True

    Worker.mutation = wrong
    result = execute(case)
    assert result["build"]["status"] == "failed"
    assert not (case[0] / "pkg").exists()


@pytest.mark.parametrize(
    "bad", ["dependency", "verification", "overlap", "budget", "reviewer"]
)
def test_missing_build_requirements_fail_before_any_call(work, bad):
    case = prepare(work, accept=False)
    r = case[2]
    changes = {}
    if bad in ("dependency", "overlap"):
        tasks = copy.deepcopy(r["request"]["tasks"])
        if bad == "dependency":
            tasks[1]["dependencies"] = []
        else:
            tasks[1]["outputs"].append(EXPORT)
        changes["tasks"] = tasks
    elif bad == "verification":
        effects = copy.deepcopy(r["request"]["effects"])
        effects["verification"].pop()
        changes["effects"] = effects
    elif bad == "budget":
        budget = {**r["request"]["budgets"], "max_operations": 3}
        changes = {
            "budgets": budget,
            "assignments": [
                {**a, "budgets": budget} for a in r["request"]["assignments"]
            ],
        }
    else:
        changes["assignments"] = [
            a for a in r["request"]["assignments"] if a["role"] != "reviewer"
        ]
    revised = revise_work(case[1], checkpoint=r["checkpoint_digest"], changes=changes)
    contracts.accept(
        work,
        revised,
        supported_controls=[work_effects.identity(revised["request"]["controls"][0])],
    )
    with pytest.raises((ValueError, FeatureUnavailable)):
        execute(case)
    assert Worker.seen == [] and not (case[0] / "pkg").exists()


def test_high_review_blocks_completion_and_advice_is_separate(work):
    case = prepare(work)

    def finding(p, t, peer):
        if t["role"] == "reviewer":
            p["findings"] = [
                {
                    "id": "missing",
                    "severity": "high",
                    "text": "Synthetic review finding",
                    "evidence": ["source.py"],
                }
            ]

    Worker.mutation = finding
    assert execute(case)["build"]["status"] == "needs_revision"
    assert (
        read_task(case[1])["status"] == "accepted"
    )  # Acceptance of intent isn't acceptance of outcome.


def test_worker_cannot_edit_checkout_outside_the_effect_host(work):
    case = prepare(work)
    Worker.mutation = lambda p, t, peer: (peer.cwd / "unrelated.txt").write_text(
        "changed"
    )
    result = execute(case)
    assert result["build"]["status"] == "unresolved"
    assert not (case[0] / "pkg").exists()


def test_stale_final_source_test_or_configuration_cannot_reuse_success(work):
    case = prepare(work)
    execute(case)
    (case[0] / GENERATED).write_text("changed test")
    with pytest.raises(UnresolvedOperation):
        execute(case)


def test_lost_file_ack_reconciles_in_the_same_build_owner(work, monkeypatch):
    case = prepare(work)
    original = RunStore.save

    def fail(store, record):
        events = record.get("build", {}).get("events", [])
        if (
            events
            and events[-1]["kind"] == "file_effect"
            and events[-1]["state"] == "completed"
        ):
            raise PersistenceError("lost acknowledgment")
        return original(store, record)

    with monkeypatch.context() as m:
        m.setattr(RunStore, "save", fail)
        with pytest.raises(PersistenceError):
            execute(case)
    r = read_task(case[1])
    event = r["build"]["events"][-1]
    with pytest.raises(UnresolvedOperation):
        execute(case)
    reconcile_work_effect(case[1], r["checkpoint_digest"], event["event_id"])
    assert execute(case)["build"]["status"] == "completed" and len(Worker.seen) == 3


def test_completed_build_handoff_uses_existing_test_owner_and_rejects_stale_source(
    work,
):
    from attune_harness.task_handoff import completed_source
    from attune_harness.test_change import (
        create_test_task,
        accept_test_task,
        execute_test_task,
    )

    case = prepare(work)
    built = execute(case)
    root, changed, binding = completed_source(case[1])
    assert root == case[0] and set(changed) == {EXPORT, GENERATED, "source.py"}
    assert binding["kind"] == "completed-feature-v1"
    assert binding["checkpoint_digest"] == built["checkpoint_digest"]
    directory = case[1].parent / "test-handoff"
    task = create_test_task(
        None,
        directory,
        source_task=case[1],
        interpreter=sys.executable,
        tests=[GENERATED],
    )
    accept_test_task(directory, task["checkpoint_digest"])
    assert execute_test_task(directory)["execution"]["result"]["outcome"] == "passed"
    (root / "source.py").write_text("changed later")
    with pytest.raises(ValueError, match="stale completed producer evidence"):
        completed_source(case[1])
    with pytest.raises((ValueError, UnresolvedOperation)):
        execute_test_task(directory)


def test_unfinished_or_failed_build_cannot_supply_handoff(work):
    from attune_harness.task_handoff import completed_source

    case = prepare(work)
    with pytest.raises(ValueError, match="completed dependent build"):
        completed_source(case[1])
    execute(case, max_operations=2)
    with pytest.raises(ValueError, match="completed dependent build"):
        completed_source(case[1])


@pytest.mark.parametrize(
    "bad",
    [
        "status",
        "source",
        "order",
        "probe",
        "pass",
        "control",
        "effect",
        "participant",
        "attempts",
        "extra",
    ],
)
def test_rechecksummed_build_cannot_forge_evidence(work, bad):
    case = prepare(work)
    r = execute(case)
    run = r["build"]
    if bad == "status":
        run["events"].pop()
    elif bad == "source":
        run["source_evidence"]["source.py"] = "different"
    elif bad == "order":
        run["events"][0:2] = run["events"][0:2][::-1]
    elif bad == "probe":
        next(e for e in run["events"] if e["kind"] == "acceptance_probe")["result"][
            "artifact_digest"
        ] = ("0" * 64)
    elif bad == "pass":
        next(e for e in run["events"] if e["kind"] == "acceptance_probe")["result"][
            "returncode"
        ] = 1
    elif bad == "control":
        run["events"][0]["result"]["passed"] = False
    elif bad == "effect":
        next(e for e in run["events"] if e["kind"] == "file_effect")["result"]["entry"][
            "mode"
        ] = 0
    elif bad == "participant":
        run["participants"]["worker:export"]["participant_id"] = "critic"
    elif bad == "attempts":
        next(e for e in run["events"] if e["kind"] == "participant_turn")[
            "attempts"
        ] = 2
    else:
        run["events"].append({**run["events"][-1], "operation_key": "extra"})
    store = RunStore(case[1], existing=True)
    with store.lease():
        store.save(r)
    with pytest.raises(ValueError):
        read_task(case[1])


def test_probe_outcome_cannot_claim_pass_with_nonzero_exit(work):
    from attune_harness.work_build import _probe_plan

    case = prepare(work)
    r = execute(case)
    event = next(e for e in r["build"]["events"] if e["kind"] == "acceptance_probe")
    result = copy.deepcopy(event["result"])
    result["returncode"] = 1
    plan = _probe_plan(
        r["request"],
        work_effects.verification_probes(r["request"]["effects"])["export"],
    )
    with pytest.raises(ValueError, match="does not match its accepted invocation"):
        work_effects.validate_probe_result(result, plan, result["artifact_digest"])


def test_standalone_effect_api_cannot_take_over_a_dependent_build(work):
    from attune_harness.work_runtime import apply_work_effects

    case = prepare(work)
    r = execute(case, max_operations=1)
    proposal = {
        "schema_version": 1,
        "files": [
            {"path": EXPORT, "before_sha256": None, "text": "def answer(): return 42\n"}
        ],
    }
    with pytest.raises(ValueError, match="owning dependent-build runtime"):
        apply_work_effects(case[1], r["checkpoint_digest"], proposal)
    assert not (case[0] / "pkg").exists()


@pytest.mark.parametrize("kind", ["participant_turn", "acceptance_probe"])
def test_uncertain_call_or_check_cannot_be_blindly_repeated(work, monkeypatch, kind):
    case = prepare(work)
    original = RunStore.save

    def lose(store, record):
        events = record.get("build", {}).get("events", [])
        if events and events[-1]["kind"] == kind and events[-1]["state"] == "completed":
            raise PersistenceError("lost response")
        return original(store, record)

    with monkeypatch.context() as m:
        m.setattr(RunStore, "save", lose)
        with pytest.raises(PersistenceError):
            execute(case)
    calls = len(Worker.seen)
    with pytest.raises(UnresolvedOperation):
        execute(case)
    assert len(Worker.seen) == calls


def test_default_deterministic_adapter_does_not_invent_a_build(work):
    case = prepare(work)
    r = build_work(case[1])
    assert r["build"]["status"] == "unresolved"
    assert "no invented feature implementation" in r["build"]["error"]["detail"]
    assert not (case[0] / "pkg").exists()


@pytest.mark.parametrize("permission", ["external", "native"])
def test_provider_authorization_is_explicit_before_dispatch(work, permission):
    config = json.loads(work[1].read_text())
    config["participants"]["local"] = {
        "adapter": "codex",
        "model": "fixture-model",
        "tools": [],
        "max_turns": 1,
        "max_tool_calls": 0,
        "timeout": 2,
    }
    work[1].write_text(json.dumps(config))
    case = prepare(work)
    with pytest.raises((ValueError, FeatureUnavailable)):
        execute(case, allow_external=permission == "native")
    assert Worker.seen == [] and "build" not in read_task(case[1])


def test_build_command_worker_and_reviewer_use_actual_subprocesses(work):
    peer = work[0].parent / "peer.py"
    peer.write_text(
        """import json,sys,hashlib
w=json.load(sys.stdin);t=w['turn']
if t['role']=='reviewer':p={'kind':'critique','findings':[],'notes':['Synthetic command fixture']}
else:
 texts={'pkg/export.py':'def answer():\\n    return 42\\n','tests/generated/test_app.py':'def test_generated():\\n    assert True\\n','source.py':'from pkg.export import answer\\ndef value():\\n    return answer()\\n'}
 p={'schema_version':1,'task_id':t['step']['id'],'dependencies':t['step']['dependencies'],'files':[{'path':n,'before_sha256':hashlib.sha256(t['source_evidence'][n].encode()).hexdigest() if n in t['source_evidence'] else None,'text':texts[n]} for n in t['step']['outputs']]}
print(json.dumps({'schema_version':1,'request_digest':w['request_digest'],'action':{'kind':'final','text':json.dumps(p)}}))
"""
    )
    config = json.loads(work[1].read_text())
    for name in config["participants"]:
        config["participants"][name] = {
            "adapter": "command",
            "command": [sys.executable, "-B", str(peer)],
            "timeout": 2,
            "tools": [],
            "max_turns": 1,
            "max_tool_calls": 0,
        }
    work[1].write_text(json.dumps(config))
    case = prepare(work)
    r = build_work(case[1], allow_external=True)
    assert r["build"]["status"] == "completed", r["build"].get("error")
    events = [e for e in r["build"]["events"] if e["kind"] == "participant_turn"]
    assert len(events) == 3 and all(
        e["result"]["identity"]["returncode"] == 0 for e in events
    )
    with pytest.raises(FeatureUnavailable, match="allow-external"):
        build_work(case[1], allow_external=False)


@pytest.mark.parametrize("role", ["worker", "reviewer"])
def test_native_build_profile_binds_substance_on_the_host_without_paid_call(
    work, monkeypatch, role
):
    import hashlib
    from dataclasses import dataclass
    from attune_harness import review_participants
    from attune_harness.review_contract import digest
    from attune_harness.review_participants import ReviewExchange
    from attune_harness.work_build import PROFILE

    case = prepare(work)
    execute(case)
    turn = next(t for t in Worker.seen if t["role"] == role)
    seen = []

    @dataclass
    class Identity:
        provider: str = "codex"
        session_id: str = "injected-only"

    class Native:
        identity = Identity()

        def __init__(self, *args, **kwargs):
            seen.append(kwargs)

        def __call__(self, raw):
            wire = json.loads(raw)
            attempt = wire["attempt"]
            assert attempt["role"] == role and attempt["adapter_version"] == PROFILE
            assert "host binds control metadata" in attempt["task"]["requirements"][0]
            return canonical(
                {
                    "version": 1,
                    "request_digest": hashlib.sha256(raw.encode()).hexdigest(),
                    "text": '{"substantive":"fixture"}',
                }
            )

    monkeypatch.setattr(review_participants, "NativeExchange", Native)
    config = {
        "adapter": "codex",
        "model": "fixture-model",
        "tools": [],
        "max_turns": 1,
        "max_tool_calls": 0,
        "timeout": 1,
    }
    peer = ReviewExchange(config, case[0], profile=PROFILE)
    wire = {"schema_version": 1, "request_digest": digest(turn), "turn": turn}
    response = json.loads(peer(canonical(wire)))
    assert response["request_digest"] == digest(turn)
    assert (
        peer.last_identity["declared_role"] == role
        and seen[0]["model"] == "fixture-model"
    )
