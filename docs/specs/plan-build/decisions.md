# Decisions — plan and build

Status: **Tasks 1–7 accepted; Task 8 open; expanded worker comparison complete; Sol qualifies for the next connected trial**.
Historical decisions below are retained. D7 supersedes the former unresolved
first-journey and scoping-only status.

## D1 — User-set objective

Patrick requested: “Implement plan and build using the next generation of spec
command. It should build on our use of multiple modals/LLM's, scope the work
(determine the goal), be creative but ground it in our discipline that we've used
successfully in the past. pushback?” The assistant stated its interpretation of
“modals” as models/LLMs. No multimodal-input capability was inferred.

Prior settled direction from this conversation remains applicable: humans can
intercede through verbs; specs are principal authoring for complex constructs or
features; Harness should use clear prompts or XML-enhanced prompts when those fit.
Human control includes spec writing and quality decisions, not only command use.

## D2 — Assistant recommendation; first journey unresolved

Use one lifecycle behind plan and build. Recommend a complete feature in an existing
repository, including creation, modification, acceptance checks and continuation.
The native decision form also offers creating a new project and supporting both
journeys initially. No response has been recorded. This recommendation is not a
user scope decision.

The assistant supports the requested direction. The stated counter-case is the
size of combining authoring, multiple-model collaboration and new build effects;
a real bounded journey provides an acceptance target. No opposing user claim that
every task must use multiple agents was inferred.

## D3 — Creation tracking, not plan approval

The request authorizes preparing the concrete spec. The shared spec workspace
`spec-9cc4b3607da2443ea893b2fa02ff46ab` accepted `create_spec` at revision 1.
The common contract explicitly retains the unresolved first-journey choice.
The existing directory warning refers to this same session's source assessment;
these files amend that directory rather than creating a competing spec.

No plan-approval, start-execution or task-acceptance action has been submitted.
No plan/build source code, paid/native-provider run or delegated agent was started.
The source assessment and draft are preparation for the requested implementation.

## D4 — Safety and quality have several controls

Patrick clarified that humans in the middle are one method of enforcing safety
and quality alongside hooks and other constructs that influence model behavior.
The draft now treats human judgment, runtime enforcement, hooks, automated checks
and model guidance as complementary controls. It does not add a human gate to
every step or remove existing required decisions.

The assistant clarified the technical distinction: runtime instructions, feedback
and hooks influence execution behavior; changing model training or weights
requires a separate training process. No training capability is included here.
This clarification does not resolve the first-journey choice or approve the
implementation plan.

## D5 — Account for training; audit and improve controls

Patrick clarified that training had to be considered when designing the grammar
and obtaining correct responses, and that control/safety constructs should be
examined and reimplemented for maximum effectiveness and reliability. The
assistant acknowledged that D4's response had narrowed training too much to
changing weights: learned model behavior is a design input even without retraining.

The assistant recommended auditing and measuring controls, separating influence
from enforcement, preserving effective mechanisms and replacing weak parts rather
than starting with a wholesale rewrite. Patrick replied, “that makes sense to me.”
This accepts the audit-and-improve direction. It does not answer the earlier
first-journey form or approve an executable implementation plan.

The [control audit](control-audit.md) records source findings, four pure hook
observations, 31 passing existing test cases and proposed model/host qualification.
These are local baseline observations, not evidence that the future controls or
model responses have already improved.

## D6 — Latency before findings and decisions appear

Patrick proposed inspection/disposition mechanisms as a possible cause of latency.
In the native diagnostic form he selected “A — Before findings or a decision form
appear.” This narrows the measurement to time to first useful output, not primarily
processing after a human answer. It does not answer the unrelated first-journey
scope form.

The assistant verified historical raw timing receipts: repeated generation checks
dominated one local retrieval profile, while small intake-form presentation took
about two milliseconds. These findings justify tracing repeated inspection and
serial orchestration; they do not establish the cause of the delay Patrick sees.
The control audit and qualification outline now retain that distinction.

## D7 — Proceed with the existing draft after current authorized work

Patrick's side-conversation instruction, forwarded into the main task, was
“proceed with the existing draft since it already includes your recommended next
steps,” followed by “when the existing work is done.” The authorized Spec handoff
repair, independent review and closeout were completed first. This proceeds in
sequence, not concurrently with or by shortening that work.

The settled first journey is a small feature in an existing repository, including
file creation, intent correction, review, actual tests, Spec acceptance,
status/resume and interruption recovery. The lead selected JSON Lines export for
a captured, byte-identical copy of Harness's existing documentation tool as the
concrete fixture. The original eight-task outline is retained and made concrete;
no competing plan or fresh intake is created.

