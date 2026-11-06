# Approved comparison decisions

**Status: Patrick approved D1–D6 on November 6, 2026.** He also selected T1's
offline fixture and controls, explicitly excluding live model calls. T2–T4,
live eligibility, funding/budget and publication remain separate decisions.
See [requirements](README.md#requirements-and-acceptance).

| ID | Approved decision | Alternative and tradeoff |
| --- | --- | --- |
| D1 | Compare five scenarios across H/S/N on one macOS arm64 machine. Qualify offline first; reserve 15 assigned live attempts for a separately authorized exploratory pilot. | A larger repeated campaign could estimate reliability but needs a sample-size rationale and substantially more collection. A single polished demo could hide failures. |
| D2 | Pin Harness 1.7.0, Superpowers 7.0.2 commit `22f0b463e7a5e579904dd6211a520321035526f7`, and Claude Code 2.1.318. Use SDD for S and ordinary subagents for N. Match explicit lead permissions and available sandbox policy. | Latest-floating installs are easier but invalidate attribution. Adding experimental agent teams or inline Superpowers execution creates additional conditions and requires its own frozen scope. |
| D3 | Compare product workflows with a common task, declared scope and external verdict, preserving normal product controls and exposing differences. | Forcing identical internal tool envelopes would remove the mechanisms under comparison. Independently optimizing every configuration would answer a different question and introduce tuning effort. |
| D4 | Score prevention, detection, mutation, human intervention and recovery independently; no weighted winner score. Unexercised challenges and missing observations stay explicit. | A single pass percentage is easier to market but obscures whether the product, person or observer caught a violation. |
| D5 | Keep settled pause and abrupt check-in-flight interruption separate. Require matched trigger evidence and confirmed process stop; preserve safe unresolved outcomes. | A generic interrupt/resume case is simpler but confuses graceful checkpoints, conversation persistence, uncertain external work and rollback. |
| D6 | Limit this spec to new experiment fixtures, collection/scoring adapters and a report. Approval can select offline tasks independently. Live eligibility/model/funding/budget and publication remain separate gates. | Folding in product repairs would change the comparison baseline and widen the task. Fixes found by the study should be separately scoped and evaluated in a new campaign. |

## Values required before live authorization

The implementation must bring a concrete campaign manifest back for review:

- Exact principal/subagent model IDs, role assignments, exposed settings and
  provider/account route; evidence that every arm can use them.
- Installed Harness wheel hash, host integration identity, Superpowers resolved
  commit, Claude binary hash, OS and Python identities. A future version change
  needs a new manifest rather than relabeling this proposed baseline.
- Effective permission/sandbox/settings profiles, clean trial-profile locations,
  plugin inventory, active roots, native session persistence and updater state.
- Concrete fixture/oracle/attachment hashes, observer/controller commands, C3/C4
  admissibility receipts, scenario order/seed and trial locators.
- Spending ceiling covering setup, practice, all 15 attempts, reviewers, failed
  calls and retries; timeout/quota/unknown-billing stop policy and approval
  reference. Existing subscription access does not establish free extra usage.
- Named operator, permitted assistance, redaction/retention locations and report
  review plan. No human subject or customer dataset is included by implication.

No model/provider or account has been selected for live work by this document.
Before making that selection, consult applicable approved private project policy
through an authorized access path. Missing applicable policy blocks the affected
selection/spending action, not offline drafting or fixture work.

## Rejected premises

- “Only Harness has gates or durable state.” Superpowers includes helpers and
  saved ledgers; native Claude provides enforceable permissions and checkpoints.
- “An invalid proposal proves shell isolation.” Harness's trusted effects
  profile does not supply an OS sandbox.
- “A clean pause proves crash recovery.” Completed operation checkpoints and
  uncertain in-flight operations have different refusal conditions.
- “The observer caught it, so the product prevented it.” Detection and
  attribution must remain separate.
- “15 attempts establish a reliability advantage.” They are a bounded exploratory
  comparison and can expose mechanisms or gaps, not a stable population rate.
