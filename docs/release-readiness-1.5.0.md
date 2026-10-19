# Attune Harness 1.5.0 preparation readiness

**DRAFT — UNRELEASED.** Current package and plugin metadata identify an
unpublished `1.5.0` validation candidate. The historical preparation snapshot
below is from October 16, 2026; its `1.4.0` artifact identities remain unchanged.
Full Windows parity is deferred, and final release acceptance remains pending.
This record does not establish an accepted final release SHA, a published 1.5.0 distribution,
a publication date, or release approval.

## Current candidate and release scope

Patrick approved preparing verified 1.5.0 changes while deferring the full
Windows parity claim. This changes the release claim, not the strict Windows
acceptance criteria or publication authority.

The documentation proposal uses integrated runtime baseline
`18e9f2894e0c0e6ac0d18dda2c65615648f1dcc7`, tree
`ab897c080d41e2d7c03409a42d58af3c537b7657`.
[Qualification run 39148684067](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39148684067)
passed all 16 jobs, including eight installed-wheel platform/runtime cells and
four Windows Server full-source-suite cells. This is hosted CI evidence for
that commit and the artifacts it built. It does not qualify Windows 11,
PowerShell procedures, live native memory, full storage acceptance, strict
arbitrary-descendant stop behavior, or this later metadata-changed artifact.

The selected local review wheel is
`17823fbd7037ce26e9de6108a8db9680956ee2b7a20224bc490173ccb5e0bd6d`.
Its original build-time source archive is
`b0d9d2ca6e88ae10e3ec63ead65eabe0b3577b2aba9d2e8f0ecde914f459e2cb`;
the source commit was null when it was built. The archive retains all 1,008
tracked build inputs. The changed README description required distinct wheel
bytes. Compared with retained wheel `85912054`, only the metadata description,
build-generator value and wheel `RECORD` differ. All 107 runtime modules,
metadata headers and dependency requirements, wheel tags and five dependency
locks match. The new environment has the same 94 dependency distributions;
5,539 installed package/data files match byte for byte. Generated launchers,
bytecode and installation-provenance files are excluded from that comparison.

A fresh noneditable installation, installed-module/source identity and
`pip check` passed on macOS arm64/Python 3.12.2. Local checks passed: 114 focused
packaging checks; 5,057 full-source tests with 237 skips and seven passing
subtests; and 2,826 installed-selection tests with 193 skips and two passing subtests. The retained evidence records the commands,
phase timings, warnings, skips and exact environment. These are software checks
with zero paid provider calls, separate from the four observed procedures and
from model-quality or Windows qualification.

The current canonical review document is
`e2bec1b87b108dbc484a4cb336e1038790671134ca0e565fdbc0c1790a7ba2f8`.
It is an outside-wheel documentation revision after the build-time archive; the
archive's original canonical identity remains unchanged. Its six command
fences and eight numbered action lines preserve the observed command inputs.
The planning preparation prose now returns to the action table for one
execution. A separate check on installed wheel178 passed one init, draft,
accept and accepted-status sequence. A repeated-init negative control refused
with exit 2 and preserved the accepted task/request bytes. Neither check started
a build or called a model. The other three journeys were not rerun. All 25
example files and effective runtime/dependency inputs match the retained
observations. Later source/archive bindings remain additive; they do not
replace the original build receipt or relabel the four wheel859 observations.

The earlier local wheel remains
`859120544a5040532f06a19eab02996377afc0f73b05f7d0b19829378249b586`.
Its original source archive is
`f38205a1bdb15c4890d8e7c08d633a5f1353a369c868d0b78900e8d2614a157e`,
with a null source commit at build time. The later archive
`88ee9faa605eb374be4e04ca297d3ac082b070e0bdff8922fa2b7137cd06de36`
binds all 1,008 earlier integrated-candidate inputs; two outside-wheel release
documents differ from the original archive. All original identities and failed
or uncertain outcomes remain retained. Neither local wheel is claimed
byte-identical to a hosted CI artifact or future published distribution.

Before release, accept the final integrated source and artifact, reconcile any
subsequent changes, check affected claims and close the final documentation
completion review. A documentation proposal is not accepted final main.
Release tags, publication and published PyPI-byte verification remain
separately gated. Windows 11 candidate reports and later uncommitted runtime
proposals do not qualify this integrated source without their exact receipts
and source bindings.

## Historical October 16 preparation snapshot