The instruction permits local preparation and implementation through the existing
quality/acceptance controls. It does not accept an unfinished task or approve
additional paid/native trials, activation, release or Attune AI retirement.
Task 1's actual baseline and concrete integration seams are ready for its existing
acceptance gate. Later product effect/dispatch controls remain implementation work.

## D8 — Task 1 accepted; Task 2 local implementation authorized

Patrick replied “proceed with recommended task” to the Task 1 gate's recommendation
to accept and continue. All 14 gate bindings and all 53 frozen receipt hashes were
checked first. The canonical Spec collector accepted `approve_task`, advancing
workspace `spec-9cc4b3607da2443ea893b2fa02ff46ab` from revision 8 to 9. The actual
result and Task 2 start event are retained under
`docs/receipts/plan-build-task2-2026-09-18/`. Spec state retains the accepted Task 1
receipt and current Task 2; auto-run remains false. This was not approval of all
remaining tasks or additional paid/native trials.

Task 2 makes two necessary compatibility changes alongside the new validator:
the existing execution owner explicitly rejects this contract-only profile, and
the preparation probe still rejects its deliberately incomplete envelope now that
the profile is recognized. Neither adds execution or changes the frozen baseline.
The host-projection trust boundary and deferred real Spec bridge are documented
in [work-contract.md](work-contract.md).

## D9 — Task 2 accepted; Task 3 planning assignments authorized

Patrick replied “excellent Approve and continue.” The 14 gate bindings and all
37 Task 2 receipt hashes were current before the canonical `approve_task` action.
Workspace revision 11 advanced to 12; Task 3 started at revision 13. The existing
Spec state owner retains both accepted task receipts, current Task 3 and auto-run
false. The real collector response is in
`docs/receipts/plan-build-task3-2026-09-18/task2-acceptance.json`.

Task 3 also extends the existing work validator/revision owner to retain planning
journals without confusing them with human authority. This is necessary for one
work identity across the conversation. It adds no new approval store. Planner
and critic results remain proposals; staging produces another unaccepted draft.
Source/configuration changes must not be refreshed away while staging an old
proposal. These choices and remaining host boundaries are recorded in
[planning-runtime.md](planning-runtime.md).

## D11 — Task 3 accepted; implement Task 4

Patrick selected “approve and continue.” The actual Spec collector consumed
`approve_task` at workspace revision 14, returned revision 15 and completed tasks
1–3. The existing Spec state owner persisted that acceptance. Task 4 started at
workspace revision 16. Auto-run remains false. The accepted Task 3 evidence is
retained unchanged; the collected response is in the Task 4 receipt directory.

Task 4 necessarily adds an optional effect manifest and journal to the Task 2
contract, and extracts the existing repair probe validator for reuse. These are
shared-owner changes required to bind scope and control commands before writes,
not another decision store. Old records retain their existing binding and profile.
Native trials, live activation and release remain outside this authorization.

## D12 — Task 4 accepted; auto-run non-high tasks

Patrick selected B: “Accept and auto-run remaining non-high tasks; retain paid-trial
boundaries.” All 20 Task 4 artifact hashes and all 47 receipt hashes were current
before submission. The collector requires `confirmed: true` for this explicit
auto-run choice; the initial false flag was rejected, and the corrected projection
of Patrick's same decision was accepted at revision 18. Task 5 started at revision
19. Both rejected responses and the accepted response are retained. Canonical and
persisted state agree: tasks 1–4 complete, current task 5, auto-run true.

Task 5 adds a dependent-build policy module to keep the existing planning runtime
readable, extends its effect manifest with fixed verification commands, and adds
the new qualified producer to the existing testing handoff. Its first supported
profile is an explicit ordered task chain with one producer per output, distinct
worker/reviewer identities and protected checks. Branching task graphs, repeated
edits of the same output and journal-preserving correction remain unqualified.
No paid/native dispatch, activation, release or retirement is authorized by B.

## D13 — Task 5 accepted; Task 6 connects the actual collector

The Spec workspace automatically accepted the non-high Task 5 receipt at revision
20, then started Task 6 at revision 21 under Patrick's existing B choice. The
embedded Spec state agrees: completed 1–5, current 6, auto-run true. Task 5's
source/installed/protection-removal receipts are frozen.

Task 6 adapts the existing Spec evidence display for an external Harness work
record while retaining the actual action collector. A successful collection is
followed by the work owner's bound acceptance write. This does not activate a new
MCP host or add another persistence owner. Steering is deliberately qualified for
a verified completed prefix and corrected pending suffix; broader rebasing needs
a separately explicit implementation boundary.

## D14 — Task 6 accepted; installable verb experience

