# Control reliability and time to useful output

Date: 2026-09-16. Status: research synthesis and proposed experiments.
This contributes evidence to the [control audit](../specs/plan-build/control-audit.md).
The plan/build specification remains a scoping draft.

## Recommendation

Build on the existing contracts, failed trials and measurement utilities. First
trace the interval Patrick identified: request to first useful finding or
actionable decision. In parallel, design a shared grammar comparison that tests
meaning and control fidelity across actual consumers. Replace a mechanism when
evidence identifies a weakness, retaining working enforcement and recovery.

Use bounded research agents for independent questions, with the lead responsible
for checking evidence and integrating conclusions. Each investigation should
name its question, prior evidence, deliverable and stopping condition. A standing
research committee is unnecessary for this increment; more model roles have not
consistently produced better results in the existing trials.

### Low-cost support workers remain part of the design

Patrick clarified that the proposed low-cost model for memory management and
other routine work must remain in consideration. The caution about research
committees does not reject specialized support workers. Review-team results do
not establish whether a model can curate memory effectively, and this research
has not demonstrated a better substitute for that role.

**Corrected provider direction, 2026-09-16:** Patrick explicitly wants lower-cost
models from either OpenAI or Anthropic considered for memory and routine support
work. He is shifting more work toward OpenAI. The assistant's preceding inference
that this meant Anthropic-only workers with Fable 5.1 as the starting default was
incorrect and is superseded. Choose by task fidelity, latency and total cost,
including correction and escalation. Neither a provider preference nor an
existing review configuration establishes fitness for memory management.

The existing `participants.fable.json` configures Fable and Opus review roles;
those remain review configuration references, not selected memory workers.
The lead also updated the prior global memory that said to avoid OpenAI so future
recommendations reflect Patrick's current preference.

**Accepted evaluation priority, 2026-09-16:** Patrick agreed with the priorities
and GPT-5.6 Luna as the first candidate for the stated reasons. Evaluate Luna for
memory and routine support work, with Haiku 4.5 as the comparison; GPT-5 nano
remains an optional candidate for narrower tasks. Judge accuracy, latency and
total cost including correction and escalation. The candidate priority is
settled; memory-task quality and an installed routing policy remain unproven.

#### Lower-cost candidates checked September 16, 2026

The following are standard base API prices in USD per million text tokens,
excluding cache/batch discounts, additional tools and long-context premiums.
Luna's displayed base rates apply through 272K input tokens. These are API rates,
not subscription billing or measured cost per successful memory update.

