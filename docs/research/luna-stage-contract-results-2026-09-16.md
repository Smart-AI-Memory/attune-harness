# Luna stage contracts and memory fidelity

Date: 2026-09-16. Status: completed bounded research; memory worker not qualified.

**Finding:** all eight replies passed the response-format and mechanical case
checks. Source review still found an unsupported cost claim in one proposed
memory and ambiguous cost wording in the other. A stricter response schema is
useful for an interface, but this trial does not demonstrate better memory
accuracy or qualify automatic memory curation.

## Frozen experiment

The [design](https://github.com/Smart-AI-Memory/attune-harness/blob/312e7af/experiments/luna_stage_contract/DESIGN.md) compared four new
synthetic tasks, once each under a text-envelope contract and a native contract
for the current stage. Each pair used the same logical prompt, evidence and
Codex profile; arm order alternated. Requested model: `gpt-5.6-luna`, high effort,
through the existing ChatGPT subscription, Codex CLI 0.153.4. The events do not
independently authenticate serving model identity.

The controller made exactly eight serial native dispatches, no automatic retries,
no Voyage/Anthropic requests and no memory writes. It retained all responses,
usage and diagnostic warnings. All seven frozen source hashes still match.
The prior September 15 campaign and its failures remain unchanged.

Before dispatch, 21 offline checks passed, covering the saved premature-answer
failure, malformed actions, wrong decisions, missing usage, ambiguous replies,
unexpected tool activity, unknown native errors and the eight-call limit.

## Outcomes

Grades below are unblinded, source-grounded lead assessments against the frozen
rubric, not independent human grading or a general accuracy estimate.

| Synthetic case | Text envelope | Native stage schema |
|---|---|---|
| Read an unread preference correction before answering | Pass: requests S2 | Pass: requests S2 |
| No available budget evidence | Pass: no reads or invented budget | Pass: no reads or invented budget |
| Update preference while preserving a local-only journal exception | Revise: ambiguous cost qualifier | Fail: unsupported cost comparison |
| Tentative suggestion does not replace an accepted preference | Pass: no change | Pass: no change |

Both proposed updates retained the local-only journal exception and the
similar-quality condition for choosing OpenAI. The stage-schema answer added
“because it costs less,” which none of the supplied sources established.
The text-envelope answer said “choose lower-cost OpenAI”: that can describe
an inexpensive model or introduce an extra relative-cost condition. Preserve
that ambiguity instead of claiming a demonstrated false comparison in both arms.

Both answers also retained the old general Anthropic preference. Whether that
remains applicable outside the newer conditional rule needs clearer temporal
reconciliation; this observation is not a new post-hoc failure criterion.

All field checks passed because decision, required source IDs, action scope and
memory presence were correct. Those checks do not establish that each sentence
is supported. Citations to the right source IDs did not prevent the unsupported
claim. This is a concrete requirement for memory evaluation, not a reason to
route every routine memory operation through another full lead pass.

## Usage and duration

| Arm | Native dispatches | Input tokens | Output tokens | Process total | Mean per call |
|---|---:|---:|---:|---:|---:|
| Text envelope | 4 | 15,374 | 501 | 52.72 s | 13.18 s |
| Native stage schema | 4 | 15,498 | 494 | 41.62 s | 10.40 s |

All eight processes together took 94.34 seconds. Reported reasoning-output
subcounts were 338 and 350 respectively; do not add those to reported output
totals. Cache-read and cache-write counts were zero. This consumed subscription
quota; no API-dollar conversion is asserted. Preparation, offline tests and lead
grading are outside those process totals, so these are not total delegation costs.

Every call contained the same three known warnings about the experimental host
feature, unavailable code mode and exhausted skill-description budget. No
unexpected tool event or unknown native error stopped the run. These observations
do not establish universal isolation. Native dispatch counts do not reveal any
internal HTTP retries by the CLI.

With only one call per case and arm, startup/order effects and task variation
remain uncontrolled. Do not claim a speed improvement, a preferred contract on
quality, or a cause for Patrick's wait before findings/forms. These are complete
process durations, not first-useful-output measurements.

## Implications for memory features

Patrick explicitly asked to retain the memory features and include their
management in Luna's intended role. Preserve the existing capabilities while
qualifying a replaceable model worker over them:

- Curated personal decisions, preferences and topic-based recall, including
  global versus project scope.
- Session findings and lessons, their recall and promotion into curated memory.
- Structured/classified patterns, search, storage, lifecycle and cross-agent use.

These surfaces are documented in the existing memory skills and backed by
attune-ai's [personal memory](/Users/patrickroebuck/attune-ai/src/attune/memory/personal.py),
[session stash](/Users/patrickroebuck/attune-ai/src/attune/memory/session_stash.py)
and [memory handlers](/Users/patrickroebuck/attune-ai/src/attune/mcp/memory_handlers.py).
This was a source inventory, not an installed integration or an end-to-end test
of every feature. The current experiment does not wire a Luna worker into them.

Proposed responsibility: Luna handles relevance, extraction, tags, candidate
updates and possible duplicates/conflicts. Existing host/backend code retains
scope, classification, source records, version checks, write verification and
applicable authorization. Conflicts and unsupported semantic changes escalate;
routine operations need not repeatedly ask Patrick when already authorized.
Replacing the model must not silently drop memory capabilities or equate retrieved
content with permission. Voyage can supply retrieval evidence, but this run made
no Voyage requests and cannot measure its contribution.

## Disposition and next increment

Keep Luna first in the evaluation order, with Haiku as the agreed comparison.
Continue using stage-specific contracts in the prototype for clearer boundaries;
do not promote a worker or claim a schema quality gain from these results.

Next qualify source-preserving memory operations. Start with explicit corrections,
retained exceptions, uncertain claims, duplicate candidates and stale records.
Compare constrained changes to identified facts against rewriting a whole memory;
retain exact source excerpts and supported reasons for each proposed change.
That is a hypothesis to test, not a promise that another field solves fidelity.
Use identical evidence for candidate models first, then separately measure
Voyage retrieval, installed memory operations and total correction/escalation
cost. Freeze new fixtures, grading, profiles and any spend before another trial.

Limits: the missing-evidence and no-change cases explicitly cue their desired
behavior; the live text-arm prompt now includes the logical schema and does not
replicate the historical prompt. This compares complete contracts, including
removal of JSON-in-string escaping. It cannot isolate schema enforcement alone.

Evidence: [protocol](../receipts/luna-stage-contract-2026-09-16/protocol.json),
[ledger](../receipts/luna-stage-contract-2026-09-16/ledger.json),
[per-response grades and usage](../receipts/luna-stage-contract-2026-09-16/analysis.json).
Raw receipts remain local under the repository's existing ignore policy. The
[analysis script](../receipts/luna-stage-contract-2026-09-16/analyze.py) verifies
frozen hashes and recomputes aggregates without provider calls. It records the
lead's judgments explicitly rather than disguising them as deterministic tests.
