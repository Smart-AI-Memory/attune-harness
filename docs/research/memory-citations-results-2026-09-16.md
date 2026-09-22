# Memory citation-contract repair results

Date: 2026-09-16. Status: completed disposable comparison; **carry the repaired
contract forward**. Production memory behavior and the plan/build spec are unchanged.

Continuation: the authorized [bounded worker prototype](memory-worker-results-2026-09-16.md)
now wraps this unchanged contract in durable host routing, sampled review and
stale/duplicate-job controls. It uses saved-response replay and isolated adapter
probes, not a replacement or rerun of this native comparison.

**Result:** Luna completed all eight fresh cases with correct meaning, relevant
citations and host acceptance on its first attempt. The old contract passed only
2/8 initial host checks and needed six Astra citation repairs. Both arms' initial
operations, dispositions and core meanings passed all eight cases. The observed
extra work came from the citation interface, not a demonstrated need for stronger
reasoning on these tasks.

## What changed

The [design](https://github.com/Smart-AI-Memory/attune-harness/blob/312e7af/experiments/memory_citations/DESIGN.md),
[new cases and rubrics](../../experiments/memory_citations/cases.json),
[adapter](../../experiments/memory_citations/citation_contract.py) and
[runner](../../experiments/memory_citations/run_citations.py) were frozen before
native dispatch. Patrick authorized proceeding with the citation repair recommendation.

The repaired model-facing schema requires nonempty reference arrays and limits
their values to supplied source IDs. Instructions distinguish top-level evidence
for the operation, disposition and explanation from each fact's content provenance.
An absent attachment is named in the request or explanation; the supplied note
describing it supplies the citation. Audit instructions refer to the audit's own
verdict, reason and evidence fields.

The host still independently checks unique references, grants, source scope,
operation completeness and current task/record/evidence/grants. It owns versions
and stops on stale state. It does not synthesize citation choices. Source packets
outside this experiment's one-to-eight unique supplied-ID profile fail before
any call. These input limits are a declared prototype boundary, not a new
production restriction.

Each fresh synthetic case ran through both contracts, alternating arm order.
Task bytes, requested profiles and routing policy were identical within each
pair. This compares the combined schema-and-instruction repair; it does not
isolate which part changed model behavior. Each arm used Luna/high and allowed
one Astra/xhigh escalation for invalid output or a reasoning request. Evidence
and owner-decision outcomes stop without an additional reasoning call once valid.

## Outcomes and actual citation support

| Case | Old initial host check | Repaired initial host check | Source-based finding |
|---|---|---|---|
| Capture preference | Rejected; empty decision citations | Accepted | Captures only granted new-7 with P10; no invented rationale |
| Conditional correction | Rejected; empty decision citations | Accepted | Preserves retained-log condition with P22 and mandatory signed-run exception with P21 |
| Distinct project preferences | Rejected; empty decision citations | Accepted | Keeps both exact snapshots; P30/P31 support distinct scope and day conditions |
| Consolidate duplicates | Rejected; empty decision citations | Accepted | Preserves P40/P41 merged provenance and P42 emergency exception |
| Forget all temporary notes | Accepted | Accepted | Empty resulting facts; P52 supports the explicit removal request |
| Classify observation | Rejected; empty decision citations | Accepted | Only note-to-lesson changes; fact stays P60, decision cites P61 |
| Missing finalized attachment | Accepted | Accepted | Requests decision-bundle-m2 and cites supplied P71, without choosing CSV or reaffirming JSON |
| Unmade owner choice | Rejected; empty decision citations | Accepted | Requests Ash/Fir selection with P81 support; no choice on the owner's behalf |

All six old-arm escalations supplied acceptable citations while preserving the
already correct operation, disposition and memory meaning. There were **zero
model-requested reasoning escalations**. All final results passed host and source
grading: 8/8 in each arm. The initial old capture explanation was empty; this is
disclosed separately from an unsupported explanation and was not retroactively
made a failure criterion. No other unsupported explanation was found.

Forgetting and classification demonstrate why top-level references cannot always
be copied from surviving facts. The forgetting result has no facts from which
to derive P52. Classification preserves fact provenance P60 while P61 supports
the kind-change decision. A separate offline check deliberately supplies a known
but irrelevant citation: it passes structural checks, making the continuing need
for semantic review explicit. Valid IDs alone do not prove truth or authority.

The one preselected Astra audit reviewed the **original repaired Luna conditional
update**, supported it and correctly identified the condition and exception using
P22/P21. It did not repeat the routine worker task to repair metadata. There was
no naturally incorrect repaired result in this small set, so this audit does not
measure error-detection probability or establish a production sampling rate.

## Calls, tokens and elapsed process time

| Segment | Calls | Input tokens | Output tokens | Native process seconds |
|---|---:|---:|---:|---:|
| Old workers, including six Astra corrections | 14 | 76,616 | 3,202 | 207.26 |
| Repaired Luna workers | 8 | 39,031 | 1,645 | 94.25 |
| Scheduled repaired-result Astra audit | 1 | 6,434 | 281 | 17.86 |
| **Repaired path including audit** | **9** | **45,465** | **1,926** | **112.11** |
| **Whole campaign** | **23** | **122,081** | **5,128** | **319.37** |

The repaired workers avoided six observed correction calls. Their native process
sum was 94.25 seconds, versus 207.26 for the old workers and corrections; including
the scheduled audit gives 112.11 seconds for the repaired path. Audit assignment
was deliberately unequal and its cost is shown separately. There was no direct
all-Astra worker baseline in this trial.

Reported cached input was 14,592 tokens, all in the old arm; repaired calls
reported none. Reasoning output was 2,946 tokens across the trial. These are
usage subfields, not additions to total input/output. Single observations,
cache differences and native variability prevent an isolated speed estimate.
This is an observed improvement over this faulty interface, not a measured
production workload saving or a comparison against lead-managed work.

Requested profiles were GPT-5.6 Luna/high and GPT-6 Astra/xhigh through Codex CLI
0.153.4 and the existing ChatGPT subscription: 16 Luna calls and seven Astra calls.
The run used 23 of at most 33 calls and remained within the 1,800-second campaign
deadline. Every call returned one agent message and the same three previously
recorded host warnings. There were no native boundary failures or automatic
transport retries. No Voyage/Anthropic requests, new credentials, direct API
charges or live memory effects were part of this experiment.

Durations exclude design, implementation, reviewer work, offline checks and lead
grading. They do not measure first visible output, a displayed decision form,
human response time or full project effort. Subscription tokens are not converted
into dollar savings.

## Verification and recommendation

**157 offline tests passed: 43 new and 114 inherited.** Saved regressions preserve
the eleven original Luna replies: the new schema rejects all ten known
empty/unknown-reference failures without rewriting them, while retaining the
one previously valid reply. Tests cover prompt/schema identity, wrong-but-known
citations, unchanged host restrictions, empty-result forgetting, whole-set source
preflight, stale input, one-hop escalation and audit quarantine. Inherited checks
exercise native failure, deadline and call-cap handling.

The bounded read-only reviewer identified an audit/worker wording mismatch before
freeze. It was corrected, and the lead reran the complete targeted suite centrally.
All 17 new frozen source hashes matched after dispatch. The four preceding
campaigns' frozen sources, protocols, ledgers and **81 raw native receipts** also
matched their saved hashes. Raw native events, prompt hashes, reconstructed
prompts, schema equality and host assessments were rechecked during aggregation.
Grading covered all 16 initial replies, six corrections and one audit; it was
source-based and **unblinded by the lead**, not an independent evaluation.

Carry this repaired contract into the next bounded memory-worker prototype.
Keep Luna as the sorter and routine-worker candidate, with explicit host routing
rules and sampled semantic review. Do not add a stronger router merely to correct
this interface defect. This eight-case feasibility result does not qualify actual
storage concurrency or deletion, installed adapter taxonomies, security
classification, retrieval/context refresh, representative workload performance
or active-lead delegation. Those remain the integration boundary before live use.

Evidence: [frozen protocol](../receipts/memory-citations-2026-09-16/protocol.json),
[ledger](../receipts/memory-citations-2026-09-16/ledger.json),
[lead grades](../receipts/memory-citations-2026-09-16/grades.json),
[aggregation](../receipts/memory-citations-2026-09-16/analysis.json),
[analysis script](../receipts/memory-citations-2026-09-16/analyze.py),
[offline verification](../receipts/memory-citations-2026-09-16/offline-verification.json).
Raw receipts remain local under the existing ignore policy.
