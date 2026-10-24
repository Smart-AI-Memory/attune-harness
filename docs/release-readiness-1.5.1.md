# Attune Harness 1.5.1 preparation readiness

**Prepared source — publication held.** This release-preparation branch
incorporates merged main `31dd4eb92f980c6bcac3867d8ac85a8423879f3a`, including
canonical Help (#299), current installation and walkthrough guidance (#300),
the Windows reader repair (#303), diagnostic compatibility (#304) and the
historical-guidance audit (#305). It updates version metadata and documentation,
coverage measurement, failure diagnostics and test supervision. Production Python
package modules, dependency pins and workflows are unchanged from that main.
The eventual reviewed merge is the release SHA. Candidate evidence cannot
replace qualification of that exact main commit or authorize publication.

## Version and scope

The package and both shared plugin manifests identify **1.5.1**, and the
changelog has its own `## 1.5.1` heading. The Claude marketplace stays pinned to
published [1.5.0](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.5.0)
until a separately approved update after the new tag exists. Dependency pins,
minimum Python and saved formats are unchanged. Recheck the PyPI version slot
and remote tag at the selected source; an earlier absence is not a reservation.

Version 1.5.1 helps users apply existing planning, building, review and saved-work
capabilities through clearer entry points and guidance. Windows users can install
Harness and use documented CLI workflows within the supported profiles. Hosted
Server 2022/2025 checks remain distinct from desktop, shell, recovery, storage and
live-provider acceptance. Richer GUI/CLI training and a new independent-user
walkthrough are follow-up work, not added 1.5.1 release requirements.

## Current candidate checks

The [release PR](https://github.com/Smart-AI-Memory/attune-harness/pull/301)
records the current head's exact commit/tree, distribution hashes, source and
installed-wheel results, native CI outcomes, skips and independent review.
Check those records against the selected head before a release decision. Each
new head requires its own applicable validation; no earlier wheel or passing
precursor schedule qualifies the combined candidate.

Main includes verified #299 and #300 merges. #299 had 29 successful checks and
one intentional profile skip; #300 had all 28 checks pass, including all eight
Windows full-source/installed cells and dynamic CodeQL. Their signed squash
trees match their tested heads. These are source-bound preparation observations,
not full Windows parity or a final 1.5.1 artifact.

The four-file audit/archive [PR #305](https://github.com/Smart-AI-Memory/attune-harness/pull/305)
is included through signed main `31dd4eb92f980c6bcac3867d8ac85a8423879f3a`.
Its earlier documentation checks remain evidence for that source. The combined
release candidate requires the exact-head validation recorded in the release PR.

Earlier #301 schedules retain separate failures: the Windows 2022/Python 3.10
eight-writer save reported three busy/not_committed callers before the final
history/replay assertions; a Windows 2025/Python 3.12 GUI build exceeded its
30-second future deadline. The bounded #306 process trace is complete and stays
draft/unmerged; the slow storage incident did not reproduce and no causal runtime
fix was established. Later passing checks do not repair those observations.
The two-second storage limit, one save per caller, eight writers, assertions and
durability barriers remain intact.

## Earlier software and documentation evidence

The following October 22 observations belong to preparation source
`0f2711b4c88ee4f231f61d71cd70a0c840be6357` and its explicitly identified local
version-overlay wheel. Their original hashes, counts, failures and limitations
remain historical evidence; they are not executions of this combined candidate.


The October 22 assessed-main [qualification run 39872982676](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39872982676)
completed successfully. All eight installed-wheel jobs, Ubuntu full-source and
all four Windows full-source jobs pass. Documentation links, classification,
CodeQL, isolated Windows effects, coverage and native-memory offline checks also
pass at this source. These are software results, not full Windows parity or live
model acceptance. No manual workflow was dispatched for this review.

The former source-suite timeout did not block the October 22 assessed main after #298.
Later selected changes still require qualification on their exact integrated
source. Do not substitute a passing branch or this local wheel for that result.

### Current documentation observations

The [1.5.1 walkthroughs](tutorials-1.5.1.md#verification-and-release-boundary)
record four newly exercised no-spend procedures on a fresh noneditable local
wheel. Its package version alone was changed to 1.5.1 in an isolated snapshot;
all 108 runtime modules match assessed source `0f2711b4c88ee4f231f61d71cd70a0c840be6357`. Wheel SHA-256:
`def6ab630dd677a346cc5ed728ee880a38927bf2e3142272071f96b168decc71`.
All 96 installed packages pass dependency compatibility checks. This local
artifact is not the accepted final 1.5.1 release candidate.

On macOS arm64/Python 3.10.11, 222 installed-wheel documentation-link,
printed-command, assessment-view and signature tests passed. The offline plan
reached acceptance with unchanged sample code; retrieval and one link check
passed with semantic checking off. Browser intake acceptance and saved-draft
reload/listener restart passed. Actual completed-assessment Markdown and HTML
inspection preserved saved-file hashes, attribution and unverified semantic
acceptance. No model calls occurred. Independent user acceptance, other browsers
and Windows shell/desktop observations remain separate.

### Completed local software checks

The full source suite passed on macOS arm64/Python 3.10.11: **5,214 passed,
238 skipped and seven subtests passed** in 643.77 seconds, with four warnings.
The noneditable validation wheel passed `scripts/qualify_platform.py`:
**2,937 passed, 197 skipped and two subtests passed** in 341.18 seconds, with
three warnings. Its receipt reports `checks_passed`, exit 0 and zero model calls;
the subsequent installed memory/R2 checks and all ten signed-plugin probe steps
passed. Platform skips retain their declared boundaries. These local results
do not replace exact-final-source CI or qualify native Windows behavior.

The disposable managed base installation separately passed
`scripts/check_installed.py --mode all`: plan, acceptance, build, review and
status completed with command/deterministic participants and zero model calls.
An initial `--mode core` invocation refused that normal dependency-bearing
installation; `core` is the deliberately dependency-free wheel profile. The
correct `all` invocation passed without a runtime change. The publish workflow
checks both profiles separately.

The final documentation-only diff passes the local link/index checker and
44 documentation-link tests. Their sandboxed run emitted one cache-write
warning. The static API-documentation command returned seven verified static
claims while explicitly leaving runtime behavior unchecked.

The PyPI environment was read without mutation: only `main` is permitted and
Patrick remains the required reviewer. Trusted-publisher configuration and an
actual upload were not exercised by this review.

### Historical software evidence on the earlier source

[Library qualification run 39786227278](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39786227278)
ran on the earlier assessed source and completed with failure.

| Check | Observed result | Claim boundary |
| --- | --- | --- |
| Eight installed-wheel jobs: macOS, Ubuntu, Windows Server 2022/2025, Python 3.10/3.12 | Passed | Only the selected tests and artifacts from this run |
| Ubuntu/Python 3.10 full source suite | Passed | This source/runtime combination |
| Windows full source suites: Server 2022/Python 3.10 and 3.12; Server 2025/Python 3.10 | Passed | These three source/runtime combinations |
| [Server 2025/Python 3.12 full source suite](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39786227278/job/119850108502) | Timed out after 2,700 seconds; receipt reports `timeout_effects_unknown`, exit 124 | Earlier cause unresolved in that receipt; the October 22 assessed source passed after #298 |
| Documentation links and change classification | Passed | Link resolution and classification, not walkthrough correctness |
| Required aggregate Qualification | Failed | Gate was closed for that earlier source; the October 22 assessed-source result is above |

The same source passed
[supplemental coverage](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39786227398),
[isolated Windows effects](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39786227288),
[native-memory offline SDK](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39786227318)
and [CodeQL](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39786226259).
Those results do not replace required qualification or qualify live model use.
No workflow was dispatched or rerun for this assessment.

### Earlier documentation validation

On macOS/Python 3.10.11, 204 focused documentation-link, assessment-presentation
and plugin-signature tests passed. The repository link/index check and strict
Twine check also passed. A disposable noneditable wheel installation supplied
the isolated CLI subprocess; its three changed runtime modules matched the
assessed source bytes. The environment reused local dependencies. This wheel
still identifies as 1.5.0 and is not the published 1.5.0 wheel or a final 1.5.1 artifact.

The first local invocation reported one missing-package subprocess failure and
48 GPG-fixture setup errors. The installed environment and a rerun permitting
scratch GPG-agent startup passed all 204 checks without source changes. These
focused checks do not replace the full suite, final installed-wheel
qualification, native Windows results or the pending walkthrough review.

## Documentation preparation


The following record follows the [release runbook](release-runbook.md#documentation-readiness).
Source and test references establish what the prose describes; final-candidate
execution, derivative coordination and released-artifact checks remain separate.

| Topic | Source and check | Disposition | Derivatives and owner | Result and remaining limits | Older guidance |
| --- | --- | --- | --- | --- | --- |
| README, installation and workflow selection | Assessed package metadata, [installation guide](installation.md), [workflow selector](supported-journeys.md) | Changed: distinguish published 1.5.0 from planned 1.5.1 | Help Center installation and integration topics: coordinate with existing website owner; update pending | Published 1.5.0 remains available; local 1.5.1 validation wheel exercised; final artifact and later index-install checks remain separate | 1.5.0 release record retained |
| Completed-assessment inspection | [Renderer](../src/attune_harness/assessment_view.py), [CLI owner](../src/attune_harness/task_cli.py), [owner tests](../tests/test_assessment_view.py) | Changed: label 1.5.1-only presentation and give inspection commands | Evidence-review help topic and related walkthroughs: owner coordination pending | Recorded outcomes, attribution and source identities checked against code; local candidate Markdown/HTML commands pass without saved-file changes; final-artifact reconciliation and human acceptance remain pending | Published 1.5.0 generic rendering identified explicitly |
| Signed-plugin verification | [Verifier](../src/attune_harness/plugin_signing.py), [regression tests](../tests/test_plugin_signing.py), [design](design-plugin-signature-input.md) | Changed: explain exact validated bytes and malformed-envelope refusals | No separate plugin-training derivative identified in this review | Source-reviewed behavior; October 22 assessed-source installed-wheel jobs pass; final artifact and full qualification pending | September signature findings and receipts preserved |
| Pause and return | [CLI procedure](cli-guide.md#pause-and-return-to-work), [printed-command tests](../tests/test_cold_start_journey.py) | Merged #296 retains raw Windows paths and stopping-note/report/handoff steps | Canonical Help is merged; website delivery remains with its owner | One assisted text walkthrough remains distinct from independent return and GUI acceptance | Earlier session-continuity observations retain their identities |
| Four training walkthroughs | [Current 1.5.1 procedures](tutorials-1.5.1.md), [1.5.0 preparation procedures](tutorials-1.5.0-candidate.md), [historical 1.3.0 procedures](tutorials-1.3.0.md) | Four local 1.5.1 procedures exercised; earlier observations retain their original source/artifact | Help, HTML tutorials and decks: coordinate with existing content owner | Four procedures pass on the explicitly version-overlay validation wheel; final release identity and actual derivative integration remain pending | Existing versioned procedures retained |
| Windows capability and reliability limits | [Reliability reference](windows-reliability.md), [approved task checkpoint](specs/windows-parity/tasks.md) | Reviewed for scope; existing limits retained | Windows help and shell/desktop procedures: existing owners; qualification pending | Maintenance changes do not establish full parity, storage or process recovery | 1.5.0 preparation record remains historical |

### Current reference review

At the October 22 assessment source `0f2711b4`, the runtime diff from released 1.5.0 contained only `assessment_view.py`,
`plugin_signing.py` and `task_cli.py`. Other instructions were checked for stale
setup, contradictory capability claims and release status; their retained
software evidence is not a fresh model or external-service campaign.

| Current pages | Review disposition and evidence boundary |
| --- | --- |
| [Index](README.md), [workflow selector](supported-journeys.md), [project checkpoint](project-plan.md), [opportunity register](opportunity-log.md), [documentation maintenance](documentation-maintenance.md) | Updated entry points and 1.5.1 status. Register now distinguishes merged assessment, continuation and signature fixes from remaining slices. Versioned designs and earlier release records stay dated. |
| [Installation](installation.md), [memory guidance](memory-saving.md), [current walkthroughs](tutorials-1.5.1.md) | Updated and exercised on the explicitly identified local wheel. A private managed-tool installation selected 1.5.1, exposed its interpreter and passed the deterministic module example; existing user tools were not replaced. |
| [CLI guide](cli-guide.md), [operations](operations.md), [model consultation](model-consultation.md), [signed plugins](executable-plugin-run.md) | Reviewed current command and authority boundaries. The completed-assessment commands were exercised with synthetic participants; signature regressions passed. No live consultation, paid call or plugin deployment was performed. Published 1.5.0 commands and versioned examples retain their labels. |
| [Local verification](local-workflow.md), [review](review-workflow.md), [recovery](recovery-workflow.md), [extensions](extension-workflow.md), [pilot](pilot-workflow.md), [passage review](passage-review.md) | Corrected current setup pointers and labeled old development wheels/environments. Existing review/recovery contracts stay bounded; the retained local-model completion and quality measurements were not rerun or promoted to current qualification. |
| [MCP](mcp-workflow.md), [A2A](a2a-workflow.md), [portable contract](portable-contract.md) | Corrected interpreter guidance and the obsolete “no implementation” protocol row. Local stdio/loopback contracts and independent-peer evidence remain distinct from remote authentication, cross-machine ownership and general interoperability. |
| [Code retrieval](code-first-rag.md), [Voyage retrieval](voyage-retrieval.md), [code-grounded documentation](documentation-workflow.md) | Corrected obsolete development-version/setup language and removed-extra instructions. Base static documentation behavior was reviewed against its owner and tests; no model callback, Voyage request, index rebuild or retained campaign was executed. |
| [Codex plugin](codex-plugin.md), [compatibility](compatibility.md), [envelopes](envelopes.md), [migration](migration-from-attune-ai.md) | Reviewed unchanged versioned contracts. The October 22 local Codex observation reported 0.153.4, matching the explicitly scoped plugin instructions. No host registration, plugin installation, migration campaign or wider desktop qualification occurred. |
| [Qualification](qualification.md), [coverage](coverage-measurement.md), [Windows reliability](windows-reliability.md), [Windows task checkpoint](specs/windows-parity/tasks.md) | Reviewed software-versus-capability claims against the October 22 assessed-source hosted matrix. Component success does not close deferred Windows recovery/storage, live-provider, desktop/shell or human-observation gates. |
| [Earlier journey map](release-journey-map.md), [readiness direction](harness-release-readiness-direction.md) | Historical absence claims now point to delivered plan/build guidance. Original measurements, frozen designs, receipts, wheels and model artifacts were preserved. |
| [Guidance examples](user-guidance-examples.md), [controls article](blog/controls-savings-user-journey.md) | Reviewed as dated proposed copy and an unpublished editorial draft. Reported 16-attempt comparison, replay controls and 21-call contaminated trial remain consistent with their linked result summaries. Raw unavailable receipts were not independently replayed; no customer savings or publication is claimed. This separate article still requires its own content approval. |

### Help and training ownership

The canonical Help source from
[PR #299](https://github.com/Smart-AI-Memory/attune-harness/pull/299) is merged
as signed `013b84a6d1984f388df41452299ddacc90bb5f5b`, with a tree equal to
its tested `3073eb4a` head. It retains the reviewed documentation pin
`0dc82db327af9eae41f7bf812480cc76d2cd7fc7`; original behavior, tutorial and
observation identities are unchanged.
The website cutover is
[PR #2574](https://github.com/Smart-AI-Memory/attune-ai/pull/2574), followed by
the surrounding entry points in
[PR #2575](https://github.com/Smart-AI-Memory/attune-ai/pull/2575).
The named owners agreed to preserve the goals route, prominent landing link,
learning-first compact navigation, 21 goal accordions, six testing FAQs and
local unapproved worksheet. The website entry-point PR must drop its duplicate
Help implementation after the canonical export is reviewable. The website PRs remain separate
drafts; final website integration, source pins, drift/build/link checks and
publication approval remain required. Independent browser review found the spec worksheet outside
its collapsed topic in the first port. Corrected Help source
`295230ac53d601c9a2539020a3f5be7044cc7559` preserves worksheet ownership and
all six testing FAQs inside their topic; the renderer now rejects broken nesting
and missing resources. Its 12-page export, compact link, worksheet choices,
reset and exact clipboard copying were checked in the browser. This does not
substitute for the final website rewrite/import checks.

Website #2575's `when-green` run 39880319742 failed with HTTP 401 at its
metadata API call, while build/test/preview checks passed. Credential repair
remains a website administration action, separate from Harness package CI and
PyPI's OIDC environment. A prepared guide is not a production deployment.

Existing 1.3.0/1.4.0 training pages, decks and HTML captures remain explicitly
historical. The four current procedures are in `tutorials-1.5.1.md`; no current
deck projection has been generated or qualified. Preserve each older artifact's
source identity rather than relabeling it as 1.5.1.

The repository writing guide and approved policy apply. Google's
[documentation style guide](https://developers.google.com/style) was checked on
October 22, 2026. Links and software tests support this review; they do not
establish user comprehension or semantic acceptance of participant judgments.
Package preparation does not deploy Help Center, tutorial or deck updates.

## Required before publication

1. Select the complete source, reconcile accepted dependencies through main and
   pass the final candidate checks. Preserve failures and older evidence under
   their original identities; no runtime or assertion weakening follows.
2. Review the metadata, changelog, README, current migration guidance and affected
   walkthroughs against that candidate. Package and plugin versions must agree;
   the marketplace stays at 1.5.0 until the new tag exists. Close Help/tutorial/deck
   dispositions with their existing owners or retain an explicit approved older
   version. Software checks do not establish user comprehension.
3. Build and validate distributions, install the actual wheel and run the required
   installed checks. After the preparation PR merges, require successful
   push-to-main qualification for that exact release SHA.
4. Obtain separate authorization for the build-only `publish-pypi.yml` rehearsal
   from main with `publish=false`. Inspect its release gate and distributions;
   local builds and branch CI do not substitute for that post-merge rehearsal.
5. Recheck PyPI/tag availability and obtain Patrick's separate publication go.
   Patrick approves the PyPI environment himself. Verify both published files
   against the publishing run, then follow separately authorized signed tag,
   GitHub release and marketplace-update steps.

The deferred full Windows parity, process stop/recovery, saved-store acceptance,
historical eight-writer cause, live native-memory, Windows 11 standard-user desktop,
shell and human-observation requirements remain open with their existing owners.
No new parity, migration, training or independent-user campaign is added here.
Publication, PR merges and manual workflow dispatch remain held.
