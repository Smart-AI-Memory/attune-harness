# Move from Attune AI to Harness

Updated on October 30, 2026, for unreleased Harness 1.6.0 preparation.

Harness 1.6.0 requires Python 3.12 or later. Follow the
[installation guide](installation.md) to select an isolated runtime and check a
local result.

Attune AI is deprecated. Use Harness for new work and keep an existing working
setup while checking the workflows you need. The [historical 1.0.0 migration
guide](migration-from-attune-ai.md) retains its original September 27 scope and
observations.

<a id="candidate-160-migration"></a>

## Upgrade to 1.6.0

When published, install Harness 1.6.0 in a separate Python 3.12 environment.
Before then, use only the exact local candidate identified by the release owner;
published 1.5.1 remains available. No 1.5.2 release is planned. Keep the previous
runtime, original participant registry, memory sources, writer/hook settings and
saved tasks. Check the needed workflow before changing the runtime your host uses.

Command environment filtering is opt-in. Without an `environment` policy, command
participants retain full parent inheritance during the 1.6.0 notice window.
The selected release schedule starts the notice in 1.6.0, with removal no earlier
than 1.7.0. The runtime NOTICE and machine-readable register use that same
1.6.0/1.7.0 schedule.
This implementation continues to accept legacy configurations. Add named-variable grants through the participant
configuration's existing preparation and acceptance flow. Version 1.5.1 rejects
the new `environment` field, so keep its original registry separately.

The generation reader requires explicit selection and compatible existing state.
Keep your hydration writer and host hooks. A new Redis projection writer and RedisVL adoption remain excluded. This version does not supply a writer,
generation publication/cleanup or automatic fresh-session delivery.

To roll back, select the previous runtime and its original registry and reader
configuration. Keep saved approval records, Redis keys and memory source files
unchanged. Use the original runtime to inspect older tasks; there is no general
proof that a newer saved task can safely resume in an older runtime. Rollback
does not undo file effects, cancellation or external commands. Check the selected memory source's freshness before relying on it.

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
or the [host integration instructions](https://smartaimemory.com/harness/help/dependencies/#integrate-with-a-host)
for the selected integration.

## Choose one journey

Use the [current workflow map](supported-journeys.md) to select a procedure and
check its requirements. Preserve a working alternative until that exact
replacement has been validated in your environment.

| You use Attune AI for | Harness route | Keep or verify before switching |
| --- | --- | --- |
| Read raw, personal or curated memory files | [File-memory commands](cli-guide.md#memory): **`memory`** recall, resolve and refresh | Keep the existing writers and supported formats. Configure the intended roots; a reader is not a replacement writer. |
| Hydrate Redis and recall across sessions | [Redis memory and serving](cli-guide.md#memory) | Harness reads an existing hydrated Redis projection; 1.6.0 also offers an explicitly selected generation reader. Keep the writer, hooks, working settings and source files that maintain your chosen path. Check serving in an actual fresh host session before replacing a working setup. |
| Save memory or task intent explicitly | [Saved-memory lifecycle](memory-saving.md) | Saved entries retain revisions and history. Saving intent does not execute a task or automatically place that entry in fresh-session recall. |
| Plan, build, review, fix or test work | [Workflow selector](supported-journeys.md) and [CLI procedures](cli-guide.md) | Check the declared input profile, configured participants, protected checks and recovery path. Accept scope and grant execution separately. Deterministic software checks do not qualify every model or project. |
| Review source or consult several models | [Source review and roundtable](model-consultation.md) | Choose explicit configured identities and inspect the prepared scope. Installation and local seat checks authorize no paid calls. |
| Use host skills or MCP tools | [Plugin setup](codex-plugin.md) and [CLI integration](cli-guide.md) | Compare the exact skills, tools and schemas you use. Keep any required Attune AI capability that has no validated Harness replacement; installing Harness does not establish complete host parity. |
| Use executable extensions or Voyage | [Extension and retrieval procedures](cli-guide.md) | Inspect the exact artifact, signature, effective grants and provider requirements. Installation alone authorizes neither activation nor paid calls. |

## Check the current Windows profile

Harness 1.6.0 includes native Windows components for captured testing,
file-memory reads, saved storage and experimental native-memory transport.
Windows file-memory reads use the supported local NTFS path profile. Read the
[current Windows capabilities and limits](supported-journeys.md#windows-capabilities-and-reliability)
before selecting a journey.

These components do not establish full Windows parity. Complete saved-store
acceptance, strict descendant stop and recovery, live native-memory acceptance,
Windows 11 desktop and the declared PowerShell journeys retain their separate
gates. The current hosted profile covers Windows Server 2022/2025 with Python 3.12;
a historical Windows 11 standard-user smoke used x64 Python under ARM emulation.
Neither proves native ARM64 parity or every desktop/shell journey.
The [Windows reliability reference](windows-reliability.md) records the
requirements and evidence boundaries. Earlier Windows refusals remain part of
the historical guide; they are not the current capability map.

## Validate before replacing a working path

Record the actual Harness version, interpreter, host and operating system,
selected inputs and configuration, accepted scope, outcome and evidence
location. Exercise the needed interruption and recovery path without editing
saved approval or execution evidence. Retain the original environment as a
fallback until the replacement meets your requirements.

Read the [1.6.0 preparation guide](release-preparation-1.6.0.md)
for current evidence and final release gates. The [published 1.5.1 release](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.5.1)
retains its original artifacts and Python minimum. The [documentation archive](https://smartaimemory.com/harness/help/archive/)
retains older guides and preparation observations. The
[original migration ruling](specs/release-1.0/addendum-2026-09-23.md#d26-the-deprecation-is-a-notice)
remains historical context; the current deprecation direction does not change
existing artifacts, data or the validation requirements above.

**Next:** Open the [installation guide](installation.md), then choose one journey
from the [workflow map](supported-journeys.md).
