# Choose a Harness workflow

Updated on October 30, 2026, for unreleased Harness 1.6.0 preparation.
Published 1.5.1 remains available; this guide does not announce a final 1.6.0 artifact.

Find your goal below, then follow its procedure for setup, commands and expected
results. New to Harness? Start with the [installation guide](installation.md)
and choose a task in the [Help goals guide](https://smartaimemory.com/harness/help/goals/).
Read the [1.6.0 release notes](release-notes-1.6.0.md) for changes and migration.
Earlier [1.5.1 preparation walkthroughs](tutorials-1.5.1.md#choose-a-walkthrough)
remain historical examples with their original source and runtime.

## Work

| What you want to do | Where to start | What to expect |
| --- | --- | --- |
| Plan and build a change | [Plan and build](cli-guide.md#plan-and-build): `init`, `plan`, `build` | Review and accept the plan before execution. Use a dedicated checkout and configure a worker that can make the change; demo reviewers cannot build. |
| Review a document or proposed change | [Evidence review](cli-guide.md#task-oriented-evidence-review): `review` | Compare it with your criteria and supporting evidence. Choose which findings to act on; a review does not apply repairs automatically. |
| Repair existing files | [Scoped repair](cli-guide.md#scoped-repair): `fix` | Check the proposed repair against a protected test. The repair profile excludes file creation, deletion, renames and linked Git worktrees. |
| Check a code change | [Captured testing](cli-guide.md#test-this-change): `test` | Preview the tests, approve the plan, then inspect the results. Tests run in a captured copy using your selected Python environment. |
| Consult configured models | [Model consultation](model-consultation.md): `roundtable`, `source-review` | Gather independent responses. Setup does not call a model; execution needs the configured participants and permission for any paid calls. |
| Bring in an existing plan | [Plan import](journeys/r4-legacy-spec-state.md): `plan --import-plan` | Inspect the imported plan before accepting it. Importing a plan does not authorize execution. |

Use trusted workers, commands and tests; a captured copy is not a security
sandbox. For Windows build, repair and testing, read the
[process reliability limits](#windows-capabilities-and-reliability) before running.

## Inspect and recover

| What you want to do | Where to start | What to expect |
| --- | --- | --- |
| Continue saved work | [Pause and return](cli-guide.md#pause-and-return-to-work): inspect `status` before any authorized `resume` | Retain an explicit stopping note and inspect its source and freshness. Completed work reuses saved evidence; uncertain effects require reconciliation before continuation. |
| Inspect a completed document assessment | [Assessment evidence](cli-guide.md#inspect-completed-assessment-evidence-151-candidate): `status --format markdown` or `html` | Inspect recorded checker outcomes, source identities and attributed judgments. Reading the report does not rerun checks or establish semantic acceptance. |
| Recover after an interruption | [Recovery workflow](recovery-workflow.md): **`reconcile-task`** | The saved task history helps you see where work stopped and choose the next recovery step. Available recovery actions depend on the task type and its recorded outcome. |
| Close a task | [Recovery workflow](recovery-workflow.md): `cancel-task --reason` | Record why work stopped. Cancellation does not undo effects or erase unresolved operations. |
| Save and approve a request in browser forms | [Forms companion](cli-guide.md#browser-forms): the browser interface for existing task drafts | Answer questions, save your draft, review the request and approve it when ready. Return to your saved answers later. Approval records the request; execution is a separate step. Browser build dispatch and execution resume are unavailable; use the CLI for those operations after reviewing saved state. |

## Memory

Harness 1.6.0 supports file-based memory and optional Redis-backed memory. You can
read memory files, save memories and keep local working notes without Redis.
The Redis integration adds access to an existing Redis memory index and shared
temporary working notes; it requires the `redis` extra and a configured service. Live Redis+Search verification for the final 1.6.0 artifact remains incomplete; offline profiles do not establish
a live service result. A new Redis projection writer and RedisVL adoption remain outside 1.6.0.

For long-term Redis memory, 1.6.0 includes readers for existing data. Keep the
separate writer and startup hooks that prepare and deliver that memory. The new
generation reader is optional; installing it does not create or update the index
or arrange automatic recall in a fresh session.

| What you want to do | Where to start | What you need to know |
| --- | --- | --- |
| Read configured memory files | [File-memory guidance](cli-guide.md#memory): `memory recall`, `resolve`, `refresh` | Configure the roots you want Harness to read. Windows requires supported local NTFS paths. |
| Retrieve existing memory for a prompt | [Memory serving](cli-guide.md#memory): **`memory serve`** | Read context from your existing Redis memory setup. The optional generation reader identifies the snapshot used. Keep the writer and startup hooks that prepare and deliver the memory. |
| Save memories or task intent | [Saved memory](memory-saving.md): `memory saved` | Keep revisions and history, then retrieve entries explicitly. Saving task intent does not execute the task. See the Windows storage limits below. |
| Keep temporary working information | [Scratch memory](cli-guide.md#memory): **`memory scratch`** | Keep local notes in files, or use optional Redis storage to share them across processes and machines. Choose the storage explicitly; an unavailable Redis service is reported rather than silently switching to files. |
| Inspect the Redis memory index | [Redis access](cli-guide.md#memory): `memory redis` | Requires the Redis extra and a reachable configured service. File-pointer records do not include the file's contents. |
| Prepare model-generated memory proposals | [Native-memory guidance](specs/windows-parity/README.md#native-memory-proposal-transport): `memory create`, `memory execute` | Requires the separate experimental `memory-native` extra. Provider execution needs credentials and paid-call approval; installation grants neither. |

## Connect tools

| What you want to do | Where to start | What you need to know |
| --- | --- | --- |
| Use Harness from Claude Code or Codex | [Claude Code setup](../README.md#use-harness-with-codex-claude-or-other-models) or [Codex setup](codex-plugin.md) | Install the host integration and CLI separately. Confirm which runtime the integration uses. |
| Search code with Voyage embeddings | [Voyage retrieval](voyage-retrieval.md) | Install the Voyage extra, configure credentials and approve paid calls before building or updating an index. |
| Serve scoped retrieval through MCP | [CLI guidance](cli-guide.md): `mcp-serve` | Uses local stdio. Remote authentication and automatic host setup are not provided. |
| Run a signed Python extension | [Signed extension procedure](executable-plugin-run.md) | Inspect and accept the artifact and its grants. Installation does not authorize execution; extensions are not a security sandbox. |

## Windows capabilities and reliability

Windows includes native implementations for captured testing, file-memory reads,
saved memory and task storage, and experimental native-memory transport.
Choose the setup and reliability conditions for your workflow:

| Workflow | Setup | Reliability consideration |
| --- | --- | --- |
| Build or repair files | Use a dedicated checkout on fixed local NTFS, with a local `.git` directory and task state outside it. The repair profile accepts existing UTF-8 files up to 64 KiB; linked Git worktrees and creation/deletion/renames remain refused. | If stop or wait cannot be confirmed, Harness records unknown effects. Inspect the saved task and affected processes/files before choosing a recovery action; do not assume rollback or redispatch. |
| Test a captured change | Select a Python environment with your test dependencies and approve the captured test plan. | The selected interpreter must exist and the task directory must be outside the project. Child shutdown must be confirmed before output is read or completion reported; uncertain shutdown requires inspection. |
| Read memory files | Configure supported local NTFS roots. | Unsafe paths and unsupported volumes are refused. |
| Save memories or task intent | Use the documented local storage profile. Keep an independent copy of important data. | Windows concurrent-write and power-loss durability validation is incomplete. |
| Use native-memory proposals | Install the separate experimental extra and configure the provider only when needed. | Offline transport checks exist; live-provider use has not completed validation. |

Inspect interrupted or uncertain runs before attempting recovery. A retry must
not silently repeat an operation. The merged PR #320 tree passed installed, full-source
profiles on both Windows Server 2022 and 2025 with Python 3.12. A separate
`windows-latest` supplemental coverage job also passed. That is evidence
for those workflows and fixtures, not complete desktop or storage durability.
A separate Windows 11 standard-user smoke used x64 Python under ARM emulation;
it does not establish native ARM64 parity or all PowerShell workflows.

## Technical evidence

Use these references when you need to inspect the checks or reliability criteria:

- [1.6.0 preparation and evidence](release-preparation-1.6.0.md): source/CI identity and remaining final-artifact gates; unreleased.
- [Documentation archive](https://smartaimemory.com/harness/help/archive/): earlier versioned guides and observations.
- [Platform qualification](qualification.md): CI matrix and installed-wheel procedures.
- [Windows reliability reference](windows-reliability.md): exact requirements, evidence bindings and remaining validation.
