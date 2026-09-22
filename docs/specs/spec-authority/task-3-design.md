# Spec authority, Task 3: design note

September 22, 2026. Task 2 is built and waiting at the merge gate: #34 (2.2),
#42 (2.3) and #43 (2.4), stacked. Task 3 is "specify and implement approval
and gate decisions on the task engine", with the evidence "R1 and R3 tests;
stale and replayed decisions refused". **Status: proposed. It names five
decisions that are Patrick's. No code starts until he says go.**

## What Task 3 has to end with

After Task 3, `spec_bridge.py` imports nothing from Attune AI, so the import
check's `KNOWN` list shrinks to `memory_context.py`, and an approved-spec
journey runs in a clean environment (R2). Every decision that today passes
through Attune AI's Spec collector still passes through a human (R3), and each
one is recorded in Harness's task store and nowhere else (R1).

## What exists today, measured

**Harness already has the authority store.** `work_contract.bind_work_acceptance`
takes the store's lease, requires an unaccepted draft ("do not replay a
decision"), checks freshness, and saves the decision with the collector's
receipt. `work_decisions.retain_decision` saves the decision *text* bound to
the work revision by digest before a form is shown, and
`require_current_decision` refuses a response whose saved text changed or was
already collected. Stale and replayed decisions are refused there today, across
processes, because the lease and the saved record are files. R1's store is not
new work.

**What the bridge borrows from Attune AI**, read at `b89f7953f`:

| Module | Lines | Tests | What the bridge takes |
| --- | ---: | ---: | --- |
| `elicitation/command_workspace.py` | 504 | 22 | `CommandWorkspaceHost` (open, collect, publish; one nonce per rendered view; refuses a response when the re-projected view or its contract hash drifted; refuses a terminal workspace) and `CommandWorkspaceProjection` |
| `spec/workspace.py` | 995 | 23 | `SpecWorkspaceAdapter` (eleven stages, the action table below, `publish` for trusted events, `_resume` from a plan and its state) and `SpecWorkspaceState` |
| `elicitation/spec_intake.py` | 229 | 11 | four names: `OTHER`, `area_candidates`, `existing_spec_slugs`, `compose_spec_contract`, about 50 lines together |

Both modules already depend on `attune_forms`, which is Harness's `review`
extra, for views, bindings and rendering. Neither touches a registry, a plugin
loader or an MCP host. `command_workspace.py` holds everything in memory: a
dict of records and a dict of `asyncio.Lock` keyed by workspace id, created
on first use and never evicted. Its one side effect is telemetry:
`attune_forms.form_events.log_workspace_stage` on render and on collect,
which appends under `ATTUNE_FORMS_HOME`, else `ATTUNE_HOME`, else `~/.attune`.
`workspace.py` writes nothing; on task completion it returns a `save_state`
payload and leaves writing it to the caller. It reads plans through `read_spec`
(now 2.2) and state through `load_state` (now 2.3), and reaches back into
Harness for `spec_handoff.check_test_evidence`, the one place the two products
import each other.

**The human decisions, as the action table has them.** Each is a
`(stage, action id, confirmed)` triple validated per stage; there is no
separate decision object.

| Stage | Action | Effect |
| --- | --- | --- |
| preview | `create_spec` | to creating |
| review | `approve_plan` | to approval |
| approval | `start_execution` | to gate_running |
| chair_required | `acknowledge_gate` (confirmed) | to the gate's next stage |
| blocked | `retry_gate` | to gate_running |
| task_gate | `approve_task`, `redo_task`, `auto_run_remaining` | complete, redo, or complete and set auto-run |
| task_gate, high severity | `fix_retry`, `acknowledge_risk` (confirmed) | redo, or complete with the risk acknowledged |

The bridge uses only the task gate: it builds a state already in `executing`,
publishes one `task_result` event, and turns `approve_task` or
`auto_run_remaining` into `bind_work_acceptance`. Every other action returns
without a grant.

## The design

**Carry both modules, adapt at three seams, and let the task store be the
authority.** The host stays what it is, an in-process collector whose records
die with the process, which is already the bridge's stance ("reopening after
restart issues fresh authority"). Nothing about cross-process refusal is asked
of its locks: every authority-changing action is followed, as today, by a
store operation under the lease, and that is where a stale or replayed
decision is refused. The `asyncio.Lock` becomes what it can honestly be, a
guard against two coroutines in one process, and R1 is proved by tests that
run two processes against one task directory.

The three seams:

1. **`command_workspace.py`.** Remove the `attune_forms.form_events` telemetry
   (decision 2 below says what, if anything, replaces it). Evict a workspace's
   record and lock when it goes terminal, so a long-lived host does not grow
   without bound. Everything else carries as written, with its 22 tests.
