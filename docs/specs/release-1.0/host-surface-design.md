# The host surface: spec on Harness end to end, design note

Draft of September 23, 2026, the night the telemetry was read. It is the
first row of the deprecation milestone that [D26](addendum-2026-09-23.md)
named and the plan's 4.8 row points at: the Claude Code plugin's `/spec`
skill, which today runs on attune-ai's MCP server and Python, running on
Harness alone, so that the deprecation notice can go out without taking
away the workflow its one certain user relies on most. Like the design
notes before it, it puts what was read first, then the design, then the
decisions that are Patrick's. Nothing here is authorized until he rules;
the rulings go in the release addendum, numbered on from D29.

## What was read

**The telemetry.** Every local transcript of the last sixty days, 586
sessions, and attune-ai's own telemetry for thirty. By invocation the skills
Patrick reaches for are cross-review (85), retro (50), roundtable (50), the
two release skills (38 and 37) and docs-outbox (23); spec is invoked ten
times. By weight spec is the whole: 72 spec directories and 44 plans in
attune-ai, 20 more in attune-rag, and the forms and workspace calls that
dominate attune-ai's server traffic are spec's. Spec is entered rarely and
inhabited for hours. Both readings are true, and the second is the one that
decides what a deprecation notice would take away.

**What each skill needs from attune-ai**, from the skills' own text in the
installed plugin (16.4.0):

- `/spec`: the intake form, `python -m attune.elicitation.spec_intake` and
  its `--compose` seam; the reader, `attune.pipeline.spec_reader.read_spec`;
  the state and presentation helpers in `attune.spec` (`load_state`,
  `save_state`, `find_resumable_plans`, `present_tasks`,
  `present_task_detail`, `present_task_result`, `format_progress_bar`); the
  per-task gates, `PipelineOrchestrator.run_gates_for_task`, which runs a
  model-backed quality gate, the task's tests and a model-backed simplify;
  the lifecycle gates, `attune gates check tasks|execution --spec <slug>
  --changed <paths>`, with G5 exit semantics; and, when the host has them,
  the three command workspace tools of attune-ai's MCP server,
  `command_workspace_open`, `command_workspace_collect_action` and
  `command_workspace_publish`, opened on adapter `spec`. The forms it
  renders come through `elicitation_*`, which attune-forms' own MCP server
  provides independently of attune-ai. `help_lookup`'s preamble and the
  `context_get`/`context_set` interaction preference are conveniences on
  attune-ai's server.
- `/roundtable`: the same three workspace tools, on adapter `roundtable`.
- `/fix`: attune-ai's `fix_workspace_preview` and
  `fix_workspace_collect_action`, and `attune fix`; Harness's `fix` is its
  own scoped repair with a different contract.
- cross-review, smart-test, run, release-execute and attune-release-check:
  Markdown plus `gh` and `uv`. Nothing from attune-ai's Python.

