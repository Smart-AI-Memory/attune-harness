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

## Unified task execution — September 16 follow-up

Patrick authorized Task 8 and use of newly added credit, then explicitly chose
“Use existing Claude subscription.” The first configured-key attempt returned
HTTP 400 insufficient credit with zero inference tokens and $0 provider-reported
cost. Patrick clarified that Anthropic Claude is funded; the failed request is
not evidence of his account-wide funding state. No alternate key or API retry
was used.

Task 8 then completed 92 native calls plus an announced 16-call correction run
through Claude's existing Max login and Codex's authorized ChatGPT credits.
Claude's API-key override was removed only from the subprocess environment.
The preliminary $15 Task 8 API planning reservation was not used and is released;
the original calibration reservation remains unchanged. Claude's subscription
model-use cost metadata is not a verified API charge and must not be deducted
from the shared $40 as though it were one. Codex credit estimates and subscription
quota remain separate from this API allocation. No top-up purchase was performed.
See the [Task 8 native receipt](specs/unified-task-execution/task-8-live-receipt.md)
for retained failures, corrected outcomes and remaining human grading.

## Bounded assessment comparison — September 17

Patrick approved a fresh eight-case baseline/candidate comparison after an
explicit estimate: **90–150 Codex credits expected, 250-credit planning ceiling**,
existing Claude Max subscription, **zero additional API-dollar allocation**.
Maximum 64 calls: 16 Astra assessments, 16 Fable assessments, 16 Sol grades and
16 Fable grades. The original Task 8 campaign is not repeated. Frozen scope and
current spending evidence live in
[`assessment-quality-2026-09-17`](receipts/assessment-quality-2026-09-17/protocol.json)
and its `ledger.json`. No automatic retry or top-up is authorized. Child calls
remove API-key overrides and explicitly select standard Codex service tier.
This reservation is separate from the shared Claude API budget above; unknown
billed dollars remain unknown. The controller's per-call reservation is not a
provider-enforced ceiling on an individual response or account-wide usage.

Completed at **59 native invocations** (16 Astra, 12 Sol, 31 Fable), including
11 grading calls excluded after an evidence-packet defect. Cumulative token-based
Codex estimate: **107.62386 credits**. A corrected 16-call grading pass covered
all 32 preserved assessments by batching two different cases per call. No
assessment was rerun; original call/model/credit ceilings were retained. Final
account observation still showed 1,957.225698 credits and 38% weekly quota
remaining; this is not proof of a trial-specific charge or no later charge.
The candidate failed the quality floor; no automatic repeat or additional spend
is implied. See [results](assessment-quality-comparison-results.md).

## Assessment correction — allocated September 17

The [bounded correction](assessment-quality-correction.md) and offline rehearsal
made zero provider calls. A fresh comparison is prepared for 24 calls: Astra8,
Sol4, Fable12. Expected Codex use is 45–65 credits (historical median projection
53.1414), planning ceiling 100, existing Claude Max and zero new API dollars.
Patrick approved this additional allocation in the saved
[form reply](receipts/assessment-quality-correction-2026-09-17/approval.json).
The original 59 calls / 107.62386 estimate remain recorded above; the new
allocation does not reset that history. The prepared contract is under
`receipts/assessment-quality-correction-2026-09-17/prepared/`; actual calls and
usage are retained separately under `live/`. Completed: **24 calls**, exactly
the allocated profile counts, **50.94182 estimated Codex credits**. Combined with
the previous assessment experiment: **83 calls / 158.56568 estimated credits**.
The displayed shared balance stayed 1,957.225698; that is not a verified deduction
or proof of no later charge. Both instruction arms scored 8/8 substantively, with
48/48 control judgments passing. No further trial or production adoption is
authorized by this completed allocation.

## Plan/build role comparison — September 18

Patrick approved 24 native invocations: Luna 8, Astra 8, Fable 8, expected
35–75 Codex credits, a 100-credit planning ceiling, existing Claude Max and zero
new API dollars. All 24 completed. The token-based Codex estimate is **59.83688
credits** (Luna 1.12538; Astra 58.71150). Claude's reported $5.01351925 list-price
equivalent is not a verified API charge and is not deducted from the shared API
allocation. Subscription routing was checked; no top-up or new API allocation
was used. Account deductions were not verified.

