# Unified task execution

Status: revised spec approved by Patrick Roebuck, 2026-09-16, including design, validation, the eight-task review/fix plan and the session-reflection extension. **Task 1 accepted on offline evidence; 1/8 tasks accepted. Task 2 intake implementation awaits acceptance.** Execution was explicitly authorized. Owner: attune-harness.

Give Harness one task request and durable identity across intake, evidence, participants, integration, inspection, and recovery. First deliver evidence assessment through explicit solo and independent-review plans. Then deliver scoped repair through the same services, with real file effects and independent acceptance checks.

| Document | Purpose |
|---|---|
| [Requirements](requirements.md) | Approved R1–R14: scope, acceptance criteria, and source-verified premises |
| [Design](design.md) | Task contract, shared orchestration, integration, effects, and compatibility |
| [Decisions](decisions.md) | User instructions versus proposed implementation choices |
| [Task ladder](tasks.md) | Eight bounded implementation units and dependencies |
| [Validation plan](validation.md) | Failure-sensitive cases, provider qualification, and frozen comparisons |
| [Authoring receipt](authoring-receipt.md) | Actual draft checks, lifecycle receipts, and review state |
| [Task 1 baseline](baseline.md) | Actual compatibility, recovery, source identity and intake-timing evidence |
| [Task 2 intake](task-2-receipt.md) | Versioned intake, form reuse, checks and limitations |
| [Session reflection](session-reflection.md) | Approved reflect design and reusable insight form; follow-on slice outside the current eight tasks |
| [XML plan](../../../.claude/plans/unified-task-execution.md) | Canonical machine-readable tasks and saved execution state |

The two slices have separate acceptance records. Evidence assessment cannot establish repair correctness. Software/fixture qualification cannot establish native-provider quality. Neither a spec gate nor a model's completion message accepts implementation.

The [intake design](design.md#fast-intake-and-bounded-reuse) includes bounded form caching, reuse of still-valid answers, and completed-response replay. Cold/warm/bypassed measurements must establish any latency benefit; cached answers do not supply approval and independent reviewers do not share judgments.

Patrick agreed the task vocabulary **plan, build, fix, review, ship**. These slices deliver **review** and **fix** with proposed status/resume supporting controls. They share the task engine; `run` is no longer the primary user verb. Plan/build/ship await their supported journeys. All 18 existing commands remain callable. A new setup hierarchy is deferred; existing index, extension, and protocol commands already preserve those operations.

Background: [Harness command assessment](../../harness-command-consolidation-assessment-2026-09-16.md), [portable contract](../../portable-contract.md), and [phased plan](../../harness-phased-plan.md). This spec owns the two stated task journeys, not the entire Harness roadmap.

Before implementation, refresh source and in-flight work. The unrelated [Voyage validation reuse](../voyage-validation-reuse/requirements.md) ladder is already active; this spec consumes retrieval through its public interfaces and does not take ownership of that change.
