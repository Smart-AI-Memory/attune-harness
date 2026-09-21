# Engineering opportunity log

Keep opportunities visible without automatically adding them to the active spec.
The current register separates open work, completed improvements, experiments and
release follow-through. Dated notes below retain the evidence and reasoning;
their former next steps are not automatically current assignments.

Last reviewed: **September 18, 2026**, against current source and retained results.
Patrick selected **A — better status and next-action guidance** and **B — durable
decisions** as the affordable scope (estimated 25–40k working tokens together).
**A and B are implemented and verified in the current CLI/Spec source**; see
[A's receipt](status-guidance-a-results.md) and [B's receipt](durable-decisions-b-results.md). The
remaining groups are deferred for the October 1 review below. This work does not
upgrade the active plugin or change the original experiment grades.

## Recommended order

“Low hanging fruit” means a bounded change with a direct user benefit. Effort is
an engineering estimate from inspection, not a measured schedule: **small** fits
an existing presentation or check; **medium** crosses saved state or execution
interfaces; **larger** includes wider integration or live qualification.

| Group | Opportunity and user benefit | Bounded next step / done when | Effort |
|---|---|---|---|
| **A — Clearer guidance: verified locally** | O-16, O-17, O-36. Explain what happened, whether it blocks progress and what to do next. | Implemented in plan/build/status/resume JSON: summaries, blocking indicators, evidence pointers and state-appropriate actions. Stale/uncertain work suppresses ordinary progression; required failures and optional advice remain distinct. [Verification](status-guidance-a-results.md). | This first surface is complete; broader consistency and rollout remain separate. |
| **B — Keep decisions readable: verified locally** | O-01, O-36. A disappearing form should not erase the question or available choices. | The existing Spec renderer is retained before collection; plan questions and explicit `plan --decision` previews persist beside the owner. Read-only status exposes current/historical text. Delayed answers remain bound; replaced, stale and consumed replies cannot grant acceptance. [Verification](durable-decisions-b-results.md). | The local plan/Spec surface is complete; native form lifetime and rollout remain separate. |
| **C — Protect the next experiment** | O-14, O-15, O-23, O-31. Avoid paying for a trial whose inputs invalidate its results. | Reuse retained controls and startup checks; add a pre-dispatch check for leaked reference answers across all model-visible inputs. Demonstrate rejection of the known contaminated fixture. | **Small–medium**, offline first; most urgent before another paid trial. |
| **D — Carry review findings forward** | O-28. The builder should receive relevant findings without the user repeating them. | Carry finding IDs, evidence and their accepted disposition into the worker request, bound to the current revision. Keep optional advice distinct from requirements. | **Medium**; saved planning state and build handoff both change. |
| **E — Integrate the demonstrated edit control** | O-34, O-35. Preserve unrelated code while repairing a selected function. | Integrate the body-only prototype into the existing effect owner for its supported source profile; retain behavioral checks for wrong logic inside the function and compatibility with saved work. | **Medium–larger**; local benefit is demonstrated, production integration and fresh model reliability remain open. |
| **F — Make evidence easier to inspect** | O-09, O-16. Reduce reconstruction of what ran and what it checked. | Add only missing executor-input references and runtime origins to existing receipts; present actual check results separately from model judgments. Reuse metadata already recorded by the testing path. | **Small–medium**, after confirming the exact missing fields. |

**Recommendation:** A and B's first surfaces are complete. Scope C separately
before another paid experiment; then prioritize D and E for stronger handoffs
and repair boundaries. A was the smallest useful step; C is the urgent pre-trial
step. No new trial is allocated by this ordering.

For A, the [warning and guidance examples](user-guidance-examples.md) now separate
the implemented CLI fields from proposed UI wording. The
[plan/build presentation](../src/attune_harness/work_cli.py) follows the existing
testing convention of outcome, next action and saved evidence. The reproduced
stale-draft acceptance suggestion is repaired, including stale proposals and
built work. Required failures, optional advice, uncertain effects, rejected saved
replies and completed outcomes have local regressions. Execution authority,
dispatch, recovery and exit-code contracts are preserved. The
[design note](design-status-guidance-a.md) records the baseline probes.

### Other logical groups

- **Measure waiting time before optimizing:** O-11 and O-27 separate model time,
  local processing and the delay before the user sees a result. O-20 adds startup
  and provider-turn attribution. O-06 considers earlier quality checks, including
  their runtime cost. One timing receipt does not establish the cause of delay.
  The [Voyage validation-reuse plan](specs/voyage-validation-reuse/tasks.md) remains
  its own work; this review does not activate it.
- **Release and complete journeys:** O-03, O-04, O-07, O-08, O-10 and O-12 cover
  live memory delegation, connected capabilities, supported installations,
  rollout of the verified Spec summary repair and remaining specialist backends.
  These are valuable integration work, not small copy changes. Plan/build Tasks
  1–7 are accepted; native Task 8 remains open.
- **Keep deferred work visible:** O-02 access separation remains explicitly
  deferred. O-05 packaging cleanup has lower immediate user value. O-36's blog
  and examples await Patrick's content approval before website integration.
  Prompt enhancement has a reported clarity benefit; effects on rework and
  technical debt still need evidence. This is not an automatic cleanup feature.

## Deferred review — October 1, 2026

Patrick wants to revisit all remaining opportunity groups when budget allows.
Review this list on October 1; refresh status from the current register before
recommending work. The reminder is for review, not automatic implementation or
paid experiments. A and B remain the selected scope. Token estimates below cover
implementation, focused verification and documentation, excluding fresh paid
model trials; they are planning estimates, not metered billable totals.

**Budget decision, September 18:** release and complete-journey work is deferred
until Patrick receives his October allotment. At his request, the reminder moves
from September 25 to **October 1 at 9 a.m. Eastern**. The
[October plan](october-release-plan.md) proposes **270k additional working tokens**:
225k planned work plus 45k for rework, including C before fresh native trials.
This is a planning allocation, not measured usage or an exact completion forecast.
A/B and paid worker-call costs are separate. The reminder reviews the plan and
backlog; it does not automatically start work. A and B remain the selected scope.

| Deferred group | Complete remaining scope | Earlier token estimate |
|---|---|---|
| **C — Experiment safeguards** | O-14, O-15, O-23, O-31: verify reference delivery, reject leaked answers, preserve grader context, reuse known bad cases and check launcher access. Reuse completed checks; add the missing pre-dispatch protection before another paid trial. | 15–25k |
| **D — Review-to-builder handoff** | O-28: carry relevant findings, evidence and accepted dispositions into the current worker request without turning advice into requirements. | 25–40k |
| **E — Function-body controls** | O-34, O-35: integrate the demonstrated edit boundary and retain checks for wrong logic inside the function. Qualify the supported source profile and existing saved-work compatibility. | 35–60k |
| **F — Easier evidence inspection** | O-09, O-16: fill missing executor-input/runtime references in existing receipts and distinguish actual verification from model judgments. Coordinate with A so presentation work is not repeated. | Not yet estimated |
| **Performance and process** | O-06, O-11, O-20, O-27: assess earlier quality checks, profile local waiting time, separate startup/provider turns from model time, and measure when findings reach the user. Revisit the separate Voyage validation-reuse plan if still relevant. | Not yet estimated |
| **Release and complete journeys** | O-03, O-04, O-07, O-08, O-10, O-12: live memory delegation, current capability maps, installation/platform coverage, optional Spec-owner availability, rollout of the verified summary repair, specialist testing backends and connected assessment/repair/test/Spec execution. Include O-13's shared evidence validation, O-26's genuinely new steering case and O-30's remaining native completion evidence. | 140–265k base; 175–330k with contingency. Deferred until October allotment. |
| **Previously deferred work and public content** | O-02: ownership/relevance/sharing separation. O-05: Attune AI packaging metadata. O-36 beyond A/B: review the blog and guidance, integrate them into smartaimemory.com after content approval, and assess prompt clarity, rework and technical-debt effects without claiming unmeasured savings. | Not yet estimated |

