# Return to work: current implementation and completion scope

Updated October 22, 2026. Task 1's static implementation is integrated. Its real
interrupted-task acceptance remains open. Start with the
[pause-and-return procedure](../../cli-guide.md#pause-and-return-to-work).

## Implemented and remaining

| Capability | Current position |
| --- | --- |
| Contextual HTML/Markdown briefing | Goal, desired result, current focus, stopping point, recorded progress and owner guidance are implemented in [the existing view](../../../src/attune_harness/task_view.py). |
| Explicit pause context and comparison | [Continuation notes](../../../src/attune_harness/task_continuation.py) bind a caller report to task identity and a retained revision. Comparisons cover saved scope, not a run timeline or external-reference validation. |
| Saved Tasks and assistant handoff | Explicit task collections, local navigation and copyable replies are implemented. Replies identify task/revision and request current inspection; they do not send, approve or execute. |
| Integrated source | [#142](https://github.com/Smart-AI-Memory/attune-harness/pull/142), [#143](https://github.com/Smart-AI-Memory/attune-harness/pull/143) and [#226](https://github.com/Smart-AI-Memory/attune-harness/pull/226) are merged. The view and continuation reader match the 1.5.0 source tag at `7caa86ab6d476e9599b08ff75a81bc816e60c382`. |
| Software evidence | The October 22 source review ran 70 task-view checks and six navigation checks successfully; four opt-in Chrome checks were skipped. The three PRs' exact-head APIs each report 19 completed successful checks. These are separate from fresh installed or human acceptance. |
| Real return journey | Still open: finding the agreed entrance after interruption, understanding the real stopping point, correcting context and reaching the right handoff without rereading the conversation. Record assistance explicitly. |
| Released browser forms | The forms companion handles saved-intent intake and approval. It does not expose the general `/snapshot` briefing. Use static CLI output for this slice. |

The earlier [snapshot design](task-1-design.md) remains historical. The
[first-increment acceptance](task-1-return-to-work.md#walkthrough-and-acceptance)
and [later connected plan](plan.md) keep their requirements. Local reply
preparation is the narrow, documented extension to the original no-script design.

## Bounded completion slice

Update specification status and the existing CLI/skill guidance, test the printed
pause-and-return procedure, open a draft PR and observe one real interrupted
feature-work task. Use the caller-owned note and existing renderer. Keep runtime
source, schemas, dependencies, storage, providers and released GUI policy out of
scope. A demonstrated runtime defect needs a separate bounded proposal.

Record the selected task/runtime, saved note and report, browser/platform,
observed result, assistance and next handoff. Keep private task contents outside
the public PR. Do not substitute deterministic fixtures for the real observation,
or count this assisted walkthrough as independent discovery, S6 acceptance or
full graphical M2/M4 acceptance. The current slice does not start Tasks 2–7.

## Command-owner walk

The printed procedure uses these owners in order. Their full validators remain
authoritative; this table does not introduce additional approvals.

| Step | Source-bound refusal or limit | Valid input from the preceding step |
| --- | --- | --- |
| Inspect **`status TASK`** | [Task reader](../../../src/attune_harness/task_contract.py#L212) and feature-work validation refuse unsafe, malformed or copied owners. | Use the existing task directory, not a guessed ID or copied record. Have the assistant verify the saved owner's profile; take task ID/revision from successful JSON status, which does not repeat `task_profile`. |
| Prepare the explicit pause note | [Note reader](../../../src/attune_harness/task_continuation.py#L19) refuses unknown fields/oversized JSON; raises at lines 30, 33 and 40 reject wrong task identity, invalid revision and a timestamp without timezone. | Retain a new UTF-8 note outside the effects checkout using that identity/revision, current time, actual stopping point and attributed reports. The caller writes the file; no product capture command is implied. |
| Render **`status TASK --format html --continuation NOTE`** | [CLI routing](../../../src/attune_harness/task_cli.py#L214) refuses continuation with JSON or non-feature work. [View inspection](../../../src/attune_harness/task_view.py#L28) validates the owner; [the size guard](../../../src/attune_harness/task_view.py#L67) refuses views over 512 KiB. | Select HTML or Markdown, the same task and explicit bounded note. Historical notes remain readable but obsolete suggestions are withheld. The documented wrapper saves output only after exit 0; a refusal cannot replace the previous report with JSON. |
| Optionally include another task | [Collection owner](../../../src/attune_harness/task_view.py#L544) limits count, distinct directories and total bytes. Invalid additional entries are visibly unavailable; a bad primary fails. | Supply only explicitly chosen directories; at most 20 tasks and 2 MiB of serialized views. The continuation applies only to the primary. One task can open its direct briefing. |
| Reopen and prepare a reply | [Handoff and reply renderer](../../../src/attune_harness/task_view.py#L398) binds task/revision. [Current design-question selection](../../../src/attune_harness/task_view.py#L365) withholds historical/stale/completed questions. | Regenerate successful output, then open that report. **Continue with guidance**, **Correct context** and **Ask a question** prepare local text; **Copy reply** does not send it. |
| Return the handoff to the assistant | [Handoff text](../../../src/attune_harness/task_view.py#L398) requires current inspection and existing authorization. Lifecycle owners retain execution/refusal rules. | Paste the prepared reply. Reinspect the identified task/note before acting. This walkthrough can stop at the valid handoff; opening/copying does not authorize **`resume`**. |

## Acceptance and evidence

The returning user can identify the correct task and explain its goal, stopping
point, evidenced progress, unresolved matters and next useful action, then reach
the valid handoff without rereading the conversation. They can correct the
explanation. Missing history and stale or uncertain state remain visible.
Record the actual outcome and help needed; a failed journey remains open.

The printed-command checks cover current, absent, historical, stale and unresolved
context with disposable owners. Keep task/note bytes unchanged and external
reports attributed. Software checks do not supply the human observation. Existing
qualification and review rules govern the draft PR; merge and publication remain
separate maintainer decisions.
