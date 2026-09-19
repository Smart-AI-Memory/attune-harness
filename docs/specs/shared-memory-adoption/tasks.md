# Shared memory adoption — task ladder

Status: plan approved on 2026-09-17. **All five tasks accepted; 5/5 complete at canonical revision 23. Live activation and release remain outside this plan.** XML plan: `.claude/plans/shared-memory-adoption.md`.

| Task | Result | Required evidence |
|---|---|---|
| 1 | Baseline existing memories and preserve their useful behavior | Legacy-format content/recall fixtures, service/caller capability map, explicit roots and no live effects |
| 2 | Extract one shared contract and worker into Harness | No experimental imports, repaired semantics, failure-sensitive routing/state tests, dependency-free core |
| 3 | Add current-memory readers and qualified service mutations | Real disposable service round trips, security before dispatch/effects, legacy-writer and uncertain-write behavior |
| 4 | Expose both entry points and refresh receiving-agent context | Both hosts consume one core; relevant full-source resolution and correction/deletion refresh; no loss of existing paths |
| 5 | Qualify installed artifacts and publish the support matrix | Installed outside-tree consumers, regression/mutation receipts, platform limits, rollback and separate native evidence |

Tasks are sequential when they consume the previous contract. Task 1 starts from
the actual existing interfaces; it must not assume only notes matter. Native
trials and live activation do not start merely because an offline task passes.
The design names actual inspected seams and proposed new modules, not implemented
capabilities. The final matrix must distinguish what still uses its existing path
from what the new worker can safely manage.

Task 1 maps telemetry emitters and consumers by purpose. Task 4 preserves useful
local signals and verifies no usage uploads from the new route through shutdown,
including a legacy upload opt-in setting. Product-wide uploader and hosted
collector retirement are tracked separately from this integration.

Read requirements.md, design.md and decisions.md together. The chair's accepted
adoption direction is preserved; Patrick approved the implementation plan and acknowledged the packaging
receipts at both lifecycle boundaries. Live activation and release remain outside
that approval; task acceptance follows the existing spec workflow.
