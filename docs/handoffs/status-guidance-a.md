# Implement A — plan/build status and next-action guidance

September 18, 2026. Patrick selected **A** for implementation. The work so far
is source inspection only; no production code or tests have changed for A.
Patrick selected a fresh task using this same checkout directly. His earlier
worktree selection was accidental and is withdrawn. Continue A here from this
handoff; the originating task will stop implementation work to avoid overlap.

## Contract

- Project: `/Users/patrickroebuck/attune-harness`.
- Mode: implement the bounded A opportunity.
- Outcome: plan/build results clearly state what happened, whether it blocks
  progress and the valid next action, with a reference to complete saved evidence.
- Done when: current draft/planning/build states have accurate guidance; stale
  work never suggests ordinary acceptance; required-check failures remain blocking;
  optional advice stays optional; uncertain execution never suggests a blind
  retry; relevant behavior checks pass and documentation describes actual support.
- Estimated implementation work: 10–15k working tokens, not a hard authorized
  token cap or a billed-token prediction. Keep work focused and reuse existing code.

B (durable decision persistence), C–F, broader release work, paid experiments,
publication and active plugin upgrades are outside A. The October plan and
October 1 reminder already exist; do not recreate them or treat the proposed
270k October budget as permission to execute those phases now.

## Workspace and evidence

The current checkout contains substantial existing modified and untracked work,
including plan/build implementation and experimental receipts. Preserve it.
A clean checkout from HEAD will omit needed work. Inspect status before editing;
do not reset, stash, commit or publish unrelated files. Read this handoff and
current source rather than reconstructing the full experiment history.

Original experiment grades and receipts must remain untouched. Plan/build Tasks
1–7 are accepted, native Task 8 remains open. A is a presentation improvement;
it does not qualify native model reliability or change execution authority.

## Inspected code and concrete finding

- [`work_cli.present`](../../src/attune_harness/work_cli.py) builds plan/build
  output over `work_status`. It provides draft/planning next actions but no
  equivalent build-result guidance. In inspection mode, its freshness exception
  sets `status=stale`, then the following branch can attach the normal acceptance
  or staging instruction. Correct this precedence without weakening freshness.
- [`work_runtime.work_status`](../../src/attune_harness/work_runtime.py) supplies
  current revision, checkpoint, authority, run status, completed steps, preserved
  prior completion and missing information. Inspect the validated saved run for
  reasons; do not invent a second source of execution state.
- [`test_change.present_test_task`](../../src/attune_harness/test_change.py) is the
  existing pattern for current outcome, next action, saved evidence and grammar.
  Reuse its conventions rather than creating another UI framework.
- [`work_build`](../../src/attune_harness/work_build.py) owns dependent execution,
  freshness and build validation. Inspect `check_build_fresh`, `validate_build`
  and `build_work` for exact error/advisory/event shapes before deciding copy.
- [`work_effects.control_runners`](../../src/attune_harness/work_effects.py)
  rejects unavailable required runners and returns unavailable optional runners
  as advisory. Preserve this distinction. `_error` in the CLI currently emits
  status and exception detail, including failures before a saved build exists.
- `execute_control` routes feature-work status/resume to the same presentation.
  Keep JSON fields, exit codes, read-only status behavior and existing command
  contracts compatible; prefer additive presentation fields.

Never claim no effects occurred unless the journal establishes that. A completed
planning proposal is not a completed build. A check passing is not proof of every
semantic claim. Keep summaries concise and full findings accessible.

## Next implementation steps

1. Inspect the exact saved outcomes and run focused scratch reproductions for
   stale guidance, required-check availability and optional advice. Preserve the
   baseline result. Do not call a native participant.
2. Write the short design note required by Patrick's core-path/>50-line rule
   before production edits: cases, actual probe results and rejected alternatives.
   A is already selected; do not invent another routine approval gate.
3. Implement presentation and next-action precedence in the existing CLI owner,
   extracting a small helper only if it improves clarity. Keep acceptance,
   dispatch, journal and recovery policy unchanged.
4. Verify actual command behavior for stale draft, accepted work, paused progress,
   failed checks, unavailable required check, optional advice, uncertain execution
   and completed results. Use real local fixtures where practical; status must
   neither change saved work nor dispatch calls. Add meaningful regressions for
   misleading guidance, not tests that simply mirror a message dictionary.
5. Run relevant work CLI/runtime checks, update the
   [guidance examples](../user-guidance-examples.md) and
   [opportunity log](../opportunity-log.md), and report the actual verified scope.
   Keep B pending and distinguish source changes from an installed host upgrade.

## Existing verification material

Start with `tests/test_work_cli.py`, particularly the complete console journey,
stale-draft inspection and cross-process tests. `tests/test_work_build.py` supplies
scripted local workers and a disposable Git fixture; `tests/test_work_controls.py`
exercises the actual Spec collector. Relevant failure/recovery tests also live in
`tests/test_work_repair_resume.py` and `tests/test_work_invalid_reply.py`.

The prior qualified local runtime paths below existed during inspection; check
them before use. They are dependencies, not substitutes for importing the current
Harness source under test:

```text
/private/tmp/attune-fresh-resolution-y74ui3g8/integrated/bin/python
/private/tmp/task7-installed-spec-n2emxesr/installed
/private/tmp/repair-feedback-qualified-dimrbw3e/installed
```

The system `python3` lacks `tomllib`; the retained runtime is Python 3.12.
Disable usage/version pings as in prior local qualification. No new provider
budget or subagent work is needed for A.
