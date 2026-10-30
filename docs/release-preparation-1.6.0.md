# Prepare for Harness 1.6.0

**Local preparation guide — unreleased.** Published 1.5.1 remains the current
installation and Help reference. The next release is 1.6.0, with Python 3.12 or
later; no 1.5.2 release is planned. These instructions announce no public artifact.

## Review the draft

1. Read the local README and [draft release notes](release-notes-1.6.0.md).
2. Check [installation](installation.md), [migration and rollback](migration.md),
   and the [workflow selector](supported-journeys.md) against the work you need.
3. Have Patrick review the README before final source/version freeze.

The existing Help manifest and 14 registered pages remain published 1.5.1 guidance.
Their history, screenshots and release record retain their version identities.
Selected registered pages include clearly marked 1.6.0 preparation notes; there
is no new 1.6.0 Help URL or renderer behavior in this documentation change.

## Keep the evidence scoped

Merged main `d0849441c6420b73baa796cf80f7bdf3c1ed4fec` has the same tree
`1331daf9d2abb86e6629075017c8816afc8be62d` as reviewed PR #320 head
`8133e5f3d147d4a4bd6c80c9a3ed51d3d6edc8d6` and its successful PR checkout.
The PR cohort finished 23 successful checks and one expected disabled preflight
skip. Both Windows Server 2022/2025 ordinary installed and full-source profiles,
separate `windows-latest` and `ubuntu-latest` supplemental coverage jobs, native-owner/SDK, Qualification and CodeQL passed.
See [the PR](https://github.com/Smart-AI-Memory/attune-harness/pull/320) and
[Library CI](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/41059299183).

Main-event CI started automatically after the human merge. It was still pending
at the recorded handoff; this document does not substitute PR success for that
result. The private repair artifacts used 1.5.1 metadata and are not final 1.6.0
wheels. Completed logs/metadata are not an independent raw-wheel/complete-RECORD
verification, live provider result or model-quality assessment.

The historical Windows 11 smoke was standard-user, ARM-host/x64-Python emulation
on an older repair artifact. It does not qualify all desktop features, native
ARM64 or a final 1.6.0 artifact. Current hosted workflows remain the first practical
Windows evidence route; full POSIX parity is not claimed.

## Finish the release gates

- Synchronize the stale runtime NOTICE and machine-readable deprecation register
  to the selected 1.6.0 notice/earliest 1.7.0 removal schedule. Legacy behavior stays
  accepted; no removal is implemented here.
- Complete main-event CI review and Patrick's README review.
- Select final 1.6.0 package/plugin metadata and freeze the exact source.
- Build and qualify the exact new artifacts, then perform the nonpublishing rehearsal.
- Obtain the separate publication decision. Never reuse published 1.5.1; Patrick
  controls the PyPI gate.

Writer #318/RedisVL and unfinished convenience features remain outside 1.6.0.
Current-final-artifact live Redis+Search verification remains incomplete; retain
accurate service claims and working data/hooks rather than infer a pass from pins.
This guide authorizes no operation, release or provider call.
