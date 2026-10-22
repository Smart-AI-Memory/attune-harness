# Bound Windows full-suite runtime with verified partitions

Design before code, October 22, 2026. Scope: the full-source CI driver and its
pytest evidence plugin. No runtime feature, assertion, operation deadline,
installed-wheel selection or publication authority changes.

## Observed failure

Windows Server 2025/Python 3.12 run
[39786227278](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39786227278)
retains 4,975 passes, 442 skips and seven passing subtests. All 5,417 collected
cases finished; pytest printed success at 2,696.28 seconds, but the supervised
process reached the unchanged 2,700-second deadline during final shutdown.
Earlier failure
[39779009190](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39779009190)
reached the same deadline before finishing. Last green
[39727718207](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39727718207)
took 2,602.407 seconds. The driver bytes match across these runs.

The 44 newly added documentation cases cost 10.938 seconds in the latest run;
older modules also varied. This is cumulative suite capacity, not evidence of
a single hanging test or a product assertion failure. Retained artifacts remain
unchanged.

## Choice and experiment

Run two supervised pytest processes concurrently inside each existing Windows
cell, with separate temporary/evidence directories and the same 2,700-second
deadline per child. Partition by SHA-256 of the collected module path so module
fixtures and within-module order stay together. Each child collects the full
suite, records its complete collection and selected cases, then runs its own
partition. The parent accepts only two successful child receipts whose full
collections agree, selected cases match the partition, and case start/end
journals prove the complete collection ran exactly once across both children.
Keep the existing serial default for other callers and the Ubuntu source job.

A disposable partition probe over retained case timings assigned the last-green
5,373 cases as 2,635/2,738, with recorded case-time sums of 1,376.904/1,207.501
seconds. The failed run's 5,417 cases split 2,679/2,738 and
1,372.378/1,311.234 seconds. These sums are estimates, not measured concurrent
wall time; runner contention and real Windows completion must be checked in CI.

Rejected: extend the deadline. The serial suite already consumes nearly all of
it, so that provides no durable runtime margin. Rejected: remove tests or trust
a printed pytest success. That loses coverage or ignores incomplete shutdown.
Rejected: change production plugin verification for CI speed. Its security and
freshness contracts are separate from this capacity defect.

## Cases and verification

- Complete partitions, unchanged module ownership and collection order: pass only
  after every selected case starts and ends and both child processes exit zero.
- Failed assertion, timeout, failed launch or interruption: retain diagnostics
  and fail the aggregate; a pytest success marker cannot clear supervision failure.
- Missing/duplicate cases, mismatched collections, wrong partition, empty
  partition, missing manifests/journals, stale revision or inconsistent child
  receipts: refuse aggregate success.
- Existing serial callers and retained artifacts: behavior and bytes stay intact.
- Prove concurrent execution with a bounded rendezvous fixture; exercise the
  actual pytest plugin and cross-shard failures. Test workflow commands against
  stubs, run focused checks and the full local suite, build the wheel and run
  installed qualification. Read all four Windows source-cell results before
  calling the timeout fixed.

Completion review remains pending until verification and the reviewable PR
record the actual outcome. This note authorizes no merge, manual workflow
dispatch, paid provider call or release.
