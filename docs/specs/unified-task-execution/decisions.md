# Decisions — unified task execution

Status: revised spec approved, 2026-09-16. D16 accepts the implementation proposals and reflection extension; D17 records execution. Earlier entries preserve their original proposal/approval history. D18 records offline Task 1 acceptance; 1/8 tasks accepted. Task 2 intake implementation awaits acceptance.

## D1 — User-set scope

Patrick first requested consolidation of workflows and commands, then explicitly focused the work on attune-harness. He subsequently requested this Harness-owned spec and supplied both slices and six acceptance bullets. These establish the outcome and scope. They do not constitute approval of an implementation plan that did not yet exist.

Settled: evidence assessment first; solo and bounded independent review through one path; scoped repair second; explicit policies; adaptive selection separately evaluated; compatibility routes; operation-specific qualification; truthful recovery; frozen outcome/cost comparisons.

## D2 — Proposed command scope, revised after naming steer

Use task-facing **review** and **fix**, with **status** and **resume** for continuation. The original proposed run/task/setup primary vocabulary described machinery and is superseded by this proposal after Patrick's naming steer. Keep the 18 existing commands, with review controls becoming compatibility adapters where their behavior is migrated. Retain setup/index/extension/protocol operations directly. An advanced task-control group may expose reconcile/transfer/cancel without making them new workflow concepts.

Reason: the maintenance target is shared execution. A broad command rename would add migration work before demonstrating it. D11 settles the familiar task verbs; exact CLI syntax and supporting status/resume controls remain proposed.

## D3 — Proposed small task contract above the core

Keep public core Task/Participant/Output/Check unchanged. Add a product task envelope and bounded assignment plan in existing `src/attune_harness`. Scope, current grants, model/settings, budgets, inputs and policy version are revision-bound. Old records use versioned translation and existing operation identifiers; do not rewrite their accepted digests.

Reason: the tiny core is reusable; expanding it with document, checkout, and review-specific fields would weaken that boundary. A second persistence or model execution stack is rejected.

## D4 — Proposed explicit assessment plans and integration

Support solo and independent-review plans with exactly one or two assessment assignments. The host projects identical permitted evidence to each role; the reviewer does not see the lead narrative before returning. Host validation creates a deterministic integrated result containing each narrative and attributed findings/disagreements. No extra synthesis model call is required in the first slice.

Findings may carry supporting evidence references and bounded dispositions; valid references do not prove their interpretation. Semantic correctness remains assessed separately. A configurable roster with two same-model identities does not establish different-model independence when that is required by policy.

## D5 — Proposed repair effect boundary

Models propose a structured patch through the read-only participant boundary. Harness validates an exact list of regular UTF-8 file replacements, before-image hashes and scope, then applies each replacement through the operation journal. An accepted, separately defined argument-vector probe checks the resulting artifact. The worker cannot edit the probe or choose a different command after seeing failure.

Use a dedicated checkout and preserve the original user's work. Partial multi-file effects are recorded, not described as an atomic transaction. Before/after hashes support bounded reconciliation; any unexplained content remains unresolved. No automatic rollback overwrites later edits.

Reason: this produces real effects without first qualifying unrestricted native editing. The alternative is a native editing adapter with equivalent scope/effect controls; it remains viable later but needs its own boundary evidence.

## D6 — Proposed review policy for repair

Accepted plan records review as none, requested, or required. None is allowed only where existing policy permits. A requested review is part of the accepted plan; removing it changes the accepted plan rather than silently treating failure as success. Required review cannot be disabled by a weaker per-run preference. Reviewer receives the frozen patch, before/after evidence and probe results, but no worker self-verdict. Decisions and evidence bind to the final artifact hash.

Material review objections remain unresolved until supported probes or an explicit recorded disposition resolve them under existing policy. Model agreement is not acceptance evidence. Do not invent a broad new governance framework in this runtime.

## D7 — Proposed qualification plan

Use deterministic and independent subprocess peers to prove software boundaries; qualify native providers separately with frozen matching cases. Preserve requested versus observed identity and report qualification per operation/role/profile. Reuse the retained eight-case screening only as historical context, not as training/evaluation material for claiming unseen-case improvement.

There is no numerical savings promise. Correctness and critical-miss comparisons precede economics; missing billed usage or human correction data remains unknown. Task 8 prepares a concrete protocol and estimate before any separately authorized live calls.

## D8 — Ownership and timing

Voyage validation reuse remains owned by its active ladder. This spec uses retrieval entry points without replacing generation validation or changing reranking defaults. Before touching shared retrieval integration tests, refresh the baseline and preserve the other task's accepted changes. No dependency on completing the wider adaptive-collaboration research is invented.

## D9 — Review questions and remaining execution inputs

D16 approves the implementation proposals in D2–D7 and D13. Baseline fixture identities, native participant/model profiles, trial count, live-call estimate, and the first real repair pilot repository are fixed in the named execution tasks before their experiments. Their absence does not prevent design approval, but live quality or real-application readiness cannot be declared until they exist and the relevant checks run.

