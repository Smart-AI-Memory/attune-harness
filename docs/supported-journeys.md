# Supported journeys and their limits

## Current map — 1.5.0, reviewed October 21, 2026

Checked against `main` at `4b773a6edb488afbe9b66348b7020c1b40dfbb67`,
the CLI/source owners and existing journey tests. The
[published 1.5.0 release record](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.5.0)
identifies release source `7caa86ab6d476e9599b08ff75a81bc816e60c382`,
distribution hashes and published-install evidence. The runtime source is
unchanged between that release and the main snapshot checked here. This map
adds no fresh execution receipt.

The [hosted baseline run](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/39205220937)
passed all 16 jobs for `77d5b2b4fe9f3c6285a5b535f4e735103f7e192d`,
including four Windows Server full-source and four Windows installed-wheel
cells across Server 2022/2025 and Python 3.10/3.12. These are bounded software
checks for that source and its artifacts. Full Windows parity remains deferred;
see the [Windows checkpoint](specs/windows-parity/tasks.md). The original 1.2.0
map is retained below as historical evidence.

## Windows capabilities and reliability

Version 1.5.0 includes native Windows implementations for captured tests,
file-memory reads, saved memory and task storage, and experimental native-memory
transport. The table describes their available functionality and the limits of
the retained evidence. Full Windows parity remains deferred.

