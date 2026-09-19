# Plan/build Task 4 — bounded file effects and controls

Tasks 1–3 are accepted. Task 4 is implemented and locally qualified; its human
acceptance is pending. Tasks 5–8 have not begun. Auto-run remains false.

An accepted work request can now bind exact file creation/modification scope,
missing parent directories, protected acceptance inputs and trusted build checks.
The runtime enforces these through the existing task store, writer lease,
subprocess runner and recovery journal. All proposals are validated before the
first write. Required controls must actually pass; declaring them supported does
not satisfy them. Required controls from unqualified planning/acceptance phases
also block effects. Advisory failures remain visible.

New files refuse collisions and symlink traversal. Existing replacements retain
their qualified repair owner. Whole-checkout checks preserve unrelated dirty
work and metadata. Unknown writes are retained for explicit reconciliation;
completed writes are reused without repeating them. Partial files remain intact.
The optional effect contract and shared probe-validator extraction were necessary
changes to existing owners; no additional gate store or scheduler was added.

## Evidence

| Actual check | Result |
| --- | --- |
| Source tests | [636 passed](receipts/plan-build-task4-2026-09-18/final-source-tests.xml), plus the [new independent scope case](receipts/plan-build-task4-2026-09-18/final-scope-test.xml): **637 total**, including 87 effect/control cases and existing planning, contracts, repair, recovery, process, review, native-adapter and test routes. No skips or xfails; one inherited Attune AI deprecation warning. |
| Installed wheel | [636 passed](receipts/plan-build-task4-2026-09-18/installed-tests.xml) outside the source tree, excluding only the source-preparation experiment. [Four module hashes](receipts/plan-build-task4-2026-09-18/installed-identity.json) match current source. Base import needs no optional Attune packages. No active installation changed. |
| Protection removal | [9/9 detected](receipts/plan-build-task4-2026-09-18/guard-removal.json): scope, preimage, protected inputs, explicit parents, required runner, failed control, exclusive creation, snapshot transition and accepted authority. Each corresponding baseline case passes. |
| Changed-line coverage | [New effect module 95.36%; runtime additions 95.89%; contract additions 93.75%; shared repair changes 88.24%](receipts/plan-build-task4-2026-09-18/changed-line-coverage.json). These are software coverage figures, not model outcome scores. |
| Selected fixture | [Actual captured documentation module](receipts/plan-build-task4-2026-09-18/journey-result.json), fixed host-authored candidate, one accepted batch, five journaled operations. Protected baseline runs before effects; the [independent four-case feature oracle passes](receipts/plan-build-task4-2026-09-18/journey-oracle.json) afterward. Protected inputs and unrelated work survive. Later source changes invalidate stale success. Production documentation is unchanged. |
| Recovery | Real process death before, during and after creation; lost acknowledgment for directory creation, file creation and replacement; failed fsync; incomplete/zero-progress writes; explicit before-state retry ceiling; changed root/configuration/executable; corrupted post-write bytes; no blind repeats. Existing replacement process-death tests also pass. |
| Lifecycle and preservation | [Symbol reality and falsifiability PASS](receipts/plan-build-task4-2026-09-18/lifecycle.json), 40 cited tokens, no waiver. [All 135 files in prior Task 1–3 receipt manifests remain unchanged](receipts/plan-build-task4-2026-09-18/prior-receipts.json). |

The fixture's first useful baseline-control result was ready in **151 ms**; the
effect batch completed in **178 ms**. These are single backend observations with
local checks and a fixed candidate. They exclude model latency, desktop rendering
and human response time. The protected feature oracle runs separately afterward.

## Findings and corrections

The initial run retained in `initial-tests.xml` had two failures: one test fixture
omitted its declared control-support descriptor; the runtime discovered a missing
POSIX primitive only when acquiring its lock. The fixture now supplies the exact
descriptor, and platform availability is checked before lock acquisition.

The first scope-removal trial survived because a second preimage guard rejected
the same input. This was a gap in that mutation test, not evidence the scope guard
was unnecessary. An independent out-of-scope creation case now detects its
removal. Original mutation logs are retained alongside the successful rerun.

Review also tightened control-result binding and rejected required controls from
earlier phases without execution evidence. The failure tests demonstrate that
passing metadata or a declared support list cannot stand in for actual checks.

## Qualified boundary and next step

This is one batch in a dedicated, exclusively owned local POSIX Git checkout.
Bounded UTF-8 files, complete snapshots and explicit missing parents are supported.
Deletion, hostile concurrent writers, worktree Git indirection, Windows effects
and hardware/power-loss durability remain outside this profile. Trusted checks
run as bounded subprocesses; they are not a security sandbox.

Reconciliation verifies observed state under exclusive ownership. It cannot
attribute identical bytes to a particular writer. Partial content, foreign files,
leftover replacement staging files and interrupted controls remain unresolved;
the runtime does not silently delete them. Journal-preserving correction and the
broader human recovery surface remain Task 6.

The fixture uses a synthetic trusted-host Spec projection and a fixed host-written
candidate. It does not qualify an autonomous worker, dependent task execution or
the real collector bridge. No independent model review, provider-backed quality
pipeline, native/provider call, paid trial, activation or release ran.

Recommend accepting Task 4 and continuing with Task 5: execute the selected
feature through accepted dependent tasks and independent tests, including wrong
implementations and misleading generated tests. The strongest counter-case is
that operational integration and native outcome quality still need their own
evidence; Task 4 acceptance covers the disclosed local effect boundary only.
