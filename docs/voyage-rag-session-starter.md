# Starter: continue Attune RAG after the Voyage retrieval merge

Updated September 16, 2026, after PR #1 merged.

**Latest reranker result:** Patrick approved the `rerank-2.5` versus
`rerank-2.5-lite` comparison with a $1 local stop budget. Read
[the results and decision](reranker-comparison-results.md) first. All 200 calls
completed for $0.09212483 before credits. Lite cost 60% less but saved only a paired
median 19.0 ms. Complete top-five evidence was 74/80 versus 75/80; both scored
76/80 at top ten. Two case-level losses failed the predefined no-loss check;
keep the current default. This retrospective experiment does not approve or
complete the separate production task ladder below.

**Latest continuation:** Patrick approved the `/spec` task ladder for the latency
increment. Read [the draft task ladder](specs/voyage-validation-reuse/tasks.md),
[design and measurements](specs/voyage-validation-reuse/design.md), and
[decisions](specs/voyage-validation-reuse/decisions.md) first. The XML plan is
`.claude/plans/voyage-validation-reuse.md`; plan approval and execution start are
recorded. Task 1's offline implementation/checks are ready: 79 Voyage tests pass,
and the fresh baseline confirms direct 4/3 and session 6/5 full checks. The
standard paid review workflow has not run; offline-review/auto-run selection and
task acceptance remain pending. Do not restart the assessment.
A separate disposable prototype removed one immediate duplicate validation:
six-query warm offline means fell from 3.098 to 2.624 s for recomputation and
2.559 to 2.064 s for cached results; 68 existing tests passed on each snapshot.
No production source or preserved installation changed. Larger caching and
Voyage options are assessed in the design, including their remaining proof work.

Continue my work on the new repository-grounded Attune RAG integration using
**Voyage AI**. Attune Harness helps AI users build applications through vibe
engineering. I want retrieval anchored in application code, tests, and selected
configuration/schema files; a separate document collection is optional.

## Session contract

- **Project:** `/Users/patrickroebuck/attune-harness`. Inspect the current checkout
  and preserve existing work. PR #1's `codex/voyage-retrieval` branch is already
  merged; this starter is a follow-up documentation update.
  Start any new implementation branch from freshly verified `main` and carry
  forward relevant local changes without discarding them.
- **Initial mode:** continue planning the next focused increment from the existing
  assessment. Do not restart the completed review, fixes or benchmark analysis.
- **Outcome:** identify the best remaining opportunities, recommend one bounded
  next increment, and prepare its implementation/validation plan. The existing
  recommendation is scoped exact file/range lookup; reassess its priority against
  the measured latency problem and real application needs.
- **Done when:** opportunities are ranked by expected value, supporting evidence,
  effort and uncertainty; the recommended increment has concrete acceptance
  criteria; unresolved decisions are explicit. Distinguish recommended,
  implemented, installed and measured behavior.

Start with the existing code and receipts. Do not make me repeat settled context.
Push back when warranted, especially if a benchmark score is being mistaken for
proof that an AI writes better code. Ask only for material missing information,
and continue independent local work while awaiting an answer.

## Read first

Read the current-state receipts and existing plan first. Paths are absolute:

1. `/Users/patrickroebuck/attune-harness/docs/sol-review-fix-receipt.md`
2. `/Users/patrickroebuck/attune-harness/docs/cross-review-sol-2026-09-16.md`
3. `/Users/patrickroebuck/attune-harness/docs/voyage-next-increment-2026-09-15.md`
4. `/Users/patrickroebuck/attune-harness/docs/voyage-latency-assessment-2026-09-15.md`
5. `/Users/patrickroebuck/attune-harness/docs/code-first-rag.md`
6. `/Users/patrickroebuck/attune-harness/docs/voyage-100-question-evaluation.md`

For historical evaluation details, use the preserved local
`/Users/patrickroebuck/attune-harness/.pilot/voyage-100-2026-09-15/` files
`summary.json`, `freeze.json`, and `manual-review.json`, plus
`/Users/patrickroebuck/attune-harness/docs/code-first-rag-receipt.md`.
Raw `.pilot/` and `docs/receipts/` artifacts are intentionally local and ignored
by Git; a fresh clone may not contain them. Never invent missing evidence.

Inspect the implementation under
`/Users/patrickroebuck/attune-harness/src/attune_harness/`, especially
`voyage_retrieval.py`, `voyage_sources.py`, `voyage_index.py`,
`voyage_provider.py`, `retrieval_task.py`, `mcp_server.py`, and `attune_bridge.py`.
Use the relevant tests to verify behavior, not just documentation claims.

## Merged state — September 16, 2026

