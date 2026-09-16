# Model-mix answer accuracy experiment — preparation

September 15, 2026. **Content frozen; initial live scope explicitly approved;
calibration stopped with 16/60 final answers. Claude is blocked by provider
billing; Sol by provider capacity. Luna and local Llama stopped on inspection
protocol failures. See the [results](voyage-answer-accuracy-calibration-2026-09-15.md).**

Patrick selected Codex to do the work and **Sonnet, Opus, Sol, and Astra** as the
models to evaluate. The same 50 questions will be answered in two conditions for
each model: 400 final answers. The executor choice does not narrow the model mix.
Patrick subsequently requested **Luna and local Ollama**, and withdrew Spark.
Their append-only calibration adds 20 answers to the original 40; the six-model
full study would have 600 answers and is not automatically authorized by this
calibration. See the [design addendum](design-voyage-answer-accuracy.md#addendum-luna-and-local-ollama).

## Comparison

| Condition | Available evidence and checks |
| --- | --- |
| Ordinary | Selected repository file list, literal searches, and line reads |
| Assisted | Same tools, one fixed Voyage top-five result, and applicable `attune-verify` feedback |

Both conditions get two adaptive inspection rounds (up to three ordinary tools
per round), a draft, and one revision. That is four model invocations per answer,
up to 1,600 across the complete four-model campaign. These are native invocations,
not a guarantee about the clients' internal HTTP request counts.

Report accuracy change, gains, regressions, control abstentions, unsupported
claims, latency, and usage **for each model**. Forty questions have source-backed
answers; ten ask about unavailable capabilities. Do not pool away a model's losses.
This combined treatment cannot attribute a gain separately to Voyage or verify.

## Prepared locally

The experiment directory is
`.pilot/voyage-answer-accuracy-2026-09-15/` (ignored local artifacts).

- `content-freeze.json`: 98 source files, 50 questions, 88 source anchors; source
  hashes still match the earlier accepted generation. Content digest:
  `97ccb16388c386d7cad8a03345ea541af5a8c31d9a8ddfe9c5eab3cdcbda0869`.
- `public/questions.json`: prompts only, with no expected answers or control labels.
- `private/oracle.json`: required facts and exact source spans. Keep private from
  answering runs. Alternative supported answers require a written grading rationale.
- `private/schedule.json`: 400 neutral answer IDs, randomized model order, and
  exactly 25 ordinary-first / 25 assisted-first pairs per model.
- `broker.py`: manifest-limited reads and literal searches with finite call limits.
- `workflow.py`: shared four-invocation answer procedure, with separate verifier
  feedback and draft/final retention.
- `transport.py` and `campaign.py`: client controls, durable dispatch receipts,
  exclusive writer ownership, finite calls, conservative spend reservations, and
  an exact-packet approval gate. `preflight` is the default, with no inference.
- `score.py`: within-model paired arithmetic and descriptive bootstrap intervals;
  missing grades, duplicate grades, and incomplete runs cannot yield a complete score.
- `execution-proposal.json`: proposed exact models/settings and remaining gates.

The source-informed questions concern Harness code. They are not an independent
unseen sample, and these results will not establish application coding success.
Question wording differs from the earlier retrieval benchmark; conceptual overlap
is possible. The answer key was authored before any answering-model inference.

## Runtime qualification and validation

Nineteen offline experiment checks pass. Another 57 existing operations, GitHub
checks, and verification tests pass against the installed environment. These
results validate boundaries and known code behavior; they are **not accuracy scores**.

Local fake-provider probes exercised Codex CLI 0.153.4 and Claude CLI 2.1.266.
Both outgoing fixture requests contained an empty native tool list. The Codex
request specified Astra/xhigh; the Claude request specified Sonnet/high and an
explicit output-token limit. Neither probe made real inference calls. Any token,
latency, or dollar figures inside these fixture responses are synthetic and must
not enter the campaign's measurements.

Codex retained global personal instructions; Claude bare/safe mode did not.
Keep that context constant within each model's pair and disclose the host
difference. The probes establish local request construction, not paid access,
server-authenticated model identity, or live success. Controls are grounded in
the installed clients and [OpenAI's configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

## Proposed model settings and costs

| Model family | Proposed exact ID | Proposed effort | Proposed route |
| --- | --- | --- | --- |
| Sonnet | `claude-sonnet-5` | high | Claude CLI, API billing |
| Opus | `claude-opus-5` | high | Claude CLI, API billing |
| Sol | `gpt-5.6-sol` | high | Codex CLI, subscription quota |
| Astra | `gpt-6-astra` | xhigh | Codex CLI, subscription quota |

The family roster is accepted. These exact IDs/settings are a proposal, not a
claim that they match every model Patrick currently uses. Claude IDs and base
rates are from the [current Anthropic model table](https://platform.claude.com/docs/en/models/overview);
Codex IDs are exposed by the installed desktop model catalog.

Retrieve once per question and reuse identical passages across models. Fifty
query embeddings plus fifty reranks would cost approximately **$0.033** at the
earlier workload's token mix, excluding model generation. This is an estimate,
not an enforced dollar ceiling. No new indexing is planned.

Model cost remains unmeasured. For scale only, at **25,000 total input tokens and
4,000 total output tokens per final answer**, accumulated across all its stages,
100 Sonnet answers would cost $9 and 100 Opus answers $22.50 at current base rates.
Doubling both token amounts doubles their combined $31.50 to $63. These are
arithmetic scenarios, not predictions; they exclude caching adjustments and assume
all billable reasoning output is included in the stated output count.

Codex subscription usage must be reported separately. A read-only account snapshot
during preparation showed 28% of the weekly Codex allowance remaining; that is
shared, changes during other work, and does not predict how much of this campaign
will fit. Orchestration/grading quota is also separate from answering-run receipts.

## Current execution packet

Patrick assigned a shared **$40 Claude API budget for Harness and related work**
and authorized current Sonnet/Opus testing. See [the budget](harness-api-budget.md).
This task-scoped authorization supersedes the earlier date-based freeze for the
current tests. It does not authorize a top-up or unrelated project spending.

The prepared calibration reserves **$15 of that allocation**, uses Codex quota
for Sol/Astra, and allows ten Voyage calls with a separate $1 stop budget. Expected
Voyage charges at the historical query mix are approximately $0.0033 for these five
questions. The source uploads are selected Harness Python/TOML excerpts: candidate
passages to `api.voyageai.com`, and prompts/source observations to the selected
Anthropic/OpenAI answer routes. No answer key or prior grading is included.

`preflight-packet.json` binds exact model/settings, source and execution artifact
hashes, client versions, and the global Codex instruction-file hash. The launch
defaults to no paid execution. Unknown effects stop continuation; a partial answer
is not automatically repeated. Native retry behavior remains client-controlled;
four invocations must not be presented as exactly four HTTP calls. Conservative
reservations and client stop budgets are not an account-level provider billing cap.

Automatic approval review rejected the first launch before creating the process,
requiring explicit approval of this exact batch, allocation, and upload destination.
Patrick then explicitly approved the annotated scope. The initial rejection and
later authorization are both preserved; execution began after that confirmation.
All five Voyage retrievals completed: ten calls, $0.00391509 recorded cost.
The first Claude request was rejected before inference with HTTP 400, insufficient
credit. One minimal diagnostic retry, explicitly requested by Patrick, received
the same rejection. No Claude inference charge is recorded. Sol later received a
provider capacity rejection after four final answers; its failed attempt has no
reported token usage and was not retried. Astra completed all ten answers under
recorded operational amendments preserving the frozen prompts and counters.

The predeclared first five questions (`a002`, `a017`, `a026`, `a037`, `a045`) can
calibrate operational behavior and actual token usage: 40 final answers across
the four models, retained in the final 400. Keep questions, prompts, settings, and
grading fixed afterward; if a material defect requires changing them, stop and
version the experiment rather than silently mixing protocols. Do not select which
models continue based on favorable preliminary accuracy.

The Luna/Ollama extension reuses the completed Voyage evidence and the original
protocol. `extension-packet.json` and `extension-approval.json` bind its pinned
models, separate schedule, artifact hashes, and 80-invocation ceiling. Its ledger
is `extension-live/ledger.json`; this adds no Claude or Voyage allocation and
does not reset the original ledger. Six offline extension boundary checks pass.
The local route is pinned to Ollama 0.31.1, `llama3.1:8b` Q4_K_M, full model
digest recorded in the packet. Luna uses `gpt-5.6-luna` at high effort.

Ollama completed one native request, but returned a prose answer where the first
inspection stage requires JSON actions. The frozen workflow stopped; no final
answer was produced and no correction request was made. The response, 1,213 input
tokens, 44 output tokens, and 10.82-second request time (6.84 seconds loading) are
preserved in `ollama-protocol-failure.json` and its native receipt. Those timings
are not comparable to a complete four-stage answer. An explicit execution
amendment defers Ollama and continues Luna with the same questions and prompts.
The model loaded by the failed local run was unloaded afterward. Luna completed
one paired question after versioned decoder corrections recovered unambiguous
multiple/duplicate messages without repeated inference. Its next question then
returned prose without inspection actions; the unchanged workflow stopped.
All final answers and failures are retained in the result receipt. No full study
or automatic retry is running.

See [the design](design-voyage-answer-accuracy.md) and
[the earlier latency assessment](voyage-latency-assessment-2026-09-15.md).
