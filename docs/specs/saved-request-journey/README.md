# From an idea to a saved, inspectable request

This implements the selected first GUI journey: idea, clear request, partial
save, reopen, review and deliberate intent acceptance. Additions here are
candidate behavior beyond released 1.3.0. They do not complete the broader
[graphical companion program](../graphical-companion/README.md).

## Starting handoff

An assistant prepares a draft through the existing `create_work` or
`plan --request` owner, using the actual project, supplied file scope, known
context, constraints and configured participants. Missing material answers
remain questions. Follow [Plan and build](../../cli-guide.md#plan-and-build)
for real request construction. Do not invent scope or use the training example
as the user's real task. Task storage stays outside the project. Preparation
creates a draft, not approval or dispatch; no new CLI verb is needed.

Use one installed interpreter throughout. Validate the private structured
launcher's type, version, loopback origin and `execution_enabled: false`, then
open its exact URL using the host browser tool at default placement. Keep the
listener alive. Preserve the host's split view and Files behavior. The
[browser reference](../../../.agents/skills/attune-harness/references/browser.md)
describes launch and reopening; the companion cannot dock native panes.

## Read-only return and prompt explanation

The authenticated workspace GET projects the saved intent, choices, revision
and checkpoint without creating a decision. **View saved request** and **View
accepted request** share approval review's escaped plain-language renderer.
The complete goal, scope, success criteria, context, constraints, questions
and choices remain inspectable after acceptance. Identity and authoring format
are in **Technical details**. Changed inputs show a warning outside the
disclosure and preserve the saved request as historical evidence. Inspection
does not grant current authority, submit an answer or dispatch work.

**How this becomes a prompt** starts closed. It explains prompt sections and
illustrative XML; ordinary answers remain sufficient. Prompt/XML/Spec choice
comes from `work_contract.select_authoring`, not a click. Approval consequences
and blockers remain visible. Preserve Harness's visual style, existing control
labels and the accessibility owner's independent #242 instructions/hints and
`aria-describedby` associations. No questions-render seam is changed here.

## Source-owner walk

Every step uses one registered owner and its current revision. The complete
transitive schema/path/text/budget/registry validators remain authoritative.

| Step | Refusal source | Input flow and required preservation |
| --- | --- | --- |
| Prepare | [`draft_request`](../../../src/attune_harness/work_contract.py#L406), `_validate_intent`, `_validate_request`, `_capture`: invalid fields, unknown assignments, budgets, scope/evidence paths, missing/linked files, state/project overlap; [`safe_storage`](../../../src/attune_harness/task_contract.py#L76): repository metadata | Supply the actual project/config and explicit bounded intent. Capture regular selected inputs; keep task state outside project. The synthetic helper requires an unused directory, creates its supplied evidence and deterministic registry, and accepts nothing. |
| Launch | [`CompanionServer`](../../../src/attune_harness/gui.py#L96): unavailable build mode, noncanonical/nonexistent/duplicate task paths, unreadable owner, outside the 1–20 limit | Register the returned canonical saved task with `--edit --launch-json`; validate and open its private launcher. No browser path or command endpoint is added. |
| Inspect/reopen | [`Decisions._record/inspect`](../../../src/attune_harness/gui_decisions.py): unknown/moved task; [`read_task`](../../../src/attune_harness/task_contract.py#L212): unsafe/invalid record and acceptance; [`Handler.boundary/authenticated`](../../../src/attune_harness/gui.py): foreign Host/Origin or capability | GET reads the same owner. Freshness failure becomes a visible historical warning, not authority. No decision is opened. Restart uses a new private launcher; answers stay saved. |
| Open form | [`Decisions._draft/open`](../../../src/attune_harness/gui_decisions.py): wrong profile/status, active planning/build, stale input/checkpoint; [`WorkAcceptance.open`](../../../src/attune_harness/work_accept.py): incomplete or incompatible authority | Deliberate open supplies the inspected checkpoint. Owner selects remaining questions or review. A second tab invalidates the first collector. |
| Save partial answers | [`Decisions.submit`](../../../src/attune_harness/gui_decisions.py), [`answer_planning`](../../../src/attune_harness/work_runtime.py), [`require_current_decision`](../../../src/attune_harness/work_decisions.py): stale/replayed/foreign decision, empty/malformed/unbound answer | Submit only entered answers to current owner field IDs. Reopen remaining questions; never remap old positional answers. Uncertain saves retain readable input and require inspection, never automatic replay. |
| Accept/reconsider | [`WorkAcceptance._fresh/collect`](../../../src/attune_harness/work_accept.py#L472), [`bind_work_acceptance`](../../../src/attune_harness/work_contract.py#L726): changed revision, readiness, unsupported action, already accepted work | Show exact intent and owner blockers; submit only a displayed single-use choice. Acceptance grants intent only. Reconsider stays unaccepted. Return through GET to inspect accepted answers without another collector. |

## Reproducible populated sample

Run these with the installed candidate interpreter from a repository checkout:

```sh
python examples/browser-intake/prepare.py /absolute/unused/training-form
python -m attune_harness.gui --task /absolute/unused/training-form/saved-task --edit --launch-json
```

This is synthetic preparation, not browser task creation or real implementation.
The fixture scopes `source.py`, retains `Training example` and
`No implementation or model calls`, and leaves goal/success unanswered.

1. Click **Continue form**. Enter `Group saved work by the decision it needs`
   for the goal, then **Save answers** with success still empty.
2. Reopen the workspace, including a listener restart with a new private
   launcher. Inspect the saved goal and scope, then click **Continue form**.
3. Enter `Each saved task shows its next decision` for success and save.
4. Click **Review your answers**. Review all answers and allowed files; choose
   **Accept this intent** or **Keep draft for reconsideration** deliberately.
5. Reopen and expand **View accepted request**. Confirm the same answers,
   saved revision and separate execution boundary. No new form is needed.

These literal entries match the canonical 1.3.0 Navigation tutorial's signed
local documentation source `86e83c6`; the accepted disclosure is candidate
behavior. Existing released tutorials remain separately owned.

## Observable completion and evidence

Verify the installed sample chain plus stale, replayed, cross-tab, failed-save,
restart, denied-origin and invalid-record cases. Captures show entered answers,
confirmed save, retained answers, approval review and accepted summary. Check
keyboard/disclosures and narrow layout. Label version/commit/state, preserve
private capabilities outside captures, and use actual saved owner state.

A named real-task trial by Patrick or a collaborator remains necessary to
establish comprehension and usefulness. Synthetic software/capture evidence
cannot supply that observation. The article/post follows that trial and reports
observed benefit, confusion and recovery. Publication is a separate decision.
Completion review is complete for this bounded source increment. The changed
vantage reveals a recovery-guidance opportunity: a readable historical request
still needs a clear next step when its inputs change. A task-local opportunity
draft records that observation and the need to test it with a real user; it
authorizes no additional implementation. Real-task observation, combined-candidate
qualification and release decisions remain open as described above.
