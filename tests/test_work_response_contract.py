"""Host binding, real effects and versioned replay; no native dispatch."""

import copy
import json

import pytest
import test_work_build as builds
import test_work_contract as contracts
import test_work_planning as planning

from attune_harness import work_build, work_runtime
from attune_harness.review_contract import canonical
from attune_harness.recovery import RecoveryCursor
from attune_harness.task_contract import read_task
from attune_harness.work_contract import response_contract

work = contracts.work


@pytest.fixture(autouse=True)
def reset_scripts():
    planning.Scripted.seen = []
    planning.Scripted.mutate = None
    builds.Worker.seen = []
    builds.Worker.mutation = None
    yield
    planning.Scripted.mutate = None
    builds.Worker.mutation = None


def test_host_stages_criterion_bindings_without_rewriting_the_original_reply(work):
    planning.add_critic(work)
    draft = contracts.make(work)
    criterion = draft["request"]["intent"]["acceptance"][0]

    def paraphrase(payload, turn):
        if turn["role"] == "planner":
            payload["tasks"][0]["checks"] = ["Every finding survives the CLI export"]

    planning.Scripted.mutate = paraphrase
    record = work_runtime.plan_work(
        work[2]["directory"], exchange_factory=planning.Scripted
    )
    assert record["planning"]["status"] == "completed"
    assert record["planning"]["response_contract"] == 2
    proposal = record["planning"]["participants"]["planner"]["proposal"]
    assert criterion not in proposal["tasks"][0]["checks"]
    assert (
        planning.Scripted.seen[0]["protocol"] != planning.Scripted.seen[1]["protocol"]
    )
    assert planning.Scripted.seen[0]["build_profile"]["reserved_task_id"] == "final"
    staged = work_runtime.apply_planning_proposal(
        work[2]["directory"], checkpoint=record["checkpoint_digest"]
    )
    assert staged["request"]["tasks"][0]["checks"] == [
        "Every finding survives the CLI export",
        criterion,
    ]
    assert (
        staged["history"][-1]["planning"]["participants"]["planner"]["proposal"]
        == proposal
    )
    assert staged["status"] == "draft" and staged["acceptance"] is None
    assert read_task(work[2]["directory"]) == staged
    with pytest.raises(ValueError, match="Stale"):
        work_runtime.apply_planning_proposal(
            work[2]["directory"], checkpoint=record["checkpoint_digest"]
        )


def test_explicit_empty_choices_reaches_the_planner_and_stays_unaccepted(work):
    contracts.make(work)
    record = work_runtime.plan_work(
        work[2]["directory"], exchange_factory=planning.Scripted
    )
    turn = planning.Scripted.seen[0]
    assert '"choices": []' in turn["protocol"]
    assert record["planning"]["participants"]["planner"]["proposal"]["choices"] == []
    staged = work_runtime.apply_planning_proposal(
        work[2]["directory"], checkpoint=record["checkpoint_digest"]
    )
    assert staged["status"] == "draft" and staged["acceptance"] is None


@pytest.mark.parametrize("bad", ["omitted", "null", "object", "selected"])
def test_bad_choices_stop_planning_without_defaults_or_authority(work, bad):
    planning.add_critic(work)
    contracts.make(work)

    def malformed(payload, turn):
        if bad == "omitted":
            payload.pop("choices")
        else:
            payload["choices"] = {
                "null": None,
                "object": {},
                "selected": [contracts.choice("jsonl")],
            }[bad]

    planning.Scripted.mutate = malformed
    record = work_runtime.plan_work(
        work[2]["directory"], exchange_factory=planning.Scripted
    )
    assert record["planning"]["status"] == "failed"
    assert [t["role"] for t in planning.Scripted.seen] == ["planner"]
    assert record["acceptance"] is None
    with pytest.raises(ValueError):
        work_runtime.apply_planning_proposal(
            work[2]["directory"], checkpoint=record["checkpoint_digest"]
        )


