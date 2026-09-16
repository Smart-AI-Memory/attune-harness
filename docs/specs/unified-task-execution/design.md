# Design — unified task execution

Status: approved by Patrick Roebuck as part of the revised spec, 2026-09-16. This is the accepted design, not implemented behavior. Existing execution authority, provider-spend rules, and supported legacy contracts remain unchanged.

## Task-facing interface

Agreed task verbs are plan, build, fix, review, ship. Proposed syntax for the first two journeys and their supporting controls:

```text
attune-harness review --goal "Check this guide against the project evidence"
attune-harness fix --goal "Repair the failing configuration parser"
attune-harness status <task>
attune-harness resume <task>
```

Slice 1 implements review/status/resume; Slice 2 adds fix. Missing inputs are collected through the existing forms library or plain CLI prompts. Headless callers can supply one request object instead. The accepted contract contains the same fields on both paths. Supported project profiles can supply existing source and participant selections; absent profiles produce a focused input request, not guessed permissions or new model calls.

Preserve `review <request.json>` exactly as the legacy path. `--goal` explicitly selects new intake and is mutually exclusive with the legacy positional request; never guess whether a string is a goal or a filename. New status/resume work from the saved accepted request. An optional explicit checkpoint supports scripted compare-and-set control; ordinary users should not have to paste hashes or reconstruct config JSON. Existing low-level review controls keep their required arguments.

Show review/fix/status/resume as primary help when implemented, plus a clear route to the complete advanced catalog. All existing parser names remain recognized; hiding a command is not retiring it. Future plan/build/ship vocabulary is outside these slices until supported outcomes exist.

## Fast intake and bounded reuse

The current `review_form` in `src/attune_harness/review_contract.py` builds a declarative form in code, renders it through attune-forms, and hashes the definition plus participant registry. It does not call a model to generate that form. Preserve deterministic construction for routine review/fix intake. Caching this rendering alone has no measured latency benefit yet; unnecessary question and model round trips may be larger costs and must be measured separately.

| Reusable item | Proposed rule |
|---|---|
| Form definition and unbound presentation | Cache immutable templates or pure render fragments by schema, policy, forms/renderer version, presentation preferences, and every dynamic option dependency. Include project identity where content is project-specific. Bind the current task/workspace state when presenting; never reuse another action's nonce, acceptance flag, or bound response skeleton |
| Answers in the current task | Reuse accepted, still-valid answers from its durable record. Ask only for missing or materially changed information; an unchanged answer does not need reconfirmation merely because the form was rendered again |
| Answers from another task | An explicit saved project profile may supply allowlisted non-sensitive defaults. Show their origin and permit correction; validate against current options and scope. Free-text goals, secrets, acceptance decisions and one-time permissions do not become reusable defaults |
| Participant/tool responses | Reuse a completed operation only through the existing task journal, with matching revision, assignment/attempt, provider/settings, evidence and input digests. This is continuation of that operation, not a new successful attempt. Uncertain effects stay unresolved |

A shared template is immutable; per-task field values and bindings live outside the cached object. Independent assessor/reviewer assignments cannot share a cached judgment, even when their prompts match. A new evaluation repetition must perform its intended new calls; report any replay separately. General cross-task model-response or semantic caching is deferred because it changes freshness and independence requirements.

Keep this inside the task intake adapter and existing record services, using a bounded local cache with explicit bypass/clear and deterministic eviction. Start with process-local immutable entries; Task 1 measures whether short-lived CLI processes justify a small project-local on-disk template cache. Do not add Redis, a remote cache, speculative model prefetch, or a second response store. Cache storage is excluded from retrieval and repair scope just like task state. Shared rendering improvements belong in attune-forms when its public API needs a change; do not fork its validator or renderer in Harness.

Recompute or validate current dependency fingerprints before using an entry: changed schema, locale/presentation, registry/capabilities, source selection, project or relevant policy invalidates it. TTL alone cannot prove freshness. A hit never bypasses current validation or canonical action collection. Missing, corrupt or evicted entries fall back to the ordinary builder without model calls; record the miss reason. Cache contents are disposable and cannot be the sole copy of accepted task state.

Record lookup/validation/build/render/transport durations, cache hit or miss, avoided questions and avoided calls without logging answer contents. Compare cold, warm and bypassed paths, including separate-process invocations. Measure time to a usable form and to accepted intake; keep human think time separate. Set any numeric latency target from that baseline before implementation comparison. If lookup/freshness work costs more than rebuilding, keep the simpler builder for that path and report the result.

## One accepted task, bounded plans

Keep the public in-memory core unchanged. Add a versioned product envelope around it:

