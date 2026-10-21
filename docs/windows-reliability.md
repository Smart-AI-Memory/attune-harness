# Windows reliability reference

Updated on October 21, 2026. Applies to the 1.5.0 implementation and evidence.

Use this reference to inspect the reliability requirements and their evidence.
For task selection and procedures, use the [workflow guide](supported-journeys.md).

## Evidence snapshot

Checked against `main` at `4b773a6edb488afbe9b66348b7020c1b40dfbb67`,
the CLI/source owners and existing journey tests. The
[published 1.5.0 release record](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.5.0)
identifies release source `7caa86ab6d476e9599b08ff75a81bc816e60c382`,
distribution hashes and published-install evidence. The runtime source is
unchanged between that release and the main snapshot checked here. This reference
adds no fresh execution receipt.

The [hosted baseline run](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39205220937)
passed all 16 jobs for `77d5b2b4fe9f3c6285a5b535f4e735103f7e192d`,
including four Windows Server full-source and four Windows installed-wheel
cells across Server 2022/2025 and Python 3.10/3.12. These are bounded software
checks for that source and its artifacts. See the [workflow table](supported-journeys.md#windows-capabilities-and-reliability)
and [Windows checkpoint](specs/windows-parity/tasks.md) for workflow-specific
reliability boundaries.

## Reliability requirements

Reliable operation remains the acceptance standard for each workflow:

- **Complete process shutdown:** confirm every owned descendant has terminated
  before reading or decoding captured output, or reporting process completion.
  Preserve the existing shared five-second stop deadline and successful
  fast-child behavior.
- **Truthful outcomes and recovery:** preserve the original result and failure
  information. Uncertain effects must remain explicit; status or resume must not
  silently repeat a dispatched operation.
- **Durable saved data:** retain the approved standard-user durability requirement,
  including its power-loss proof obligation. Process-crash tests alone do not
  establish power-loss durability, and an app-crash-only fallback is not approved.
- **Consistent concurrent writes:** retain committed saves, exact request-ID
  replay and revision-conflict behavior. Recovery must preserve a valid before
  or after state without duplicate history.

The [approved design and acceptance criteria](specs/windows-parity/design.md)
and [Windows checkpoint](specs/windows-parity/tasks.md) retain the detailed
verification conditions and current acceptance status. The requirements above
are unchanged; this reference does not mark them complete.

## Further user observations

Fresh-session recall and exclusion, a qualifying non-programmer walkthrough,
and installed migration-row observations remain open in the
[observation record](release-readiness-1.4.0.md#open-observations-and-publication-boundary).
Bounded maintainer forms observations do not establish all three. The
[opportunity register](opportunity-log.md#current-register) tracks follow-up work.
