# Stabilization, release readiness and phased GUI delivery

## Current checkpoint — November 8, 2026

Harness 1.7.0 was published on November 6 and requires Python 3.12 or later.
The release was built from `5159e7a79fbdb84d2982937716043b142534e6e9`.
The Claude Code marketplace points to `v1.7.0`. This checkpoint reflects
`main` at `cba3fd05343d826204addd47b076f82d3dd1d9bd`, including the 1.7.0
Help and course updates, the published-course wording correction, and the
offline recovery study controls.
[GitHub release](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.7.0) ·
[PyPI](https://pypi.org/project/attune-harness/1.7.0/) ·
[Marketplace update](https://github.com/Smart-AI-Memory/attune-harness/pull/341)

The Help Center and six-lesson course are live. Website #2593 merged as
`e8b5b2161f36f110cdc51cf0c7e4d5a5fc239313`, importing both exports from
Harness #347's signed merge `cba3fd05343d826204addd47b076f82d3dd1d9bd`.
The public Help, course setup and reading routes work. Both served receipts
identify that source, and all 75 public payload hashes match, including the
course example ZIP. The original rehearsal evidence and archive remain intact.
Website #2594 then merged as `5e85046d4f912db165826dc15e8bcef5c43c1ed0`,
making **Get started with Harness** the primary homepage link to the published
1.7.0 installation guide.
[Course wording correction #347](https://github.com/Smart-AI-Memory/attune-harness/pull/347) ·
[Website rollout #2593](https://github.com/Smart-AI-Memory/attune-ai/pull/2593) ·
[Homepage entry #2594](https://github.com/Smart-AI-Memory/attune-ai/pull/2594) ·
[Live Help](https://smartaimemory.com/harness/help/) ·
[Live course](https://smartaimemory.com/harness/learn/)

Production delivery and repository qualification have separate evidence.
The website's #2594 merge has a failed Windows Python 3.10 test and failed
aggregate check; its cause remains unestablished. The earlier minimatch
development-dependency update also remains unresolved. Keep those failures
open without treating them as a failed Help deployment or claiming that all
post-merge checks passed.
[Website test run](https://github.com/Smart-AI-Memory/attune-ai/actions/runs/42504250560) ·
[Dependency update job](https://github.com/Smart-AI-Memory/attune-ai/actions/runs/42501809468/job/128795980491)

Full Windows parity remains deferred. The process stop and recovery drafts
closed without merging, and deployment of that work remains held. Any future
implementation needs a supported design that verifies every owned descendant
has stopped within the existing deadline, with the original assertions and
fast-child behavior preserved.
[Windows closure #274](https://github.com/Smart-AI-Memory/attune-harness/pull/274#issuecomment-6316884599) ·
[Windows closure #279](https://github.com/Smart-AI-Memory/attune-harness/pull/279#issuecomment-6316363242)

## Delivery phases

| Workstream | Delivered | Remaining work or evidence |
| --- | --- | --- |
| Release and onboarding | The 1.7.0 package is published, and the Claude Code marketplace catalog pins its tag. The six-lesson course, Help, installation, CLI, migration and workflow guides use published 1.7.0 on `main`. The website serves the reviewed Help and course exports, with the primary homepage link to 1.7.0 Help. [Training source #340](https://github.com/Smart-AI-Memory/attune-harness/pull/340) · [Onboarding update #344](https://github.com/Smart-AI-Memory/attune-harness/pull/344) | Prioritize the independent first-time learner walkthrough. Keep the two-starting-paths change in draft through that observation. [Starting-paths draft #348](https://github.com/Smart-AI-Memory/attune-harness/pull/348) |
| Windows parity | Published-wheel checks passed on Windows Server 2022 and 2025. Captured testing, file readers, a saved-store implementation and offline native-memory transport are merged. [October task checkpoint](specs/windows-parity/tasks.md#current-checkpoint--october-21-2026) | Full parity is deferred. Strict stop and recovery, full saved-store acceptance, live native memory, Windows 11 standard-user journeys, and the declared PowerShell journeys remain open. [Windows requirements](specs/windows-parity/design.md) |
| User observations | Installed software checks and bounded maintainer walkthroughs are recorded. [Observation record](release-readiness-1.4.0.md#open-observations-and-publication-boundary) | Record fresh-session memory recall, provenance and exclusion (S3), a named non-programmer's installed walkthrough (S6), and migration rows exercised against the installed artifact (S9). Record a decision for any observation that remains open. |
| Graphical companion | M1 is complete. Released browser forms support saving, previewing and approving an existing draft. [GUI progress](specs/graphical-companion/progress.md) | Complete M2, including production browser execution and recovery, new-task creation, and standalone assessment. M3 journey coverage and M4 release qualification follow their existing gates. [GUI milestones](specs/graphical-companion/README.md#milestones-and-acceptance) |
| Memory | All five shared-memory adoption tasks were accepted at revision 23. Version 1.7.0 includes hydration source capture, secret checks and payload accounting. [Shared-memory acceptance](specs/shared-memory-adoption/verification.md#final-acceptance-and-display-caveat) · [Hydration source PR](https://github.com/Smart-AI-Memory/attune-harness/pull/318) | Deliver the hydration command, Redis generation publication and cleanup, packaged startup hook, and host-specific fresh-session evidence. [Hydration tasks](specs/native-memory/hydration-writer/tasks.md#sequential-tasks) |
| OpenAI funding | Separate API and plan OAuth paths shipped with offline software evidence. The plan OAuth profile is limited to macOS arm64 with CPython 3.12.2. [1.7.0 release](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.7.0) | Live account and model eligibility, quota and billing need separate qualification. Claude subscription feasibility remains a separate task. [Subscription tasks](specs/codex-subscription/tasks.md#s6--separately-authorize-minimal-live-route-qualification) |
| Failure and recovery comparison | T1 is complete. The POSIX evidence qualified all 11 offline controls with zero model calls. Full Windows evidence collection remains unqualified. [T1 PR](https://github.com/Smart-AI-Memory/attune-harness/pull/343) | T2 adapter and interruption qualification, T3 live pilot, and T4 scoring and review remain unselected. Live inference needs separate authorization. [Study tasks](specs/failure-recovery-comparison/tasks.md) |
| Opportunity maintenance | Review handoffs (D/O-28) and function-body controls (E/O-34/O-35) exist in source. [Opportunity register](opportunity-log.md#current-register) | Keep the register aligned with release and acceptance evidence. The experiment input safeguards in C remain a prerequisite for another paid trial. |

Use the existing scope, merge, spending, deployment and publication gates for
each workstream. See the [release runbook](release-runbook.md) for release work.

## Where each gate's evidence is

The [1.7.0 release record](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.7.0)
identifies the source, publish run, distribution hashes, Windows Server
exact-wheel results, and fresh macOS arm64 installations. The separate Windows
11 observation used x64 CPython on ARM64 hardware. Native Windows ARM64 and full
desktop and shell parity remain unqualified. The
[qualification guide](qualification.md) defines the software checks, and the
[observation record](release-readiness-1.4.0.md#open-observations-and-publication-boundary)
tracks S3, S6 and S9 separately.

The [1.5.0 release record](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.5.0)
retains its own publication and installation evidence. The separate
[hosted baseline run](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39205220937)
at `77d5b2b4fe9f3c6285a5b535f4e735103f7e192d` passed 16 jobs, including four
Windows Server source-suite and four installed-wheel cells across Server
2022 and 2025 and Python 3.10 and 3.12. The
[historical 1.2.0 gate index](#historical-gate-evidence-for-120) retains the
original S1–S9 evidence. Each record applies to its stated artifact, source and
profile.

## Previous checkpoints

These snapshots retain the status and evidence recorded on their dates.

### October 22, 2026

Version 1.5.0 remains published. Version 1.5.1 is an unpublished maintenance
preparation against `0f2711b4c88ee4f231f61d71cd70a0c840be6357`. Current-main
[qualification](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39872982676)
passes, including the Windows source-suite partitions added in #298. The
[1.5.1 readiness record](release-readiness-1.5.1.md) distinguishes that result
and fresh documentation observations from final-source selection, metadata,
artifact validation, Help integration and publication approval.

Use the [current walkthroughs](tutorials-1.5.1.md) for preparation, and the
published version for an installation today. The deferred Windows requirements
and S3/S6/S9 observations below retain their existing scope.

### October 21, 2026

Reconciled against main `462d37be4fa06140c62e5f39f3489a4f8785c112`.
[Version 1.5.0 was published October 19](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.5.0),
from `7caa86ab6d476e9599b08ff75a81bc816e60c382`. The subsequent main commit
points the Claude Code marketplace at that release. The earlier 1.3.0 hold,
October 6–12 schedule and 1.2.0 evidence index below are retained historical
planning records; they no longer describe the current release state.

Use the [current journey map](supported-journeys.md) for delivered entry points
and limits, and the [opportunity register](opportunity-log.md#current-register)
for scoped next steps. The approved Windows parity specification remains the
implementation priority. This update neither starts a new feature chain nor
changes its requirements or authorization.

## Historical stabilization plan — October 2026

The following plan retains its original wording, decisions and measurements.
Its present-tense status and relative dates describe the earlier planning
checkpoint. The current sections above supersede its scheduling and release
status claims without rewriting that evidence.

**Approved release boundary (October 6):** 1.3.0 includes browser draft intake,
preview and explicit intent approval, alongside CLI/agent forms. The local server
exposes only registered-task form navigation and the existing decision owners.
Browser build grants, dispatch, resume and broader GUI controls are deferred to
1.4.0; launch flags cannot enable them. Historical development receipts below do
not qualify this revised candidate. M2/M3/M4 gates remain; full M2 is not required
for this bounded forms release. S3/S6/S9 observations remain open for explicit
disposition. October 6–11 publication needs an explicit decision; October 12
remains the scope review, with no automatic M3.

Phased delivery update October 3, 2026 against main
`23d6e7e1c6ef35f698fbc1f0462e951c41b099a8`. The release evidence below retains
its 1.2.0 baseline; it is not a new publication check. This
updates the execution focus of [the v1 roadmap](plan-1.0.md), retaining
[S1–S9 and D25–D30](specs/release-1.0/addendum-2026-09-23.md). The earlier
phased and October plans remain historical inputs, not an extra release
backlog. Planning scope: stabilization through October 12 and the dependency-gated
GUI phases afterward. The existing four GUI milestones remain the acceptance
structure; the delivery phases below sequence them around release work.
This document selects work; it does not authorize merges, paid calls, workflow
dispatch, publication, repository settings changes or a deprecation notice.

## Executive status

**Stable v1 is published, and the stabilization period is under way.** R0 is
September 28, 2026, the date 1.0.0 reached PyPI. Four stable releases followed
in two days:

| Release | Date | What it carried |
|---|---|---|
| 1.0.0 | September 28 | rc2's runtime and pins, no frozen-surface change; S3/S6/S9 observations moved into stabilization |
| 1.0.1 | September 28 | PyPI README links |
| 1.1.0 | September 29 | The [first-run journey](specs/first-run-journey/README.md) (T1–T7), including the published Claude Code plugin |
| 1.2.0 | September 30 (UTC) | A structured Claude CLI refusal may authorize one turn retry |

The per-release hashes, publish runs and the remaining gaps for S1–S9 are in
[the evidence index](#where-each-gates-evidence-is) below. The software gates
are met for the released artifact. **S3, S6 and S9 remain open as
observations**: real fresh-session memory recall, a named non-programmer's
installed walkthrough, and each migration row tried against the installed
artifact. Green software checks do not close them, and no percentage-complete
estimate is useful while they are open.

Main still declares 1.2.0, but includes changes not yet published in that
artifact. Since [#202](https://github.com/Smart-AI-Memory/attune-harness/pull/202),
the Claude Code marketplace catalog on `main` pins the plugin to the release
tag. The [runbook](release-runbook.md) now calls for reopening development
with a `.dev0` version after 1.3.0. Source availability, publication and
observed user acceptance are separate states.

## Historical delivery phases

PR #199 remains held for the October 6–11 release window; October 12 is a review point,
not an automatic release or end to compatibility obligations. Patrick subsequently
authorized the four-milestone [GUI program](specs/graphical-companion/README.md).
That permits bounded M2 work alongside stabilization, superseding the earlier
blanket GUI deferral. Critical defects and release acceptance work take priority.
Keep GUI increments in separate PRs; do not start M3 during the stabilization window.
Dates below are 2026, in Patrick's US Eastern calendar. Later phases have evidence
gates rather than promised dates. Unfinished observations remain explicit gaps;
the calendar does not close them.

| Phase | Window / entry | Work and responsibility | Exit evidence |
|---|---|---|---|
| 1 — Stabilize and learn | Now–October 5; active | Agent triages defects, prepares observation steps and completes bounded documentation/timing analysis. Patrick or participants supply real-use observations. Agent may advance a bounded M2 owner integration separately. | Current S3/S6/S9 observation status, reproduced friction and dispositions; each GUI increment has its own tests/review, without a production-readiness claim. |
| 2 — Prepare the batched release | Preparation starts now; release window October 6–11, with explicit publication approval | #199's owner integrates current main, reconciles the release inventory and GUI maturity claims, then qualifies the exact candidate. Continue observation collection; GUI work must not displace release qualification. | Current release notes, full/installed/platform evidence, recorded limits and Patrick's publication decision under the runbook. If blocked, retain the hold. |
| 3 — Review stabilization and choose scope | October 12 review | Patrick and agent review defects, observations, release outcome and M2 evidence. Choose continued bounded M2, broader work after M2 passes, or extended stabilization. | Written go/hold and next bounded scope. Open gaps have explicit disposition; no automatic M3 start or publication. |
| 4 — Complete connected GUI journeys | Existing M2 authority; main delivery focus after Phase 3 permits it | Agent binds intake, decisions, build/review, progress and recovery to existing owners, retaining author inspection and prototype behavior. Bounded increments may begin in Phases 1–2. | M2's real offline owner chain, stale/replay refusals, restart and uncertain-outcome recovery pass through the browser. Required source review and evidence accompany each PR. |
| 5 — Broaden journey coverage | Phase 3 permits broadening and M2 exit passes | M3 adds fix/test, research, opportunities, memory, import and host entry in owner-specific slices. Resolve provider/budget choices before any new live dispatch. | Every required journey row has executable evidence; unsupported required capabilities remain open gates. Preserve research, opportunity selection, retention controls and author inspection. |
| 6 — Qualify and release the GUI | Required M3 coverage implemented | M4 covers clean install/upgrade, accessibility, security, recovery, claimed hosts/platforms and named user walkthroughs. Agent prepares evidence; participants provide observations; Patrick decides release. | M4 criteria met and a reviewed release handoff. Production claims and publication wait for their existing gates. |

### Parallel work and dependencies

Start three workstreams now, with at most two active implementation efforts:

| Workstream | Owner and first bounded action | Boundary |
|---|---|---|
| Stabilization and release readiness (Phases 1–2) | One assigned owner audits #199's release inventory against current main and prepares remaining observation steps; critical defects come first. | Preparation can begin before October 6. Final qualification uses the exact candidate; early checks do not qualify later changes. Publication stays held. |
| GUI M2 (Phase 4) | A separate owner checks #219's final evidence, then takes the intake/decision slice through real-owner and refusal tests. | Own worktree and PR; no shared-file edits with the release owner. M3 implementation waits for the Phase 3 decision and M2 acceptance. |
| User feedback (Phase 1) | Patrick coordinates voluntary participation; the agent prepares a short walkthrough and records reported or observed outcomes accurately. | Runs alongside development, without claiming the agent can supply human observations or authorizing unsolicited outreach. |

Assign owners before dispatch; a workstream is not evidence that an agent is
already running. Keep one owner for shared planning files and serialize merges
through main. Separate branches isolate edits, not release contents: any merged
GUI change must be reconciled into the release inventory before final qualification.
When stabilization demand exceeds capacity, pause GUI work at a clean boundary
rather than adding another competing implementation effort.

Phases 1 and 2 overlap with bounded Phase 4 work. Phase 3 reviews their results.
Phase 5 implementation requires both the Phase 3 scope decision and M2 acceptance;
Phase 6 final qualification requires the implemented M3 coverage. Accessibility,
security and recovery checks begin with the first relevant M2 increment and
continue through M3. M4 consolidates and repeats them against the release candidate;
it is not the first time those qualities are checked.

### Current GUI baseline

- **M1 complete:** 16 journey rows, reuse inventory, owner refusal walk and
  preservation rules in the graphical-companion spec.
- **M2 started:** #219 merged the read-only task companion. #225–#227 connected
  browser draft intake, partial-answer recovery, preview and explicit intent
  approval through existing owners. This bounded slice is included in the
  1.3.0 candidate and requires exact-candidate qualification and Patrick's
  personal acceptance. Execution and recovery controls remain deferred to 1.4.0.
- **M3/M4 not started:** merged source and prototypes do not establish production
  qualification. #220 adds shared collaboration guidance, not a GUI capability.

The first M2 intake and intent-decision slice is implemented; source integration
does not establish full M2 acceptance. Retain its owner checks, stale/refusal
states and answer recovery when planning the deferred execution controls. Use
the spec's acceptance criteria rather than inventing another milestone system.

### Early user feedback and the next observation

Patrick reports that a real user downloaded the product, read available
documentation, reacted positively and gave the repository a star. This is
preliminary, second-hand adoption feedback, not an independently observed installed
walkthrough. The version, installation outcome, completed task and whether the
participant meets S6's non-programmer criterion are not yet established. No
identity or private conversation is published here.

For the next voluntary walkthrough, record the installed version/platform, chosen
task, expected result, actual outcome, help needed and friction. Keep identifying
material private with appropriate consent. A positive reaction or star must not
stand in for task completion; equally, do not describe early user feedback as absent.
S3 still needs fresh-session recall/exclusion evidence, and S9 needs each migration
row tried against the installed artifact. These can be collected independently.

### Working through the phases

Use verified lessons to inform the next bounded task, acceptance criteria to choose
checks, and the results to improve the next handoff. Apply the shared disciplines
without duplicate forms or approval steps. At a meaningful completion point, update
the existing plan/progress evidence and complete the proportional opportunity review.
Autonomous work covers in-scope inspection, implementation, tests and draft PRs;
merges, releases, additional spend and settings retain their existing gates.

## Historical gate evidence for 1.2.0

Added September 29, 2026 for the released **1.2.0** (O-09/O-16). This index
links to existing receipts; it adds no new receipt format. Each item is
labeled with the kind of claim it supports:

- **measured:** a check the host ran, which passes or fails;
- **replay:** recorded responses run again offline;
- **live:** a real provider call, recorded once;
- **model:** a model's judgment, which is never a verified result;
- **observed:** a person's recorded use;
- **reported:** second-hand feedback, with unconfirmed details stated explicitly.

Software checks never stand in for an observation. A gate with no observed
receipt says so.

| Gate | Evidence | Kind | Gap still open |
| --- | --- | --- | --- |
| S1 compatibility | [Compatibility list](compatibility.md), [envelopes](envelopes.md), the CLI [surface fixture](../tests/fixtures/compatibility/surface.json) and protocol fixtures beside it, the 33-file [saved-state capture](../tests/fixtures/compat-1.0/README.md) with its reader tests, [deprecations](deprecations.json) | measured | None for the frozen surface; each release must keep the fixtures green |
| S2 native independence | The [R2 journey](journeys/r2-clean-environment.md) from the installed wheel with Attune AI absent, in every platform job; the [R4 import receipts](journeys/r4-legacy-spec-state.md) | measured | Attune AI's hydrate writer is still Attune AI's; Harness only reads what it writes |
| S3 useful memory | `tests/test_memory_serving.py` (inactive nodes and `wrong` verdicts not served, prompt mode), `tests/test_memory_prompt_hook.py`; the path against a hydrated server passed once on a maintainer's machine on September 22, as the [README](../README.md#what-is-qualified-and-what-is-not) states, with no retained receipt | measured | **Observed:** fresh-session recall and exclusion in real use. Saved entries do not feed automatic recall ([journey map](supported-journeys.md#memory)) |
| S4 signed plugins and Voyage | `tests/test_plugin_signing.py` and `tests/test_plugin_runtime.py` in the six installed-wheel jobs; the [Voyage recorded fixture](../tests/fixtures/voyage-live-recorded/README.md); [running a signed plugin](executable-plugin-run.md) | measured; live on macOS only; replay on all six jobs | No general ranking-quality claim; no live call on Ubuntu or Windows |
| S5 platform limits | The README's [qualification table](../README.md#what-is-qualified-and-what-is-not), the [qualification guide](qualification.md), the platform receipts from the [`Qualification` run](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/36627949560) at the 1.2.0 commit (one `qualification-<os>-<python>` artifact per job) | measured | Windows native memory, `fix` and `test` remain written limits |
| S6 usability | Preliminary user feedback, described above; no installed-walkthrough receipt | reported | **Observed:** a named non-programmer's installed walkthrough. Still unconfirmed |
| S7 release mechanics | [Release runbook](release-runbook.md). Each publish run's `release-evidence` artifact holds `SHA256SUMS`, and PyPI's hashes were compared against it: 1.0.0 [run 36451826139](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/36451826139), 1.0.1 [run 36466359597](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/36466359597), 1.1.0 [run 36522747598](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/36522747598), 1.2.0 [run 36629591220](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/36629591220). For 1.2.0 the wheel is `17c3f0953d136314b199af3b72d7ce6773c9766066ac8c086742aa0d863351f7` and the sdist `2f36d6cd492738a8c737c493e222c9a66d252a9fe89d38f1bdb0a554bea638bc` | measured | None; each release repeats the runbook's steps |
| S8 loose ends | [Qualification guide](qualification.md) (the historical `check_code_rag_host.py` is labeled as such); [documentation maintenance](documentation-maintenance.md) | measured | Any replacement host check needs its own scope |
| S9 migration | [Current migration guide](migration.md), [journey map](supported-journeys.md) | — | **Observed:** each row tried against the installed stable artifact. Not yet done |

Model judgments appear in none of these rows as evidence. Review narratives,
native model reviews and assessments are unverified proposals, and the CLI
labels them as such ([status guidance](status-guidance-a-results.md)).

## The road to stable v1, completed

The ordered work that led to R0 is done. Its receipts stay where they were
recorded:

1. **Voyage evidence (S4).** The bounded live signed-plugin and direct-provider
   campaign retained four matching stage pairs (29,698 provider-reported
   tokens; $0.00249178 at pinned rates, not invoice-verified). PR161 replays
   them offline on all six platforms. Live evidence is macOS only, and replay
   does not establish general retrieval quality.
2. **Candidate compatibility and claims (S1/S5/S8).**
   [PR162](https://github.com/Smart-AI-Memory/attune-harness/pull/162) merged
   the installed-writer fixture, reader/refusal matrix, CLI choices/defaults
   and bounded claim audit.
3. **Candidates.** 1.0.0rc1 and rc2 were published to production PyPI on
   September 28, and rc2's fresh `[all]` install passed.
4. **Stable 1.0.0.** On September 28, after reviewing the README, Patrick
   authorized proceeding with stable publication and shepherding
   [#169](https://github.com/Smart-AI-Memory/attune-harness/pull/169), under
   the [runbook](release-runbook.md). This was an accelerated release
   decision: the fourteen-day candidate observation had not run (#169's
   body; [release notes](release-notes-1.0.0.md)). Stable v1 does not
   deprecate Attune AI or claim GUI/workflow parity.

## Completed since the September 30 refresh

The [starter-files task list](specs/starter-files/tasks.md) records T1–T5
complete: documented journeys (#191), `init --for fix` (#193),
`init --for plan` (#194), the example command worker (#198), and resolved-path
guidance (#190). The `plan-starter` journey completes plan/build; the
`fix-starter` journey completes on POSIX. This does not qualify Windows `fix`
or close the S3/S6/S9 observations. O-76's separate `--test-root .` refusal
remains outside the smaller path remedy.

Follow-up corrections for participant guidance (#201), partial starter writes
(#204), and forced probe-backup accounting (#209) are on main. The Codex
plugin preparation fix (#210), consultation citation inspection and direct
Google seats (#211), qualification timing diagnostics (#212), and explicit
mistake escalation policy (#213) also merged. These are source changes, not
claims about the published 1.2.0 artifact.

**T6 is prepared, with integration and release still pending.**
[PR #199](https://github.com/Smart-AI-Memory/attune-harness/pull/199) contains
the spec closeout and 1.3.0 preparation. It remains a draft under the deliberate
publication hold. At this refresh, it conflicts with current main and retains
an older failed macOS supplemental check; its owner must integrate current
main, reconcile the release inventory, and obtain fresh exact-head checks
before release. Those readiness tasks do not lift the hold.

## Next, ranked (October 3, R0+5)

The [Windows-traps guidance](windows-traps.md) is complete in
[#215](https://github.com/Smart-AI-Memory/attune-harness/pull/215). It covers
signed-bundle bytes, GPG discovery, portable capture paths and separate
qualification/measurement budgets. The temporary Windows measurement
headroom in [#216](https://github.com/Smart-AI-Memory/attune-harness/pull/216)
does not close the O-11 investigation or broaden platform qualification.

New critical defects preempt this list. Smallest first where the value is
equal; each item is a separate pull request.

| Rank | Work | Why here | Status |
|---|---|---|---|
| 1 | **S3/S6/S9 observations** | The open acceptance gaps; software checks cannot close them | Needs Patrick or named participants, including a non-programmer for S6 |
| 2 | **O-11 timing baseline** (quick opportunity 4) | Diagnose recurring suite-budget pressure using retained evidence | #212 adds timing diagnostics; #216 adds temporary measurement headroom; the investigation remains open |
| 3 | **T6 / 1.3.0 release readiness** | Deliver already implemented starter journeys in one batch | Prepared in draft #199; integrate and qualify before release, preserving the hold |

Four stable releases in two days is fast for a stabilization period. Batch
compatible fixes into one release per window unless a critical defect needs
its own.

**O-70 is ruled a journey defect (2026-09-30 retro).** The rule above against
starting a feature chain in the window allows defects. Starter files address
the missing setup path for `plan` and `fix`; T1–T5 are now implemented, while
T6 and publication remain pending. Its release, 1.3.0, remains held for one
batched release in R0+8–R0+13
(October 6–11), not one per task. The S3, S6 and S9 observations still come
before any claim of acceptance. Building O-70 does not close them.

## R0 through R0+14: post-release stabilization

Under the accelerated release decision, these observations include the work
originally planned for the candidate period. R0 is September 28, 2026.

| Window | Focus | Exit evidence |
|---|---|---|
| R0–R0+2 (Sep 28–30) | Verify the published install and documented journeys; triage installation, recovery, saved-state and unexpected-spend reports first | Artifact identities, reproduced issues and clear dispositions; any urgent patch is independently reviewed and separately released |
| R0+3–R0+7 (Oct 1–5) | Check real usage and support friction; collect S3/S6/S9 observations and prepare bounded documentation while incident load permits | Observed receipts or explicit gaps, with source changes distinguished from stable artifacts |
| R0+8–R0+13 (Oct 6–11) | Complete bounded guidance/timing work if still useful; qualify the batched 1.3.0 candidate under the existing release hold and gates | Small documentation/report deliverables and exact-candidate release evidence; publication still requires Patrick's authority |
| R0+14 (Oct 12) | Review stability, unresolved defects and user feedback; choose the next bounded milestone | Written go/hold for continued M2, broadening after M2 acceptance, or further stabilization; no automatic M3 start |

New critical defects preempt the opportunity queue. Preserve saved state and use
existing rollback guidance; do not automatically delete data, alter security
settings or publish emergency versions. A patch changing a frozen contract must
follow the existing deprecation policy. No extra universal fourteen-day hold is
invented for an ordinary compatible patch.

## Four quick opportunities, maximum five

These are bounded slices of the existing [opportunity log](opportunity-log.md),
not four additional release gates. Time estimates include writing and review but
exclude passive CI wait; they are planning timeboxes, not measured forecasts.
Maximum two active hours per item, six hours total. Stop and defer any item that
needs a schema/API change, new provider, paid experiment or broader implementation.
Do not fill the fifth slot just to reach five. Reassess at the start of each item;
skip anything already completed by release-gate work.

| Priority / existing opportunity | Small deliverable and acceptance | Timebox | When |
|---|---|---|---|
| 1 — O-04, supported journey map | Refresh the existing map for install, plan/build/review, memory, Voyage and recovery. Each row names entry point, platform limit, evidence and workaround. Distinguish explicit saved capture from automatic recall. Done: no stale claim that merged implementation is absent or unqualified behavior is complete. | 1–2 hours | **Done:** [#186](https://github.com/Smart-AI-Memory/attune-harness/pull/186), for 1.2.0 |
| 2 — O-09/O-16, evidence navigation | Add links in existing release documentation to artifact hashes, CI, observed receipts and known limits. Label measured checks versus model judgments and live versus replay. No receipt-schema change or duplicate evidence system. Done: a reviewer reaches each S1–S9 receipt or explicit gap from one index. | 1–2 hours | **Done:** [#187](https://github.com/Smart-AI-Memory/attune-harness/pull/187), the index above |
| 3 — existing Windows-traps follow-through | Document byte-exact signed bundles, GPG path rules, drive-qualified capture refusal, and distinct qualification/measurement budgets. Each statement is checked against shipped behavior. | 0.5–1 hour | **Done:** [#215](https://github.com/Smart-AI-Memory/attune-harness/pull/215), targeted guidance and links; no runtime edits |
| 4 — O-11, timing baseline only | Summarize existing qualification/coverage job durations and slow test cases for the final candidate/stable head; separate setup, suite and instrumentation. Done: reproducible report and at most one measured bottleneck proposed for later work. No caching or automatic timeout increase. | 1 hour | Week 2 |

The known Windows suite took 601.218 seconds on a successful PR159 run; the old
600-second limit could truncate a healthy run. Installed qualification now allows
1,500 seconds on Windows and 900 seconds on POSIX, with respective 30-minute
and 20-minute outer CI jobs for setup/evidence. Individual operation deadlines
remain unchanged. Retain timeout evidence and investigate recurring overruns;
the larger Windows budget is headroom, not a performance correction.

## Explicitly deferred

GUI M3 broadening during stabilization and GUI production-release claims before
M4 acceptance. Bounded M2 implementation is authorized as described above. Extra RAG
providers/OpenAI retrieval fallback; automatic
provider switching; broad memory/workflow parity and Spec lifecycle expansion;
new cross-provider model campaigns; general caching/performance redesign;
Attune AI deprecation and removal of attune-rag. Existing supported paths and
experimental labels stay honest. These exclusions protect release focus, not a
claim that the work has no value.

## Review outcome

Goal: stable interfaces backed by live and installed evidence, with remaining
human observations retained as named gaps during stabilization. Stable v1 is
published and the software gates are met; the highest-value remaining
distinction is between software checks and observed user acceptance. Quick
opportunities 1–3 and starter tasks T1–T5 are done on main. T6 is prepared
in held draft #199; 1.3.0 is not published. The next acceptance evidence is
the S3/S6/S9 observations, while bounded guidance and timing work can proceed
during the hold. This refresh covers this roadmap and its linked status
sources, not a complete documentation-corpus review. It narrows existing
opportunities rather than inventing a new register or reopening closed work.
Completion review: complete for this phase alignment. The highest-value finding
is that early adoption feedback and an observed installed walkthrough are different
evidence states; the next user-facing step is the voluntary walkthrough already
covered by S6. No separate opportunity entry is needed. Release acceptance remains
open, and this planning change supplies no new execution or qualification receipt.
