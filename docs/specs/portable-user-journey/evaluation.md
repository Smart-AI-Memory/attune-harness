# Journey evaluation

**Status: draft for approval; read-only evaluation, not a live user trial.**
Baseline and scope are in the [overview](README.md). This evaluation distinguishes
source/test inspection from executed qualification. No model calls were made.

## What exists

| Journey stage | Primary evidence | Assessment |
|---|---|---|
| Ask only what is missing | `work_contract.missing_information`; `tests/test_work_contract.py::test_vague_intent_preserves_answered_and_optional_questions` | The owner filters structured facts. Extracting them correctly from conversation remains the assistant's responsibility. |
| Correct before execution | `work_contract.revise_work`; `test_corrected_goal_preserves_history_but_invalidates_assignment_and_authority` | Saves history, increments revision and clears acceptance/bindings for changed work. Reuse. |
| Preserve an unchanged decision | `test_unchanged_revision_preserves_accepted_decision` | The tested no-op correction preserves record bytes. This is not a blanket guarantee for every planning/execution state. |
| Continue a saved task | `task_cli.execute_control`, `work_cli.execute_control`, `work_contract.check_work_fresh` | Routes feature work to its owner and preserves dispatch checks. No live cross-host journey was demonstrated by this review. |
| Correct after partial completion | `work_runtime._steer_build` | Settled dependent builds only; completed prefix must remain unchanged. Uncertain effects must be reconciled. General scope edits after execution are not supported by this operation. |
| Orient after interruption | `task_view.inspect`, `task_continuation.read_continuation`, `tests/test_task_view.py` | One validated snapshot; stale/uncertain guidance takes precedence. External continuation notes do not manufacture acceptance or completion. |
| Inspect completion | `execution_evidence.work_execution_evidence`, `task_view._sections`, `_body` | Validated record pointers and expandable supporting detail exist. A summary mapping each criterion to evidence and a consistent outcome-level Inspect results action are not established. |
| Submit a decision | `command_workspace`, `spec_workspace`, `workspace_mcp` | Revision/nonce/contract conventions exist. Workspace MCP explicitly refuses lifecycle/execution publication until its separate gates exist; do not route this proposal through that unqualified path. |

Harness evidence paths above are under `src/attune_harness/` unless marked as
tests. Existing tests were inspected, not rerun. The installed Harness tool
interpreter lacks pytest; it was not modified to perform this planning review.

## Forms findings relevant to this journey

Forms source at the pinned revision is available in the
[Forms repository](https://github.com/Smart-AI-Memory/attune-forms/tree/4191c4e0c6bfe7ff21e4dd926f0ba8202775a9a7).

- `bridge.select_form_surface` exposes widget capability and keyboard mode, but
  no host-profile parameter. `_route` tests the Claude AskUserQuestion profile.
  `mcp_server._host_question_profile` selects the registry's route-active target.
- A read-only probe against installed Forms 0.17.0 returned `ask` for four
  two-option questions, admissible under the Claude profile. This says nothing
  about another host's question count or reply format.
- A numeric field with `widget_capable=False` returned `ask`, while host-question
  admissibility was false. The API documents that ask includes conversation;
  this is an ambiguous fallback contract for consumers, not a proven data loss.
- `host_question_turn` is stateless; the caller supplies attempt count and prior
  answers. Its profile declares a response deadline, but the collection path
  does not enforce elapsed time. A consuming host must own that lifecycle.
- The released stability document has stale statements about the host-question
  path and workspace tiers. Those documentation corrections are separate Forms
  maintenance work; they do not prove the journey is broken.

The probes disabled bytecode and telemetry. They tested routing only. No native
question was submitted to Claude, Codex or Antigravity during this review.

## Walkthrough and failure cases

1. **Intake.** Preserve CSV, filters and exclusion of private notes. Ask only
   current page versus all records. Do not ask which model the user prefers
   unless model choice is genuinely a decision affecting this task.
2. **Correction.** Save current page as the effective choice and revise any
   affected tasks/checks before acceptance. The old all-records choice remains
   historical. A receipt cannot still claim the superseded criterion passed.
3. **Acceptance.** Show the resulting scope and bind the user's explicit decision
   to that exact revision. A correction alone is not permission to execute; do
   not add a second confirmation if one valid decision already accepts this
   revision through the trusted collector.
4. **Host switch.** Read the saved task again using the same directory/checkout.
   Derive current scope and guidance from the owner, not a summary in the new
   model's prompt. Preserve acceptance if still valid. Changed registry, provider
   permissions, evidence or effects are separate changes, not incidental UI.
5. **Interruption.** If an effect is unresolved, explain what needs reconciling.
   Do not retry it or treat an interrupted call as cancellation or success.
6. **Later correction.** If pending-suffix steering accepts the change, preserve
   completed evidence and show the new scope. Otherwise retain the original task
   and prepare successor scope for explicit acceptance. No automatic rollback.
7. **Completion.** Show the outcome with Inspect results. Opening it shows the
   criteria, recorded checks, relevant revision and limitations. A claim without
   a linked check is visibly unverified, not silently inferred from model prose.

## Findings to carry forward

| ID / lens | Finding | Priority and confidence | Follow-up |
|---|---|---|---|
| J1 / user | Host-specific routing and portable fallback need an explicit shared contract | High; source/probe supported; live behavior unmeasured | Design R1/R2, tasks T1/T2 |
| J2 / contract | Correction storage exists; assistants still need consistent orchestration and impact explanations | High; source/test inspection supported | R3/R4/R5, T1/T3 |
| J3 / user | Evidence is retained but not yet presented as the agreed outcome-level one-action summary | High; presentation source supported; usefulness unmeasured | R6, T4 |
| J4 / evidence | Cross-host continuity and human benefit cannot be inferred from parser tests | High; qualification gap, not a demonstrated host failure | R7, T5 |

The smallest useful implementation slice is T4's evidence summary using existing
records. The more consequential risk is J2: a correction represented differently
in prose, stored scope and execution. T1 therefore locks that contract down first.

Forms' recorded outcome pilot completed 72 simulated units successfully but could
not rank conditions by success; human effort/abandonment were unmeasured. See its
[results](https://github.com/Smart-AI-Memory/attune-forms/blob/4191c4e0c6bfe7ff21e4dd926f0ba8202775a9a7/docs/specs/outcome-experiment/outcome-pilot-v0.2-results.md).
This plan proposes exploratory actual-host observation, not a claim of comparative
superiority or a new paid benchmark. Findings authorize nothing beyond planning.
