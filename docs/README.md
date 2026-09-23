# Documentation index

Two kinds of file live under `docs/`. The documents in the first list are
kept current and describe Harness as it is. Everything after them is dated
evidence: results, receipts, design notes and research from the days they
were written, kept because other documents cite them, and not refreshed.
Read a dated file for what was true on its date. Attune AI behaviour that
some of them describe is being replaced by the spec authority.

Generated on September 22, 2026 from the 191 Markdown files under
`docs/`; `scripts/check_doc_links.py` keeps every link here honest.

## Start here

- [CLI guide](cli-guide.md): Every command, its arguments and exit codes
- [Envelopes](envelopes.md): The top-level keys, schema version, status and exit code every verb is pinned to before 1.0
- [Release runbook](release-runbook.md): How a release is cut, and the state that lives outside the repository
- [Library qualification](qualification.md): What the platform jobs qualify and what they do not
- [Portable contract and qualification map](portable-contract.md): The execution contract and the qualification map
- [Checks, handoffs and repair economics](operations.md): Checks, handoffs and repair economics
- [Coordinated evidence review](review-workflow.md): Coordinated evidence review
- [Local verification and retrieval](local-workflow.md): Local verification and retrieval
- [Local MCP retrieval profile](mcp-workflow.md): The local MCP retrieval profile
- [Recover and transfer a local review](recovery-workflow.md): Recovering and transferring a review
- [Local extension workflow](extension-workflow.md): The local extension workflow
- [Code-grounded documentation](documentation-workflow.md): Code-grounded documentation
- [Local A2A task/artifact profile](a2a-workflow.md): The local A2A task and artifact profile
- [Attune RAG anchored in repository code](code-first-rag.md): Attune RAG anchored in repository code
- [Voyage context for coding agents](voyage-retrieval.md): Voyage context for coding agents
- [Review using host-owned source passages](passage-review.md): Review using host-owned source passages
- [Agent collaboration: what is in force, and what is planned](agent-collaboration-plan.md): Planned and aspirational items for the agents
- [Engineering opportunity log](opportunity-log.md): Opportunities noticed and not yet authorized; dated evidence
- [The standing brief for a different-model review](review-brief.md): What the reviewing agent is told before every `src/` change merges
- [Review findings log](review-findings.md): What each review found that the author had missed, by class
- [Windows traps](windows-traps.md): The platform differences that cost a finding or a failed job, with the fix for each
- [The four phases between 0.4.0 and 1.0.0](plan-1.0.md): What remains before 1.0.0, with each phase's tasks, receipts and decisions
- [Native memory, Phase 2: design note](specs/native-memory/phase-2-design.md): What the attune-ai dependency actually is, the native reader that replaces it, and eight decisions for Patrick
- [Phase 3: design note](specs/phase-3-design.md): The journey native and memory served, with ten decisions for Patrick
- [Spec authority — owned by Harness, built from reviewed Attune AI code](specs/spec-authority/README.md): The spec authority: Harness takes over spec approval from Attune AI
- [Spec authority: addendum, September 21, 2026](specs/spec-authority/addendum-2026-09-21.md): Rulings on the spec authority, dated
- [Spec authority: addendum, September 22, 2026](specs/spec-authority/addendum-2026-09-22.md): D14, Task 3's five decisions, and a same-day correction
- [Spec authority: addendum, September 23, 2026](specs/spec-authority/addendum-2026-09-23.md): D20, the Phase 3 rulings on the journey, the plugins, Windows and the order; D22, the plugins spec approved
- [Native memory: decisions, September 22, 2026](specs/native-memory/decisions-2026-09-22.md): D15 to D19, the base install, the Redis backend and the Phase 2 rulings
- [Native memory: decisions, September 23, 2026](specs/native-memory/decisions-2026-09-23.md): D21, the Phase 3 rulings on serving and the store, and a correction to the note
- [Spec authority, Task 1: module verdicts](specs/spec-authority/verdicts.md): Task 1's adopt, adapt, reference or drop verdict for each module
- [Spec authority, Task 2: plan](specs/spec-authority/task-2-plan.md): Task 2's four steps
- [Attune Harness — phased delivery plan](harness-phased-plan.md): The earlier phased plan, superseded in part

