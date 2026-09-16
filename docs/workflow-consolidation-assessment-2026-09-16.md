# Attune workflow consolidation assessment

Date: 2026-09-16. Status: proposal for discussion, not an approved spec or executable task queue.

**Scope update:** Patrick clarified that the primary target is Harness's own commands and agent/team workflows. This document is retained only as background on the attune-ai fleet. The current recommendation is [Harness command and team consolidation](harness-command-consolidation-assessment-2026-09-16.md); the four-family proposal below is not the selected Harness command design.

Patrick's objective: reduce both the workflows users must choose between and the implementations maintained, using the agent and LLM architecture specified for Attune Harness.

**Recommendation: four primary workflows—Plan, Change, Check, and Release—built on shared Harness execution services.** Keep specialized knowledge, tools, checks, and output contracts as reusable profiles. Preserve existing names as compatibility routes during migration. This is a feasible architectural direction inferred from source, not demonstrated migration parity or measured savings.

## Evidence and scope

- Inspected attune-ai checkout: `/Users/patrickroebuck/attune-ai`, HEAD and cached `origin/main` both `fe08f282fb0ad9cbb7eedf75af2597336576578e`. Network freshness was not checked. Its existing untracked usage snapshot was preserved.
- Inspected Harness checkout: `/Users/patrickroebuck/attune-harness`, branch `codex/update-session-starter`, HEAD `ce61c18ac396c91e5441ac34f218e41c942df593`. Existing Voyage/reranker work was preserved.
- AST inspection of the built-in registry found **23 names, 21 distinct classes**. `release-prep`/`release-gate` and `health-check`/`orchestrated-health-check` are the two alias pairs. The tracked plugin contains **28 skills**, a different inventory from the workflow registry.
- **13 of the 21 classes declare SDK subagent dictionaries directly.** `deep-review` separately builds its dictionary dynamically. These classes repeat model dispatch, permission/tool configuration, depth budgets, result collection, telemetry, and error handling around different specialist instructions. They already share helpers; the opportunity is to consolidate the remaining execution paths, not introduce the first common base class.
- Scope covers all built-in registry names and all tracked plugin skill entry points. It is not an inventory of third-party extensions, every internal helper, all host commands, or installed user customizations.
- Repository preflight preserved status and passed projection checks, but its governance test subprocess failed because the system Python could not import `attune`. No implementation tests, new model trials, paid synthesis, or production mutations were performed for this assessment.

Primary sources: [registry](/Users/patrickroebuck/attune-ai/src/attune/workflows/__init__.py:298), [existing base](/Users/patrickroebuck/attune-ai/src/attune/workflows/base.py:169), [code review](/Users/patrickroebuck/attune-ai/src/attune/workflows/code_review.py), [deep review](/Users/patrickroebuck/attune-ai/src/attune/workflows/deep_review.py:267), and [SDK helper facade](/Users/patrickroebuck/attune-ai/src/attune/workflows/agent_sdk_adapter.py).

## Four user-facing workflows

| Workflow | User's intended outcome | What remains specialized |
|---|---|---|
| **Plan** | Understand the evidence and decide what to do | Research, architecture, refactoring analysis, requirements, acceptance criteria, spec decisions |
| **Change** | Produce or repair an artifact and demonstrate the requested behavior | Code, tests, documentation, scoped fixes, single-source authoring, relevant acceptance probes |
| **Check** | Assess an artifact or repository and return evidence-backed findings | Security, correctness, performance, dependencies, test gaps, documentation accuracy, independent review |
| **Release** | Establish release readiness and carry out separately authorized shipping steps | Deterministic release gates, packaging/version rules, release notes, publication and rollback procedures |

These names describe outcomes, not model identities. Depth, domain, participants, and collaboration strategy are settings within the workflow. Examples of the proposed interface: “check this diff for security issues,” “change this module to fix the regression,” and “plan a refactor using the repository evidence.” Exact CLI spelling is unresolved.

Keep Release distinct because readiness, authority to publish, and actual publication are different states. It can compose Check and Change without owning another model runtime. A clean check never grants publication authority.

