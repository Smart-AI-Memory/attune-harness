# Spec authority, Task 4: design note

Written September 23, 2026, after 0.5.0 shipped and Patrick ruled on the
Phase 3 note ([D20](addendum-2026-09-23.md), all as recommended). Task 4 is
[the plan's 3.1](../../plan-1.0.md): switch `plan` and `build` to the native
authority and retire the bridge; done when the R2 clean-environment journey,
plan, accept, build and review with attune-ai absent, runs and
`spec_bridge.py` is gone or reduced to the legacy reader's shim. Like the
Task 3 note, this one puts what was read from the code first, then the
design, then the decisions that are Patrick's. Nothing here is authorized
until he rules; the rulings go in this directory's next addendum.

## What D20 already settled

- **D20.1.** The refusal texts, the readiness check and the import receipts
  are contracts and stay as written; class and module names are scaffolding.
  `spec_bridge.py` shrinks to `plan_content` and `legacy_plan` under the name
  `spec_legacy.py`, with the reader tests following it; `WorkSpecBridge`,
  `import_plan` and `reimport_plan` move beside `work_cli`.
- **D20.2.** The R2 journey runs in the release gate from the `--no-deps`
  wheel with `attune` blocked, and is written down as a test and a document.
  This note finds that the wording cannot be met literally, below, and asks
  for the amended reading.
- **D20.10.** This note and the executable plugins spec come first, in
  parallel; 3.2 and 3.4 wait for 3.1 to land.

## What the code says today

**The bridge's six names, and who calls them.** `spec_bridge.py` (439 lines,
no `__all__`) exports `SPEC_APPROVAL` (`:45`), `plan_content` (`:48`),
`legacy_plan` (`:68`), `import_plan` (`:146`), `reimport_plan` (`:194`) and
`WorkSpecBridge` (`:217`, `open` at `:307`, `collect` at `:389`). Its
imports are all Harness's own: `command_workspace`, `features`,
`review_contract`, `spec_tasks`, `spec_workspace`, `task_contract`,
`work_contract`, and lazily `work_decisions`. The callers:

| Caller | Name | What it does |
|---|---|---|
| `work_cli.py:403`, used at `:406`, `:409` | `SPEC_APPROVAL` | `_guidance` builds the supported control list and asks `work_contract._supported` whether the draft's required controls are satisfiable |
| `work_cli.py:430`, used at `:439` | `WorkSpecBridge` | `_accept` opens the gate and collects an `approve_task` for `plan --accept` |
| `work_cli.py:458`, used at `:477` | `WorkSpecBridge` | `_preview_decision` opens without collecting for `plan --decision` |
| `work_cli.py:538`, called at `:544` | `import_plan` | `plan --request … --import-plan` |
| `work_cli.py:591`, called at `:593` | `reimport_plan` | `plan --reimport --checkpoint` |
| `work_contract.py:691`, `:812` | `legacy_plan` | `check_work_fresh` and `revise_work` compare the imported plan's digest; both lazy, both behind `"legacy" in request` |

`work_runtime.py`, `work_build.py` and `work_decisions.py` import nothing from
the bridge; the `build` verb (`work_cli.py:484`) touches no bridge name.

**The CLI reaches the host only through the bridge.** The only
`CommandWorkspaceHost` constructed in `src/` is `spec_bridge.py:236`, and the
only `register(...)` is `:298`, registering the bridge's anonymous
`Adapter(SpecWorkspaceAdapter)` (`:245`). That adapter overrides `create`
(`:265`) to hand back a state already at `executing` and refuses any intake
or prior state ("Reopen the bridge for a different work revision").

**What "unwired" means.** `spec_workspace._STAGES` (`:84`) names eleven
stages: `preview`, `intake`, `creating`, `gate_running`, `review`,
`approval`, `chair_required`, `blocked`, `executing`, `task_gate`,
`receipt`. Because the bridge starts at `executing` and publishes only
`task_result`, these have no caller in `src/`:
`SpecWorkspaceAdapter.create` (`:384`) and `_resume` (`:534`), the four
`spec_intake` names they use, `_publish_artifacts` (`:620`),
`_publish_lifecycle` (`:654`), `_publish_task_started` (`:702`), the
`execution_progress` branch (`:520`), and the `apply` branches for
`preview`, `review`, `approval`, `chair_required` and `blocked`
(`:451`–`:500`). Only `tests/test_spec_workspace.py` (32 tests) and two
places in `tests/test_connected_journey.py` exercise them.

