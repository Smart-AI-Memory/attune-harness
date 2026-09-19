# Design: reuse the immediately checked generation

Proposed production change; the only implementation so far is a disposable copy
under `.pilot/validation-bottleneck-20260916/prototype/`.

## Task 1: approved implementation baseline

The task ladder is now approved. Before production edits, Task 1 added
`experiments/voyage/profile_validation.py` and 35 behavioral/probe cases to
`tests/test_voyage.py`. The complete Voyage file passed 79 tests. All 36 current
package modules still match the archived baseline from
`ce61c18ac396c91e5441ac34f218e41c942df593` (see the exact Git identity in the raw
receipt; the probe also records every imported module hash).

The new portable probe prepared its own 105-file, 1,050-passage fixture from a
fresh source archive containing no historical `.pilot` data. It creates
deterministic synthetic 1,024-dimensional vectors with real LanceDB, and seeds
completed local stage receipts. Live provider construction raises an error.
Measured calls run without provider permission and assert zero new calls/tokens/
cost, exact evidence including scores and byte offsets, and the expected cache
state. Fixture content hashes before and after measurement must match.

Baseline results from six fixed queries, each in a fresh direct/session work
directory:

| Path | Mean warm offline time | Full checks per call |
|---|---:|---:|
| Direct recomputation from completed stages | 1.992 s | 4 |
| Direct final-result replay | 1.463 s | 3 |
| Session setup | 0.489 s | 1 |
| Session recomputation from completed stages | 2.967 s | 6 |
| Session final-result replay | 2.427 s | 5 |

These are baseline observations only. No production speedup has yet been measured.
The probe records all samples, nested check timings/callers, dependency versions,
interpreter, module hashes and fixture identity. Optional small-fixture switches
serve its subprocess behavior test; acceptance measurements use the defaults.
It refuses existing fixture/output directories. Fixture preparation, stage
copying, imports and teardown are outside timed calls. Task 3 will run both
variant orders in separate processes and qualify an installed wheel.

Exact Task 1 commands, from the repository root after preparing the fresh source
archive and copying only the new probe into it:

```sh
.venv-code-rag/bin/python .pilot/validation-reuse-task1-20260916/baseline-source/experiments/voyage/profile_validation.py prepare \
  --source .pilot/validation-reuse-task1-20260916/baseline-source \
  --workspace .pilot/validation-reuse-task1-20260916/fixture
.venv-code-rag/bin/python .pilot/validation-reuse-task1-20260916/baseline-source/experiments/voyage/profile_validation.py measure \
  --source .pilot/validation-reuse-task1-20260916/baseline-source \
  --workspace .pilot/validation-reuse-task1-20260916/fixture \
  --output .pilot/validation-reuse-task1-20260916/baseline-first
```

For a fresh clone, the same probe can prepare new data with `--source .`; it has
no dependency on these ignored receipts. Omit `--source` when intentionally
measuring an installed wheel outside the checkout.

New failure-sensitive cases target these guards:

| Guard | New behavior exercised |
|---|---|
| Public selection validation | Returns the original object, performs a full check, rejects malformed fields, digest/path changes, invalid generation and foreign scope before creating work or calling a provider. |
| Fresh source manifest/revision | Equal-length edit to an unrelated source, revision-only commit, newly selected file and deletion; all repeated with an existing final cache. |
| Publication and semantic row digest | Modified metadata/publication, changed table text and changed vectors; fresh calls and cache replay both refuse before provider dispatch. |
| Guard before reranking | Source, vector or metadata changes introduced by embedding or candidate search stop before rerank. Completed stage receipts remain inspectable. |
| Final evidence guard | The same changes introduced by reranking, or while reading a final-cache record, prevent evidence delivery. |
| Offline fixture contract | Fresh-directory CLI subprocesses prove exact baseline counts and evidence/stage replay; both fixture and measurement overwrites are refused. |

Existing tests continue covering scope filtering, zero-result scope, budgets,
completed-stage reuse, unknown paid effects and persistence failures. The broader
session/plugin/recovery consumers are part of Task 2's regression selection.

Raw Task 1 identity, fixture and measurements are under
`.pilot/validation-reuse-task1-20260916/`; the suite receipt is
`docs/receipts/validation-bottleneck-20260916/task1-voyage-tests.xml`.
All 468 preserved historical files were rehashed unchanged.

A disposable baseline copy with the semantic row-digest guard removed caused
**8/35 new tests to fail** (27 passed); these are the expected text/vector boundary
failures, not failures of the working implementation. Its JUnit evidence is
`docs/receipts/validation-bottleneck-20260916/task1-row-mutation.xml`.
Production files were never mutated. Task 2 will repeat targeted mutations for
the changed implementation, including the other retained guards.

## Verified mechanism and proposed seam

At merged commit `7eabe5821aaf484276909e13f116a4ffe2bdaed4`, retrieval calls
`load_selection(selection)`, which runs a full `check_generation`. Its next
operation runs that same full check to obtain the directory and metadata. There
is only a local config lookup between them. Full validation reads publication
metadata, snapshots selected source/Git state, and loads and hashes database rows.

