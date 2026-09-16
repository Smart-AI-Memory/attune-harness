# Harness command and team consolidation

Date: 2026-09-16. Status: design assessment, proposed and not executable.

**Naming update:** the subsequent [unified task execution spec](specs/unified-task-execution/README.md) supersedes this assessment's illustrative run/task/setup vocabulary. Patrick agreed **plan, build, fix, review, ship**, with review and fix implementing the first two journeys. The inventory and implementation findings below remain the design baseline; the new spec owns the proposed routes and task ladder.

**Recommendation: give Harness one task entry point, shared task controls, and a separate setup surface. Let task policies compose reusable capabilities and agent teams underneath.** Exact command names below are illustrative, not implemented or ratified.

Patrick clarified the target: consolidate Harness's workflows and commands using the advanced agents, teams, and LLM capabilities called for in its spec. Attune-ai is a reference for useful behavior and migration compatibility, rather than the product whose menu should dictate Harness's design.

## Proposed user experience

| Surface | Purpose | Illustrative command |
|---|---|---|
| `run` | Describe an outcome; resolve material unknowns, establish the task contract, and perform the supported work | `attune-harness run "Review this change for security and correctness"` |
| `task` | Inspect and control the same durable task | `attune-harness task <id> resume` |
| `setup` | Configure participants, source/index resources, extensions, and connections | `attune-harness setup sources` |

Retain explicit deterministic tool and protocol entry points for scripts, diagnostics, and host integration. They can live under an advanced command group or retain compatibility aliases. An MCP server launch is a protocol process; it should not acquire a conversational/model dependency simply to make the top-level menu shorter.

Inside `run`, **understand/plan, change, and assess** are task policies, not separate runtime implementations. They determine the expected artifact, permitted effects, and acceptance evidence. A requested assessment never silently becomes a repair. Named shortcuts can select a policy without making users choose retrieval engines, individual agents, or internal phases first.

Example future journey: “Fix this failing test and check the related documentation.” Harness establishes the goal and scope, gathers code/test evidence, assigns bounded repair work, runs the relevant checks, gets independent review where required, checks documentation against the changed code, and returns the diff with evidence. Each step belongs to one recoverable task. This end-to-end journey is a proposed target; current Harness does not implement it.

## Verified command inventory and complete mapping

Source-checkout probe: `PYTHONPATH=src python3 -B -m attune_harness --help`, exit 0. It lists **18 top-level commands**. This proves the local parser's command surface, not installed-package or workflow qualification.

| Current commands | Proposed home | Behavior to preserve |
|---|---|---|
| `review-form`, `review` | `run` intake and assess policy | Accepted request, evidence scope, participant selection, and separate execution/verification results |
| `inspect-review`, `resume-review`, `reconcile-review`, `transfer-review`, `cancel-review` | `task` inspect/resume/reconcile/transfer/cancel | Checkpoint binding, unknown-effect handling, and no duplicate dispatch of completed work |
| `retrieve`, `verify` | Shared task tools; direct advanced access | Deterministic invocation where applicable, provenance, scope, and explicit unknown/unavailable outcomes |
| `retrieval-task` | Task intake plus a retrieval capability grant | Accepted source generation, participant grant, and provider-call budget |
| `code-config`, `index` | `setup sources` and index lifecycle | Plan/build/update/inspect distinctions; source uploads and paid calls keep their existing authorization semantics |
| `extension` | `setup extensions` | Discover/install/inspect/enable/disable/remove/replace behavior and artifact-bound lifecycle |
| `github-checks`, `triage-check` | Task evidence and triage operations; direct advanced access | Read-only import/proposal semantics; neither command currently dispatches a repair |
| `repair-economics` | Task reporting plus direct ledger analysis | Complete-attempt accounting; missing costs remain unknown |
| `mcp-serve` | Connection setup and explicit protocol launch | Accepted grants, stdio framing, participant identity, and session receipts |
| `mcp-inspect` | `task`/connection inspection | Read receipts without resuming or dispatching work |

