# First journey and concrete implementation boundaries

Status: **Tasks 1–7 accepted; Task 8 connected comparison stopped at contract/test handoffs; corrective qualification pending**.
This advances the existing draft following Patrick's instruction to proceed after
the preceding authorized work is done. The Spec handoff correction was closed
before this preparation began. Additional native trials and release remain separate.

## Selected feature

Add JSON Lines export to Harness's existing static Python documentation tool in a
disposable checkout containing a byte-identical captured package subtree. This is
an existing-code feature, not a new-project generator. Its source is
`src/attune_harness/documentation.py`; the original checkout remains untouched.
The preparation script records its hash and runs the existing command before any
candidate change.

The accepted final intent is: preserve the default JSON bundle, add an explicit
`--format jsonl`, and retain every finding, including unknown/refuted claims and
advisory reviewer notes. One header carries the existing receipt metadata with
kind `documentation-header`; each following line carries schema_version 1, kind
`finding` and the unchanged finding object. Empty evidence yields one unknown
header. JSON escaping must preserve embedded quotes and newlines.

The steering case begins with a simulated request to export only verified claims,
then corrects it to retain all findings. That correction must replace the current
intent, invalidate the old approval and leave completed unaffected evidence visible.
It is labeled synthetic, not attributed to Patrick as a real mistaken request.

Build may modify the captured documentation module, create
[[?src/attune_harness/documentation_export.py]], and create optional generated tests
under [[?tests/generated/test_documentation_export.py]]. These fixture effects are
distinct from the Harness engine modules below. Creating the generated-test parent
directory is explicitly allowed and journaled. No deletion is in this first profile.
Existing unrelated dirty work and all baseline acceptance inputs are protected.

The frozen `experiments/plan_build/fixtures/acceptance.py` is copied before dispatch
and kept outside worker authority. Its tests establish actual CLI output, default
compatibility, unknown/refuted/advisory preservation and empty-document behavior.
Generated tests may supplement it; a wrong feature with an always-passing generated
test must still fail. The fixture's Python files are never evidence of production
plan/build support until the actual commands create the feature and qualify it.

## Owners and exact seams

| Proposed file or existing owner | Responsibility |
| --- | --- |
| `src/attune_harness/work_contract.py` | Versioned feature-work profile; goal, missing information, explicit authoring reasons, accepted contract/artifact digest, participant assignments, budgets, revision history and dependent task validation |
| `src/attune_harness/work_runtime.py` | Planning/build policies and ordered task orchestration over existing dispatch, supervision, RunStore and RecoveryCursor; required controls and completion evidence |
| `src/attune_harness/work_effects.py` | Creation and modification proposal validation, protected-input checks, bounded POSIX effects, parent creation and reconciliation; reuse existing repair handle utilities where their contract fits |
| [[?src/attune_harness/work_cli.py]] | Plan/build argument handling and projections through existing forms; no independent renderer or state store |
| [[?src/attune_harness/spec_bridge.py]] | Optional legacy-reader import bridge; validate supported content before using the existing parser, preserve original artifact identity and import no old approval as fresh authority |
| `src/attune_harness/task_contract.py` | Route the new profile to its validator while retaining old record shapes and their validators |
| `src/attune_harness/task_policies.py` | Route execute/status/resume/control for the new profile; preserve existing profile behavior |
| `src/attune_harness/review_participants.py` | Explicit operation profile and assignment-role mapping; planner→lead and critic→reviewer are transport mappings while the declared planning role remains retained |
| `src/attune_harness/cli.py`, `src/attune_harness/cli_help.py` | Add actual plan/build routes once implemented; keep existing verbs and specialist routes |
| `src/attune_harness/review_store.py`, `src/attune_harness/recovery.py`, `src/attune_harness/process.py` | Existing authoritative persistence, operation receipts, bounded process execution and failure handling |
| `src/attune_harness/test_change.py`, `src/attune_harness/spec_handoff.py` | Existing test execution and evidence-to-Spec binding; extend their producer support only with qualified new-profile receipts |

The feature-work record owns executable scope and effects. Existing Spec lifecycle
decisions remain human authority: accepted Spec actions are bound to the same work
revision and content, and are projected into that record, not replaced by a second
approval store. A bridge cannot infer acceptance from model output, persisted prose
or an edited XML file. Base imports remain dependency-free; optional legacy imports
are deferred to the bridge. The standalone host and the current AI host must each
have a declared supported boundary rather than silently switching authorities.

## Controls selected for the first profile

| Control | Enforcer and failure behavior |
| --- | --- |
| Goal/scope/artifact and decision freshness | Work validator plus current Spec/action collector; a material correction requires the current bound decision before execution |
| Explicit participant and operation budgets | Existing registry/dispatch/process owners; no unavailable-role fallback or unapproved native call |
| Proposal scope and protected acceptance inputs | Host effect validator before any write; model claims cannot replace validation |
| Creation, collision and partial effects | POSIX handle-based effects and existing journal; uncertain operations stop for reconciliation, never blind replay |
| Required automated checks | Existing qualified runners with fixed interpreter/cwd/argv/timeout and full output; missing, failed, interrupted or unsupported required checks stop the dependent task |
| Independent artifact review | Distinct accepted role, final source/check identities and attributed findings; model agreement cannot mark the feature tested or human-approved |
| Hooks | Only explicitly supported, configured hooks are invoked through qualified boundaries. An unavailable required hook blocks; advisory feedback stays advisory. No claim of generic cross-host hook coverage |
| Human intervention and acceptance | Current revision, grammar, Spec quality gate and saved work record; corrected intent and high-severity findings interrupt auto-run |

First effect profile: a dedicated local POSIX Git checkout, explicit UTF-8 regular
files and bounded inventory. Qualify absent/existing parent directories, symlinks,
hardlinks, protected paths, collisions, fsync failures, lost acknowledgments and
resume. Unsupported hosts fail visibly. This bounds the first supported profile;
it does not remove existing capabilities or claim arbitrary-repository support.

## Pre-code evidence and consequences

The [actual preparation receipt](../../receipts/plan-build-task1-2026-09-17/qualified/result.json)
establishes:

- Existing default JSON and unknown-claim behavior pass two baseline tests. The
  proposed feature yields two assertion failures and one missing-module error;
  the unchanged-default control passes. These are expected pre-feature negatives.
- RunStore retains a new-profile record, but the task reader rejects it. Add a
  profile validator/dispatch seam; do not loosen the existing record validator.
- Existing repair refuses absent files. Creation needs its own validated effect,
  not a renamed repair route or pre-created placeholders.
- Planner and critic are rejected by the current native attempt vocabulary.
  Worker/reviewer still carry a review protocol. Map roles explicitly and qualify
  planning/building operation contracts; these probes never invoke a model.
- The existing XML reader preserves supported task fields/dependencies but ignores
  unknown elements and returns an empty list for non-task input. The optional
  bridge must disclose unsupported content and reject empty execution plans.
- A scratch exclusive-create operation leaves complete bytes after an injected
  lost acknowledgment. RecoveryCursor rejects blind replay; an observed result
  can be reconciled and reused without another write. This only probes the shared
  journal seam and a trusted existing parent, not production containment.

Retain the whole eight-task ladder. Tasks 2–7 implement and qualify the selected
local journey; Task 8 freezes native comparisons and stops before paid execution
until the concrete allocation is approved. Deterministic participant fixtures test
software behavior and controls; they cannot establish native planning competence.
