# Attune Harness 1.5.0 preparation readiness

**DRAFT — UNRELEASED.** Preparation snapshot: October 16, 2026. The target is
1.5.0 after full Windows parity; the runtime metadata remains `1.4.0`.
No final release SHA, 1.5.0 distribution, publication date, or release approval
is established by this record.

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
records their remaining evidence needs; it does not create a new process.

| Gate | Required evidence before a release claim | Status in this draft |
| --- | --- | --- |
| Production storage (T5/R4) | Reviewed delivered source; locking, privacy, namespace publication, complete writes and barriers; concurrency, crash/restart, replay, task, index, and CLI evidence | Current finite witnesses pass; full acceptance and the historical eight-writer busy-failure cause remain open |
| Owned-process completion and recovery | Current-source evidence for the declared child-completion and recovery contract, retaining the failing cases | Pending; PR #274 remains open |
| Native-memory acceptance (T7/R5) | Controlled production-transport acceptance, actual outcome and usage, with the existing authority and uncertainty boundaries | Pending; offline SDK evidence is separate, and an unknown prior outcome blocks redispatch |
| Native server qualification (T8) | Final combined full suite and installed journeys on Windows Server 2022/2025 with Python 3.10/3.12; required cases run rather than hidden by an OS-wide skip | Pending. In the latest [main qualification run](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39087566327), Windows 3.12 full source passed; Windows 3.10 timed out at 2,700 seconds (`exit 124`, `timeout_effects_unknown`), and qualification failed. An [earlier run of the same source tree](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39084249044) passed Windows 3.10 within the deadline; that comparison does not identify the later timeout's cause. |
| Native desktop qualification (T8) | Final installed-wheel journeys on Windows 11 with Python 3.10/3.12 under standard user permissions; OS build, architecture, and fixed local NTFS recorded separately | Pending; server or primitive evidence cannot substitute |
| Shell and documented journeys (T6/R6) | Real Windows PowerShell and PowerShell 7 commands, literal path quoting, printed continuations, preview/acceptance, completed handoffs, and recovery against the installed candidate | Pending |
| Compatibility and combined artifact (R7) | Exact final source, wheel and installed modules; dependencies and runtime; historical schema/token/receipt compatibility; required final-head reviews and regression checks | Pending; earlier wheels and component receipts retain their original identities |
| Claims and completion review (R8) | Reconcile the inventory and public platform guidance with final receipts; close the implementation completion review | Pending; this preparation review does not close full-spec completion |

Do not promote a Windows journey into the README's Qualified column from a
component pass or a diagnostic result. Final T8 must use the combined source,
including its final README; a later documentation edit can change packaged
metadata and distribution hashes.

## Documentation preparation

Use the existing [documentation readiness procedure](release-runbook.md#documentation-readiness)
for the release review and coordinate derivatives with their owners. These
notes and the [draft release notes](release-notes-1.5.0.md) prepare that review;
they are not a substitute for its walkthroughs.

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
