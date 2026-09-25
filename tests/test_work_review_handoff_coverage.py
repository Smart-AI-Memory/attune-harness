"""Critique evidence survives staging, narrowing and immutable build turns."""

from copy import deepcopy

import pytest
from test_work_contract import work

from attune_harness import work_review_handoff as handoff
from attune_harness.review_contract import digest


@pytest.fixture
def staged():
    tasks = [
        dict(id="parse", outputs=["parse.py"], dependencies=[], checks=["retains fields"]),
        dict(id="render", outputs=["render.py"], dependencies=["parse"], checks=["renders fields"]),
    ]
    request = dict(
        task_id="work", revision=1, tasks=[], choices=[], inputs=["input.json"],
        artifact="plan.md", evidence={"source": "original"},
        intent=dict(goal="Retain every field", context=[], scope=["parse.py", "render.py"],
                    constraints=["Preserve unknown fields"], acceptance=["round trip"], questions=[]),
    )
    critique = dict(kind="critique", findings=[
        dict(id="parse-loss", severity="medium", text="Unknown fields can be lost", evidence=["task:parse"]),
        dict(id="render-order", severity="low", text="Keep field order", evidence=["task:render"]),
    ], notes=["Keep diagnostics separate from output"])
    run = dict(status="completed", participants={
        "planner": dict(status="completed", proposal=dict(tasks=tasks, choices=[])),
        "critic": dict(status="completed", participant_id="critic", proposal=critique),
    })
    target = deepcopy(request)
    target.update(revision=2, tasks=deepcopy(tasks))
    dispositions = {"parse-loss": dict(disposition="address", rationale="Retain unknown fields",
                                        task_ids=["parse"])}
    payload = handoff.derive(request, run, target, dispositions)
    target["review_handoff"] = payload
    return target, [dict(request=request, planning=run)]


def test_findings_retain_source_and_order_through_stage_freeze_and_turns(staged):
    request, history = staged
    payload = request["review_handoff"]
    handoff.validate_source(payload, request, history)
    handoff.validate_transition(payload, request, history)
    marker = handoff.freeze(request)
    handoff.validate_frozen(marker, request)
    worker = handoff.turn_context(marker, "worker", request["tasks"][1])
    reviewer = handoff.turn_context(marker, "reviewer", request["tasks"][1])
    assert [f["id"] for f in worker["findings"]] == ["render-order"]
    assert [f["id"] for f in reviewer["findings"]] == ["parse-loss", "render-order"]
    assert reviewer["findings"][0]["disposition"] == "address"
    assert reviewer["findings"][1]["disposition"] == "advisory"
    assert reviewer["notes"][0]["text"] == "Keep diagnostics separate from output"
    worker["notes"][0]["text"] = "worker tries to rewrite advice"
    reviewer["findings"][0]["evidence"].clear()
    assert marker == handoff.freeze(request)


@pytest.mark.parametrize("change", ["missing", "reordered", "text", "evidence", "note"])
def test_edited_critique_cannot_be_laundered_as_original_evidence(staged, change):
    request, history = staged
    payload = request["review_handoff"]
    if change == "missing":
        payload["findings"].pop()
    elif change == "reordered":
        payload["findings"].reverse()
    elif change == "note":
        payload["notes"][0]["text"] = "Different advice"
    else:
        payload["findings"][0][change] = "Different claim" if change == "text" else ["task:render"]
    with pytest.raises(ValueError, match="retain every source"):
        handoff.validate_source(payload, request, history)


@pytest.mark.parametrize("change", ["history", "owner", "participant", "unfinished", "proposal"])
def test_handoff_requires_its_completed_owned_critique(staged, change):
    request, history = staged
    if change == "history":
        history.clear()
    elif change == "owner":
        request["task_id"] = "foreign-work"
    elif change == "participant":
        history[0]["planning"]["participants"]["critic"]["participant_id"] = "another-critic"
    elif change == "unfinished":
        history[0]["planning"]["status"] = "paused"
    else:
        history[0]["planning"]["participants"]["critic"]["proposal"]["notes"].append("New advice")
    with pytest.raises(ValueError, match="source"):
        handoff.validate_source(request["review_handoff"], request, history)


