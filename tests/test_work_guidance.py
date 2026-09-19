"""Status guidance follows real local journals without dispatch or writes."""

import copy

import pytest
import test_work_build as builds
import test_work_cli as console
import test_work_contract as contracts
import test_work_effects as effects
import test_work_planning as planning
import test_work_repair_resume as repairs

from attune_harness import repair, work_effects, work_runtime
from attune_harness.review_participants import ReviewExchange
from attune_harness.review_store import PersistenceError, RunStore
from attune_harness.task_contract import read_task
from attune_harness.work_contract import revise_work

work = contracts.work
reset_worker = builds.reset_worker
reset_script = planning.reset_script


def inspect(case, capsys, monkeypatch):
    def snapshot():
        return {
            str(p): (p.read_bytes(), p.stat().st_mtime_ns)
            for root in case[:2]
            for p in root.rglob("*")
            if p.is_file() and ".git" not in p.parts
        }

    def forbidden(*args, **kwargs):
        pytest.fail("Status attempted dispatch, a check, an effect or a save")

    before = snapshot()
    with monkeypatch.context() as patch:
        patch.setattr(ReviewExchange, "__call__", forbidden)
        patch.setattr(work_runtime, "plan_work", forbidden)
        patch.setattr(repair, "run_probe", forbidden)
        patch.setattr(work_effects, "write_effect", forbidden)
        patch.setattr(RunStore, "save", forbidden)
        result = console.invoke(capsys, "status", case[1])
        assert console.invoke(capsys, "status", case[1]) == result
    assert snapshot() == before
    assert result["evidence"]["record_path"] == str(case[1] / "record.json")
    saved = read_task(case[1])
    for item in [*result["evidence"]["checks"], *result["evidence"]["reviews"]]:
        value = saved
        for key in item["pointer"].strip("/").split("/"):
            value = value[int(key)] if isinstance(value, list) else value[key]
        assert value  # References reach complete saved evidence, including review text.
    return result


@pytest.mark.parametrize(
    "stage", ["draft", "proposal", "accepted", "paused", "completed"]
)
def test_stale_evidence_never_offers_ordinary_progress(
    work, capsys, monkeypatch, stage
):
    case = builds.prepare(work, accept=stage not in ("draft", "proposal"))
    if stage == "proposal":
        work_runtime.plan_work(case[1], exchange_factory=planning.Scripted)
    elif stage in ("paused", "completed"):
        builds.execute(case, max_operations=8 if stage == "paused" else None)
    (case[0] / "source.py").write_text("changed after preparation\n")
    result = inspect(case, capsys, monkeypatch)
    assert result["status"] == "stale" and result["blocking"]
    assert result["freshness_error"]
    assert "--accept" not in result["next_action"]
    assert "--stage" not in result["next_action"]
    assert "Use resume" not in result["next_action"]
    assert "stale" in result["summary"]
    if stage == "proposal":
        assert result["planning"]["status"] == "completed"
    if stage in ("paused", "completed"):
        assert result["completed"]  # Historical completion remains visible.
        assert "journal" in result["next_action"]


def control_case(work, *, required, runner):
    case = builds.prepare(work, accept=False)
    record = case[2]
    controls = copy.deepcopy(record["request"]["controls"])
    controls[0]["required"] = required
    manifest = copy.deepcopy(record["request"]["effects"])
    if runner:
        manifest["checks"][0]["probe"]["argv"][-1:] = ["-c", "raise SystemExit(1)"]
    else:
        manifest["checks"] = []
    record = revise_work(
        case[1],
        checkpoint=record["checkpoint_digest"],
        changes={
            "controls": controls,
            "effects": manifest,
        },
    )
    contracts.accept(
        work, record, supported_controls=[work_effects.identity(c) for c in controls]
    )
    return case


def test_unavailable_required_runner_is_blocking_before_a_saved_build(
    work, capsys, monkeypatch
):
    case = control_case(work, required=True, runner=False)
    result = console.invoke(capsys, "build", case[1], code=2)
    assert result["status"] == "failed" and result["blocking"]
    assert "no qualified runner" in result["error"]["detail"]
    assert "required" in result["next_action"]
    assert result["record_path"] == str(case[1] / "record.json")
    assert "build" not in read_task(case[1]) and builds.Worker.seen == []
    result = inspect(case, capsys, monkeypatch)
    assert result["authority"] == result["status"] == "accepted"
    assert result["blocking"] and "no qualified runner" in result["readiness_error"]
    assert "Use build" not in result["next_action"]


