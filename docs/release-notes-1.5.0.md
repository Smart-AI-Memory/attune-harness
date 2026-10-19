# Attune Harness 1.5.0 release notes

Version 1.5.0 includes verified merged Windows components and retains their
bounded evidence. Full Windows parity is deferred; strict acceptance criteria
remain unchanged. Earlier artifacts retain their recorded identities. The
[preparation readiness record](release-readiness-1.5.0.md) preserves their
source bindings and open Windows requirements.

These notes describe the selected release scope. Index installation commands
apply after publication; the release workflow supplies the final distribution
hashes. Publication requires separate approval.

## Merged Windows components

The following entries describe implementation checkpoints. They do not
establish full Windows parity, Windows 11 desktop qualification, or live
provider acceptance.

- **Test a captured change.** The merged Windows implementation previews a
  test plan, runs accepted tests in a captured copy, and retains their output
  and check evidence. It also supports the existing completed-task handoff
  through `test --from-task`. Checkpoints and single-dispatch recovery remain
  part of the workflow.
- **Read file-based memory.** Merged native readers cover raw, personal, and
  curated roots, complete-source resolution, refresh, and eligible file-pointer
  serving. The reader keeps the existing limits of 4,096 Markdown files per
  root, 8 MiB per file, and 64 MiB per query snapshot. Native path and retained
  file-identity checks apply within the declared local NTFS profile.
- **Save memory and task intent.** The production Windows implementation
  checkpoint merged in [PR #275](https://github.com/Smart-AI-Memory/attune-harness/pull/275).
  It retains revisions, withdrawn history,
  request-ID replay, pending task reviews, and an optional rebuildable Redis
  index. Full saved-store acceptance remains open while the historical
  eight-writer busy failure has no established cause.
- **Use the experimental native-memory transport.** The merged Windows
  transport has offline evidence through the supervised helper and pinned SDK.
  Live provider acceptance remains open. Experimental native memory remains
  separate from the base and `all` profiles; installation does not authorize a
  provider call.

The [readiness record](release-readiness-1.5.0.md#component-evidence) links the
merged component evidence. Component success does not qualify their final
combination, every Windows configuration, or model quality.

Integrated baseline `77d5b2b4fe9f3c6285a5b535f4e735103f7e192d` passed all
16 jobs in [Qualification run 39205220937](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39205220937),
including four Windows Server full-source-suite cells and four Windows
installed-wheel cells across Server 2022/2025 and Python 3.10/3.12. These
results cover that source and the artifacts built by that run.

## Installation and upgrade

After 1.5.0 is published, install the base runtime in an isolated tool
environment:

```sh
uv tool install 'attune-harness==1.5.0'
uv tool list --show-paths
attune-harness --help
```

The tool list should identify `attune-harness` 1.5.0. Confirm the selected path
before running examples. Before publication, validate the selected local wheel
instead; a version string alone does not bind its source or installed bytes.

Python 3.10 or later is required; the hosted matrix exercises 3.10 and 3.12.
Harness and Attune AI require separate environments because they pin different
MCP SDK versions. Redis and Voyage remain optional. The experimental
`memory-native` profile is separate, and installation authorizes no provider
call. The [1.5.0 README](../README.md#installation) lists exact base and extra
installation commands.

Before changing an existing installation, inspect its version and path with
`uv tool list --show-paths`, then explicitly select 1.5.0 when you choose to
upgrade. Preserve saved task directories, older wheels and evidence environments.
The v1 compatibility contract remains in effect; these checks do not qualify
every saved-work migration or Windows configuration. The
[historical 1.4.0 installation guide](installation.md) retains its older pins
and observed environment checks; use the commands above for 1.5.0.

## Workflows and compatibility

Use the existing commands and explicit configuration; version 1.5.0 does
not introduce a separate Windows workflow.

| Goal | Existing entry points | Guidance |
| --- | --- | --- |
| Check a captured change | `test`, then saved checkpoint acceptance; `test --from-task` for a completed task | [CLI guide](cli-guide.md); [Windows command walk](specs/windows-parity/README.md#testing-repair-and-build) |
| Read configured memory | `memory recall`, `memory resolve`, `memory refresh`, and `memory serve` | [CLI guide](cli-guide.md); [file-memory command walk](specs/windows-parity/README.md#file-memory-reads) |
| Save memory or task intent after the port qualifies | `memory saved` lifecycle, history, and pending-review operations | [Saved-store command walk](specs/windows-parity/README.md#saved-memory-and-tasks) |
| Prepare a native-memory proposal | `memory create`, with separate `memory execute` authority and configuration | [Native-memory command walk](specs/windows-parity/README.md#native-memory-proposal-transport) |

The Windows command walks are specification references, not qualified
PowerShell procedures. The [four POSIX preparation walkthroughs](tutorials-1.5.0-candidate.md)
retain their exact local-wheel identities, example inputs and observed limits.
They are not relabeled as executions against a future published wheel. Existing
preview and acceptance boundaries, saved schemas, historical receipts and
explicit execution grants remain part of the parity requirements.

The browser companion retains its documented forms boundary: saving answers
and approving a request do not execute work. Read the
[1.4.0 notes](release-notes-1.4.0.md) for that release's behavior and retained
human-observation limits. A Windows port does not establish new browser,
model-quality, or migration claims.

## Release artifacts and deferred parity

Use the release workflow's evidence to identify the final source, wheel, sdist,
installed checks and distribution hashes. A build-only rehearsal does not publish
files. After publication, compare PyPI's file hashes with the publishing run and
verify the installed package. Earlier wheels and rehearsal artifacts retain
their own identities; a README change affects package metadata even when runtime
files are unchanged. Package publication does not deploy the separate Help or
deck materials.

The deferred full Windows parity claim still requires current production
storage and process-recovery qualification, live native-memory acceptance, Windows 11 desktop journeys under
standard user permissions, Windows Server 2022/2025 with Python 3.10/3.12, and
combined installed-wheel and documented CLI qualification. The
[readiness record](release-readiness-1.5.0.md#remaining-release-gates) tracks
these outstanding requirements separately from the candidate release checks.
The [release runbook](release-runbook.md) governs final preparation and separately authorized publication.
