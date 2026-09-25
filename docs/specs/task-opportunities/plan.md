# Real task progress and ranked opportunities

Status: implementing Task 1, the return-to-work journey described in
[task-1-return-to-work.md](task-1-return-to-work.md). Its user acceptance is pending.
The earlier unmerged snapshot implementation is a candidate foundation; passing
its software checks does not establish completion of the revised first task.
Each increment retains its verification and review. Merge and release remain
separate maintainer decisions.

## Outcome and first increment

A user can inspect a real saved Harness task, understand what its evidence
establishes, review opportunities discovered during the work, and choose one as
the starting point for a draft plan. Both the assistant and graphical view use
the same task identity and current revision. The destination is a connected task
companion in the installed production package: progress and submitted opportunities
update automatically while the user's selection, reading position and decision
context stay stable. Delivery begins with a useful return-to-work journey backed
by a reusable snapshot projection, then adds live observation and carefully
scoped interaction. Rendering a record alone does not complete the first increment.

The observed motivating case is a navigation task whose retained record remained
a draft with no completed steps while separately authored prototype artifacts
and browser reports existed. Show both facts accurately. An external artifact
must not manufacture a Harness run, completion event or acceptance.

The first workplace use case is **returning to work after an interruption**. A
person should recover the goal, where work stopped, established progress, open
decisions or blockers, and one useful next step without rereading the whole
conversation. Show changes since an explicitly retained comparison point when
one exists; otherwise say that comparison history is unavailable. Technical
record details support this orientation. Reviewing delivered work remains a later
use case. Results produced outside the task journal retain their own provenance.

## Agreed direction and proposed defaults

Agreed product direction: real saved tasks; production integration; opportunities
ranked automatically as recommendations; goal and user benefit first, with feature
contribution, sound reuse, effort/risk and evidence confidence visible. Show both
highest value and easiest useful win, with reasons. Ranking never starts work.

The connected destination and stable-reading behavior are now agreed direction.
Automatic display updates consume retained task changes and explicitly submitted
opportunities; they do not imply automatic access to an assistant's hidden context
or establish when context mining should run.

The architecture, sort policy, file formats and staged delivery below are proposed
implementation defaults. The product does not gain an automatic background miner
in this slice. Existing assistants may submit explicitly sourced opportunities
from their current context through the proposed package API. A later decision
can specify automatic capture timing, host access, models and cost budgets.

## Baseline and reuse

Original planning baseline: repository commit
`1df4ea0ecec30f81d071847dc212689d83a34950`; installed Harness 0.6.0.
The snapshot implementation was prepared against `11071a1de97c8878a9cc6e710ba1aeb0b9301c00`.
Its validated reader, literal-text rendering and compatibility checks are reuse
candidates for the revised Task 1, not proof of the return-to-work journey.

- `work_cli.present(..., inspect_only=True)` already provides feature-work
  identity, current state, intent, steps, evidence, freshness and next action.
- `work_runtime.work_status` derives completion from the saved work journal.
- `execution_evidence.work_execution_evidence` provides retained-run references.
- `task_cli.execute_control` routes status across task profiles. The initial
  view supports feature-work records; other profiles get a clear limitation and
  their existing status output, not an invented shared meaning.
- `command_workspace` and `spec_workspace` own shared rendering and bound
  decisions. Use their conventions, not a second acceptance store.
- `work_contract` selects prompt/XML/spec from structured facts; it does not
  discover intent from arbitrary natural language.
- `docs/compatibility.md` requires additive CLI surface changes to update the
  pinned fixture and changelog. Existing status JSON and exit semantics stay.

Existing prototype files are design references, not production components to
copy wholesale. Their sample data, browser persistence and simulated approvals
must not become authoritative. Existing retrieval ranking is not an opportunity
priority policy and should not be reused merely because both are called ranking.

## Requirements and evidence of completion

