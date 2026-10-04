# Shepherd: a named autonomous workflow

Say **“Shepherd #221”** to an agent that knows this repository's working rules.
The intended outcome is a verified merge of the authorized change, or a precise
blocker with enough evidence for someone else to resume.

This is conversational shorthand for a development workflow, not a shipped
`attune-harness shepherd` CLI command, installed skill, or autonomous background
service. The [merge helper](../../scripts/merge_when_green.sh) implements part
of it. The agent supplies the authority checks, review judgment and handoff.
Installing `[all]` does not register this conversational verb.

## The contract

Think of a function invocation backed by a resumable workflow:

```text
shepherd(repository, pull_requests, authorization, constraints)
    -> verified merge receipt | blocked handoff | incomplete verification
```

This is explanatory notation, not an executable API or a proposed class schema.
Inputs may come from verified session context; do not ask the user to repeat them.
If the repository or authorized PR set is ambiguous, resolve that before effects.

| Input | What must be known |
|---|---|
| Target | Repository and named PR or ordered set, current head, base and owner |
| Authority | Human authorization covering that scope and its limits; a green badge is not permission |
| Review | Required reviewer, exact reviewed source/delta and unresolved findings |
| Constraints | Applicable repository rules, publication holds, protected evidence and spending limits |
| Done | All applicable checks settled, protected pinned merge, verified tree and accurate cleanup receipt |

The repository's [AGENTS.md](../../AGENTS.md) governs execution. This guide grants
no authority and does not generalize one session's standing delegation to everyone.
An instruction to shepherd is not permission to publish, force-push, change
protection or expand the implementation scope. Different-model source review
remains required where the rules say so.

## Walk the user journey

| Step | What the agent does | What the user sees / decides |
|---|---|---|
| 1. Invoke | Resolve the target and authorization; inspect state before acting. If already merged, inspect its receipt instead of attempting another merge. | “I will shepherd #221; other PRs are outside this request.” |
| 2. Inspect | Check actual diff, ownership, branch freshness, review evidence and check/workflow state. | A concise scope confirmation or a specific missing decision. |
| 3. Prepare | Within authority, mark ready and update the owned branch if behind. Recheck any changed head and required review. Stop on conflicts or unapproved changes. | Only meaningful changes or blockers, not requests to perform routine checks. |
| 4. Wait and investigate | Wait for every applicable workflow/check. Examine failures and review findings against primary evidence. Do independent, isolated work while waiting. | Progress when the state materially changes; actionable evidence if blocked. |
| 5. Merge | Reconfirm final head and gates; squash without bypass, pinned to the checked head. | A brief merging notice; no repeated permission question when authority already covers it. |
| 6. Verify | Confirm API merge state, compare squash and tested trees, inspect branch dependencies and complete authorized cleanup. | Receipt naming the tested head, merge SHA, checks and any incomplete cleanup. |
| 7. Learn | Review the outcome proportionally; retain a useful lesson or update an existing opportunity without inventing follow-up work. | A useful finding, or a reasoned no-change outcome. |

Agents are participants in the workflow, not its identity. One coordinator owns
merge effects; a reviewer can independently inspect changes. Parallel workers
must not write the same checkout or push the same branch.

## What the helper refuses, and what the agent supplies

These source locations refer to the helper at main `5cdedaf`. It is shell code,
so refusals are explicit `exit` paths rather than Python `raise` statements.
The table documents existing behavior; it does not claim missing guards exist.

