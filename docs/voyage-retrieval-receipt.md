# Voyage implementation receipt

September 15, 2026. Branch: `codex/voyage-retrieval`. Base commit:
`6bece93e8d5ddae3205d394b9b9c90d4408b8ee3`. Changes are in the working tree;
no release, merge or remote CI execution is claimed.

## Delivered

- Optional Voyage integration: code embeddings, local persistent LanceDB,
  lexical/identifier search, RRF and standard reranking.
- Scoped Git source selection, original byte passages, immutable generations,
  changed-input embedding reuse, source/table integrity checks and offline plans.
- Coding-agent CLI/MCP intake; optional review/extension integration; versioned
  recovery; multi-passage citations; per-run retrieval reuse and paid-stage
  ledgers. Unknown billed effects cannot use a read-only retry.
- Exact dependency pins, installed-wheel checks, expanded CI matrix checks,
  setup documentation, an explicit live smoke command, and a prepared retrieval
  evaluation packet. Existing structured operations remain deterministic.

## Artifact and actual checks

Package: **0.1.0.dev12**. Wheel:
`dist/voyage-dev12/attune_harness-0.1.0.dev12-py3-none-any.whl`.

SHA-256:
`5c8e9b697bd8b0393b278fcadba9d91a6c14cc50a3b768bed1c53d3c6ac41e4c`.

Source, wheel and all three new installed environments have matching Python-file
hashes. Existing environments and earlier artifacts were retained.
[Artifact provenance](receipts/voyage-artifact-2026-09-15.json)

| Check | Result |
|---|---|
| Installed wheel outside checkout, macOS arm64 / Python 3.10.11 | 442 passed |
| Installed wheel outside checkout, macOS arm64 / Python 3.12.13 | 442 passed |
| Current regression selection | 893 passed, 9 platform skips, 7 frozen-campaign cases excluded |
| Scope/hash/replay/budget mutation guards | All four removals detected |
| Dependency-free base wheel / CLI import | Passed; no Voyage/LanceDB/Attune extras imported |
| Dependency consistency | `pip check` passed in both Voyage environments |
| Live Voyage authentication / code embeddings | Passed: two document batches and one query embedding |
| Live standard reranker / end-to-end retrieval | Passed subsequent four-question check; original HTTP 429 run retained |
| Linux/Windows execution for the new extra | CI checks added; not run in this local session |
| Application-building benefit | Not measured; no routine-use promotion |

Installed receipts: [Python 3.10](receipts/voyage-artifact310-2026-09-15/platform.json),
[Python 3.12](receipts/voyage-artifact312-2026-09-15/platform.json).
Patrick's installation retest on September 15 passed all 442 installed checks
again on Python 3.10.11. All 34 Python modules still match source and wheel;
`pip check` found no broken requirements. The offline smoke plan remains ready
with zero provider calls. [Installation retest](receipts/voyage-install-retest-2026-09-15/platform.json).
The subsequent terminal-run smoke confirmed live embedding authentication;
reranking was initially rate-limited, as recorded below. The later
[focused accuracy check](voyage-accuracy-receipt.md) completed eight live requests:
correct supporting passage first for 3/3 answerable cases; absent-answer handling
remains unqualified. Actual provider token counts imply $0.00150586 at list rates.
Mutation evidence: [four guard removals](receipts/voyage-artifact-mutations-2026-09-15/mutations.json).
Full current regression output is retained in
[the regression log](receipts/voyage-artifact-regressions-2026-09-15.txt).

Seven historical `test_review_quality` cases require the immutable dev5 campaign
artifact and its original source hashes. Running them against this changed
checkout correctly refuses that provenance. They are excluded from the current
artifact regression selection; their manifests, receipts and frozen environment
were not rewritten to make a new package appear equivalent. The other 19 scorer
checks remain in the current regression selection.

Pinned integration: `voyageai==0.5.0`, `lancedb==0.38.0`, `pyarrow==25.0.1`,
`jsonschema==4.26.0`; 67 transitive constraints in
[`requirements-voyage.lock`](../requirements-voyage.lock). These are resolution
and local execution evidence, not a claim that all platform wheels were run.

## Decisions from probes

