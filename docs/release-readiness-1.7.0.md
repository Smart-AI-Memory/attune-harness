# Harness 1.7.0 readiness record

Status: **release preparation, unpublished**. Software preparation #338 merged
at `9ecefe8a0fded05b1bb55b2f81d8579725666666`; its exact-main qualification and
build-only rehearsal passed. The documentation follow-up is a separate local
draft for review. Its changed source and artifacts require their own checks;
the earlier rehearsal does not qualify new changes. Publication, tagging,
GitHub release, marketplace updates and website delivery remain separate gates.
See the [release notes](release-notes-1.7.0.md) and [runbook](release-runbook.md).

This record supplies evidence and remaining decisions. It grants no merge,
publication, workflow dispatch or deployment authority.

## Source and compatibility

The initial preparation started from verified main
`4d0b7ff9690f74ebfe9f864159cf06abc0266440`, after #337 merged. GitHub reported the
merge on November 4, 2026. Its tree
`2fa146afd2aff86ebe7f21cadafa4eb460144ae2` exactly matches checked head
`fee8dd4f29f18c59ae26eb7e4f6c6e17dfe5dd25`.
The release PR records the full prepared commit, independent review, candidate
artifact hashes and exact run results. The resulting squash SHA and its independent checks appear below. Any later
source or distribution change requires new qualification; earlier green checks
do not qualify new source or distributions.

Package metadata and the two coupled `plugin/attune-harness` manifests select
1.7.0. The independent Codex package remains 0.1.0. The live Claude marketplace
stays pinned to released 1.6.0; its post-publication update is not part of this PR.

Legacy command environment inheritance remains accepted. Only its removal
schedule changes: first notice 1.6.0, earliest removal postponed from 1.7.0 to
1.8.0. Runtime and register agree. Existing compatibility, warning, presentation,
replay and overdue-deprecation checks remain required. Historical records are
preserved, including the original 1.6.0 schedule.

## Candidate validation

Focused/full source suites, distribution build and strict metadata checks,
installed-wheel core/platform qualification and separate explicit optional-extra
qualification are required for this candidate. Results, failures, skips and
artifact identities are recorded in the release PR as they complete. A pending
or skipped check is not a pass. No paid provider request, account sign-in,
Keychain mutation or production Redis mutation is included.

Reviewed source: `1fe75ad6f0c1292e69dbe5b3df93a36a8378fad3`. Later review and
evidence edits are documentation-only; the PR records their commit identities.
Local results below use macOS arm64 / CPython 3.12.2 and fresh environments.

| Check | Actual result |
| --- | --- |
| Focused release/funding/environment checks | 355 passed, no skips; one existing Authlib deprecation warning |
| Complete source suite, explicit optional dependencies installed | 6,723 passed, 232 skipped, seven additional passing subtests; zero failures/errors |
| Standard `voyage,redis` installed-wheel qualification | Passed: 4,134 passed, 216 skipped, two additional passing subtests; post-suite memory/R2 and all ten plugin-probe steps passed; zero model calls |
| `voyage,redis,plan-oauth` installed-wheel qualification | Passed: 4,146 passed, 204 skipped, two additional passing subtests; post-suite memory/R2 and all ten plugin-probe steps passed; zero model calls |
| Additional installed OAuth/profile/worker checks | 112 passed, no skips; real local signing keys and inert transports, no provider calls |
| Broader installed profile also including `memory-native` | Failed qualification: 4,165 selected tests passed, 185 skipped and two passing subtests; the provider-SDK absence guard then failed. Post-suite R2/memory checks were not completed |
| Distribution, static and installation checks | Wheel/sdist build, strict Twine checks, dependency consistency, Ruff 0.14.4, documentation links/index and local static Help build passed. All 130 runtime files matched source, wheel and installed profiles |
| Minimal and normal installed CLI checks | Fresh no-dependency core and standard `all` checks passed; installed plan/accept/build/review/status completed with zero model calls |
| Independent review | Configured GPT-6.1 Sol approved the exact source, no findings; 81 focused archive tests and bounded schedule/expiry/inheritance mutation controls passed. Separate documentation review's two wording findings were corrected in docs-only `f0199b5` and its delta approved |

