# Assessment correction: bounded comparison passed

2026-09-17. The selected correction is implemented in a separate
[experimental contract](../experiments/assessment_quality/correction_v2.json).
It requires qualification, removal or evidence for unsupported definite assertions,
while treating an accurately disclosed unknown as acceptable. Optional wording
advice remains separate. The production instructions and original Task 8
acceptance have not changed.

Patrick approved the additional 24-call allocation through the decision form.
The [approval](receipts/assessment-quality-correction-2026-09-17/approval.json)
and [live protocol](receipts/assessment-quality-correction-2026-09-17/live/protocol.json)
bind the prepared contract. **All 24 native calls completed.** Forty offline
controller/contract checks pass. The preparation evidence below remains separate.

## Result and limits

The independent graders and the lead's frozen review agree on all 16 substantive
assessments. Both arms satisfy the prospective semantic floor:

| Lead profile | Baseline correct | Revised candidate correct |
|---|---:|---:|
| Fable 5.1 | 4/4 | 4/4 |
| Astra | 4/4 | 4/4 |
| Total | **8/8** | **8/8** |

All **48 control judgments** passed: six known-answer controls repeated across
eight grading batches. There were no matched regressions, critical misses or
unsupported findings in the real assessments. Both revised-candidate responses
to the signature case require qualification, removal or evidence; both preserve
actual signing as unknown. The disclosed-unknown cases are accepted. Optional
precision suggestions stay optional, and tool claims remain within the shown
link checks. See the [machine audit](receipts/assessment-quality-correction-2026-09-17/live/audit.json)
and [lead reconciliation](receipts/assessment-quality-correction-2026-09-17/live/reconciliation.json).

**This supports the correction on these cases; it does not demonstrate superiority
over the baseline.** Four fresh synthetic cases and one repetition do not establish
representative reliability. The missing-signature evidence is explicitly disclosed
in the references; ordinary documents with implicit gaps, conflicting sources or
unclear authority remain untested. Original Task 8 remains unaccepted. Production
instructions, the active plugin and release status are unchanged.

Two Fable outputs—baseline a05 and candidate a09—measured 351 under the experiment's
whitespace word counter. It includes standalone Markdown markers. Thus 14/16 fall
below 350 by that convention; this is a separate length observation, not an
independent semantic-grade failure. The grader packets carry the case requirements
but do not grade the shared response-length request. Do not present the semantic
score as proof of every formatting instruction being satisfied. O-17 records the
reading-length opportunity. [Measurements](receipts/assessment-quality-correction-2026-09-17/live/assessment-metrics.json)
also retain native-call timing; four observations per arm do not establish a
latency advantage or explain the user's total wait.

The [frozen lead review](receipts/assessment-quality-correction-2026-09-17/live/lead-review.json)
predates independent grading. Sol graded Fable and Fable graded Astra; neither
grader received arm labels, case keys or earlier grades. Grading remains assistant
review, not human acceptance. The different graders also prevent treating this
small table as a model ranking. Codex retained the existing skill-context-budget
warnings, while every call returned a completed answer. Native host context and
authenticated Codex model identity remain outside this qualification.

Recommendation: carry the revised contract into the next experimental qualification
with realistic mixed-evidence documents. Preserve the successful distinction and
test its generality before production adoption. No additional campaign is implied.

## Changes and pushback incorporated

The four fresh cases use delivery receipts, not the previously examined Canada
example. They test both the intended correction and possible overcorrection:

| Case | Expected assessment |
|---|---|
| Definite Ed25519 signature claim; source silent about signatures | Require qualification, removal or substantiation. Actual signing behavior remains unknown. |
| Guide accurately says signing behavior is unknown | No defect. Missing evidence alone does not require a document change. |
| Receipt available at transfer start; source says only after completion; required owner absent | Require correction of the contradiction and addition of the explicitly required owner. |
| Availability correctly qualified and owner named | No defect. Optional publication-date or glossary advice cannot become a requirement. |

The prospective grading rule separates detection from disposition. Noticing a gap
but making correction optional is an incorrect assessment. It is not labeled a
failure to notice the gap. Missing a separate operational defect can still be a
critical miss. Every candidate output must be correct regardless of severity.
This clarification does not rewrite the old grades or resolve their disagreements
retroactively.

Each grading packet carries six known-answer controls: the original three plus
optional-only correction, a disclosed unknown with harmless optional advice, and
an invented opposite fact. Control answers and case keys are withheld from grader
inputs. The full document, references and limited host checks come from the actual
assessor request; omitted evidence blocks preparation. A passing control cannot
override an incorrect real sample.