| Part | Required content |
|---|---|
| Identity | Durable task ID; request schema; accepted requirement revision; owning run directory |
| Intent | Goal; assess or repair policy/version; expected artifact; scope; acceptance criteria |
| Evidence | Input paths and byte hashes; context manifest; source snapshot or selected generation; retrieval scope |
| Participants | Adapter-backed identities, roles, requested model/settings, required capabilities, recorded qualification scope |
| Policy | Explicit solo/independent-review plan; review requirement; allowed effect classes; tool/provider/output/attempt budgets |
| Acceptance | Host probe definitions and immutable input hashes; review completion/disposition rules; existing authorization references |

Create the task identity during intake, before acceptance; saving a draft never dispatches. Accepted material changes increment the revision and invalidate dependent responses/grants. Subrequests generated for retrieval or review refer to this task; users do not sign or maintain a second manual JSON chain. Digests correlate content and detect staleness; they are not authentication.

Proposed default storage is a project-local `.attune-harness/tasks/<id>` directory with one authoritative record and bounded evidence artifacts. Exclude this state root from retrieval selection and repair scope, and add the appropriate ignore entry. Reject configurations whose selected source scope would ingest task state; do not weaken existing source freshness checks. A caller may choose an explicit supported run root. No global mutable task registry is needed for the first slice.

The plan is a bounded list of host-known operations and assignments, not executable code supplied by a model. Assignment identity is separate from participant identity. Operation inputs, dependencies, and effect classes are reconstructible and checked on resume. The initial engine executes serially; that does not prevent a later qualified concurrency policy.

## Shared execution services

Proposed new modules, deliberately not present yet: [[?src/attune_harness/task_contract.py]], [[?src/attune_harness/task_runtime.py]], [[?src/attune_harness/task_policies.py]], [[?src/attune_harness/task_cli.py]], and the Slice 2 [[?src/attune_harness/repair.py]]. Names are locations, not a commitment to create abstractions unused by these slices.

| Existing seam | Planned treatment |
|---|---|
| `src/attune_harness/review_store.py` | Reuse atomic saving and writer leases; support versioned task records without rewriting legacy records |
| `src/attune_harness/recovery.py` | Extract shared operation replay/checkpoint mechanics; keep old review entry points as schema/policy adapters |
| `src/attune_harness/review.py` | Translate accepted legacy review to the shared assessment plan and project its original result/exit semantics |
| `src/attune_harness/review_contract.py` | Preserve old request/registry validation; new contract owns solo support and new schema |
| `src/attune_harness/review_participants.py` | Reuse native host-evidence projection and response correlation behind participant invocation |
| `src/attune_harness/retrieval.py`, `src/attune_harness/verification.py` | Call public functions; preserve source/unknown-result contracts |
| `src/attune_harness/retrieval_task.py`, `src/attune_harness/voyage_retrieval.py` | Generate task-bound intake internally; retain paid-stage journal, scope, generations and replay semantics |
| `src/attune_harness/process.py`, `src/attune_harness/native.py` | Reuse transport supervision and existing read-only native behavior; no silent permission expansion |

One service owns participant dispatch and result collection; one owns operation persistence/replay; policies decide which operations and acceptance predicates apply. New primary commands and legacy review routes call those services. Use one-way dependency flow from CLI/policies to runtime and existing adapters. Do not add a provider SDK or Attune dependency to the core import path.

### Slice 1: assessment

Sequence: intake → preflight → retrieve → verify supported claims → participant assignment(s) → integrate attributed results → final input/evidence freshness check → persist result. Each step carries the task/revision and durable operation identity. Host-scheduled evidence must satisfy current native evidence-mode budgets; a missing tool or source must remain visible before model invocation where detectable.

Solo has one assessor. Independent review has assessor and reviewer identities, with separate contexts and the same permitted evidence. Where existing policy requires a different model, two identities selecting the same model do not satisfy it. The reviewer sees no assessor output until its own result is final. Distinct attempts are used even if a native session identifier happens to repeat.

Integration is deterministic in this slice: retain complete bounded narratives, participant attribution, source references, supported tool-check results, and disagreements/unknowns. An optional structured finding projection must retain its original narrative and be validated; absence of extractable findings is not a clean verdict. Do not add a synthesis invocation merely to manufacture agreement. A later semantic reconciler requires separate evidence.

Store execution status separately from acceptance status and assessed-object findings. Execution may complete while evidence remains unknown or the assessed document is refuted. An assessment that correctly reports a defect can complete its requested work; its subject is still defective. Preserve the legacy CLI's existing interpretation of document/retrieval outcomes through result translation. Never label model prose semantically verified because attune-verify checked links/imports.

### Continuation and legacy records

Use explicit prepared → dispatching → completed operation transitions. Persist dispatch intent before the call; persistence failure stops further dispatch. Replay completed operations only when reconstructed inputs match. A dispatching/failed operation may have effects and remains unresolved until a supported reconciliation supplies evidence. An accepted new revision never reuses a stale response merely because task identity matches.

