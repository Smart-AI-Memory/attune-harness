# Memory authoring and routing experiments

Date: 2026-09-16. Status: completed bounded research, no production routing change.

**Result:** Luna handled four source-selected memory cases correctly. A dedicated
Astra router reached the same final outcomes as the other approaches but added
calls and time in this sample. Contract friction and escalation over missing
evidence also caused avoidable work. These findings do not qualify an autonomous
memory service or establish general model superiority.

## Execution and evidence

Patrick authorized the next experiments. The [design](https://github.com/Smart-AI-Memory/attune-harness/blob/312e7af/experiments/memory_routing/DESIGN.md)
preceded the disposable prototype; cases, schemas, controller and rubric were
frozen before dispatch. Twenty-seven offline tests passed centrally. Two bounded
read-only reviews covered design and code, correcting the distinction between
routing policy and evidence insufficiency and tightening deadline enforcement.

Requested profiles were Luna/high and Astra/xhigh through Codex CLI 0.153.4 and
the existing ChatGPT subscription. Eight authoring trials and nine routing jobs
completed in 21 native calls, below the 26-call bound, with one planned escalation
and no retries. All eight frozen source hashes matched afterward. Earlier frozen
sources and campaign results remain intact. Serving model identity is not
independently attested by the CLI events.

Evidence was synthetic and supplied directly. There were no Voyage/Anthropic
requests, new credentials, direct API charges or live memory writes. All prompts,
schemas, replies, diagnostics, usage and durations were retained.

## A. Source-preserving updates

Four cases tested an explicit correction with an unchanged exception, a tentative
suggestion, unresolved decisions, and separate project preferences. Each ran once
with whole-record rewriting and once with selecting target facts and source
statements. The latter copies exact statements and preserves untouched facts.

| Luna method | Accepted by host | Meaning passed lead review | Calls | Process total |
|---|---:|---:|---:|---:|
| Whole-record rewrite | 1/4 | 4/4 | 4 | 44.13 s |
| Source-selected replacement | 4/4 | 4/4 | 4 | 40.74 s |

The rewrite failures were interface failures, not observed false memory content:

- Two replies returned the resulting version while the host expected the input
  version. **Our prompt did not define that distinction.** Do not attribute this
  to poor memory reasoning.
- One `no_change` reply returned unchanged facts despite an explicit empty-list
  instruction. The host rejected harmless redundancy.

Both methods preserved intended meaning, scopes and exceptions. Host acceptance
is therefore not a semantic accuracy comparison. Source selection has a narrower
expressive scope: new facts, deletion and free paraphrase remain untested. It can
also select the wrong real statement, as an offline case demonstrated.

### Separate offline replay

A post-observation [replay design](../receipts/memory-routing-2026-09-16/replay-design.md)
tested candidate interfaces on the saved rewrite replies. Host-owned base-version
binding made 3/4 admissible. Additionally accepting redundant `no_change` facts
only when exactly equal to the captured facts made 4/4 admissible. Six negative
controls were rejected: stale version, changed content under the same version,
changed no-change text, incomplete facts, changed references and changed scope.

This is an in-memory guard probe on known failures, not a fresh native evaluation,
installed storage test or measured latency gain. The original ledger and grades
were unchanged. [Replay results](../receipts/memory-routing-2026-09-16/replay.json).

## B. Routing and final outcomes

Three new cases ran independently through direct Astra, host rules plus a worker,
and Astra routing plus a worker, with rotated order. Workers used the same
source-selected contract. Routed Luna could escalate once with original evidence
and its retained attempt. Correct unresolved outcomes preserved the record.

| Approach | Correct final dispositions | Calls | Input tokens | Output tokens | Process total |
|---|---:|---:|---:|---:|---:|
| Direct Astra | 3/3 | 3 | 18,366 | 462 | 42.71 s |
| Host rules and bounded escalation | 3/3 | 4 | 20,555 | 543 | 47.39 s |
| Dedicated Astra router, then worker | 3/3 | 6 | 34,350 | 818 | 76.82 s |

| Case | Direct Astra | Host rules | Astra router + worker |
|---|---:|---:|---:|
| Routine replacement | 1 call / 12.72 s | 1 Luna call / 11.16 s | 2 calls / 23.02 s |
| Flagged conflict | 1 call / 13.44 s | 1 Astra call / 13.00 s | 2 calls / 25.13 s |
| Unflagged conflict | 1 call / 16.55 s | Luna + Astra / 23.23 s | 2 calls / 28.66 s |

Astra's router matched the reference routing policy in 3/3 cases. Host rules
assigned the unflagged conflict to Luna, differing from that policy. **Luna still
recognized the conflict and safely abstained.** Astra then confirmed the same
missing chronology. This additional call was required by the experimental policy;
it was not an observed rescue from an incorrect Luna memory.

Neither conflict could be settled from the sources. Stronger reasoning cannot
manufacture the missing authority or chronology. `needs_review` therefore needs
more precise treatment: further reasoning, missing evidence and a user decision
are different needs. Their classification still requires qualification.

The sample deliberately overrepresents conflicts and includes no difficult,
sufficiently evidenced case where stronger reasoning improves the answer. It
cannot establish ordinary workload economics or which tasks truly need Astra.
All grades are unblinded lead assessments, with one run per case and arm.

## Memory access and measurement limits

Both models received original evidence, not only a Luna summary. The escalation
also carried Luna's attempt as untrusted material. A local snapshot probe showed
that changing a shared record does not refresh an existing reader snapshot and
that stale proposals are rejected. This is a version-guard demonstration, not
installed multi-agent synchronization, retrieval qualification or a memory-feature
integration test.

Across both experiments: 106,119 input tokens, 2,829 output tokens, zero cache
reads/writes, and 251.78 seconds of native process time. Reasoning counts are
reported subcounts, not additional output tokens. Every call had one answer and
the same three known host warnings. No unresolved native failure or unexpected
tool event occurred.

Durations include native startup but exclude local orchestration between calls,
preparation, offline tests, research review and post-run grading. They are not
full project costs, first-useful-output timing or subscription dollar savings.
Production sampling audits and their costs remain unmeasured.

An already-active lead was not tested: that needs a real foreground task and
session continuation. A dedicated router call cannot be declared free because
the lead hypothetically has context. Batching and context refresh also remain
workload questions.

## Disposition

Keep Luna first for routine-memory evaluation. Favor the simpler background path
for further tests; dedicated stronger routing showed no final-quality gain here.
Retain the stronger lead's ability to delegate during its own work, which these
experiments neither validate nor reject.

The three changes below were subsequently implemented in a disposable prototype
and exercised in the [v2 live follow-up](memory-routing-v2-results-2026-09-16.md).
That report separates live observations from offline-only control paths;
production integration remains pending:

- The host owns version binding and checks the captured record against current
  state. Copied control metadata should not become a model reasoning task.
- Give benign unchanged replies an explicit policy while continuing to reject
  changed facts, evidence and scope.
- Distinguish reasoning escalation from missing-evidence/user-decision outcomes.
  Preserve evidence checks and sampled review for confident mistakes.

The v2 follow-up adds a fully evidenced calculation task, which Luna solved.
Before selecting production routing, broaden difficult-task coverage, establish
representative operation frequencies and add a real active-lead comparison. Preserve
existing memory features; creation, consolidation, forgetting and classified
storage are outside this narrow trial. No quality threshold or production policy
is ratified by these results.

Evidence: [protocol](../receipts/memory-routing-2026-09-16/protocol.json),
[ledger](../receipts/memory-routing-2026-09-16/ledger.json),
[lead grades](../receipts/memory-routing-2026-09-16/grades.json),
[verified aggregation](../receipts/memory-routing-2026-09-16/analysis.json),
[analysis script](../receipts/memory-routing-2026-09-16/analyze.py).
Raw receipts remain local under the existing ignore policy.
