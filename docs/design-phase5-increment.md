# Phase 5 local evaluation increment

Status: authorized deterministic evaluation, 2026-09-14. No production policy
change or provider call. Phase 4's remote/host qualification remains open.

Cases: E1's local precursor compares the installed Attune 16.4.0 packet primitives
with installed Harness recovery. Four evidence-review variants (valid link,
broken link, unsupported prose, no retrieval results), three interruption points
(durably prepared before dispatch, effect before lost acknowledgement, durably
saved result), and two local lead directions give 24 cases per condition.
These are four evidence variants, **not** the four general task types required by
full E1. Both conditions use the same initial Harness workflow, separate processes
and directories, and retain the same accepted request and visible state. The packet
condition exports after the interruption, giving it an operator-supplied current
snapshot rather than penalizing it with a stale one. Only transport/recovery differs.

An independent local command appends one effect per request digest and saves its
reply. The oracle reads the ledger only after continuation finishes; it checks
duplicate request effects, accepted constraints and expected document outcome.
Injected producer crashes use os._exit after an actual durable save. Lost replies
come from a command that writes its effect/reply then exits unsuccessfully.
Unknown effects must block resume and transfer; explicit correlated-reply
reconciliation precedes continuation. A new lead may create a new, distinct effect.

The baseline exercises installed packet assemble/check/write/parse functions, not
the handoff_create/resume facade, whose memory linkage is outside this scope.
Its frontmatter explicitly declares experiment provenance, with no invented Git
verification. A parsed handoff requiring an operator is a valid baseline outcome,
not a failed task. Human repair time and model correctness are unmeasured. E1 is
therefore inconclusive on comparative product value even if all mechanical cases pass.

Scratch probes actually run: installed packet round-trip preserved every section;
saved RecoveryCursor result returned unchanged with exactly one callable effect.
Raw results: receipts/phase5/packet-disposable.json and replay-disposable.json.
Rejected: an invented automatic-restart handoff baseline (unfair duplicate effects);
rejecting the packet because it is not executable (not its contract); upgrading
fixture success to general recovery superiority (no human/model evidence).

E3 will prepare a versioned 12-task evaluation set, four strategy descriptions and
144 trial envelopes (three repeats). Separate task inputs from scoring answers;
prepare offline so no tool here invokes a model. Validate matrix completeness,
duplicates, task revision binding, finite cost/latency and critical misses before
reporting metrics. Synthetic validation must stay labeled synthetic and cannot
produce an adopt disposition. Exact model/settings and a priced spend plan remain
required before real trials. Do not tune on this candidate evaluation set; use
separate training tasks. Freezing these materials is readiness, not held-out results.
