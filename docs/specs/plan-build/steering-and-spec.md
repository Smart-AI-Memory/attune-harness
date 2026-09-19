# Task 6 — Spec authority and bounded steering

Task 6 connects the existing Spec adapter and command workspace collector to a
current Harness work revision. It reuses their grammar, nonce/revision validation,
severity decisions and accepted receipt. The work record remains the sole durable
owner; the bridge neither creates a second gate engine nor upgrades the running
MCP installation. Optional Attune AI supplies the actual Spec owner at runtime.

Opening the form grants nothing. Its contract binds the current work checkpoint,
request and declared controls. A successful collector response is retained
separately from the work's planning/build/test evidence. Only an ordinary approval
or explicit auto-run choice can grant build intent; acknowledging a high finding
does not grant effects. Paid/native dispatch still requires its separate flag.
The bridge uses an in-process host. After a restart, issue a fresh form. If the
collector succeeds but work persistence fails, reopen instead of replaying the
consumed nonce. This is a cooperating single-writer boundary, not a distributed
transaction or an authentication service for arbitrary callers.

The supported human control is `spec-approval`, owner `spec`, version 1, required
at acceptance. It requires an actual retained collector receipt. Existing bounded
build hooks/checks run before governed effects; failure, unavailability and
advisory outcomes retain their existing policies. Other required planning or
acceptance controls remain blocked until their runners are qualified.

A stopped dependent build can correct pending task descriptions/checks at a
verified step boundary. Completed tasks must be identical. The new revision:

- retains the entire original request, authority and build journal in history;
- protects the completed outputs as inputs to the remaining work;
- captures fresh pending-effect preimages and verification commands;
- loses its previous grant and requires the existing Spec decision again.

The existing test handoff includes preserved earlier outputs in the final change
scope, and still rechecks the current whole checkout.

Task 8 addendum, 2026-09-18: a stopped build may also revise immediately after
the next task's settled nonzero-exit probe failure. Keep pending task identities,
outputs and dependencies fixed; retain the failed journal and require current
acceptance. This bounded repair extension passes source and installed checks
with a retained-failure replay; see [qualification](../../plan-build-repair-resume-results.md).

No uncertain operation, in-flight step, completed-intent change, deletion
or silent rewrite is handled by this correction profile. Ordinary interruption
and continuation use the existing operation cursor; file uncertainty uses the
existing explicit reconciliation operation. General goal rebasing and arbitrary
graph edits remain outside this first profile.

Legacy import uses the existing XML task parser after strict complete-block
validation. It retains supported names, descriptions, risks, dependencies and
checks in provenance; unmapped content is disclosed and its full text is retained.
Imported state/approval never grants Harness authority. Reimporting an edited
artifact retains the work identity and requires acceptance of its new revision.
A single well-formed trailing Spec state comment is excluded from the semantic
planning hash; the original whole-file hash is retained. Material prose/task
changes still invalidate authority. During an effect batch, the stricter full
checkout snapshot remains in force: even a state-comment write inside that
checkout requires reconciliation rather than silently refreshing accepted bytes.

All qualification uses temporary synthetic fixtures and scripted participants.
Local bridge behavior is not evidence of native planning/building quality or of
activation in the user's current MCP host.
