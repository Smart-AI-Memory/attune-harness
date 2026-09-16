# Requirements — unified task execution

Status: approved by Patrick Roebuck, 2026-09-16. Requirements R1–R14 were approved first; the subsequent revised-spec approval also covers the design, validation and eight-task plan. The approved [session-reflection extension](session-reflection.md) adds a follow-on design without changing R1–R14. Execution is authorized; Task 1 implementation and offline checks are ready, with task acceptance pending. See the [baseline receipt](baseline.md).

## Outcome and slices

**Slice 1: evidence assessment.** One request carries the user through intake, retrieval, verification, selected participants, result integration, inspection, and interrupted continuation. Both solo and bounded independent-review plans use the same orchestration path.

**Slice 2: scoped repair.** Add real file effects and a real acceptance probe to that same path, supporting optional or required independent review. The user receives a checked artifact and evidence, not a model's unsupported claim that it fixed something.

Explicit policies select collaboration. Adaptive participant/team selection remains a separately evaluated extension. Existing commands remain compatibility routes during the transition.

## Verified starting point

Inspected local HEAD: `ce61c18ac396c91e5441ac34f218e41c942df593`, branch `codex/update-session-starter`. Network freshness was not checked. Existing Voyage/reranker work is outside this spec's authorship changes.

| Premise | Source evidence | Consequence |
|---|---|---|
| There are 18 top-level commands | Source CLI help executed successfully; `src/attune_harness/cli.py` and its three command-registration modules | All 18 require an explicit disposition |
| Core already separates returned output from independent acceptance | `src/attune_harness/__init__.py` | Preserve the dependency-free public core; do not replace it with a product-specific contract |
| Durable review currently requires two identities and document/context/corpus inputs | `src/attune_harness/review_contract.py` | New solo intake must not change the legacy two-role request contract |
| Roles currently execute sequentially with separate histories | `src/attune_harness/review.py` | Generalize bounded assignments, not a speculative distributed scheduler |
| Local operation records distinguish prepared, dispatching, and completed | `src/attune_harness/recovery.py`, `src/attune_harness/review_store.py` | Reuse durable effect boundaries and preserve unknown outcomes |
| Native adapter prohibits edits; Claude tools are disabled and Codex requests read-only execution | `src/attune_harness/native.py` | Real repairs need a new controlled effect operation; stronger prompting alone cannot provide one |
| Native evidence mode lets host code schedule retrieval/verification and bind response identity | `src/attune_harness/review_participants.py` | Preserve host ownership of correlation and required tool steps |
| Verification checks supported Markdown claims, not arbitrary semantic truth | `src/attune_harness/verification.py` | Evidence reports must distinguish tool checks from model judgments |
| Extensions currently support retrieval bindings | `src/attune_harness/extensions.py` | Do not imply a general executable-plugin capability |
| GitHub check import and triage only propose | `src/attune_harness/github_checks.py`, `src/attune_harness/operations.py` | No background repair dispatch is created by consolidation |

The portable-contract document includes historical status tables. Use current source and dated receipts when they differ; do not promote historical plans to implemented capabilities.

## Requirements and acceptance evidence