def pending_repair(staged):
    old, history = staged
    new = deepcopy(old)
    new.update(revision=3, tasks=deepcopy(old["tasks"][1:]))
    new["tasks"][0]["dependencies"] = []
    new["intent"]["scope"] = ["render.py"]
    new["inputs"].append("parse.py")
    new["evidence"] = {"source": "after verified parse"}
    new["review_handoff"] = handoff.project_for_repair(old["review_handoff"], old, new)
    history.append(dict(request=deepcopy(old), acceptance={"accepted": True}, build={"events": [
        dict(operation_key="probe:parse", state="completed", result={"passed": True})]}))
    return old, new, history


def test_verified_prefix_archives_its_findings_but_reviewer_keeps_them(staged):
    old, new, history = pending_repair(staged)
    payload = new["review_handoff"]
    handoff.validate_source(payload, new, history)
    handoff.validate_transition(payload, new, history)
    assert payload["findings"][0]["archived"] is True
    assert payload["findings"][0]["task_ids"] == []
    assert payload["findings"][0]["disposition"] == "address"
    assert payload["findings"][1]["task_ids"] == ["render"]
    assert old["review_handoff"]["findings"][0]["task_ids"] == ["parse"]
    marker = handoff.freeze(new)
    assert len(handoff.turn_context(marker, "reviewer", new["tasks"][0])["findings"]) == 2
    assert len(handoff.turn_context(marker, "worker", new["tasks"][0])["findings"]) == 1


@pytest.mark.parametrize("change", ["approval", "build", "failed", "nonprefix", "goal", "outputs", "disposition"])
def test_repair_cannot_invent_verified_prefix_or_repurpose_findings(staged, change):
    old, new, history = pending_repair(staged)
    previous = history[-1]
    if change == "approval":
        previous["acceptance"] = None
    elif change == "build":
        previous.pop("build")
    elif change == "failed":
        previous["build"]["events"][0]["result"]["passed"] = False
    elif change == "nonprefix":
        previous["build"]["events"][0]["operation_key"] = "probe:render"
    elif change == "goal":
        new["intent"]["goal"] = "Publish data instead"
    elif change == "outputs":
        new["tasks"][0]["outputs"] = ["credentials.txt"]
    else:
        new["review_handoff"]["findings"][0].update(disposition="dismissed", rationale="Ignore")
    with pytest.raises(ValueError, match="repair"):
        handoff.validate_transition(new["review_handoff"], new, history)


@pytest.mark.parametrize("change", ["identity", "outputs"])
def test_projection_cannot_reassign_a_finding_to_different_work(staged, change):
    old, _ = staged
    new = deepcopy(old)
    if change == "identity":
        new["tasks"][0]["id"] = "new-work"
    else:
        new["tasks"][0]["outputs"] = ["different.py"]
    with pytest.raises(ValueError, match="rename or repurpose"):
        handoff.project_for_repair(old["review_handoff"], old, new)


@pytest.mark.parametrize("change", ["version", "request", "payload"])
def test_frozen_context_is_bound_to_exact_accepted_request(staged, change):
    request, _ = staged
    marker = handoff.freeze(request)
    if change == "version":
        marker["version"] = True
    elif change == "request":
        request["revision"] += 1
    else:
        marker["payload"]["findings"].clear()
    with pytest.raises(ValueError, match="review_handoff"):
        handoff.validate_frozen(marker, request)


def test_no_critic_cannot_acquire_dispositions(staged):
    request, history = staged
    run = history[0]["planning"]
    run["participants"].pop("critic")
    assert handoff.derive(history[0]["request"], run, request) is None
    assert handoff.freeze(history[0]["request"]) is None
    with pytest.raises(ValueError, match="retained critic"):
        handoff.derive(history[0]["request"], run, request, {"invented": {}})


@pytest.mark.parametrize("dispositions", [[], {"unknown": {}}, {
    "parse-loss": dict(disposition="address", rationale="Act", task_ids=[])}])
def test_dispositions_must_name_real_findings_and_current_work(staged, dispositions):
    request, history = staged
    with pytest.raises(ValueError, match="disposition"):
        handoff.derive(history[0]["request"], history[0]["planning"], request, dispositions)