The actual Spec workspace accepted Task 6 automatically at revision 22 and started
Task 7 at revision 23. State and frozen receipts agree: completed 1–6, current 7,
auto-run true. Task 7 adds plan/build to the compact catalog and routes existing
status/resume/file-reconciliation controls through the same work owner. Task CLI
dispatch is a necessary shared seam beyond the originally named CLI files. Older
commands retain their contracts; feature-only permission flags cannot override
other profiles' saved permissions.

Source checks and the first installed Harness run use the actual candidate Spec
owner. A separate isolated wheel of that owner is also built for the complete
installed bridge journey, so this task does not equate a source-path dependency
with a fully installed end-to-end result. No active installation is changed.

## D16 — Task 8 preparation is not native qualification

Tasks 5–7 continued under the accepted non-high auto-run choice. Task 8 now has
frozen planner/worker comparisons and 18 passing offline checks. The proposed
24 calls (eight each Luna, Astra and Fable) require a separate allocation decision.
No native calls or task-completion receipt has been issued. The concise comparator
retains identical host protections; semantic correctness is separately scored.
A successful role screen would still leave native connected-journey evidence to
be established before Task 8 acceptance. See [the concrete proposal](../../plan-build-task8-preparation.md).

## D17 — Approved native allocation completed; Task 8 remains open

Patrick replied A to the concrete 24-call allocation: Luna 8, Astra 8, Fable 8,
35–75 estimated Codex credits, 100-credit planning ceiling, existing Claude Max
and no new API dollars. All 24 invocations completed at 59.83688 estimated credits.
The trial allocation is exhausted; no repeat, release or Task 8 acceptance follows.

The [result](../../plan-build-native-results.md) retains 1/24 originally usable
responses, hidden exact-text/identity contract defects, three actual worker
implementation failures and separate diagnostics. Candidate profiles fail the
frozen 2/2 acceptance floor. Existing non-high local authorization supports
bounded contract correction; another native comparison requires a new allocation.
Native connected-journey quality and time to first useful presentation remain open.

## D18 — Continue Task 8's bounded local correction

Patrick reiterated “go task 8” after the completed native screen. Existing
non-high local authorization already covered the repair; no additional local
approval was required. The [correction](../../plan-build-contract-correction-results.md)
is now locally qualified, including legacy journal preservation, strict file
scope and stale-evidence controls. This checkpoint does not accept Task 8.

A candidate-only 12-call confirmation is prepared: four each Luna/Astra/Fable,
expected 25–40 Codex credits, 50-credit planning ceiling, existing Claude Max and
no new API dollars. It was awaiting separate approval at that checkpoint. D19 records the
subsequent approval and outcome. The instruction to continue local work does not
renew an exhausted native allocation.


## D19 — Approved v2 confirmation completed; retain the connected-journey boundary

Patrick selected “A — Run the bounded confirmation (Recommended)” for the
prepared twelve calls: Luna four, Astra four, Fable four; 25–40 estimated Codex
credits, 50-credit planning ceiling, existing Claude Max and no new API dollars.
All twelve completed using 30.29318 estimated credits. No retries or fallback
calls occurred; the allocation is exhausted.

The response contract accepted all original replies. Luna and Astra each pass
both repetitions in both roles. Fable has one functional worker failure and one
low-severity planner rationale requiring factual qualification; these are kept
separate. All six plans retain the corrected intent and stage without acceptance;
five worker artifacts pass the actual protected oracle. Grade limitations, original
outputs and source-change rejection remain in the
[confirmation report](../../plan-build-contract-confirmation-results.md).

This decision approves the confirmation only. It does not accept Task 8, native
critic/reviewer behavior, a connected journey, live activation or release. Continue
local preparation under the existing non-high authorization; a further native
allocation must be concrete and separately approved.

## D20 — Approved connected comparison stopped; preserve both original failures

Patrick replied “do A” to the prepared sixteen-call allocation: Luna four,
Astra twelve, 80–130 estimated credits, 160-credit planning ceiling, existing
ChatGPT and zero new API dollars. Ten invocations completed at 66.959635
estimated credits. Six unused calls are not reallocated; the campaign is closed.

All four Astra review controls pass. Luna's faithful plan omits required `choices`
and stops before critique. Astra's plan, critique, exporter and CLI pass; its
supplemental test discovery fails because the experimental runner does not expose
the fixture source path. A separate unchanged-source diagnostic passes six
supplemental and four protected checks. The original native journey remains
`needs_revision`; no final reviewer, completed handoff or stale-completion probe
is claimed. Actual Spec reacceptance, replay rejection and preserved completed
output were exercised before that failure.