## Dated evidence and design notes

### Design notes

| File | Title | Dated |
| --- | --- | --- |
| [design-a2a-increment.md](design-a2a-increment.md) | A2A local peer profile — design before implementation | 2026-09-14 |
| [design-adapter-increment.md](design-adapter-increment.md) | Adapter boundary experiment |  |
| [design-astra-review.md](design-astra-review.md) | Astra review selection — design |  |
| [design-code-first-rag.md](design-code-first-rag.md) | Code-first Attune RAG | September 15, 2026 |
| [design-documentation.md](design-documentation.md) | Code-grounded documentation: first increment |  |
| [design-durable-decisions-b.md](design-durable-decisions-b.md) | B — retain decision text before collection | September 18, 2026 |
| [design-e2-increment.md](design-e2-increment.md) | E2 — design and criteria frozen before evaluation | 2026-09-14 |
| [design-e2-revision.md](design-e2-revision.md) | E2 revision: historical evidence and actual-call results | 2026-09-14 |
| [design-e3-local-increment.md](design-e3-local-increment.md) | E3 local collaboration research and explicit local-model adapter | 2026-09-14 |
| [design-extension-increment.md](design-extension-increment.md) | Local extension increment — design before implementation | 2026-09-14 |
| [design-feature-workflow.md](design-feature-workflow.md) | Local verification and retrieval milestone |  |
| [design-first-increment.md](design-first-increment.md) | First local increment: standalone execution contract |  |
| [design-grounded-passages.md](design-grounded-passages.md) | Passage selection revision |  |
| [design-grounded-review.md](design-grounded-review.md) | Grounded local review increment |  |
| [design-mcp-increment.md](design-mcp-increment.md) | MCP local retrieval profile — design before implementation | 2026-09-14 |
| [design-native-evidence-review.md](design-native-evidence-review.md) | Native evidence review — repair after the first Astra run |  |
| [design-native-increment.md](design-native-increment.md) | Native CLI boundary increment |  |
| [design-navigation.md](design-navigation.md) | Task-first command navigation | 2026-09-16 |
| [design-opportunities.md](design-opportunities.md) | Reliability opportunities 1–5 | 2026-09-15 |
| [design-output-budget-increment.md](design-output-budget-increment.md) | Configurable review output budget |  |
| [design-passage-review.md](design-passage-review.md) | Passage review — implementation design |  |
| [design-phase5-increment.md](design-phase5-increment.md) | Phase 5 local evaluation increment | 2026-09-14 |
| [design-phase6-grammar-fix.md](design-phase6-grammar-fix.md) | Pilot grammar and error diagnostic fix |  |
| [design-phase6-increment.md](design-phase6-increment.md) | Phase 6 — local documentation-review pilot | 2026-09-14 |
| [design-recovery-increment.md](design-recovery-increment.md) | Local recovery and lead transfer |  |
| [design-review-increment.md](design-review-increment.md) | Coordinated local evidence review |  |
| [design-review-quality-evaluation.md](design-review-quality-evaluation.md) | Documentation review quality: frozen local acceptance check |  |
| [design-sol-review-fixes.md](design-sol-review-fixes.md) | Fix the four confirmed Sol review findings | September 16, 2026 |
| [design-spec-test-handoff.md](design-spec-test-handoff.md) | Bound Harness test evidence at Spec acceptance | 2026-09-17 |
| [design-status-guidance-a.md](design-status-guidance-a.md) | A — plan/build status guidance | September 18, 2026 |
| [design-token-accounting-increment.md](design-token-accounting-increment.md) | Model-aware token accounting |  |
| [design-voyage-100-question-evaluation.md](design-voyage-100-question-evaluation.md) | 100-question code retrieval evaluation | 2026-09-15 |
| [design-voyage-answer-accuracy.md](design-voyage-answer-accuracy.md) | Final-answer accuracy pilot | September 15, 2026 |
| [design-voyage-full-code-evaluation.md](design-voyage-full-code-evaluation.md) | Full-code retrieval evaluation | September 15, 2026 |
| [design-voyage-retrieval.md](design-voyage-retrieval.md) | Voyage application retrieval: implementation design | September 15, 2026 |
| [design-windows-effect-backend.md](design-windows-effect-backend.md) | Windows file-effects backend from the observed native primitive | September 18, 2026 |
| [design-windows-feature-effects.md](design-windows-feature-effects.md) | Windows feature and repair effects — design only | September 18, 2026 |
| [design-windows-runtime.md](design-windows-runtime.md) | Native Windows execution and recovery | 2026-09-15 |

