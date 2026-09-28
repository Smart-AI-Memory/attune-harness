# Design and acceptance criteria

**Status: draft for approval; proposed interfaces are not shipped APIs.**
See the [evaluation](evaluation.md) for the verified baseline and the
[tasks](tasks.md) for implementation order. Initial scope is same-machine
`feature-work-v1` with explicit task and project paths.

## Ownership

| Owner | Responsibility | Must not do |
|---|---|---|
| Forms | Form schema, typed answers, host-profile admissibility, render/decode and portable fallback | Infer task approval from a valid answer or change Harness state |
| Harness | Effective task intent, revision/history, acceptance, permissions, effects, checks, recovery, evidence summary | Trust model prose as completed work or treat a rendered view as a grant |
| Host integration | Declare capabilities; display the selected surface; correlate actual replies; open results; invoke existing owners | Invent responses, infer approval from defaults, or replay uncertain work |
| Assistant/model | Infer supplied facts, propose scope/corrections, explain limitations and next steps | Rewrite retained evidence or replace owner validation with its judgment |

Use existing `work_contract`, `work_cli`, `work_runtime`, `command_workspace`,
`task_view` and `execution_evidence` boundaries. Do not enable workspace MCP
lifecycle execution merely to make this journey convenient.

## R1 — Only material unresolved questions

Normalize the initial request into existing intent/questions/choices. Keep the
user's constraints verbatim where meaning could otherwise drift. Call the owner's
missing-information logic before eliciting a response. A single simple ambiguity
gets a single question; multiple independent ambiguities may be batched within
the selected host's limits. Dependent questions remain sequential.

Acceptance: fixture CSV intake emits exactly one semantic question. A fully
specified variant emits none. Optional uncertainty is disclosed without blocking
an otherwise complete request. Repeat intake after a host switch does not ask
answered questions unless they are stale or the user explicitly reopens them.

## R2 — Explicit presentation selection

Add an additive Forms API, proposed `select_interaction(form, capabilities)`,
without changing `select_form_surface` behavior. `capabilities` contains an
explicit installed `host_profile_id` or null, `rich_available`,
`portable_available`, and `keyboard_preferred`. Unknown profiles must not silently
become Claude. A named profile includes measured limits and its reply codec;
host/version evidence accompanies its installation, not a claim from model prose.

Return a pure, serializable decision: `schema_version: 1`,
`surface: native|rich|portable|unsupported`, `profile_id`, `reason_code`, and
`limitations` (a list). No task grants or external effects are part of this value.
Reasons are closed codes with separate display text; unsupported has no payload.

Selection order: a declared admissible native profile; otherwise rich if available
and not opted out; otherwise the existing validated portable/Markdown path; else
unsupported with an actionable explanation. Keyboard preference cannot force an
inadmissible native control. No truncation, option renaming or silent field loss.
The portable path must round-trip the field/construct; its existence is not proof
that every host can collect every construct. Refuse unrepresentable combinations.

MCP selection may use an explicit server configuration supplied by the host; do
not infer host identity from the selected language model. Its exact public config
extension belongs to the Forms change and must preserve old callers. Direct
Harness integration passes capabilities explicitly; it does not depend on a new
workspace MCP execution path. Reuse existing profile and renderer registries.

Acceptance: native, rich, portable and unsupported routes have deterministic tests;
question/option limits, delimiter ambiguity, numeric input, ranking and unknown
profiles get explicit outcomes. Every admitted route returns equivalent typed
answers. Existing router callers retain their behavior and warnings.

## R3 — Persist correction before continuation

The host constructs an explicit change proposal from the user's correction,
reads the current record, and passes the observed checkpoint to `revise_work`.
No presentation-owned copy becomes authoritative. It then reads back the result
and shows the effective scope and whether acceptance remains or is needed.
Coherent intent, choices, tasks and criteria must all reflect the correction;
changing only the displayed sentence is insufficient.

| Input/state | Owner operation and resulting guidance |
|---|---|
| Same effective scope, unchanged dependencies | Inspect; avoid a gratuitous revise call. Preserve valid acceptance. |
| Changed draft or accepted work, no build | Existing revise; retain history, clear obsolete acceptance, show exact new scope |
| Stopped settled build, eligible pending suffix | Existing `preserve_completed` steering; preserve completed prefix and evidence; accept corrected suffix through its owner |
| Running/uncertain effect | Reconcile or stop through existing controls first; no correction-driven retry |
| Completed intent or broader post-effect change | Explain unsupported in-place change; explicitly create successor scope only after the user chooses it; retain original journal |

No automatic acceptance carry-forward for a smaller scope: reducing scope can
still change acceptance criteria. A trusted response may accept the already
displayed revised scope once; plain correction text by itself does not bind it.
No new top-level task states or persisted correction schema are required.

Acceptance: old decision replay fails; restart sees current-page scope everywhere;
stale concurrent correction makes no write; rejection/cancellation grants nothing;
the old revision and its evidence remain inspectable. No supported correction
requires re-entering unchanged fields. Failure saving a correction prevents
execution and reports that the correction was not saved.

