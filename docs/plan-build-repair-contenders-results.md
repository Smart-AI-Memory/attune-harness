# Expanded Luna/Sol repair comparison — September 18, 2026

**Sol passes 27/27; Luna passes 23/27. Use Sol for the next complete-journey
qualification.** Only Sol meets the frozen 27/27 worker-candidate floor. Keep
Luna under consideration for narrower routine work; neither this result nor the
separate pilot qualifies a production router. Tasks 1–7 remain accepted and
Task 8 remains open.

Patrick approved the prepared allocation with “run.” All **54 original calls**
completed, with no retries, edited responses or unused slots. The allocation is
closed at **90.296895 estimated worker credits** against its separate 200-credit
planning ceiling and **$0 new API dollars**. Ordinary session Astra grading
usage is excluded. Token-based estimates are not verified account deductions.
All **13,678 earlier receipt files** retain their captured hashes.

| Requested worker | Original repairs | Estimated worker credits | Credits per successful repair, failures included | Median native time | Mean native time |
|---|---:|---:|---:|---:|---:|
| Luna 5.6 | 23/27 | 4.414375 | 0.191929 | 33.6 s | 48.1 s |
| Sol 5.6 | 27/27 | 85.882520 | 3.180834 | 32.3 s | 40.8 s |

Sol is faster in **18/27 matched case/repetition pairs**, Luna in nine. The
median paired difference favors Sol by 2.37 seconds. Total native time is
1,102.9 seconds for Sol and 1,298.4 for Luna. This supports a modest observed
latency advantage here, with a substantial cost premium. It does not establish
a general speed ranking or the economics of a failed-Luna-then-Sol cascade.

## Original outcomes and preservation

| Case | Stratum | Luna | Sol | Luna native seconds, repetitions 1–3 | Sol native seconds, repetitions 1–3 |
|---|---|---:|---:|---|---|
| Nested status assertion | Retained anchor | 3/3 | 3/3 | 36.3, 32.4, 36.1 | 32.3, 37.8, 36.1 |
| Finding filtering | Retained anchor | 3/3 | 3/3 | 18.8, 20.6, 20.2 | 16.5, 16.1, 16.0 |
| Default format | Retained anchor | 1/3 | 3/3 | 103.0, 65.2, 158.3 | 64.2, 73.1, 73.4 |
| Finding envelope | New single defect | 3/3 | 3/3 | 20.1, 20.1, 16.3 | 15.8, 22.5, 17.4 |
| Empty output | New single defect | 3/3 | 3/3 | 18.4, 20.0, 19.6 | 16.9, 18.5, 16.4 |
| Status precedence | New single defect | 2/3 | 3/3 | 64.7, 78.1, 66.6 | 89.1, 92.5, 67.5 |
| Header data loss | New paired defect | 3/3 | 3/3 | 19.5, 20.2, 20.4 | 15.8, 16.1, 15.3 |
| Default and punctuation | New paired defect | 2/3 | 3/3 | 76.0, 100.7, 123.2 | 77.9, 84.1, 66.6 |
| Two test assertions | New paired defect | 3/3 | 3/3 | 34.4, 33.6, 55.5 | 36.3, 31.2, 37.5 |

Luna passes 7/9 retained-anchor attempts and 16/18 new-case attempts; Sol passes
9/9 and 18/18. These are nine selected related cases, each repeated three times,
not 54 independent tasks. The earlier 18-call screen remains historical and is
not pooled with this trial. Repetition reveals variability without qualifying a
population reliability rate.

The four original Luna failures remain failed:

| Call | Original defect | Evidence and disposition |
|---|---|---|
| `ls04` | Fixes the default but removes the async prefix from unrelated static signatures | All eight tests pass; semantic preservation fails. A separate synthetic diagnostic confirms the changed signature. Local build completion alone is insufficient. |
| `ls19` | Malformed response with invalid property encoding and placeholder file content | Known response and usage; parser rejects it. No file effects, test execution or repaired retry. |
| `ls29` | Fixes status precedence but changes dashes into literal escape text | Four supplemental tests pass; one of four protected tests fails. Completion is refused. |
| `ls41` | Fixes the default but corrupts Python quote delimiters and other escapes | Strict response envelope passes, but the supplemental runner stops at import with SyntaxError. No test runs; protected execution is not reached. Completion is refused. |

Fifty-three responses pass the strict host response contract and enter the
isolated local evaluation. Fifty-two reach all eight tests; 51 pass them all.
There are **416 actual test executions**, repeatedly exercising the same small
suites rather than 416 distinct tests. Fifty replies satisfy every acceptance
criterion. Fifty-one local completions pass no-repeat and stale-source rejection,
including `ls04`, whose independent semantic grade is still failed. Both failed
local builds reject incomplete completion. Protected and unrelated files remain
unchanged in all 53 evaluated proposals.

Every proposal was inspected before execution. Equivalent variable names and
literal Unicode versus equivalent escapes remain accepted; optional style advice
does not become a functional defect. The fixed tests and case inputs were not
expanded after observing a failure. The async diagnostic supports the original
preservation requirement; it does not repair or regrade the original response.
Opportunity O-35 records later test coverage work.

## Timing, cost and method limits

