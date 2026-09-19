# Shared memory adoption — verification and support

2026-09-17. **All five tasks are accepted.** Task 4 completed at canonical
revision 21 after the bounded review and repair verification; Task 5 completed at
revision 23 after installed qualification and independent support review. Nothing
here activates live memory management, publishes a release or qualifies a new
provider campaign.

## Supported paths

| Capability | Existing path retained | New shared route |
|---|---|---|
| Raw session findings, all existing kinds | Existing stash/recall/forget services and format | Explicit-root read, complete-source handle and refresh; no managed mutation |
| Personal documents | Existing authoring, retrieval and forgetting | Single-root retrieval with full content, summaries and metadata retained; no managed mutation |
| Curated documents | Existing reviewed promotion and retrieval | Read in place with provenance and full-source resolution; no automatic promotion |
| Keyed working memory | Existing key/value services and callers | Advertised as retained; no new adapter capability |
| Persisted long-term patterns | Existing governed pattern services | Advertised as retained; no new adapter capability |
| Shared worker | Additive to existing memory commands and separate memory-agent | Durable proposal replay through both CLI hosts and explicit MCP plugin |
| Routine/stronger routing | Existing native research receipts remain evidence | Explicit policy and sampled review run against supplied responses; no live Luna/Astra dispatch |
| Receiving context | Full sources remain in their original stores | Bounded excerpts, version-bound full-source resolution, explicit whole-packet refresh |
| Local accounting and team signals | Local events and explicitly configured coordination remain available | Usage upload suppressed through process exit; team transport is not globally disabled |

The host supplies trusted owner/scope/classification/profile configuration. This
is not a new identity or team access-control service. A caller must replace the
entire prior memory packet with `refresh.context` before the next receiving turn.
Correction/deletion invalidates old handles; it does not erase conversation
history or automatically inject context into every agent.

The job journal and configuration are trusted local host files. Consistency and
scope checks do not authenticate them against someone who controls those files
or the running process. Hostile filesystem ownership and a general multi-user
identity service are outside this profile. The configured actor/owner values are
explicit labels; the integration does not infer people from email addresses.

`available` and genuinely `empty` retrieval succeed. `partial` and `unavailable`
retrieval/refresh return exit 2 with JSON details. Expected filesystem, content
and missing-dependency failures degrade per root. Unexpected programming defects
reach the host's explicit failed response. Diagnostics use stderr.

## Executed entry points

These command shapes were executed with explicit synthetic config files and
separate temporary job directories:

```sh
attune-harness memory --config config.json recall Aurora
attune memory worker --config config.json recall Aurora
attune-harness memory --config config.json --jobs jobs create RUN --envelope envelope.json --policy policy.json
attune-harness memory --config config.json --jobs jobs replay RUN JOB --replies replies.json
attune memory worker --config config.json --jobs jobs inspect RUN JOB
python -m attune_harness.memory_bridge --config config.json --jobs jobs
```

Config paths and memory roots are explicit; the route does not discover or migrate
live corpora. The seven MCP tools are `harness_memory_capabilities`, `recall`,
`resolve`, `refresh`, `create`, `replay` and `inspect` (each with the same prefix).
The test starts the real Attune MCP stdio server and observes durable job state.
That server retains existing tools; this evidence applies to the named new tools,
not a claim that all existing MCP features are newly qualified or offline.

## Central evidence

