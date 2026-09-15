# A2A local peer profile — design before implementation

2026-09-14. Phase 4 continuation: qualify one independently implemented local
HTTP peer against A2A 1.0 JSON-RPC. Done for this increment: pinned discovery,
bounded task/artifact round trip, local operation grants, HTTP access refusals,
correlation, disconnect and cancellation receipts from an installed package.
Production remote authentication and general A2A conformance remain outside this
credential-free increment.

The disposable `/tmp/harness-a2a-disposable.py` used a stdlib HTTP server/client:
SendMessage created exactly one task then closed before acknowledging; a later
GetTask returned its completed artifact. [Probe result](receipts/a2a-disposable.json).
The default sandbox refused local socket binding; the loopback-only probe passed
with automatic escalation approval. The scratch client knew the task ID only
because the fixture fixed it. Production code must never infer an unknown ID or
repeat SendMessage after that failure.

Use a new optional-in-behavior, dependency-free `A2AExchange` callable for the
existing JsonParticipant boundary. Send its canonical request as a data part;
receive the correlated response in one data artifact. JsonParticipant still
owns independent verification. Peer completion never means verified output.
Pin the exact agent card digest, name, endpoint and selected 1.0 JSONRPC interface.
Only literal 127.0.0.1 HTTP endpoints are executable in this first profile. No
DNS, proxy settings, redirects, credentials, external artifact URL fetches or
card-selected endpoint changes. A digest is identity correlation, not authentication.

Enumerate success (immediate/polled completion, matching artifact); failure
(unknown revision, changed card, denied operation, HTTP 401/403, wrong RPC/task
identity, invalid state, missing/duplicate artifact, unsupported media, oversized
or malformed JSON); lifecycle (known-task poll disconnect then refresh, unknown
submission outcome, working cancellation, lost cancel response then refresh,
late cancellation, persistence failure). One submission per exchange and a finite
request budget. Save pending operations before dispatch under the existing local
writer lease. Reconnect only through explicit read-only GetTask for a known ID;
never automatically repeat SendMessage or an uncertain CancelTask. Mark local
unresolved records truthfully. No cross-process resumption is introduced.

Socket inactivity timeout and payload/request-count bounds apply; no aggregate
hard wall-clock limit or remote cancellation guarantee is claimed. The fixture
uses a separate process with no Harness imports, maintains actual task state and
returns a computed arithmetic artifact. Local allow/deny policy plus server-side
403 behavior tests access handling without pretending to qualify authentication.
Reject a full SDK/server framework and review-roster integration for this first
profile: they would add unmeasured surfaces before basic interoperability works.

Primary [A2A specification](https://a2a-protocol.org/latest/specification/) sections
3.2, 3.6, 4.1, 4.4 and 9 establish the selected wire contract. Current 1.0 uses
PascalCase method names, ROLE_USER, TASK_STATE_* and SendMessage's task wrapper;
do not reuse the obsolete 0.3 wire shapes. The profile is deliberately narrower
than the protocol. Raw receipts establish what was actually exercised.
