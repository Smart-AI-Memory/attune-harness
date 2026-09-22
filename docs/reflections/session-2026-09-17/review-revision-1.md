# Reflect — Attune session, September 16–17

Revision 1 · All candidates unreviewed

**My assessment:** The strongest progress came from separating model reasoning from responsibilities the host should enforce. The useful result is a clearer route to preserving memory and using less expensive workers, with the operational limits still visible.

**Coverage:** User messages visible in this conversation, a compacted summary of earlier assistant/tool work, and the linked local receipts. Earlier assistant turns were not audited as a complete verbatim transcript. This is a bounded reflection, not an exhaustive inventory of every insight. No separate model campaign or external research was run for this reflection.

**Review form:** Choose **Keep / Edit / Revisit / Discard** for any item. No action is preselected. Unanswered items stay unreviewed. Keep saves the exact claim below to its displayed destination, or records its existing saved reference; it does not approve a proposal, start an experiment, release software, or change a prior decision. Edit requires replacement wording, which will be shown again before saving. Revisit creates no reminder. Discard affects only this proposed collection.

Short replies work: `keep 1, 3, 6; revisit 7; edit 9: <replacement wording>`. An explicit `keep all` selects all nine exact claims. Partial rulings apply only to named items.

## Candidates

### 1. Preserve memories as a core product asset

**Category:** Decisions · **Disposition:** Unreviewed

**Claim to keep:** Patrick values accumulated memories as one of Attune’s most useful features. Harness adoption must preserve their content and useful behavior, begin with compatible access to existing stores, and qualify new operations individually; it does not authorize a migration or rewriting the corpus.

