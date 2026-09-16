# Voyage: 100-question Harness evaluation

September 15, 2026. Installed Harness `0.1.0.dev13`, `voyage-code-4`, and `rerank-2.5`.

**Completed:** 100 fresh questions — 80 answerable and 20 missing-answer controls — using the unchanged 98-file, 1,050-passage index. No reindexing.

## Retrieval results

A pass means every required claim has a complete, predeclared evidence alternative within the first k passages. Minimal exact source spans are required; a relevant filename alone is insufficient. Seven criteria accept a second valid evidence alternative. Five questions require evidence from two files; those claims must both be covered.

| Method | Full support in top 5 | Full support in top 10 |
|---|---:|---:|
| lexical_bm25 | 58/80 (72.5%) | 63/80 (78.8%) |
| hybrid | 71/80 (88.8%) | 75/80 (93.8%) |
| voyage_rerank | 75/80 (93.8%) | 76/80 (95.0%) |

Reranking versus hybrid: **6 gains and 2 losses** in complete top-five support. The 50-candidate hybrid pool contained full gold support for 78/80 questions.

## Capability breakdown

| Area | Questions | BM25 @5 | Hybrid @5 | Rerank @5 | Rerank @10 |
|---|---:|---:|---:|---:|---:|
| a2a | 8 | 7 | 8 | 8 | 8 |
| coding_host | 8 | 5 | 6 | 7 | 7 |
| coding_workflows | 8 | 4 | 5 | 6 | 6 |
| contracts | 7 | 6 | 7 | 7 | 7 |
| extensions | 6 | 4 | 5 | 5 | 5 |
| grounded_review | 7 | 6 | 7 | 7 | 7 |
| local_model | 7 | 5 | 7 | 6 | 7 |
| native_process | 6 | 5 | 6 | 6 | 6 |
| provider_integrity | 8 | 6 | 7 | 8 | 8 |
| recovery | 8 | 5 | 7 | 8 | 8 |
| source_index | 7 | 5 | 6 | 7 | 7 |

## Recommendation

Continue using Voyage embeddings and the standard reranker as a code-evidence provider in Harness and the optional Attune integration. This run supports that choice: reranking improves full-evidence retrieval over both baselines at a small measured API cost. Retain exact file/configuration lookup alongside it. This benchmark does not qualify an autonomous answerer or establish that coding tasks finish more successfully.

Prioritize two retrieval improvements: route exact package/schema questions to the relevant structured file; retrieve companion tests and expand the relevant implementation where a question needs both. The deduplication question (`n008`) missed its test in the candidate pool; the entry-point question (`n040`) missed `pyproject.toml`. The independent-review question (`n055`) found its test but lost the coordinator implementation during final ranking. The two scored losses versus hybrid (`n056`, `n067`) have the manual qualifications below, so they do not establish wrong answers.

Before claiming application-development benefit, use an unseen application and realistic bug/feature tasks, compare completion with and without retrieval, and judge the resulting code through tests and source review. Keep unsupported-question handling explicit in the caller; a similarity result is not proof that the requested feature exists.

## Missing-answer controls

**0/20 explicit automatic absence decisions.** These controls request features absent from the selected implementation, including remote JWT authentication, pgvector, OCR, and automatic embedding failover. Returning related candidates with `answer_support: not_established` does not determine that an answer is absent. This test contains no generated answers, so it does not measure hallucination frequency.

## Cost and efficiency

| Stage | API calls | Provider tokens | Cost before credits |
|---|---:|---:|---:|
| query_embeddings | 100 | 1,286 | $0.00015432 |
| reranking | 100 | 1,316,069 | $0.06580345 |

Total: **$0.065958** for 200 calls, with zero indexing calls. The sum of question runtimes was 8.9 minutes; median 5.32 seconds. All 200 HTTP responses succeeded and matched completed durable paid-stage receipts. No unresolved stages or automatic retries. Benchmark runtime includes repeated source-integrity checks, baseline computation and grading; it is not a production search-latency measurement.

