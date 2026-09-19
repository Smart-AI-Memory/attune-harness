# Plan/build Task 2 — shared work contract

Task 1 is accepted. Task 2 is implemented and locally qualified; its human
acceptance is pending. Tasks 3–8 have not started. Auto-run remains false.

The new [work contract](../src/attune_harness/work_contract.py) stores intent,
unresolved material questions, alternatives and their evidence/uncertainty,
authoring choice, configured assignments, budgets, dependent tasks and explicit
controls in the existing RunStore task envelope. Corrections preserve other
answers and accepted history while invalidating changed authority. Unchanged
content preserves its current decision. No new approval store or renderer exists.

Authoring follows the existing rules: continuity or consequential decisions call
for a spec; dependencies, cold handoff, material risk or an XML consumer call for
XML; simpler bounded work uses a prompt. File count is not a cutoff. These are
rules over explicit structured facts, not evidence of natural-language planning.

The existing reader recognizes this profile while preserving its old validators.
Legacy acceptance/revision APIs reject it explicitly, and the execution owner
refuses it until the later runtime is qualified. The preparation probe still
rejects its incomplete record; the original Task 1 receipt remains unchanged.

## Evidence

| Actual check | Result and limits |
| --- | --- |
| [Final source suite](receipts/plan-build-task2-2026-09-18/final-source-tests.xml) | 273 passed; 84 new contract cases plus existing assessment, repair, recovery, compatibility, test-task and preparation checks. One inherited Attune AI deprecation warning. No skip/xfail. |
| [Isolated wheel suite](receipts/plan-build-task2-2026-09-18/installed-final-tests.xml) | 272 passed outside the checkout. Excludes the one source-preparation experiment. No skip/xfail. |
| [Installed identity](receipts/plan-build-task2-2026-09-18/installed-identity.json) | Built current wheel locally, installed with no index/dependency resolution into a temporary target. Relevant installed/source module hashes match. Active installation untouched. |
| [Base import](receipts/plan-build-task2-2026-09-18/installed-base-import.log) | Actual installed contract imports with isolated Python and site packages disabled; no Attune AI/forms/verify/RAG import. |
| [Protection removal](receipts/plan-build-task2-2026-09-18/guard-removal.json) | Seven baseline negative cases pass; all five independently removed guards are detected: decision binding, storage owner, source freshness, required control and retained history. Expected failures retained. |
| [Coverage](receipts/plan-build-task2-2026-09-18/coverage.json) | New module: 313/329 executable lines, 95.14%. [All 12 added shared routing/guard lines](receipts/plan-build-task2-2026-09-18/changed-line-coverage.json) executed. This is line coverage, not branch or outcome-quality scoring. |
| [Lifecycle](receipts/plan-build-task2-2026-09-18/lifecycle.json) | Symbol reality and falsifiability PASS; 25 cited tokens checked. No waiver. |
| [Preservation](receipts/plan-build-task2-2026-09-18/preservation.json) | All 53 Task 1 receipts, the selected existing owners and protected feature oracle unchanged. Temporary synthetic project data only; no memory-store access. |

Black and Ruff pass on the new module and tests. The local review checked the
authority and profile boundaries; no independent model review, provider-backed
quality pipeline or native trial ran. The task score, if displayed by Spec, is
local checklist completion only.

The first isolated suite had 269 passes and three test-layout failures: a copied
helper script and a source-layout import path were absent. The disposable layout
was corrected to point only at wheel-installed package contents. All 272 then
passed without changing product code or test assertions. [Original output](receipts/plan-build-task2-2026-09-18/installed-tests.log)
and [correction](receipts/plan-build-task2-2026-09-18/installed-layout-correction.json)
are retained; no failure is silently discarded.

## Acceptance boundary

Decision projection is a trusted Python host seam. It validates a collected Spec
decision against the exact work revision, request, storage owner and checkpoint;
it cannot authenticate an arbitrary caller from a source-reference string. Task 6
must qualify the actual Spec collector bridge. Hashes do not defend against a
malicious local writer who can replace the entire store.
Source files are checked around decision validation but are not locked by the
task-store lease. Later execution must recheck freshness before governed use;
reading an accepted record alone is not permission to use stale inputs.

Required control availability binds its exact identity, owner, kind and version.
Availability is not evidence that a hook/check ran; Task 4 must enforce and retain
those results before effects. Unknown advisory controls remain visible. The
accepted contract grants no provider calls or filesystem effects.

The first profile uses an explicit external state directory, bounded regular UTF-8
inputs and a basic participant registry. Retrieval/extension registries fail
visibly on this new profile pending qualification; existing routes are preserved.
Planning competence, actual builds, interruption recovery and the full installed
verb journey remain later tasks. No additional native/paid call, activation or
release was performed.

The [opportunity log](opportunity-log.md) records the need for the future bridge to
distinguish executable plan content from its mutable state comment. Exact-byte
artifact freshness remains enforced here.

Recommended next decision: accept Task 2 and continue to Task 3's planning
assignments. The strongest counter-case is that the host/Spec integration remains
unqualified; this acceptance covers the contract boundary only.
