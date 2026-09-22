# Default-output oracle correction — September 18, 2026

**The local correction passes 38 source checks, 38 installed checks and 1/1
guard-removal detection. No new model calls ran.** The original four-call native
journey remains failed; Task 8 remains open.

Fixture preparation captures stdout from the original documentation CLI for
normal and empty input before worker effects. The two strings are embedded in
the existing protected acceptance.py. Existing snapshot and oracle hashes bind
them; no new gate or state store is introduced. Verification compares against
these pre-change bytes and still checks receipt consistency. It cannot silently
regenerate the expected result from the candidate implementation.

The six focused cases accept the captured baseline and unchanged passing Astra
artifacts, reject the original Luna regression through both baseline and feature
checks, reject an empty-input default regression and missing capture, and show
that removing the new equality assertion recreates the original false green.
The separate guard trial retains both subprocess logs. Original replies are not
edited. All 1,298 earlier plan/build receipt files are verified unchanged.

The broader 38-check suite covers preparation freshness, original malformed-choice
rejection, import origins and the actual connected handoff replay. It passes
against source and the previously qualified installed Harness/Spec artifacts.
No product Python module changed in this oracle correction, so a new product
wheel was not built. The optional Spec dependency retains its existing ModelTier
deprecation warning. Formatting and lint checks pass.
Both existing lifecycle checks pass. The local Spec workspace records progress
at revision 25, event sequence 25, with Task 8 still current; no acceptance event
was published.

The separately retained installed replay reuses five original native Astra replies
and one explicitly scripted final reviewer, with native dispatch forbidden. It
completes effects and checks, requires synthetic correction/reacceptance, preserves
completed work, rejects replay and stale source, and makes no repeated participant
calls. Local binding now includes fixture preparation and oracle sources too.
This is local integration evidence, not native final-review or completion evidence.

The correction covers two fixed sample inputs, not arbitrary compatibility or
production reliability. It adds no feature to the shipped documentation exporter;
that exporter remains a disposable experiment. The prior supplemental-runner
correction is preserved. Planning critique transfer remains a logged opportunity.

Evidence: [source checks](receipts/plan-build-default-compatibility-2026-09-18/source-tests.xml),
[installed checks](receipts/plan-build-default-compatibility-2026-09-18/installed-tests.xml),
[guard trial](receipts/plan-build-default-compatibility-2026-09-18/guard-removal.json),
[installed replay](receipts/plan-build-default-compatibility-2026-09-18/installed-replay/qualification.json),
[original native result](plan-build-handoff-confirmation-results.md).
