# Voyage retrieval: verified assessment and next increment

September 15, 2026. **Evaluation and planning only.** The lookup API and campaign
below are proposals; production retrieval behavior is unchanged.

## Recommendation

Keep **hybrid candidate retrieval followed by `rerank-2.5`** as the current
default. Implement **an explicitly granted, bounded exact file/range lookup
within the accepted index** next. This gives a coding agent a reliable way to
read a package manifest, schema, implementation, or test once it knows the path.

An explicit hybrid-only mode merits a later controlled comparison. Conditional
reranking is premature: there is no validated rule for deciding when skipping
the reranker preserves useful evidence. Neither a high similarity score nor a
large score gap proves answer support.

The smallest concrete implementation is scoped exact lookup. The most important
remaining product validation is completed bug/feature work on a real application.
Prepare that evaluation alongside implementation; another Harness question score
cannot substitute for it.

## Verified state

- Checkout: `codex/voyage-retrieval`, HEAD
  `6bece93e8d5ddae3205d394b9b9c90d4408b8ee3`. Substantial existing modified and
  untracked work was present. This audit adds only this document and its receipts.
- Isolated interpreter: `/Users/patrickroebuck/attune-harness/.venv-code-rag/bin/python`.
  Imports resolve to that environment's installed package, not `src/`.
  Versions: Harness `0.1.0.dev13`, Attune AI `16.4.0`, MCP `1.29.1`,
  Voyage SDK `0.5.0`, LanceDB `0.38.0`.
- All **35 installed Python modules** match both checkout and indexed source
  hashes. The **98-file, 1,050-passage** generation remains fresh. Publication,
  source manifest, passage identity, and database row integrity checks passed.
  Generation: `434ba693f76dfb50e00b37c376271e44d2b10ab56f2b9a1c8ecdf3c0ce81336e`.
- Frozen runner hashes and oracle passed preflight. All 300 stored variant grades
  were recomputed and **3,000 returned passages** matched their original metadata,
  source bytes, and hashes. The 200 recorded stages are completed, with 200
  recorded HTTP 200 responses. Both experiment directories stayed unchanged
  during the audit: 468 files, excluding Python bytecode caches.
- **73 tests passed against the installed package:** 61 retrieval/integration/host
  cases, plus the nine recorded behavior cases and three evaluator cases.
  A separate real Attune MCP subprocess discovered `code_evidence_query`, returned
  explicit insufficient evidence for an empty selected code set, and closed cleanly.
  These checks used zero live provider calls. One host deprecation warning occurred.
- The optional bridge works when explicitly launched. This session's available
  tools contain legacy `rag_knowledge_query`, not `code_evidence_query`; the local
  Codex configuration contains no Harness bridge reference. The configuration
  check is text presence only, not proof about every running host. No desktop
  switch, legacy-package replacement, or general workflow migration was performed.

Evidence: [offline audit and measurements](receipts/voyage-next-increment-2026-09-15/audit.json),
[audit experiment](receipts/voyage-next-increment-2026-09-15/audit.py),
[61-case JUnit](receipts/voyage-next-increment-2026-09-15/installed-tests.xml),
[12-case JUnit](receipts/voyage-next-increment-2026-09-15/behavior-tests.xml),
[MCP subprocess receipt](receipts/voyage-next-increment-2026-09-15/host-receipt.json).
The installed environment inherits existing Attune dependencies; this is not a
clean dependency-resolution or cross-platform qualification.

## What the implementation does

[`candidates()`](../src/attune_harness/voyage_retrieval.py) combines a scoped dense
search with lexical full-text search and exact **word-token overlap**, using
reciprocal-rank fusion. Token overlap is not exact file lookup, schema validation,
or a relationship between implementation and test. The accepted configuration
limits the final candidate pool to 50.

`retrieve_voyage()` embeds the query, collects candidates, and always reranks a
nonempty pool. Its returned count is the requested `k`; the Python default is
three, while the recorded evaluation requested ten and scored prefixes of five
and ten. Reranked top five is therefore an evaluated operating point, not a claim
that every installed caller currently requests five. There is no public
hybrid-only/conditional mode.

