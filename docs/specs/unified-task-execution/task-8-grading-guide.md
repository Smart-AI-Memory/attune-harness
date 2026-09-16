# Task 8 human grading

The frozen original candidate completed its 60 trials. Grade only the anonymous packet at `docs/receipts/unified-task-execution/task8-subscription-live/blind-packet.json`; use `grades-template.json` beside it as the response format. Do not give the grader `blind-key.json`, protocol trial IDs, mechanical summaries, the pre-redaction packet or raw identity receipts. Absolute trial-directory names were removed recursively from the exported packet; the redaction receipt retains both hashes. Prose and assignment count may still reveal the model or arm, so this is limited blinding.

For every blind ID, supply:

- `completed_correct`: boolean; both successful execution and a substantively correct response/repair are required. An execution that failed cannot be counted as completed-correct even if its probe passed.
- `critical_miss`: boolean; did it miss a material contradiction or leave the seeded repair defect unresolved? Judge the supplied document/reference or original code/probe, not the model’s self-description.
- `unsupported_findings`: nonnegative integer; count distinct alleged defects unsupported by the supplied evidence. Clearly expressed uncertainty is not automatically a defect allegation.
- `human_correction_seconds`: measured correction time, or null if unmeasured. Do not estimate it or turn missing measurements into zero.

Assessment must distinguish a supported contradiction, a qualified consistent claim and an unsupported/unknown fact. Source matching and link verification do not certify the model’s interpretation. Repair must respect the frozen oracle and file scope. Successful execution alone is not a semantic grade.

Save all 60 entries as `grades.json`; keep failures, unknowns and all comparison arms. The auditor rejects missing, duplicate or foreign IDs and altered retained results. Run it with the original installed environment, whose module identity still matches this candidate:

```sh
.venv-task-repair-final310/bin/python -I experiments/task_execution/campaign.py audit docs/receipts/unified-task-execution/task8-subscription-live --grades docs/receipts/unified-task-execution/task8-subscription-live/grades.json
```

The separate corrected-prompt follow-up is complete: **all eight required-review repairs passed**, using 16 native calls against the new artifact. Every case failed its probe before repair, passed afterward, and received digest-bound approval with empty findings. All 212 retained artifacts and the wheel hash were reverified. See the [native receipt](task-8-live-receipt.md) and [follow-up summary](../../receipts/unified-task-execution/task8-review-contract-live/mechanical-summary.json). No repeat run is needed merely to complete this follow-up.

This is targeted requalification; retain the original 60 outcomes separately in the final ruling. The frozen protocol selected human grading for the original comparison; those grades remain pending. No assistant-generated labels have been presented as human grades.

Patrick subsequently requested outcome grading. The [supplementary assistant pass](task-8-assistant-grading.md) is complete: 48/60 original completed-correct, no critical misses, six unsupported allegations; the original auditor returns revise. The separate corrected follow-up grades 8/8. These tracked assistant labels have separate filenames and provenance; they do not replace this frozen human protocol or its template.