### Results and receipts

| File | Title | Dated |
| --- | --- | --- |
| [a2a-workflow-receipt.md](a2a-workflow-receipt.md) | A2A local interoperability and final protocol receipt | 2026-09-14 |
| [assessment-quality-comparison-results.md](assessment-quality-comparison-results.md) | Assessment-quality comparison: revise the candidate | 2026-09-17 |
| [astra-review-receipt.md](astra-review-receipt.md) | Astra reviewer selection — dev8 receipt | September 15, 2026 |
| [code-first-rag-receipt.md](code-first-rag-receipt.md) | Repository-first RAG implementation receipt | September 15, 2026 |
| [connected-journey-qualification-results.md](connected-journey-qualification-results.md) | Connected journey qualification — results | 2026-09-17 |
| [durable-decisions-b-results.md](durable-decisions-b-results.md) | Opportunity B — durable decision text verified | September 18, 2026 |
| [e2-capability-evidence-receipt.md](e2-capability-evidence-receipt.md) | E2 capability-evidence experiment | 2026-09-14 |
| [e2-revision-receipt.md](e2-revision-receipt.md) | E2 fix: evidence belongs to an invocation | 2026-09-14 |
| [e3-local-research-receipt.md](e3-local-research-receipt.md) | E3 local collaboration research — revise | 2026-09-14 |
| [extension-workflow-receipt.md](extension-workflow-receipt.md) | Local extension implementation receipt | 2026-09-14 |
| [feature-workflow-receipt.md](feature-workflow-receipt.md) | Four-step local feature milestone — 2026-09-14 | 2026-09-14 |
| [fresh-installation-results.md](fresh-installation-results.md) | Fresh installation qualification | 2026-09-17 |
| [grounded-review-receipt.md](grounded-review-receipt.md) | Grounded review dev6 — closing receipt | September 14, 2026 |
| [live-probe-receipt.md](live-probe-receipt.md) | Approved live probes — 2026-09-14 | 2026-09-14 |
| [local-build-receipt.md](local-build-receipt.md) | First local build receipt |  |
| [mcp-workflow-receipt.md](mcp-workflow-receipt.md) | MCP implementation and SDK upgrade receipt | 2026-09-14 |
| [native-adapter-experiment.md](native-adapter-experiment.md) | Next native adapter experiment |  |
| [native-build-receipt.md](native-build-receipt.md) | Native adapter implementation receipt — 2026-09-14 | 2026-09-14 |
| [native-evidence-review-receipt.md](native-evidence-review-receipt.md) | Astra native evidence review — dev9 receipt | September 15, 2026 |
| [output-budget-receipt.md](output-budget-receipt.md) | Configurable output budget — 2026-09-14 | 2026-09-14 |
| [passage-review-receipt.md](passage-review-receipt.md) | Passage review dev7 — receipt | September 15, 2026 |
| [phase5-evaluation-receipt.md](phase5-evaluation-receipt.md) | Phase 5 local evaluation receipt | 2026-09-14 |
| [phase6-pilot-receipt.md](phase6-pilot-receipt.md) | Phase 6 local pilot — complete | 2026-09-14 |
| [plan-build-connected-results.md](plan-build-connected-results.md) | Connected plan/build comparison — September 18, 2026 | September 18, 2026 |
| [plan-build-contract-confirmation-results.md](plan-build-contract-confirmation-results.md) | Plan/build response-contract confirmation — September 18, 2026 | September 18, 2026 |
| [plan-build-contract-correction-results.md](plan-build-contract-correction-results.md) | Task 8 — response-contract repair and local qualification |  |
| [plan-build-default-compatibility-results.md](plan-build-default-compatibility-results.md) | Default-output oracle correction — September 18, 2026 | September 18, 2026 |
| [plan-build-fresh-journey-results.md](plan-build-fresh-journey-results.md) | Fresh journey qualification — September 18, 2026 | September 18, 2026 |
| [plan-build-function-body-replay-results.md](plan-build-function-body-replay-results.md) | Function-body replay — completed without model calls | September 18, 2026 |
| [plan-build-handoff-confirmation-results.md](plan-build-handoff-confirmation-results.md) | Fresh connected confirmation — September 18, 2026 | September 18, 2026 |
| [plan-build-handoff-correction-results.md](plan-build-handoff-correction-results.md) | Connected handoff correction — September 18, 2026 | September 18, 2026 |
| [plan-build-luna-broader-results.md](plan-build-luna-broader-results.md) | Broader Luna trial — stopped and closed | September 18, 2026 |
| [plan-build-native-results.md](plan-build-native-results.md) | Plan/build native role comparison — September 18, 2026 | September 18, 2026 |
| [plan-build-repair-contenders-preparation.md](plan-build-repair-contenders-preparation.md) | Luna/Sol repair comparison — prepared September 18, 2026 | September 18, 2026 |
| [plan-build-repair-contenders-results.md](plan-build-repair-contenders-results.md) | Expanded Luna/Sol repair comparison — September 18, 2026 | September 18, 2026 |
| [plan-build-repair-feedback-results.md](plan-build-repair-feedback-results.md) | Rejected-reply inspection and repair handoff — September 18, 2026 | September 18, 2026 |
| [plan-build-repair-model-preparation.md](plan-build-repair-model-preparation.md) | Repair-worker comparison — prepared September 18, 2026 | September 18, 2026 |
| [plan-build-repair-model-results.md](plan-build-repair-model-results.md) | Repair-worker comparison — September 18, 2026 | September 18, 2026 |
| [plan-build-repair-native-results.md](plan-build-repair-native-results.md) | Guided repair trial — startup failure, September 18, 2026 | September 18, 2026 |
| [plan-build-repair-native-retry-results.md](plan-build-repair-native-retry-results.md) | Native guided repair — unchanged proposal, September 18, 2026 | September 18, 2026 |
| [plan-build-repair-resume-results.md](plan-build-repair-resume-results.md) | Bounded repair and resume qualification — September 18, 2026 | September 18, 2026 |
| [plan-build-routing-eligibility-preparation.md](plan-build-routing-eligibility-preparation.md) | Narrow Luna eligibility — prepared experiment | September 18, 2026 |
| [plan-build-routing-eligibility-results.md](plan-build-routing-eligibility-results.md) | Narrow Luna eligibility — completed pilot | September 18, 2026 |
| [plan-build-routing-filter-opportunities.md](plan-build-routing-filter-opportunities.md) | Python intake filtering: evidence-backed opportunities | September 18, 2026 |
| [plan-build-task1-results.md](plan-build-task1-results.md) | Plan/build Task 1 — concrete journey and baseline ready | 2026-09-17 |
| [plan-build-task6-results.md](plan-build-task6-results.md) | Plan/build Task 6 — steering, controls and Spec |  |
| [plan-build-task7-results.md](plan-build-task7-results.md) | Plan/build Task 7 — installed verbs |  |
| [recovery-workflow-receipt.md](recovery-workflow-receipt.md) | Local Phase 3 recovery receipt — 2026-09-14 | 2026-09-14 |
| [release-readiness-follow-through-results.md](release-readiness-follow-through-results.md) | Release-readiness follow-through — complete | 2026-09-17 |
| [review-quality-receipt.md](review-quality-receipt.md) | Documentation-review quality acceptance — 2026-09-14 | 2026-09-14 |
| [review-workflow-receipt.md](review-workflow-receipt.md) | Local coordinated-review receipt — 2026-09-14 | 2026-09-14 |
| [sol-review-fix-receipt.md](sol-review-fix-receipt.md) | Four Sol review fixes — September 16, 2026 | September 16, 2026 |
| [spec-completion-repair-results.md](spec-completion-repair-results.md) | Spec completion evidence repair — results | 2026-09-17 |
| [spec-test-handoff-results.md](spec-test-handoff-results.md) | Spec test handoff: local correction qualified | 2026-09-17 |
| [status-guidance-a-results.md](status-guidance-a-results.md) | Opportunity A — verified plan/build guidance | September 18, 2026 |
| [test-this-change-results.md](test-this-change-results.md) | Test this change — first slice complete | 2026-09-17 |
| [token-accounting-receipt.md](token-accounting-receipt.md) | Model-aware token accounting — 2026-09-14 | 2026-09-14 |
| [voyage-accuracy-receipt.md](voyage-accuracy-receipt.md) | Voyage focused accuracy check | September 15, 2026 |
| [voyage-retrieval-receipt.md](voyage-retrieval-receipt.md) | Voyage implementation receipt | September 15, 2026 |

