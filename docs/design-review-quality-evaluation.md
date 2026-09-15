# Documentation review quality: frozen local acceptance check

Patrick authorized comparing single-pass review with Harness on a small fixed
set, measuring misses, unsupported findings and review effort. No production
change is part of this evaluation. Done means all scheduled trials retained,
scored against an independent answer key, and a pass/revise/inconclusive decision
with the next demonstrated gap. The proposed acceptance target is no missed
critical defects and no invented findings on this set.

Pre-code disposable probe: strict verification returned `verified` for both a
correct timeout policy and a contradictory automatic-retry policy, because its
one supported extracted claim was a valid local Markdown link. This confirms
that execution/verification status cannot grade policy-review quality. The probe
made no model call; `receipts/review-quality/disposable-probe.json` retains both
results. Its short documents were disposable fixtures, not project edits.

Freeze six short controlled documentation excerpts derived from actual Harness
recovery/evidence/migration documentation: a correct timeout policy and one
critical contradiction; correct handling of unknown claims and one critical
promotion to verified; and two explicitly unresolved preference/effort claims.
Each has a complete short reference file and valid local link. The oracle stays
outside the corpus and never enters model prompts. These are controlled excerpts,
not six full real-world projects or a representative performance benchmark.

Compare the installed dev5 single-pass model with the existing dev5 Harness
two-role workflow. Both use the same pinned local Llama model, system policy,
objective, schema, 2,048-token ceiling, tokenizer and document/reference facts.
The baseline receives the full reference file directly. Harness receives real
retrieval and strict verification and produces two independent narratives. The
comparison measures the complete workflows: it does not isolate the effects of
tools, prompt layout and a second call. Match the baseline seed to the lead seed,
use a separate reviewer seed, and shuffle the 36 trials with a fixed order seed.
Six cases × three repeats × (one baseline + two Harness generations) = at most
54 generation calls. No paid APIs, retries, model downloads or parameter tuning.

Freeze scoring before generation. Review each narrative against the oracle with
arm/role labels hidden in a shuffled packet; keep a separate hash-bound mapping.
Codex supplies explicit quote/rationale judgments in this existing session, not
the model under test and not an independent human replication. Score a critical
issue detected only when the narrative identifies the specific contradiction;
generic uncertainty is insufficient. Unsupported assertions need an exact quote
and a reference-based explanation. Suggestions/questions clearly presented as
uncertain are not invented defects. Explicit false endorsements count as
unsupported; a generic failure to find a planted issue counts as a miss.

At workflow level, a critical issue is detected if either delivered narrative
identifies it. Any unsupported assertion in either narrative fails the workflow.
Ambiguous cases pass only if uncertainty is preserved in every delivered
narrative. Failed/incomplete executions stay in denominators and cannot pass.
Report both workflow and per-narrative evidence, so aggregation cannot hide a
weak lead. Keep all repeats and do not tune the rubric after reading outputs.

Measure elapsed time, input/output tokens, narrative count/words and corrections
needed (missing critical issues plus unsupported assertion instances). The last
two are inspection-workload proxies, not Patrick's personal review/repair time;
that remains unmeasured. Require all 18 Harness trials to complete, all six
critical opportunities detected, zero unsupported assertions, and preserved
uncertainty on all six ambiguous opportunities before accepting this bounded
quality check. Compare baseline descriptively; do not infer general superiority.

Rejected: using verifier status or keyword matching as the quality oracle;
withholding reference facts from the baseline; judging only the better Harness
narrative; repeated prompt tuning until the planted defects are found; changing
production policy during the evaluation. Add tests for scorer failures, missing
judgments, identity/hash mismatches and aggregation before freezing the runner.