The [connected report](../../plan-build-connected-results.md) retains the original
replies, source inspections, controls, probe outputs, timing and local diagnosis.
Task 8 remains open. Existing non-high local authorization covers bounded runner
and explicit-empty-choice grammar corrections. Further native trials require
their own concrete allocation; Task 8 acceptance and release remain separate.

The existing Spec workspace records progress at revision 25, event sequence 24;
completed tasks remain 1–7 and current task remains 8. An initial progress update
was rejected by automatic approval review as an external/private-data action.
Read-only configuration and handler inspection established the local stdio,
in-memory destination; a shorter update through the same tool succeeded. No
indirect state write or acceptance event was used.

## D21 — Local handoff qualification and approved six-call confirmation

The bounded correction passes 267 distinct source checks, 267 isolated-wheel
checks and 4/4 runner guard-removal trials. Unchanged original Astra replies plus
a labeled scripted reviewer complete source and installed local replays. The
original missing-field Luna reply still fails; no original native result is
regraded. These local checks made no provider calls.

Patrick replied “40 is fine for a credit limit” to the concrete six-call
confirmation: Luna four, Astra two, expected 15–30 estimated Codex credits,
40-credit planning ceiling, existing ChatGPT and zero new API dollars. This
approves that allocation without another form. It reuses the four previously
passed review controls as retained evidence and allows no automatic retries,
replacement calls or fallback. The prior allocation remains closed. Task 8
acceptance and release remain separate.

See the [local correction report](../../plan-build-handoff-correction-results.md)
and the frozen `plan-build-handoff-confirmation-preparation-2026-09-18` packet.

## D22 — Close the fresh confirmation; correct the independent baseline locally

The approved confirmation uses four calls and 7.744460 estimated credits, with
zero new API dollars. Explicit empty choices now pass the fresh planner contract.
The plan retains a disclosed medium envelope-detail finding and wording advice;
the exporter follows the protected envelope correctly. Synthetic Spec correction,
reacceptance, replay rejection and completed-export preservation pass.

Original CLI source changes the default Markdown punctuation. Direct pre/post
subprocess output confirms the violation of unchanged default JSON. The frozen
oracle misses it because both its expected output and CLI call the changed
implementation. The semantic failure closes the campaign before supplemental
worker/final reviewer dispatch; two calls are unused and not reallocated. The
journal stays paused at its recorded operation boundary. No original response,
source or grade is repaired into a success.

Existing non-high local authorization covers replacing this circular compatibility
expectation with pre-change output captured inside the already protected oracle.
The local correction passes 38 source and 38 installed checks; removal of its
guard reintroduces the false green (1/1 detected). The unchanged passing Astra
artifacts complete the local replay with a labeled scripted final reviewer.
This is not a fresh native completion or Task 8 acceptance. Further native calls
need a new allocation; release remains outside scope. Critique transfer is logged
separately as O-28 and has not been implemented in this correction.

## D23 — Authorize one fresh complete journey with 40 additional credits

Patrick directed “qualify the fresh complete journey. pushback?”, then clarified
“you're authorized to spend 40 more credits” and “continue the current task.”
That settles the allocation: one fresh six-call journey, Luna four and Astra two,
expected 15–30 estimated credits with a 40-credit additional planning ceiling,
existing ChatGPT and zero new API dollars. The prior 7.744460-credit failed
campaign stays closed and separate. No additional approval form is required.

The new packet freezes current sources, corrected captured-output oracle,
installed evidence, existing controls and decision material. Twenty local
preflight checks and both lifecycle checks pass. Original replies and source
proposals will be retained; a substantive failure stops the run without repair,
retry, replacement or fallback. Success must reach native final review and the
completed handoff, including no-repeat and stale-source checks. The synthetic
steering limitation remains disclosed. No Task 8 acceptance or release follows
automatically from this experiment.

## D24 — Fresh journey reaches a generated-test failure; retain the stop

The fresh six-call campaign uses five invocations and 4.701455 estimated credits,
with zero new API dollars. Planning, exporter and CLI pass, including the newly
protected pre-change output comparison. The original supplemental test reads
status from the outer JSONL envelope instead of its nested finding. Actual
execution yields three passes and one KeyError; the existing host records
needs_revision. Incomplete completion is rejected and failed resume dispatches
no additional participant call.

The final reviewer is not called. The allocation is closed with one unused call;
the remaining credit allowance is not silently converted into a new call sequence.
The original failure stays intact. In a disposable copy, one assertion correction
passes four supplemental and four protected checks. This is a local diagnostic,
not native repair or complete-journey qualification. All 1,355 earlier receipt
files remain unchanged. The [report](../../plan-build-fresh-journey-results.md)
retains original calls, actual outputs, timing and the diagnostic patch.

