# Starter files: `plan` and `fix` start from a command

**Status: implementation and release preparation complete; 1.3.0 publication pending.** Approved September 30, 2026. Patrick approved Q1–Q6 as
recommended; Q6's vehicle moves to 1.3.0 because 1.2.0 shipped first. Written against
main `3d2dcea` (1.1.0). It takes up O-70 in
[the opportunity log](../../opportunity-log.md), the largest gap left by
[the first-run journey](../first-run-journey/README.md), and the macOS path
refusal in O-76 that a user meets next.

Read in order:

1. This page: the outcome, the evidence and the rulings on Q1–Q6.
2. [Requirements and acceptance](design.md): R1–R5 and what each must not change.
3. [Tasks](tasks.md): the order, the scope of each PR and its done condition.

## Outcome

A person with Harness installed can go from a Git checkout and a named file
to an accepted `plan` with a finished `build`, or to a finished `fix`, using
only commands printed in the CLI guide. No JSON is written by hand and no
Python is run. CI proves this on every platform by running the guide's `plan`
and `fix` blocks as written.

## Evidence

After 1.1.0, `init` writes the participant registry, and `test` and `review`
finish from commands. `plan` and `fix` still stop at the point where a user
has to supply files:

| Verb | What it needs that no command writes | Owner that validates it today |
|---|---|---|
| `plan --request` | `work.json`: `intent` (goal, context, scope, constraints, acceptance, questions), assignments, tasks with checks, and for `build` an `effects` manifest frozen before acceptance | `work_contract` (request), `work_effects.freeze` / `validate_manifest` / `validate_request_effects` (effects) |
| `fix --probe` | A probe JSON: `argv` with an absolute executable outside the checkout, `cwd` `"."`, timeout, output limit, an allowed environment, 1–20 oracle files outside scope | `repair.validate_probe`, frozen by `task_contract.freeze_repair_contract` |

The only thing that writes a frozen request is the `FREEZE` snippet in
`scripts/check_installed.py:231-275`, which calls `work_effects.freeze` from
Python. The guide has no example `work.json`. The `fix` section shows a probe
in prose (`docs/cli-guide.md:473-482`) and gives the checkout's entry limit
as 1,000. That figure is out of date: `effect_limits.MAX_ENTRIES` has been
2,048 since #144.

Two more facts constrain the design:

- **Deterministic participants cannot write during a build.** `work_build`
  allows a deterministic turn only read-only effects (`work_build.py:431-436`).
  So the `demo` registry from `init` can take a plan to acceptance, but a
  build that changes files needs a command or native participant. The
  installed-wheel check uses a command participant (`PEER` in
  `check_installed.py:220-228`).
- **macOS paths (O-76).** `safe_storage` refuses a task directory with a
  symlinked parent, `repair.root_handle` refuses a checkout the same way, and
  `plan` requires `project_root` to equal its resolved path. `/tmp` and `/var`
  are symlinks on macOS, so the guide's `--task-dir /tmp/my-work` is refused
  there.

## Constraints this spec inherits

- **The 1.0 freeze.** [The compatibility list](../../compatibility.md) treats
  new verbs, new optional flags and new optional envelope keys as additive.
  The surface guard pins every option string, choice and default, so each
  change rewrites `tests/fixtures/compatibility/surface.json` on purpose, with
  a changelog line. No exit code and no pinned key changes meaning.
- **The owners stay the owners.** A starter file is valid because the module
  that reads it says so, not because the writer produced it. The writer calls
  the same validators before it writes anything.
- **No model on the CI path.** As in the first-run journey.
- **Acceptance stays a separate act.** Writing a starter request records no
  decision. The user still previews and accepts it with `plan`.

## Questions for Patrick, ruled September 30

| | Question | Recommendation | Not chosen, and why |
|---|---|---|---|
| Q1 | Which command writes the starter files? | New optional flags on `init`: `init --for plan\|fix --scope FILE… [--interpreter PY] [--tests PATH…]`. A new optional envelope key `files` lists what was written, and `path` still names the registry. `init` stays the single "set me up" verb. | A new `scaffold` verb, which adds a second setup verb to learn. `plan --scaffold` and `fix --scaffold`: `plan`'s `--request` sits in a mutually exclusive group and `fix` requires `--probe`, so both would bend frozen argument rules. |
| Q2 | When is the effects manifest frozen? | At write time. `init --for plan` calls `work_effects.freeze` and writes a request ready to preview. If the checkout changes before acceptance, `plan` refuses as it does today, and its `next_action` says to run `init --for plan --force` again. (At T3: `--force` once the preview refuses; with a new `--task-dir` once `plan` has made the old one, because `plan` creates it exclusively.) | A new `plan --freeze` step. It adds a verb option and a second moment where the snapshot can go stale. |
| Q3 | What finishes the build in the CI journey? | A command worker shipped under `examples/starter/`, used by the guide's `plan` block and by CI. It applies one declared replacement inside scope, so the journey ends at a completed build. The `demo` registry and profile are unchanged. | Ending the CI journey at plan acceptance, which proves less than O-70's done condition asks for. Letting deterministic participants write, which changes a safety rule in `work_build`. |
| Q4 | Does `init --for fix` run the probe? | No. `init` writes and validates, and runs nothing. `fix` already refuses a probe that passes before the repair, in words that say so ("Repair requires an observed failing baseline probe", `task_policies.py:298-299`), and the guide's `fix` block starts from a failing test. | Running the probe once and warning if it passes. That executes project code during `init`, which runs nothing today. |
| Q5 | Is O-76 part of this spec? | Yes, the small half. The guide's examples move to a task directory outside `/tmp`, and the symlink refusals name the resolved path to use instead. The symlink rule itself is unchanged. `init --for` writes resolved paths, so the files it writes never trip it. | Accepting `/tmp` and `/var` as system aliases, which changes a safety rule and deserves its own ruling. |
| Q6 | Release vehicle? | 1.3.0, a minor release: new optional flags and envelope keys, no break to the frozen surface. (Drafted as 1.2.0; 1.2.0 shipped a separate fix first.) | — |

## Out of scope

- Generating the goal, constraints or acceptance criteria. The starter
  request carries placeholders that `plan` already reports as missing
  questions, and the user or their agent fills them in.
- Native registries for `build`, and any model call in CI.
- Windows `fix` qualification beyond today's, and relaxing the linked-worktree
  or checkout-size rules.
- `review` and `test`, which already finish from commands.
