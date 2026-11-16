# Harness 1.8.1 readiness record

This record defines the scope and verification requirements for 1.8.1 after
published 1.8.0. The [release-preparation PR](https://github.com/Smart-AI-Memory/attune-harness/pull/365)
records candidate validation results, exact source identities and distribution
hashes. Consult that record for check status; this document does not establish
publication. Earlier results below retain their tested source and package
identities. See the [release notes](release-notes-1.8.1.md) and
[release runbook](release-runbook.md).

## Candidate scope

The runtime fix merged in
[PR #364](https://github.com/Smart-AI-Memory/attune-harness/pull/364) as
`c3b1e7cb6572e0468f0abd7d4c3ee12a8d9b01a2`. Its tree matches tested commit
`3fe34e6c1b8536b5a0ae38eb0d4a98f63065b0fa`. The only file under `src/` changed
since `v1.8.0` is `attune_harness/init_cli.py`: it preserves literal Windows
paths and following options in prepared PowerShell commands. The change does
not make raw JSON response text directly executable; shell tests decode command
values before execution.

The release also carries the documentation and catalog work already merged
since 1.8.0:

| Changes | Scope |
| --- | --- |
| [#359](https://github.com/Smart-AI-Memory/attune-harness/pull/359) | Make the Help Center and quickstart easier to find. |
| [#360](https://github.com/Smart-AI-Memory/attune-harness/pull/360), [#361](https://github.com/Smart-AI-Memory/attune-harness/pull/361) | Maintain one reporting course and improve readability, setup and navigation. |
| [#362](https://github.com/Smart-AI-Memory/attune-harness/pull/362), [#363](https://github.com/Smart-AI-Memory/attune-harness/pull/363) | Update the learner walkthrough and Windows evidence in the project plan. These are planning and evidence updates, not additional runtime features. |
| [#358](https://github.com/Smart-AI-Memory/attune-harness/pull/358) | Point the Claude Code marketplace at published 1.8.0. This remains separate from the future 1.8.1 catalog update. |

[PR #365](https://github.com/Smart-AI-Memory/attune-harness/pull/365) prepares
the 1.8.1 release. Its validation record identifies each tested candidate and the final shipping
commit after selection. The intended package version and both shared manifests under
`plugin/attune-harness` are 1.8.1. Python 3.12 remains the minimum; the distinct
Codex workflow plugin retains its independent 0.1.0 version.

## Earlier compatibility evidence

PR #364 settled with 23 successful checks, one intentional skip, and no pending
or failing check. Its [Library qualification run](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/43811578818)
and [coverage run](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/43811578837)
apply to the tested 1.8.0 development candidate, not a 1.8.1 distribution.

| Profile and source | Retained result | Boundary |
| --- | --- | --- |
| Windows Server 2022, Python 3.12.10, tested PR #364 head | Installed suite: 4,550 passed, 281 skipped, 2 deselected and 2 passing subtests in 1,592.12 seconds; post-suite checks passed. | Candidate metadata still read 1.8.0. |
| Windows Server 2025, Python 3.12.10, tested PR #364 head | Installed suite: 4,550 passed, 281 skipped, 2 deselected and 2 passing subtests in 1,813.29 seconds; post-suite checks passed. | Candidate metadata still read 1.8.0. |
| Windows 11 ARM64 Parallels, x64 CPython 3.12.10 under emulation | Earlier selected run: 227 passed with zero failures, skips or expected failures across PS5.1 and PS7. | Standard user on fixed local NTFS; no native-x64 desktop or native ARM64 Python qualification. |

The Windows CI suite limit is now 2,100 seconds, with a 40-minute hosted job
budget. Individual operation deadlines, selected tests and failure handling
are unchanged. This CI adjustment does not diagnose the separate desktop
timeout or establish that increasing a task's probe timeout is a remedy.

The Windows 11 run covers 192 native argument checks, 28 roundtable
preparations, two expected scope refusals, four review-intake journeys and one
worker-selection case. It accepted no plan, started no build and made no model
calls. The earlier and timeout-fix local wheels have identical bytes for all
133 `attune_harness/` members. The shared formatter SHA-256 remains
`fee5653ae9648176f1d0930050a32ee947bf1a57449b0db453ebd429af7a54ab`.
These comparisons preserve the earlier evidence; they do not qualify a new
version's distribution metadata, installation or complete artifact.

## Candidate checks

Record each result below in PR #365 with its tested source SHA, tree and exact
artifact identity. Keep distribution hashes outside the source they identify:
editing this document after building creates a new candidate. Retain earlier
results under their original identity, and validate any selected replacement.
The later publishing run supplies the authoritative hashes for published bytes.

| Check | Required evidence |
| --- | --- |
| Source and version consistency | Final source SHA, package/shared-manifest versions and exact `## 1.8.1` changelog heading. Preserve the independently versioned Codex package and published marketplace pin. |
| Focused checks and full source suite | Exact candidate source, interpreter, counts, skips and failures. Keep prior PR #364 checks separate. |
| Wheel and source distribution | Filenames, SHA-256 hashes, build inputs and strict Twine check. Use the validation record for local candidate hashes. |
| Fresh installed CLI checks | The same wheel in separate no-dependency core and normal base environments; retained `check_installed.py` results for both profiles. |
| Installed-wheel platform qualification | The noneditable 1.8.1 wheel, platform, Python, dependencies, suite outcomes and exclusions. Earlier 1.8.0 qualification is not a substitute. |
| Documentation and plugin checks | Final-source link/index checks, manifest checks, Help export, course projection check, walkthrough review and version boundaries. |
| Shipping-source CI | Successful Library qualification for the exact merged 1.8.1 release SHA. |
| Build-only rehearsal | Authorized run and attempt, artifact identities, and Windows Server 2022/2025 results for the same Ubuntu-built wheel, including separate offline native-memory SDK profiles. |
| Publication verification | Separate authorization and publishing-run hashes; verified index installation, tag, GitHub release and later marketplace update. |

## Documentation readiness

Apply the [writing guide](writing-guide.md). The table identifies affected
source and actual derivative locations. PR #365 records the semantic review,
walkthrough results and build/link checks separately. Named human content owners
are unconfirmed; this preparation has not contacted owners or published a site.

| Canonical topic/source | 1.8.1 disposition and evidence | Actual derivatives and ownership | Walkthrough result and older guidance |
| --- | --- | --- | --- |
| README, `docs/installation.md`, `docs/cli-guide.md` | Release/status wording and prepared-command benefits updated. Record candidate installation and link checks in PR #365. | `help/get-started.md`, exported by `scripts/build_help.py`; the `attune-ai` repository imports it through `website/scripts/harness-help-export.mjs`. Human owner confirmation pending. | Help manifest currently names published 1.8.0; retain the 1.5.1 reference and other historical guide identities. New candidate walkthrough results belong in PR #365. |
| `docs/supported-journeys.md`, `docs/windows-reliability.md` | Describe the narrower PowerShell change from PR #364; retain profile/recovery limits. Record actual 1.8.1 candidate checks separately. | Existing Help setup guidance; no separate new deck or Windows tutorial is asserted. Human owner confirmation pending. | Earlier Server and emulated-x64 results remain as recorded above. Prepared command values were exercised; raw JSON copy/paste was not. |
| `training/reporting/*/lesson.json` | Lesson sources unchanged for this patch. Record the projection check and exact-wheel practice run in PR #365. | `training/build_course.py` generates interactive lessons, `read.html` and presenter scripts from the same source. Website import belongs to `attune-ai`; human owner confirmation pending. | `training/reporting/assets/compatibility.json` records published 1.7.0/1.8.0 runs. Retain those hashes, archived course routes and prior learner observations. |
| `docs/qualification.md`, `docs/release-runbook.md` and package/plugin guidance | Version/status guidance updated; record final artifact checks in PR #365. Integration and funding boundaries retained. | Shared plugin README/manifests, separate marketplace catalog, Help dependency/integration guidance. Cross-repository publication coordination pending. | Existing provider, Redis, memory and Plan OAuth evidence keeps its original scope and version; no new live-service claim. |

The November 16 public-page review found that
[Get started](https://smartaimemory.com/harness/help/get-started/) identifies
Harness 1.8.0 as the current release, and
[Learn](https://smartaimemory.com/harness/learn/) redirects to that setup page.
The retrieved web-cache source was crawled the previous day; this establishes
the existing 1.8.0 guidance, not a fresh deployment or 1.8.1 website delivery.
`docs/content-map.json` records the observed entry routes and the limits of
that review. It is not a website deployment receipt; historical compatibility
evidence retains its original identities.
The runbook names additional deck topics, but no specific deck source or owner
was verified for this change. No new deck update is claimed.

## Remaining boundaries

Native-x64 Windows 11 repeatability, native ARM64 Python dependency availability,
the observed desktop timeout, strict descendant shutdown, uncertain-operation
recovery and power-loss durability remain separate work. The native ARM64
binary-only attempt could not resolve pinned `tiktoken==0.12.0`.

The recorded finite-environment difference also occurs with direct Python.
Privilege-dependent symbolic links, filesystem profiles beyond fixed local
NTFS, positive Redis service behavior and live providers are not qualified by
the desktop checks. Plan OAuth retains its macOS-only profile. Existing memory
writers, hooks and archived evidence remain unchanged.

This preparation record supplies no merge, workflow-dispatch, publication,
website, provider-call or owner-contact authority. Complete the candidate
checks and documentation review before requesting the next release decision.
