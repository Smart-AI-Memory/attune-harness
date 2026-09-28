# First-run journey: every verb works from a fresh install

**Status: Q1–Q5 ruled by Patrick on September 28, 2026: Q1–Q3 and Q5 as
recommended; Q4 changed later that day to "publish the Claude plugin now
provided it will not interfere with the library working in codex or
antigravity". Patrick approved the spec the same day ("approve the spec, start T1"); T1–T7 are authorized in order.** Written September 28, 2026 against main `1b56ce5` (1.0.1). It belongs to the
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
| `review --goal` | Refused three times; works when invoked another way | No `./participants.json` ("Not a regular input file"). The walkthrough then took `examples/local-workflow/project` as `--project`, which leaves `context.json` outside the project, and task intake refuses that ("context must be inside the project and outside task state"). *Corrected during T1:* with `--project examples/local-workflow`, the bundled example completes offline. No documented command shows this, and the refusal gives the resolved path without saying which base resolved it: `--config` resolves against the working directory, `--document` and `--context` against `--project` |
| `fix --goal` | Refused | argparse usage error on stderr, not an envelope: needs `--checkout`, `--scope`, a hand-written probe JSON and a registry |
| "Ask your agent" in Claude Code | Not available | The `attune-harness` skill lives in `.agents/skills/` only. `plugin/attune-harness/.claude-plugin/plugin.json` says version 0.6.0 and "development candidate", and its skills are `spec`, `cross-review`, `smart-test`, `release-execute` and `attune-release-check`; the Harness skill is not among them. The skill itself says it "targets the 0.6.0 CLI" |

### The same walkthrough after T1–T7, September 28, 2026

Re-run against the T7 head (#178, stacked on #172 and #174–#177), with the
same scratch repository, macOS, deterministic participants and no model
calls. Stdin is closed, as for an agent.

| Journey | Result |
|---|---|
| `python -m attune_harness` | Completed, exit 0 |
| `attune-harness init` | Created `participants.json` (demo), exit 0; its `next_action` runs as printed |
| `test ... --format markdown`, preview then accept | Markdown preview (exit 1, a draft), then `passed` (exit 0) |
| `status --format markdown` on that test task | Rendered, exit 0 |
| `plan --request` without `--config` | Refused, exit 2, with the pinned detail and a `next_action` naming `init`. It still needs a work request with a frozen effects manifest: an accepted limit, documented in the CLI guide |
| `review --goal ... --intake-only --format markdown` | The intake form, exit 1 (a draft) |
| `fix --goal` alone | A JSON refusal on stdout, exit 2, with a `next_action`. It still needs a checkout and a trusted probe: an accepted limit, documented |
| "Ask your agent" in Claude Code | The plugin is published by #173. The live receipt is owed after merge (it needs Patrick signed in) |

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
  is published to the marketplace with it. Q4 moves the publication forward
  to T2; the location and versioning terms stand.
- **No model on the CI path.** Every journey here runs with deterministic or
  command participants. Native participants keep needing `--allow-native`;
  `init` writing a native registry makes no call.

## Questions for Patrick, ruled

All five were ruled on September 28, 2026, Q4 against the original recommendation. None weakens an
acceptance, provider-spend or recovery gate.

| | Question | Ruling |
|---|---|---|
| Q1 | How does a new user get a participant registry? | A new verb, `attune-harness init`, writing `participants.json` from a named profile: `demo` (deterministic, offline), `claude`, `codex`. It refuses to overwrite. Not chosen: documentation plus copyable example files only |
| Q2 | How do people get readable output, given JSON is frozen as the default? | An optional `--format markdown` on the task verbs, printing the Markdown the envelope already carries; JSON stays the default everywhere. Not chosen: switching to Markdown when stdout is a terminal, which breaks "every verb prints one JSON object" for interactive scripts |
| Q3 | Path resolution between `--config` and `--document`/`--context` | Keep both rules (changing either is a behaviour change) and make every path refusal state the rule, the value given and the path it resolved to. Fix the example layout to match the rule |
| Q4 | Plugin publication | **Publish the Claude Code plugin now**, from a `.claude-plugin/marketplace.json` in this repository as attune-forms does, provided it does not interfere with Codex, Antigravity or the Python library (conditions in R4). This amends D30.2's timing, which tied publication to the deprecation notice; D30.2's other terms stand. Not chosen: installing from the checkout until the notice |
| Q5 | Release vehicle | 1.1.0, a minor release: a new verb and new optional flags, no frozen-surface break |

## Out of scope

Changing any default, exit code or path-resolution rule; model calls in CI;
the portable cross-host journey ([its own spec](../portable-user-journey/README.md),
which should follow this one); new task profiles; Windows `fix`/`test`
qualification beyond today's; the non-programmer walkthrough itself (S6),
which this spec makes worth scheduling.