Documentation target base: `0735cca55480b031050dc8d7e3c2ea72a3cd6dc1`, tree
`040e2acd576af04542d49dc17c71fc4cf5c3cf84`. Patrick merged the saved-store
implementation checkpoint as [PR #275](https://github.com/Smart-AI-Memory/attune-harness/pull/275)
on October 16, 2026. Its whole tree equals reviewed and tested head
`05b649f2d255f3a9a2d4bc9f4c92c70cf530f03a`. The
[process-completion work](https://github.com/Smart-AI-Memory/attune-harness/pull/274)
and final parity gates remain open.

The earlier documentation head `46ad1ffe` passed its own docs-only checks,
separate supplemental coverage, and offline SDK checks on base `0ecb45d`.
Those results do not qualify this later merged production source or the final
combined README and artifacts. The final integrated source needs its own
qualification.

## Component evidence

| Component | Merged evidence | Boundary of the claim |
| --- | --- | --- |
| Captured-change testing | [PR #271](https://github.com/Smart-AI-Memory/attune-harness/pull/271) | Native Windows test execution and installed component witnesses; final combined CLI and desktop journeys remain open |
| Retained-handle read primitives | [PR #270](https://github.com/Smart-AI-Memory/attune-harness/pull/270) | Shared read-only primitives; their success alone does not qualify a reader consumer or saved storage |
| File-memory readers and serving | [PR #272](https://github.com/Smart-AI-Memory/attune-harness/pull/272) | Native reader, capacity, freshness, and path witnesses; final combined product qualification remains open |
| Experimental native-memory transport | [PR #269](https://github.com/Smart-AI-Memory/attune-harness/pull/269) | Offline supervised-helper and pinned-SDK evidence; no live provider or model-quality acceptance |
| Saved-store implementation checkpoint | [PR #275](https://github.com/Smart-AI-Memory/attune-harness/pull/275) | Current finite native lifecycle, concurrency, crash, replay, and task witnesses pass; full T5 and the historical busy-failure cause remain open |
| Saved-store feasibility | [PR #268](https://github.com/Smart-AI-Memory/attune-harness/pull/268), [native run 38916934064, attempt 1](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/38916934064) | Accepted finite fixed-component T2/D3 feasibility; not current production storage, Windows 11, or final parity |

The D3 event ran four standard-primary-token cells on Windows Server 2022/2025
with Python 3.10/3.12. Its public head is
`30beb61d081a73ad0e04e8dfbdd1ea2a628ee204`, with the
[exact workflow source](https://github.com/Smart-AI-Memory/attune-harness/blob/30beb61d081a73ad0e04e8dfbdd1ea2a628ee204/.github/workflows/windows-saved-store-observed-account-event.yml).
Its fixed component is `bde059cf08924937948f4fb7c8347f88010a5bc4`; the
observed normal merge is `1ed9c1264c149bbef114af6dabe8a81d897dedfc`.
The accepted claim is the finite local NTFS OS storage-barrier composition,
with explicit setup and storage/device assumptions. Mapping the referenced
MS-FSA contract to the local handle protocol remains an engineering inference.
Controller anchor setup is a separate premise; primitive enclosing-path
publication and unretained seed/retry I/O are not newly qualified. Replays add
no fresh barrier. Process termination does not establish physical power-loss
behavior.

This later disposition satisfies the D3 feasibility precondition for T5. The
[earlier proof design record](design-windows-saved-store-proof.md) retains its
dated pending states and failed attempts unchanged. None of those records, or
the fixed-component proof, certifies a later production wheel.

## Merged saved-store checkpoint

The [ordinary qualification](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/38954330802)
at `05b649f2` passed all 19 native saved-store cases in each early and broad
Windows run on Python 3.10.11 and 3.12.10, without skips or failures in those
cases. Both broad runs also passed the four saved CLI/parser and seven index
cases. The complete current concurrency witnesses accepted eight independent
and eight identical original writer results. All four crash-boundary whole-byte,
identity, confirmed-close, revision/history, and replay assertions completed.

[Supplemental Windows coverage](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/38954330956)
also passed the 19 native cases for that source. This is instrumented evidence;
its receipt explicitly leaves native process/recovery qualification open.
The ordinary runs retain actual wheel build, constrained local-wheel install,
`pip check`, installed qualifier success, and source bindings. A complete
current CI wheel/RECORD audit is not established; final R7 artifact binding
remains open. No additional host execution is implied by this preparation.

These complete current finite witnesses support a bounded implementation
checkpoint, not full T5 acceptance. The historical Ec eight-writer busy failure
still lacks an observed holder/API timeline or supported causal explanation.
Production and the two-second lock budget are unchanged; the added observer
changes scheduling, so passing traces do not explain the earlier failure. The
accepted first-oracle correction preserves the required whole-byte/replay,
identity, close, and timing criteria; it does not establish the underlying
historical CRT cause or a production fix. The CRT correction does not explain
the distinct busy failure.

Final Windows 11 standard-user desktop, complete Windows Server 2022/2025
qualification with both Python runtimes, declared PowerShell journeys, live
native-memory acceptance, compatibility, and combined artifacts remain T8
work. Full T5 acceptance and the historical busy finding remain open after the
human merge. The earlier observations below are retained as historical evidence.

## Historical pre-merge storage observations

This subsection preserves the Ec/297 preparation snapshots. References to
“current” below describe those earlier heads, not merged `0735cca5`; their
failures and then-pending observations are not erased by the later checkpoint.

The preparation snapshot for PR #275 is signed head
`ecbacc0813a94cabf00bb8df3b7996e1d9b63f0c`, based on then-main
`0ecb45d855250d65f41226b644ca2f2742ff7bfa`.
The current-head Python 3.12
[early installed-owner check](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/38946613117/job/117127300867)
ran 33 cases in 45.611 seconds: 32 passed, one failed, and none skipped; the
original rename-boundary CRT read raised `PermissionError` with Errno 13 and no
WinError. Both later native opens closed cleanly after reading the whole
expected after-image with matching checkpoint identity, and a production read
observed revision 2; these later observations establish neither the original
cause, same-ID write/replay, nor a functioning fix. Other current-head results from the
[Library qualification run](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/38946613117)
and [supplemental coverage run](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/38946613085)
remain pending evidence review in this record.

A later current-head Windows Python 3.10
[qualification job](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/38946613117/job/117127300816)
retains 33 passing early cases, followed by 2,784 passed, 155 skipped, and two
failed broad-suite cases. One child in the first group of eight independent
fresh-root writers returned `SavedError` with code `busy` before the
identical-request phase; the original rename-boundary CRT read also failed with
Errno 13. No lock holder or native
timing cause is established, and the early pass does not erase the later
failures. A separately reviewed local test-method correction supplies no new
Windows acceptance or concurrency repair; the two-second lock budget and
eight-writer acceptance criteria remain unchanged.

The candidate's public evidence records successful local macOS full-source and
fresh installed-wheel checks with zero model calls. Those checks do not replace
native Windows evidence. Historical head
`29763277c433d0bc580ddb7fcc4d32185ed94163` failed the immediate `state.json`
read after killing a writer at the rename boundary on both Windows Python
runtimes. Eighteen other native storage cases passed on each runtime. The
instrumented Windows run repeated that failure; macOS instrumented coverage
reached its earlier time limit without final XML.

The current revision adds ordered diagnostics, early storage-owner coverage,
and macOS instrumentation headroom. Its production source is unchanged from
that historical head. These changes do not establish a production fix, the
native denial's cause, or working crash recovery. Preserve the original failure
evidence and acceptance criteria when evaluating later observations. PR #274's separate
process-completion failure also remains unresolved.

## Remaining release gates

The approved [Windows requirements](specs/windows-parity/design.md) and
[ordered tasks](specs/windows-parity/tasks.md) govern completion. This table
records their remaining evidence needs; it does not create a new process. Full
Windows parity remains open after deferral. Candidate release acceptance still
requires R7 source/artifact binding and R8 claims and completion review for the
selected release scope; no Windows criterion is waived.

| Gate | Required evidence before a release claim | Status in this draft |
| --- | --- | --- |
| Production storage (T5/R4) | Reviewed delivered source; locking, privacy, namespace publication, complete writes and barriers; concurrency, crash/restart, replay, task, index, and CLI evidence | Current finite witnesses pass; full acceptance and the historical eight-writer busy-failure cause remain open |
| Owned-process completion and recovery | Current-source evidence for the declared child-completion and recovery contract, retaining the failing cases | Pending; PR #274 remains open |
| Native-memory acceptance (T7/R5) | Controlled production-transport acceptance, actual outcome and usage, with the existing authority and uncertainty boundaries | Pending; offline SDK evidence is separate, and an unknown prior outcome blocks redispatch |
| Native server qualification (T8) | Final combined source and installed checks on Windows Server 2022/2025 with Python 3.10/3.12 | The four full-source and four installed-wheel Windows cells passed for `18e9f289` in [run 39148684067](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39148684067). This hosted checkpoint does not close the deferred full-parity claim or qualify a later artifact. |
| Native desktop qualification (T8) | Final installed-wheel journeys on Windows 11 with Python 3.10/3.12 under standard user permissions; OS build, architecture, and fixed local NTFS recorded separately | Pending; server or primitive evidence cannot substitute |
| Shell and documented journeys (T6/R6) | Real Windows PowerShell and PowerShell 7 commands, literal path quoting, printed continuations, preview/acceptance, completed handoffs, and recovery against the installed candidate | Pending |
| Compatibility and combined artifact (R7) | Exact final source, wheel and installed modules; dependencies and runtime; historical schema/token/receipt compatibility; required final-head reviews and regression checks | Pending; earlier wheels and component receipts retain their original identities |
| Claims and completion review (R8) | Reconcile the inventory and public platform guidance with final receipts; close the implementation completion review | Pending; this preparation review does not close full-spec completion |

The earlier server checkpoint remains retained: in
[run 39087566327](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39087566327),
Windows 3.12 full source passed, Windows 3.10 timed out at 2,700 seconds
(`exit 124`, `timeout_effects_unknown`), and qualification failed.
[Run 39084249044](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39084249044)
passed Windows 3.10 for the earlier same-tree comparison. Later success does not
identify that historical timeout's cause.

Do not promote a Windows journey into the README's Qualified column from a
component pass or a diagnostic result. Final T8 must use the combined source,
including its final README; a later documentation edit can change packaged
metadata and distribution hashes.

## Documentation preparation

Use the existing [documentation readiness procedure](release-runbook.md#documentation-readiness)
for the release review and coordinate derivatives with their owners. These
notes and the [draft release notes](release-notes-1.5.0.md) prepare that review;
they are not a substitute for its walkthroughs.

The later frozen local 1.5.0 checkpoint completes the four scoped walkthroughs
against wheel `85912054` on macOS arm64/Python 3.12.2: Navigation,
Specification workflow, Four workflows/research, and Session continuity.
Its canonical document SHA-256 is
`b70d24337ce0cf2d39aff7f8ea5ec9401db8497ad72b9fd989dddd540ad6820a`.
The 41-slide replacement PowerPoint/HTML pairs, existing Help derivatives,
reuse checks and 249-file review manifest are prepared and inspected locally.
These materials remain provisional and unpublished. Their original scoped
results do not establish Windows shell, native PowerPoint, model-quality,
migration or final published-artifact qualification. Final release-scope
reconciliation and completion review remain open.

The earlier limited-release snapshot selected wheel `17823fbd` and canonical
`d2f61a0b` while retaining those wheel859 procedure observations. Four new
PowerPoint/HTML pairs preserve all 41 complete notes projections, 26 native
tables and eight historical image placements. All 24 changed footer surfaces
were inspected; the other 17 rendered slides match their fresh references.
The 557 recorded local/static deck targets resolve. Native PowerPoint and a
live external HTTP crawl remain unverified.

Its matching Help overlay retains four topics and nine routes. Its 73 site
tests, historical/candidate drift checks, lint, types and direct 126-page build
passed. Lint retains three existing warnings and no errors. Local checks cover
nine current views, 17 linked responses and 22 pinned source-file/heading
targets. Eight new captures inspect changed disclosures; unchanged procedures
reuse their retained captures. Eight reusable claims retain all 20 primary
propositions. The website overlay remains a local patch; nothing was pushed or
published. Central read-back verified the source/archive/patch and claim chains.

The current E2 correction preserves all 41 visible slide surfaces and their
rendered PNG bytes from that snapshot. Complete notes and HTML projections
include the corrected planning preparation and separate wheel178 witness.
All four package checks and 659 local/static deck targets passed; ten actual
Spec notes return links reached the intended workflow table. Its local Help
overlay passed 74 tests, both drift checks, lint/types and eight conditional
canonical-publication controls. Six new captures inspect the changed planning
handoff and source disclosures. Nine routes, 17 linked responses, 22 pinned
source targets and all eight reuse claims/20 propositions passed. The earlier
126-page production build covers the d2 snapshot; the E2 correction has local
dev compilation and browser inspection only. Its final production build and
public-source disclosure inspection await accepted main.

Scoped artifact and derivative reviews are complete. Final integrated-source
acceptance and the overall pre-publication completion review remain separate
requirements. Full Windows parity stays deferred and unqualified.

### Historical four-topic preparation (metadata 1.4.0)

The following table and its wheel identities preserve the earlier preparation
checkpoint. They do not describe the later 1.5.0 walkthrough artifact.

| Canonical topic/source | Candidate evidence and disposition | Derivatives and owners | Walkthrough result and limits | Older guidance |
| --- | --- | --- | --- | --- |
| [README](../README.md), [installation](installation.md), and release notes | Draft 1.5.0 release-notes content approved; install/version instructions still describe published 1.4.0. Final candidate pins and readiness acceptance remain pending | Release documentation owner; agent-plugin instructions require the selected runtime to match | No new install, existing-tool upgrade, or migration walkthrough run during this draft | Preserve versioned 1.4.0 notes and installation evidence |
| [CLI guide](cli-guide.md), [supported journeys](supported-journeys.md), and [qualification](qualification.md) | Existing entry points checked against parser and source; platform reconciliation awaits final T8 | Release documentation owner; help projections remain separately owned | Source inspection is not a completed native command journey | Keep the historical evidence and its version labels |
| [Navigation](tutorials-1.5.0-candidate.md#navigation-an-accepted-intent) | Provisional source `677a51439cbc76a4a8726280025358e3af175d2e`, installed local wheel with metadata `1.4.0`; final release binding pending | Replacement 9-slide PPTX/HTML and existing Help `start-and-continue` projection prepared locally; publication held | Saved both literal answers, approved the complete request, reloaded and inspected accepted read-only state; no planning/build state or model call | Preserve original 1.3.0 decks/Help and [written 1.4.0 guide](tutorials-next-release-candidate.md) |
| [Specification workflow](tutorials-1.5.0-candidate.md#specification-workflow-preview-and-acceptance) | Same candidate and wheel; full current checkpoint digest used | Replacement 10-slide PPTX/HTML and existing Help `plan-and-accept` projection prepared locally | `created`, `draft`, then `accepted`; `calc.py` unchanged, no build state; starter reviewer makes no substantive judgment | Original plan/deck evidence retained |
| [Four workflows](tutorials-1.5.0-candidate.md#four-workflows-research-a-question) | Same candidate and wheel; exact example inputs and hashes retained | Replacement 12-slide PPTX/HTML and existing Help `research` projection prepared locally | Retrieval returned two sources; verification accepted one link with `result.semantic_ran: false`; repair/execution examples remain references | Original four-workflow guidance and qualification limits retained |
| [Session continuity](tutorials-1.5.0-candidate.md#session-continuity-saved-answers-in-another-session) | Same candidate and wheel; a separate synthetic draft | Replacement 10-slide PPTX/HTML and existing Help `save-and-resume` projection prepared locally | Exact saved goal survived same-page reload and fresh listener; remaining success stayed blank; unsaved text disappeared; no execution resume | Retain earlier version labels and browser observations |

The four-topic candidate review uses the local wheel SHA-256
`695dc2e8c52a25f641ec752e188ce25ae5c14fac6255881fda90e7a9bb6ddaff`.
All 107 installed Harness modules match the selected source. The installed-wheel
qualifier passed on macOS arm64, Python 3.12.14 (2,826 passed, 193 skipped).
This is candidate software evidence; it does not qualify Windows, model quality,
accessibility or user comprehension. The Help patch retains historical source
bytes and has a local build, 73 passing site tests, and checks of 17 selected
page views. Decks have 41 inspected slides across the four topics. The exact
local artifacts, hashes, checks and failed-harness explanations remain in the
private documentation review bundle; no hosted preview was created.
The broader source suite also found a deep-JSON memory-prompt hook mismatch on
this Python build, reproduced from unchanged candidate files. Its disposition
on the selected release runtimes remains open; no green full-source suite is
claimed by this documentation review.

Before publication, compare final source, dependency pins and metadata with
this candidate and rerun changed units. After publication, verify the GitHub
tag/release and live PyPI file hashes against publishing evidence and the
installed artifact, then reconcile labels and links. Passing candidate checks
does not close that final released-artifact gate.

This draft adds no version bump, tag, release, package upload, website or Help
publication, account operation, workflow dispatch, or provider call. Final
preparation and publication follow the [release runbook](release-runbook.md)
and Patrick's separate decisions.
