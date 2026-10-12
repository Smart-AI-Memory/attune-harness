# Attune Harness 1.4.0 preparation readiness

## October 12 readiness addendum

This is a dated preparation checkpoint, not live qualification or publication
status. It preserves the evidence available before the final documentation
successor. Match a published package to the exact run that uploaded it and its
archive identities; later results do not rewrite this checkpoint.

The software qualification and build-only rehearsal below are complete for
predecessor main `e3eec266a2bb9f0e28b0227abcb232fe30534eb2`, tree
`0be17834c9c25ff01878babe38f4d76b03c9d390`. Its signature is valid and its
tree equals corrected PR #262 head `4ccf4dce05dfab29407758ccb01606206bdda58a`.
This documentation-only correction changes the package README and creates a
successor source/archive identity. These predecessor receipts do not certify
the successor package. Bind its qualification and final build verification to
the actual merged source; no self-referential commit pin is added here.

### Completed predecessor checks

- [Exact-main qualification](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/38196724703)
  and all 19 main checks succeeded. Full source: 4,435 passed / 65 skipped.
  All six installed-platform jobs passed; all 18 GUI client cases passed in
  each profile. Three isolated Windows effects profiles passed 10 cases each.
  Supplemental coverage passed separately with its stated instrumentation limits.
- All 12 retained CI artifact ZIP digests matched their GitHub digests;
  module receipts matched all 105 source modules and coverage bound 915 inputs
  without drift. These checks do not establish native user acceptance or model quality.
- [Build-only rehearsal 38198404008, attempt 1](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/38198404008)
  succeeded on October 12 with version `1.4.0`, target `pypi` and
  `publish=false`. All publication jobs were skipped. The source/version,
  successful main qualification and unused version slot passed preflight.
  Twine strict validation, 21 core and 29 dependency-installed CLI cases passed.
  The dependency-installed plan/accept/build/review/status journey used command
  and deterministic adapters with four participant turns and zero model calls.
  Installed browser policy remained forms-only.

| Predecessor rehearsal archive | SHA-256 |
| --- | --- |
| `attune_harness-1.4.0-py3-none-any.whl` | `572e38759cf9df9f03870172697fc0e0d67db0a4e8aa760b459b1868fef6b63d` |
| `attune_harness-1.4.0.tar.gz` | `5b8a116964f3be145a482cc833db7db08ec346735282d81ab034705673fe6a83` |

Both archives matched the run's checksum list and all 105 runtime modules.
Wheel RECORD hashes/sizes, package name/version and the sdist README,
MANIFEST and pyproject matched their source. The canonical tutorial is maintained
in the repository, outside the standard sdist file set. Rehearsal hashes are
not proof of any later publishing run's bytes or trusted-publisher operation.

### Canonical topics and the approved interim guidance

Patrick approved the bounded release disposition on October 12: ship the
current written tutorial; keep 1.3.0 decks historical; defer replacement decks
and separate Help deployment; retain S3/S6/S9 observations visibly open.