### Other documents

| File | Title | Dated |
| --- | --- | --- |
| [architecture-brainstorm-starter.md](architecture-brainstorm-starter.md) | Read before forming conclusions |  |
| [assessment-quality-correction.md](assessment-quality-correction.md) | Assessment correction: bounded comparison passed | 2026-09-17 |
| [astra-review.md](astra-review.md) | Review with GPT-6 Astra at extra-high reasoning |  |
| [communication-grammar-review.md](communication-grammar-review.md) | Human–AI communication grammar: bounded review |  |
| [cross-review-sol-2026-09-16.md](cross-review-sol-2026-09-16.md) | Sol cross-review — September 16, 2026 | September 16, 2026 |
| [documentation-maintenance.md](documentation-maintenance.md) | Documentation content maintenance | September 18, 2026 |
| [fable-review.md](fable-review.md) | Fable and Opus review candidates | September 15, 2026 |
| [harness-api-budget.md](harness-api-budget.md) | Harness Claude API budget | September 15, 2026 |
| [harness-release-readiness-direction.md](harness-release-readiness-direction.md) | Harness release readiness — direction and proposed next step | 2026-09-17 |
| [integrated-rag-architecture.md](integrated-rag-architecture.md) | ADR — Integrated RAG owned by Attune Harness | September 15, 2026 |
| [memory-documentation-journey.md](memory-documentation-journey.md) | Memory documentation journey: local handoff qualified, native sample pending | 2026-09-17 |
| [october-release-plan.md](october-release-plan.md) | October release and complete-journey plan | September 18, 2026 |
| [opportunities-implementation-report.md](opportunities-implementation-report.md) | Attune Harness: opportunities 1–5 implementation report | September 15, 2026 |
| [pilot-migration.md](pilot-migration.md) | Pilot migration decision record |  |
| [pilot-workflow.md](pilot-workflow.md) | Local documentation-review pilot |  |
| [rag-options-research-2026-09-15.md](rag-options-research-2026-09-15.md) | RAG options for Attune Harness | September 15, 2026 |
| [release-journey-map.md](release-journey-map.md) | Harness release journey map | 2026-09-17 |
| [reliability-accuracy-review-2026-09-14.md](reliability-accuracy-review-2026-09-14.md) | Attune Harness reliability and accuracy review | September 14, 2026 |
| [user-guidance-examples.md](user-guidance-examples.md) | Warnings and guidance: concrete examples | September 18, 2026 |
| [verification-checkpoint.md](verification-checkpoint.md) | Verification checkpoint — 2026-09-14 | 2026-09-14 |
| [voyage-100-question-evaluation.md](voyage-100-question-evaluation.md) | Voyage: 100-question Harness evaluation | September 15, 2026 |
| [voyage-answer-accuracy-calibration-2026-09-15.md](voyage-answer-accuracy-calibration-2026-09-15.md) | Voyage answer-accuracy calibration: results and operational limits | September 15, 2026 |
| [voyage-answer-accuracy-preparation.md](voyage-answer-accuracy-preparation.md) | Model-mix answer accuracy experiment — preparation | September 15, 2026 |
| [voyage-full-code-evaluation.md](voyage-full-code-evaluation.md) | Voyage: 98-file Harness evaluation | September 15, 2026 |
| [voyage-latency-assessment-2026-09-15.md](voyage-latency-assessment-2026-09-15.md) | Voyage retrieval latency: measured breakdown | September 15, 2026 |
| [voyage-next-increment-2026-09-15.md](voyage-next-increment-2026-09-15.md) | Voyage retrieval: verified assessment and next increment | September 15, 2026 |
| [voyage-rag-session-starter.md](voyage-rag-session-starter.md) | Starter: evaluate and improve Attune RAG with Voyage AI |  |
| [voyage-retrieval-implementation-plan.md](voyage-retrieval-implementation-plan.md) | Voyage retrieval implementation plan | September 15, 2026 |

