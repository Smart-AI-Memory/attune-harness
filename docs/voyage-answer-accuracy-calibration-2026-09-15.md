# Voyage answer-accuracy calibration: results and operational limits

Started September 15, 2026; stopped September 15 at 10:03 p.m. Eastern.
**Partial result: 16 of 60 planned final answers. Only Astra completed all five
question pairs. This does not establish a general accuracy improvement.**

Patrick approved the initial 40-answer calibration and selected source uploads,
then added Luna and local Ollama and withdrew Spark. The original source snapshot,
50 questions, answer key, and original schedule were preserved. The calibration
uses four answerable questions and one unavailable-capability control, with two
conditions: ordinary repository tools; those same tools plus Voyage evidence and
applicable `attune-verify` feedback. Each final answer requires four native model
invocations: two inspection rounds, a draft, and a revision.

## Model coverage

| Requested model / setting | Final answers | Result |
| --- | ---: | --- |
| Astra: `gpt-6-astra`, xhigh | 10/10 | Complete calibration |
| Sol: `gpt-5.6-sol`, high | 4/10 | Provider capacity rejection on the next question; no automatic retry |
| Luna: `gpt-5.6-luna`, high | 2/10 | Next question stopped when inspection returned prose without actions |
| Ollama: `llama3.1:8b`, Q4_K_M | 0/10 | First inspection returned prose without actions |
| Opus: `claude-opus-5`, high | 0/10 | First request rejected for insufficient organization credit |
| Sonnet: `claude-sonnet-5`, high | 0/10 | Shared account billing block; separate minimal retry also rejected |

Ollama 0.31.1 used the installed model digest beginning `46e0c10c039e`, a 131,072
token context, 4,096 output-token cap, temperature 0, and seed 20260915 on this
64 GiB Mac. No model download occurred. Codex model names/settings identify the
requested route; the CLI receipts do not authenticate server-side model identity.

## Accuracy

| Astra outcome | Ordinary | Voyage + verify |
| --- | ---: | ---: |
| Answerable questions correct | 4/4 | 4/4 |
| Correct unavailable-capability response | 1/1 | 1/1 |
| Paired gains / regressions | — | 0 / 0 |

The two completed Sol question pairs contained one improvement: ordinary answers
were correct on 1/2, assisted answers on 2/2. The incorrect ordinary answer claimed
that a dictionary result reaches verification and is retained; the source and a
direct execution probe show rejection before verification, with `output=None`.
This is an observed case-level gain, not a completed Sol accuracy result.

Luna's one completed question pair was correct in both conditions. Its later
premature inspection response and Ollama's response are protocol failures, not
final answers. They are not silently omitted from the coverage table or treated
as evidence about final-answer accuracy.

All 16 final answers received source-grounded grades with model/condition labels
withheld as far as possible. The grader was the same Codex orchestrator that
authored the questions; it was not independent, and style/execution order can
reveal labels. The sample is small, source-informed, and specific to Harness.

## Latency

Seconds per complete four-stage Astra answer, five observations per condition:

| Measurement | Median | Mean | Range |
| --- | ---: | ---: | ---: |
| Ordinary workflow, observed | 84.90 | 89.17 | 74.28–105.90 |
| Assisted answer workflow, observed after retrieval | 87.87 | 94.61 | 77.52–123.42 |
| Assisted including retrieval, reconstructed | **90.87** | **98.67** | **80.48–126.40** |

The difference between condition medians is approximately **6.0 seconds (+7%)**.
The median of the five paired differences is **6.21 seconds**; the mean paired
difference is **9.50 seconds**. These are descriptive calibration observations,
not a stable production latency estimate or a p95 measurement.

Retrieval was performed once per question and reused across models. The total
assisted estimate adds each question's measured retrieval time to its answer
workflow; it was not measured as one uninterrupted uncached request.

| Component | Median | Range |
| --- | ---: | ---: |
| Complete Voyage retrieval, five queries | 3.001 s | 2.963–8.308 s |
| Embedding provider stage | 0.245 s | 0.208–0.289 s |
| Reranking provider stage | 0.369 s | 0.344–0.376 s |
| Local verification, eight completed assisted answers | 0.036 s | 0.028–0.054 s |

Most retrieval time was outside the two provider stages. Full-answer timings
include native client startup, repeated prompts, source inspection, drafting,
revision, and local checks. They are not time to first token or single-model-call
latency. Astra's assisted answers used 270,208 reported input tokens versus
206,832 ordinarily, about 31% more, across the five answers in each condition.

Luna's single completed pair took 79.70 seconds ordinarily and approximately
80.77 seconds assisted including retrieval. The assisted measurement reconstructs
one interrupted workflow from saved native stage times plus continuation time,
excluding adapter repair delay. One pair cannot establish a latency difference.
Ollama's only request took 10.82 seconds, including 6.84 seconds loading; it did
not complete the answer workflow and cannot be compared with these totals.

