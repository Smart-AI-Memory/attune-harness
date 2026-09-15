"""Fault-sensitive checks of the disposable adapter, without provider calls."""

import hashlib
import json
from dataclasses import replace

import pytest

from attune_harness import Check, Output, Status, Task
from attune_harness.adapters import Attempt, JsonParticipant


def assignment():
    return Attempt(Task("t1", "Compute 2 + 2", ("Return 4",)), "a1", "r1", "peer", "reviewer", "test-v1")


def response(request, text="4"):
    return json.dumps(dict(version=1, request_digest=hashlib.sha256(request.encode()).hexdigest(), text=text))


def verify(task, output):
    return Check(output.text == "4", "arithmetic oracle")


@pytest.mark.parametrize("answer,status", [("4", Status.VERIFIED), ("5", Status.REJECTED)])
def test_exchange_preserves_assignment_and_checks_answer(answer, status):
    work = assignment()
    requests = []
    def exchange(request):
        requests.append(json.loads(request))
        return response(request, answer)
    result = JsonParticipant(work, exchange).execute(verify)
    assert result.attempt is work
    assert result.receipt.task is work.task
    assert result.receipt.status is status
    assert requests[0]["attempt"]["requirement_revision"] == "r1"
    assert requests[0]["attempt"]["task"]["requirements"] == ["Return 4"]


@pytest.mark.parametrize("change", [
    {"attempt_id": "a2"}, {"requirement_revision": "r2"},
    {"participant_id": "other"}, {"role": "lead"}, {"adapter_version": "test-v2"},
    {"task": Task("t2", "Compute 2 + 2", ("Return 4",))},
    {"task": Task("t1", "Changed objective", ("Return 4",))},
    {"task": Task("t1", "Compute 2 + 2", ("Changed requirement",))},
])
def test_stale_response_cannot_reach_verifier(change):
    stale = response(replace(assignment(), **change).request())
    result = JsonParticipant(assignment(), lambda _: stale).execute(lambda *_: pytest.fail("stale output verified"))
    assert result.receipt.status is Status.FAILED
    assert "does not match" in result.receipt.error


@pytest.mark.parametrize("raw", [
    None, [], '{"text":', '[]', 'null', '{}',
    '{"version":1,"version":1,"request_digest":"x","text":"4"}',
])
def test_malformed_response_is_explicit_failure(raw):
    receipt = JsonParticipant(assignment(), lambda _: raw).execute(verify).receipt
    assert receipt.status is Status.FAILED
    assert receipt.output is None
    assert receipt.error.startswith("participant:")


@pytest.mark.parametrize("change", [
    {"version": True}, {"version": 2}, {"text": ""}, {"text": 4},
    {"request_digest": None}, {"complete": True},
])
def test_invalid_envelope_never_verifies(change):
    def exchange(request):
        data = json.loads(response(request))
        data.update(change)
        return json.dumps(data)
    assert JsonParticipant(assignment(), exchange).execute(verify).receipt.status is Status.FAILED


def test_byte_limit_counts_utf8_and_accepts_exact_boundary():
    raw = response(assignment().request(), "é").replace('\\u00e9', 'é')
    size = len(raw.encode())
    good = JsonParticipant(assignment(), lambda _: raw, max_response_bytes=size)
    assert good.run(assignment().task) == Output("é")
    bad = JsonParticipant(assignment(), lambda _: raw, max_response_bytes=size-1)
    assert "byte limit" in bad.execute(verify).receipt.error


@pytest.mark.parametrize("fail", [False, True])
def test_repeated_call_does_not_dispatch_even_after_failure(fail):
    calls = []
    def exchange(request):
        calls.append(request)
        if fail:
            raise TimeoutError("effects unknown")
        return response(request)
    adapter = JsonParticipant(assignment(), exchange)
    first = adapter.execute(verify)
    second = adapter.execute(verify)
    assert first.receipt.status is (Status.FAILED if fail else Status.VERIFIED)
    assert second.receipt.status is Status.FAILED
    assert "already dispatched" in second.receipt.error
    assert len(calls) == 1


def test_wrong_task_does_not_consume_attempt():
    adapter = JsonParticipant(assignment(), response)
    with pytest.raises(ValueError, match="task does not match"):
        adapter.run(Task("other", "other", ("other",)))
    assert adapter.execute(verify).receipt.status is Status.VERIFIED


def test_verifier_failure_keeps_identity_and_output():
    result = JsonParticipant(assignment(), response).execute(lambda *_: None)
    assert result.attempt == assignment()
    assert result.receipt.status is Status.FAILED
    assert result.receipt.output == Output("4")
    assert result.receipt.error.startswith("verification:")


@pytest.mark.parametrize("change", [{"task": None}, {"attempt_id": ""}, {"requirement_revision": " "}, {"participant_id": 1}, {"role": "admin"}, {"adapter_version": ""}])
def test_invalid_assignment(change):
    with pytest.raises((TypeError, ValueError)):
        replace(assignment(), **change)


@pytest.mark.parametrize("limit", [0, -1, True, "1"])
def test_invalid_limit(limit):
    with pytest.raises(ValueError):
        JsonParticipant(assignment(), response, max_response_bytes=limit)


def test_invalid_adapter_inputs():
    with pytest.raises(TypeError):
        JsonParticipant(None, response)
    with pytest.raises(TypeError):
        JsonParticipant(assignment(), None)