@pytest.mark.parametrize(
    "required,runner", [(True, True), (False, True), (False, False)]
)
def test_required_control_failure_and_optional_advice_have_different_consequences(
    work, capsys, monkeypatch, required, runner
):
    case = control_case(work, required=required, runner=runner)
    saved = builds.execute(case)
    result = inspect(case, capsys, monkeypatch)
    assert result["blocking"] is required
    if required:
        assert saved["build"]["status"] == result["status"] == "unresolved"
        assert "required control" in result["summary"] and "failed" in result["summary"]
        assert "Use resume" not in result["next_action"]
        assert not builds.Worker.seen
    else:
        assert result["status"] == "completed"
        assert result["advisory"][0]["status"] == (
            "failed" if runner else "unavailable"
        )
        assert "No build retry" in result["next_action"]
        assert len(builds.Worker.seen) == 3


def test_failed_protected_check_keeps_prior_completion_and_failure_evidence(
    work, capsys, monkeypatch
):
    case, _ = repairs.failed_case(work)
    result = inspect(case, capsys, monkeypatch)
    assert result["status"] == "needs_revision" and result["blocking"]
    assert result["completed"] == ["export"]
    failed = [c for c in result["evidence"]["checks"] if not c["passed"]]
    assert [c["operation"] for c in failed] == ["probe:wire"]
    assert "protected check failed" in result["summary"]
    assert "resume does not rerun" in result["next_action"]


@pytest.mark.parametrize("high", [False, True])
def test_review_findings_are_attributed_separately_from_passing_checks(
    work, capsys, monkeypatch, high
):
    case = builds.prepare(work)

    def review(payload, turn, peer):
        if turn["role"] == "reviewer":
            payload["findings"] = [
                {
                    "id": "fixture",
                    "severity": "high" if high else "low",
                    "text": "A reviewer judgment",
                    "evidence": ["source.py"],
                }
            ]
            payload["notes"] = ["Optional wording advice"]

    builds.Worker.mutation = review
    builds.execute(case)
    result = inspect(case, capsys, monkeypatch)
    assert result["blocking"] is high
    assert all(c["passed"] for c in result["evidence"]["checks"])
    assert result["evidence"]["reviews"][0]["blocking_findings"] == int(high)
    assert result["advisory"][0]["kind"] == "optional_notes"
    assert "reviewer" in result["summary"].lower()
    if not high:
        assert "do not prove every semantic claim" in result["next_action"]


@pytest.mark.parametrize(
    "kind", ["file_effect", "participant_turn", "acceptance_probe"]
)
def test_lost_ack_never_offers_blind_retry_even_with_stale_files(
    work, capsys, monkeypatch, kind
):
    case = builds.prepare(work)
    original = RunStore.save

    def lose(store, record):
        events = record.get("build", {}).get("events", [])
        if events and events[-1]["kind"] == kind and events[-1]["state"] == "completed":
            raise PersistenceError("Lost acknowledgment")
        return original(store, record)

    with monkeypatch.context() as patch:
        patch.setattr(RunStore, "save", lose)
        with pytest.raises(PersistenceError):
            builds.execute(case)
    (case[0] / "unrelated.txt").write_text("changed during uncertain execution\n")
    result = inspect(case, capsys, monkeypatch)
    assert result["status"] == "unresolved" and result["blocking"]
    assert "uncertain" in result["summary"]
    assert "do not blindly retry" in result["next_action"]
    assert "Use resume" not in result["next_action"]
    assert "freshness_error" in result


def test_accepted_paused_and_completed_build_guidance_matches_existing_commands(
    work, capsys, monkeypatch
):
    directory, draft = console.create(work, capsys)
    accepted = console.invoke(
        capsys,
        "plan",
        "--task-dir",
        directory,
        "--accept",
        "--checkpoint",
        draft["checkpoint_digest"],
    )
    assert not accepted["blocking"] and "Use build" in accepted["next_action"]
    paused = console.invoke(
        capsys, "build", directory, "--allow-external", "--max-operations", 8, code=1
    )
    assert not paused["blocking"] and "Use resume" in paused["next_action"]
    inspect((work[0], directory), capsys, monkeypatch)
    done = console.invoke(
        capsys,
        "resume",
        directory,
        "--allow-external",
        "--checkpoint",
        paused["checkpoint_digest"],
    )
    assert done["status"] == "completed" and not done["blocking"]
    assert done["completed"] == ["export", "wire"]
    assert "protected checks passed" in done["summary"]
    assert "No build retry" in done["next_action"]


