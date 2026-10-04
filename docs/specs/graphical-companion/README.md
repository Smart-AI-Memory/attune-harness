# Production graphical companion

Status: milestone 1 working specification; implementation authorized by Patrick.
Baseline: origin/main `bd517064507bac1264b0dbf01287837b25b4df0c`.
The existing prototype journeys are retained inputs, not discarded work.
This specification defines production qualification; it does not claim it.

## Outcome and scope

A local web companion lets people start, inspect, decide, execute and resume
Harness work through task-selected forms. Codex, Claude and Antigravity enter
one shared interface. Author review can inspect each journey and its UI states.
Harness remains the authority for state, acceptance, effects and reconciliation.
The GUI must explain the difference between a proposal, a user's decision,
a successful operation, and verified completion.

The program has four milestones:

1. Inventory existing journeys, map owners and refusals, define architecture and
   acceptance criteria. Deliver a navigable coverage record and bounded backlog.
2. Qualify the existing plan/build/review/continuity journey with real owners,
   retained state and interruption recovery. Reuse the present interactions.
3. Cover fix, test, memory, opportunities, research, import and host entry points.
4. Qualify installation, upgrade, accessibility, security, platform behavior and
   real user walkthroughs; prepare a release candidate.

Scope includes browser UI, a loopback companion service, narrowly scoped owner
adapters, tests, packaging and documentation. It does not include hosted accounts,
remote collaboration, arbitrary remote execution, replacing model vendors,
changing release/settings policy, or automatic model escalation. Unsupported
platform capabilities remain explicit refusals until independently qualified.

## Reuse inventory

| Existing journey/artifact | Preserve | Production work still needed |
| --- | --- | --- |
| `prototypes/navigation/` | Workspace navigation and task-oriented entry | Bind projects/tasks to actual registered owners |
| `prototypes/spec-workflow/` | Goal/scope, optional research, questions, alternatives, review | Arbitrary real tasks, owner questions, source freshness and current-checkpoint acceptance |
| `prototypes/refined-workspace/` | Opportunity collection, per-opportunity drafts, narrow/uncertain fix, author inspection | Owner-backed persistence and actions; remove fixture assumptions from operational mode |
| `prototypes/session-continuity/` | Two-session recovery and explanation of retained context | Canonical saved entries and task-linked continuation |
| `prototypes/live-mining/` | Exact input preview, source-linked suggestions, editable drafts, receipts and tutorial | Current decisions/completion in packets, provider selection, semantic evaluation, durable review |
| `task_view`, `spec_presenter`, `command_workspace` | Existing projections, decisions, identity and replay rules | Web transport and accessible component mapping |
| `memory_saved`, `task_continuation` | Explicit saved intent, revisions, task identity and continuation | Visual capture/search/edit controls and provenance presentation |

Prototype evidence is local and contains private session material; it is not
copied into a public pull request. Prior results are not rewritten. Prototype
checks prove their stated interactions, not installed production workflows.

## Journey coverage matrix

Each row requires happy, empty, invalid, stale, unavailable and interrupted states
where applicable. “Existing” below means source inspected, not fresh host qualification.

| ID | Journey | Existing owner | GUI deliverable | Milestone |
| --- | --- | --- | --- | --- |
| J01 | Choose project and resume task | `task_view.inspect`, `work_cli.present` | Registered task list, status, next action, source and capture time | 2 |
| J02 | Goal and context intake | `init_cli`, `work_contract.draft_request`, `spec_intake` | Editable goal/scope/done; precise missing-input questions | 2 |
| J03 | Research | Retrieval and consultation owners; static research prototype | Explicit source selection, quote/citation, date, uncertainty and incorporation; web provider contract is still a gap | 3 |
| J04 | Compare, review and accept spec | `work_accept`, `command_workspace`, `work_decisions` | Alternatives, findings, baseline diff and exact-revision acceptance | 2 |
| J05 | Build and verify | `work_build`, `work_effects`, `work_review_handoff` | Protected checks, operation progress, evidence, explicit dispatch grant | 2 |
| J06 | Evidence review | `task_policies`, `review_participants`, `assessment_effects` | Document/corpus intake, findings, uncertainty and disagreement | 2/3 |
| J07 | Scoped fix | `repair`, `task_handoff`, `task_policies` | Failure/probe, dedicated checkout, exact file scope, fail-before/pass-after evidence | 3 |
| J08 | Test change | `test_change`, `test_scope`, `test_execution` | Captured change preview, accepted test scope and result | 3 |
| J09 | Mine and choose opportunities | Live prototype; saved task intent; no general production miner | Evidence-bound candidates, novelty/resolution status, dismiss/select/edit | 3 |
| J10 | Save/revise/forget knowledge | `memory_saved`, `memory_saved_cli` | Scope, source, revision, conflict and explicit retention controls | 3 |
| J11 | Recall and context assembly | `memory_reader`, `memory_serving`, `memory_context` | Distinguish saved capture from Redis automatic recall; selection/exclusion | 3 |
| J12 | Handoff and recover | `task_continuation`, `task_view`, recovery policies | Reviewed packet, source, changed context, stale acceptance and unresolved effects | 2/3 |
| J13 | Import legacy work | `work_accept.import_plan`, `spec_legacy` | Import preview, unsupported fields and new acceptance | 3 |
| J14 | Cancel/reconcile/transfer | `task_cli`, `task_policies`, `work_runtime` | Evidence-specific recovery choices; cancellation is not rollback | 2/3 |
| J15 | Inspect author journeys | Refined prototype + tutorial | Component/state gallery using the same components as operational views | 2–4 |
| J16 | Host entry and consultation | Existing Codex/Claude plugin packaging, `consultation`, `antigravity` | Task deep links, connection diagnostics and per-capability qualification | 3 |

