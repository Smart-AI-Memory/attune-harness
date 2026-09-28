# Stable v1 and the first two weeks after release

Refreshed September 28, 2026 against main
`30ae645560cf309cfbd8eed16875bf83b1dbb1c9`. This updates the execution focus of
[the v1 roadmap](plan-1.0.md), retaining [S1–S9 and D25–D30](specs/release-1.0/addendum-2026-09-23.md).
The earlier phased and October plans remain historical inputs, not an extra
release backlog. Planning scope: stable v1, then fourteen days of stabilization.
This document selects work; it does not authorize merges, paid calls, workflow
dispatch, publication, repository settings changes or a deprecation notice.

## Executive status

**Current decision: prepare an accelerated stable 1.0.0 release for Patrick's
review.** The production PyPI `1.0.0rc2` release is published and its fresh
unconstrained `[all]` install has passed `pip check`, installed checks and an
offline Forms plan/accept/build/review journey. PyPI's unversioned project and
search result still display stable `0.6.0`; a direct rc2 link does not change
the default page or ordinary install selection. Mirror-excluded PyPI Stats
recorded one download on September 27, before rc2 publication. That count is
not a measure of people or evidence that the PyPI display caused the decline.

The proposed stable release uses rc2's runtime and pins without a frozen
surface change. It has **not** completed the previously planned fourteen days
of observed candidate use, a named non-programmer installed journey, real
fresh-session memory observation, or per-row candidate migration trial. Those
are acceptance gaps, not results to infer from green software checks. This
plan proposes moving those observations into the post-release stabilization
period to improve discoverability, subject to an explicit stable-release
decision after the exact artifact and platform evidence are reviewed.