The first complete validated response arrived in **19.51 seconds**; its first
test-backed disposition arrived in **63.27 seconds**. Native times span
15.25–158.33 seconds. Local evaluation averages 1.22 seconds for Luna and 1.26 for
Sol. Dispatch-to-disposition also includes assistant inspection, tool scheduling
and context transitions: `ls20` includes about 130.9 seconds beyond native time.
That delay must not be attributed to Sol. First-token, desktop-rendering and
human-attention latency were not measured.

| Requested worker | Input tokens | Cached input subset | Output tokens |
|---|---:|---:|---:|
| Luna | 711,329 | 183,040 | 56,047 |
| Sol | 753,592 | 138,752 | 46,022 |

All 54 calls return usage. The existing meter uses the Standard rates frozen
before approval, including observed cache savings. Luna's failed calls cost
1.072599 credits and remain included in every model cost/time total. Unknown
provider dollar fields stay unknown; they are not treated as zero. Shared account
balance snapshots are not debit measurements, and no reset credit was consumed
by this campaign.

Models were requested with the same case turns, high reasoning and Standard
service, using ChatGPT authentication and an inner read-only sandbox. Streams
contain one agent-message item each and no tool-execution items. All contain the
known nonfatal skills-context warning: seven omit 165 additional skills and 47
omit 167. Thus complete host startup context was not identical or fully isolated.
Backend model names are not reported in the streams; names above are the actual
requested dispatch models. The side pilot ran concurrently on the shared account,
and cache usage varied, limiting causal latency claims.

Original grades were frozen before the final aggregate recommendation. Astra
graded in this active session, with model identity visible: this is neither
independent nor strictly blinded review. The installed Spec/build/test owner and
effect journal are real; the final reviewer in each local replay is scripted.
**Native final review and a completed native connected journey remain
unqualified.** Product code, live memory stores and unrelated work were not changed.

## Integrating the separate Python-filter pilot

Patrick asked that its work inform the recommendation. The pilot's completed
[report and original receipts](receipts/plan-build-repair-contenders-native-2026-09-18/side-pilot/results.md)
are retained: **276 files copied with matching hashes**, without dispatching or
regrading anything. Its separate eight calls cost **7.158747 worker credits**;
four optional Sol follow-ups were unused and its allocation is closed. Combined
worker estimates across these two separate allocations total **97.455642 credits**,
excluding ordinary session review. Quality samples and budget headroom are not pooled.

Both models pass all four new short pilot cases, producing identical paired
repairs. Selecting Sol whenever the target imports argparse costs 2.986188
credits versus always-Luna's 0.375167, with 6.735 seconds less summed native time
and no observed quality gain. It misses a delegated CLI parser and flags an
ordinary library's unused import. **Do not promote this crude rule.**

Applying the same rule retrospectively to this completed main screen selects
27/27 passing replies at 41.728516 credits. That is an exploratory selection
from already-run responses, not demonstrated production savings. The rule was
chosen after first-round outcomes; later repetitions reuse the same cases and
are not an independent new-task holdout. CLI role, file size and full-file
preservation surface remain confounded. Its apparent success here and lack of
quality benefit on the new pilot cases are both retained.

The [filter-opportunity handoff](plan-build-routing-filter-opportunities.md)
identifies pre-call evidence checks and two bounded worker-selection hypotheses,
their counterexamples and genuinely new validation cases. It authorizes no
implementation, extra agents or paid experiment. Missing evidence and interface
defects should not be mislabeled as a need for a stronger model.

## Next acceptance boundary

Use Sol as the candidate for a fresh connected repair/retest/resume qualification
with Astra performing native final review through the existing Spec gate. Prepare
the concrete packet and call/cost estimate before any new paid execution. Do not
reuse this closed allocation's unused credit ceiling or the superseded two-call
packet. Keep Luna's bounded-work opportunity, and pursue a better intake feature
only after the current journey is qualified. No production routing, Task 8
acceptance, live activation or release follows from these worker screens.

Evidence: [authorization](receipts/plan-build-repair-contenders-native-2026-09-18/authorization.json),
[frozen protocol](receipts/plan-build-repair-contenders-preparation-2026-09-18/protocol.json),
[original grades](receipts/plan-build-repair-contenders-native-2026-09-18/grades.json),
[grade freeze](receipts/plan-build-repair-contenders-native-2026-09-18/grade-freeze.json),
[summary](receipts/plan-build-repair-contenders-native-2026-09-18/summary.json),
[timing and cost](receipts/plan-build-repair-contenders-native-2026-09-18/timing-and-cost.json),
[transport audit](receipts/plan-build-repair-contenders-native-2026-09-18/transport-audit.json),
[shadow selection](receipts/plan-build-repair-contenders-native-2026-09-18/shadow-routing-analysis.json),
[closed ledger](receipts/plan-build-repair-contenders-native-2026-09-18/ledger.json).

## Interrupted-session closeout

The session usage interruption occurred after all 54 calls and original grades
were saved. On resumption, the read-only
[closeout verifier](receipts/plan-build-repair-contenders-native-2026-09-18/verify-closeout.py)
checked the frozen protocol and installed bindings, original requests/responses,
usage calculations, inspection/evaluation hashes, reported aggregates and the
prior/pilot manifests. [Verification passed](receipts/plan-build-repair-contenders-native-2026-09-18/closeout-verification.json).
No model call, original replay or regrading was needed. The task outline,
decision log, executable plan narrative and budget record now agree with the
completed experiment; Task 8 remains open.
