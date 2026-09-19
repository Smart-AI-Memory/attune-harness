"""A rejected model reply is retained evidence, never effect authority."""

import copy
import json

import pytest
import test_work_build as builds

from attune_harness.task_contract import read_task
from attune_harness.task_handoff import completed_source
from attune_harness.work_build import validate_build

work = builds.work
reset_worker = builds.reset_worker


def test_paused_unchanged_reply_is_readable_and_resume_fails_without_repeating(work):
    case = builds.prepare(work)

    def unchanged(payload, turn, peer):
        if turn["role"] == "worker" and turn["step"]["id"] == "wire":
            payload["files"][0]["text"] = turn["source_evidence"]["source.py"]

    builds.Worker.mutation = unchanged
    paused = builds.execute(case, max_operations=9)
    assert paused["build"]["status"] == "paused"
    assert paused["build"]["events"][-1]["kind"] == "participant_turn"
    assert read_task(case[1]) == paused
    assert len(builds.Worker.seen) == 2
    failed = builds.execute(case)
    assert failed["build"]["status"] == "failed"
    assert "unchanged file" in failed["build"]["error"]["detail"]
    assert read_task(case[1]) == failed
    assert builds.execute(case) == failed
    assert len(builds.Worker.seen) == 2
    assert (case[0] / "source.py").read_text() == "def value():\n    return 1\n"
    assert not any(
        e.get("item", {}).get("path") == "source.py" for e in failed["build"]["events"]
    )
    with pytest.raises(ValueError, match="completed dependent build"):
        completed_source(case[1])


@pytest.mark.parametrize(
    "bad",
    ["scope", "dependency", "omitted_output", "task_identity", "approval", "reviewer"],
)
def test_failed_reply_round_trips_without_repeating_or_granting_effects(work, bad):
    case = builds.prepare(work)

    def invalid(payload, turn, peer):
        if bad == "reviewer":
            if turn["role"] == "reviewer":
                payload.pop("findings")
        elif turn["role"] == "worker" and turn["step"]["id"] == "export":
            if bad == "scope":
                payload["files"][0]["path"] = "source.py"
            elif bad == "dependency":
                payload["dependencies"] = ["invented"]
            elif bad == "omitted_output":
                payload["files"].pop()
            elif bad == "task_identity":
                payload["task_id"] = "invented"
            else:
                payload["approved"] = True

    builds.Worker.mutation = invalid
    failed = builds.execute(case)
    assert failed["build"]["status"] == "failed"
    count = len(builds.Worker.seen)
    assert read_task(case[1]) == failed
    assert builds.execute(case) == failed
    assert len(builds.Worker.seen) == count
    if bad != "reviewer":
        assert not (case[0] / "pkg").exists()


@pytest.mark.parametrize("forged", ["completed", "trailing_effect", "host_metadata"])
def test_invalid_reply_cannot_hide_completion_effects_or_broken_host_metadata(
    work, forged
):
    case = builds.prepare(work)
    done = builds.execute(case)
    run = copy.deepcopy(done["build"])
    index = next(
        i for i, e in enumerate(run["events"]) if e["kind"] == "participant_turn"
    )
    reply = run["events"][index]["result"]["action"]
    payload = json.loads(reply["text"])
    payload["files"] = []
    reply["text"] = json.dumps(payload)
    if forged == "trailing_effect":
        run["status"] = "paused"
    elif forged == "host_metadata":
        run["events"] = run["events"][: index + 1]
        run["status"] = "paused"
        run["events"][-1]["result"]["untrusted_host_field"] = True
    with pytest.raises(ValueError):
        validate_build(run, done["request"])


def test_actual_native_unchanged_reply_is_retained_as_readable_failure(tmp_path):
    import importlib.util
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[1]
        / "experiments/plan_build/qualify_rejected_reply.py"
    )
    spec = importlib.util.spec_from_file_location("rejected_native_replay", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.qualify(tmp_path / "qualification")
    assert result["native_calls"] == 0
    assert result["paused_readable"] and result["failed_readable"]
    assert result["file_effects"] == result["repeated_participant_calls"] == 0