### specs/connected-journey-qualification

| File | Title | Dated |
| --- | --- | --- |
| [specs/connected-journey-qualification/assessment-correction-design.md](specs/connected-journey-qualification/assessment-correction-design.md) | Bounded assessment correction, revision 2 | 2026-09-17 |
| [specs/connected-journey-qualification/assessment-quality-design.md](specs/connected-journey-qualification/assessment-quality-design.md) | Bounded assessment-quality comparison | 2026-09-17 |
| [specs/connected-journey-qualification/capability-map.md](specs/connected-journey-qualification/capability-map.md) | Connected capability map — 2026-09-17 | 2026-09-17 |
| [specs/connected-journey-qualification/native-follow-through.md](specs/connected-journey-qualification/native-follow-through.md) | Native qualification: implementation and acceptance schedule |  |

### specs/cross-review

| File | Title | Dated |
| --- | --- | --- |
| [specs/cross-review/receipts.md](specs/cross-review/receipts.md) | Cross-review advisory receipts |  |

### specs/executable-plugins

| File | Title | Dated |
| --- | --- | --- |
| [specs/executable-plugins/README.md](specs/executable-plugins/README.md) | Executable plugins: the spec | 2026-09-23 |

### specs/native-memory

| File | Title | Dated |
| --- | --- | --- |
| [specs/native-memory/scoping.md](specs/native-memory/scoping.md) | Native memory — scoping note | 2026-09-19 |
| [specs/native-memory/task-4-design.md](specs/native-memory/task-4-design.md) | Native memory, Task 4: design note | 2026-09-22 |