- The Voyage SDK has a second HTTP connection-retry layer even when client
  retries are zero. The adapter supplies a bounded, zero-retry session scoped
  to its current thread and restores the prior SDK session afterward.
- The SDK's high-level embedding object drops response indices. The adapter
  validates raw indices and restores input order before associating vectors
  with passages. Both embedding and rerank truncation are explicitly disabled.
- The SDK token counter downloads a moving tokenizer reference. Planning uses
  a labeled bytes/4 estimate; enforced controls are call/payload bounds, not a
  claimed hard dollar ceiling. Embedding-only heading/symbol context is bounded
  separately; source evidence retains its original bytes.
- The initial receipt limits remain: 8 MiB run records and 512 KiB participant
  requests. Vector batches and index metadata are stored outside review records.

## Live smoke result and retest

Patrick selected **attune-harness**. The local smoke configuration selects five
unchanged files: `adapters.py`, `github_checks.py`, `native.py`, `operations.py`
and `process.py`. Plan: **43 passages, 32,785 embedding-input bytes**, approximately
8,196 tokens, two indexing requests plus one query embedding and one rerank.
Estimated indexing cost is **$0.00098355**; the total smoke estimate is approximately
**$0.002**. Estimates exclude credits and do not assert exact token counts.

The API key was not visible in the agent's separate process. A key exported in
Patrick's project terminal is available to commands launched there. The prepared
command uses that terminal's environment and writes a local receipt:

```zsh
.venv-voyage/bin/python -I scripts/voyage_smoke.py \
  --config .pilot/voyage-smoke/config.json \
  --output .pilot/voyage-smoke/live \
  --allow-provider
```

Patrick ran the command at 18:49 UTC on September 15. The saved
[smoke receipt](../.pilot/voyage-smoke/live/receipt.json) reports failure because
the CLI stopped at reranking. Inspection of the durable stage records established:

- Both document embedding requests completed: 4,109 + 3,070 tokens. The index
  published all 43 passages; source and database integrity checks pass.
- The query embedding completed: 13 tokens. These three successful requests
  establish working credentials and live `voyage-code-4` compatibility.
- The `rerank-2.5` request raised the SDK's `RateLimitError` (HTTP 429). Its stage
  is retained as unresolved; reranking usage and billing remain unknown.
- Known successful usage totals 7,192 tokens, estimated at **$0.00086304** using
  the recorded list rate, before account credits. This is not a billing receipt
  or a full-run total.
- An offline `build_index` recheck reused the published generation with **zero
  provider calls**. No live retry was dispatched by the agent.

The SDK only retained the sanitized exception class, so the exact exceeded limit
is unknown. [Voyage's rate-limit guide](https://docs.voyageai.com/docs/rate-limits)
documents both organization and project limits. The new-account trial limit is a
possible explanation, not an observed account setting.

After the limit window has cleared, an explicit terminal retest can preserve the
failed run and reuse the existing index:

```zsh
.venv-voyage/bin/python -I scripts/voyage_smoke.py \
  --config .pilot/voyage-smoke/config.json \
  --output .pilot/voyage-smoke/live-retry-1 \
  --allow-provider
```

This is a new, deliberate attempt with one query embedding and one rerank, not a
resume or rewrite of the unresolved stage. Estimated additional list cost is
under $0.001; actual account limits and credits are not known. If rate limiting
persists, inspect the account's organization/project limits before another run.

Patrick subsequently authorized a separate four-question accuracy campaign and
clipboard credential use. That campaign completed with pacing and retained all
results in `.pilot/voyage-accuracy-2026-09-15/`; it did not run the alternative
`live-retry-1` command above. See the [accuracy receipt](voyage-accuracy-receipt.md)
for baseline comparison, exact answer support, costs and the absent-answer limit.

The current packet has 48 source
questions across 12 related symbol families, 12 absent-answer controls, and four
tuning questions. It does not replace matched application feature/fix trials.
See the [evaluation protocol](../experiments/voyage/README.md).

Usage and limitations: [Voyage setup](voyage-retrieval.md). Original scenario
pricing and comparison: [RAG options](rag-options-research-2026-09-15.md).
