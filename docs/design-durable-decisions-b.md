# B — retain decision text before collection

September 18, 2026. A's source hashes still match its 476-test receipt. Patrick
authorized completing A, then B. B's outcome: the question, choices, consequences
and evidence remain inspectable when a form disappears, and delayed responses
remain bound to the current work and existing collector. No native calls, active
plugin changes, C–F or release work are included.

Cases: missing planning intent/choices; a complete draft's Spec approval view;
delayed valid answer; dismissal/silence with no answer; partial planning answers;
changed work/source/config; reopened/expired or consumed Spec bindings; high-risk
actions and required-control rejection; artifact write failure before collection;
restart and read-only status; work created before this feature without an artifact.

The disposable actual-Spec probe at
`/private/tmp/durable-decisions-b/baseline.json` established: `open()` renders the
goal, scope, criteria, actions, consequences and bound reply template, but writes
no artifact and leaves the checkpoint unchanged. A delayed same-host response
is accepted, and its duplicate is rejected. Existing planning questions already
derive Markdown and the answer mapping from the saved work; their responses are
checkpoint-bound. No model/provider was used.

Retain the latest display as an atomic `decision.json` artifact beside the existing
work record. Bind it to the exact work checkpoint and retain the actual existing
renderer output; it is a display artifact, never a second authority store.
Opening a Spec view must save it before returning for collection. Retain known
collected outcomes as well. Surface the artifact through read-only status, clearly
distinguishing current text from historical/consumed text and warning that saved
text cannot revive expired host authority. Add an explicit `plan --decision`
preview for questions or the complete draft's approval view, without approval
or dispatch. Plan mutations that display missing questions also retain their
text. Existing `--accept`, answer JSON, authority and exit-code contracts remain.

Use the existing atomic JSON writer and work writer lease; recheck the bound
owner before artifact writes. Do not change the task's persisted schema or digest
simply to display a question. Keep status read-only even when the display artifact
is absent or invalid. The live Spec collector remains the response validator;
changed or replaced displays must be reopened, and old responses must never be
silently rebound. Test durable text, actual collection, read-only inspection,
restart and rejection behavior together.

Rejected: putting the projection inside `record.json` (would rotate the checkpoint
while displaying it), a separate approval protocol or guessed text-to-action
router (would duplicate established controls), and changing native form timers
(the display-lifetime incident is not a Harness renderer qualification).
This is the authorized implementation design, not another approval gate.
