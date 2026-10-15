# Native Windows feature parity

**Status: approved for staged implementation.** October 15, 2026. Source baseline: `017d1ba833acd0549d628e4b4f040b77b5e45594`.
Patrick selected feature parity, including the currently POSIX-only features,
and allowed more than one PR. This replaces the initial one-PR effort cap.

Read [the design and acceptance criteria](design.md),
[the fixture producers](fixtures.md), then [the ordered tasks](tasks.md).
Patrick separately authorized necessary paid validation for this Windows
compatibility process on October 15, 2026, with a $50 total spending ceiling.
Approval does not authorize merges, releases, repository settings changes or
workflow dispatches.

## Outcome and completion

A person using native Windows can complete every supported Harness CLI feature
within its declared input and safety profile, including testing changes,
file-based memory, saved memory/tasks and native memory proposals. Windows must
not require WSL or refuse a feature solely because the host is Windows.

Done means all requirements R1–R8 pass from the installed wheel, the full source
suite passes in Windows Server CI with Python 3.10 and 3.12, the documented
installed-wheel journeys also pass on Windows 11 desktop, and
each code PR has its required independent review. Existing macOS and Linux
behavior and historical records remain compatible. Completion review: pending
for implementation; the planning review is recorded in [tasks](tasks.md#planning-review).

“Feature parity” covers software behavior, data preservation and failure
reporting. It does not turn offline SDK tests into live provider qualification,
or remove constraints such as a dedicated checkout, bounded input, explicit
authority, or refusal of links and unsafe volumes. Any additional Windows-only
restriction must be visible and approved before the affected requirement closes.

## Verified starting point

| Observation | Evidence | Consequence |
|---|---|---|
| Selected installed-wheel checks passed on Windows Python 3.10/3.12 | [Library qualification 38267127140](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/38267127140) at the baseline SHA | This does not establish complete feature coverage |
| The full source suite runs only on Ubuntu | [qualification.yml](../../../.github/workflows/qualification.yml), `full-suite` | Native Windows failures outside the selection can remain invisible |
| Windows effects have an existing native implementation | [Backend run 38267127488](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/38267127488), [windows_effects.py](../../../src/attune_harness/windows_effects.py) | Reuse qualified primitives; do not replace them with path-based effects |
| Testing refuses Windows before intake | [test_change.py:64](../../../src/attune_harness/test_change.py#L64) | Port admission, environment and evidence together |
| File-memory capture refuses Windows | [memory_reader.py:134](../../../src/attune_harness/memory_reader.py#L134) | Add a read-only native backend, including pointer-verdict reads |
| Every saved-storage command refuses non-POSIX hosts | [memory_saved.py:214](../../../src/attune_harness/memory_saved.py#L214) | Implement locking, private storage and durable commit together |
| Experimental native memory preflight refuses Windows | [memory_native.py:449](../../../src/attune_harness/memory_native.py#L449) | Qualify the actual supervised helper, with the pinned SDK and no live calls |
| The saved-memory platform table says “All three” | [supported-journeys.md:57](../../supported-journeys.md#L57), contradicted by the saved-store owner above | Correct the current claim before advertising parity |

[Draft PR #266](https://github.com/Smart-AI-Memory/attune-harness/pull/266) adds
the first full Windows source-suite measurement. It is an audit vehicle, not
completed parity. Its measurements must be inspected before implementation is
declared ready. Unfinished implementation changes are retained in a task-owned
stash and are not part of this specification.

## Decisions

Patrick approved D1–D5 on October 15, 2026, including the staged delivery plan.
The $50 cap covers the entire process. Continue fixes, reviews and qualification
until a required approval or missing information blocks the affected work.
Merges and publishing remain Patrick's decisions.

| Decision | Recommendation and boundary |
|---|---|
| D1: Native qualification profile — approved | Require Windows 11 desktop validation and Windows Server 2022/2025 CI before declaring parity, with Python 3.10/3.12, fixed local NTFS and standard user permissions. Record architecture and OS build. Desktop validation is part of completion; server CI cannot substitute for it |
| D2: Data and bounds — approved | Preserve public schemas, accepted POSIX records and their version tokens. Windows must match the existing memory limits: 4,096 Markdown files per root, 8 MiB per file and 64 MiB per query snapshot. Adapt native enumeration rather than inheriting the effects helper's smaller 2,048-entry bound. Lower initial Windows limits are not approved |
| D3: Saved-store durability — approved | Require a justified native equivalent for the current file-flush, atomic-replace and parent-flush contract under standard user permissions. Run the bounded proof in T2 before implementing production saved storage. If equivalence cannot be established, stop saved-storage work and return to Patrick with evidence and alternatives; other independent approved work may continue. An app-crash-only profile is not approved |
| D4: Provider qualification — approved | Keep comprehensive offline SDK/Windows-helper tests in CI, then perform controlled live Windows validation through the production transport. Necessary paid validation is authorized with one $50 total cap across this entire Windows compatibility process, including contributors, runs and retries; it does not reset per agent or PR. Use synthetic data and existing allowed models, bound input/output, retain actual usage/results and reserve worst-case cost before dispatch. No automatic retries. No new per-run spending approval is needed within the authorized scope and remaining cap |
| D5: Delivery — approved | Land independently reviewable PRs through main, in the order below. New platform claims follow receipts, after the implementation and its final review |

## Walk the command journeys

These are source-level walks of the intended fixtures, not claims that Windows
already passes them. Each implementation PR replaces its current blocker with
observed native evidence. A new fixture
must satisfy every validator it reaches, not just the CLI parser.

The fixture owns a disposable dedicated Git checkout, commits its initial files,
then changes one source file without committing. Its interpreter is absolute,
outside the checkout and has pytest installed. Task state is a new sibling of
the checkout. Memory configs and request files are bounded regular UTF-8 JSON
written by the trusted fixture; the root directories are disjoint from job state.
No fixture modifies the developer's project, keyring, live memories or Redis.
The repair/build fixture uses the existing starter command worker and reviewer,
with no tools or review mode; these are offline examples, not model-quality
reviewers. Seed that registry before `init` and use the same file for preview,
acceptance and execution. Its `python` command resolves to the fixture venv.
The failing fixture has `calc.py` return `a - b` and a protected test asserting
`add(2, 2) == 4`; the example's exact-one replacement therefore applies.

### Testing, repair and build

| Command in order | Refusal owner and source | How the prior fixture/output satisfies it; remaining Windows work |
|---|---|---|
| `init --for fix --project ROOT --scope calc.py --interpreter PY --tests tests/test_calc.py` | Required flags: [init_cli.py:229](../../../src/attune_harness/init_cli.py#L229). Dedicated checkout/disjoint state/scope: [repair.py:172](../../../src/attune_harness/repair.py#L172), lines 174–180. Probe environment/oracle: [repair.py:131](../../../src/attune_harness/repair.py#L131), lines 145–165 | The fixture supplies every required flag, an existing editable UTF-8 file, protected test outside scope, and new external task directory. `pytest_probe` already supplies one Windows `SystemRoot` at [init_cli.py:185](../../../src/attune_harness/init_cli.py#L185). T6 walks its emitted command in real PowerShell |
| Run the printed `fix` preview with the fixture registry, then accept its exact checkpoint with `--allow-external` | Failing baseline required: [task_policies.py:302](../../../src/attune_harness/task_policies.py#L302). Final probe and requested review: lines 312–334. Scope and preimage: [repair.py:238](../../../src/attune_harness/repair.py#L238), lines 240–247 | The failing protected test and exact-one starter replacement are defined above. Use distinct `lead`/`reviewer` identities from the same seeded registry and accept only the saved checkpoint. The command adapters need explicit external execution authority but call no provider. Preserve protected bytes and record the actual final probe; T6 must cover Windows effects and recovery rather than accepting a recorded refusal |
| `test --project ROOT --scope calc.py --interpreter PY --task-dir TEST_TASK` | Inputs/platform/state/interpreter/limits: [test_change.py:61](../../../src/attune_harness/test_change.py#L61), lines 64–95. Changed scope: [test_scope.py:161](../../../src/attune_harness/test_scope.py#L161) | The fixture's uncommitted source change satisfies scope. Use a new external task directory and existing interpreter; defaults satisfy timeout/output/plugin bounds. Current Windows refusal is T3's explicit blocker. Port its fixed environment at [test_execution.py:177](../../../src/attune_harness/test_execution.py#L177) |
| `test --task-dir TEST_TASK --checkpoint PREVIEW_DIGEST --accept` | No overrides: [test_cli.py:94](../../../src/attune_harness/test_cli.py#L94). Current draft/checkpoint: [test_change.py:274](../../../src/attune_harness/test_change.py#L274). Source and runtime freshness: lines 254–262 | Read the exact digest from preview; pass no project/scope/interpreter overrides. Do not edit inputs between steps. Execution must produce one observed pytest event with valid artifacts, not merely exit zero |
| `status-task TEST_TASK`, then `resume-task TEST_TASK` | Result/request binding and single dispatch: [test_change.py:228](../../../src/attune_harness/test_change.py#L228), lines 231–241; freshness above | Reuse the completed owner. Assert byte-identical evidence and one dispatch; separately test cancellation, timeout and unknown outcomes without redispatch |
| `init --for plan --goal "Repair addition" --project ROOT --scope calc.py --interpreter PY --tests tests/test_calc.py --task-dir PLAN_TASK` | Required inputs/new task/request: [init_cli.py:328](../../../src/attune_harness/init_cli.py#L328), lines 334–338. Request size: line 365. Manifest validation: [work_effects.py:157](../../../src/attune_harness/work_effects.py#L157), lines 162–193 | The seeded registry exists before snapshot; scope and oracle are distinct existing files with no missing parents. `init` calls both `draft_request` and build `preflight` before writing, at [init_cli.py:358](../../../src/attune_harness/init_cli.py#L358). Its small generated request is written beside PLAN_TASK, outside ROOT |
| `plan --request WORK_FILE --project ROOT --config REGISTRY --task-dir PLAN_TASK` | Registry/request/root validation: [work_contract.py:428](../../../src/attune_harness/work_contract.py#L428), lines 429–456; exclusive run creation: [review_store.py:70](../../../src/attune_harness/review_store.py#L70) | WORK_FILE is `init`'s actual output path; use the identical registry/root and a still-absent PLAN_TASK. Do not change the checkout after freeze. The writer has already called this same draft owner |
| `plan --task-dir PLAN_TASK --accept --checkpoint PREVIEW_DIGEST` | Exact approval checkpoint: [work_cli.py:470](../../../src/attune_harness/work_cli.py#L470). Material intent/planner/bindings: [work_contract.py:589](../../../src/attune_harness/work_contract.py#L589), lines 591–594; freshness: line 719 | Use the returned digest. The generated request has a nonempty goal/scope/acceptance, no unanswered material questions, a planner assignment and no required human controls. Inputs and registry remain unchanged |
| `build PLAN_TASK --allow-external` | Manifest/tasks/probes/output ownership: [work_build.py:99](../../../src/attune_harness/work_build.py#L99), lines 105–108. Roles/budgets: lines 118–128. Tools/review mode/external/native grants: lines 739–754 | The generated request has one `change` task, matching `change`/`final` probes, one output owner and sufficient DEFAULT_BUDGETS. Seeded command roles are distinct, have no tools/review mode, and receive explicit external authority; they are not native model adapters. The actual failing source matches their exact-one replacement |
| `status PLAN_TASK`, then completed `test --from-task PLAN_TASK --interpreter PY --task-dir HANDOFF_TASK` | Handoff excludes scope/project overrides: [test_change.py:56](../../../src/attune_harness/test_change.py#L56); completed-source validation: [task_handoff.py](../../../src/attune_harness/task_handoff.py); testing freshness and evidence checks above | Status reads completed work. Pass the actual completed owner and a new external HANDOFF_TASK, with no project/scope overrides. T3/T6 prove the native completed handoff and separately exercise uncertain-effect recovery; status does not manufacture completion |

### File-memory reads

Use `attune-harness memory --config ROOTS_CONFIG` as the prefix.
The [fixture producers](fixtures.md) specify the matching authority and content;
document-tier tests install the pinned `attune-rag==1.2.0`. Raw-only no-dependency
qualification remains a separate success profile.

| Command in order | Refusal owner and source | How the previous artifact satisfies it; remaining Windows work |
|---|---|---|
| `capabilities`, then `recall Aurora --k 10` | Root authority/canonical paths: [memory_reader.py:69](../../../src/attune_harness/memory_reader.py#L69), lines 77–103. Capture safety/platform: lines 113–165. Query bounds: line 285 | Fixture roots contain current raw rows and matching personal/curated documents with authorized labels. All paths are canonical and outside system directories. T4 supplies native capture/enumeration and preserves existing ranking/bounds |
| Save distinct raw and document handles unchanged, then `resolve HANDLE_FILE` for each | Foreign authority: [memory_reader.py:314](../../../src/attune_harness/memory_reader.py#L314). Expiry/scope/version: lines 323–341 | Select by actual root ID/path, not list position; the output supplies exact authority, locator, ID and version. Raw expiry/scope cases use the raw handle. Document source/sidecar changes invalidate the document handle; a raw handle does not bind document sidecars |
| Save the whole recall packet unchanged, then `refresh PACKET_FILE` | Shape/version and authority: [memory_context.py:97](../../../src/attune_harness/memory_context.py#L97), line 99 | Reuse the packet, not a reconstructed subset. Unchanged inputs remain valid; correction, expiry, withdrawal and verdict changes invalidate the expected IDs |
| `serve --for Aurora` with synthetic Redis and file-verdict evidence | File-verdict failure suppression: [memory_serving.py:49](../../../src/attune_harness/memory_serving.py#L49) | Fixture Redis config, active membership and pointers map canonical paths/stems to exactly one authorized personal/curated root. T4 enables safe Windows pointers and suppresses wrong, unreadable, replaced or unsupported-volume pointers while eligible curated nodes still serve. Output is a text banner or skipped diagnostic with exit 0, not a recall packet |

### Saved memory and tasks

Use `attune-harness memory --config SAVED_CONFIG saved` as the prefix. The
fixture supplies one absolute store root, global scope, a fresh nonempty string
request ID of at most 256 UTF-8 bytes for each distinct mutation, and bounded
text/source fields. Request IDs need not be UUIDs. Keep the worker-disable flag
unset. [Exact payload producers](fixtures.md#saved-lifecycle) bind every revision
to the corresponding observed result.

| Command in order | Refusal owner and source | How the previous artifact satisfies it; remaining Windows work |
|---|---|---|
| `save --request SAVE_FILE`, then repeat it identically | Request/intent schema: [memory_saved.py:38](../../../src/attune_harness/memory_saved.py#L38), lines 109–127 and 346. Reused ID with different content: line 353. Platform: line 214 | The fixture supplies valid memory intent. Preserve the same file and request ID for replay; expect one canonical UUID, revision 1, and one history entry. T2/T5 own the native storage blocker |
| `show ID --scope SCOPE_FILE`, `list --scope SCOPE_FILE`, `search acceptance --scope SCOPE_FILE` | UUID/scope/visibility: [memory_saved.py:73](../../../src/attune_harness/memory_saved.py#L73), line 440. Query bounds: line 47 | Use the returned UUID, unchanged scope and text actually saved. Reads use authoritative state, including when the optional index is absent |
| `revise ID --request REVISE_FILE`, then `forget ID --request FORGET_FILE` | Mutation envelope: [memory_saved_cli.py:66](../../../src/attune_harness/memory_saved_cli.py#L66). Changes/scope/revision/withdrawal: [memory_saved.py:397](../../../src/attune_harness/memory_saved.py#L397), lines 362–366 | Revise uses a fresh request ID and returned revision 1; forget uses another ID and returned revision 2. Expect withdrawn revision 3. The identical original save replay must not resurrect it |
| `show ID --scope SCOPE_FILE --history` | Withdrawn visibility: [memory_saved.py:440](../../../src/attune_harness/memory_saved.py#L440) | `--history` requests withdrawn records explicitly. Original-save replay returns historical revision 1, while current state remains withdrawn revision 3 with three history entries. Do not use replay's revision for later mutations. Ordinary show refuses; list/search omit the withdrawn record |
| `save --request TASK_SAVE_FILE`, then `complete TASK_ID --request COMPLETE_FILE`; `list --scope SCOPE_FILE --pending-review` | Task next action: [memory_saved.py:119](../../../src/attune_harness/memory_saved.py#L119). Execution restrictions: lines 125–127. Completion: line 377. Pending-review shape: lines 84–103 | Supply task `next_action`, no execution reference, valid pending review, matching scope, fresh ID and returned revision. Completing the task must retain its pending review checkpoint |
| `reindex --scope SCOPE_FILE` | Index configuration: [memory_saved_index.py:19](../../../src/attune_harness/memory_saved_index.py#L19), lines 22–24. Persistence uncertainty: [memory_saved.py:337](../../../src/attune_harness/memory_saved.py#L337) | Without Redis expect disabled. With an unavailable test index expect pending and readable authoritative data. Failure to persist index metadata remains uncertain |

### Native memory proposal transport

Use the existing `memory --config CONFIG --jobs JOB_ROOT --native-config NATIVE_CONFIG`
prefix. The test fixture supplies matching host authority, a valid explicit
envelope/policy, and a dummy key. JOB_ROOT already exists, is canonical/absolute,
and neither contains nor is inside a memory root ([memory_context.py:35](../../../src/attune_harness/memory_context.py#L35)).
RUN_ID is fresh and matches `[A-Za-z0-9_-]{1,64}`; JOB_ID is caller-selected
nonempty text of at most 128 UTF-8 bytes. Keep `ATTUNE_MEMORY_WORKER=0` unset.
The [fixture contract](fixtures.md#native-proposal) names existing valid producers
and the new child-only in-memory HTTP responder; external network is denied.

| Command in order | Refusal owner and source | How the prior fixture/output satisfies it; remaining Windows work |
|---|---|---|
| `create RUN_ID --envelope ENVELOPE_FILE --policy POLICY_FILE` | Source exposure and scopes: [memory_contract.py:95](../../../src/attune_harness/memory_contract.py#L95), line 98; [memory_context.py:121](../../../src/attune_harness/memory_context.py#L121), lines 124–130. Distinct policy profiles: [memory_contract.py:109](../../../src/attune_harness/memory_contract.py#L109) | Host and envelope actors match; access lists and grants fit the host. Routine/stronger logical profiles are distinct and native profile-map keys exactly equal accepted profiles. Create returns generation, not a job ID. The fixture chooses a fresh JOB_ID; execute claims it, inspect reuses it |
| `execute RUN_ID JOB_ID`, then `inspect RUN_ID JOB_ID` inside the offline harness | Missing transport: [memory_context.py:180](../../../src/attune_harness/memory_context.py#L180). Windows/overrides/key/profiles: [memory_native.py:449](../../../src/attune_harness/memory_native.py#L449), lines 452–461. SDK/runtime: lines 127–132 and 399. Unknown results: line 491 | The test installs exact SDK pins, clears denied overrides, supplies a dummy key and host-owned SystemRoot, and chooses an unsampled happy-path job/policy. T7 runs the installed helper via a test-only trusted child wrapper with synthetic HTTP replies and denied external sockets. Preserve production `provider_transmission` uncertainty; a separate test receipt establishes zero live calls. Ordinary user execution can incur provider charges and is not automated here |

## Approval boundary

The staged plan is approved, with T2 as a technical decision gate. A
failed durability proof stops saved-store implementation and returns the
decision to Patrick. No narrower persistence promise or smaller advertised
memory bound is approved implicitly. The smallest useful increment is T1's
truthful coverage and platform claims; T2 is the most urgent feasibility work.
