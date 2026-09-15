"""Disposable JSON adapter boundary; no native runtime is qualified here."""

import hashlib
import json
from dataclasses import asdict, dataclass
from threading import Lock
from typing import Callable

from . import Check, Output, Receipt, Task, _text, run


@dataclass(frozen=True)
class Attempt:
    """An assignment; role and identity are context, never authorization."""

    task: Task
    attempt_id: str
    requirement_revision: str
    participant_id: str
    role: str
    adapter_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.task, Task):
            raise TypeError("task must be a Task")
        for name in ("attempt_id", "requirement_revision", "participant_id", "adapter_version"):
            _text(getattr(self, name), name)
        if self.role not in ("lead", "reviewer", "worker"):
            raise ValueError("role must be lead, reviewer, or worker")

    def request(self) -> str:
        """Canonical v1 request. Its digest correlates, but does not authenticate."""
        return json.dumps(
            {"version": 1, "attempt": asdict(self)},
            sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        )


@dataclass(frozen=True)
class AttemptReceipt:
    """Keep assignment identity even when exchange or verification fails."""

    attempt: Attempt
    receipt: Receipt


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


class JsonParticipant:
    """Single-use, synchronous exchange with strict response validation.

    exchange accepts request JSON and returns response JSON. It owns transport,
    timeouts and any external effects. The byte limit bounds decoding, not network
    allocation. A failed call must not be assumed effect-free or safe to retry.
    """

    def __init__(
        self, attempt: Attempt, exchange: Callable[[str], str], *,
        max_response_bytes: int = 65_536,
    ) -> None:
        if not isinstance(attempt, Attempt):
            raise TypeError("attempt must be an Attempt")
        if not callable(exchange):
            raise TypeError("exchange must be callable")
        if type(max_response_bytes) is not int or max_response_bytes < 1:
            raise ValueError("max_response_bytes must be a positive integer")
        self._attempt = attempt
        self._exchange = exchange
        self._limit = max_response_bytes
        self._used = False
        self._lock = Lock()

    @property
    def attempt(self) -> Attempt:
        return self._attempt

    def run(self, task: Task) -> Output:
        """Accept one matching task; consume the attempt before dispatch."""
        if task != self.attempt.task:
            raise ValueError("task does not match bound attempt")
        with self._lock:
            if self._used:
                raise RuntimeError("attempt already dispatched; reconcile before new attempt")
            self._used = True
        request = self.attempt.request()
        raw = self._exchange(request)
        if not isinstance(raw, str):
            raise TypeError("exchange must return JSON text")
        if len(raw.encode("utf-8")) > self._limit:
            raise ValueError("response exceeds byte limit")
        response = json.loads(raw, object_pairs_hook=_unique_object)
        if not isinstance(response, dict) or set(response) != {"version", "request_digest", "text"}:
            raise ValueError("invalid response fields")
        if type(response["version"]) is not int or response["version"] != 1:
            raise ValueError("unsupported response version")
        digest = hashlib.sha256(request.encode("utf-8")).hexdigest()
        if response["request_digest"] != digest:
            raise ValueError("response does not match bound request")
        return Output(response["text"])

    def execute(self, verify: Callable[[Task, Output], Check]) -> AttemptReceipt:
        """Return correlated evidence using the existing independent verifier."""
        return AttemptReceipt(
            self.attempt,
            run(self.attempt.task, self.attempt.participant_id, self, verify),
        )
