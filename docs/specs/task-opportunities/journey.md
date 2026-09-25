# Worked example: return to work, then review and choose

Status: proposed acceptance scenario, not an execution receipt or a claim that
the feature is available. This will become the short tutorial after verification.

1. **Return after an interruption.** A user asks to pick up a saved task. The
   overview restores the goal, the retained stopping point, supported progress,
   remaining uncertainty and one useful next step. The user can understand these
   without rereading the earlier conversation or decoding internal record fields.
2. **Recover the right context.** With a retained comparison point, identify
   relevant changes and their evidence; with none, state that the comparison is
   unavailable. Separately authored code or reports remain attributed external
   work. A draft does not gain fictitious execution or completion. If a decision
   or missing evidence blocks continuation, explain it; otherwise the user can
   continue through the existing authorized workflow without an invented question.

The first task ends with this useful return-to-work journey. The following steps
describe later capabilities, rather than requirements to browse opportunities
every time the user comes back.

3. **Retain an opportunity.** The assistant submits a candidate: connect displayed
   progress to the authoritative saved task. Its sources, user obstacle, expected
   benefit, uncertainty and suggested done condition remain inspectable. The
   connected view announces its arrival without moving the user's reading position.
4. **Compare candidates.** Illustrative assessments might place the real-task
   connection above a small cosmetic cleanup because it removes a user obstacle.
   The cleanup may be an easiest useful win only if it clears that policy's value
   floor. No benefit or effort rating in this example is measured evidence.
   The explanation also states that the top-ranked candidate need not be worth
   building now. Show a credible existing-feature or smaller-change alternative
   when one is supported, and explain testing, maintenance and interface cost.
5. **Correct or choose.** The user can challenge the effort estimate, defer a
   candidate, or choose Work on this. The system explains why its recommendation
   changed. A candidate with missing evidence remains visible for investigation.
   If evidence changes during this review, the selected item, keyboard focus and
   edits stay in place. Review changes compares the new recommendation before
   applying its order; superseded decision context is labeled explicitly.
   Include a branch where the user chooses an existing capability or defers a new
   feature to finish current work. Retain the idea and rationale; no new feature
   implementation is needed for that branch to be a successful outcome.
6. **Open a draft.** Selection produces an editable goal, bounded scope, done
   condition and source link. Repeating selection opens the same draft. Existing
   authoring rules select the appropriate prompt/XML/spec structure.
7. **Continue through existing verbs.** The assistant prepares the concrete plan
   and checks; the user makes the applicable bound decision. A plan accepted
   elsewhere appears automatically within the connected view's declared freshness
   bound. Only a real build/check receipt can
   establish execution completion. HTML selection cannot grant that authority.
8. **Resume with context.** A later session sees the retained opportunity and
   current task separately. Changed sources or assumptions require reassessment;
   the record keeps why the prior choice was made.
9. **Recover the connection.** On disconnect the view shows when it last updated.
   Reconnection retrieves current validated state, preserves edits and reading
   position, and explains changed or unavailable items. An old action cannot
   silently apply to a new revision or a different selection.

First observe whether a returning user can explain the goal, where work stopped,
supported progress, unresolved matters and the next useful action without reading
the whole conversation. Include changed inputs and absent comparison history.

For later review and selection, observe whether the user can explain what is done, identify the missing evidence,
understand the ranking, correct one assumption and select a next task without
mistaking a draft or an external report for completed execution. Observe automatic
updates during an active review and verify stable selection, focus and reading
position; check changed recommendations and reconnect behavior. Record findings
and disagreements; the tutorial is not proof of general ranking effectiveness.
Check that users understand an opportunity is optional, can explain a simpler
alternative and ongoing cost, and can defer without losing the idea. Do not use
the number of opportunities selected as evidence that the journey succeeded.

## Production integration: Saved Tasks and a human briefing

Design status: implementation in progress. Completion review: pending.

The returning user needs a stable entrance as well as an understandable task.
Keep `status TASK` JSON unchanged. Add repeatable `--include-task TASK` for an
explicit collection in HTML or Markdown (maximum 20 distinct directories).
The caller saves HTML to a stable filename; its Saved Tasks links and back links
navigate locally inside that one document. No directory scanning, host-history
access, registry, server or task mutation is introduced. Unreadable/unsupported
additional tasks appear as unavailable entries, not as empty or completed work.
Reject duplicate task identities rather than presenting two copies as distinct.
Bound each view as before and the collection to 2 MiB of serialized content.

The opening separates context, overall goal, desired end state, current focus,
where work stopped and the next useful step. Existing saved-owner guidance stays
visible and authoritative. Full evidence, comparisons and recorded progress stay
available below. An explicit continuation note may add a bounded `briefing`
object: title, context, goal, desired_end_state, current_focus and done_when.
These are attributed caller summaries, not new task authority. Display them only
when the declared revision is current; stale summaries fall back to saved intent.
The existing note size limit and strict validation still apply. Canonical goal,
criteria and task details remain inspectable.

This increment supersedes the earlier blanket exclusion of scripts/buttons only
for local reply preparation: fixed bundled JavaScript allows Continue, Correct
context or Ask a question, optional personal wording, an exact read-only reply
and Copy reply. Every reply identifies the task path and displayed revision and
asks the assistant to inspect current status before acting. No response is sent,
accepted, persisted or executed by the page. Copy failure selects the reply for
manual copy. Without JavaScript, the baseline reply remains readable/selectable.
Use “Your reply to the assistant”; host-specific branding is not a control label.
Only the bundled script and style hashes are allowed by CSP; task content is
literal text, never JavaScript, links, form actions or navigation targets.

Cases to verify: absent/current/historical summaries; blocked, stale, completed
and uncertain owner state; literal hostile input; default JSON compatibility;
collection ordering, duplicates, missing/non-feature tasks, count/byte limits;
keyboard/mobile navigation and response controls, unavailable clipboard, no JS;
no changes to task/note bytes and no participant dispatch. Installed wheel checks
must exercise the same interface. Retained prototype experiments established
layout/interaction behavior; a formative interrupted-work walkthrough exposed
navigation difficulty and supported the new hierarchy. Independent discovery
from a closed host remains unverified.

Rejected alternatives: automatic filesystem/history discovery creates hidden
scope; new task storage duplicates existing owners; a live write endpoint would
prematurely introduce Task 6. The read-only single-file entrance can be reused by
Task 2, with connected response delivery left to the later controlled-action work.
