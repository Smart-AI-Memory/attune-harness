"""Actual storage and negative authority checks; synthetic trusted Spec decisions."""

import copy
import json
import shutil

import pytest

from attune_harness import review_participants
from attune_harness.review_store import PersistenceError, RunStore
from attune_harness.task_contract import (
    accept_task,
    check_fresh,
    read_task,
    revise_task,
)
from attune_harness.task_policies import execute_task, inspect_task
from attune_harness.work_contract import (
    SIGNALS,
    bind_work_acceptance,
    create_work,
    decision_binding,
    missing_information,
    revise_work,
    select_authoring,
)

BUDGET = {"max_operations": 20, "max_attempts": 1, "max_output_bytes": 10000}


@pytest.fixture
def work(tmp_path, monkeypatch):
    def poison(*args, **kwargs):
        pytest.fail("Contract attempted native/provider dispatch")

    monkeypatch.setattr(review_participants, "NativeExchange", poison)
    root = tmp_path / "project"
    root.mkdir()
    (root / "source.py").write_text("def value():\n    return 1\n")
    (root / "plan.md").write_text("Preserve all findings and default JSON.\n")
    (root / "unrelated.txt").write_text("Keep my dirty work\n")
    config = tmp_path / "participants.json"
    config.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "participants": {
                    "local": {
                        "adapter": "deterministic",
                        "tools": [],
                        "max_turns": 1,
                        "max_tool_calls": 0,
                    },
                    "critic": {
                        "adapter": "deterministic",
                        "tools": [],
                        "max_turns": 1,
                        "max_tool_calls": 0,
                    },
                },
            }
        )
    )
    data = {
        "directory": tmp_path / "work",
        "intent": {
            "goal": "Export every finding",
            "context": ["Default JSON must survive"],
            "scope": ["source.py", "export.py"],
            "constraints": ["Preserve unknown claims"],
            "acceptance": ["CLI exports every finding without changing default output"],
            "questions": [],
        },
        "signals": {**dict.fromkeys(SIGNALS, False), "existing_artifact": None},
        "assignments": [
            {
                "role": "planner",
                "participant": "local",
                "output_contract": "Bounded plan with observable checks",
                "budgets": BUDGET,
            }
        ],
        "inputs": ["source.py"],
        "artifact": "plan.md",
        "budget": BUDGET,
    }
    return root, config, data


def make(work):
    root, config, data = work
    return create_work(root, config, **data)


def decision(record):
    return {
        **decision_binding(record),
        "accepted": True,
        "source": {
            "owner": "spec",
            "reference": "synthetic-collector:revision-8:approve_task",
            "disposition": "approve_task",
        },
    }


def accept(work, record=None, **kwargs):
    record = record or read_task(work[2]["directory"])
    return bind_work_acceptance(work[2]["directory"], decision(record), **kwargs)


def correction(work, **changes):
    current = read_task(work[2]["directory"])
    return revise_work(
        work[2]["directory"], checkpoint=current["checkpoint_digest"], changes=changes
    )


def control(required=True):
    return {
        "id": "independent-tests",
        "kind": "check",
        "owner": "pytest-change-v1",
        "version": 1,
        "required": required,
        "phases": ["build", "accept"],
    }


def choice(selected=None):
    return {
        "id": "format",
        "question": "How should export stream?",
        "selected": selected,
        "options": [
            {
                "id": name,
                "proposal": name,
                "rationale": reason,
                "evidence": [],
                "uncertainty": ["No workload benchmark yet"],
                "counter_case": counter,
            }
            for name, reason, counter in (
                ("jsonl", "Allows incremental consumption", "Changes output shape"),
                ("bundle", "Preserves old consumers", "Requires the whole result"),
            )
        ],
    }


def task(name, dependencies=()):
    return {
        "id": name,
        "objective": "Implement and verify export",
        "dependencies": list(dependencies),
        "outputs": ["export.py"],
        "checks": ["Independent CLI oracle passes"],
    }


