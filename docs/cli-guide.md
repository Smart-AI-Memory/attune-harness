# CLI guide

Full usage for the `attune-harness` commands: arguments, exit codes, supported
profiles and recovery controls. The [README](../README.md) gives the short version.
This text was moved here from the README for the 0.1.0 release so that the package
page can stay brief. Nothing was dropped. Links were adjusted for this location and
install commands now name the published package.

## How people and AI work together

People can direct or intervene in work through the task verbs. **Specs are the
principal authoring form for complex features and constructs**, with human
decisions at the applicable quality gates. The AI uses operational commands to
carry out accepted work and produce evidence.

The design calls for Harness to choose the authoring form that fits the work:

| Authoring form | When it fits |
|---|---|
| Clear one-shot prompt | The request already expresses a bounded, understandable task |
| XML-enhanced prompt | Explicit structure makes the instructions, constraints or expected output clearer |
| Spec | Complex features or constructs need durable requirements, planning and acceptance criteria |

These are alternative forms, not mandatory steps through every level. Humans can
use task verbs with any form; the form does not change existing authorization or
gate requirements. The work contract selects among these forms using explicit work requirements.
The CLI now provides bounded plan/build journeys alongside review/fix intake and
scoped test execution; native planning/building quality still needs qualification.

Many commands primarily serve the AI and its integrations. Users can inspect or
operate them directly when useful; learning their syntax is not the onboarding
goal. The compact CLI catalog presents the execution interface:

```text
attune-harness --help

Task execution
  plan         Define intent and accept its scope
  build        Execute accepted tasks and protected checks
  review       Assess a document against project evidence
  fix          Repair scoped files and check the result
  test         Test a captured change and retain the evidence

Task controls
  status       Inspect a saved task
  resume       Continue a saved task

AI tools and integration
  --help-all   Browse operational tools and compatibility commands
```

For direct use, `attune-harness COMMAND --help` explains the options.
The full catalog groups older compatibility commands separately; existing scripts
keep their original commands and arguments. Ship and the approved reflect follow-on remain planned routes.

Development reading: [one blog draft on controls, potential savings and the user
journey](blog/controls-savings-user-journey.md), with
[warning and guidance examples](user-guidance-examples.md). Proposed message
copy is labeled separately from existing behavior and measured results.

For ongoing content maintenance, use the [opportunity log](opportunity-log.md)
and [documentation review checklist](documentation-maintenance.md).

## Plan and build