J03 and J09 need new production capability, not just a renderer. Antigravity has
a consultation adapter; that is not evidence of native plan/build parity. Do not
hide these gaps behind generic “AI connected” badges.

## Architecture

- Package the companion with Harness under an explicit GUI launch command. The
  exact command registration is an implementation task, not an existing command.
- Serve bundled static assets over a loopback-only listener. The browser sends
  typed actions to an allowlisted owner adapter; it cannot submit a shell command.
- Start with existing HTML projections where useful. Extract the prototypes'
  visual language and forms into reusable browser modules. No frontend runtime
  framework is required to validate the first owner-connected increment. Revisit
  framework adoption only against concrete component complexity and packaging cost.
- Register explicit project/task directories at launch. Address them through
  opaque local IDs; do not accept arbitrary browser filesystem paths. Validate
  project/task association using owners, not directory naming.
- Keep records in their existing owner stores outside effect checkouts. A GUI
  index stores locations/preferences only and is rebuildable. Never duplicate
  authority or claim browser localStorage is canonical memory.
- Use bounded snapshots/polling initially. Expose capture time and refresh failures.
  Later event streaming may improve latency; it must not change operation identity.
- Persist before dispatch through existing owners. A transport timeout means
  “inspect outcome,” never “retry automatically.” Reconnection reads owner state.
- Send current checkpoint plus action identity on writes. Re-read and let the
  owner refuse stale, replayed or incompatible requests. Serialize per task and
  retain owner leases; a UI lock is insufficient across processes.
- Task state deterministically selects forms. AI output fills bounded proposal
  fields, with evidence and uncertainty. It never selects its own authority.
- Author fixtures are separately labeled, stored and routed; switching to an
  operational task cannot import fixture approvals or execution flags.

## Local service boundary

The implementation must test loopback binding, exact Host/Origin checks, an
unguessable local session capability, no permissive CORS, no caching of private
responses, content security policy, bounded requests/responses and escaped text.
A capability is not put in a query string or retained in logs. Static assets
must not expose arbitrary project files. Symlink/path traversal, foreign task
association, duplicate requests, cross-tab races and disk failure need negative
checks. Logs and diagnostics redact credentials and private source text by default.
Native/provider credentials remain in their established host configuration.
Read-only inspection never calls a model or accepts a task.

## Command-owner walk before execution implementation

This table binds the first connected journey to actual owners at the baseline.
The complete owner validators remain authoritative; UI preflight is explanatory.
Where satisfaction is not yet exercised through the GUI, it is marked as a gate,
not assumed from a prior mockup. No GUI execution route ships while that gate is open.

| Step | Refusal source | How the preceding step supplies it / required proof |
| --- | --- | --- |
| Prepare starter request | `init_cli.py:308` (`execute_plan`), raises at 310/316/320/347: missing inputs, existing task/request, oversized request | Intake requires nonempty goal, scope, interpreter and tests; choose fresh state outside project; request preview before writing. Existing `test_init_cli.py` covers CLI; GUI binding pending |
| Create draft with `plan --request` | `work_contract.py:405` (`draft_request`), validators and `_capture` at 336; raises at 339/343/348/361 | Starter construction calls this validator; register canonical project and separate task root, regular bounded inputs, explicit registry. UI must display missing material intent rather than accept it |
| Preview decision | `work_cli.py:499`, raises at 505/507/513 | Re-read draft, use current checkpoint, render owner-supplied questions or approval. Browser must not reconstruct hidden defaults |
| Accept exact revision | `work_cli.py:465`, raises at 470/484/495; `WorkAcceptance._fresh` at `work_accept.py:472` | Submit displayed checkpoint, owner lifecycle requirements and complete intent; changing goal/evidence invalidates displayed approval. Stale/replay GUI tests required |
| Build | `work_runtime.py:312/315/318`; `work_build.py:95–128`, 745/754/793/809 | Accepted effects, fresh config, distinct worker/reviewer, protected task/final probes, adequate budgets, configured allowed participant policies and separate dispatch grants. Preparation must surface missing effects rather than offer an executable button |
| Review outcome | `task_handoff.py:59` and completed-assessment validation; review intake owner | Pass real artifact and bounded corpus/context; explicit review scope. A completed narrative remains unverified. Repair handoff requires completed structured findings, not copied text |
| Save handoff and inspect | `task_continuation.py:19`, raises at 30/33/40/66; `task_view.py:28/32/74` | Existing task ID and retained revision, timezone timestamp and attributed reports; preserve 512 KiB view bound. Never infer execution from a note |
| Resume or reconcile | `work_build.py:793/809`; `task_cli.py:239/245/247` | Inspect first; keep original permissions; unresolved effects route to supported evidence-specific reconciliation, never blanket retry |

