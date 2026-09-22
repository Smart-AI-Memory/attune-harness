# Revised memory controls and routing results

Date: 2026-09-16. Status: completed disposable prototype and bounded live trials.
Production memory management and the separate plan/build spec are unchanged.

Subsequent evidence: the [mixed-queue sorter trial](memory-sorter-results-2026-09-16.md)
broadened operation coverage. Luna's core judgments passed all 11 assigned cases,
but an expanded citation contract caused ten repair escalations. The earlier v2
successes do not qualify that expanded interface or establish general savings.

**Result:** all three changes from the [first campaign](memory-routing-results-2026-09-16.md)
are now implemented in a disposable prototype. Four revised Luna memory replies
passed both host checks and source grading. Explicit missing-evidence and
pending-decision outcomes avoided two unnecessary Astra calls. Luna also solved
the fully evidenced calculation case, so this run did not demonstrate a stronger
model rescuing its reasoning.

## What is implemented and what was exercised

| Change | Implementation and offline evidence | Live observation |
|---|---|---|
| Host-owned version binding | Deep-copy the captured record and evidence; compare both with independently supplied current state before acceptance; host advances version only for an update. Tests reject changed versions, same-version content changes and changed evidence, including changes during generation or audit. | Both revised updates received the correct next version without a model version field. No concurrent live-store change was induced. |
| Explicit unchanged-reply policy | Accept either empty facts or an exact full snapshot for `no_change`; reject altered fact text, identity, scope or support references. | Both revised unchanged replies actually returned the exact full preview and were accepted without advancing the version. |
| Distinct unresolved outcomes | `needs_reasoning` can escalate once; `needs_evidence` and `needs_decision` stop with a specific request. Original evidence accompanies escalation. Tests cover one-hop escalation, direct assignment for a known multi-step flag, stale stops and unresolved stronger-model work. | Luna requested the absent attachment and drafted the owner's choice without escalating. It solved the calculation, so native `needs_reasoning` emission and direct assignment from the difficulty flag remain unexercised in this campaign. |

The prototype is [contract_v2.py](../../experiments/memory_routing_v2/contract_v2.py)
and [run_revised.py](../../experiments/memory_routing_v2/run_revised.py).
It produces proposals and synthetic requests, not memory-store writes or an
installed decision-form integration. A production write still needs its own
atomic current-state check at the storage boundary.

## Method and verification

Patrick authorized proceeding after asking whether the earlier recommendations
had actually been implemented. The [design](../../experiments/memory_routing_v2/DESIGN.md)
and [seven cases with rubrics](../../experiments/memory_routing_v2/cases.json)
were frozen before native dispatch. Private expectations and rubrics were not
sent to participants. A bounded read-only review corrected the initial design
so the fully evidenced case actually reached Luna, then reviewed the controller.

Central offline verification passed **58 tests**: 31 new prototype checks and the
27 inherited supervisor/contract checks. This includes negative and concurrent
change cases, malformed proposals, audit quarantine, deadlines, call caps,
native-failure stopping and refusal to rerun a frozen ledger. Schema acceptance
of a deliberately wrong abstention is also tested: the controller cannot prove
the semantic correctness of a model's disposition.

```sh
/Users/patrickroebuck/attune-ai/.venv/bin/python -B -m pytest -q experiments/memory_routing_v2/test_revised.py experiments/memory_routing/test_memory_routing.py
```

Seventeen jobs and one preselected audit completed in **20 native calls**:
14 Luna/high and six Astra/xhigh, using Codex CLI 0.153.4 and the existing ChatGPT
subscription. There were two coarse-policy escalations, no retries and no native
boundary failures. Every call had one agent message and the same three known
host warnings. No Voyage/Anthropic requests, credential changes, direct API
charges or live memory writes were made.

All final replies, initial worker replies, reasons, requests and the audit were
graded against original sources by the lead. This grading is **unblinded and not
independent**. No unsupported claim was found in this sample. Host acceptance,
source meaning, disposition and policy efficiency are recorded separately.

## Memory authoring: revised contract versus legacy

| Luna arm | Correct memory meaning | Host accepted | Worker calls | Input tokens | Output tokens | Worker process seconds |
|---|---:|---:|---:|---:|---:|---:|
| Legacy rewrite | 4/4 | 1/4 | 4 | 16,450 | 457 | 44.73 |
| Revised rewrite | 4/4 | 4/4 | 4 | 17,346 | 630 | 42.47 |

