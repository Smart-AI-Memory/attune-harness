# Luna/Sol repair comparison — prepared September 18, 2026

**Prepared locally: 54 proposed worker calls, paid allocation pending.** Patrick
asked for a larger experiment, limited the competing workers to Luna and Sol,
and assigned grading to Astra. Astra will inspect the work in this active session;
no separate native Astra call is proposed. The prior 18-call result remains intact.

There are **27 calls per candidate: nine cases × three attempts**. Each attempt
uses a fresh model invocation and disposable local owner, with the same frozen
case turn for both candidates. Three randomized rounds keep both candidates
represented throughout. High reasoning, Standard service, one response, no tools
or retries; the host remains responsible for scope, effects and actual execution.

| Case | Required repair | Stratum |
|---|---|---|
| Nested status | Correct the generated assertion's nested access, retaining coverage | Retained guided anchor |
| Finding filtering | Preserve unknown/refuted findings as well as verified findings | Retained anchor |
| Default format | Restore captured default JSON/Markdown; retain explicit JSONL | Retained anchor |
| Empty output | Emit one unknown header and final newline for an empty document | New single defect |
| Status precedence | Preserve refuted status when findings have mixed statuses | New single defect |
| Finding envelope | Restore the complete finding under the required nested field | New single defect |
| Header data loss | Restore both source evidence and advisory reviewer notes | New paired defects |
| Default and punctuation | Restore format selection and captured Markdown punctuation | New paired defects |
| Two test assertions | Correct nested access and empty-record expectation without deleting checks | New paired defects |

All defects are in disposable fixtures. The six new cases use observed symptoms,
requirements and actual failure excerpts; reference patches are not supplied to
workers. New cases still belong to the same documentation feature. This increases
case coverage and repetition, not the number of independent product domains.

## Local qualification

- All nine broken cases reproduce an actual failure in the current installed profile.
- All nine full reference repairs pass four supplemental and four protected tests,
  preserve unrelated/protected files, avoid repeated participant calls and reject
  stale completion after a source edit.
- All six partial repairs of the three paired defects fail actual checks. Fixing
  only one of those defects cannot earn a passing result.
- The existing native transport completes a 54-slot rehearsal with an injected
  process: exactly 27 Luna and 27 Sol invocations, matching turns, explicit
  ChatGPT/Standard selection, read-only native sandbox and empty temporary cwd.
  These are synthetic dispatches, **zero paid calls**.
- The new preparation and rehearsal scripts pass Ruff. Existing host and worker
  controls retain their prior source/installed qualification; no product code changed.

The first preparation attempt exceeded the existing 4 KB intent-context limit
when combining failure logs. New-case excerpts are now bounded to 1,700 bytes per
failing runner; full logs remain in the receipts. The partial attempt is retained.
A local hook blocked dynamic Python execution for a rehearsal attempt; the
completed rehearsal uses an ordinary inspectable script with an injected process.
No host limit was relaxed and no model was dispatched during either correction.

## Decision criteria and measurements

Astra's session review checks every original proposal before execution and
records semantic preservation separately from test outcomes. Neither contender
grades itself. This review is not independently blinded; prior results and model
identity are known. Valid source must pass the existing strict response contract,
exact write scope, all eight checks, preserved assertions/evidence, no-repeat
continuation and stale-source rejection. Optional equivalent rewrites remain
advisory. Unsafe or invalid replies fail without executable effects; ordinary
resolved failures count while independent cases continue.

The conservative next-trial eligibility floor is **27/27**, with no serious
preservation miss. Report the three anchors separately from the six new cases
and retain every case/attempt outcome. If both qualify, retain the lower-cost
candidate provisionally and show any latency advantage with its cost premium.
If neither qualifies, analyze failure classes before preparing more calls.
This floor qualifies a candidate for the next connected trial, not production.

Compare latency within matching cases, with all three attempts visible. Record
native response time, test-backed disposition, local execution, input/cache/output
tokens and cost per successful repair including failures. Assistant inspection,
scheduling and context transitions must not be attributed to a worker's native
latency. A faster overall median alone does not establish a consistent winner.
No fixed production reliability rate follows from repeated, related selected
cases. [NIST's exact-interval guidance](https://itl.nist.gov/div898/handbook/prc/section2/prc241.htm)
and [OpenAI's evaluation guidance](https://openai.com/index/trustworthy-third-party-evaluations-foundations/)
support reporting the sampling and harness limits explicitly.

## Proposed new allocation

**54 worker calls; 90–180 estimated new Codex credits; 200-credit planning ceiling;
$0 new API dollars.** Astra's ordinary session review usage is outside this worker
ledger and is not included in that estimate. No separate paid grader campaign is
being proposed. These estimates are not measured deductions or a hard invoice cap.

| Candidate | Calls | Calculated worker-credit range |
|---|---:|---:|
| Luna 5.6 | 27 | 4.455–9.180 |
| Sol 5.6 | 27 | 85.050–167.400 |
| Total | 54 | 89.505–176.580 |

Assume 24–32k input and 1.5–6k output tokens per call, without cache savings.
Standard credit rates were rechecked on September 18 against the
[official table](https://learn.chatgpt.com/docs/pricing). Scaling the previous
Luna/Sol observations alone gives about 106.56 worker credits; new cases and
context may differ, so the proposal retains wider headroom.

Stop dispatch for unknown usage or dispatch state, authentication ambiguity,
changed bound inputs, host enforcement failure, or exhausted allowance. Do not
retry, add calls adaptively, or stop early merely because results look favorable.
Preserve every original result. No complete native journey, Task 8 acceptance,
production route change, live memory action or release is included.

The prior 150-credit campaign is closed; its remaining headroom is not transferred.
Patrick's C/go instructions authorize this local preparation. The concrete new
spend amount above is the remaining decision. The strongest counter-case to
running it is cost and delay on nine related cases while connected native review
remains unqualified. The benefit is a larger, fixed comparison of the two actual
candidates with both repetition and additional failure coverage.

Evidence: [protocol](receipts/plan-build-repair-contenders-preparation-2026-09-18/protocol.json),
[case qualification](receipts/plan-build-repair-contenders-preparation-2026-09-18/qualification.json),
[transport rehearsal](receipts/plan-build-repair-contenders-preparation-2026-09-18/transport-rehearsal.json),
[durable decision](receipts/plan-build-repair-contenders-preparation-2026-09-18/decision-form.md).
