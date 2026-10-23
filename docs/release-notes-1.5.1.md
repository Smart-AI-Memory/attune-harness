# Attune Harness 1.5.1 release notes

**Draft — unpublished.** Version 1.5.1 is the proposed maintenance release after
[1.5.0](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.5.0).
These notes cover merged changes through
`0f2711b4c88ee4f231f61d71cd70a0c840be6357`; the final release source and
distribution have not been accepted. Package and plugin manifests still identify
1.5.0. The [readiness record](release-readiness-1.5.1.md) tracks remaining checks.

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

Publication remains held for final preparation and approval. Current-main
[qualification](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39872982676)
passes, including all eight installed-wheel jobs and all four Windows full-source
jobs. PR #298 introduced verified partitions within the unchanged total deadline.
The earlier [failed run](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39786227278)
is retained historical evidence, not the current-main result. The selected final
1.5.1 source and artifact still need their own qualification, documentation
reconciliation and authorized build-only rehearsal before publication approval.

Full Windows parity, strict arbitrary-descendant stop and recovery, full
saved-store acceptance, the historical eight-writer busy-failure cause, live
native-memory acceptance, Windows 11 standard-user desktop journeys and shell
qualification remain open. A maintenance release does not close these gates.
The [readiness record](release-readiness-1.5.1.md) separates them from current
software checks and pending documentation reconciliation.
