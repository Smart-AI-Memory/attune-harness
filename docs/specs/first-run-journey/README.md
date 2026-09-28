# First-run journey: every verb works from a fresh install

**Status: Q1–Q5 ruled as recommended by Patrick on September 28, 2026
("all five as recommended"); the tasks await spec approval before
implementation.** Written September 28, 2026 against main `1b56ce5` (1.0.1). It belongs to the
stabilization period in [the project plan](../../project-plan.md) and is the
prerequisite for its S6 gap, the named non-programmer walkthrough: a
walkthrough is not worth scheduling while three of the five task verbs cannot
start without undocumented setup.

Read in order:

1. This page: the outcome, the evidence and the questions for Patrick.
2. [Requirements and acceptance](design.md): R1–R7 and what each must not change.
3. [Tasks](tasks.md): the order, the scope of each PR and its done condition.

## Outcome

A person who has just run `uv tool install 'attune-harness[all]'`, or their
agent in Claude Code or Codex, can complete `test`, `review`, `fix` and
`plan`/`build` on the bundled examples, without hand-writing configuration,
reading design notes or parsing JSON. CI proves this on every platform by
running the documented commands as written.

## Evidence: a cold walkthrough of 1.0.1

Fresh `uv tool install --force --refresh 'attune-harness[all]'` on macOS,
Python 3.11 tool environment, a scratch Git repository with one function and one
test, deterministic participants only, no model calls. One reviewer, one
platform; this is a defect list, not a usability measurement.

| Journey | Result | What stopped it |
|---|---|---|
| `python -m attune_harness` | Completed | - |
| `test --scope --interpreter`, then `--checkpoint --accept` | Completed, 0.65 s | - |
| `status --format markdown` on that test task | Refused, exit 2 | "Human-readable snapshots require feature-work-v1", although `test` had just printed the same task as Markdown inside its envelope |
| `plan --request` | Refused | Needs `--config` naming a participant registry. No command writes one; `--help` does not say what one contains |
| `review --goal` | Refused after three attempts | No `./participants.json` ("Not a regular input file"); then the bundled example's `context.json` sits outside `examples/local-workflow/project`, and task intake requires it inside ("context must be inside the project and outside task state"). `--config` resolves against the working directory, `--document` and `--context` against `--project`; the error does not say so |
| `fix --goal` | Refused | argparse usage error on stderr, not an envelope: needs `--checkout`, `--scope`, a hand-written probe JSON and a registry |
| "Ask your agent" in Claude Code | Not available | The `attune-harness` skill lives in `.agents/skills/` only. `plugin/attune-harness/.claude-plugin/plugin.json` says version 0.6.0 and "development candidate", and its skills are `spec`, `cross-review`, `smart-test`, `release-execute` and `attune-release-check`; the Harness skill is not among them. The skill itself says it "targets the 0.6.0 CLI" |

Refusals came in three shapes: argparse usage text (`fix`), an envelope with
`next_action` (`plan`), and an envelope without one (`review`).

**A correction to the walkthrough notes.** The `test` preview exits 1, which
the walkthrough first counted as a defect. It is not: `test-preview` is pinned
at exit 1 in [the envelope table](../../envelopes.md), where a draft record is
a stopped control verb. This spec leaves every exit code unchanged.

## Constraints this spec inherits

- **The 1.0 freeze.** [The compatibility list](../../compatibility.md) pins the
  verbs, options, choices and defaults, every envelope's top-level keys,
  `status` values and exit codes, and "every verb prints one JSON object".
  Everything below is additive: a new verb, new optional flags, new optional
  envelope keys, new golden rows. Each rewrites its fixture on purpose with a
  changelog line; none needs a deprecation.
- **D30.2.** The Claude/Codex plugin lives under `plugin/`, is versioned with
  the package, is installed from the checkout until the deprecation notice, and
  is published to the marketplace with it. This spec fixes the version and the
  skill set; it does not move the publication date unless Q4 says so.
- **No model on the CI path.** Every journey here runs with deterministic or
  command participants. Native participants keep needing `--allow-native`;
  `init` writing a native registry makes no call.

## Questions for Patrick, ruled

All five were ruled as recommended on September 28, 2026. None weakens an
acceptance, provider-spend or recovery gate.

| | Question | Ruled (as recommended) |
|---|---|---|
| Q1 | How does a new user get a participant registry? | A new verb, `attune-harness init`, writing `participants.json` from a named profile: `demo` (deterministic, offline), `claude`, `codex`. It refuses to overwrite. Not chosen: documentation plus copyable example files only |
| Q2 | How do people get readable output, given JSON is frozen as the default? | An optional `--format markdown` on the task verbs, printing the Markdown the envelope already carries; JSON stays the default everywhere. Not chosen: switching to Markdown when stdout is a terminal, which breaks "every verb prints one JSON object" for interactive scripts |
| Q3 | Path resolution between `--config` and `--document`/`--context` | Keep both rules (changing either is a behaviour change) and make every path refusal state the rule, the value given and the path it resolved to. Fix the example layout to match the rule |
| Q4 | Plugin publication | Keep D30.2: sync the shared plugin's version, add the Harness skill for Claude Code only (R4) and install from the checkout now; the marketplace waits for the notice. Not chosen: publishing the plugin at 1.1.0, ahead of the notice |
| Q5 | Release vehicle | 1.1.0, a minor release: a new verb and new optional flags, no frozen-surface break |

## Out of scope

Changing any default, exit code or path-resolution rule; model calls in CI;
the portable cross-host journey ([its own spec](../portable-user-journey/README.md),
which should follow this one); new task profiles; Windows `fix`/`test`
qualification beyond today's; the non-programmer walkthrough itself (S6),
which this spec makes worth scheduling.
