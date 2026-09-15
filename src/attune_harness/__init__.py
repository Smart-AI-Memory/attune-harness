"""Minimal portable execution contracts; no provider dependencies."""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Protocol


def _text(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")


@dataclass(frozen=True)
class Task:
    """Immutable accepted work; schema revision is explicit."""

    task_id: str
    objective: str
    requirements: tuple[str, ...]
    schema_version: int = 1

    def __post_init__(self) -> None:
        _text(self.task_id, "task_id")
        _text(self.objective, "objective")
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("unsupported schema_version")
        if not isinstance(self.requirements, tuple) or not self.requirements:
            raise ValueError("requirements must be a nonempty tuple")
        for requirement in self.requirements:
            _text(requirement, "requirement")


@dataclass(frozen=True)
class Output:
    """Participant output, which makes no claim of verified completion."""

    text: str

    def __post_init__(self) -> None:
        _text(self.text, "output text")


@dataclass(frozen=True)
class Check:
    """Acceptance decision with a human-readable evidence description."""

    accepted: bool
    evidence: str

    def __post_init__(self) -> None:
        if type(self.accepted) is not bool:
            raise ValueError("accepted must be a boolean")
        _text(self.evidence, "evidence")


class Status(str, Enum):
    """Terminal states for this synchronous experiment."""

    VERIFIED = "verified"
    REJECTED = "rejected"
    FAILED = "failed"


class Participant(Protocol):
    """Provider-independent executor interface."""

    def run(self, task: Task) -> Output:
        """Return output for the accepted task."""
        ...


@dataclass(frozen=True)
class Receipt:
    """Execution outcome retaining the original task and check evidence."""

    task: Task
    participant_id: str
    status: Status
    output: Output | None = None
    check: Check | None = None
    error: str | None = None


def run(
    task: Task,
    participant_id: str,
    participant: Participant,
    verify: Callable[[Task, Output], Check],
) -> Receipt:
    """Execute once and apply an independent check; never retry implicitly.

    Ordinary extension exceptions become failed receipts with diagnostics.
    Process interrupts propagate. This function is not an isolation boundary.
    """
    if not isinstance(task, Task):
        raise TypeError("task must be a Task")
    _text(participant_id, "participant_id")
    output = None
    stage = "participant"
    try:
        candidate = participant.run(task)
        if not isinstance(candidate, Output):
            raise TypeError("participant must return Output")
        output = candidate
        stage = "verification"
        check = verify(task, output)
        if not isinstance(check, Check):
            raise TypeError("verifier must return Check")
    except Exception as error:
        return Receipt(
            task,
            participant_id,
            Status.FAILED,
            output=output,
            error=f"{stage}: {type(error).__name__}: {error}",
        )
    status = Status.VERIFIED if check.accepted else Status.REJECTED
    return Receipt(task, participant_id, status, output, check)
