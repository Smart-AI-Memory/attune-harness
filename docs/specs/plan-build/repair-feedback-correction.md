# Retain rejected replies and clarify the repair handoff

Status: locally qualified under Task 8's existing non-high execution authority:
362 source and 362 installed checks pass, with 3/3 guard removals detected.
See [results](../../plan-build-repair-feedback-results.md). The paid guided-repair
trial is closed and remains failed.

The native reply copies the faulty test unchanged. The host correctly forbids
unchanged replacements. Its cursor nevertheless saves the raw response before
decoding, so a paused or failed owner becomes unreadable when validation decodes
that same rejected response. Preserve the original response while allowing a
terminal rejected participant reply to be read in paused/failed state. Resume
must consume that saved reply without calling the model again, record failure,
and apply no proposed effects. Do not relax host metadata validation, permit
operations after the invalid reply, or permit a completed status for it.

Separately, the experiment's accepted task still says to add tests. Clarify it
as repair of the observed test failure, carrying a bounded excerpt from the
actual failed probe through the existing objective/check fields. Preserve the
diagnosed expected behavior and current Spec reacceptance. This is an experimental
handoff correction, not a new product retry system or a causal claim about Luna.

Qualify wrong-scope, wrong-identity, omitted-output, unchanged-file and malformed
review replies through actual persistence, status and no-repeat resume. Reject
forged completion and post-reply effects. Reconstruct the real unchanged response
in a disposable fixture rather than editing the original owner. Run relevant
source/installed checks and remove the new guards to show the negative cases
detect them. No new paid trial is included.
