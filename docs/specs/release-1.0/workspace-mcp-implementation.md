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

A second review found that the internal trusted publisher accepted nonexistent
draft paths. The MCP boundary now verifies every artifact is a regular file
inside the fixed project and parses the bounded plan to compare task IDs in
order. Publisher prose in `probes` remains a caller assertion, not test or
lifecycle evidence. Missing drafts, directories, escaping paths, empty plans
and invented task IDs are refused without advancing the workspace.

## Accepted task contents — PR 141 P1 correction

The disposable regression in `/private/tmp/pr141-result-probe` changed the
objective of an already completed task without changing its ID or state comment.
The old CLI printed PASSED for the rewritten task, reproducing review finding
`discussion_r4095010101`. Test-run freshness alone cannot establish which Spec
text was accepted.

Persist an optional map of task IDs to canonical parsed-task content digests at
the state writer's acceptance boundary: only newly completed tasks carrying test
receipts receive a digest. Preserve existing bindings on subsequent saves; never
retroactively bind historical completions or refresh a digest from edited text.
The digest includes all fields returned by `DecomposedTask.to_dict`; duplicate
IDs cannot establish a binding. Legacy states remain readable but result display
refuses missing bindings. Existing bound completions must keep their task text
and accepted receipt on resave. This records local acceptance, not a signature
or authorization against an owner who deliberately rewrites the state file.

Read the bounded plan once for both tasks and state. Result display requires
exactly one selected task, its saved content digest and its existing exact test
receipt binding before producing output. Cases: unchanged task passes; changed
name/objective/files/checks/risks/dependencies, missing binding, duplicate IDs,
changed receipt and resaving an edited accepted task fail. Ordinary progress saves
preserve the binding. No lifecycle or execution path is enabled.

Rejected: recomputing a digest during presentation (would bless the edit),
retroactively stamping legacy completions (would fabricate acceptance history),
and using only mtime or task ID (neither binds the displayed task contents).

A present but unreadable prior state is not a fresh acceptance: binding new test
receipts over it is refused. This digest proves post-persistence task freshness,
not which task ran before that save; trusted execution-boundary provenance stays
with M3.

Independent review reproduced a two-save bypass: remove a bound completion, then
re-add the old receipt against rewritten text. Progress saves therefore cannot
remove any prior completion, including an unbound legacy completion. A deliberate plan reset remains the explicit
`clear_state` operation and is not a progress-save shortcut.

The same rule applies to unreadable history: every progress save over a present
unreadable comment is refused, including an empty-state save. Otherwise two
saves could erase the unreadable history and mint a new binding from old evidence.

## Untrusted presentation — PR 141 P2 correction

The disposable `/private/tmp/pr141-render-probe` passed a repository-controlled
plan through the real CLI. Its Markdown table contained unescaped pipes and
bold markers, and a literal ESC control from the malformed-XML fallback. XML
escaping alone is insufficient because the supported fallback preserves text.

Use one literal-text formatter for every dynamic task field in table, detail
and result views, including file descriptions, checks, risks, dependencies and
the evidence path. Collapse whitespace to one line, remove Unicode control and
format characters (including terminal ESC and bidi controls), escape HTML and
Markdown delimiters, and keep only the renderer's own structural Markdown.
Avoid wrapping escaped arbitrary paths in backtick spans: backslashes do not
protect backticks inside such spans. Ordinary prose and task statuses keep their
meaning; input files and evidence are never rewritten.

Cases: injected rows/headings, pipe/backtick/link/HTML payloads, CR/LF/tab,
ANSI/OSC and bidi controls, every detail field, and checked result headers/paths.
Exercise the actual malformed-XML CLI route as well as the pure presenters.
Reject the alternative of sanitizing only the table or relying on the parser:
detail/result renderers and parser fallback share the same trust boundary.

Independent inspection found the same control characters in parser diagnostics,
including task IDs and rejected raw XML blocks. Diagnostic arguments now quote
nonprinting characters, retaining normal warning text and line structure while
preventing terminal controls from leaking through stderr.

The fixed brackets around a risk severity also need escaping: severity `x`
inside `- [x]` becomes a checked GFM task-list item even when the field itself
is escaped. Keep the visible brackets as literals and cover x, X and whitespace
severities so task text cannot borrow the renderer's delimiters.
