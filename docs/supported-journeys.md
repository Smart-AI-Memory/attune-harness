# Choose a Harness workflow

Updated on October 22, 2026. This guide describes the 1.5.1 source and package.
Read the [release notes](release-notes-1.5.1.md) and
[readiness record](release-readiness-1.5.1.md) for publication status, checks and
behavior introduced after 1.5.0.

Find your goal below, then follow the linked procedure for setup and complete
commands. New to Harness? Start with the [installation guide](installation.md)
and choose a [practice walkthrough](tutorials-1.5.0-candidate.md#choose-a-walkthrough).

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
| Inspect a completed document assessment | [Assessment evidence](cli-guide.md#inspect-completed-assessment-evidence-151-candidate): `status --format markdown` or `html` | In 1.5.1, inspect recorded checker outcomes, source identities and attributed judgments. Reading the report does not rerun checks or establish semantic acceptance. |
| Resolve an interrupted operation | [Recovery workflow](recovery-workflow.md): `reconcile-task` | Choose the action supported by the saved evidence. Do not repeat an operation whose effects are still unknown. |
| Close a task | [Recovery workflow](recovery-workflow.md): `cancel-task --reason` | Record why work stopped. Cancellation does not undo effects or erase unresolved operations. |
| Save and approve a request in a browser | [Forms workflow](cli-guide.md#browser-forms) | Open a registered task, save answers and approve the request. Approval does not execute work. Keep the local forms server running while using it. |

## Memory

**Saving a memory does not automatically add it to session recall.** Choose the
path that matches how you want to store or retrieve information.

| What you want to do | Where to start | What you need to know |
| --- | --- | --- |
| Read configured memory files | [File-memory guidance](cli-guide.md#memory): `memory recall`, `resolve`, `refresh` | Configure the roots you want Harness to read. Windows requires supported local NTFS paths. |
| Recall memory at session start or for a prompt | [Memory serving](cli-guide.md#memory): `memory serve` | Reads an existing hydrated Redis index; file access also needs configured roots. Keep your existing hydration writer. |
| Save memories or task intent | [Saved memory](memory-saving.md): `memory saved` | Keep revisions and history, then retrieve entries explicitly. Saving task intent does not execute the task. See the Windows storage limits below. |
| Keep temporary working information | [Scratch memory](cli-guide.md#memory): `memory scratch` | Choose file or Redis storage explicitly. The file backend does not declare sharing. Redis failure does not switch storage backends. |
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
| Build or repair files | Use a dedicated checkout on fixed local NTFS. The repair profile accepts existing UTF-8 files up to 64 KiB. | Some child-process shutdown and recovery cases remain unresolved. |
| Test a captured change | Select a Python environment with your test dependencies and approve the captured test plan. | Child-process shutdown must complete before captured output is read or the process is reported complete; some Windows cases remain unresolved. |
| Read memory files | Configure supported local NTFS roots. | Unsafe paths and unsupported volumes are refused. |
| Save memories or task intent | Use the documented local storage profile. Keep an independent copy of important data. | Windows concurrent-write and power-loss durability validation is incomplete. |
| Use native-memory proposals | Install the separate experimental extra and configure the provider only when needed. | Offline transport checks exist; live-provider use has not completed validation. |

Inspect interrupted or uncertain runs before attempting recovery. A retry must
not silently repeat an operation. Windows 11 desktop and PowerShell workflows
still need end-to-end validation.

## Technical evidence

Use these references when you need to inspect the checks or reliability criteria:

- [1.5.0 release record](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.5.0): source, distribution hashes and published-install checks.
- [Platform qualification](qualification.md): CI matrix and installed-wheel procedures.
- [Windows reliability reference](windows-reliability.md): exact requirements, evidence bindings and remaining validation.
