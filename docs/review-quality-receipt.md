# Documentation-review quality acceptance — 2026-09-14

**Disposition: revise.** The installed dev5 Harness workflow fails the frozen
quality target on this six-excerpt set. Single-pass review performs better here,
but also fails the zero-miss/zero-unsupported-assertion target. No production
code, package version, default workflow or historical receipt was changed.

## Scope and execution

Patrick authorized this comparison after the configurable output budget and
qualified tokenizer increments. The [design](design-review-quality-evaluation.md)
froze six controlled documentation excerpts: two clean policies, two critical
contradictions, and two explicitly unresolved preference/effort statements.
These are short cases derived from Harness documentation, not six full projects
or a representative benchmark. The answer key stayed outside model inputs.

Each case ran three times in two conditions. Single-pass review received the
complete document and reference directly. Harness used its existing independent
lead/reviewer command participants, each with real retrieval and strict
verification. Every Harness prompt included the complete short reference.
Both conditions used the same objective, system, schema, model and runtime
options; the baseline seed matched the lead, and the reviewer seed was one higher.
Order and grading-packet shuffles used frozen seeds. This compares whole workflows;
it does not isolate tool context, prompt layout or the second generation as causes.

- Installed package: **0.1.0.dev5**, all 22 production modules matching the
  [qualified artifact](receipts/token-accounting/artifact.json).
- Local model: **llama3.1:8b**, Ollama **0.31.1**, digest
  `46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`.
- Output ceiling: **2,048 tokens per generation**, qualified local tokenizer,
  16,384-token context, 512-token margin, no input truncation/context shifting.
- **36/36 workflow trials completed; 54/54 generations stopped normally.**
  Campaign execution took 199.82 seconds. No retries, paid APIs or downloads.
- Actual outputs used **20–336 tokens**, with at least **13,038 context tokens
  remaining after reserves**. All server input counts matched the tokenizer.
  The largest delivered narrative was 1,337 UTF-8 bytes. These failures did not
  exhaust the output or transport budgets.

## Results

| Measure | Single pass | Harness, two independent roles |
| --- | ---: | ---: |
| Completed workflows | 18/18 | 18/18 |
| Passed quality criteria | **16/18** | **9/18** |
| Missed critical issues | **1/6** | **2/6** |
| Unsupported assertion instances | **3** | **9** |
| Clean cases passing | 6/6 | 4/6 |
| Defective cases passing | 4/6 | 1/6 |
| Ambiguous cases preserving uncertainty | 6/6 | 4/6 |
| Median workflow latency | 3.50 s | 6.95 s |
| Median input tokens per workflow | 328.5 | 1,329 |
| Median output tokens per workflow | 119 | 167.5 |
| Delivered narratives | 18 | 36 |
| Total narrative words | 1,576 | 1,952 |
| Median narrative words per workflow | 95 | 111.5 |
| Correction instances: misses + unsupported assertions | 4 | 11 |

Critical detection is the union across delivered narratives. An unsupported
assertion by either participant still fails the workflow. All narratives must
preserve uncertainty in ambiguous cases. Narrative word counts exclude the common
unverified-proposal label. Counts and reading volume are inspection-workload
proxies; Patrick's personal review/repair time remains **unmeasured**.

Both Harness misses concerned the instruction to promote unknown claims to
verified. It also invented conflicts in two clean recovery trials. Other
unsupported assertions misattributed policy verification to the link checker,
misquoted the reference or guide, or invented a numerical discrepancy. Two
ambiguous trials delivered a reviewer introduction without any actual findings
or uncertainty judgment. A successful JSON response was insufficient evidence
of a useful review.

Examples retained in the [graded results](receipts/review-quality/run-01/summary.json):

- `c01.harness.2`, q006: “conflicting information between source texts and
  reference evidence.” Both supplied texts prescribe the same recovery policy.
- `c04.harness.1`, q035: “The reference evidence (reference.md) contains a similar
  statement about promoting unknown claims to verified”. The reference instead
  requires unknown claims to remain unknown.
- `c04.harness.0`, q052/q001: both discuss unknown status or missing semantic
  verification without identifying the unsafe promotion instruction.

## Verification and judgment limits

**680 tests passed**, including **26 new evaluation-only checks** and an offline
36-trial rehearsal using fake generations with real retrieval/verification.
Tests cover missing outputs, critical misses, false claims, uncertainty,
role aggregation, missing/extra grades and altered hashes. They qualify the
evaluation machinery; live quality evidence comes from the separate 54 real
generations. The [preliminary probe](receipts/review-quality/disposable-probe.json)
and [six-case offline check](receipts/review-quality/offline-verification.json)
show why strict verification status is not the narrative-quality answer key.

The [scorer audit](receipts/review-quality/score-output.txt) passed: frozen inputs,
grading mapping/result hashes, exact model/seed/options, complete reference access,
independent tool histories, raw-to-delivered response and token accounting.
[Post-run checks](receipts/review-quality/run-01/post-run-checks.json) also confirm
the unchanged dev5 wheel and production modules.

Codex graded all 54 narratives before opening their arm/role mapping, with exact
quotes and case-based rationales in [grades.json](receipts/review-quality/run-01/grades.json).
The [method](receipts/review-quality/grading-method.md) records label blinding and
its limitations: prompt style may reveal a workflow; the experiment author also
graded it; there is no independent human replication. The tested model did not
grade itself. This small repeated set does not establish general superiority.

Judgment choices remain visible. Q030 received critical-detection credit despite
its separate false assertions. Q046's explicitly uncertain suggestion was not
counted as an invented defect. Empty ambiguous-case introductions did not
demonstrate preserved uncertainty; accepting those two responses would still
leave Harness's critical misses and unsupported assertions above the target.

## Next bounded increment

Revise the review-output contract so each proposed defect binds to exact document
and reference excerpts, and tool-verified claims remain distinct from model
interpretations. Require an actual verdict and uncertainty account instead of
accepting an unfinished introduction as a review. Test fabricated citations,
false tool-verification claims and empty findings before comparing the revised
workflow with this baseline and fresh held-out cases. This is a proposed next
increment, not an implemented fix or evidence that prompt changes will suffice.
Increasing the token ceiling again is not supported by this run's results.

Keep the current workflow opt-in and its narratives unverified. The Phase 6
execution pilot remains complete within its original scope; preferred-path
adoption and broader provider/platform qualification remain open.

To reproduce the retained audit without making model calls:

```sh
.venv-token-accounting/bin/python -I experiments/review_quality/score.py \
  --output docs/receipts/review-quality/run-01 \
  --grades docs/receipts/review-quality/run-01/grades.json
```

The campaign [freeze](receipts/review-quality/run-01/freeze.json), source snapshots,
per-trial inputs, process output, native records and raw generations are retained.
The runner refuses automatic re-execution of the started campaign.
