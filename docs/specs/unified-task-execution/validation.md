# Validation plan — unified task execution

Status: validation plan approved with the revised spec, 2026-09-16. These are future implementation checks, not results. Spec-authoring validation is reported separately; the approved reflection extension has its own acceptance cases and template-authoring receipt.

Task 1 now has an actual [behavior/latency baseline](baseline.md): 54 CLI captures, retained path-bound legacy records, source/library hashes, zero live provider attempts, targeted regression results and a failure-sensitive exit-semantics mutation. Its compatibility suite is `tests/test_task_compatibility.py`; its reproducible runner is `experiments/task_execution/baseline.py`. This does not complete the future slice or provider qualification below.

## Evidence boundaries

Use four distinct receipts: software/behavioral, installed artifact, native-provider/live-fire, and outcome/metric. A passing earlier receipt never substitutes for a later one. Preserve both slice verdicts and the operation-specific qualification matrix even when the overall spec is incomplete.

Current regression foundations include `tests/test_contract.py`, `tests/test_review.py`, `tests/test_review_boundaries.py`, `tests/test_recovery.py`, `tests/test_native_evidence_review.py`, `tests/test_extensions.py`, `tests/test_mcp.py`, `tests/test_voyage_integration.py`, `tests/test_operations.py`, and `tests/test_process.py`. Their names describe candidate coverage, not proof that all new requirements are tested.

## Frozen behavioral cases

| Family | Valid case | Negative or fault case that must be detected |
|---|---|---|
| Intake | Goal and selected inputs become one accepted task | Missing/declined intake, stale form, changed scope, ambiguous legacy/goal arguments dispatch nothing |
| Form and answer reuse | Warm immutable template and valid same-task answers preserve the cold path's meaning | Changed dynamic choices/schema/project/policy miss the cache; mutable values leak across tasks; cached approval or nonce is replayed; deleted/invalid defaults are accepted |
| Response reuse | Same completed assignment resumes without a new call | Reviewer reuses lead output, new trial replays an old judgment, changed inputs reuse stale evidence, or an uncertain effect is retried |
| Solo | One participant receives required evidence and produces an attributed result | Hidden second participant/synthesis call or exhausted budget cannot pass |
| Independent review | Separate attempts and isolated evidence packets | Lead narrative leaks before review; same model used when different-model policy is required |
| Integration | Clean/defective/uncertain cases retain their distinct findings | Contradictory narratives collapsed into a clean verdict; tool verification mistaken for semantic truth |
| Legacy routing | Existing CLI arguments/results and module entry points work | Wrapper bypasses shared engine or changes old record/digest/exit semantics |
| Recovery | Resume after every completed operation replays saved results | Lost acknowledgement, persistence failure, stale/corrupt/future record, copied owner directory, concurrent writer |
| Grants and sources | Same accepted source generation, input bytes, settings and tools | Changed source, removed capability, disabled extension, modified grant or model profile |
| Paid retrieval | Completed stages replay under existing rules | Unknown paid stage retried as read-only or input exclusion applied after upload |
| Repair | Baseline fails; correct scoped replacement passes independent probe | Wrong/no-op patch, changed probe, unauthorized file, symlink/reparse/hard-link escape, traversal, duplicate path |
| Repair recovery | Recognized after-image reconciles without another write | Partial patch or unexpected bytes incorrectly marked clean or overwritten |
| Repair review | Reviewer and probes bind to final artifact | Missing required reviewer, unresolved objection, stale artifact, or changed file after review |
| Deterministic interfaces | Tool/inspection/protocol use without models | Poisoned model constructor invoked by direct verify/retrieve/status/protocol setup |
| Vocabulary | User selects review for assessment, fix for modification | Help advertises an unsupported verb or a review goal changes files |

Task 1 freezes deterministic fixtures, source hashes, expected results, and baseline command captures in a fresh output directory. Task 8 freezes unseen model-evaluation material separately. Do not change fixture expectations to accommodate candidate failures; protocol corrections require a new identified run and retain the earlier failure.

## Execution and installed checks

At implementation start, identify the actual interpreter, optional extras and imported module paths. Use the repository's isolated environments without upgrading frozen campaigns. Run targeted new suites plus the relevant regression families, then the full applicable suite once for each completed implementation slice. Repeated broad runs require a new change or unresolved failure.

Build a wheel into a fresh artifact directory, install it into a fresh environment, and run consumers outside the source tree with isolated import behavior. Compare every installed module hash with the candidate artifact before interpreting results. Exercise actual forms/retrieval/verification libraries and an independent JSON subprocess peer; mocks alone cannot qualify those boundaries. Cross-platform claims require the relevant native runner receipts, not OS simulation.

