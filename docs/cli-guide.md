# CLI guide

Full usage for the `attune-harness` commands: arguments, exit codes, supported
profiles and recovery controls. The [README](../README.md) gives the short version.
Updated on October 22, 2026.

## Installation

This guide describes the 1.5.0 commands, with planned 1.5.1 changes labeled below.
Version 1.5.1 is [in preparation](release-notes-1.5.1.md); the installation
command selects published 1.5.0. Install Harness in its own environment.
Use the [workflow guide](supported-journeys.md) to check capabilities and
reliability requirements.

Start with a managed base installation:

```sh
uv tool install 'attune-harness==1.5.0'
```

The base carries the forms, verification, local retrieval, review, test, MCP and
acceptance dependencies. Add Redis or Voyage when you need those integrations;
`all` includes both and excludes experimental native memory. Python 3.10 or later.
The [installation guide](installation.md) covers executable checks, alternatives,
optional profiles, selection of the managed Python interpreter for module and
fixture commands, and separate host-plugin setup. The example below needs no
API key or attune-ai installation; Voyage retrieval needs a Voyage API key and
makes paid calls.
Harness and attune-ai cannot share one environment:
they pin different lines of the MCP SDK, and installing Harness over attune-ai
replaces attune-ai's; an isolated install avoids that, and `mcp-serve` says so
if it finds the two side by side.

## Checks and receipts

A participant produces output; a separate check decides whether it meets the
criteria. This local example needs no API key:

<!-- journey: checks-and-receipts -->
```python
from attune_harness import Check, Output, Task, run

class Worker:
    def run(self, task: Task) -> Output:
        return Output("4")

receipt = run(
    Task("addition", "Compute 2 + 2", ("Return the integer result",)),
    "example-worker",
    Worker(),
    lambda task, output: Check(output.text == "4", "Compared with independent arithmetic"),
)
print(receipt.status.value)  # verified
```

Change the worker to return `"5"` and the same call returns `rejected`, with the
output and the check's evidence still attached. If the participant or the check
raises, the status is `failed` and the receipt names the stage and the error. `run`
executes once. It never retries on its own.

