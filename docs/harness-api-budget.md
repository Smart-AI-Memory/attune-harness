# Harness Claude API budget

Patrick allocated **$40 total to Harness and related work on September 15, 2026**,
after adding $40 in Claude API credit. This is one shared allocation across tasks,
models, retries, experiments, and related work. Do not reset it for a new task or
treat it as $40 per model. No recurring replenishment was specified.

Patrick explicitly authorized testing Claude Sonnet and Opus now. That current
project authorization supersedes the earlier Anthropic spending freeze for these
tests; it does not lift restrictions for unrelated projects.

## Current reservation

- Initial Voyage answer-accuracy calibration: **$15 Claude API allocation**.
- Remaining unallocated project budget: **$25** before actual spending is settled.
- Sol/Astra/Luna use Codex subscription quota, recorded separately from this Claude
  API allocation. Voyage receipts are also separate provider charges.
- Local Ollama inference has no API charge; local compute costs are not priced.

Actual calibration charges and unresolved dispatches are recorded in
`.pilot/voyage-answer-accuracy-2026-09-15/live/ledger.json` and the individual
`*-native.json` receipts. Read them before reporting remaining funds or starting
another paid project task. Missing usage is unresolved, never zero.

The controller reserves conservatively before each request and stops on unknown
effects or exhausted limits. Its stop budget is not a provider-enforced account
billing cap. No automatic retry or top-up is authorized. Review calibration usage
against the shared $40 before allocating further work; successful calibration
must not silently reset limits.

The first live launch was blocked before the process started. Patrick subsequently
explicitly approved the annotated **40-answer calibration and selected source
uploads to Anthropic, OpenAI, and Voyage**. The approved calibration has started;
consult the live ledger for current spending rather than an earlier zero-cost
checkpoint.

Current billing finding: the configured Anthropic key authenticates, but the
provider rejected both the first calibration request and Patrick's one explicitly
requested minimal retry with HTTP 400, insufficient credit. Both were rejected
before inference; recorded Claude spend remains $0. The configured organization
is `271346eb-a5b2-4840-a703-11a2d68e55e5`; successful authentication does not show
which organization received the reported $40 top-up. Preserve both receipts and
resolve the funding/key organization before another attempt. The diagnostic
retry is in `claude-credit-retry.json` and is outside the accuracy sample.

Patrick's later Luna/Ollama addition uses the same frozen source evidence and
adds no Claude allocation or Voyage calls. Its separate usage ledger is
`extension-live/ledger.json` alongside the original ledger; neither ledger is
a budget reset. The five completed Voyage retrievals cost $0.00391509 separately.

The calibration has stopped with 16/60 planned final answers. Its API allocation
and reservation are unchanged; no automatic restart or full-study expansion is
running. See the [calibration result](voyage-answer-accuracy-calibration-2026-09-15.md)
for billing, capacity, and protocol blockers and the preserved usage receipts.

Approval basis: Patrick said, “I just added $40 to the api of claude,” then
“so you can test claude and sonnet and opus,” and “Use that as a budget for the
harness project and related work.” The initial $15 calibration allocation was
stated before this authorization.
