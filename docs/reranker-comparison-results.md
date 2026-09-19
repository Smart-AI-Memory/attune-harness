# Voyage reranker comparison — September 16, 2026

Keep `rerank-2.5` as the current default. Lite reduced reranker cost by 60%, but
its measured latency advantage was small and it failed the predefined no-loss
check for complete expected evidence in the first five passages. It remains
worth evaluating as an explicit lower-cost option on fresh cases.

The approved comparison completed all 200 requests with no retries, failures,
unresolved effects or unrun cases. Total cost from provider-reported tokens at
the frozen list rates was **$0.09212483**, below the **$1 local stop budget**.
This is cost before account credits, not a fetched invoice. No embedding or
answer-generation calls were made.

## Results

Both models ranked the same 50 candidates for each of 100 frozen historical
questions. There were 80 answerable questions and 20 missing-answer controls.
Each model ran first on 50 questions. All scores use the unchanged, source-bound
oracle; no result was rescored to favor either model.

| Measure | rerank-2.5 | rerank-2.5-lite |
|---|---:|---:|
| Complete expected evidence in top 5 | 75/80 | 74/80 |
| Complete expected evidence in top 10 | 76/80 | 76/80 |
| Median provider duration | 333.0 ms | 320.7 ms |
| Mean provider duration | 338.2 ms | 324.0 ms |
| 95th percentile duration | 399.3 ms | 388.7 ms |
| Cost for 100 calls | $0.06580345 | $0.02632138 |
| Provider-reported tokens | 1,316,069 | 1,316,069 |
| Median excerpt bytes in top 5 | 5,430.5 | 5,570.0 |
| Mean excerpt bytes in top 5 | 5,580.49 | 5,458.77 |

The median **within-question** saving was 19.0 ms (median relative saving 5.65%);
this differs from subtracting the two model medians. Lite was faster on 65/100
questions. The median difference favored lite with either ordering: 22.8 ms when
baseline ran first and 14.2 ms when lite ran first. A descriptive case-resampling
interval spans approximately 6.4–28.5 ms saved; it does not account for day-to-day
provider variation or establish a production-workload confidence interval.

Provider duration includes SDK and network processing, without deliberate pacing
or retries. It excludes local validation and scoring. The complete evaluator took
108.0 seconds, including its own checks and durable receipts; that is not production
search latency. This experiment does not measure the server's inference time alone.

## Changed cases and qualifications

Lite had two scored top-five losses and one gain. There were **no case-level
changes** in complete top-ten evidence. Inspection of the frozen passages gives
these qualifications; they do not change the frozen scores:

| Case | Frozen question | Observed change |
|---|---|---|
| n013 — loss | Why does an ordinary failed GitHub check with no classified cause request human review? | The adapter passage assigning `failure_kind: unknown` moved from rank 5 to rank 10. Lite retained the human-review implementation and the test mapping failed checks to human review in its top five. |
| n063 — loss | Can a model invent its own citation IDs in the host-owned passage review? | The production identifier guard moved from rank 3 to rank 6. Lite still returned the test rejecting unknown identifiers at rank 3 and the test establishing closed citation choices at rank 5. |
| n067 — gain | How much context is reserved for framing in local generation? | The continuation containing the budget formula moved from rank 6 to rank 4. Baseline already returned the literal `framing_margin: 512`; the frozen oracle also requires the formula. |

The quality metric is exact expected-evidence completeness, not answer accuracy.
These observations demonstrate why a one-point aggregate change must not be
described as one additional wrong generated answer. No answers or code changes
were generated or graded. The 20 controls returned candidates with
`answer_support: not_established`; neither model demonstrated correct abstention.

## Decision and next increment

The proposed candidate check required both lower paired median latency and **no
loss on any baseline-supported top-five case**. Lite passed the latency condition
and failed the no-loss condition. Preserve that result instead of relaxing the
criterion after observing it. No default, installed package or live index changed.

The strongest measured route to lower local retrieval latency remains the
[validation-reuse increment](specs/voyage-validation-reuse/design.md). Its separate
offline prototype removed roughly half a second of repeated checking; that
measurement and this provider study have different conditions and cannot be added
into a promised end-to-end speedup. Production execution of that three-task spec
remains pending.

For lite, a next study should freeze genuinely new development questions and
include implementation/test evidence alternatives before requests. Lite with ten
passages retained the same expected-evidence coverage here, but increasing answer
context has an unmeasured downstream token and latency cost. This campaign does
not authorize another paid study or automatically enable that configuration.

## Receipts and reproducibility

The [prepared design, budget and validation](reranker-comparison-preparation.md)
records the approved scope. Packet identity:
`f53546222f045be518f75ae21f69c153b28c694a73982de44d3c238c61cecbb1`.

Local raw artifacts under `.pilot/rerank-comparison-2026-09-16/`:

- `authorization.json`: Patrick's explicit spend approval and bounds.
- `packet.json`: frozen queries, candidate order/text, oracle, models, rates,
  source manifest and evaluator/source hashes.
- `live/record.json`: all 200 durable dispatch/result receipts and final summary.
- `analysis.json`: independently recomputed costs, scores, order effects and timing.
- `case-comparison.json`: case-level outcomes, source IDs and raw normalized results.
- `analyze.py`: deterministic offline verification and descriptive analysis.

The offline verifier checked every request digest, ranking, selected passage ID,
score and token-priced cost against the packet, then verified the saved summary.
All 468 historical experiment files retain their original hashes. Record SHA-256:
`754ed3acebee27fd9406739a59a1e42914e54ca9d95dc493473aac301745e86a`.

Before live execution, 108 focused and related tests passed, including 35 new
evaluator tests. The source did not change between qualification, freezing and
execution. Offline scorer validation reproduced 600 historical score checks.
Raw artifacts are intentionally Git-ignored; a new clone may lack them.

Rerun the analysis without provider calls:

```sh
.venv-code-rag/bin/python .pilot/rerank-comparison-2026-09-16/analyze.py
```

The experiment and documentation are local and uncommitted. No installation,
push, PR or merge was performed. The validation-reuse production ladder remains
at 0/3 tasks implemented or accepted.
