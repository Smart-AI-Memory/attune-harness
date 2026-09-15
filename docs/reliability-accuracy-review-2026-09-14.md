# Attune Harness reliability and accuracy review

September 14, 2026, America/New_York. Patrick selected the known failures as the starting point. Original review scope: inspect current code and saved evidence, replay failures offline, check relevant regressions, and prioritize repairs. That review made no production edits or new model calls. Patrick subsequently authorized implementation; its outcome is appended below.

## Recommendation

**Repair the grounded-review output contract first, then measure end-to-end review quality again.** The current guards preserve useful boundaries, but the evaluated model could not produce an accepted review in any of the 27 grounded trials. A guard that rejects an invalid answer protects accuracy; the workflow also needs to produce useful, supported answers reliably.

Do not loosen citation checks or treat a passing software test suite as proof of accurate model judgments. The proposed correction is to let the host own citation identities and derive the overall verdict from individual assessments, reducing avoidable model-generated bookkeeping.

## What the evidence establishes

### 1. Grounded review is the immediate workflow failure

The saved dev6 campaign contains **27 failed Harness trials and zero delivered reviews**, across six regression cases and three new cases, repeated three times. Its [summary](receipts/grounded-review/run-01/summary.json) remains `revise`. Every first failure was `Reference quote/path is absent from retrieved evidence`.

I replayed all 27 retained outputs through the unchanged current renderer. Every rejection reproduced. Independent inspection also found:

| Structural problem | Trials affected |
|---|---:|
| Absolute reference paths outside the supplied relative-path choices | 27/27 |
| At least one reference path points to the reviewed document itself | 22/27 |
| At least one purported document quote is absent from that document | 8/27 |
| Overall verdict disagrees with the passage assessments | 10/27 |

Categories overlap. These are structural observations, not new semantic grades. The first path rejection masks later errors; merely removing a path prefix would not resolve the full problem. The renderer correctly prevents the reviewed document from corroborating itself.

[Replay evidence](receipts/reliability-review-2026-09-14/grounded-replay.json) · [Self-reference details](receipts/reliability-review-2026-09-14/citation-path-details.json) · [Current renderer](../src/attune_harness/grounded_review.py)

### 2. Accurate interpretation remains a separate problem

The prior dev5 comparison passed **9/18 Harness quality trials versus 16/18 single-pass trials** on the same six short cases. Harness delivered nine unsupported assertions and missed two of six critical opportunities. The [original receipt](review-quality-receipt.md) explicitly records that output and context budgets were not exhausted.

The newer dev6 single-pass comparison covered only the three new cases, while its Harness arm included all nine cases. Those overall denominators must not be presented as a matched model ranking. Neither experiment qualifies other models, general repository repairs or autonomous documentation editing.

Exact source selection will improve provenance handling only if demonstrated. It cannot establish that a model's interpretation is correct. The [verification integration](../src/attune_harness/verification.py) explicitly checks supported extracted claims without a semantic judge; its result does not certify participant prose.

### 3. More collaboration has not demonstrated better value here

The earlier [144-trial collaboration experiment](e3-local-research-receipt.md) found adaptive and fixed-roundtable strategies each correct on 22/36 trials. Adaptive missed two critical opportunities versus one for roundtable, with negligible measured token and latency reduction. All roles used the same installed model weights. Keep adaptive escalation experimental; this evidence does not qualify mixed-model teams.

### 4. Recovery has passing local checks and explicit platform gaps

The fresh targeted run passed **130 tests** across grounded-review validation, recovery and subprocess handling. These were local behavioral checks, not new model evaluations or a full-suite run. [Command and output](receipts/reliability-review-2026-09-14/targeted-tests.json)

Current [process handling](../src/attune_harness/process.py) and the [review-store lease](../src/attune_harness/review_store.py) explicitly reject non-POSIX operation. Windows support for these paths is an implementation gap. The separate [Guardian fixture experiment](../experiments/guardian_v1/RECEIPT.md) passed 20 macOS cases; Windows/Linux native service lifecycle and process containment remain unqualified.

## Prioritized repair plan

| Priority | Proposed change | Evidence needed before calling it successful |
|---|---|---|
| 1 | Give document and reference passages distinct host-issued identifiers; constrain model selections to supplied identities; render exact source text in code. Derive the overall verdict from passage assessments. | The old invalid/self-citation cases stay rejected; valid selections work; all original failures remain retained; a separately frozen end-to-end campaign demonstrates usable completion. |
| 2 | Evaluate semantic accuracy on fresh cases with an independent answer key, including clean documents, actual defects and explicit uncertainty. Compare capable reviewers on the same tasks. | Report completion, critical misses, unsupported claims and preserved uncertainty together. Keep failed attempts in the denominator. Source matching alone never counts as semantic verification. |
| 3 | Qualify native execution and recovery adapters, starting with Windows process ownership/cancellation and durable work ownership. | Native crash, lost-acknowledgement, cancellation, descendant-cleanup and restart evidence on each supported platform. A simulated platform flag is insufficient. |
| 4 | Revisit team routing only after individual review/repair quality is established. | Compare the same task mix, retain escalation and retry costs, and measure total cost per verified repair alongside verified completion rate. Include validation and human review; currently those costs are not fully measured. |

At the time of the original review, the citation/derived-verdict design was a **proposal**. It is now implemented as dev7, with the failed quality disposition recorded below. New experiments must use fresh output directories and frozen criteria; preserve dev5/dev6/dev7 packages, inputs, scores and failed generations.

## Evidence maintenance

Current source hashes match all 23 modules listed in the retained dev6 artifact. The build-history rollup and `CLAUDE.md` still end with the older documentation-quality result, and the grounded campaign lacks a top-level closing receipt. The smallest useful documentation task is to reconcile that status so a future session cannot mistake dev6 for unevaluated work or miss its 0/27 result. The most urgent product task remains the grounded-review contract.

This review adds its own evidence and plan. It does not change historical results, production defaults, the unrelated steering-cards spec, or the supported-platform claims.

## Authorized implementation outcome

The [dev7 passage-review receipt](passage-review-receipt.md) closes the first implementation increment and the bounded local part of priority 2. Host-issued document/reference IDs, exact host-rendered text and a derived verdict are implemented behind `--grounded-passages`. All 27 old invalid outputs remain rejected. **758 software tests, 35 installed review/recovery checks and 10/10 targeted mutations pass.** The original commands and historical evidence are preserved; the dev6 closing receipt and status rollups are now current.

The new frozen campaign evaluated **45 trials / 76 local generations**. Harness completed **30/36** and passed all quality criteria in **2/36**, with **three critical misses and 73 unsupported assertions**. On the matched three fresh cases, Harness passed **0/9** versus single-pass **5/9**. All six workflow failures were duplicate passage assessments. Exact quotations worked in delivered reviews, while reasoning often attributed body policies to headings or footers. The independent answer key and blinded-before-mapping grades are retained; the experiment author also graded, so independent human replication remains open.

**Disposition: revise.** The contract implementation is complete; the intended semantic reliability is not established. The mode remains opt-in. Before another live run, replace model-chosen metadata comparisons and repeated pairs with host-assigned substantive assessment slots, then test focused policy interpretation. Broader capable-model comparison, Windows/Linux native qualification and cost-per-verified-repair team routing (priorities 2–4) remain open. The local result does not authorize paid-provider calls or support a claim of autonomous documentation quality.