def test_empty_new_choices_preserves_an_existing_human_decision(work):
    work[2]["choices"] = [contracts.choice("jsonl")]
    contracts.make(work)
    record = work_runtime.plan_work(
        work[2]["directory"], exchange_factory=planning.Scripted
    )
    staged = work_runtime.apply_planning_proposal(
        work[2]["directory"], checkpoint=record["checkpoint_digest"]
    )
    assert staged["request"]["choices"] == [contracts.choice("jsonl")]
    assert staged["acceptance"] is None


@pytest.mark.parametrize(
    "bad",
    [
        "missing",
        "criterion",
        "task",
        "duplicate",
        "goal",
        "outputless",
        "reserved",
        "chain",
        "duplicate_output",
        "authority",
    ],
)
def test_v2_plans_keep_coverage_and_executable_scope_guards(work, bad):
    request = contracts.make(work)["request"]
    p = work_runtime.demonstration_reply(
        {"role": "planner", "work": {"intent": request["intent"]}}
    )
    p["tasks"][0]["checks"] = ["Concrete independent check"]
    if bad == "missing":
        p["coverage"] = []
    elif bad == "criterion":
        p["coverage"][0]["criterion"] = "A different goal"
    elif bad == "task":
        p["coverage"][0]["tasks"] = ["foreign"]
    elif bad == "duplicate":
        p["coverage"].append(copy.deepcopy(p["coverage"][0]))
    elif bad == "goal":
        p["goal"] = "Drop uncertainty"
    elif bad == "outputless":
        p["tasks"][0]["outputs"] = []
    elif bad == "reserved":
        p["tasks"][0]["id"] = "final"
    elif bad in ("chain", "duplicate_output"):
        p["tasks"][0]["outputs"] = ["source.py"]
        task = copy.deepcopy(p["tasks"][0])
        task.update(
            id="second",
            outputs=["export.py"] if bad == "chain" else ["source.py"],
            dependencies=[] if bad == "chain" else ["implement"],
        )
        p["tasks"].append(task)
    else:
        p["accepted"] = True
    with pytest.raises(ValueError):
        work_runtime.validate_reply(p, request, "planner", contract_version=2)


def v2_worker(payload, turn, peer):
    if turn["role"] == "worker":
        payload.pop("task_id")
        payload.pop("dependencies")
        payload["schema_version"] = 2


def test_v2_build_binds_steps_runs_actual_probes_and_resumes_without_dispatch(work):
    case = builds.prepare(work)
    builds.Worker.mutation = v2_worker
    record = builds.execute(case)
    assert record["build"]["status"] == "completed", record["build"].get("error")
    assert record["build"]["response_contract"] == 2
    workers = [e for e in record["build"]["events"] if e["kind"] == "participant_turn"][
        :2
    ]
    for event in workers:
        payload = json.loads(event["result"]["action"]["text"])
        assert (
            set(payload) == {"schema_version", "files"}
            and payload["schema_version"] == 2
        )
    assert builds.Worker.seen[0]["output_schema"]["schema_version"] == 2
    assert builds.Worker.seen[0]["output_schema"]["files"][0]["before_sha256"] is None
    template = {f["path"]: f for f in builds.Worker.seen[1]["output_schema"]["files"]}
    assert (
        template["source.py"]["before_sha256"]
        == record["request"]["effects"]["before"]["source.py"]["sha256"]
    )
    assert builds.Worker.seen[-1]["output_schema"]["kind"] == "critique"
    assert builds.Worker.seen[0]["protocol"] != builds.Worker.seen[-1]["protocol"]
    assert all(
        e["result"]["passed"]
        for e in record["build"]["events"]
        if e["kind"] == "acceptance_probe"
    )
    assert builds.execute(case) == read_task(case[1]) == record
    assert len(builds.Worker.seen) == 3
    assert (case[0] / "unrelated.txt").read_text() == "Keep my dirty work\n"


