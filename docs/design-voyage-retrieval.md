# Voyage application retrieval: implementation design

September 15, 2026. Implements the approved focused plan on
`codex/voyage-retrieval`, starting at `6bece93`. Live quality qualification is
separate from implementation checks.

## Contracts and cases

1. Offline `index plan` reads explicitly selected Git roots and extensions;
   tracked files are the default. Dirty tracked bytes require explicit overlay
   selection; untracked files require their own selection. JSON ledgers are
   excluded. Reject symlinks, escapes, non-UTF-8 files and exceeded bounds.
2. Preserve source bytes, including CRLF and Unicode. Python symbol boundaries,
   Markdown headings/fences and bounded line splits produce independently
   hashed passages with original byte offsets. Context used for embedding is
   separate from evidence. Repository IDs disambiguate duplicate paths.
3. A generation binds the exact manifest, passages and algorithm configuration.
   Build/update checkpoints embedding batches before publishing a local LanceDB
   table. Reuse identical embedding inputs across generations; never modify an
   existing generation. Empty and unchanged indexes incur no provider calls.
4. Accepted retrieval configuration pins generation and scope. Both vector and
   lexical candidates receive the same exact scope filter. Identifier matching
   supplements full-text search; explicit RRF deduplicates before at most 50
   passages reach `rerank-2.5`. Check current source bytes before and after work.
5. Persist paid stage dispatch before sending and validate/save its response.
   Completed stages can replay; uncertain dispatch is unresolved and is never
   retried as read-only. Same-run repeated queries reuse evidence and record
   zero new usage. Enforce accepted call and byte budgets before dispatch.
6. Preserve legacy schema/form digests and the keyword backend. A new retrieval
   profile integrates coding-only CLI/MCP intake and optional review registries.
   Evidence identities include original positions; distinct passages in one
   file remain distinct. Structured check and economics tools stay deterministic.

## Scratch experiments actually run

Disposable `.venv-voyage`, macOS arm64, Python 3.10.11:

- Installed `voyageai==0.5.0`, `lancedb==0.38.0`, `pyarrow==25.0.1`.
- Created and reopened a real two-row LanceDB table; row count remained two.
- Full-text `read_record` filtered to repo `a` returned only its row; cosine
  vector search filtered to repo `b` returned only its row (distance 1.0).
- Qualified the current `create_index(..., config=FTS(...))` API with stemming,
  stop-word removal and ASCII folding disabled. `checkpoint_digest` matched.
- A UTF-8/CRLF example containing `é` and `💡` round-tripped exact byte slices.
- SDK inspection: explicit `max_retries=0`, finite timeout, document/query input
  type and dimensions supported; embedding/rerank truncation defaults true, so
  the adapter must pass false. `count_tokens` downloads a tokenizer from a moving
  Hugging Face model reference. Do not silently download it during offline plans.

Python 3.12 and Linux/Windows execution remain CI qualification targets; local
experiments above do not establish those platforms or live model compatibility.

## Decisions and rejected alternatives

- Keep `voyage-code-4` and 1024 floats for both code and docs: a single query
  embedding space. Do not substitute a preview reranker.
- Use a versioned byte-bounded chunker with a bytes/4 **advisory** token estimate
  until the model tokenizer artifact is qualified. This preserves offline
  planning and bounded requests without pretending to enforce a USD ceiling.
- Store large provider stage results outside the 8 MiB run record, with hashes;
  keep dispatch/usage and replay pointers in the record. Do not inflate review
  checkpoints with vectors or silently repeat billed operations after crashes.
- Do not replace field queries with embeddings, rely on file prefixes for code
  evidence, rebuild implicitly, or fall back to keywords after provider failure.
- Shared retrieval implementation supplies CLI, MCP and review delegates;
  launcher-selected paths and grants cannot be widened by tool arguments.

## Verification matrix

Offline tests cover config rejection, source scope/drift, byte offsets, multiple
repos, updates/deletions, empty sets, ranking/filtering with real LanceDB and
injected providers, malformed responses, budget exhaustion, uncertain dispatch,
completed-stage replay, accepted coding intake, review/MCP integration and legacy
regressions. Installed-wheel checks run outside the checkout. A separate frozen
application-task evaluator records ranking and coding outcomes only when run;
no fake-provider test constitutes a retrieval-quality measurement.
