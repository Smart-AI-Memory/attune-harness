# Voyage lite comparison — approved run packet

September 16, 2026. Patrick approved the frozen 200-call comparison, its stated
upload scope and $0.09–$0.11 estimate, with a $1 local stop budget:
“yes approvade with a $1 local stop budget.” The authorization is preserved in
`.pilot/rerank-comparison-2026-09-16/authorization.json`. Execution completed:
200 successful calls, $0.09212483 before credits, no failures or retries.
See [the measured results and decision](reranker-comparison-results.md).
He previously authorized preparation with “go” and pointed to Voyage's FAQ
recommendation of lite for latency-sensitive applications.

`rerank-2.5-lite` is the preferred latency candidate, consistent with the
[Voyage FAQ](https://docs.voyageai.com/docs/faq). The experiment compares it with
the current `rerank-2.5` model before recommending a production change.

## Concrete run

- Reuse all 100 September 15 historical candidate pools: 80 answerable questions
  and 20 missing-answer controls. Each contains 50 passages.
- Send identical ordered passages and query text to both models; alternate
  which runs first (50 cases each). Request top 10; score completeness at 5 and 10.
- Make at most 200 requests to `https://api.voyageai.com/v1/rerank`.
  No embeddings, reindexing, answer generation or retries are planned.
- Upload the historical Harness source/test excerpts and their contextual text,
  plus the questions. Expected answers and scoring criteria stay local.
  Canonical request JSON totals 11,688,150 bytes across both models; SDK framing
  may differ. The packet retains the historical source manifest and passage hashes.
- Compare per-case evidence completeness, returned context bytes, and paired
  provider latency. Provider timing includes transport and SDK processing but
  excludes local integrity checks; it is not production search latency.
- Candidate gate: no loss on any baseline-supported top-five case and a lower
  paired median latency. Report individual gains/losses, not just aggregate counts.
  A retrospective pass alone does not qualify a default change; fresh cases remain
  necessary. Controls returning candidates do not establish successful abstention.

This is a retrospective diagnostic using known questions and an archived source
snapshot. Both models receive fresh calls in the same campaign. Yesterday's
baseline latency is not used as today's comparator.

## Cost and authorization

[Voyage list pricing](https://docs.voyageai.com/docs/pricing), checked September 16:
`rerank-2.5` costs $0.05 per million tokens; lite costs $0.02.

| Estimate | Both models, 100 cases |
|---|---:|
| Historical 1,316,069 reranker tokens per model | $0.092125 |
| UTF-8 input bytes divided by four | $0.106346 |
| Conservative reservation using bytes plus allowance | $0.436807 |
| Campaign stop budget | $1.00 |

Estimates exclude credits. Models may tokenize differently. The evaluator reserves
each request before dispatch and checks reported cost afterward. The stop budget
is a local dispatch policy, not a provider account billing cap: an unexpectedly
large returned charge can exceed it before the next dispatch is stopped.

Prepared packet:
`.pilot/rerank-comparison-2026-09-16/packet.json`

SHA-256 identity:
`f53546222f045be518f75ae21f69c153b28c694a73982de44d3c238c61cecbb1`

Offline preflight receipt:
`.pilot/rerank-comparison-2026-09-16/preflight.json`

The packet binds cases, oracle spans, candidate order/text, source snapshot,
models, rates, evaluator/source hashes, and limits. Editing the evaluator or
production code requires a new freeze and a new digest. Raw study artifacts are
local and Git-ignored; a fresh clone may not contain them.

## Implementation and validation

Implementation: `experiments/voyage/compare_rerankers.py`.
Tests: `tests/test_reranker_comparison.py`.
Design: [execution preparation](design-reranker-comparison.md).

The experiment imports this checkout's source explicitly, so the preserved older
installation cannot silently supply a different transport. It uses the existing
bounded Voyage transport with retries and redirects disabled. Requests require
both `--allow-provider` and the exact approved digest. A synced pending receipt
precedes every dispatch. Missing usage, invalid rankings, interruption, source
change, or persistence failure stops further dispatch. Existing live run directories
are never reused, including incomplete or uncertain runs.

- 35 focused tests passed using injected providers and local fixtures.
- The combined reranker, Voyage, code-RAG, integration and evaluation suite passed:
  108 tests in 38.77 seconds, with one existing Attune ModelTier deprecation warning.
  JUnit receipt: `docs/receipts/validation-bottleneck-20260916/reranker-preparation-tests.xml`.
- The scorer reproduced all 600 historical checks (100 cases × three methods ×
  top 5/top 10), including null scores for missing-answer controls.
- All 468 preserved historical experiment files retain their original hashes.
- Archived generation publication, metadata, database rows, exact oracle spans
  and ordered candidates passed offline validation.
- No production module, installed environment, index or default model changed.
  The validation-reuse spec remains at 0/3 production tasks implemented/accepted.

Preflight, with zero provider calls:

```sh
.venv-code-rag/bin/python experiments/voyage/compare_rerankers.py preflight \
  --output .pilot/rerank-comparison-2026-09-16
```

The following is the approved invocation, recorded for reproducibility. It has
already completed; do not repeat the campaign. Execution used the existing local
credential setup without printing the key:

```sh
.venv-code-rag/bin/python experiments/voyage/compare_rerankers.py run \
  --output .pilot/rerank-comparison-2026-09-16 \
  --allow-provider \
  --approved-digest f53546222f045be518f75ae21f69c153b28c694a73982de44d3c238c61cecbb1
```

Do not delete or reuse an interrupted live run. Inspect its durable receipt,
identify completed/uncertain/unrun operations, and prepare any continuation
explicitly. A fresh output directory is not authorization to repeat paid work.

These changes are local and uncommitted. No installation, push, PR or merge was
performed for this comparison.