**Source:** Patrick: “I consider the memories one of the most useful features and I value them a lot.” Shared-memory decisions D1–D3, D6. [Open source](https://github.com/Smart-AI-Memory/attune-harness/blob/c8b3235/docs/specs/shared-memory-adoption/decisions.md).

**Basis:** Explicit user preference and accepted shared-memory decision.

**Why it matters:** Makes preservation part of acceptance, rather than a cleanup task after integration.

**Keep destination:** [kept.md](kept.md) (created only after Keep).

**Existing status:** Already represented in the approved spec; Keep adds this synthesis to the selected session collection.

**Choose:** Keep · Edit · Revisit · Discard

### 2. Let people author intent and control consequential gates

**Category:** Decisions · **Disposition:** Unreviewed

**Claim to keep:** For complex work, specs are the principal human authoring surface. Use a clear one-shot prompt or XML-enhanced prompt when appropriate; people may still intervene with verbs. Human decisions, hooks and host controls serve different roles and must be assessed for actual reliability rather than assumed interchangeable.

**Source:** Patrick: “the principal authoring for more complex constructs or features will be the spec”; “Humans can intercede using the verb commands too.” [Open source](../../design-navigation.md).

**Basis:** Explicit user direction; reliability distinction is the assistant’s synthesis, not a claim that all proposed controls are implemented.

**Why it matters:** Avoids forcing people to learn the full internal command catalog while retaining control.

**Keep destination:** [kept.md](kept.md) (created only after Keep).

**Existing status:** Direction documented; automatic authoring-form selection remains unqualified.

**Choose:** Keep · Edit · Revisit · Discard

### 3. Repair interface defects before paying for stronger reasoning

**Category:** Lessons and patterns · **Disposition:** Unreviewed

**Claim to keep:** When a worker’s answer is semantically correct but fails the host contract, inspect the schema, citation requirements and ownership of control metadata before adding a stronger router. The host should own version binding and validate authority and evidence. In this session, citation-contract repair allowed Luna to pass all eight fresh cases without escalation; this bounded result does not establish production savings.

**Source:** The original mixed trial used ten Astra calls to repair metadata; the paired citation repair passed eight fresh cases without escalation. [Open source](../../research/memory-citations-results-2026-09-16.md).

**Basis:** Observed experimental result plus a proposed general lesson.

**Why it matters:** Addresses the cause of avoidable escalation while preserving validation.

**Keep destination:** [lesson_interface_defects_before_model_escalation.md](/Users/patrickroebuck/.claude/memory/lesson_interface_defects_before_model_escalation.md).

**Existing status:** New cross-project lesson proposed; no memory write yet.

**Choose:** Keep · Edit · Revisit · Discard

### 4. Use Luna routinely, with explicit escalation and sampled review

**Category:** Decisions · **Disposition:** Unreviewed

**Claim to keep:** Keep Luna as the sorter and routine-worker candidate. Route known difficult work directly to a stronger model; use explicit host rules and sampled semantic review to catch confident mistakes. Distinguish missing evidence and pending user decisions from reasoning failures. Stronger agents should receive original relevant evidence when needed, without repeating every successful routine task.

**Source:** Patrick approved: “Keep Luna as the sorter and routine-worker candidate, with explicit host routing rules and sampled semantic review.” [Open source](https://github.com/Smart-AI-Memory/attune-harness/blob/c8b3235/docs/specs/shared-memory-adoption/decisions.md).

**Basis:** Accepted routing direction; live product delegation remains unqualified.

**Why it matters:** Makes delegation savings testable instead of adding a second model to every job.

**Keep destination:** [kept.md](kept.md) (created only after Keep).

**Existing status:** The existing global delegation memory uses earlier provider-specific guidance. This candidate records the accepted memory-worker direction without silently changing general delegation rules.

**Choose:** Keep · Edit · Revisit · Discard

### 5. Separate usage collection from team operations

**Category:** Decisions · **Disposition:** Unreviewed

**Claim to keep:** Disable unwanted product-usage collection while preserving useful local accounting and explicitly configured team coordination, shared memory and operational reporting. Patrick’s final choice A supersedes the briefly selected entirely-offline option. A team feature that reuses the legacy usage uploader needs its purpose and destination separated before support is claimed.

**Source:** Patrick reopened the A/B form and then replied: “A that’s acceptable.” Decision D9 records the supersession. [Open source](https://github.com/Smart-AI-Memory/attune-harness/blob/c8b3235/docs/specs/shared-memory-adoption/decisions.md).

**Basis:** Explicit final user decision, including its correction history.

**Why it matters:** Prevents a privacy improvement from accidentally disabling collaboration.

**Keep destination:** [kept.md](kept.md) (created only after Keep).

**Existing status:** Already recorded as D9; this is a reflection candidate, not a request to approve it again.

**Choose:** Keep · Edit · Revisit · Discard

### 6. Treat the third review pass as a checkpoint

**Category:** Lessons and patterns · **Disposition:** Unreviewed

**Claim to keep:** Three review rounds are a default checkpoint, not an absolute prohibition on progress. Surface a concrete remaining question, the bounded additional check that could resolve it, and a stopping condition. Patrick is willing to extend when useful; this is not unlimited review authorization. Task 3’s focused timestamp recheck demonstrated the approach.

**Source:** Patrick: “I am willing to lift the 3 pass rule when there is an opportunity to progress. I like it when you point out opportunities too.” [Open source](/Users/patrickroebuck/.claude/memory/feedback_lane_cadence_cap_and_early_stop.md).

**Basis:** Explicit user clarification and observed verification closure.

**Why it matters:** Avoids accepting a preventable evidence gap solely because a round counter was reached.

**Keep destination:** [feedback_lane_cadence_cap_and_early_stop.md](/Users/patrickroebuck/.claude/memory/feedback_lane_cadence_cap_and_early_stop.md).

**Existing status:** Already saved in this exact global memory; Keep records its existing reference without duplicating it.

**Choose:** Keep · Edit · Revisit · Discard

### 7. Measure the wait users actually experience

**Category:** Opportunities · **Disposition:** Unreviewed

**Claim to keep:** Measure request-to-visible-form and display persistence across preparation, model, transport and rendering phases. Local construction medians of about 2.08 ms cold and 1.84 ms cached do not explain the user’s wait or disappearing forms. Preserve the existing grammar and use a persistent readable fallback when the native form cannot be seen. Compare controlled end-to-end trials before attributing a UX improvement to caching.

**Source:** Patrick reported forms disappearing or not appearing. The latest located Codex request-to-visible observation was about 6.5 seconds in one September 7 trial. [Open source](/Users/patrickroebuck/attune-harness/docs/receipts/unified-task-execution/task2-intake-timing-final/summary.json).

**Basis:** Proposed experiment informed by local receipts and Patrick’s reports; no root cause established.

**Why it matters:** Targets the actual latency and availability problem. Counter-case: persistent fallbacks and lifecycle measurements require work beyond a renderer microbenchmark.

**Keep destination:** [kept.md](kept.md) (created only after Keep).

**Existing status:** Opportunity only; Keep does not launch the experiment.

**Choose:** Keep · Edit · Revisit · Discard

### 8. Do not equate experimental success with live adoption

**Category:** Pushback · **Disposition:** Unreviewed

**Claim to keep:** The repaired Luna contract has encouraging receipts, but those do not prove live memory management is ready. Keep separate claims for experimental behavior, shared-core implementation, installed integration, native participant qualification and activation. Finish Tasks 4–5 and the support matrix before representing this route as adopted operationally. The counter-case is slower rollout; the benefit is exposing unsupported operations before they affect valued memories.

**Source:** Patrick’s approved boundary explicitly leaves concurrency/deletion, adapter taxonomy, security classification, context refresh, representative performance and active-lead delegation for integration qualification. [Open source](https://github.com/Smart-AI-Memory/attune-harness/blob/c8b3235/docs/specs/shared-memory-adoption/tasks.md).

**Basis:** Assistant pushback grounded in the accepted integration boundary.

**Why it matters:** Prevents a successful small experiment from carrying an unsupported production claim.

**Keep destination:** [kept.md](kept.md) (created only after Keep).

**Existing status:** Tasks 1–3 accepted; Task 4 remains unaccepted. Its independent review did not complete.

**Choose:** Keep · Edit · Revisit · Discard

### 9. Prioritize the Harness transition without declaring Attune AI retired

**Category:** Decisions and open questions · **Disposition:** Unreviewed

**Claim to keep:** Prioritize documented Harness release blockers first, then work benefiting both products, then Harness-only work, then optional Attune AI-only enhancements. Patrick is leaning toward deprecating Attune AI and releasing Harness; that leaning is not a final deprecation or release decision. Shared memory adoption preserves value while that direction develops.

**Source:** Patrick: “a documented Harness release blocker should outrank an optional shared enhancement—agreed”; “I’m leaning toward deprecating attune-ai”.

**Basis:** Accepted priority order plus an explicitly unsettled product decision.

**Why it matters:** Keeps effort aligned with the likely product direction without inventing a retirement decision.

**Keep destination:** [kept.md](kept.md) (created only after Keep).

**Existing status:** User statements are present in the visible conversation; no deprecation action is authorized by this candidate.

**Choose:** Keep · Edit · Revisit · Discard

## Current work and evidence limits

Tasks 1–3 are accepted. Task 4 remains in progress. Its independent reviewer failed to complete because its request received an automated safety refusal; no review findings or approval were returned. The failed attempt must not count as a completed review. The scheduled continuation can still do unaffected verification within its existing authority; it must not bypass that refusal or advance the acceptance gate without the required evidence.

Task 5 has not started. Overnight continuation remains authorized within the approved plan. Live activation, release, migration and new provider campaigns remain outside that approval.

## Presentation receipt

The attempt to use the forms connector was rejected by automatic approval review because it would send session details and local paths to an unverified destination. No successful connector render is claimed. This local Markdown document is the portable review form; no disposition was submitted or memory saved by creating it.
