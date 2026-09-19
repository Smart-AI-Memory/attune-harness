# “Test this change” — existing capability map and bounded case study

2026-09-17. Patrick approved investigating testing as the first consolidation
case. This is a structured one-shot investigation, with a proposed next scope;
it does not approve or implement a new command, remove a workflow, or reopen the
completed shared-memory and release-readiness plans.

**Recommendation:** connect the existing capabilities through one change-focused
journey. Run relevant existing tests first. Offer gap analysis, generation or
repair when the evidence calls for it. Preserve specialist entry points. The main
problem demonstrated here is incomplete or inconsistent handoffs; this study
does not establish that the different testing engines should be merged.

## Inspected capabilities

AI source root: `/Users/patrickroebuck/attune-ai-memory-adoption`.
Source references below are relative to that root unless marked Harness. The
installed candidate matches the inspected source for all 14 imported modules
recorded in the [trace](../receipts/test-this-change/trace.json).

| Existing surface | Actual job and implementation | Role in the proposed journey |
|---|---|---|
| `/smart-test` | `src/attune/workspaces/smart_test.py`: staged audit, proposed paths, explicit generation choice, file hashes and submitted validation result | Reuse the useful interaction pattern; it currently starts with an audit, not a run of existing tests |
| `test_audit` / `test-audit` | MCP handler → `workflows/test_audit/workflow.py`; Agent SDK coverage/gap/planning specialists | Optional deeper analysis. Provider execution was not run in this study |
| `test_generation` / `test-gen` | MCP handler → `workflows/test_gen/workflow.py`; Agent SDK identifiers/designers/writer, guarded output directory, newly created file inventory | Useful generation specialization; output-path handoff needs repair before wiring |
| `test_gen_parallel` | MCP handler → `workflows/test_gen_parallel.py`; low-coverage discovery and batched generation | Preserve batch capability for a requested campaign; it is not equivalent to testing a selected change |
| Migration aliases | `workflows/migration.py` maps older generation names to flags on `test-gen`; current CLI calls the registry directly | Alias definitions alone do not establish compatibility; see observed failure below |
| Project index and test maintenance | `project_index/{index,file_analysis}.py`, `workflows/test_maintenance.py`: filename-based test association, impact/staleness and maintenance plans | Candidate selection hints; execution placeholders cannot serve as a qualified worker |
| Real test execution | `verification/runner.py` with `RunTestsStrategy`; separate `workflows/test_runner.py` adds opt-in local execution/coverage accounting | Reuse execution and retain useful accounting; normalize the meaning of results before connecting gates |
| `/fix-test` | Skill describes a model-guided diagnose/edit/retry loop | Preserve intervention route. Its assertion-failure → update-assertion heuristic needs stronger expected-behavior discipline |
| Pattern test generator | `test_generator/{cli,generator}.py` scaffolds tests from workflow/pattern identifiers | A different input contract and useful specialization; no evidence here warrants treating it as a duplicate of SDK generation |
| Harness `fix` and Spec acceptance | Harness `repair.py`/`task_policies.py` freeze probes and check failed-before/passed-after; AI `spec/{workspace,state}.py` retain accepted task evidence | Existing quality boundaries to connect. Harness repair currently replaces existing files; new test creation requires its own supported write contract |

This is the inventory relevant to the selected case, not a claim that every
testing-related plugin or team has been qualified. Inspection of two subprocess
runners shows overlapping execution mechanics, but different reporting purposes.
Merge decisions require caller and compatibility evidence beyond this map.

## Real change and executed trace

Selected change: the recent Spec-summary repair in `src/attune/spec/state.py`
and `src/attune/spec/workspace.py`. The two corresponding test files are
`tests/unit/spec/test_state.py` and `tests/unit/spec/test_workspace.py`.

The lead selected those tests by reading the change and direct tests. The project
index found the same pair in a disposable copy. That is **not** evidence of an
automatic, complete dependency-based selector. Its current mapping uses source
and test filename stems, takes the first matching source and stores one test
path per source; duplicate names, indirect consumers and multiple test files
need separate coverage.

