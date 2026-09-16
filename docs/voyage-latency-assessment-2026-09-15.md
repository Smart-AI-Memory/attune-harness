# Voyage retrieval latency: measured breakdown

September 15, 2026. Installed Harness `0.1.0.dev13`, 98 files / 1,050 passages,
`voyage-code-4`, `rerank-2.5`. No production changes or new paid calls.

## Main finding

**Repeated local validation dominates the measured retrieval overhead.** The
historical provider calls together took about half a second. A new offline probe
of the installed shared session took 3.22 seconds on average even when both
provider responses were already saved. Of those 3.22 seconds, 3.16 were spent
checking index integrity and source freshness.

Evidence: [raw timing receipt](receipts/voyage-next-increment-2026-09-15/latency.json)
and [disposable probe](receipts/voyage-next-increment-2026-09-15/latency_probe.py).

## 1. Historical timings: all 100 questions

All values below are seconds. p95 uses nearest rank: 95% of these observations
were at or below that value. It is a sample percentile, not a service guarantee.

| Timed boundary | Mean | Median | p95 | Maximum |
|---|---:|---:|---:|---:|
| Query embedding provider stage | 0.218 | 0.211 | 0.276 | 0.483 |
| Reranking provider stage | 0.344 | 0.327 | 0.404 | 0.879 |
| Both stages, summed per query | 0.562 | 0.538 | 0.707 | 1.090 |
| Complete benchmark question | 5.313 | 5.321 | 5.447 | 5.897 |
| Question time outside provider stages | 4.751 | 4.770 | 4.865 | 4.881 |

The complete question timings sum to **531.31 seconds (8 minutes 51 seconds)**.
The two provider stages sum to **56.16 seconds**, about 10.6% of that benchmark
time. The remaining 475.15 seconds include both retrieval's local work and extra
evaluation work: repeated integrity checks, a second hybrid search, lexical
baseline calculation, validation of each variant, grading, and receipt writes.
It cannot all be labelled production overhead.

Provider stages time the SDK wrapper, including any campaign pacing and response
validation. They are not measurements of provider server compute alone. Combined
percentiles were calculated from paired per-query sums, not by adding percentiles.
The original receipt has no separate full production-call timing.

## 2. Newly measured local retrieval costs

The probe selected every fifth frozen question, starting with n001: **20 queries**,
including 16 answerable questions and four missing-answer controls. Each path
returned ten passages. All paths ran in one warm Python process on this machine,
sequentially, using the original selected files and real local database.

For each query, a fresh scratch directory received copies of its campaign's
completed paid stages. The installed retriever reran real candidate search and
integrity checks, while its normal journal reused the saved embedding and rerank
responses. Provider permission was disabled and client construction was replaced
with an assertion failure. A second invocation measured reuse of the completed
result cache. Returned passage identities matched the original results.

| Local path; zero live provider calls | Mean | Median | p95 |
|---|---:|---:|---:|
| Direct retriever, candidate search recomputed | 2.162 | 2.162 | 2.178 |
| Direct retriever, final result cached | 1.592 | 1.587 | 1.635 |
| Shared session, candidate search recomputed | 3.220 | 3.217 | 3.241 |
| Shared session, final result cached | 2.660 | 2.656 | 2.681 |
| Session object setup, separate from calls | 0.527 | 0.527 | 0.536 |

The session is `RetrievalSession.invoke`, used by the Harness MCP and optional
Attune bridge. This does not include stdio transport, UI scheduling, full plugin
startup/imports, cold disk caches, live provider dispatch writes, concurrent
requests, or answer generation. Scratch setup/copying and cleanup were outside
the timers. The final result-cache path follows its recomputation immediately,
so these measurements characterize warm replay only.

The two paths have deliberately different cache states. Their timings describe
those states, not a before/after production optimization. Original experiments
remained byte-for-byte unchanged: 468 files, excluding Python bytecode caches.

### Where the 3.22 local session seconds go

