# Phase 5 local evaluation receipt

**Latest continuation:** [144 real local-model trials](e3-local-research-receipt.md)
are complete. E3/C16 are **revise**: adaptive matched correctness but added a
critical miss. E1 remains inconclusive beyond local recovery; E2 retains its
original revise and narrowed replacement adoption. Bounded Phase 5 research
decisions are complete; wider native/model/human obligations remain unqualified.

## Earlier preparation receipt

2026-09-14. The bounded local increment is complete. **Phase 5 remains open.**
No provider calls, downloads, credential operations or production source changes
occurred. The [design note](design-phase5-increment.md) preceded implementation.

| Obligation | Evidence and disposition |
|---|---|
| E1 recovery value | Local mechanical precursor passed 48 cells. **Inconclusive** on product value: general task/model and human repair trials remain unrun. |
| E2 capability evidence | Original cache: **revise**. Its call-bound replacement passes the new 24-cell comparison and two post-success fault checks: **adopt the narrowed local contract**. [Revision receipt](e2-revision-receipt.md). |
| E3 adaptive collaboration | Twelve candidate diagnostic tasks and 144 trial envelopes prepared; synthetic scorer validated. **Inconclusive**, real strategy execution and cost/quality comparison unrun. |
| C16 collaboration value | **Inconclusive**. Useful outcomes, accepted findings, false alarms, tokens/cost, elapsed time and human intervention need real comparison on the same tasks. |

## E1: supported local mechanics

Frozen [protocol](../experiments/e1/protocol.json),
[freeze](receipts/phase5/e1-freeze.json),
[final matrix](receipts/phase5/e1-run-03/summary.json), and
[separate audit invocation](receipts/phase5/e1-audit.json).

Four **evidence variants**, three interruption points, two local lead directions,
and two conditions produce 48 cells. These are not four general task types, nor
Claude/Codex transfers. Producers and consumers use separate processes; each
condition starts in its own directory. Both share the initial Harness review
workflow. Baseline transport exercises installed Attune 16.4.0 packet assembly,
caps, write and parse functions. Candidate transport exercises installed Harness
checkpoint, reconciliation, transfer and resume functions. The packet receives
an exported current snapshot after interruption. This does not compare complete
independent workflow products.

| Mechanical result | Attune packet | Harness capsule |
|---|---:|---:|
| Evaluated cells | 24 | 24 |
| Lost accepted constraints | 0 | 0 |
| Duplicate request effects | 0 | 0 |
| False document-verification claims | 0 | 0 |
| Completed review after continuation | Unmeasured | 24 |
| Awaiting operator continuation at trial end | 24 | 0 |
| Explicit recovered-reply reconciliations | Unmeasured | 8 |

The packet remains a valid operator handoff. Its lack of an execution engine is
not scored as a task failure. Capsule completion demonstrates automation, not
lower human effort or better model correctness. The experiment driver supplies
the eight explicit reconciliations; they are not automatic Harness reconciliation
or measured human work.

An independent command appends each request to a local effect ledger and saves
its correlated reply. Prepared and saved-result interruptions terminate the
producer with `os._exit` after an actual durable save. Lost acknowledgements come
from the command writing its effect/reply before exiting unsuccessfully. Resume
and transfer both refuse the uncertain event before explicit reconciliation.
Each capsule trial dispatches two distinct requests, one per lead assignment:
48 total effects. Packet trials retain 16 pre-interruption effects and execute
no continuation. Different totals reflect different progress, not duplicates.

The post-continuation oracle checks request correlation, unique ledger entries,
checkpoint digests, accepted submissions, source snapshots, original evidence,
transferred artifacts and expected supported verification outcomes. A separate
audit process recomputes all 48 results and verifies matrix completeness, archived
experiment-source hashes, installed Harness source hashes and baseline packet
identity. This is reproducibility evidence, not authenticated provenance.

The handoff facade's Git verification and optional memory linkage were not invoked.
Packet frontmatter declares experiment assertions. Model semantics, actual host
transfer, authentication, arbitrary effect reconciliation, general code changes
and human repair timing remain unmeasured.