## Complete built-in workflow mapping

Every registry slug appears below. Placement is a proposed destination; compatibility routes must retain their present effect and output contracts.

| Existing workflow(s) | Proposed destination | Preserve or change deliberately |
|---|---|---|
| `code-review` | Check / code | Review scope, findings, severity, evidence, and report consumers |
| `deep-review` | Check / code, deeper profile | Selected review dimensions; depth must not silently become an obligatory larger team |
| `security-audit` | Check / security | Security-specific detection and evidence; model prose cannot substitute for deterministic checks |
| `perf-audit` | Check / performance | Distinguish suspected bottlenecks from measured performance |
| `bug-predict` | Check / defect risk | Preserve predictions as hypotheses, separate from reproduced defects |
| `dependency-check` | Check / dependencies | Dependency inventory, audit evidence, and actionable dependency failures |
| `test-audit` | Check / tests | Actual coverage/test evidence and gap analysis |
| `doc-audit` | Check / documentation | Staleness, source agreement, missing evidence, and explicit uncertainty |
| `discovery-sweep` | Check / repository sweep | Source composition, normalized findings, deduplication, and act/question/reject dispositions |
| `orchestrated-health-check`, `health-check` | Check / project health | Existing health modes, scoring, and report schema |
| `refactor-plan` | Plan / refactoring | Priorities, dependencies, rationale, and proposed acceptance criteria |
| `research-synthesis` | Plan / research | Source citations, contradictions, and uncertainty |
| `simplify-code` | Plan / simplification; Change only when applying | Current SDK tool grant is read-only. Its old alias must not start editing merely because the destination supports Change |
| `fix` | Change / scoped repair | Existing scope guards, accepted goal, done conditions, real diff, and probe-based receipt |
| `test-gen` | Change / tests | Actual output files, collection/execution, and tests that detect the intended defect |
| `rag-code-gen` | Change / grounded code draft | Retrieval provenance and draft output; saving/applying a draft remains a separate effect |
| `doc-gen` | Change / documentation draft | Draft output and polish; current agent tools are read-only, so do not silently add file writes |
| `doc-orchestrator` | Change / documentation maintenance | Scout/prioritize/generate/update behavior becomes composition of shared operations |
| `release-prep`, `release-gate` | Release / readiness | Real checks, quality gates, missing/failed gatekeeper handling; executed assessment is not approval |
| `release-notes` | Release / notes, using Change's authoring operation | Draft notes and advisory readiness remain separate from the deterministic gate |
| `secure-release` | Release / security profile | Existing blocker and go/no-go rules, invoking shared Check operations |

The opportunity is strongest among the audit/review wrappers. Mutation workflows and release gates carry additional contracts that cannot be reduced to a different prompt.

## All tracked skills also have a home

Skills are entry points and instruction packages; some are services or shortcuts rather than independent workflows. They need not all become menu-level choices.

| Proposed home | Existing skill names |
|---|---|
| Plan | `planning`, `refactor-plan`; `spec` remains the lifecycle entry spanning planning and accepted execution |
| Change | `fix`, `fix-test`, `doc-gen`, `rag-code-gen`, `author-feature`, `docs-outbox` |
| Check | `code-quality`, `security-audit`, `bug-predict`, `discovery-sweep`, `verify`, `workflow-orchestration` |
| Check → Change composition | `smart-test` finds gaps and then generates tests within the requested scope |
| Release | `release-prep` |
| Collaboration modes | `cross-review`, `roundtable`; reusable in Plan/Check/Change where existing policy requires or the user requests them |
| Shared intake and evidence services | `elicit`, `image-analysis`, `recall`, `memory-and-context`, `personal-memory` |
| Execution option | `bulk`; retain its separate execution semantics rather than exposing it as another task goal |
| Navigation/help | `attune-hub`, `catalog`, `coach` |

Keep memory administration and help directly accessible. Folding their implementation into an LLM workflow would add complexity. Keep spec approvals, outbox decisions, and single-source projection rules attached to their owning operations.

## What actually gets consolidated underneath

The proposed shape is **one shared execution core, four small product policies, reusable domain operations, and provider/host adapters**. This is not a requirement for one giant function or a universal workflow language.

