# Disposable citation-contract repair

2026-09-16. Patrick authorized proceeding with the recommendation to fix the
sorter's citation contract before integration or savings claims. Preserve all
prior frozen code, cases, replies and grades. No production memory changes.

Observed baseline: all eleven Luna replies passed JSON shape and core meaning,
but nine empty top-level reference arrays and one absent attachment filename
failed host checks, causing ten Astra repairs. The schema allowed these values
and the prompt did not state the top-level nonempty requirement. One initial
explanation was empty. This experiment repairs the demonstrated citation gap;
it does not attribute a model-training cause or change the reasoning policy.

Keep the established response fields. Bind top-level evidence_ids and fact
source_ids to enums of the supplied source IDs, with minItems=1 and maxItems=8.
Describe the top-level field as evidence supporting the operation, disposition
and explanation; fact references preserve proposed content provenance. A missing
attachment is named in request (and may appear in a truthful explanation); its
mention is supported by a supplied source, never used as a source ID itself.
Removal or classification authority cannot safely be inferred from the remaining
fact references alone, so do not synthesize that field silently. Preserve all
host validation, including unique references, fact scope, grants, versions,
staleness and complete-operation checks. Valid citations do not prove meaning.
Reject empty/duplicate-ID/oversized source packets before dispatch rather than
forcing invented citations. This supported input profile is explicit.

The [official Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs)
lists enum, minItems and maxItems support (checked 2026-09-16). It does not list
uniqueItems; do not assume provider enforcement of uniqueness. Require uniqueness
in instructions and retain the independent host check. Native schema acceptance
remains an observed part of this trial; incompatible native output stops it.

Eight fresh synthetic cases: capture, conditional correction with an exception,
distinct scoped preferences, consolidation preserving provenance, exact forgetting,
logical-kind classification, an absent attachment and an unmade owner choice.
Each runs once through the frozen old contract and once through the repaired
contract, alternating order. Same task bytes, profile and routing policy per pair.
This compares complete citation-interface packages, not schema versus wording
in isolation. These are new examples of established task shapes, not a broad
unseen-domain benchmark or measured workload distribution.

One preselected repaired conditional-correction result gets the frozen Astra
semantic audit with its citation schema constrained to the same source packet.
Audit cost is separate and included in totals. Original and repaired workers use
Luna/high; invalid or needs_reasoning output can escalate once to Astra/xhigh
with original evidence. Evidence/decision outcomes stop without stronger work.
An unresolved stronger result stops; no bounce, retry or provider fallback.

Sixteen worker jobs plus one audit: 17 planned native calls, natural/hard maximum
33 including every possible escalation. Reuse the unchanged prior transport,
Codex subscription and host profile. Per-call timeout 180 seconds bounded by
1,800-second campaign deadline. No new credentials, direct API charges,
Voyage/Anthropic requests, live-memory access or effects.

Before dispatch: reject every known empty/unknown citation failure using the
new model-facing schema without rewriting replies; validate prompt/schema
equality, no shared-schema mutation, unknown/duplicate/source-scope rejection,
valid-but-wrong citations, missing-attachment requests, removal provenance,
stale record/evidence/grants, one-hop routing, semantic-audit quarantine, private
oracle exclusion and inherited native failure/cap/deadline/frozen-run controls.
Re-run centrally after bounded read-only review, then freeze code/cases/rubrics.

Grade original and final content, operation, disposition, explanations and actual
source support independently of shape/host acceptance. Lead grading is unblinded.
Count all calls, escalations, audit, usage/cache and native process durations.
Preparation, review and grading are outside native-path costs; no first-visible
output, subscription dollar savings or general reliability claim. Any old-arm
failure stays visible. No stronger-model worker baseline is added; compare the
two contracts rather than extrapolating to all-Astra economics.

Rejected: editing the failed campaign; accepting empty/unknown references;
guessing decision evidence from surviving facts; adding a second sorter call;
claiming correct IDs establish truthful or authorized proposals; adding unrelated
response requirements or production integration to this correction.