def test_complete_intent_round_trip_needs_no_repeated_intake_or_effects(work):
    before = {p.name: p.read_bytes() for p in work[0].iterdir()}
    record = make(work)
    assert missing_information(record["request"]) == []
    accepted = accept(work, record)
    assert (
        read_task(work[2]["directory"])
        == accepted
        == inspect_task(work[2]["directory"])
    )
    assert accepted["request"]["intent"] == work[2]["intent"]
    assert accepted["bindings"]["effect_classes"] == []
    assert accepted["events"] == [] and "execution" not in accepted
    assert {p.name: p.read_bytes() for p in work[0].iterdir()} == before
    assert not (work[0] / "export.py").exists()
    with pytest.raises(ValueError, match="contract only"):
        execute_task(work[2]["directory"])


def test_vague_intent_preserves_answered_and_optional_questions(work):
    intent = work[2]["intent"]
    intent.update(
        goal=None,
        scope=[],
        acceptance=[],
        questions=[
            {
                "id": "audience",
                "question": "Who consumes it?",
                "answer": "CLI users",
                "material": True,
            },
            {
                "id": "format",
                "question": "Which format?",
                "answer": None,
                "material": True,
            },
            {
                "id": "speed",
                "question": "Workload latency?",
                "answer": None,
                "material": False,
            },
        ],
    )
    record = make(work)
    assert missing_information(record["request"]) == [
        "goal",
        "scope",
        "acceptance",
        "question:format",
    ]
    with pytest.raises(ValueError, match="Unresolved material"):
        accept(work)
    questions = copy.deepcopy(intent["questions"])
    questions[1]["answer"] = "JSONL"
    updated = correction(
        work,
        intent={
            "goal": "Export all findings",
            "scope": ["export.py"],
            "acceptance": ["Unknown findings survive"],
            "questions": questions,
        },
    )
    assert missing_information(updated["request"]) == []
    assert updated["request"]["intent"]["questions"][0]["answer"] == "CLI users"
    assert accept(work)["status"] == "accepted"


@pytest.mark.parametrize(
    "signal,tier",
    [(None, "prompt")]
    + [(s, "spec" if i < 5 else "xml") for i, s in enumerate(SIGNALS)],
)
def test_authoring_uses_consequences_and_continuity(work, signal, tier):
    if signal:
        work[2]["signals"][signal] = True
    record = make(work)
    assert record["request"]["authoring"]["tier"] == tier
    # A many-file rename still has the same authoring tier.
    more = correction(work, intent={"scope": [f"module{i}.py" for i in range(50)]})
    assert more["request"]["authoring"] == record["request"]["authoring"]


@pytest.mark.parametrize("existing", ["prompt", "xml", "spec"])
def test_existing_consumer_requirement_cannot_be_downgraded(work, existing):
    work[2]["signals"]["existing_artifact"] = existing
    assert make(work)["request"]["authoring"]["tier"] == existing


def test_unresolved_real_choice_has_evidence_uncertainty_and_countercase(work):
    work[2]["choices"] = [choice()]
    record = make(work)
    assert record["request"]["authoring"]["tier"] == "spec"
    assert missing_information(record["request"]) == ["choice:format"]
    with pytest.raises(ValueError, match="Unresolved"):
        accept(work)
    updated = correction(work, choices=[choice("jsonl")])
    assert missing_information(updated["request"]) == []
    assert accept(work)["request"]["choices"][0]["options"][0]["evidence"] == []


def test_ordered_dependencies_require_xml_even_without_signal(work):
    work[2]["tasks"] = [task("export"), task("cli", ["export"])]
    record = make(work)
    assert record["request"]["authoring"] == {
        "tier": "xml",
        "reasons": ["task_dependencies"],
    }
    work[2]["signals"]["multi_session"] = True
    assert (
        select_authoring(work[2]["signals"], tasks=work[2]["tasks"], choices=[])["tier"]
        == "spec"
    )