@pytest.mark.parametrize(
    "bad",
    [
        "foreign_id",
        "dependencies",
        "notes",
        "scope",
        "other_step",
        "preimage",
        "missing",
        "version",
        "array",
        "legacy_id",
    ],
)
def test_v2_worker_rejects_extra_metadata_and_changed_evidence(work, bad):
    _, _, record = builds.prepare(work)
    request = record["request"]
    step = request["tasks"][0]
    files = [
        {"path": p, "before_sha256": None, "text": "synthetic content\n"}
        for p in step["outputs"]
    ]
    p = {"schema_version": 2, "files": files}
    if bad == "foreign_id":
        p["task_id"] = "foreign"
    elif bad == "dependencies":
        p["dependencies"] = []
    elif bad == "notes":
        p["notes"] = ["Accepted"]
    elif bad == "scope":
        files[0]["path"] = "oracle.py"
    elif bad == "other_step":
        p["files"] = [
            {
                "path": "source.py",
                "before_sha256": request["effects"]["before"]["source.py"]["sha256"],
                "text": "def value():\n    return 99\n",
            }
        ]
    elif bad == "preimage":
        files[0]["before_sha256"] = "a" * 64
    elif bad == "missing":
        p["files"] = []
    elif bad == "version":
        p["schema_version"] = True
    elif bad == "array":
        p = []
    else:
        p.update(
            schema_version=1,
            task_id=request["task_id"],
            dependencies=step["dependencies"],
        )
    with pytest.raises(ValueError):
        work_build.decode(
            {"kind": "final", "text": canonical(p)},
            request,
            "worker",
            step,
            contract_version=2,
        )


@pytest.mark.parametrize("version", [0, 3, True, "2", None])
def test_unknown_response_contracts_never_downgrade(version):
    with pytest.raises(ValueError, match="Unsupported response contract"):
        response_contract({"response_contract": version})


@pytest.mark.parametrize("phase", ["planning", "build"])
def test_response_contract_tampering_invalidates_saved_event_bindings(work, phase):
    if phase == "planning":
        contracts.make(work)
        record = work_runtime.plan_work(
            work[2]["directory"], exchange_factory=planning.Scripted
        )
        validator = work_runtime.validate_planning
    else:
        case = builds.prepare(work)
        record = builds.execute(case)
        validator = work_build.validate_build
    run = copy.deepcopy(record[phase])
    run.pop("response_contract")
    with pytest.raises(ValueError, match="bind|stale|foreign"):
        validator(run, record["request"])


@pytest.mark.parametrize("phase", ["planning", "build"])
def test_legacy_journals_reopen_and_resume_without_rewriting_or_repeating(
    work, phase, monkeypatch
):
    def legacy_cursor(run, store, limit):
        # Simulate original creation before any event exists; no reply is rebound.
        assert run["events"] == []
        run.pop("response_contract")
        return RecoveryCursor(run, store, limit)

    owner = work_runtime if phase == "planning" else work_build
    monkeypatch.setattr(owner, "RecoveryCursor", legacy_cursor)
    if phase == "planning":
        planning.add_critic(work)
        contracts.make(work)
        directory = work[2]["directory"]
        record = work_runtime.plan_work(
            directory, exchange_factory=planning.Scripted, max_operations=1
        )
    else:
        case = builds.prepare(work)
        directory = case[1]
        record = builds.execute(case, max_operations=1)
    monkeypatch.setattr(owner, "RecoveryCursor", RecoveryCursor)
    assert record[phase]["status"] == "paused"
    assert read_task(directory) == record
    if phase == "planning":
        result = work_runtime.plan_work(directory, exchange_factory=planning.Scripted)
        again = work_runtime.plan_work(directory, exchange_factory=planning.Scripted)
        seen = planning.Scripted.seen
        assert len(seen) == 2
    else:
        result = builds.execute(case)
        again = builds.execute(case)
        seen = builds.Worker.seen
        assert len(seen) == 3
    assert "response_contract" not in result[phase]
    assert "response_contract" not in seen[0]
    assert result[phase]["status"] == "completed" and again == result
    assert read_task(directory) == result


def test_valid_shape_can_still_be_semantically_wrong(work):
    request = contracts.make(work)["request"]
    payload = work_runtime.demonstration_reply(
        {"role": "planner", "work": {"intent": request["intent"]}}
    )
    payload["tasks"][0]["objective"] = "Silently discard all unknown findings"
    work_runtime.validate_reply(payload, request, "planner", contract_version=2)
    # Explicit semantic-review obligation, never a structural correctness claim.
    assert payload["goal"] == request["intent"]["goal"]
