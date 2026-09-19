# Response controls — disposable console prototype

An executable prototype for elapsed-time warnings and user control over one
running attempt. This directory is independent of the Luna experiment's source
bindings, receipts and scoring. No model dispatch is part of the demo or tests.
The function-body replay remains with the primary session.

The implementation provides one owned, bounded local attempt with separate
response/validation stages, a configurable elapsed-time warning, keep waiting,
detached completion notification and cancellation. Status reads and user actions
must never launch a second attempt. A slow result does not become incorrect.

Acceptance: real subprocess tests cover detached completion, notification after
validation, cancellation before/during work, cancellation/completion races,
timeout, failed validation, owner loss and no repeated dispatch. Unknown effects
or cost after cancellation stay unknown. Desktop notification delivery is an
optional capability; a durable local inbox is available for console hosts.

This prototype is not enabled in Harness's existing `build` command. Production
integration must preserve the accepted work owner, dispatch budget and effect
journal. The standalone job files here are disposable experimental state.

## Shared controls, different presentation

`status(job)` returns structured state and available actions. `action(job,
"wait" | "notify" | "cancel")` applies a choice to that same job. A form, an inline
message with wired actions, or a terminal can consume this contract. Only the
terminal is implemented here; no forms integration is claimed.

The [expandable-text example](disclosure.html) demonstrates revealing the related
text inline. It is a presentation example, with no live task-action handlers.

| Action | Behavior |
| --- | --- |
| Keep waiting | Observe the same attempt; no new dispatch or deadline extension. |
| Notify me when finished | Continue independently and request a desktop notice after the terminal outcome, including any configured validation. Available with the desktop backend. |
| Finish in background — save notice | Continue independently and save `notification.json`. The inbox backend does not proactively alert the user. |
| Cancel | Record cancellation, then wait for the owner to confirm local process cleanup. Already processed work can still incur cost or external effects. |

A response received without a validator is `ready`, with correctness `unknown`.
`passed` means only that the configured checks passed. Response time, correctness,
notification delivery and cost remain separate fields. The prototype has no live
cost meter; it reports cost as unavailable. Thresholds are required configuration,
not empirically qualified product defaults.

## Try the local demo

Requires Python 3.10+ and POSIX. From any directory, this exact command runs only
the local `sleep` command; it does not invoke a model. In an interactive terminal,
choose an action when the warning appears. Without a terminal, it prints the
warning once and waits. No validator is configured in this demo.

<!-- flow: local-response-demo -->
```sh
python3 -B /Users/patrickroebuck/attune-harness/experiments/response_controls/control.py start \
  --jobs /private/tmp/attune-response-demo --cwd /private/tmp \
  --label "Local response demo" --warn-after .2 --timeout 5 \
  --notify-backend inbox --attach -- /bin/sleep 1.3
```

The first output line is the job directory. The `status`, `wait`, `notify` and
`cancel` subcommands each take that path as their sole argument. `start` without
`--attach` returns the path immediately while the owned worker continues.

Use `--validator-json` with a JSON array of an absolute executable and arguments
to validate response text delivered on stdin. `--notify-backend desktop` enables
an optional macOS notification request. OS delivery and visibility have not been
qualified here: a successful request is not proof that the user saw a notice.
Delivery failure remains visible in status and retains the local notice.

## Verification and optimizations

The behavioral suite uses actual local subprocesses for background lifetime,
validation, deadlines and cancellation; notification failure and a precise
cancellation race use controlled injection. See [verification.json](verification.json)
for the measured result and file hashes. Run the suite with a Python environment
containing pytest:

```sh
python3 -B -m pytest -q -p no:cacheprovider /Users/patrickroebuck/attune-harness/experiments/response_controls/test_controls.py
```

- Status polling reads small state records instead of reloading response text or prompts.
- Cancellation observation stops promptly when the attempt finishes.
- The soft warning appears once per attachment. The terminal keeps observing
  completion while the user considers a choice, so an unanswered prompt cannot
  hide a completed result.
- One total deadline covers both the response and configured validation.
- Late or repeated choices cannot start another attempt; completed results are retained.

No model cost reduction or response latency improvement is claimed. These are
control and supervision improvements, not a faster model experiment.

## Limits and integration

Owner loss is reported as unresolved; inspection cannot restart or reconcile it.
The detached worker survives its client exiting but is not a durable service
across host shutdown. This experiment uses POSIX locks; Windows is not qualified.
Commands run with ordinary local permissions, not inside a security sandbox.
Use only explicitly authorized commands.

See [INTEGRATION.md](INTEGRATION.md) for the existing runtime seams, shared
presentation contract and remaining production acceptance work.