@pytest.mark.parametrize(
    "tasks",
    [
        [task("cli", ["missing"])],
        [task("cli", ["cli"])],
        [task("a", ["b"]), task("b", ["a"])],
        [task("a"), task("a")],
        [{**task("a"), "outputs": ["outside.py"]}],
        [{**task("a"), "checks": []}],
    ],
)
def test_invalid_task_graph_or_scope_never_creates_record(work, tasks):
    work[2]["tasks"] = tasks
    with pytest.raises(ValueError):
        make(work)
    assert not work[2]["directory"].exists()


def test_corrected_goal_preserves_history_but_invalidates_assignment_and_authority(
    work,
):
    work[2]["intent"][
        "goal"
    ] = "Synthetic earlier intent: export only verified findings"
    old = accept(work, make(work))
    before = old["bindings"]["assignments"]["planner"]
    revised = correction(
        work, intent={"goal": "Export all findings, including unknown and refuted"}
    )
    assert revised["request"]["task_id"] == old["request"]["task_id"]
    assert revised["request"]["revision"] == 2
    assert revised["acceptance"] is None and revised["bindings"] == {}
    assert revised["history"] == [
        {"request": old["request"], "acceptance": old["acceptance"]}
    ]
    assert (
        revised["request"]["intent"]["constraints"]
        == old["request"]["intent"]["constraints"]
    )
    after = accept(work)["bindings"]["assignments"]["planner"]
    assert before["assignment_id"] != after["assignment_id"]
    assert before["request_digest"] != after["request_digest"]
    assert (
        read_task(work[2]["directory"])["history"][0]["acceptance"] == old["acceptance"]
    )


def test_unchanged_revision_preserves_accepted_decision(work):
    accepted = accept(work, make(work))
    before = (work[2]["directory"] / "record.json").read_bytes()
    assert (
        correction(work, intent={"goal": accepted["request"]["intent"]["goal"]})
        == accepted
    )
    assert (work[2]["directory"] / "record.json").read_bytes() == before


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.pop("request_digest"),
        lambda d: d.update(extra=True),
        lambda d: d.update(accepted=False),
        lambda d: d.update(accepted=1),
        lambda d: d.update(schema_version=True),
        lambda d: d.update(revision=True),
        lambda d: d.update(revision=2),
        lambda d: d.update(task_id="foreign"),
        lambda d: d.update(checkpoint_digest="stale"),
        lambda d: d.update(record_path="foreign"),
        lambda d: d.update(request_digest="changed"),
        lambda d: d["source"].update(owner="model"),
        lambda d: d["source"].update(disposition="looks_good"),
        lambda d: d["source"].update(reference=""),
    ],
)
def test_partial_foreign_or_unbound_decision_leaves_bytes_unchanged(work, mutate):
    record = make(work)
    before = (work[2]["directory"] / "record.json").read_bytes()
    response = decision(record)
    mutate(response)
    with pytest.raises(ValueError):
        bind_work_acceptance(work[2]["directory"], response)
    assert (work[2]["directory"] / "record.json").read_bytes() == before


def test_replayed_and_stale_revision_decisions_fail(work):
    draft = make(work)
    accept(work, draft)
    with pytest.raises(ValueError, match="replay"):
        accept(work, draft)
    correction(work, intent={"goal": "Corrected intent"})
    with pytest.raises(ValueError, match="Stale"):
        accept(work, draft)
    with pytest.raises(ValueError, match="Stale"):
        revise_work(work[2]["directory"], checkpoint=draft["checkpoint_digest"])


def test_copied_record_cannot_gain_another_owner(work, tmp_path):
    draft = make(work)
    copied = tmp_path / "copied"
    shutil.copytree(work[2]["directory"], copied)
    with pytest.raises(ValueError, match="Copied"):
        bind_work_acceptance(copied, decision(draft))


