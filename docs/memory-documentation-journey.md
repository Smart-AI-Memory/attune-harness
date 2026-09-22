# Memory documentation journey: local handoff qualified, native sample pending

2026-09-17 follow-through: Patrick approved “A repair and qualify the spec handoff.”
The demonstrated stale-approval defect is now repaired in the owning Spec adapter,
using Harness-owned evidence validation. [Source and isolated installed
qualification](spec-test-handoff-results.md) passes. The complete native semantic
journey and Patrick's actual acceptance remain pending; no additional paid trial
was run. The memory adapter and live stores are unchanged.

## Verified behavior and concrete cases

The installed Attune AI 16.4.0 adapter matches the inspected source checkout:
`file_stash.py` SHA256
`9f97a33f16ca727e13aa42af52dea73415f4a24687cb0db1b32c0ce7e256391f`.
`search` adds a matching-cwd score bonus; `recent` orders matching records first.
Both returned Cedar **and Elm** from an explicit temporary two-project store.
This establishes the selected adapter's behavior, not the security properties
of other adapters or the shared-memory host.

The scoped README/docs/memory-source inspection found accurate documentation,
including the [baseline](specs/shared-memory-adoption/baseline.md) and
[capability map](specs/connected-journey-qualification/capability-map.md).
No production documentation mismatch was selected. The experiment therefore
uses the requested clearly labeled disposable fixtures.