| Layer | Responsibility |
|---|---|
| Shared execution services | Task/revision identity, participant invocation, budgets, operation/effect records, cancellation/recovery, artifact references, and execution versus acceptance status |
| Product policies | Plan stops with decisions/proposals; Change requires artifact acceptance; Check produces findings and dispositions; Release preserves readiness/publication transitions |
| Domain profiles and operations | Specialist instructions, required inputs, scoped tool grants, output contracts, deterministic probes, and domain-specific aggregation |
| Participant strategy | Explicit solo, independent review, or roundtable; selectable lead/model and bounded roles, with existing mandatory review rules retained |
| Adapters | Provider-specific model/effort configuration and native execution; host-facing CLI, MCP, skills, forms, and compatibility aliases |

Attune-ai already has a large mixin-based `BaseWorkflow` and shared SDK helpers. Merely putting another facade above it would reduce visible names while leaving maintenance intact. A migrated profile must actually stop owning its own dispatch/result/error/telemetry loop. Preserve public Attune-family library calls instead of copying forms, retrieval, verification, memory, or authoring implementations into Harness.

## Match to the enhanced Harness requirements

The original [Harness roadmap](/Users/patrickroebuck/attune-harness/docs/harness-phased-plan.md:78) and [C1–C20 requirements](/Users/patrickroebuck/.codex/worktrees/593b/attune-ai/docs/research/agent-harness-communications.md:283) support this direction. They do not establish that every capability is ready.

| Requested capability | How consolidation uses it | Evidence and remaining gap |
|---|---|---|
| Either Claude or Codex leads; additional models participate (C1–C3) | Workflow policy selects a role; adapters supply execution | Harness has a participant registry and native/command boundaries. This does not establish arbitrary-provider or full feature parity |
| Shared forms, retrieval, verification, skills and plugins (C3, C17–C20) | Reuse the same evidence/intake/tool services across profiles | Implemented local review integrations exist. Extension contract 1 accepts only retrieval bindings; general executable extensions are not implemented there |
| Rich model settings with portable guarantees (C19) | Capability checks select a suitable participant and expose unavailable operations | Native adapter accepts model selection; reasoning effort and skill-catalog budget are Codex-specific in the inspected code |
| Structured output and independent acceptance (C8, C15) | Same result envelope, domain-specific acceptance probes | Core separates output from Check. Native envelope constrains a text field; this is not an already-general structured findings schema or semantic correctness guarantee |
| Durable work and lead transfer (C4–C7, C13–C14) | Shared recovery records replace per-workflow continuation machinery | Implemented for the bounded local review journey. General editing, external effects, and cross-machine continuation require further work |
| Evidence-based collaboration choice (C16) | Team composition becomes a reusable option instead of a separate workflow class | Explicit comparisons exist; automatic adaptive team selection was not qualified for production by those results |

**The blocking implementation gap is concrete:** the present `review` coordinator requires a reviewed document, context, corpus, and distinct lead/reviewer identities. It is not a general Plan/Change/Check/Release runner. Its native adapter tells participants not to use tools or modify files; Claude is launched with tools disabled and Codex with a read-only sandbox. Built-in review tools are `retrieve` and `verify`. Supporting scoped edits, real test/command execution, artifact acceptance, solo orchestration, and publication effects requires deliberate extensions. The dependency-free in-process core can run a single participant, but does not itself provide that richer durable workflow.

Source: [review contract](/Users/patrickroebuck/attune-harness/src/attune_harness/review_contract.py:49), [review coordinator](/Users/patrickroebuck/attune-harness/src/attune_harness/review.py:16), [native boundary](/Users/patrickroebuck/attune-harness/src/attune_harness/native.py:119), [extensions](/Users/patrickroebuck/attune-harness/src/attune_harness/extensions.py:65), and [core](/Users/patrickroebuck/attune-harness/src/attune_harness/__init__.py).

## What the experiments justify