| Ordered boundary | Existing refusal / behavior | What must be supplied before advancing |
|---|---|---|
| Target and head | `number` requires an argument (line 22); expected prefix waits (36–38); changed head exits 2 (50–52) | Verify repo and PR; provide the full intended head and restart inspection when it changes. |
| Checks | Failed rollup exits 1 (58–71); missing Qualification waits, with no-run timeout (77–82); pending checks wait (84–85) | Inspect workflow runs as well as job checks. A queued workflow may have no jobs yet; wait for its completion before relying on the rollup. Verify any skipped jobs match the change classification. |
| Mergeability | Behind/conflicting branch exits 2 (90–95); other blocked states wait until deadline (30–33) | Integrate only within ownership/authority; stop on conflict. Inspect unresolved reviews, signatures or protection without bypassing them. |
| Title and dependents | Empty title exits 1 (99–100); open PRs based on the head branch exit 2 (103–105) | Nonempty subject; inspect dependent PRs and obtain any authority needed to retarget them. |
| Merge | `gh pr merge --squash --match-head-commit` (106); API must report MERGED (107) | Authority and required independent review are agent checks, not enforced by this script. Preserve co-author/review evidence in the squash message as required. |
| Tree | Unequal tested/squash trees exit 4 (109–116) | Treat this as merged with verification incomplete; do not retry merge or clean up as if verified. Investigate the mismatch. |
| Cleanup | Deletion attempts suppress errors (120–124) | Verify actual remote/local branch state independently. The helper's final “deleted” text alone does not prove cleanup. Keep needed local notes and artifacts. |

The helper accepts SUCCESS, SKIPPED and NEUTRAL check conclusions, and disregards
a cancelled duplicate if another result for that check exists. An unexplained
skip is not qualification. Its first wait checks head stability; the later
mergeability wait does not repeat the full rollup. If waiting there is prolonged,
re-read head, runs and checks before continuing. A pinned merge protects head
identity; it does not replace all workflow-level checks.

## Worked example: PR #221

This is a reconstruction from retained evidence, not a new live merge exercise.
[PR #221](https://github.com/Smart-AI-Memory/attune-harness/pull/221) changed three
planning documents. Its checked head was
`74bf8262f911131a058bb1cf07cf4c9396286ef0`.

1. The user explicitly authorized shepherding. The agent checked scope and
   marked the draft ready.
2. Documentation qualification passed, but supplemental run
   [37172151315](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/37172151315)
   was queued before its job checks appeared. The agent waited for those jobs
   rather than treating an incomplete rollup as all-green.
3. Linux, Windows and macOS measurements passed. Separate installed-platform
   and full-suite qualification jobs were intentionally skipped for a docs-only
   change; no new platform capability was qualified.
4. GitHub still blocked merging on an automated missing-co-author finding.
   Both remote commit messages already contained the trailer. The agent checked
   the messages, recorded the evidence and resolved the false positive without
   rewriting history. A valid finding would have required a repair or handoff.
5. The helper merged the pinned head as
   `5cdedafc1988ad516f59b18563c157c733093dc3`, verified tree equality and completed
   branch cleanup. The PR body retains the final receipt.

The human supplied the outcome and authority. The agent handled the mechanical
span and evidence-based review disposition. No paid model call was needed.

## Interruptions and honest outcomes

Before stopping, keep repository, PR/head, authorization source and limits,
reviewed head, run IDs, outstanding findings, last completed step and next safe
action in the existing PR handoff or private operational notes. Avoid storing
expiring CI state as permanent knowledge. No new persistence engine is implied.

On resumption, re-read GitHub and repository state. If merged, verify that merge;
if the head changed, refresh its review/checks; if authority is unclear, ask.
A lost connection during merge means inspect outcome, not blindly retry. The
script is not a durable resumable controller and cannot continue after its host
stops. Unattended continuation requires an explicitly configured executor.

| Outcome | Report |
|---|---|
| Complete | PR, tested head, merge SHA, check evidence, tree match and actual cleanup status |
| Blocked before merge | Exact refusal, retained evidence, decision/repair required and how to resume |
| Merged but unverified | Known merge SHA, missing or mismatched evidence; no claim of completion |
| Interrupted | Last verified step and next safe action; no implied background activity |

## Session review

This walkthrough clarifies an existing conversational contract, not a new product
feature. The queued-workflow and cleanup-reporting gaps belong in the existing
merge-helper audit; they are not fixed by this document. Completion review:
complete for documentation. The first gap a user would meet is queued CI appearing
absent from the job rollup. No new live merge, code qualification or resumable
runtime was exercised by writing this guide.