### specs/plan-build

| File | Title | Dated |
| --- | --- | --- |
| [specs/plan-build/baseline.md](specs/plan-build/baseline.md) | Plan and build — source assessment | 2026-09-16 |
| [specs/plan-build/contract-correction.md](specs/plan-build/contract-correction.md) | Task 8 — bounded response-contract correction |  |
| [specs/plan-build/control-audit.md](specs/plan-build/control-audit.md) | Control audit — plan and build | 2026-09-16 |
| [specs/plan-build/default-compatibility-correction.md](specs/plan-build/default-compatibility-correction.md) | Preserve captured default output in the experimental oracle |  |
| [specs/plan-build/dependent-build.md](specs/plan-build/dependent-build.md) | Task 5 — dependent feature execution |  |
| [specs/plan-build/design.md](specs/plan-build/design.md) | Design — one work lifecycle behind plan and build |  |
| [specs/plan-build/first-journey.md](specs/plan-build/first-journey.md) | First journey and concrete implementation boundaries |  |
| [specs/plan-build/routing-eligibility-experiment.md](specs/plan-build/routing-eligibility-experiment.md) | Narrow Luna eligibility — experiment design | September 18, 2026 |
| [specs/plan-build/tasks.md](specs/plan-build/tasks.md) | Task outline — plan and build |  |
| [specs/plan-build/work-contract.md](specs/plan-build/work-contract.md) | Task 2 — shared work contract |  |

### specs/shared-memory-adoption