An agent can author a work request from the user's goal. The request records
`intent` (goal, context, exact file scope, constraints, acceptance criteria and
questions), explicit participant assignments and any dependent tasks. Complex
work can import an existing Spec using `--import-plan`; import grants no authority.
A plan from another project, outside the checkout, is imported by naming it
with `--allow-outside-project` beside `--import-plan` (spec authority Task 5,
D4): the plan is read once through `spec_state` (schema versions 1 and 2; any
other is refused with the next action) and `spec_legacy`, converted exactly
as the implicit import is, and the conversion leaves a receipt, one JSON line
per conversion in `import-receipts.jsonl` beside `record.json`, with the path
as given (in the command line's normalised spelling) and as resolved, the
file's SHA-256, the state comment read, or whether one was present and
ignored, what was mapped, what was not, and the time. A `--reimport` of such
a task, one whose bound plan lies outside the project, appends a second line;
a receipts file that cannot take the line, full, linked or not a regular
file, refuses the conversion before anything is saved, with the next action.
A plan the flag names that resolves inside the project is refused: import it
without the flag. The plan is only read. Without the flag a plan outside the
project, or behind a symlink, is refused as before. The sequence with its
envelope, its receipt and its refusals is
[the R4 journey](journeys/r4-legacy-spec-state.md).
For construction, freeze the supported effect manifest and protected verification
commands before accepting the work. See [the contract](specs/plan-build/work-contract.md)
and [bounded build profile](specs/plan-build/dependent-build.md).

```bash
attune-harness plan --request work.json --project ./checkout \
  --config participants.json --task-dir /tmp/my-work
attune-harness plan --request work.json --project ./checkout \
  --config participants.json --task-dir /tmp/my-work \
  --import-plan ~/other-project/.claude/plans/feature.md --allow-outside-project
attune-harness plan --task-dir /tmp/my-work --run --allow-external
attune-harness plan --task-dir /tmp/my-work --stage --checkpoint CURRENT_CHECKPOINT
attune-harness plan --task-dir /tmp/my-work --accept --checkpoint CURRENT_CHECKPOINT
attune-harness build /tmp/my-work --allow-external --max-operations 4
attune-harness status /tmp/my-work
attune-harness resume /tmp/my-work --allow-external
```

Use the checkpoint returned by the preceding command each time. `--run` asks the
configured planner for a proposal; `--stage` makes it a new unaccepted draft.
`--accept` submits the explicit console choice through Harness's own Spec
collector, after walking the workspace's execution stages: the approval, the
execution gate whose receipts are the draft's readiness checks, then the task
gate the choice decides; a draft the gate blocks is refused in the gate's
words. The forms package that renders the decision is part of the base install
since 0.4.0 (before that, the `review` extra); Attune AI is not needed, and
core imports and help stay independent of it. Until Task 3 of the spec
authority the collector was Attune AI's; that arrangement is recorded in
[Task 6's results](plan-build-task6-results.md). Installing Harness does not
upgrade an active MCP host. The whole sequence as it runs from a fresh install
with Attune AI absent, the envelope each step returns, and the refusals the
`--no-deps` wheel gives instead, is [the R2 journey](journeys/r2-clean-environment.md).

Commands return durable record locations and JSON results. Missing intent uses the
existing question grammar. Use `plan --answers` for bound answers or `--revise`
with the displayed checkpoint for an explicit correction. A verified completed
prefix can be preserved with `--preserve-completed`; broader post-effect rebasing
is not yet supported. `reconcile-task --observe-file` and `--retry-before` retain
the existing file-recovery boundary. Unsupported transfer/cancel operations fail
explicitly for this profile; use bounded operation pauses and inspect uncertainty.

External command participants require `--allow-external`; native participants also
require the separate `--allow-native` authorization. Approval alone does not grant
paid dispatch. A paused command returns 1; a blocked/failed command returns 2.
Successful intake, approval and completed execution return 0 with distinct statuses.
The supported build profile is an ordered chain in a dedicated local POSIX checkout,
with fixed protected checks and one producer per output. Native model effectiveness,
active integration and release remain separate qualification boundaries.

## Task-oriented evidence review

Install `attune-harness`, then supply one goal and the source/participant choices. Missing
answers are collected interactively; headless runs return a bound intake form.
Explicit acceptance executes the assessment. For example, from a project with
`docs/guide.md`, a trusted verification context and a participant registry:

```sh
attune-harness review --goal "Check the guide against project evidence" \
  --project . --config participants.json --document docs/guide.md \
  --context context.json --corpus docs --query "retention policy" \
  --criteria "Identify unsupported claims and preserve uncertainty" \
  --assessor alpha --accept
attune-harness status .attune-harness/tasks/<task-id>
attune-harness resume .attune-harness/tasks/<task-id>
```

Use `--plan independent-review --reviewer beta` for a separate assignment;
`--allow-external` explicitly enables configured command/native participants.
`--intake-only` prepares accepted inputs without executing. `--pause-after 2`
creates a durable interruption for later resume. A completed assessment can report
a refuted or unknown document; participant narratives remain unverified proposals.
The JSON includes the task directory and identity.

Use `--help-all` when you need additional recovery or setup controls.
See the [assessment receipt](specs/unified-task-execution/assessment-receipt.md)
for installed software evidence and outstanding native-model qualification.

## Test this change

Install `attune-harness`, which carries the forms grammar, and choose an interpreter with
pytest. Supply a changed file or directory relative to Git HEAD. The first command
saves a preview; accept its returned checkpoint to run the captured inputs:

```sh
attune-harness test --project /path/to/repo --scope src/example.py \
  --interpreter /path/to/venv/bin/python --task-dir /path/outside/repo/test-task
attune-harness test --task-dir /path/outside/repo/test-task \
  --checkpoint <preview-checkpoint> --accept
attune-harness status /path/outside/repo/test-task
attune-harness resume /path/outside/repo/test-task
```

The preview shows static import/name associations and an explicit broader fallback
to `tests/`. Use `--test-root` for another directory, or repeat `--tests` to select
a narrower file/directory set with excluded checks disclosed. Collection-only and
all-skipped runs never count as passed execution. JSON output includes a durable
grammar view and the complete saved-record path, with retained stdout/stderr and
pytest evidence. `test`/`resume` return 0 for passed tests, 1 for a preview, failure
or no executed tests, and 2 for interrupted/blocked execution. `status` returns 0
when inspection succeeds; read its displayed outcome for the test result.

This profile supports local POSIX Git working-tree changes, regular files and
default pytest Python file discovery. Custom file patterns and collectors,
committed revision ranges, Git metadata and ignored inputs are not qualified.
To test a completed Harness repair, use `--from-task` instead of project/scope:

```sh
attune-harness test --from-task /path/to/completed-repair \
  --interpreter /path/to/python --task-dir /path/outside/repo/test-task
```

The preview derives the checkout and changed files from the repair and binds its
current completion evidence. Accept the saved preview with the checkpoint command
above. Failed, unfinished, changed or missing repair evidence blocks the handoff;
test approval remains separate. The completed repair record stays unchanged.
See the [connected journey qualification](connected-journey-qualification-results.md).

Tests run in a verified copy; trusted test code can still have external effects.
The selected interpreter supplies dependencies. Plugin autoload and inherited
credentials are disabled; explicitly add `--pytest-plugin pytest_asyncio.plugin`
when needed. `--pytest-arg=-oaddopts=` explicitly clears repository default options.
The timeout defaults to 60 seconds and retained output to 1 MiB; overflow is
unsuccessful, visibly incomplete evidence. A changed snapshot invalidates reuse.
Completed attempts are not repeated, and uncertain dispatch requires inspection
before a newly accepted task. Existing generation and repair workflows remain
available. See the [implementation results](test-this-change-results.md).

## Scoped repair

`fix` replaces explicitly listed existing UTF-8 files in an exclusively owned,
bounded POSIX checkout with a local `.git` directory. Keep task state outside that
checkout. Creation, deletion, renames, symlinks/hardlinks and linked Git worktrees
are outside this first profile. The entire checkout is bounded to 1,000 entries
and 16 MiB, including protected metadata.

On Windows, `fix` is experimental as of 0.2.0. It requires a fixed local NTFS
drive-letter volume, limits files to 64 KiB, and refuses reparse points, files
with more than one hard link and alternate data streams before writing. It passes
its own native tests and is not qualified beyond them. See the
[design note](design-windows-effect-backend.md).

Prepare a trusted probe JSON before the worker runs:

```json
{
  "argv": ["/absolute/path/to/python", "probe.py"],
  "cwd": ".",
  "timeout": 30,
  "max_output_bytes": 8192,
  "environment": {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"},
  "oracle_paths": ["probe.py"]
}
```

```sh
attune-harness fix --goal "Repair addition" --project /path/to/parent \
  --checkout /path/to/parent/dedicated-clone --scope src/math.py \
  --probe /path/to/probe.json --config /path/to/participants.json \
  --worker alpha --reviewer beta --review required \
  --criteria "The frozen acceptance probe passes without changing its oracle" \
  --accept --allow-external
```

Repair uses the same status/resume controls. `--review none` explicitly selects no
review; both requested and required review must complete with no unresolved
objections. A required native reviewer must select a different configured model.
The worker returns a replacement proposal; the host applies it and retains the
failed-before/passed-after probe evidence. Native participant tool grants remain
read-only. Trusted command peers and probes are supervised processes, **not a
security sandbox**; use a dedicated checkout and trusted commands.

For an uncertain file write, `reconcile-task <task> --event <id> --observe-file`
records an observed matching after-image. `--retry-before` permits one retry only
when the original bytes remain. Unexpected bytes stay unresolved; cancellation
never rolls back later edits. Unknown probe effects are not automatically retried.
See the [repair receipt](specs/unified-task-execution/repair-receipt.md) for the
exact tested profile and pending native qualification.

## Memory

`attune-harness memory` takes one JSON config file with `--config`. It has up
to three sections, each optional:

```json
{
  "roots": [],
  "redis": {"url_env": "REDIS_URL", "password_env": "REDIS_PASSWORD"},
  "scratch": {"backend": "redis", "namespace": "harness"}
}
```

`roots` is the read-only integration the adoption spec accepted: `memory
capabilities|recall|resolve|refresh` over explicit roots of the `raw`,
`personal` and `curated` tiers. Which code reads them is `reader`: `native`,
Harness's own reader (Phase 2 of the plan to 1.0, D19), which needs nothing
from attune-ai and is POSIX-only at 0.5.0; or `adapter`, attune-ai's
compatibility adapter, which only an environment built from attune-ai's
`codex/shared-memory-adoption` branch has. `native` is the default; `adapter`
is the rollback, a config edit with no data conversion, until Task 9 removes
it. The `redis`, `scratch` and `reader` keys are set aside before the roots
contract is validated, so one file serves every memory verb. The other two
sections need only Harness.

**`redis`**, with the `redis` extra, reads the Redis Stack keyspace a hydration
keeps warm, read-only: `memory redis status`, `digest [--limit N]`,
`related ID`, `node ID` and `search QUERY [--layer curated|file|lesson|rule]
[--k N]`. Exactly one of `url` and `url_env` says where the URL comes from;
`password_env` names a variable read only when the URL carries no password;
`index` defaults to `idx:attune_memory`. Every answer is an evidence packet
with an authority binding and the guidance that memory is untrusted evidence;
the `text` body of a file, lesson or rule pointer is never served. An id is a
curated node's bare id or a family-qualified pointer id such as
`file:<corpus>:<stem>`, and every id `search` returns resolves through `node`.

**`serve`** is the same digest as plain text for a session-start hook:
`memory serve [--limit N] [--chars N]` prints one header line with the count,
the hydration stamp and the host, one line per curated node (`- id [type]
name: description`, control characters dropped, cut at 240 characters), and
one footer line saying the memory is untrusted evidence and how to read one
node or search. Node lines are dropped from the end until the text fits in
`--chars` (default 4000) and the header then says how many are shown; the
header and footer are always printed, so about 600 characters is the floor.
Once the command line has parsed, it never fails: with no digest, because the
config has no `redis` section, the extra is not installed, the server cannot
be reached or is not hydrated, the digest is empty, or the config file cannot
be read, it prints nothing on stdout, one line `[attune-harness memory]
skipped: <reason>` on stderr, and still exits 0; a stream that is closed,
gone, or cannot encode a character never produces a traceback. Only a
malformed command line (`--limit abc`, no `--config`) exits 2 with the usage
text, as every verb does. A Claude Code hook that serves the digest at
session start:

```json
{"hooks": {"SessionStart": [{"hooks": [{"type": "command", "timeout": 10,
  "command": "attune-harness memory --config ~/.attune/harness-memory.json serve"}]}]}}
```

**`scratch`** is working memory: JSON values up to 64 KiB under keys of up to
128 characters, with an optional time to live, through `memory scratch
capabilities`, `stash KEY (--value JSON | --value-file PATH) [--ttl SECONDS]`,
`retrieve KEY`, `forget KEY` and `keys [PATTERN]`. `backend` is `file`, with a
`root` directory the config names and no sharing, or `redis`, which uses the
`redis` section and is shared across processes and machines; `namespace`
separates users of one store. The backend is chosen when the command starts.

Statuses and exit codes follow the other memory verbs, except `serve`, which
exits 0 once its command line has parsed: `ok` and `no_results` exit 0;
`disabled` (the section is absent), `unavailable` (the extra is not installed,
the server cannot be reached, or the keyspace is not hydrated) and `failed` (a
refused input) exit 2, each with a `detail`. A Redis that cannot be reached is
reported; it is never replaced by the file store at runtime.

Qualification: every platform job installs the extra and, with no server,
confirms the reads and a Redis scratch report unreachable, `serve` exits 0
with its one stderr line, the file scratch round-trips, and nothing is
written when Redis is refused; the release gate
does the same with the extra absent. The path against a hydrated server runs
only where `ATTUNE_TEST_REDIS_URL` is set.

## AI tools, integrations and existing scripts

`attune-harness --help-all` lists the complete catalog. `reconcile-task`,
`transfer-task`, and `cancel-task` provide bounded recovery controls. Indexing,
extensions, retrieval, verification and protocol operations remain directly
available to the AI, integrations and direct callers when needed. Their use stays
within the accepted task scope and existing authorizations.

All 18 original command routes remain callable, including positional
`review request.json --config ... --run-dir ...` and the older review controls.
They preserve their original arguments, output and exit behavior. These are
compatibility routes, not an additional vocabulary required for new tasks.
See the [navigation design](design-navigation.md) for the discovery policy.