@pytest.mark.parametrize("which", ["source.py", "plan.md", "configuration"])
def test_changed_evidence_requires_fresh_decision(work, which):
    draft = make(work)
    path = work[1] if which == "configuration" else work[0] / which
    path.write_text(path.read_text() + "\n")
    with pytest.raises(ValueError, match="Stale"):
        accept(work, draft)
    with pytest.raises(ValueError, match="Stale"):
        check_fresh(draft)
    updated = correction(work)
    assert updated["request"]["revision"] == 2
    assert accept(work)["status"] == "accepted"


def test_unrelated_dirty_file_does_not_revoke_scoped_acceptance(work):
    draft = make(work)
    (work[0] / "unrelated.txt").write_text("Still unrelated\n")
    assert accept(work, draft)["status"] == "accepted"


def test_required_control_unavailable_wrong_version_or_omitted_blocks(work):
    work[2]["controls"] = [control()]
    draft = make(work)
    for capabilities in (
        [],
        [
            {
                "id": "independent-tests",
                "kind": "check",
                "owner": "pytest-change-v1",
                "version": 2,
            }
        ],
    ):
        with pytest.raises(ValueError, match="Unavailable required"):
            accept(work, draft, supported_controls=capabilities)
    supported = [
        {k: v for k, v in control().items() if k not in ("required", "phases")}
    ]
    accepted = accept(work, draft, supported_controls=supported)
    assert accepted["events"] == []  # Available does not mean executed.
    assert accepted["acceptance"]["supported_controls"] == supported


def test_unknown_advisory_control_remains_visible_without_fabricated_execution(work):
    work[2]["controls"] = [{**control(False), "owner": "future-hook", "kind": "hook"}]
    accepted = accept(work, make(work))
    assert accepted["request"]["controls"] == work[2]["controls"]
    assert accepted["acceptance"]["supported_controls"] == []


@pytest.mark.parametrize(
    "update",
    [
        lambda d: d["signals"].update(multi_session=1),
        lambda d: d["intent"].update(extra="discard me"),
        lambda d: d["intent"].update(scope=["../outside"]),
        lambda d: d["intent"].update(scope=["a//b"]),
        lambda d: d["assignments"][0].update(participant="unknown"),
        lambda d: d["assignments"][0].update(role="router"),
        lambda d: d.update(assignments=d["assignments"] * 2),
        lambda d: d["assignments"][0].update(budgets={**BUDGET, "max_operations": 50}),
        lambda d: d.update(controls=[{**control(), "required": 1}]),
        lambda d: d.update(controls=[{**control(), "phases": []}]),
        lambda d: d.update(controls=[control(), control()]),
        lambda d: d.update(inputs=["missing.py"]),
        lambda d: d.update(inputs=[".git/config"]),
        lambda d: d.update(choices=[{**choice(), "selected": "unknown"}]),
        lambda d: d.update(choices=[{**choice(), "options": []}]),
    ],
)
def test_malformed_contract_never_creates_state(work, update):
    update(work[2])
    with pytest.raises(ValueError):
        make(work)
    assert not work[2]["directory"].exists()


def test_missing_planner_blocks_acceptance_without_inventing_an_assignment(work):
    work[2]["assignments"] = []
    make(work)
    with pytest.raises(ValueError, match="planner"):
        accept(work)


@pytest.mark.parametrize("target", ["inputs", "state"])
def test_symlink_boundary_fails(work, tmp_path, target):
    if target == "inputs":
        (work[0] / "source.py").unlink()
        (work[0] / "source.py").symlink_to(work[0] / "plan.md")
    else:
        alias = tmp_path / "alias"
        alias.symlink_to(tmp_path, target_is_directory=True)
        work[2]["directory"] = alias / "work"
    with pytest.raises(ValueError, match="symlink"):
        make(work)


