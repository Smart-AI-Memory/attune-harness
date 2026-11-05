# Harness 1.7.0 — release preparation

Version 1.7.0 is prepared in source and is not published by this change. It
requires Python 3.12 or later. The [readiness record](release-readiness-1.7.0.md)
separates candidate checks from the later exact-main release gate.
Published [1.6.0](../help/release-1.6.0.json) remains available with its original
source, artifacts and qualification limits.

## Keep legacy command environments

Command participants without an `environment` policy continue to inherit the
full parent environment in 1.7.0. This release explicitly postpones their
earliest removal from **1.7.0 to 1.8.0**. The first notice remains **1.6.0**.
The runtime notice, active deprecation register and migration instructions use
that schedule; the guard that rejects overdue active deprecations stays intact.
Historical 1.6.0 records retain the schedule announced at that time.

The `command-env-v1` profile remains opt-in. Grant exact variable names through
the participant's existing preparation and acceptance process. Environment
filtering is not an operating-system sandbox. See
[command environments](command-environments.md) and [migration](migration.md).

## Choose explicit OpenAI funding

The separate `openai` API adapter sends one bounded request after persisted
per-call admission and fresh `--allow-api-spend` authority. It never replaces an
existing native participant or automatically retries a subscription refusal
using API funding. Usage can be recorded while billing remains unknown.

The explicit `openai-plan` adapter adds app-owned OAuth/Keychain profiles and one
supervised HTTPS/SSE request per admitted turn. Its runtime is restricted to
**macOS arm64 / CPython 3.12.2** with the pinned `plan-oauth` dependencies. The
extra remains outside `all`. Connecting a profile, checking local metadata,
accepting a task and authorizing execution are separate actions. API seats in a
mixed operation still require fresh API-spending authority.

These paths have offline software evidence. **Real provider-account
qualification is not established for this release:** live consent, native
Keychain interoperability, account/model eligibility, quota, billing and model
quality remain unverified. Subscription identifies the plan OAuth route; it
does not promise free usage, identical native Codex allowance or a known balance.
Explicit funding on native `codex` and `claude` adapters remains refused.
Omitted legacy funding keeps inherited, unverified authentication.
Read [participant funding](participant-funding.md) before selecting a route.

## Retain the existing hydration setup

This release includes internal groundwork for authorized source capture,
complete-record secret checks and generation-payload accounting. It does not
yet provide a supported hydration command, Redis generation publication or
cleanup, or automatic delivery into a fresh Claude Code or Codex session.
Keep your current writer, memory sources and host hooks. The existing optional
generation reader remains separate; source-capture tests do not establish live
Redis publication or automatic recall.

## Follow the first plan and build

The [plan/build procedure](cli-guide.md#plan-and-build) explains preparation,
scope inspection, checkpoint acceptance, separate execution permission and
result inspection. It includes checkpoint-bound corrections and saved recovery
guidance. Demonstration workers and offline tests do not qualify every model,
project or independent user's understanding.

Existing Windows workflow, storage, process-recovery and desktop/PowerShell
qualification limits remain. The plan OAuth runtime is not supported on Windows.
See [supported journeys](supported-journeys.md) and [qualification](qualification.md).

## Install and retain rollback

Before publication, use the exact reviewed local wheel in a new environment.
After publication, select `attune-harness==1.7.0` explicitly; add `plan-oauth`,
Redis or Voyage only for the integration you intend to use. Follow the
[installation guide](installation.md) and keep the previous environment,
participant registry, saved work and memory setup intact.

The Claude marketplace and deployed Help Center remain on 1.6.0 until separately
authorized updates. This preparation does not create a tag, publish packages,
deploy documentation or update the live marketplace. Older release and tutorial
records retain their original version labels and evidence.