[`voyage_sources.py`](../src/attune_harness/voyage_sources.py) explicitly selects
structured files, excludes environment paths, and chunks original source bytes.
[`voyage_index.py`](../src/attune_harness/voyage_index.py) checks accepted generation
identity and live source/database integrity. The current code repeats full
generation validation at several boundaries. This could matter at larger scale;
the audit did not isolate its latency or justify weakening it.

[`retrieval_task.py`](../src/attune_harness/retrieval_task.py) accepts finite
retrieve-only grants. [`RetrievalSession`](../src/attune_harness/mcp_server.py)
fixes scope, checks accepted task changes, and records invocations.
[`CodeEvidencePlugin`](../src/attune_harness/attune_bridge.py) uses that session and
adds no generation workflows. [`StageJournal`](../src/attune_harness/voyage_provider.py)
records dispatch before paid work, reuses completed stages, and refuses automatic
retry of an unresolved paid stage. Missing usage remains unknown.

## Quality, charges, latency, and context are separate

### Retrieval evidence

| Method | Complete frozen support @5 | @10 |
|---|---:|---:|
| Passage BM25 | 58/80 | 63/80 |
| Hybrid | 71/80 | 75/80 |
| Hybrid + reranking | 75/80 | 76/80 |

Reranking has six top-five gains and two losses against hybrid. Preserve the
scores. Separately, `n056` has an unanticipated supporting alternative, and `n067`
already answers the framing-reserve question but misses an unnecessary formula
required by its oracle. See the unchanged [manual qualifications](../.pilot/voyage-100-2026-09-15/manual-review.json).

Hybrid @10 and rerank @5 both score 75/80, but pass different cases: rerank alone
passes `n048` and `n053`; hybrid alone passes `n056` and `n067` under this rubric.
Equal aggregates do not establish interchangeable evidence.

All 20 missing-answer controls returned candidates with
`answer_support: not_established`; none made an explicit absence decision.
No generated answer or patch was scored. Assistant-authored, source-informed
questions are diagnostic evidence, not a random or independent sample of real
coding work. Passage BM25 also understates what an agent can do with repeated
`rg`, file reads, and test runs.

### Voyage charges

| Method | API estimate / 1,000 searches | / 10,000 searches |
|---|---:|---:|
| Hybrid | $0.001543 | $0.015432 |
| Hybrid + reranking | $0.659578 | $6.595777 |

The original 100 searches used 1,286 query-embedding tokens and 1,316,069 rerank
tokens: **$0.06595777** at the frozen rates, excluding credits. The reused index's
previously recorded build cost is $0.019272. New indexing, local compute, and
coding-model usage are separate.

