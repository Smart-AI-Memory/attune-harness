# Voyage focused accuracy check

September 15, 2026. **Completed: eight live requests, no failures.**
Installed Harness `0.1.0.dev12`, `voyage-code-4`, standard `rerank-2.5`.
The test reused the existing 43-passage index over five selected Harness files.
It made no new indexing calls and preserved the original rate-limited smoke run.

## Result

Voyage reranking returned the correct supporting passage first for **3/3
answerable questions**. All returned passages passed source hash and exact-byte
checks. Independent local execution also confirmed each expected behavior.

The following ranks measure the first passage overlapping the expected function.
The rank-1 reranked passage also contained the actual code needed to answer each
question, rather than merely mentioning the function.

| Question | Plain text search | Hybrid search | Hybrid + Voyage rerank |
|---|---:|---:|---:|
| Refuse repeated work when prior effects are unknown | 1 | 1 | 1 |
| Reject an incomplete GitHub check export | 1 | 2 | 1 |
| Enforce a child-process deadline | 2 | 2 | 1 |

All three methods retrieved the complete supporting code within their top five
results on all three questions. Reranking improved ordering in this sample;
it did not recover an answer missing from either baseline's top five.

Expected behaviors, frozen before the run:

- `operations.triage`: unknown effects produce `reconcile` before check-status
  handling, with dispatch authorization false.
- `github_checks.check_suggestions`: `total_count` must be an integer equal to
  the number of supplied check runs; a partial export raises `ValueError`.
- `process.invoke`: a monotonic deadline produces `timeout_effects_unknown`
  when a running child reaches its deadline.

## Absent-answer control

“Which code accepts Stripe checkout webhooks?” has no answer in this selected
corpus. Plain text search returned two unrelated candidates; hybrid and reranked
search each returned ten. The top reranked result was `JsonParticipant.run`
at score `0.291015625`; it implements participant JSON handling, not Stripe.

The retriever supplies ranked candidates without a calibrated “no answer” rule.
This control therefore does **not** pass an automatic abstention criterion.
No downstream model generated an answer in this test, so no generated
hallucination rate was measured. Do not choose a score cutoff from this single
negative example.

## Usage and limits

- Four query embeddings and four rerank requests; all eight completed.
- Provider-reported usage: **30,064 tokens**.
- Cost calculated from the recorded list rates: **$0.00150586**, before credits.
  This is a usage-based estimate, not an account billing statement.
- Requests were paced with a 61-second pause between question pairs. The prior
  rate-limit error did not recur; its exact account-level cause remains unknown.
- The clipboard credential was used only in process memory and was neither
  displayed nor saved. The process cleared its environment entry at completion.

## Assessment

The integration works and its reranker improved ordering on this small check.
Continue bounded evaluation with representative application code. This is three
positive cases and one negative case over five Harness files, not a general
accuracy percentage or proof of better generated applications. Consumers must
verify answer support and handle missing answers. A larger unseen application
packet and matched coding tasks remain necessary before routine-use promotion.

## Evidence

- [Frozen questions and source spans](../.pilot/voyage-accuracy-2026-09-15/campaign/freeze.json)
- [Expected answers](../.pilot/voyage-accuracy-2026-09-15/answer-oracle.json)
- [All ranking results and usage](../.pilot/voyage-accuracy-2026-09-15/campaign/results.json)
- [Exact passages and answer-support checks](../.pilot/voyage-accuracy-2026-09-15/accuracy.json)
- [Independent behavior checks](../.pilot/voyage-accuracy-2026-09-15/behavior-checks.json)
- [Disposable evaluation runner](../.pilot/voyage-accuracy-2026-09-15/run.py)

The original first-query hybrid check also retrieved its expected revision guard
at rank 1 using the initial saved live query embedding, with zero new requests.
That earlier check did not include a successful rerank and is kept separate
from the four-question campaign above.