Mutation work targets specific load-bearing guards: remove revision matching, source checks, reviewer isolation, required-review enforcement, dispatch-intent persistence, scope validation, before-image checks, protected-probe checks, and final artifact rechecks one at a time in disposable copies. Report detected mutations and the number of new selected tests that fail per mutation in the ordinary suite receipt. Green original tests alone do not establish guard sensitivity.

## Intake latency and cache comparison

Task 1 captures the current form build/render/validation and transport timings before adding a cache. Task 2 adds bounded reuse and failure-sensitive cases; Task 5 runs cold/warm/bypassed installed journeys, including separate processes, using the same inputs and presentation. Record sample counts, median and p95 where supported by the sample size, cache/dependency versions, memory/bytes, lookup/freshness overhead, hit/miss reasons, calls/questions avoided, and time to usable form and accepted intake. Keep user think time and provider/network time distinct; do not attribute an end-to-end difference to rendering alone.

Prove warm and cold paths produce equivalent current fields/options and accepted contracts while preserving their own bindings. Mutate each key dependency, remove saved profile selections, corrupt/evict entries and bypass the cache; validation and resulting task meaning must remain unchanged. No model call is permitted merely to fill a routine form cache. Prove one task cannot observe another task's answers or consume its action binding. Accepted unchanged answers within the same task remain usable without repeated confirmation.

Task 8 reports measured latency alongside useful correctness, with matched cache conditions across arms. Independent assignments and new evaluation trials execute separately; completed-operation replays have their own category. No invented savings claim or universal numerical target follows from a cache hit.

## Provider qualification

Matrix columns: adapter/runtime version; requested and observed model identity; settings; lead/worker/reviewer role; assess/repair operation; granted tool/effect profile; deterministic/installed/native receipt; limitations. A provider configured but not exercised stays unqualified. Where the provider does not attest actual model identity, record requested settings as requested.

Demonstrate both supported lead-provider choices and an additional command-backed participant on their real supported boundaries. Fixture transports qualify decoders, not native behavior. Native tests requiring existing credentials or billable calls are prepared with concrete inputs, call counts and estimated spend before the applicable authorization. No paid fallback or inferred credential change is introduced.

If a native profile is unavailable, software work can continue, but R10 and the associated slice qualification remain partial. Do not mark the full ladder accepted by substituting an unavailable profile's fixtures.

## Outcome and cost comparison

Assessment arms: retained current two-role review, unified independent review, and unified solo on identical source bytes and settings. Repair arms: a frozen direct single-worker path with the same host patch/probe contract, unified solo repair, and unified required-review repair. Match granted evidence, output limits, oracle and effect boundary so the comparison measures orchestration rather than unequal access.

Task 8 fixes task IDs, source/probe hashes, participant settings, repetitions, execution order, budget, graders, and disposition criteria before new model calls. Include clean cases, seeded defects, absent evidence, conflicting claims, correct/wrong repair candidates and interruptions. Keep tuning and unseen cases separate. Save decisions before grading and retain raw failed, truncated, cancelled and inconclusive outputs.

Quality acceptance on the frozen matched set requires no lost contracted capability, no reduction in completed-correct outcomes against the applicable baseline, and no additional critical miss. Also report false positives/unsupported findings, severity definitions, disagreements and per-task variability; do not turn a small passing sample into a population accuracy claim. A weaker result is revise/inconclusive even if cheaper.

Report all model/tool calls, input/output tokens, elapsed time, human interventions/corrections and checking work. Do not add reasoning tokens twice. Billed dollars and human time are unknown until observed; missing values are not zero. Count failed/escalated work. Any cost ranking requires complete costs and a passing quality floor. No cost/latency improvement is required as an invented user threshold; if absent, report the maintenance/usability result separately and make no savings claim.

## Consolidation receipt

Record the original 18-name inventory, its final dispositions, primary help entries, compatibility routes, and before/after ownership of intake/dispatch/evidence/recovery. Re-run a scripted old and new journey through the same engine. Name removed duplicate paths, remaining adapters, and any policy branches that indicate the abstraction has grown too broad. Conduct the R13 intent-to-command walkthrough and record confusion without claiming broad UX validation from a single participant.

## Task 5 observed software evidence

See [installed assessment qualification](assessment-receipt.md): 40 module hashes matched, 15 outside-tree consumer/measurement processes, 35 legacy installed checks, five guard mutations detected, and 1,076 applicable tests passed with 25 skips. Two historical/host-limited modules are explicitly excluded and their failed receipts retained. Model/native quality and other-platform task receipts remain pending.
