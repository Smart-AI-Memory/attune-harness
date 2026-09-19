# Requirements — plan and build

Status: **Tasks 1–7 accepted; Task 8 connected comparison stopped at contract/test handoffs; corrective qualification pending**.
The selected existing-code feature and explicit effects are in [first-journey.md](first-journey.md).

## User-set direction

Implement plan and build using the next generation of the spec command. Establish
the goal and scope, support multiple models/LLMs, encourage useful creativity and
retain the discipline established in prior work. Humans can intervene with verbs;
complex features use specs, while clear prompts and XML-enhanced prompts serve
work that does not need a full spec. Existing authorizations and quality gates
retain their meanings.

Human intervention is one layer of safety and quality alongside hooks, enforced
permissions, automated checks and model guidance. Use the applicable controls for
the work; this direction does not require a human decision at every step. Account
for models' learned behavior when designing grammar, guidance and feedback, and
qualify the results across supported model/host profiles. This does not require
changing model weights.

## Proposed requirements and acceptance

| ID | Required behavior | Observable acceptance |
|---|---|---|
| R1 | Plan establishes the goal, context, scope, constraints and evidence of success; missing material information is explicit | A vague request produces focused questions; a complete request preserves supplied answers without another intake ritual; corrections replace the affected facts |
| R2 | Select the authoring form using the existing collaboration contract and XML eligibility rules | Frozen clear-task, handoff, dependency, consequential-choice and complex-feature cases produce an explained selection; changing file count alone does not determine the form; a shorter form cannot bypass required information or authority |
| R3 | Separate useful exploration from settled decisions | When a real design choice exists, alternatives include rationale, evidence, uncertainty and a counter-case; no artificial disagreement or alternatives are generated for a settled choice |
| R4 | Multiple configured models can perform explicit bounded roles | Planner, specialist, critic, worker and reviewer assignments carry role, provider/model settings, accepted inputs, output contract and budget; unavailable assignments are reported; no silent provider fallback |
| R5 | One durable work identity spans plan, build and human intervention | The accepted revision, assignments, attempts, files, checks and decisions remain linked; a material goal/scope/plan change invalidates affected execution and acceptance; completed unaffected work is not silently repeated |
| R6 | Build implements a real feature using the accepted contract | The selected first journey creates needed files and changes existing ones, then passes task and integrated acceptance checks; a renamed repair wrapper or a generated plan alone cannot satisfy this requirement |
| R7 | Build effects have explicit scope and recoverable receipts | File proposals cannot change protected acceptance inputs or task state; stale preimages, collisions, partial changes and uncertain writes are detected and retained; retries reconcile the original operation |
| R8 | Quality evidence and human decisions remain distinct | Tests, review findings and artifact hashes are retained separately from approval; missing/skipped checks are visible; model agreement does not accept a task; auto-run retains the existing stop conditions and authorized scope |
| R9 | Human verbs and grammar operate on the current contract | Plan/build/status/resume identify the same work; goal changes, pushback, per-item dispositions and quality decisions are bound to the shown revision; stale or replayed actions cannot alter a newer plan |
| R10 | Current commands and accepted records remain usable | Existing compatibility, assessment, repair and recovery regressions pass; new plan/build state is versioned; importing an old plan does not import approval of changed content |
| R11 | Shared services remain shared | Plan and build reuse Harness dispatch, process supervision, storage, journals and forms; the base core remains dependency-free; an optional legacy bridge owns Attune-specific imports |
| R12 | Qualification measures outcomes rather than generated artifacts | Frozen cases include wrong-goal plans, unnecessary questions, unsupported assumptions, incomplete builds, misleading test success and interrupted work; report correctness, human corrections, calls/tokens/time and known costs; offline peers and native outcomes have distinct receipts |
| R13 | Safety and quality combine model guidance, runtime enforcement, automated evidence and human judgment | Each supported execution profile identifies applicable controls and who enforces them; required hook/check failures or unavailability stop the dependent operation visibly; a model proposal cannot bypass an enforced boundary by claiming compliance; valid work proceeds within existing authority without invented manual gates |
| R14 | Reassess controls and grammar against actual model behavior, including training-sensitive response patterns | Inventory controls and their coverage; compare existing and candidate mechanisms on frozen cases across supported models/hosts; measure response meaning, enforcement failures, unnecessary blocks, repeatability and cost; preserve effective controls and reimplement weaknesses without treating schema validity as a correct response or inferring training causes from outputs alone |
| R15 | Measure and reduce delay before useful findings or decisions appear | Correlate inspection, validation, hooks, model turns and visible presentation; report first useful output separately from full completion and human response time; compare changes against a separate baseline while preserving required evidence, freshness checks and authority |

The first R6 fixture is JSON Lines export for the existing documentation module.
It includes a new module, a changed CLI and optional generated tests in a new
directory. New-project scaffolding remains outside this first profile; the broader
product direction is unchanged.

## Existing policy sources

- [Artifact selection](/Users/patrickroebuck/attune-ai/content/collaboration/contract.md#artifact-selection)
  owns the authoring tiers and the precedence of spec/XML requirements.
- [XML eligibility](/Users/patrickroebuck/attune-ai/.claude/rules/attune/xml-enhanced-prompts.md)
  owns structured-task eligibility and parser-sensitive information requirements.
- [Communication grammar](/Users/patrickroebuck/attune-ai/.claude/rules/attune/communication-grammar.md)
  owns decision, pushback, progress and disposition semantics.

These sources guide the new Harness policy. Attune AI remains a reference project;
this spec does not authorize editing its runtime or rewriting its existing gates.
