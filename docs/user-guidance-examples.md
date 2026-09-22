# Warnings and guidance: concrete examples

September 18, 2026. Companion to the [blog draft](blog/controls-savings-user-journey.md).
The numbered examples preview wording and interaction design. **Their proposed
message blocks and action labels are not installed UI features.** Opportunity A
now implements status summaries and next-action guidance in the current Harness
CLI source, as described below. B now retains decision text through the same
plan/Spec surface. The active plugin has not been upgraded. Neither display
feature grants execution or approval authority.

The message blocks show what a user would see. The notes explain when to show
each message and link to the code or test evidence for programmers. Lead with
the practical meaning, explain necessary technical terms, and keep enough detail
to diagnose the problem. Review the claims and reasoning as critically as the prose.

The discussion in “Discuss navigation consolidation” established the direction:
keep optional advice separate from requirements, preserve useful completed work,
show missing evidence, and support short replies, clicks and natural language
without tying input preference to explanation length. The
[navigation design](design-navigation.md) and
[control audit](specs/plan-build/control-audit.md) retain those decisions and limits.

Name the condition, explain its consequence, and give the next useful action.
Use direct verbs for process steps and consistent terms across messages. Preserve
the author's deliberate voice choices; do not replace passive constructions
mechanically. State “no changes applied” only when the execution record proves it.
Distinguish a rejected proposal from a failed check after changes were applied.
Do not offer a continue-anyway action for a missing required protection.

## Implemented in source: plan/build status guidance (A)

The [CLI presentation](../src/attune_harness/work_cli.py) adds `phase`, `summary`,
`blocking`, `next_action`, `advisory` and `evidence` to the existing JSON output.
`blocking` means input, acceptance, investigation or correction is needed before
execution can advance; it is also true for a ready draft awaiting acceptance.
A deliberate pause is resumable and is not itself a failure. Neither this field
nor any suggested action grants dispatch permission.

| Current evidence | Summary and valid next action |
|---|---|
| Draft needs answers | Name missing intent/decisions; submit `plan --answers` bound to the displayed checkpoint. |
| Draft ready for review | Review the record; use `plan --accept` with the exact checkpoint. |
| Draft missing a required runner or planner | Show `readiness_error`; correct the draft before requesting acceptance. |
| Planning proposal complete | Say the work is still a draft; review and `plan --stage`, then review the new draft before acceptance. |
| Stale draft or proposal | Suppress ordinary acceptance/staging; inspect changed inputs, revise or explicitly reimport an edited legacy plan. Update the effect manifest where needed. |
| Accepted, incomplete build setup | Keep accepted authority visible but mark progress blocked; expose `readiness_error` and correct required tasks, runners or checks before new acceptance. |
| Accepted, build setup present | Offer `build` with the current checkpoint and only explicitly authorized dispatch flags. |
| Paused at a valid operation boundary | Retain progress; offer `resume` with the current checkpoint and the saved dispatch permissions. |
| Required control or protected check failed | Keep it blocking, retain completed steps and point to the failed check; a settled failure is not rerun by ordinary resume. |
| Optional check unavailable/failed, or participant notes | Keep optional advice visible separately; it does not turn an otherwise completed build into failure. Low/medium reviewer findings are counted separately from blocking high findings. |
| Saved participant reply rejected | Point to the original reply and validation error, including a pause before decoding; resume will not replace that reply. |
| Running owner or uncertain effects | Inspect the journal/owner; do not blindly retry. Only existing supported file reconciliation is offered. This takes precedence even when files are stale. |
| Completed dependent build | Say protected checks passed and no high reviewer finding blocks completion; offer evidence review, not another build. Passing checks do not prove every semantic claim. |
| Completed file-effect batch | Do not describe it as verified completion of a dependent build. |
| Paused file-effect batch | Continue through its existing owning API; dependent build/resume cannot take over the batch. |
| Stale accepted or built work | Preserve historical completion but do not claim current completion; inspect the mismatch and retain the build journal. Ordinary build rebasing remains unsupported. |

`evidence.record_path` names the complete saved JSON record; `run_pointer`, check
pointers and review pointers locate evidence inside it. Review `action/text`
points to the complete serialized reply. Findings are not shortened to fit the
summary. `run_error` retains saved failures; command errors retain their original
type/detail and add guidance, with a saved-record reference when readable.

