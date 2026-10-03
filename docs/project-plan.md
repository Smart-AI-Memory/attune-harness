# Stable v1 and the first two weeks after release

Refreshed October 3, 2026 against main
`4276c3503470a286fda33104e6d4fffb495bb54d`, with 1.2.0 still the latest release. This
updates the execution focus of [the v1 roadmap](plan-1.0.md), retaining
[S1–S9 and D25–D30](specs/release-1.0/addendum-2026-09-23.md). The earlier
phased and October plans remain historical inputs, not an extra release
backlog. Planning scope: the fourteen days of stabilization after stable v1.
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

## Where each gate's evidence is

Added September 29, 2026 for the released **1.2.0** (O-09/O-16). This index
links to existing receipts; it adds no new receipt format. Each item is
labeled with the kind of claim it supports:

- **measured:** a check the host ran, which passes or fails;
- **replay:** recorded responses run again offline;
- **live:** a real provider call, recorded once;
- **model:** a model's judgment, which is never a verified result;
- **observed:** a person's recorded use.

Software checks never stand in for an observation. A gate with no observed
receipt says so.

| Gate | Evidence | Kind | Gap still open |
| --- | --- | --- | --- |
| S1 compatibility | [Compatibility list](compatibility.md), [envelopes](envelopes.md), the CLI [surface fixture](../tests/fixtures/compatibility/surface.json) and protocol fixtures beside it, the 33-file [saved-state capture](../tests/fixtures/compat-1.0/README.md) with its reader tests, [deprecations](deprecations.json) | measured | None for the frozen surface; each release must keep the fixtures green |
| S2 native independence | The [R2 journey](journeys/r2-clean-environment.md) from the installed wheel with Attune AI absent, in every platform job; the [R4 import receipts](journeys/r4-legacy-spec-state.md) | measured | Attune AI's hydrate writer is still Attune AI's; Harness only reads what it writes |
| S3 useful memory | `tests/test_memory_serving.py` (inactive nodes and `wrong` verdicts not served, prompt mode), `tests/test_memory_prompt_hook.py`; the path against a hydrated server passed once on a maintainer's machine on September 22, as the [README](../README.md#what-is-qualified-and-what-is-not) states, with no retained receipt | measured | **Observed:** fresh-session recall and exclusion in real use. Saved entries do not feed automatic recall ([journey map](supported-journeys.md#memory)) |
| S4 signed plugins and Voyage | `tests/test_plugin_signing.py` and `tests/test_plugin_runtime.py` in the six installed-wheel jobs; the [Voyage recorded fixture](../tests/fixtures/voyage-live-recorded/README.md); [running a signed plugin](executable-plugin-run.md) | measured; live on macOS only; replay on all six jobs | No general ranking-quality claim; no live call on Ubuntu or Windows |
| S5 platform limits | The README's [qualification table](../README.md#what-is-qualified-and-what-is-not), the [qualification guide](qualification.md), the platform receipts from the [`Qualification` run](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/36627949560) at the 1.2.0 commit (one `qualification-<os>-<python>` artifact per job) | measured | Windows native memory, `fix` and `test` remain written limits |
| S6 usability | None | — | **Observed:** a named non-programmer's installed walkthrough. Not yet done |
| S7 release mechanics | [Release runbook](release-runbook.md). Each publish run's `release-evidence` artifact holds `SHA256SUMS`, and PyPI's hashes were compared against it: 1.0.0 [run 36451826139](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/36451826139), 1.0.1 [run 36466359597](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/36466359597), 1.1.0 [run 36522747598](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/36522747598), 1.2.0 [run 36629591220](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/36629591220). For 1.2.0 the wheel is `17c3f0953d136314b199af3b72d7ce6773c9766066ac8c086742aa0d863351f7` and the sdist `2f36d6cd492738a8c737c493e222c9a66d252a9fe89d38f1bdb0a554bea638bc` | measured | None; each release repeats the runbook's steps |
| S8 loose ends | [Qualification guide](qualification.md) (the historical `check_code_rag_host.py` is labeled as such); [documentation maintenance](documentation-maintenance.md) | measured | Any replacement host check needs its own scope |
| S9 migration | [Migration guide](migration-from-attune-ai.md), [journey map](supported-journeys.md) | — | **Observed:** each row tried against the installed stable artifact. Not yet done |

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
| R0+14 (Oct 12) | Review stability, unresolved defects and user feedback; choose the next bounded milestone | Written go/hold decision for GUI discovery, workflow restoration or further stabilization; no automatic GUI implementation |

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
900 seconds on all platforms, with a 20-minute outer CI job for setup/evidence.
Individual operation deadlines remain unchanged. If the fifteen-minute budget is
repeatedly exhausted, investigate before changing it again.

## Explicitly deferred

GUI implementation (any prototype is a separate track); extra RAG
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
Completion review: complete for planning; release acceptance remains open.