## R4 — Handoff preserves meaning, not stale authority

A portable handoff is a non-authoritative locator containing the task directory,
project path and last-observed task ID/revision/checkpoint. Render it through the
existing continuation/briefing conventions; do not introduce another task store.
The destination reads status afresh and compares identity. A newer valid revision
supersedes the locator's snapshot; an identity/path mismatch stops continuation.

Reopening itself is read-only. Continue invokes the existing task owner with its
required current checkpoint and execution permissions. A host switch does not
change the participant registry. If the person also changes providers, model
assignments, configuration or paid-call permissions, process that through the
existing revision/authorization boundary; host portability does not grant spend.

Acceptance: fresh accepted work opens in another adapter without new acceptance;
draft work stays draft; stale work cannot execute; an unavailable dependency gets
a clear diagnostic without rewriting the task. Completed work replays evidence
without repeating effects. No automatic cross-machine path relocation is claimed.

## R5 — Host owns reply lifecycle

Keep form-instance correlation, accumulated validated answers and bounded retry
state in the consuming session, tied to the current task checkpoint when relevant.
Use existing workspace bindings where available; plain Forms answers alone are
not task decisions. Explicit cancellation terminates the display without accepting
or executing anything. Reopening after a process restart reads task state and
issues a fresh display/binding; it need not persist an unfinished UI session.

Use the chosen profile's configured attempt cap/deadline, counted by the host.
An expired or exhausted display explains how to reopen it; it cannot restart its
budget merely because an assistant sends attempt=1. Do not reinterpret a malformed
reply as cancellation. This requirement belongs to the host session, not a change
that pretends the stateless Forms decoder can enforce wall-clock deadlines.

Acceptance: stale display, duplicate reply, deadline expiry, retry exhaustion,
partial invalid answer and cancellation are tested. Valid prior answers survive
supported retries. A restarted session cannot submit an old nonce to mutate work.

## R6 — One action opens understandable evidence

Add an outcome-level **Inspect results** entry to the existing task presentation.
It opens a bounded read-only summary from one validated record snapshot. In HTML,
use an accessible disclosure/anchor with keyboard activation; in a capable host,
open the generated report through that host's artifact/resource mechanism. Avoid
inventing a universal URI scheme. Unsupported artifact opening gets an explicit
inline portable summary; do not count that host as one-click qualified yet.

The summary contains:

- Task identity, revision, capture time, current freshness and effective scope.
- Each acceptance criterion, its recorded supporting check(s), verdict and limits.
- Superseded/preserved evidence clearly labeled with its source revision.
- Named unresolved, failed, skipped or missing checks and a useful next action.
- Supporting record pointers and changes when actually retained; missing diffs
  are reported as unavailable, not reconstructed from the current working tree.

Use `execution_evidence` pointer validation. A criterion with no deterministic
existing association is unverified. Initial implementation may match explicit
existing task/control identifiers, but may not claim full criterion coverage from
an overall passing build. Defer a persisted criterion/check mapping to a separate
compatibility-reviewed extension if real tasks require it. Model-authored mapping
alone is attribution, not proof.

No arbitrary paths/URLs from model text become active links. Generated summary
targets are host-owned; escape all repository text and retain the view's bounded
size/CSP approach. Opening results never dispatches, accepts or changes state.

Acceptance: from the completed-task outcome, one activation shows the summary,
not merely a pathname or raw JSON. Missing, stale, failed and unverified evidence
cannot appear passed. Malicious labels/paths remain inert. A task change while a
summary is open does not silently relabel the older snapshot as current.

## R7 — Qualify the actual journey

First run deterministic contract tests with scripted host adapters and no model
calls. Then observe the same journey in version-recorded Codex, Claude and
Antigravity installations. A script stub qualifies only the seam, not the host.
Record input, displayed decisions, actual response, correction revision, handoff,
evidence-opening steps, outcome and limitations. Keep private content out of
public artifacts. Paid dispatch needs separate approval and a concrete budget.

Acceptance: each claimed host completes intake/correction/read-only handoff and
evidence inspection; applicable execution paths retain their existing platform
qualification. Unsupported capability cells stay explicitly unqualified. Record
human misunderstandings, redundant questions and effort; do not turn one
walkthrough into a comparative speed or safety claim.

## Compatibility and rollout

Ship Forms additions first and qualify their wheel independently. Harness adopts
the released exact version only in its integration task; update dependency locks
through its normal process. Do not upgrade retained environments. No existing
saved record needs migration in this slice. Old records keep their original
meaning and may show unverified criterion mapping.

Public export/config additions require Forms stability/registry records and
changelog evidence. Any Harness CLI/envelope change is separately identified in
the implementation PR and checked against compatibility fixtures; this design
does not authorize relaxing them. A frozen-surface change may require another RC
and observation period under the release runbook; this plan does not choose that
release timing. Rollback pins the prior packages and disables the new adapter
entry; never rewrite history or evidence to restore compatibility.
