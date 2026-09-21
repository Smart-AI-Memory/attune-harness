# Spec authority, Task 2: plan

September 21, 2026. Patrick accepted [Task 1's verdicts](verdicts.md) the same
day (D12 in [the addendum](addendum-2026-09-21.md)) and asked for Task 2 to be
lined up. This is the plan. **Status: proposed. No code has been written, and
none starts until Patrick says go.**

[The note](README.md) defines Task 2 as "bring adopted modules and their tests
into Harness", with the evidence "tests green under Harness CI; no `import
attune`". Task 1 found no module fit to adopt as written, so Task 2 carries
**adapt** modules: each comes with its tests, and with its named seam reworked
in the same change.

## What Task 2 covers, and what it leaves to Task 3

Task 2 carries the three leaf modules whose seams can be fixed without any new
design. The other three adapt modules in the spec path wait for Task 3.

| Module | Task | Why there |
| --- | --- | --- |
| `security/path_validation.py` | 2 | No imports. Its seam is a Windows check |
| `<task>` parser lifted from `wizards/decomposer.py`, with `pipeline/spec_reader.py` | 2 | Needs only `path_validation` |
| `spec/state.py` | 2 | Needs only the two above |
| `elicitation/command_workspace.py` | 3 | Its seam is locking. R1 needs decisions refused across processes, which is Task 3's design |
| `spec/workspace.py` | 3 | It *is* the approval authority Task 3 specifies |
| Four names from `elicitation/spec_intake.py` | 3 | Only `workspace.py` uses them |
| `memory/harness_adapter.py` and the store reader | its own spec | D10 and D11 |

This split is a proposal. The note's ladder does not say which module belongs to
which task.

## The steps

One pull request each, in this order. They cannot run side by side: each adds a
line to `CHANGELOG.md` and a test to the platform selection, and 2.3 imports
what 2.1 and 2.2 add. So each starts from `main` after the one before it has
merged.

### 2.1 Path validation

- **Outcome:** `attune_harness/paths.py` with a public `validate_file_path`,
  carried from `_validate_file_path`.
- **The seam:** on Windows it matches substrings such as `\etc\` and
  `\program files`, so `C:\repo\etc\plans\x.md` is refused. Compare resolved
  path components against the protected roots instead.
- **Done when:** its 19 tests pass under Harness; new cases show a legitimate
  repository path containing `etc`, `sys`, `dev` or `program files` is accepted
  and the real system directories are still refused; the Windows jobs run them.
- **Size:** small. 93 lines, 19 tests, plus the Windows cases.

### 2.2 The task parser and the plan reader

- **Outcome:** `attune_harness/spec_tasks.py` holding `DecomposedTask`, the
  `<task>` parser (189 lines lifted from the decomposer) and `read_spec`.
- **The seam:** `read_spec` builds a `TaskDecomposer(workflow=None)` only to
  reach its parser. Harness gets the parser alone, with no `workflows.compat`.
- **Constraints from Task 1's XML test:** it parses extracted `<task>` blocks and
  never a whole file, with the standard library parser and no new dependency.
  The five hostile-input cases stay in its suite.
- **Done when:** the reader's 10 tests and the parsing cases from the
  decomposer's 66 pass; the five hostile cases pass; and for each of the seven
  plans in `.claude/plans/` on the wip branch, `to_dict()` output is identical
  to Attune AI's `read_spec`. `spec_bridge.legacy_plan` consumes that shape
  today (`spec_bridge.py:67`), so it must not drift. The comparison needs Attune
  AI installed, so it is run once in a scratch environment and reported in the
  pull request; it cannot be a CI test.
- **Size:** medium. About 245 lines.

### 2.3 Spec state

- **Outcome:** `attune_harness/spec_state.py`, carried from `spec/state.py`.
- **The seams, all from Task 1:** refuse an unknown `schema_version` instead of
  loading it, accepting 1 and 2 as `spec_bridge.py:43` already does; take the
  plans directory as an argument, not the relative default `".claude/plans"`;
  and agree with `spec_bridge.plan_content` on where the state comment lives, a
  single trailing comment, so one never writes what the other refuses.
- **Done when:** the 130 tests are ported and pass; new tests show version 0, 3
  and a missing version are refused with a plain next action (R4), and a plan
  with a misplaced state comment is handled the same way by both modules.
- **Size:** medium. 319 lines, and the largest test port.

### 2.4 Use the Harness reader in the bridge

- **Outcome:** `spec_bridge.legacy_plan` calls Harness's `read_spec`, and its
  import of `attune.pipeline.spec_reader` is gone.
- **Why now:** it is the first piece of the bridge's retirement (Task 4) that
  becomes possible, and it is small. Reading an imported plan stops needing
  Attune AI; accepting one still does, until Task 3.
- **Done when:** `legacy_plan` works with Attune AI absent, proven by a test that
  runs in CI. `spec_bridge.py` stays on the import check's `KNOWN` list, because
  it still imports the workspace modules.
- **Size:** small.

## Rules for every step

- **Provenance.** Each carried file's pull request names its source: the Attune
  AI branch `codex/shared-memory-adoption` at `b89f7953f`, and the path. Both
  projects are Apache-2.0 and have one owner.
- **Tests travel with the code,** unchanged where they can be. Any test that is
  changed or left behind is listed in the pull request with the reason.
- **Review.** Every step changes `src/`, so each is reviewed by a different model
  before it merges, and the pull request records who reviewed it and what they
  found (AGENTS.md; D5 for the verdicts themselves is already done).
- **Design note first.** 2.1 changes a security check and 2.3 changes what is
  refused. Each gets a half-page note in its pull request before the diff: the
  cases, what was tried, and the alternative that was rejected.
- **Python 3.10 and Windows.** None of the three modules uses a feature newer
  than 3.10. Each step's tests join the platform selection in
  `scripts/qualify_platform.py`, because a Windows fix that only Ubuntu tests is
  not evidence.
- **No `import attune`.** The import check from #28 already fails the build if a
  carried module brings one.

## Decisions to make before starting

1. **The split above:** Task 2 carries three leaf modules and the bridge change;
   `command_workspace.py`, `workspace.py` and the `spec_intake` names move to
   Task 3.
2. **A stale pin.** Adding tests to `scripts/qualify_platform.py` changes a file
   that `testpypi-candidate-source.json` pins by hash. That file records the
   0.1.0rc1 rehearsal of September 18, and its pin for `publish-pypi.yml` already
   stopped matching. The receipt is not edited; the pull request says which pin
   goes stale.
3. **R4's wording.** R4 speaks of schema version 1. The format's current version
   is 2, and Harness accepts both today. Record in the addendum that R4 covers 1
   and 2, leaving the note as written.

## What this plan does not do

It does not start Task 3, touch memory, change any limit, or publish anything.
It does not size the work in tokens: Task 1 explains why there is no measured
baseline. After 2.1 merges there will be one: what a small step actually cost.