| Topic | Disposition and applicable evidence | Result and limits | Derivatives and older guidance |
| --- | --- | --- | --- |
| Navigation / saving and approval | Changed: [current eight-step written procedure](tutorials-next-release-candidate.md#save-and-approve-a-clear-work-request), reviewed source/client checks and Patrick's bounded forms observations. PR #262 corrects step 8 to inspect the already-expanded accepted request and expand only if collapsed. | Saved literal answers, whole-request review and read-only accepted inspection; approval grants no execution. Assistance and independent-comprehension/keyboard limits remain recorded. | Current written procedure is official interim 1.4.0 guidance. Keep 1.3.0 procedures, decks and captures versioned; new deck rendering is deferred. |
| Session continuity | Changed: [same-view restoration and deliberate reopening](tutorials-next-release-candidate.md#session-continuity-what-survives-reload-and-reopening), current client checks and retained applicable observations. | Saved answers persist; unsaved typing does not. Storage, navigation, exclusive ownership and fresh checkpoints bound restoration; stale/unconfirmed replies are not replayed. Broader native ownership/AT observations remain open. | Same written interim; retain old screenshots with original source attribution. |
| Specification workflow | Unchanged but reviewed: [historical CLI procedure](tutorials-1.3.0.md#specification-workflow-preview-and-acceptance) and retained corrected-wheel replay cited in the candidate topic record. | Plan accepted, `calc.py` unchanged, no build state. Carry original replay provenance where CLI inputs/behavior remain unchanged. | Preserve historical canonical bytes and decks; avoid relabeling GUI imagery. |
| Four workflows / research | Unchanged but reviewed: [retrieval/verification procedure](tutorials-1.3.0.md#four-workflows-research-a-question) and retained corrected-wheel replay. | Two retained source hashes, one verified link and `semantic_ran: false`; no policy-truth or model-output-quality claim. | Preserve historical instructions and sample limits. |
| Consultation | Changed: [current consultation guide](model-consultation.md), selected merged concurrency/partial/refused-turn recovery and current source/installed qualification. | JSON remains default; setup/inspection is separate from dispatch. Eligible explicit retry preserves history; unknown effects block blind retry. Offline checks do not authenticate a live model or qualify live model quality. | Keep earlier instructions/version labels; separate Help projection remains deferred. |

The retained Help snapshot and canonical 1.3.0 tutorial match at SHA-256
`a31a785ce28a5b035cc202e06959f2832048f235e0724f753fd84f50102a2d97`.
Keep its original provenance and all eight historical deck files / 39 slides.
The approved written guide introduces no new embedded 1.4.0 screenshots;
new visual derivatives are deferred with the deck/Help work. Do not mark older
visual tasks passed or infer new screenshots, accessibility or comprehension
acceptance from a native confirmation. A Help website deployment is not itself
a package-upload prerequisite under this explicit written-interim disposition.

Exact-main Documentation links passed. All 19 README GitHub blob target paths
exist in their released 1.3.0 tree or selected 1.4.0 source. The added written-guide
target and local anchors are checked with this documentation correction.
The versioned `v1.4.0` links remain prospective until the separately authorized
tag/release step in the [release runbook](release-runbook.md#steps).

### Open observations and publication boundary

S3 still needs real fresh-session recall/provenance/exclusion observations;
S6 still needs the qualifying named non-programmer installed walkthrough;
S9 still needs installed stable-artifact migration-row observations.
The scope decision defers those observations; it does not close them or turn
software checks or Patrick's assisted forms practice into their acceptance.
Full M2/M3/M4, browser execution, migration parity and general AI-accuracy claims
remain outside this release's claim. Existing working environments and hooks
remain subject to their separate migration/deprecation decisions.

The remaining package gate is qualification and build verification for the
actual documentation successor, then explicit publication authority and
Patrick's queued deployment approval. No successor build dispatch, upload,
tag, GitHub Release, marketplace or website action is authorized by this record.
Retain the predecessor archives and evidence unchanged.

## Historical October 11 preparation record

The following preparation pins, component observations and pending-status
statements are retained as the earlier checkpoint. The dated addendum above
supersedes their current qualification and release-scope status; it does not
rewrite their source, archive or capture identities.

**Not publication-ready.** The selected version is 1.4.0. Final shipping SHA,
distribution hashes and publication date remain unset. This record implements
the existing [documentation-readiness requirement](release-runbook.md#documentation-readiness);
it grants no merge, dispatch, upload, tag, catalog or website authority.

## Selected source and completed evidence

Patrick selected one combined release containing the merged #233 consultation
changes, approved forms presentation and aligned documentation. The preparation
base is signed main `e459faeb9909c9d2cbbb7337dc18e460d5d49e1f` (#260),
complete tree `f485cbb3aa7ff2330e437399857b65484ab5f4fd`, merged October 11,
2026 at 19:11 UTC. It also contains #257's approval/reload corrections,
#258's consultation changes and #259's prepared-summary regression.
The consultation change adds first-round
concurrency, retained partial results and explicit eligible refused-turn recovery.
It adds one runtime module, making 105. The browser remains forms-only.

The consultation owner retains independent source review, full-source,
installed-wheel, meaningful mutation and offline selective-retry receipts.
Actual-main CI verification remains with that owner. Component qualification
does not qualify this future combined source or its shipping distribution.

The merged #234 golden follow-up checks the snapshot digest and output-byte
budget. Its sole change from main0c is the reviewed six-addition/three-deletion
test patch; runtime source is unchanged. The verified baseline is fixed for
combined local full-source and installed-wheel qualification. The owner retains
the failed 1,200-second macOS supplemental coverage attempt and watches its one
retry; that coverage result remains a release gate, not a reason to duplicate
main/PR checks or block independent combined local qualification. A timeout
without a failed phase does not establish a runtime regression or its cause.

The selected saved-answer refinement remains local at
`3d317e71324b609d5e9f603bf88b447e9007345e`, based on earlier #257 main. Its four-file
delta changes intake presentation, two existing client regressions and the CLI
guide. All 18 client checks pass; meaningful negative controls reject the older
presentation. Independent GPT-6 Astra review approves the final source. The two
existing focused checks also confirm **Done when:** already includes its colon.
Patrick's exact-source visual preview inspection is accepted. No further colon
patch or repeat visual review is required.

The CLI-guide update belongs to the forms owner. This companion documentation
delta changes the existing candidate tutorial, release notes, changelog,
consultation version framing and this readiness record. The isolated
`release/1.4.0-combined-qualified` branch carries the reviewed forms series once
over the merged consultation source. New source changes and version changes are
not part of this integration. The frozen earlier forms-only candidate
`214a402d4dd5d5b84e181fb8713571ed646e693f` and earlier combined preparation
`1e7975941020bf61ad5d79ec284aa480c2189a3a`, their distributions where present, receipts,
installed environments and live practices remain unchanged. Main integration
and exact combined qualification remain pending.

## Human observations and their limits

Patrick observed saving and accepted-request inspection, accepted-state reload,
and unfinished same-view reload retaining the goal with an immediately editable
remaining field. The unfinished answer was deliberately left unsaved. These
observations use retained C09 wheel SHA-256
`c09c3ccc3cd4f280994204f95d35a64b997eaab6e8eaab993c0e7e4dbd064f45`, built from
`df3e242c98a0fecb4c7ac4f6cb143ae30752ab00`; all 104 runtime modules match
merged #257. This carried runtime excludes the later layout refinement.

The revised inline preview is a separate source-bound, synthetic visual
observation. It has no Harness connection or saved-state transport. Its visual
acceptance does not establish installed revised-layout behavior, exact Tab order,
native accessibility names, screen-reader announcements or general accessibility
conformance. Independent approval comprehension and other native ownership
transitions remain unscored. Earlier launcher failures, absent-listener failure
and unknown root causes remain in the owner receipts. Do not relabel them as
passes or repeat already completed scenarios merely because prose changes.

## Required documentation completion

Documentation updates are part of this change, not later cleanup. Before
publication, integrate the companion instructions and release notes with the
selected layout, confirm examples against the combined source, and complete the
source and image dispositions below. No new UI feature or historical Attune-AI
documentation repair is added to this release.

| Topic/source | Changed or reviewed unchanged | Evidence and remaining completion | Older guidance |
| --- | --- | --- | --- |
| CLI guide | Changed by forms owner | Inline labels, preserved spacing, **Saved answers** and **Still needed** match reviewed local source. Carry this existing delta once. | Retain released 1.3.0 guide. |
| Candidate tutorial | Changed here | The first goal-based walkthrough saves and approves a clear request. It names **Saved goal:**, **Done when:** and **Still needed**, separates saved data from remaining input, and ends with read-only accepted inspection. Check the complete journey on the exact combined installed wheel, distinguish software checks from native observations, and bind its final source pin. | Preserve the immutable historical #243 section and 1.3.0 walkthrough. |
| Release notes and changelog | Changed here | State the local layout, completed main evidence and remaining installed/native limits; replace preparation pins with the final shipping identity before publication. | Keep published 1.3.0 notes. |
| Screenshots and changed visual examples | Required before publication | Retain source-bound saved/remaining layout capture with **Saved goal:** and **Still needed**, plus **Done when:** when criteria are shown. Record whether each image is an exact-source synthetic preview or installed candidate. Reuse approval/accepted/reload captures only where implementation and inputs still match, retaining original provenance. Never relabel old images. | Keep historical captures with their original source/version. |
| Planning and research examples | Unchanged, reviewed | Five retained C09 CLI actions passed with no model calls: accepted plan without build, two retained retrieval sources, one verified link and `semantic_ran: false`. Layout does not change these commands. | Canonical 1.3.0 text remains byte-identical. |
| Consultation | Newly selected release scope; version framing changed here | Carry the merged #233 concurrency and explicit refused-turn recovery guide and reviewed implementation. First rounds are concurrent, later synthesis requires a completed first round, partial sibling results survive, and unknown effects still block blind retry. Existing #237/#238/#240/#246 setup and inspection guidance remains applicable; JSON stays default. The separate packaged cross-review preflight omission remains an owner follow-up. | Earlier forms-only preparation excluded #233; that earlier scope is superseded, not rewritten. |
| Decks | Disposition needed | Recommend current 1.4.0 canonical instructions as an explicit interim addendum paired with clearly labeled historical 1.3.0 PPTX/HTML. Candidate deck rendering remains pending; require Patrick and content-owner disposition rather than silently waive it. | Preserve all eight historical files and 39 slides. |
| Harness Help Center | Applicable topics and source pins need reconciliation | Help owner updates start-and-continue, save-and-resume and troubleshooting for final tutorial/layout source, including changed visual examples. Local content readiness and website publication are separate. | Preserve 1.3.0 snapshot/projection/captures. |

## Deck and Help disposition

The supported presentation runtime is unavailable in the tutorial owner's
environment. New candidate deck copies have not been rendered. Recommend a
bounded interim arrangement: publish the updated canonical 1.4.0 instructions
beside accurate 1.3.0 historical training files, clearly stating the changed
controls, saved-answer presentation, conditional reload and browser forms-only limits.
This proposal needs an explicit release/content-owner decision; old decks cannot
be called revised 1.4.0 training. Unchanged historical files need no rerender.

At the earlier October 11 read, Help PR #2552 was draft/unmerged at
`87cb091b85bd16e90b4b480f709784ed6f5ef26c`, based on website main
`5e11cb025b605d7a6c1725024baf517a9dc8369e`.
Its retained hosted preview names that older source. The Help-owner
handoff describes a separate nine-file staged 1.4.0 correction at tree
`9661c9d2f6bb3018a05490576b7f31bcd852de47`; its reported tests/build qualify
that input, not the new layout or final Harness tutorial. The owner must reconcile
the combined source pins and newly selected consultation scope before calling
affected Help content ready. These are dated inputs, not a fresh hosting check.

Website scanner/helper authentication failures and earlier public-link HTTP 503
remain website-owner constraints. They block that website's affected outward
actions, not Harness package CI. Production Help hosting is not a package upload
prerequisite by itself. Package documentation readiness still requires either
matching prepared Help content or an explicit owner/Patrick disposition that
the current canonical 1.4.0 instructions are the official interim guidance.
No authentication change, website merge or deployment is requested by this
documentation branch. Unrelated historical Attune-AI documents stay out of scope.

## Final release gates and decisions

1. Integrate only the approved local layout and companion documentation over
   the fixed #260 baseline through
   owned PRs. Preserve the four-file forms delta once, resolve the final canonical
   source pins, retain matching changed screenshots, and record source/doc review.
   Named merge authority is still required; current main checks do not qualify
   the future combined tree. Preserve the owner's pending supplemental coverage
   disposition as a separate release gate.
2. Read the final exact-head full-source/platform evidence and the actual merged
   tree. Build and verify the shipping wheel/sdist, package metadata and installed
   checks against that tree; record both archive hashes. Retained C09 is rehearsal
   evidence, not the final published distribution. Existing practices remain
   untouched; any needed installed check uses a new disposable environment.
3. Resolve the interim deck/Help arrangement and retained observation gaps in one
   release decision. S3 fresh-session recall/exclusion, S6 a named non-programmer's
   installed walkthrough and S9 stable-artifact migration rows remain open; do
   not count Patrick's preview as S6. Full M2/M3/M4 and browser execution are
   outside the selected release claim, consistent with the project plan.
4. Recheck main, qualification, the unused version slot and the PyPI environment.
   At the October 11 read, PyPI latest is 1.3.0, the exact 1.4.0 endpoint and
   GitHub v1.4.0 tag are absent, and the environment permits main with Patrick's
   required review. Protection requires strict Qualification and signed commits.
   Trusted-publisher operation is not established by these read-only checks.
5. After the source/docs packet is ready, obtain explicit approval for the
   build-only release-gate dispatch and, later, the named package-publication
   dispatch. Patrick approves the queued PyPI deployment. Verify the actual
   published hashes and install, then request/create the signed v1.4.0 tag and
   GitHub release under explicit authority. Reconcile the Claude marketplace by
   its own reviewed PR after the verified tag exists. TestPyPI is an optional
   RC-only route, not a required stable-1.4.0 detour.

Publication follows review of the final source, artifact and documentation
packet; no publication date is selected here. Publication, tags,
release creation, marketplace changes and website hosting remain separate named
actions. #233 and the merged #260 golden follow-up are included.

Previous preparation identities, early pending statuses, source failures and
component receipts remain preserved in the immutable
[earlier readiness record](https://github.com/Smart-AI-Memory/attune-harness/blob/e314e78a96f9999a600430d4d49aee6c4da160dc/docs/release-readiness-1.4.0.md)
and the local owner handoffs. Software qualification establishes checked behavior;
it does not guarantee hallucination-free output or live model quality.