| ID | Required behavior | Proof required |
| --- | --- | --- |
| R1 | The view names task, project, revision, snapshot time, state and next action | Compare a rendered real record with installed CLI status; distinguish draft, paused, failed, stale, unresolved and completed fixtures |
| R2 | Evidence says what was checked and what remains unknown | Run references resolve; external reports are labeled separately; missing or changed artifacts cannot imply passing checks |
| R3 | Retain useful opportunities with provenance and dispositions | Save/reopen retains identity, sources, reasons and edits; duplicate submission is idempotent; dismissed items remain inspectable |
| R4 | Automatically order opportunities with understandable reasons | Frozen comparison cases produce the documented order; unknowns, dependencies and ties behave as specified; a user override is preserved |
| R5 | Selection opens a linked, editable draft using existing authoring rules | Repeated selection returns the same draft; no acceptance, dispatch or file effects; stale source needs refresh or explicit retained-history disclosure |
| R6 | Users can return to work, recover context and choose the next useful step without learning internal forms | First, an interruption/reopen walkthrough establishes goal, stopping point, supported progress, uncertainty and the next action without rereading the conversation; later, review and opportunity-selection walkthroughs establish informed correction, choice and deferral; text fallback works |
| R7 | Installable production behavior preserves compatibility | Build and test the installed wheel outside its source checkout; required platform CI passes; old CLI callers still work |
| R8 | The companion observes changes automatically without disrupting a decision in progress | External task progress and submitted opportunities appear within the declared freshness bound; selection, focus, scroll anchor and unsaved edits survive; changed rankings are announced for review rather than silently reordering the active list |
| R9 | Connected controls preserve current task authority and revision meaning | Supported select/defer/correct actions use validated owners; stale actions are refused, duplicate delivery is idempotent and uncertain outcomes are inspectable; the displayed task/revision is the one acted upon |
| R10 | Guidance helps users choose useful work without accumulating unnecessary features | Selection explains user benefit, credible existing-feature alternatives and ongoing cost; the walkthrough includes choosing reuse or deferral; selecting more work is not presented as success by itself |

## Scope and boundaries

Include a return-to-work journey over local feature-work tasks and explicitly
retained context; a reusable graphical snapshot and equivalent Markdown; live
observation of retained changes; explicit opportunity
submission and retention; ranking; draft-plan handoff; connected controls for
candidate selection, deferral and assessment correction; a packaged entry point
through the skill/library; and a short verified tutorial. No cloud service is
required. Task 1 needs no persistent server; later tasks add the local connection.

Exclude hidden host-conversation scraping, automatic memory writes, cross-project
discovery, general web research, paid inference, production model selection,
approval inside exported HTML, browser-triggered build/merge/release, autonomous execution,
publication and broad migration of old prototype records. Existing lifecycle
commands continue to own plan acceptance, build, review, test and resume.

## Proposed architecture

1. **Task projection:** add `task_view.py` to consume the existing validated status
   projection. Organize the first view around the return-to-work questions,
   with bounded, escaped supporting details. Reuse status freshness and evidence
   semantics; do not reconstruct authority from file timestamps or prose. Task 1
   must establish how explicitly retained continuation context and external work
   evidence enter that view; a manually authored briefing is not a shipped API.
2. **Installed presentation:** proposed optional `status --format json|markdown|html`
   defaults to today's JSON. Output goes to stdout, so task inspection stays
   read-only; the caller may explicitly save the HTML. No scripts, remote assets,
   embedded secrets or executable content from task text. Unsupported profile or
   unreadable record yields a truthful diagnostic, never an empty success screen.
3. **Opportunity collection:** new versioned advisory storage outside the project
   checkout and outside the immutable task journal. Reuse appropriate existing
   bounded I/O and locking utilities after checking their semantics. This is the
   owner of opportunity dispositions only, never task approval or completion.
4. **Ranking:** a pure deterministic function over explicit assessments and their
   evidence. Assessments may be supplied by a human or the active assistant; origin
   and confidence stay visible. Automatic ordering does not claim automatic,
   verified estimation of effort or value. No extra model invocation is required.
