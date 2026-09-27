# Voyage embed/rerank adapter: host-owned paid-stage journal

This slice ends at the paid-stage subprocess adapter. Selected index
construction remains explicitly unavailable until its separate index tool
is implemented. All probes use offline fake runners; no credential or paid
call is part of this evidence.

## Contract and order

1. Resolve the PR155 pin and selected run tool under the existing selected
   bundle signature, closure, enabled-state and grant checks. The accepted
   registry records the exact Voyage network declaration; it does not by
   itself authorize a paid call. The per-invocation `allow_provider` flag and
   a concrete host-owned Voyage paid-stage context authorize a *new* embed or
   rerank dispatch. Generic MCP `run` remains unable to execute network
   declarations. No generic `allow_network` switch is added.
2. The host StageJournal keeps the existing key, request-byte bound, call
   reserve, ledger, `prepared`, `dispatching`, `completed`, result validation,
   usage and replay semantics. For a completed stage, validate and replay from
   the host record before checking `allow_provider` or reading
   `VOYAGE_API_KEY`. A missing key refuses a new or prepared dispatch before
   `dispatching` and, preferably, before creating a new prepared sidecar.
3. Immediately before launching the selected subprocess, persist
   `dispatching` and form a Voyage-specific context bound to that stage key,
   exact canonical request/profile digest, kind, accepted local tool name,
   configuration digest and bundle. The runner refuses a mismatched argument,
   role or index tool before invoking a child. It receives the signed archive, bounded
   embed/rerank arguments, named granted inputs and a scratch directory. It
   receives the key only in its filtered environment; request, receipt and
   diagnostics retain the **name**, never the value. The ledger path stays in
   host-only guarded paths and out of child request paths. This excludes the
   path from a cooperating child's declared inputs; it is not an OS sandbox.
   Re-read and recheck the accepted registration revision, enabled state and bundle after execution before accepting the result,
   as the current run binding does.
4. The adapter extracts the child result and lets the existing host
   `embeddings`/`ranking` and `usage` checks decide validity. A timeout or
   killed/interrupted child becomes `PaidStageInterrupted`; StageJournal leaves
   the durable `dispatching` record and a later attempt refuses without a
   second call. A malformed result or ordinary SDK exception follows the
   existing `unresolved` path with safe, class-only diagnostics. Neither case
   retries. The child cannot write `completed` or calculate billing receipts.
5. Selected build/retrieve cannot fall back to builtin Voyage or attune-rag.
   Until the selected index tool materializes and publishes a generation,
   those high-level paths refuse before creating index/retrieval state. The
   adapter is exercised through the host journal with offline fake signed
   runners and compared with in-process journal fixtures.

## Offline probes

- A real signed fake runner returns indexed embed vectors and rerank order;
  the host validates counts, dimensions, indices, scores and token usage,
  then records equal stage states/receipts to the in-process fixture (ignoring
  process-specific timing and signer fields). A second invocation replays
  completed results with no key and `allow_provider=False` and no child launch.
- A fake runner sleeps past the bounded time or is killed after `dispatching`;
  the stage remains `dispatching`, retains its budget slot, and a fresh
  journal refuses another launch with either allow-provider value.
- Map `timeout_effects_unknown`, `interrupted_effects_unknown`,
  `cancelled_effects_unknown` and `output_limit` to
  `PaidStageInterrupted`/retained `dispatching`, testing each receipt failure
  against a fresh journal and proving no replay/re-dispatch. A completed
  record replays without key or permission and has zero new calls/cost.
- Missing secret, missing permission, pin drift, disabled/revoked bundle,
  wrong role and closure drift refuse before child launch. A missing key
  creates no new stage sidecar. An injected builtin provider is never called.
- Direct runner calls with wrong arguments, a rerank role or an index role
  against an embed stage refuse before launch. A registration changed or
  disabled while the child executes cannot complete the host stage.
- Invalid JSON/schema, wrong embed indices/vector dimensions, duplicate
  rerank indices, invalid usage and changed guarded host evidence are all
  refused and retain unresolved evidence. The child cannot access the ledger
  through granted paths; no key value appears in any saved receipt or error.
- Direct generic MCP network `run` still refuses. Selected index build and
  retrieve still refuse without publishing or preparing state.

## Contract ruling

Root approved conservative interruption handling for `output_limit` as well
as timeout, interrupt and cancellation: a bounded output kill cannot prove
the paid effect did not occur. `nonzero_exit` and invalid responses retain
the ordinary `unresolved` record. Neither state allows automatic retry, and
`process.py` needs no behavior change for this classification.
