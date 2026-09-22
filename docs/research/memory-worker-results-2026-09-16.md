# Bounded memory-worker prototype

Date: 2026-09-16, local time. Status: **implemented and verified as a disposable,
proposal-only prototype**. Luna remains the sorter and routine-worker candidate.
This increment adds a host-controlled lifecycle around the proven citation
contract; it does not add another router model or enable live memory writes.

Patrick authorized this increment after the eight-case citation repair result.
The [design note](https://github.com/Smart-AI-Memory/attune-harness/blob/312e7af/experiments/memory_worker/DESIGN.md) preceded the code.
The [worker](https://github.com/Smart-AI-Memory/attune-harness/blob/c8b3235/experiments/memory_worker/worker.py) imports the frozen repaired
contract without changing its prompts, schemas, normalizer or prior campaigns.

## Implemented behavior

| Host condition | Worker behavior |
|---|---|
| Supported routine task | Luna sorts and proposes the result in one call |
| Host declares known difficult work | Goes directly to Astra; no preliminary Luna/router call |
| Invalid Luna proposal or reasoning request | One Astra escalation with original evidence |
| Stronger result still needs reasoning | Stops without another worker or audit call |
| Missing evidence or unmade owner choice | Records the specific unresolved need; no reasoning escalation |
| Host selects a semantic sample | Audits a valid proposal, no-change, evidence request or decision request before publication |
| Unsupported, uncertain or malformed audit | Quarantines the proposal |
| Participant unavailable or interrupted | Retains the uncertain attempt; no automatic retry |
| Input, grants, host class or policy changes | Stops stale work, including change-and-restore sequences |
| Duplicate job ID | Refuses a new dispatch; existing receipt can be inspected |
| Unsupported capability or host task class | Stops before any participant call |

The host declares the class; source prose and model confidence do not select
routing or sampling. `known_difficult` exercises a policy route, not an automatic
difficulty classifier or proof that a particular task needs Astra. The supported
capability is explicitly `synthetic_facts_v1`; live-memory, security-classification
and retrieval-refresh requests do not silently enter this prototype.

Jobs retain the captured input, host generation, policy, route, sample selection,
dispatch intent, replies and final disposition. Harness's existing RunStore
provides short OS-backed writer leases and atomic record persistence. Locks are
released before participant calls. Freshness is checked before each dispatch and
before final publication; a monotonic generation rejects ABA change-and-restore.
Reopening and inspection do not run models or repeat effects. An interrupted
running record is explicitly uncertain; no recovery or exactly-once remote
execution guarantee is claimed.

There is **no memory apply/export method**. A ready proposal is an inspectable
candidate, not a claim that a memory changed or that all unsampled semantics
were verified. Pending decision requests are persisted; this increment does not
add a decision-form renderer or replace the existing human-control grammar.

## Controller evidence

**211 checks passed: 54 new and 157 inherited**, in the final central run.
Checks cover the routes above, original-evidence handoff, audit failure, stale
record/source/grant/policy changes, ABA, dispatch/publication persistence failure,
interruption and read-only inspection. Two actual spawned processes competed for
one job: only one participant callback ran. That qualifies this local job-claim
path, not concurrency of actual memory updates or another platform.

The terminal demo replays **eight original Luna replies and one original Astra
audit** against exactly matching prompts, schemas, roles and model aliases.
All eight jobs reach their expected outcomes after reopening: five ready
proposals, one no-change, one evidence request and one decision request. Every
captured memory record stays unchanged. There are **zero new native model calls**;
these are controller observations, not eight new quality successes.

Sampling uses a deterministic hash of the host's job ID and configured salt,
modulus and bucket. The demonstration salt was selected to exercise the sole
already-recorded conditional-update audit. This is explicit fixture scheduling,
not an independently drawn sample or a calibrated production sampling rate.

Injected replies test the response to a confident error, false no-change and
failed audits. Their verdicts are supplied fixtures, so they demonstrate
quarantine control flow, not new audit detection performance. Another test shows
that a structurally valid **unsampled semantic error can remain proposal-ready**.
Sampling is not a truth guarantee; production quality policy remains to be qualified.

A bounded read-only evidence-chain review found one unnecessary-call path:
sampled final Astra `needs_reasoning` replies could trigger another audit. Audit
eligibility now excludes that terminal state, with sampled and unsampled direct
and escalated cases checked centrally. The reviewer performed no model calls or
tests; the lead owns the executed verification.

All five preceding campaigns' frozen sources, protocols, ledgers and **104 raw
native receipts** still match their recorded hashes. Available saved grade hashes
also match. Exact replay data retain links and hashes for their original receipts.

## Actual memory-adapter boundary

The [adapter probe](https://github.com/Smart-AI-Memory/attune-harness/blob/c8b3235/experiments/memory_worker/probe_adapter.py) directly
constructed the installed Attune 16.4.0 FileStashBackend with an explicit temporary
directory and synthetic notes. It passed capture, close/reopen, recall, exact-ID
forgetting, physical absence verification and preservation of an unrelated note.
It did not use automatic backend resolution, service wrappers, live memories,
Voyage, Redis, provider calls or credentials.

Two observations matter for integration: remembering the same ID twice produced
two records, and exact-ID forgetting removed both; specifying a project in search
still returned another project's matching note. The latter is intended soft
ordering, **not access isolation**. The former means retry/dedup behavior cannot
be assumed from the ID alone. This single-process fixture does not qualify
concurrent forgetting, crash recovery, tombstones or durable erasure across tiers.

Source review confirms the separate interfaces and vocabularies:

| Surface | Existing vocabulary / relevant boundary |
|---|---|
| [Personal documents](/Users/patrickroebuck/attune-ai/src/attune/memory/personal.py:169) | decision, pattern, troubleshooting, reference; document and summary writes are separate |
| [Raw session stash](/Users/patrickroebuck/attune-ai/src/attune/memory/session_stash.py:39) | decision, pattern, bug, reference, note; the service entry truncates content above 500 characters |
| [Curated promotion](/Users/patrickroebuck/attune-ai/src/attune/memory/promotion.py:38) | user_context, feedback, project_context, reference; distinct frontmatter mapping and review workflow |
| [Sensitivity/access](/Users/patrickroebuck/attune-ai/src/attune/memory/long_term_classification.py:142) | PUBLIC, INTERNAL, SENSITIVE; independent of logical memory kind |

The experimental preference/lesson kinds therefore require an explicit semantic
mapping. They cannot simply pass through these interfaces. The
[file stash](/Users/patrickroebuck/attune-ai/src/attune/memory/file_stash.py:180)
also exposes no expected-version update/commit API. Its
[lock](/Users/patrickroebuck/attune-ai/src/attune/memory/atomic_io.py:99) expires by
age, so it must not span model work. Personal capture has separate document/index
writes, and [topic forgetting](/Users/patrickroebuck/attune-ai/src/attune/memory/personal.py:420)
can cover both global and project roots; a returned count alone is not sufficient
proof of all requested deletions. These are recorded integration constraints,
not changes to sibling memory code or newly declared Harness release blockers.

The isolated direct-backend probe does not qualify sanitization, promotion
approval, service-wrapper fallback, security policy or injected session-context
refresh. Those remain explicit boundaries before live use, along with real
storage concurrency, representative workload economics and active-lead delegation.

## Reproduce and inspect

Run the compact controller demonstration from the Harness root:

```sh
/Users/patrickroebuck/attune-ai/.venv/bin/python -B experiments/memory_worker/replay_worker.py
```

Add `--full` for the complete job records. The demonstration uses disposable
directories and cleans up its synthetic store. The separate real-adapter probe is:

```sh
/Users/patrickroebuck/attune-ai/.venv/bin/python -B experiments/memory_worker/probe_adapter.py
```

Evidence: [verification and source hashes](../receipts/memory-worker-2026-09-16/verification.json),
[persisted replay records](../receipts/memory-worker-2026-09-16/worker-replay.json),
[real adapter observations](../receipts/memory-worker-2026-09-16/adapter-probe.json),
[central test output](../receipts/memory-worker-2026-09-16/suite.txt).
The [receipt collector](https://github.com/Smart-AI-Memory/attune-harness/blob/c8b3235/experiments/memory_worker/verify_worker.py) refuses
to overwrite an existing destination. Production packages and the non-executable
plan/build outline are unchanged by this increment.

## Subsequent isolated storage journey

The authorized [Luna note lifecycle](memory-journey-results-2026-09-16.md) now adds
a separate experimental apply/recall path over real temporary FileStashBackend
stores. It passes 253 central checks and one native capture/correct/forget journey
in three Luna calls plus one sampled Astra review, without escalation. This worker
and its original receipts remain frozen; the later result does not qualify live
memory integration, service security, other taxonomies or workload economics.
