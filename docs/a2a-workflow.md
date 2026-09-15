# Local A2A task/artifact profile

`attune_harness.a2a.A2AExchange` is a callable for the existing `JsonParticipant`.
It has no additional dependencies. The tested interface is A2A **1.0**, JSON-RPC
over literal `http://127.0.0.1:PORT/path`. Use an explicitly selected peer name,
endpoint and exact canonical agent-card SHA-256. Remote URLs, credentials,
redirects, required extensions and authenticated cards are unsupported.

The independent fixture and installed consumer are runnable in two terminals:

```sh
python3 -I examples/a2a/peer.py --log /tmp/harness-peer.json
```

Copy the printed endpoint and card_digest into the installed client's arguments:

```sh
.venv-core-check/bin/python -I examples/a2a/client.py --endpoint http://127.0.0.1:PORT/rpc --card-digest PRINTED_DIGEST --run-dir /tmp/new-harness-a2a-run
```

For the complete automated fixture journey, with no manual substitution:

```sh
python3 scripts/check_a2a_installed.py --python .venv-core-check/bin/python --report docs/receipts/a2a-installed.json
```

The client binds an immutable accepted Attempt, sends one canonical JSON request
as a data part, and accepts one matching data artifact. The fixture computes
integer addition without importing Harness. JsonParticipant independently checks
the returned answer. A peer's `TASK_STATE_COMPLETED` means protocol completion;
the independent receipt may still be rejected. Artifact and card hashes establish
local correlation, not signed provenance or remote identity authentication.

Constructor controls: `max_polls` 0–8 (default 4), `max_requests` 1–32 (default 12),
and LocalPeer socket inactivity timeout in (0,30] seconds (default 5). The local
operation grant set may include SendMessage, GetTask and CancelTask. Each dispatch
rechecks the pinned card and consumes the finite request budget. Requests are
limited to 64 KiB, cards to 16 KiB and responses to 256 KiB. No aggregate hard
wall-clock deadline is promised. Required task/context identity and one JSON data
artifact make this profile narrower than general A2A; no external URL is fetched.

One submission is allowed per exchange. Before dispatch, a pending event is saved
under a POSIX writer lease. Unacknowledged SendMessage is unresolved even if the
peer created a task. Without an acknowledged task ID, neither automatic retry nor
refresh can safely identify that work; reconcile with the peer owner.

For a known task, `exchange.refresh()` issues explicit read-only GetTask.
`exchange.cancel()` permits one CancelTask attempt. Losing the cancellation
response requires refresh; it cannot trigger another cancellation attempt.
Cancellation racing with completion preserves the returned completed artifact.
Late controls on an observed terminal task return the saved record without a
network request. Persistence failure stops subsequent dispatch.

`inspect_exchange(Path(...))` reads local records without execution. A saved
working/prepared record is displayed as unresolved. An unresolved historical
event can remain in the audit trail after a later GetTask establishes the current
remote state; that observation does not fabricate the missing acknowledgement.
The example retains the initial independent receipt unchanged after controls.

The record supports inspection, not process-restart resumption. This adapter is
not yet a review-roster adapter. HTTP 401/403 and local operation refusals are
tested without configuring authentication. Remote TLS/OAuth, production identity,
streaming, push, tenant routing, multi-turn input and general artifact types remain
unqualified. The fixture is a protocol test peer, not another language model.