@pytest.mark.parametrize(
    "state", ["needs_input", "paused", "completed", "needs_revision", "failed"]
)
def test_planning_guidance_does_not_claim_a_completed_build(
    work, capsys, monkeypatch, state
):
    planning.add_critic(work)
    if state == "needs_input":
        work[2]["intent"]["goal"] = None
    contracts.make(work)

    def mutate(payload, turn):
        if state == "failed" and turn["role"] == "planner":
            payload.pop("kind")
        if state == "needs_revision" and turn["role"] == "critic":
            payload["findings"] = [
                {
                    "id": "issue",
                    "severity": "high",
                    "text": "Fixture finding",
                    "evidence": ["source.py"],
                }
            ]

    planning.Scripted.mutate = mutate
    saved = work_runtime.plan_work(
        work[2]["directory"],
        exchange_factory=planning.Scripted,
        max_operations=1 if state == "paused" else None,
    )
    assert saved["planning"]["status"] == state
    result = inspect((work[0], work[2]["directory"]), capsys, monkeypatch)
    assert result["phase"] == "planning" and result["authority"] == "draft"
    assert result["completed"] == []
    assert "Build completed" not in result["summary"]
    assert "--accept" not in result["next_action"]
    if state == "completed":
        assert "--stage" in result["next_action"]
    elif state == "paused":
        assert "Use resume" in result["next_action"]
    else:
        assert result["blocking"]


def test_file_effect_completion_does_not_claim_dependent_build_verification(
    work, capsys, monkeypatch
):
    case = effects.prepare(work)
    effects.execute(case)
    result = inspect(case, capsys, monkeypatch)
    assert result["status"] == "completed"
    assert "dependent build verification is not established" in result["summary"]


def test_error_without_readable_owner_retains_json_error_and_exit_code(
    tmp_path, capsys
):
    result = console.invoke(capsys, "build", tmp_path / "absent", code=2)
    assert result["status"] == "failed" and result["error"]["detail"]
    assert result["blocking"] and "Inspect" in result["next_action"]
    assert "record_path" not in result


@pytest.mark.parametrize("role", ["worker", "reviewer"])
def test_rejected_saved_reply_is_blocking_even_when_paused(
    work, capsys, monkeypatch, role
):
    case = builds.prepare(work)

    def invalid(payload, turn, peer):
        if turn["role"] == role:
            payload.pop("files" if role == "worker" else "findings")

    builds.Worker.mutation = invalid
    # Boundary 2 retains the first worker reply before decoding it.
    saved = builds.execute(case, max_operations=2 if role == "worker" else None)
    assert saved["build"]["status"] == ("paused" if role == "worker" else "failed")
    result = inspect(case, capsys, monkeypatch)
    assert result["blocking"] and "response contract" in result["summary"]
    assert result["evidence"]["rejected_reply"]["source"] == role
    assert "Use resume" not in result["next_action"]
    count = len(builds.Worker.seen)
    assert builds.execute(case)["build"]["status"] == "failed"
    assert len(builds.Worker.seen) == count


def test_failed_draft_action_does_not_repeat_the_acceptance_suggestion(work, capsys):
    directory, _ = console.create(work, capsys)
    result = console.invoke(
        capsys,
        "plan",
        "--task-dir",
        directory,
        "--accept",
        "--checkpoint",
        "0" * 64,
        code=2,
    )
    assert (
        result["blocking"]
        and "exact displayed work checkpoint" in result["error"]["detail"]
    )
    assert "--accept" not in result["next_action"]


@pytest.mark.parametrize("requirement", ["runner", "planner"])
def test_unavailable_required_draft_setup_does_not_offer_acceptance(
    work, capsys, monkeypatch, requirement
):
    case = builds.prepare(work, accept=False)
    request = case[2]["request"]
    changes = (
        {"effects": {**request["effects"], "checks": []}}
        if requirement == "runner"
        else {
            "assignments": [a for a in request["assignments"] if a["role"] != "planner"]
        }
    )
    revised = revise_work(
        case[1], checkpoint=case[2]["checkpoint_digest"], changes=changes
    )
    result = inspect(case, capsys, monkeypatch)
    assert result["status"] == "draft" and result["blocking"]
    assert result["readiness_error"] and "--accept" not in result["next_action"]
    failed = console.invoke(
        capsys,
        "plan",
        "--task-dir",
        case[1],
        "--accept",
        "--checkpoint",
        revised["checkpoint_digest"],
        code=2,
    )
    assert failed["blocking"] and "--accept" not in failed["next_action"]
    assert read_task(case[1])["status"] == "draft"


def test_paused_file_effect_batch_does_not_offer_dependent_resume(
    work, capsys, monkeypatch
):
    case = effects.prepare(work)
    effects.execute(case, max_operations=1)
    result = inspect(case, capsys, monkeypatch)
    assert result["status"] == "paused"
    assert "owning file-effect API" in result["next_action"]
    assert "Use resume" not in result["next_action"]
    assert effects.execute(case)["build"]["status"] == "completed"
