# Design: parallel consultation rounds and partial outcomes (#233)

Status: design note, before code. Owner: Lane A (see the coordination brief
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

**D1. Seats within a round run concurrently. Bookkeeping stays on one thread.**
`RecoveryCursor.perform` is split into `begin(key, …)` (create the event and make
the `dispatching` phase durable) and `finish(key, result)` (record completion).
`perform` becomes `begin`, then call, then `finish`, with identical behavior, so
review recovery code is untouched. For each round, the run loop:

- `begin`s every pending seat in configuration order, on the main thread;
- runs only `dispatcher(...)` on worker threads, which never touch the record;
- `finish`es results in configuration order, on the main thread.

The saved record is the same whichever seat finishes first. Concurrency width is
the number of seats, or the remaining `max_operations` budget when one is set.
So `--max-operations 1` keeps today's exact one-saved-turn pause.

**D2. Rounds stay sequential, and round 2 needs a complete round 1.** The
documented promise ("second-round seats receive only the completed preceding
round") is unchanged. If any seat in a round fails, the run stops after that
round instead of after that seat.

**D3. A new status, `partial`.** At the end of a stopped round: at least one
completed turn gives `partial`; none gives `failed`. All answers are kept in
configuration order. `partial` exits 2, like `failed`, because not every seat
answered. The JSON envelope grows one status value (additive, with a changelog
line), and `status`/`evidence` report it.

**D4. `effects: 'none'` only where the evidence proves no call ran.**
`dispatch()` classifies a failed turn as `effects: 'none'` in exactly these cases,
and `'unknown'` otherwise:

| Evidence | Why it proves no model call |
|---|---|
| `failure` is `not_found` or `launch_failed` | `Popen` raised. P3: `returncode None`, so the process never started. |
| `refusal.kind == 'claude_structured_error'` | The CLI exited with its own error result and `modelUsage == {}` (`native.claude_refusal`). |

`cancelled_before_start` stays `status: 'cancelled'`, as now. Codex reports no
equivalent structured refusal, so a Codex sign-in failure stays `unknown`. #232's
preflight is the remedy there, not optimistic classification.

**D5. One retry, only for turns that provably made no call.** `run` with the same
accepted digest may continue a `partial` or `failed` run only when **every**
non-completed turn of the stopped round has `effects: 'none'`. Otherwise it
refuses as terminal, as today.

- A retry moves the event to attempt 2. The prior attempt goes into the event's
  existing `reconciliations` history, with `reason: 'refused_before_start'`.
  P2: `load()` accepts attempt 2 with that history and refuses attempt 3, so the
  existing journal bound caps it at one retry per turn.
- Completed turns replay without a call.
- The contract's `max_calls` is unchanged: a retried turn's first attempt made
  no model call by D4's evidence.

**D6. Interrupts.** On `KeyboardInterrupt` the main thread sets the shared cancel
event, which makes each worker's `invoke` stop its process group. It joins the
workers, `finish`es those that returned, and leaves the rest in `dispatching`.
The status is `unresolved` and effects unknown, as today. An exception raised
inside a worker, outside `dispatch()`'s own catch, is re-raised on the main
thread after the join, so it also leaves the run `unresolved`.

## Cases the tests must drive

- All seats complete, in rounds 1 and 2: `completed`, same saved bytes in
  either finish order (stub seats with reversed sleep times).
- Seat A refused (`claude_structured_error`), B completes: `partial`, B's answer
  kept, round 2 not run. A same-digest `run` retries A only (attempt 2), B is
  not called again, and the run reaches `completed`.
- Seat A `timeout_effects_unknown`, B completes: `partial`, and a retry is refused.
- A refused **and** C unknown in one round: retry refused (D5 "every").
- All seats `not_found`: `failed`, and a retry is allowed.
- A second retry of the same turn: refused (attempt cap).
- `--max-operations 1`: pauses after one saved turn, with no concurrency.
- Interrupt mid-round: `unresolved`, the finished turn kept, the others in
  `dispatching`. Resume refuses until reconciled.
- Exit codes: `partial` and `failed` exit 2; existing statuses are unchanged.
- Old records (all `effects: 'unknown'`) load unchanged, and a retry is refused.

## Experiments run (disposable, scratch)

- P1: current loop, first seat failing. Result: one call, `failed`, and a
  same-digest rerun is refused. The failed turn is journaled as event
  `completed` with `result.status == 'failed'`, so D5 has to reopen the event
  rather than add a new one.
- P2: on a real consultation record, attempt 2 with `reconciliations`, `prepared`
  phase. `load()` accepts it. Attempt 3: `Invalid saved attempt count`.
- P3: `invoke` of a missing binary gives `not_found`; of a directory path,
  `launch_failed`. Both have `returncode None`.

## Alternatives rejected

- **A lock around `perform`:** it would serialize the calls themselves, giving no
  concurrency. Finer locks would need `perform` to be lock-aware anyway.
- **A process pool:** turns are already subprocesses waiting on I/O, so threads
  suffice and keep cancellation in-process.
- **Retrying any failed seat:** it would re-send frozen source after a call of
  unknown effect. That breaks "no automatic retries" in spirit, and the cost
  can't be accounted for.
- **Running round 2 on a partial round 1:** round-2 seats would critique an
  incomplete table, contradicting the documented contract.
- **A new event key per retry:** it would break `operation_key` uniqueness, and
  the call-budget count of events would mistake retries for new calls.

## Files

`src/attune_harness/recovery.py` (the `begin`/`finish` split, with `perform`
unchanged), `src/attune_harness/consultation.py` (`run`, `dispatch`
classification, and the retry gate), `src/attune_harness/consultation_cli.py`
(the exit code for `partial`), `tests/test_consultation.py`, a compatibility
fixture if the envelope test pins statuses, `docs/model-consultation.md`, the
roundtable `SKILL.md`, and `CHANGELOG.md`.