The next useful qualification is bounded repair/retest/resume of this real
failure, preserving successful work and current acceptance controls. Establish
that continuation locally before any additional paid sequence. Task 8 acceptance
and release remain outside the completed trial's authorization.

## D25 — Approve means approve and continue; qualify the retained recovery

Patrick clarified “that should approve and continue” and then “approve” after
the proposed bounded repair of the stopped-task handoff. Continue the existing
non-high local work without another approval ritual. This does not reopen the
closed native allocation or accept Task 8.

The existing preserve-completed boundary now supports the next task's settled
ordinary test failure. Fresh Spec acceptance, retained failure history, protected
completed files and actual retesting remain mandatory. Qualification passes 351
source and 351 installed checks, catches 3/3 guard removals and completes the
installed retained-reply reconstruction with scripted repair and final review.
All 12,378 earlier receipt files captured at correction start remain unchanged.
The original campaign remains failed. See [results](../../plan-build-repair-resume-results.md).

Prepare two native calls, Luna guided repair and Astra final review, expected
5–15 estimated Codex credits with a 20-credit planning ceiling and no new API
dollars. This is a proposed separate allocation, not spend authority or Task 8
acceptance. Keep the original scope and stop on substantive failure.

## D26 — Two-call trial approved; preserve its startup failure

Patrick selected “a/approve” for the two-call guided repair/final-review trial,
expected 5–15 credits with a 20-credit planning ceiling. One attempted Luna
process fails during local Codex client initialization under the outer workspace
sandbox. No model reply or usage is reported. Its unresolved journal is retained;
no file effect or Astra call occurs. The trial closes under its frozen no-retry
and unknown-usage rules. A separate host-access startup handshake passes without
starting a model thread or turn. See [results](../../plan-build-repair-native-results.md).

The proposed replacement keeps the total planning allowance at 20 credits,
reserving 2 for the unresolved startup and allowing 18 for the two new calls.
This is not a measured charge or a new authorization. Retain the original failure
and require explicit approval before replacement dispatch. Task 8 remains open.

## D27 — Approved retry fails unchanged; repair inspection and clarify intent

Patrick approved the replacement with “A/approve.” Proper host launch access
allows one Luna call, which returns the original faulty test unchanged. Its
estimate is 0.179815 credits; the reserved two credits for unknown startup usage
are not a measured charge. The host rejects unchanged replacements. Parent
inspection stops effects; Astra is not called and the allocation closes.

The saved invalid reply also prevents the previous reader from inspecting the
owner. The bounded local correction retains terminal invalid replies as readable
paused/failed evidence, while refusing effects, completion and invalid host
metadata. Resume records failure without another call. The experimental task
objective now states the actual failed test and diagnosed correction. Qualification
passes 362 source and 362 installed checks, with 3/3 guard removals detected;
original owners and trials remain unchanged. See [results](../../plan-build-repair-feedback-results.md).

Prepare one clarified two-call case, expected 5–15 new estimated credits and a
17-credit new-call ceiling within the same total 20-credit planning allowance.
This is pending allocation, not an automatic retry or Task 8 acceptance. The
observed clarity gap does not establish why Luna returned unchanged source.

## D28 — Prepare a matched repair-model screen before choosing a worker

Patrick asked whether another model would be better than Luna, then chose “go”
and A — Prepare comparison. That authorizes local preparation only, replacing
the pending Luna repair/Astra review proposal. Keep its frozen packet and all
prior failures. Do not treat this as a new paid allocation or production routing
decision.

Prepare Luna, Sol and Astra on three fixed cases with two repetitions each:
retained nested-status test failure, fresh injected finding filtering, and fresh
injected CLI default-format regression. Same case turns, current worker contract,
high reasoning and Standard service. Actual tests plus explicit preservation
inspection decide success; all original failures contribute to time/cost results.
The repaired handoff is fixed before the comparison; no model-specific tuning.

Local qualification passes 78 source and 78 installed checks and detects 3/3
guard removals. Reference repairs all pass; injected-process rehearsal exercises
18 dispatches with no model calls. The proposed new allocation is 18 calls,
65–135 estimated credits and a 150-credit planning ceiling, $0 new API dollars.
Ordinary resolved model/test failures are scored while independent cases proceed;
uncertain dispatch/usage, changed inputs and host boundary failures stop the
screen. No retry, native final reviewer, connected completion, Task 8 acceptance
or release is included. [Preparation](../../plan-build-repair-model-preparation.md).

## D29 — Approve the 18-call comparison; retain Luna provisionally

