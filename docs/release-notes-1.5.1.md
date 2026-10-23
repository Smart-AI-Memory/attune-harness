# Attune Harness 1.5.1 release notes

**Prepared — publication pending.** Version 1.5.1 is the maintenance release after
[1.5.0](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.5.0).
This preparation incorporates merged main
`13e46e06cbcefc3a5bd806fe58c913a7a695bcb7`, including the reader repair in #303, diagnostic
compatibility in #304, canonical Help in #299 and current walkthroughs in #300.
It sets the package and both plugin manifests to 1.5.1. The
[readiness record](release-readiness-1.5.1.md) separates candidate validation,
remaining acceptance and publication approval.

## Put existing capabilities to work

Version 1.5.1 emphasizes clearer paths through the capabilities Harness already
provides. Use the [installation guide](installation.md) to prepare your runtime,
then the [workflow selector](supported-journeys.md) to choose work to plan,
build, review, fix or test. The guides connect entry points, expected results
and approval requirements. Saved progress and the
[pause-and-return procedure](cli-guide.md#pause-and-return-to-work) help you
inspect work and continue from a known stopping point.

## Use Harness on Windows

Windows users can install Harness and use its documented CLI workflows within
the supported profiles. Windows implementations include captured test
execution, native file-memory reads, saved memory and task storage, and
experimental native-memory transport. This maintenance release improves the
Windows memory-target walk and the evidence retained by software checks.

Hosted checks exercise Windows Server 2022 and 2025 with Python 3.10 and 3.12.
Use the [Windows capability table](supported-journeys.md#windows-capabilities-and-reliability)
to select a workflow and understand its limits. The checks qualify their
recorded source and artifacts; the remaining desktop, shell, recovery and
storage acceptance work is listed below.

## Validate the exact plugin signature input

Harness now gives GPG the exact binary signature bytes checked by its packet
guard. One complete ASCII signature envelope is decoded before verification.
Trailing messages, duplicate armor blocks, malformed delimiters, invalid base64
and malformed or incorrect optional checksums refuse before GPG starts.

Valid binary signatures and supported LF/CRLF armor, headers and optional
checksums retain verification. The existing signature size bound, signer
authority, accepted grants and subprocess deadlines remain in effect.
See [PR #289](https://github.com/Smart-AI-Memory/attune-harness/pull/289) and the
[signature-input design](design-plugin-signature-input.md). This fixes a parser
input mismatch; it does not make cooperating plugins an operating-system sandbox.

## Inspect completed assessment evidence

For a completed document assessment, **`status`** with `--format markdown` or
`--format html` now presents:

- The accepted goal and criteria.
- Recorded document-check verdicts and checker findings.
- Retrieved-source identities and exact saved-record pointers.
- Separately attributed participant judgments.

The report keeps software check outcomes distinct from participant judgments.
Semantic acceptance remains unverified, and inspection does not rerun checks,
refresh source evidence or authorize execution. Entered wording and line breaks
are preserved in the display; non-layout control characters appear as `\uXXXX`.
Default JSON and saved records are unchanged. Other task profiles, incomplete
assessments and repair presentation retain their existing rendering.

Follow the [inspection procedure](cli-guide.md#inspect-completed-assessment-evidence-151-candidate)
and [PR #292](https://github.com/Smart-AI-Memory/attune-harness/pull/292).
These changes are absent from published 1.5.0.

## Follow clearer guidance

The README, installation guide and workflow selector clarify managed-runtime
selection, optional integrations, separate agent installation and Windows
reliability requirements. Browser-form tests retain timeout diagnostics.
Repository documentation checks now validate local heading fragments,
source-file targets and source line ranges while keeping historical exceptions
explicit. Selected refusal-continuation tests follow the printed next command
with saved-state checks and zero model calls. This bounded audit does not prove
every refusal journey, native shell execution or observed user comprehension.

See [PR #288](https://github.com/Smart-AI-Memory/attune-harness/pull/288),
[PR #290](https://github.com/Smart-AI-Memory/attune-harness/pull/290),
[PR #291](https://github.com/Smart-AI-Memory/attune-harness/pull/291) and
[PR #293](https://github.com/Smart-AI-Memory/attune-harness/pull/293).

## Pause and return with preserved Windows paths

Follow the connected [pause-and-return procedure](cli-guide.md#pause-and-return-to-work)
to retain a stopping note, inspect saved context, regenerate the report and
prepare the next assistant handoff before any authorized continuation. The
printed Python wrapper uses raw path literals so native Windows backslashes
reach the CLI unchanged. Keep the `r` prefix when replacing its paths.

The printed-command checks cover current, absent, historical, stale and
unresolved context. One assisted text walkthrough is retained separately from
Task 1's incomplete independent-return and GUI acceptance. See
[PR #296](https://github.com/Smart-AI-Memory/attune-harness/pull/296).

## Complete bounded Windows source checks

Each hosted Windows full-source cell now runs two supervised pytest partitions
without increasing the 2,700-second child deadline. The driver verifies matching
complete collections, disjoint complete selections, case journals and successful
process exits. Each child uses a distinct root under the native system temporary
base. Timeout or missing evidence still fails the cell, even after printed success.

All four repaired Windows source cells passed on the merged precursor, and all
28 checks passed on #296's combined head. This is server/software evidence;
full Windows parity and desktop/shell acceptance remain separate. See
[PR #298](https://github.com/Smart-AI-Memory/attune-harness/pull/298) and the
[partition design](design-windows-source-suite-shards.md).

## Check dangling Windows memory targets

Raw-memory reads treat a confirmed dangling `findings.jsonl` symbolic link as
absent without reading its target content. The Windows target walk now binds
each selected ancestor name and identity without freezing unrelated siblings or
ordinary-directory timestamps between completed observations. This avoids a
false refusal when another operation changes an ancestor's unrelated contents.

The missing target's immediate parent retains its complete namespace snapshot.
Link metadata and reparse data, selected path bindings, completed directory scans
and exact native missing-status checks still refuse observed changes or unsafe
access. Targets receive no content authority. See
[PR #303](https://github.com/Smart-AI-Memory/attune-harness/pull/303); its evidence
separates portable regressions from native Windows results.

## Installation and compatibility

Use [published 1.5.0](https://pypi.org/project/attune-harness/1.5.0/) while 1.5.1 is in preparation. The [installation guide](installation.md) and [current walkthroughs](tutorials-1.5.1.md) distinguish candidate validation from installation after publication. After
publication, the base installation command for 1.5.1 will be:

```sh
uv tool install 'attune-harness==1.5.1'
uv tool list --show-paths
attune-harness --help
```

The tool list should identify 1.5.1. Before changing an existing installation,
inspect its version and path. Preserve saved task directories, older wheels and
evidence environments. Runtime installation and agent-plugin updates are separate;
the Claude marketplace remains pinned to released 1.5.0 until a later catalog
update after the new tag exists.

The v1 compatibility contract remains in effect. The assessed diff changes no
dependency pins, minimum Python version or saved-state format. Python 3.10 or
later is required; the hosted matrix exercises 3.10 and 3.12. These observations
do not qualify every saved-work migration or upgrade path.

## Release checks and remaining limits

The earlier [qualification run](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39786227278)
retains its Windows full-suite timeout. #298 addresses the measured cumulative
suite budget with verified partitions; #296's combined head passed all 28 checks,
including the previously failing Windows wheel job. The old Node startup/exit
delay's cause remains unknown; no deadline or assertion was weakened.

All 28 checks on #300's integrated preparation head passed, including the
Windows source and installed-wheel cells. The release-preparation PR records
fresh validation of the actual combined 1.5.1 candidate; precursor results do
not substitute for it. The separate audit/archive PR #305 remains unmerged
and is not included in this source.
Publication still requires the reviewed preparation merge, passing qualification
for that exact main commit, an authorized build-only release rehearsal and
Patrick's separate publication approval.

Full Windows parity, strict arbitrary-descendant stop and recovery, full
saved-store acceptance, the historical eight-writer busy-failure cause, live
native-memory acceptance, Windows 11 standard-user desktop journeys and shell
qualification remain open. A maintenance release does not close these gates.
The [readiness record](release-readiness-1.5.1.md) separates them from current
software checks and pending documentation reconciliation.
