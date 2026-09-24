---
name: attune-harness
description: Run Attune Harness workflows for planning, building, evidence review, scoped repair, testing changes, and inspecting or resuming saved tasks. Use when the user requests Harness workflows or asks to continue a Harness task.
---

# Attune Harness workflows

Translate the user's goal into the installed `attune-harness` CLI. This is the
Harness entry point; the older `/attune` command invokes a different product.

## Select the task

Reuse the project, scope, constraints and acceptance criteria already supplied.
Ask only for missing decisions that affect the work. With no goal, ask what the
user wants to accomplish and offer the routes below. Do not start a workflow just
because the skill was opened.

| Intent | Route | Required context |
| --- | --- | --- |
| Plan new work | `plan` | Goal, exact scope, acceptance criteria, participant registry |
| Execute an accepted plan | `build` | Saved task directory and current accepted scope |
| Check a document against evidence | `review` | Document, verification context, corpus, criteria, assessor |
| Repair a known failure | `fix` | Dedicated checkout, existing files, frozen probe, worker/review choice |
| Test working-tree changes | `test` | Git checkout, changed scope, interpreter with pytest |
| Inspect progress or outcome | `status` | Saved task directory |
| Continue saved work | `resume` | Saved task directory; inspect it first |

`review` assesses documentary evidence; it is not a general source-code security
audit. `test` executes checks; it does not generate a test suite. `ship` and
`reflect` are not implemented task routes. Explain unsupported requests rather
than silently routing them through Attune AI or claiming Harness ran them.

## Establish the runtime

1. Locate `attune-harness` and run `attune-harness --help`. Check the installed
   distribution version using its interpreter when available. Use one explicit
   executable/environment throughout the task; do not mix a global CLI with an
   unrelated checkout's Python modules.
2. Read `attune-harness <route> --help` for the selected route and the relevant
   section of [the workflow reference](references/workflows.md). This skill
   targets the 0.6.0 CLI. If the installed interface differs, inspect that version
   before acting. Report missing dependencies using the CLI's actual diagnostic.
3. If no runtime is available, prepare an isolated `pip install attune-harness`
   environment within the user's installation permissions. Do not upgrade a
   retained environment or install Attune AI to satisfy Harness acceptance.
4. Resolve the actual target checkout and task directory. Keep task state outside
   a checkout used for file effects. Check route-specific checkout/platform
   restrictions before promising execution; `fix` refuses linked worktrees.

## Execute within the accepted scope

- Inspect the selected participant registry before dispatch. Preserve configured
  roles/models; do not invent a provider or silently substitute a deterministic
  demonstration for requested model work.
- Prepare inputs and present the CLI's preview, questions, or checkpoint. Bind
  acceptance to the concrete current scope. Existing explicit authorization may
  be used only when it covers that scope; never infer acceptance from a model
  proposal or from opening this skill.
- For plan/build, scope acceptance does not grant external or paid execution.
  Add `--allow-external` and, for native participants, `--allow-native` only when
  authorized. Other routes have their own flags: read their help and inspect the
  registry for paid calls even when there is no separate native flag.
- Preserve task IDs, checkpoints, checks, budgets and recorded decisions. Do not
  edit a receipt to unblock execution or weaken a protected probe after failure.
- Read structured results as well as exit status. A preview or pause is not a
  completed task; successful `status` means inspection succeeded. A completed
  review can still contain refuted or unknown claims.
- On pause, inspect `status` and continue through `resume` within existing
  authorization. On uncertain effects, retain the record and use the documented
  reconciliation path; do not retry blindly or start a replacement task to bypass
  a blocked record. Stop for missing authority, unsupported scope, or unresolved
  effects, and state the concrete next action.

## Report the evidence

Return the task directory, observed status, verification result, and next action
if unfinished. Link the saved evidence. Separate participant claims from host
checks, software validation from model quality, and supported behavior from
unqualified platforms. This skill does not grant merge, release or publication
authority.