Legacy records retain their schema/profile, accepted digests, operation keys and unknown fields. The legacy adapter constructs the same operation identities and translates results; it does not rewrite the old on-disk format into a new acceptance contract. Existing supported checkpoints remain resumable. Unsupported/future records stay inspectable where safe and cannot silently advance. New tasks use their own explicit schema and engine-profile version.

Transfer preserves the accepted contract and only selects an already authorized, capable participant. It creates a fresh assignment attempt and cannot conceal unresolved operations or violate reviewer independence. Respect legacy transfer limits and timing for old records. Cancel preserves known and unknown effects; completion wins over late cancellation. Existing stopped-run cancellation is not relabeled as remote cancellation of a still-running provider.

### Slice 2: scoped repair

Initial effect profile: replacements of existing regular UTF-8 files inside an accepted dedicated checkout. Worker proposes path, before-image hash and replacement bytes in a strictly decoded structured result. Host rejects duplicate paths, traversal, absolute/outside paths, symlinks/reparse escapes, hard-link ambiguity, metadata/state/probe paths, oversized output, stale before images, and undeclared changes. This profile does not accept creation/deletion/renames or shell commands from worker prose.

Before applying anything, validate the complete patch and snapshot the checkout's protected state. Journal each replacement, then replace through a safe file handle/atomic-write boundary with a final preimage check. Record the actual after-image. The host rechecks whole declared scope and unrelated state before reporting success. These are required properties to prove, not a claim that current file helpers already implement them.

If a crash occurs between write and acknowledgement, reconcile observed bytes against recorded before/after hashes: known-after permits recording that effect as complete; known-before permits a bounded explicit retry; unexpected content remains unresolved. A multi-file patch can be partially applied. Preserve that state and stop; never describe multi-file writes as atomic or roll back later user edits automatically.

The acceptance probe is an approved argument vector, working directory, timeout, output limit and environment policy bound before model work. It runs in the dedicated checkout through the bounded process boundary. Probe configuration and any external oracle/tests are protected from the patch. The worker cannot change the expected result, suppress a failing check, or choose an easier probe. Process supervision is not a security sandbox: qualify and disclose the supported isolation/environment profile, including network and filesystem effects, rather than claiming general containment.

Run the probe on the baseline to establish the failure and again on the final artifact; retain output, exit status and hashes. A no-op or incorrect patch must not satisfy the seeded acceptance case. A requested/required reviewer receives the frozen diff, relevant before/after code, and probe evidence, not worker self-praise. Final acceptance requires successful probes, unchanged final bytes, and the configured review obligation/disposition. Any later change invalidates affected review/probe evidence.

## Disposition of all current commands

| Current names | Disposition for these slices |
|---|---|
| `review-form`, `review` | Preserve legacy contracts; add task-oriented goal intake to review |
| `inspect-review`, `resume-review`, `reconcile-review`, `transfer-review`, `cancel-review` | Preserve exact low-level routes; reuse shared task controls with legacy translation |
| `retrieve`, `verify` | Preserve direct deterministic/tool routes; reuse as task operations |
| `retrieval-task` | Preserve headless preparation; generate needed intake internally for ordinary tasks |
| `code-config`, `index` | Preserve resource setup/lifecycle; no forced setup rename |
| `extension` | Preserve lifecycle and its current capability bounds |
| `github-checks`, `triage-check` | Preserve read-only evidence/proposals; no automatic repair dispatch |
| `repair-economics` | Preserve direct ledger analysis; new task reports can feed compatible evidence |
| `mcp-serve`, `mcp-inspect` | Preserve explicit protocol launch/inspection and stdout discipline |

## Approved follow-on task: reflect

Patrick requested session/chat mining for useful facts, Opportunities, Keep and Pushback and approved the revised spec. The [session reflection extension](session-reflection.md) defines `reflect`, a source-linked insight list and a reusable triage form with Keep/Edit/Revisit/Discard over the same task/evidence/recovery services. Its implementation breakdown and concrete host/storage adapters are future work; the approved extension follows the current eight-task review/fix ladder and does not alter R1–R14.

## Alternatives and failure signals

Merely adding a natural-language router would hide 18 entries without sharing execution. Copying review into a second generic engine would increase maintenance. Broad native write grants would add an unqualified effect boundary. A universal scheduler/DSL would delay the two concrete journeys. The bounded policy/runtime design is preferred; narrow it if a policy requires numerous special branches in shared dispatch.

Do not measure success only by fewer help entries. Record which duplicated paths were removed, which adapters remain, and the observable behaviors they preserve. R13 adds a user walkthrough: an intent such as “check this document” should lead to review without explaining internal retrieval/MCP terminology.
