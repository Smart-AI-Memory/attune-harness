"""Local planning journeys, real subprocesses and injected native transport only."""

import copy
import hashlib
import json
import sys
from dataclasses import dataclass

import pytest
import test_work_contract as contract_cases

from attune_harness import review_participants
from attune_harness.review_contract import canonical, digest
from attune_harness.review_participants import ReviewExchange
from attune_harness.review_store import RunStore
from attune_harness.task_contract import read_task
from attune_harness.task_policies import execute_task, inspect_task
from attune_harness.work_contract import bind_work_acceptance
from attune_harness.work_runtime import (
    PLANNING_PROFILE,
    apply_planning_proposal,
    demonstration_reply,
    plan_work,
    planning_questions,
)
from test_work_contract import (
    make,
    correction,
    accept,
    decision,
    choice,
    control,
    BUDGET,
)

work = contract_cases.work


class Scripted(ReviewExchange):
    seen = []
    mutate = None

    def __call__(self, raw):
        request = json.loads(raw)
        self.seen.append(copy.deepcopy(request["turn"]))
        payload = demonstration_reply(request["turn"])
        if type(self).mutate:
            type(self).mutate(payload, request["turn"])
        self.last_identity = {"adapter": "scripted-local", "profile": self.profile}
        return canonical(
            {
                "schema_version": 1,
                "request_digest": request["request_digest"],
                "action": {"kind": "final", "text": canonical(payload)},
            }
        )


@pytest.fixture(autouse=True)
def reset_script():
    Scripted.seen = []
    Scripted.mutate = None


def add_critic(work):
    work[2]["assignments"].append(
        {
            "role": "critic",
            "participant": "critic",
            "output_contract": "Evidence-linked critique; advice separate",
            "budgets": BUDGET,
        }
    )


def test_complete_corrected_conversation_and_existing_spec_projection(work):
    add_critic(work)
    work[2]["intent"]["goal"] = None
    draft = make(work)
    result = execute_task(work[2]["directory"], exchange_factory=Scripted)
    assert result["planning"]["status"] == "needs_input" and Scripted.seen == []
    shown = planning_questions(work[2]["directory"])
    assert shown["missing"] == ["goal"] and len(shown["definition"]["fields"]) == 1
    assert "What should this work accomplish?" in shown["markdown"]
    # Synthetic correction from partial intent; this is not attributed to Patrick.
    corrected = correction(
        work, intent={"goal": "Retain every finding, including unknown and refuted"}
    )
    assert corrected["request"]["task_id"] == draft["request"]["task_id"]
    assert corrected["history"][0]["planning"]["status"] == "needs_input"
    assert planning_questions(work[2]["directory"])["definition"] is None
    result = plan_work(work[2]["directory"], exchange_factory=Scripted)
    assert result == inspect_task(work[2]["directory"])
    assert result["planning"]["status"] == "completed"
    assert [t["role"] for t in Scripted.seen] == ["planner", "critic"]
    assert Scripted.seen[0]["work"]["intent"] == corrected["request"]["intent"]
    assert (
        Scripted.seen[1]["proposal"]["goal"] == corrected["request"]["intent"]["goal"]
    )
    assert result["acceptance"] is None and result["status"] == "draft"
    assert result["planning"]["metrics"]["first_useful_seconds"] > 0
    assert plan_work(work[2]["directory"], exchange_factory=Scripted) == result
    assert len(Scripted.seen) == 2  # Completed proposals do not spend another call.
    with pytest.raises(ValueError, match="Stage the planning proposal"):
        bind_work_acceptance(work[2]["directory"], decision(result))
    staged = apply_planning_proposal(
        work[2]["directory"], checkpoint=result["checkpoint_digest"]
    )
    assert "planning" not in staged and staged["acceptance"] is None
    assert staged["history"][-1]["planning"]["participants"]["critic"]["proposal"][
        "notes"
    ]
    assert accept(work)["status"] == "accepted"
    with pytest.raises(ValueError, match="contract only"):
        execute_task(work[2]["directory"])
    assert (work[0] / "unrelated.txt").read_text() == "Keep my dirty work\n"
    assert not (work[0] / "export.py").exists()


