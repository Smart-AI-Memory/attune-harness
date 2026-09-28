# First-run journey: tasks

**Status: approved September 28, 2026. All seven tasks implemented the
same day, each in its own pull request and awaiting Patrick's merge:** T1 #172,
T2 #173, T3 #174, T4 #175, T5 #176, T6 #177, T7 #178. T3–T7 are stacked on T1
in that order. T2 is based on `main`. Each `src/` pull request records its
different-model review (Claude Sonnet 5). The 1.1.0 prepare pull request and
the publication follow the merges. A checkbox means implemented, not merged. Requirements are in [design.md](design.md), questions Q1–Q5
in the [README](README.md).

## Order

T1 first, because it turns every later task's done condition into a CI
result. T2 is the smallest change with the widest reach. After those, T3–T6
are independent and can be separate PRs in any order. T7 closes out.
`src/` changes get the different-model review, as usual.

- [x] **T1: the cold-start journey test, red first (R6).**
  Scope: `tests/test_cold_start_journey.py`, a doc-block extractor under
  `scripts/`, one step in `qualification.yml`'s installed-wheel jobs, and
  `<!-- journey: -->` tags on the blocks that already run. Each step that
  fails today is `xfail(strict=True)` with the walkthrough's reason, so each
  later task must flip its own xfail to pass.
  Done when: the job runs on all six platform jobs; `demo` and `test` pass;
  `init`, `review`, `fix`, `plan`/`build` and `status --format markdown` are
  strict xfails naming the task that will fix them.
  Size: one PR, no `src/` change.

- [x] **T2: publish the Claude Code plugin with the Harness skill (R4, Q4).**
  Scope: `plugin/attune-harness/.claude-plugin/plugin.json`, a generated
  `plugin/attune-harness/claude-skills/attune-harness/`, both
  `plugin/attune-harness` manifests' versions, the plugin README,
  `.agents/skills/attune-harness/SKILL.md`'s version line, a new
  `.claude-plugin/marketplace.json`, and a test pinning:
  the shared manifests' version = package version, the Claude copy identical
  to its source, the skill absent from the shared `./skills/`, and
  `plugins/attune-harness/` unchanged.
  Done when: the test passes; every R4 non-interference check passes (Codex
  package output, Codex validator, one skill entry in Codex, unchanged wheel
  and sdist file lists); and a fresh Claude Code session that installs from
  the marketplace completes the skill to a `test` receipt (a recorded manual
  receipt). Merging this PR is the publication. Patrick approves the merge
  separately.
  Size: one PR, no `src/` change.

- [x] **T3: `init` and registry refusals (R1, R2 registry part).**
  Scope: new `init_cli.py`, `cli.py` and `cli_help.py` registration,
  `surface.json`, golden rows `init` and `init-refusal`, the missing-registry
  refusal in `review_cli.py`, `task_cli.py` and `work_cli.py`.
  Done when: T1's `init` step passes, and `review`, `plan` and `fix` without a
  registry return `next_action` naming `init`.

- [x] **T4: path refusals and the documented review example (R3).**
  Scope: `task_contract.py` path refusals, the CLI guide's review section,
  golden refusal rows that gain words but no keys.
  Done when: T1's `test_path_refusal_explains_resolution` passes; each path
  refusal names its base and resolved path; the guide shows the bundled
  example's working invocation, which T1's `test_review_bundled_example`
  already pins, and T7 tags it.

- [x] **T5: `--format markdown` and `status` profiles (R5).**
  Scope: the six task verbs' parsers, one shared renderer over existing
  presentation Markdown, `task_view.py`'s profile gate, `surface.json`,
  `docs/compatibility.md`'s `status` paragraph.
  Done when: T1's `status --format markdown` steps pass for every profile, and
  a golden check shows each verb's exit code identical under both formats.

- [x] **T6: one refusal shape (R2 remainder).**
  Scope: the option-combination `parser.error` calls in `task_cli.py`, refusal
  envelopes for `plan`, `review`, `fix`, `test`, `build`, `status` and
  `resume`, new golden refusal rows.
  Done when: every refusal row in `docs/envelopes.md` for those verbs carries
  `error` and `next_action`, at exit 2.

- [x] **T7: the journey is the documentation, then release (R7, Q5).**
  Scope: the README's five-minute path, each CLI-guide verb section opening
  with a tagged runnable block, the changelog, release notes for 1.1.0.
  Done when: T1 has no xfail left (or each remaining one is a named, accepted
  limit in the README table), the walkthrough table is re-run, and the release
  runbook's qualification passes.

## Estimate

Seven PRs. T1, T2 and T7 are documentation, tests and packaging; T3–T6 touch
`src/` at the CLI and presentation layers only, with no runtime, saved-state
or execution-route change.