Extract a private helper which performs the existing selection validations and
returns the checked directory and metadata. Retain the public `load_selection`
wrapper, including its full validation and input-object return. Retrieval calls
the helper once and uses that returned metadata. The prototype names the helper
`_checked_selection`; the name is an implementation proposal.

The helper result stays within one synchronous retrieval entry. It is never
cached between invocations or supplied by an untrusted caller. The ordinary
selection dictionary is still used for bindings and receipt identities.

Keep every other full check: session pre/post-dispatch, before reranking after
candidate search, and final evidence validation. Keep the independent byte checks
for returned source excerpts. Neither callback work nor filesystem/database reads
move between the existing guards. This preserves the existing observed boundaries;
it does not create atomicity against arbitrary concurrent filesystem writes.

## Cases to establish before production edits

| Case | Required evidence |
|---|---|
| Fresh direct retrieval; cached result; completed-stage replay | Identical passage IDs, excerpts, scores, usage and replay semantics, ignoring nondeterministic receipt IDs/timestamps. |
| Public selection validation; invalid config/digest/scope | Same valid return contract and rejected invalid inputs; no work/provider dispatch on rejection. |
| Source change before call or during a provider stage | Rejection at the relevant retained pre/post boundary, including cache replay and equal-length edits. |
| Revision-only change; selected file addition/deletion | Freshness rejection even if a previously returned excerpt is unchanged. |
| Publication, metadata, row-text or vector tampering | Full verification still rejects alteration; caching never masks a second-call change. |
| Restricted or empty scope | Scope remains enforced before reranking; empty selection returns no evidence without provider work. |
| Budget exhaustion, unknown billing, changed grants, closure, persistence failure | Existing error and durable lifecycle behavior remain unchanged. |

## Experiments completed for planning

Both variants were extracted from the same merged Git commit and run with the
same Python/dependencies in separate processes. The new fixture has 105 tracked
Python files, 1,050 passages and deterministic nonzero 1,024-dimensional float
vectors in real LanceDB. Fake provider responses were created locally, then copied
as completed stage records. Measurement disables provider permission and replaces
live-client construction with an error. No service or model was called.

Six fixed queries each measured candidate recomputation followed by final-result
replay, with k=10. Fixture preparation, imports, session setup, stage copying and
teardown are outside call timings. Session setup is measured separately.

| Mean warm offline boundary | Baseline | Disposable prototype | Full checks |
|---|---:|---:|---|
| Session candidate recomputation | 3.098 s | 2.624 s | 6 to 5 |
| Session final-result replay | 2.559 s | 2.064 s | 5 to 4 |
| Session setup | 0.507 s | 0.511 s | 1 in both |

All 12 outputs per variant match the fixture's expected passage order. Recompute
time fell 15.3% and replay 19.3% in this small, ordered sample. This is a feasibility
result, not a production latency promise, semantic-quality result, installed-wheel
qualification or randomized experiment. Baseline ran first; reverse-order testing
remains part of implementation acceptance.

Baseline full checks used 3.035 of 3.098 seconds per recomputed call (97.9%). Their
row loading/hashing used 2.556 seconds. A separate one-check profile spent 0.400
of 0.523 seconds in JSON encoding. These are nested observations, not additive
timing categories. Candidate search averaged 0.032 seconds.

The existing Voyage, code-RAG and integration selection passed **68 tests in each
source snapshot**, with one existing ModelTier deprecation warning per run. These
are regression/feasibility checks, not the new boundary tests, targeted mutations,
full suite or installed-artifact qualification required by the task ladder.

Raw experiment, exact module hashes, call stacks and samples are local under
`docs/receipts/validation-bottleneck-20260916/` and
`.pilot/validation-bottleneck-20260916/fixture/`. Promote a standalone reproducible
measurement script in Task 1; fresh clones cannot depend on these ignored files.

## Alternatives and priority

- **Session-wide validation reuse:** larger possible saving, but spans mutable
  state and extension/provider callbacks. Defer until a separately specified
  invalidation contract can preserve all boundaries.
- **Binary/vector-specific row hashing:** profiling suggests greater potential,
  but changes publication and compatibility rules. Investigate after this small
  compatible change; do not silently reinterpret existing row digests.
- **Exact file/range lookup:** useful for callers that know a path, but whole-index
  validation would retain this overhead. The earlier proposal stays separate.
- **Skip reranking:** changes the evaluated evidence tradeoff and does not remove
  the dominant local validation cost. Keep the current retrieval default.

The smallest useful increment is this duplicate-check removal. The most important
product validation is real coding outcomes. The largest remaining latency
opportunity is the repeated row-hash cost; none of those three claims is the same.

## Further latency options: caching and Voyage

Patrick asked whether Voyage features or caching could improve latency further.
Yes: the strongest larger opportunity is avoiding repeated conversion and JSON
encoding of every vector while retaining effective tamper detection. The selected
one-check removal is a bounded first step, not the final latency architecture.

