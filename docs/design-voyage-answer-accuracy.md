# Final-answer accuracy pilot

Status: Patrick explicitly approved the initial 40-answer calibration and selected
source uploads on September 15, 2026, then added Luna and local Ollama and withdrew
Spark. The expanded roster has six models and 60 calibration answers planned.
Execution stopped with 16 final answers after billing, capacity, and protocol
failures; see the [results](voyage-answer-accuracy-calibration-2026-09-15.md).
The full 600-answer study would be a later, separately bounded stage. Keep Codex
as the experiment executor, separate from the evaluated models.

## Question and scope

Does each evaluated answering model give more correct answers about the accepted
Harness source snapshot when supplied with Voyage evidence and applicable
`attune-verify` feedback? A decrease or no improvement is a valid outcome.
This is a same-repository diagnostic, not an application coding-success claim.

Freeze 50 new scenario questions (40 answerable, 10 unavailable-capability
controls), source-backed required facts, prohibited unsupported conclusions,
grading rules, order, budgets, and source identity before any inference. These
are assistant-authored against familiar code, not an independent unseen sample.
Keep every experiment artifact and expected answer outside the index.

## Two conditions

A: same model with bounded ordinary repository listing, literal search, and
file/range reads. B: the same tools plus one Voyage query using the exact question
and top five passages; its draft also receives deterministic `attune-verify`
feedback. Both get one final revision opportunity with the same instruction to
check their draft. A receives no verifier findings. No semantic verifier judge.

Use the same model/version/settings and cumulative input/output/time limits
within each model's pair. Reuse identical questions and the answer key across
models. Do not compare one model's baseline against another model's treatment,
or assume an Astra result applies to Sonnet, Opus, or Sol. Record the host route,
exact model identifier, reasoning settings, runtime version, and available tools
for every model. "Claude" alone is not a model identifier.
Use two adaptive inspection rounds of at most three ordinary repository tool
calls each, then a draft and one revision: four model invocations per answer.
The local workflow enforces prompt and visible-response byte limits; those are
not hidden-reasoning-token caps. Freeze the paid adapter and quota limits before
live execution. More ordinary tool calls are not granted for reaching a cap.
New query embeddings/reranks are limited to 50 each, with no indexing. Retrieve
once per question and freeze those passages for reuse across evaluated models.
Record retrieval latency separately. Each model's estimated uncached workflow
latency includes that recorded retrieval stage; label this reconstruction rather
than attributing all retrieval delay to whichever model executes first.

Serve only the 98 frozen source files through the tool broker. Neither model
gets arbitrary shell/filesystem access, the real repository path, the oracle,
earlier evaluations, or this conversation. File contents are untrusted evidence.
The local Codex probe exposed no native tools but retained global personal
instructions despite disabling project documents. Hold that host context fixed
within both conditions and disclose it. Claude's bare/safe-mode probe omitted
personal instructions. Thus comparisons across hosts are not controlled estimates
of intrinsic model differences; the primary comparison remains within each model.
The ordinary tools give both conditions direct access to the same selected code
and tests; baseline is not limited to its model's memory or a one-shot BM25 result.

## Cases and local experiments

Positive cases cover core execution, triage/economics, imported checks, source
selection, index/replay, paid-stage handling, host grants, and supported document
verification. Controls request specific capabilities absent from the snapshot.
Acceptance checks cover source anchors, 40/10 balance, distinct prompts, source
freshness, evaluator leakage, scoped tool reads, blinded grading, missing grades,
and paired-score arithmetic. Fixtures will exercise those checks without a model.

The existing evidence shows 75/80 reranked top-five source coverage, not final
answer accuracy; the latency probe shows large repeated-validation overhead.
These observations motivate the experiment but are not its answer scores.

## Scoring and fairness

Grade the final answer, not evidence retrieval. A positive case passes only if
all required facts are correct, citations substantiate material claims, and no
material false claim contradicts the answer. An unavailable control passes with
a scoped absence/insufficient-evidence response and no invented implementation.
Blank answers do not pass. Abstention on answerable questions is incorrect.
Permit source-supported alternatives not anticipated by the key, with a written
rationale applied symmetrically to both arms; do not require exact wording.