An initial core-only check was invoked against the optional-dependency
environment and correctly rejected its installed SDK/base dependencies. The
fresh no-dependency core check is the applicable passing result; the original
failed invocation is retained. No assertion, timeout or skip was relaxed.

Skips retain native Windows/local-NTFS, private tokenizer/experiment artifact,
frozen historical-runtime, optional browser and live-service limits. Source
success on macOS and these offline funding checks do not establish those
missing observations or a new hosted Windows qualification.

The normal hosted qualification installs `voyage,redis`; it omits `plan-oauth`
and `memory-native`. A separate fresh noneditable wheel environment selects
`voyage,redis,plan-oauth` explicitly. A broader profile including `memory-native`
passed its selected tests but failed the existing post-check's provider-SDK
absence guard; that receipt remains failed and the assertion is unchanged.
Plan execution remains limited to macOS arm64 /
CPython 3.12.2. Its offline keys, grants and request witnesses do not establish
live consent, account/model entitlement, native Keychain interoperability,
quota, billing or model quality. Full Windows behavior requires the candidate's
hosted results; local macOS tests cannot establish it.

## Verified software checkpoint — November 5, 2026

Merged main `9ecefe8a0fded05b1bb55b2f81d8579725666666`, tree
`d34613696c3ee3e9f0a288324f17e29367b5fc46`, exactly matches the reviewed PR head.
GitHub verifies the merge signature. The
[exact-main qualification](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/41957572830)
passed all 11 jobs; earlier branch checks were not substituted. Ubuntu source
passed 6,678 tests with 268 skips; both Windows source cells passed 6,392 with
555 skips and seven passing subtests. Installed cells passed 4,131/219 skips
on Ubuntu, 4,134/216 on macOS, and 4,115/224 on each Windows Server cell, with
two passing subtests per installed cell, complete memory/R2 and ten plugin
probes, and zero model calls. Native SDK component, isolated Windows effects,
CodeQL and dependency-graph checks also passed; safe-profile preflight was skipped.

[Build-only rehearsal 41961339343](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/41961339343)
passed on that exact main SHA with `publish=false`. All three publishing and
remote-verification jobs were skipped. Strict distribution checks, no-dependency
core checks and the base-dependency plan/accept/build/review/status journey passed.
The PyPI-target route records SHA256SUMS rather than the TestPyPI-only manifest.

| Rehearsal distribution | SHA-256 |
| --- | --- |
| Wheel | `57223f23037014a0c134956375aa8088ca586e9816e0c7a1c7b8161c5eb3916a` |
| Sdist | `03f0120e5a66928067c70ea9c928a6a11621b300504be6b61ca4f726e1725c4e` |

That exact wheel passed a fresh macOS arm64 / CPython 3.12.2 qualification with
explicit `voyage,redis,plan-oauth`: 4,146 passed, 204 skipped, two passing subtests,
complete memory/R2/native process/recovery and all ten plugin probes, zero model
calls. The focused OAuth/profile/worker selection passed 112 with no skips;
the selections overlap. Independent artifact review verified all 137 packaged
source files against main, wheel RECORD, metadata and distribution checksums.
There was no separate complete installed-sdist qualification. The retained
combined `memory-native` profile failure above remains failed.

Windows installed evidence covers actual CRLF wheel payloads: 128 Python modules
match Git after LF-to-CRLF materialization and one matches raw bytes. It does
not establish byte identity with the LF rehearsal wheel. Fresh supplemental
[coverage](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/41957572989)
passed all three jobs but Windows ignored one invalid 24,576-byte raw trace.
Its lost unique line/arc scope and percentage impact are unknown. That warning
is separate from the earlier PR run's malformed 8,192-byte file; successful
tests do not establish complete tracing. Original warnings and bytes remain
retained. No guard, timeout or assertion was relaxed.

The new [Help preparation walkthroughs](../help/1-7-0-preparation.md) use this
recorded wheel/source checkpoint. Their actual command and automated-browser
observations are separate from the old tutorials and from final qualification
of this documentation follow-up. Publishing rebuilds must verify their own
actual bytes; sdist timestamps and the unpinned build backend can change them.

## Documentation readiness

This is the current source-documentation disposition, not a claim that every
published derivative is ready. Use versioned code and reproducible checks as
the authority for behavior. Follow the [writing guide](writing-guide.md); its
linked Google UI, tone and code-font guidance was checked November 4, 2026.