The legacy contract again rejected two correctly worded updates because the
model returned the resulting version instead of the captured version. Its
prompt underspecifies that convention. It also rejected one harmless unchanged
snapshot because it required empty facts. These are interface failures, not
observed failures to understand the memories.

The revised replies preserved the reproducibility condition, compliance
exception, separate East/West scopes and tentative-versus-accepted distinction.
No model version field was needed. Both benign full unchanged previews were
accepted under the explicit policy.

The preselected revised conditional-correction proposal received an Astra audit.
It returned `supported`, consistent with lead source grading. This added **one
call, 6,242 input tokens, 230 output tokens and 14.93 seconds**. Including that
audit, the revised authoring arm used five calls and 57.40 process seconds.
Unsupported/uncertain/malformed audit quarantine was tested offline; this one
supported live proposal does not measure detection of confident mistakes or
establish a sampling rate.

## Routing: distinguish the actual need

| Policy over the same three cases | Correct final outcomes | Calls | Escalations | Input tokens | Output tokens | Process seconds |
|---|---:|---:|---:|---:|---:|---:|
| Direct Astra | 3/3 | 3 | 0 | 19,667 | 1,285 | 65.24 |
| Luna with coarse `needs_review` | 3/3 | 5 | 2 | 26,415 | 1,148 | 65.82 |
| Luna with distinct dispositions | 3/3 | 3 | 0 | 13,523 | 824 | 40.59 |

For the missing attachment, both Luna policies identified the absent evidence.
Only the coarse policy called Astra, which requested the same attachment.
For the unmade owner choice, both recognized that only the owner could choose
Vale or Brook. The coarse policy again called Astra without gaining information.
The revised policy returned the appropriate evidence request or decision draft
directly. Neither task was falsely treated as complete or a reason to rewrite
the prior record.

All three policies correctly computed North 13, South 7 and Staging 10, preserved
the independent aggregate cap of 18, and retained manual approval for production
migrations. They applied the corrected budget and expired temporary exception.
Both Luna attempts completed this case without escalation. A multi-step label
therefore does not establish a need for Astra; the prototype's task flag is a
control demonstration, not a qualified production difficulty classifier.

The two avoided dispatches are directly observed. The timing difference is not
an isolated causal estimate: these are single observations, complete policy
packages and different model/effort profiles. The revised owner-choice call also
reported **1,792 cached input tokens**; the other calls reported none. Do not
attribute all timing or token differences solely to the disposition vocabulary.

## Cost, retained evidence and next boundary

The complete campaign, including the audit and all escalations, used **99,643
input tokens, 4,574 output tokens and 273.77 native-process seconds**. Reported
reasoning tokens were 2,201 and cached input tokens were 1,792; these are separate
usage fields, not additions to the input/output totals. These process durations
exclude design, code review, offline verification and post-run grading. They do
not measure first useful finding, first visible form, human response time,
end-to-end project effort or subscription dollar savings.

All 11 frozen v2 source hashes matched after the run. The earlier seven-source
stage-contract packet and eight-source routing packet also matched; both earlier
protocols, ledgers and all 29 raw native receipts matched their saved analysis
hashes. Earlier failures and replay results were retained.

Carry the revised contract and disposition policy into the next integration
design. Continue evaluating Luna first for routine work, with original evidence
available to a stronger participant and explicit checks beyond self-reported
uncertainty. Do not install a dedicated stronger router based on these results.

Before production qualification, the remaining evidence includes representative
memory operations and frequencies, actual storage concurrency, live handling of
a reasoning escalation, detection of confident errors, retrieval/context refresh,
and an already-active lead comparison. Existing personal, session and classified
memory features remain required; creation, consolidation and forgetting were
not covered here. This supplied-evidence prototype does not establish a Voyage
benefit or qualify the parked plan/build execution spec.

Evidence: [frozen protocol](../receipts/memory-routing-v2-2026-09-16/protocol.json),
[ledger](../receipts/memory-routing-v2-2026-09-16/ledger.json),
[explicit lead grades](../receipts/memory-routing-v2-2026-09-16/grades.json),
[verified aggregation](../receipts/memory-routing-v2-2026-09-16/analysis.json),
[aggregation script](../receipts/memory-routing-v2-2026-09-16/analyze.py).
Raw receipts remain local under the existing ignore policy.