| File | Title | Dated |
| --- | --- | --- |
| [specs/shared-memory-adoption/adapter-design.md](specs/shared-memory-adoption/adapter-design.md) | Current-memory adapter implementation note |  |
| [specs/shared-memory-adoption/baseline.md](specs/shared-memory-adoption/baseline.md) | Existing memory compatibility baseline |  |
| [specs/shared-memory-adoption/design.md](specs/shared-memory-adoption/design.md) | Shared memory adoption — design | 2026-09-17 |
| [specs/shared-memory-adoption/requirements.md](specs/shared-memory-adoption/requirements.md) | Shared memory adoption | 2026-09-17 |
| [specs/shared-memory-adoption/task3-review.md](specs/shared-memory-adoption/task3-review.md) | Task 3 review disposition | 2026-09-17 |
| [specs/shared-memory-adoption/task4-gate.md](specs/shared-memory-adoption/task4-gate.md) | Historical Task 4 gate — superseded |  |
| [specs/shared-memory-adoption/verification.md](specs/shared-memory-adoption/verification.md) | Shared memory adoption — verification and support | 2026-09-17 |

### specs/spec-authority

| File | Title | Dated |
| --- | --- | --- |
| [specs/spec-authority/task-3-design.md](specs/spec-authority/task-3-design.md) | Spec authority, Task 3: design note | 2026-09-22 |
| [specs/spec-authority/task-4-design.md](specs/spec-authority/task-4-design.md) | Spec authority, Task 4: design note | 2026-09-23 |

### specs/unified-task-execution

| File | Title | Dated |
| --- | --- | --- |
| [specs/unified-task-execution/assessment-receipt.md](specs/unified-task-execution/assessment-receipt.md) | Installed assessment software qualification |  |
| [specs/unified-task-execution/repair-receipt.md](specs/unified-task-execution/repair-receipt.md) | Repair software qualification — Task 7 |  |
| [specs/unified-task-execution/task-8-assistant-grading.md](specs/unified-task-execution/task-8-assistant-grading.md) | Task 8 assistant outcome grading |  |
| [specs/unified-task-execution/task-8-grading-guide.md](specs/unified-task-execution/task-8-grading-guide.md) | Task 8 human grading |  |
| [specs/unified-task-execution/task-8-live-receipt.md](specs/unified-task-execution/task-8-live-receipt.md) | Task 8 native qualification receipt | September 16, 2026 |
| [specs/unified-task-execution/task-8-review-contract-note.md](specs/unified-task-execution/task-8-review-contract-note.md) | Task 8 correction note — review findings semantics |  |

### specs/voyage-validation-reuse

| File | Title | Dated |
| --- | --- | --- |
| [specs/voyage-validation-reuse/design.md](specs/voyage-validation-reuse/design.md) | Design: reuse the immediately checked generation |  |
| [specs/voyage-validation-reuse/tasks.md](specs/voyage-validation-reuse/tasks.md) | Voyage validation reuse — task ladder |  |

### blog/

| File | Title | Dated |
| --- | --- | --- |
| [blog/controls-savings-user-journey.md](blog/controls-savings-user-journey.md) | What better controls can save in an AI workflow | September 18, 2026 |

### handoffs/

Session handoffs and starters, kept as written. The directory is ignored on
`main` since O-43 closed; these files were added by name.

| File | Title | Dated |
| --- | --- | --- |
| [handoffs/2026-09-22-autonomous-run.md](handoffs/2026-09-22-autonomous-run.md) | Handoff: autonomous run of September 22, 2026 | 2026-09-22 |
| [handoffs/README-draft-0.1.0.md](handoffs/README-draft-0.1.0.md) | README draft for 0.1.0 (historical) |  |
| [handoffs/README-independence-wording-draft-2026-09-21.md](handoffs/README-independence-wording-draft-2026-09-21.md) | Draft: README independence wording, corrected | 2026-09-21 |
| [handoffs/archive/shared-memory-before-bounded-review.md](handoffs/archive/shared-memory-before-bounded-review.md) | Shared memory adoption handoff (archived) |  |
| [handoffs/codex-update-session-starter.md](handoffs/codex-update-session-starter.md) | Completed: next bounded assessment correction |  |
| [handoffs/first-pypi-release-2026-09-19.md](handoffs/first-pypi-release-2026-09-19.md) | Handoff: attune-harness first PyPI release | 2026-09-19 |
| [handoffs/function-body-controls-e.md](handoffs/function-body-controls-e.md) | Item E — implementation handoff |  |
| [handoffs/release-0.1.0-windows-fix-2026-09-21.md](handoffs/release-0.1.0-windows-fix-2026-09-21.md) | Handoff: attune-harness 0.1.0, Windows record-replace fix, then release | 2026-09-21 |
| [handoffs/session-starter-2026-09-19.md](handoffs/session-starter-2026-09-19.md) | Session starter: attune-harness, after 2026-09-19 | 2026-09-19 |
| [handoffs/session-starter-cut-attune-ai-dependency-2026-09-21.md](handoffs/session-starter-cut-attune-ai-dependency-2026-09-21.md) | Session starter: make attune-harness run without attune-ai | 2026-09-21 |
| [handoffs/smartaimemory-controls-article.md](handoffs/smartaimemory-controls-article.md) | Website integration: controls article and supporting examples |  |
| [handoffs/spec-test-handoff-review.md](handoffs/spec-test-handoff-review.md) | Local review of Spec evidence handoff |  |
| [handoffs/status-guidance-a.md](handoffs/status-guidance-a.md) | Implement A — plan/build status and next-action guidance |  |

