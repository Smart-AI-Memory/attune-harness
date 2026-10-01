# Attune Harness 1.3.0 release notes

`1.3.0` lets `plan` and `fix` start from a command. Until now, both verbs
needed a file nobody wrote for you: `plan --request` needed a work request
with a frozen effects manifest, and `fix` needed a trusted probe. `init --for`
writes each one, checked by the verb that reads it (O-70). Use an isolated
environment:

```sh
pipx install 'attune-harness[all]==1.3.0'
```

The v1 compatibility contract holds. Envelope keys only grow: `init` adds
`files`. Existing defaults and exit codes are unchanged, and
`docs/deprecations.json` stays empty. One argparse effect is new: `init --f`,
`--fo` and `--t` are now ambiguous abbreviations. Spell `--force`, `--tests`
or `--task-dir`.

## What is new

- **`init --for fix`** writes `probe.json`, the trusted probe `fix` reads. It
  runs the named tests with pytest. Before writing, `init` runs the same freeze
  `fix` runs, as a dry run, so anything `fix` would refuse is refused first, in
  the same words. It runs nothing. Its `next_action` is the `fix` preview.
- **`init --for plan`** writes a work request `plan --request` accepts as
  written: the goal, the scope, the named tests as acceptance, one task,
  distinct worker and reviewer, and an effects manifest frozen over the
  checkout. It goes beside the task directory, as `<task-dir>.work.json`,
  outside the checkout the manifest freezes. Writing it accepts nothing: the
  preview and `--accept` stay separate steps. A refused `init` removes what it
  wrote.
- **Example participants** in `examples/starter/participants.json` finish both
  journeys with no model call. They are example code, not a profile: `lead`
  applies one declared replacement and `reviewer` approves without judging.
  They need `python` on PATH.
- **Symlink refusals name the path to use.** On macOS, `/tmp` and `/var` are
  symlinks, so a task directory under them is refused. The refusal now says
  which link and what to use instead (O-76).

## The two journeys

The CLI guide's `plan` and `fix` sections open with blocks that CI runs as
printed on the installed wheel. The `fix` block runs on POSIX only, as `fix`
is qualified.

```sh
attune-harness init --for fix --project /path/to/repo --scope calc.py \
  --interpreter /path/to/venv/bin/python --tests tests/test_calc.py
```

See [Plan and build](cli-guide.md#plan-and-build) and
[Scoped repair](cli-guide.md#scoped-repair).

## Known limits

- The registry `init` writes by default (the offline `demo` profile) can
  preview and accept a plan but cannot build it. Its participants carry review
  tools and cannot propose files, so `build` refuses with "Build proposals
  cannot carry review tools or policies" (O-77). Use the example registry
  above or your own participants for `--config`.
- `--test-root .` is still refused (O-76).

## Evidence

The publish run, PyPI hashes and each release gate's receipts, or the gap where
there is none, are indexed in [the project plan](project-plan.md#where-each-gates-evidence-is).
