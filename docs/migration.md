# Move from Attune AI to Harness

Updated on October 25, 2026, for published
[Harness 1.5.1](https://pypi.org/project/attune-harness/1.5.1/). Follow the
[installation guide](installation.md) to select an isolated runtime and check
a local result.

Attune AI is deprecated. Use Harness for new work. Keep a working Attune AI
setup while you validate the Harness journeys you need. Deprecation does not
qualify saved-work migration or establish complete host or Windows parity. The
[historical 1.0.0 migration guide](migration-from-attune-ai.md) preserves the
September 27 baseline and its original limits; use the current guidance below
for installation and capability decisions.

## Keep environments and evidence separate

1. Keep Attune AI in its existing environment. Install Harness separately;
   the packages pin different MCP SDK versions.
2. Preserve existing memory files, writer configuration, saved task directories
   and retained evidence environments. This guide requires no conversion or
   deletion of those records.
3. Inspect older saved work with its original runtime before choosing another
   version. Installing a new runtime does not prove that an older task can
   continue with unchanged meaning or execution permissions.

Installing the Python package does not install the host plugins or replace an
existing host configuration. Follow the [Codex plugin guide](codex-plugin.md)
or the [Claude installation instructions](installation.md)
for the selected integration.

## Choose one journey

Use the [current workflow map](supported-journeys.md) to select a procedure and
check its requirements. Preserve a working alternative until that exact
replacement has been validated in your environment.

| You use Attune AI for | Harness route | Keep or verify before switching |
| --- | --- | --- |
| Read raw, personal or curated memory files | [File-memory commands](cli-guide.md#memory): **`memory`** recall, resolve and refresh | Keep the existing writers and supported formats. Configure the intended roots; a reader is not a replacement writer. |
| Hydrate Redis and recall across sessions | [Redis memory and serving](cli-guide.md#memory) | Keep the existing Attune AI hydration hook in its own environment. Harness reads the configured hydrated data; it does not replace that writer. Validate serving in an actual fresh host session. |
| Save memory or task intent explicitly | [Saved-memory lifecycle](memory-saving.md) | Saved entries retain revisions and history. Saving intent does not execute a task or automatically place that entry in fresh-session recall. |
| Plan, build, review, fix or test work | [Workflow selector](supported-journeys.md) and [CLI procedures](cli-guide.md) | Check the declared input profile, configured participants, protected checks and recovery path. Accept scope and grant execution separately. Deterministic software checks do not qualify every model or project. |
| Review source or consult several models | [Source review and roundtable](model-consultation.md) | Choose explicit configured identities and inspect the prepared scope. Installation and local seat checks authorize no paid calls. |
| Use host skills or MCP tools | [Plugin setup](codex-plugin.md) and [CLI integration](cli-guide.md) | Compare the exact skills, tools and schemas you use. Keep any required Attune AI capability that has no validated Harness replacement; installing Harness does not establish complete host parity. |
| Use executable extensions or Voyage | [Extension and retrieval procedures](cli-guide.md) | Inspect the exact artifact, signature, effective grants and provider requirements. Installation alone authorizes neither activation nor paid calls. |

## Check the current Windows profile

Published 1.5.1 includes native Windows components for captured testing,
file-memory reads, saved storage and experimental native-memory transport.
Windows file-memory reads use the supported local NTFS path profile. Read the
[current Windows capabilities and limits](supported-journeys.md#windows-capabilities-and-reliability)
before selecting a journey.

These components do not establish full Windows parity. Complete saved-store
acceptance, strict descendant stop and recovery, live native-memory acceptance,
Windows 11 desktop and the declared PowerShell journeys retain their separate
gates. The [Windows reliability reference](windows-reliability.md) records the
requirements and evidence boundaries. Earlier Windows refusals remain part of
the historical guide; they are not the current capability map.

## Validate before replacing a working path

Record the actual Harness version, interpreter, host and operating system,
selected inputs and configuration, accepted scope, outcome and evidence
location. Exercise the needed interruption and recovery path without editing
saved approval or execution evidence. Retain the original environment as a
fallback until the replacement meets your requirements.

A passing software test or a completed deterministic example does not establish
user acceptance or complete migration. The non-programmer migration observation
and broader host acceptance remain open. Read the
[1.5.1 readiness record](release-readiness-1.5.1.md) for current release gates and
the [release plan](project-plan.md) for the remaining acceptance work. The
[original migration ruling](specs/release-1.0/addendum-2026-09-23.md#d26-the-deprecation-is-a-notice)
remains historical context; the current deprecation direction does not change
existing artifacts, data or the validation requirements above.

**Next:** Open the [installation guide](installation.md), then choose one journey
from the [workflow map](supported-journeys.md).
