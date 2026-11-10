# Harness 1.8.0 readiness record

This record covers preparation of the 1.8.0 package from the changes after
published 1.7.0. The candidate and publication evidence are recorded
separately. See the [release notes](release-notes-1.8.0.md) and
[release runbook](release-runbook.md).

## Candidate scope

The preparation starts from `829a4c01b64722c44ff8e5ac19095cb502060fa7`, which
merged the updated command environment schedule in
[PR #356](https://github.com/Smart-AI-Memory/attune-harness/pull/356). The
candidate also includes the private memory preparation in
[PR #351](https://github.com/Smart-AI-Memory/attune-harness/pull/351) and the
secret-check performance change in
[PR #342](https://github.com/Smart-AI-Memory/attune-harness/pull/342). The
earlier PR results apply to their recorded source and artifacts.

The Python package and both bundled manifests under `plugin/attune-harness`
use version 1.8.0. Python 3.12 remains the minimum. The separate Codex
workflow plugin has its own 0.1.0 version. The Claude Code marketplace selects
the published `v1.7.0` tag until the post-publication catalog update.

## Candidate checks

| Check | Evidence to record |
| --- | --- |
| Focused checks and complete source suite | Exact source, interpreter, counts, skips, and failures. Include legacy inheritance, finite command environments, deprecation expiry, guarded memory preparation, and secret matching. |
| Wheel and source archive | Exact source and distribution filenames and SHA-256 hashes. Record the strict Twine check. |
| Fresh installed CLI checks | Use the same wheel in two separate environments. Record the no-dependency core result and normal base install result, including the deterministic local result and first plan/build journey. |
| Installed-wheel platform qualification | Run `scripts/qualify_platform.py` with the noneditable candidate wheel. Record the artifact, operating system, Python, dependency profile, results, and exclusions. |
| Documentation and plugin checks | Record the checked source, documentation link and index checks, static Help export, course projection check, manifest checks, and candidate walkthrough results. |
| Hosted Library qualification | After merge, record the successful run on the full shipping SHA. |
| Publish workflow rehearsal | After authorization, run the build-only rehearsal on that SHA. Record its run and attempt, artifact identities, and Windows Server 2022 and 2025 results for the exact Ubuntu-built wheel. Each server runs the standard installed qualification and the offline native-memory SDK checks in separate environments. |

The rehearsal and publication runs build their own distributions. Use the
publish run's checksums to verify the files that reach PyPI. After approval and
upload, record the verified index install, signed tag, and GitHub release. The
runbook also covers the later marketplace update.

## Documentation readiness

Apply the [writing guide](writing-guide.md). Each procedure keeps its runtime
and evidence identity. Record the candidate walkthrough results before
requesting publication.

| Topic | Candidate disposition | Existing guidance and evidence |
| --- | --- | --- |
| README, installation, and CLI | Describe the reviewed wheel, version, expected CLI result, and rollback. Verify the example against the candidate and label package-index steps for use after publication. | The [1.7.0 release record](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.7.0) retains the published files and their checks. |
| Command environments and migration | Retain legacy inheritance through 1.8.0 and set 1.9.0 as the earliest removal. Check the runtime notice and expiry guard against the active register. | Published 1.7.0 and earlier records retain the schedule announced with each release. |
| Memory preparation | Describe the private projection and input checks. Keep instructions for existing writers and hooks. Check that supported journeys still match the candidate. | The [preparation increment](specs/native-memory/hydration-writer/preparation-increment.md) describes its synthetic checks and the remaining writer and delivery work. |
| Help, course, and reference walkthroughs | Review the affected links and version boundaries. The live [Get started guide](https://smartaimemory.com/harness/help/get-started/) and [course](https://smartaimemory.com/harness/learn/) remain on published 1.7.0. | The Help reference keeps its 1.5.1 identity. Course fixtures, saved progress, and retained walkthrough evidence keep their original versions. The [content map](content-map.json) records the delivered source. A website update follows its own review and deployment. |
| Windows guidance | State the Windows Server profiles and use the qualification results for the exact candidate. | The [quickstart rehearsal](https://github.com/Smart-AI-Memory/attune-harness/pull/355) used the 1.7.0 wheel, x64 Python under ARM emulation, and Windows PowerShell 5.1. Windows 11 desktop support is outside the 1.8.0 claim. |

## Separate observations

A supported Windows 11 desktop walkthrough would need the exact candidate
wheel on native x64, under PowerShell 5.1 and 7 as a standard user on local
NTFS. The observer would open the generated HTML in a desktop browser and
check the report. This work stays with
[quickstart #355](https://github.com/Smart-AI-Memory/attune-harness/pull/355).

The independent first-time learner walkthrough stays with the
[next Help publication](project-plan.md#next-help-publication). Live provider
account and billing qualification, production hydration and host delivery,
and broader GUI execution remain separate workstreams. See the
[delivery checkpoint](project-plan.md#delivery-phases).