| Canonical topic | Candidate disposition and code/test evidence | Derivatives and owner state | Walkthrough result and limits | Older guidance |
| --- | --- | --- | --- | --- |
| README, installation and CLI guide | Changed for prepared 1.7.0; metadata, CLI help, installed core and cold-start checks | Source Help now restores an isolated 1.5.1 practice setup and labels a separate 1.7.0 written preparation topic; review and website activation remain pending | Local-wheel route before publication; index commands explicitly wait for publication. Exact candidate results in the release PR | 1.6.0 release JSON and tagged guide retained; historical tutorials unchanged |
| Command environments and migration | Changed to retain legacy behavior through 1.7.0, removal no earlier than 1.8.0; `command_environment.py`, notice/lifecycle tests and existing overdue guard | Source guidance updated; published Help and tutorial/deck derivatives require owner reconciliation before publication | Legacy and opt-in dispatch, presentation and replay controls run offline; filtering does not supply an OS sandbox | 1.6.0 changelog/release records retain their announced schedule |
| Participant funding | Changed to describe separate `openai` and `openai-plan` routes; API, plan worker, profile, OIDC and owner/journey tests | Active guide updated; approved specs retain their original design/baseline wording. Source release guide supersedes outdated proposed-configuration availability statements | Offline software evidence only; no provider account, native Keychain or billing qualification | Original API-first/S1 failed evidence and later software receipts retained |
| Hydration and memory migration | Clarified as capture/secret/ledger groundwork from #318; source primitive tests. Existing reader behavior retained | Existing writer/hooks remain required; no finished hydration command or automatic host-delivery derivative | Live Redis publication/cleanup and fresh Claude Code/Codex delivery remain unfinished | 1.6.0 reader evidence and approved writer specification retained |
| First plan/build and saved-work inspection | Procedure from #337 retained and reviewed for candidate CLI; cold-start and installed R2 checks | Written 1.7.0 Navigation, Specification Workflow, local research and Session Continuity preparation is separate from historical pages; independent-user acceptance and deck replacement remain pending | Software journey uses deterministic workers and does not establish model quality or user comprehension | Historical walkthroughs keep their source, interpreter and observation labels |
| Windows, forms and plugin limits | Existing source boundaries reviewed; candidate source/platform/plugin checks retain their own evidence | No desktop, live-host or marketplace acceptance promoted by version metadata | Hosted Server CI and local software tests do not qualify every Windows desktop/shell or host-plugin journey | Older platform/observation receipts unchanged |

The existing training projections cover Navigation (**Start and continue work**),
Specification Workflow, Four Workflows and Session Continuity. Their owners must
reconcile the 1.7.0 changes before claiming current help/tutorial/deck readiness.
Historical 1.3.0/1.4.0/1.5.1 walkthroughs and source 1.6.0 onboarding are
preserved. The website repository's retained export still identifies a 1.5.1
source checkpoint; the live deployment was not verified. Do not describe source
Help as deployed content. A separate importer compatibility draft preserves the
historical reference version, strict published-status gate and active export.
It supplies no release record or activation authority.

The new written preparation topic is proposed interim material for the four
training topics. Actual browser automation checks software behavior; they do
not establish independent-user comprehension, exact keyboard order, assistive
technology support or every ownership transition. Delivered decks remain
historical; their replacement or explicit interim-material disposition needs
review. A static Help build/link check validates projection and routes, not
semantic acceptance or permission to deploy. No derivative owner approval or
publication is claimed here.

## Remaining release gates

- Complete candidate evidence and different-model review at the recorded commit.
- Read the candidate's hosted checks, including both Windows Server profiles;
  retain failures and skipped scopes explicitly.
- Resolve documentation derivative ownership/readiness before requesting
  publication; do not silently relabel old observations as 1.7.0.
- Review and qualify the final documentation source and built artifacts, then
  obtain separate merge authority. Qualify the resulting exact main SHA and
  arrange any required rehearsal for that changed candidate. Publication,
  tagging and GitHub release require their separate approvals.
- Verify published distributions against the publishing run's recorded hashes
  and artifact identities before
  the marketplace pin or website is updated. Versioned README links are
  prospective until the release tag exists.
