# Disposable memory fidelity and routing experiments

2026-09-16. Patrick authorized the next experiments after discussing Luna memory
management, stronger-agent escalation and shared memory access. This is bounded
research, not production routing, a memory migration or plan/build execution.

Prior evidence: the eight-call stage-contract trial passed every shape check but
produced one unsupported memory claim and one ambiguous cost qualifier. Its
frozen sources and receipts remain unchanged. Design note precedes this prototype.

## A. Source-preserving memory updates

Four fresh synthetic cases: an explicit replacement with an unchanged exception;
a tentative suggestion; unresolved conflicting decisions; and a correction that
applies to only one of two project scopes. Compare Luna/high whole-record rewrite
with source-selected replacements, one call per arm/case, alternating order.
Eight calls maximum. Same inputs, task and expected meaning; contract differs.

The replacement arm chooses target fact IDs and supplied source-statement IDs;
the host copies those statements exactly and preserves untouched facts. The
rewrite arm supplies the complete resulting record with provenance. This is a
comparison of complete authoring methods, not schemas alone. Both must deliver
equivalent memory meaning. Selecting a real source can still be semantically
wrong; source binding is not a correctness oracle. New fact creation/deletion,
arbitrary paraphrase and production storage are outside this extractive probe.

Both arms can return update, no_change or needs_review. The latter means evidence
does not support a settled update; in this isolated comparison it ends the trial.
Inputs include a record version; host guards reject mismatched versions, unknown
or duplicate fact/source IDs, scope changes and malformed or empty updates.
The current version is fixed for live cases; stale races are tested offline.

## B. Routing and completed work

Three fresh tasks: an explicit routine replacement; a conflict already marked
by intake; and an unflagged conflict requiring examination of source content.
All use the replacement contract and identical evidence for worker invocations.
Run three independent arms per case with rotated order:

1. Direct Astra/xhigh execution.
2. Host rules: known conflict, scope change or an unsupported operation goes to
   Astra; otherwise Luna/high. No access to private case answers.
3. Astra/xhigh routes after reading the evidence, then the selected model executes.

In either routed arm, a Luna needs_review response or rejected contract triggers
one Astra execution on the original evidence plus Luna's retained attempt and
failure reason. The added handoff is recorded, not treated as an identical prompt
comparison. Astra cannot bounce the task back. An Astra needs_review disposition
ends unresolved for human judgment; it can be the correct outcome. A failed native
transport stops the entire campaign; it does not silently trigger another model.

Base dispatches: 12. At most six additional escalations: 18 maximum for B and 26
for the full campaign. Compare routing-policy deviations, safe abstention,
final correctness, input/output usage and total process time for
all calls in each arm. A failed routed answer cannot count as a cheap success.
No sample audit runs inside these tiny arms: all final answers receive post-run
lead grading, outside reported automated-path costs. Production sampling remains
unqualified. Stronger routing is not assumed to be correct.

The reference policy sends unresolved conflicts to Astra, but this is a policy
label, not proof that Astra is needed or can resolve absent evidence. Grade safe
Luna abstention separately from compliance with that routing policy. Report any
second call that merely reconfirms unresolved evidence. This deliberately
conflict-heavy mix does not represent ordinary workload frequencies or savings.

Already-active lead delegation needs a real foreground workload and session
continuation, so do not simulate its cost by declaring a new Astra call free.
This campaign measures background routing; active-lead economics remain open.

## Execution, evidence and grading

Use existing Codex ChatGPT subscription, CLI 0.153.4 profile reused from the prior
experiment, with fresh temporary directories and native stage schemas. No Voyage
or Anthropic calls, direct API billing, new credentials or live memory writes.
Bound each call to min(180 seconds, remaining campaign time), with a 1,800-second
campaign deadline including active calls;
no automatic retry, fallback or resumption. Persist dispatch intent and every raw
reply, diagnostics, usage, prompt and schema. Exclusive ledger prevents rerunning.
Stop on unknown native errors, unexpected tool events, missing usage, ambiguous
distinct messages, process failure or timeout. Count CLI dispatches, not hidden
internal HTTP requests. Requested model identity is not independently attested.

Freeze source hashes, cases, schedule, model settings and rubric before dispatch.
Validate guards and controller failure paths offline first, using the previous
unsupported-claim output as a regression, not a scored fresh case. Review design
and code before freeze. Disposable code may import frozen prior transport/parser
helpers; it must not modify them or the product runtime.

Grade each final record against original sources: correct disposition, intended
change, preserved exceptions/scopes, no fabricated rationale, and explicit
uncertainty when decisions conflict. Private case expectations never enter model
prompts. Report field checks separately from unblinded lead semantic grades.
Ambiguous grades stay ambiguous. This small sample can expose failures and show
operational feasibility, not estimate general reliability or select a production
winner. No invented percentage target; no destructive memory action is executed.

Rejected: confidence-only routing; type-only routing; Luna summaries as the sole
evidence supplied to Astra; reusing worker outcomes across arms as measured total
latency; silently repairing failed responses; stronger review on every routine
production operation; adding a paid Haiku comparison without the required spend
authorization. The shared-store/context-refresh behavior gets an offline version
probe here; no retrieval-quality or full memory-feature integration claim.
