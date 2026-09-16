# Starter: evaluate and improve Attune RAG with Voyage AI

Continue my work on the new repository-grounded Attune RAG integration using
**Voyage AI**. Attune Harness helps AI users build applications through vibe
engineering. I want retrieval anchored in application code, tests, and selected
configuration/schema files; a separate document collection is optional.

## Session contract

- **Project:** `/Users/patrickroebuck/attune-harness`. The last verified branch was
  `codex/voyage-retrieval`. Inspect the current checkout and preserve existing work.
- **Initial mode:** code-grounded evaluation and planning of the next focused
  implementation increment.
- **Outcome:** recommend how hybrid retrieval and Voyage reranking should work
  together, based on useful coding evidence, total cost, and latency; prepare a
  concrete next implementation increment.
- **Done when:** the recommendation cites verified implementation and evaluation
  evidence, explains remaining limitations, and supplies a bounded change plan
  with meaningful acceptance tests. Distinguish proposals from implemented work.

Start with the existing code and receipts. Do not make me repeat settled context.
Push back when warranted, especially if a benchmark score is being mistaken for
proof that an AI writes better code. Ask only for material missing information,
and continue independent local work while awaiting an answer.

## Read first

All paths below are absolute:

1. `/Users/patrickroebuck/attune-harness/docs/voyage-100-question-evaluation.md`
2. `/Users/patrickroebuck/attune-harness/.pilot/voyage-100-2026-09-15/summary.json`
3. `/Users/patrickroebuck/attune-harness/.pilot/voyage-100-2026-09-15/freeze.json`
4. `/Users/patrickroebuck/attune-harness/.pilot/voyage-100-2026-09-15/manual-review.json`
5. `/Users/patrickroebuck/attune-harness/docs/code-first-rag.md`
6. `/Users/patrickroebuck/attune-harness/docs/code-first-rag-receipt.md`

Inspect the implementation under
`/Users/patrickroebuck/attune-harness/src/attune_harness/`, especially
`voyage_retrieval.py`, `voyage_sources.py`, `voyage_index.py`,
`voyage_provider.py`, `retrieval_task.py`, `mcp_server.py`, and `attune_bridge.py`.
Use the relevant tests to verify behavior, not just documentation claims.

## Established findings — September 15, 2026

The completed evaluation reused 98 files and 1,050 passages. All 100 fresh
questions and expected evidence were frozen before requests: 80 answerable
questions and 20 missing-answer controls.

| Method | Complete expected evidence in top 5 | In top 10 |
|---|---:|---:|
| Passage BM25 | 58/80 | 63/80 |
| Hybrid | 71/80 | 75/80 |
| Hybrid plus Voyage reranking (`voyage_rerank`) | 75/80 | 76/80 |

Hybrid combines Voyage dense embeddings, lexical search, and exact token
matches. Voyage reranking orders that same candidate pool. These are stages
of one pipeline. The installed public retrieval path currently reranks nonempty
candidates; the hybrid-only result was an evaluation baseline, not a separately
qualified production switch.

Reranking produced six gains and two losses in the frozen top-five metric.
Both scored losses have qualifications: one retrieved a supporting alternative
outside the oracle, and the other already contained the answer but lacked an
unnecessary formula required by the oracle. Preserve the recorded scores and
explain those qualifications separately.

None of the 20 missing-answer controls produced explicit absence. They returned
candidates with `answer_support: not_established`. This is not a measurement of
hallucinated generated answers. No generated answers or code changes were scored.
The questions were assistant-authored with source knowledge, not a random or
independently reviewed sample of real development requests.

## Cost and efficiency

The 100-question run used 200 successful API calls, cost approximately $0.06596
at the recorded list rates, and took 8.9 minutes. No indexing calls or retries
were needed. Nine focused behavior tests passed; all 35 installed Harness
modules matched the indexed source hashes.

At that query mix, estimated API costs before credits were:

| Method | 1,000 searches | 10,000 searches |
|---|---:|---:|
| Hybrid without reranking | $0.00154 | $0.01543 |
| Hybrid plus reranking | $0.65958 | $6.59578 |

The reused index originally cost $0.019272 to embed. These estimates exclude
local compute, index refreshes, and answer generation. Benchmark runtime includes
integrity checks and all baseline/scoring work; do not present it as production
search latency. Measure the extra answer-context cost when comparing hybrid
top ten with reranked top five, despite their equal aggregate 75/80 coverage.

## Work to do

1. Verify the current installed path, checkout, index freshness, and actual
   integration. Last qualified: Harness `0.1.0.dev13`, `voyage-code-4`,
   `rerank-2.5`, and interpreter
   `/Users/patrickroebuck/attune-harness/.venv-code-rag/bin/python`.
2. Assess hybrid plus reranking as the current default, and whether an explicitly
   selectable hybrid-only or conditional-reranking path merits implementation.
   Keep quality, latency, provider charges, and downstream context costs separate.
   Do not assume selective reranking already exists or is necessarily better.
3. Review the concrete gaps: `n008` missed its companion test; `n040` missed
   `pyproject.toml`; `n055` lost relevant implementation during ranking. Consider
   exact file/schema lookup and implementation/test context expansion. Select one
   focused next increment and explain why it should come first.
4. Design the next useful validation around real application bug/feature tasks,
   with expected behavior and tests recorded beforehand. Compare completed coding
   outcomes with and without retrieval. If an application repository is needed,
   ask me to select it; continue the Harness audit and local preparation meanwhile.

## Boundaries to preserve

- The new implementation is in Harness with an optional Attune AI plugin exposing
  `code_evidence_query`. Do not assume the separately installed legacy
  `attune-rag` package, its documents, or all Attune workflows have been replaced.
  The desktop MCP configuration was not switched by these evaluations.
- Preserve both frozen experiments and raw receipts. Keep new evaluation answers
  outside the index, and do not tune on an evaluation set then call it unseen.
- Source revisions, byte/hash checks, scoped grants, finite budgets, and durable
  paid-stage receipts remain part of the implementation contract. Never silently
  retry a provider operation with unknown billing effects.
- Use the existing local credential setup without displaying secrets. The
  completed campaign's upload/spend approval was for its specified scope. Prepare
  any new live campaign concretely, state its upload scope and estimated cost,
  and obtain the applicable authorization before new paid work. Local inspection
  and preparation can proceed immediately.

Begin with a concise verified assessment and your recommended next increment.
