# Stable v1 and the first two weeks after release

Reviewed September 27, 2026 against main
`38a5663909139a1811013c8f30d072a516c0067e`. This updates the execution focus of
[the v1 roadmap](plan-1.0.md), retaining [S1–S9 and D25–D30](specs/release-1.0/addendum-2026-09-23.md).
The earlier phased and October plans remain historical inputs, not an extra
release backlog. Planning scope: stable v1, then fourteen days of stabilization.
This document selects work; it does not authorize merges, paid calls, workflow
dispatch, publication, repository settings changes or a deprecation notice.

## Executive status

PR154–159 and PR161 are merged. Main matches PR161's tested head tree:
`626f6450635ee59f9b4ed805a7f30c04f618ac87`.
All sixteen PR161 checks passed, including six installed-wheel platform jobs,
three supplemental coverage jobs, full suite and security checks. Local final-head
full validation passed 3,328 tests with 52 skipped; installed macOS qualification
passed 1,623 with seven skipped. The bounded live Voyage campaign completed on
macOS; PR161 retains four paired direct/signed-plugin stage responses and tests
keyless offline replay across the six CI platforms. This is not broad retrieval
quality, live cross-platform or human acceptance evidence. See
[the retained replay fixture](../tests/fixtures/voyage-live-recorded/README.md).
The earlier release check listed v0.6.0; release and package-index publication
state must be checked again before candidate publication.

**Status: preparing the release candidate; not ready to publish stable v1.**
No percentage-complete estimate is useful while observed acceptance is open.

| Gate | Present now | What still closes it |
|---|---|---|
| S1 compatibility | Versioned state, CLI/API/envelope and deprecation/protocol guards; PR159 capture preparation | Real candidate-written saved records, reader/resume checks and final freeze. The capture tool verifies byte/package provenance, not who originally wrote arbitrary records. |
| S2 native independence | D28 adapter removal and native installed journey merged in PR149 | Retain final-artifact proof; Patrick's separate Attune AI writer constraint is not claimed complete. |
| S3 useful memory | Serving/filter software and explicit saved capture exist | Real fresh-session provenance/recall and corrected/inactive exclusion; explicit saves are not automatically connected to serving. |
| S4 signed Voyage | Bounded live direct/signed-plugin campaign complete; retained responses and six-platform offline replay merged in PR161 | Final plugin R1–R7 public claim/evidence reconciliation in step 2. Live evidence is local macOS; CI replay is offline, not live platform qualification. |
| S5 platform limits | Six platform jobs green | Final README/qualification claims match actual scope; Windows fix/test/native-reader limitations remain unless separately qualified. |
| S6 usability | Observation procedure prepared | Named non-programmer completes the installed candidate journey under observation. |
| S7 candidate/release | Existing runbook and earlier build-only rehearsal | Current environment/artifact verification, approved rc1 publication, two-week candidate observation, then stable approval. |
| S8 loose ends | Most historical hygiene closed | Explicitly disposition the old code-RAG check/callers without removing retained functionality; final claim audit. |
| S9 migration | Migration guide drafted | Exercise its supported rows and verify workarounds against the candidate; preserve separate environments. |

## Ordered work to stable v1

1. **Voyage evidence complete (S4 bounded campaign).** The approved signed-plugin
   and direct-provider comparison retained four matching stage pairs, with eight
   attempted paid stages and 29,698 provider-reported tokens. Calculated cost at
   pinned rates was $0.00249178, not an invoice-verified amount. PR161 adds keyless
   replay of the retained responses. Live evidence is macOS only; interruption
   refusal is synthetic, and replay does not establish general retrieval quality.
   The public requirement/claim reconciliation remains in step 2. No further paid
   calls are needed for this completed campaign. Explicit local keyword retrieval
   stays available; keep attune-rag until its features have tested replacements.
2. **Finish candidate compatibility and claims (S1/S5/S8), active in
   [PR162](https://github.com/Smart-AI-Memory/attune-harness/pull/162).** Use an
   unpublished candidate-version wheel to write real saved state, retain raw bytes
   and hashes, and prove final readers/status/resume consume it. Patrick approved
   including CLI choices/defaults in the freeze inventory. Reconcile README,
   migration and qualification claims, and disposition obsolete callers. Done:
   freeze inventory, actual writer provenance and guards agree, with full suite,
   fresh-wheel qualification and independent review. An unpublished local wheel
   does not start the candidate observation clock. Owner: Sol/Astra; Patrick owns
   scope rulings and merge approval.
3. **Prepare and publish rc1 (S7).** Verify current release settings through the
   existing runbook; qualify the exact clean source/artifacts. Present the concrete
   hashes and evidence for dispatch/publication approval. Candidate channel is
   TestPyPI; do not repeat historical instructions that imply rc1 is on PyPI.
   At least the S3 SessionStart filter evidence must hold before rc1. Owner:
   agents prepare; Patrick approves release actions.
4. **Observe the candidate for at least fourteen days (S3/S6/S7/S9).** Set C0 from
   the actual published, installed candidate with frozen surfaces. Record artifact,
   session, outcome, failures and help required. Observe real memory behavior,
   one non-programmer walkthrough, migration paths and ordinary plugin use. A
   frozen-surface change requires the next candidate and restarts the interval.
   Elapsed days without observations are not acceptance evidence.
5. **Approve stable v1.** At C0+14 days or later, review all S1–S9 evidence and
   unresolved findings, qualify the exact stable artifacts against retained candidate
   state, then obtain concrete publication/tag approval under the runbook. Stable
   release is R0. October remains a target, not a promised date. Stable v1 does not
   automatically deprecate Attune AI or claim GUI/workflow parity.

The shortest useful next unit is completing and validating candidate-written
compatibility fixtures. The next release dependency is closing that freeze and
claim audit before rc1 preparation. Scheduling human observations can proceed
alongside it. Do not start another feature chain while those gates remain open.

## R0 through R0+14: post-release stabilization

This is **additional to**, not a substitute for, the fourteen-day candidate period.
Dates are relative because neither publication date is established.

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

GUI implementation; extra RAG providers/OpenAI retrieval fallback; automatic
provider switching; broad memory/workflow parity and Spec lifecycle expansion;
new cross-provider model campaigns; general caching/performance redesign;
Attune AI deprecation and removal of attune-rag. Existing supported paths and
experimental labels stay honest. These exclusions protect release focus, not a
claim that the work has no value.

## Review outcome

Goal: stable interfaces backed by live, installed and observed evidence, followed
by a quiet stabilization period. The highest-value finding is the distinction
between merged implementation and unclosed acceptance: more feature PRs will not
supply candidate compatibility proof or fourteen days of observed acceptance.
The first user-facing opportunity is O-04's accurate journey/limits map. This review narrows
existing opportunities rather than inventing a new register or reopening closed
work. Completion review: complete for planning; release acceptance remains open.
