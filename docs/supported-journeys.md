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
checks for that source and its artifacts. See the capability table below and
the [Windows checkpoint](specs/windows-parity/tasks.md) for workflow-specific
reliability boundaries.

## Windows capabilities and reliability

Version 1.5.0 includes native Windows implementations for captured tests,
file-memory reads, saved memory and task storage, and experimental native-memory
transport. The table pairs their available functionality with the reliability
boundaries of the retained evidence.

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

Use the [approved design and acceptance criteria](specs/windows-parity/design.md)
and [retained Windows checkpoint](specs/windows-parity/tasks.md) to review the
evidence for these guarantees. The requirements remain unchanged; the table
keeps each remaining reliability boundary beside its available capability.

## Install and first run

| Journey | Entry point and guidance | Evidence and remaining limit |
| --- | --- | --- |
| Install the released base | `uv tool install 'attune-harness==1.5.0'`; inspect the selected version/path with `uv tool list --show-paths`. See the [release README](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.5.0/README.md#installation). | The release record reports a fresh macOS base install and installed CLI checks. Python 3.10+ is required; hosted checks exercise 3.10/3.12. Keep Harness and Attune AI in separate environments. This map does not qualify an upgrade or every saved-work migration. |
| Prepare a first task | `init`; `init --for plan` or `init --for fix` for scoped starter files. Follow the existing [CLI examples](cli-guide.md) and [starter specification](specs/starter-files/tasks.md). | Starter generation writes the request and probe files for the selected workflow. Demo participants cannot propose a build; use the documented command worker or an explicitly configured participant. Preparation does not execute a model. |

## Work

| Journey | Entry point and guidance | Evidence and remaining limit |
| --- | --- | --- |
| Plan, accept and build | `plan --request`, `plan --accept`, then `build`; [plan/build guide](cli-guide.md#plan-and-build). | The [R2 installed journey](journeys/r2-clean-environment.md) supplies the offline owner chain. Review findings and optional function-body boundaries are integrated. Native/model reliability is a separate qualification; accepting intent does not authorize paid calls. |
| Review evidence and select a repair | `review`; explicit `fix --from-assessment` with selected finding IDs. See the [CLI guide](cli-guide.md#task-oriented-evidence-review). | [The handoff owner](../src/attune_harness/task_handoff.py) binds selected provenance. Model narratives remain unverified proposals. Selecting findings does not authorize a wider repair or automatic execution. |
| Repair scoped files | `fix --goal --checkout --scope --probe`; [repair guide](cli-guide.md#scoped-repair). | Existing protected probes and effects owners apply. Windows effects have hosted checks, while strict arbitrary-descendant stop/recovery and declared Windows shell/desktop journeys remain open. Use the documented source profile and a dedicated checkout. |
| Test a captured change | `test --project --scope`; `test --from-task` for eligible completed work. See [testing guidance](cli-guide.md#test-this-change). | Windows captured execution is merged in [#271](https://github.com/Smart-AI-Memory/attune-harness/pull/271), with installed component witnesses. Acceptance, single-dispatch recovery and immutable evidence remain required; the process-completion boundary is listed in the table above. |
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
| Read configured memory files | `memory recall`, `memory resolve`, `memory refresh`, `memory serve`; [memory guide](cli-guide.md#memory). | Native Windows readers are merged in [#272](https://github.com/Smart-AI-Memory/attune-harness/pull/272), retaining the 4,096-file/root, 8 MiB/file and 64 MiB/query bounds and native path/identity checks. Combined desktop/shell acceptance remains open. |
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
Bounded maintainer forms observations do not close all three. Windows acceptance
follows the [unchanged reliability criteria](specs/windows-parity/design.md),
including strict process/recovery, full storage, live native memory, Windows 11
standard-user desktop and Windows PowerShell/PowerShell 7 journeys.

The [current opportunity register](opportunity-log.md#current-register) identifies
remaining work.