Voyage's current table agrees with the recorded $0.12/million embedding tokens
for `voyage-code-4` and $0.05/million rerank tokens for `rerank-2.5`.
Rerank billing counts the query for every candidate plus all candidate-document
tokens; returning five instead of ten from the same 50 documents does not halve
that input charge. [Official pricing](https://docs.voyageai.com/docs/pricing),
[reranker API semantics](https://docs.voyageai.com/docs/reranker).

### Observed latency boundaries

**Follow-up:** the [latency assessment](voyage-latency-assessment-2026-09-15.md)
adds a 20-query offline timing probe. Repeated full-index validation accounts for
3.16 of 3.22 local seconds in a shared-session query with saved provider responses.
It separates those measurements from historical live-provider timings and
illustrative end-to-end estimates.

| Historical paid stage | Median | p95, nearest rank |
|---|---:|---:|
| Query embedding | 0.211 s | 0.276 s |
| Reranking | 0.327 s | 0.404 s |

These are saved provider-wrapper durations, including any campaign pacing and
response validation. They are not isolated network latency or a production
hybrid-versus-rerank timing experiment. The whole benchmark took 531.3 seconds;
its 5.32-second median question includes repeated checks, baselines, and scoring.
Do not promise that skipping reranking saves exactly 0.327 seconds end to end.

### Measured extra answer context

This audit rendered each saved passage as `repo:path:start-end` plus the original
excerpt. It measured UTF-8 bytes without calling a generation model.

| Mean per query | Hybrid @10 | Rerank @5 | Extra for hybrid |
|---|---:|---:|---:|
| Cited source text, all 100 | 12,424.54 B | 5,848.73 B | 6,575.81 B |
| Cited source text, answerable 80 | 12,318.01 B | 5,571.33 B | 6,746.69 B |
| Full source-object JSON, all 100 | 18,017.70 B | 9,226.95 B | 8,790.75 B |

Hybrid @10 carries **2.12 times** the cited text across all questions. JSON is
reported separately because hosts may pass full tool results, including hashes
and scores. Neither representation includes the complete surrounding prompt.

Actual downstream token cost is not measured: no coding model/tokenizer has been
selected. Let `D` be the measured extra input tokens under that tokenizer and
`P` its effective dollars per million input tokens. Then per query:

`hybrid@10 total - rerank@5 total = -$0.0006580345 + D × P / 1,000,000`

This comparison holds other model usage equal and excludes output differences.
For a sensitivity illustration only, bytes/4 estimates `D ≈ 1,644`; the input
price crossover is about **$0.40/million tokens**. At an illustrative $1/million,
the extra input would cost about $1.644 per 1,000 searches, versus $0.658 saved
in reranking. This is not a model price quote or tokenizer measurement. Caching,
repeated inclusion in later turns, compaction, and changed output can alter it.
Measure actual serialized prompts and usage in the coding trial.

## Diagnosed gaps and chosen scope

| Case | Verified mechanism | Implication |
|---|---|---|
| `n008` | `operations.py` support is candidate 1; required `test_operations.py` support is absent from 50. The selected test file is 4,854 bytes / 11 passages. | Companion-test discovery is missing; reranking alone cannot fix it. |
| `n040` | Selected `pyproject.toml` is 846 bytes / one passage, contains the exact script entry, and is absent from 50. | Small authoritative files can lose to semantically similar code. |
| `n055` | Required `review.py` implementation is candidate 11; required test is candidate 33. The test becomes rerank result 1, while implementation drops out of ten. | Need to preserve complementary evidence, not just related test passages. |

The proposed lookup can read all three missing source components **when the caller
supplies the right path/range**. That is a local feasibility observation, not a
new retrieval score. In particular, `n040` does not name `pyproject.toml`; the
lookup API alone cannot repair the original natural-language question. Tool
guidance should direct agents to inspect selected package manifests for package
declarations. Ordinary agent file reads remain a valid alternative.

Implementation/test expansion is the next candidate after lookup. It needs
evidence for language-specific mapping, ambiguous test names, and protection of
both sides under a context budget. Adding neighboring chunks alone would not
discover `n008`'s separate file. Unbounded expansion would increase context cost.

## Bounded implementation plan — proposed, not built

**One increment:** add `read_evidence(repo_id, path, start_line?, end_line?)`,
exposed as `harness.read_evidence` and optional Attune `code_evidence_read`, plus
an equivalent CLI operation. It reads only original passages in the caller's
accepted generation. It makes zero embedding/rerank calls and does not change
the existing query algorithm, models, index profile, or automatic routing.

1. Add a small local lookup module. Require an exact repository-relative path;
   apply accepted repository and path exclusions before selecting passages.
   Return existing immutable passages in source order, with their current
   revision, line/byte ranges, and hashes. No filesystem fallback outside the
   indexed manifest and no basename guessing across repositories.
2. With no range, return the complete selected file only if it fits the limits.
   With a range, return whole existing passages that overlap it; explicitly
   report requested and returned ranges. Validate positive integer, ordered line
   bounds. Proposed limits: 20 passages, 16 KiB total excerpt bytes, and the
   existing 192 KiB response ceiling. Reject over-limit requests with a
   narrow-range instruction and file line count; never silently truncate.
3. Reuse generation and byte validation before returning evidence. An unavailable
   path yields generic `no_results` in the accepted scope. Do not distinguish an
   excluded existing file from an unselected/missing one. Out-of-scope repository
   IDs and invalid path syntax are rejected before reads of that target.
   `answer_support` remains `not_established` for nonempty evidence. Reading a
   schema supplies text; it does not execute or validate that schema.
4. Extend task preparation to accept an **optional explicit `read_evidence`
   grant**. Keep existing retrieve-only templates and accepted tasks valid and
   unchanged. Bind lookup operation, repository, path, range, scope, and generation
   into durable event/cache identity. Count reads against the same finite
   participant tool budget; mark their effect as local read-only. Provider
   permission is unnecessary for the lookup itself.
5. Dispatch through the existing session and adapter lifecycle. Publish its
   separate input/output schema only to a principal granted that operation.
   Preserve closed-session, changed-request, persistence-failure, and lease
   behavior. Query failures with unknown paid effects still stop the paid path;
   lookup must never become an implicit fallback or retry.

Likely files: new `voyage_lookup.py`; focused edits to `retrieval_task.py`,
`mcp_server.py`, `attune_bridge.py`, and the CLI/schema definitions; focused tests
and usage documentation. No broad retrieval refactor. This document is the design
note before that production change.

### Acceptance tests for that increment

| Case prepared before implementation | Required observable result |
|---|---|
| Fresh fixture with a tiny selected `pyproject.toml` and competing CLI code | Exact manifest lookup returns its real declaration with correct bytes; a provider stub that raises on any call is never invoked. |
| Same relative path in two accepted repositories | Explicit repository selects only that repository; unauthorized repository fails without target reads. |
| Indexed file excluded by task scope; missing file; unselected structured file | No source bytes leak and no fallback scan; identical generic no-results shape for paths unavailable in scope. |
| Absolute path, traversal, backslash/drive path, glob, source or parent symlink | Rejected; zero provider calls. |
| Unicode and a line crossing passage boundaries | Returned original chunks cover the requested range, hashes and byte offsets match; reported bounds disclose whole-chunk expansion. |
| Boolean/zero/negative/reversed range; range outside file; excessive response | Invalid inputs rejected; outside-file range returns no results; oversized selection asks for a narrower range without partial evidence. |
| Same-length source edit, revision change, or database-row tampering | Freshness validation fails, including repeat reads; no stale success. |
| Accepted task changes or scope override in call arguments | Rejected before lookup; caller cannot replace configuration or generation. |
| Retrieve-only task versus newly accepted lookup grant | Old task and schemas continue to work; lookup is exposed/invocable only for the new grant. |
| Mixed reads/queries and replay exhaust a two-call grant | Third call denied; replay consumes the tool budget but adds no provider charge; operation identities cannot collide. |
| Failed persistence, closed plugin, interrupted lifecycle | No further dispatch after persistence failure or closure; durable session state remains honest. |
| Existing unknown rerank billing receipt | No automatic retry or hidden exact-lookup fallback. |
| Real CLI, Harness MCP, and Attune MCP installed-wheel paths | Same scope/byte behavior; discoverable schemas; clean shutdown; zero live provider calls. |

Use new fixture names and paths to test the general contract. Keep `n008`, `n040`,
and `n055` as explicitly known regressions; any tuning on them is development
work. Record guard-removal checks for scope, freshness, and call-budget tests as
`N/M fail with the guard removed` in the ordinary suite receipt.

Alternatives deferred: automatic schema-intent routing (no validated classifier),
implementation/test expansion (a separate discovery and packing problem), and
hybrid-only/conditional modes (do not address candidate misses and lack coding
outcome/latency qualification). Exact lookup is especially useful for MCP-only
clients; it may add little to an agent already using scoped native file reads.

## Next validation: application coding outcomes

**Preparation status:** protocol ready; application repository and real tasks
unselected. Patrick has been asked for the local repository path. No application
source upload, index build, or model campaign is authorized by this document.

### Proposed first pilot

Use six genuine application tasks, ideally three bugs and three features drawn
from existing work, at a pinned source revision. Favor observable behavior across
implementation, tests, and configuration. Do not invent tasks solely to reward
lookup. For each task, freeze the following before any agent attempt:

- Problem statement, expected behavior, reproduction, allowed change scope, and
  the baseline commit. For a bug, its acceptance test must fail for the intended
  reason at baseline. For a feature, demonstrate the behavior is missing.
- Acceptance and regression commands, independent hidden assertions, test hashes,
  prohibited workarounds (for example disabling a check), and a review rubric.
- A finite run time, output/token budget, allowed tools, retrieval call limit,
  and the selected coding model/version and sampling settings.

Run two arms, two fresh attempts per task: **24 coding runs**. Both arms receive
the same task, model, repository snapshot, normal `rg`/file-reading/test tools,
and budget. Arm A has no Voyage retrieval. Arm B has the current hybrid-plus-
rerank query tool with `k=5`, at most eight queries. Run the proposed lookup
feature as a separate subsequent treatment, so the first pilot isolates current
retrieval rather than attributing a combined feature change to reranking.

Randomize/counterbalance arm order, isolate workspaces and agent histories, and
do not transfer patches, grader feedback, or retrieval answers between attempts.
Keep frozen hidden tests, expected solutions, run outputs, and evaluation answers
outside the indexed source selection. Existing application tests remain in scope.
Freeze each index selection explicitly; adding a test or script can invalidate
the current broad source globs even without modifying existing files.

**Coding edits and freshness:** each run gets an immutable source snapshot for
retrieval plus a separate editable checkout at the same starting revision.
Citations identify the baseline snapshot. The agent must inspect the current
working file before editing or claiming changed behavior. No implicit reindexing
during a run. This avoids the current stale-index guard stopping every later
query after the first code edit, while making baseline evidence limits explicit.

Primary result: a completed patch passes the frozen acceptance tests and relevant
regression tests, without prohibited workarounds, and passes source review with
arm identity hidden where practical. Report per-task paired wins/losses, both
attempts, unresolved cases, and failures; six tasks cannot establish population
performance. Secondary measures: time to accepted patch, invalid edits, test
iterations, context bytes/tokens actually delivered, total coding-model usage,
Voyage usage, and source-verification failures. Capture unsupported claims in the
actual final explanations; the old 20 controls did not measure hallucination.

Measure query stages separately: integrity checks, embedding, candidate search,
reranking, serialization, and whole-call latency; record cold/warm/replay status
and p50/p95. Do not subtract the old benchmark runtime to estimate speedup.

### Later hybrid-only comparison and authorization packet

If the pilot shows useful coding benefit, add a third arm with explicitly
labelled experimental hybrid-only retrieval. Compare at a common evidence-byte
budget first, then compare practical hybrid @10 versus rerank @5 with measured
downstream costs. Its result/cache identities must include mode, and it must
retain all source, scope, budget, and paid-stage controls. Do not promote it to
production merely because skipping a stage is cheaper. A conditional rule would
then need calibration on development tasks and a separate untouched validation
set, with explicit reporting of when and why it reranked.

Before any live campaign, prepare the selected repository/revision, exact file
manifest and hashes, exclusions, upload text/byte limits, index plan, query and
candidate upload scope, model settings, finite calls/tokens/dollar limits, and
unknown-billing stop behavior for authorization. The existing approval covered
the completed campaign only.

For the proposed two-arm pilot, the retrieval arm has **at most 96 queries**:
12 runs × eight queries, or at most 96 query embeddings and 96 reranks, plus
separately planned indexing. At the old query mix this would be approximately
**$0.06332 in search API charges**, not a ceiling or application-specific quote.
Actual indexing cost remains unknown until repository selection; use its local
`index plan`. Coding-model cost remains unknown until model, budgets, and billing
arrangement are specified, and can dominate retrieval. Those unresolved amounts
must appear in the concrete authorization packet; they are not excluded from
total cost.

## Reproduce the audit without paid work

Run from outside the checkout with `-I`, giving the script a new output filename:

```sh
/Users/patrickroebuck/attune-harness/.venv-code-rag/bin/python -I \
  /Users/patrickroebuck/attune-harness/docs/receipts/voyage-next-increment-2026-09-15/audit.py \
  /private/tmp/voyage-assessment-audit-new.json
```

The script refuses to overwrite an output, verifies the frozen sources, and
never invokes a provider. A later legitimate source change should fail the
frozen freshness check; preserve these receipts rather than rewriting history.
