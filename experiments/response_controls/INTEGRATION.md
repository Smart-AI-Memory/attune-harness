# Response controls: integration handoff

Scope: the authorized side experiment adds runnable response controls under
`experiments/response_controls` only. It makes no model calls and does not alter
the primary experiment, its grades or the production dispatch paths. Treat the
standalone persistence in `control.py` as disposable implementation evidence.

## One runtime contract for forms, text and terminals

The host owns the attempt; the presentation shows its observed state. The current
prototype returns `id`, `phase`, `elapsed_seconds`, `message`, `warning`,
`soft_limit_exceeded`, `correctness`, `responsiveness`, `cost`, `notification`,
`cancel_requested` and `options`. Each option has a stable `action` identifier and
a user-facing `label`; notification options identify the delivery backend.

Map these to the existing communication grammar rather than inventing a separate
form system. A form button submits the attempt identity and action. Inline text
can present the same status and link to a real handler. Plain text without a
handler can explain how to act but must not imply that clicking it controls work.
The current Python functions are local calls, not an authenticated web API.

An expandable text affordance can reveal status and actions in place. Native HTML
`<details>` / `<summary>` supports this disclosure without scripting; a plain
fragment anchor by itself only navigates. [disclosure.html](disclosure.html) is a
small presentation example with no task mutation handlers. Use the host's
equivalent disclosure construct where raw HTML is unsupported. Revealing details
must not submit an action. The underlying controls still target the same owner.

Refresh state when a choice arrives. A completed attempt preserves its outcome
if a stale Cancel arrives. Repeated notification requests do not duplicate the
notice. A cancellation request and confirmed local cleanup are distinct states.
No action grants a retry, new model allocation, automatic escalation, or more time.

Product wording must retain these distinctions:

- Waiting for a response versus validating the response versus a terminal result.
- A soft elapsed-time warning versus the hard operational deadline.
- Configured checks passing versus broader correctness or full task completion.
- Local process cleanup versus provider cancellation, billing or external effects.
- A saved notice versus an OS notification request versus confirmed delivery.

## Existing seams, inspected in this checkout

- `src/attune_harness/work_build.py:build_work` acquires `RunStore.lease()` and
  checks the accepted owner before dispatch. Attach controls to this owner and its
  accepted operation; do not introduce a second job owner around a live build.
- `src/attune_harness/review_participants.py:ReviewExchange.__call__` dispatches
  command participants via `invoke`, with a configured timeout. Production work
  must propagate the owning cancellation signal and remaining deadline through
  each supported native/command adapter; this prototype does not do that wiring.
- `src/attune_harness/process.py:invoke` already accepts a cancellation `Event`,
  bounds execution/output, stops owned process groups, and preserves diagnostics.
  The prototype exercises this existing supervisor without modifying it.
- `src/attune_harness/work_runtime.py:work_status` is an existing owner-based
  observation seam. Project the control state into it and the existing effect
  journal. Standalone prototype JSON must not become competing production truth.

Notification should follow the task's actual accepted terminal state, including
required tests and review. A raw model response or successful CLI exit is not
enough. If the host cannot continue independently and deliver a notification,
omit the notification option or explicitly offer saving a local notice instead.

The selected product direction includes a real notification channel: one
meaningful notice for completion, failure or cancellation, with a host-supported
link back to the persisted outcome. Repeated unchanged progress should stay quiet.
The prototype has an optional macOS notification request and saved notice, but it
does not implement a clickable notification destination or qualify OS delivery.

## Remaining production acceptance

Wire one selected product surface to the existing runtime, then qualify it with
the normal task journal and installed CLI. Cover stale/repeated form submissions,
lost client connections, ownership loss, effect reconciliation, cancellation of
each supported adapter, real notification permissions/delivery, and supported
platforms. Verify that background continuation survives the actual host lifecycle.
No extra model allocation is implied by this handoff.

Select warning thresholds from a declared responsiveness requirement, then
measure response and validation stages separately by task class. Latency can
inform warnings but must not silently change frozen correctness scoring or route
work to a different model. There is no benchmarked model-speed or cost saving here.

Two implementation checks changed this prototype: saving a notice was initially
labeled as notifying the user, so the inbox option now says exactly what it does;
and cancellation before validator launch was initially able to say no response
had started, so its terminal state now preserves the fact that response work ran.
Both distinctions are covered by behavioral tests.