Sources: [CLI](/Users/patrickroebuck/attune-harness/src/attune_harness/cli.py:10), [review controls](/Users/patrickroebuck/attune-harness/src/attune_harness/review_cli.py:12), [retrieval/index setup](/Users/patrickroebuck/attune-harness/src/attune_harness/voyage_cli.py:10), [extension lifecycle](/Users/patrickroebuck/attune-harness/src/attune_harness/extension_cli.py:9).

Reducing 18 menu entries is only a usability improvement. The maintenance improvement requires these routes to share task intake, dispatch, evidence, and recovery behavior rather than wrap distinct implementations indefinitely.

## How advanced agents and teams enable consolidation

The spec already separates model, runtime, role, task identity, feature access, and evidence. That makes specialized work composable without giving every combination a new command.

| Capability | Proposed use in the consolidated task system |
|---|---|
| Selectable lead | Claude or Codex can hold the task's lead role within the supported qualification profile; provider identity does not define workflow policy |
| Bounded specialist agents | The lead proposes assignments with goals, required inputs, allowed tools, artifact contracts, and acceptance probes. The runtime checks them against the accepted task |
| Agent teams | Run independent assignments concurrently when appropriate; wait for dependencies when one artifact feeds another. Keep independent reviewers' contexts separate until review completes |
| Reusable skills and tools | Retrieve evidence, inspect images, verify claims, generate artifacts, and run supported checks through shared interfaces instead of bespoke per-workflow teams |
| LLM/model selection | Select a qualified participant and supported reasoning/output settings for the assignment. A configured model is not proof of task fitness |
| Team coordination | Lead integrates returned artifacts and dispositions, records disagreements, and orders required independent checks. Agent agreement alone cannot mark the task verified |
| Durable task state | All assignments refer to the accepted task revision and retain attempts, artifacts, unresolved effects, and evidence across interruption or lead transfer |

These are proposed implementation mechanics for the settled architectural direction. Recursive spawning, unrestricted agent-to-agent messaging, and automatic team optimization are not implied by the word “advanced.” Add them only if a concrete task needs them and evidence supports them.

The simplest useful internal separation is:

1. **Task contract:** goal, scope, constraints, expected artifact, acceptance criteria, and current authorizations.
2. **Execution plan:** bounded assignments, dependencies, selected participants, required capabilities, and budgets.
3. **Shared runtime:** invocation, tool dispatch, operation/effect records, recovery, artifact/evidence collection, and status.
4. **Task policy:** plan, change, or assess semantics and domain-specific acceptance; reusable across command aliases and hosts.

Use one execution authority and work record. Domain checks remain explicit functions or small policies. Avoid a new universal workflow language that merely encodes the old implementation count in configuration.

Specification basis: [Harness outcome and settled requirements](/Users/patrickroebuck/attune-harness/docs/harness-phased-plan.md:76), [Phase 2 coordination](/Users/patrickroebuck/attune-harness/docs/harness-phased-plan.md:156), [original coordination/feature architecture](/Users/patrickroebuck/.codex/worktrees/593b/attune-ai/docs/research/agent-harness-communications.md:168), and [C1–C20 proposed conformance cases](/Users/patrickroebuck/.codex/worktrees/593b/attune-ai/docs/research/agent-harness-communications.md:283).

## What is present, and what remains to build

| Area | Inspected implementation | Gap for the proposed experience |
|---|---|---|
| Core task acceptance | `Task`, `Participant`, `Output`, independent `Check`, and receipt status | Core execution is synchronous/in-process; it is not a general durable team scheduler |
| Review coordination | Document/context/corpus inputs, two distinct role identities, sequential participant loop, scoped retrieval/verification, and saved evidence | General task inputs, solo/team plans, dependency-aware scheduling, and artifact integration |
| Native participants | Claude/Codex CLI boundaries, structured text envelope, configured models; Codex effort and skills-catalog settings | Scoped editing and command execution; the present adapter prohibits edits, disables Claude tools, and requests Codex read-only execution |
| Recovery | Local review inspect/resume/reconcile/lead-transfer/cancel operations | General assignment/effect recovery across task policies; cross-machine transfer is not established by local lead transfer |
| Extensions and protocols | Data-only extension lifecycle, retrieval binding, local MCP/A2A boundaries | General executable capability lifecycle and qualification of each required operation |
| Operations | Check import, deterministic triage suggestions, repair economics | Actual authorized repair dispatch and a complete checked-artifact journey |

