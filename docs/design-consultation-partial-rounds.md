# Design: parallel consultation rounds and partial outcomes (#233)

Status: design note, before code. Revision 3: Codex review, then a delta re-review that resolved all nine findings and added one (`runtime_origin` on retry), fixed here. Owner: Lane A (see the coordination brief
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
- P2: on a real consultation record, attempt 2 with `reconciliations`, `prepared`
  phase. `load()` accepts it. Attempt 3: `Invalid saved attempt count`. This only
  proves the load-time shape check. The retry gate checks the cap itself before
  mutating (D5).
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