Patrick approved the concrete comparison with “a/approve”; the following “ok”
acknowledged continuation. This authorizes the prepared 18 calls and separate
150-credit planning ceiling, not another retry sequence or Task 8 acceptance.

All original replies pass: six each for Luna, Sol and Astra, including both
repetitions of the guided assertion repair and two fresh related injected defects.
Every repair passes four supplemental and four protected tests, semantic
preservation, unrelated-file protection, no-repeat continuation and stale-source
rejection. Grade evidence is frozen before aggregate recommendation. Review is
by the session assistant; the final reviewer in local replay is scripted.

The allocation closes at 79.574004 estimated credits and zero new API dollars,
without retries or unused calls. Luna uses 1.123814 credits, Sol 22.555440 and
Astra 55.894750. All meet the candidate floor; the predeclared tie policy favors
Luna's cost provisionally. Sol's lower median native latency in this small sample
does not establish a dependable speed ranking. Equivalent optional source
rewrites are not promoted into functional defects. All 12,879 earlier receipt
files remain unchanged. [Results](../../plan-build-repair-model-results.md).

Carry Luna into the next proposed connected repair/native-review qualification.
Do not change production routing or infer general reliability. The previous
two-call proposal remains superseded. Any new paid execution needs a concrete
allocation; unused credit headroom is not transferred. Tasks 1–7 remain accepted,
Task 8 stays open, and release remains outside this comparison.

## D30 — Increase evidence for Luna versus Sol; Astra grades

Patrick selected C after “redo,” authorizing preparation of another trial. He
then questioned the small call count, directed that Astra not compete for the
worker slot, and assigned grading to Astra. His “go” continues local preparation.
The 54-call design uses nine cases and three attempts per candidate. Three are
retained anchors, three new cases each have one defect, and three contain paired
defects. Astra performs semantic review in this active session; no separate
native grader call is proposed and neither worker grades itself.

Nine reference repairs pass all eight checks and preservation controls; all six
partial repairs fail actual tests. The offline transport rehearsal covers all
54 slots and only Luna/Sol, with zero paid calls. Full logs are retained after
bounding model-facing excerpts to the existing intent-context limit. No product
limit, protected oracle or original result was weakened.

Propose 90–180 new estimated worker credits and a 200-credit planning ceiling,
with zero new API dollars. Ordinary session review usage is outside that ledger.
The new concrete spend amount still needs the required decision; previous
allowances are closed. Patrick's latency question also calls for case-level
paired timing rather than declaring a winner from the first small median.
No complete native journey, Task 8 acceptance, production routing or release is
included. [Prepared proposal](../../plan-build-repair-contenders-preparation.md).

## D31 — Close the expanded worker comparison and retain the pilot evidence

Patrick approved D30's concrete allocation with “run.” All 54 original worker
calls completed before the session usage interruption. Sol passes 27/27 and
Luna 23/27; only Sol meets the frozen candidate floor. The allocation closes
at 90.296895 estimated worker credits, zero new API dollars and no retries.
Session Astra grading is outside that worker ledger and is neither independent
nor blinded. Four Luna failures remain failed, including an unrelated behavior
regression that the eight tests missed. No original reply or grade was repaired.

Patrick explicitly requested integration of the side pilot. Its eight calls
pass four new short cases per model and cost a separate 7.158747 credits. The
argparse-import selector costs more than always choosing Luna without improving
observed quality. Retain the narrower Luna opportunity, but do not adopt this
rule or pool the pilot with the main screen. The main-screen shadow selection
is retrospective and does not measure deployed routing or retry economics.

Closeout independently checks the saved response/usage/grade chain, aggregates,
13,678 earlier receipt hashes and all 276 retained pilot-file hashes. The task
outline and executable plan now reflect the completed run; Tasks 1–7 remain
accepted and Task 8 remains open. See [results](../../plan-build-repair-contenders-results.md)
and [closeout evidence](../../receipts/plan-build-repair-contenders-native-2026-09-18/closeout-verification.json).

Sol is the candidate for a newly prepared connected repair/retest/resume trial
with Astra providing native final review through the existing Spec gate. This
recommendation grants no new worker allocation, Task 8 acceptance, production
routing or release. Prepare its packet and estimate before additional paid
execution; the closed allocations' credit headroom is not transferred. The
[filter opportunities](../../plan-build-routing-filter-opportunities.md) remain
evidence-backed hypotheses for later qualification.

## D32 — Prepare a narrow direct-routing experiment

Patrick asked whether Python could identify repairs for Luna and send the rest
directly to Sol, then said “run” after the recommendation to test a narrow
eligibility rule on new source cases. This explicitly selects filter validation
next, changing the earlier proposed order of connected-journey qualification.
The connected native journey remains open; no production route is installed.