Source: [core](/Users/patrickroebuck/attune-harness/src/attune_harness/__init__.py), [review contract](/Users/patrickroebuck/attune-harness/src/attune_harness/review_contract.py:49), [sequential role loop](/Users/patrickroebuck/attune-harness/src/attune_harness/review.py:128), [native execution](/Users/patrickroebuck/attune-harness/src/attune_harness/native.py:119), [recovery](/Users/patrickroebuck/attune-harness/src/attune_harness/recovery.py), and [extension binding limit](/Users/patrickroebuck/attune-harness/src/attune_harness/extensions.py:65).

**Conclusion:** Harness has reusable foundations. It does not yet have the general agent-team execution path needed to make all these commands disappear behind an end-to-end task. Renaming commands alone would leave that gap intact.

## Collaboration policy should remain evidence-based

The [retained eight-case screening](/Users/patrickroebuck/attune-harness/experiments/opportunities/results-2026-09-15.json) records 8/8 agreed passes for both one Astra reviewer and two Astra roles, with eight versus sixteen review calls. That small synthetic experiment does not establish general superiority of solo execution, but it provides no justification for mandatory extra roles on every task. The historical [adaptive-policy trial](/Users/patrickroebuck/attune-harness/docs/e3-local-research-receipt.md) also did not qualify its tested policy for production.

Support explicit solo, specialist-team, and independent-review plans. Preserve existing required review rules. Let a lead propose a plan within the accepted contract; do not treat automatic team selection as already validated or permit a model's plan to expand authority. More capable agents can reduce fixed orchestration steps, but the benefit needs task-level measurement.

## Recommended first design and implementation boundary

Write a Harness-owned **unified task execution** spec, using this inventory and the existing portable contract. Its first vertical slice should carry an evidence assessment from one task request through intake, retrieval, verification, selected participants, result integration, inspection, and interrupted continuation. This exercises supported foundations while testing whether one task record can actually replace the fragmented journey.

The first slice should demonstrate both a solo assessment and a bounded independent-review plan through the same orchestration path. Generalize only the services that slice needs. Use explicit policies; leave adaptive selection as a separately evaluated extension. Existing commands remain compatibility routes during the transition.

Then add a scoped repair with real file effects, a real acceptance probe, and optional/required independent review. That second slice is necessary to demonstrate the broader “do useful work with a team” vision; success on evidence assessment alone cannot stand in for it.

Proposed acceptance criteria for the future spec:

- One task request and identity cover the end-to-end journey; users do not hand-connect feature-specific JSON artifacts for ordinary work.
- Every current command has a preserved route or an explicit, reviewed disposition; protocol and deterministic automation remain usable without model calls.
- Task policies share intake, dispatch, evidence, and recovery implementation. Count retired duplicate paths as well as visible commands.
- A second lead/provider and additional participant are qualified only for the operations actually tested; unsupported assignments are visible before execution where detectable.
- Interruptions and uncertain effects never cause silent repeated work or false verified completion.
- Frozen comparative cases measure useful correctness, missed defects, unsupported findings, tokens/calls, elapsed time, and human correction. Cost remains unknown when billing evidence is absent.

The strongest counter-case is overbuilding a scheduler before useful tasks require it. Bound the first slice, keep specialist contracts simple, and require reuse across two actual task policies before generalizing further. No performance/cost reduction is claimed by this assessment.

## Assessment receipt

Inspected local Harness HEAD `ce61c18ac396c91e5441ac34f218e41c942df593` on `codex/update-session-starter`, source command declarations, runtime boundaries, the original architecture requirements, and retained experiment results. The source CLI help probe passed. New output is planning documentation only; existing source changes and experimental artifacts were preserved. No provider/model calls, implementation changes, commits, or publication were performed.

The [earlier attune-ai inventory](workflow-consolidation-assessment-2026-09-16.md) remains background for future migration. Its proposed four-family menu does not govern this Harness design.