| ID | Requirement | Failing probe / receipt |
|---|---|---|
| R1 | One task request and durable identity span each journey; ordinary users do not hand-connect feature-specific JSON files | Installed CLI behavioral journey from goal plus selected inputs through resume/result; assert all suboperations reference one task/revision and no manually edited intermediate JSON |
| R2 | Solo and independent-review assessment use the same intake, dispatch, evidence, integration, and recovery services | Behavioral parity suite plus call-path evidence; assert solo invokes one participant, review invokes two distinct identities, and neither path owns a second orchestration loop |
| R3 | All current commands retain routes or explicit reviewed dispositions; deterministic and protocol use does not require a model | Command compatibility suite against all 18 names; poison model constructors for tool/protocol/inspection cases and assert zero dispatch |
| R4 | Accepted scope, inputs, participant bindings, effect grants, policies, and budgets survive interruption and transfer | Stale request/checkpoint, changed input/grant, and transfer fault suite; assert no invocation under changed authority and no lost accepted constraint |
| R5 | Independent review is an actual separate assignment, and integration preserves disagreement and provenance | Capture participant packets; assert assessment reviewer never receives lead narrative before responding. Seed disagreement; assert no majority-vote or coordinator success assertion becomes verified acceptance |
| R6 | Execution completion, assessment findings, artifact acceptance, and required review disposition stay distinct | Seed completed-but-refuted, unknown evidence, invalid result, missing reviewer, and failing repair probe; assert truthful non-verified results |
| R7 | Continuation never silently repeats a completed effect or guesses an uncertain effect safe | Inject faults before dispatch, after effect/before acknowledgement, and during persistence; assert completed replay makes no new call and unknown effects remain unresolved until supported reconciliation |
| R8 | Repair is limited to the accepted checkout/files and produces real changes checked by the declared acceptance probe | Real filesystem/command behavioral journey; before state fails probe, intended repair passes, wrong/no-op/out-of-scope patches fail; snapshot unrelated files and protected probes |
| R9 | Review policy for repair is explicit; required review cannot be dropped when unavailable | Solo optional-review and required-review matrices; assert stale review, wrong artifact hash, or missing required reviewer prevents verified completion |
| R10 | A second lead/provider and an additional participant are qualified only for the exact operations tested | Installed independent-peer and native live-fire receipts by adapter/model/role/tool profile; missing live evidence remains unqualified, never inferred from fixtures or registration |
| R11 | Frozen comparative cases measure correctness, missed defects, unsupported findings, calls/tokens, elapsed time, and human correction | Metric receipt against retained current-workflow/direct-model baselines; preserve every failed/uncertain trial and record absent billing/human data as unknown |
| R12 | Consolidation removes duplicate execution responsibility as well as reducing the primary menu | Before/after source-path inventory plus behavioral probes show new assessment, legacy review, and repair share dispatch/persistence/evidence services; compatibility adapters only translate contracts |
| R13 | Commands are memorable and map to recognizable vibe-engineering tasks; names communicate the expected effect | Usability walkthrough from an intent card without internal-feature terminology; assert review never repairs, fix returns an actual checked change, status never dispatches, and every advertised verb has a supported journey |
| R14 | Reuse forms, applicable answers, and completed task responses to reduce avoidable interaction latency while preserving freshness and independent assignments | Cold/warm/bypassed intake timings and avoided calls/questions; changed schema, options, project, scope or bindings invalidate reuse. Cached answers cannot grant approval, and one assignment's output cannot satisfy another independent assignment |

All user acceptance bullets are represented: R1 (one request); R3 (commands); R2/R12 (shared implementation); R10 (qualification); R4/R6/R7 (continuity/truth); R11 (measurement).

R13 records Patrick's subsequent naming direction and agreement to plan/build/fix/review/ship. Do not optimize raw command count by merging operations with different user promises. The agreed future verbs plan, build, and ship are not advertised as implemented or stubbed by this two-slice implementation.

R14 records Patrick's subsequent suggestion to cache dynamic forms or responses to reduce added latency. The design separates reusable presentation, answer defaults, and authoritative same-task results. Measure savings before claiming them; broad reuse of model judgments across tasks is outside this slice.

## Scope and compatibility

Reuse public forms, retrieval, verification, process, and adapter boundaries. Keep the core dependency-free and optional integrations lazy. Keep current exports, supported CLI inputs/results/exit semantics, native read-only defaults, and accepted old review records usable inside their existing supported recovery profiles.

Slice 1 supports the current bounded Markdown evidence-assessment domain with keyword retrieval and the existing explicitly selected Voyage path. It does not claim general code/security assessment solely because the objective is free text. A selected retrieval setup can be prepared by setup tools; ordinary task execution must generate and preserve the required intake/binding artifacts itself.

Slice 2 initially proposes regular UTF-8 file replacements in a dedicated local checkout, with an immutable acceptance-probe definition. File creation/deletion/rename and arbitrary native tool execution are outside the initial effect profile. This is a proposed implementation bound, not a new limit on Harness's eventual product.

Existing authorization and spend rules remain in force. This authoring request grants spec creation; it does not authorize model campaigns, implementation execution, publication, or migration of the user's active host. No new approval stage is introduced by this spec; draft/review/task acceptance follow the existing spec lifecycle.

## Non-goals

Adaptive team optimization, recursive delegation, a general DAG language, distributed scheduling, cross-machine ownership transfer, hosted service operation, automatic monitoring, package release, destructive command removal, replacement of Attune-family libraries, and rewriting attune-ai's workflow fleet.

Concurrent execution is not needed to prove the first two plans. The data model must not confuse dependency order with role identity, but the first engine may execute its bounded plan serially.
