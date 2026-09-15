"""Independent deterministic consumer; run against an installed wheel."""

import hashlib
import json

from attune_harness import Check, Task
from attune_harness.adapters import Attempt, JsonParticipant


def exchange(request):
    """Simulate a peer. Native adapters must translate their own wire format."""
    data = json.loads(request)
    assert data["attempt"]["task"]["objective"] == "Compute 2 + 2"
    return json.dumps({
        "version": 1,
        "request_digest": hashlib.sha256(request.encode("utf-8")).hexdigest(),
        "text": "4",
    })


attempt = Attempt(
    Task("example", "Compute 2 + 2", ("Return the exact integer",)),
    "example-attempt-1", "requirements-1", "deterministic-peer", "worker", "fixture-1",
)
adapter = JsonParticipant(attempt, exchange)
result = adapter.execute(lambda task, output: Check(output.text == "4", "arithmetic oracle"))
assert result.receipt.status == "verified"
assert adapter.execute(lambda *_: Check(True, "must not run")).receipt.status == "failed"
print(json.dumps({"attempt_id": result.attempt.attempt_id, "status": result.receipt.status}))
