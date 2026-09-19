# Guided repair trial — startup failure, September 18, 2026

**The native repair trial stopped before a model response.** Patrick approved
the prepared two-call trial with “a/approve.” Its first Codex process exited
during app-server client initialization because the outer workspace sandbox
could not write Codex's own local state database. Native stdout is empty; no
model-turn event, source proposal or usage was received. Astra was not called.
The native ledger retains one unresolved process attempt and an unknown credit
estimate. Do not report absent usage as a verified zero billing deduction.

The allocation is closed under the frozen rule to stop on unresolved dispatch
or unknown usage, with no automatic retry. The work record is unresolved, its
completion handoff rejects, and there are no file effects. The completed exporter
and CLI remain unchanged. The source/installed local qualification still stands;
Task 8 is not accepted.

## Diagnosed launch boundary

Filesystem ownership and ordinary permissions permit the user's Codex state
files. The failed subprocess explicitly reports read-only database and operation
not permitted errors. A separate no-model startup probe, run with approved host
access, successfully completes the local app-server initialize handshake and
exits zero. It sends no thread/start or turn/start request. This establishes the
launch correction; it does not establish model availability, native response
quality or billing status. No credentials or Codex configuration were changed.

The execution mistake was launching the native trial inside the outer workspace
sandbox. Future trial steps need host launch access while retaining the native
participant's read-only sandbox and the existing effect-owner controls.

## Prepared restart

Propose one replacement two-call trial: Luna guided repair, then Astra final
review. Keep the original **20-credit total planning allowance**, reserve **2
credits** for the unresolved startup attempt, and cap new-call planning at **18
credits**. Expected new-call estimate remains **5–15 credits**, existing ChatGPT,
and **$0 new API dollars**. The reserve is a conservative accounting provision,
not measured usage or an invoice guarantee.

Reconstruct a fresh disposable work owner from the retained replies. Preserve
the failed native attempt and its unresolved journal; do not retry it in place.
Use the same test repair, evidence, synthetic current Spec acceptance and final
review criteria. Stop on a substantive or unresolved failure, with no further
retry or fallback. This restart requires explicit approval because the original
approved packet forbids automatic retries. It does not accept Task 8 or release.

Evidence: [startup failure](receipts/plan-build-repair-native-2026-09-18/startup-failure.json),
[raw process output](receipts/plan-build-repair-native-2026-09-18/calls/luna-routine-worker-2/raw.json),
[no-model startup check](receipts/plan-build-repair-native-2026-09-18/startup-probe.json),
[original no-retry packet](receipts/plan-build-repair-native-preparation-2026-09-18/decision-form.md).
