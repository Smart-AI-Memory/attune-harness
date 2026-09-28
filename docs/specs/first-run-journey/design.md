# First-run journey: requirements and acceptance

**Status: Q1–Q5 ruled September 28, 2026; awaiting spec approval.** Overview, evidence and rulings are in the
[README](README.md). Each requirement names what it must not change; the
[freeze](../../compatibility.md) governs anything not named.

## R1: a starter participant registry (Q1)

`attune-harness init [--profile demo|claude|codex] [--project DIR] [--force]`
writes `participants.json` at `schema_version` 1 into the project.

- `demo` writes the deterministic `lead`/`reviewer` pair from
  `examples/review/participants.json`. `claude` and `codex` write a lead and a
  reviewer on different models, as a required native review demands; the model
  IDs come from a table in the package, not from the network.
- The file validates through the existing registry reader before it is
  written. An existing file is refused unless `--force`, and `--force` keeps
  the old file as `participants.json.bak`.
- The envelope reports the path, the profile, whether any participant needs
  `--allow-external` or `--allow-native`, and a `next_action` naming a command
  that runs as printed.
- `init` makes no model call, reads no credentials and writes nothing outside
  the project.

Must not change: the registry schema, any verb's `--config` default, or the
rule that a native participant needs `--allow-native` at dispatch.

## R2: refusals that name the next step

When `plan`, `review` or `fix` cannot find a registry, the refusal says so in
those words and its `next_action` names `attune-harness init`. Every refusal
from `plan`, `review`, `fix`, `test`, `build`, `status` and `resume` carries
`error` and `next_action`. The argparse `parser.error` calls in `task_cli.py`
that reject a *combination* of valid options become JSON refusal envelopes
with exit 2, the exit code argparse already uses. Unknown flags and malformed
argv stay argparse errors.

Must not change: any exit code, or any pinned key of an existing row. New keys
on refusal envelopes are additive and rewrite the golden rows.

## R3: path refusals that explain resolution (Q3)

A refusal about an input path states which base it resolved against (the
working directory or `--project`), the value given and the resolved path. The
bundled examples are laid out so each documented verb accepts them: the
review example's `context.json` moves inside its project, or the project root
moves up, whichever keeps the legacy `review-form` example working unchanged.

Must not change: how any path resolves.

## R4: the agent path ships in Claude Code, without touching Codex (Q4)

Claude Code discovers skills in `~/.claude/skills/`, a project's
`.claude/skills/` and installed plugins. It does not read `.agents/skills/`,
the location Codex's standalone discovery uses, so the Harness skill has no
path into Claude Code today. Two Codex artifacts already exist and must keep
working unchanged:

- `plugins/attune-harness/`, the Codex task-verb plugin (0.1.0), packaged by
  `scripts/package_codex_plugin.py`, whose version is independent of the
  package by [its documented rule](../../codex-plugin.md).
- `plugin/attune-harness/`, the shared Spec-workspace plugin under D30.2, with
  both a `.claude-plugin` and a `.codex-plugin` manifest reading `./skills/`.

So:

- The Harness skill reaches Claude through `plugin/attune-harness/` in a
  directory only the Claude manifest names (for example
  `claude-skills/attune-harness/`, added to `.claude-plugin/plugin.json`'s
  `skills` beside `./skills/`). It is **not** added to the shared `./skills/`,
  where a Codex user with both plugins installed would see the skill twice.
- `.agents/skills/attune-harness/` stays the one source. The Claude copy is
  generated from it and a test fails when they differ; nobody edits the copy.
- The shared plugin's two manifests carry the package version (D30.2); the
  Claude description drops "development candidate" for what ships.
  `plugins/attune-harness/` keeps its own version and packaging.
- The skill's "targets the 0.6.0 CLI" line becomes a check against the
  installed CLI surface (`cli_surface`), which serves every host that reads the
  skill.
- The plugin README gives one install sequence from the checkout that a fresh
  Claude Code session follows to a working skill.

Antigravity has no packaging in this repository and no participant adapter.
This spec adds neither; the host-neutral pieces (the skill text, `init
--profile demo`, `--format markdown`) are what it would consume when it is
qualified under [the portable journey](../portable-user-journey/README.md).

Must not change: `plugins/attune-harness/`, the shared `./skills/` set, the
Codex manifests' skill paths, the workspace MCP profile, D30.2's publication
timing, or the skill's rules on acceptance and permissions. Moving the
maintainer skills (`release-execute`, `attune-release-check`) out of the shared
plugin would change what Codex users get too, so it is left to a separate
decision.

## R5: readable output on request (Q2)

`plan`, `build`, `review`, `fix`, `test` and `resume` accept
`--format json|markdown`, default `json`. `markdown` prints the Markdown the
envelope already carries (`markdown` or `presentation.markdown`), then one
line naming the saved record and the next action. The exit code is the one
the JSON path would return. A verb whose envelope has no Markdown for that
state renders `summary`, `error` and `next_action` as text; it never prints
nothing.

`status --format markdown|html` extends from `feature-work-v1` to the
`pytest-change-v1`, assessment and repair profiles, reusing each profile's
existing presentation. Oversized views and genuinely unsupported profiles keep
today's JSON refusal and exit 2.

Must not change: the JSON default, any JSON envelope, any exit code, the
read-only nature of `status`.

## R6: a cold-start journey test, run by CI

A test module installs the built wheel into a fresh virtual environment and,
from an empty temporary directory with no `ATTUNE_*` variables and no
`participants.json`, runs:

1. `python -m attune_harness`.
2. `attune-harness init --profile demo`.
3. `test` preview and accept on a generated two-file repository.
4. `review --goal ... --accept` on the bundled example, to `completed`.
5. `fix` on a generated repository with a deterministic or command worker and
   a generated probe, to failed-before/passed-after. If no offline worker can
   produce a replacement, the case stops at accepted intake and the gap is
   recorded here, not hidden.
6. `plan --request`, `--stage`, `--accept`, then `build` and `status`, offline,
   reusing the R2 journey in `scripts/check_installed.py`, whose build worker
   and reviewer are one local script run as two command participants. What
   this step adds is that it starts from `init` and the documented commands,
   not from a registry the script writes itself.
7. `status --format markdown` for each task above.

The commands come from the documentation: every fenced block in `README.md`
and `docs/cli-guide.md` preceded by `<!-- journey: NAME -->` is extracted and
run with placeholders substituted from one table, so a documented command that
stops working fails CI. The job runs on the existing six installed-wheel
platform jobs; POSIX-only verbs record their Windows refusal as today.

Must not change: the no-model rule in CI; the existing qualification jobs'
names or required status.

## R7: the journey is the documentation

`README.md` gains a five-minute path, *install, init, test, review*, made of
journey-tagged blocks. The CLI guide's per-verb sections each open with one
runnable tagged block before any qualification prose. Long qualification
paragraphs move below the example.

## Acceptance for the whole spec

- R6's job passes on all six platform jobs for the release candidate's wheel.
- Each R1–R5 change has its golden, surface and document rows rewritten on
  purpose, with a changelog line, and `docs/deprecations.json` stays empty.
- A fresh Claude Code session, with the plugin installed from the checkout
  per R4, runs `$attune-harness` to a completed `test` receipt. This is a
  recorded manual receipt, like the host display receipts under D30.7, not a
  CI threshold.
- The walkthrough table in the README is re-run and every row reads
  *Completed*, or states a named, accepted limit.
