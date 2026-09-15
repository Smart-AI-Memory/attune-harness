"""Behavioral checks for the portable contract experiment."""

from dataclasses import FrozenInstanceError

import pytest

from attune_harness import Check, Output, Status, Task, run
from attune_harness.__main__ import main


class Stub:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def run(self, task):
        self.calls += 1
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


def task():
    return Task("t1", "Compute 2 + 2", ("Return 4",))


def check(work, output):
    return Check(output.text == "4", "Compared with arithmetic oracle")


@pytest.mark.parametrize(
    "answer,status", [("4", Status.VERIFIED), ("5", Status.REJECTED)]
)
def test_acceptance_is_independent(answer, status):
    work = task()
    participant = Stub(Output(answer))
    receipt = run(work, "test", participant, check)
    assert receipt.status is status
    assert receipt.task is work
    assert receipt.check.evidence == "Compared with arithmetic oracle"
    assert participant.calls == 1


@pytest.mark.parametrize("result", [RuntimeError("offline"), "invalid", None])
def test_participant_failure_never_verifies_or_retries(result):
    participant = Stub(result)
    receipt = run(task(), "test", participant, check)
    assert receipt.status is Status.FAILED
    assert receipt.output is None
    assert receipt.check is None
    assert receipt.error.startswith("participant:")
    assert participant.calls == 1


@pytest.mark.parametrize("mode", ["raise", "invalid"])
def test_verification_failure_retains_output(mode):
    def broken(work, output):
        if mode == "raise":
            raise RuntimeError("oracle unavailable")
        return True

    receipt = run(task(), "test", Stub(Output("4")), broken)
    assert receipt.status is Status.FAILED
    assert receipt.output.text == "4"
    assert receipt.error.startswith("verification:")


@pytest.mark.parametrize(
    "fields",
    [
        {"task_id": " "},
        {"objective": ""},
        {"requirements": ()},
        {"requirements": ["x"]},
        {"requirements": ("",)},
        {"schema_version": 2},
        {"schema_version": True},
    ],
)
def test_invalid_tasks_rejected(fields):
    values = dict(task_id="t1", objective="work", requirements=("x",))
    values.update(fields)
    with pytest.raises(ValueError):
        Task(**values)


def test_contract_rejects_invalid_values_and_mutation():
    with pytest.raises(FrozenInstanceError):
        task().objective = "changed"
    with pytest.raises(ValueError):
        Output("")
    with pytest.raises(ValueError):
        Check(1, "evidence")
    with pytest.raises(ValueError):
        Check(True, "")
    with pytest.raises(TypeError):
        run(None, "test", Stub(Output("4")), check)
    with pytest.raises(ValueError):
        run(task(), "", Stub(Output("4")), check)


def test_interrupt_is_not_swallowed():
    with pytest.raises(KeyboardInterrupt):
        run(task(), "test", Stub(KeyboardInterrupt()), check)


def test_demo(capsys):
    main()
    import json

    receipt = json.loads(capsys.readouterr().out)
    assert receipt["status"] == "verified"
    assert receipt["task"]["requirements"] == ["Return the exact integer"]