| Candidate | Input | Output | Evaluation role |
|---|---:|---:|---|
| [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna) | $0.20 | $1.20 | Agreed first candidate for routine memory and support work |
| [Claude Haiku 4.5](https://platform.claude.com/docs/en/about-claude/pricing) | $1.00 | $5.00 | Anthropic comparison on the same memory tasks |
| [GPT-5 nano](https://developers.openai.com/api/docs/models/gpt-5-nano) | $0.05 | $0.40 | Cheaper candidate for narrowly bounded extraction or classification |

OpenAI's current guidance recommends Luna for new cost-sensitive workloads;
its older GPT-5 nano remains a lower-priced comparison. These provider statements
justify candidate selection, not a memory-quality conclusion. Fable 5.1's
[$10 input / $50 output base rates](https://platform.claude.com/docs/en/about-claude/pricing)
do not justify naming it the low-cost default. Consider stronger models when
the task or measured correction cost warrants them. The agreed evaluation
priority does not establish completed qualification or an installed routing policy.

#### Existing Luna and Voyage evidence

The [September 15 answer calibration](../voyage-answer-accuracy-calibration-2026-09-15.md)
already includes a requested GPT-5.6 Luna/high route through Codex. Its single
completed question pair was graded correct both ordinarily and with the combined
Voyage/verification treatment. The next question stopped because inspection
returned a premature prose answer instead of the requested actions. This is
partial evidence, not a completed quality comparison, a memory-management test
or proof of faster performance. The grader was the experiment's orchestrator,
not an independent grader.

The lead checked the [partial results](../../.pilot/voyage-answer-accuracy-2026-09-15/usage-and-partial-results.json),
[grades](../../.pilot/voyage-answer-accuracy-2026-09-15/grading/grades.json) and
[failed inspection reply](../../.pilot/voyage-answer-accuracy-2026-09-15/extension-live/2b782af543291bb141ee8645-inspect-2-native.json).
That native receipt also contains host configuration warnings; the failure does
not isolate a model-only cause. Preserve the stopped campaign and its failures.

Harness selects Voyage retrieval separately from the participant model in
`task_runtime.execute_assessment`; participants receive source excerpts and
provenance. Changing the reader from Astra to Luna therefore does not inherently
require replacing the Voyage index or embeddings. For the proposed memory role,
reuse host-managed retrieval and supply bounded evidence to Luna, with explicit
structured contracts for each stage. First qualify response meaning and protocol
completion on separate cases, then compare memory outcomes. Retrieval relevance
alone does not establish that an answer or proposed memory is correct.

Patrick agreed that these questions need more information. The
[follow-up research](luna-voyage-follow-up-2026-09-16.md) records a new offline
analysis: all ten Luna replies meet the outer text-envelope shape, but only five
of six inspections meet the required actions shape. The three host warnings
also occur in shape-valid inspections for both models. It defines separate
comparisons for stage control, retrieval value, evidence interpretation and total
delegation cost, preserving the stopped campaign and distinguishing research
questions from production qualification.

The [bounded native comparison](luna-stage-contract-results-2026-09-16.md) has
now completed eight calls over four synthetic cases. Both contracts passed the
mechanical checks; one proposed memory added an unsupported cost claim and the
other used ambiguous cost wording. Native schema validity did not establish
source fidelity. No Voyage request or memory write was made, and neither contract
is qualified as more reliable by this small sample.

**Memory preservation, 2026-09-16:** Patrick explicitly values the existing memory
features and wants Luna considered for managing them. Preserve curated personal
memory, session recall and structured/classified pattern capabilities. Qualify
the model worker over the existing storage, retrieval and control interfaces;
do not silently replace those capabilities with a simple summary generator.
The worker integration remains proposed.

Proposed division of work:

- A low-cost model extracts candidate memories, organizes and tags evidence,
  identifies possible duplicates or contradictions, and drafts summaries or
  handoffs. Preserve source references and distinguish explicit decisions from
  inferred conclusions. Other routine tasks need their own bounded qualification.
- Deterministic code checks schema, identifiers, links, exact duplicates and
  stale versions, then performs atomic writes within the assigned scope. It
  cannot establish semantic correctness merely by validating structure.
- The lead handles unresolved contradictions, changes in governing meaning and
  synthesis that exceeds the worker's qualified scope. Patrick retains decisions
  that require his judgment. Routine work should not require the lead to repeat
  every step; that would defeat the intended delegation.

The expected advantage over doing all memory work in the lead is less expensive
model work and less foreground interruption. The advantage over code alone is
semantic extraction and organization. Neither advantage is measured yet. Compare
against the existing path using real memory tasks, including corrections,
near-duplicates with meaningful differences, missing sources and retained
exceptions. Measure fact/decision fidelity, harmful omissions or merges, required
correction, foreground wait and total cost including retries and escalation.
Do not choose a model by its name or claim savings before those measurements.
Use existing memory storage and validation interfaces; no new memory platform or
always-running service is required by this proposal.

### Proposed Luna agent with escalation

Patrick proposed a Luna-powered agent that manages routine work and delegates
harder tasks to an agent using a more capable model. This refines the worker
design into an agent with workflow ownership. It remains a proposal for evaluation,
not an installed route or evidence that a larger model will resolve every case.

- Luna performs operations within its qualified scope and tracks completion.
  Routine successful work does not require another full pass by the stronger agent.
- Escalation combines Luna's request with explicit task rules and failed checks.
  Self-reported confidence cannot be the sole trigger: the trial's unsupported
  claim passed structural checks. Evaluate missed escalations as well as excessive
  escalations, with sampled source-fidelity review to expose silent errors.
- The stronger agent receives the goal, original sources and versions, proposed
  change, failed checks and the exact unresolved question. It returns a supported
  result or an unresolved disposition to the owning workflow. A stronger model
  does not gain wider authority or replace the user's decisions.
- Known difficult task classes can route directly to the stronger agent, avoiding
  an obligatory failed Luna attempt. Keep model selection configurable; qualify
  it by operation instead of assuming a model name guarantees competence.
- Bound escalation and retries, preserve the handoff and receipts, and stop
  unresolved work without an agent-to-agent loop. Compare quality, total tokens,
  elapsed time and correction cost with handling the same task directly in the
  stronger model. Neither an extra role nor a cheaper first call proves savings.

For memory, candidate escalation cases include conflicting accepted decisions,
ambiguous replacement of old preferences, meaningful differences between apparent
duplicates and uncertain changes to scope or classification. The exact routing
rules and acceptance cases must be tested; these examples do not establish a new
approval policy. Existing authorization and effect controls continue to apply.

**Accepted safeguards, 2026-09-16:** Patrick explicitly agreed that escalation
must combine explicit task rules and sampled quality checks with model judgment;
known difficult work should route directly to the stronger agent, and routine
successful work should finish without that agent repeating it. Sampling can expose
missed errors but does not guarantee the correctness of every unsampled result.

### Open routing design: active lead and background memory work

Patrick asked whether the stronger agent should route work, potentially according
to the nature of the memories, since it needs their content for its own reasoning.
The lead recommends two operating paths for evaluation:

- When the stronger agent already owns the foreground task and has the relevant
  memory context, let it delegate bounded routine work to Luna within the routing
  policy. Do not add a separate model invocation solely to make that same decision.
- For background maintenance, use host rules over the requested operation, scope,
  known conflicts and evidence availability. Send qualified routine cases to Luna,
  known difficult cases directly to the stronger agent, and unresolved routing
  cases for stronger assessment. Luna can additionally request escalation.

Memory type is one routing signal, not a sufficient difficulty measure. Adding a
tag to a preference and reconciling contradictory preference changes are different
operations on the same kind of memory. Complexity also depends on the meaning and
consequences of the proposed change. Hidden conflicts can escape metadata checks;
source-fidelity evaluation remains necessary for both the router and worker.

Both agents should receive appropriate access to the same source-backed memory
store. The stronger agent needs relevant memory content to do its own work,
regardless of which agent maintains the records; it should not depend solely on
Luna's rewritten summary. Supply applicable standing context plus task-relevant
records and access to their original evidence. A digest is a discovery aid, not
complete evidence. Retrieval ranking does not make source text authoritative or
grant permission. Preserve current trust and scope boundaries.

An updated store does not itself refresh an agent's existing context. Carry source
IDs and versions and refresh relevant changed records at the next appropriate
task boundary. Avoid sending the whole corpus to every invocation or rereading
unchanged records without a task need. Reusing context already present still has
model input/processing cost; measure incremental routing and retrieval work.

Source basis: Harness's `task_runtime.execute_assessment` selects retrieval
separately and supplies `initial_retrieval` to participants. Attune-ai's
`memory.personal` supports scoped/kind-filtered recall and status annotations;
`memory.recall_digest` exposes a bounded digest of curated nodes. These are seams
to evaluate and reuse, not an implemented shared-memory router.

Compare host routing, a stronger-model router on every item, and delegation from
an already-active stronger lead under their actual workloads. Count retrieval,
routing, execution, audits, corrections and escalation, and score missed difficult
cases and unnecessary escalations separately. The proposed two-path design has
not been selected by Patrick or qualified by the eight-call schema experiment.

**Authorized follow-up completed, 2026-09-16:** Patrick directed the next
experiments. The [21-call memory/routing campaign](memory-routing-results-2026-09-16.md)
found correct meaning in all eight authoring replies, but three rewrite replies
were rejected by interface conventions, including an underspecified version field.
Source-selected Luna replies passed all four authoring cases. All three routing
arms reached correct final dispositions on their three cases; dedicated Astra
routing added calls without a final-quality gain in this small sample. Luna safely
recognized the unflagged conflict, and an escalation only reconfirmed missing
evidence. Separate offline replay demonstrated host-owned version binding and
exact unchanged-reply handling on known failures while retaining six negative
controls. The live failures remain recorded. Active-lead routing, sufficiently
evidenced hard tasks and representative workload economics remain unqualified.

**Revised follow-up completed, 2026-09-16:** After Patrick checked whether the
three recommendations had actually been done, he authorized the revised
[contract and disposition experiment](memory-routing-v2-results-2026-09-16.md).
The disposable implementation passed 58 offline checks and completed 20 native
calls, including one counted Astra audit. Revised Luna memory replies passed 4/4
host and source checks; legacy meaning also passed but three replies were
rejected by interface conventions. Distinct missing-evidence and pending-decision
outcomes avoided two unnecessary escalations, completing three routing cases in
three calls versus five for the coarse policy. Luna solved the fully evidenced
calculation, so native reasoning escalation remains unexercised. Timing includes
a disclosed cache difference. Production memory writes, error-detection sampling,
active-lead routing and first-visible-result latency remain unqualified.

**Mixed sorter trial completed, 2026-09-16:** Patrick authorized the proposed
[mixed-queue experiment](memory-sorter-results-2026-09-16.md). Its 114 offline
checks and 32 native calls covered capture, correction, consolidation, distinct
scopes, proposed forgetting, logical kind, chronology and unresolved needs.
Luna's initial operation/disposition/core meaning passed all 11 assigned cases,
but only one initial reply passed host checks: nine omitted required top-level
citation list and one used an absent attachment name there. The schema permitted
values the host rejected. Ten Astra calls repaired metadata, not reasoning.
The current path was slower than direct Astra on all three matched tasks.
Audits explicitly caught three injected semantic errors and accepted the valid
control; these were not natural Luna errors. Revise the citation contract before
claiming efficiency or promoting this prototype. Production remains unchanged.

**Citation repair completed, 2026-09-16:** The separately frozen
[paired follow-up](memory-citations-results-2026-09-16.md) passed 157 offline
checks and completed 23 native calls. Repaired Luna replies passed meaning,
actual citation support and host checks on all eight fresh cases without
escalation; the old contract required six citation repairs. Repaired workers
used 94.25 native process seconds, or 112.11 including the one scheduled audit,
versus 207.26 for the old workers and corrections. Cache and audit differences
are explicit; no production savings or first-visible-output claim is established.
Decision evidence remains distinct from fact provenance, particularly when all
facts are removed or a logical kind changes. Carry the interface repair forward
with host controls intact; production storage and routing integration remain open.

**Bounded worker completed, 2026-09-16:** The next authorized
[proposal-only controller](memory-worker-results-2026-09-16.md) persists host
assignments, sample selection, dispatch intent and outcomes. It passes 211 checks
and replays eight saved Luna replies plus one saved audit without changing the
contract. Known difficult work bypasses Luna; terminal unresolved stronger work
stops without an extra audit. This increment used zero new native calls and
establishes no new quality or latency result. Real temporary file-stash checks
expose adapter constraints without enabling production memory writes.

## Evidence already available

| Evidence | What it establishes | What it does not establish |
|---|---|---|
| [Original communications research](/Users/patrickroebuck/.codex/worktrees/593b/attune-ai/docs/research/agent-harness-communications.md), [parallel execution research](/Users/patrickroebuck/attune-ai/docs/research/parallel-lane-execution.md) | Existing contract, interface and experiment designs to reuse | Their hypotheses are not implementation qualifications; subsequent receipts take precedence |
| [Control audit](../specs/plan-build/control-audit.md) | 31 local authority/effect/recovery cases passed; hook dictionary probes expose coverage limits | Real-host enforcement, model understanding and new build effects remain separate qualifications |
| [E2 replacement](../e2-revision-receipt.md) | Call-bound capability evidence replaced a cache that produced false availability claims | Historical success does not authorize or verify the next operation |
| [E3 trials](../e3-local-research-receipt.md) | Adaptive collaboration matched correctness but added a critical miss against the declared comparison; disposition remains revise | No general advantage for additional roles, current native models or diverse-model collaboration |
| [Task 8 grading](../specs/unified-task-execution/task-8-assistant-grading.md) | Original 48/60 grade remains revise; corrected repair cases were reported separately as 8/8 | Corrected samples do not erase original failures or qualify plan/build |
| [Retrieval timing](../receipts/voyage-next-increment-2026-09-15/latency.json) | Saved-provider session path averaged 3.220 s, including 3.160 s in six generation checks; cached results still incurred five checks | These are recorded local profiles, not live-provider timings or a baseline/candidate improvement claim |
| [Intake timing](../receipts/unified-task-execution/task2-intake-timing-final/summary.json) | Small-fixture median construction/validation was 2.081 ms cold and 1.842 ms warm | Excludes model turns, transport and visible presentation |

The `ask_payload.py` compatibility repair demonstrates concrete semantic defects:
injected recommendations and lost context. Its [isolated handoff](/private/tmp/attune-ask-payload-reliability-20260916/docs/handoffs/codex-fix-ask-payload-reliability.md)
records verification and replacement limits. The implementation benefits
attune-ai directly; shared lessons alone do not make it a shared runtime fix.

## Primary research checked against those findings

Sources were checked on 2026-09-16. These support experiments, not claims that
Attune has already achieved the documented behavior.

- **Interface design affects behavior.** SWE-agent's interface ablations found
  performance differences within its GPT-4 Turbo software-engineering setup.
  This supports comparing instructions, tools and feedback under a fixed task
  contract. It does not identify the training cause of a current model's errors
  or predict a gain for Harness. [SWE-agent paper](https://arxiv.org/html/2405.15793v3)
- **Typed output still needs semantic evaluation.** OpenAI documents that
  structured outputs can contain mistakes and that incompatible input needs an
  explicit response policy. Test insufficient evidence, preserved intent and
  correct disposition independently of schema validity.
  [Structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- **Enforcement location matters.** Claude's documented permission sequence can
  resolve a call before `canUseTool`; it recommends `PreToolUse` for mandatory
  per-call checks. Qualify the installed host/version and actual effects before
  treating either integration as an enforcement boundary. This is not evidence
  that an Attune host was bypassed.
  [SDK permissions](https://code.claude.com/docs/en/agent-sdk/permissions)
- **Remove avoidable sequencing.** OpenAI identifies request count, independent
  parallel work and earlier presentation as latency techniques. Apply them only
  where the measured dependencies permit; required checks must still precede
  the operations they govern.
  [Latency optimization](https://developers.openai.com/api/docs/guides/latency-optimization)

## New local probe: telemetry starts after the reported wait

The inspected Forms `workspace_latency` API explicitly measures render-to-
canonical-acceptance, including human dwell and excluding paint. Its render
duration comes from a supplied event field. Existing
[conformance timing utilities](/Users/patrickroebuck/attune-forms/src/attune_forms/conformance.py)
already name useful presentation phases and should be considered for reuse;
their existence does not establish instrumentation of the full current journey.

Two synthetic event streams differed only in diagnostic request-start time:
one had zero seconds before rendering, the other 30 seconds. Both retained a
2 ms render field and acceptance five seconds after rendering. The installed
Forms 0.17.0 aggregator returned identical results: render p50/p95 2 ms;
acceptance p50/p95 5 s; one matched instance.

This confirms the aggregate's documented scope. It is not a measured 30-second
production delay, a telemetry defect or an explanation of Patrick's actual wait.
`request_started` is an invented diagnostic event, not an existing supported
Forms event. No model, real host or production event store participated.

The [probe](../receipts/control-latency-2026-09-16/probe.py) and
[observed output](../receipts/control-latency-2026-09-16/observed.json) retain the
inputs, installed version, source path/hash and results. Reproduce from the repo:

```sh
/Users/patrickroebuck/attune-ai/.venv/bin/python -B docs/receipts/control-latency-2026-09-16/probe.py
```

## Next experiments, in priority order

1. **Shared latency measurement.** Follow one correlated request through
   inspection, repeated validation, hooks, model turns, assembly and actual
   presentation. Reuse Forms identifiers and measurement utilities where suitable.
   Record first useful finding, decision readiness, completion and human dwell
   separately. Preserve nested spans to avoid double counting. An acknowledgement
   alone is not useful output. Demonstrate both consumer paths before calling
   this a shared implementation. Done when the trace locates the wait and its
   dependencies reproducibly; baseline observation precedes optimization.
2. **Shared grammar fidelity.** Hold meaning and authority constant while
   comparing current guidance with concise examples and typed host tools derived
   from the same contract. Reuse known neutral-confirmation, consequence, partial
   answer, stale revision and insufficient-evidence cases. Include the Task 8
   confusion between a defect and a positive explanation. Use fresh held-out
   material for model evaluation. Measure correct construct, disposition,
   human-answer fidelity, repair turns and unnecessary blocks; do not count
   syntactically valid output as correct. Done when a bounded candidate improves
   the declared outcomes without weakening control behavior.
3. **Harness control qualification and targeted latency changes.** Verify
   required controls at their actual dispatch/effect boundary, including earlier
   permission resolution, unavailable hooks, stale state and uncertain replay.
   Independently compare safe validation reuse, concurrent independent checks
   or earlier qualified findings only where experiment 1 identifies useful work.
   Partial findings must not enable decisions requiring incomplete evidence.
   The existing [Voyage validation-reuse spec](../specs/voyage-validation-reuse/design.md)
   owns that optimization; integrate its evidence rather than duplicate it.

For outcome trials, freeze supported profiles, fixtures, sample sizes, budgets
and acceptance criteria before running the comparison. Use baseline observations
and the product requirement to choose meaningful thresholds; no arbitrary speed
percentage is asserted here. Compare baseline and candidate in separate processes
or checkouts. Retain failures and report escaped effects separately from averages.

The agreed product order applies: shared benefit, Harness benefit, then
attune-ai-only enhancements. A documented Harness release blocker outranks an
optional shared enhancement and must name the release criterion it resolves.
None of these new hypotheses is labeled a release blocker by this brief.

## Research provenance and disposition

Patrick explicitly authorized building on prior research and using agents to
return focused findings for final analysis. Two read-only investigations supplied
this synthesis: `prior_control_research` traced local evidence and raw timing
receipts; `control_research_sources` checked four primary sources against the
control design. The lead checked the source claims, local timing evidence and
telemetry implementation, ran the synthetic scope probe, and owns the resulting
recommendations. A further read-only protocol review identified event-handling
and attribution issues addressed before the eight-call Luna experiment. Agreement
between agents is not independent proof.

Disposition: adopt the bounded research method and carry these proposed
experiments into the owning control/latency design. The bounded Luna native trial
is complete; production instrumentation, worker integration and the plan/build
execution plan have not been implemented by this research increment. The separate
first-journey scope decision remains open.
