# Attune Harness 1.1.0 release notes (draft)

**Draft, prepared with first-run journey T7. Not released.** The version, its
changelog heading, the README's release links and the plugin versions are set
by the release's own prepare pull request (see the [release runbook](release-runbook.md)),
after the first-run journey pull requests merge.

`1.1.0` makes every task verb reachable from a fresh install. A cold
walkthrough of 1.0.1 found that only `test` completed: `plan`, `review` and
`fix` needed a participant registry that nothing wrote, refusals came in three
shapes, and the Harness skill had no way into Claude Code. Everything below is
additive under the v1 compatibility contract: no envelope key, exit code,
default or saved-state format changes, and `docs/deprecations.json` stays
empty.

## What is new

- **`attune-harness init`** writes a starter `participants.json`: `demo`
  (two offline deterministic participants, the default), `claude` or `codex`
  (a lead and a reviewer on different models). It refuses to replace a
  registry unless given `--force`, which keeps a backup. Writing a native
  profile authorizes nothing.
- **Refusals name the next step.** `review`, `fix` and `plan` without a
  registry name `init`. Every refusal from the task verbs and controls carries
  `next_action`. A rejected option combination for `review` or `fix` is a JSON
  refusal on stdout rather than usage text on stderr, and still exits 2.
- **Path refusals explain resolution.** `--document`, `--context` and
  `--corpus` resolve against `--project`, and `--config` against the working
  directory. A refusal now says which base it used and what the path resolved
  to.
- **Readable output on request.** `--format markdown` on `plan`, `build`,
  `review`, `fix`, `test` and `resume` prints the same result for people, with
  the same exit code. `status --format markdown|html` works for every task.
- **The Claude Code plugin.** `/plugin marketplace add Smart-AI-Memory/attune-harness`
  installs the Harness skill with `cross-review` and `smart-test`. The Codex
  plugins are unchanged.
- **Documented journeys run in CI.** Blocks tagged in the README and the CLI
  guide run as written, from an empty directory, in every installed-wheel
  platform job.

## Limits

- `plan`/`build` and `fix` still have no copy-and-paste example: they need a
  frozen effects manifest and a trusted probe that no command writes. The
  offline plan, accept, build and review journey in `scripts/check_installed.py`
  covers them in CI.
- Markdown `status` for assessment and repair tasks is the generic envelope
  rendering, not a designed per-profile report.
- This release adds no model or platform qualification. The named
  non-programmer walkthrough (S6) is still to be performed. It is now worth
  scheduling, because each verb starts from a fresh install.