`status` is read-only and still exits 0 for a readable owner, including stale or
blocked work. Plan/build/resume exit-code rules are unchanged. An accepted owner
can therefore have `status=accepted` and `blocking=true`; a required control's
settled failure can retain the runtime's `status=unresolved` while the summary
identifies the failed control. Use the summary, evidence and error together.
Repeated status inspection is covered by snapshots and dispatch/write guards.
See [A's verification receipt](status-guidance-a-results.md) and
[design note](design-status-guidance-a.md). B's separate implementation is below.
Broader UI integration, native qualification and the remaining numbered example
wording are outside these implementations.

## Implemented in source: durable decision text (B)

`plan --decision` retains the current planning questions or a complete draft's
Spec approval view in `decision.json` beside the work record. It returns the
usual JSON presentation with an additional `decision` object; it grants no
approval and dispatches no participant. Plan mutations that display missing
questions also retain their text. The in-process `WorkSpecBridge.open()` saves
the actual rendered Spec view before returning it for response collection.

The retained display contains the question/goal, complete choices and their
consequences, evidence references and the existing bound response template.
`decision.display.markdown` is the text fallback when the form is unavailable;
`decision.artifact_path` names the saved file. No option is submitted merely
because it is shown or preselected. Status reads the artifact without creating
a form, dispatching, saving or changing the task checkpoint.

| `decision.state` | Meaning |
|---|---|
| `current` | Text is bound to the current work checkpoint; no collector response is recorded in this artifact. It does **not** establish that the native form or host session is still active. |
| `collected` | The Spec collector consumed the recorded response. Consult the work record for acceptance: acknowledgments and redo choices do not grant it. |
| `historical` | The work checkpoint or freshness changed. Text stays readable; its old answer must not be rebound to current work. |
| `unavailable` | The saved display cannot be read or validated. Status still reports the work and the display error; it does not recreate a decision. |

A task created before this feature may have no `decision` field. For explicit
inspection of the current draft, use:

```sh
attune-harness plan --task-dir /path/to/work --decision
attune-harness status /path/to/work
```

For questions, fill the retained `response_template.answers` using its field map
and submit the existing `plan --answers` JSON. Partial answers create a new
checkpoint and retain the remaining questions; old answer files are rejected.
For console approval, the existing `plan --accept --checkpoint` command remains
available after reviewing the exact work checkpoint. It opens a fresh Spec
decision, retains it and routes the explicit approval through the collector.

A live in-process Spec host can collect a delayed response using the saved bound
template while the same decision remains current. Reopening replaces the display;
old replies are rejected. After a host restart, the text survives but the old
host's response authority is not restored: reopen and use the new binding.
There is no new arbitrary natural-language-to-action parser or second approval
system. High-risk confirmation and required-control checks remain in force.

`decision.json` holds the **latest display**, replaced only by explicit display
or work operations; it is not an archive of every prior form. A known Spec
collection result is retained as well. Failure to save the display or its
collection result prevents work acceptance; a consumed host response cannot be
blindly retried. The work record remains authoritative even if collection
succeeded but acceptance persistence failed.

See [B's verification receipt](durable-decisions-b-results.md) and
[design note](design-durable-decisions-b.md). This qualifies local CLI/Spec text
retention, not a change to Codex's form timer, automatic native UI integration,
selectable input defaults or the original disappearance incident.

## 1. A repair failed a behavioral check

**Proposed copy, based on the actual replay failure:**

> **Repair needs revision**
>
> The repair reports interrupted test runs as “no tests.” Two checks for this
> known error failed. Harness saved the proposed repair and failing results.
>
> Correct how the repair identifies interrupted runs, then run the checks again.

**Possible actions:** View failing cases · Repair within approved scope

The repair action requires existing write and dispatch authority; the label does
not grant more budget. This is an actual failed requirement, not wording advice.
The [replay evaluation](receipts/plan-build-function-body-replay-2026-09-18/replays/lb02/evaluation.json)
records both failures and `needs_revision`.

## 2. The source changed after preparation

**Proposed copy:**

> **Paused before applying the repair**
>
> The file changed after this proposal was prepared. Harness has not applied the
> replacement. Refresh the proposal against the current file before continuing.

**Possible actions:** Show source changes · Refresh proposal

Refreshing evidence is distinct from approving changed work or buying another
model response. The body replay verifies the actual source hash before inserting
the body; all twenty stale-source controls were rejected. A different case—a
worker copying the wrong hash—needs “The proposal does not match the accepted
file version,” without claiming the user edited the file.

## 3. The proposal tries to change unrelated code

**Proposed copy for a rejected body proposal:**

> **Replacement rejected**
>
> This repair would change code outside the agreed repair area. Harness rejected
> it before applying changes. Limit the replacement to the selected function's
> instructions, then submit it again.

**Possible actions:** Show rejected changes · Prepare scoped repair

For the successful `lb07` projection, use a completion message instead:

> **Repair passed its checks**
>
> The function repair passed its eight checks. The surrounding code is unchanged,
> including the code that formats the output.

The [body replay](plan-build-function-body-replay-results.md) supports these two
different outcomes. Editing boundaries do not prove all runtime behavior safe.

## 4. A required protection cannot run

**Current source message:**

> Required build control has no qualified runner

**Proposed copy:**

> **Build paused: required check unavailable**
>
> The check for changes to existing behavior cannot run in this environment.
> This build has not started. Restore the check, then resume.

**Possible actions:** Show check requirements · Inspect environment

The named check is illustrative; display the actual required check. Use the
before-build wording only for that recorded stage. Current
[`control_runners`](../src/attune_harness/work_effects.py) rejects missing required
runners and records missing optional runners as advisory instead.

## 5. Optional advice after a successful check

**Proposed copy:**

> **Optional suggestion**
>
> The required checks passed. A clearer function name could help future readers.
> This suggestion does not block completion.

**Possible action:** View suggestion. No response is required.

This must not introduce a new approval gate or an automatic rename. Conversely,
a definite unsupported claim is not merely a style suggestion: require evidence,
qualification or removal while leaving the underlying unknown unresolved. The
[assessment correction](assessment-quality-correction.md) documents that tested
distinction; it does not claim universal model reliability.

## 6. No tests ran

**Current source message:**

> No test call completed; collected or skipped tests are not passing execution.

**Proposed copy:**

> **No tests ran**
>
> None of the selected tests ran. The check has not passed. Review which tests
> were selected and whether the test runner could find them before continuing.

**Possible actions:** Show test selection · Inspect discovery

Keep an interrupted run distinct: “Testing was interrupted. Completion is
unverified. Inspect the saved run before resuming.” Current
[`classify`](../src/attune_harness/test_execution.py) distinguishes interrupted,
blocked, failed, no-tests and passed outcomes. A broader test selection must be
visible and stay within the authorized execution scope.

## 7. Some skill context was omitted

**Observed native warning, shortened:** skill descriptions were removed and
additional skills were omitted from the model-visible list because its context
budget was exceeded. Replies still completed. See the
[retained transport audit](receipts/plan-build-luna-broader-native-2026-09-18/transport-audit.json).

**Proposed copy:**

> **Some skill information was omitted**
>
> The model's input limit left out skill descriptions and some entries in its
> list of available skills. View the saved warning for details.

**Possible action:** View context details

Do not infer that every skill is broken, or that all intended guidance loaded.
If a required capability cannot be verified, pause its dependent work under the
existing control policy. Otherwise retain a visible advisory. Show the warning
once per unchanged condition, keep it in the durable record, and surface it again
if its impact changes. This presentation policy is proposed, not implemented.

## 8. The next call exceeds the approved allowance

**Proposed copy for that condition:**

> **Paused before the next model call**
>
> The next call would exceed the approved planning allowance. It has not started.
> Review the recorded usage and the estimate before choosing whether to extend
> this trial.

**Possible actions:** View usage · Keep paused · Review a new allocation

Show the actual used amount, remaining calls and estimate from the ledger. A
planning allowance is not a provider-enforced billing cap. If usage is unknown,
say it is unknown and reconcile before retrying. The completed broader trial
stopped because of reference leakage, **not** because its allowance was exhausted.

## 9. Progress and a decision that stays understandable

**Proposed progress copy for a verified partial result:**

> **First finding available**
>
> The requested function change passes its focused check. Compatibility checks
> are still running; the work is not ready for acceptance yet.

**Proposed continuation copy after the necessary evidence is complete:**

> **Ready to continue**
>
> The accepted step passed its required checks. The next step remains within the
> approved scope and allowance. Continue from the saved work, or hold here.

Where a decision is required, offer **Continue / Hold**, with the same
meaning through a click, `continue`, or a natural-language answer. Keep this text
available if the form disappears. Where continuation is already authorized, show
status and proceed rather than asking again. Silence, a preselected choice and
an old response are not new approval. These presentation examples preserve the
[approved interaction design](design-navigation.md#interaction-preferences--approved-2026-09-18).

## 10. Prompt enhancement before work begins

**Illustrative example.** The conversation has already identified the classifier,
the failing exit-code case and permission to repair only its function body.

User request:

> Fix the interrupted-test status.

Proposed enhanced working prompt:

> Repair the accepted classifier function so an interrupted test run with exit
> code 2 reports “interrupted,” including when no tests completed. Preserve the
> other outcomes and all code outside the function body. Run the regression check
> and the existing required checks; report their results and any remaining failure.

The additional precision comes from established context and evidence. If the
target, desired outcome or edit permission is unknown, leave that missing detail
visible and ask only the question needed to settle it. Do not silently select a
broader target or create new acceptance conditions. A clear terse request does
not need a rewrite displayed every time; show material interpretation changes.

Prompt enhancement can help prevent misunderstood requirements from becoming
implementation debt. It does not prove the resulting code correct, authorize
execution, or replace source-bound controls and behavioral tests. This example
illustrates the intended interaction; the repair replay did not measure prompt
enhancement's effect on reliability, maintenance cost or time saved.

Enhancement should also apply the user's established writing style. For a process
step addressed to the person performing the check:

> Before: The configuration must be checked before the build is started.
>
> After: Check the configuration before starting the build.

The direct verb makes the action easier to follow. The requirement and sequence
stay the same. Do not invent an actor or change responsibility when it is unknown.

## What would demonstrate a better journey

Before calling this UX qualified, check that users can distinguish advisory,
blocked, failed, incomplete and completed states; reach the relevant evidence;
and recover without repeating verified work. Exercise terse, click and natural-
language answers against the same current decision, including a missing form.
Measure time to the first useful finding separately from total completion,
and record unnecessary stops, repeated calls and user corrections. This is a
documentation follow-up direction, not a new trial allocation.