The retained [September 15 aggregate](/Users/patrickroebuck/attune-harness/experiments/opportunities/results-2026-09-15.json) records 8/8 agreed passes for direct Astra and 8/8 for two Astra roles. The team used 16 review calls versus eight and 317,682 input tokens versus 158,021. Mixed Sol/Astra recorded six passes, one failure, and one inconclusive case. These were eight synthetic cases with one repetition and model/implementation-author grading, not independent human validation or a general accuracy estimate.

The separate [E3 local trial receipt](/Users/patrickroebuck/attune-harness/docs/e3-local-research-receipt.md) records a failed adaptive-collaboration acceptance criterion on the historical local model: equal correctness count but an additional critical miss against the selected fixed baseline. Patrick subsequently retired that local model from intended use. This evidence rejects that tested policy/profile, not adaptive collaboration in principle.

**Inference:** stronger participants and better host-managed evidence can eliminate some fixed “scanner → analyst → writer” chains, but the proposed solo policy must be tested on the migrated domains. Preserve required independent review. Add agents for a defined purpose and evaluate their contribution; do not equate more roles with greater correctness. No fleet-wide token, dollar, latency, or maintenance savings have been measured.

## Migration experiment and decision criteria

Start with **Check**, using code review, security audit, and documentation audit as three profiles. This tests a shared engine across distinct domains. Harness's evidence-review machinery provides a starting point, but actual diff/repository evidence and each profile's probes must be added before claiming replacement.

1. Freeze each old workflow's inputs, effects, result consumers, failure behavior, and representative clean/defective/uncertain cases. Reuse existing behavioral records as historical context, then establish a fresh matched baseline when model execution is authorized.
2. Implement one bounded shared Check path using existing Harness primitives. Make profiles supply domain policy and checks; compare solo and explicitly requested/required review strategies on the same evidence. Do not implement an adaptive selector in this increment.
3. Require no lost contracted capability, no additional critical misses on the frozen set, explicit failure/unknown outcomes, and functioning legacy CLI/MCP result translation. Include interrupted execution, stale input, unavailable tools, and missing reviewers in deterministic checks. Freeze sample sizes and quantitative quality criteria before model trials.
4. Measure total calls/tokens, elapsed time, billed cost where known, false findings, missed defects, human corrections, and how many independent execution paths remain. A four-item menu above 21 unchanged engines fails the maintenance objective.
5. Migrate through aliases one profile at a time, keeping a reversible old path until parity is demonstrated. Then add scoped Change, reuse Plan's evidence operations, and compose Release from qualified operations while preserving its gates.

Existing [fix contracts](/Users/patrickroebuck/attune-ai/docs/specs/outcome-first-fix/requirements.md), [intake forms](/Users/patrickroebuck/attune-ai/docs/specs/workflow-intake-forms/requirements.md), [host surface parity](/Users/patrickroebuck/attune-ai/docs/specs/host-surface-parity/requirements.md), and [models/workflows layering](/Users/patrickroebuck/attune-ai/docs/specs/models-workflows-layering/requirements.md) are dependencies to reconcile in a future consolidation spec. This assessment does not supersede them or approve their draft tasks.

One inventory caution: the current [visibility table](/Users/patrickroebuck/attune-ai/src/attune/workflows/visibility.py) still hides `test-gen`, `doc-gen`, and `research-synthesis` for recorded failures, while the [projected probe registry](/Users/patrickroebuck/attune-ai/docs/specs/workflow-behavioral-validation/registry.md) contains later PASS records. Current test generation also grants Write. These disagree; neither hiding nor a historical pass alone establishes present usability. Reconcile them when choosing baseline cases, rather than counting hidden workflows as either disposable or verified.

## Strongest counter-case

A generic engine can become harder to reason about than small explicit workflows, with the old 21 implementations merely reappearing as elaborate configuration. Domain-specific checks and effect boundaries are real differences. The alternative is to retain explicit product workflows while sharing only proven execution services.

Use the three-profile Check experiment to decide. If it needs numerous profile-specific engine branches, weakens checks, or fails to retire duplicate execution paths, narrow the abstraction. Four primary user goals remain useful even if the best internal design needs several small coordinators. The proposed number is a product design hypothesis, not an optimization result.
