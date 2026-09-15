# Local Phase 3 recovery receipt — 2026-09-14

Implemented the authorized bounded recovery increment. New reviews can pause and
resume from saved evidence, reconcile a lost participant reply, explicitly retry
one known read-only operation, transfer the local lead assignment in both
directions, and cancel stopped work without claiming external effects were undone.

## Behavior delivered

- Prepared, dispatching and completed checkpoints distinguish operations that
  never started from operations that may have executed. Stable operation/turn IDs
  reconstruct the workflow; completed operations are not invoked again.
- Resume rechecks the original accepted request, registry, document/context and
  bounded Markdown source snapshot. Every mutation requires the current checkpoint
  digest and a nonblocking POSIX writer lock. A dead owner's lock is released by
  the OS; stale decisions, copied run directories and corrupt checkpoints fail.
- Reconciliation retains the exact recovered reply and provenance, or permits
  one additional known read-only attempt. Unknown effects in external transports
  or verification cannot use the read-only retry path. Recovered actions still
  pass normal tool grants and argument checks when the workflow continues.
- Local transfer selects a participant from the accepted registry, creates a new
  attempt and retains prior lead work as context. Accepted constraints and the
  original revision stay unchanged. Reviewer execution is independent; transfer
  cannot overlap it or bypass unresolved effects. This experiment allows two
  transfers. No provider-level governance authority is copied or reassigned.
- Old Phase 2 records remain inspectable, without automatic migration to executable
  state. New optional data is preserved; future control versions fail closed.

See the [design note](design-recovery-increment.md), [operator instructions](recovery-workflow.md),
[installed example summary](receipts/recovery-example.json) and
[complete example record](../examples/recovery/installed-run/record.json).

## Evidence

Baseline: **252 tests passed**. Final: **319 tests passed**, **97.50% statement
coverage** (1132/1161). [Suite output](receipts/recovery-suite.txt),
[coverage data](receipts/recovery-coverage.json). All 67 added recovery cases pass.

The suite covers resumption at all 13 completed-operation boundaries, faults at
prepared/dispatch/result-write boundaries, changed inputs, concurrent owners and
process death, stale decisions, optional/future record fields, cancellation and
effect reconciliation. A real local command wrote an effect marker and a reply,
then exited unsuccessfully. Resume was blocked until the reply was reconciled;
the final workflow completed with the marker written **exactly once**.

The **24-case deterministic transfer matrix** covers four evidence cases
(verified, refuted, unknown, no sources), three checkpoints and two directions.
It asserts the accepted revision, prior evidence and reviewer independence remain
intact. This is a bounded adaptation, not the full E1 evaluation across four task
types with repeated live models and a measured existing-handoff baseline.

Five targeted tests against changed existing code failed with their respective
guards removed: **5/5**. Disposable source copies tested profile isolation,
checkpoint integrity, corpus snapshot consistency, writer locking and CLI routing.
[Mutation receipt](receipts/recovery-mutations.json); individual raw outputs are
linked by filename in the receipts directory. Production source was not mutated.

**63 installed CLI cases passed** with `python -I` outside the source tree, using
the final wheel in five isolated dependency profiles:

| Check | Cases | Receipt |
|---|---:|---|
| Core regression | 3 | [result](receipts/recovery-regression-core.json) |
| Verification-only regression | 8 | [result](receipts/recovery-regression-verify.json) |
| Retrieval-only regression | 5 | [result](receipts/recovery-regression-rag.json) |
| Both feature extras regression | 10 | [result](receipts/recovery-regression-all.json) |
| Review workflow regression | 12 | [result](receipts/recovery-review-regression.json) |
| Core-only inspection/form absence | 2 | [result](receipts/recovery-core-regression.json) |
| Recovery controls and uncertain command | 23 | [result](receipts/recovery-installed.json) |

Console help checks passed. The installed two-way transfer example completed with
verified document claims, 17 retained events and unchanged accepted constraints.
The prior Phase 2 installed wheel rejected resume-review as an unknown command;
[baseline output](receipts/recovery-phase2-baseline.txt). That establishes the
previous surface, not a quantitative quality comparison with Attune's handoff.

Testing caught and fixed a shared recovery-profile object: mutating one record
could otherwise change the engine's accepted version. The mutation probe confirms
the fix is failure-sensitive. The installed fixture also exposed an incorrect
expectation about a one-term retrieval query; the actual library returned no
results correctly. The fixture now uses a verified matching query and asserts
positive versus no-source outcomes explicitly.

## Build and qualification boundary

Wheel: `attune_harness-0.1.0.dev0-py3-none-any.whl`  
SHA256: `7d20570b7ea5407d4ad8e00f5b9f43eb56b95da706521bd2eda0e84376012bfc`

Dependency pins are unchanged: forms 0.17.0, verify 0.6.0, rag 1.2.0. No new runtime
dependency was added. The installed test environments contain no attune-ai or
mandatory provider SDK. Validation ran on macOS/Python 3.10.11. Recovery mutations
require POSIX file locks; Windows and cross-machine recovery are not qualified.
No source checkout outside Harness was edited, and nothing was committed,
published, deployed or scheduled. Harness still has no Git metadata.

**Provider calls: 0.** Tests used deterministic participants, injected native
transports and known local process fixtures. No credential action, account recharge
or paid model invocation occurred. Claude qualification remains on hold.

This completes the bounded local recovery increment, not every roadmap Phase 3
obligation. Live Phase 2 qualification, full E1 repetitions/comparison, moving
artifacts between machines, provider-level authority transfer and general external
effect reconciliation remain outstanding. The source snapshot excludes arbitrary
external verifier inputs; cached checks remain evidence from their original calls,
not fresh verification of an interpreter, service or mutable external target.
An uncertain verification operation remains blocked. No exactly-once guarantee or
automatic retry policy was introduced.