PR154–159 and PR161–163 are merged. Main matches [PR163's](https://github.com/Smart-AI-Memory/attune-harness/pull/163)
tested head tree `7c93877a3d8b5c8ed140539e9b3c505d7c947c28`; all 19 PR163 checks
passed, including the six installed-wheel platform jobs. The final source suite
passed 3,342 tests with 52 skipped, and fresh installed macOS qualification
passed 1,632 with seven skipped. [PR162](https://github.com/Smart-AI-Memory/attune-harness/pull/162)
retains 33 byte-exact files written through the clean unpublished `1.0.0rc1`
candidate wheel, reader/refusal tests and CLI choice/default guards. Its source
and public-claim reconciliation are merged. The bounded live Voyage campaign completed on
macOS; PR161 retains four paired direct/signed-plugin stage responses and tests
keyless offline replay across the six CI platforms. This is not broad retrieval
quality, live cross-platform or human acceptance evidence. See
[the retained replay fixture](../tests/fixtures/voyage-live-recorded/README.md).
Those are historical prepublication receipts. Rc1 and rc2 are now published on
production PyPI; rc2 is the current candidate. Recheck the exact stable SHA,
PyPI version slot and installed artifact before any authorized stable dispatch.
No percentage-complete estimate is useful while observed acceptance is open.

| Gate | Present now | What still closes it |
|---|---|---|
| S1 compatibility | Versioned state, CLI/API/envelope and deprecation/protocol guards; PR162's candidate-written 33-file fixture, reader/refusal checks and CLI choice/default guard; fresh-wheel and six-platform evidence | Preserve the frozen rc2 contract through the final release SHA. The capture manifest proves installed package and bytes, while the writer recipe and reader tests provide the separate writer/consumption evidence. |
| S2 native independence | D28 adapter removal and native installed journey merged in PR149 | Retain final-artifact proof; Patrick's separate Attune AI writer constraint is not claimed complete. |
| S3 useful memory | Serving/filter software and explicit saved capture exist | Real fresh-session provenance/recall and corrected/inactive exclusion; explicit saves are not automatically connected to serving. |
| S4 signed Voyage | Bounded live direct/signed-plugin campaign complete; retained responses and six-platform offline replay merged in PR161; PR162's bounded R1–R7 public claims reconciled | Keep live-macOS versus offline cross-platform limits visible in the final artifact and candidate observations; no general ranking-quality claim. |
| S5 platform limits | Six platform jobs green; PR162/163 release claims state native-memory, saved-storage and plugin limits | Recheck the exact release artifact and observed-period receipts; Windows native memory/saved limits remain unless separately qualified. |
| S6 usability | Observation procedure prepared; no named non-programmer walkthrough recorded | Keep the gap visible in release notes; perform and retain the installed stable journey during stabilization. Do not claim prior human acceptance. |
| S7 candidate/release | Rc2 is published on PyPI; its fresh `[all]` install passed. The candidate observation period is incomplete. | Qualify the exact stable SHA, recheck the PyPI slot, rehearse the publication gate, obtain separate merge/dispatch/publication/tag decisions, verify the installed stable artifact and continue observations. |
| S8 loose ends | Most historical hygiene closed; PR162 explicitly labels the old code-RAG caller/check historical and reconciles public claims | Any replacement host check needs separate scope and evidence; retained script/receipts stay untouched. |
| S9 migration | Migration guide drafted; candidate row-by-row trial not recorded | Preserve separate environments and exercise each supported row against the installed stable artifact during stabilization. |

## Ordered work to stable v1

1. **Voyage evidence complete (S4 bounded campaign).** The approved signed-plugin
   and direct-provider comparison retained four matching stage pairs, with eight
   attempted paid stages and 29,698 provider-reported tokens. Calculated cost at
   pinned rates was $0.00249178, not an invoice-verified amount. PR161 adds keyless
   replay of the retained responses. Live evidence is macOS only; interruption
   refusal is synthetic, and replay does not establish general retrieval quality.
   The public requirement/claim reconciliation was completed in step 2. No further paid
   calls are needed for this completed campaign. Explicit local keyword retrieval
   stays available; keep attune-rag until its features have tested replacements.
2. **Candidate compatibility and claims (S1/S5/S8), completed before publication.**
   [PR162](https://github.com/Smart-AI-Memory/attune-harness/pull/162) merged
   the installed-writer fixture, exact raw bytes and hashes, reader/refusal
   matrix, CLI choices/defaults and bounded claim audit. Its clean writer wheel
   was unpublished when captured; the content froze at rc1 publication.
   Retain those receipts and require the final release wheel's packaged runtime
   files and selected metadata/entry points to match the writer contract.
3. **Prepare stable 1.0.0 (S7).** The rc1 and rc2 publication steps are complete.
   Make a separate version-and-docs pull request from current `main`, with no
   runtime or saved-format change. Qualify its wheel, source suite, dependency
   resolution and all six installed-wheel platform jobs. Compare its frozen
   surfaces and published dependency pins with rc2. State the abbreviated
   observation decision and remaining S3/S6/S9 gaps in the pull request.
4. **Approve and publish stable 1.0.0.** Patrick reviews the exact diff and
   evidence, decides whether to accept the shortened candidate period, and
   separately authorizes each merge, workflow dispatch, publication and tag as
   required by the [runbook](release-runbook.md). Verify the PyPI hashes and a
   fresh unconstrained `[all]` install. R0 is the actual stable publication,
   never the date of this plan. Stable v1 does not deprecate Attune AI or claim
   GUI/workflow parity.
5. **Observe after R0 (S3/S6/S9).** Record artifact, session, outcome, failures
   and help required. Observe real memory behavior, a named non-programmer
   installed walkthrough, migration rows and ordinary plugin use. Treat
   findings as product work with separate reviews and releases; do not
   backdate observations or relabel software checks as human acceptance.

The shortest useful next unit is a reviewable stable-release diff and local
wheel qualification. The most urgent user-facing outcome is a stable PyPI
listing that routes ordinary search and installs to the current runtime. Those
are distinct: publication still waits on exact-main qualification and the
release decisions. Do not start another feature chain while these gates remain
open.

## R0 through R0+14: post-release stabilization

Under the proposed accelerated release decision, these observations include
the work originally planned for the candidate period. Dates are relative
because stable publication has not occurred.

| Window | Focus | Exit evidence |
|---|---|---|
| R0–R0+2 | Verify the published install and documented journeys; triage installation, recovery, saved-state and unexpected-spend reports first | Artifact identities, reproduced issues and clear dispositions; any urgent patch is independently reviewed and separately released |
| R0+3–R0+7 | Check real usage and support friction; complete shortlist items 1–2 only while incident load permits | Supported-journey map and evidence index tied to stable artifacts |
| R0+8–R0+13 | Complete shortlist items 3–4 if still useful; review CI durations and recurring failures | Small documentation/report deliverables, no unmeasured speed claims |
| R0+14 | Review stability, unresolved defects and user feedback; choose the next bounded milestone | Written go/hold decision for GUI discovery, workflow restoration or further stabilization; no automatic GUI implementation |

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
| 1 — O-04, supported journey map | Refresh the existing map for install, plan/build/review, memory, Voyage and recovery. Each row names entry point, platform limit, evidence and workaround. Distinguish explicit saved capture from automatic recall. Done: no stale claim that merged implementation is absent or unqualified behavior is complete. | 1–2 hours | Release claim audit where required; finish remaining map during week 1 |
| 2 — O-09/O-16, evidence navigation | Add links in existing release documentation to artifact hashes, CI, observed receipts and known limits. Label measured checks versus model judgments and live versus replay. No receipt-schema change or duplicate evidence system. Done: a reviewer reaches each S1–S9 receipt or explicit gap from one index. | 1–2 hours | Candidate/release preparation if needed; finish week 1 |
| 3 — existing Windows-traps follow-through | Document byte-exact signed bundles, GPG path rules, drive-qualified capture refusal, and the 15-minute suite/20-minute job distinction. Verify each statement against shipped behavior. Done: targeted guidance and links; no runtime edits. | 0.5–1 hour | Week 2, or earlier if needed for walkthrough |
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
human observations retained as named gaps during stabilization. The rc2
compatibility proof and PyPI install are complete; the highest-value remaining
distinction is between software checks and observed user acceptance.
The first user-facing opportunity is O-04's accurate journey/limits map. This review narrows
existing opportunities rather than inventing a new register or reopening closed
work. Completion review: complete for planning; release acceptance remains open.