Keep the arm key separate from neutral answer IDs and grade against source/tests,
with labels hidden as far as possible. Style may reveal the condition, so call
this label masking, not guaranteed blinding. The source-informed question author
is not an independent grader. Record grader identity and disagreements explicitly.
`attune-verify` is a treatment, not the final-answer judge. Unknown verifier results
are not error detections. Verification findings can be wrong and must be checked.

Primary: paired change in correct-answer rate on the 40 answerable cases, reported
separately for every evaluated model. Do not claim a general improvement from
the pooled average. A usage-weighted aggregate is secondary and requires explicit
weights reflecting Patrick's model use, fixed before scores are revealed.
Report control abstention rate (10), overall rate (50), gains, regressions,
unsupported claims, and ungraded/failed runs separately. A paired bootstrap
interval describes uncertainty for these authored cases; it cannot establish
population accuracy. Incomplete runs cannot be promoted as a completed result.
Record draft/final changes, raw verifier reports, tool traces, wall times, and
provider/model usage. All model stages, retries, and corrections count toward cost.

## Execution boundary and alternatives

Prepare an immutable source snapshot, read-only ordinary-tool broker, public
question packets, private oracle, label-masked grading packet, and model-neutral
local preflight. Pin the selected answering model and runtime, test its bounded
adapter without inference, then freeze an execution supplement and the complete
cost/upload packet before requesting paid authorization. Content can be frozen
while the model matrix is pending; the campaign cannot be marked ready to run.

Adding a model adds 100 final answers (50 questions times two conditions), plus
its bounded search, drafting, and revision requests. It does not require another
Voyage retrieval pass. A staged rollout may evaluate one model first; the frozen
questions must remain unchanged for later models. Do not silently add provider
calls or treat subscription quota as zero cost.

Provider/model operations require a durable dispatch receipt before invocation.
Unknown effects stop the campaign; no automatic retry, provider substitution,
or resetting the budget through a new work directory. Preserve all raw records.

Deferred alternative: a four-condition component study. It answers attribution
but doubles the initial conditions before we know whether the combined workflow
helps. The two-condition pilot is simpler, at the cost of that attribution.
Also reject unrestricted native CLI agents: the existing wrapper explicitly
does not guarantee tool isolation, and could expose oracle files to the model.

## Addendum: Luna and local Ollama

Patrick requested Ollama and Luna during the running calibration. Append their
conditions in a separate frozen schedule; preserve the original four-model
schedule, source snapshot, questions, oracle, prompts, and receipts. This adds
20 calibration answers and at most 80 native invocations: 40 for Luna through
the already qualified Codex route and 40 local Ollama requests. Reuse the five
completed Voyage retrievals. No further Voyage calls or Claude spending occur
in this addition, and it does not replenish any earlier budget.

Read-only probes found Ollama 0.31.1 and one installed generative model:
`llama3.1:8b`, Q4_K_M, digest
`46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`.
The other installed model is an embedding model. This Mac has 64 GiB RAM;
the model advertises a 131,072-token context. Use that full context, a 4,096-token
output cap, temperature 0, seed 20260915, and the same four-stage workflow.
The 80,000-byte prompt ceiling plus output fits this context even at one token
per byte. Keep the model resident for 30 minutes and report actual load duration
separately; the initial request is cold. Luna uses `gpt-5.6-luna`, high effort,
and the existing Codex settings. These settings are held fixed within each pair.

Cases to validate locally before dispatch: only the installed pinned digest may
run; no remote Ollama endpoint or cloud model; no tools passed to Ollama; missing
usage, incomplete generation, context exhaustion, and malformed envelopes fail
closed; every dispatch is recorded before invocation; duplicate invocation and
budget reset are refused. Run under the same live-writer lock after the current
Sol/Astra sequence so local inference cannot distort its host timing.

The addition is a disposable experiment adapter under `.pilot/`, not production
Harness integration. Rejected alternatives: downloading a different Ollama model
would add unrequested setup and change what Patrick uses; modifying the running
controller would invalidate the original execution receipt. Host differences,
local quantization, model loading, and subscription usage must accompany any
cross-model comparison. Ollama input/output counts and load/inference durations
come from its [local generate API](https://docs.ollama.com/api/generate).
