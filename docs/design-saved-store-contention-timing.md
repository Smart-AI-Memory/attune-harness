# Locate saved-store lock-held latency

## Scope and decision

Preserve eight concurrent, single-attempt writers, the two-second acquisition
budget and every commit, replay and history assertion. Patrick selected further
latency investigation on October 23, 2026, and rejected caller-retry qualification.
This diagnostic change does not establish a storage repair or full R4 acceptance.

The [R4 requirements](specs/windows-parity/design.md#r4-saved-store-locking-privacy-and-commit)
and [existing lock bound](../src/attune_harness/memory_saved.py) remain in force.
No persistence barrier, access flag, private ACL, source format or retry changes.

## Evidence and discriminating question

[PR #301's source job](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39896576478/job/120228341555)
records seven returned writers and one `busy/not_committed` writer.
[PR #299's source job](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39896523031/job/120228178115)
records three returned writers and five `busy/not_committed` writers. Their
retained diagnostics show one lock identity per run, successful holder unlocks
and closes, and deadlines expiring during another writer's hold. Poll-event
drops are explicit. The declared clock resolution is 15.625 ms.

The same-head Server 2025/Python 3.12 installed-wheel case passes both eight-writer
phases; its longest observed independent hold is 62 ms. This comparison does not
isolate storage waiting, scheduling or observer overhead. The historical failure
cause remains unknown.

Disposable POSIX controls retained outside the repository confirm the budget
interaction: eight undelayed single attempts return; adding 0.4 seconds inside
each held write yields five commits and three bounded busy refusals without lost
reported commits. A caller-retry probe preserved all records, but that proposed
qualification interpretation was rejected. These are causal controls, not native
Windows qualification or evidence that the old failed runs succeeded.

The next question is where elapsed time accumulates: prepared-file creation,
inspection, writing, verification reads, rename or flushing.

## Observation and failure cases

Use a separate ordinary-run prefix around the existing child script. Preserve
the original script and retained-cell campaign route. Call each wrapped method
exactly once with the same arguments; preserve its result and original exception.
Do not add saved-store operations, synchronization objects, retries or provider calls.

The combined ordinary script exceeds the Windows inline command-line limit.
Transport its exact UTF-8 bytes with a compressed standard-library bootstrap;
decode before storage starts, preserving all argument positions. Verify the
round trip and the complete serialized Windows command line in portable controls.
This adds startup imports/decoding and can affect scheduling; it adds no saved-store
operation. The frozen campaign still uses its original inline program.

Record compact `perf_counter_ns` operation spans while the lock is held, with
separate declared clock metadata and bounded acquisition/commit/unlock boundaries.
Never subtract these timestamps from the existing monotonic-clock timestamps or
sum nested spans. Keep the operation buffer separate from lock-poll diagnostics;
record drops and observer failures. Include no paths, payloads or arbitrary error
messages. Serialize and emit only through the existing post-release report.

Portable controls must expose changed call order/counts/arguments, replaced
results/exceptions, clock or recorder failure, buffer overflow and report growth
beyond the existing 32 KiB limit. Native receipts must retain actual workload,
outcomes and diagnostics, including failures. A diagnostic pass is not evidence
that instrumentation is free or that the latency cause is repaired.

## Alternatives retained or rejected

High-resolution spans are the smallest next observation; scheduler/I/O tracing
may still be needed to attribute a slow span. Increasing the budget, reducing
concurrency, skipping busy writers, removing durability checks or adding retries
would change the question. None is part of this patch. Frozen experiments,
receipts and their admission rules remain unchanged.
