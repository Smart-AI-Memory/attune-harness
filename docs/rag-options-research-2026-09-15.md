# RAG options for Attune Harness

Research refreshed: September 15, 2026. Public prices are USD.

Scope: refresh the comparison, recommendation, and cost analysis for code and documentation across Attune repositories. This report evaluates quality-oriented candidates, including managed cloud; it does not claim measured superiority on Attune data. Research used public primary sources and local source inspection. No provider experiment, upload, installation, or runtime change was performed.

**Product focus clarified:** Attune assists AI users building applications through
vibe engineering. Retrieval should supply the coding agent with relevant source,
tests, interfaces, requirements, and selected documentation from the application
being built. Attune repositories can serve as test projects. Internal structured
records support execution and verification; their prevalence does not determine
whether semantic code retrieval is useful.

## Recommendation

**Evaluate Voyage code embeddings plus lexical search and a dedicated reranker first. Use LanceDB for a single-workspace experiment; use Qdrant when the index needs to serve multiple processes or machines.** Compare Google embeddings, OpenAI managed retrieval, and an open-weight baseline before adoption. Keep Harness responsible for accepted scope, evidence records, verification, and recovery.

The recommendation is about the retrieval pipeline; neither database has demonstrated better relevance on Attune data. An embedded evaluation keeps the first measurement independent of a paid database commitment while retaining semantic search, lexical search, and reranking. [LanceDB hybrid search](https://docs.lancedb.com/search/hybrid-search), [Qdrant hybrid queries](https://qdrant.tech/documentation/search/hybrid-queries/)

The proposed stack is:

- **Code:** `voyage-code-4`, built specifically for code and coding-agent retrieval. Its August 2026 release and vendor evaluation justify testing it first; the vendor's results do not establish Attune performance. [Voyage release and evaluation](https://blog.voyageai.com/2026/08/13/voyage-code-4/)
- **Documentation:** compare `voyage-context-4` against using the code model for everything. Contextual embeddings encode each passage with its surrounding document. Use separate indexes and matching query embeddings when models differ. Adopt the extra model only if its documentation gains justify the complexity. [Contextualized embeddings](https://docs.voyageai.com/docs/contextualized-chunk-embeddings)
- **Search:** combine semantic and lexical candidates, deduplicate them, then rerank original passages. LanceDB supports vector/full-text fusion; Qdrant supports dense/sparse fusion and multi-stage queries. Both require a deliberate lexical representation for code identifiers. [LanceDB hybrid search](https://docs.lancedb.com/search/hybrid-search), [Qdrant hybrid queries](https://qdrant.tech/documentation/search/hybrid-queries/)
- **Reranking:** use `rerank-2.5` as the established comparison point and test `rerank-3`, still marked **preview**, if available. A reranker reads the query and candidate passages together and reorders them. Test a lite model separately for cost and latency; equal quality is unproven. [Voyage rerankers](https://docs.voyageai.com/docs/reranker)

**Cost implication:** the shared workload below costs **$1.20 for initial Voyage embedding**, then **$1.63/month at 1,000 searches** or **$15.24/month at 10,000 searches** in embedding and reranking charges. Add database/compute, generation, and maintenance. These are calculated scenarios, not measured Attune usage. Reranking depth and hosting matter more to these totals than the difference between Voyage and Google embedding prices. See [cost comparison](#cost-comparison).

Strongest counter-case: this requires owning chunking, synchronization, index lifecycle, and several service boundaries. OpenAI's managed retrieval could match its quality with substantially less maintenance. That is why OpenAI belongs in the initial comparison.

**Structured-data fit:** apply Voyage to semantic discovery in code, documents,
and selected descriptive fields. Keep exact status/revision checks, schema
validation, and cost arithmetic in Harness's existing structured capabilities;
[`operations.py`](../src/attune_harness/operations.py) and
[`github_checks.py`](../src/attune_harness/github_checks.py) already perform
those operations deterministically. Mixed searches can constrain repository,
revision, or other typed metadata before ranking relevant text.
[LanceDB filtering](https://docs.lancedb.com/search/filtering)
Measure representative coding tasks before broad adoption. Compare against
direct file inspection and exact symbol/lexical search, especially for small
or new applications where indexing may add little value.
The cost scenarios count paid semantic searches, not every Harness operation.

### Changes in this refresh

- Separate the single-workspace database choice from the shared-service choice.
- Add initial indexing, monthly updates, query embeddings, reranking, storage, and model-generation boundaries to the cost comparison.
- Add `voyage-4-nano` as a local embedding challenger and distinguish its documented compatibility from the code/context models.
- Price Google RAG Engine's database commitment explicitly; avoid a guessed Qdrant production price or unverified promotional credits.

## What Harness has today

Rechecked Harness source at `6bece93`, on local `main`. The designated `.venv-platforms` environment contains `attune-harness==0.1.0.dev11` and `attune-rag==1.2.0`; Harness pins that RAG version in its optional extras. The sibling attune-rag checkout carries unrelated edits. Its inspected source is evidence of reusable capabilities, not proof that every capability is qualified in Harness's installed artifact.

| Observed behavior | Consequence for this project |
|---|---|
| Harness constructs `DirectoryCorpus` and `KeywordRetriever` directly. | Semantic/hybrid retrieval is not currently selectable. |
| It selects only `**/*.md`, up to 1,000 files and 16 MiB. | Source-code indexing and federated repository scope need explicit support. |
| Each returned excerpt is `entry.content[:500]`. | Even a correct file match can omit the relevant passage. |
| Results preserve source hashes and a corpus version. | New backends must retain traceable evidence. |
| Acceptance and recovery snapshot Markdown sources and recheck local paths. | A cloud backend cannot simply return remote IDs in the current schema. |

Sources: [retrieval adapter](/Users/patrickroebuck/attune-harness/src/attune_harness/retrieval.py:15), [review coordinator](/Users/patrickroebuck/attune-harness/src/attune_harness/review.py:16), [recovery snapshot](/Users/patrickroebuck/attune-harness/src/attune_harness/recovery.py:36).

attune-rag already implements `HybridRetriever` and `TransformerRetriever`. However, its default embedding representation includes only the first 1,000 body characters, and its hybrid implementation can fall back to keyword results after an embedding `RuntimeError`. Reuse is worth measuring, but an explicitly selected Harness backend needs to report missing/degraded capability visibly. Enabling embeddings alone does not solve passage coverage. Sources: [hybrid implementation](/Users/patrickroebuck/attune-rag/src/attune_rag/hybrid.py:21), [embedding representation](/Users/patrickroebuck/attune-rag/src/attune_rag/embedding.py:103), [transformer implementation](/Users/patrickroebuck/attune-rag/src/attune_rag/transformer.py:49).

## Provider comparison

These are assessments of suitability, not benchmark rankings. Embeddings, search databases, and complete RAG services occupy different layers and can be combined.

### OpenAI: Retrieval API and File Search

OpenAI supports direct vector-store search returning relevant chunks, with metadata filters, configurable ranking, optional query rewriting, and semantic/keyword fusion weights. Uploaded files are automatically chunked and indexed. The separate File Search tool invokes retrieval inside a model workflow. [Retrieval guide](https://developers.openai.com/api/docs/guides/retrieval), [File Search guide](https://developers.openai.com/api/docs/guides/tools-file-search)

**Fit:** strongest simple managed challenger. Use direct retrieval and pass its evidence to whichever lead/reviewer Harness selected; this avoids making an OpenAI-generated answer the retrieval result.

**Tradeoff:** Harness still needs an ingestion manifest linking remote file/chunk identifiers to repository revision, original bytes, and source locations. OpenAI documents eventual consistency after file removal. An old remote result must fail the accepted source-version check. This costs some of the simplicity of outsourcing ingestion. [Vector-store lifecycle](https://developers.openai.com/api/docs/guides/retrieval#vector-store-file-operations)

### Anthropic: Contextual Retrieval plus an external retrieval stack

Anthropic's documentation says it does not provide its own embedding model and describes Voyage as one available provider. Voyage is a separate provider, not an Anthropic-hosted vector database. [Anthropic embeddings guide](https://platform.claude.com/docs/en/build-with-claude/embeddings)

Anthropic's Contextual Retrieval technique adds document-specific context to chunks before semantic and BM25 indexing, then optionally reranks. Its published evaluation reports improvements, but those are specific to its experiment. [Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval)

**Fit:** adopt the context-preservation idea. For Attune, first add deterministic repository, path, enclosing class/function, and heading context. Compare generated context only as a separate experiment. Generated summaries should remain index aids; cited evidence must point to original code or prose.

### Google: three distinct choices

| Option | What it supplies | Assessment for Harness |
|---|---|---|
| Gemini Embedding 2 | Embeddings usable with an independent search backend; supports text and multimodal inputs. | Strong embedding challenger with the same Qdrant/chunking setup. |
| RAG Engine, formerly under Vertex AI and now documented under Gemini Enterprise Agent Platform | Managed ingestion and retrieval; `retrieveContexts` exposes evidence separately from generation. | Suitable managed backend, particularly if sources and operations already live in Google Cloud. |
| Gemini API File Search | Managed file ingestion and search integrated into Gemini model calls, with citations and metadata filtering. | Convenient for a Gemini document assistant; a less direct fit for Harness's host-owned retrieval and multiple model providers. |

Sources: [Google embeddings](https://ai.google.dev/gemini-api/docs/embeddings), [RAG Engine overview](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/rag-engine/rag-overview), [retrieval endpoint](https://docs.cloud.google.com/gemini-enterprise-agent-platform/reference/rest/v1/projects.locations/retrieveContexts), [File Search](https://ai.google.dev/gemini-api/docs/file-search).

Implementation detail that matters: Gemini Embedding 2 uses task instructions in text rather than the older model's `task_type` parameter. Its embedding space also differs from `gemini-embedding-001`; switching requires reindexing. [Migration guidance](https://ai.google.dev/gemini-api/docs/embeddings#migration-from-gemini-embedding-001)

RAG Engine's current retrieval reference supports one corpus, or files within one corpus, per request. A cross-repository adapter would need a shared corpus with appropriate scoping or explicit federation. Its managed vector-storage choices can also introduce Spanner charges. [Retrieval scope](https://docs.cloud.google.com/gemini-enterprise-agent-platform/reference/rest/v1/projects.locations/retrieveContexts), [RAG Engine billing](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/rag-engine/rag-engine-billing)

## Open-source and open-weight options

| Candidate | Relevant capability | Recommended role |
|---|---|---|
| **Qdrant** | Dense/sparse fusion; local development mode, server, and managed cloud deployment. | Preferred search service candidate for shared repository retrieval. Local client mode is for development/testing, not evidence of production concurrency behavior. |
| **LanceDB** | Embedded open-source retrieval with vector/full-text search and reranker integration. | Preferred first experiment when one local process/workspace owns the index. It can use the same hosted embedding models as Qdrant. |
| **Qwen3 Embedding + Reranker** | Open-weight model families with 0.6B, 4B, and 8B variants and instruction-aware retrieval. | Independent self-hosted quality baseline. Compare a larger variant if hardware permits; use 0.6B as a resource baseline, not an assumed quality ceiling. |
| **Voyage 4 Nano** | Open-weight embedding model with a documented shared space with `voyage-4-large`, `voyage-4`, and `voyage-4-lite`. | Additional local baseline; test hosted document embeddings with local query embeddings only within that documented compatible family and matching dimensions. |
| **PostgreSQL + pgvector** | Vector search combined with PostgreSQL full-text search, with fusion or cross-encoder ranking. | Attractive if an existing PostgreSQL deployment already owns the corpus; otherwise another database to operate. |
| **Haystack components** | Reusable retrievers and document-list fusion, including reciprocal rank fusion. | Optional pipeline plumbing; add it only if it removes substantial adapter code. Harness already coordinates participants and recovery. |

Sources: [Qdrant client and deployment modes](https://github.com/qdrant/qdrant-client), [LanceDB repository](https://github.com/lancedb/lancedb), [LanceDB hybrid search](https://docs.lancedb.com/search/hybrid-search), [Qwen model family](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B), [Qwen reranker](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B), [pgvector hybrid search](https://github.com/pgvector/pgvector#hybrid-search), [Haystack DocumentJoiner](https://docs.haystack.deepset.ai/docs/documentjoiner).

The Nano model card names the four general-purpose Voyage 4 models in its compatibility claim. It does not establish compatibility with `voyage-code-4` or `voyage-context-4`; do not substitute Nano queries into those indexes on the strength of the shared family name. A hosted-document/local-query arrangement still sends documents to the embedding provider during indexing. [Voyage 4 Nano model card](https://huggingface.co/voyageai/voyage-4-nano)

Qdrant versus LanceDB is primarily an operational choice. Compare relevance with identical chunks, vectors, filters, and ranking before crediting either storage engine with a quality improvement.

## Cost comparison

### Published rates

Checked September 15, 2026. M means one million billed tokens. Prices exclude taxes, negotiated discounts, and promotional credits.

| Component | Published rate or cost basis |
|---|---|
| Voyage code/context embeddings | $0.12/M for `voyage-code-4` and `voyage-context-4`. |
| Voyage reranking | $0.05/M for `rerank-2.5` and preview `rerank-3`; $0.02/M for their lite variants. |
| Gemini Embedding 2, Developer API | Text: $0.20/M standard; $0.10/M batch. |
| OpenAI vector stores | $0.10/GiB/day beyond the first 1 GiB across all stores. |
| OpenAI File Search in Responses | $2.50/1,000 tool calls, plus model tokens and storage. |
| Gemini File Search | Indexing charged at the selected embedding model's rate; storage and query embeddings free; retrieved context and generation billed. |

Sources: [Voyage pricing](https://docs.voyageai.com/docs/pricing), [Google embedding prices](https://ai.google.dev/gemini-api/docs/pricing#gemini-embedding-2), [OpenAI pricing](https://developers.openai.com/api/docs/pricing), [Gemini File Search pricing](https://ai.google.dev/gemini-api/docs/file-search#pricing).

**Credit caveat:** Voyage's prose and tables disagree about reranker free-token allowances. Budget at list price until account eligibility is confirmed. Its Batch API advertises a 33% discount and excludes free credits; batching is a separate ingestion optimization. [Voyage pricing](https://docs.voyageai.com/docs/pricing)

### Shared workload assumptions

These are illustrative workloads for the proposed cross-repository system, not measurements of current Harness usage or its existing Markdown limit:

- Initial index: **10M billed embedding tokens**, including added context and overlap.
- Monthly refresh: **1M billed embedding tokens** for updates, including any surrounding content re-embedded with changed passages.
- Two usage levels: **1,000 or 10,000 searches/month**; one embedding request and one reranking request per search.
- Each query: **100 tokens**. Each reranking request: **50 candidate passages averaging 500 tokens each**.
- Code and documentation are indexed once each; the totals above cover both. The first table assumes one query embedding space. Searching two model-specific indexes needs another query embedding.
- A 30-day billing month. Provider tokenizers may count the same source differently; replace these nominal volumes with usage receipts during evaluation.

Voyage bills reranking as query tokens repeated for each candidate plus all candidate tokens. Here that is `50 × (100 + 500) = 30,000` tokens per search. The candidate count is the number submitted, even if only five results are returned. [Reranker accounting](https://docs.voyageai.com/docs/reranker)

### Comparable custom pipelines

These rows use the same candidate budget and a locally computed lexical index. They compare service charges, not demonstrated retrieval quality. Add database/compute and the chosen Harness participant models to every row.

| Pipeline | Initial embedding | Monthly service subtotal: 1,000 searches | Monthly service subtotal: 10,000 searches |
|---|---:|---:|---:|
| **Voyage code/context + `rerank-2.5`** | **$1.20** | **$1.63** | **$15.24** |
| Gemini Embedding 2 + the same Voyage reranker | $2.00 | $1.72 | $15.40 |
| Voyage code/context + `rerank-2.5-lite` | $1.20 | $0.73 | $6.24 |
| Qwen3 embeddings + Qwen3 reranker, self-hosted | $0 API fees + compute | $0 API fees + compute | $0 API fees + compute |
| Current Harness keyword retrieval | $0 API fees | $0 API fees + local compute | $0 API fees + local compute |

Monthly subtotals include updates, query embeddings, and reranking. They exclude the initial embedding charge. For the recommended row at 10,000 searches: `$0.12 updates + $0.12 queries + $15.00 reranking = $15.24`. First month including initial embedding is **$16.44**; at 1,000 searches it is **$2.83**. Figures are rounded only after calculation. The existing keyword row is a cost baseline with a narrower supported task, not an equivalent semantic retriever.

Using a separate code and context query embedding for every search adds **$0.012/month at 1,000 searches**, or **$0.12 at 10,000**. Indexing every source in both models would also duplicate its embedding volume. A local Nano embedding baseline still needs a lexical index and a separately selected reranker.

### Database and managed-service costs

| Choice | Monthly cost to add or compare | Interpretation |
|---|---|---|
| LanceDB OSS on existing hardware | Local compute, storage, backups, and maintenance; no managed database subscription. | Preferred single-workspace experiment. Hosted embeddings/reranking still incur the charges above. |
| Qdrant Cloud prototype | $0 database charge within its single-node 0.5-vCPU, 1-GB-RAM, 4-GB-disk tier. | Capacity and workload suitability remain unmeasured; this tier has no high availability. |
| Qdrant Cloud production | Add a deployment-specific amount **D** to the custom-pipeline subtotal. | Public pricing is resource-based. Obtain a region/capacity quote; do not treat the prototype price as production pricing. |
| OpenAI direct vector-store retrieval | Published storage charge **S**; the retrieval guide lists no separate indexing or direct-search request price. | Model generation is separate. The Responses File Search tool fee does not describe this endpoint. |
| OpenAI Responses File Search | **S + $2.50** at 1,000 tool calls, or **S + $25.00** at 10,000; add model tokens. | Assumes one tool call per search. Multiple tool calls in a model workflow multiply the fee. |
| Gemini File Search with Embedding 2 selected | **$2.00 initial indexing + $0.20/month updates**, plus Gemini context/generation tokens. | No storage/query-embedding charge; this subtotal omits the required model workflow and is not a complete cost per answer. |
| Google RAG Engine with Basic managed DB | Example: **$88.56/month compute**, plus database storage/backups, embeddings, ranking, parsing, and any transfer charges. | Assumes 100 processing units of Spanner Enterprise in Iowa for 720 hours; region and configuration matter. |

Sources: [LanceDB OSS](https://github.com/lancedb/lancedb), [Qdrant tiers and pricing](https://qdrant.tech/pricing/), [OpenAI direct retrieval pricing](https://developers.openai.com/api/docs/guides/retrieval#pricing), [OpenAI tool pricing](https://developers.openai.com/api/docs/pricing), [Gemini File Search](https://ai.google.dev/gemini-api/docs/file-search), [Google embedding rates](https://ai.google.dev/gemini-api/docs/pricing#gemini-embedding-2), [RAG Engine billing](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/rag-engine/rag-engine-billing), [Spanner regional pricing](https://cloud.google.com/spanner/pricing).

**OpenAI storage example:** assuming the free allowance is otherwise unused, `S = max(total indexed GiB − 1, 0) × $0.10 × 30`. That gives **$0 at 1 GiB, $12 at 5 GiB, or $27 at 10 GiB**. These sizes are independent sensitivity examples, not a conversion from the 10M-token corpus. Billing uses parsed chunks plus embeddings, not repository source bytes. [Storage definition](https://developers.openai.com/api/docs/guides/retrieval#pricing)

**Google database example:** Basic provisions 100 processing units; Scaled starts at 1,000. Spanner's Iowa Enterprise list rate is $1.23/node-hour, with 1,000 processing units per node. Thus Basic compute is `0.1 × $1.23 × 720 = $88.56`; Scaled starts at **$885.60/month compute** under the same assumptions. These are configured examples, not a universal minimum for every RAG Engine storage choice. [RAG-managed tiers](https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/rag-engine/rag-engine-billing), [Spanner rates](https://cloud.google.com/spanner/pricing)

### What changes the decision

1. **Reranking depth:** at 10,000 searches, submitting 20, 50, or 100 passages costs $6, $15, or $30 in standard Voyage reranking under the same token assumptions. Reducing depth or choosing lite needs a recall check; returning fewer results alone does not reduce submitted-token cost.
2. **Hosting:** the recommended custom pipeline totals `$15.24 + D` before generation and labor at 10,000 searches. A dedicated service can dominate the inference subtotal; measure whether a shared service is needed before committing to it.
3. **Maintenance:** total operating cost is `service charges + hardware/energy + maintenance hours × hourly value`. Those hours and local inference throughput have not been measured. An assumed one hour valued at $100 would outweigh the embedding-price difference; this is sensitivity arithmetic, not an effort estimate.
4. **Generation and retries:** add input, cached-input, output, and any separately billed reasoning tokens for the actual lead/reviewer models. At 10,000 searches, passing five 500-token passages once contributes 25M input tokens; passing them independently to two roles contributes 50M before other prompts. Provider-managed answer generation may add a model call if Harness still uses its own participants afterward.

**Cost-aware recommendation:** preserve the strongest quality candidate and start with an embedded index. At these volumes the Voyage-versus-Google embedding difference is cents per month; quality and integration evidence should decide. Keep OpenAI direct retrieval as the managed cost/maintenance challenger, Qwen3 as the fully local challenger, and RAG Engine for a demonstrated Google Cloud integration benefit. Compare total spend per verified useful result before adopting any candidate.

## Proposed Harness integration

```text
Accepted repository revisions and file hashes
                    |
       Code symbols / Markdown sections
                    |
    Lexical search + semantic passage search
                    |
       Merge candidates by rank; rerank
                    |
     Original passages + precise source refs
                    |
       Harness verification and reviewers
```

1. **Add a retrieval backend interface behind the existing tool.** Return evidence through one Harness-owned result schema. Keep provider dependencies optional. Retrieval can serve any participant model.
2. **Expand corpus intake deliberately.** Enumerate selected repositories and file types. Separate committed revisions from working-tree overlays using a manifest of actual file hashes. Do not silently search every branch or local directory.
3. **Index useful units.** Code chunks should follow functions/classes with bounded surrounding context; documentation chunks should follow headings. Retain repository, revision, path, line/byte span, file hash, and passage hash. Return the matched passage rather than a fixed file prefix.
4. **Record index provenance.** Bind the corpus manifest, chunker version, embedding model/dimensions, backend, and ranking configuration to acceptance. Keep incompatible vector spaces separate and combine their ranked results. Use mixed embedding models only where compatibility is documented and qualified in the selected configuration.
5. **Preserve recovery semantics.** Update acceptance, snapshot validation, result validation, and resume together. Reuse stored evidence on resume; a live remote query is new work. Report stale/missing indexes and failed ranking stages explicitly.
6. **Treat indexing as a separate operation.** Hosted indexing sends selected content to providers and changes remote state. Implement explicit indexing and index-selection flows; retrieval must not quietly upload or rebuild a corpus.

For repair tasks, retrieval helps locate code; it does not prove a fix. Independent tests remain the acceptance evidence.

## Evaluation that would decide adoption

Proposed first campaign: **60 held-out questions**, ten each for exact identifiers, natural-language bug symptoms, code/document relationships across repos, long-file evidence beyond the prefix, stale/contradictory versions, and absent answers. Use a separate small tuning set. Freeze repository snapshots and expected evidence before running candidates.

Compare:

1. Current Harness keyword/prefix behavior on its supported Markdown subset.
2. A shared passage corpus with lexical retrieval only, including literal symbol/path lookup for code.
3. Existing attune-rag semantic/hybrid capabilities on a compatible corpus.
4. Voyage code/context embeddings + reranking on the selected shared passage backend: LanceDB for the single-workspace experiment, Qdrant for shared-service evaluation.
5. OpenAI direct managed retrieval.
6. Gemini Embedding 2 and Qwen3 on that same backend, using the same passage corpus and retrieval budget; add Voyage 4 Nano as a local embedding comparison.

Treat unsupported code cases in the existing baseline as unsupported, not as a comparable accuracy score. First vary embeddings while holding ranking constant; then test rerankers and contextualization separately. Set fusion parameters explicitly rather than inheriting different library defaults. Keep a separate end-to-end comparison for managed services that own their chunking/ranking.

Measure relevant-passage recall@5/10, first useful hit, graded ranking quality (nDCG@10), unsupported-answer rejection, wrong-revision hits, valid source locations, p50/p95 latency, indexing time, and complete cost. Record billed ingestion/query/reranking tokens, stored bytes, model calls, retries, and operating effort so the cost scenarios can be replaced with measured costs per verified useful result. Include index update/deletion and interrupted-run checks. A high relevance score is not a calibrated confidence of correctness.

Inspect a smaller downstream review set using the same participant models and context budget. Better retrieval must also reduce missed evidence or unsupported findings; extra context can otherwise conceal the benefit.

For Attune's application-building purpose, also compare matched feature/fix tasks
with fixed coding-agent models and budgets. Measure independently accepted code
changes, regressions, time, and total cost. Include a competent direct-file and
symbol-search baseline; document-review results alone do not qualify this use.

**Proposed promotion rule:** choose the candidate with the strongest held-out evidence retrieval and downstream review results, subject to zero accepted wrong-revision/out-of-scope citations and no newly introduced critical misses. Report ties and uncertainty. Use latency, operating effort, and cost to distinguish similarly accurate candidates; do not select a winner solely from the vendor's leaderboard.

## Decision summary

- **First quality candidate:** Voyage code embeddings and `rerank-2.5`; compare contextual document embeddings and preview `rerank-3` separately.
- **First database:** LanceDB for one workspace/process; Qdrant for a shared service. Storage-engine relevance differences remain unmeasured.
- **Service-cost scenario:** $1.20 initial Voyage embedding; $1.63/month at 1,000 searches or $15.24 at 10,000, plus infrastructure, generation, and labor under the assumptions above.
- **Managed challenger:** OpenAI direct retrieval, with published storage pricing and a source-provenance adapter.
- **Google challenger:** Gemini Embedding 2 on the same backend; RAG Engine if managed ingestion justifies its configuration and database costs.
- **Self-hosted challenger:** Qwen3 embeddings/reranking; Voyage 4 Nano as another local embedding candidate.
- **Immediate architectural priority:** source-aware passages and a versioned retrieval contract. These improvements are necessary regardless of the eventual provider.

The comparison and cost arithmetic are refreshed. Provider access, installation compatibility, workload volumes, operating effort, and Attune-specific quality remain to be established by the proposed experiment. No candidate is promoted to Harness's runtime by this report.

Patrick selected the Voyage plus standard-reranker option for implementation
planning. See the [phased implementation plan](voyage-retrieval-implementation-plan.md)
for the proposed LanceDB integration, acceptance criteria, recovery behavior, and
cost accounting.