Verified account limits were used from the start. Each query embedding served both the hybrid baseline and reranked result. Five separate 20-query work directories respected the unchanged configuration limit of 40 provider calls per work directory.

Illustrative monthly API costs at this sample’s measured average usage:

| Method | 1,000 searches | 10,000 searches |
|---|---:|---:|
| lexical_bm25 | $0.0000 | $0.0000 |
| hybrid | $0.0015 | $0.0154 |
| voyage_rerank | $0.6596 | $6.5958 |

These are provider-token estimates before account credits, not invoices. Local compute and answer generation are excluded. The earlier index build cost $0.019272; it was reused here. Index refresh costs depend on the selected source size and changed content.

## Diagnostic misses

- Gold support missing from the 50 candidates: n008, n040.
- Gold support available in candidates but incomplete after reranking to five: n055, n056, n067.
- Still incomplete after reranking to ten: n055, n056.

These are frozen-rubric misses. A result may contain other valid evidence that was not anticipated; such cases must be noted without rewriting this run’s scores.

Manual qualifications: `n056` retrieved the extension artifact guard and a test exercising in-call mutation, but missed the exact post-callback guard invocation selected by the oracle. That supporting alternative was not predeclared. `n067` already shows the requested 512-token framing reserve at rank two, with corroborating tests; the extra remaining-context formula demanded by its oracle appears at rank six and is unnecessary to answer the question. Neither frozen top-five miss establishes a wrong generated answer. Scores remain unchanged; see the [separate manual review](../.pilot/voyage-100-2026-09-15/manual-review.json).

## Interpretation and limits

The larger set gives a broader diagnostic and a finer score increment: each answerable question changes the score by 1.25 percentage points. It does not establish population precision. Questions were authored and reviewed by the same assistant with source knowledge, are clustered by topic, and emphasize explicit implementation behaviors and guards. They are not a random independent sample of application-development requests. Each capability has only 6–8 cases, so its percentage remains coarse.

Questions, expected answers, alternatives, scoring rules and runner hashes were frozen before the first new provider request. All gold spans were checked locally. Scorer checks exercised partial evidence, required bundles, alternative evidence, top-k limits, wrong paths/repositories and duplicates. Nine selected behavior tests passed against the installed package. All 35 installed Harness modules matched their indexed source hashes. All returned source evidence passed byte/hash validation.

The earlier 20-case set remains unchanged. Its stricter and occasionally overspecified rubric differs from this one; percentages are not a before/after improvement claim. Neither experiment measures generated-answer correctness, successful code changes, real application usefulness, or performance on another repository. The lexical baseline is passage BM25, not an experienced developer using ripgrep or an agent making several searches.

## Artifacts

- [Frozen questions and expected answers](../.pilot/voyage-100-2026-09-15/questions.md)
- [Freeze: source identity, gold spans and code hashes](../.pilot/voyage-100-2026-09-15/freeze.json)
- [Raw results and original retrieved excerpts](../.pilot/voyage-100-2026-09-15/results.json)
- [Machine-readable summary and receipt audit](../.pilot/voyage-100-2026-09-15/summary.json)
- [Expected-behavior tests](../.pilot/voyage-100-2026-09-15/expected-behavior-tests.xml)
- [Installed module/source audit](../.pilot/voyage-100-2026-09-15/installed-code-audit.json)
- [Prior 20-question evaluation](voyage-full-code-evaluation.md)

## Case results

