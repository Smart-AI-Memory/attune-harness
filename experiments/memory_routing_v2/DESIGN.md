# Disposable revised memory contract and disposition experiment

2026-09-16. Patrick authorized proceeding with the plan and routing experiments
after explicitly checking whether the three proposed changes had been implemented
and live-tested. This campaign implements and tests all three in a disposable
prototype. Production integration and the separate plan/build spec are outside it.

## Prior evidence and hypotheses

The first routing campaign used 21 calls. Memory meaning was correct in all eight
authoring replies, but three rewrite replies failed control conventions. An
offline replay accepted those known replies using host-owned versions and exact
unchanged-record handling. Routing added a stronger call when Luna had already
recognized evidence insufficiency. Preserve both campaigns and all failures.

Test these hypotheses, without inventing performance targets:

1. Removing model-generated version metadata and explicitly handling unchanged
   snapshots yields usable live proposals while current-state checks still reject
   stale or altered records.
2. Distinct needs_reasoning, needs_evidence and needs_decision dispositions avoid
   unnecessary model escalation without mistaking a solvable task for missing
   information. Wrong abstention or disposition counts as failure, not savings.
3. A sufficiently evidenced multi-step policy case can test meaningful reasoning
   outcomes. Its difficulty and need for Astra are hypotheses, not established
   properties. Retain the initial Luna result for comparison even if it succeeds.

## Cases, arms and execution

A: four fresh cases (conditional correction plus exception, already-current
record, two-project correction, tentative suggestion), each in two Luna/high arms:
the frozen v1 rewrite contract and a revised rewrite contract. Eight calls.
Same logical inputs and meaning; prompts/schema differ as a complete interface
package. The v1 version ambiguity remains a known limitation of this comparison.
Revised no_change replies explicitly preview the unchanged facts; the host also
accepts an empty list. Only exact full-snapshot equality is tolerated.

The revised response has no version field. The host retains a deep-copied input
record and compares it with independently supplied current state at acceptance,
then advances the version only for an admissible update. No model-generated
version is silently repaired. Scope, fact identity, support IDs and semantic
fidelity remain separate checks. Offline tests simulate a change while a reply
is in flight, including same-version content changes.

B: three fresh cases (referenced evidence absent, a user choice explicitly not
made, and a multi-step but fully evidenced policy computation). Rotate three arms:

- direct Astra/xhigh with the revised contract;
- coarse Luna-first routing with host-owned versions and needs_review, escalating
  once on needs_review or invalid output;
- typed host routing: an explicit multi-step task flag goes directly to Astra;
  otherwise Luna, with one escalation only on needs_reasoning or invalid output.
  Needs_evidence/needs_decision yield an evidence request/decision draft without
  dispatching another model or presenting a real question about synthetic data.

The live hard case deliberately lacks the multi-step intake flag so typed Luna
must solve it or classify its need. The known-flag direct-Astra branch is checked
offline. If Luna solves the case, that is success, not an obligation to manufacture
a reasoning escalation; actual needs_reasoning emission remains separately reported.

The latter two compare complete policies, including vocabulary and initial
assignment. They do not isolate the effect of a label alone. Their worker output
shape and version/unchanged-record semantics otherwise match. The missing cases
must name the actual needed evidence/choice; the hard case must compute the
supported result, not claim information is missing. A stronger agent's unresolved
result stops; no bounce or retry loop.

One preselected revised A update (the conditional-correction case) receives a
separate Astra source-fidelity audit. Count that call separately and in campaign
totals. Unsupported/uncertain/malformed audit output quarantines that proposal;
it never authorizes writes. This one sampled audit tests the path, not a calibrated
sampling rate or proof of detection. All final results also receive unblinded
post-run lead grading, outside automated-path costs. Do not hide audit overhead
inside or exclude it from claimed production savings.

Seventeen jobs plus the one audit: natural upper bound 24 calls; supervisor cap
26 calls reused from the frozen transport. Existing Codex ChatGPT subscription,
Luna/high and Astra/xhigh, prior host profile, 180 seconds per call bounded by
remaining 1,800-second campaign time. No API spend, Voyage/Anthropic requests,
live memory writes, automatic retry or rerun. Save dispatch intent, raw outputs,
prompts, settings, usage, warnings and all rejected replies. Native boundary
failures stop the campaign; do not treat an unknown-effect transport as escalation.

## Offline checks and grading

Before dispatch: schema rejection of model version fields; unchanged full/empty
snapshots; changed facts/references/scopes; record drift after capture; invalid
and empty updates; no-change versus information/decision/reasoning distinctions;
one-hop escalation; no escalation on supported missing-evidence or user-choice
outcomes; audit quarantine; native failure, deadline, cap and frozen-rerun guards.
Freeze cases, rubric, schedule, code and expected policy before live dispatch.

Grade contract acceptance, semantic correctness, disposition, unsupported claims
and safe effects separately. Preserve unknown/ambiguous outcomes. Compare all
native calls/tokens/process time per arm, including failed/secondary calls and
the explicitly reported audit. These tiny synthetic samples do not estimate
general reliability, workload frequency, subscription dollar savings or time to
first visible finding. Source support IDs alone cannot prove correctness.

Rejected: patching old campaigns; teaching a new version-echo convention instead
of binding in the host; accepting arbitrary no_change payloads; treating every
needs_review as stronger-model work; declaring the stronger model necessary from
a synthetic case label; pretending an already-active lead was measured. Real
active-lead/session reuse and installed memory features remain separate trials.