**Tests and the block.** Four files import the bridge or its names:
`test_spec_bridge_gate.py` (14 tests, `WorkSpecBridge`),
`test_spec_bridge_legacy.py` (7, `legacy_plan`), `test_spec_state.py` (55,
`plan_content`) and `test_features.py` (1 of 10, `legacy_plan`); 139
collected. `import_plan` and `reimport_plan` have no direct test and are
exercised through `work_cli` only. There is no `conftest.py`; the block is a
per-file autouse fixture that sets `attune` and its submodules to `None` in
`sys.modules`, plus one subprocess in the gate file that blocks
`attune_forms` too and asserts `--help` still works. The static half is
`test_no_attune_runtime_import.py` with `KNOWN = set()`.

**Nothing runs plan, accept, build and review end to end.** The gate test
runs `plan --accept` through `main` and stops at `accepted`;
`test_work_build.py` calls `build_work` directly on fixture records;
`docs/cli-guide.md:74` is the only documented sequence and ends at `resume`.
`scripts/check_installed.py` exercises no plan or build verb; `plan` and
`review` appear only as help-text substrings (`:82`–`:87`). The release
gate's only extra assertion on the core report is about memory
(`publish-pypi.yml:92`).

**R2 as defined.** `docs/specs/spec-authority/README.md:90`: "Plan/build
completes an approved-spec journey in a clean environment with Attune AI
absent. The import check passes in CI." (The shared-memory spec has its own,
unrelated R2.)

**What the journey needs at runtime.** None of `work_build.py`,
`work_runtime.py`, `work_decisions.py` or `review_cli.py` imports anything
outside the standard library and the package. Two steps need `attune-forms`
at call time through `features.require_feature`: `plan --accept` (and
`--decision`), because the host renders the decision
(`command_workspace.py:71`, `spec_workspace.py:74`), and `review` on both
of its routes (`review_contract.py:118`, `:154`; `task_contract.py:336`,
`:410`). `build` needs it not at all. `attune-forms==0.17.0` is a base
dependency since D15 (`pyproject.toml:16`), with `review = []` kept as an
empty extra.

**The seven plans.** `.claude/plans/` on `wip/local-snapshot-2026-09-19`,
seven files, readable with `git show`; `.claude/` is not tracked on `main`.

## The finding that amends D20.2

The release gate installs the wheel with `pip install --no-index --no-deps`
(`publish-pypi.yml:88`, `:211`, `:216`). In that environment `attune_forms`
is absent, so `plan --accept` exits 2 with the install hint and `review`
refuses the same way; both are tested behaviours
(`test_spec_bridge_gate.py:529`). The R2 journey therefore cannot run from
the `--no-deps` wheel as D20.2 says. What the gate can prove there is the
half that needs no forms, `plan --request` and `build`, plus the exact
refusal texts for accept and review; the full journey has to run where the
base dependencies are installed: the platform matrix, which installs
`attune-harness[review,voyage,mcp,redis]` from the built wheel on all three
platforms, and the post-publish index install that step 8 of the runbook
already runs with `check_installed.py --mode all`. That is the reading this
note asks Patrick to adopt (decision 1). It is the same shape the memory
verbs already have in the gate: the raw tier from `--no-deps`, the document
tiers where attune-rag is installed.

A second constraint on the gate journey: `build` dispatches work to a
participant, and the gate makes no model calls. The precedent is
`test_work_build.py::test_build_command_worker_and_reviewer_use_actual_subprocesses`,
where the worker and the reviewer are `command` participants, local scripts
run through `process.invoke`. The gate journey uses the same: a fixture
project, a request whose worker and reviewer are two small scripts shipped
under `tests/fixtures/` or generated by the check, and an acceptance through
the console approval the CI already submits for the gate tests.

## The design

### 4.1 `plan` owns the host; the bridge's switch names move

`work_cli` constructs `CommandWorkspaceHost` and registers
`SpecWorkspaceAdapter` itself, in a small module beside it, `work_accept.py`,
which is where `WorkSpecBridge` (renamed `WorkAcceptance`), `SPEC_APPROVAL`,
`import_plan` and `reimport_plan` go with their words unchanged. The
anonymous adapter subclass goes with them for now: its override of `create`
is what keeps the workspace at `executing`, and 4.3 decides its fate.
`work_contract`'s two lazy imports move to `spec_legacy`. The 139 collected
tests keep passing with only their import lines changed; that is the first
half of the acceptance proof.

### 4.2 `spec_bridge.py` becomes `spec_legacy.py`

