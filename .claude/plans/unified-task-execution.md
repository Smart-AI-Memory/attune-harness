# Unified task execution

Status: revised spec and implementation plan approved, September 16, 2026. Owner: attune-harness.
Requirements R1–R14, design, validation and this eight-task plan are approved. Execution is authorized.
Spec: `docs/specs/unified-task-execution/`. Tasks 1–7 accepted on offline evidence; 7/8 accepted. Task 8 supplementary assistant grading is complete: 48/60 original trials completed correctly, with both original quality floors requiring revision; the separate corrected repair follow-up grades 8/8. Task 8 remains current and unaccepted. Frozen human grading and final acceptance remain pending. See docs/specs/unified-task-execution/task-8-assistant-grading.md.

Outcome: one task identity and shared execution services for evidence assessment
(solo and independent review), then scoped repair with real effects and a real
acceptance probe. Agreed task vocabulary: plan, build, fix, review, ship.
These two slices deliver review and fix; status/resume are supporting controls.
Preserve all 18 current command routes and supported old review records.

<tasks>
  <task id="1" name="freeze-contracts-and-behavioral-baseline">
    <objective>Freeze the current command, request, result, effect and recovery contracts against refreshed source before creating a new orchestration path; prepare failure-sensitive deterministic baseline cases for requirements R1 through R14.</objective>
    <files-to-create>
      <file path="tests/test_task_compatibility.py">Behavioral command/request/result and legacy-record fixtures, including all 18 command dispositions and no-model deterministic routes.</file>
      <file path="experiments/task_execution/baseline.py">Portable zero-provider baseline runner using fresh output directories and actual optional-library boundaries; retain source hashes, call counts and command results.</file>
      <file path="docs/specs/unified-task-execution/baseline.md">Actual interpreter/source identity, frozen fixture definitions, legacy semantics and duplicate-path inventory.</file>
    </files-to-create>
    <files-to-modify>
      <file path="docs/specs/unified-task-execution/validation.md">Record exact fixture/probe references and gaps after inspecting the current regression suite; preserve future native obligations.</file>
    </files-to-modify>
    <validation>
      <check>Run the legacy review, recovery, native-evidence and relevant retrieval integration baseline in an identified environment. Poison live provider construction and assert zero model/provider calls.</check>
      <check>Capture current CLI argument, output and exit contracts; parse all 18 top-level commands and match every one to the disposition table. Include clean, defective, unknown, missing-input and interrupted cases.</check>
      <check>Retain genuine paused/completed/uncertain legacy records with accepted digests and operation identities. Record current dispatch/persistence ownership so a renamed wrapper alone cannot count as consolidation.</check>
      <check>Refresh shared source and tests against active Voyage validation work. Save the actual source hashes and preserve its unrelated changes and frozen experiment environments.</check>
      <check>Measure existing intake build/render/validation and transport latency separately, including repeated same-process and fresh CLI invocations; record question/model call counts before choosing bounded cache storage.</check>
    </validation>
    <risks>
      <risk severity="high">A stale or self-generated baseline can certify a regression. Capture real pre-change behavior and independent file/probe observations before candidate execution.</risk>
    </risks>
  </task>
  <task id="2" name="add-unified-intake-and-task-record">
    <objective>Introduce a versioned product task contract and single-request intake without changing the dependency-free core or weakening legacy two-role request validation.</objective>
    <files-to-create>
      <file path="src/attune_harness/task_contract.py">Task/revision, explicit policy, bounded assignments, accepted inputs, participant settings, scope and budgets; no provider SDK imports.</file>
      <file path="src/attune_harness/task_cli.py">Task-oriented review intake, form or conversational/headless collection, bounded unbound-template reuse, validated answer defaults, explicit legacy-versus-goal mode, and generated internal bindings.</file>
      <file path="tests/test_task_contract.py">Input, revision, budget, source-state exclusion, identity, schema, cache invalidation/isolation and deterministic no-dispatch behavior.</file>
    </files-to-create>
    <files-to-modify>
      <file path="src/attune_harness/cli.py">Register task-oriented review intake while retaining the existing positional request mode and all existing command routes.</file>
      <file path="src/attune_harness/review_store.py">Reuse atomic persistence/leases with explicitly versioned new task records; leave supported legacy records intact.</file>
      <file path=".gitignore">Ignore generated task state without hiding the spec or authoring evidence.</file>
    </files-to-modify>
    <validation>
      <check>Behavioral tests prove one durable identity across intake and generated retrieval/review bindings. Missing, declined, stale or mutually conflicting inputs dispatch nothing.</check>
      <check>Assert accepted material changes invalidate dependent grants/results, unknown control fields fail closed, and new solo requests do not relax legacy registry/form rules.</check>
      <check>Reject task-state paths inside selected retrieval or repair scope. Confirm package core imports without optional Attune/provider dependencies.</check>
      <check>Legacy review request parsing and public core construction remain unchanged. This task does not claim an end-to-end assessment before Task 3.</check>
      <check>Cold/warm/bypassed forms have equivalent current meaning and separate task bindings. Changed schema/options/project/policy invalidate entries; corruption/eviction rebuild without a model call. Reuse valid same-task answers, validate saved profile defaults, and reject cached approval or replayed action authority.</check>
    </validation>
    <risks>
      <risk severity="high">Task identity could be mistaken for authorization. Bind scope and current grants to the accepted revision, and never accept model output as a grant.</risk>
    </risks>
    <dependencies><dep>1</dep></dependencies>
  </task>
  <task id="3" name="share-solo-and-independent-assessment-runtime">
    <objective>Execute solo and bounded independent-review assessment through one shared operation path with real evidence services, isolated participants and truthful integration.</objective>
    <files-to-create>
      <file path="src/attune_harness/task_runtime.py">Bounded operation execution using existing adapters and recovery primitives; one participant-dispatch and evidence collection path.</file>
      <file path="src/attune_harness/task_policies.py">Explicit assessment plans and deterministic integration with attribution, unknowns and separate execution/acceptance outcomes.</file>
      <file path="tests/test_task_assessment.py">Solo/team call counts, actual tools, context isolation, contradictory findings, invalid output and source-freshness cases.</file>
    </files-to-create>
    <files-to-modify>
      <file path="src/attune_harness/review.py">Translate legacy review into the shared assessment services; retain legacy operation identities and result projection.</file>
      <file path="src/attune_harness/review_participants.py">Reuse host-issued evidence and correlation for assignment-based invocation, preserving native read-only behavior.</file>
      <file path="src/attune_harness/task_cli.py">Connect accepted goal intake to the actual assessment path.</file>
    </files-to-modify>
    <validation>
      <check>Behavioral journey runs actual forms/retrieval/verification libraries and an independent command peer; solo invokes one participant and independent review invokes two distinct assignments via the same service.</check>
      <check>Inspect exact packets and assert reviewer receives no lead output before its response. Enforce different-model obligations where required, not merely distinct labels.</check>
      <check>Seed unsupported claims, no evidence and disagreement; retain them without silently returning clean or semantically verified. A refuted document remains distinct from a failed execution.</check>
      <check>Run legacy regression cases and source-path probes showing no second dispatch/error/telemetry loop remains behind the legacy wrapper. Do not add an automatic synthesis call or adaptive routing.</check>
    </validation>
    <risks>
      <risk severity="high">A generic engine may erase domain semantics or leave duplicate loops intact. Require actual shared call paths and preserve raw attributed outputs.</risk>
    </risks>
    <dependencies><dep>2</dep></dependencies>
  </task>
  <task id="4" name="unify-continuation-and-legacy-controls">
    <objective>Provide status/resume and bounded reconciliation, transfer and cancellation through common task controls while preserving supported legacy checkpoints and all 18 command routes.</objective>
    <files-to-create>
      <file path="tests/test_task_recovery.py">Failure injection, legacy/new record continuation, scope changes, ownership, reviewer isolation and completed-operation replay.</file>
    </files-to-create>
    <files-to-modify>
      <file path="src/attune_harness/recovery.py">Share operation replay and task controls through explicit schema/policy adapters; preserve existing paid-stage and unknown-effect handling.</file>
      <file path="src/attune_harness/review_store.py">Version-aware inspection and state validation without rewriting accepted legacy digests.</file>
      <file path="src/attune_harness/review_cli.py">Translate old command/control contracts to shared services without changing arguments or exit semantics.</file>
      <file path="src/attune_harness/task_cli.py">Expose primary status/resume and advanced bounded controls using saved accepted inputs.</file>
      <file path="src/attune_harness/cli.py">Complete command routing and task-oriented primary help while preserving advanced discovery.</file>
      <file path="tests/test_task_compatibility.py">Assert every retained route's semantics and zero-model tool/protocol/inspection paths.</file>
    </files-to-modify>
    <validation>
      <check>Pause/resume after every completed operation without repeating calls. Crash after dispatch and before acknowledgement; assert unresolved effects block automatic retry.</check>
      <check>Load Task 1's real legacy checkpoints and resume without changing their original schema, accepted hashes or operation keys. Unknown future controls cannot execute.</check>
      <check>Reject stale checkpoints, copied ownership, concurrent writers and changed accepted inputs/registry/grants. Transfer uses a fresh attempt without violating independent review or legacy limits.</check>
      <check>Verify stopped-run cancellation preserves effect uncertainty and completed-state precedence. Preserve existing paid-stage replay with zero new permission when only completed stages are consumed.</check>
      <check>All 18 command dispositions pass compatibility probes; inspect/status and direct deterministic/protocol commands invoke no model.</check>
      <check>Reuse completed responses only for the same matching task revision and operation/assignment. Another reviewer, changed evidence/settings or a new evaluation attempt cannot consume that result as fresh independent work.</check>
    </validation>
    <risks>
      <risk severity="high">Rekeying operations can repeat external effects. Keep version-specific translation explicit and prove old-record replay from baseline artifacts.</risk>
    </risks>
    <dependencies><dep>3</dep></dependencies>
  </task>
  <task id="5" name="qualify-installed-assessment-slice">
    <objective>Demonstrate the first complete task journey from installed artifacts and record its software qualification separately from outstanding native-model quality.</objective>
    <files-to-create>
      <file path="scripts/qualify_task_execution.py">Independent installed consumers for intake, solo/team assessment, inspection, interruption and continuation; explicit no-provider default.</file>
      <file path="docs/specs/unified-task-execution/assessment-receipt.md">Source/artifact hashes, executed commands, suite/mutation results, provider-profile matrix and outstanding live obligations.</file>
    </files-to-create>
    <files-to-modify>
      <file path="README.md">Document the actually supported review/status/resume journey and compatibility routes without claiming repair or unqualified providers.</file>
      <file path="docs/specs/unified-task-execution/validation.md">Bind the installed consumer and qualification matrix to observed results.</file>
    </files-to-modify>
    <validation>
      <check>Build/install in a fresh environment; from outside the source tree verify all installed module hashes, then complete solo and independent-review tasks using real optional libraries and an independent subprocess peer.</check>
      <check>Demonstrate one goal-to-result identity and interrupted continuation without hand-editing intermediate JSON. Inspect old/new results and compare required behaviors to Task 1.</check>
      <check>Run required targeted and full applicable software suites, plus disposable guard mutations; report detected mutations and failing new tests per guard. Test supported OS behavior on actual native runners before claiming it.</check>
      <check>Record native provider and semantic qualification as pending when no real receipt exists. Task acceptance establishes software/installed behavior only; Task 8 still owns R10/R11 live evidence.</check>
      <check>Compare cold/warm/bypassed installed intake with matched inputs, including separate-process calls. Report lookup/freshness/render/transport durations, usable-form latency, avoided questions/calls and cache size; no latency claim follows from hits alone.</check>
    </validation>
    <risks>
      <risk severity="medium">Source-tree imports can make an old installed wheel appear current. Hash modules and use isolated outside-tree consumers.</risk>
    </risks>
    <dependencies><dep>4</dep></dependencies>
  </task>
  <task id="6" name="implement-scoped-repair-effects-and-probes">
    <objective>Provide a host-controlled patch and acceptance-probe effect boundary using real files in a dedicated checkout, without expanding existing native participant tool grants.</objective>
    <files-to-create>
      <file path="src/attune_harness/repair.py">Strict replacement-patch decoding, path/preimage validation, protected probe policy, journaled writes and bounded effect reconciliation.</file>
      <file path="tests/test_task_repair_effects.py">Real file/command acceptance, scope attacks, stale preimages, protected checks, partial writes and lost acknowledgements.</file>
    </files-to-create>
    <files-to-modify>
      <file path="src/attune_harness/task_contract.py">Revision-bound repair scope, immutable probe and review obligations.</file>
      <file path="src/attune_harness/task_runtime.py">Dispatch patch/probe operations through the shared effect journal.</file>
      <file path="src/attune_harness/recovery.py">Bounded before/after-image reconciliation without assuming whole-patch atomicity or overwriting later edits.</file>
      <file path="src/attune_harness/process.py">Only changes justified by the accepted probe's environment/control profile; preserve existing adapter supervision semantics.</file>
    </files-to-modify>
    <validation>
      <check>In a real dedicated fixture checkout, establish a failing immutable acceptance probe; apply the intended file replacement and observe passing behavior. Wrong and no-op patches must fail acceptance.</check>
      <check>Reject traversal, outside paths, symlink/reparse/hard-link ambiguity, state/metadata/probe edits, duplicate paths, invalid encoding, oversized output and stale before images before protected effects.</check>
      <check>Inject failure after one replacement but before acknowledgement and across a multi-file partial patch. Known after-images reconcile without a second write; unexpected bytes remain unresolved.</check>
      <check>Probe argv, cwd, environment, timeout and oracle are fixed before worker execution. A worker cannot suppress or replace a failed check. Document the actual isolation profile rather than calling process supervision a sandbox.</check>
      <check>Mutation receipt detects removed scope, preimage, protected-probe and post-write guards; unrelated files remain unchanged.</check>
    </validation>
    <risks>
      <risk severity="high">Filesystem races or multi-file partial effects can corrupt work. Use qualified handle-based boundaries, dedicated checkout scope and explicit unresolved outcomes.</risk>
    </risks>
    <dependencies><dep>5</dep></dependencies>
  </task>
  <task id="7" name="compose-fix-review-and-repair-continuation">
    <objective>Deliver the fix task through the shared runtime with optional/requested/required independent review, a final checked artifact and truthful continuation.</objective>
    <files-to-create>
      <file path="tests/test_task_repair.py">End-to-end repair plans, review policy, final-artifact binding, native-boundary fixtures and resumed effects.</file>
      <file path="docs/specs/unified-task-execution/repair-receipt.md">Actual patch/probe/review evidence and installed software qualification, separate from native outcome evaluation.</file>
    </files-to-create>
    <files-to-modify>
      <file path="src/attune_harness/task_policies.py">Repair plans using the same intake, dispatch, evidence and recovery services as assessment.</file>
      <file path="src/attune_harness/task_cli.py">Add goal-oriented fix intake and surface resulting diff/probe/review states.</file>
      <file path="src/attune_harness/cli.py">Expose the supported fix verb without advertising unsupported plan/build/ship journeys.</file>
      <file path="scripts/qualify_task_execution.py">Installed repair consumers with real writes, subprocess probes and interrupted continuation.</file>
      <file path="README.md">Document supported fix effects, required evidence and precise limitations.</file>
    </files-to-modify>
    <validation>
      <check>One request produces real failing-before/passing-after behavior, an attributed diff and immutable acceptance evidence. Assert the same dispatch/persistence/evidence services execute assessment and repair.</check>
      <check>Optional no-review mode works only where policy permits; requested/required review cannot disappear on failure. Reviewer sees final diff and probe evidence without worker self-verdict.</check>
      <check>Missing review, unresolved objections, incorrect/no-op patches, changed probes, or changed final bytes cannot produce verified completion.</check>
      <check>Resume every completed effect without repeating writes or probes under unchanged inputs; uncertain effects require evidence-based reconciliation. Preserve current native read-only defaults.</check>
      <check>Build a fresh installed artifact and run outside-tree consumers, appropriate regressions and failure-sensitive mutation cases. Keep live-provider outcome claims pending until Task 8 receipts exist.</check>
    </validation>
    <risks>
      <risk severity="high">Passing tests can be gamed by changed probes or stale reviews. Protect the oracle and bind every acceptance result to final artifact bytes.</risk>
    </risks>
    <dependencies><dep>6</dep></dependencies>
  </task>
  <task id="8" name="qualify-outcomes-providers-and-consolidation">
    <objective>Freeze and execute matched outcome comparisons under applicable authorization, qualify exact participant/operation profiles, and report whether both slices deliver useful consolidation.</objective>
    <files-to-create>
      <file path="experiments/task_execution/campaign.py">Prepare/execute/score immutable held-out assessment and repair comparisons, explicit provider invocation and retained failed/inconclusive attempts.</file>
      <file path="tests/test_task_campaign.py">Offline evaluation-integrity, cost-unknown, input-freeze and no-implicit-dispatch checks.</file>
      <file path="docs/specs/unified-task-execution/verification.md">Final source/artifact IDs, both slice verdicts, per-operation qualification, command/path inventory and measured outcome/economic limitations.</file>
    </files-to-create>
    <files-to-modify>
      <file path="docs/specs/unified-task-execution/validation.md">Record frozen protocol and exact commands before calls, then link retained results without changing acceptance after scoring.</file>
      <file path="docs/specs/unified-task-execution/tasks.md">Reflect accepted task state only after actual receipts and user task decisions.</file>
      <file path="docs/qualification.md">Describe only supported task/provider/platform profiles and outstanding obligations.</file>
    </files-to-modify>
    <validation>
      <check>Prepare task hashes, model/settings, repetitions, order, budgets, graders and outcome criteria before any live call. Produce a concrete call/spend estimate and apply existing authorization; never infer permission from a green offline test.</check>
      <check>Compare retained current review, unified solo and unified independent review on matched evidence; compare direct and unified repair plans with identical host effect/probe boundaries. Include clean, defective, unknown and interrupted cases and retain every outcome.</check>
      <check>Demonstrate actual supported Claude/Codex lead paths and an additional participant, with per-operation receipts. Fixtures or configured identities cannot satisfy missing native qualification.</check>
      <check>Report completed-correct outcomes, critical misses, unsupported findings, calls/tokens, elapsed time and human correction. No quality regression on the frozen set; unknown billed or human costs remain unknown and block unsupported rankings.</check>
      <check>Complete all 18 command compatibility probes and the task-vocabulary walkthrough. Record primary help entries, actual retired duplicate execution paths, remaining adapters and the separate decisions for both slices.</check>
      <check>Preserve historical campaigns, unrelated work and every failed trial. Report partial or inconclusive qualification honestly; no full-spec acceptance without required evidence.</check>
      <check>Match and disclose cache conditions across comparison arms; distinguish resumed completed operations from fresh model trials. Independent reviewers and new repetitions must execute their own assignments; report measured intake latency with correctness.</check>
    </validation>
    <risks>
      <risk severity="high">Small synthetic sets, shared grading errors or unequal context can produce false improvement. Freeze comparable inputs, retain disagreement and limit conclusions to the measured profile.</risk>
    </risks>
    <dependencies><dep>7</dep></dependencies>
  </task>
</tasks>

Read decisions D1, D11 and D16 for the user's approved direction and revised-spec approval.
The approved reflect extension follows this ladder; its implementation breakdown is separate.

<!-- spec-state: {"schema_version": 1, "completed": ["1", "2", "3", "4", "5", "6", "7"], "current": "8", "auto_run": true, "last_updated": "2026-09-16T15:38:43.630167+00:00"} -->
