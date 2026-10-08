# Design: parallel consultation rounds and partial outcomes (#233)

Status: design note, before code. Revision 3: Codex review, then a delta re-review that resolved all nine findings and added one (`runtime_origin` on retry), fixed here. Revision 4 adds the ordered refusal walk requested on PR #239; that documentation delta needs its own review. Runtime owner: Lane A (see the coordination brief
for #232–#236). Core path: the consultation run loop, its recovery journal and
saved status.

## Problem, as observed

`consultation.run` (src/attune_harness/consultation.py:205-265) calls seats one
at a time and stops the run at the first turn that did not complete. Three
effects, each probed in scratch on 2026-10-08:

1. **Later seats are never asked.** P1: in a two-seat roundtable whose first seat
   fails, `called == ['reviewer']`, the status is `failed`, and the second seat
   has no turn.
2. **A failed run cannot be continued.** P1: `run` with the same digest refuses
   with `Terminal consultation cannot dispatch again`. On 2026-10-07 the Claude
   CLI refused before any model ran (`claude_structured_error`, empty
   `modelUsage`). Recovering still needed a new run directory and acceptance
   for a byte-identical contract.
3. **Every failure is `effects: 'unknown'`** (consultation.py:193-195), including
   failures that provably made no call.

Round 1 seats are independent by contract, yet a round's wall time is the sum of
seat timeouts: up to 3 × 300 s per round.

## Decisions

Revised 2026-10-08 after a Codex review (`source-review`, verdict
`request_changes`, nine citations, all checked against the source). The revision
adopts the existing refused-turn retry in `recovery.reconcile_record`
(recovery.py:322-366) instead of inventing a weaker one.

**D1. Seats within a round run concurrently, within an admitted budget.
Bookkeeping stays on one thread.**

- **Admission comes before `begin`.** For each round, the loop first replays
  completed turns (no call, no budget use). It then admits the first *k* pending
  seats in configuration order, where *k* is the remaining `max_operations` budget,
  or all seats when none is set. Only admitted seats reach `begin`. Seats outside
  the admission are never marked `dispatching`, so a pause never strands a
  never-called seat as unresolved.
- **The split keeps every `perform` branch.** `RecoveryCursor.perform` is split
  into `begin` (replay check, request-mismatch and unresolved-phase rejection,
  event creation, dispatch-origin capture, durable `dispatching`) and `finish` /
  `fail` (the success save, and the existing exception path with effects and
  native evidence). The pause check moves to the caller, which `finish`es every
  admitted result before raising `ReviewPaused`. `perform` keeps its exact
  behavior as `begin`, then call, then `finish`/`fail`, then the pause check,
  including the `Exception` versus `BaseException` split. Existing review callers
  get regression tests, including replay under an operation limit.
- Worker threads run only `dispatcher(...)`. `finish` runs on the main thread in
  configuration order, so the saved record doesn't depend on finish order.
  `--max-operations 1` admits one seat, which is today's behavior.

**D2. Rounds stay sequential, and round 2 needs a complete round 1.** Unchanged
from the first draft. A failure stops the run after its round, not after its seat.

**D3. A new status, `partial`.** Unchanged: at least one completed turn in the
stopped round gives `partial`, otherwise `failed`. Both exit 2.

**D4 (revised). No new `effects` value; record retry evidence instead.** Every
failed turn keeps `effects: 'unknown'`. `dispatch()` adds a `retry_basis` to the
error only in these cases, as evidence for an operator, not a claim of no call:

| `retry_basis` | Condition | What it does and doesn't show |
|---|---|---|
| `not_launched` | `failure in ('not_found', 'launch_failed')` **and** `returncode is None` | The launch raised before a process existed. The post-supervision `job.launch_failure()` path on Windows (process.py:116) has a return code, so it is excluded. Windows launch-raise provenance is qualified only by its own CI jobs. |
| `cli_refusal` | `refusal.kind == 'claude_structured_error'` | The CLI exited with its own error result and **no reported** model usage. It does not prove no request was made, so usage may repeat (the existing provenance wording, recovery.py:347-348). |

