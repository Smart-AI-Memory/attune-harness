# Harness 1.6.0 — unreleased

This is the local release-note draft for the next release after published 1.5.1.
No 1.5.2 release is planned. No 1.6.0 package, tag or deployed Help route is
announced by this document.

## Keep work moving on Windows

Use the supported build, repair and captured-testing workflows within their
local NTFS and dedicated-checkout profiles. When child stop/wait cannot be
confirmed, saved error guidance preserves the original cause and unknown-effects
status. Inspect saved task/process/file evidence before continuing; do not infer
termination, rollback or permission to redispatch from an error.

PR #320 also improves software verification: collection-time module skips are kept
separate from executed-case admission, workers have private pytest caches, and
signing fixtures retain bounded startup-error evidence. These changes retain
existing assertions and native-operation deadlines. They do not prove the cause
of every historical failure or qualify full Windows/POSIX parity.

The merged repair's PR cohort passed Windows Server 2022/2025 installed and
full-source profiles, separate `windows-latest` and `ubuntu-latest` supplemental coverage jobs, native-owner/SDK and required
checks. Main-event CI and exact final 1.6.0 artifact qualification remain separate.
See [preparation evidence](release-preparation-1.6.0.md).

## Choose which credentials commands receive

The opt-in `command-env-v1` policy grants exact environment-variable names and
retains names-only audit metadata. For example, a trusted command can receive
`SERVICE_TOKEN` without inheriting unrelated parent credentials. Existing
configurations without the policy still inherit the full parent environment.
Environment filtering is not an operating-system sandbox.

The selected notice schedule starts in 1.6.0, with removal no earlier than 1.7.0.
Current emitted NOTICE and the machine-readable register still say 1.5.2/1.6.0;
that source integration item must be corrected before release. This draft does
not claim it has been repaired. See [command environments](command-environments.md).

## Trace memory to its source

The explicitly selected generation reader identifies the snapshot and source
associated with its results. Legacy reads remain the default. Keep the writer,
source files and startup hooks maintaining the path you use. Writer #318/RedisVL,
generation publication/cleanup and automatic fresh-session delivery are excluded.
The Redis extra remains pinned to redis-py 5.3.1. Live Redis+Search verification for the final 1.6.0 artifact is incomplete; optional services and paid providers
need their own setup and authority.

## Install, upgrade and keep a rollback path

Version 1.6.0 requires Python 3.12 or later. Until it is published, use published
1.5.1 or the exact reviewed local candidate provided by its owner. Install a
replacement in a separate environment; preserve the original runtime, registry,
saved tasks, approvals, memory sources, Redis data and writer/hook settings.
Published 1.5.1 retains Python 3.10 compatibility and rejects the new command
`environment` field, so keep its original configuration separately.

Inspect older tasks with their original runtime. Changing runtimes does not
prove safe continuation, and rollback does not undo effects. Follow
[installation](installation.md) and [migration/rollback](migration.md).

## Unavailable features and limits

Browser forms support existing-task intake, saved answers and request review;
browser build dispatch and execution resume remain unavailable. Use the CLI
workflow after inspecting its accepted scope. Native Windows support is bounded
by the documented profiles. The historical Windows 11 standard-user smoke used
x64 Python under ARM emulation; native ARM64 and every desktop/shell workflow
are not qualified. Read [supported workflows](supported-journeys.md) for refusals
and next actions. Missing optional dependencies are reported; installation does
not silently configure a service or authorize paid calls.