The [probe](../../experiments/test_change/probe.py) copies these four files to a
temporary directory, adds labeled synthetic cases, invokes installed APIs and
records interpreter identity, module/source hashes, selected diff, exact commands
and outputs. No production source or live index is modified. The probe writes
two retained Harness receipts, `selected-change.diff` and `trace.json`; index
mutations and test artifacts are confined to the temporary copy. No provider
workflow is invoked. Parent and child socket guards recorded zero connection
attempts. The guard is deliberately local to this experiment, not a general
process sandbox or new product feature.

| Probe | Observed result | What it establishes |
|---|---|---|
| Existing verifier + real selected Spec tests | 80 passed, exit 0 | This existing executor can run the selected installed-case tests |
| Synthetic assertion failure | 1 failed, exit 1; verifier rejects | Failure remains visible |
| Empty test directory | No tests, exit 5; verifier rejects | Empty selection is not accepted as passing |
| Collection-only of real selected tests | 80 collected, exit 0; verifier says passed | Generic command success is insufficient to claim test execution |
| Real maintenance planner with two changed paths | Includes unrelated synthetic module and the experiment’s guard module | `changed_files` prioritizes work; it is not a scope boundary |
| Real maintenance executor on that disposable plan | Reports 4 successes, no Python files changed; index marks unrelated module as having tests although none exist | Placeholder success can manufacture misleading test-health metadata |
| Smart-test transitions with a labeled synthetic gap | Approved path is `tests/unit/spec/test_workspace.py`; delegate args contain only `module` | Approved exact paths are not transmitted in the generator’s argument contract |
| Generator path resolution for that source file | Defaults to `src/attune/spec/tests/generated`; rejects sibling repository test directory | Existing smart-test proposal and generator default cannot be joined as-is |
| Installed CLI `workflow run test-gen-parallel` | Exit 3, “Workflow not found” | The declared legacy alias is not wired into this CLI |

The maintenance executor’s create/update/review/delete methods currently log
“Would…” and return true (`test_maintenance.py`, methods at lines 488–508).
The caller then updates test metadata. This is a concrete defect in that utility,
not evidence that the Harness `fix` runtime has the same defect. The utility is
not in the current CLI workflow registry. Repair it before using it as an
execution backend; this finding alone is not a universal Harness release blocker.

The migration helper itself resolves `test-gen-parallel` to `test-gen` plus
`parallel=True`. The canonical generator consumes `path`, `depth`, `output_dir`;
the parallel flag does not select the MCP batch implementation. The CLI calls
`get_workflow` directly, so even the migration helper is bypassed. This corrects
the initial hypothesis that the CLI simply reached a different parallel engine.

The smart-test adapter validates submitted written paths and hashes files after
generation; that is useful evidence checking, not proof that all unauthorized
writes were prevented. Its MCP generation handler passes only the validated
source path. The generator’s output-directory guard is a different boundary.
No native generation was run, and no escaping-write claim is made here.

The audit workflow returns a report-oriented result; smart-test publication
expects structured gap entries and proposed paths. The skill currently assigns
that translation to the leading assistant. Likewise `tests.run` is a delegation
label emitted by the workspace; it is not a registered MCP tool in the inspected
server. A documented manual handoff is useful but must not be described as an
already automated end-to-end route.

Two further boundaries matter: `verification/runner.py` retains only the first
10,240 characters of each output stream, and the shared `RunTestsStrategy`
classifies by exit code. `VerificationMixin` has other callers of those generic
semantics. `CommandWorkspaceHost` keeps its records in an in-process dictionary;
the smart-test workspace is not itself a restart-safe store.

## Evidence reuse and research

This run verifies the connection to an existing executor; it does not replace
the [earlier Spec repair qualification](../spec-completion-repair-results.md):
153 Spec/host checks, 678 repository gates, 19 initial regressions failing before
the repair, changed-code coverage and 4/4 protection removals. Those are retained
historical receipts, not repeated or added to this run’s 80-test count. Broader
checks remain important because the selected pair does not cover every consumer
of the shared state format.

