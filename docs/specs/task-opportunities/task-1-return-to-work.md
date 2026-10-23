# Task 1: return to work

Status, corrected October 22, 2026: the static briefing and continuation
implementation is integrated. One assisted text walkthrough is recorded in the
current checkpoint; complete interrupted-task acceptance remains pending.
The [current checkpoint](README.md) records source, evidence, remaining work and
the command-owner walk. This task supersedes the earlier record-first and
review-first framing. Passing software checks does not establish user acceptance.

## User outcome

After an interruption, a person can pick up the right task with enough context
to continue confidently, without rereading the entire conversation. The first
screen helps them finish their current work. Reviewing a delivered result and
discovering additional opportunities remain later use cases.

## What the first view answers

1. **What am I trying to accomplish?** The current goal and intended result.
2. **Where did we stop?** The last retained stopping point, established progress
   and remaining work, with the evidence source and its freshness available.
3. **What changed?** A comparison with an explicitly retained prior checkpoint
   when available. With no comparison point, say so; do not invent an activity
   timeline or equate file modification times with completed work.
4. **What needs attention?** A real blocker, missing evidence or unresolved
   decision. Show no artificial question when the next step is already clear.
5. **What is the next useful step?** One recommendation tied to the goal and
   current authority, with its reason. The user can continue, correct the context
   or stop through the existing assistant/command workflow.

IDs, checkpoints, file inventories and full evidence remain available as detail.
The overview must distinguish known facts, attributed claims and missing context
without requiring the user to understand the storage model.

## Evidence and continuation boundary

Use the validated saved task plus explicitly supplied or retained continuation
context and linked artifacts. First inspect existing task/workspace history and
handoff mechanisms for suitable reuse. Before implementing an additional record,
define the minimum missing information, its owner, source references, size bounds
and revision binding. There is no new storage or context-mining API implied by
this plan.

Work performed in an assistant session may be real even when the Harness journal
has no execution. Show externally supported work with its provenance intact;
never turn a summary, source file or passing external test into a Harness build
receipt. Stale or contradictory sources require an explanation and next step.
When evidence is missing, acknowledge the gap instead of asking the user to infer
that nothing happened.

The first version uses explicit continuation context. Hidden conversation access,
automatic background mining, inferred approvals and automatic execution remain
outside scope. Resume/build/plan continue to enforce their existing authority.
Showing a next step does not execute it.

## Walkthrough and acceptance

Use one real task interrupted between meaningful steps. Retain an explicit
stopping point and evidence, then reopen it as a returning user would. Include
both fresh and changed inputs, an unresolved decision, externally supported work,
and a case with no prior comparison point. Avoid invented progress in examples.

Done when:

- From the overview, the user can explain the goal, where work stopped, what is
  supported, what remains unresolved and which action would move the work forward.
- The user reaches that action without rereading the conversation or interpreting
  raw record fields. A correction to the displayed understanding remains possible.
- Comparisons name their baseline; absent history and stale evidence are visible.
  Settled decisions are retained, and external work does not impersonate a run.
- The actual next command or assistant handoff uses the current task and existing
  authorization; a blocked or uncertain task cannot silently resume.
- Installed behavior, state fixtures, read-only inspection, hostile text and
  existing JSON compatibility pass the relevant checks. The real walkthrough
  establishes user usefulness separately from software correctness.

## Remaining completion work

The October 22 [observation](README.md#acceptance-and-evidence) covers one assisted
return, context correction and stale-draft refresh. The printed-command checks
cover the five context states below. Retain these results; collect the missing
original-pause and independent-return evidence before closing this task.

1. Use the [pause-and-return procedure](../../cli-guide.md#pause-and-return-to-work)
   with one real saved feature-work task and an explicit caller-owned note.
2. Verify the printed procedure against current, absent, historical, stale and
   unresolved context in disposable owner fixtures. Preserve task/note bytes and
   current guidance; keep software results separate from the human observation.
3. Observe returning to the real task, recovering context and preparing the next
   valid assistant handoff without rereading the conversation. Record the chosen
   artifact/runtime, browser/platform, actual result and help needed. An assisted
   walkthrough does not establish independent discovery from a closed host.
4. Update the acceptance record from that observation. Runtime changes remain
   outside this completion slice; scope a demonstrated source defect separately.

The connected companion remains the destination. This task establishes the value
and evidence model of returning to work before live updates or new opportunities
make that experience more complex.

## Implementation decision

Reuse inspection found that feature-work history already retains every prior
request revision. Spec workspace resume owns a different XML/state lifecycle;
`review_handoff` owns planning critique. Neither owns an assistant's stopping
point. Reuse the request history for scope comparison, and accept one explicit,
caller-owned continuation JSON file through `status --continuation FILE` with
`--format markdown|html`. No new store, journal mutation or model call is needed.

The note supplies schema version 1, task ID, declared request revision, timestamp
with timezone, source, stopping point, at most six reported progress items (each
with literal evidence references), and an optional suggested next step/reason.
Read at most 32 KiB using the existing bounded regular-file reader and strict JSON
parser. Reject unknown fields, wrong identity, absent/future revisions and malformed
values. Bind the revision to the validated current request or its retained history.
This checks association, not the truth or authorship of the note's claims.

Only the explicit note is read. References are displayed as text, never fetched,
executed or treated as passing checks. All note content is visibly attributed.
An old revision is labeled historical and its suggestion is withheld. Current
scope does not establish current external evidence: even same-revision notes
remain reported claims, and their references are not revalidated by the view.

Compare named request fields against the declared baseline: goal/context/scope,
constraints/acceptance/questions, choices, tasks, captured input evidence, controls,
assignments, budgets, effects and artifact. Show before/after goals and changes to
decision selections; otherwise name the changed area and retain full current detail.
This is a saved-scope comparison, not an activity timeline or a run-progress diff.
Without a note, disclose that no stopping point or baseline was supplied.

The overview presents goal, intended result, next authorized action, stopping point,
reported progress, saved-scope changes, open decisions and remaining planned work.
The existing owner's guidance always wins; the supplied suggestion stays advisory
below it and cannot override a blocked/uncertain/stale or completed state. Detailed
record fields go in native HTML disclosure sections; Markdown stays readable.
The original implementation excluded scripts and buttons. The later
[Saved Tasks and human briefing increment](journey.md#production-integration-saved-tasks-and-a-human-briefing)
supersedes that boundary only for fixed local reply preparation and navigation.
It sends no response, accepts no checkpoint and dispatches no work.

Original implementation scope: `task_continuation.py`, `task_view.py` and
`task_cli.py`, with the existing single-read changes in `work_cli.py` and
`work_runtime.py`. Tests precede these changes: a saved/reopened real-owner task,
revision comparison and resolved decisions, absent context, stale input and old
notes, wrong identity, malformed/oversized notes, hostile text, no writes/dispatch,
and unchanged default JSON. Preserve prior receipts and qualify the new wheel.
