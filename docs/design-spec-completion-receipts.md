# Spec completion evidence repair

2026-09-17. Approved scope: O-08 in the three-task release-readiness follow-through.
Design note written before production edits. AI edits belong only to the isolated
`attune-ai-memory-adoption` worktree; the active installed MCP host is not upgraded.

## Observed behavior

The original workspace/state suite passes 60 checks. A separate two-task lifecycle
probe nevertheless reproduces the defect: both tasks are completed, but neither
execution proof appears in the terminal Markdown. `_complete_task` clears the
current task receipt and renders `_artifact_section`, whose probes came from plan
creation. Its returned `save_state` also omits task-result evidence. The recorded
probe is `docs/receipts/release-readiness-follow-through/terminal-before.json`.

The same omission therefore affects both immediate completion and resume. This
repair preserves accepted execution evidence in the existing plan-state comment,
alongside progress, rather than adding a parallel journal or reconstructing facts
from historical prose. Existing old plans remain readable; their missing execution
evidence must be disclosed explicitly. Planning evidence remains available under
an explicitly historical heading.

## Cases and design

- Manual approval and automatic continuation retain each accepted task's exact
  severity, score, probes, detail and disposition, in completion order.
- A high result acknowledged by the user remains visibly an acknowledged risk;
  it cannot become an ordinary green task merely because the ladder ended.
- Redo/retry never promotes a rejected result into the accepted-results list.
- The existing atomic `save_state`/`load_state` round trip retains accepted
  receipts, and `_resume` restores them before executing the next task.
- Legacy completed IDs without receipts are reported as evidence unavailable.
  Invalid, duplicate or foreign persisted receipts must not be rendered as valid
  accepted evidence or silently reset completed progress.
- Persisted proof text can contain newlines, Unicode, backslashes and HTML-comment
  delimiters. JSON must round-trip inside the plan comment without regex
  replacement interpretation or premature comment termination.
- Existing action binding, task order, high-severity pause, lifecycle checks,
  completed-plan resume rejection and authority semantics remain unchanged.

Use a small typed accepted-result wrapper in the workspace adapter. Add a
backward-compatible optional receipt list to the existing persisted state and
include it in the existing `save_state` payload. Validate restored receipt shapes
at the adapter boundary and keep them bound to completed IDs. Render final progress
and accepted task details separately from historical planning artifacts/probes.

Compatibility clarification from the independent review: schema 2 adds an
**optional** receipt list, not a guarantee that every completed ID has one. The
existing `spec/runner.py::execute_with_approval` also writes `SpecState` and records
completed IDs without workspace receipts. A resumed legacy plan can likewise
have old completed IDs without evidence alongside newly accepted results. Both
must remain readable and explicitly disclose missing evidence. Schema version
alone cannot establish receipt provenance or completeness. The workspace must
retain every receipt it actually accepts; callers cannot reconstruct earlier
evidence merely from a completed ID. Fully authoritative receipt provenance would
be a separate contract change, not a prerequisite for this display repair.

## Alternatives and verification

Rejected: overwrite planning probes with the last result (loses earlier results
and provenance); concatenate prose into one list (loses task/disposition binding);
keep receipts only in memory (repeats the defect after resume); introduce a second
receipt database (unnecessary competing persistence).

Verify real host creation-to-terminal and save/reopen/continue sequences, explicit
risk acknowledgement, retry and old-plan compatibility. Regressions must fail on
the original behavior and when the repaired protections are removed. Run the
existing spec/command-host suites, changed-code coverage, required repository gates
and the different-model review before acceptance. The new wheel's installed
consumer will prove the fix; the unchanged active plugin can still show the old
summary until a separately authorized installation/activation.