5. **Draft handoff:** materialize an ordinary plan request through `create_work`
   or the existing `plan --request` route, retaining the source opportunity and
   its revision. No writes to `record.json` outside its existing owner.
6. **Connected observation:** a local companion adapter reuses the projection and
   watches or polls for changed task/collection revisions. Read complete validated
   records, retain last-good data with an explicit freshness state on read failure,
   and never label disconnected or stale data live. Transport, refresh bounds and
   resource limits are frozen in Task 2's design; no host embedding is presumed.
7. **Connected interaction:** a later action adapter uses existing bound decision
   mechanisms and the new advisory-store owner. Validate task, candidate and
   collection revision before effects. Qualify the local transport's access and
   origin boundaries before enabling writes. A browser never directly edits task
   JSON. Task execution continues through the existing authorized workflow.

The package API supports opportunity submission, inspection, assessment revision,
disposition and draft selection. The skill uses that API on the user's behalf;
end users continue expressing intent in conversation. Concrete API names and
schemas are frozen with Task 3's tests, not presented here as already installed.

### Automatic updates with stable decision context

Update progress and notify about new evidence automatically. Keep stable item IDs
and semantic scroll anchors; preserve keyboard focus, selection and draft edits.
While someone inspects an opportunity or a ranking, retain that displayed revision
and announce the newer recommendation with a Review changes action. The comparison
shows changed evidence, assumptions and reasons before the user adopts the new
order. Keep the current recommendation accessible without imposing the reorder.

Pinning a view does not keep its authority valid. Mark superseded material clearly;
an action on a stale revision requires refresh/reconciliation under the existing
owner. When a selected item becomes unavailable, retain an explanatory placeholder
rather than selecting another item. On disconnect, show last successful update;
on reconnect, reconcile current state without losing edits or hiding intervening
changes. Define and test a refresh bound and overload behavior in the connection
design rather than making an unmeasured immediate-update promise.

### Opportunity and ranking records

Each opportunity needs a stable ID, collection revision, project/task identity,
source checkpoint, source references and hashes where available, observation,
proposed change, user obstacle, goal relationship, affected/reused capabilities,
dependencies, acceptance idea, assessment author/time, uncertainty and disposition.
Store only supplied excerpts needed to explain the finding; do not copy an entire
private conversation. Validate IDs, sizes and references. Treat all text as data.

Proposed dispositions: proposed, deferred, selected and dismissed. A selected
opportunity links to a draft task; implementation completion is always read from
that task. Revising the opportunity preserves prior versions and does not rewrite
an accepted downstream plan. Concurrent writers compare expected revisions; a
failed or uncertain write is visible. Unknown schema versions fail explicitly.

Ranking snapshots retain input revisions, policy version, factor assessments,
eligibility groups, ordered IDs and per-item explanations. Recompute when the goal,
dependencies or assessments change; retain old results. A pinned human order is
shown separately from the current recommendation, with its reason and freshness.

### Initial qualitative ranking policy

First separate actionable candidates, dependency-blocked candidates, and candidates
needing evidence. Keep every group visible. Exclude dismissed and already-selected
items from new recommendations, while preserving access to them.

Within actionable candidates use this explicit order: goal contribution, user
journey benefit, needed feature contribution, lower delivery risk, lower total
effort, then suitable reuse. Use high/medium/low with reasons; effort includes
verification, integration and maintenance. Stable ID resolves remaining ties for
display only; show substantive ties as ties. This is a proposed policy, not a
measured utility function. No weighted decimal score or invented time savings.

Unknown goal/value/risk/effort assessments go in needs-evidence, not a low-value
bucket. Explain missing evidence and show a next investigation action. An absent
reusable component can be explicitly marked not applicable; do not force reuse.
Confidence is a disclosure and investigation trigger, not a blanket penalty that
hides important uncertain work. Blocking dependencies remain visible even when
the opportunity's value is high.

