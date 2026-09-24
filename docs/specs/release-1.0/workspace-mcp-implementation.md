# Workspace MCP and host plugins — implementation note

September 24, 2026. Implements H1/M1 and H2/H5/M2 under D30, brought
forward by Patrick's instruction to build these before the lifecycle gates.
The steering-cards draft is unrelated and remains non-executable.

## Cases and boundaries

- Keep accepted retrieval invocations and their schemas unchanged. Workspace
  mode has an explicit project and fresh state directory; reject mixed profile
  arguments before opening a store. Plugin launches may use the host's current
  project directory and a freshly allocated private state subdirectory.
- Expose exactly the three existing command-workspace tool names and schemas.
  Use the carried host and Spec adapter for nonce, revision, contract, replay,
  terminal and project-path validation. Never add another action authority.
- Return the same HTML/Markdown render and forms bridge metadata. Persist the
  session lifecycle and nonce-free host events. A failed session-record write
  stops dispatch. Record dropped host events truthfully; they are not receipts.
- Tool arguments cannot change the startup project or state directory. Serialize
  calls, bound serialized input, and reject unknown tools and malformed values.
  No participant, provider, paid dispatch or fabricated lifecycle approval.
- Plugin and CLI intake/presentation carry no `attune` imports. Until M3 lands,
  the skill stops at lifecycle gates and reports the missing command. Existing
  attune-ai skills have drifted: cross-review/smart-test must be adapted rather
  than copied with unavailable imports. No marketplace publication in this PR.

## Disposable probe

A scratch temporary-project probe using the installed pinned forms package and
the carried host opened Spec intake, returned all 11 render fields plus the
dynamic-surface bridge descriptor, consumed `create_spec`, and refused replay
with `command workspace is not awaiting a bound action`. No model call or real
project mutation occurred. Source inspection confirms the old MCP handlers are
thin calls to the same host, followed by `mcp_app_result`.

## Verification planned

Real SDK stdio discovery and actions, schema comparison against the original,
nonce/revision/replay/terminal mutations, session record inspection, bounded
input, persistence failure, unchanged retrieval tests, plugin manifest checks,
full suite and installed-wheel platform qualification. Fresh-host display
acceptance remains separate and will need Patrick's Claude/Codex sessions.

## Rejected alternatives

- Installing Attune AI behind the new plugin would hide the missing port.
- Reimplementing workspace validation would duplicate the reviewed authority.
- Pretending missing lifecycle checks passed would allow unverified execution.
- Reusing a fixed session directory would collide across host restarts.

## Port deviations found by probes

Importing `attune_forms.mcp_server` under MCP 2.2.0 raises AttributeError at
its MCP 1.x decorator registration. The response schema is therefore carried
as pure data; the shared app resource comes from the independent `mcp_app`
module. The intake template validates provider registration even when passed
candidate overrides; static derived options preserve its form shape without
mutating global provider/template registries. Original sources were read at
Attune AI b769dc2e81c432553a87010e2658508722120317.

The shared plugin uses the candidate executable on the launcher PATH rather
than resolving published 0.6.0 with uvx: 0.6.0 cannot run this new profile.
Release versioning and marketplace distribution remain separate release work.
The plugin lives at `plugin/attune-harness/` so its directory and manifest name
agree with the Codex ingestion contract. No user installation is replaced.

## Independent review corrections

GPT-6-sol found that exposing the carried trusted-publisher method to an MCP
client made invented lifecycle PASS events and bare-plan resume sufficient to
advance. Both were reproduced locally. M1/M2 now refuse lifecycle events,
resume and execution publication at the server boundary until M3 can verify
real gate evidence. Real test evidence alone does not bypass that gate. This
limits the candidate to intake and draft creation; end-to-end execution is not
qualified. MCP Apps initialization now advertises the shared UI extension,
which the real SDK test checks alongside the resource and tool metadata.