- [PR #1](https://github.com/Smart-AI-Memory/attune-harness/pull/1) merged into
  `main` as `7eabe5821aaf484276909e13f116a4ffe2bdaed4`. Its complete tree was
  verified identical to tested branch commit
  `b0bbc7279e646087c7640f2ce268705687e18a76`.
- The 65-file change includes the Voyage retrieval implementation, optional
  Attune plugin, documentation/evaluation tooling, tests and reports. Local
  workflow history and raw receipts were excluded from the commit.
- Sol's review produced four confirmed medium-severity findings and three
  rejected claims. All four confirmed defects are fixed: reserve rerank capacity
  before a new/prepared query embedding; record exceptions leaving plugin
  activation as unresolved; exit 1 for incomplete evaluator campaigns; retain
  host qualification checks under optimized Python. Completed stages still replay
  at a full provider-call budget without new charges.
- **363 distinct local tests passed. All 4/4 targeted mutations were detected;
  23/27 new cases failed with their guards removed.** Tests and affected usage,
  qualification and review documentation were updated.
- Both the push and PR qualification runs passed all six installed-wheel jobs:
  macOS, Ubuntu and Windows, each on Python 3.10 and 3.12. The PR run is
  [35053571235](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/35053571235).
  This records pre-merge CI, not the status of any later run.
- No new local wheel installation, desktop MCP switch, package release or live
  provider campaign accompanied the fixes. Preserve `.venv-code-rag` and the
  frozen experiments. That environment's installed dev13 wheel predates the
  fixes; the version label alone does not establish source identity.
- The older reports' installed/source/index hash matches describe their dated
  snapshots. Git revisions and source bytes have changed since those checks.
  Verify index freshness before use; do not assume the old generation accepts
  the merged checkout or overwrite frozen evidence to make it pass.

## Historical findings — September 15, 2026

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
modules matched the indexed source hashes at that evaluation snapshot.

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

## Opportunities to evaluate

The following order is a proposed priority, not an approved implementation plan.
Keep the smallest useful feature separate from the most important product test.
For each opportunity, report the evidence, expected benefit, effort, uncertainty
and the cheapest meaningful validation. Do not invent numerical ROI or speedups.

| Proposed priority | Opportunity and evidence | Next useful step |
|---|---|---|
| 1 | Reduce repeated integrity-validation work. The historical warm offline session probe spent 3.16 of 3.22 local seconds in full generation checks; hybrid candidate search took about 0.032 seconds. This is the strongest measured performance opportunity, not a promised live speedup. | Reproduce on fresh, separate fixtures, then investigate sharing validated state across nested checks while retaining revision, byte, scope, pre/post-dispatch and tamper guarantees. Compare separate baseline/changed runs. |
| 2 | Add bounded exact file/range lookup. `n040` missed the selected package manifest; semantic ranking is unnecessary when an agent knows the path. A detailed design and acceptance table already exist. | Validate the proposed `read_evidence` grant, CLI and MCP surfaces. Demonstrate exact bytes, limits, scope and zero provider calls on fixtures. The API remains unimplemented. |
| 3 | Measure completed coding outcomes. The 100 questions measured retrieval support, not accepted bug fixes or features. This is the most important outstanding product validation. | Select a real application and freeze genuine tasks and acceptance tests. Reuse the proposed paired pilot protocol; prepare upload and total-cost estimates before any live run. |
| 4 | Preserve implementation plus test evidence. `n008` omitted the companion test from candidates; `n055` lost implementation evidence during reranking. | Prototype bounded companion discovery and evidence packing on new cases. Measure completeness and added context; keep both existing misses as known regressions. |
| 5 | Make the merged integration usable in the actual coding host. The optional plugin was qualified, but the local installed wheel and desktop configuration were not migrated. | Build and qualify a fresh wheel in a separate environment, then prepare the concrete host switch and rollback. Preserve the historical environment and legacy consumers. |
| 6 | Test cheaper retrieval modes and missing-answer handling. Reranking costs more per query but reduced cited context in the sample; all 20 absent-answer controls still returned unverified candidates. | Treat hybrid-only/conditional reranking and abstention as separate experiments with untouched validation cases, measured downstream costs and explicit failure criteria. No automatic mode or calibrated abstention rule exists yet. |

## Work to do

1. Verify the checkout, merged commit, active installed package, index freshness
   and actual host integration. Preserve the old qualified interpreter at
   `/Users/patrickroebuck/attune-harness/.venv-code-rag/bin/python`; use a separate
   environment for any new installed-artifact qualification.
2. Carry forward the existing recommendation to keep hybrid plus `rerank-2.5`
   as the current default. Compare the measured validation bottleneck with scoped
   lookup as the next bounded increment; explain which should come first and why.
   Do not bundle all opportunities into one implementation.
3. Reuse the exact-lookup design and acceptance table in
   `/Users/patrickroebuck/attune-harness/docs/voyage-next-increment-2026-09-15.md`
   if lookup is selected. Its proposed CLI, `harness.read_evidence` and Attune
   `code_evidence_read` are not present in the merged implementation.
4. Continue preparing real application bug/feature evaluation. The application
   repository and tasks remain unselected; ask for the repository when needed,
   while continuing independent Harness inspection and local preparation.

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

Begin with a concise verified assessment, the strongest opportunities and one
recommended next increment. When reporting completion, state separately what is
implemented/tested, installed, committed/pushed, and opened as a PR or merged.
