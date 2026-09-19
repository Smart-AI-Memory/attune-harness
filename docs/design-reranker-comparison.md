# Reranker comparison — execution preparation

September 16, 2026. Patrick's “go” follows the proposal to compare rerank-2.5
and rerank-2.5-lite. This authorizes preparing the evaluator and its concrete
run packet. The first estimated paid-call approval remains outstanding.

## First study and limits

Run both models on all 100 **historical, already frozen** candidate pools from
the September 15 retrieval evaluation. This is a retrospective paired diagnostic,
not the fresh development/validation study proposed for eventual promotion.
It avoids index changes and new embedding calls, isolates reranking, and retains
all 80 answerable cases and 20 missing-answer controls rather than selecting
favorable cases. A fresh validation set remains required before a default switch.

Freeze original ordered candidate passages, queries, expected evidence, source
generation and study criteria before requests. Verify original publication and
database integrity without pretending that the historical index is fresh against
the current working tree. Do not rewrite or refresh the historical campaign.
Alternate model order per case, so each model runs first 50 times; repeat neither
completed nor uncertain requests. Keep k=10, score prefixes at 5 and 10, and
preserve candidate count and input text across both models.

## Cases and implementation

The evaluator is an isolated experiment, not a production profile change.
Model IDs, request text, source snapshot, code hashes, rate snapshot and call/cost
limits are bound into the packet digest. Exact request identity includes model.
The normal invocation is read-only preflight. Live dispatch requires an explicit
permission flag and that exact packet digest.

Use the existing bounded Voyage transport (no automatic retries/redirects) with
an experiment adapter that supplies the selected model. Use RunStore's exclusive
writer lease and atomic, synced receipts. Record pending before each API call;
any exception or missing usage stops the campaign. Pending/failed effects never
retry automatically. A completed final study can be inspected without new calls.
Known completed results retain model-specific token and cost accounting.

The receipt reports all failed/unrun operations. Provider time and evaluator wall
time are separate; neither is production end-to-end search latency. Cases with
no oracle evidence measure returned candidates, not correct abstention. Same
passage text at both models does not establish answer support.

## Validation before live dispatch

- Behavioral tests detect packet or code tampering, changed candidate text/order,
  wrong digest, absent permission and output overwrite before any provider call.
- A fake provider proves both models receive identical candidate text in the
  frozen order, model-specific costs are correct, and missing usage is unknown.
- Timeout, invalid ranking, KeyboardInterrupt, pending receipt and persistence
  failure prevent further dispatch or automatic retry.
- Scorer probes reject partial spans/wrong files and require all evidence in a
  bundle; duplicate passages cannot inflate completeness. Missing answers are
  not treated as zero-quality or successful abstention.
- Real CLI subprocess tests prove incomplete runs exit nonzero and preflight
  makes zero calls. All 468 historical files retain their original hashes.

The previous latency work verified the immutable historical campaign's artifact
hashes. This study will verify its candidate/oracle bindings separately. No live
results exist at design time.

## Rejected alternatives

Changing the global production PROFILE to lite would change generation identity
and misprice its receipts; use an isolated model-aware evaluator. Calling lite
only and comparing its present latency with yesterday's baseline would confound
model and time; run both models now. Calling the old corpus “held out” would
misrepresent known evidence; label this study retrospective.
