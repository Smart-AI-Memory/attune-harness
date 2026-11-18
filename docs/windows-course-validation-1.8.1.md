# Windows reporting course validation with Harness 1.8.1

Recorded November 18, 2026. Published Harness 1.8.1 completed the bounded
reporting exercise in both PowerShell versions with the corrected course
candidate in [PR #367](https://github.com/Smart-AI-Memory/attune-harness/pull/367).
These results cover the named configuration and course files. They do not
establish full Windows parity or publication of the revised website course.

## Tested configuration

Both fresh environments used Windows 11 Pro build 26200 in Parallels, an
ARM64 guest CPU, x64 CPython 3.12.10 under emulation, local NTFS and
non-elevated PowerShell sessions. Each installed Harness 1.8.1 and pytest
9.1.1. The installed Harness payload matched 145 files from the verified
published wheel; installer bookkeeping and generated launchers were excluded.

| Shell | Change probe | Final probe | Workflow result |
| --- | --- | --- | --- |
| Windows PowerShell 5.1.26100.9974 | 77 passed | 77 passed | Completed once |
| PowerShell 7.6.10 | 77 passed | 77 passed | Completed once |

## What passed

Each run installed into a fresh course environment, checked the selected
interpreter, prepared a draft and displayed its plan. Exact checkpoint
acceptance and BUILD received separate human approvals before execution.

Each completed build recorded two fixed local command-participant turns and
two protected probes. All five build events completed with one attempt each.
Participant and probe limits remained 30 seconds. The participants made zero
model calls; the deterministic reviewer was a protocol witness, not a
substantive model review.

Only `report.py` changed among 44 captured project files. All seven protected
files retained their hashes. Both generated HTML files matched the protected
expected bytes, with six CSV entries totaling 270 minutes. Saved **`status`**
checks and a return from a fresh shell completed; the test controller recorded
unchanged saved task and project bytes after those checks.

The runner executed the guide's displayed command blocks in fresh shell
processes and restored the documented path variables between steps. This
checks the commands, not manual copying or an uninterrupted learner session.

## Artifact identity

| Artifact | Identity |
| --- | --- |
| Tested course source | `c41b9b2ef15898237eedacb7d038f3064815d261` |
| Practice ZIP SHA-256 | `52ade57bf4784fb0d1dc1693ab1c8b1849495fd8d8c9ab5fa0af7fd292be4bdd` |
| Published 1.8.1 wheel SHA-256 | `f83e924599b0eb0b3d40c428a80cb8fc5794c22cf2341752702cccf2f98ceaae` |
| Expected and generated HTML SHA-256 | `ae59332ac013d0ec220484b723457d4ac06a179e350218b769dc2d3425678124` |

Maintainers retain the installation transcripts, wheel comparisons, accepted
and completed task records, raw command output and before/after manifests.
Those local records support this summary; they are not published with this
page. Earlier failed attempts and historical release evidence remain separate.

## What remains open

- Native Windows 11 x64 execution of this revised course with published 1.8.1.
- An unaided learner walkthrough and browser inspection of that learner's
  generated report.
- A recorded browser download and Explorer extraction of the reviewed package.
- Broader command, integration and recovery qualification beyond this exercise.

The separately supplied PowerShell diagnostic helper is not in the practice
ZIP. A reported launch refusal before preparation is separate from these course
results. The [learner setup](../help/get-started.md#set-up-the-practice-folder)
calls its selected Python executable directly; it needs no activation script
or execution-policy change. Native ARM64 Python has
[separate installation evidence and limits](windows-arm64-validation-1.8.1.md).