def test_state_must_be_disjoint_and_failed_revision_leaves_current_bytes(work):
    work[2]["directory"] = work[0] / "state"
    with pytest.raises(ValueError, match="outside"):
        make(work)
    work[2]["directory"] = work[0].parent / "work"
    make(work)
    before = (work[2]["directory"] / "record.json").read_bytes()
    for changes in (
        {"invented": True},
        {"intent": {"invented": True}},
        {"tasks": [task("a", ["b"])]},
    ):
        with pytest.raises(ValueError):
            correction(work, **changes)
    assert (work[2]["directory"] / "record.json").read_bytes() == before


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.update(status="running"),
        lambda r: r.update(events=[{"kind": "write"}]),
        lambda r: r.update(recovery={}),
        lambda r: r["request"].update(authoring={"tier": "prompt", "reasons": []}),
        lambda r: r["bindings"].update(effect_classes=["file_replacement"]),
        lambda r: r["history"][0]["request"].update(revision=2),
        lambda r: r.update(history=[]),
        lambda r: r["history"][0]["acceptance"]["decision"].update(
            request_digest="stale"
        ),
    ],
)
def test_even_rechecksummed_record_cannot_silently_change_contract_or_history(
    work, mutate
):
    accept(work, make(work))
    correction(work, intent={"goal": "Updated scope"})
    record = accept(work)
    mutate(record)
    store = RunStore(work[2]["directory"], existing=True)
    with store.lease():
        store.save(record)
    with pytest.raises(ValueError):
        read_task(work[2]["directory"])


def test_one_writer_and_revision_limit(work):
    make(work)
    store = RunStore(work[2]["directory"], existing=True)
    with store.lease(), pytest.raises(PersistenceError, match="busy"):
        correction(work, intent={"goal": "Blocked other writer"})
    for number in range(2, 33):
        record = correction(work, intent={"goal": f"Correction {number}"})
        assert record["request"]["revision"] == number
    with pytest.raises(ValueError, match="limit"):
        correction(work, intent={"goal": "One too many"})


def test_existing_intake_cannot_accept_or_revise_work_profile(work):
    draft = make(work)
    before = (work[2]["directory"] / "record.json").read_bytes()
    with pytest.raises(ValueError, match="acceptance owner"):
        accept_task(work[2]["directory"], decision(draft))
    with pytest.raises(ValueError, match="revision owner"):
        revise_task(work[2]["directory"], checkpoint=draft["checkpoint_digest"])
    assert (work[2]["directory"] / "record.json").read_bytes() == before


def test_draft_cannot_drop_accepted_history(work):
    accept(work, make(work))
    record = correction(work, intent={"goal": "Changed goal"})
    record["history"] = []
    store = RunStore(work[2]["directory"], existing=True)
    with store.lease():
        store.save(record)
    with pytest.raises(ValueError, match="retain every preceding"):
        read_task(work[2]["directory"])


def test_freshness_rechecked_after_decision_validation(work, monkeypatch):
    from attune_harness import work_contract

    draft = make(work)
    before = (work[2]["directory"] / "record.json").read_bytes()
    original = work_contract.validate_work_task

    def change_after_validation(record, directory):
        result = original(record, directory)
        if record["status"] == "accepted":
            (work[0] / "source.py").write_text("Changed during validation\n")
        return result

    monkeypatch.setattr(work_contract, "validate_work_task", change_after_validation)
    with pytest.raises(ValueError, match="Stale"):
        accept(work, draft)
    assert (work[2]["directory"] / "record.json").read_bytes() == before


@pytest.mark.parametrize("field", ["controls", "assignments", "budgets", "tasks"])
def test_each_authority_bearing_correction_revokes_previous_acceptance(work, field):
    prior = accept(work, make(work))
    changes = {
        "controls": [control()],
        "assignments": [{**work[2]["assignments"][0], "participant": "critic"}],
        "budgets": {**BUDGET, "max_operations": 21},
        "tasks": [task("new-task")],
    }
    revised = correction(work, **{field: changes[field]})
    assert revised["status"] == "draft" and revised["acceptance"] is None
    assert revised["bindings"] == {}
    with pytest.raises(ValueError, match="Stale"):
        bind_work_acceptance(work[2]["directory"], prior["acceptance"]["decision"])