def test_planning_after_a_human_corrects_previously_accepted_work_keeps_history(work):
    accept(work, make(work))
    correction(work, intent={"goal": "Corrected user goal"})
    result = plan_work(work[2]["directory"])
    assert read_task(work[2]["directory"]) == result
    staged = apply_planning_proposal(
        work[2]["directory"], checkpoint=result["checkpoint_digest"]
    )
    assert staged["history"][0]["acceptance"]["decision"]["accepted"] is True
    assert accept(work)["request"]["revision"] == 3


def test_prompt_xml_spec_selection_survives_actual_plan_staging(work):
    work[2]["signals"]["multi_session"] = True
    make(work)
    result = plan_work(work[2]["directory"])
    staged = apply_planning_proposal(
        work[2]["directory"], checkpoint=result["checkpoint_digest"]
    )
    assert staged["request"]["authoring"]["tier"] == "spec"
    assert staged["request"]["intent"]["acceptance"] == work[2]["intent"]["acceptance"]


@pytest.mark.parametrize(
    "problem",
    [
        "wrong_goal",
        "unnecessary_question",
        "scope",
        "dependency",
        "omitted_criterion",
        "fake_coverage",
        "unknown_field",
        "decided_choice",
    ],
)
def test_wrong_or_incomplete_plans_fail_visibly_without_changing_intent(work, problem):
    draft = make(work)

    def corrupt(payload, turn):
        if problem == "wrong_goal":
            payload["goal"] = "Delete all uncertain findings"
        elif problem == "unnecessary_question":
            payload.clear()
            payload.update(kind="questions", questions=["What is your goal?"])
        elif problem == "scope":
            payload["tasks"][0]["outputs"] = ["outside.py"]
        elif problem == "dependency":
            payload["tasks"][0]["dependencies"] = ["missing"]
        elif problem == "omitted_criterion":
            payload["coverage"] = []
        elif problem == "fake_coverage":
            payload["coverage"][0]["tasks"] = ["nonexistent-task"]
        elif problem == "unknown_field":
            payload["accepted"] = True
        else:
            payload["choices"] = [choice("jsonl")]

    Scripted.mutate = corrupt
    result = plan_work(work[2]["directory"], exchange_factory=Scripted)
    assert result["planning"]["status"] == "failed"
    assert result["request"] == draft["request"] and result["acceptance"] is None
    assert len(result["planning"]["events"]) == 1
    assert read_task(work[2]["directory"]) == result
    assert plan_work(work[2]["directory"], exchange_factory=Scripted) == result
    assert len(Scripted.seen) == 1
    with pytest.raises(ValueError, match="Only a completed"):
        apply_planning_proposal(
            work[2]["directory"], checkpoint=result["checkpoint_digest"]
        )


def test_real_choice_retains_countercase_and_unknowns_but_requires_human_resolution(
    work,
):
    make(work)
    Scripted.mutate = lambda p, t: p.update(choices=[choice()])
    result = plan_work(work[2]["directory"], exchange_factory=Scripted)
    staged = apply_planning_proposal(
        work[2]["directory"], checkpoint=result["checkpoint_digest"]
    )
    assert staged["request"]["choices"][0]["selected"] is None
    assert staged["request"]["authoring"]["tier"] == "spec"
    assert staged["request"]["choices"][0]["options"][0]["evidence"] == []
    with pytest.raises(ValueError, match="Unresolved material"):
        accept(work)
    assert planning_questions(work[2]["directory"])["missing"] == ["choice:format"]


def test_settled_choice_cannot_be_reopened_by_planner(work):
    work[2]["choices"] = [choice("jsonl")]
    make(work)
    Scripted.mutate = lambda p, t: p.update(choices=[choice()])
    assert (
        plan_work(work[2]["directory"], exchange_factory=Scripted)["planning"]["status"]
        == "failed"
    )


