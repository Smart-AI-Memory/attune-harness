# Starter files: requirements and acceptance

**Status: approved, September 30, 2026.** Patrick approved the recommended
answers to Q1–Q6 in the [README](README.md), with Q6's vehicle moved to 1.3.0. Each requirement names what it must not change, and
[the freeze](../../compatibility.md) governs anything not named.

## R1: `init --for fix` writes a starter probe (Q1, Q4)

`attune-harness init --for fix --scope FILE… --interpreter PY --tests PATH…
[--project DIR] [--force]` writes `probe.json` into the project, and writes
`participants.json` too if there is none.

- The probe is `[PY, "-m", "pytest", "-q", *tests]`, with `cwd` `"."`, the
  guide's timeout and output limit, the environment `repair` allows, and the
  test files as `oracle_paths`. `PY` is resolved to an absolute path, and
  `init` refuses it if it lies inside the checkout.
- Before writing, the probe passes `repair.validate_probe` against the named
  scope and checkout. A scope or test path that the owner would refuse is
  refused here with the same words.
- `init` does not run the probe (Q4).
- The envelope keeps its pinned keys, adds `files` (every path written, in
  order), and gives a `next_action` naming the `fix` command that uses them,
  runnable as printed.
- An existing `probe.json` is refused unless `--force`, with the registry's
  `.bak` rule.

Must not change: the probe schema, what `fix` accepts, or `init` without
`--for`, whose output stays byte-identical.

## R2: `init --for plan` writes a frozen starter request (Q1, Q2)

`attune-harness init --for plan --goal TEXT --scope FILE… --interpreter PY
--tests PATH… [--project DIR] [--task-dir DIR] [--force]` writes the work
request beside the task directory, as `<task-dir>.work.json`. (Amended
September 30 at T3: the draft wrote `work.json` into the project, but the
effects manifest snapshots the whole checkout, so a file written into it after
the freeze makes the request stale before `plan` reads it. The task directory
must not exist yet, because `plan` creates it. Patrick ruled the request goes
beside it.)

- `intent` carries the goal, the scope and the test files as acceptance
  evidence, so the request can be accepted as written: `plan --accept` refuses
  an empty goal, scope or acceptance ("Unresolved material intent prevents
  acceptance"). Context and constraints are empty, which `plan` allows.
  (Amended September 30 at T1: the draft left the goal empty, which would have
  stopped R5's journey at acceptance. Patrick chose `--goal`, as `fix` has.)
- There is one task whose outputs are the scope and whose check is the pytest
  probe, plus the `final` verification probe `build` preflight requires.
  Worker and reviewer are distinct participants from the registry.
- `effects` is produced by `work_effects.freeze` over the resolved checkout,
  with the task directory outside it. It passes `validate_manifest` and
  `validate_request_effects` before the file is written.
- The `next_action` is the guide's `plan --request` command with the same
  paths. If the checkout changes before acceptance, `plan`'s existing
  staleness refusal gains a `next_action` naming `init --for plan` (with a
  new `--task-dir`, since `plan` has made the old one); the preview's refusal
  when a scope file changed before it names `init --for plan --force`.

Must not change: the request schema, when `plan` refuses, or the rule that
writing a request records no acceptance.

## R3: a command worker that finishes the build journey (Q3)

`examples/starter/` ships a small command participant and a registry that
names it as worker, with a separate reviewer. The worker applies one declared
replacement inside scope. It is used by the guide's `plan` block and by CI.

- It is example code, like `examples/local-workflow`, and not a profile or a
  default.

Must not change: the deterministic read-only rule in `work_build`, or the
`demo` profile.

## R4: the symlink refusals name the path to use (Q5)

The refusals from `safe_storage`, `repair.root_handle` and `plan`'s
resolved-root check add the resolved path, for example "Task storage cannot
traverse a symlink: use /private/tmp/my-work". The CLI guide's examples use a
task directory that is not under `/tmp`. Its stale entry limit (1,000) is
corrected to 2,048.

Must not change: the symlink rule, or the refusal's exit code and envelope keys.

## R5: the guide's `plan` and `fix` sections run in CI

Each of the two sections opens with a `<!-- journey: -->` block that
`scripts/doc_journeys.py` runs as printed, on a scratch checkout, in the six
installed-wheel jobs:

Both use `examples/starter/participants.json` (R3), whose worker `lead` and
reviewer `reviewer` serve build and repair turns alike (ruled at T1; renamed at
T3 from `starter-worker` and `starter-reviewer` to the names `init` writes, so
the assignments in the request `init --for plan` writes name participants the
example registry has).

- `plan-starter`: `init --for plan`, `plan --request` preview, accept,
  `build`, then `status` shows the build as completed.
- `fix-starter`: `init --for fix`, then `fix` on a failing test, ending in a
  completed repair whose after-probe passes.

Must not change: any journey that runs today.

## Acceptance for the whole spec

- Both journeys pass on all six installed-wheel platform jobs, with no model
  call and no hand-written JSON.
- `tests/fixtures/compatibility/surface.json` changes only by the new `init`
  options, and each change has a changelog line.
- `init` without `--for` produces the same output as 1.1.0.
- Every `src/` PR records a different-model review.