Execution history is retained: run-01 stopped on an evaluator mistake addressing
`accepted.answers` instead of `accepted.submission.answers`. No product defect or
criterion change resulted. Run-02 completed all 48 cases. Run-03 repeated the
matrix after strengthening the audit with checkpoint/source/correlation checks
and archived source copies. Run-03 is the final receipt. Evaluator regression
tests corrupt private copies of run-02 evidence to test rejection of misleading data.

## E3: campaign preparation only

The [protocol](../experiments/e3/protocol.json),
[candidate task inputs](../experiments/e3/tasks.json) and separate
[answer key](../experiments/e3/answer-key.json) were frozen before validation.
[The freeze](receipts/phase5/e3-freeze.json) binds exact bytes.
Three tasks per family cover clean changes, planted defects, citation disagreements
and interrupted work. These small structured diagnostic reviews do not yet
represent repository-scale implementation work. No strategy was tuned on them.
Future tuning must use a recorded, separate set.

Solo, fixed cross-review, fixed roundtable and adaptive protocols each have three
repeats per task. [The prepared plan](receipts/phase5/e3-validation-02/plan.json)
contains 144 envelopes in stable shuffled order, with task revisions and without
answer-key outputs. The tested adaptive routing function selects zero, one or
three reviewers from explicit uncertainty/risk/disagreement signals. A real
multi-model executor and its host qualification remain outstanding.

[Synthetic validation](receipts/phase5/e3-validation-02/synthetic-score.json)
includes one invented finding and one critical miss per strategy. The scorer
reports 34/36 exact answers, one false alarm and one critical miss per strategy.
These are deliberately generated test inputs, **not model results**. Zero
token/cost/time values are synthetic and establish no savings. Real campaign
claims are explicitly refused by this preparation-only scorer.

The validator rejects duplicate/missing/unknown trials, mismatched revisions,
malformed findings, invalid verdicts, nonfinite/negative costs and timings,
unmeasured repair data and noninteger token counts. Naming a critical risk while
declaring readiness still counts as a miss. Per-task scores retain correctness,
supported findings, false alarms, critical misses, tokens, cost, latency and
repair inputs. Synthetic data can only yield **inconclusive**. Validation-01
precedes the added false-positive/token-count checks; validation-02 is final.

Before actual trials: select exact model versions/settings, qualify the executor,
freeze a priced campaign and obtain explicit spend authorization. The current
API freeze does not authorize resumption on its end date. Run real held-out
comparisons with independent outcomes and task-cluster uncertainty analysis
before applying the proposed 20% cost target. No adaptive production policy was adopted.

## Reproduction and validation

From the Harness root, use fresh output directories; experiment runners refuse
existing directories:

```sh
python3 experiments/e1/evaluate.py \
  --python /Users/patrickroebuck/attune-harness/.venv-mcp2-probe/bin/python \
  --baseline-python /Users/patrickroebuck/.pyenv/versions/3.10.11/bin/python3 \
  --output /private/tmp/harness-e1-reproduction
python3 experiments/e1/evaluate.py --audit-only \
  --output docs/receipts/phase5/e1-run-03
python3 experiments/e3/campaign.py validate-synthetic \
  --output /private/tmp/harness-e3-validation
.venv-mcp2-probe/bin/python -m pytest tests/test_phase5_experiments.py -q
.venv-mcp2-probe/bin/python -m pytest -q --cov=attune_harness \
  --cov-report=json:docs/receipts/phase5/coverage.json
```

The full suite passed **479 tests** at **94.50% production statement coverage**;
**34** new evaluator checks passed. The suite includes local loopback A2A fixtures.
Final outputs are recorded in
[suite output](receipts/phase5/suite.txt) and
[evaluator output](receipts/phase5/evaluator-tests.txt). New tests cover new
experiment modules; the mutation fraction for changed existing production code
does not apply.

[Artifact verification](receipts/phase5/artifact-check.json) confirms all 19
production Python files still equal the qualified wheel. SHA256:
`c07d974a0eb4da5d9a90111d9148654a3967e251367bf6ac072dc7703799b27c`.
The prior 110 installed checks belong to that unchanged wheel's protocol receipt;
they were not rerun here. E1 adds actual installed-package boundary execution.
Broader Phase 4 qualification, prior live-model obligations and Phase 6 remain open.
