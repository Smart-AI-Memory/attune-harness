# E3 local collaboration research and explicit local-model adapter

2026-09-14. Patrick authorized the optional Phase 5 collaboration research,
followed by Phase 6, and selected evidence/documentation review in attune-harness
as the pilot. Paid-provider and credential authorizations remain separate.

Run the existing 12 candidate diagnostic tasks with four strategies and three
repeats against the installed local Llama 3.1 8B model. This is real inference,
with identical model weights across roles, not native Claude/Codex qualification.
Keep the previous E3 inputs/answer key/protocol immutable; bind a local execution
protocol to those files. Do not tune prompts or routing after seeing outcomes.

Cases: solo returns its draft; cross-review uses one independent reviewer and
lead finalization; fixed roundtable uses three independent reviewers and lead
finalization; adaptive uses zero, one or three reviewers according to the frozen
signals. Reviewers see the task and initial draft, never one another's answers.
The model sees neither family labels, answer keys nor scoring results. Repeated
trials use recorded seeds; separate processes and per-call attempt identifiers
retain complete requests, replies and usage. Failures count as failed trials,
never disappear from the matrix. No automatic generation retries.

Before the implementation, a disposable non-evaluation arithmetic probe passed
using Ollama 0.31.1, model digest
46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e,
temperature 0.2, context 4096, output cap 192. It returned 42 in 4.307 seconds,
24 input tokens and 6 output tokens. Raw receipt: receipts/e3-local/disposable.json.
The initial sandboxed inventory request failed; the approved loopback read found
the local model. No model download, account operation or paid API was used.

Add a dependency-free, explicit local adapter for this qualified path. It contacts
only literal loopback Ollama, disables proxies/redirects, pins server version,
model name and digest, rejects remote/cloud metadata, bounds requests/results,
checks response completion and usage, and returns output without claiming task
correctness. JSON attempts use existing JsonParticipant correlation; an explicit
review peer supports the existing command registry and actually requests its
granted retrieval/verification tools before producing a model narrative. No new
provider SDK, implicit adapter fallback or default selection.

Measure per-trial exact answer correctness, supported findings, false alarms,
critical misses, input/output tokens, API-reported timings and wall time. Report
human interventions during the autonomous run separately from unmeasured human
repair effort. API charges are zero, but local compute cost is not measured:
the original 20% paid-cost target is unassessable, not automatically passed.
Predeclare paired task-cluster bootstrap intervals with family-preserving
resampling, 2,000 replicas and fixed seed; they are exploratory for this small
convenience task set. If adaptive loses correctness or adds critical misses,
revise; otherwise cost/generalization remain inconclusive.

Rejected: more synthetic-only scores (cannot answer the research question), paid
fallbacks during the freeze, downloading a new model unnecessarily, changing
thresholds after results, and averaging away failed trials. The weakest part is
external validity: short diagnostic tasks, one quantized model, one local host,
and no measured human repair. Preserve those limitations in the final result.

Ollama API details were verified against primary documentation:
[generation and structured output](https://docs.ollama.com/api/generate),
[runtime parameters](https://docs.ollama.com/modelfile), and
[usage metrics](https://docs.ollama.com/api/usage).
