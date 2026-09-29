# Attune Harness 1.2.0 release notes

`1.2.0` gives a stuck review task a way forward. When the `claude` CLI refused
a participant turn before any model ran, for example because the login had
expired or the account was out of usage credits, the task could not be resumed
or reconciled. The only way on was a new task, which repeated turns that had
already completed and been paid for (#182). Use an isolated environment:

```sh
pipx install 'attune-harness[all]==1.2.0'
```

The v1 compatibility contract holds. No JSON envelope key, default or exit code
changes, and `docs/deprecations.json` stays empty. The new flag and the new
saved event field are additive.

## What is new

- **`reconcile-task --retry-refused`** (and `reconcile-review --retry-refused`)
  authorizes one retry of a participant turn the Claude CLI refused. It is
  available only when the CLI exited with a structured error result that has no
  structured output and an explicitly empty `modelUsage`. The failed turn saves
  that result as `native_refusal`. Diagnostic text alone never qualifies. The
  retry is recorded as an operator decision alongside that evidence, and
  provider usage may repeat. `resume` then continues. Completed turns, including
  another participant's finished turn, are replayed rather than dispatched
  again. A turn without this evidence still reconciles with a recovered reply,
  or `cancel-task` closes the record.
- **`init` names the flags each route takes.** For the `claude` and `codex`
  profiles, `next_action` now says a review needs `--allow-external` and only
  `plan` and `build` also take `--allow-native`. The `requires` field is
  unchanged.

## Recovering a refused turn

```sh
attune-harness status TASK_DIR
attune-harness reconcile-task TASK_DIR --event EVENT_ID --retry-refused
attune-harness resume TASK_DIR
```

Fix the cause first (log in again, or add credits). See
[the recovery workflow](recovery-workflow.md).
