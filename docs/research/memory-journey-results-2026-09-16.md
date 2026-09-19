# Luna memory journey: isolated real storage

**Disposition: carry this bounded prototype forward.** Luna completed capture,
correction and forgetting on its first attempts. The host applied each proposal
to the actual FileStashBackend in temporary storage, verified fresh recall and
confirmed physical absence after forgetting. One preselected Astra audit supported
the correction. No stronger router or escalation was needed.

This qualifies one synthetic note journey on local macOS, not production memory
management. No personal memory was accessed, production default changed, sibling
package edited or plan/build task executed. The preceding proposal-only worker
and all five native campaigns remain unchanged.

## What was built and checked

The [design](../../experiments/memory_journey/DESIGN.md) was written before code.
The [adapter](../../experiments/memory_journey/managed_stash.py) and
[coordinator](../../experiments/memory_journey/journey.py) reuse the frozen worker,
citation contract and Harness RunStore. They add:

- Explicit logical note → raw-session note mapping, one target per request,
  separate physical project stores, and scope validation before participant calls.
- Host-owned versions, byte fingerprints and operation receipts. Cooperating
  wrapper clients serialize short reads/applies with OS locks; no model call holds
  a storage lock. A completed retry returns its receipt without repeating effects.
- Write intent before public backend effects, followed by observed-state checks.
  An uncertain write blocks work until explicit reconciliation; partial or foreign
  state stays unresolved. Reconciliation observes and records, never repeats effects.
- Version-bound recall. Old context is refused after correction or forgetting;
  new requests assemble current facts and their evidence again.
- Artifact preservation on failure, including retaining the actual temporary
  directory and reporting its path if saving the receipt persistently fails.

**253 central checks passed in 1.98 seconds: 42 new journey checks and 211 inherited
checks.** New checks use actual temporary files and injected, clearly labeled
model answers. They cover duplicate retries/no resurrection, stale updates,
context change-and-restore, foreign evidence, unsupported types, malformed/expired
physical rows, changed grants/policy, rejected audits, bounded writes, failed
intent/commit persistence and before/after/partial effect failures. Two real
processes proposing from the same version produced one applied correction and
one refusal. Same-project unrelated notes and another project's bytes were preserved.

Read-only delegated review identified gaps in full physical-row validation,
claimed-packet preflight, pre-effect capacity limits and receipt-failure cleanup.
They were fixed and checked centrally before freeze. Tests were written alongside
new experimental code; no existing production guard was changed.

## Native results

The protocol froze 52 source files, seven external dependency files, the fixtures,
rubrics, requested profiles and sampling rule before dispatch. The actual backend
was attune-ai 16.4.0; Codex CLI was 0.153.4. Requested profiles were
gpt-5.6-luna/high and gpt-6-astra/xhigh. The existing subscription transport enforced
four planned calls, seven maximum, a 180-second per-call timeout and a 900-second
campaign deadline, with no automatic retries or provider fallback.

| Stage | Model result | Verified host outcome |
|---|---|---|
| Capture | Luna preserved 09:15 and weekdays, citing N1 | One stored note; fresh reopened recall at version 1 |
| Correct | Luna changed the time to 10:45, retained weekdays and cited N1/N2; Astra supported it | One replacement note at version 2; previous context refused |
| Forget | Luna proposed empty resulting facts and cited the exact N3 request | Version 3; active facts/evidence empty, backend file empty, reopened recall empty |

All three initial/final replies passed host validation, source-based meaning and
citation relevance grading. These are unblinded lead grades of three operations
on one note, not a general accuracy rate. The scheduled audit examined a correct
proposal; it does not estimate detection of confident errors.

Keeping N1 with N2 during correction is relevant provenance: N2 explicitly
supersedes N1's time. The current fact contains 10:45 only. The forgetting reply's
past-tense removal describes its proposed fact list; the separate host receipt
establishes actual storage removal. Historical worker/research receipts intentionally
retain earlier text, and already-loaded model context is not retroactively erased.

| Calls | Input tokens | Output tokens | Native process seconds |
|---|---:|---:|---:|
| Three Luna workers | 14,575 | 564 | 33.95 |
| One Astra audit | 6,352 | 471 | 22.13 |
| Total: four calls, zero escalations | 20,927 | 1,035 | 56.09 |

Reported reasoning output was 714 tokens, included in reported output; cached
input and cache-write counts were zero. Timing sums complete native processes,
not time to a visible finding or decision. There is no matched performance arm,
financial saving or dollar conversion. The existing host warnings about disabled
Code Mode, skill-context budget and experimental skill discovery are retained
verbatim; their causal impact was not measured.

The final store stayed empty when all three completed operations were retried.
The other project's canary never entered a participant prompt and its backend
bytes remained unchanged. Temporary stores were removed after their synthetic
artifacts were retained. All 104 previous native receipts, their protocols and
frozen source hashes, and the preceding worker receipts were verified unchanged.

## Remaining integration boundary

This adapter supports at most eight notes, 500 characters per note and eight
bounded source IDs per note. It does not qualify other taxonomies, sensitivity
classification, service-layer sanitization/fallback, curated promotion, or access
control against an untrusted local process. Direct writers bypassing the wrapper
remain outside its concurrency guarantee. Correction is removal plus append;
there is no atomic multi-file transaction or power-loss durability claim, and
partial effects require inspection rather than automatic repair.

The next useful increment is to qualify the actual service/context path on
disposable data: enforce its security and type rules, inject refreshed memory
into a receiving agent, and verify correction/forgetting across that boundary.
Representative workloads and active-lead delegation are still needed before
claiming that Luna saves time or cost in normal use. Keep Luna as the routine-worker
and sorter candidate, with explicit routing and sampled review.

## Reproduce and inspect

From the Harness root, this command uses injected answers and real temporary
storage, makes zero native calls and prints the three resulting states:

```sh
/Users/patrickroebuck/attune-ai/.venv/bin/python -B experiments/memory_journey/run_journey.py --demo
```

The exact central suite was:

```sh
/Users/patrickroebuck/attune-ai/.venv/bin/python -B -m pytest -q experiments/memory_journey/test_journey.py experiments/memory_worker/test_worker.py experiments/memory_citations/test_citations.py experiments/memory_sorter/test_sorter.py experiments/memory_routing_v2/test_revised.py experiments/memory_routing/test_memory_routing.py
```

Evidence: [frozen protocol](../receipts/memory-journey-2026-09-16/protocol.json),
[suite](../receipts/memory-journey-2026-09-16/suite.txt),
[offline/review receipt](../receipts/memory-journey-2026-09-16/offline.json),
[native ledger](../receipts/memory-journey-2026-09-16/ledger.json),
[actual storage and worker artifacts](../receipts/memory-journey-2026-09-16/journey.json),
[source-based grades](../receipts/memory-journey-2026-09-16/grades.json), and
[analysis with receipt hashes](../receipts/memory-journey-2026-09-16/analysis.json).
The native runner refuses an existing ledger; these receipts cannot be overwritten
by rerunning the campaign.
