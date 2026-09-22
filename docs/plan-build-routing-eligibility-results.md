# Narrow Luna eligibility — completed pilot

September 18, 2026. **All 32 original calls completed; allocation closed.**
Luna passes 16/16, Sol 15/16, and the frozen routing policy selects 15/16 passing
replies. The policy saves 46.4% versus always selecting Sol, but fails its
predeclared all-selected-replies-pass floor. No production route is qualified.
Tasks 1–7 remain accepted; Task 8 remains open.

## Cost and response speed

Each row below covers the same sixteen case/repetition positions. Always-Luna,
always-Sol and the filter are selections from paired original replies; the filter
was not deployed as a separate journey or a Luna-then-Sol retry cascade.

| Selection | Original passes | Estimated worker credits | Median response seconds | Summed response seconds |
|---|---:|---:|---:|---:|
| Always Luna | 16/16 | 1.744678 | 18.96 | 335.12 |
| Always Sol | 15/16 | 33.626240 | 16.98 | 271.42 |
| Frozen filter: 8 Luna, 8 Sol | 15/16 | 18.032038 | 17.43 | 286.59 |

The filter costs **46.4% less than always Sol**. Compared with always Luna, it
costs **10.3 times as much** and reduces summed response time by **14.5%**
(48.54 seconds across sixteen replies). Its median response is 1.53 seconds
faster. Sol responds faster in 14/16 matched pairs, with a median paired advantage
of 2.89 seconds; among pairs where both pass, Sol is faster in 13/15. These are
descriptive timings from this run, not an established latency guarantee.

Response time includes the malformed Sol reply. It excludes session inspection
and local acceptance work, so it does not measure time to a successful completed
journey. The pre-call Python classifier took a median **0.193 ms** across the
eight frozen cases (range 0.086–0.439 ms); classifier overhead is negligible here.

The actual experiment ran both workers and cost **35.370918 estimated worker
credits** against the approved 120-credit planning ceiling. No retries, credit
purchase/reset or new API dollars were used. Ordinary Astra session grading is
additional and excluded from this worker ledger. These token-based estimates
are not verified account deductions. Actual output and caching differed from
the conservative 50–105-credit preparation estimate. The allocation is closed;
84.629082 credits of unused planning headroom do not transfer to another trial.

## Frozen rule and original outcomes

The classifier selected Luna only for a host-declared isolated, undecorated
synchronous function with at most twelve statement nodes and current required
source/behavior/check bindings. Other supported structures selected Sol;
missing/stale evidence blocked either worker. All routes were frozen before
native responses. The twelve-statement threshold was provisional.

| Case | Selected worker | Luna passes | Sol passes |
|---|---|---:|---:|
| Time window, isolated | Luna | 2/2 | 2/2 |
| Time window, embedded | Sol | 2/2 | 2/2 |
| Explicit false, isolated | Luna | 2/2 | 2/2 |
| Explicit false, embedded | Sol | 2/2 | 2/2 |
| CSV record, isolated | Luna | 2/2 | 2/2 |
| CSV record, embedded | Sol | 2/2 | 2/2 |
| Terminal suffix, isolated | Luna | 2/2 | 2/2 |
| Terminal suffix, embedded | Sol | 2/2 | 1/2 |

The Luna-selected subset passes **8/8**. Luna also passes **all eight attempts
that the filter assigns to Sol**. This sample demonstrates savings relative to
always-Sol, but no observed quality benefit from those Sol selections.

Sol's original `ne11`, the first embedded terminal-suffix attempt, fails the
response contract. Its outer text envelope decodes, but malformed quote/backslash
escaping in the inner full-file proposal prevents JSON parsing. The visible
target edit is not an acceptable original repair: the host rejects the reply
before file effects or tests. Its 1.944760 credits remain counted. The later
predeclared repetition `ne19` passes; it is not a retry or replacement grade.
The original raw reply, rejection and failed disposition are retained unchanged.

All other 31 proposals pass session semantic inspection and eight actual checks
each, for **248 test executions**, including target-interface and unrelated-AST
preservation. Their no-repeat continuation and stale-source controls pass.
Semantic grading was performed by Astra in the active session with model identity
visible; it was neither independent nor blinded. Final review in these local
acceptance replays is scripted, not a new native reviewer qualification.

## Pushback on tightening

Patrick asked whether to tighten the filter. If that means admitting fewer
repairs to Luna, this run does not support it: the only observed failure was
already assigned to Sol, while Luna passed all admitted and excluded attempts.
Further restricting Luna could reduce savings without addressing this failure.
Improving classification is still a reasonable objective; these cases do not
establish the right boundary.

The concrete next recommendation is to diagnose the full-file response-encoding
failure locally before changing thresholds or allocating another native trial.
This is a recommendation, not a recorded approval to change the frozen rule.
Its strongest counter-case: response encoding does not solve the earlier Luna
regressions on larger files. Broader, realistic preservation cases remain
necessary before either a universal Luna route or a tightened rule can be
qualified. The earlier 54-call results remain separate and unchanged.

Patrick subsequently leaned toward Luna and requested pushback. Luna is the
preferred candidate for the small, bounded repair scope demonstrated here: its
cost is about one nineteenth of Sol's, for roughly two seconds slower median
response. This recommendation is scoped to further qualification, not production
adoption or every module. Keeping larger repairs outside that recommendation
leaves potential savings unrealized but respects the earlier preservation failures.

D33's broader follow-up was conditional on a passing pilot. This policy did not
pass, and no automatic larger campaign is triggered. Further paid execution
needs a separately prepared allocation. Native final review and complete native
handoff remain unqualified.

## Evidence and limits

Eight synthetic cases represent four matched behavior families with two repeats,
not sixteen independent real-world tasks. Isolated files are 112–311 bytes and
embedded files 1,185–1,384 bytes; neither reproduces the prior 9.7 KB replacement
burden. Passing the small Luna subset cannot establish “definitely passes.”

All calls requested the frozen model, high reasoning, Standard service, ChatGPT
authentication and a read-only native sandbox. Recorded native events contain
one agent message and a skills-context warning per call, with no tool-execution
events. The warning reports all skill descriptions omitted: 165 additional skills
for two calls and 167 for thirty. Requested turns/source were bound, but ambient
host context was not a wholly controlled experimental variable. Token counts
and caching varied and are retained in the ledger.

Closeout verifies original request/raw/usage/inspection/evaluation chains, the
frozen preparation and installed bindings, and **15,279 earlier receipt hashes**.
Grades were frozen before aggregate policy analysis. No original failure was
repaired or regraded; no product implementation or routing changed in closeout.

- [Approved scope](receipts/plan-build-routing-eligibility-native-2026-09-18/approval-scope.json)
- [Frozen design](specs/plan-build/routing-eligibility-experiment.md)
- [Frozen preparation](plan-build-routing-eligibility-preparation.md)
- [Original ledger](receipts/plan-build-routing-eligibility-native-2026-09-18/ledger.json)
- [Frozen grades](receipts/plan-build-routing-eligibility-native-2026-09-18/grades.json)
- [Aggregate results and per-case costs/timings](receipts/plan-build-routing-eligibility-native-2026-09-18/summary.json)
- [Transport audit](receipts/plan-build-routing-eligibility-native-2026-09-18/transport-audit.json)
- [Original failed disposition](receipts/plan-build-routing-eligibility-native-2026-09-18/calls/ne11/disposition.json)

The preparation and design retain their historical pre-approval language because
they were frozen inputs. D34 and the separate approval receipt document the
subsequent “go”; this report records the completed allocation.