| Priority | Candidate | Evidence and next falsifiable experiment |
|---|---|---|
| 1 | Cache a verified, immutable index snapshot and use cheaper integrity verification | Current full checks dominate even with a final-result cache hit. A cost-only probe hashes all 10 database files (4,573,954 bytes) in 0.0030 s on average, versus roughly 0.43 s for current row loading/hashing per check. This does **not** prove an equivalent guard. A separate design must bind the complete file set and pinned read version to trusted publication, detect modifications/additions/deletions/symlinks, preserve source/revision and pre/post-effect checks, and test concurrent replacement. No time-only or mtime-only validation cache. |
| 2 | Share exact query embeddings/results across sessions | Existing cache reuse is confined to a retrieval work directory; it already avoids provider calls on a repeated query there. Measure repeated-query frequency before expanding it. A result cache must include generation, config/profile, query, k and accepted scope; each caller still passes current grants, source and tool-budget checks. Completed provider receipts can be reused, never unresolved operations. Semantic similarity alone is not a valid cache hit. |
| 3 | Compare 512- or 256-dimensional voyage-code-4 vectors | Voyage supports both, plus quantization. Fewer vector values could reduce local serialization, transfer and search work. Test an isolated index/profile and untouched retrieval cases; the current profile is fixed at 1024 floats. Matryoshka projection can be explored offline on copied saved vectors, but changed candidate sets cannot inherit old reranking/quality claims. |
| 4 | Compare rerank-2.5-lite and fewer input candidates | Voyage recommends the lite model for latency-sensitive requests. The historical rerank wrapper averaged 0.344 s; changing this stage does not eliminate seconds of local checking. Reducing candidate count might lose supporting evidence already found below rank 20. Test quality, whole-call latency and token cost together. Changing returned top_k alone leaves the uploaded candidate list intact. |

The immutable-snapshot/file-hash idea has the greatest apparent local headroom,
but the 3 ms probe omits manifest authentication, publication migration, source
checks, safe handles and invalidation. It is a reason to run a separate bounded
feasibility investigation, not a claim of a 100x safe retrieval speedup. A raw
database file digest and the current semantic row digest are different contracts.

Official sources checked September 16, 2026: Voyage's
[code-4 announcement](https://blog.voyageai.com/2026/08/13/voyage-code-4/)
documents dimensions and quantization; its
[FAQ](https://docs.voyageai.com/docs/faq) recommends rerank-2.5-lite for latency;
the [reranker API](https://docs.voyageai.com/docs/reranker) distinguishes input
documents from returned top_k. No alternative model or dimension was called or
qualified here. The newer rerank-3 family is listed as preview, so it is not
silently substituted for the currently qualified default.

Keep these larger options visible for the next decision. They are not bundled
into this three-task production scope or authorized as paid experiments.

## Reranker API: existing role and next evaluation

Patrick explicitly asked to take advantage of the reranker API. **It is already
part of the implemented retrieval pipeline:** hybrid search selects up to the
accepted candidate limit (default 50), then the Voyage reranker orders those
passages before the requested evidence is returned. The current profile selects
`rerank-2.5`. In `src/attune_harness/voyage_provider.py`, `VoyageProvider.rerank`
calls the SDK's `Reranking.create` with query, documents, model, top_k and
truncation disabled. `src/attune_harness/voyage_retrieval.py` dispatches it through
the durable stage journal after scope and freshness checks. Completed-stage or
final-result reuse avoids another paid call; an empty candidate pool skips it.

The earlier 100-question evaluation measured complete expected evidence in the
top five for 75/80 answerable cases after reranking versus 71/80 before it. This
supports retaining reranking while improving latency; it does not establish
better completed coding tasks. See `docs/voyage-100-question-evaluation.md`.

**Proposed comparison:** keep rerank-2.5 as the baseline and evaluate
rerank-2.5-lite through the same API. Voyage describes lite as optimized for
latency and quality in its [reranker documentation](https://docs.voyageai.com/docs/reranker).

1. Freeze a fresh development/validation case split, expected source evidence,
   index generation, queries and exact ordered candidate text/hashes. Reuse query
   embeddings and identical candidates for both models so only reranking changes.
   Keep the original 100-question campaign untouched as historical evidence.
2. Use an isolated evaluation runner with an explicit model in every request,
   cache key, result and usage receipt. The current production profile and rate
   snapshot are fixed to rerank-2.5; changing a model string alone would not
   qualify generation compatibility, reporting or cost accounting for lite.
3. Measure whole-call and provider-stage latency separately, complete evidence
   at equal returned k, context bytes and measured billed tokens. Report paired
   wins/losses, especially implementation-plus-test evidence, and retain failures.
   Freeze the acceptable quality tradeoff before seeing held-out results.
4. Test smaller candidate pools as a separate experiment only after the model
   comparison. Returning fewer results through top_k does not reduce the candidate
   documents sent to the API. Candidate omissions cannot be repaired by reranking.
5. Prepare exact upload contents, calls, current model-specific rates and a cost
   estimate before any live run. No new paid call or default-model switch has been
   made. Promote a different model only from accepted comparison evidence.

The current validation-reuse tasks retain the existing API stage and its cached
receipts. This follow-on evaluates better use of an existing integration; it does
not require adding a second reranker or reranking already completed cache hits.