Spec creation was recorded through the canonical `spec` command workspace `spec-a7c71058477048ccab9fd1fc8e9b75d3`, revision 1. The user's writing request was transcribed as `create_spec`; plan approval and execution were not transcribed or inferred.

## D10 — User naming direction and pushback

Patrick: “I think they should be designed to be memorable and associated with vibe engineering tasks,” followed by “pushback?” This establishes the naming requirement, not approval of exact proposed verbs.

Recommendation: familiar task verbs; review and fix first, with plan/build/ship only when their promised journeys exist. Keep different effects recognizable while sharing their execution services. Counter-case: familiar verbs may overpromise; for example, a readiness report cannot be labeled ship. The runtime's goal is fewer duplicate mechanisms, not the smallest possible vocabulary.

## D11 — Task vocabulary agreed

Patrick quoted the recommendation “plan, build, fix, review, ship” and replied “agreed.” This settles the user-facing vocabulary and replaces run/task/setup as the primary product framing. Review and fix map to the two requested slices; plan/build/ship remain later supported journeys. It does not approve all eight implementation tasks, authorize their execution, or expand this spec to implement all five verbs. Status/resume are proposed supporting controls rather than additional work categories.

## D12 — Draft authoring checks complete

Eight XML tasks parsed; declared paths, dependencies, local links, and the disposition of all 18 current commands were checked. The real tasks-boundary gates returned PASS: symbol-reality receipt `914597203c6b` and falsifiability receipt `661be94d2bc0`. The canonical workspace advanced to review at revision 3 after receiving those actual artifact and gate receipts. See [authoring receipt](authoring-receipt.md) for the evidence and limits. Implementation remains unstarted and unapproved.

## D13 — Proposed form and response reuse after latency steer

Patrick suggested caching dynamic forms or responses to reduce added latency. Add R14 within the existing eight tasks: immutable unbound form templates, current-task answer reuse, explicit project-profile defaults, and completed-operation replay. Cache hits still validate current dependencies and bind to the current task; saved answers never create fresh approval. Separate assignments and new evaluation trials cannot reuse another judgment.

The inspected Harness form builder already constructs forms without model calls. The proposal therefore measures build/render, transport, question count and call count before deciding which cache paths help. Broad cross-task model-response caching, remote cache infrastructure, and speculative provider calls remain deferred. This is a revision for review, not implementation approval.

After this revision, all eight tasks parsed and both tasks-boundary gates passed: symbol-reality `9fbd9947d364`, falsifiability `e6546d240668`. The canonical workspace returned to review at revision 6. No task has started.

## D14 — Requirements approved

On 2026-09-16 Patrick stated, “the requirements is approved.” This approves the current requirements R1–R14, including the agreed task vocabulary and bounded form/answer/response reuse requirement. Record the requirements as approved while retaining proposed implementation choices and the eight-task ladder for design review. This scoped approval does not accept implementation tasks or authorize execution or model campaigns.

The command workspace remains at plan review, revision 6. Its `approve_plan` action would approve a broader artifact than Patrick named, so no such action was submitted. Durable task state remains `completed=[]`, `current=null`, `auto_run=false`.

## D15 — Session insight mining requested; reflect proposed

Patrick requested a command and form template to mine sessions/chats for valuable facts and insights, including Opportunities, Keep and Pushback. The [proposed extension](session-reflection.md) recommends `reflect`, extensible discovery lenses and per-item Keep/Edit/Revisit/Discard. Keep is a save action that applies to any category; opportunities and objections do not become accepted work merely because they are saved.

The authoring artifact includes a reusable candidate template validated against the installed attune-forms library. It is not a registered command, installed template or memory write. The approved R1–R14 requirements and eight-task ladder are unchanged. The additional slice's name and integration remain for review.

## D16 — Revised spec approved

On 2026-09-16 Patrick instructed, “approve the revised spec.” This approves the revised design, validation plan, eight-task review/fix ladder, and D15's reflect extension, including its name and Keep/Edit/Revisit/Discard interaction. R1–R14 retain their earlier approval. Reflect is an approved follow-on design; its concrete host/storage adapters and implementation breakdown remain execution preparation, not a completed runtime feature.

The form template was cast and rendered with installed attune-forms 0.17.0. All four synthetic dispositions validated; unknown item, invalid action, missing ruling and missing source-slot cases were rejected; a six-category batch validated. See the actual template receipt for scope and limitations. These are authoring checks, not user submissions or memory saves.

Spec approval was recorded through the canonical plan collector after publishing the revised artifacts and real gate receipts (`8045caaeb7ea` and `716120f7263c`, both PASS). The collector accepted `approve_plan` at workspace revision 10. This approval does not mark any implementation task complete or start execution; the saved state remains `completed=[]`, `current=null`, `auto_run=false`.

## D17 — Execution authorized; Task 1 offline checks ready

