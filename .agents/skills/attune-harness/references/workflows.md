# Workflow reference

Read the selected route's installed `--help` before constructing a command.
The examples below show the 0.6.0 interface. Paths, participant names and
checkpoints are placeholders, not default choices or authorization.

## Plan and build

Prepare `work.json` from the user's intent, explicit participant assignments,
inputs, budgets, controls and ordered tasks. Select prompt, XML or Spec according
to the work's requirements; do not turn a simple task into mandatory spec work.
For file construction, freeze supported effects and protected verification before
acceptance. Do not guess the request/effect schema from these command examples.

In a Harness source checkout, read `docs/cli-guide.md`,
`docs/specs/plan-build/dependent-build.md` and the request construction in
`scripts/check_installed.py` (`FREEZE` and `journey_checks`). For an installed-only
environment, consult the same files at the installed version's repository tag;
the [0.6.0 CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v0.6.0/docs/cli-guide.md)
is the baseline for this skill. If matching schema documentation is unavailable,
report that gap instead of fabricating a build manifest.

```sh
attune-harness plan --request work.json --project /path/to/checkout \
  --config /path/to/participants.json --task-dir /path/outside/checkout/task
```

Read returned questions and the current checkpoint. If a configured planner is
needed and dispatch is authorized, use `plan --task-dir TASK --run` with its
authorized dispatch flags, then `--stage --checkpoint CHECKPOINT`. Stage retains
a new unaccepted draft; it is not scope approval. Resolve retained findings and
questions before accepting the current draft:

```sh
attune-harness plan --task-dir TASK --accept --checkpoint CHECKPOINT
attune-harness build TASK --allow-external --max-operations 4
attune-harness status TASK
attune-harness resume TASK --allow-external
```

Native participants additionally require `--allow-native`. Add flags only within
authorization; accepting the plan alone is insufficient. Importing a legacy plan
with `--import-plan` never imports its approval. An outside-project import needs
the explicit `--allow-outside-project` flag and retains a conversion receipt.

Plan/build pause returns 1; blocked/failed execution returns 2. Exit 0 still needs
the result's status to distinguish draft, accepted and completed work.

## Review

Prepare the document, local evidence corpus and verification-context JSON. The
registry selects an assessor and, for independent review, a separate reviewer.
Collect missing inputs through the returned form. `--accept --intake-only`
prepares accepted inputs without execution; use acceptance only for a scope the
user has authorized. An execution example is:

```sh
attune-harness review --goal "Check the guide against project evidence" \
  --project /path/to/project --config /path/to/participants.json \
  --document docs/guide.md --context context.json --corpus docs \
  --query "retention policy" --criteria "Identify unsupported claims" \
  --assessor alpha --accept --task-dir /path/to/review-task
```

For a second assignment add `--plan independent-review --reviewer beta`.
Command/native participants need `--allow-external` and the corresponding user
authorization. `--pause-after 2` saves an interruption; inspect `status TASK`,
then `resume TASK`. A completed review is not proof that its narrative is correct.

## Fix

Use an exclusively owned clone with a local `.git` directory, not a linked
worktree. Keep task state outside it. The bounded POSIX profile replaces listed
existing UTF-8 files; creation, deletion, renames and links are unsupported. Read
the installed route and platform limits before preparing a repair.

Prepare the failing probe before dispatch: `argv`, `cwd`, `timeout`,
`max_output_bytes`, `environment` and `oracle_paths`. Keep the probe and its
oracles protected from the worker. Inspect the registry and choose the authorized
review policy. Example after concrete scope acceptance:

```sh
attune-harness fix --goal "Repair addition" --project /path/to/parent \
  --checkout /path/to/parent/dedicated-clone --scope src/math.py \
  --probe /path/to/probe.json --config /path/to/participants.json \
  --worker alpha --reviewer beta --review required \
  --criteria "The frozen probe passes without changing its oracle" \
  --task-dir /path/outside/clone/fix-task --accept --allow-external
```

The host applies the proposed replacement and records failed-before/passed-after
evidence. Required native review needs a different configured model. Inspect
uncertain writes before using `reconcile-task`; never treat cancellation as rollback.

## Test

Select a supported local POSIX Git checkout, working-tree change scope and an
interpreter containing the project's test dependencies. State capture and actual
pytest execution are separate steps:

```sh
attune-harness test --project /path/to/repo --scope src/example.py \
  --interpreter /path/to/venv/bin/python --task-dir /path/outside/repo/test-task
attune-harness test --task-dir /path/outside/repo/test-task \
  --checkpoint PREVIEW_CHECKPOINT --accept
attune-harness status /path/outside/repo/test-task
attune-harness resume /path/outside/repo/test-task
```

Present the preview's selected checks and excluded coverage before acceptance.
To test completed repair/build output, use `--from-task TASK` instead of
project/scope, with a new task directory; the test preview needs its own acceptance.
Changed source or completion evidence invalidates that handoff.

The interpreter supplies pytest and dependencies. Plugin autoload is disabled;
use `--pytest-plugin` only for required project plugins. `test`/`resume` return
0 for passed tests, 1 for preview/failure/no executed tests, and 2 for interrupted
or blocked execution. Collection-only and all-skipped runs are not passing tests.

## Status and resume

Use the task directory returned by the workflow, not a guessed task ID. `status`
is read-only; inspect its outcome rather than equating exit 0 with verified work.
`resume` may dispatch participants or effects under the saved policy. Confirm the
remaining work is within authorization. Completed attempts replay saved evidence;
uncertain attempts require inspection/reconciliation, not automatic repetition.