The new packet contains eight synthetic cases in four behavior families, with
two repetitions per worker: 32 calls, 16 Luna and 16 Sol. A predeclared structural
rule picks four isolated-function cases for Luna and four cases with additional
preservation burden for Sol; missing required evidence blocks both. Native
outcomes cannot influence these assignments. The threshold is provisional.

Local checks pass: 25 classifier/control tests; eight real reference repairs;
eight unfixed, eight interface-regression and four unrelated-behavior negatives;
32 injected transport slots and one wrapper-to-actual-check replay. No model
calls ran. Two local rehearsal defects and their corrections remain recorded.
Source sizes and synthetic/matched-case limits are disclosed in the
[prepared decision](../../plan-build-routing-eligibility-preparation.md).

Propose 50–105 new estimated worker credits with a 120-credit planning ceiling
and zero new API dollars. Session Astra grading remains outside that ledger.
Patrick's “run” authorizes preparation and the intended experiment; it preceded
this concrete cost estimate. The existing pre-spend requirement therefore still
needs its amount-specific decision. Earlier allocations remain closed and no
credit headroom transfers. Task 8 remains unaccepted.

## D33 — Broaden the evidence after a passing pilot

Patrick agreed to a bounded follow-up if the narrow eligibility pilot passes.
Use new, realistic repairs across different modules, including larger files and
difficult preservation cases. Measure both failures among Luna-selected work
and unnecessary Sol selections. More repetitions of the same eight related
cases are not the primary next evidence. A limited rollout with acceptance
checks and recorded failures may be considered after that broader evaluation;
it is not an automatic consequence of a passing pilot.

Set the follow-up's budget and stopping rule before execution. No large or
open-ended campaign is committed. This agreement settles the evaluation
strategy; the current 32-call pilot's concrete spend question remains pending,
and no follow-up allocation is granted here.

## D34 — Approve and execute the prepared routing pilot

After the concrete 32-call estimate and clarification of the pending 120-credit
planning ceiling, Patrick said “go.” This approves sixteen Luna and sixteen Sol
calls, expected 50–105 worker credits, under the separate 120-credit planning
ceiling and zero new API dollars. Session Astra grading is additional and outside
the worker ledger. It does not allocate the broader follow-up described in D33.

The frozen packet and installed source bindings pass admission. Existing ChatGPT
authentication is confirmed, and the no-model host startup check passes before
dispatch. The separate allocation and original outputs are retained under
`docs/receipts/plan-build-routing-eligibility-native-2026-09-18/`. No original
case, classifier, scoring requirement or prior receipt is changed for execution.
Task 8 remains open; current execution does not activate a production router.

## D35 — Close the routing pilot; retain the narrow Luna opportunity

All 32 authorized original calls completed with known usage and no retries.
Luna passes 16/16 at 1.744678 estimated credits; Sol passes 15/16 at 33.626240.
The actual allocation closes at 35.370918 against its 120-credit planning ceiling,
with zero new API dollars. Session grading remains outside this worker ledger.
Original grades were frozen before aggregate analysis; 15,279 earlier receipt
hashes remain unchanged. See [results](../../plan-build-routing-eligibility-results.md).

The predeclared classifier's eight Luna selections pass, but its total selected
set passes 15/16 because the original Sol `ne11` contains malformed JSON escaping.
The host rejects it before effects or tests. Its cost and failure remain counted;
the later predeclared repetition is not a retry or replacement grade. The policy
saves 46.4% against always-Sol but fails its all-selected-replies-pass floor.
All eight Sol-assigned positions also have passing Luna replies. No production
router or broader paid campaign is qualified by this outcome.

Patrick asked about tightening, then cost and speed, then leaned toward Luna and
asked for pushback. The recommendation is to carry Luna forward as the preferred
candidate for small, bounded repairs: in this pilot it costs about one nineteenth
as much as Sol, with a roughly two-second slower median response. Do not infer
universal Luna reliability from this small synthetic sample. The earlier 23/27
Luna result, including an unrelated regression missed by eight green tests,
remains unchanged and relevant to larger modules.

Tightening eligibility to send more work to Sol has no demonstrated quality gain
here and would not target the observed encoding failure. Diagnose that interface
failure locally before another native allocation; realistic larger/preservation
cases remain necessary before expanding Luna's scope. This is an assistant
recommendation in response to Patrick's lean, not a recorded production-adoption
decision or new paid authorization. Its cost is leaving some possible Luna savings
unrealized while broader reliability is unresolved. D33's passing-pilot condition
was not met. Tasks 1–7 remain accepted and Task 8 remains open.

