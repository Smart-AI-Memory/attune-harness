# E2 revision: historical evidence and actual-call results

2026-09-14. Patrick requested fixing the availability-cache proposal. Done when
the revised policy passes the frozen local comparison and failure-sensitive
tests, while retaining the original experiment and its failed hypothesis.

Cases: working, runtime broken without metadata change, missing dependency,
upgraded artifact, disabled extension, denied grant; both command-review and MCP.
Also repeat a requested call after a successful call while the fixture backend
breaks without metadata change. Reject substituted old call records, changed
scope, forged result summaries, malformed observations and uncorrelated replies.
Missing or stale history must not block an otherwise authorized current call.

Scratch probe actually ran the installed command-review adapter successfully,
then injected the runtime fault and repeated it: identical descriptors, a real
first result and a failed second call. [Raw evidence](receipts/e2-revision/disposable.json).
An initial scratch attempt used a symlinked temporary path and failed descriptor
snapshot validation; the successful probe used a canonical /private/tmp path.

Replace prediction with an invocation plan. Current grants, declarations,
lifecycle and exact dependencies determine whether an invocation may be attempted;
history only labels a prior matching/stale/invalid observation. Neither history
nor the plan establishes current availability. The caller executes the requested
operation once, then consumes that operation's scoped result. Correlate its unique
run directory, current descriptor, actual durable event and transport result.
Do not return an old cached tool result. Every completion still declares general
availability unverified, including immediately after success.

Rejected: a TTL or probe-then-assume-available cache. Both leave a race between
observation and use. Also rejected: always refuse work to avoid false claims;
working and upgraded invocations must return independently checked actual results.
The independent evaluation oracle may invoke the read-only fixture separately;
that extra call is evaluation instrumentation, not the proposed consumer workflow.

Implement under experiments/e2_revision and preserve experiments/e2 unchanged.
The original general-availability claim remains disproven; adoption of this
narrower contract is a new hypothesis, not a retroactive passing original result.
Production already preserves call-bound evidence and needs no availability-cache
patch. No provider calls, credentials, environment upgrades or package release.
