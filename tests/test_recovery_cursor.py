"""RecoveryCursor's begin/fail/finish split keeps perform's behavior (#233, D1)."""

import copy

import pytest

from attune_harness.native import NativeError
from attune_harness.recovery import RecoveryCursor, ReviewPaused, UnresolvedOperation


class Store:
    """Records each durable save so tests can see what was saved before a call."""

    def __init__(self):
        self.saves = []

    def save(self, record):
        self.saves.append(copy.deepcopy(record))


def cursor(events=(), limit=None, profile=None):
    record = {"events": [copy.deepcopy(event) for event in events]}
    if profile is not None:
        record["profile"] = profile
    return RecoveryCursor(record, Store(), limit)


def completed(key, result, kind="participant_turn", effect_class="external"):
    return {
        "event_id": f"id-{key}",
        "operation_key": key,
        "state": "completed",
        "phase": "completed",
        "attempts": 1,
        "kind": kind,
        "effect_class": effect_class,
        "result": result,
    }


def test_new_operation_is_durable_before_call_and_saved_after():
    cur = cursor()
    phases = []

    def call():
        phases.append([save["events"][0]["phase"] for save in cur.store.saves])
        return {"answer": 1}

    assert cur.perform("k", "participant_turn", call, effect_class="external") == {"answer": 1}
    assert phases == [["prepared", "dispatching"]]
    event = cur.store.saves[-1]["events"][0]
    assert (event["state"], event["phase"], event["result"]) == (
        "completed",
        "completed",
        {"answer": 1},
    )
    assert cur.completed == 1


def test_replay_returns_a_copy_without_calling_or_counting():
    cur = cursor([completed("k", {"answer": 1})])
    result = cur.perform("k", "participant_turn", pytest.fail, effect_class="external")
    assert result == {"answer": 1}
    result["answer"] = 2
    assert cur.events["k"]["result"] == {"answer": 1}
    assert (cur.completed, cur.store.saves) == (0, [])


def test_mismatched_request_is_rejected_before_any_call():
    cur = cursor([completed("k", {"answer": 1})])
    with pytest.raises(ValueError, match="does not match"):
        cur.perform("k", "participant_turn", pytest.fail, effect_class="read_only")
    assert cur.store.saves == []


def test_unresolved_dispatch_is_rejected_before_any_call():
    event = completed("k", None)
    event.update(state="pending", phase="dispatching")
    del event["result"]
    cur = cursor([event])
    with pytest.raises(UnresolvedOperation, match="reconcile before resume"):
        cur.perform("k", "participant_turn", pytest.fail, effect_class="external")
    assert cur.store.saves == []


@pytest.mark.parametrize(
    "effect_class, effects", [("external", "unknown"), ("read_only", "read_only")]
)
def test_exception_records_failure_without_another_save(effect_class, effects):
    cur = cursor()

    def call():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        cur.perform("k", "participant_turn", call, effect_class=effect_class)
    event = cur.events["k"]
    assert event["state"] == "failed"
    assert event["error"] == {"type": "RuntimeError", "detail": "boom"}
    assert event["effects"] == effects
    assert [save["events"][0]["phase"] for save in cur.store.saves] == ["prepared", "dispatching"]
    assert cur.completed == 0


def test_exception_keeps_native_refusal_for_review_turns():
    refusal = {"kind": "claude_structured_error", "returncode": 1}
    cur = cursor()

    def call():
        raise NativeError("refused", refusal=refusal)

    with pytest.raises(NativeError):
        cur.perform("k", "participant_turn", call, effect_class="external")
    assert cur.events["k"]["native_refusal"] == refusal
    assert "native_failure" not in cur.events["k"]


def test_exception_keeps_native_failure_for_feature_builds():
    cur = cursor(profile="feature-build-v1")

    def call():
        raise NativeError("stopped", failure="timeout", process_stopped=True)

    with pytest.raises(NativeError):
        cur.perform("k", "participant_turn", call, effect_class="external")
    assert cur.events["k"]["native_failure"] == {"failure": "timeout", "process_stopped": True}


def test_base_exception_leaves_the_dispatch_unresolved():
    cur = cursor()

    def call():
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        cur.perform("k", "participant_turn", call, effect_class="external")
    event = cur.events["k"]
    assert (event["state"], event["phase"]) == ("pending", "dispatching")
    assert "effects" not in event


def test_pause_comes_after_the_result_is_saved():
    cur = cursor(limit=1)
    with pytest.raises(ReviewPaused):
        cur.perform("k", "participant_turn", lambda: {"answer": 1}, effect_class="external")
    assert cur.store.saves[-1]["events"][0]["result"] == {"answer": 1}


def test_replay_does_not_consume_the_operation_limit():
    cur = cursor([completed("a", {"answer": 1})], limit=1)
    assert cur.remaining() == 1
    assert cur.perform("a", "participant_turn", pytest.fail, effect_class="external") == {
        "answer": 1
    }
    assert not cur.limit_reached()
    with pytest.raises(ReviewPaused):
        cur.perform("b", "participant_turn", lambda: {"answer": 2}, effect_class="external")
    assert cur.events["b"]["result"] == {"answer": 2}
    assert (cur.remaining(), cur.limit_reached()) == (0, True)


def test_remaining_is_none_without_a_limit():
    cur = cursor()
    cur.perform("k", "participant_turn", lambda: 1, effect_class="external")
    assert (cur.remaining(), cur.limit_reached()) == (None, False)


def test_begin_and_finish_save_what_perform_saves():
    split, whole = cursor(), cursor()
    replayed, event = split.begin("k", "participant_turn", effect_class="external")
    assert not replayed and event["phase"] == "dispatching"
    split.finish(event, {"answer": 1})
    whole.perform("k", "participant_turn", lambda: {"answer": 1}, effect_class="external")

    def without_ids(saves):
        return [[{**e, "event_id": None} for e in save["events"]] for save in saves]

    assert without_ids(split.store.saves) == without_ids(whole.store.saves)
    assert split.completed == whole.completed == 1


def test_begin_replays_a_completed_operation():
    cur = cursor([completed("k", {"answer": 1})])
    assert cur.begin("k", "participant_turn", effect_class="external") == (True, {"answer": 1})