def test_high_critic_finding_stops_staging_and_advice_remains_separate(work):
    add_critic(work)
    make(work)

    def criticize(payload, turn):
        if turn["role"] == "critic":
            payload["findings"] = [
                {
                    "id": "f1",
                    "severity": "high",
                    "text": "Wrong export behavior",
                    "evidence": ["task:implement"],
                }
            ]
            payload["notes"] = ["Optional wording suggestion"]

    Scripted.mutate = criticize
    result = plan_work(work[2]["directory"], exchange_factory=Scripted)
    assert result["planning"]["status"] == "needs_revision"
    assert result["planning"]["participants"]["critic"]["proposal"]["notes"] == [
        "Optional wording suggestion"
    ]
    with pytest.raises(ValueError, match="Only a completed"):
        apply_planning_proposal(
            work[2]["directory"], checkpoint=result["checkpoint_digest"]
        )


@pytest.mark.parametrize(
    "mode",
    [
        "no_planner",
        "budget",
        "same_identity",
        "required_hook",
        "tools",
        "unapproved_command",
        "unapproved_native",
    ],
)
def test_preflight_blocks_before_any_participant_attempt(work, mode):
    add_critic(work)
    if mode == "no_planner":
        work[2]["assignments"] = work[2]["assignments"][1:]
    elif mode == "budget":
        work[2]["budget"] = {**BUDGET, "max_operations": 1}
        for a in work[2]["assignments"]:
            a["budgets"] = work[2]["budget"]
    elif mode == "same_identity":
        work[2]["assignments"][1]["participant"] = "local"
    elif mode == "required_hook":
        work[2]["controls"] = [{**control(), "kind": "hook", "phases": ["plan"]}]
    else:
        config = json.loads(work[1].read_text())
        item = config["participants"]["local"]
        if mode == "tools":
            item["tools"] = ["verify"]
        elif mode == "unapproved_command":
            item.update(
                adapter="command", command=[sys.executable, "-c", "print(1)"], timeout=1
            )
        else:
            item.update(adapter="codex", model="fixture-model", timeout=1)
        work[1].write_text(json.dumps(config))
    make(work)
    result = plan_work(
        work[2]["directory"],
        exchange_factory=Scripted,
        allow_external=mode == "unapproved_native",
    )
    assert result["planning"]["status"] in ("failed", "unavailable")
    assert result["planning"]["events"] == [] and Scripted.seen == []
    assert read_task(work[2]["directory"]) == result


def command_peer(work, mode="ok"):
    peer = work[0].parent / "peer.py"
    peer.write_text("""import json,sys,time
r=json.load(sys.stdin);t=r['turn']
mode=sys.argv[1]
if mode=='timeout':time.sleep(3)
if mode=='malformed':print('not JSON');sys.exit(0)
if mode=='exit':sys.exit(3)
i=t['work']['intent']
p={'kind':'plan','goal':i['goal'],'tasks':[{'id':'export','objective':i['goal'],'dependencies':[],'outputs':i['scope'],'checks':i['acceptance']}],'coverage':[{'criterion':c,'tasks':['export']} for c in i['acceptance']],'choices':[],'notes':['Local command fixture']}
if t['role']=='critic':p={'kind':'critique','findings':[],'notes':['Local command critique']}
print(json.dumps({'schema_version':1,'request_digest':r['request_digest'],'action':{'kind':'final','text':json.dumps(p)}}))
""")
    config = json.loads(work[1].read_text())
    for item in config["participants"].values():
        item.update(
            adapter="command",
            command=[sys.executable, "-B", str(peer), mode],
            timeout=1,
        )
    work[1].write_text(json.dumps(config))


def test_actual_command_process_planner_and_critic_round_trip(work):
    add_critic(work)
    command_peer(work)
    make(work)
    result = plan_work(work[2]["directory"], allow_external=True)
    assert result["planning"]["status"] == "completed"
    assert len(result["planning"]["events"]) == 2
    assert all(
        p["last_identity"]["returncode"] == 0
        for p in result["planning"]["participants"].values()
    )
    assert read_task(work[2]["directory"]) == result


@pytest.mark.parametrize("mode", ["timeout", "malformed", "exit", "missing"])
def test_actual_process_failures_preserve_uncertainty_and_do_not_retry(work, mode):
    command_peer(work, mode)
    if mode == "missing":
        cfg = json.loads(work[1].read_text())
        cfg["participants"]["local"]["command"] = ["/does/not/exist"]
        work[1].write_text(json.dumps(cfg))
    make(work)
    result = plan_work(work[2]["directory"], allow_external=True)
    assert result["planning"]["status"] == "unresolved"
    assert len(result["planning"]["events"]) == 1
    assert result["planning"]["events"][0]["effects"] == "unknown"
    with pytest.raises(ValueError, match="Uncertain"):
        correction(work, intent={"goal": "Try again"})
    resumed = plan_work(work[2]["directory"], allow_external=True)
    assert (
        len(resumed["planning"]["events"]) == 1
        and resumed["planning"]["status"] == "unresolved"
    )


