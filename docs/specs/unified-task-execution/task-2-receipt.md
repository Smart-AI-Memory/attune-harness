# Task 2 — unified intake and task records

Status: implementation and offline checks ready; **Task 2 acceptance pending, 1/8 tasks accepted**. September 16, 2026. Baseline/spec commit: `e546cc6`. No paid review or provider trial was performed.

## Delivered behavior

- `review --goal` creates a versioned task request with a durable UUID, revision, source/configuration fingerprints, explicit solo/independent-review plan, bounded budgets and task-bound assignments. `--accept` or a bound headless response accepts intake. Missing inputs can be collected interactively; noninteractive callers receive the form and its unaccepted submission. Legacy `review request.json --run-dir ...` remains a separate route.
- `task_contract.py` reuses `RunStore` for exclusive creation, writer locking, atomic persistence and checkpoint digests. Material revisions retain earlier accepted requests and clear current acceptance/grants/bindings. Identical inputs keep their existing acceptance without another action.
- Current-task answers remain visible and reusable. Explicit project profiles supply allowlisted source/query/participant defaults, with origin and corrections shown. Profiles cannot supply goals, acceptance, permissions, budgets or credentials. Each new draft is unaccepted, with provider/external permissions false.
- Real attune-forms validation checks responses bound to task/revision, checkpoint and current form definition/version. Foreign, stale, replayed, declined and unknown-control responses fail. Template entries are bounded, process-local and immutable, with bypass/clear, dependency invalidation and visible corruption recovery; they contain no accepted responses or task bindings.
- Corpora cannot ingest task state. Inputs remain project-scoped; verification manifests use the existing public loader without running verification. Explicit Voyage selection retains public generation/scope validation; selected-root overlap currently requires an external task directory.

**This is intake, not the complete runtime.** Output explicitly reports `execution_status: not_started`. No assessment, repair, task status/resume command, semantic-verification claim or provider qualification is delivered by this increment. Tasks 3–8 retain those obligations. Library helpers support intake presentation/revision; future task controls are not advertised.

## Validation

The final selected suite passes **322 tests**, including **66 new intake cases** and all 28 baseline compatibility cases. It covers review, boundaries, recovery, native-evidence/Astra/focused-native contracts, Voyage integration and MCP. New intake cases poison participant/provider constructors. A subprocess imports the public core with `-I -S`, excluding optional dependencies.

Receipt: `docs/receipts/unified-task-execution/task2-final-tests-v2.xml`. Tests used `.venv-voyage312/bin/python -B -m pytest` with `-p no:cacheprovider`. No preserved environment was upgraded. These are source-checkout checks; installed qualification belongs to Task 5 and cross-platform execution has not been claimed for this increment.

Disposable guard-removal probes detected **4/4 mutations; 6/20 selected new cases failed with the guards removed**, with zero test errors. The unmodified control passed all 20 selected cases. These cover foreign task responses (1/14 failures), stale evidence (3/4), source/state overlap (1/1) and changed form meaning (1/1). Final source/test hashes and exact replacements are retained in `docs/receipts/unified-task-execution/task2-mutations-v2/summary.json`. No skipped paid review is represented as passing; any task-workspace numeric field is explicitly the observed offline-test pass percentage.

## Intake timing

Reproduce with a new output directory:

```sh
.venv-voyage312/bin/python -B experiments/task_execution/intake.py --output /tmp/harness-intake-new --samples 30 --process-samples 5
```

The probe rotates cold/warm/bypassed order, asserts identical submission meaning and unchanged records, poisons live constructors and retains samples. Separate child processes prove that entries do not cross process boundaries. Fresh-process timing includes probe startup, source imports, poison-boundary setup and JSON transport; it is not isolated CLI startup or user-visible latency. Template, record-validation and source-validation durations are separated without answer contents in timing rows.

The final source snapshot measured presentation medians of **2.081 ms cold, 1.842 ms warm and 2.120 ms bypassed**, with a **226.895 ms** guarded fresh-process median. Template-only medians were 0.933/0.714/0.940 ms. Raw samples and source hashes: `docs/receipts/unified-task-execution/task2-intake-timing-final/`. The earlier working snapshot remains in `task2-intake-timing-v2/`. This small local difference does not establish an end-to-end speedup or justify a persistent cache.

The initial process probe failed because isolated Python excluded the sibling probe import. That attempt remains in `task2-intake-timing/`; the runner now loads its known sibling path explicitly and retains child failures. No production path depended on that measurement fix.

## Scope and remaining work

The design note preceded production edits. Additional touched seams are `review_cli.py` for explicit parser modes and `review_contract.py` for shared registry validation with the unchanged legacy minimum. `review_store.py` required no changes. Unrelated Voyage work was preserved. Raw receipts remain local/ignored; runnable measurement code and summary documentation travel with the implementation.

Final integrity check: all 154 Task 1 baseline artifacts remain unchanged. The unrelated Voyage starter, tests and profiling script match their pre-implementation hashes. `docs/receipts/unified-task-execution/task2-integrity.json` records these checks and all 38 current production-module hashes.

No wheel installation, active-host switch, push, PR, merge or release is claimed. Task 2 is ready for its existing acceptance decision. Task 3 will connect accepted intake to real evidence/participant execution through shared services.