| Case | BM25 @5 / @10 | Hybrid @5 / @10 | Rerank @5 / @10 |
|---|---|---|---|
| n001 — What form must the requirements of an accepted Task take? | miss / pass | pass / pass | pass / pass |
| n002 — When the independent verifier rejects valid participant output, which terminal status does the core executor return? | pass / pass | pass / pass | pass / pass |
| n003 — Does a verifier failure discard the participant output already obtained? | pass / pass | pass / pass | pass / pass |
| n004 — How does the JSON adapter reject duplicate object keys during decoding? | pass / pass | pass / pass | pass / pass |
| n005 — Can the same JSON participant dispatch twice after its first exchange throws an error? | pass / pass | pass / pass | pass / pass |
| n006 — If the wrong task is supplied to a JSON participant, is its one allowed attempt consumed? | pass / pass | pass / pass | pass / pass |
| n007 — Is the JSON response size limit measured in characters or UTF-8 bytes? | pass / pass | pass / pass | pass / pass |
| n008 — How are repeated failing check runs at one commit deduplicated, and which test shows a new commit is treated separately? | miss / miss | miss / miss | miss / miss |
| n009 — What must a Claude CLI result envelope report before its structured answer is accepted? | pass / pass | pass / pass | pass / pass |
| n010 — Will the Codex event decoder accept additional events after a terminal completion? | pass / pass | pass / pass | pass / pass |
| n011 — Which arguments run the native Codex CLI in a read-only, temporary session? | pass / pass | pass / pass | pass / pass |
| n012 — How does the GitHub checks importer detect an incomplete paginated export? | pass / pass | pass / pass | pass / pass |
| n013 — Why does an ordinary failed GitHub check with no classified cause request human review? | miss / miss | miss / pass | pass / pass |
| n014 — What happens to subprocess descendants when the direct child has already exited? | miss / miss | pass / pass | pass / pass |
| n015 — How does process supervision divide its output byte allowance between stdout and stderr? | pass / pass | pass / pass | pass / pass |
| n016 — What failure is recorded when subprocess output is not valid UTF-8, and how are diagnostics returned? | pass / pass | pass / pass | pass / pass |
| n017 — Which script can reconstruct the frozen E3 source workspace while verifying every copied file hash? | pass / pass | pass / pass | pass / pass |
| n018 — May structured configuration files be selected through wildcard paths? | pass / pass | pass / pass | pass / pass |
| n019 — What must be enabled before indexing modified tracked source files? | pass / pass | pass / pass | pass / pass |
| n020 — How does the repository snapshot discover eligible untracked files when they are allowed? | pass / pass | pass / pass | pass / pass |
| n021 — What chunking fallback is used when Python source cannot be parsed? | miss / miss | miss / pass | pass / pass |
| n022 — How does the chunker avoid splitting a multibyte UTF-8 character in an overlong source line? | pass / pass | pass / pass | pass / pass |
| n023 — Does a Markdown heading inside a fenced code block create a new section boundary? | pass / pass | pass / pass | pass / pass |
| n024 — What text is prepended to each original passage for embedding? | miss / miss | pass / pass | pass / pass |
| n025 — What kinds of invalid embedding vectors are rejected? | pass / pass | pass / pass | pass / pass |
| n026 — How are embedding responses matched back to input passages if the provider returns rows out of order? | pass / pass | pass / pass | pass / pass |
| n027 — How is missing provider token usage represented in a paid-stage cost receipt? | pass / pass | pass / pass | pass / pass |
| n028 — Can a redirect response send a Voyage request to a different endpoint? | miss / miss | miss / pass | pass / pass |
| n029 — What bounds the amount of response data read from the Voyage API? | pass / pass | pass / pass | pass / pass |
| n030 — What prevents a missing provider ledger from silently resetting billing history? | pass / pass | pass / pass | pass / pass |
| n031 — Which durable paid-stage state is written immediately before invoking the provider? | miss / miss | pass / pass | pass / pass |
| n032 — How does a replayed completed provider stage report newly consumed tokens and cost? | pass / pass | pass / pass | pass / pass |
| n033 — Is a newly generated coding retrieval task accepted automatically? | pass / pass | pass / pass | pass / pass |
| n034 — What range of retrieval calls can be granted to a coding principal in a task? | pass / pass | pass / pass | pass / pass |
| n035 — Can an MCP coding retrieval task be combined with a separate configuration file? | pass / pass | pass / pass | pass / pass |
| n036 — What happens if a launched retrieval session sees its accepted task or grants edited? | pass / pass | pass / pass | pass / pass |
| n037 — Does the repository-evidence Attune plugin register any generation workflows? | miss / miss | miss / pass | pass / pass |
| n038 — How does the Attune plugin avoid registering its MCP tool over an existing handler? | pass / pass | pass / pass | pass / pass |
| n039 — How does the repository-evidence plugin handle an exception from a search call? | miss / pass | pass / pass | pass / pass |
| n040 — What command-line entry point does the Harness package declare? | miss / miss | miss / miss | miss / miss |
| n041 — Why is a copied review run not allowed to resume under a new directory? | miss / miss | pass / pass | pass / pass |
| n042 — When a recovery operation budget is reached, is the completed operation saved before the pause? | pass / pass | pass / pass | pass / pass |
| n043 — How many explicit read-only attempts may a reconciled review operation have? | pass / pass | pass / pass | pass / pass |
| n044 — Can an operator supply a recovered reply for an unresolved tool operation? | pass / pass | pass / pass | pass / pass |
| n045 — Can leadership transfer after the independent reviewer starts executing? | pass / pass | pass / pass | pass / pass |
| n046 — Does cancellation roll back pending external effects of a review? | pass / pass | pass / pass | pass / pass |
| n047 — How is a persisted running review presented during read-only inspection? | miss / pass | pass / pass | pass / pass |
| n048 — How are review record writes made durable before replacing the current record? | miss / miss | miss / miss | pass / pass |
| n049 — What evidence must accompany an economics-ledger attempt labeled as a verified repair? | pass / pass | pass / pass | pass / pass |
| n050 — Which operation bindings may a version-one extension declare? | miss / pass | pass / pass | pass / pass |
| n051 — Can an extension refer to a skill file outside its bundle? | pass / pass | pass / pass | pass / pass |
| n052 — What prevents changing extension state from an outdated checkpoint? | pass / pass | pass / pass | pass / pass |
| n053 — What conditions must hold when replacing an installed extension bundle? | miss / miss | miss / miss | pass / pass |
| n054 — Can a removed extension registration simply be reenabled? | pass / pass | pass / pass | pass / pass |
| n055 — How is a reviewer prevented from inheriting the lead participant history, and which test checks the independent context? | miss / miss | miss / miss | miss / miss |
| n056 — What detects an extension bundle changing while its scoped retrieval call is running? | pass / pass | pass / pass | miss / miss |
| n057 — May the document being reviewed serve as its own corroborating reference? | pass / pass | pass / pass | pass / pass |
| n058 — What happens when two retrieved references have the same identity but disagree in hash or excerpt? | pass / pass | pass / pass | pass / pass |
| n059 — Can a quoted grounded review cite text absent from the retrieved reference excerpt? | pass / pass | pass / pass | pass / pass |
| n060 — How is the review verdict determined when at least one assessment is a contradiction? | pass / pass | pass / pass | pass / pass |
| n061 — Where is a repeated citation pair prevented from counting as another passage assessment? | pass / pass | pass / pass | pass / pass |
| n062 — How are paragraph offsets within a retrieved excerpt converted to original source byte offsets? | miss / miss | pass / pass | pass / pass |
| n063 — Can a model invent its own citation IDs in the host-owned passage review? | pass / pass | pass / pass | pass / pass |
| n064 — Where does a review stop before a participant exceeds its tool-call budget, and which regression verifies there is only one invocation? | miss / miss | pass / pass | pass / pass |
| n065 — Does the local model HTTP client honor system proxy configuration? | miss / miss | pass / pass | pass / pass |
| n066 — What input accounting is used when no qualified local tokenizer is selected? | pass / pass | pass / pass | pass / pass |
| n067 — How much context is reserved for framing in local generation? | miss / miss | pass / pass | miss / pass |
| n068 — What happens if the local model artifact changes during a generation? | pass / pass | pass / pass | pass / pass |
| n069 — Can local generation download a missing pinned model automatically? | pass / pass | pass / pass | pass / pass |
| n070 — What does local generation do when the server input count disagrees with the qualified tokenizer? | pass / pass | pass / pass | pass / pass |
| n071 — Which rollback demonstration restores the later package in a finally block and verifies the original pilot files stayed unchanged? | pass / pass | pass / pass | pass / pass |
| n072 — Which output conditions distinguish a completed local generation from a truncated response? | pass / pass | pass / pass | pass / pass |
| n073 — What network address form is allowed for a local A2A peer? | miss / pass | pass / pass | pass / pass |
| n074 — How does the local A2A client bind a peer to its expected agent card? | pass / pass | pass / pass | pass / pass |
| n075 — Will the local A2A profile accept a peer that requires authentication? | pass / pass | pass / pass | pass / pass |
| n076 — What correlates an A2A JSON-RPC reply to the request? | pass / pass | pass / pass | pass / pass |
| n077 — Can a completed A2A artifact be supplied as a URL for Harness to download? | pass / pass | pass / pass | pass / pass |
| n078 — Can a peer change its task ID or context ID after acknowledging a task? | pass / pass | pass / pass | pass / pass |
| n079 — What should follow an already-attempted A2A cancellation whose outcome is uncertain? | pass / pass | pass / pass | pass / pass |
| n080 — How does A2A dispatch react after run persistence has failed? | pass / pass | pass / pass | pass / pass |
| n081 — Which Harness routine indexes an AST call graph so a query can traverse callers and callees? | absent control | absent control | absent control |
| n082 — Where does Harness deploy its retrieval service to Kubernetes and configure autoscaling? | absent control | absent control | absent control |
| n083 — Which Kafka consumer turns repository events into incremental index updates? | absent control | absent control | absent control |
| n084 — How does the Voyage index upload its vector database to Amazon S3? | absent control | absent control | absent control |
| n085 — Which Azure Blob synchronization function downloads repository index generations? | absent control | absent control | absent control |
| n086 — Where is the PostgreSQL pgvector backend selected for code similarity search? | absent control | absent control | absent control |
| n087 — Which routine rotates encryption keys for vector data encrypted at rest? | absent control | absent control | absent control |
| n088 — Where does the MCP server validate a remote client JWT before allowing retrieval? | absent control | absent control | absent control |
| n089 — Which OCR pipeline converts scanned PDF pages into code-search passages? | absent control | absent control | absent control |
| n090 — How are screenshot images sent for multimodal repository embeddings? | absent control | absent control | absent control |
| n091 — Which live SQL database connection verifies generated migration queries against production tables? | absent control | absent control | absent control |
| n092 — Where does Harness use browser automation to test a generated web application? | absent control | absent control | absent control |
| n093 — Which Jira OAuth handler turns review findings into new remote tickets? | absent control | absent control | absent control |
| n094 — Which WebSocket endpoint streams review tokens to a dashboard? | absent control | absent control | absent control |
| n095 — How does a Voyage outage automatically switch embeddings to a second provider? | absent control | absent control | absent control |
| n096 — Where are user relevance votes used to retrain the reranker automatically? | absent control | absent control | absent control |
| n097 — Which function records audio and transcribes spoken coding requests? | absent control | absent control | absent control |
| n098 — Where does an LDAP group lookup determine retrieval permissions? | absent control | absent control | absent control |
| n099 — How does Harness send email notifications when an index build finishes? | absent control | absent control | absent control |
| n100 — Which GraphQL resolver exposes repository evidence to third-party clients? | absent control | absent control | absent control |