def test_pause_resume_consumes_completed_reply_without_repeating_participant(work):
    add_critic(work)
    make(work)
    first = plan_work(work[2]["directory"], exchange_factory=Scripted, max_operations=1)
    assert first["planning"]["status"] == "paused" and len(Scripted.seen) == 1
    assert read_task(work[2]["directory"]) == first
    result = plan_work(work[2]["directory"], exchange_factory=Scripted)
    assert result["planning"]["status"] == "completed" and len(Scripted.seen) == 2


def test_stale_checkpoint_and_source_block_proposal_staging(work):
    draft = make(work)
    result = plan_work(work[2]["directory"])
    with pytest.raises(ValueError, match="Stale"):
        apply_planning_proposal(
            work[2]["directory"], checkpoint=draft["checkpoint_digest"]
        )
    (work[0] / "source.py").write_text("changed\n")
    with pytest.raises(ValueError, match="Stale"):
        apply_planning_proposal(
            work[2]["directory"], checkpoint=result["checkpoint_digest"]
        )


@pytest.mark.parametrize(
    "role,transport", [("planner", "lead"), ("critic", "reviewer")]
)
def test_native_operation_mapping_and_host_owned_correlation_without_native_call(
    work, monkeypatch, role, transport
):
    add_critic(work)
    make(work)
    # Build an actual turn with deterministic runtime, then exercise native adapter with a spy.
    plan_work(work[2]["directory"], exchange_factory=Scripted)
    turn = next(t for t in Scripted.seen if t["role"] == role)
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
            request = json.loads(raw)
            attempt = request["attempt"]
            seen.append(attempt)
            assert (
                attempt["role"] == transport
                and attempt["adapter_version"] == PLANNING_PROFILE
            )
            assert (
                "Do not claim arbitrary prose is verified"
                not in attempt["task"]["requirements"][0]
            )
            return canonical(
                {
                    "version": 1,
                    "request_digest": hashlib.sha256(raw.encode()).hexdigest(),
                    "text": canonical(demonstration_reply(turn)),
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
    exchange = ReviewExchange(config, work[0], profile=PLANNING_PROFILE)
    request = {"schema_version": 1, "request_digest": digest(turn), "turn": turn}
    response = json.loads(exchange(canonical(request)))
    assert response["request_digest"] == request["request_digest"]
    assert exchange.last_identity["declared_role"] == role
    assert exchange.last_identity["transport_role"] == transport
    assert seen[0]["model"] == "fixture-model"


@pytest.mark.parametrize(
    "tamper", ["status", "request", "assignment", "operation", "attempts", "proposal"]
)
def test_rechecksummed_planning_record_cannot_forge_completion(work, tamper):
    add_critic(work)
    make(work)
    result = plan_work(work[2]["directory"])
    p = result["planning"]
    if tamper == "status":
        p["participants"]["critic"]["status"] = "running"
    elif tamper == "request":
        p["request_digest"] = "foreign"
    elif tamper == "assignment":
        p["participants"]["planner"]["participant_id"] = "someone_else"
    elif tamper == "operation":
        p["events"][0]["request_digest"] = "stale"
    elif tamper == "attempts":
        p["events"][0]["attempts"] = 2
    else:
        p["participants"]["planner"]["proposal"]["goal"] = "wrong goal"
    store = RunStore(work[2]["directory"], existing=True)
    with store.lease():
        store.save(result)
    with pytest.raises(ValueError):
        read_task(work[2]["directory"])


def test_actual_form_partial_answers_preserve_unknowns_and_bind_revision(work):
    from attune_harness.work_runtime import answer_planning

    work[2]["intent"].update(goal=None, acceptance=[])
    make(work)
    plan_work(work[2]["directory"])
    shown = planning_questions(work[2]["directory"])
    response = {
        "schema_version": 1,
        "checkpoint_digest": shown["checkpoint_digest"],
        "answers": {"answer_0": "Preserve all findings", "answer_1": None},
    }
    revised = answer_planning(work[2]["directory"], response)
    assert revised["request"]["intent"]["goal"] == "Preserve all findings"
    assert planning_questions(work[2]["directory"])["missing"] == ["acceptance"]
    with pytest.raises(ValueError, match="Stale"):
        answer_planning(work[2]["directory"], response)
    shown = planning_questions(work[2]["directory"])
    answer_planning(
        work[2]["directory"],
        {
            "schema_version": 1,
            "checkpoint_digest": shown["checkpoint_digest"],
            "answers": {
                "answer_0": "Default output unchanged\nUnknown findings retained"
            },
        },
    )
    assert planning_questions(work[2]["directory"])["missing"] == []
    result = plan_work(work[2]["directory"])
    assert result["planning"]["status"] == "completed"


def test_actual_choice_form_shows_countercase_and_records_selected_alternative(work):
    from attune_harness.work_runtime import answer_planning

    work[2]["choices"] = [choice()]
    make(work)
    shown = planning_questions(work[2]["directory"])
    field = shown["definition"]["fields"][0]
    assert field["type"] == "single_select"
    assert "Counter-case: Changes output shape" in shown["markdown"]
    assert "No workload benchmark yet" in shown["markdown"]
    result = answer_planning(
        work[2]["directory"],
        {
            "schema_version": 1,
            "checkpoint_digest": shown["checkpoint_digest"],
            "answers": {"answer_0": field["options"][0]},
        },
    )
    assert result["request"]["choices"][0]["selected"] == "jsonl"


def test_oversized_reply_never_becomes_a_plan(work):
    work[2]["assignments"][0]["budgets"] = {**BUDGET, "max_output_bytes": 100}
    make(work)
    result = plan_work(work[2]["directory"])
    assert result["planning"]["status"] == "failed"
    assert "100 bytes" in result["planning"]["error"]["detail"]


def test_source_change_during_transport_invalidates_received_plan(work):
    make(work)

    def change_source(payload, turn):
        (work[0] / "source.py").write_text("changed during reply\n")

    Scripted.mutate = change_source
    result = plan_work(work[2]["directory"], exchange_factory=Scripted)
    assert result["planning"]["status"] == "failed"
    assert "Stale" in result["planning"]["error"]["detail"]
    assert "proposal" not in result["planning"]["participants"]["planner"]


def test_lost_acknowledgment_leaves_uncertain_attempt_and_blocks_blind_retry(
    work, monkeypatch
):
    make(work)
    original = RunStore.save

    def lose_after_dispatch(self, record):
        events = record.get("planning", {}).get("events", [])
        if events and events[0]["state"] == "completed":
            raise KeyboardInterrupt("simulated process death after dispatch")
        original(self, record)

    monkeypatch.setattr(RunStore, "save", lose_after_dispatch)
    with pytest.raises(KeyboardInterrupt):
        plan_work(work[2]["directory"], exchange_factory=Scripted)
    monkeypatch.setattr(RunStore, "save", original)
    saved = read_task(work[2]["directory"])
    assert saved["planning"]["events"][0]["phase"] == "dispatching"
    resumed = plan_work(work[2]["directory"], exchange_factory=Scripted)
    assert resumed["planning"]["status"] == "unresolved" and len(Scripted.seen) == 1
    with pytest.raises(ValueError, match="Uncertain"):
        correction(work, intent={"goal": "Changed after uncertain attempt"})


def test_proposal_staging_cannot_refresh_away_changed_source(work, monkeypatch):
    from attune_harness import work_runtime

    make(work)
    result = plan_work(work[2]["directory"])
    original = work_runtime.revise_work

    def change_before_revision(*args, **kwargs):
        (work[0] / "source.py").write_text("Changed while staging proposal\n")
        return original(*args, **kwargs)

    monkeypatch.setattr(work_runtime, "revise_work", change_before_revision)
    with pytest.raises(ValueError, match="Stale"):
        apply_planning_proposal(
            work[2]["directory"], checkpoint=result["checkpoint_digest"]
        )
    assert read_task(work[2]["directory"])["request"] == result["request"]
