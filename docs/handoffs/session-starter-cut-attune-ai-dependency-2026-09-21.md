# Session starter: make attune-harness run without attune-ai

Written 2026-09-21 at the end of the 0.1.0 release session. Paste the block under
"Prompt" into a fresh Claude Code session started in `~/attune-harness`. This note
authorizes nothing. Every push, tag and workflow dispatch needs Patrick's approval.

## Prompt

> Project: attune-harness (`~/attune-harness`, trunk is `main`, currently
> `0.2.0.dev0`). Mode: (b) executing a planned spec, starting with the spec itself.
>
> Outcome: attune-harness's memory feature works in a clean environment with attune-ai
> not installed, and there is a written decision about the Spec tie.
>
> Done when: (1) `attune-harness memory capabilities --config <fixture>` succeeds in a
> fresh venv containing only attune-harness; (2) a CI job with attune-ai absent
> exercises memory context and records what `plan --accept` does; (3) qualification is
> six of six green; (4) a decision on the Spec tie is recorded in the spec; (5) the
> README claims only what that clean environment demonstrates.
>
> Effort cap: the spec plus the memory adapter port. The Spec tie gets a decision, not
> an implementation, unless I say otherwise.
>
> Read `docs/handoffs/session-starter-cut-attune-ai-dependency-2026-09-21.md` first,
> then `docs/specs/native-memory/scoping.md` on branch
> `wip/local-snapshot-2026-09-19`. Use `/spec`. Write a design note before touching
> `memory_context.py` or any sanitizer or path-validation code: those are core,
> security-sensitive paths. Ask before every command that pushes, tags or dispatches a
> workflow.

## What is true today (verified 2026-09-21 on `main` at `3b3b5ff`)

Patrick's position: attune-ai must not be a dependency of attune-harness; code was
brought over from attune-ai and modified, the memory system among it.

The state does not match that yet. Four modules import attune-ai at ten sites, and
`pyproject.toml` names attune-ai nowhere (no dependency, no extra).

| Module | Imports from attune-ai | Kind |
| --- | --- | --- |
| `memory_context.py:21` | `attune.memory.harness_adapter.CompatibilityAdapter` | Feature tie: `MemoryHost.__init__` cannot run without it |
| `spec_bridge.py:51,190,194` | `attune.pipeline.spec_reader.read_spec`; `attune.elicitation.command_workspace` (`CommandWorkspaceHost`, `CommandWorkspaceProjection`); `attune.spec.workspace` (`SpecWorkspaceAdapter`, subclassed, and `SpecWorkspaceState`) | Feature tie: `plan --accept`, and `--import-plan` via `read_spec` |
| `attune_bridge.py:12,109,124` and `memory_bridge.py:8,102,111` | `attune.plugins.base`, `attune.plugins.registry`, `attune.mcp.server` | Plugins loaded by attune-ai. Not entry points; nothing in Harness imports them. Expected: a plugin imports its host. Leave alone |

Harness has no in-tree copy of `harness_adapter.py`, `command_workspace.py` or
`workspace.py`.

### The finding that changes the priority

`attune.memory.harness_adapter` **does not exist in any released attune-ai.** In
`~/attune-ai` it is only on branch `codex/shared-memory-adoption`, commit `c170febaf`
("feat(memory): optional shared Harness memory worker adapter and CLI route"). It is
not on attune-ai `main` (`fa7112219`), no tag contains it, and the branch has no PR.
attune-ai 16.4.0 on PyPI therefore almost certainly lacks it (inferred from the
branch state; the wheel was not downloaded and inspected). So harness memory is
unavailable for everyone, even with attune-ai installed, except in an environment
built from that branch. `~/attune-harness/.venv-attune-bridge-check` may be such an
environment; not inspected.

It fails safely. `memory_cli.py` catches `ImportError` and prints
`{"status": "unavailable", "detail": "Optional current-memory adapter dependencies are
unavailable", ...}` with exit code 2. The 0.1.0 README labels memory "experimental and
not activated for live memories". So this is not a 0.1.1 emergency.

## The memory port is smaller than it looks

- `harness_adapter.py` on that branch is 423 lines.
- Harness uses four members of `CompatibilityAdapter`: `binding`, `capabilities`,
  `query`, `resolve` (all in `memory_context.py`).
