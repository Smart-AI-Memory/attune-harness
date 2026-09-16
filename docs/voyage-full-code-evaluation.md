# Voyage: 98-file Harness evaluation

September 15, 2026. Installed Harness `0.1.0.dev13`; `voyage-code-4` and `rerank-2.5`.

**Completed:** 98 files, 1,050 passages, 20 frozen questions (17 answerable, three absent features).

## Retrieval results

A question passes only when the retrieved passages cover every frozen evidence fragment in every required component. Some questions require both implementation and a regression test. This is stricter than retrieving a relevant file or symbol.

| Method | Complete evidence in top 5 | Complete evidence in top 10 | Components in top 5 |
|---|---:|---:|---:|
| lexical_bm25 | 3/17 | 5/17 | 6/27 |
| hybrid | 7/17 | 8/17 | 16/27 |
| voyage_rerank | 10/17 | 10/17 | 20/27 |

Compared with hybrid retrieval, reranking changed complete top-five evidence for 4 questions from fail to pass and 1 from pass to fail.

## Assessment and next recommendation

Keep the 98-file index as a repository evidence aid. Reranking improved complete
evidence coverage in this diagnostic, at a small measured provider cost. It is
not yet a reliable complete-answer mechanism: seven answerable questions missed
some frozen evidence, and all three absent features returned candidates.

Post-run diagnosis, using the already paid query embeddings, found complete
required evidence in the initial 50 candidates for 13/17 questions. Four misses
already existed before reranking (`q04`, `q08`, `q09`, `q17`); three others lost
required fragments during final ranking (`q01`, `q03`, `q15`). Merely returning
ten results instead of five did not improve reranked full-evidence coverage.

The strongest next improvement is to retrieve implementation and related tests
deliberately, then expand relevant functions where a fragment alone is incomplete.
For stale-index and cache-reuse questions, all five top results were tests. The
dependency-version question failed to retrieve `pyproject.toml` even among the
50 candidates, despite that file being indexed. Exact configuration questions
should use direct file/schema access alongside semantic retrieval. Missing-answer
handling needs separate qualification; one relevance-score cutoff inferred from
these three controls would not establish it.

One frozen requirement was stricter than its question needed: `q15` asked about
input changes during verification, and the rank-one result contained the correct
reread-and-reject guard. The frozen answer additionally required the later hash
construction, which was omitted. Its recorded coverage loss therefore does not
establish that the answer to the question became incorrect. The original score
is retained; this manual qualification is separate from rescoring.

See the [post-run diagnosis](../.pilot/voyage-full-code-2026-09-15/diagnosis.json).
These recommendations are interpretations of the retained results; no retrieval
implementation or frozen evaluation criterion was changed after the run.

## Missing-answer controls

Explicit automatic absence signals: **0/3**. The controls asked for a Stripe payment endpoint, a shared Redis retrieval cache, and an automatic background index watcher. Mentions in fixtures or comments do not implement those features. Ranked candidates and `answer_support: not_established` are not an explicit missing-answer decision. No score threshold was fitted after seeing these results.

## Cost

| Stage | API calls | Provider tokens | Estimated cost before credits |
|---|---:|---:|---:|
| indexing | 33 | 160,600 | $0.01927200 |
| query_embeddings | 20 | 340 | $0.00004080 |
| reranking | 20 | 265,156 | $0.01325780 |

Total: **73 calls, $0.03257060**. Costs use provider-reported tokens and the recorded list rates, not an account invoice.

Illustrative search costs if these 20 questions represent later queries; indexing, refreshes, local compute and answer generation are excluded:

| Method | 1,000 searches | 10,000 searches |
|---|---:|---:|
| lexical_bm25 | $0.0000 | $0.0000 |
| hybrid | $0.0020 | $0.0204 |
| voyage_rerank | $0.6649 | $6.6493 |

## Question-by-question evidence coverage