Keep completed work as a reusable baseline: O-18's host bindings, O-19's actual
entry-point checks, O-21's supplied hashes, O-24's runner correction, O-25's
response guidance, O-29's compatibility oracle and O-32's readable rejected
replies. O-22 and O-33 retain closed model comparisons and their limits; they
are not outstanding allocations. Completed portions of other entries likewise
stay completed. Together with A and B, this accounts for all O-01–O-36 without
turning historical lessons into duplicate tasks.

## Current register

“Verified locally” describes the recorded source/installed checks or replay. It
does not mean the active plugin was upgraded, the feature was published, or a
complete native journey passed. Original experimental grades remain unchanged.

| ID | Opportunity | Current position and remaining action |
|---|---|---|
| O-01 | Durable decisions and form visibility | **B verified locally.** [Plan/Spec text now persists before collection](durable-decisions-b-results.md), and delayed/replaced/stale response behavior is checked. The [UI probe](research/form-visibility-2026-09-17.md) identified display limits; the original disappearance incident remains unreproduced and the host timer is unchanged. |
| O-02 | Ownership, relevance and sharing authority | **Deferred by Patrick.** Project matching ranks memories; it does not establish sharing permission. Retain the [access questions](specs/shared-memory-adoption/design.md). |
| O-03 | Active memory delegation | **Future live qualification.** [Citation evidence](research/memory-citations-results-2026-09-16.md) supports a candidate. Define one complete receiving-agent journey before live activation. |
| O-04 | Map capabilities to complete journeys | **Map and testing slice completed; current-state refresh needed.** [Connected testing](connected-journey-qualification-results.md) and [plan/build Tasks 1–7](plan-build-task7-results.md) now exist. Older maps still describe plan/build as absent. Native completion remains open. |
| O-05 | Attune AI packaging metadata warnings | **Open; low priority.** License-table metadata remains in Attune AI. Make a bounded packaging compatibility cleanup when that package is next maintained. |
| O-06 | Earlier repository quality checks | **Open process improvement.** Evaluate the existing full gates in the relevant preflight mode and measure added waiting time before changing the default. |
| O-07 | Fresh installation and platform coverage | **Partly qualified.** The [fresh macOS/Python 3.12 combination](fresh-installation-results.md) passes. Other intended combined profiles and optional Spec-owner availability remain open. Earlier core platform checks do not qualify every newer integration. |
| O-08 | Accurate Spec completion summaries | **Candidate repair verified; rollout remains.** [Accepted task evidence now survives resume](spec-completion-repair-results.md). The active installed plugin was not replaced by that qualification. |
| O-09 | Complete evidence of what ran | **Open; F.** [Closeout](release-readiness-follow-through-results.md) required transcript/runtime reconstruction. Add missing input references and origins to existing receipts, without duplicating current test metadata. |
| O-10 | Reliable specialist testing backends | **Testing journey implemented; legacy backend work remains.** [Selection, execution and receipts](test-this-change-results.md) are connected. Maintenance placeholders, generation/write contracts, generic verifier behavior and aliases need their own bounded repairs. |
| O-11 | Reduce local waiting time | **Measured once; cause unresolved.** [Installed case](receipts/test-this-change-implementation/installed-spec-journey.json): preview 6.72s, execution 9.31s, status 1.02s, resume 1.72s. Profile inventory, hashing and freshness checks before caching. |
| O-12 | Coherent assessment, repair, test and Spec handoffs | **Several improvements realized; integration remains.** [Stale decision acceptance repaired](spec-test-handoff-results.md); [local plan/build complete through Task 7](plan-build-task7-results.md). Assessment-to-repair automation and native end-to-end completion remain open. |
| O-13 | Validate terminal evidence consistently | **Observed contradictions fixed.** [Handoff checks](receipts/connected-journey-qualification/connected-journey-implementation-review.json) reject the known inconsistencies. Consolidate validation with its owner when adding another consumer. |
| O-14 | Verify reference delivery and trial inputs | **Delivery check added to the assessment experiment; C remains.** [Original retrieval gap](specs/connected-journey-qualification/assessment-quality-design.md) and later [answer leakage](plan-build-luna-broader-results.md) are different problems. Check both; delivered evidence alone does not prove clean inputs. |
| O-15 | Give graders the evidence they need | **Bounded experiment corrected.** [Eleven initial grades](specs/connected-journey-qualification/assessment-quality-design.md#grading-only-correction-during-execution) remain retained and excluded. Reuse the corrected evidence projection in C. |
| O-16 | Separate actual checks from model claims | **A verified locally; F remains.** [CLI evidence](status-guidance-a-results.md) distinguishes protected checks, attributed reviewer findings and optional advice. Passing checks are not universal semantic proof. Broader evidence-origin work remains F. |
| O-17 | Concise results with complete findings | **A's plan/build surface verified locally.** Concise summaries link to full saved checks/replies, retaining complete findings. [Verification](status-guidance-a-results.md); broader surfaces and rollout remain separate. |
| O-18 | Host-owned step/control metadata | **Implemented and confirmed.** [Contract correction](plan-build-contract-correction-results.md) plus [12/12 contract-valid replies](plan-build-contract-confirmation-results.md). Contract validity does not establish complete native success. |
| O-19 | Test actual entry points | **Retained testing lesson.** [Native artifacts](plan-build-native-results.md) exposed CLI failures missed by direct serializer checks. Keep CLI controls; Task 7 also repaired ownership of subprocess diagnostic streams. |
| O-20 | Routine choices and startup overhead | **Planning guidance corrected; transport work open.** [All six confirmation planners](plan-build-contract-confirmation-results.md) stage within the supported profile. Startup isolation and turn accounting remain unqualified for latency comparisons. |
| O-21 | Supply source hashes instead of asking models to infer them | **Implemented.** [Version 2](plan-build-contract-correction-results.md) supplies exact paths and hashes, checked by the host. The body-only prototype further removes copying from the model's responsibilities. |
| O-22 | Evaluate lower-cost workers | **Evidence incorporated into later comparisons.** [Narrow confirmation](plan-build-contract-confirmation-results.md) supported Luna as a candidate; O-33 holds the later results. No separate unused experiment remains here. |
| O-23 | Reuse known bad artifacts as review controls | **Four connected controls passed.** [Results](plan-build-connected-results.md) retain wrong-plan/CLI cases. Reuse these fixtures in C; their success does not qualify the whole journey. |
| O-24 | Make test runners select the intended source | **Local correction verified.** [Corrected import setup](plan-build-handoff-correction-results.md) passes source/installed checks and detects four removed guards. Preserve the original native failure. |
| O-25 | Distinguish a missing field from an empty answer | **Guidance corrected.** [The handoff correction](plan-build-handoff-correction-results.md) clarifies `choices: []`; strict rejection of an omitted required field remains. Later responses exercised the corrected contract. |
| O-26 | Demonstrate adaptation to genuinely new intent | **Open qualification case.** [Earlier steering](plan-build-connected-results.md) repeated a requirement already in the plan. Use a materially new bounded requirement when this journey is next qualified. |
| O-27 | Measure the delay before findings reach the user | **Open measurement work.** [Connected timing](plan-build-connected-results.md) separates a 19.67s response from a combined grade at 298.46s. Record actual presentation timing before attributing the gap. |
| O-28 | Pass planning findings to the builder | **Open; D.** [Worker request construction](../src/attune_harness/work_build.py) supplies intent, step, source and checks, but no planning critique/disposition. Bind any added handoff to the current accepted revision. |
| O-29 | Protect existing output behavior | **Experimental oracle corrected.** [Captured pre-change output](plan-build-default-compatibility-results.md) catches the punctuation regression; the original failure stays failed. Keep that independent expectation in later cases. |
| O-30 | Repair, retest and resume failed work | **Local recovery verified.** [Installed replay](plan-build-repair-resume-results.md) preserves completed work and repairs the failed assertion. Native final review and completed connected handoff remain unqualified. |
| O-31 | Check native launcher access before dispatch | **No-model startup check implemented.** [Initialization evidence](plan-build-repair-native-results.md) supports reusing it in C. An unresolved attempt with no usage report must not be labeled zero-cost. |
| O-32 | Keep rejected replies inspectable | **Locally repaired.** [Readable failed records](plan-build-repair-feedback-results.md) preserve rejection, prevent effects and resume without repeating a call. No need to reopen this defect without new evidence. |
| O-33 | Compare models before choosing a route | **Trials closed; no production route qualified.** [Expanded screen](plan-build-repair-contenders-results.md), [routing pilot](plan-build-routing-eligibility-results.md) and [stopped broader trial](plan-build-luna-broader-results.md) retain different results and limits. No automatic Luna/Sol filter route follows. |
| O-34 | Reduce unnecessary replacement content | **Local opportunity realized; E.** [Body-only replay](plan-build-function-body-replay-results.md) preserves surrounding code. Fresh response cost and speed gains remain unmeasured. |
| O-35 | Catch unrelated edits and wrong logic | **Local opportunity realized; E.** The [same replay](plan-build-function-body-replay-results.md) prevents the observed unrelated edit; separate behavioral checks reject wrong logic inside the function. Both protections are necessary. |
| O-36 | Useful guidance, prompt clarity and public explanation | **A/B verified locally.** [Guidance](user-guidance-examples.md) separates current CLI/Spec support from proposed UI wording. [Blog](blog/controls-savings-user-journey.md) and public examples still await content approval before [website integration](handoffs/smartaimemory-controls-article.md). Prompt clarity is reported; downstream debt savings remain unmeasured. |

## Maintenance

Patrick directed that this log and associated content be included in every full
review of documentation for content maintenance. Follow the
[documentation maintenance checklist](documentation-maintenance.md): reconcile
current status with code and evidence, refresh linked summaries and examples,
retain historical grades, and check publication status. Update the review date
only for the material actually checked. This sweep did not audit every document.

The completed September 15 opportunities retain their separate
[design](design-opportunities.md) and [implementation report](opportunities-implementation-report.md);
their numbering is independent of O-01–O-36.

## Dated evidence and follow-through

These notes explain how the opportunities developed. Read the current register
above for today's position. Five Task 6–8 reflection labels originally reused
O-13–O-17; they now point to the matching opportunity, with the old label retained
in parentheses. No experiment grade or receipt was changed.

O-12 follow-through, 2026-09-17: the [memory documentation journey](memory-documentation-journey.md)
reproduces a concrete acceptance blocker. After a Spec form is rendered, a source
change correctly invalidates Harness test evidence, but the unchanged Spec form
still accepts. Current-evidence validation is needed when the decision is consumed,
not only before publication. The negative receipt is retained; a bounded correction
needs expansion of this slice's documentation-only repair scope. No paid calls or
new gate subsystem are authorized by this entry.

O-12 correction, 2026-09-17: Patrick approved option A. The [bounded Spec
handoff repair](spec-test-handoff-results.md) now binds the test owner's record,
checks freshness on publication and every completion path, and preserves accepted
history. Source and installed qualification plus removal-of-guard tests pass.
Assessment→repair and automatic executor wiring remain opportunities; this closes
the demonstrated stale-decision defect, not the whole plan/build integration.

Related qualification lesson: nominally read-only Git inventory refreshed the
index and invalidated producing repair evidence. The same bounded repair disables
that refresh and distinguishes timestamp hints from actual captured bytes. Keep
inspection side effects in the O-11 latency investigation; do not add caching or
a new control system without measuring the existing path first.

Priority steering, 2026-09-17: Patrick is leaning toward publishing Harness and
deprecating Attune AI as soon as readiness supports it. Documented Harness release
blockers outrank optional shared enhancements; shared value precedes AI-only
enhancements. See [release direction](harness-release-readiness-direction.md).
This is neither a retirement deadline nor publication authorization.

O-12 plan/build follow-through, 2026-09-18: after the handoff correction closed,
Patrick directed continuation of the existing draft. [Task 1 preparation](plan-build-task1-results.md)
now fixes a JSONL export feature in a captured existing-code subtree and the exact
integration seams. Probes show the legacy task reader silently ignores unknown
XML and yields no tasks for non-plan content. The planned optional import bridge
must retain/disclose unsupported information and reject empty execution, while
preserving the existing parser. Native roles also require explicit operation
mapping. These are requirements within the existing ladder, not new side features.

Reflection checkpoints should update an existing entry when evidence changes,
record a newly discovered opportunity when warranted, or close one with a reason.
Capture does not approve implementation, create a reminder or change task gates.

O-12 Task 2 reflection, 2026-09-18: the new shared contract separates declaration,
control availability, decision authority and execution evidence. A host's supported
control list is not a receipt that the control ran. Keep that distinction in the
Task 4 runtime. Task 6 also needs an explicit plan-content identity: the existing
Spec owner saves acceptance in an HTML state comment inside the plan, so hashing
the entire mutable plan as both input and approval storage would invalidate itself.
The current generic artifact capture intentionally binds exact bytes; the bridge
must qualify a canonical executable-content projection and retain the original
artifact identity, without ignoring material edits. This is a bounded integration
opportunity within the accepted ladder, not another approval system.

O-12 Task 3 reflection, 2026-09-18: a current proposal must not silently become
a fresh one because the generic revision API refreshes source/configuration.
The staging path now requires unchanged inputs inside the revision owner; a
negative race test and guard-removal probe detect regression. Native planning
also lets the host bind control metadata while the participant returns substance,
building on the earlier memory-worker interface findings. Actual native planning
competence and semantic fidelity remain the Task 8 qualification boundary.

O-12 Task 4 reflection, 2026-09-18: creation needs its own failure policy. An
exclusive create prevents overwriting a collision but can leave partial bytes
after a crash. Task 4 journals that uncertainty and requires explicit observation;
it never equates a visible file with a durable success or deletes ambiguous
content. The broader Task 6 intervention path should explain partial-file and
interrupted-control evidence clearly and offer a bounded recovery decision. It
must not turn “retry” into permission to erase an unexplained file. Full power-loss
and concurrent-writer qualification remain separate from process-death tests.

Task 4 test reflection: a scope-removal mutant initially survived because the
chosen unsafe input also violated a separate preimage guard. Use an independent
valid-looking out-of-scope creation when testing the scope boundary. The corrected
case detects that guard removal. Passing negative tests alone did not establish
that the intended guard was carrying the protection.

O-12 Task 5 reflection, 2026-09-18: retain two distinct judgments in the result.
The protected feature check rejects a wrong implementation even when its generated
test passes through the actual pytest route. A completed effect, a successful
generated test, a reviewer opinion and human acceptance are different evidence.
The existing test handoff now derives scope from a completed dependent build and
rechecks its producer; it must not turn a stale passing test into fresh authority.

O-12 Task 6 reflection (formerly labeled O-13), 2026-09-18: bind executable intent separately from mutable
Spec progress. Import now retains the original file hash and canonical content,
while excluding only the trailing Spec-owned state comment from the planning
freshness hash. Keep the stricter effect snapshot until coordinated state writes
have their own qualification; broad hash exclusions would hide material drift.

O-12 Task 6 guard trials (formerly labeled O-14): isolate the earliest authority check and the exact
verified-step boundary. An integration test can still reject a bad action after
a guard is removed, hiding that guard's absence. Retain both the direct negative
and complete journey checks. The first 3/5 detection result is preserved beside
the repaired 5/5 result.

O-07 Task 7 reflection (formerly labeled O-15), 2026-09-18: qualify dependency packaging as part of the
journey. An installed Harness wheel using a candidate Spec source path is useful
integration evidence but does not prove the complete installed route. Task 7
therefore builds the optional owner as an isolated wheel and runs the actual
console script outside both repositories. Standalone Harness release still needs
an explicit decision on packaging/availability of that optional Spec owner.

O-19 Task 7 testing opportunity (formerly labeled O-16): own subprocess diagnostic streams explicitly.
The MCP SDK default stderr retained an import-time pytest capture object, making
the existing transport test order-dependent. A real owned test log removes that
accidental dependency while preserving the actual transport and memory checks.

O-23 Task 8 preparation (formerly labeled O-17), 2026-09-18: retain an explicitly wrong but structurally
valid plan as a semantic scoring control. It can copy the corrected goal and
criteria while proposing to discard unknown/refuted findings. The host correctly
validates structure, not meaning. This observed boundary supports evaluating native
planning outcomes independently of schema success; it does not call for another
router or a keyword-based semantic gate. The wrong serializer also fails the
protected oracle while a trivial generated test passes.

O-18 Task 8 native comparison, 2026-09-18: move copied control metadata out of
model reasoning. All 12 plans failed an unstated exact-text duplication check;
11 workers confused the outer work ID with the accepted step ID. Source-preserving
diagnostics recovered structural validity for 11 plans and passed the actual
oracle for nine worker sources. Original failures remain failures. Bounded next
step: repair host binding and role contracts, preserving wrong-goal, scope,
authority and stale-evidence negatives. This is Task 8 corrective work, not a
reason to add a stronger router. [Evidence](plan-build-native-results.md).
Status update: host step binding and criterion staging are implemented and locally
qualified in the [contract correction](plan-build-contract-correction-results.md).
The separately approved v2 confirmation now accepts 12/12 original replies.
Luna and Astra each pass all four planner/worker cases; connected native handoffs
remain unqualified. See [confirmation evidence](plan-build-contract-confirmation-results.md).

O-19 Task 8 artifact evidence: direct serializer tests passed three implementations
that failed the actual CLI. Two had an imported-class versus __main__ identity
trap; one duplicated findings in the header. Preserve the CLI in future protected
oracles and apply the same handoff check to adjacent journeys when scoped. The
defects are in disposable model proposals, not shipped exporter code.

O-20 Task 8 planning/transport boundary: routine alternatives became unanswered
human gates, and verification-only tasks exceeded the supported build profile.
Clarify which decisions require people and expose executable profile constraints
through role-specific grammar. Separately, unused native startup integrations,
skills truncation and provider-internal turns limit timing attribution. Qualify
per-child isolation and turn accounting before another paid latency comparison;
preserve the user's configured integrations. Both opportunities refine existing
owners rather than introduce commands or permanent committees.
Status update: role-specific guidance and executable planning constraints now
have local qualification. Startup isolation and provider-turn accounting remain
open; the proposed next role confirmation makes no comparative-latency claim.

Confirmation update: all six planners now stage within the ordered build profile
without unanswered routine choices. The remaining transport caveats were observed
again, so measured output durations still do not establish desktop latency.

O-21 Contract correction: models need supplied preimage digests for modified
files. The original build prompt supplied source text but expected SHA-256 without
hashing tools. Version 2 now includes each exact path and accepted preimage in
the reply template, independently rechecked by the host. Covered by actual
dependent-build and changed-preimage tests; native multi-step use remains part
of Task 8's connected-journey qualification.

O-22 Native confirmation: Luna's four clean planner/worker cases used an estimated
0.57568 Codex credits; Astra's four clean cases used 29.71750. This supports testing
Luna in the connected journey with stronger review and protected checks. Two
repetitions per role do not establish a reliability rate or justify removing
review. Stronger critic/reviewer roles still need actual outcome evidence.

O-23 Preserve known bad artifacts as review controls. Fable's fresh worker again
used a runtime class-identity check that passes direct serialization but fails
the CLI. A next reviewer trial can use that unchanged artifact to test whether
the reviewer identifies the handoff defect; the protected oracle remains required
even if the reviewer misses it. One planner also made a minor unsupported claim
about printing records. Keep factual qualification distinct from a functional
failure and from optional wording advice. Both controls can be prepared locally
without buying a replacement response merely to make the screen green.

O-24 Connected comparison, 2026-09-18: test setup belongs to the host runner.
The scripted supplemental tests imported the acceptance harness, whose import
side effect exposed checkout/src. Fresh Astra tests used ordinary package imports
and the frozen runner instead reached the installed package. All six unchanged
supplemental tests pass with the correct source path. Qualify the runner with
ordinary tests and a deliberate installed-package shadow; preserve the original
failed journey. This is an experimental handoff correction, not evidence that
the native implementation needs repair. [Evidence](plan-build-connected-results.md).

Qualification update: the protected fixture runner now selects checkout/src,
checks actual import origins, rejects empty discovery and propagates failure.
Source and installed replay routes pass; 4/4 guard removals are detected.
Fresh native completion remains a separate observation.

O-25 Connected comparison: distinguish an omitted response field from an empty
decision list. Luna preserved the goal but omitted required choices. Explain the
explicit empty-list form in the existing planner grammar and retain rejection of
missing/malformed decisions; do not silently infer that the user has no unresolved
choices. Inspect the actual structured-output boundary before considering a
stronger router. One original failure does not overturn earlier bounded success.

Qualification update: explicit empty-list guidance is implemented; strict
rejection and preservation of existing human choices are covered locally.
The first fresh planner reply includes `choices: []`; one success does not
establish a reliability rate. The connected confirmation is still in progress.

O-26 Connected comparison: the synthetic pending-task correction exercised actual
acceptance invalidation and preservation, but Astra's plan already included the
same reconstruction check. Retain that narrow success and use a materially new,
bounded pending requirement when qualifying adaptation to changed intent. Avoid
claiming novel human steering from a redundant assertion.

O-27 Connected comparison timing: the first upheld control finding returned in
19.67 seconds, but the durable combined grade was written 298.46 seconds after
the first request. Inspection/orchestration gaps matter alongside model runtime.
Record semantic-assessment and actual presentation timestamps separately in the
existing experiment evidence; do not invent desktop latency from transport or
renderer timing. No new runtime telemetry service is implied.

O-28 Fresh connected confirmation: carry assessed planning findings into the
existing build handoff. Astra identified a medium omission of the exact finding
record envelope in Luna's plan; the protected oracle already specified it, and
Luna's exporter implemented it correctly. The retained worker request does not
contain the critic finding identifier, and work_build.turn supplies intent,
step, source and probes without the planning critique. Preserve the original
experiment; investigate a bounded handoff that retains actionable findings and
their disposition without automatically rewriting an accepted plan or promoting
advisory wording into a blocking requirement. This observed success does not
qualify critique transfer when the finding is absent from the protected oracle.

O-29 Fresh confirmation: compatibility checks need an external pre-change
expectation. Luna's CLI changed default Markdown punctuation; the old protected
test compared the new CLI to the new markdown() implementation and passed.
Direct before/after output exposed the regression, stopping the trial at four
calls without consuming its last two. The local oracle now embeds normal and
empty-input stdout captured before worker effects, inside the existing protected
acceptance file. Six focused cases and removal of the equality guard establish
that this known false green is detected. This corrects the experimental oracle;
the original native failure is preserved. Retained passing Astra artifacts still
pass, and this success does not qualify a fresh native completion.

O-30 Fresh complete-journey trial: qualify repair/retest/resume using a real
generated-test failure. Planning, exporter and CLI succeed, including captured
default compatibility. A supplemental assertion indexes status on the outer
record instead of its nested finding; the actual runner fails and Harness stops
with needs_revision. Failed resume dispatches no extra call and incomplete
completion evidence is rejected. A separate one-line diagnostic correction passes
four supplemental and four protected checks without changing the original.
Use this retained failure to test bounded correction, authority invalidation,
preserved completed work and final review through existing owners. Do not treat
diagnostic success as native completion or restart whole journeys until green.

O-30 update, 2026-09-18: the local recovery qualification found that the existing
revision boundary refused settled failed-task probes. The bounded correction is
now qualified (351 source and 351 installed checks; 3/3 guard removals detected).
An installed replay retains the failure and repairs only the test under fresh
Spec authority, preserving exporter/CLI bytes and rejecting stale completion.
Native guided repair and final review remain separate proposed evidence; see
[the recovery result](plan-build-repair-resume-results.md).

O-31 Native trials should qualify the launcher before consuming an allocation.
The first guided-repair attempt failed during local Codex initialization because
the outer workspace sandbox blocked local state writes. An explicit host-access
initialize handshake succeeds without starting a model turn. Use that bounded
startup check before later allocations, preserving the participant's read-only
sandbox and the Harness effect owner. Do not infer zero billing from absent
usage, retry an unresolved journal, or add a permanent service for this check.

O-32 Rejected participant data must remain inspectable. The native repair returned
the faulty test unchanged; its rejection made the paused owner unreadable because
validation decoded the persisted raw reply again. The bounded correction now
retains terminal rejected replies as readable failures and resumes them without
another call, while preserving refusal of effects/completion and malformed host
metadata. It passes 362 source/installed checks and catches 3/3 guard removals.
The accepted experimental objective also now carries the observed failure rather
than asking generically to add tests. Native benefit remains unproven; avoid
repeated prompt changes around one case without a strategy review.

O-33 Compare models on fixed handoffs before changing routing. Patrick questioned
another Luna-only retry after the unchanged repair. The prepared screen uses one
retained guided failure and two new injected defects, equivalent case inputs,
two repetitions and actual preservation checks. It separates role-specific
repair evidence from earlier memory-sorter results. Measure cost/time including
failed attempts; a cheap response is not necessarily a cheap successful outcome.
A green-but-weakened-test control demonstrates why executable success and semantic
preservation must remain separate. This is a bounded experiment, not a new router
or a claim that a stronger model is better. [Prepared comparison](plan-build-repair-model-preparation.md).

O-34 Investigate response size as part of bounded repair latency. In the approved
repair-model screen, a one-value CLI default correction still returns the entire
source file. One Sol response also rewrites equivalent quotes, Unicode literals
and escape expressions, increasing inspection work without a demonstrated defect.
Log response bytes, model time and inspection/disposition time separately. A
future experiment could compare full-file proposals with a host-bound targeted
edit using the same preimage, scope, preservation and execution checks. This is
a hypothesis about possible savings, not a causal timing result or authorization
to add an edit protocol. Finish the fixed comparison and native journey first.

O-33/O-34 update, 2026-09-18: the completed screen passes 18/18. Luna remains the
provisional candidate on observed cost (1.123814 credits for six repairs versus
Sol 22.555440 and Astra 55.894750). Sol has the lower median native time; Luna has
the lower total. Preserve case-level results rather than claiming a stable speed
ranking. Full-file source replies span 631–9,685 bytes; actual local evaluation
averages about 1.25–1.28 seconds, while native responses take 17.4–99.4 seconds.
Inspection/scheduling and renderer latency are separate concerns; no causal
response-size result follows. [Results](plan-build-repair-model-results.md).

O-35 Expanded Luna/Sol trial: semantic preservation must cover behavior outside
the requested fix, even inside an allowed file. Luna's original ls04 reply fixes
the CLI default but replaces the async/sync declaration prefix with literal
`def`. All eight frozen tests pass; Astra's session inspection rejects the
unrelated behavior regression. A separate synthetic `api_claims` diagnostic
confirms the before/after difference without executing the sample declaration.
Consider adding async/static-signature compatibility coverage after this frozen
comparison. Preserve the original failed grade and frozen oracles; the new
diagnostic is supporting evidence, not a mid-experiment scoring change.
[Diagnostic](receipts/plan-build-repair-contenders-native-2026-09-18/diagnostics/ls04/async-signature.json).

O-34/O-35 realized opportunity, 2026-09-18: Patrick called the control work a
breakthrough and an opportunity realized. After closing the broader trial, the
separate zero-model body-only replay prevented the unrelated renderer edit while
retaining the useful target repair. Replay-only exit-code checks still rejected
the within-function decision-ordering defect. Twenty reference repairs, twenty
scope-escape controls, twenty stale-source controls and twelve boundary unit tests
pass; all original grades and 17,216 prior receipts remain unchanged. This realizes
the bounded edit/preservation opportunity locally. Fresh model response cost,
latency and reliability remain unmeasured; the original contaminated trial stays
flagged. [Body replay](plan-build-function-body-replay-results.md).

O-36 Make the control outcome useful to the person doing the work. Patrick asked
for one blog post about potential savings and improvements to the user journey,
plus examples of warnings and other guidance. The
[blog draft](blog/controls-savings-user-journey.md) and
[message examples](user-guidance-examples.md) are prepared. They distinguish
measured worker-cost differences from proposed body-only savings, and distinguish
optional advice, blocked work, failed checks, unknown outcomes and completion.
Examples include the observed skill-context warning, stale source, scope escape,
budget stops, progress and durable decision fallbacks. All new message copy is
labeled proposed; no runtime/UI support, publication or additional paid trial is
claimed. A later bounded implementation should verify user understanding and
recovery across the existing grammar before claiming UX improvement.

O-36 extension: Patrick asked whether normal use could reduce technical debt.
The blog now explains the opportunity to close testing gaps and repair shared
interfaces using observed failures, while distinguishing prevention of new
regressions from removal of existing architectural debt. Avoid accumulating
duplicate controls, noisy warnings or special cases; record larger refactoring
separately instead of expanding routine repairs. Net maintenance savings have
not been measured, and this discussion authorizes no automatic cleanup feature.

O-36 prompt-enhancement extension: Patrick identified refinement as another
potential contributor to debt reduction. The blog and tenth guidance example now
cover upstream prevention: use known context, expose material uncertainty and
make the agreed outcome testable before implementation. Preserve intent, scope,
permissions and optionality; clear terse requests need no extra intake ceremony.
Measure requirement corrections and repeated repairs alongside clarification
effort. This is an opportunity hypothesis, not evidence produced by the body
replay, a new implementation authorization or a change to refinement settings.

O-36 evidence clarification: Patrick reports having seen several long prompts
improve through ambiguity removal. Retain this as an observed user benefit in
clarity, rather than describing every benefit as hypothetical. Downstream effects
on rework, maintenance cost and technical debt remain unmeasured. Improvement
means clearer preserved intent, not necessarily fewer words; resolve uncertainty
from evidence or clarification instead of silently choosing an interpretation.

O-36 publication destination, 2026-09-18: Patrick directed integration of the blog
and its associated content into smartaimemory.com **after he approves the content**.
That approval is pending. Website integration and publication have not started.
The [integration handoff](handoffs/smartaimemory-controls-article.md) identifies the
two working drafts, the approval condition and the public-link/content checks.

Unnumbered, 2026-09-19 (assign the next O-number at the next log review): product
modules named like tests. While inspecting the source distribution before a first
PyPI publication, Patrick noticed `test_change.py`, `test_cli.py`,
`test_execution.py` and `test_scope.py` inside `src/attune_harness/`. They are
product code for the `attune-harness test` command, not tests, and must ship. The
`test_*.py` names match pytest's default discovery pattern, so they read as
misplaced tests to people and tools. No defect is observed: `testpaths = ["tests"]`
keeps pytest out of `src/`, and the modules define no test functions. Candidate
follow-up: move them to a subpackage such as `attune_harness/testing/` (`cli.py`,
`scope.py`, `execution.py`, `change.py`). The rename touches package imports,
changes module hashes that existing receipts bind, and needs its own regression
pass, so it is recorded separately and does not block publication. Effort: small
to medium. Nothing is renamed or authorized by this note.

Unnumbered, 2026-09-19 (assign the next O-number at the next log review): pinned
GitHub Actions target Node.js 20. The TestPyPI rehearsal run 35476747591 raised a
deprecation annotation on its `build` and `verify_testpypi` jobs: three pinned
actions target Node.js 20 and are being forced to run on Node.js 24. The pins are
`actions/checkout@11d5960a326750d5838078e36cf38b85af677262` (v4),
`actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065` (v5) and
`actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02` (v4). The same
three SHAs are pinned in `qualification.yml`, so the library qualification matrix
is affected as well as `publish-pypi.yml`. No defect is observed: the jobs ran and
the rehearsal was not blocked. Candidate follow-up: bump each pin to a current
release that targets Node.js 24, keeping full-SHA pins with the version comment,
in every workflow on every branch that carries them. New pins change the workflow
on a release branch, so qualification and a `publish=false` dry run must pass
again before the next real publish. Effort: small. Nothing is bumped or authorized
by this note.

Unnumbered, 2026-09-19 (assign the next O-number at the next log review):
`ubuntu-latest` moves to Ubuntu 26. The same rehearsal run 35476747591 carried a
notice on `build`, `publish_testpypi` and `verify_testpypi` that the
`ubuntu-latest` label will migrate to Ubuntu 26 beginning October 19, 2026
(actions/runner-images issue 14748). `publish-pypi.yml` runs those jobs on
`ubuntu-latest`, and the `qualification.yml` matrix uses `ubuntu-latest` alongside
`macos-latest` and `windows-latest`. No defect is observed. The risk is that the
runner image changes underneath a release without any change to the repository,
so a qualification pass recorded before the migration does not describe the image
used after it. Candidate follow-up: either pin `ubuntu-24.04` in both workflows so
the image changes only by a reviewed commit, or let the label float and treat the
first qualification run on Ubuntu 26 as evidence to read before relying on it for
a publish. The macOS and Windows `-latest` labels float the same way and deserve
the same decision. Effort: small. Nothing is pinned or authorized by this note.

Unnumbered, 2026-09-21 (assign the next O-number at the next log review): make
Redis-backed memory the recommended install for 0.2.0. After 0.1.0 was published
(run 35564794974, commit `8fc26a4`), Patrick observed that the README should have
recommended a `[redis]` extra as the default install. It could not have: 0.1.0
declares seven extras (`tokens`, `verify`, `rag`, `voyage`, `review`, `mcp`,
`memory-native`) and none is `redis`. `pip install "attune-harness[redis]"` against
0.1.0 warns that the extra does not exist and installs the bare core. No Redis
client is imported anywhere under `src/attune_harness`; the two matches for the word
are a comment in `attune_bridge.py` and the substring in "redispatch". The published
`memory-native` extra is a pinned Anthropic API transport for memory proposals, not
the Redis-backed direction, and its name is now permanent. The 0.1.0 page on PyPI is
frozen, so nothing about this can be corrected there; it can only be different in
0.2.0. The intent is already recorded: the
[native memory scoping note](specs/native-memory/scoping.md), direction N3, puts
Redis behind an optional `[redis]` extra, lazily loaded like the Voyage and MCP
extras, with a stdlib file backend in the base for people who do not run Redis, the
backend chosen at startup, and a configured but unreachable Redis reported as
unavailable instead of a write being diverted to files. Task 4 of that note's
candidate ladder ("Backend interface and Redis extra") is this work. Two things are
undecided. First, what "recommended" means beside a base that must stay stdlib-only:
the 0.1.0 README leads with a core that has no dependencies and needs no server, and
the clean-install check on 2026-09-21 confirmed zero packages pulled. A README that
shows `pip install "attune-harness[redis]"` as the recommended line and keeps the
bare `pip install attune-harness` beside it as the no-server option would hold both
claims; making Redis a hard dependency would not. Second, packaging: move the backend
into Harness under the extra, or republish `attune-redis` without its hard
`attune-ai>=3.5.0` dependency. The scoping note found the backend looks portable but
had not verified that `memory.py`, `config.py` and `signals.py` import cleanly with
attune-ai absent. Candidate follow-up: run that import check first, because it
decides the packaging question cheaply; then scope ladder Task 4 in the successor
spec. Done when, in a fresh environment with attune-ai absent,
`pip install "attune-harness[redis]"` yields a working Redis-backed working memory;
the bare install still pulls zero dependencies and uses the file backend; an
unreachable configured Redis is reported as unavailable and is distinct from "no
matching memory"; CI exercises the Redis backend against a real server on at least
one platform; and the README's qualified table says which platforms the Redis path
is and is not qualified on. An empty or alias `redis` extra added only so the install
line resolves is rejected: it would recommend an install that does nothing. Extra
names are permanent once published, so `redis` should be chosen deliberately against
the existing `memory-native`. Effort: larger; it crosses packaging, a new backend
interface and live qualification. Whether Task 4 can start before ladder Tasks 1 to
3 is not settled: the ladder is sequential only where a task consumes the previous
result, and working memory does not obviously consume the file-tier readers, but
that is an inference to confirm in the successor spec, not a finding. Nothing is
built, renamed, scheduled or authorized by this note.

Unnumbered, 2026-09-21 (assign the next O-number at the next log review): open the
harness's own run-record readers with Windows delete-sharing. 0.1.0 shipped a bounded
fix (`8fc26a4`) for the defect that blocked the release: `RunStore.save()` replaced
`record.json` once with no retry, Windows refuses to replace a file another handle
has open, and the resulting `PersistenceError` stops all further dispatch in an MCP
session by design. The reproduction (scratch commit `8f59e9e`, run 35561326066)
failed on Windows with `[WinError 5] Access is denied` and passed on macOS and
Ubuntu. The shipped fix retries `os.replace` on `PermissionError` every 5 ms for up
to `REPLACE_RETRY_SECONDS = 2.0`, then fails closed as before. That treats the
symptom on the writer's side. The limit is stated in the 0.1.0 README and changelog:
a process that holds the record open for more than about two seconds still fails the
run. Part of the contention is the harness's own. `load_record` in
`review_store.py` reads through `features.read_text`, which uses `path.open('rb')`,
and Python's `open` on Windows does not request `FILE_SHARE_DELETE`, so every
harness reader (`status`, `resume`, recovery, the polling MCP test) is itself a
handle that blocks the replace for as long as it is open. Candidate follow-up: on
Windows only, open run records for reading with delete-sharing (through
`CreateFileW` with `FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE` and
`msvcrt.open_osfhandle`, stdlib only, no new dependency), leaving the POSIX path
untouched. Hypothesis, not tested: with the reader sharing delete access, the
writer's replace succeeds on the first attempt while the reader still holds its
handle, so harness readers stop contributing to the retry at all. Done when a
Windows-only test holds a harness-opened read handle indefinitely and `save()`
succeeds without entering the retry loop; the existing
`test_save_still_fails_closed_when_record_stays_open` still fails closed for a
handle opened without delete-sharing; and qualification is six of six green. This
does not help against third-party handles (an indexer, antivirus, an editor), which
is why the bounded retry stays. Whether to then shorten or keep the two-second
budget is a separate decision to make from evidence, not now. Effort:
small to medium; the change is a few lines but it is Windows-only file-handle code
in a fail-closed persistence path, and CI is the only place it can be verified.
Nothing is changed or authorized by this note.

Unnumbered, 2026-09-21 (assign the next O-number at the next log review): the 10 s
`observe` deadline in the MCP cancellation test.
`tests/test_mcp.py::test_sdk_cancellation_retains_started_call_receipt` polls for a
pending receipt through a local `observe` helper with a fixed deadline of 10 seconds
(`asyncio.get_running_loop().time() + 10`), inside an SDK client created with
`read_timeout_seconds=5`. When the Windows record-replace defect stopped dispatch,
the receipt never reached disk and the test spent its full 10 seconds before failing
(runs 35559398300 and 35560396368). The original failure message reported only the
saved record, which hid the cause; scratch commit `8f59e9e`, carried into `8fc26a4`,
made the timeout report what the tool call returned as well. The deadline was not
the defect. Junit timings ruled out a tight budget before the cause was known: the
sibling SDK test does spawn plus real calls in about 2.5 s on the same runners, and
after the fix this test took 2.1 to 3.0 s across four Windows jobs (runs 35562268487
and 35562701896). Two things remain worth a look. First, the deadline is a bare
literal with no stated relation to the code it waits on, and it now sits beside a
writer that may legitimately spend up to 2.0 s per save under contention, so several
contended saves in one test could approach 10 s on a slow runner and fail for a
reason that is not a defect. Second, a pass records nothing about how close it came.
Candidate follow-up: name the deadline as a constant with a comment stating what it
bounds and how it relates to `REPLACE_RETRY_SECONDS`; include elapsed time in the
timeout assertion message; and decide from a few weeks of junit timings whether 10 s
is right, rather than raising it pre-emptively, because a longer deadline would have
made this defect slower to notice, not easier to diagnose. Done when the constant and
message are in place and qualification is six of six green. Effort: small. Nothing
is changed or authorized by this note.

Unnumbered, 2026-09-21 (assign the next O-number at the next log review):
`docs/handoffs/` is ignored on one branch only. Both release handoff notes
(`first-pypi-release-2026-09-19.md` and `release-0.1.0-windows-fix-2026-09-21.md`)
state that `docs/handoffs/` is gitignored. That is true only on
`wip/local-snapshot-2026-09-19`, where `.gitignore` line 30 reads `docs/handoffs/`.
`main` and `release/0.1.0rc1-packaging` have no such rule: on both, the directory
shows as untracked (`?? docs/handoffs/`), as does `docs/reflections/` in the main
checkout. The notes were written while the `wip` branch was checked out, which is
how the claim came to be recorded as general. No file from the directory is tracked
on any of the three branches, and nothing leaked: the 0.1.0 release commits added
files by name, as the handoff instructed. The exposure is that the repository is
public and the directory holds session notes, run IDs, draft articles and
qualification output, so a single `git add -A` or `git add docs` on `main` or a
release branch would publish them. Candidate follow-up: add `docs/handoffs/` (and
decide about `docs/reflections/`) to `.gitignore` on `main`, so every branch cut
from it inherits the rule. Do not add it to the published release line by itself: a
commit there starts a qualification run and moves the branch head away from the
tagged, published SHA for no product benefit; let it arrive through whatever
reconciles the lines. Until then the working rule stands: add files by name. Done
when `git status` on a fresh checkout of `main` with a populated `docs/handoffs/`
shows a clean tree, and the two handoff notes no longer make the general claim
(the 2026-09-21 note's worktree copy is already corrected). Effort: small. Nothing
is changed or authorized by this note.

Unnumbered, 2026-09-21 (assign the next O-number at the next log review): the
published 0.1.0 source is on no line that future work starts from. Three lines
diverge from the same merge base, `7eabe58`, and none contains another. `main` is 3
commits ahead of the base (`da99bb3`, `3607e4f`, `82efb27`, all CI registration) and
reports version `0.1.0.dev13`. `release/0.1.0rc1-packaging` is 5 ahead (`ff05cfa`,
`361bdcb`, `afa415f`, `c4fc89d`, `8fc26a4`), reports `0.1.0`, and its head is the
commit published to PyPI by run 35564794974 and tagged `v0.1.0`.
`wip/local-snapshot-2026-09-19` is 24 ahead, reports `0.1.0.dev14`, and is the only
line carrying this log, `docs/specs/native-memory/scoping.md` and the
`docs/handoffs/` ignore rule. The consequence that matters: the Windows
record-replace fix exists only on the release line. `review_store.py` on `main` and
on `wip` has no `_replace` helper and no `REPLACE_RETRY_SECONDS`. A 0.2.0 cut from
either would ship without a fix that 0.1.0 has and would reintroduce the Windows
failure that blocked this release. Neither has the `## 0.1.0` changelog entry or the
PyPI README. `main` additionally lacks `LICENSE` and `docs/cli-guide.md`; `wip` has
its own copies of both, which were not compared with the release line's. The tag keeps the published source reachable, so nothing is lost today;
the risk is at the next release. A trial merge of the release line into `main`
(`git merge-tree`, nothing written) reports two conflicts. One is
`.github/workflows/publish-pypi.yml`, add/add: `main` deliberately carries an inert
registration stub, which is why the guardrail says never to dispatch from `main`,
while the release line carries the real workflow. That conflict needs a decision,
not a mechanical resolution: keep the stub on `main` and the real workflow only on
release branches, or promote the real one and rely on the `pypi` environment's
branch policy and required reviewer. The other is `tests/test_mcp.py`, a content
conflict. `wip` against the release line was not trial-merged. Candidate follow-up:
decide which line is the trunk for 0.2.0, then bring the five release commits onto
it (merge, so the published SHA stays an ancestor, in preference to cherry-picks
that would make the fix look new), resolve the workflow question explicitly, set the
next development version, and qualify the result. Separately decide what becomes of
`wip`'s 24 commits. The release branch itself should stay where it is: the `pypi`
environment's branch policy names it, the published README's links resolve through
`v0.1.0`, and that tag must not move again. Done when a single line contains
`8fc26a4` as an ancestor, carries the Windows fix, this log and the scoping note,
reports a development version above `0.1.0`, and passes qualification six of six;
and the workflow decision is written down where the guardrails live. Effort: medium;
the merges are small but the workflow decision and the fate of `wip` are judgment
calls, and everything lands on a public default branch. Nothing is merged, moved or
authorized by this note.

Unnumbered, 2026-09-21 (assign the next O-number at the next log review): the
published 0.1.0 README overstates the harness's independence, and attune-ai is an
undeclared runtime tie. Patrick read the README on the PyPI page after the release
and found it inaccurate. His position, stated 2026-09-21: attune-ai should not be a
dependency, and code was imported and modified from attune-ai into Harness. Checked
against the source at tag `v0.1.0`. What holds: the bare `pip install
attune-harness` pulls zero packages (clean venv, 2026-09-21), and no module under
`src/attune_harness` has a static import of a provider SDK. What does not hold falls
into three parts. First, provider SDKs are used. README line 26 says "No provider
SDK, no API key, and no attune-ai installation" and line 127 says the core "must run
with no provider SDK and nothing else from the Attune family installed". Both are
true of the bare core install and read as claims about the harness. `memory_native.py`
imports `anthropic` and constructs `anthropic.Anthropic(...)` behind the
`memory-native` extra, and `voyage_provider.py` loads `voyageai` behind `voyage`.
Second, attune-ai is called at runtime and declared nowhere in `pyproject.toml`,
neither as a dependency nor as an extra. `memory_context.py` imports
`attune.memory.harness_adapter.CompatibilityAdapter` inside `MemoryHost.__init__`, so
memory context cannot be constructed without attune-ai; the native memory scoping
note recorded on 2026-09-19 that `attune-harness memory capabilities` reports
`unavailable` and exits 2 with attune-ai absent (not re-run today: the command needs
a `--config` that was not fabricated for the check). `spec_bridge.py` imports
`attune.spec.workspace` and `attune.elicitation.command_workspace` and subclasses
`SpecWorkspaceAdapter`, which is why `plan --accept` needs the Attune AI Spec
runtime; the README's qualified table concedes that one case. README line 127 goes
on to say the Attune libraries "come in as extras, where you can see exactly what
each one adds". That is true of `attune-forms`, `attune-verify` and `attune-rag`,
which load lazily through `features.require_feature` at pinned versions, and false of
attune-ai, which no extra names. Separately, `attune_bridge.py` and
`memory_bridge.py` import `attune.plugins.base` at module top level. They are plugins
meant to be loaded by attune-ai, are not entry points, and are imported by nothing in
Harness; a plugin importing its host is expected, so they are a different case from
the two above and should not be counted as the same defect. Third, provenance is
unstated. A search of `README.md`, `docs/`, `src/`, `LICENSE` and `CHANGELOG.md` at
`v0.1.0` finds no statement that any Harness code originated in attune-ai, and there
is no `NOTICE` file. Which modules are derived was not determined from the source;
that fact is Patrick's. Asked which portions, he named the memory system as an
example ("things like the memory system"); the full list is not established. Both packages are Apache-2.0 and both are his, so this is an
accuracy question, not a licensing defect. The 0.1.0 page on PyPI is frozen; a
correction shows on GitHub when it lands and on PyPI only with the next version.
Direction N1 of the [native memory scoping note](specs/native-memory/scoping.md)
already says to cut the functional tie for memory, and its ladder Task 1 ("Map the
dependency") is the first step; the table of four modules above is a start on it.
The Spec tie in `spec_bridge.py` is covered by no note or spec. A suggestion made
during the session to declare attune-ai as an extra was withdrawn: it would formalize
the tie Patrick wants removed. Candidate follow-up, in order: correct the README
wording on whichever line becomes the trunk (a draft is at
`docs/handoffs/README-independence-wording-draft-2026-09-21.md`, on disk only), with
the origin sentence completed by Patrick; decide whether a `NOTICE` or a short
provenance section in the docs is wanted; extend the dependency map to the Spec tie
and decide whether it is cut, kept as a stated optional integration, or replaced;
then do the cut through the successor spec. Done when the README claims only what a
clean environment demonstrates, every runtime call into attune-ai is either removed
or named in the README and in packaging, and an installed-environment check with
attune-ai absent exercises memory context and plan acceptance and records what each
does. Effort: small for the wording, larger for the cut. Nothing is changed or
authorized by this note.