| Windows capability | What's available | Reliability boundary |
| --- | --- | --- |
| Build and repair scoped files | Build accepted files and apply scoped repairs in a dedicated checkout under the declared fixed-local NTFS profile. Hosted checks exercise these native effects. | Strict completion of every owned descendant and process recovery remain open. General process supervision is not an OS security sandbox. See [repair guidance](cli-guide.md#scoped-repair). |
| Test a captured change | Preview and accept a test plan, run it in a captured copy, and keep output and check evidence. Eligible `test --from-task` handoffs have installed component witnesses. | Preserve accepted input, protected files and single-dispatch recovery. Complete descendant termination before reading captured output or reporting process completion remains a separate requirement. See [captured testing](cli-guide.md#test-this-change). |
| Read configured memory files | Recall, resolve and refresh raw, personal and curated memory, and serve eligible file pointers through native retained-handle reads. Existing file and query limits are preserved. | Use admitted local NTFS roots; unsupported volumes and unsafe paths are refused. Combined Windows desktop and shell acceptance remains open. See [memory guidance](cli-guide.md#memory). |
| Save memories and task intent | Save and revise memories and task intent, retaining history, request-ID replay and pending reviews. Redis is an optional rebuildable index. | Full saved-store acceptance remains open, including the unresolved historical eight-writer busy failure. Standard-user durability, concurrency and recovery requirements still apply. See [saved storage](memory-saving.md). |
| Prepare native-memory proposals | The experimental transport has Windows offline evidence through the supervised helper and pinned SDK. | The `memory-native` extra is separate from base/`all`; live-provider acceptance remains open. Configuration and installation grant no provider-call authority. See [native memory](specs/windows-parity/README.md#native-memory-proposal-transport). |

Windows Server checks cover their recorded source, artifacts and runtime cells.
Windows 11 standard-user desktop, Windows PowerShell and PowerShell 7 journeys
still need their own acceptance evidence. An unobserved journey is an evidence
gap; it does not by itself mean the command is absent.

### Reliability requirements

Reliable operation remains the acceptance standard for each workflow:

- **Complete process shutdown:** confirm every owned descendant has terminated
  before reading or decoding captured output, or reporting process completion.
  Preserve the existing shared five-second stop deadline and successful
  fast-child behavior.
- **Truthful outcomes and recovery:** preserve the original result and failure
  information. Uncertain effects must remain explicit; status or resume must not
  silently repeat a dispatched operation.
- **Durable saved data:** retain the approved standard-user durability requirement,
  including its power-loss proof obligation. Process-crash tests alone do not
  establish power-loss durability, and an app-crash-only fallback is not approved.
- **Consistent concurrent writes:** retain committed saves, exact request-ID
  replay and revision-conflict behavior. Recovery must preserve a valid before
  or after state without duplicate history.

These are requirements, not a claim that every Windows implementation already
satisfies them. The [approved design and acceptance criteria](specs/windows-parity/design.md)
and [retained Windows checkpoint](specs/windows-parity/tasks.md) preserve the
remaining obligations and original evidence. Describing support by workflow
does not relax those criteria or remove Windows components already delivered.

## Install and first run

| Journey | Entry point and guidance | Evidence and remaining limit |
| --- | --- | --- |
| Install the released base | `uv tool install 'attune-harness==1.5.0'`; inspect the selected version/path with `uv tool list --show-paths`. See the [release README](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.5.0/README.md#installation). | The release record reports a fresh macOS base install and installed CLI checks. Python 3.10+ is required; hosted checks exercise 3.10/3.12. Keep Harness and Attune AI in separate environments. This map does not qualify an upgrade or every saved-work migration. |
| Prepare a first task | `init`; `init --for plan` or `init --for fix` for scoped starter files. Follow the existing [CLI examples](cli-guide.md) and [starter specification](specs/starter-files/tasks.md). | Starter generation exists; the old 1.2.0 statement that no command writes the request/probe is superseded. Demo participants cannot propose a build; use the documented command worker or an explicitly configured participant. Preparation does not execute a model. |

## Work

| Journey | Entry point and guidance | Evidence and remaining limit |
| --- | --- | --- |
| Plan, accept and build | `plan --request`, `plan --accept`, then `build`; [plan/build guide](cli-guide.md#plan-and-build). | The [R2 installed journey](journeys/r2-clean-environment.md) supplies the offline owner chain. Review findings and optional function-body boundaries are integrated. Native/model reliability is a separate qualification; accepting intent does not authorize paid calls. |
| Review evidence and select a repair | `review`; explicit `fix --from-assessment` with selected finding IDs. See the [CLI guide](cli-guide.md#task-oriented-evidence-review). | [The handoff owner](../src/attune_harness/task_handoff.py) binds selected provenance. Model narratives remain unverified proposals. Selecting findings does not authorize a wider repair or automatic execution. |
| Repair scoped files | `fix --goal --checkout --scope --probe`; [repair guide](cli-guide.md#scoped-repair). | Existing protected probes and effects owners apply. Windows effects have hosted checks, while strict arbitrary-descendant stop/recovery and declared Windows shell/desktop journeys remain open. Use the documented source profile and a dedicated checkout. |
| Test a captured change | `test --project --scope`; `test --from-task` for eligible completed work. See [testing guidance](cli-guide.md#test-this-change). | Windows captured execution is merged in [#271](https://github.com/Smart-AI-Memory/attune-harness/pull/271), with installed component witnesses. Acceptance, single-dispatch recovery and immutable evidence remain required; component success does not establish full Windows parity. |
| Consult configured seats | `init --for roundtable`, then `roundtable` or `source-review` `check`, `prepare`, `status` and `evidence`. See the [1.4.0 feature guide](release-notes-1.4.0.md#changes-in-140). | Setup/check operations do not dispatch models; explicit execution has its own configuration, authority and budget. Readable evidence and partial-round recovery exist. Unknown effects block blind retries; no general model-quality claim follows. |
| Import another project's plan | `plan --import-plan PATH --allow-outside-project`; [R4 guide](journeys/r4-legacy-spec-state.md). | Import preserves provenance and grants no execution authority. The existing reader/refusal limits remain; malformed-input behavior is not requalified here. |

## Inspect and recover

| Journey | Entry point and guidance | Evidence and remaining limit |
| --- | --- | --- |
| Inspect and continue saved work | `status TASK`, then eligible `resume TASK`; [recovery workflow](recovery-workflow.md). | Completed operations replay from saved evidence; unknown effects require reconciliation. Feature work has richer Markdown/HTML snapshots. Other task profiles retain generic envelope rendering; assessment-specific inspection remains O-74. |
| Settle uncertainty or close a task | `reconcile-task` with the option matching retained evidence; `cancel-task --reason`. | Recovered replies, read-only retry, refused-turn retry and effect observations have different conditions. Follow the current checkpoint and owner refusal; cancellation does not erase unknown effects. Strict Windows process completion/recovery remains open. |
| Save and approve a browser request | `python -m attune_harness.gui --task PATH --edit`; [forms walkthrough](tutorials-next-release-candidate.md#save-and-approve-a-clear-work-request). | The released companion retains its forms boundary: saved answers and approval do not execute work. Browser build grants and broader M2/M3/M4 acceptance remain unavailable or incomplete; historical development prototypes do not enable them in 1.5.0. |

## Memory

Explicit saved entries and automatic recall are separate paths. Saving a memory
does not feed it into automatic recall.

| Journey | Entry point and guidance | Evidence and remaining limit |
| --- | --- | --- |
| Read configured memory files | `memory recall`, `memory resolve`, `memory refresh`, `memory serve`; [memory guide](cli-guide.md#memory). | Native Windows readers are merged in [#272](https://github.com/Smart-AI-Memory/attune-harness/pull/272), retaining the 4,096-file/root, 8 MiB/file and 64 MiB/query bounds and native path/identity checks. The historical POSIX-only refusal is superseded for this component; combined desktop/shell acceptance remains open. |
| Automatic session/prompt recall | `memory serve`, including `--for PROMPT`; the existing [prompt hook](../scripts/memory_prompt_hook.py). | Synthetic provenance/exclusion checks and retained server observations remain bounded evidence. Harness consumes the hydrated Redis index; it does not replace Attune AI's hydrate writer. Fresh-session recall and exclusion observations remain S3. |
| Read Redis or use scratch memory | `memory redis`; `memory scratch stash`, `retrieve`, `forget`, `keys`. | Redis is optional and needs a reachable configured server; it is not an automatic fallback. Scratch version ordering is exact only among writers using the documented expected-version protocol. See the [CLI guide](cli-guide.md#memory). |
| Save memory and task intent | `memory saved` lifecycle/history/pending-review operations; [saving guide](memory-saving.md). | [#275](https://github.com/Smart-AI-Memory/attune-harness/pull/275) merged the Windows implementation checkpoint. Finite witnesses support that checkpoint; full saved-store acceptance and the historical eight-writer busy-failure cause remain open. Saving task intent does not execute the task. |
| Prepare native-memory proposals | `memory create`, then separately authorized `memory execute`; [Windows command walk](specs/windows-parity/README.md#native-memory-proposal-transport). | The experimental extra stays separate from base/`all`. [#269](https://github.com/Smart-AI-Memory/attune-harness/pull/269) supplies Windows offline supervised-helper/SDK evidence. Live-provider acceptance remains open; installation supplies no spending authority. |

## Retrieval, hosts and extensions

| Journey | Entry point and guidance | Evidence and remaining limit |
| --- | --- | --- |
| Voyage retrieval | Optional `[voyage]`; `index plan`, `build`, `update`, `inspect`; [Voyage guide](voyage-retrieval.md). | Retained live macOS stages and offline platform replay remain distinct. No general ranking-quality claim or automatic provider switching is established. Paid calls need their existing authority. |
| Claude Code or Codex integration | [Claude installation](../README.md#use-harness-with-codex-claude-or-other-models); [Codex packaging](codex-plugin.md). | The [Claude catalog](../.claude-plugin/marketplace.json) pins 1.5.0. The Codex plugin is packaged separately from the wheel. Check the selected CLI/runtime independently; plugin availability does not qualify every host journey. |
| MCP/A2A and signed plugins | `mcp-serve`; `extension install`, `inspect`, `enable`; [signed execution guide](executable-plugin-run.md). | Local protocol and installed plugin checks retain their declared profiles. Remote authentication is not supplied, plugins are not an OS sandbox for hostile same-user code, and installation is not an execution grant. |

## Observations still owed

S3 fresh-session recall/exclusion, S6 a qualifying non-programmer installed
walkthrough and S9 installed migration-row observations remain open in the
[observation record](release-readiness-1.4.0.md#open-observations-and-publication-boundary).
Bounded maintainer forms observations do not close all three. Full Windows
parity additionally needs the [unchanged spec criteria](specs/windows-parity/design.md),
including strict process/recovery, full storage, live native memory, Windows 11
standard-user desktop and Windows PowerShell/PowerShell 7 journeys. The calendar
and a published package do not close these gaps.

The [current opportunity register](opportunity-log.md#current-register) identifies
remaining work. The dated map below preserves earlier claims and evidence;
use the current sections above for 1.5.0 guidance.

## Historical map — 1.2.0 and its later preparation annotation

**Historical 1.2.0 map.** The dated text and table below are retained as
historical claims, including the original “current map” wording. The saved-store
row's “All three” entry does not establish Windows support: the released 1.2.0
and 1.4.0 owners refuse non-POSIX storage. See the
[released saving profile](memory-saving.md#released-140-profile).
Unreleased `main` now includes a merged Windows saved-store implementation
checkpoint with passing current finite witnesses; full T5 acceptance, the
historical busy-failure cause, and final parity remain open in the
[draft 1.5.0 readiness record](release-readiness-1.5.0.md).

Written September 29, 2026 against the released **1.2.0** (`v1.2.0`, commit
`d833c371f5fb132ddc2af35e5cb069169dae1df3`). This is the current map (O-04). It
replaces the [September 17 release journey map](release-journey-map.md) and the
[connected capability map](specs/connected-journey-qualification/capability-map.md)
as the account of what works. Both are kept as historical records: they
describe `plan` and `build` as absent, and those verbs now exist.

Each row names the entry point, the platform limit, the evidence behind it and
what to do where the journey stops. "Evidence" means software checks unless
it says otherwise. None of it is observed use by a person. The observations
the [project plan](project-plan.md) still owes (real memory sessions, a named
non-programmer walkthrough and the migration rows) are listed at the end.

## Historical install and first run

| Journey | Entry point | Platform limit | Evidence | Where it stops, and what to do |
| --- | --- | --- | --- | --- |
| Install | `pipx install 'attune-harness[all]==1.2.0'` ([README](../README.md#installation)) | Python 3.10 and 3.12 on macOS, Ubuntu and Windows are in the CI matrix; other versions are not | Installed-wheel qualification runs for each row in the [canonical matrix](qualification.md#platforms) on every push to `main`; the release gate compares PyPI's hashes with the publish run's `SHA256SUMS` | Harness and attune-ai pin different MCP SDK lines and cannot share an environment. Install each in its own environment |
| First run | `init`, then a `test` preview and the `review` intake ([README](../README.md#your-first-five-minutes)) | All three platforms | The README's journey-tagged block runs as written in every platform job | `init` writes offline demo participants. Native participants need `init --profile claude` or `codex`, and a review then needs `--allow-external` |

## Historical work

| Journey | Entry point | Platform limit | Evidence | Where it stops, and what to do |
| --- | --- | --- | --- | --- |
| Evidence review | `review --goal ... --accept` ([CLI guide](cli-guide.md#task-oriented-evidence-review)) | All three platforms | Review and task tests; the review step of the R2 journey in every platform job | Narratives are unverified model output. Participant disagreement is left for a person to settle, never adjudicated |
| Plan, accept, build | `plan --request`, `plan --accept`, `build` ([CLI guide](cli-guide.md#plan-and-build)) | Build runs through the POSIX effects profile, or the Windows one, which may refuse with a `FeatureUnavailable` that names Windows | The offline [R2 journey](journeys/r2-clean-environment.md) (plan, accept, build, review, status) runs from the installed wheel in every platform job, with Attune AI absent | No copy-and-paste example: `work.json` needs a frozen effects manifest that no command writes. Native model planning and building are experimental (1 of 24 replies accepted before the contract correction, 12 of 12 after it; not a reliability rate) |
| Import another project's plan | `plan --import-plan PATH --allow-outside-project` ([R4](journeys/r4-legacy-spec-state.md)) | All three platforms | Eight retained fixtures and a conversion receipt per import | Import grants no authority. Acceptance is still a separate step |
| Scoped repair | `fix --goal --checkout --scope --probe` ([CLI guide](cli-guide.md#scoped-repair)) | Local POSIX Git checkouts. On Windows, experimental and unqualified beyond its CI tests | Repair tests; the fail-before, pass-after probe is bound to the task. On Windows, the effects backend's installed owner journey on Windows 2022 and 2025 | Existing regular files only: no creation, deletion, renames or linked worktrees. Use a dedicated checkout |
| Test a change | `test --project --scope` ([CLI guide](cli-guide.md#test-this-change)) | POSIX. Unqualified on Windows | Test-change tests; the preview is saved and accepted by checkpoint | Default pytest discovery only: no custom collectors or committed revision ranges |

## Historical inspect and recover

| Journey | Entry point | Platform limit | Evidence | Where it stops, and what to do |
| --- | --- | --- | --- | --- |
| Inspect and continue | `status TASK`, `resume TASK` | All three; on Windows a process holding `record.json` open for more than about two seconds fails the run closed | Recovery tests at every boundary; completed operations replay without repeating calls or writes | Run `status` before acting. Resume refuses when an operation's effects are unknown |
| Settle an uncertain operation | `reconcile-task TASK --event ID` and one of the options below ([recovery workflow](recovery-workflow.md)) | All three | One test per path | Pick the option that matches the saved evidence. None of them repeats an effect without that evidence |
| | `--reply FILE` | | | A recovered, correlated participant reply. It is not authenticated identity |
| | `--retry-read-only` | | | Known read-only operations only: local retrieval, or the built-in deterministic participant |
| | `--retry-refused` (new in 1.2.0) | | | A Claude participant turn the CLI refused with a structured error reporting no model usage, such as an expired login or no credits. One retry; usage may repeat |
| | `--retry-native` | | | A Codex build participant that timed out, with saved evidence that the direct process stopped |
| | `--observe-file`, `--retry-before` | | | A `fix` or `build` file replacement whose outcome is unknown |
| Close a stuck task | `cancel-task TASK --reason` | All three | Cancellation tests | Records the reason. Pending effects stay marked unresolved; nothing is rolled back |

## Historical memory

Harness serves memory that is already in Redis, and it can save memory you
give it explicitly. **These are two separate paths: saved entries do not feed
automatic recall.**

| Journey | Entry point | Platform limit | Evidence | Where it stops, and what to do |
| --- | --- | --- | --- | --- |
| Read existing memories | `memory recall`, `resolve`, `refresh` over configured roots ([CLI guide](cli-guide.md#memory)) | POSIX only; on Windows the reader refuses | Every POSIX platform job reads a raw root from the installed wheel; the Windows jobs record the refusal | On Windows, use the POSIX profile through WSL2 |
| Automatic recall at session start or per prompt | `memory serve` from a SessionStart hook; `serve --for PROMPT` through `scripts/memory_prompt_hook.py` | All three; Windows and Redis-only configs serve curated nodes but no file pointers | Synthetic tests of provenance, and of inactive-node and `wrong`-verdict filtering. The path against a hydrated server passed once on a maintainer's machine | Consumes Redis that attune-ai's hydrate writer fills; Harness does not replace that writer. **Not yet observed in real fresh sessions (S3)** |
| Read Redis memory directly | `memory redis status\|digest\|related\|node\|search` (`[redis]` extra) | All three | Every platform job checks the unreachable-server report | Needs a hydrated Redis Stack. A pointer's `text` body is never served |
| Save a memory or task explicitly | `memory saved save\|search\|show\|revise\|forget\|complete` ([saving guide](memory-saving.md)) | All three | Saved-store tests, including replay, conflicts and atomic replacement | Files are authoritative; Redis is an optional index. Saving a task records intent, not execution |
| Working memory | `memory scratch stash\|retrieve\|forget\|keys` | All three | File and Redis backends in every platform job | An unreachable Redis is reported, never replaced by the file store |

## Historical retrieval, hosts and extensions

| Journey | Entry point | Platform limit | Evidence | Where it stops, and what to do |
| --- | --- | --- | --- | --- |
| Voyage code retrieval | `[voyage]` extra, `VOYAGE_API_KEY`, `index plan\|build\|update\|inspect` ([Voyage guide](voyage-retrieval.md)) | Live calls recorded on macOS only | One fixed query through eight live stages (direct and signed-plugin paths agreed); offline replay across the [installed-wheel qualification matrix](qualification.md#platforms) | Paid calls. No general ranking-quality claim. A stage with unknown effects is not retried automatically |
| Claude Code plugin | `/plugin marketplace add Smart-AI-Memory/attune-harness` ([README](../README.md)) | Wherever Claude Code runs; the CLI must be installed separately | `tests/test_claude_plugin.py` keeps the manifests in step with the package, and a test checks the skill's commands against the CLI | Carries the Harness skill, `cross-review`, `roundtable` and `smart-test`, with no MCP server. The live-session receipt is a draft (#180) |
| Codex plugin | Packaged from a checkout ([Codex plugin guide](codex-plugin.md)) | Wherever Codex runs | `tests/test_codex_plugin_package.py` | Not in the wheel; plugin version 0.1.0 |
| MCP and A2A | `mcp-serve` (retrieval grants over stdio) | Local only | Independent-client receipts for MCP (2025-11-25 and 2026-07-28 profiles) and A2A 1.0 | No remote authentication and no automatic host installation |
| Signed Python plugins | `extension install\|inspect\|enable` | All three | Installed-wheel tests across the [qualification matrix](qualification.md#platforms): signatures, revocation, grants, import closure, subprocess bounds | Not an OS sandbox for hostile same-user code. Installing a plugin does not authorize it to run |

## Historical not-carried list

- `ship` and `reflect` are planned verbs; they do not exist.
- attune-ai's hydrate writer, its broader Claude Code workflows and multi-agent
  round-table parity stay in attune-ai. Keep it in its own environment
  ([migration guide](migration-from-attune-ai.md)).
- Remote A2A authentication; the `memory-native` extra for live memories
  (experimental, POSIX only, never exercised in CI).

## Historical observations still owed

Software checks do not stand in for these. The
[project plan](project-plan.md) schedules them for the two weeks after the
release:

- **S3:** memory recall and exclusion observed in real fresh sessions.
- **S6:** an installed walkthrough by a named non-programmer.
- **S9:** each migration row tried against the installed stable artifact.
- Ordinary use of the Claude Code plugin, recorded.