Patrick confirmed “yes” to “go—start implementing the approved spec.” This resolved automatic approval review's rejection of the earlier ambiguous “g0.” The canonical collector accepted start_execution at revision 11. Real execution gates passed (symbol-reality `642d64892a92`, falsifiability `5d808e09d5af`); Task 1 started at revision 13. Saved state is `completed=[]`, `current=1`, `auto_run=false`.

Task 1 delivered the reproducible zero-provider baseline, 28 compatibility cases, a source/ownership inventory and [actual receipts](baseline.md). All 36 production modules and the captured unrelated Voyage work remain unchanged. The standard spec task-quality workflow invokes paid review agents, which the offline Task 1 scope does not authorize. No paid review ran or skipped score was labeled passing. Task acceptance and the offline-versus-paid review route remain explicit decisions after this concrete result.

## D18 — Baseline committed; offline Task 1 acceptance selected

Patrick instructed committing the existing spec and Task 1 baseline before continuing production implementation. Commit `e546cc6` contains those artifacts and their supporting assessments; unrelated Voyage work was excluded. The 28 compatibility tests passed again, all 154 frozen artifacts matched their manifest, and all 36 production modules still matched the baseline before implementation.

On the open review-route choice Patrick said, “I'm leaning toward offline unless you think the paid would be superior.” The assistant agreed for this deterministic baseline and transcribed acceptance through the canonical workspace. `approve_task` was accepted at revision 2 of `spec-a783c8d9ea154f23a68e04f7effe23a3`; Task 2 started at revision 3. The numeric receipt field explicitly denotes observed test pass percentage (28/28 × 100), never a paid-model score. Paid reviews and live qualification remain unrun. Saved state is completed=[1], current=2, auto_run=false; this does not approve remaining implementation tasks.

## D19 — Task 2 choices and limits

Intake uses the existing `RunStore` unchanged and shares participant configuration validation with the legacy loader, whose two-participant minimum remains intact. The new loader permits one configured participant for solo intake. The CLI explicitly separates positional legacy requests from goal intake and bound task responses. The new route ends at accepted intake with execution marked not_started; Task 3 owns assessment execution.

Form construction/cache and validation share the contract module, with the CLI depending on it in one direction. Only unbound immutable rendering is cached; identities, answers, permissions and submission bindings are produced separately. Process-local reuse measured a small local benefit; no persistent cache or user-visible speed claim is justified. Keyword corpora must exclude task storage; the conservative Voyage check requires an external task directory when selected repository roots overlap it. No unrelated Voyage validation-reuse implementation was changed.

## D20 — Auto-run remaining offline tasks (2026-09-16)

Patrick: “auto-run the rest.” Canonical Task 2 action `auto_run_remaining` accepted its offline receipt and enabled automatic continuation. Completed tasks: 1 and 2. This includes implementation and offline qualification for Tasks 3–7 and preparation of Task 8's frozen trials. It does not authorize model/provider spend or manufacture unrun native evidence.

## D21 — Offline implementation complete; native comparison held

Tasks 3–7 were automatically accepted from actual software receipts under D20; no paid-model gate score was substituted. Saved state is completed=[1,2,3,4,5,6,7], current=8, auto_run=true. Task 8 has a frozen installed-artifact protocol, 49 offline runner checks and a refreshed all-command compatibility receipt. It is not accepted: native quality, blind human outcomes and economic evidence remain absent under Patrick’s offline choice. No paid trial, new budget allocation, remote push or PR was performed. [Verification](verification.md) gives both bounded slice decisions.

## D22 — Paid execution authorized; first trial rejected by Claude billing

Patrick asked to proceed with Task 8, then explicitly said “I just added money to the account please use it.” The Codex top-up was observed. Following a stated planning estimate and exact-protocol admission, the frozen first Claude trial returned HTTP 400 insufficient credit, with zero tokens and $0 reported cost. The runner stopped after one dispatch; zero Codex trials ran. The [live receipt](task-8-live-receipt.md) preserves the failure and separates the Codex and Anthropic billing routes. Task 8 is still current and unaccepted. No authentication fallback or retry was attempted.

## D23 — Subscription route and retained correction experiment

Patrick explicitly selected “Use existing Claude subscription,” later clarified that Anthropic Claude is funded, and agreed to continue after successful subscription responses were observed. Normal keychain access confirmed the Max login when the API-key override was omitted from only the subprocess environment. The original configured-key rejection remains a time-specific receipt, not a claim about overall funding.

The unchanged 60-trial comparison completed all 92 native calls and exposed eight required-review failures caused by approve responses containing positive findings. The prompt clarification was designed before editing, preserves the strict validator, and passed 178 software tests plus 22 independent installed processes. A separate targeted eight-case/16-call native follow-up was announced before dispatch under the same authorized spend class. It preserves original outcomes and has its own new artifact/protocol. Neither software nor runtime completion substitutes for the required human grades.

The targeted correction completed eight of eight repairs successfully, with 16 calls, passing probes and bound approval/empty findings. Total successful-provider dispatches across the original study and correction are 108, plus the separately retained rejected API attempt. Task 8 remains current because independent human semantic grading and correction-time evidence are not supplied by these runtime receipts.
