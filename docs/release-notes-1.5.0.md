# Attune Harness 1.5.0 release notes

**DRAFT — UNRELEASED.** Version 1.5.0 is planned after the full
[Windows parity specification](specs/windows-parity/README.md) is complete.
The runtime version remains `1.4.0`. These notes describe the release target
and prepared components; they do not announce Windows qualification or a
published 1.5.0 package. See the [readiness record](release-readiness-1.5.0.md)
for the evidence and open gates.

## Planned Windows changes

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
- **Save memory and task intent.** The production Windows port is prepared in
  [PR #275](https://github.com/Smart-AI-Memory/attune-harness/pull/275), with
  qualification still open. The target retains revisions, withdrawn history,
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

## Installation and upgrade

Version 1.5.0 is not available yet. To use published 1.4.0 now, follow the
[installation guide](installation.md):

```sh
uv tool install 'attune-harness==1.4.0'
```

Python 3.10 or later is required. Use an isolated runtime; Harness and Attune AI
require different MCP SDK versions. Redis and Voyage remain optional, and the
experimental `memory-native` profile is separate.

Before upgrading an existing installation, inspect its selected version and
path using the installation guide. Preserve saved task directories and retained
evidence environments. The final 1.5.0 installation and upgrade instructions,
including any migration limits, remain pending final candidate qualification
and publication. No 1.5.0 installation command is supplied in this draft.

## Workflows and compatibility

Use the existing commands and explicit configuration; this release target does
not introduce a separate Windows workflow.

| Goal | Existing entry points | Guidance |
| --- | --- | --- |
| Check a captured change | `test`, then saved checkpoint acceptance; `test --from-task` for a completed task | [CLI guide](cli-guide.md); [Windows command walk](specs/windows-parity/README.md#testing-repair-and-build) |
| Read configured memory | `memory recall`, `memory resolve`, `memory refresh`, and `memory serve` | [CLI guide](cli-guide.md); [file-memory command walk](specs/windows-parity/README.md#file-memory-reads) |
| Save memory or task intent after the port qualifies | `memory saved` lifecycle, history, and pending-review operations | [Saved-store command walk](specs/windows-parity/README.md#saved-memory-and-tasks) |
| Prepare a native-memory proposal | `memory create`, with separate `memory execute` authority and configuration | [Native-memory command walk](specs/windows-parity/README.md#native-memory-proposal-transport) |

These are command references, not a completed 1.5.0 walkthrough. The final
installed-wheel journeys must verify the commands, printed continuations, and
shell quoting on the delivered candidate. Existing preview and acceptance
boundaries, saved schemas, historical receipts, and explicit execution grants
remain part of the parity requirements.

The browser companion retains its documented forms boundary: saving answers
and approving a request do not execute work. Read the
[1.4.0 notes](release-notes-1.4.0.md) for that release's behavior and retained
human-observation limits. A Windows port does not establish new browser,
model-quality, or migration claims.

## Release gates

Full parity still requires current production storage and process-recovery
qualification, live native-memory acceptance, Windows 11 desktop journeys under
standard user permissions, Windows Server 2022/2025 with Python 3.10/3.12, and
combined installed-wheel and documented CLI qualification. The
[readiness record](release-readiness-1.5.0.md#remaining-release-gates) tracks
these requirements. The [release runbook](release-runbook.md) governs final
preparation and separately authorized publication.
