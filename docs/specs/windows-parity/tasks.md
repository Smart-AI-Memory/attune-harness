# Windows parity tasks

**Status: proposed, awaiting spec approval.** [Scope](README.md) and
[requirements](design.md) govern each task. Estimates are scope estimates, not
measured durations. Code work is paused; no task below is marked implemented.

## Order and gates

T1 establishes truthful coverage. T2 is the feasibility gate for saved storage
and comes before a production storage port. After T1, testing, reader and native
transport work can proceed in isolated branches; saved storage waits for T2.
Each code PR integrates through main under the existing review and merge rules.
Any shared primitive change lands before its consumers. A source delta after
review returns to its reviewer. No branch is merged automatically.

| Task | Scope and likely owners | Dependencies and risk | Done when |
|---|---|---|---|
| T1: Inventory and native baseline | Full CLI/refusal ledger; qualification workflow; platform claim correction; portable test fixtures. Start from draft #266 without declaring its run complete | First. Low production risk; medium CI/runtime uncertainty | Read both Windows full-suite results, classify every failure/skip by owner, retain results, and correct the saved-store platform claim. Add witnesses for missing journeys; expected red cases remain visible and cannot satisfy final parity |
| T2: Saved-store native proof | New bounded primitive experiment and native PR-triggered tests for lock sharing, private ACLs, file/namespace flush, atomic replacement and crash observation. Preserve existing experiments/receipts | After inventory; before T5. High semantic risk | A documented non-admin durability/ACL/locking protocol is supported by references and native observations on both Windows runtimes. Patrick receives a decision with evidence if equivalent semantics cannot be established; no downgrade is presumed |
| T3: Captured-change testing | `test_change`, `test_execution`, `test_scope`, observer and testing/handoff tests; minimal shared process changes only if required | After T1. Medium; public evidence and recovery | R2 passes on Windows 3.10/3.12 from the installed wheel, including one-dispatch recovery and immutable handoff. Existing POSIX tests/records stay compatible |
| T4: File-memory reader and serving | `memory_reader`, read-only native helper if needed, `memory_serving` error boundaries, reader/compatibility/annotation tests; coordinate any primitive extension | After T1 and any shared primitive PR. High; source authority/freshness | R3 passes, including full file bounds, retained-handle discovery, sidecar absence/race handling, raw/personal/curated resolve/refresh and pointer verdicts. Installed witness records successful Windows tiers rather than the old POSIX-only refusal |
| T5: Saved memory/tasks | `memory_saved`, native helper, saved CLI/index/linked-task tests; keep platform-independent mutation owner | T2 must pass or Patrick must decide on a revised explicit contract. High; persistence/privacy | R4 and the full saved lifecycle pass with native concurrency/crash evidence, unchanged schema/replay behavior, and no silent durability or ACL fallback |
| T6: Core CLI and effects journeys | Native shell quoting and command rendering; existing fix/build native profiles and recovery; starter/cold-start/documented journeys; required regression fixtures | T3 for testing/handoff; T4/T5 for their journey sections. Medium/high | R6 passes in actual declared Windows shells, with successful repair/build/test and recovery. Existing qualified safe effects remain safe; a recorded feature refusal is not journey completion |
| T7: Native memory transport | `memory_native`, dedicated SDK/offline child tests; qualification install selection; exact host environment | After T1; can proceed independently of reader storage using explicit fixtures. High; disclosure/process boundary | R5 passes with actual supervised helper + pinned SDK, external network blocked, zero paid calls, exact finite environment and valid offline receipts. Missing optional dependencies still refuse truthfully |
| T8: Combined qualification and claims | Rebuild wheel after all implementation lands; full suite; installed journeys; final docs, inventory and completion review | T3–T7. Medium integration risk | R1–R8 all met at the final source heads; Windows CI settled green; no parity case hidden by OS-wide skip; final code reviews recorded. Report desktop evidence separately. Release remains Patrick's decision |

Plan for roughly eight PRs, with a shared primitive change split out if it needs
independent review. Do not force unrelated source owners into one PR to preserve
the initial cap. No wall-clock or provider budget is allocated by this estimate.

## Validation and rollback

Run owner tests first, then the full suite and installed-wheel qualifier as
required by AGENTS.md. Run source-hash-sensitive tests in a stable checkout;
do not edit loaded modules during a suite. Inspect Windows job output and
receipts, not just the aggregate badge. A failed check is unresolved until its
cause is established; a baseline comparison must use the same inputs/runtime.

Before each merge request, record the exact head, review, Windows receipts and
unverified claims. Preserve any created Windows profile marker and old reader
tokens. Reverting a backend must leave historical records readable or explicitly
unavailable without mutating them. Never revert by rewriting accepted state,
deleting evidence, or replaying uncertain provider/effect operations.

If T2 cannot justify durability, stop T5 and return the evidence to Patrick.
Other independent approved tasks can continue, but the overall parity claim
stays open. If directory bounds or filename eligibility differ, resolve the
compatibility decision before R3 closes. Two failed attempts at one approach
trigger a strategy review before a third.

## Planning review

Broader goal: native Windows completes the same supported feature journeys
with their safety and evidence intact. Highest-value finding: the present green
matrix and saved-storage platform claim do not establish that outcome; storage
durability is an unresolved feasibility gate, not a small OS guard removal.

Three isolated read-only audits checked reader, saved-storage and native-memory
owners against the pinned source. Their findings are incorporated into R3–R5
and the README's command walk. No source implementation or provider calls were
made in those audits. Root's unfinished shell/fixture code is stashed separately.

The interrupted macOS source run is not a passing baseline: 3,791 passed, 38
skipped and 12 source-hash-drift failures before interruption. Source edits were
made while that process was running. After stashing the edits, all 35 reranker
comparison tests passed. The existing plan and fix starter fixture journeys
also passed (two tests) on POSIX. Retain that distinction; do not classify those failures
as pre-existing Windows defects. Planning evidence remains in the local session
handoff and `/private/tmp/windows-compat-local-full-unrestricted.txt`.

Completion review for this planning milestone: complete with no separate
opportunity-log entry. The discovered reader limits, missing native SDK witness,
storage durability and misleading platform claim are already requirements of
this spec, rather than deferred opportunities. A user encounters the saved-store
platform claim first. Implementation completion review remains pending.