Pytest distinguishes successful execution, failures, interruption, internal or
usage errors, and no collected tests. Preserve those outcomes in the user-facing
result rather than reducing all nonzero outcomes to a product regression.
[Official exit-code reference](https://docs.pytest.org/en/stable/reference/exit-codes.html).

Google’s ICSE 2019 study evaluated selection algorithms on real execution data,
including flaky tests and result transitions, and found that some history-based
heuristics performed worse than expected. Our inference: qualify a selector by
missed failures and total feedback time on representative changes before claiming
that it safely replaces broader checks. This one case supports integration work,
not a performance or completeness claim.
[Assessing Transition-based Test Selection Algorithms at Google](https://research.google/pubs/assessing-transition-based-test-selection-algorithms-at-google/).

## Proposed next spec boundary

**Goal:** a human can request “test this change” through the existing intent and
grammar surface, see what will be checked and why, and receive evidence tied to
the selected change. The exact CLI spelling remains a design decision; this
report does not invent or advertise an implemented `test` verb.

**Proposed ownership to settle in the implementation spec:** a testing policy in
Harness's existing task runtime dispatches the accepted test command and owns
pytest-specific result classification. Extend the existing
`task_policies.TaskExecutionStore` / `review_store.RunStore` and
`recovery.RecoveryCursor` path for durable task evidence and restart/resume.
These currently support assessment/repair; testing requires an explicit policy
and contract extension, not relabeling an assessment. Grammar forms project that
durable state. AI's process-local smart-test workspace remains an optional
specialist interface, not the authoritative persistence owner.

Full-output retention needs an executor artifact sink **before** output is
truncated; wrapping the current returned `VerificationResult` cannot recover
discarded text. Bind its artifact digest to the task, record output limits and
mark incomplete capture explicitly. Keep the shared verifier's generic semantics
compatible; put pytest-specific execution/collection/outcome rules in the testing
policy unless a separately qualified shared change is justified.

Proposed first implementation slice:

1. Capture repository, revision/working-tree evidence and explicit change scope.
   Preserve unrelated dirty work. Select existing tests using known associations
   and inspected callers; disclose uncertainty and fall back to a broader named
   check when needed. Scope expansion must be visible.
2. Execute selected tests through an existing qualified runner with explicit
   interpreter, cwd, command, timeout and full output reference. Separate test
   collection from execution. Bind results to the tested source/test/config
   snapshot so later changes cannot reuse stale success.
3. Render one durable result through the established grammar: passed within the
   stated scope, failed, no tests, interrupted, or blocked by the environment.
   Show excluded checks and missing evidence. Use the existing receipt and task
   mechanisms; do not add another free-standing gate system.
4. Offer a specific next action only when warranted: investigate a failure,
   analyze a gap, or propose tests. Generation and repair retain explicit write
   boundaries, expected-behavior checks and actual post-change execution.
   Existing specialist routes remain available while their handoffs are repaired.

Routine execution needs no model router or automatic multi-agent audit. Models
can help interpret intent, inspect ambiguous dependencies and diagnose failures;
the host owns scope, process results, freshness and authority. Reuse Luna for
bounded routine assistance only under the routing and sampled-review discipline
already established; this study did not benchmark any model on test selection.

Acceptance cases for that slice: this real Spec repair, a real failing change,
no relevant tests, environment/collection failure, unrelated dirty files,
same-basename modules, an indirect consumer, changed configuration, stale
source/test evidence, collection-only false success, output beyond 10,240
characters, interrupted execution and restart/resume without invented or duplicate
completed work. A failed assertion must
not be “fixed” merely by weakening its expected result. Record elapsed time to
first useful result separately from the full investigation and model cost.

The highest-value first unit is the connected selection → execution → receipt
path. The maintenance false-success bug is the most urgent defect **if that
utility is selected for execution**; it is not a reason to route the new journey
through it. Alias compatibility and generation path alignment are concrete shared
repairs, tracked before those routes are advertised as interchangeable.

Reflection: naming several features “testing” hid distinct useful jobs. The
missing distinction is between choosing evidence, producing evidence and accepting
evidence. Preserve those responsibilities while making their handoffs coherent.
The experiment changed the recommendation from broad workflow consolidation to
one connected journey with explicit evidence boundaries.

## Independent review

The bounded [evidence-chain review](../receipts/test-this-change/independent-review.json)
confirmed the behavioral findings and proposed direction. Its three required
clarifications are incorporated above: retained repository receipt writes, an
explicit output/classification boundary, and named proposed dispatch/persistence
owners. The lead checked the cited source and retained the original findings;
this is not implementation or native-provider qualification.
