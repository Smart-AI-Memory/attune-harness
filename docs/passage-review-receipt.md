# Passage review dev7 — receipt

**Current status: dev7 implemented and locally evaluated; semantic quality remains `revise`.** Recorded September 15, 2026 UTC (September 14 in America/New_York).

Patrick authorized implementing the [reliability/accuracy review](reliability-accuracy-review-2026-09-14.md). The [design](design-passage-review.md) precedes the production diff. This increment adds explicit `--grounded-passages`, host-issued passage IDs, closed citation choices, exact host-rendered quotations and a derived overall verdict. The original `--grounded` and narrative modes remain available for accepted commands and reproducibility.

## Implementation evidence

- **758 software tests passed**, including **36 new cases**. The first full run retained 33 A2A loopback-bind failures caused by sandbox restrictions; the run with loopback access passed. [Passing log](receipts/passage-review/full-tests-02.txt) · [Initial restricted run](receipts/passage-review/full-tests.json)
- **10/10 targeted mutations detected; 29/36 new tests fail under at least one relevant mutation.** Mutations use disposable source copies. This is not an exhaustive mutation score. [Mutation evidence](receipts/passage-review/mutations/summary.json)
- **24 installed production modules match source** in a new offline-installed dev7 environment. [Artifact](receipts/passage-review/artifact.json) · [Build/install commands](receipts/passage-review/build-install.json)
- **35 installed workflow/recovery checks passed**: 12 review cases and 23 recovery cases, including one retained external fixture effect and two transfer directions. [Review](receipts/passage-review/installed-review.json) · [Recovery](receipts/passage-review/installed-recovery.json)
- An offline rehearsal exercised **45 trials / 81 fake generations**, real retrieval/verification and the new scorer. It is machinery validation, not model-quality evidence. [Rehearsal](receipts/passage-review/offline-rehearsal.json)

All 27 old malformed raw outputs still fail the new contract. Stale/cross-role IDs, self references, copied citation fields, duplicate pairs and invalid content are rejected. Matching passages can still be interpreted incorrectly; the test suite explicitly preserves the unverified-proposal label for that case.

## Live comparison