**D5 (revised). Retry is an explicit operator action, reusing the reconcile pattern.**
A new `roundtable reconcile RUN --checkpoint DIGEST --round R --participant P
--retry-refused` (and the `source-review` twin). It never runs automatically, and
`run` alone never retries.

- **Gate, checked before any mutation:** the stopped round's turn exists, its saved
  result is `failed` with a `retry_basis`, the run is `partial` or `failed`, and
  `attempts < 2`. Anything else refuses with zero dispatches. The cap is checked
  here explicitly, not left to `load()`.
- **One transition:** a consultation's failed turn is journaled as event
  `completed` with `result.status == 'failed'` (probe P1). The transition copies
  the event as `previous`, resets it to `prepared`/`pending`, increments `attempts`
  exactly once, and removes `result`, `error`, `effects` and `runtime_origin`, as
  `reconcile_record` does (recovery.py:345). Keeping an origin on a `prepared`
  event fails `validate_events`. The removed values survive in `previous`. Attempt
  2 captures a fresh origin at its own `begin`. The transition also removes the
  stale answer from `record['answers']`. It appends
  `{event_id, checkpoint, previous, evidence}` to
  `record['recovery']['reconciliations']`, the same list the review path writes.
  The evidence carries `retry_basis` and the provenance text. The status becomes
  `paused`.
- **Then** `run` with the same accepted digest replays completed turns and calls
  only the reopened seat.
- **Budget, stated honestly:** the contract's `max_calls` bounds first attempts.
  Each retry is a separate operator-authorized call, at most one per turn, and its
  usage may repeat. `status` reports total attempts per turn.

**D6 (revised). Interrupts and cancellation separate three worker outcomes.** On
`KeyboardInterrupt`, the main thread sets the shared cancel event and joins
admitted workers, each with a bound of its seat timeout plus a grace period:

- **Returned a result:** `finish`, as normal. A cancelled `invoke` returns
  `cancelled_effects_unknown`, which `dispatch()` turns into a `cancelled` result
  journaled as completed. The run status is `cancelled`, as today.
- **Raised outside `dispatch()`'s catch:** `fail` with effects unknown, then
  re-raise on the main thread. The run is `unresolved`.
- **Still alive after the join bound:** left `dispatching`. The run is
  `unresolved` and resume refuses until reconciled.

## Ordered recovery journey (proposed, not a released command)

The source citations below pin the existing implementation at
`b5a705af2fa3928b328af19dec2dceef026ce9dc`. The consultation CLI does **not**
yet implement `reconcile`, `partial` or D1's concurrent admission. This table
defines the implementation's acceptance tests; it is not an instruction to
dispatch a provider or evidence that the future journey already passes.

Use the original absolute run directory `RUN`, its unchanged accepted contract
digest `CONTRACT`, and the latest **record** checkpoint `CHECKPOINT` returned by
inspection. These are two different digests. For the roundtable witness, round
`0` seat `reviewer` has a saved failed result with a permitted D4 `retry_basis`,
attempt `1`; sibling `critic` completed, and no later-round seat has dispatched.
For the source-review twin, its sole `reviewer` failed and the saved operation is
`source-review`. Each witness retains its originally validated configuration,
frozen snapshot, owner path and contract budget; it contains no citation
assessment of the failed answer being removed. An unresolved sibling is a
separate reconciliation requirement, not permission to repeat it.