## What verification actually established

Across eight assisted drafts, `attune-verify` extracted **45 claims: 45 unknown,
0 verified, 0 refuted**. They comprised **28 source links** with fragments such as
`#L98-L106` and **17 numeric claims**. The checker reported that file existence
does not verify a heading fragment, and that numeric claims had no unambiguous
declared count source. An unknown result is neither a detected error nor proof
of correctness.

This calibration therefore did **not** demonstrate added verification value.
The combined treatment also cannot isolate Voyage's contribution from feedback
and revision. Retain the division of work: Voyage supplies candidate evidence;
`attune-verify` checks supported generated-content claims; behavioral tests establish
code behavior. A follow-up should explicitly measure applicable-check coverage.

## Cost and usage

- Claude: **$0 recorded inference charges** against the shared $40 project
  allocation. The initial $15 calibration reservation does not become a new
  allocation on restart. The configured organization still rejected the requests;
  this is not evidence that the funded account's balance is $40 or $0.
- Voyage: **$0.00391509 at the recorded usage rates**, ten successful provider
  calls, no reindexing or retries. This is usage-valued cost, not an invoice.
  Adding Luna/Ollama reused the same five evidence packets.
- Native invocations: 58 original plus 11 extension attempts. These include the
  failed requests and unfinished workflows. A separate, explicitly requested
  minimal Sonnet billing retry is outside the accuracy sample.
- Codex usage is subscription quota, not a fabricated API-dollar price. The
  shared weekly meter moved from 74% used before launch to 78% afterward; this
  includes orchestration and any other account activity. Sol's capacity rejection
  reported no token usage, so that attempt's quota consumption remains unknown.
- Ollama has no API charge in this local run; electricity and hardware costs were
  not priced. Its model was unloaded after the failed inspection.

| Native route | Attempts | Known input tokens | Known output tokens |
| --- | ---: | ---: | ---: |
| Astra | 40 | 477,040 | 18,829 |
| Sol | 17 | 159,166 | 7,818 |
| Luna | 10 | 105,292 | 4,699 |
| Ollama | 1 | 1,213 | 44 |
| Opus | 1 rejected before inference | 0 | 0 |

Token totals include unfinished workflows. Sol has one additional attempt with
unreported usage. Native invocations do not guarantee the same number of HTTP
requests inside a CLI client.

## Adapter findings and next bounded increment

Luna exposed two decoder assumptions: multiple messages can contain one usable
inspection response, and messages can be identical duplicates. Versioned decoder
corrections selected only unambiguous actions, counted every message's output,
and rejected conflicting choices. Saved outputs replayed equivalently; completed
stages resumed only with identical prompts and receipt hashes. No model call was
repeated. Raw replies and each execution amendment remain preserved.

Luna then returned prose with no actions, which normalization cannot fix. The
next experiment should use **stage-specific structured output schemas** for every
model: an actions object for inspection, and an answer object for drafting and
revision. Qualify that protocol on separate operational fixtures before producing
new scored answers. Do not silently mix the changed protocol with this calibration.
Also resolve the Anthropic funding/key organization and recheck Sol availability.
The 50-question, six-model study is not automatically launched from this result.

Validation: ten targeted behavior tests and a direct dictionary-return probe
passed; six extension-boundary checks and six native-message/replay checks passed.
These checks establish workflow boundaries and relevant code behavior, not model
accuracy beyond the separately recorded grades.

Running `attune-verify` on this report verified its local artifact links. Numeric
claims remained unknown without a declared count source, so the report's strict
overall result is unknown. Its numbers were checked against the experiment
receipts; the link check does not establish their truth.

## Receipts

- [Complete-model summary](../.pilot/voyage-answer-accuracy-2026-09-15/calibration-summary.json)
- [Per-model usage and partial answers](../.pilot/voyage-answer-accuracy-2026-09-15/usage-and-partial-results.json)
- [Final-answer grades](../.pilot/voyage-answer-accuracy-2026-09-15/grading/grades.json)
- [Source-grounded rubric clarification](../.pilot/voyage-answer-accuracy-2026-09-15/grading/rubric-clarifications.md)
- [Original ledger](../.pilot/voyage-answer-accuracy-2026-09-15/live/ledger.json)
- [Extension ledger](../.pilot/voyage-answer-accuracy-2026-09-15/extension-live/ledger.json)
- [Behavior tests](../.pilot/voyage-answer-accuracy-2026-09-15/calibration-behavior-tests.json)
- [Model inventory](../.pilot/voyage-answer-accuracy-2026-09-15/ollama-inventory.json)
- [Decoder design and corrections](../.pilot/voyage-answer-accuracy-2026-09-15/native-message-v2-design.md)
- [Stop status](../.pilot/voyage-answer-accuracy-2026-09-15/calibration-stop.json)
- [Shared budget](harness-api-budget.md)