`attune-harness` with no arguments runs the installed demonstration and prints a
JSON receipt. For `python -m` commands or Python API examples, use the
[selected runtime's interpreter](installation.md#select-python-for-module-and-fixture-examples).

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

Getting started
  init         Write a starter participant registry

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

## Codex skill

For discovery through the Plugins list, use the separate
[Attune Harness plugin package](codex-plugin.md). The instructions below install
the standalone skill only; Attune-AI is a different plugin.

The repository's [attune-harness skill](../.agents/skills/attune-harness/SKILL.md)
routes natural-language tasks to the existing CLI. For example:

```text
Use $attune-harness to test my changes to src/example.py.
Use $attune-harness to inspect the task at /path/to/saved-task.
```

Codex discovers repository skills in `.agents/skills`. For use across projects,
copy the entire `.agents/skills/attune-harness` directory, including `references`
and `agents`, into `~/.agents/skills/attune-harness`. Inspect an existing
destination before replacing it; a user copy is a snapshot and must be updated
deliberately when the repository skill changes. Having both copies can produce
two selector entries. These discovery locations and automatic reload behavior
are described in the [Codex skill documentation](https://developers.openai.com/codex/skills/).
If a new skill does not appear, restart Codex.

The CLI must also be installed in the environment the agent uses. The skill
targets 0.6.0 and checks the selected route's installed help before dispatch.
It does not add new CLI verbs or install a host plugin, and the Python wheel
does not contain it. `review` checks a document against evidence; `test` runs
checks on captured changes. Neither a source-security audit nor test generation
is implied by those names. `ship` and `reflect` remain planned routes.

## Readable output

Every verb prints one JSON envelope, for the agent and for scripts. Add
`--format markdown` to `plan`, `build`, `review`, `fix`, `test` or `resume` to
print the same result for people: the envelope's own Markdown where it has
one, otherwise its status, outcome and any refusal, then where the record is
saved and what to do next. The exit code does not change. `status --format
markdown` (or `html`) works for every saved task.

## Get started with a participant registry

`plan`, `review` and `fix` read a participant registry, `participants.json`,
naming who plans, works, assesses and reviews. `init` writes a starter one into
the project:

<!-- journey: init -->
```sh
attune-harness init
attune-harness init --profile claude --project /path/to/repo
```

The default `demo` profile has two deterministic participants that call no
model, enough to run the review intake and the bundled examples offline.
`claude` and `codex` name a lead and a reviewer on different models, since a
required native review needs one. Writing them authorizes nothing: running them
still needs `--allow-external` and `--allow-native`, and may incur provider
costs. `init` refuses to replace an existing registry unless you pass
`--force`, which keeps the old file as `participants.json.bak`. Its JSON names
the next command to run. When `plan`, `review` or `fix` finds no registry, the
refusal's `next_action` names `init`.

## Plan and build

For a guided plan-acceptance example, choose a
[preparation walkthrough](tutorials-1.5.0-candidate.md#choose-a-walkthrough)
and use its stated source and fixtures.

The planning and build commands take a Git checkout from a named file to an
accepted plan with a finished build. `init --for plan` writes the work request, with
its effects manifest frozen, beside the task directory (`starter-plan.work.json`
for `--task-dir ~/harness-tasks/starter-plan`), outside the checkout the
manifest freezes. The example command participants in
`examples/starter/participants.json` make the change: `lead` applies one
declared replacement (`calc.py`, `a - b` to `a + b`) and `reviewer` approves
without judging. They are example code, carried inline as `python -c` with a
readable copy in `examples/starter/worker.py`, so they need `python` on PATH.
`examples/` is in the repository, not the installed package: run any block
that names it from a checkout of this repository, with a virtual
environment activated so that `python` is on PATH on every platform
(`source .venv/bin/activate`, or `.venv\Scripts\activate` on Windows).
Use your own participants for real work: the participants `init` writes are
for review and cannot build.
This journey and the `fix` one below run in CI as printed.

<!-- journey: plan-starter -->
```sh
attune-harness init --for plan --goal "Repair addition" \
  --project /path/to/repo --scope calc.py \
  --interpreter /path/to/venv/bin/python --tests tests/test_calc.py \
  --task-dir ~/harness-tasks/starter-plan
attune-harness plan --request ~/harness-tasks/starter-plan.work.json --project /path/to/repo \
  --config /path/to/examples/starter/participants.json \
  --task-dir ~/harness-tasks/starter-plan
attune-harness plan --task-dir ~/harness-tasks/starter-plan --accept \
  --checkpoint <preview-checkpoint>
attune-harness build ~/harness-tasks/starter-plan --allow-external
attune-harness status ~/harness-tasks/starter-plan
```

The starter request carries the goal, the scope and the named tests as its
acceptance evidence; add context and constraints by revising it before you
accept. Writing the request accepts nothing: the preview and `--accept` are
still separate steps.

An agent can author a work request from the user's goal. The request records
`intent` (goal, context, exact file scope, constraints, acceptance criteria and
questions), explicit participant assignments and any dependent tasks. Complex
work can import an existing Spec using `--import-plan`; import grants no authority.
For construction, freeze the supported effect manifest and protected verification
commands before accepting the work. See [the contract](specs/plan-build/work-contract.md)
and [bounded build profile](specs/plan-build/dependent-build.md).

```bash
attune-harness plan --request work.json --project ./checkout \
  --config participants.json --task-dir ~/harness-tasks/my-work
attune-harness plan --request work.json --project ./checkout \
  --config participants.json --task-dir ~/harness-tasks/my-work \
  --import-plan ~/other-project/.claude/plans/feature.md --allow-outside-project
attune-harness plan --task-dir ~/harness-tasks/my-work --run --allow-external
attune-harness plan --task-dir ~/harness-tasks/my-work --stage --checkpoint CURRENT_CHECKPOINT
attune-harness plan --task-dir ~/harness-tasks/my-work --accept --checkpoint CURRENT_CHECKPOINT
attune-harness build ~/harness-tasks/my-work --allow-external --max-operations 4
attune-harness status ~/harness-tasks/my-work
attune-harness resume ~/harness-tasks/my-work --allow-external
```

These commands are not a copy-and-paste example yet: `work.json` must carry a
frozen effects manifest, which no command writes. The offline plan, accept,
build, review and status journey in `scripts/check_installed.py` (`FREEZE` and
`journey_checks`) builds one and runs in every platform job.

A task directory may not sit behind a symlink. That rules out `/tmp` on macOS,
which links to `/private/tmp`; the refusal names the link and the resolved path
to use instead.

### Importing a plan from another project

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

To return to a saved feature-work task, export a read-only overview:

```bash
attune-harness status ~/harness-tasks/my-work --format markdown > task-status.md
attune-harness status ~/harness-tasks/my-work --format html > task-status.html
attune-harness status ~/harness-tasks/my-work --format html --continuation pause.json > return-to-work.html
```

The overview leads with the goal, next useful step, stopping point, reported
progress, changes and open decisions. The HTML's expandable supporting details
retain checks, choices, task identity and evidence. It works without a server or
network resources. It does not refresh: inspect again before acting. Completed
planning is still a draft, and stale passing checks do not establish current
completion. Output contains local paths and task intent; choose where to share it.

### Browser forms

For browser draft intake and explicit intent approval in the **forms companion**, register a
canonical absolute saved feature-work draft directory and enable form actions:

```bash
python -m attune_harness.gui --task /absolute/path/to/task --edit
```

The private launcher link grants access only to this local forms session. Without
`--edit`, inspection is read-only. Refresh lists registered drafts. With one draft, the workspace opens its current
form directly; accepted work shows read-only answers. Click **Continue form**
for remaining questions or **Review your answers** for the current preview.
Save partial answers, review the preview, then click **Approve this work request**
or **Keep as draft**. The first records approval; the second leaves an unapproved
draft. Neither starts work. Saving answers is not approval; approval is not execution or
paid dispatch. Stale checkpoints, replaced forms and foreign-origin submissions
refuse. A restart requires opening a fresh form; retained text is evidence only.

A same-view reload can restore its current form when the listener, checkpoint,
collector and browser ownership remain current. This requires usable session
storage, navigation timing and an exclusive Web Lock. Saved answers are restored;
unsaved typing is not. Stale or uncertain recovery remains blocked across
**Refresh forms** until you deliberately reopen. When browser support is missing,
click **Continue form** or **Review your answers** to reopen the current form.
Do not resubmit an unconfirmed response. A listener restart needs a new launcher
and collector. Native-browser and human assessment remain pending.

Reopened intake forms show **Saved answers** above the remaining questions,
including the saved goal, success criteria, answered questions and selected
choices. Bold labels flow inline with their saved values, using one ordinary
separating space without adding to an entered leading space. Entered whitespace
is preserved. **Still needed** separates
the remaining questions from the saved answers. Remaining fields start empty;
saved answers are never remapped into
new questions. The full unchanged owner record stays below the form under
**Technical details (optional)**. The approval preview still shows the complete
intent and blocking evidence before an explicit decision. Its main view shows
the questions and their saved answers in plain language. The full unchanged
owner record, action definitions, checkpoint and file-effects JSON stay inside
the initially collapsed **Technical details** disclosure. Blocking reasons from
the owner's retained readiness receipts remain visible above it; unavailable
approval actions remain unavailable.

**Open in browser** requests the same private workspace in your system browser.
It stays available at every width; panels at most 600 pixels wide recommend it.
Click to open, and copy any unsaved answers first. Switching makes the old form
read-only without saving or transferring its answers. Use the current form in
the new view to continue. The system browser decides between a tab and a window;
Harness cannot resize the chat panel or move a window to another monitor. If
opening cannot be confirmed, paste the complete private launcher link from
Terminal into your browser.

For host integrations, `--launch-json` emits one private JSON launch record on
stdout and suppresses automatic external-browser opening:

```bash
python -m attune_harness.gui --task /absolute/path/to/task --edit --launch-json
```

The record contains `type: attune-harness.browser-launch`, `version: 1`,
`origin`, `launch_url`, `editable`, `task_count` and `execution_enabled`.
The server keeps running after this line. Treat `launch_url` as private access
data: it includes a fragment token for this listener, not a permanent task link.
Do not retain it in a shared artifact. A new listener produces a new link.
`execution_enabled` is false in the forms companion; structured launch
does not enable browser builds or dispatch.

An assistant can pass the exact link to an available host browser-opening tool.
Use the built-in browser's **Enter split view** control for chat beside the form;
an opening request alone does not verify rendering or pane order. Reopen the same
link while the listener is alive, refresh, and open the current form to retrieve
saved answers. Unsaved typing needs separate preservation. This is a browser
integration, not a native MCP conversation-panel registration.
See [the opening and resume workflow](../.agents/skills/attune-harness/references/browser.md).

Browser build grants, dispatch, resume and broader GUI navigation remain future
work outside the **forms companion**. `--allow-build-commands` exits 2 before
task/listener/browser effects;
imported server construction with that option also refuses. `/build/preview`,
`/build/start`, resume/grant routes and general `/snapshot` navigation are absent
from the release server. CLI owners and static status remain separately available
under their existing authorization boundaries. Future development instructions in
the [specification](specs/graphical-companion/README.md) are not released scope.

### Pause and return to work

Use this procedure to return to an existing feature-work task after an
interruption. Your assistant can prepare the note and report. The report is
read-only and does not refresh itself; the released forms companion is a separate
intake/approval view, not this return briefing.

1. Before leaving, inspect the actual task directory returned by its owner:

<!-- journey: pause-return-inspect -->
```sh
attune-harness status /path/outside/repo/work --format json
```

   Replace `/path/outside/repo/work` with that saved directory. Read its status
   and next action; exit 0 means inspection succeeded, not that work is complete.
   Ask your assistant to verify that the saved owner's `task_profile` is
   `feature-work-v1`; the status envelope supplies task ID/revision but does not
   repeat the profile. Other profiles keep their own status/recovery route and
   do not accept this continuation format.

2. Ask your assistant to save a new UTF-8 pause note outside the effects checkout.
   Copy the actual task ID and revision from the inspection, use the current time
   with a timezone, and describe where work actually stopped. Preserve earlier
   notes under their own filenames. Leave `progress` empty when no external work
   is established; reported work must name its source and retain its limits.

   This is a format template, not an account of completed work:

<!-- journey: pause-return-note -->
```json
{
  "schema_version": 1,
  "task_id": "COPY-THE-ACTUAL-TASK-ID",
  "revision": 1,
  "recorded_at": "2026-09-25T09:30:00-04:00",
  "source": "Developer's end-of-session note",
  "stopped_after": "Export is implemented; consumer review is next.",
  "progress": [{
    "summary": "The export check passed outside this Harness task.",
    "references": ["reports/export-check.txt"]
  }],
  "next_step": {
    "action": "Review the export with a consumer.",
    "reason": "Check that it fits the support team's workflow."
  }
}
```

3. Generate a report with the same installed environment's Python and
   `attune-harness` executable. Replace the three paths below with the saved task,
   new note and agreed report location. Keep note/report files outside the effects
   checkout and make sure the report's parent directory exists.
   Keep the `r` string prefixes so Windows backslashes are preserved.

<!-- journey: pause-return-report -->
```python
from pathlib import Path
import subprocess

task = Path(r"/path/outside/repo/work")
note = Path(r"/path/outside/repo/pause-note.json")
report = Path(r"/path/outside/repo/return-to-work.html")
result = subprocess.run(
    ["attune-harness", "status", str(task), "--format", "html",
     "--continuation", str(note)],
    check=True, capture_output=True, text=True, encoding="utf-8",
)
report.write_text(result.stdout, encoding="utf-8")
print(report)
```

   The wrapper saves output only after successful inspection. On a refusal,
   `CalledProcessError` retains the CLI diagnostic in `stdout`; ask the assistant
   to inspect it. Keep any earlier report and do not treat it as current. This
   wrapper is ordinary caller code, not a new Harness command or capture API.

4. Retain the task, note and report paths in the existing handoff or chat. When
   you return, ask the assistant to inspect that task and regenerate the report
   using the same procedure, then open the successful HTML file. Copy unsaved
   reply text before replacing or reloading a report. A local snapshot path is
   distinct from the forms companion's expiring private launcher link.

   If the host cannot open a local HTML file, ask the assistant to return the
   same briefing as Markdown and read it in the conversation, file viewer or
   terminal:

```sh
attune-harness status /path/outside/repo/work --format markdown --continuation /path/outside/repo/pause-note.json
```

   Markdown provides the handoff text without interactive controls. Copy
   **Your reply to the assistant** manually. Record this as a text walkthrough,
   not a rendered-browser check. A queued opening request does not confirm that
   a report is visible. Keep host security restrictions in place.

5. Read **Context**, **Goal**, **Desired end state**, **Current focus**,
   **Current position** and **Next action**. Expand the supporting detail if
   needed. Historical notes, changed sources and uncertain operations require
   following the current saved guidance before any retry.

6. Click **Continue with guidance**, **Correct context** or **Ask a question**
   to prepare a reply. A current design-review question instead shows
   **Discuss next decision**. Enter your words where needed, then click
   **Copy reply** and paste the text into your conversation. If clipboard access
   fails, copy the selected reply manually. Nothing is sent, approved or executed
   by the report; unsaved reply drafts clear on reload.

7. Have the assistant reinspect the named task and note before acting. Correcting
   a caller note does not revise accepted task scope. **`resume`** may dispatch
   work and is used only when the current task and existing authorization permit
   it; reopening the briefing does not require **`resume`**.

If no pause note exists, use the saved owner's context without inventing one:

<!-- journey: pause-return-no-note -->
```sh
attune-harness status /path/outside/repo/work --format markdown
```

The report states that no stopping point or comparison baseline was supplied.
Record what you can establish now; do not reconstruct missing observations as
fact. To choose among explicitly supplied tasks, use
[Saved Tasks](#saved-tasks-and-briefing-replies). The note applies to the primary
task only. For this journey's scope and remaining observed acceptance, see the
[return-to-work checkpoint](specs/task-opportunities/README.md).

### Continuation note contract

`--continuation` reads only the named UTF-8 JSON file, at most 32 KiB. It requires
Markdown or HTML; it never changes default JSON or the task. All fields shown in
the template are required; `next_step` may be null and `progress` may be empty.
Each text field is at most 2,048 UTF-8 bytes. At most six progress items and six
references per item are allowed. Unknown fields, wrong task IDs and revisions
absent from retained history fail explicitly.

The note is attributed context, not verified execution. References remain literal
text: the view does not open them or check their claims. The timestamp is supplied
by the author; matching a task/revision does not authenticate authorship. Historical
notes compare saved scope against retained request history, not run progress or
external file activity. Without a note, the view explains the missing stopping
point and comparison baseline. A note's suggested action is withheld for an older
revision, a blocked task or completed work; current Harness guidance always wins.
Edit the note to correct context; use the existing `plan --revise` flow to correct
task intent. Neither action grants acceptance or execution permission.

Omitted `--format` and explicit `--format json` preserve the existing JSON
contract. Markdown/HTML require `feature-work-v1`; other profiles retain JSON.
An inspection succeeds with exit code 0 even when the task is blocked or stale;
read its status and guidance. Invalid records or projections over 512 KiB fail
with an explicit JSON diagnostic and exit code 2 instead of a truncated page.

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

For a Codex build participant that timed out, `reconcile-task TASK --event EVENT
--checkpoint CHECKPOINT --retry-native` can prepare one explicit retry when the
saved host evidence establishes that the direct CLI process stopped. Detached
descendants and external effects are not proven absent. It checks the
accepted inputs, configuration and checkout before preparing the retry; `resume`
then still requires the original dispatch permissions. The first attempt remains
inspectable. This is not a read-only classification: provider work or quota usage
may have occurred and may repeat. Missing stop evidence, non-timeout failures
and a second retry are refused unless the legacy observation path below applies.

For an older Codex timeout without a structured stop receipt, an operator who
has independently observed the direct worker stop may add `--stop-observation
observation.json` to the same `--retry-native` command. This is a new attributed
assertion, not reconstructed host evidence or proof that external effects ceased.
The observation must name the current task, checkpoint and failed event:

```json
{
  "schema_version": 1,
  "task_id": "COPY-TASK-ID",
  "checkpoint": "COPY-CURRENT-CHECKPOINT",
  "event_id": "COPY-FAILED-EVENT-ID",
  "observer": "Operator who inspected the stopped worker",
  "observed_at": "2026-09-26T06:30:00+00:00",
  "statement": "direct_process_stopped",
  "evidence": "Describe the independently observed exit and process inspection.",
  "acknowledge_unknown_effects": true
}
```

Keep this file outside the checkout. Reconciliation retains its bounded contents,
path and digest with `operator_assertion` provenance, alongside the untouched
failed event and participant details. It validates the observation's bindings and
rechecks accepted inputs, configuration and the complete checkout under the task
lease. The operator's name is attribution, not authenticated identity. The legacy
timeout diagnostic only selects eligible failures; it never proves termination.
No observation is generated automatically, no historical `native_failure` receipt
is fabricated, and reconciliation does not dispatch the next attempt.

Codex build workers and reviewers use `--ignore-user-config` and disable apps,
plugins and remote plugins. Authentication still uses the existing `CODEX_HOME`;
the configured model, checkout directory, read-only sandbox and rules remain.
This isolates user configuration and plugin integrations, not every project or
system MCP configuration. Other native routes keep their existing configuration.
A Codex CLI lacking these flags refuses the invocation; there is no fallback to
an inherited user configuration. Timeout duration is unchanged.

External command participants require `--allow-external`; native participants also
require the separate `--allow-native` authorization. Approval alone does not grant
paid dispatch. A paused command returns 1; a blocked/failed command returns 2.
Successful intake, approval and completed execution return 0 with distinct statuses.
Build uses an ordered chain in a dedicated local checkout, with fixed protected
checks and one producer per output. The
[workflow guide](supported-journeys.md#windows-capabilities-and-reliability)
describes Windows NTFS requirements. Native model effectiveness and host
integration require their own acceptance evidence.

## Task-oriented evidence review

The bundled example runs offline from a checkout, with its deterministic participants and the example directory as the project:

<!-- journey: review-bundled-example -->
```sh
cd examples/local-workflow
attune-harness review --goal "Check the guide against its evidence" --project . \
  --config ../review/participants.json --document project/guide.md \
  --context context.json --corpus project --query "quartz retention policy" \
  --criteria "Identify unsupported claims" --assessor sample-lead \
  --task-dir /path/outside/repo/review-task --accept
```

`--document`, `--context` and `--corpus` resolve against `--project`, while
`--config` resolves against the working directory; a refusal about a path says
which base it used and what it resolved to.

For your own project, supply one goal and the source/participant choices. Missing
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

### Inspect completed assessment evidence (1.5.1 candidate)

The following presentation is merged on `main` for the planned 1.5.1 release;
published 1.5.0 uses the earlier generic status report.

Inspect a completed assessment with **`status`** and `--format markdown` or
`--format html`. The readable report shows the accepted goal and criteria,
recorded document-check verdicts and checker findings, retrieved source paths and
hashes, and separately attributed participant judgments. Record pointers identify the
supporting fields in the saved JSON. Semantic acceptance remains unverified;
reading status does not rerun checks, refresh source evidence or grant execution.
Non-layout control characters display as `\uXXXX`, and line endings display as
line breaks. Saved text and the default JSON output are unchanged.

Use the task directory returned by your completed review. For example, if it is
`~/harness-tasks/review-task`:

```sh
attune-harness status ~/harness-tasks/review-task --format markdown
attune-harness status ~/harness-tasks/review-task --format html > assessment.html
```

Expect **Assessment evidence**, a **Document check verdict** and separately
attributed participant judgments. A document-check verdict of `verified`,
`refuted` or `unknown` describes the recorded checks; **Semantic acceptance**
remains unverified. Incomplete assessments, repair tasks and other task profiles
keep their existing presentation.

Use `--help-all` when you need additional recovery or setup controls.
See the [assessment receipt](specs/unified-task-execution/assessment-receipt.md)
for installed software evidence and outstanding native-model qualification.

## Test this change

Install `attune-harness`, which carries the forms grammar, and choose an interpreter with
pytest. Supply a changed file or directory relative to Git HEAD. The first command
saves a preview; accept its returned checkpoint to run the captured inputs:

<!-- journey: test-this-change -->
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

This profile supports local Git working-tree changes, regular files and
default pytest Python file discovery on POSIX and Windows. Custom file patterns
and collectors, committed revision ranges, Git metadata and ignored inputs are
not qualified.
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

`init --for fix` writes the trusted probe, `probe.json`, that `fix` needs,
and validates it before writing. It does not run the probe. The repair starts
from a failing test and ends when the probe passes. This journey runs in CI
as printed, with the example participants in `examples/starter/`.

<!-- journey: fix-starter -->
```sh
attune-harness init --for fix --project /path/to/repo --scope calc.py \
  --interpreter /path/to/venv/bin/python --tests tests/test_calc.py
attune-harness fix --goal "Repair addition" --project /path/to/repo \
  --checkout /path/to/repo --scope calc.py --probe /path/to/repo/probe.json \
  --config /path/to/examples/starter/participants.json \
  --worker lead --reviewer reviewer --review required \
  --criteria "The frozen probe passes without changing its oracle" \
  --task-dir ~/harness-tasks/starter-fix --accept --allow-external
```

`fix` replaces explicitly listed existing UTF-8 files in an exclusively owned,
bounded checkout with a local `.git` directory. Keep task state outside that
checkout. Creation, deletion, renames, symlinks/hardlinks and linked Git worktrees
are outside the repair profile. The POSIX checkout is bounded to 2,048 entries
and 16 MiB, including protected metadata.

The Windows repair profile requires a fixed local NTFS drive-letter volume,
limits files to 64 KiB, and refuses reparse points, files with more than one
hard link and alternate data streams before writing. See the
[capability table](supported-journeys.md#windows-capabilities-and-reliability)
for its process-completion and recovery requirements.

The `fix-starter` block above is the copy-and-paste example: `init --for fix`
writes the trusted probe, and the example participants propose and approve
the replacement. For your own repairs, `fix` needs a dedicated checkout, a
trusted probe and a worker that proposes a replacement. A probe written by
hand looks like this:

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
`personal` and `curated` tiers. `reader` accepts only `native`, the default. The former `adapter` selection
is refused immediately with "Memory reader must be 'native'" (D28); no
installed attune-ai distribution supplied it. Harness reads the
[frozen legacy formats](specs/native-memory/formats.md) without importing
attune-ai. Native reads use POSIX descriptors. On Windows, retained handles
enforce the [local NTFS profile](supported-journeys.md#windows-capabilities-and-reliability).
The `redis`, `scratch` and `reader` keys are set aside before the roots
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
`memory serve [--for PROMPT] [--limit N] [--chars N]` prints one header line with the count,
the hydration stamp and the host, one line per curated node (`- id [type]
name: description`, control characters dropped, cut at 240 characters), and
one footer line saying the memory is untrusted evidence and how to read one
node or search. Node lines are dropped from the end until the text fits in
`--chars` (default 4000) and the header then says how many are shown; the
header and footer are always printed, so about 600 characters is the floor.
The banner identifies Redis as the source and the records as untrusted evidence,
not instructions, and asks the model to disclose IDs of memories that influence
its answer. A host membership check removes curated nodes absent from
`status:active`. `--for PROMPT` searches prompt terms (at most 512 characters)
instead of the global digest; it does not print the prompt. Both modes consider
at most 100 candidates, filter, then keep `--limit` items (default 8).

File pointers in prompt results require a canonical path inside exactly one
configured `personal` or `curated` root, and an ID stem matching that path.
The root uses the same explicit authority config as `memory recall`; a Redis
`corpus` or `path` does not grant access by itself. The latest `wrong` verdict
for the stem suppresses the pointer. A missing `.verdicts.jsonl` means no
recorded verdict; an unreadable, malformed or unsafe log suppresses pointers
from that root. Sidecar reads share an 8 MiB budget and use the native reader
for the selected platform. Redis-only configurations serve eligible curated
nodes without granting file-pointer access. Lesson and rule pointers
keep their existing semantics. Pointer `text` bodies are never displayed.

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

For a UserPromptSubmit hook, the checkout's
[`scripts/memory_prompt_hook.py`](../scripts/memory_prompt_hook.py) reads the
host's JSON from stdin and passes its `prompt` as one argument to the installed
CLI. Use the interpreter from the Harness environment, not a shell expression
containing the prompt:

```json
{"hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command", "timeout": 12,
  "command": "/path/to/harness-venv/bin/python /path/to/attune-harness/scripts/memory_prompt_hook.py --config /absolute/path/memory.json"}]}]}}
```

Replace all three paths with your local paths. The bridge accepts at most
64 KiB of hook JSON and 512 prompt characters, skips longer input, has a
10-second child deadline, and does not log the prompt. These examples do not
install or alter your hooks automatically. The real-session receipt remains
an acceptance step beyond the synthetic tests.


**`scratch`** is working memory: JSON values up to 64 KiB under keys of up to
128 characters, with an optional time to live, through `memory scratch
capabilities`, `stash KEY (--value JSON | --value-file PATH) [--ttl SECONDS]
[--expected-version N]`, `retrieve KEY`, `forget KEY` and `keys [PATTERN]`.
`backend` is `file`, with a `root` directory the config names and no sharing,
or `redis`, which uses the `redis` section and is shared across processes and
machines; `namespace` separates users of one store. The backend is chosen
when the command starts.

Each stored record is a versioned format (native memory Task 5, D21.6):
`stash` and `retrieve` report `format` (`attune-harness/scratch`),
`format_version` (2), `writer` (the package and version that wrote it) and
`version`, the count of successful stashes since the key was last absent,
from 1. `--expected-version N` is a compare-and-set: the stash lands only
when the stored record is at version `N` (`0` means no record) and is
otherwise refused with `failed`, a `detail` saying what was expected and
what was found, and nothing written; retrieve the key and stash with the
version it reports. The count is exact only when every writer to the key
passes an expected version: a stash without one reads the record only to
count and then overwrites unconditionally, a record a compare-and-set just
landed included. A record 0.4.0 or 0.5.0 wrote is read in place and
reported with `format_version` 1 and no `version`; the first plain stash
over it writes the current format. A stash whose effect cannot be known,
the record written and the replace raised, or the write sent to Redis and
its reply lost, is reported as `uncertain` with the `version` and
`stored_at` the write carried: retrieve the key, and a record at that
version stored at that stamp means it landed, while one at that version
with another stamp is another writer's; the stash is not retried and
nothing is diverted. `docs/envelopes.md` lists the record under "Stored
formats".

Statuses and exit codes follow the other memory verbs, except `serve`, which
exits 0 once its command line has parsed: `ok` and `no_results` exit 0;
`disabled` (the section is absent), `unavailable` (the extra is not installed,
the server cannot be reached, or the keyspace is not hydrated) and `failed` (a
refused input, or a `stash` whose expected version is not the stored one)
exit 2, each with a `detail`; `uncertain` (a scratch stash whose effect
cannot be known) exits 2 with what is known. A Redis that cannot be reached
is reported; it is never replaced by the file store at runtime.

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

`extension enable` takes `--registry PATH` for a plugin bundle, one whose
manifest carries `grants` or `declares`: a registry file whose `extensions`
section lists the `signers` that vouch for the bundle's `artifact.sig`, the
`revoked` list it is checked against, and the registration that carries the
grant (the accepted registry's, or one written for the enable; every call
checks the registry the run accepted). Without it a plugin refuses
to enable; a data-only bundle enables as before, with no registry and no
signature. The enable receipt and every contributed call then carry `plugin`:
the signer's fingerprint, the effective grant and the acknowledged declarations,
with the words that the signature means this exact bundle was reviewed by the
signer under the brief and that declarations are recorded, not enforced. The
signed bytes, the registry's fields and every refusal are in
[the extension workflow](extension-workflow.md). No plugin code runs yet; the
`run` binding is a later cycle of plan task 4.3.

All 18 original command routes remain callable, including positional
`review request.json --config ... --run-dir ...` and the older review controls.
They preserve their original arguments, output and exit behavior. These are
compatibility routes, not an additional vocabulary required for new tasks.
See the [navigation design](design-navigation.md) for the discovery policy.


### Saved Tasks and briefing replies

Supply task directories explicitly to produce one navigable HTML file:

```sh
attune-harness status ~/harness-tasks/my-work --include-task ~/harness-tasks/other-work --format html > saved-tasks.html
```

Re-run the same command to refresh that file. Open it to choose a task; each
briefing links back to Saved Tasks. This does not install a host entry or refresh
a browser automatically. The collection accepts at most 20 distinct directories
and 2 MiB of serialized views. Additional missing, unsupported or duplicate-owner
tasks appear as unavailable; a failure in the primary task fails the command.
Markdown is also supported; `--include-task` with JSON is refused. Inspection
performs no discovery, dispatch or task mutation. `--continuation` applies only
to the primary task in a collection.

The briefing separates context, overall goal, desired end state, current focus,
stopping point and authoritative next action. HTML offers local reply preparation
and Copy reply. Selecting a response does not send it or accept a checkpoint.
If clipboard access is unavailable, select/copy the text manually. Without
JavaScript, the initial handoff remains selectable. Replies identify the task and
revision and require current inspection before acting. Unsaved reply drafts last
only while the page remains open; they do not survive reload.

The existing continuation schema optionally accepts `briefing` with exactly six
nonempty text fields (each at most 2,048 UTF-8 bytes): `title`, `context`, `goal`,
`desired_end_state`, `current_focus`, and `done_when`. These caller-authored
summaries retain the note's source/timestamp and are shown only for its current
revision. Historical notes fall back to canonical intent. Full saved intent and
owner guidance remain available; a summary cannot establish progress, approval
or a different next action. The entire note remains bounded to 32 KiB.


The same continuation note optionally accepts `design_review` with exactly:

- `presentation_revision`: nonempty text, at most 64 UTF-8 bytes, distinct from
  the saved task revision.
- `next_question`: null or nonempty text, at most 2,048 UTF-8 bytes. This is a
  discussion question, never an executable action or approval.
- `feedback`: at most six objects, each containing `criterion`, `status`,
  `observation` and `references`. Criterion and observation are nonempty text
  limited to 2,048 UTF-8 bytes each; status is `observed`, `partial` or
  `unverified`; references are at most six nonempty strings, each limited to
  2,048 UTF-8 bytes. References are retained as literal text, not opened.

Reports retain the note's source and timestamp; neither claims nor authorship
are authenticated. They do not complete tasks. A design question is withheld
for historical scope, stale task evidence or a completed task. On a current
non-completed task it may be discussed even when automated build readiness is
blocked; saved guidance stays visible first. The prepared discussion reply binds
the task, scope revision, presentation revision and note digest and grants no
implementation, execution or checkpoint acceptance. Inspect current status and
the continuation again before relying on it. A same-revision note can still be
outdated; inspection does not validate its external reports.

HTML and Markdown use Context, Goal, Desired end state, Current focus, Current
position and Next action. HTML help buttons expose the same definitions used in
the visible reference; the full saved goal and definitions remain available
without JavaScript. Snapshot inspection time and caller-report time are separate.