| Order and command | Input producer | Refusal and source | Witness and resulting state |
| --- | --- | --- | --- |
| 1. `attune-harness roundtable status RUN` (or `attune-harness source-review status RUN`) | Original prepared run and retained failed/partial attempt | The CLI loads and refuses an operation mismatch: [consultation_cli.py:64–67](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/consultation_cli.py#L64-L67). All shared load gates below apply. | Inspect with the verb matching the saved operation. Retain the printed contract/checkpoint and selected turn evidence; inspection grants no dispatch authority and makes no call. `partial` is a proposed saved status; current failed runs remain terminal. |
| 2. **Proposed** `attune-harness roundtable reconcile RUN --checkpoint CHECKPOINT --round 0 --participant reviewer --retry-refused` (matching `source-review` twin) | Step 1's current checkpoint and failed-turn evidence; explicit operator retry decision | Proposed D5 must reject a stale checkpoint, wrong saved operation, absent selected turn, non-stopped run, non-failed saved result, missing/permitted-basis mismatch, missing explicit retry choice or attempt `>= 2`, before mutation or dispatch. Existing review reconciliation supplies the checkpoint/owner pattern ([recovery.py:216–231](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/recovery.py#L216-L231)) and explicit choice/cap pattern ([recovery.py:311–345](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/recovery.py#L311-L345)); those are not an implemented consultation reconciler. | The selected event is `consultation_turn`, `completed/completed` with `result.status == 'failed'`, attempt 1, permitted D4 basis; run is proposed `partial` (roundtable) or `failed` (source-review). D5 specifically handles this completed failed-result shape. Calling today's `reconcile_record` directly would reject it as not an unresolved dispatch ([recovery.py:324–327](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/recovery.py#L324-L327)). |
| 3. Proposed D5 save, then matching `status RUN` | D5's single declared transition | Preserve event key/kind/effect class/request digest and contract/owner/snapshot/budget; copy prior event/evidence, increment once, clear declared result/error/effects/runtime_origin, remove only the selected stale answer, append reconciliation history, set `paused`. [RunStore.save:118–139](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/review_store.py#L118-L139) recomputes the checkpoint and refuses failed persistence. Shared load/event gates below must pass on reload. | Reopened event is `prepared/pending`, attempt 2; successful sibling bytes are unchanged. The record checkpoint changes, while `CONTRACT` does not. **Current `consultation.load` rejects `recovery.reconciliations` because its recovery mapping must equal `{'profile': PROFILE}` exactly** ([consultation.py:96–99](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/consultation.py#L96-L99)). Implementing the already-declared D5 history therefore also requires explicitly validating that extended recovery shape while preserving old records; the future full-history reload test must prove it, rather than claim current code accepts it. |
| 4. `attune-harness roundtable run RUN --accept CONTRACT --allow-external` (matching `source-review` twin); add `--allow-native` if any configured seat is not `command` | Same original accepted contract, successfully reloaded paused record, and separate host dispatch authorization | CLI operation match and every shared gate below still apply. Wrong acceptance refuses at [consultation.py:211–212](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/consultation.py#L211-L212); missing external or applicable native authority refuses at [214–215](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/consultation.py#L214-L215); terminal status refuses at [216–217](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/consultation.py#L216-L217). Flags express an existing authorization; these examples do not grant it. | `--accept` supplies the contract digest, not the new checkpoint. `paused` is dispatchable. Reconstruct the identical turn request; replay successful completed seats without calls/budget consumption and admit only the explicitly reopened seat in the stopped round under D1. Any later round requires the complete preceding round (D2), uses the original bounded contract, and is a later first attempt rather than another retry. |
| 5. Matching `status RUN` after resume; an optional operation limit is `--max-operations 1` on step 4 | Durable results or a saved pause | Cursor rejects invalid limits, duplicate keys, mismatched requests and unresolved phases: [recovery.py:147–174](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/recovery.py#L147-L174). The existing cursor saves each result before its pause ([208–212](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/recovery.py#L208-L212)); D1 must retain that property. | With limit 1, the retry result is saved before pause; a subsequent separately authorized matching `run` replays it. Without that limit and if all required seats succeed, the run reaches completed. Attempt 2 is the cap: another refusal cannot be reopened. Failure, cancellation or unresolved effects remain retained under D2–D6; no automatic retry or assurance of success follows. |

### Shared refusals each load/resume must satisfy

| Existing refusal boundary | Source raise / validation | Input proof required after the proposed transition |
| --- | --- | --- |
| Run ownership, record access and persistence | [review_store.py:53–115](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/review_store.py#L53-L115), [152–159](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/review_store.py#L152-L159); [consultation.py:98–106](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/consultation.py#L98-L106) | Original existing absolute directory, readable bounded/versioned JSON, valid recalculated checkpoint, matching record_path, supported profile/operation and unchanged contract digest/operation; acquire the existing lease, never copy the run to evade ownership. Storage errors stop the journey. The D5 extended recovery history needs its explicit future validator, as above. |
| Configuration and frozen source | [consultation.py:21–72](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/consultation.py#L21-L72), [107–108](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/consultation.py#L107-L108); [consultation_snapshot.py:156–179](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/consultation_snapshot.py#L156-L179) | Preparation's schema/question/explicit identities, distinct seats, adapter/provider/effort, command argv, timeout and round bounds remain unchanged. Retain the exact canonical frozen paths/text/hashes and aggregate bounds. Validation reads retained bytes, not later live-checkout changes. |
| Contract call/output budget and event identity | [consultation.py:109–115](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/consultation.py#L109-L115); [recovery.py:235–282](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/recovery.py#L235-L282) | Preserve max_calls/output/automatic_retries; reopen the existing event rather than add one. Every event has supported kind, unique operation_key, integer attempt 1 or 2 and valid phase/state. Prepared events carry no runtime_origin; preserve applicable policy and old origin in prior evidence, and require fresh attempt-2 capture where configured. D5's record-level history is proposed; current event-history validation does not by itself validate that new record-level list. |
| Retained citation assessments | [consultation.py:116–130](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/consultation.py#L116-L130) | Preserve bounded valid list, snapshot digest, advisory authority, prior checkpoint and existing cited claims. The failed-answer witness has no assessment to orphan; other retained completed-seat claims remain unchanged. If removal invalidates a retained assessment, reload must refuse; no silent evidence deletion is authorized. |
| Turn reconstruction, replay, authority and interruption | [consultation.py:211–240](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/consultation.py#L211-L240); [recovery.py:147–212](https://github.com/Smart-AI-Memory/attune-harness/blob/b5a705af2fa3928b328af19dec2dceef026ce9dc/src/attune_harness/recovery.py#L147-L212) | Exact accepted digest and applicable host flags; same key/kind/effect class/request digest from frozen source and unchanged prior-round context; optional integer limit 1..100; completed siblings replay, selected event is prepared. An unresolved dispatch still refuses. Cancellation before admission causes no call; during/after dispatch D6 retains uncertain effects. Missing required origin/invalid origin also refuses before its call. |

The implementation tests must exercise each negative row with **zero new
dispatcher calls**, compare before/after durable bytes for refused reconcile,
and execute the full proposed roundtable and source-review witnesses. A shape
probe of `validate_events` is not proof of the extended loader, native Windows
launch provenance, concurrent admission or paid-model behavior. No provider
call is needed for these stub-based acceptance tests.

## Cases the tests must drive

- Real overlap: two stub seats meet at a `threading.Barrier`, so the test hangs
  if dispatch is serial. Same saved bytes in either finish order, with UUIDs and
  process diagnostics controlled.
- `--max-operations 1` and `2`: admission bound, pause after `finish`ing every
  admitted result, then continuing across a round boundary and after replay. No
  seat outside the admission is marked `dispatching`.
- Existing review callers of `perform`: replay, mismatch rejection, the exception
  path with native evidence, and pause after save are all unchanged.
- Seat A `cli_refusal`, B completes: `partial`, round 2 not run. `reconcile
  --retry-refused` for A: `paused`, attempt 2, history in
  `recovery.reconciliations`, then `run` calls A only and reaches `completed`.
- A second reconcile of the same turn is refused with zero dispatches.
- `load()` passes immediately after reconcile: no `runtime_origin`, `result` or
  `error` on the reopened event, all of them preserved in `previous`. With a capture
  policy present, attempt 2 records a fresh origin with `attempt == 2`.
- Mixed candidates: one turn with its attempt cap exhausted next to a fresh one.
  Only the fresh one can reopen; the exhausted one refuses without mutating.
- A round-2 refusal and retry: round-1 context is identical before and after.
- `timeout_effects_unknown` (no `retry_basis`): reconcile refused.
- `not_launched` with `not_found`, and with `launch_failed`.
- Negative refusal cases: non-empty or missing `modelUsage`, any
  `structured_output`, and a supervision failure with refusal-shaped stdout all
  give no `retry_basis`.
- A worker exception next to a successful sibling: the sibling is kept and the
  run is `unresolved`.
- Cancellation set before dispatch, cancellation during launch, and an interrupt
  mid-round, covering all three D6 outcomes.
- A crash after `begin`, and after the reconcile transition but before `run`:
  resume behavior matches the saved phase.
- Exit codes: `partial` and `failed` exit 2; existing statuses are unchanged. Old
  records load unchanged, and reconcile refuses them (no `retry_basis`).

## Experiments run (disposable, scratch)

- P1: current loop, first seat failing. Result: one call, `failed`, and a
  same-digest rerun is refused. The failed turn is journaled as event
  `completed` with `result.status == 'failed'`, so D5 has to reopen the event
  rather than add a new one.
- P2 (historical reported probe): revision 3 described an attempt-2 prepared
  record as accepted by `load()`. That description is not verified evidence of
  a complete D5 history reload. Revision 4's offline probe confirms only that
  `validate_events` accepts the attempt-2 `prepared/pending` event shape and
  rejects attempt 3 with `Invalid saved attempt count`. At the pinned current
  head, `load()` rejects added `recovery.reconciliations` at the exact recovery-
  profile check. The ordered journey requires the future validated history
  extension and full reload test. D5 still checks the cap before mutation.
- P3: `invoke` of a missing binary gives `not_found`; of a directory path,
  `launch_failed`. Both have `returncode None`.

## Alternatives rejected

- **A lock around `perform`:** it would serialize the calls themselves, giving no
  concurrency. Finer locks would need `perform` to be lock-aware anyway.
- **A process pool:** turns are already subprocesses waiting on I/O, so threads
  suffice and keep cancellation in-process.
- **Classifying a Claude refusal as "no call"** (first draft): `claude_refusal`
  shows no *reported* usage, not that no request happened. The review path
  already says usage may repeat.
- **Automatic retry on `run`** (first draft): retries spend again, so they stay
  operator-authorized, as `reconcile_record`'s `retry_refused` already is.
- **Retrying any failed seat:** it would re-send frozen source after a call of
  unknown effect. That breaks "no automatic retries" in spirit, and the cost
  can't be accounted for.
- **Running round 2 on a partial round 1:** round-2 seats would critique an
  incomplete table, contradicting the documented contract.
- **A new event key per retry:** it would break `operation_key` uniqueness, and
  the call-budget count of events would mistake retries for new calls.

## Files

`src/attune_harness/recovery.py` (the `begin`/`finish`/`fail` split, with
`perform` unchanged), `src/attune_harness/consultation.py` (`run`, the `dispatch`
`retry_basis`, and a consultation `reconcile`), `src/attune_harness/consultation_cli.py`
(a `reconcile` verb and the `partial` exit code; this is a new parser beside
Lane B's `check`, so whichever merges second rebases), `tests/test_consultation.py`,
`tests/test_recovery*.py` regressions, the compatibility fixture, `docs/model-consultation.md`,
the roundtable `SKILL.md`, and `CHANGELOG.md`.