| Component | Mean per call | Detail |
|---|---:|---|
| Full generation checks, inclusive | **3.160 s** | Six checks per recomputed session query |
| ↳ Load/hash all database rows | 2.615 s | Included in generation checks |
| ↳ Snapshot selected sources and Git state | 0.422 s | Included in generation checks |
| ↳ Load/validate generation metadata | 0.092 s | Included in generation checks |
| Hybrid candidate search | 0.032 s | Dense, lexical, token matching, fusion |
| Invocation/session receipt saves | 0.004 s | Four saves |
| Reuse two completed paid stages | 0.002 s | Local parsing and validation only |

Do not add indented child rows to their parent. Full generation checks account
for **98.1% of this offline local call**, not 98.1% of a live request.
Database loading/hashing alone accounts for 81.2% of the local call.

[`check_generation()`](../src/attune_harness/voyage_index.py) reloads generation
metadata, snapshots sources, and calls `table_rows()`. That routine converts
every database row to Python data and hashes the complete result, including
1,050 vectors with 1,024 dimensions each: 1,075,200 vector values per check.

The direct recompute path performs four generation checks: accepted selection,
initial retrieval, before reranking, and final evidence validation. The session
adds scope checks before and after the call, for six total. Final-result replay
still performs three direct checks or five through the session. This explains
why avoiding provider charges does not make the existing cache instantaneous.
Session setup performs one further check outside the call timer.

## 3. What this implies for user-visible latency

An illustrative reconstruction substitutes each sampled query's historical live
provider durations for its local paid-stage replay time:

| Reconstructed path | Mean | Median |
|---|---:|---:|
| Direct retrieval plus historical provider time | 2.71 s | 2.70 s |
| Shared session plus historical provider time | **3.77 s** | **3.75 s** |

**These are estimates assembled from two measurements, not observed live
end-to-end calls.** They exclude fresh paid-dispatch persistence, desktop/MCP
transport, startup, current network conditions, concurrency, and generation.
The defensible current planning estimate is therefore roughly **3.8 seconds per
uncached session query before those additional costs**, on this index and machine.
A true live end-to-end measurement remains outstanding.

### Effects of the design choices

- **Reranking:** its historical provider stage adds a median 0.327 seconds and
  p95 0.404 seconds. A hybrid-only mode would avoid that stage, but the complete
  latency difference is unmeasured because no such public mode is implemented;
  its local validation boundaries could also differ.
- **Context size:** reranked top five contains about 47% of the cited-text bytes
  of hybrid top ten in the saved sample. Smaller input may reduce the coding
  model's input-processing time. No generation latency was measured, so neither
  a 53% speedup nor a net end-to-end gain can be claimed.
- **Caching:** it eliminates new provider calls, but the measured shared-session
  cache still takes about 2.66 seconds because five full checks remain.
- **Exact lookup proposal:** it would avoid embedding/reranking and semantic
  candidate search. Its latency is unmeasured, and preserving current whole-index
  validation would retain substantial local cost.
- **Scale:** full row loading/hashing grows with indexed data and repeated checks.
  This run does not establish a scaling curve or performance under concurrency.
- **Whole coding task:** add generation, follow-up searches, edits, and tests.
  This evaluation contains none of those task-level timings. Better retrieval
  could reduce follow-up work, but successful coding outcomes must establish it.

## Recommendation for latency work

Investigate repeated whole-index loading and hashing first. Candidate search is
already around 32 milliseconds here. Preserve the source-revision, scope,
pre/post-dispatch byte integrity, and database tamper guarantees while designing
how validated state can be shared across nested checks. Do not replace those
guarantees with unchecked time-based caching or skip revalidation after external
work.

Qualify any optimization in separate baseline/changed runs with identical input,
cache states, and source/tamper tests. Then obtain the scoped authorization for a
small live measurement of full client-to-tool latency, recording cold startup,
warm requests, cached repeats, and model time separately. No latency implementation
change or new live campaign is authorized by this report.
