# Fix the four confirmed Sol review findings

September 16, 2026. Scope: the four defects confirmed in the
[Sol review](cross-review-sol-2026-09-16.md), their regression tests,
the affected usage/qualification documentation, and the existing budget mutation
probe affected by the guard change. Include the new host checks in the installed
platform test selection.
The existing in-flight work is the baseline; these fixes do not publish it.

The review's disposable, offline probes already showed: a one-call retrieval
budget consumes an embedding before failing; an exception outside plugin
search saves a completed lifecycle; an incomplete evaluator exits zero; and
optimized Python lets a failed host fixture produce a passed qualification.
The original probe outputs remain in `docs/receipts/cross-review-sol-20260916/`.

Cases and implementation:

1. Before dispatching an uncached query embedding, the stage journal must have
   budget for that stage and the following rerank. The caller already holds
   the writer lease, so checking this capacity requires no new persistent
   reservation format. A prepared stage already occupies one slot; completed
   stages replay freely even at a full budget. Test fresh and partially spent
   budgets, prepared continuation, exact-budget success, and completed-stage
   replay after a lost final response/cache. Empty evidence still needs no calls.
2. Plugin activation must pass interruption to its finalizer when any exception
   leaves the context body, including cancellation and interrupts outside
   `search`. Preserve normal completion and propagation of the original error.
3. Evaluator CLI success means frozen or completed. Preserve the JSON report
   and saved failed/unrun cases, and return nonzero for an incomplete campaign.
4. Host qualification checks use explicit runtime checks that survive Python
   optimization. Each existing condition must reject an invalid fixture under
   both normal and optimized compilation; valid fixtures must still pass.

Rejected: an unconditional two-free-calls retrieval check, because completed
stage replay is free; changing accepted configuration or ledger schemas, because
existing immutable generations and recovery receipts must remain readable;
rejecting optimized Python entirely, because explicit checks are small and
keep the qualification command usable there.

Verification: run the new regression cases against the pre-fix code first,
then the affected suites on the fixed source. Exercise each restored pre-fix
guard in an isolated scratch copy and report which new cases detect it.
Use deterministic providers and controlled host fixtures; no paid evaluation
or frozen-campaign rerun is needed. Record the attributed diff and independently
run probes in the fix receipt.