The easiest useful win is the lowest-effort, low-risk actionable candidate with
at least medium goal contribution and user benefit; break ties by the main order.
If none qualifies, say so. Users can correct assessments, defer, or select another
candidate. Reordering is advisory and cannot bypass a blocked implementation.

## Interaction grammar and authoring

### Teach judgment at the point of selection

User education is part of the intended experience. An opportunity is a possibility,
not a commitment or an instruction to add a feature. A high rank is a comparison
within the candidate set, not proof that any candidate is worth implementing now.

Use concise decision support in the existing detail and draft views: what user
problem this solves; whether an existing capability, clearer documentation or a
smaller change could solve it; implementation plus ongoing maintenance, testing
and interface complexity; and what current work it would delay when that is known.
Ground alternatives in inspected capabilities and label unknown estimates. Reuse
is useful when it improves the journey, not merely because code already exists.

Offer save/defer/dismiss alongside selection without treating them as failure.
The recommendation may be to finish current work or implement none of the proposed
features. Avoid urgency cues, rewards for the number selected or repeated prompts
to activate a growing backlog. Keep saved ideas retrievable without giving every
one equal prominence in the active workspace. No automatic deletion is implied.

Teach through the worked journey and short contextual explanations rather than
a mandatory lesson or another approval gate for every small task. Progressive
detail should keep familiar work quick. The counter-case is paternalism: arbitrary
caps or lectures can suppress valuable exploration. Users retain the choice to
proceed after seeing the tradeoff. This requirement adds guidance to Tasks 4–7,
not another service, scoring subsystem or implementation chunk.

| Moment | Presentation and meaning |
| --- | --- |
| Return to work | Goal, stopping point, supported progress, changes where comparison is possible, blockers and one useful next step; source details remain available |
| Review delivered work | Outcome, supporting evidence, unresolved claims and the applicable decision; later use case |
| Propose interpretation | Assumption review only for consequential inferred facts |
| Compare opportunities | Ranked recommendation with factors, uncertainties and Why ranked here |
| Rule on candidates | Triage for per-item dispositions; focused decision for the selected next task |
| Select work | Editable draft of goal, scope and done condition, with credible smaller/reuse alternatives and ongoing cost; clear consequence: no execution; defer remains available |
| Accept or execute | Existing bound decision and authority path; never an exported HTML button |

Use prompt for bounded clear work, XML where structure helps, and spec for complex
or continuing work. A PR carries actual changes and review evidence; it is not an
alternative authoring tier. This multi-session feature uses a spec. Text and click
presentations must preserve the same meaning. Do not force a form when there is
no question. Rank presentation is not a submitted user ranking answer.

## Seven sequential implementation tasks

Each task produces its own reviewable change and evidence. Later tasks consume
the previous accepted result; shared files are not parallel implementation lanes.
Task-local effects and protected probes must be frozen before any Harness build.
The roadmap below is not yet an executable effects manifest.

| Task | Deliverable and likely owners | Done when |
| --- | --- | --- |
| 1. Return to work | A usable continuation overview, reusing `task_view.py`, `task_cli.py`, compatibility protections and view tests where suitable; explicit context/evidence boundary | After interruption, a user can state the goal, stopping point, supported progress, unresolved issues and the next useful action without rereading the conversation; available changes and missing comparison history are distinguished; externally performed work retains provenance; installed identity/evidence match JSON; inspection is read-only and hostile text is inert |
| 2. Connected observation | Local companion adapter, shared projection and connection tests | An external task transition appears within the declared freshness bound; selection/focus/reading position survive; stale, disconnected, rapid and out-of-order updates remain truthful |
| 3. Retained opportunities | `opportunities.py`, storage helpers if needed, API/skill guidance and persistence tests | Proposed/deferred/selected/dismissed survive reopen; source and revision are retained; duplicates, stale writers, corrupt records and unknown schemas are handled explicitly; submitted candidates appear in the companion |
| 4. Explainable ranking | `opportunity_ranking.py`, view integration and policy tests | Ranking cases, ties, unknowns, dependencies, stale assessments and human overrides pass; highest value and easiest useful win are separately explained; new rankings do not displace an active review |
| 5. Selection into planning | `opportunity_handoff.py`, existing plan owner, skill integration and handoff tests | One selection creates one linked editable draft; retry after interrupted creation recovers that draft; source revision is checked; no acceptance or execution occurs |
| 6. Connected controls | Companion action adapter, existing decision mechanisms and action tests | Select/defer/correct operate on the displayed IDs and revisions; stale and replayed actions cannot apply to different work; edits and decision context survive concurrent updates |
| 7. Installed journey and tutorial | Documentation, installed check script, package assets if needed and existing qualification selection | Fresh wheel completes the connected journey with real records; platform checks and independent review pass; observed walkthrough meets R6/R8/R9/R10, including reuse or deferral; tutorial states remaining limits |

