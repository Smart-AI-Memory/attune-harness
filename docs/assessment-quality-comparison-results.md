# Assessment-quality comparison: revise the candidate

2026-09-17. **Do not adopt the candidate instructions.** Both model families
recognized an unsupported factual assertion but, under the candidate wording,
treated correcting it as optional. Their matched baseline answers required
supporting evidence or removal. The experiment is complete; production
instructions, the installed plugin and original Task 8 acceptance are unchanged.

## Results

Eight fresh synthetic cases, two instruction arms and two native lead profiles
produced 32 assessments. Opposite-family graders reviewed every retained output:
Sol graded Fable; Fable graded Astra. The completed amended grading audit reports:

| Lead profile | Baseline correct narratives | Candidate correct narratives |
|---|---:|---:|
| Claude Fable 5.1 | 7/8 | 5/8 |
| GPT-6 Astra | 8/8 | 7/8 |
| Total | **15/16** | **12/16** |

These are full-narrative grades, including claims about tool verification. They
are not population accuracy estimates or a cross-model ranking: graders differ
between families. All **48 known-answer controls** passed across 16 amended
grading calls. Passing controls did not establish correctness of the real outputs.
The [machine audit](receipts/assessment-quality-2026-09-17/grading-amendment/audit.json)
returns `revise_or_arbitrate` and records three matched regressions, no promotion.

The decisive example is case c05. The guide asserts that exports are always
stored in Canada, while the reference leaves storage region unspecified.
Both baseline answers call the assertion unsupported and require correction or
evidence. Both candidate answers describe the uncertainty but say no blocking
defect is established and make qualification optional. **An unknown real-world
fact and an unjustified assertion of certainty are different things.** The
candidate instruction blurred that distinction. See the unchanged
[Astra output](receipts/assessment-quality-2026-09-17/runs/a21/result.json) and
[Fable output](receipts/assessment-quality-2026-09-17/runs/a24/result.json).

The graders also flagged three tool-attribution statements: a11 and a17 claim a
link check confirmed a source hash; a07 says the extracted claim matches. The
first two overstate the checks shown. The a07 phrase is ambiguous: it could refer
to the extracted link rather than semantic factual matching. Its negative grade
is retained as disputed. Accepting a07 would raise the candidate to **13/16**;
the three matched regressions and recommendation remain unchanged.

The lead's frozen review initially counted **30/32 correct primary document
decisions**, with tool-attribution concerns in its notes. The independent grades
apply the broader narrative criterion above; do not interchange these counts.
Sol labels Fable's c05 failure a critical miss; the lead and Fable's grading of
Astra distinguish noticing the gap from choosing the wrong disposition. This
severity disagreement also cannot change the failed acceptance floor. The
[reconciliation](receipts/assessment-quality-2026-09-17/reconciliation.json)
preserves both differences. No human grade or acceptance was fabricated.

## Grading correction and evidence

I initially supplied graders with abbreviated case text, omitting the real
document link and the host checks seen by the assessors. That caused false
allegations of invented provenance. The simple controls passed despite this
context defect. I stopped after **43 observed native invocations**, with no
unresolved call, and preserved the 32 assessments and 11 unusable grades.

The corrected packet derives the full document, reference paths/hashes and host
checks from the actual saved assessor request. It omits arm-specific instructions
and absolute paths. Two different cases are graded per call, never the matched
baseline/candidate outputs for one case. Sixteen amended calls covered all 32
outputs without repeating an assessment. This is a disclosed grading-protocol
amendment; the original protocol and ledger remain intact. The controller's
existing integrity check safely prevented the next dispatch while the correction
was prepared; the [stop receipt](receipts/assessment-quality-2026-09-17/controlled-stop.json)
records the deliberate trigger and restoration of the frozen runner bytes.

Evidence: [original protocol](receipts/assessment-quality-2026-09-17/protocol.json),
[amended protocol](receipts/assessment-quality-2026-09-17/grading-amendment/protocol.json),
[cumulative ledger](receipts/assessment-quality-2026-09-17/grading-amendment/ledger.json),
[frozen lead review](receipts/assessment-quality-2026-09-17/lead-audit.json), and
[design/probes](specs/connected-journey-qualification/assessment-quality-design.md).
Raw requests, process output, task records and grading replies remain alongside
these receipts. Hash checks bind the final audit to those actual inputs/outputs.

## Budget and validation

**59 of 64 authorized native CLI invocations** were used: 16 Astra, 12 Sol and
31 Fable. That includes all 11 discarded grading calls. The token-based Codex
estimate is **107.62386 credits against the 250-credit planning ceiling**, within
the original 90–150 expected range. Rates use the
[published credit table](https://learn.chatgpt.com/docs/pricing); this is not a
verified account deduction. The final account check still showed **1,957.225698
credits**, 38% weekly usage remaining, ordinary usage allowed and no spending
control reached. Those are shared-account observations, not trial-only billing.

Claude used the existing Max login, and Codex used ChatGPT login with an explicit
standard-tier request. No API-key funding or top-up was added. Billed dollars
remain unknown; Claude's API-equivalent cost metadata is not treated as an API
charge. Native invocations are not assumed to equal underlying inference
requests: Claude reports two CLI turns per invocation. See
[execution summary](receipts/assessment-quality-2026-09-17/execution-summary.json).

**19 offline checks pass** against the qualified installed Harness candidate,
including the full simulated pipeline, exact assessor/grader evidence equality,
budget inheritance, stopped-call retention, frozen admission and no replay. Ruff
and Black checks pass. Final native audit revalidates raw/request/result/grade
and usage bindings. No production source changed. The wheel remains the prior
qualified candidate (`ba57ea1b…a4`), used from its isolated target install.

All assessments met the requested under-350-word limit. Baseline/candidate
median native call times were 15.69/15.89 seconds for Fable and 24.00/23.71 seconds
for Astra; median lengths were 321/320 and 78.5/79.5 words respectively.
[Descriptive measurements](receipts/assessment-quality-2026-09-17/assessment-metrics.json)
do not establish a speed advantage: each case ran once on a shared host.

## Next bounded correction

Keep the current instructions while revising the candidate around this rule:

> Distinguish contradictions, unmet explicit requirements, and factual assertions
> stronger than the supplied evidence supports. When support is missing, leave
> the real-world fact unknown while requiring a definite assertion to be
> qualified, removed or substantiated. An accurately disclosed unknown is not
> itself a defect. Keep optional wording advice separate.

This proposed wording is unqualified and was not used in the completed trial.
The later [bounded correction](assessment-quality-correction.md) implements it in
a separate experimental contract. Its separate four-case live comparison scores
8/8 for both revised candidate and baseline, with all controls passing. That result
does not revise this trial's failures or establish production readiness.
Also evaluate having the existing host receipt render mechanical verification
claims, so model prose cannot silently enlarge what a tool established. These
are targeted follow-through items, not a new router, general gate subsystem or
automatic new campaign. The original native Task 8 remains unaccepted; neither
this failed candidate nor the baseline's results establish broad operational
readiness, security isolation, live memory readiness or plan/build qualification.