def test_carry_is_unchanged_and_fresh_stage_cannot_change_intent(staged):
    request, history = staged
    history.append(dict(request=deepcopy(request)))
    handoff.validate_transition(request["review_handoff"], request, history)
    request["review_handoff"]["findings"][0]["rationale"] = "Changed without staging"
    with pytest.raises(ValueError, match="without fresh staging"):
        handoff.validate_transition(request["review_handoff"], request, history)
    with pytest.raises(ValueError, match="preceding planning"):
        handoff.validate_transition(request["review_handoff"], request, [])
    request["intent"]["goal"] = "Different goal"
    with pytest.raises(ValueError, match="fresh staging"):
        handoff.validate_transition(request["review_handoff"], request, history[:1])


def test_native_contract_staging_keeps_acceptance_coverage_once(staged):
    request, history = staged
    run = history[0]["planning"]
    run["response_contract"] = 2
    run["participants"]["planner"]["proposal"]["coverage"] = [
        dict(criterion="round trip", tasks=["parse", "render"]),
        dict(criterion="retains fields", tasks=["parse"]),
    ]
    request["tasks"][0]["checks"].append("round trip")
    request["tasks"][1]["checks"].append("round trip")
    payload = request["review_handoff"]
    payload["target_digest"] = digest(handoff.target_binding(request))
    handoff.validate_shape(payload, request)
    handoff.validate_transition(payload, request, history)
    request["tasks"][0]["checks"].remove("round trip")
    with pytest.raises(ValueError, match="fresh staging"):
        handoff.validate_transition(payload, request, history)


def test_planning_findings_reach_actual_dependent_build_turns(work, monkeypatch):
    """Exercise the journal and file effects, not just standalone projections."""
    from test_work_build import prepare, Worker
    from test_work_contract import decision
    from test_work_planning import Scripted
    from attune_harness.work_contract import revise_work, bind_work_acceptance
    from attune_harness.work_runtime import plan_work, apply_planning_proposal, build_work
    from attune_harness.work_effects import identity

    root, directory, record = prepare(work, accept=False)
    assignments = deepcopy(record["request"]["assignments"])
    assignments.append({**assignments[-1], "role": "critic"})
    revise_work(directory, checkpoint=record["checkpoint_digest"], changes={"assignments": assignments})

    def plan_with_finding(payload, turn):
        if turn["role"] == "planner":
            payload["tasks"] = deepcopy(turn["work"]["tasks"])
            payload["coverage"] = [dict(criterion=c, tasks=["export", "wire"])
                                   for c in turn["work"]["intent"]["acceptance"]]
        else:
            payload["findings"] = [dict(id="retain-return", severity="medium",
                                       text="Keep the return value", evidence=["task:wire"])]

    monkeypatch.setattr(Scripted, "mutate", plan_with_finding)
    monkeypatch.setattr(Scripted, "seen", [])
    monkeypatch.setattr(Worker, "seen", [])
    monkeypatch.setattr(Worker, "mutation", None)
    planned = plan_work(directory, exchange_factory=Scripted)
    assert planned["planning"]["status"] == "completed"
    staged_record = apply_planning_proposal(
        directory, checkpoint=planned["checkpoint_digest"],
        review_dispositions={"retain-return": dict(disposition="address",
                                                   rationale="Keep the accepted return contract", task_ids=["wire"])})
    assert staged_record["acceptance"] is None
    bind_work_acceptance(directory, decision(staged_record),
                         supported_controls=[identity(c) for c in staged_record["request"]["controls"]])
    completed = build_work(directory, exchange_factory=Worker)
    assert completed["build"]["status"] == "completed"
    assert "return answer()" in (root / "source.py").read_text()
    contexts = [turn["review_context"] for turn in Worker.seen]
    assert [len(c["findings"]) for c in contexts] == [0, 1, 1]
    assert contexts[1]["findings"][0]["disposition"] == "address"
    assert contexts[2]["source"]["proposal_digest"] == contexts[1]["source"]["proposal_digest"]
    assert build_work(directory, exchange_factory=Worker) == completed
    assert len(Worker.seen) == 3