### receipts/

| File | Title | Dated |
| --- | --- | --- |
| [receipts/phase5/e1-run-02/26/project/guide.md](receipts/phase5/e1-run-02/26/project/guide.md) | docs/receipts/phase5/e1-run-02/26/project/guide.md |  |
| [receipts/phase5/e1-run-02/26/project/reference.md](receipts/phase5/e1-run-02/26/project/reference.md) | docs/receipts/phase5/e1-run-02/26/project/reference.md |  |

### reflections/

| File | Title | Dated |
| --- | --- | --- |
| [reflections/connected-journey-qualification-2026-09-17.md](reflections/connected-journey-qualification-2026-09-17.md) | Connected journey reflection — 2026-09-17 | 2026-09-17 |
| [reflections/session-2026-09-17/kept.md](reflections/session-2026-09-17/kept.md) | Kept session insights — 2026-09-17 | 2026-09-17 |
| [reflections/session-2026-09-17/review-revision-1.md](reflections/session-2026-09-17/review-revision-1.md) | Reflect — Attune session, September 16–17 | 2026-09-17 |
| [reflections/session-2026-09-17/review.md](reflections/session-2026-09-17/review.md) | Reflection review — revision 2 | 2026-09-17 |

### research/

| File | Title | Dated |
| --- | --- | --- |
| [research/control-and-latency-2026-09-16.md](research/control-and-latency-2026-09-16.md) | Control reliability and time to useful output | 2026-09-16 |
| [research/form-visibility-2026-09-17.md](research/form-visibility-2026-09-17.md) | Native question visibility investigation — 2026-09-17 | 2026-09-17 |
| [research/luna-stage-contract-results-2026-09-16.md](research/luna-stage-contract-results-2026-09-16.md) | Luna stage contracts and memory fidelity | 2026-09-16 |
| [research/luna-voyage-follow-up-2026-09-16.md](research/luna-voyage-follow-up-2026-09-16.md) | Luna, Voyage and reliable memory work | 2026-09-16 |
| [research/memory-citations-results-2026-09-16.md](research/memory-citations-results-2026-09-16.md) | Memory citation-contract repair results | 2026-09-16 |
| [research/memory-journey-results-2026-09-16.md](research/memory-journey-results-2026-09-16.md) | Luna memory journey: isolated real storage |  |
| [research/memory-routing-results-2026-09-16.md](research/memory-routing-results-2026-09-16.md) | Memory authoring and routing experiments | 2026-09-16 |
| [research/memory-routing-v2-results-2026-09-16.md](research/memory-routing-v2-results-2026-09-16.md) | Revised memory controls and routing results | 2026-09-16 |
| [research/memory-sorter-results-2026-09-16.md](research/memory-sorter-results-2026-09-16.md) | Mixed-queue memory sorter results | 2026-09-16 |
| [research/memory-worker-results-2026-09-16.md](research/memory-worker-results-2026-09-16.md) | Bounded memory-worker prototype | 2026-09-16 |
