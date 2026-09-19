# Plan/build Task 8 — comparison ready for allocation

Tasks 1–7 are accepted. Task 8's offline preparation passes **18 checks**, including
the existing preparation regression. Both freshness-guard removals are detected. **No new native or provider calls ran.**
The native comparison is unapproved and Task 8 remains incomplete.

## Concrete comparison

| Case | Requested outcome | Deliberately wrong control |
|---|---|---|
| Planner | Plan opt-in JSONL after the human corrects an earlier verified-only idea. Preserve all findings, notes, default JSON and protected tests. Keep performance unknown. | Retain the exact goal/criteria fields while proposing to discard unknown/refuted findings. This passes structural validation but must fail semantic scoring. |
| Worker | Implement only `json_lines(document)` in the new exporter. Preserve the complete evidence and JSONL representation. | Filter out unknown/refuted findings. The full protected oracle rejects it although its trivial generated pytest test passes. |

The worker is evaluated with the frozen Task 4 CLI implementation as an integration
driver. That CLI is not credited as native model output. The original baseline
source and protected oracle are supplied as evidence; expected implementation
answers are excluded from model prompts. Tests also reject wrong goals, scope,
authority, dependencies, omitted criteria, stale preimages and changed trial
material. An accurately disclosed unknown passes the host contract.

The candidate uses the implemented `feature-planning-v1` and `feature-build-v1`
protocols. The baseline uses concise guidance with identical inputs and host
protections. It is an experimental comparator, not an earlier released version.
All 60 Harness modules match the previously qualified installed wheel.

## Allocation proposal

- **24 native calls:** Luna 8, Astra 8, Fable 8. Two roles × two prompt arms ×
  two repetitions per model; fixed randomized order.
- Exact models: `gpt-5.6-luna`, `gpt-6-astra`, `claude-fable-5-1`.
  Codex reasoning is `high`; one turn, no tools, 300-second timeout per call.
- **Estimated 35–75 Codex credits; 100-credit planning ceiling.** Existing
  Claude Max for Fable; **$0 new API dollars**, no purchases or authentication changes.
- Rates were checked against [OpenAI's current pricing](https://learn.chatgpt.com/docs/pricing)
  on 2026-09-18. Per million input/cached/output tokens: Luna 5/0.5/30 credits;
  Astra 250/25/1,250 credits. Assuming 6,000–10,000 input and 2,000–5,000 output
  tokens per call without caching gives 32.72–71.60 credits, rounded upward for
  planning. These are token assumptions, not measured native usage or account balance.
- Before each call, reconcile reported usage and reserve 10 Astra credits or
  1 Luna credit. Stop if the remaining allocation cannot cover the next reserve.
  The CLI cannot impose a hard per-response credit cap. Standard speed must be
  verified or forced before dispatch; unknown routing/speed stops the trial.
- Failures count toward the 24 calls. No automatic retries, model fallback or
  additional grader calls. Inspect proposed code against the allowed scope before
  executing it in a disposable fixture with a minimal environment.

## Acceptance and measurement

Score schema validity separately from meaning and artifact behavior. Require zero
critical correctness or host-enforcement misses, both candidate repetitions to
pass for a role/model, and no matched baseline-correct/candidate-wrong regression.
Reject invented guarantees, unnecessary material questions and ignored human
corrections. Useful alternatives require grounded reasons; optional advice is
nonblocking and an alternative is not mandatory when no real choice remains.

Blind model/arm labels before semantic scoring and retain source-based rationales.
Semantic grades come from this session's assistant, disclosed as such; this is
not independent model review. Unresolved judgments remain unknown. XML authoring
is selected by the host and is not credited as model authoring-tier competence.

Measure dispatch-to-validated-useful-output, full completion, reported tokens and
all calls. Wrong but valid-shaped output is not counted as useful. Presentation
timing remains separate and unknown until measured; human response time is
excluded. Local preparation took 63 ms, which measures none of those native or
desktop outcomes.

This screen can identify promising planner/worker profiles and protocol defects.
It cannot establish native critic/reviewer quality, an autonomous complete journey
or production reliability. Those outcome gaps remain within Task 8. Successful
screening warrants the next bounded connected trial; it does not itself accept
Task 8, activate live features or authorize release.

## Decision — durable fallback

**Approve this 24-call comparison?**

**A — Run the bounded comparison (Recommended).** Approve the exact allocation
above, then evaluate the results before proposing any further native work.

**B — Hold native calls.** Keep the locally qualified implementation and frozen
preparation available for later work.

Recommendation: run A to test the actual planning/building outcomes now that the
local integration is qualified. The strongest counter-case is that two narrow
cases and two repetitions cannot demonstrate production reliability.

This decision is required because Patrick explicitly retained the separate
paid-trial boundary while enabling non-high task auto-run. Preparation is complete;
no additional implementation approval is being requested.

The exact protocol, four prompt packets, source identities, fixture and test receipt
are retained under `docs/receipts/plan-build-task8-2026-09-18/`.