The R2 installed-owner test provides an executable valid plan/build/review/status
chain with deterministic peers. It does not prove native model quality or the GUI.
The first GUI integration must run equivalent calls against an isolated fixture,
then show stale and interrupted variants. A full refusal inventory for J03 and
J07–J14 is required before their respective write routes are implemented.

## Milestones and acceptance

### M1 — reuse and specification

Deliver this matrix, source-bound command walk, baseline test receipt, architecture,
backlog and explicit open gaps. Preserve prototypes and source identifiers.
Completion review: see progress.md; the inventory is source-grounded, and GUI integration remains unqualified.

### M2 — production integration of existing journey

1. Registered task inspector using real `task_view` projections; browser reload
   and restart reproduce task identity, revision, evidence and current status.
2. Intake and owner-selected decision forms, with current-checkpoint submissions.
3. Accepted effects and build/review controls, separate model/command permission.
4. Operation progress, interruption, uncertain-outcome handling and handoff.
5. Author gallery of all these states, sharing components with operational views.

Exit: browser runs the real offline owner chain and refusal variants; no fabricated
completion; second tab's stale action rejected; restart during an operation cannot
repeat effects; server/browser/disk failures retain inspectable state. Native
connection trials require separately bounded approval. Milestone demo includes
one existing user journey end to end and the author view of its refusal states.

### M3 — complete the agreed coverage matrix

Add J03 and J07–J14 with owner-by-owner writes and negative cases, not a universal
command endpoint. Connect Codex, Claude and Antigravity separately. Keep task
history, explicit saved entries, curated recall and new proposals distinguishable.
Research includes source/date, selected implications and dependency invalidation;
network failure leaves useful local work intact. Opportunity mining includes
settled/completed status and can return no useful opportunities. No blanket Luna
or Sol routing follows from a single demo.

Exit: every row has executable evidence or an explicit unsupported capability
with a useful next action. An unsupported required capability is an open release
gate, not a way to declare complete coverage. Existing prototype interactions
are checked against their replacements; retained user drafts are not discarded.

### M4 — release qualification

Run targeted and full suites, build/install wheel and platform qualification,
package asset checks, clean launch, upgrade/migration and recovery tests. Check
keyboard-only usage, focus restoration, labels/errors, contrast, zoom and screen
reader behavior. Test local service security boundaries and resource limits.
Obtain independent review for source changes and named user walkthroughs. Verify
host entry in each claimed host. Record measured startup/action latency and
resource use before setting performance targets. Keep fixtures separate from
model-quality and platform qualification.

Exit: all required matrix rows pass on supported profiles; failures and limits
are published accurately; draft release handoff is complete. Merge, publication,
paid runs and settings changes retain their existing approval gates.

## Planning estimate and autonomous work

These are engineering sizing bands, not elapsed-time promises or approved token
or model spend. Re-estimate from actual M2 integration evidence.

| Milestone | Sized increments | Principal uncertainty |
| --- | --- | --- |
| M1 | 1–2 | Hidden owner contracts and current evidence |
| M2 | 5–8 | Effects preparation, form projection and crash recovery |
| M3 | 8–14 | Web research/miner gaps, memory paths and host differences |
| M4 | 4–7 | Cross-platform defects and real walkthrough findings |

An increment is a reviewable implementation plus its focused evidence, not a
fixed number of hours. Do not price existing backend/prototype implementation
again. Each increment updates coverage and completion review. Proceed autonomously
with reversible in-scope design, code, tests and draft PRs. Escalate only concrete
product conflicts, additional spend, scope changes or repository approval gates.

## Open decisions and evidence

- Experiment 23 identity and primary evidence review remain pending. It may
  inform model selection; it does not block owner-backed GUI foundations.
- Internet research provider and unattended mining budget are not selected.
  Implement source review and provider boundaries first, without paid dispatch.
- No GUI production capability is qualified by the prior localStorage tutorial.
- A named user's final walkthrough and actual host observations cannot be
  replaced by scripted browser tests.

## Preservation and replacement gate

Existing prototype directories and frozen receipts are read-only inputs to this
program. New production assets use separate paths. A private archive with a
per-file checksum manifest preserves the current local artifacts; its location
is recorded in private session notes, not in distributed package metadata.
Browser-only user choices require explicit export/migration support before any
prototype storage key is retired. No automatic reset or deletion is permitted.

For each journey replacement, name the prototype behaviors being preserved,
run the equivalent interaction against real owners, and retain both results.
Intentional behavior changes need an explicit rationale; visual restyling cannot
silently remove research, opportunities, memory controls or author inspection.
No prototype retirement is part of milestones 1–3. Production readiness includes
a recovery/export path and an explicit comparison with the previous interface.
