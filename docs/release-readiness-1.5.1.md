# Attune Harness 1.5.1 preparation readiness

**Draft — unpublished.** Assessed on October 22, 2026, at
`0f3c3c0afd33eca6045b7aada242cab490cf1971`, then the current `main`.
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

Nine merged commits follow the 1.5.0 source. They include the plugin-signature
input fix (#289), completed-assessment presentation (#292), documentation and
browser-test diagnostics (#288, #290), broader documentation link checks (#291)
and bounded refusal-continuation tests and follow-through (#293, #295).
The remaining commits update the released Claude catalog (#287) and agent
collaboration guidance (#276). No dependency-pin, minimum-Python or saved-state
format change appears in this diff.

This preparation changes documentation. Package and both plugin manifests
remain at 1.5.0, and the Claude marketplace remains pinned to that released tag.
The version bump and final changelog heading belong to final candidate preparation.
Open PRs #294 and #296 were not included in this assessed source; any later
change needs its own scope and evidence reconciliation.

## Current software evidence

[Library qualification run 39786227278](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39786227278)
ran on the assessed source and completed with failure.

| Check | Observed result | Claim boundary |
| --- | --- | --- |
| Eight installed-wheel jobs: macOS, Ubuntu, Windows Server 2022/2025, Python 3.10/3.12 | Passed | Only the selected tests and artifacts from this run |
| Ubuntu/Python 3.10 full source suite | Passed | This source/runtime combination |
| Windows full source suites: Server 2022/Python 3.10 and 3.12; Server 2025/Python 3.10 | Passed | These three source/runtime combinations |
| [Server 2025/Python 3.12 full source suite](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39786227278/job/119850108502) | Timed out after 2,700 seconds; receipt reports `timeout_effects_unknown`, exit 124 | Cause unresolved; no passing complete-suite result |
| Documentation links and change classification | Passed | Link resolution and classification, not walkthrough correctness |
| Required aggregate Qualification | Failed | Publication gate remains closed |

The same source passed
[supplemental coverage](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39786227398),
[isolated Windows effects](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39786227288),
[native-memory offline SDK](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39786227318)
and [CodeQL](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39786226259).
Those results do not replace required qualification or qualify live model use.
No workflow was dispatched or rerun for this assessment.

### Documentation validation

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
| README, installation and workflow selection | Assessed package metadata, [installation guide](installation.md), [workflow selector](supported-journeys.md) | Changed: distinguish published 1.5.0 from planned 1.5.1 | Help Center installation and integration topics: coordinate with existing website owner; update pending | Existing 1.5.0 install commands retained; fresh 1.5.1 index installation unavailable before publication | 1.5.0 release record retained |
| Completed-assessment inspection | [Renderer](../src/attune_harness/assessment_view.py), [CLI owner](../src/attune_harness/task_cli.py), [owner tests](../tests/test_assessment_view.py) | Changed: label 1.5.1-only presentation and give inspection commands | Evidence-review help topic and related walkthroughs: owner coordination pending | Recorded outcomes, attribution and source identities checked against code; final-candidate command reproduction and human acceptance pending | Published 1.5.0 generic rendering identified explicitly |
| Signed-plugin verification | [Verifier](../src/attune_harness/plugin_signing.py), [regression tests](../tests/test_plugin_signing.py), [design](design-plugin-signature-input.md) | Changed: explain exact validated bytes and malformed-envelope refusals | No separate plugin-training derivative identified in this review | Source-reviewed behavior; current-main installed-wheel jobs pass; final artifact and full qualification pending | September signature findings and receipts preserved |
| Four training walkthroughs | [1.5.0 preparation procedures](tutorials-1.5.0-candidate.md), [historical 1.3.0 procedures](tutorials-1.3.0.md) | Pending candidate review; existing observations retain their original source/artifact | Help, HTML tutorials and decks: coordinate with existing content owner | Not rerun against a 1.5.1 artifact; no 1.5.1 walkthrough or derivative acceptance claimed | Existing versioned procedures retained |
| Windows capability and reliability limits | [Reliability reference](windows-reliability.md), [approved task checkpoint](specs/windows-parity/tasks.md) | Reviewed for scope; existing limits retained | Windows help and shell/desktop procedures: existing owners; qualification pending | Maintenance changes do not establish full parity, storage or process recovery | 1.5.0 preparation record remains historical |

The repository writing guide and approved policy apply. Google's
[documentation style guide](https://developers.google.com/style) was checked on
October 22, 2026. Links and software tests support this review; they do not
establish user comprehension or semantic acceptance of participant judgments.
Package preparation does not deploy Help Center, tutorial or deck updates.

## Required before publication

1. Resolve or establish the cause of the Windows source-suite timeout and obtain
   passing required qualification for the selected final source. A presumed
   runner flake is not a passing check. Workflow reruns require authorization.
2. Set the package and both plugin manifests to the final version, add its
   changelog heading, review README claims and pin its documentation links to
   the release tag or an existing reviewed revision. Reconcile later changes
   with these notes. Keep the marketplace at 1.5.0 until the new tag exists.
3. Complete affected walkthrough checks and coordinate the actual help/tutorial/
   deck dispositions with their owners. Record the candidate source, artifact,
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
