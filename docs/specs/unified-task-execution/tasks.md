# Task ladder — unified task execution

Status: implementation plan approved with the revised spec, 2026-09-16. **Tasks 1–7 accepted on offline evidence. Task 8’s 60-trial native comparison finished and exposed a review-contract defect. The correction passed eight targeted native cases. Independent human grading and final acceptance remain pending. See the [live receipt](task-8-live-receipt.md).** The approved reflect design is a follow-on slice; its implementation breakdown is not part of these eight tasks. See the [Task 1 baseline](baseline.md) and [Task 2 receipt](task-2-receipt.md) for actual checks and acceptance status.

Canonical XML: `.claude/plans/unified-task-execution.md`. Task acceptance and auto-run decisions belong to the existing spec lifecycle, not this summary. Naming agreement does not approve implementation.

| Task | Deliverable | Depends on | Requirements | Receipt |
|---|---|---|---|---|
| 1 | Freeze current contracts, deterministic fixtures, command inventory and baseline journeys | None | R1–R14 | Behavioral/metric baseline with source hashes, intake latency and exact commands |
| 2 | Add task intake, bounded form/answer reuse, versioned contract and identity-bound storage | 1 | R1,R4,R6,R13,R14 | Intake/cache/serialization and no-dispatch negative tests |
| 3 | Implement solo and independent-review assessment on shared services | 2 | R2,R5,R6,R12 | Real-library journey, isolated reviewer packets, path/call counts |
| 4 | Generalize continuation and preserve legacy review/control routes | 3 | R3,R4,R7,R12,R14 | Fault injection, isolated same-operation replay, all-command compatibility |
| 5 | Qualify installed Slice 1 and publish its bounded evidence | 4 | R1–R7,R10,R12–R14 | Independent consumer, cold/warm intake and artifact receipt; native obligations tracked |
| 6 | Implement scoped patch application and immutable acceptance probes | 5 | R4,R6–R8 | Real file/command effects, protected scope, fault and mutation cases |
| 7 | Add fix policy, review obligations and repair continuation to shared runtime | 6 | R2,R5–R9,R12,R13 | Failed-before/passed-after repair, review binding, recovery, installed checks |
| 8 | Run frozen comparative qualification and report both slice decisions | 7 | R3,R10–R14 | Native/live-fire and outcome/metric receipts, matched cache conditions, full command disposition |

Task 5 qualifies software and installed behavior without pretending native outcome evidence is complete. Task 8 owns the cross-provider/model comparison. Slice 2 may build on accepted Slice 1 software receipts while the unrun native obligations remain visible; neither full-slice promotion nor total spec completion follows from that narrower task acceptance.

## Boundaries and probes

- **Task 1 — baseline.** Behavioral probes capture legacy CLI exit/report semantics and operation/effect counts using current source. Freeze clean, defective, unknown and interrupted cases; a poison provider must fail any accidentally live invocation. Refresh shared files against Voyage validation reuse before freezing them.
- **Task 2 — intake.** Behavioral tests assert one identity across all generated bindings; missing/declined/stale/conflicting inputs dispatch zero operations. Prove core imports remain dependency-free and no old schema is relaxed to allow solo.
- **Form/response reuse — Tasks 1, 2, 4, 5, 8.** Baseline form/transport latency, then test cold/warm/bypassed equivalence, dependency invalidation, corrupted entries, saved-default freshness and task isolation. Assert a cached answer cannot approve an action and a completed response cannot satisfy another independent assignment. Measure avoided calls/questions and lookup overhead in-process and across CLI processes before claiming savings.
- **Task 3 — assessment.** Behavioral tests assert solo makes one participant invocation and independent review uses two isolated assignments through the same dispatch service. Seed disagreement and tool-only verification to fail any false semantic-verification claim.
- **Task 4 — continuation.** Fault probes cover every completed boundary, lost acknowledgement, stopped-run cancellation, transfer, invalid checkpoint and persistence failure. Existing accepted v1 records resume without digest rewriting; unknown paid effects stay unresolved.
- **Task 5 — installed artifact.** Evidence-chain receipt verifies module hashes outside the source tree, real optional-library calls, an independent command peer and primary review/status/resume journey. Record unsupported native profiles explicitly. Behavioral checks cover all 18 legacy routes without model calls where previously deterministic.
- **Task 6 — effects.** Real-file probes reject unauthorized/stale/unsafe path replacements and protect acceptance commands/oracles. Kill after a write and before acknowledgement; assert known after-images reconcile without duplicate writes, while unexpected content remains unresolved. Report guard mutation detections.
- **Task 7 — repair.** Behavioral journey fails before and passes after the intended fix; wrong/no-op fixes fail. Assert requested/required review cannot disappear, review is bound to final bytes, and resume reuses completed writes/probes only with matching inputs.
- **Task 8 — qualification.** Metric/live-fire receipts use an immutable protocol, matched baselines and retained failures. Measure correctness, unsupported claims, missed defects, calls/tokens, latency and human correction; unknown cost stays unknown. Report task vocabulary and retired duplicate paths separately from savings.

## Planned surfaces

Existing implementation: `src/attune_harness/cli.py`, `src/attune_harness/review.py`, `src/attune_harness/review_contract.py`, `src/attune_harness/review_participants.py`, `src/attune_harness/review_cli.py`, `src/attune_harness/review_store.py`, `src/attune_harness/recovery.py`, `src/attune_harness/process.py`, and `.gitignore`.

Task 2 adds `src/attune_harness/task_contract.py` and `src/attune_harness/task_cli.py`. Tasks 3–7 implement `src/attune_harness/task_runtime.py`, `src/attune_harness/task_policies.py` and `src/attune_harness/repair.py`. The [verification receipt](verification.md) identifies implemented suites, installed consumers and the prepared Task 8 experiment. XML files-to-create entries retain the approved plan.

Existing regression owners: `tests/test_review.py`, `tests/test_review_boundaries.py`, `tests/test_recovery.py`, `tests/test_native_evidence_review.py`, `tests/test_voyage_integration.py`, `tests/test_operations.py`, `tests/test_extensions.py`, `tests/test_mcp.py`, and `tests/test_process.py`. Add or reuse focused cases rather than duplicating existing assertions mechanically.

## Execution notes

Write a half-page implementation note with cases, actual scratch probes and rejected alternative before each core/effect increment, as required by the existing project discipline. It supplements this design with the actual refreshed file set; it does not reopen settled scope.

Model trials are not hidden inside offline task checks. Prepare their exact packet and estimate, then apply the existing spend authorization. Gate receipts from spec authoring establish only that the plan passed those mechanical checks. No automatic paid review invocation is authorized by this draft.
