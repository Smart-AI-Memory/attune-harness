# Windows parity tasks

## Prospective Python minimum — October 25, 2026

Patrick approved Python 3.12 as the development minimum in a separate
compatibility PR, which is not yet merged or published. Once that policy lands,
future qualification uses Python 3.12; the original 3.10/3.12 planning rows and
receipts below retain their historical interpreter identities. This changes only
the future interpreter profile. All Windows Server 2022/2025, Windows 11 desktop,
standard-user, filesystem, shell, process, storage and complete-journey acceptance
requirements remain. No parity requirement is closed by reducing Python cells.
Release/version selection and any future Python 3.14 qualification remain open.

## Current checkpoint — October 21, 2026

Checked against main `462d37be4fa06140c62e5f39f3489a4f8785c112` and the
[published 1.5.0 scope](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.5.0).
The package includes merged Windows components; full Windows parity remains
deferred. The [requirements](design.md), original task acceptance conditions and
authority boundaries remain unchanged. A merged checkpoint is not a completed
T1–T8 acceptance claim.

| Task | Delivered checkpoint | Remaining acceptance |
| --- | --- | --- |
| T1 | [#281](https://github.com/Smart-AI-Memory/attune-harness/pull/281) retains complete source-suite results; [#283](https://github.com/Smart-AI-Memory/attune-harness/pull/283) adds the Server 2022/2025 matrix. | Keep original failures, refusals and skips visible. Final R1 coverage belongs to the final combined artifact. |
| T2 | [#268](https://github.com/Smart-AI-Memory/attune-harness/pull/268) supplies the accepted finite standard-user storage feasibility checkpoint, with assumptions retained in the [readiness record](../../release-readiness-1.5.0.md#component-evidence). | Primitive feasibility does not certify the later production store, desktop profile or power-loss behavior. |
| T3 | [#271](https://github.com/Smart-AI-Memory/attune-harness/pull/271) merges native captured-change test execution and component witnesses. | Combined installed, shell and recovery requirements still apply. |
| T4 | [#270](https://github.com/Smart-AI-Memory/attune-harness/pull/270) and [#272](https://github.com/Smart-AI-Memory/attune-harness/pull/272) merge retained-handle readers and serving, preserving the declared capacity/path/identity profile. | Retain component bounds; final desktop and combined-journey acceptance remain separate. |
| T5 | [#275](https://github.com/Smart-AI-Memory/attune-harness/pull/275) merges the saved-store implementation checkpoint; [#278](https://github.com/Smart-AI-Memory/attune-harness/pull/278) retains contention observations. | Full saved-store acceptance and the historical eight-writer busy-failure cause remain open. Passing observed schedules do not explain the earlier failure. |
| T6 | Existing effects, starter and hosted command journeys supply bounded software evidence. | Actual Windows PowerShell/PowerShell 7 and Windows 11 standard-user documented journeys remain open, together with strict stop/recovery. |
| T7 | [#269](https://github.com/Smart-AI-Memory/attune-harness/pull/269) merges Windows transport with offline supervised-helper and pinned-SDK evidence. | Live native-memory acceptance remains open; offline evidence is not a provider-quality result or permission to redispatch an uncertain operation. |
| T8 | [Baseline run 39205220937](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39205220937) passes the four Windows Server source-suite and four installed-wheel cells at `77d5b2b4fe9f3c6285a5b535f4e735103f7e192d`. The release record identifies later final distribution evidence separately. | Full combined parity still requires the unchanged R1–R8 conditions, including desktop, declared shells, storage, process recovery and live acceptance. |

The existing process-completion work remains in draft
[#274](https://github.com/Smart-AI-Memory/attune-harness/pull/274) and
[#279](https://github.com/Smart-AI-Memory/attune-harness/pull/279). Their retained
failed runs and later diagnostics are distinct observations; this status update
does not establish a production fix. Continue through the existing work owners.

Completion review is complete for this documentation checkpoint. Full-spec
implementation review and acceptance remain pending. No task criterion, paid-call
budget, merge gate or release authority changes here.

## Historical implementation plan and planning review

The original planning snapshot follows unchanged. References to active work or
the absence of implementation describe that snapshot; the checkpoint above
records subsequent delivery. Its task scopes, gates and done conditions still
govern acceptance.

**Status: approved for staged implementation.** [Scope](README.md) and
[requirements](design.md) govern each task. Estimates are scope estimates, not
measured durations. T1 is active; T2 feasibility work is active in an isolated
checkout. No task below is marked implemented. Completion review: pending.

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
| T7: Native memory transport | `memory_native`, dedicated SDK/offline child tests; qualification install selection; exact host environment; controlled live Windows validation | After T1; can proceed independently of reader storage using explicit fixtures. High; disclosure/process boundary | Offline R5 passes with actual supervised helper + pinned SDK, external network blocked, zero paid calls, exact finite environment and valid receipts. Missing optional dependencies still refuse truthfully. Approved D4 authorizes necessary live validation within the shared $50 process cap: reserve maximum cost, execute the production path and retain usage/results. No fresh per-run spending approval within that scope; unresolved costs/effects stop paid dispatch |
| T8: Combined qualification and claims | Rebuild wheel after all implementation lands; full suite; installed journeys; final docs, inventory and completion review | T3–T7. Medium integration risk | R1–R8 all met at the final source heads; Windows Server 2022/2025 CI settled green; Windows 11 desktop installed-wheel journeys pass with Python 3.10/3.12 under standard user permissions; no parity case hidden by OS-wide skip; final code reviews recorded. Retain separate desktop/server receipts. Release remains Patrick's decision |

Plan for roughly eight PRs, with a shared primitive change split out if it needs
independent review. Do not force unrelated source owners into one PR to preserve
the initial cap. No wall-clock budget is allocated by this estimate. Patrick's
separate D4 authorization caps necessary paid validation at $50 total across
the entire Windows compatibility process; this estimate grants no extra budget.

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

Approved D3 requires the T2 durability proof under standard user permissions
before production saved-storage implementation. If T2 cannot justify equivalent
durability, stop T5 and return the evidence and alternatives to Patrick; do not
substitute an app-crash-only profile.
Other independent approved tasks can continue, but the overall parity claim
stays open. Approved D2 requires matching memory limits; adapt native enumeration
instead of substituting a smaller Windows capacity profile. If another directory
bound or filename eligibility differs, resolve the compatibility decision before
R3 closes. Two failed attempts at one approach
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