The separate [frozen plan](receipts/passage-review/run-01/freeze.json) covers 12 cases: nine retained regressions plus three fresh cases, repeated three times. Harness uses the new mode on all 12; the original dev5 single-pass baseline runs on the three fresh cases. Maximum 45 trials / 81 local generations / 1,200 seconds. The installed model/tokenizer and 2,048-token ceiling are pinned; failed generations are retained with no retry or fallback. The [grading rule](https://github.com/Smart-AI-Memory/attune-harness/blob/312e7af/experiments/passage_review/GRADING.md) is frozen before inference.

The campaign finished all **45 planned trials**, using **76 local generations in 697.32 seconds**, with zero paid API calls. The installed `llama3.1:8b` Q4_K_M model, Ollama 0.31.1, seeds and tokenizer are recorded in the frozen protocol. The mechanical audit passed: retained source/input hashes, model identity, prompts, schemas, actual token counts, citation catalogs, rendered text and exact grading quotations match their receipts. This audit validates evidence integrity, not semantic truth.

### Full Harness result

| Measure | Frozen requirement | Observed |
|---|---:|---:|
| Completed two-role reviews | 36/36 | **30/36** |
| Critical misses | 0/12 opportunities | **3/12** |
| Unsupported assertions | 0 | **73** |
| Ambiguous trials preserving uncertainty | 12/12 | **11/12** |
| Trials passing all quality criteria | 36/36 implied | **2/36** |

All six rejected generations contain duplicate document/reference assessment pairs: five lead failures and one reviewer failure. They stopped normally at the model transport boundary and were rejected by the existing semantic structure check; no retry or silent deduplication occurred. Five skipped reviewer calls account for 76 rather than 81 generations. All three critical misses concern promoting unknown evidence to verified status: two trials failed before delivering a narrative, and the completed trial failed to identify that conflict in either role.

Real source identifiers and exact quotations now work for the delivered reviews. They do not prevent an explanation from attributing a policy to a selected heading or footer that lacks it. Other retained errors include invented disagreement between compatible policies. Detection credit and a false attribution can coexist; that still fails the quality criterion.

### Matched comparison: three fresh cases, three repeats each

Only these nine trials per arm are a matched comparison. Both arms use the same model weights; Harness has two independent roles and the new structured contract, while the baseline uses the preserved dev5 single-pass narrative contract.

| Measure | Passage Harness | Single pass |
|---|---:|---:|
| Completed | 9/9 | 9/9 |
| Passed every quality criterion | **0/9** | **5/9** |
| Critical misses | 0/3 | 0/3 |
| Unsupported assertions | 20 | 2 |
| Ambiguous trials preserving uncertainty | 3/3 | 1/3 |
| Median trial elapsed time | 23.00 s | 3.11 s |
| Median input/output model tokens per trial | 1,280 / 852 | 328 / 93 |

Historical regression cases are separate: Harness completed **21/27**, passed **2/27**, missed **3/9** critical opportunities, produced **53** unsupported assertions and preserved uncertainty in **8/9** ambiguous trials. The earlier dev6 0/27 result and this campaign have different case sets and contracts; they are not a matched estimate of improvement.

The blind packet contained 70 delivered narratives. The experiment author graded them before opening the role/arm mapping, with exact error quotations and a saved grade hash. Recognizable formatting limits blinding; this is **not independent human replication**. Conservative borderline judgments and the clean baseline's empty findings introduction are visible in the grades. Two baseline ambiguous outputs were empty introductions and failed uncertainty preservation. No new completeness penalty was invented after seeing these outputs.

[Audited summary](receipts/passage-review/run-01/summary.json) · [Matched/regression breakdown and failed generations](receipts/passage-review/run-01/breakdown.json) · [Exact grades](receipts/passage-review/run-01/grades.json) · [Grade freeze](receipts/passage-review/run-01/grade-freeze.json) · [Raw execution summary](receipts/passage-review/run-01/execution-summary.json)

## Disposition and next repair

Keep `--grounded-passages` **opt-in**. This increment removes model-authored citation text and an independently guessed overall verdict. It does **not** qualify automatic documentation updates, repair acceptance, general semantic review or a preferred daily workflow. The 73 unsupported assertions and six duplicate-pair failures remain open product issues.

Two successive output-contract experiments have failed their quality targets. Before another live run, change the task decomposition: have the host choose substantive passages and assign unique assessment slots, keeping headings and source metadata as context. Evaluate whether the model can correctly assess one explicit policy conflict at a time, especially unknown-to-verified promotion. This is the next proposed experiment, not a demonstrated fix. A capable reviewer comparison remains necessary; merely adding more roles with the same weights has not established value.

Total cost per verified repair, human review time and actual repository repair quality remain **unmeasured**. The recorded model tokens and elapsed time are diagnostic costs only. Native Windows/Linux execution and service qualification, broader provider/model comparisons and team-routing qualification remain open.

## Artifact and preservation

The [dev7 wheel](../dist/attune_harness-0.1.0.dev7-py3-none-any.whl) has SHA-256 `482a7c76181c0cc4d21114d889738fe24939cccd328073eee1585f3fe8a1bea9` and rebuilt identically. The dependency-free installed core also passes three CLI checks and imports the new module without optional integrations. Use the new isolated installation described in the [usage guide](passage-review.md).

The final [preservation audit](receipts/passage-review/final-audit.json) checks all 5,173 previously recorded artifacts, the frozen campaign and the installed source/wheel identities. Historical experiments and grades remain intact. The full software suite's 758 passes and targeted 10/10 mutation detections establish implementation behavior; they do not override the failed live quality result.