| Check | Result and boundary |
|---|---|
| Integration plus AI CLI regression, including separate memory-agent | 122 passed; both actual CLI subprocesses and actual MCP transport |
| Adapter-repair memory regression | 221 passed before the later host repair; one existing deprecation warning |
| Final host/worker/adapter/CLI regression | 215 passed after the host repair; exact six-file selection saved; counts are not aggregated |
| Historical job authorization repair | 20 integration cases pass; all six new cases fail with the exact-snapshot guard removed |
| Repository quality/gate suite | Final 678 passed; initial failures and their repairs retained |
| Collaboration preflight | 87 passed; warnings preserve the dirty original checkout |
| Task 4 changed-code coverage | AI dispatch 8/8 changed statements; lazy handler 14/14; both 100% |
| Refactored adapter coverage | 225/247 statements, 91.09%; existing strict service seams retain their Task 3 receipts |
| Protection removal | Four temporary code removals produced expected regression failures: degraded status, invalidated handles, closed-plugin calls and uncertain backend exceptions |
| Shutdown upload control | Real process exit with legacy upload opt-in retains local accounting and makes no upload; removing the guard reaches the intercepted uploader |
| Historical experiments | All 108 native receipts and frozen sources unchanged; no new provider calls |

Receipts are in [Task 4 evidence](../../receipts/shared-memory-adoption-task4/progress.json).
The complete quality run initially found the new broad read catch; its next
focused run exposed the intentional strict-write catch's missing baseline entry.
The read catch was narrowed. The strict-write boundary still handles arbitrary
backend exceptions after a possible commit as uncertain, without a retry. Its
single ratchet exception is documented and tested with a real disposable write
followed by a custom backend exception. The baseline for other modules is unchanged.

Task 4 was accepted at revision 21 under the existing auto-run approval, after
Patrick requested completion of the bounded review. The [revision 19 gate](task4-gate.md)
is historical and superseded by retry revision 20 and acceptance revision 21.

The functional reviewer independently found and closed the refresh exit-status
defect. Its exact probe was rerun centrally. A separate scoped review covered the
adapter's raw-read extraction, expected-error handling and strict-write gate exception.
The later bounded passive review evaluated all four host-scope questions and found
one historical-job authorization defect: the old path checked the current run,
then returned an older job without checking that job's own scope. The repair checks
the exact snapshot before inspection return, before each replay response and before
replay return. Six regressions cover all configured dimensions and a host-state
transition before job capture; all six detect removal of the new guard.

The reviewer traced the repair; the lead checked all 31 reviewed file hashes and
ran the behavior tests centrally. [Independent review](../../receipts/shared-memory-adoption-task4/bounded-review/independent-review.json)
and [central closure](../../receipts/shared-memory-adoption-task4/bounded-review/central-closure.json)
retain the evidence and limits. No unresolved finding remains in that bounded
scope. Synthetic identity labels do not imply multiple actual users or observed
exposure in a live installation.

The original broader review's automated refusal remains a historical non-pass;
this later user-authorized passive review has its own bounded scope and receipt.
The legacy provider-backed pipeline runner was not run; no pipeline pass is claimed.

## Installed artifacts and rollback

Final local wheels: Harness `0.1.0.dev13` and Attune AI `16.4.0` with the optional
`harness` extra. Exact wheel hashes, console scripts and metadata are recorded in
[wheels.json](../../receipts/shared-memory-adoption-task5/wheels.json).
Eleven loaded production modules were checked against the final source hashes and
resolved inside the temporary installed environment, not either source checkout.

Three fresh environments establish distinct cases:

- Harness alone imports its dependency-free core; complete help works; memory
  reports the absent AI adapter as unavailable.
- Both wheels run from an outside-tree consumer directory: generated console
  entry points, module CLI journeys and real MCP transport pass. **151 installed
  memory tests passed.**
- AI alone loads without Harness, retains legacy memory/memory-agent parser
  routes, and reports the missing optional worker package explicitly.

These are offline wheel installations with `--no-index --no-deps`. The two
AI-capable environments reuse already-installed dependencies from the existing
venv through a plain path entry, without executing its editable-package path
hooks. This verifies our wheel contents and consumers; it does not qualify fresh
PyPI dependency resolution. Selected dependency versions and paths are in the [installed dependency receipt](../../receipts/shared-memory-adoption-task5/installed/dependencies.json), including Attune RAG 1.2.0 and the AI host’s MCP SDK 1.29.1.
The base-only environment uses no shared dependency path. This qualifies the
AI-host MCP profile; it does not qualify Harness’s separate `mcp` extra profile.