The native outcome floor failed. The allocation is exhausted and does not permit
another paid comparison. See [results](plan-build-native-results.md) and the
[ledger](receipts/plan-build-native-2026-09-18/ledger.json). This is separate from
the completed assessment allocations above; no earlier budget is reset.

## Subsequent repair-worker screens — September 18

These completed worker screens and the separately authorized filter pilot used
Codex's existing ChatGPT authentication, with **zero new API-dollar allocation**.
They do not draw down the shared Claude API budget. Estimates exclude ordinary
session grading and are not verified account deductions.

| Closed allocation | Completed original calls | Estimated worker credits | Planning ceiling |
|---|---:|---:|---:|
| Luna/Sol/Astra repair screen | 18 | 79.574004 | 150 |
| Expanded Luna/Sol repair screen | 54 | 90.296895 | 200 |
| Separate Python-filter pilot | 8 | 7.158747 | 60 |

All three allocations are closed. The pilot's four conditional follow-ups were
unused; no unused call or credit headroom transfers to another trial. These rows
are specific worker experiments, not a cumulative total for the full plan/build
series, which also includes earlier confirmations and an unresolved startup
attempt. That attempt's unknown usage remains unknown.

The expanded screen and pilot together account for **97.455642 estimated worker
credits** across separate ledgers. Sol passes the expanded floor at 27/27;
Luna passes 23/27. Any next connected trial needs its own prepared allocation.
See the [18-call result](plan-build-repair-model-results.md),
[54-call result](plan-build-repair-contenders-results.md), and
[retained pilot](receipts/plan-build-repair-contenders-native-2026-09-18/side-pilot/results.md).

## Narrow routing eligibility — completed September 18

Patrick requested the next direct-routing experiment with “run.” Its locally
qualified packet proposed **32 calls, 16 each for Luna and Sol; 50–105 estimated
worker credits; 120-credit planning ceiling; zero new API dollars**. The concrete
allocation was pending at preparation. The synthetic transport ledger is explicitly
closed as synthetic and represents zero provider calls or billed usage.
The existing shared Claude API budget and all closed allocations are unchanged.
See [the prepared scope and estimate](plan-build-routing-eligibility-preparation.md).

Patrick subsequently approved the concrete allocation with **“go.”** All 32
original calls completed at **35.370918 estimated worker credits**: Luna
1.744678 and Sol 33.626240. The allocation is closed with zero unused calls,
no retries and zero new API dollars; session grading is excluded and account
deductions are not verified. Original usage is recorded in
[`plan-build-routing-eligibility-native-2026-09-18/ledger.json`](receipts/plan-build-routing-eligibility-native-2026-09-18/ledger.json).
The frozen preparation still describes its pre-approval state. No broader
follow-up, purchase or reset is authorized by this allocation. The unused
84.629082 credits of planning headroom do not transfer. The fixed policy's
18.032038-credit selection is a replay metric, not additional spend: it saves
46.4% against always-Sol but fails the required pass floor. See
[completed results](plan-build-routing-eligibility-results.md).

## Broader Luna validation — approved September 18

Patrick approved “ok” then “go” after the concrete estimate: **40 Luna calls**,
twenty realistic repair cases repeated twice, **10–20 estimated worker credits**
and a **30-credit planning ceiling**. This is a separate new allocation, with
zero new API dollars, no Sol controls, native grader, retries, purchase or reset.
Ordinary Astra session grading is additional and excluded from the worker ledger.
The allocation stopped and closed after 21 calls at **7.043789 estimated worker
credits**, with 19 slots unused and no retries. Twelve original passes and nine
failures remain unchanged. Reference-source leakage in two passing cases makes
the trial invalid for clean qualification; see [results](plan-build-luna-broader-results.md).
The separate function-body replay completed with zero model calls, zero additional
worker credits and zero new API dollars; ordinary session work remains excluded.
The earlier worker allocations remain closed. See the [design](specs/plan-build/luna-broader-experiment.md),
[original estimate](plan-build-luna-broader-cost-proposal.md), and
[current ledger](receipts/plan-build-luna-broader-native-2026-09-18/ledger.json).
