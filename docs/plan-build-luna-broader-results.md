# Broader Luna trial — stopped and closed

September 18, 2026. **21 of 40 planned calls completed: 12 original passes,
9 original failures, 7.043789 estimated worker credits.** Nineteen calls remain
unused; the allocation is closed. There were no retries or new API dollars.
Ordinary session inspection/grading usage is outside the worker ledger.

The trial is **not valid as a clean candidate qualification**. A midpoint audit
found that preparation inherited a protected `src/attune_harness/documentation.py`
whose entire contents exactly matched the reference solution for `markdown-escape`
and `public-symbols`. That file was included in the frozen model-visible evidence.
This is a preparation defect, not a worker failure. It establishes availability,
not whether Luna used the reference. The audit examined all twenty cases for exact
file or named-function AST duplication; only these two matched. It does not prove
absence of every other form of leakage.

The in-flight `lb21` completed with known usage; no further call was dispatched.
The evidence-isolation requirement had been violated, so continuing with those
frozen inputs could not repair qualification. Original `lb17` and `lb19` remain
graded pass, with contamination recorded separately. Every original response,
inspection and failed grade is retained; neither the sample nor the floor is
retroactively changed. The required 40/40 floor was not met.

| Original failure | Outcome |
| --- | --- |
| lb02, observed test classification | Wrong precedence inside `classify`; exit codes 2 and 4 become `no_tests`. All eight original tests passed; semantic inspection rejected it. |
| lb05, portable paths | Malformed JSON; no effects or tests. |
| lb07, substantive prose | Correct target repair, unrelated renderer changed newline joining to literal backslash-n. |
| lb09, scoped exclusion | Malformed JSON; no effects or tests. |
| lb12, finite amount | Correct body, incorrect copied preimage hash; rejected before effects. |
| lb15, rank fusion | Duplicate rows still consume rank positions. |
| lb16, recursive glob | Entire source encoded with literal backslash-n; invalid Python. |
| lb18, context reserve | Unchanged defective source; rejected before effects. |
| lb20, SQL escaping | Malformed JSON; no effects or tests. |

The original median native response time was 89.80 seconds; no matched Sol calls
ran. There were 116 actual test executions. All 16,944 earlier receipt hashes
verify unchanged. Grades were frozen before aggregate analysis. These controlled
mutations in twelve real modules do not measure population reliability, and
the incomplete, contaminated trial cannot establish a general Luna pass rate.
Tasks 1–7 remain accepted; Task 8, native final review and connected completion
remain unqualified. No production router changed.

Patrick authorized a separate zero-model-call function-body replay after this
closeout. Its results must stay separate from these native grades; it cannot
repair the trial or establish fresh model reliability, cost or latency.

Evidence: [summary](receipts/plan-build-luna-broader-native-2026-09-18/summary.json),
[frozen grades](receipts/plan-build-luna-broader-native-2026-09-18/grades.json),
[reference-leakage audit](receipts/plan-build-luna-broader-native-2026-09-18/reference-leakage-audit.json),
[within-function counterexamples](receipts/plan-build-luna-broader-native-2026-09-18/lb02-preservation-diagnostic.json),
[closeout verification](receipts/plan-build-luna-broader-native-2026-09-18/closeout-verification.json).