**What Harness already carries.** The command workspace host,
`command_workspace.py` (715 lines, #54), with the lease, the one-time
action nonce, the events sink and the eviction; the Spec adapter,
`spec_workspace.py` (1,057 lines, #58), with every stage and, since D24,
the execution half walked by `plan --accept`; the four intake names in
`spec_intake.py` (#55), without the form builder or its command-line seam;
`spec_state.py` with `load_state`, `save_state`, `clear_state` and
`find_resumable_plans` (#42); `spec_tasks.py` with `parse_tasks` and
`read_spec` (#34, #98); `spec_handoff.py`, which binds Harness's own `test`
and work receipts to the Spec task gate as `test_evidence`; and
`mcp_server.py`, a stdio server that today serves one profile, retrieval,
bound to an accepted request and a participant's tool grants. attune-forms
0.17.0, pinned in the base, provides `workspace_to_widget_html`,
`workspace_to_markdown`, `collect_workspace_action` and `mcp_app_result`,
the same calls attune-ai's server makes.

**What Harness does not carry.** An MCP surface for the host it carries;
the intake form builder (attune-ai's `spec_intake.py` is 229 lines against
Harness's 99); the presenters (172 lines); the lifecycle gates (756 lines
across `gates/lifecycle`, plus a 44-line command: `symbol-reality`,
`falsifiability` and `format-lint`, a ledger, an activation policy and the
G5 exit codes); the roundtable adapter (703 lines); the fix workspace
adapter; the plugin itself, a `.claude-plugin/plugin.json`, a `.mcp.json`
that launches the server with `uvx`, and the skill files.

**Patrick's own note.** `~/.attune/host-surface-parity-next-milestone.md`,
September 6, is attune-ai's brief for one measured Codex form interaction
under its host-surface-parity spec (D10 to D13 there). Two of its rules
carry over whole: build on the existing seams, never a parallel routing or
validation mechanism; and accept a surface on measured display evidence,
message-to-visible-card timing recorded per trial with cold and warm
strata, every attempted trial kept, and no claim beyond the observed range.

**What the plan already says.** 4.8 writes the migration page during the
candidate period, listing per journey what Harness carries and what it does
not, the plugin's skills among the latter; D26 makes the deprecation a
notice; the plan names the plugin's skills and the hydrate writer as the
deprecation milestone's first rows. This note is the design behind the
first of those rows.

## The design

Spec on Harness end to end means the skill's five stages, create, review,
approve, execute and resume, run with nothing from attune-ai on the path,
through Harness's own host, and are seen by the person the way they are
seen today: the widget where the host renders it, the Markdown where it
does not.

### H1. The workspace surface: three tools over the carried host

`attune-harness mcp-serve --workspace --project <root> --state-dir <dir>`
starts a second server profile beside retrieval. It registers one
`CommandWorkspaceHost` with the Spec adapter over the project root, writes
the host's events to `<state-dir>/workspace-events.jsonl` as `plan
--accept` does (D14: renders and consumed actions, never the nonce, and
since D24 the `origin: walk` mark on walked stages), and exposes exactly
three tools with attune-ai's names and input schemas, so the skill's text
changes only in where the server comes from: `command_workspace_open`
(`adapter_id`, `intake`, optional `workspace_id`),
`command_workspace_collect_action` (`response`) and
`command_workspace_publish` (`workspace_id`, `event`). Each returns what
attune-ai's returns, `success`, the render's `to_dict()` (workspace id,
revision, view, contract hash, nonce, terminal flag, event sequence, HTML
and Markdown) and `mcp_app_result(...)` from attune-forms, or `success:
false` with the host's `problems`. No participant, no budget, no paid
dispatch, no provider: the profile's `mcp-inspect` record says so, and the
tool list is pinned per protocol version as 4.1.6 requires. The session
record and its envelope get golden rows.

### H2. Intake and presentation, ported

`spec_intake.py` gains `build_spec_intake_form` and the `--compose` seam as
`attune-harness spec intake` (form out) and `spec intake --compose`
(answers in, contract block out), attune-forms rendering the form; the
presenters become `spec present tasks|task|result|progress` over the
carried reader and state, or the skill uses the workspace's own Markdown
where the two overlap. Small ports, read against their originals line by
line as the brief's carry step requires.

### H3. Task evidence: Harness's receipts, not a ported quality gate

attune-ai's `run_gates_for_task` runs a paid quality gate, the task's tests
and a paid simplify, and folds them into one severity and score. Harness
does not port that. The task's result comes from receipts Harness already
produces: `attune-harness test` on the task's change, bound through
`spec_handoff.bind_test_evidence` as the `task_result`'s `test_evidence`,
severity from the outcome; and, where the task's change touches `src/`, the
different-model review the brief already requires, recorded in the pull
request as today. No model is called by the flow itself. Decision 4 asks
whether that is the contract or whether the quality gate follows as a
paid, opt-in participant later.

### H4. The lifecycle gates, ported as `gates check`

`attune-harness gates check tasks|execution --spec <slug> --changed
<paths>` runs the three baseline gates over `docs/specs/<slug>/`,
`symbol-reality` (every path a document cites exists), `falsifiability`
(acceptance lines are testable statements) and `format-lint`, appends each
receipt to the ledger and exits per G5: `BLOCKED` 2, `CHAIR_REQUIRED` 1,
else 0. The receipts are the `lifecycle_gate` events the Spec adapter
already consumes, so the skill publishes them unchanged; D24's readiness
receipts stay the execution boundary's own. The activation policy's
waiver syntax and batching threshold are carried as written. Until this
lands, the skill may keep calling attune-ai's command for the gates alone;
decision 5.

### H5. The plugin

A Claude Code plugin named `attune-harness`, kept in this repository under
`plugin/`: `.claude-plugin/plugin.json`, a `.mcp.json` whose one server is
`uvx --from attune-harness attune-harness mcp-serve --workspace`, and the
skills. The `/spec` skill is attune-ai's, rewritten only where it names a
source: the Harness intake and presenters, `gates check`, the Harness
server, `test` receipts as task evidence, and the workspace as the only
lifecycle surface (the `AskUserQuestion` fallback stays for hosts without
tools). cross-review, smart-test and the release skills are copied as they
are. The plugin is versioned with the package and published to the
marketplace when the notice goes out; before that it is installed from the
checkout for dogfooding. Decision 2.

### H6. Roundtable and fix, the next rows

`/roundtable` needs only the roundtable adapter registered on the same
host; it is a 703-line port with its own review and follows H1 as the
milestone's second row. `/fix` on Harness is a different contract, scoped
repair with its own intake, and is a parity question for the migration
page, not a port; the page says what changes for a user.

### H7. Evidence

Deterministic first: the host's tests already cover nonce, revision,
contract and replay refusals; the surface adds a test that drives the
three tools through the real forms artifact end to end, from intake to a
completed task with a bound `test` receipt, and a mutation set in the shape
of #110's (a dropped nonce, a replayed action, a stale revision, an event
published to a terminal workspace). Then the measured evidence Patrick's
brief asks for: in Claude Code, for the review stage's card, five cold and
five warm trials with the sent-message-to-visible-controls time from the
recording, every trial kept, the range stated as observed and nothing
beyond it. Recorded as a receipt under `docs/journeys/`, not a CI gate.

### H8. The freeze

Every item above is additive: new tools under a new profile, new verbs,
new files. Under D25.2 none restarts the candidate, and the new tool list
becomes one more per-version fixture under 4.1.6. The envelope rows the
surface adds are pinned before the notice, not before `rc1`.

## Order and size

Three reviewed cycles for spec end to end, then the plugin: H1 (the
surface, with H7's deterministic tests and the golden rows); H2 with H5
(the ports and the plugin skeleton, the skill rewritten); H4 (the gates).
H6's roundtable is a fourth. They run during the candidate period, after
the freeze's first two cycles and beside 4.3, and none is on the path to
`rc1`; the notice follows the day `/spec` runs on Harness end to end in
Patrick's own sessions, which is D6's test for the users who lose
something. If October holds for 1.0.0, that day is in November, and D26's
"within days" becomes "within weeks", with the ruling unchanged.

## Decisions for Patrick

1. **Scope of "spec on Harness".** Recommended: the five stages through
   Harness's host, intake and gates, with `test` receipts as task evidence
   and no model on the path; roundtable the next row; fix a migration-page
   entry. Alternative: the skill as it is, keeping attune-ai's server behind
   it under the notice, which leaves the most-used workflow on a deprecated
   dependency indefinitely.
2. **Where the plugin lives.** Recommended: `plugin/` in this repository,
   versioned with the package, installed from the checkout until the notice
   and published to the marketplace with it. Alternative: a separate
   repository, which doubles the release mechanics.
3. **Tool names.** Recommended: attune-ai's three names and input schemas
   unchanged, so the skill and any other consumer move by changing the
   server; the retrieval profile keeps its `harness.` prefix. Alternative:
   prefixed names, which is cleaner and breaks every existing caller.
4. **Task evidence.** Recommended: `test` receipts through `spec_handoff`,
   severity from the outcome, and the different-model review for `src/`
   changes as today; the paid quality gate and simplify are not ported.
   Alternative: port them behind an opt-in participant later, as a separate
   proposal.
5. **The gates.** Recommended: port the three baseline gates, the ledger
   and the G5 exits as `gates check`, one cycle, since the receipts feed
   the adapter unchanged. Alternative: keep calling attune-ai's command for
   the gates alone until after the notice.
6. **Timing.** Recommended: the three cycles during the candidate period,
   beside 4.3 and after the freeze's first two cycles; the notice when the
   skill runs end to end on Harness in Patrick's sessions. Alternative:
   before `rc1`, which adds three cycles to the chain and puts October at
   risk.
7. **Evidence.** Recommended: deterministic tests as the CI gate, and the
   measured display receipt from Patrick's brief as acceptance evidence,
   not a CI threshold. Alternative: deterministic tests only.

## Evidence the row ends with

`mcp-serve --workspace` with its three tools and its record's golden rows;
`spec intake`, `spec present` and `gates check` with their tests; the
plugin under `plugin/` with the rewritten `/spec` skill and the copied
skills; the end-to-end test through the real forms artifact and its
mutation set; the measured display receipt under `docs/journeys/`; the
migration page's spec, roundtable and fix rows written from this note; and
one of Patrick's own specs run on Harness from intake to a completed task.

## Size

Three cycles plus the plugin's packaging for spec, a fourth for
roundtable; each cycle that touches `src/` reviewed under
[the brief](../../review-brief.md) and logged in
[the findings log](../../review-findings.md). The host and the adapter are
already carried and reviewed, so the surface is thinner than its size
suggests; the gates are the one genuine port.