| Question | BM25 top 5 / 10 | Hybrid top 5 / 10 | Reranked top 5 / 10 |
|---|---|---|---|
| q01 — How can I index application code with selected schema files while keeping Markdown documentation optional? | miss / miss | miss / miss | miss / miss |
| q02 — Which checks keep environment directories and source symlinks out of the indexed repository evidence? | miss / miss | miss / miss | pass / pass |
| q03 — If an indexed file changes without changing its length, what blocks stale retrieval and which regression test demonstrates it? | miss / miss | miss / miss | miss / miss |
| q04 — How does repeating an identical search reuse evidence without a second provider charge, and where is that tested? | miss / miss | miss / miss | miss / miss |
| q05 — After a reranking response is lost and billing is uncertain, what prevents an automatic paid retry and which test covers it? | miss / miss | miss / miss | pass / pass |
| q06 — Where are duplicate or out-of-range reranking indices and increasing scores rejected? | pass / pass | pass / pass | pass / pass |
| q07 — How are semantic matches and exact text matches combined before the reranker sees candidates? | miss / miss | miss / miss | pass / pass |
| q08 — How does the Attune plugin keep searches within the accepted task and enforce a finite search-call budget? | miss / miss | miss / miss | miss / miss |
| q09 — Can a successfully closed repository-evidence plugin continue searching with unused budget, and which test checks that? | miss / miss | miss / miss | miss / miss |
| q10 — Does a high-ranked retrieved passage mean the answer has been verified, and what happens for an empty result? | pass / pass | pass / pass | pass / pass |
| q11 — How does a timed-out child process retain partial output and record uncertain effects, and where is this exercised? | miss / miss | pass / pass | pass / pass |
| q12 — What distinction is made between cancellation before process launch and cancellation after the child has started? | miss / miss | miss / pass | pass / pass |
| q13 — How does the native Codex response parser avoid treating commentary or an incomplete turn as a final answer? | pass / pass | pass / pass | pass / pass |
| q14 — Can a repair strategy be ranked as cheapest when human time or a provider charge is missing? | miss / pass | pass / pass | pass / pass |
| q15 — What stops a document verification result from silently describing input that changed during verification? | miss / pass | pass / pass | miss / miss |
| q16 — Which qualification script refuses imports directly from the source checkout and selects process tests for the actual operating system? | miss / miss | pass / pass | pass / pass |
| q17 — Which optional dependency group installs the Voyage retrieval stack, and which versions does it pin? | miss / miss | miss / miss | miss / miss |
| q18 — Which endpoint validates Stripe checkout webhook signatures and records successful payments? | absent control | absent control | absent control |
| q19 — Where is Redis used to share cached Voyage search results between multiple worker processes? | absent control | absent control | absent control |
| q20 — Which background file watcher automatically rebuilds the Voyage index whenever repository code changes? | absent control | absent control | absent control |

## Evidence and limitations

- [Frozen questions and expected answers](../.pilot/voyage-full-code-2026-09-15/questions.md)
- [Frozen manifest, source spans and criteria](../.pilot/voyage-full-code-2026-09-15/freeze.json)
- [Complete rankings and original source excerpts](../.pilot/voyage-full-code-2026-09-15/results.json)
- [Machine-readable summary](../.pilot/voyage-full-code-2026-09-15/summary.json)
- [Six referenced behavior tests](../.pilot/voyage-full-code-2026-09-15/expected-behavior-tests.xml)
- [Rate-limit observations](../.pilot/voyage-full-code-2026-09-15/rate-observations.jsonl)

The initial fallback paced indexing at one request per minute because API responses supplied no limit headers. The signed-in dashboard subsequently established Tier 1 limits (2,000 RPM; 8M embedding TPM and 2M rerank TPM), with no project overrides shown. The runner was stopped during a confirmed local pre-dispatch wait; nine completed batches were reused. The original interrupted record and explicit reconciliation are preserved in [the pacing audit](../.pilot/voyage-full-code-2026-09-15/pacing-reconciliation.json). No previously sent provider call was repeated. Remaining work used conservative pacing within those verified limits.

All three methods use the same frozen source snapshot. Query embeddings are reused for the hybrid comparison; the comparison does not make extra provider calls. All returned passages passed original byte/hash validation. The six behavior tests exercise selected expected behaviors with deterministic providers and real local processes; they are separate from the live retrieval results.

These questions were chosen by the assistant with knowledge of the implementation. They are diagnostic, not a blinded sample or a general accuracy percentage. The BM25 baseline searches passages; it does not measure an experienced developer using ripgrep or a coding agent combining multiple searches. Alternate valid evidence outside the frozen spans may receive no credit. No LLM generated answers or application changes were evaluated. Provider timings can include deliberate pacing and local integrity checks. The index covers the approved source/test/script selection and pyproject.toml, not every artifact in the repository.

The comparison holds the 98-file selection constant across retrieval methods.
It does not isolate the effect of expanding from five files, because the earlier
small-scope campaign used different questions. New questions cover code absent
from that earlier selection.