| Case | Claim and required disposition |
| --- | --- |
| [Incorrect fixture](https://github.com/Smart-AI-Memory/attune-harness/blob/312e7af/experiments/memory_documentation_journey/fixtures/incorrect.md) | “Other projects cannot appear” contradicts the selected implementation and observed results. Correction is required. Its JSON example incorrectly predicts only Cedar. |
| Unsupported assertion in that fixture | “Every alternative memory backend guarantees the same project isolation” has no supplied support. Require qualification, removal or substantiation; other backends' actual behavior remains unknown. |
| [Correct control](https://github.com/Smart-AI-Memory/attune-harness/blob/312e7af/experiments/memory_documentation_journey/fixtures/control.md) | Describes ranking, permits foreign records and explicitly leaves other backends unknown. Accept without requiring a change. Its example correctly includes Cedar and Elm. |
| [Example correction](https://github.com/Smart-AI-Memory/attune-harness/blob/312e7af/experiments/memory_documentation_journey/fixtures/corrected.md) | Replaces the guarantee with observed behavior and preserves the unknown. Valid prose paraphrases remain allowed. |

The previously tested [assessment contract](../experiments/assessment_quality/correction_v2.json)
is passed verbatim as the criteria. Optional wording advice stays nonblocking.
The document's single JSON example is an explicit fixture requirement; the probe
compares that data with actual adapter results and never executes document text.
It does not certify surrounding prose. That judgment belongs to the reviewer.

## Existing journey and acceptance evidence

The qualified installed Harness candidate runs two independent-review assessment
tasks, a documentation-only repair, `test --from-task`, actual pytest, and the
installed AI Spec workspace/decision grammar. Six local command-participant
responses are **scripted**, so they qualify transport and controls, not native
model reasoning. All Spec actions in these fixtures are **synthetic**, not
Patrick's acceptance. The assessment→repair and test→Spec handoffs remain explicit
executor operations; no automatic bridge is claimed.

| Acceptance criterion | Local result |
| --- | --- |
| Incorrect claim receives a required correction; supported unknown is preserved | Scripted assessment supplies the required disposition; only `guide.md` is repaired. Live semantic judgment remains pending. |
| Correct control stays accepted without repair | Both scripted assessors accept it; its bytes and the unrelated dirty sentinel are preserved. |
| Actual adapter tests support the corrected statement | **3 tests passed**, executing captured byte-identical real adapter source, with installed atomic-I/O identity checked. Both APIs retain foreign records; an unmatched cwd does not hide them. |
| Tests can detect a behavioral defect | Removing the cwd score bonus in a separate disposable mutation causes the expected search-ranking test failure. |
| Stale assessment intake is rejected | Changing the supplied Markdown reference invalidates its saved acceptance submission. |
| Stale test success cannot be reused | Changing captured adapter Python source after testing makes Harness report blocked and reject reuse. |
| Existing Spec retains evidence and rejects replay | Fresh synthetic acceptance persists the linked task receipt through SpecState; replay is rejected. These fixtures' numeric gate scores are simulation data, not semantic quality grades. |
| Source change invalidates the already rendered Spec decision | **Repaired and qualified locally.** The typed Harness reference is rechecked at completion; the old form is rejected. Original failing evidence is retained, and was never persisted as accepted SpecState. |

The original preparation found that publishing a current blocked result prevented
ordinary approval, but an already rendered form remained usable after the source
changed. The correction checks through the existing task owner both at publication
and immediately before all completion paths. Executors must supply the new typed
binding; legacy arbitrary probe strings do not acquire freshness guarantees.

The original suite reported **4 passed, 1 expected failure**. That expectation has
been removed: all **5 journey checks** now pass, along with the new **25 handoff
checks** and existing connected/testing/Spec suites. See the follow-through report
for exact source and installed counts, mutation evidence and remaining limits.

## Timing and retained receipts

The original preparation run measured **0.047s** from preparation start to the actual adapter
finding, **0.294s** from assessment invocation to its first durable scripted
response, **4.059s** from preparation start to the first Spec gate rendering, and
**4.074s** for the complete rehearsal. Native reasoning time, desktop form display
time and Patrick's total wait were not measured by this simulation.

- [Original preparation result](receipts/memory-documentation-journey-2026-09-17/example-backed-prepared/result.json)
- [Actual adapter test receipt](receipts/memory-documentation-journey-2026-09-17/example-backed-prepared/work/tested/record.json)
- [Persisted synthetic Spec receipt](receipts/memory-documentation-journey-2026-09-17/example-backed-prepared/work/spec-fresh/synthetic-accepted-state.json)
- [Source-change counterexample](receipts/memory-documentation-journey-2026-09-17/example-backed-prepared/work/spec-stale/stale-decision-counterexample.json)
- [Durable rendered Spec form](receipts/memory-documentation-journey-2026-09-17/example-backed-prepared/work/spec-fresh/gate.md)
- [Qualification tests](receipts/memory-documentation-journey-2026-09-17/example-backed-tests.xml)
- [Preparation design and corrections](https://github.com/Smart-AI-Memory/attune-harness/blob/312e7af/experiments/memory_documentation_journey/DESIGN.md)

## Proposed native allocation — not approved or dispatched

After the freshness blocker is fixed and qualified, use **6 native CLI calls**:
Astra assesses each document and performs the selected repair (3); Fable performs
the two independent assessments and reviews the repair (3). The reviewer must
inspect the prose, example, supplied behavioral evidence and limited probe result;
a passing example does not automatically approve the document. The lead reconciles
the attributed results before an actual human Spec decision. Additional grading,
retries or repetitions are outside this proposed allocation.

Estimate **20–30 Codex credits**, with a **40-credit planning ceiling**, existing
Claude Max and **no new API-dollar allocation**. This is a buffered estimate from
the earlier local trial's approximately 5.4 credits per Astra assessment, allowing
more for the repair protocol. It is not current pricing verification, an account
balance check or a provider-enforced hard billing cap. CLI calls may contain more
than one inference turn. Freeze the native controller, projected evidence and
call admission before any approved dispatch. No production adoption is implied.

## Recorded decision — superseded form retained for context

Patrick selected A and authorized local implementation. The correction is now
[complete within its qualification boundary](spec-test-handoff-results.md).
The original alternatives below no longer require a response.

**Recommendation A:** expand this slice only to correct and qualify the existing
test→Spec freshness handoff. Bind the acceptance to the producing test receipt,
recheck through its existing owner when the user acts, reject changed/missing
evidence, and preserve historical receipts. Reuse the current Spec state and
grammar; add no separate gate store. Repeat the captured source-mutation case,
unchanged-evidence approval, missing-evidence rejection and replay checks.

**Counter-case:** this introduces integration work before the first live sample.
However, a model trial cannot repair the reproduced deterministic acceptance gap.

**B:** keep the documentation-only repair boundary and retain the journey as
blocked. Neither option authorizes paid calls, installation, activation or release.

Scope confirmation was needed because the initial request limited repairs to the
selected documentation. Patrick's option A expanded that boundary to this handoff.