`plan_content` and `legacy_plan` only, with the module docstring stating the
contract the verdicts recorded: a single trailing state comment, schema
versions 1 and 2, a refusal for anything else, and disclosure of everything
unmapped. `test_spec_bridge_legacy.py` becomes `test_spec_legacy.py`;
`test_spec_state.py`'s agreement class points at the new name. No
compatibility import is left behind: `spec_bridge` was never a public name
and the import guard proves nothing imports it.

### 4.3 The stages: the execution half wired, the creation half dormant

Task 4 wires the stages the plan and build journey needs and no other:
`approval` with `start_execution`, `executing`, `task_gate` with the five
actions Task 3 wired, `receipt`, and the two lifecycle gates
`chair_required` and `blocked` that a high-severity build result raises.
That is `SpecWorkspaceAdapter.create` for a draft that has an accepted
intent, `_publish_lifecycle` and `_publish_task_started`, and the `approval`,
`chair_required` and `blocked` branches of `apply`. The creation half,
`preview`, `intake`, `creating`, `gate_running` and `review`, is Attune AI's
spec-creation interview; Harness's intent comes from `plan --request`, and a
second intake would be a second authority (D2). It stays carried and
dormant, tested by its 32 tests, with a Phase 4 decision on deletion once
4.4 ends the transition. Decision 2 asks whether Patrick wants that or the
whole ladder.

### 4.4 The R2 journey, three times

- **As a test:** `tests/test_r2_journey.py`, a subprocess journey with
  `attune` blocked the way the gate file blocks it: `plan --request` on a
  fixture project, `--accept --checkpoint`, `build` with two command
  participants, `review` of the result, and `status`; asserting each
  envelope's `status` and that the import check's sentinel never appears.
  In the platform selection, so the Windows jobs run it too.
- **As a document:** `docs/journeys/r2-clean-environment.md`, the command
  sequence with the envelopes it produces, linked from the CLI guide where
  the sequence now stops at `resume`.
- **In the gate:** `check_installed.py --mode core` gains a `journey`
  section: from `--no-deps`, `plan --request` and `build` run and `plan
  --accept` and `review` are asserted to refuse with the install hint; from
  `--mode all`, the whole journey runs. `publish-pypi.yml:92` asserts on both
  reports, beside the memory assertions.

### 4.5 The differential, as Phase 2 had one

Before the switch lands, the seven plans and the gate suite's task
directories are run through the bridge and through the native host, and
every envelope, receipt and refusal text is compared; zero disagreements is
the bar, as it was for the memory reader against the adapter. The
comparison is a one-off in a scratch environment, reported in the pull
request, since after the switch there is no bridge to compare against.

## Decisions for Patrick

1. **D20.2's reading.** Recommended: the `--no-deps` gate proves `plan
   --request`, `build` and the exact refusals of `accept` and `review`; the
   full journey runs in the platform matrix and the post-publish `--mode
   all` check, which are the environments that have `attune-forms`. The
   alternative, shipping forms into the `--no-deps` gate, would make the
   gate's offline check stop meaning what it means.
2. **Which stages.** Recommended: the execution half wired (4.3), the
   creation half dormant with a Phase 4 deletion decision. Alternative: wire
   the whole ladder, which gives Harness a second intake beside `plan
   --request`.
3. **Names.** Recommended: `spec_legacy.py`, `work_accept.py`,
   `WorkAcceptance`; every refusal text kept verbatim, including "Reopen the
   bridge for a different work revision", until a deliberate diff with a
   changelog line renames it.
4. **The gate's participants.** Recommended: two command participants,
   local scripts, no model; the build's receipt shows the worker's actual
   subprocess as the existing test does.
5. **The differential is the acceptance proof.** Recommended: yes, zero
   disagreements over the seven plans and the gate's task directories
   before the bridge is deleted.
6. **Sequencing.** Recommended: three pull requests, each reviewed under
   the brief: (a) 4.1 and 4.5, the switch with its differential; (b) 4.2 and
   4.3, the shrink and the stages; (c) 4.4, the journey three times. (a) and
   (b) touch the same files and go in order; (c) may start beside (b).

## Evidence Task 4 ends with

`spec_bridge.py` gone and `spec_legacy.py` in its place with the reader
tests; `work_cli` constructing the host; the 139 collected tests green with
import lines changed and nothing else; the differential's zero
disagreements in a pull request; the R2 journey green as a test on all
three platforms, written as a document, and asserted in the release gate
from both installs; the import guard still at `KNOWN = set()`.

## Size

Three reviewed pull requests, against the plan's estimate of two to three.
The largest is (a): the host construction and the differential. (c) is
mostly scripts and tests, and its Windows run is the one to watch, since the
journey's subprocess participants meet the platform's path and encoding
traps that `docs/windows-traps.md` lists.