The previous eight cases remain development regressions for transport only. The
offline preparation used injected responses; the separate live comparison above
supplies the model evidence. Deterministic tests alone do not establish that the
revised prompt improves reasoning.

## Verification and retained evidence

The [offline rehearsal](receipts/assessment-quality-correction-2026-09-17/prepared/offline-result.json)
completed **16 fresh-case and 16 retained-case transport runs** through the real
installed task intake, acceptance, retrieval and verification path. Native
responses were explicitly injected, with process dispatch prohibited. Eight
prospective grading packets preserve the assessor-visible evidence and omit arm
labels, model identities and answer keys. Provider calls: **zero**.

Preparation passed **35 scoped automated checks** against the qualified installed
Harness candidate. They cover the existing experiment controller and the new
correction: evidence equality, omission rejection, wrong dispositions, false
allegations, grader identity completeness, budget arithmetic, unknown prior usage,
and immutable old receipts. The
[JUnit receipt](receipts/assessment-quality-correction-2026-09-17/prepared/offline-tests.xml)
records that preparation run. The execution adapter then passed
[40 controller/contract checks](receipts/assessment-quality-correction-2026-09-17/controller-tests.xml),
including allocation matching, complete grading, receipt tampering and replay
prevention. Ruff and Black checks pass.

All **384** files in the completed experiment's manifest match. The original
fixture, runner, grading amendment, raw outputs and cost history are unchanged.
The new [proposal](receipts/assessment-quality-correction-2026-09-17/prepared/proposal.json)
binds its own contract, preparation code and all 53 inventoried installed module
hashes. The [verification receipt](receipts/assessment-quality-correction-2026-09-17/prepared/verification.json)
records the exact interpreter and test command. The proposal
is not a live admission and cannot be passed to the old runner as one.

During preparation, review caught an avoidable ambiguity in the clean case: its
named owner initially lacked source support. The final source explicitly names
that owner, so an evaluator need not guess whether the metadata is supported.
The earlier offline packet remains outside `prepared/` as disclosed preparation
history; only `prepared/` is the current proposal.

The host-rendering opportunity remains separate: the scratch probe verified that
existing host receipts expose only a link check and `semantic_ran=false`. Merely
rendering that receipt would not prevent overstatements in model prose. The
comparison continues grading those overstatements without simultaneously changing
the production presentation or assessment transport.

## Approved comparison and actual usage

The comparison used **24 native CLI calls**: 16 assessments (four cases × two
arms × two families), followed by eight independent grading batches of two
different cases. Matched baseline/candidate outputs for one case never appeared
in the same batch. Sol graded Fable; Fable graded Astra. Allocation:
**Astra 8, Sol 4, Fable 12**. The baseline and installed Harness profile stayed fixed.

Actual token-based estimate: **50.94182 Codex credits**, within the expected
**45–65** and **100-credit planning ceiling**. The call counts exactly match the
allocation; no extra or retried calls were needed. The previous comparison remains
59 calls / 107.62386 estimated credits. Combined: **83 calls / 158.56568 estimated
credits** across these two assessment experiments. See
[execution summary](receipts/assessment-quality-correction-2026-09-17/live/execution-summary.json)
and [ledger](receipts/assessment-quality-correction-2026-09-17/live/ledger.json).

The shared account's displayed balance remained 1,957.225698; weekly usage moved
from 64% to 65%, with ordinary usage allowed and no spending control reached.
These snapshots include other activity and are not trial-specific billing.
Claude used its existing Max subscription; billed API dollars remain unknown
rather than inferred from subscription cost metadata. No API top-up occurred.

The pre-run estimate used the prior comparable median costs: eight Astra calls
at 5.3615 plus four Sol calls at 2.56235 implied **53.1414 credits**. The wider
45–65 range allowed for new controls and changing cache/response lengths; it was
not a statistical confidence interval or a verified bill. Per-dispatch reservations
remained admission checks, not provider-enforced hard spending caps.

Patrick approved this allocation because the original **16 Astra slots were
exhausted** and 24 more calls would exceed the original 64-call limit. His form answer
was “A — Run the bounded comparison (Recommended).” It covers this comparison and
its analysis, not production adoption. The separate live ledger retains actual
call usage; the zero-call figures above describe only offline preparation.

All 384 files in the earlier experiment's manifest still match. The current
prepared packet, live admission, raw responses, task results, grades, frozen lead
review, usage and final reconciliation are retained separately. No previous
failed or disputed grade was erased or reinterpreted as a success.

Design and scratch evidence: [correction design](specs/connected-journey-qualification/assessment-correction-design.md).
Prior outcome: [completed comparison](assessment-quality-comparison-results.md).