Task 1 is the immediate priority: help someone continue their current work. Its
smallest meaningful slice is one real interrupted-task journey with evidence and
a next action; a record renderer alone is insufficient. Ranking depends on
reliable retained candidates, so it follows Task 3 rather than distracting from
unfinished work.

Task 5 must design crash-safe selection before effects: a persistent selection key
maps opportunity revision and destination to a reserved draft directory. Inspect
an existing reservation after interruption; never create a duplicate task blindly.
Do not embed permissions in the source opportunity. Use existing authority checks.

## Verification, release and stop conditions

For each implementation chunk run targeted behavioral tests, meaningful negative
controls and the full suite; qualify the installed wheel for shipped code. Changes
under src require the repository's independent review. Inspect Windows CI rather
than inferring support from macOS. Additive interface changes include intentional
compatibility fixture updates and a changelog entry; inspect retained receipt pins
before editing any workflow or experiment. No workflow dispatch is pre-authorized.

State cases include a reopened task with and without a retained comparison point;
a draft with external evidence; paused/failed/uncertain runs;
changed task/evidence; invalid and missing files; concurrent opportunity updates;
HTML injection; source paths outside allowed roots; unknown factor values;
duplicate submission and selection; interruption between draft creation and link
publication; and editing a selected opportunity after downstream acceptance.
Connected cases also include focus/scroll stability during updates, a pending
ranking change, superseded decisions, selected-item disappearance, interrupted
connections, lost action acknowledgments, local access boundaries and recovery
without duplicate application or loss of user edits.

Distinguish software correctness, ranking usefulness and human usability. The
deterministic sort tests prove policy conformance, not that the recommendations
are optimal. Record user disagreements and actual effort to inform a later policy
revision; do not invent a quality threshold or claim measured improvement now.

Feature done means R1–R10 have evidence and production packaging is ready under
the existing release process. Planning done means this proposal is internally
consistent, current-code anchors are checked, scope/limits are explicit, and a
saved draft presents the next decision. Neither means released to users.

## Documentation timing and decisions for review

Keep the worked example in [journey.md](journey.md) with this plan. Turn it into
an executable tutorial during Task 7, based on the installed journey. A broader
article is optional follow-up, using actual outcomes and limitations; it is not
a prerequisite for planning completion or an implied publication request.

The delivery direction is return-to-work first using a reusable snapshot, then
live observation and scoped interaction using the same projection; explicitly
submitted opportunities rather than background mining; the qualitative ordering;
and the seven-task sequence. Before each chunk, prepare its concrete scope,
protected checks and review arrangement. The current first-task plan is
[task-1-return-to-work.md](task-1-return-to-work.md); earlier snapshot design notes
remain in [task-1-design.md](task-1-design.md) for reuse and evidence.
New spending and release remain gated.

Counter-case: an extra snapshot stage can become disposable work or delay the
connected experience. Keep it small and reuse its projection, fixtures and rendering
in the companion. Its acceptance validates evidence and presentation only. The
connected companion is the agreed destination; live observation and stable decision
context must pass their own criteria before the complete feature is called done.
