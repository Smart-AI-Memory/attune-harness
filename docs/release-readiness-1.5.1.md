# Attune Harness 1.5.1 preparation readiness

**Prepared — publication held.** This record accompanies the final 1.5.1
release-preparation PR, based on merged main
`5fca534972ac3904c6aa92a0a0fd89e7cf9ba4a9`. The PR changes version metadata,
documentation and Windows dangling-target ancestor validation. Dependencies and
saved formats remain unchanged.
Its **Verified** section records the actual preparation commit, built artifacts,
local results and current CI. The eventual reviewed merge is the release SHA;
this document does not substitute a precursor SHA for it or authorize publication.

## Version and scope

The package and both shared plugin manifests identify **1.5.1**. The changelog has
its own `## 1.5.1` heading. The Claude marketplace remains pinned to published
[1.5.0](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.5.0), source
`7caa86ab6d476e9599b08ff75a81bc816e60c382`, until a separately approved catalog
update after the new tag exists. Dependency pins and minimum Python remain
unchanged; no dependency-lock regeneration is required.

The changes since 1.5.0 include exact plugin-signature input (#289), completed
assessment evidence (#292), browser timeout diagnostics (#288), installation and
workflow guidance (#290), local documentation-link validation (#291), bounded
refusal-continuation checks (#293, #295), 1.5.1 guidance (#297), Windows full-suite
partitioning (#298) and the pause-and-return documentation and native-path fix
(#296), plus the bounded Windows raw-memory target-walk repair in #301. See the
[release notes](release-notes-1.5.1.md) for user-visible changes.

A live [PyPI metadata](https://pypi.org/pypi/attune-harness/json) check on October 22,
2026, reported latest 1.5.0 and no 1.5.1 release entry. Recheck both the version slot
and remote tag immediately before any authorized outward step. Availability is
not a reservation. Index-install commands select 1.5.1 only after publication;
README links to the new tag become available when that release is created.

## Windows use and the release boundary

Windows users can install Harness and use its documented CLI workflows within
the supported profiles. The Windows implementations include captured test
execution, native file-memory reads, saved memory and task storage, and
experimental native-memory transport. The
[capability table](supported-journeys.md#windows-capabilities-and-reliability)
connects these capabilities to their process, storage and recovery requirements.

The hosted software matrix exercises Windows Server 2022 and 2025 with Python
3.10 and 3.12. The evidence below identifies the source and artifacts each
result qualifies. Full Windows parity and the remaining desktop, shell,
recovery, storage and live-provider acceptance work retain their stated limits
and owners; users should select a workflow using its documented profile.

## Software evidence and its limits

The combined precursor is #296 head
`d9cb0a7ed7fe763af313556921c5fc4bc820d968`. Its tree and merged main `5fca534`
are identical: `475068962e3b529f066615bbaf94c5a3ef49db9a`.

| Evidence | Observed result | Boundary |
| --- | --- | --- |
| [Library qualification 39884922177](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39884922177) | All eight installed-wheel cells, all four Windows full-source cells, Ubuntu full-source, documentation links and aggregate Qualification passed | Combined precursor software and 1.5.0-metadata wheels; not a final 1.5.1 artifact |
| [Supplemental coverage](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39884922137), [offline SDK](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39884922225) and CodeQL on that head | All passed; 28 checks total succeeded with none pending or failed | No live model-quality or full native-journey acceptance claim |
| [Previously failing Server 2025/Python 3.12 wheel cell](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39884922177/job/120190776214) | Both unchanged Node fixtures ran and passed without skips: 5.374s and 1.535s | Earlier startup/exit delay cause remains unknown; later success does not alter the failed receipt |
| Final 1.5.1 preparation | Commit, focused/full local results, distributions, installed qualification and current native CI recorded in the release PR | A candidate wheel is not a published artifact; PR CI does not replace required push-to-main qualification after merge |

The original [Windows timeout](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39786227278)
and subsequent failed partition attempts retain their original source and
outcomes. #298 introduced complete-case verification and isolated system-temporary
namespaces, with four passing Windows source cells, without increasing deadlines
or weakening assertions. The [design](design-windows-source-suite-shards.md) and
[qualification guide](qualification.md) explain the proof and its limits.
The original #296 path failures, Node timeouts and local environment/GPG setup
failures also remain retained; fresh evidence is added beside them.

The first #301 candidate's [Server 2022/Python 3.10 source cell](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39891752523/job/120212928695)
failed a dangling-target absence case with `Symbolic-link target namespace
changed`, despite missing before/after Windows stat witnesses and zero content
reads. Controlled regressions reproduce that refusal through unrelated ancestor
changes; the historical receipt does not identify which ancestor or field changed.
The repair binds selected ancestor names and identities between observations,
preserving strict missing-parent, link, scan and unsafe-access guards. Its current
source review, local verification and native CI results belong to the PR; the
earlier failure remains evidence rather than becoming a passing receipt.

## Documentation readiness

This record follows the [release runbook](release-runbook.md#documentation-readiness)
and [writing guide](writing-guide.md). The approved policy revision is
`e6e53f6a092deb4536b63bc8609c2453a20e5a53`. Source-bound software checks and
human observations remain separate. Review results and artifact hashes belong
to the preparation PR's evidence; final-source and post-publication checks remain
explicit gates below.

| Canonical topic | Candidate disposition and source/test evidence | Derivatives and owner disposition | Walkthrough and older-guidance boundary |
| --- | --- | --- | --- |
| [README](../README.md), [installation](installation.md) and [workflow selection](supported-journeys.md) | Changed for 1.5.1: metadata-aligned commands, conditional index installation, release-tag documentation links and current workflow entry points; package/plugin and installed CLI checks in the release PR | Existing website owner: Help Center installation/integration update or explicit retained-version disposition remains pending; no website publication in this PR | New tag and index URLs are expected to be unavailable before release. The linked Help Center 1.5.0 page is labeled earlier-version guidance |
| [Completed-assessment inspection](cli-guide.md#inspect-completed-assessment-evidence-151-candidate) | Reviewed for 1.5.1 against [renderer](../src/attune_harness/assessment_view.py), [CLI owner](../src/attune_harness/task_cli.py) and [tests](../tests/test_assessment_view.py); this preparation changes no command syntax | Existing evidence-review help/walkthrough owner: derivative reconciliation or explicit disposition remains pending | Recorded checker results, attribution and source identities are software-checked; semantic acceptance and fresh user observation remain open |
| [Signed-plugin verification](design-plugin-signature-input.md) | Reviewed for 1.5.1 against [verifier](../src/attune_harness/plugin_signing.py) and [regressions](../tests/test_plugin_signing.py); final installed qualification exercises the shipped owner | No separate training derivative identified; no new publication inferred | Older signature findings and receipts retain their original identities; cooperating extensions are not an OS sandbox |
| [Pause and return](cli-guide.md#pause-and-return-to-work) | Changed in #296; reviewed raw Windows path literals and printed commands against [cold-start tests](../tests/test_cold_start_journey.py), including both native-path controls | Session Continuity topic owner: record the corrected procedure before a derivative update; external coordination is pending | One assisted text walkthrough is retained. Original pause context, independent return, HTML controls, S6 and complete Task 1 acceptance remain open |
| Four training procedures: [1.5.0 candidate](tutorials-1.5.0-candidate.md), [historical 1.3.0](tutorials-1.3.0.md) | Procedure/example bodies are unchanged by this preparation; retain their source/interpreter requirements. Candidate software checks do not relabel their older executions | Existing owner for help, HTML tutorials and decks: candidate reconciliation or explicit retained-version disposition remains pending; no derivative was republished | Keep the existing versioned sources and observations. No new 1.5.1 browser, non-programmer or training-walkthrough acceptance is claimed |
| [Windows reliability](windows-reliability.md) and [task checkpoint](specs/windows-parity/tasks.md) | Existing limits reviewed and retained; new partition checks qualify only their actual server/software cells | Existing Windows help/shell/desktop owners retain their acceptance work | Full storage, process recovery, live-provider, Windows 11 desktop and shell parity are not established by this maintenance release |

Local link/index and README-rendering checks support this review. They do not
establish a correct remote publication, semantic acceptance or user comprehension.
External content-owner coordination remains a publication decision; this PR
records the pending dispositions without sending messages or deploying content.

## Required before publication

1. Review and merge the preparation PR, then require successful Library
   qualification from the push to that exact main SHA. Preserve its candidate
   artifacts, source binding and actual outcomes; recheck main before dispatch.
2. Complete affected command walkthrough checks against that candidate and close
   the pending official-help/tutorial/deck dispositions with their existing
   owners, or record an explicit approved retained-version disposition. Keep
   older guidance versioned; do not promote software checks into human acceptance.
3. Obtain separate authorization for the build-only `publish-pypi.yml` rehearsal
   from main with `publish=false`. Inspect the resulting release gate and
   distributions before seeking publication approval. No rehearsal was dispatched
   by this preparation.
4. Recheck PyPI/tag availability and obtain Patrick's separate publication go.
   Patrick approves the PyPI environment himself. Verify both published files
   against the publishing run, then follow separately authorized signed tag,
   GitHub release and marketplace-update steps.

The deferred full Windows parity, process stop/recovery, saved-store acceptance,
historical eight-writer cause, live native-memory, Windows 11 standard-user
desktop, shell and human-observation requirements remain open. This preparation
neither expands their claims nor changes their existing acceptance owners.
