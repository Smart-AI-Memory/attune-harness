# Portable user journey: implementation proposal

**Status: draft for approval; not authorized for implementation.** Planning and
evaluation are authorized. This package does not add a release gate or change the
stable-v1 roadmap. Approving it must identify the implementation tasks selected.

## Outcome

A person can give an agent a task, correct it, continue in another supported host,
and inspect why it is called complete without repeating settled decisions or
learning the implementation. Codex, Claude and Antigravity are target hosts, not
qualified integrations merely because their names appear here. Model choice and
host capabilities are separate dimensions.

The motivating journey is: "Add CSV export to reports. Keep the active filters
and exclude private notes." Only the unresolved choice between the current page
and all matching records needs asking. The person chooses all records, corrects
that to current page, then continues in another host and inspects the result.
The CSV feature is a test scenario, not a request to implement it in this repo.

Read in order:

1. [Journey evaluation](evaluation.md): existing behavior, evidence and gaps.
2. [Design and acceptance criteria](design.md): proposed contracts and boundaries.
3. [Implementation tasks](tasks.md): sequence, owners, checks and approval gates.
4. [Performance evaluation protocol](performance-evaluation.md): real human and
   AI outcomes, a controlled Harness workflow, and secondary token costs.

## Agreed user requirements

- Infer already supplied facts; ask only unresolved material questions.
- Save a correction in authoritative task state before execution continues.
- Preserve unchanged acceptance across a host switch when freshness, identity
  and execution permissions still hold. Do not confuse host switch with changing
  an accepted participant registry, provider, machine or checkout.
- Show the outcome immediately and make its supporting evidence inspectable
  through one action. Do not make raw logs the first thing a user must read.
- Do not restart intake for a single correction. Material changes still need
  authority for the changed scope; a host change alone does not justify a gate.
- After execution starts, explain the impact before modifying remaining work.
- Prioritize human and AI performance over token reduction. Higher token use is
  acceptable when it produces a meaningful measured benefit without violating
  safety, authorization or the declared performance guardrails.

## Evaluation update: October 27, 2026

Patrick requested performance-first evaluation, with token use as a secondary
cost. The [new protocol](performance-evaluation.md) operationalizes that priority;
it does not authorize recruitment, model dispatch, spending or implementation.
It adds a controlled same-host comparison before separate portability trials.
The September review below remains historical evidence, not a fresh execution
report. This update inspected Harness source
`8b459b97a2b5dabe8c8f269fffbf47255b277d2c` and retains the Forms evidence at
`4191c4e0c6bfe7ff21e4dd926f0ba8202775a9a7` (0.17.0).

### Proposed workflow: owner refusals and input flow

These are preparation requirements, not a claim that a runnable study fixture
already exists. The fixture must demonstrate this chain before collection.

| Step | Refusal source | Required input from the preceding step |
| --- | --- | --- |
| Prepare with `plan --request` | [`work_contract._capture`](../../../src/attune_harness/work_contract.py#L339) rejects invalid project/storage separation; request validators reject invalid assignments and scope | A dedicated bounded checkout, explicit registry, protected checks, and request/task files outside the effects checkout; no invented answers |
| Open the forms condition | [`CompanionServer`](../../../src/attune_harness/gui.py#L99) refuses build mode and invalid task paths | The canonical existing task directory returned by preparation; editable intake only, never browser execution |
| Persist the correction | [`revise_work`](../../../src/attune_harness/work_contract.py#L775) rejects stale checkpoints and unsupported corrections | Current owner checkpoint and corrected intent plus affected criteria/tasks; preserve prior revision and inspect the new draft |
| Accept with `plan --accept` | [`work_cli._accept`](../../../src/attune_harness/work_cli.py#L471) rejects a different checkpoint; [`work_contract`](../../../src/attune_harness/work_contract.py#L587) rejects missing collector evidence or unresolved material intent | Fully resolved current scope and the required actual human decision; no automatic acceptance from a saved answer |
| Execute with `build` | [`work_build.preflight`](../../../src/attune_harness/work_build.py#L105) rejects missing protected verification; [`build_work`](../../../src/attune_harness/work_build.py#L749) rejects review-tool registries, missing dispatch authority and unresolved operations | Accepted frozen effects/checks, qualified proposal-capable worker/reviewer, fresh inputs and separately authorized dispatch; never an `init` review registry substituted for a build registry |
| Inspect with `status` | The [saved-task owner walk](../saved-request-journey/README.md#source-owner-walk) covers unsafe/invalid records; stale evidence cannot confer current authority | The same saved task and retained checks; read-only inspection, not `resume` or a manufactured success receipt |

The command outline and collection blockers are in the protocol. Recheck these
owners against the exact installed candidate before approving a collection run.

## Proposed delivery boundary

Start with `feature-work-v1` on the same machine and the same explicit task
directory/checkout. Use the existing Forms validator and Harness task owner.
No new approval store, automatic transcript mining, cross-machine synchronization,
provider fallback, paid benchmark, arbitrary file opening or general GUI is in
scope. Existing platform/profile limits remain until separately qualified.

The new package complements the
[return-to-work plan](../task-opportunities/plan.md), which owns the broader task
companion. Extend its current projection rather than building a second viewer.
Coordinate overlapping files when implementation begins. The
[project plan](../../project-plan.md) still owns release sequencing.

## Decisions presented for approval

| Decision | Recommended contract |
|---|---|
| D1: first portability claim | Same-machine host handoff using an explicit saved task; no implied cross-machine transfer |
| D2: correction after effects | Use qualified pending-suffix steering only; otherwise offer explicitly scoped successor work retaining the old journal |
| D3: one-click evidence | Outcome-level Inspect results opens a bounded, read-only evidence summary in the supported host; HTML also has a single disclosure fallback |
| D4: compatibility | Additive APIs and human presentation only initially; preserve saved-state formats and existing JSON/CLI contracts |
| D5: rollout | Qualify hosts individually; unsupported native controls use a validated portable path with visible limits |

These are concrete proposed defaults, not recorded approval. No decision may
quietly weaken the existing acceptance, provider-spend or recovery gates.

## Evidence and completion review

Source baseline: Harness `c6c3475390129f5dae6e5ebb4cd201e07a31b1c3`, Forms
`4191c4e0c6bfe7ff21e4dd926f0ba8202775a9a7` (0.17.0). Refreshed origin/main and
checked Forms main through GitHub on September 28, 2026. Harness rc2 work was
separate at review time; rebase/re-evaluate before implementation.

Completion review: complete for planning, not product acceptance. The user/R6
lens exposed the difference between a valid saved decision and a usable handoff;
the contract lens found existing correction ownership to preserve; the next-step
lens identified host qualification and evidence presentation as the missing
integration work. Existing O-07 installation/platform work and the return-to-work
plan remain references, not new discoveries. Distinct candidates are J1–J4 in
the evaluation; their follow-ups and done conditions are in the design/tasks.
No separate duplicate opportunity-log entry is needed: this authorized planning
package retains the findings. The first user-visible opportunity is J1, choosing
a presentation that fits the host without re-asking settled facts. Human benefit
and live host compatibility remain unverified. This note authorizes no code work.