2. **`spec_intake.py`.** Carry the four names as `attune_harness/spec_intake.py`,
   about 50 lines, taking `FormSchema` and the template types from
   `attune_forms` directly, and without line 116's write into a global template
   registry at import time. Its 11 tests are mostly about the registry and the
   full intake form; the four names get their own.
3. **`workspace.py`.** Change its imports to Harness's modules (`spec_tasks`,
   `spec_state`, `paths`, `spec_intake`, and a relative import of
   `spec_handoff`, which ends the mutual import). Nothing in its state machine
   changes. Its 23 tests carry, with their fixtures' plans given a
   `schema_version` as 2.3 required.

Then `spec_bridge.py` imports the carried modules, and the import check's
`KNOWN` list drops it.

**Rejected.** Writing a smaller host around the task store and dropping
`command_workspace.py`: it would lose the nonce, drift and terminal checks and
their tests for a saving of perhaps 300 lines, and Task 1 found the module's
protocol already separates host from domain state, which is what D2 wants.
Keeping a runtime `import attune` for the collector: refused by R2 and D8.

## Decisions for Patrick

1. **The approach above,** carry and adapt with the store as authority, rather
   than a rewrite.
2. **Telemetry.** The host logs a render and a collect event to Attune AI's
   home directory. Options: drop it; or write the same two events into the
   task directory beside `decision.json`, where they would be evidence rather
   than telemetry. The note's recommendation is the second, because it costs
   about ten lines and makes "who saw what, when" inspectable per task.
3. **Where progress lives.** 2.3 carried `save_state`, which writes progress
   into the plan's trailing comment. R1 says decisions are recorded in the task
   store "and nowhere else". For Harness's own plans, the recommendation is:
   the task store is the authority and the plan comment is a projection written
   after the store, never read as authority for a decision; D6's "read and
   convert, never write back" stays the rule for other projects' plans. If
   Patrick prefers, the writer is simply never called and plans stay read-only.
4. **Which stages Harness exposes.** The bridge uses the task gate only. The
   other eight stages (intake, creating, review, approval, lifecycle gates) are
   Attune AI's spec-creation journey. Carrying `workspace.py` brings them all;
   the question is whether Task 3 wires any of them, or only the task gate,
   leaving the rest for Task 4's switch of plan/build. The recommendation is
   the task gate only in Task 3.
5. **Sequencing and review.** Four pull requests in order, each with a
   different-model review: 3.1 `command_workspace.py`; 3.2 the four intake
   names; 3.3 `workspace.py`; 3.4 the bridge switch with the R1 and R3 tests.
   3.3 cannot start before 3.1 and 3.2 merge, and 3.4 cannot start before 3.3.

## Tests the task must end with

- **R1, across processes.** Two processes open the same task directory; the
  first collects a decision; the second's collect is refused with the existing
  "reopen the current decision" message; the store holds one acceptance. A
  replay of the first response after acceptance is refused ("do not replay a
  decision"). A response whose saved display digest changed is refused.
- **R3, every gate.** For each row of the action table that Task 3 wires: the
  action is refused without a nonce, refused when the view drifted, refused
  when the workspace is terminal, and `acknowledge_gate` and `acknowledge_risk`
  are refused without `confirmed`. Auto-run grants nothing until an explicit
  `auto_run_remaining`.
- **R2.** The import check's `KNOWN` list is `{"memory_context.py"}`, and the
  clean-environment journey test from Task 4's plan runs the task gate with
  Attune AI blocked, as `test_spec_bridge_legacy.py` does for the reader.

## Size, from what Task 2 measured

Task 2's steps, wall time from first commit to the review fix landing, read
from the GitHub API on September 22:

| Step | Lines carried or written | Tests | Wall time |
| --- | ---: | ---: | --- |
| 2.1 `paths.py` | 306 | 62 | 4 h 15 min to merge, including one review round |
| 2.2 `spec_tasks.py` | 753 | 36 | about 1 h 30 min, including one review round |
| 2.3 `spec_state.py` | 969 | 84 | about 50 min, including one review round with two blockers |
| 2.4 bridge reader | 91 | 7 | about 20 min, including one review round |

Task 3 carries about 1,550 lines with 56 tests and adds the R1 and R3 tests.
By the Task 2 rate that is two to three sessions of work, if the decisions
above are settled first. No token figure is given: the sessions did not
record one, which is itself logged as an opportunity.

## What this note does not do

It does not start Task 3, change any module, or decide anything. It does not
size Task 4.