[Construction provenance](../../receipts/shared-memory-adoption-task5/installed/construction.json)
binds the executed setup scripts and generated installation commands to the saved
environment paths. Post-install inspection of both AI-capable environments confirms
the plain dependency path, installed product-module origins and no loaded editable
hook modules. Raw pip stdout was not retained; the receipt explicitly distinguishes
commands recovered from the executed scripts from captured install output.

`ATTUNE_MEMORY_WORKER=0` disables the additive route in both generated CLIs.
The actual legacy compatibility suite then passes **24/24** against disposable
current-format records, preserving bytes, identifiers and useful retrieval.
No conversion or source-memory rewrite is needed for rollback. A closed explicit
MCP plugin rejects further calls; stopping its launcher ends that instance.

Installed commands and module proofs:
[commands](../../receipts/shared-memory-adoption-task5/installed/commands.json),
[module hashes](../../receipts/shared-memory-adoption-task5/installed/module-hashes.json),
[AI without Harness](../../receipts/shared-memory-adoption-task5/installed/ai-without-harness.json).

## Limits after acceptance

Evidence here is macOS 26.6.2 arm64, Python 3.10.11. No Linux/Windows memory
integration qualification is claimed. Legacy writers do not provide the versioned
serialization required for new managed worker mutations, so those remain
unavailable. Native worker transport, automatic receiving-agent refresh,
representative workload economics, live Redis collaboration and live memory
activation remain separate qualification boundaries. The team-signal test executes
existing coordination code with a recording Redis client; it is not a live Redis
service test.

Tasks 4 and 5 are accepted under the existing auto-run approval.
Implemented, installed for testing, native-qualified, active and released remain
distinct statuses. Acceptance of the local integration does not qualify fresh
dependency resolution, other platforms, native execution or live activation.


## Checkpoint lesson

The earlier targeted green suites established memory behavior but did not cover
all repository gates. Running the full required set exposed maintainability and
exception-baseline omissions. Keep behavior tests, repository gates, independent
review and installed verification distinct in the receipt; passing one cannot
stand in for the others. This led to a small existing-code refactor and a narrowly
justified uncertain-write exception, without adding another product feature.

The resolved review pause followed the existing Attune AI D11 requirement for an
independent review of changes affecting risk boundaries. The bounded repair kept
that requirement intact. A past high finding is not an unresolved high result
once its repair has independent review and failure-sensitive behavioral evidence.

The host repair also clarified where to focus inspection: authorization of the
current run cannot substitute for authorization of the particular saved object
being returned. Checking that concrete transition produced a small repair and
useful regressions without adding an identity service or expanding the product.

## Final acceptance and display caveat

[Task 5 acceptance](../../receipts/shared-memory-adoption-task5/acceptance.json)
records completed tasks 1–5 and terminal revision 23. The returned state was saved
through the spec state API and reread with all five completed and no current task.
The [final support review](../../receipts/shared-memory-adoption-task5/independent-review.json)
has no open findings; all 19 reviewed input hashes matched centrally.

The canonical terminal screen incorrectly repeats planning-stage probes, including
old `completed=[]` and “No implementation” text. Those are stale display claims,
not the saved completion state. The raw receipt is preserved; this current report
and the task acceptance records provide the implementation evidence. That observed
summary defect is logged as O-08 for a separate bounded repair.


## Later fresh-installation qualification — 2026-09-17

The separately approved release-readiness follow-through now [qualifies a fresh
macOS/Python 3.12 installation](../../fresh-installation-results.md) of Harness
`[review]` and AI `[harness]`, using Verify 0.6.0. It passes 151 installed memory
checks, 24 legacy rollback checks, 80 Spec checks and 146 task-journey checks. All 13
selected installed module hashes match source. The prior Python 3.10 receipts above
retain their reused-dependency scope; they are not retroactively relabeled. The
[Spec summary defect is repaired in the candidate](../../spec-completion-repair-results.md),
with the active plugin still unchanged. Live activation/release remain outside
approval.