## D36 — Approve broader Luna-only validation

After leaning toward Luna, Patrick asked the cost to test it. The concrete
proposal was twenty realistic repairs with two attempts each: forty Luna calls,
10–20 estimated worker credits and a separate 30-credit planning ceiling,
excluding ordinary session grading. Patrick said “ok” then “go,” approving that
single salient allocation. This is a new direction and approval, not an automatic
trigger from the failed D35 policy floor or a transfer of earlier headroom.

The locally prepared cases seed defects in twelve complete real Harness modules,
6,870–14,093 bytes, with seven two-defect scenarios. These are controlled mutations,
not twenty discovered product bugs. All twenty intact/reference cases pass; twenty
unfixed, twenty unrelated-code and twenty interface negatives are rejected.
The forty-slot injected transport rehearsal and one wrapper-to-check replay pass
with zero provider calls. Cases, source/dependency bindings, checks, order and
40/40 candidate floor are frozen before native execution.

Use only Luna, high reasoning, Standard service and existing ChatGPT authentication,
with no retries, new API dollars or paid native reviewer. Astra inspects originals
in-session, neither independently nor blinded. Record known ordinary failures and
continue independent slots; stop on unknown usage/dispatch, source drift, host
enforcement/authentication failure or exhausted allowance. The approved run is
executing under its separate ledger. No production route or Task 8 acceptance is
included. See [design](luna-broader-experiment.md) and
[approved scope](../../receipts/plan-build-luna-broader-native-2026-09-18/approval-scope.json).

## D37 — Queue a separate function-body replay after closing the current trial

Patrick explicitly instructed: “After closing the current trial, run a separate,
zero-model-call replay using function-body-only replacements. Preserve every
original grade. Verify that it prevents unrelated edits while still detecting
the within-function logic failure.” Complete and close the current approved
native trial first, then execute this local replay as a separate experiment.
This authorizes no additional model call, production change or regrade. Preserve
the native originals and verify their hashes before and after the replay. Test
both unrelated-edit prevention and detection of the known decision-ordering
regression inside the target function; report transformed-replay outcomes
separately from original worker outcomes.


## D38 — Stop and close broader trial on reference leakage

A midpoint evidence audit found an inherited protected documentation module in
model-visible source evidence, byte-identical to the complete correct reference
for markdown-escape and public-symbols. This violates the frozen evidence-isolation
requirement and is a preparation/control defect. Finish the already in-flight
lb21 to account for usage, then stop; do not alter inputs or substitute calls.
All twenty cases were audited for exact file/named-function AST duplication.
Only these two matched; no broader absence-of-leakage claim is made.

The allocation closes after 21/40 calls, 12 original passes, 9 failures and
7.043789 estimated worker credits. Nineteen slots remain unused. Original lb17
and lb19 pass grades are preserved, with contamination recorded separately.
No retry, new API spending or native reviewer occurred. The frozen 40/40 floor
is unmet and clean qualification invalid. All 16,944 earlier receipt hashes
verify unchanged. See [results](../../plan-build-luna-broader-results.md).
Proceed with D37's separately authorized local body-only replay after closeout;
no extra paid call, production route or Task 8 acceptance is authorized.


## D39 — Verify the separate function-body replay without regrading

After D38 closeout, D37's authorized local replay completed with zero model calls,
zero additional worker credits and zero new API dollars. A prototype uses trusted
host path/symbol/source-hash bindings and replaces only the accepted function body;
all surrounding bytes and the interface remain fixed. Twenty reference repairs,
twenty dedented-code rejection controls, twenty stale-source rejection controls
and twelve boundary unit tests pass. The installed local path executes 300
supplemental/protected test cases, with no native reviewer.

The lb07 projection retains its correct target repair and prevents the unrelated
renderer change. Removing the body boundary reproduces that regression. The lb02
projection retains its logic bug, and replay-only exit-code 2/4 checks make the
actual protected probe fail with needs_revision. Removing those post-hoc checks
reproduces eight green original tests, showing that body restriction alone cannot
establish semantic correctness. Original fixtures and grades remain untouched.

Sixteen original replies produce evaluated body projections: fourteen pass and
two fail. An unchanged body is rejected; three malformed JSON replies and one
invalid Python reply are skipped without repair. The lb12 projected body passes
with trusted host binding; its original wrong-hash envelope remains failed.
Every original grade and all 17,216 prior receipt hashes verify unchanged.
These are local transformation outcomes, not new native grades or reliability,
cost or speed evidence. The original reference contamination remains. No
production code/route changed; Task 8 stays open. See
[body replay results](../../plan-build-function-body-replay-results.md).
