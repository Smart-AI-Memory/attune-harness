# Attune Harness 1.5.1 preparation readiness

**Draft — unpublished.** Assessed on October 22, 2026, at
`0f2711b4c88ee4f231f61d71cd70a0c840be6357`, current `main` for this review.
Version 1.5.1 is proposed for the merged maintenance changes in the
[release notes](release-notes-1.5.1.md). This record does not accept a final
release SHA or artifact and does not authorize publication.

## Version and scope

The current published version is
[1.5.0](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.5.0),
from `7caa86ab6d476e9599b08ff75a81bc816e60c382`. A live
[PyPI metadata](https://pypi.org/pypi/attune-harness/json) check on October 22
reported 1.5.0 as latest and no 1.5.1 version. The remote v1.5.1 tag was absent.
Check both again before release; availability at assessment time is not a reservation.

Eleven merged commits follow the 1.5.0 source. They include the plugin-signature
input fix (#289), completed-assessment presentation (#292), documentation and
browser-test diagnostics (#288, #290), broader documentation link checks (#291)
and bounded refusal-continuation tests and follow-through (#293, #295).
Other commits update the released Claude catalog (#287), agent collaboration guidance (#276), release preparation (#297) and verified Windows source-suite partitions (#298). No dependency-pin, minimum-Python or saved-state
format change appears in this diff.

This preparation changes documentation. Package and both plugin manifests
remain at 1.5.0, and the Claude marketplace remains pinned to that released tag.
The version bump and final changelog heading belong to final candidate preparation.
Open PRs #294, #296 and #299 were not included in this assessed source; any later
change needs its own scope and evidence reconciliation.

## Current software evidence

The exact current-main [qualification run 39872982676](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39872982676)
completed successfully. All eight installed-wheel jobs, Ubuntu full-source and
all four Windows full-source jobs pass. Documentation links, classification,
CodeQL, isolated Windows effects, coverage and native-memory offline checks also
pass at this source. These are software results, not full Windows parity or live
model acceptance. No manual workflow was dispatched for this review.

The former source-suite timeout is no longer a current-main blocker after #298.
Later selected changes still require qualification on their exact integrated
source. Do not substitute a passing branch or this local wheel for that result.

### Current documentation observations

The [1.5.1 walkthroughs](tutorials-1.5.1.md#verification-and-release-boundary)
record four newly exercised no-spend procedures on a fresh noneditable local
wheel. Its package version alone was changed to 1.5.1 in an isolated snapshot;
all 108 runtime modules match current main. Wheel SHA-256:
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
| [Server 2025/Python 3.12 full source suite](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39786227278/job/119850108502) | Timed out after 2,700 seconds; receipt reports `timeout_effects_unknown`, exit 124 | Earlier cause unresolved in that receipt; superseded by current-main pass after #298 |
| Documentation links and change classification | Passed | Link resolution and classification, not walkthrough correctness |
| Required aggregate Qualification | Failed | Gate was closed for that earlier source; current-main result is above |

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
| Signed-plugin verification | [Verifier](../src/attune_harness/plugin_signing.py), [regression tests](../tests/test_plugin_signing.py), [design](design-plugin-signature-input.md) | Changed: explain exact validated bytes and malformed-envelope refusals | No separate plugin-training derivative identified in this review | Source-reviewed behavior; current-main installed-wheel jobs pass; final artifact and full qualification pending | September signature findings and receipts preserved |
| Four training walkthroughs | [Current 1.5.1 procedures](tutorials-1.5.1.md), [1.5.0 preparation procedures](tutorials-1.5.0-candidate.md), [historical 1.3.0 procedures](tutorials-1.3.0.md) | Four local 1.5.1 procedures exercised; earlier observations retain their original source/artifact | Help, HTML tutorials and decks: coordinate with existing content owner | Four procedures pass on the explicitly version-overlay validation wheel; final release identity and actual derivative integration remain pending | Existing versioned procedures retained |
| Windows capability and reliability limits | [Reliability reference](windows-reliability.md), [approved task checkpoint](specs/windows-parity/tasks.md) | Reviewed for scope; existing limits retained | Windows help and shell/desktop procedures: existing owners; qualification pending | Maintenance changes do not establish full parity, storage or process recovery | 1.5.0 preparation record remains historical |

### Current reference review

The runtime diff from released 1.5.0 contains only `assessment_view.py`,
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
| [Codex plugin](codex-plugin.md), [compatibility](compatibility.md), [envelopes](envelopes.md), [migration](migration-from-attune-ai.md) | Reviewed unchanged versioned contracts. Local Codex still reports 0.153.4, matching the explicitly scoped plugin instructions. No host registration, plugin installation, migration campaign or wider desktop qualification occurred. |
| [Qualification](qualification.md), [coverage](coverage-measurement.md), [Windows reliability](windows-reliability.md), [Windows task checkpoint](specs/windows-parity/tasks.md) | Reviewed software-versus-capability claims against the current successful hosted matrix. Component success does not close deferred Windows recovery/storage, live-provider, desktop/shell or human-observation gates. |
| [Earlier journey map](release-journey-map.md), [readiness direction](harness-release-readiness-direction.md) | Historical absence claims now point to delivered plan/build guidance. Original measurements, frozen designs, receipts, wheels and model artifacts were preserved. |
| [Guidance examples](user-guidance-examples.md), [controls article](blog/controls-savings-user-journey.md) | Reviewed as dated proposed copy and an unpublished editorial draft. Reported 16-attempt comparison, replay controls and 21-call contaminated trial remain consistent with their linked result summaries. Raw unavailable receipts were not independently replayed; no customer savings or publication is claimed. This separate article still requires its own content approval. |

### Help and training ownership

The canonical Help source is being prepared in Harness
[PR #299](https://github.com/Smart-AI-Memory/attune-harness/pull/299).
The website cutover is
[PR #2574](https://github.com/Smart-AI-Memory/attune-ai/pull/2574), followed by
the surrounding entry points in
[PR #2575](https://github.com/Smart-AI-Memory/attune-ai/pull/2575).
The named owners agreed to preserve the goals route, prominent landing link,
learning-first compact navigation, 21 goal accordions, six testing FAQs and
local unapproved worksheet. The website entry-point PR must drop its duplicate
Help implementation after the canonical export is reviewable. These are open
drafts; final integration, source pins, drift/build/link checks and release gating
remain required. Independent browser review found the spec worksheet outside
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

1. Select the final source and obtain its passing required qualification.
   Current main passes after #298; the older timeout is retained above.
   Reconcile any additional selected PRs and retain their failures separately.
   Workflow reruns require authorization.
2. Set the package and both plugin manifests to the final version, add its
   changelog heading, review README claims and pin its documentation links to
   the release tag or an existing reviewed revision. Reconcile later changes
   with these notes. Keep the marketplace at 1.5.0 until the new tag exists.
3. Reconcile the observed walkthroughs with the final source; rerun affected
   procedures if their inputs or behavior change. Finish the actual Help/website
   integration and confirm tutorial/deck dispositions with their owners. Record the candidate source, artifact,
   observed results and explicitly retained older guidance.
4. Build and validate distributions, install the wheel and run the required
   installed checks. After the preparation PR merges, verify exact-main CI and
   obtain authorization for the build-only release-workflow rehearsal.
5. Follow the runbook's separately gated publication, PyPI-byte verification,
   tag/release creation and subsequent marketplace update. Recheck version and
   tag availability at the selected source. Publication and merge remain Patrick's.

The deferred full Windows parity, process stop/recovery, saved-store acceptance,
historical eight-writer cause, live native-memory, Windows 11 standard-user desktop,
shell and user-observation requirements remain open. Preserve earlier receipts;
add evidence beside them rather than rewriting their identities or outcomes.