- It already imports Harness's own contract:
  `attune_harness.memory_contract` (`CLASSIFICATIONS`, `bounded_json`, `strings`) and
  `attune_harness.review_contract` (`bounded_text`, `digest`, `fields`, `parse_json`,
  `versioned`). It is half in Harness already, and living in attune-ai makes the two
  packages import each other.
- What must be cut or ported, its five attune-ai imports:
  `attune.memory.file_stash` (`DEFAULT_TTL_DAYS`, `FileStashBackend`),
  `attune.memory.personal` (`PersonalMemory`),
  `attune.memory.session_stash` (`prepare_strict_content`, `recall_entries`,
  `recent_entries`), and `attune.security.path_validation` (`_validate_file_path`).
  Sizes and transitive imports of those four were not measured. Measure them first:
  that is ladder Task 1, and it decides whether this is a small port or a large one.

This lines up with the scoping note: N1 (cut the functional tie), N2 (port the
reader, not the whole memory system), N4 (the Task 1 compatibility fixtures are the
format contract), N5 (two copies of security-sensitive code only as a bounded
transition, guarded by differential tests against attune-ai's implementation while
both exist). Ladder Tasks 1 to 3 are this work.

## The Spec tie has no plan at all

`spec_bridge.py` leans on about 1,370 lines of attune-ai: `spec/workspace.py` (813
lines, itself importing `attune.elicitation.command_workspace`,
`attune.elicitation.spec_intake`, `attune.pipeline.spec_reader`,
`attune.security.path_validation`, `attune.spec.state` and `attune_forms`),
`elicitation/command_workspace.py` (504 lines, imports `attune_forms`) and
`pipeline/spec_reader.py` (56 lines, imports `attune.security.path_validation` and
`attune.wizards.decomposer`). The scoping note covers memory only. Patrick decides
between: port it; replace `plan --accept` with a native acceptance path; or keep it as
a plainly stated optional integration. The third is compatible with "attune-ai is not
a dependency" only if the README says so and the feature reports unavailable cleanly.

## Order of work, proposed

1. Spec (successor to the native memory scoping note, extended to name the Spec tie).
2. Ladder Task 1: measure the four attune-ai memory modules and their transitive
   imports; confirm the compatibility fixtures cover `binding`, `capabilities`,
   `query`, `resolve`.
3. Design note, then port the adapter and what it needs into Harness, with
   differential tests.
4. CI job with attune-ai absent.
5. Decision on the Spec tie, recorded.
6. README wording: start from
   `docs/handoffs/README-independence-wording-draft-2026-09-21.md`, and make it say
   what step 4 demonstrates.

## Repository facts the next session needs

- `main` is the trunk. It holds published 0.1.0 plus `0.2.0.dev0`, the
  `docs/handoffs/` and `docs/reflections/` ignore rules, and the real publish workflow
  with `ref: ${{ github.sha }}` checkouts. `main` requires linear history, signed
  commits, resolved conversations and the six qualification jobs; PRs land by squash.
- `v0.1.0` points at `8fc26a4`, the commit published to PyPI. The tag must not move.
  `8fc26a4` is not an ancestor of `main` (squash), so
  `release/0.1.0rc1-packaging` cannot be merged cleanly again; cut future release
  branches from `main` and add them to the `pypi` environment's branch policy.
- `wip/local-snapshot-2026-09-19` holds `docs/opportunity-log.md` and
  `docs/specs/native-memory/scoping.md`, neither of which is on `main`. It lacks the
  Windows record-replace fix and fails qualification on Windows in
  `scripts/qualify_platform.py` with a `TimeoutExpired` that predates 2026-09-21. Its
  24-odd commits have no decided fate. Getting the log and the scoping note onto
  `main` is a sensible early step for the spec session.
- Local Python: pyenv has `mcp 1.29.1`; Harness pins `mcp==2.2.0`, and the package is
  not installed for subprocesses, so many tests fail locally. CI is the reference.
  pytest output for qualification is in the uploaded artifact (`tests.txt`,
  `tests.xml`), not the job log.
- Pin `-R Smart-AI-Memory/attune-harness` on `gh` commands.
- zsh traps met this session: `$var:word` is parsed as a modifier (brace it:
  `${var}:word`); unquoted `$pair` is not word-split; `grep` without `-F` treats `$`
  in a pattern as an anchor, which silently returns 0 matches.
- A Claude Code session running in a worktree cannot edit files in the main checkout,
  and its permission classifier refuses forced tag moves.
