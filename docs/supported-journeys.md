# Supported journeys and their limits

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

## Install and first run

| Journey | Entry point | Platform limit | Evidence | Where it stops, and what to do |
| --- | --- | --- | --- | --- |
| Install | `pipx install 'attune-harness[all]==1.2.0'` ([README](../README.md#installation)) | Python 3.10 and 3.12 on macOS, Ubuntu and Windows are in the CI matrix; other versions are not | Six installed-wheel platform jobs on every push to `main`; the release gate compares PyPI's hashes with the publish run's `SHA256SUMS` | Harness and attune-ai pin different MCP SDK lines and cannot share an environment. Install each in its own environment |
| First run | `init`, then a `test` preview and the `review` intake ([README](../README.md#your-first-five-minutes)) | Initialization on all three; complete test continuation is POSIX-only | Selected initialization tests run in every platform job; the complete README journey is Windows-skipped | `init` writes offline demo participants. Native participants need `init --profile claude` or `codex`, and a review then needs `--allow-external` |

## Work

| Journey | Entry point | Platform limit | Evidence | Where it stops, and what to do |
| --- | --- | --- | --- | --- |
| Evidence review | `review --goal ... --accept` ([CLI guide](cli-guide.md#task-oriented-evidence-review)) | All three platforms | Review and task tests; the review step of the R2 journey in every platform job | Narratives are unverified model output. Participant disagreement is left for a person to settle, never adjudicated |
| Bounded source review and roundtable | `source-review` or `roundtable`: check, prepare, run, status, evidence, reconcile, assess-citation, abandon | Native Windows and POSIX within the declared snapshot and process profiles | Selected consultation suites, including native retained-handle snapshot tests | Freeze explicit source paths, accept the exact checkpoint and grant each external/native transport. Consultation output remains advisory |
| Plan, accept, build | `plan --request`, `plan --accept`, `build` ([CLI guide](cli-guide.md#plan-and-build)) | Build runs through the POSIX effects profile, or the Windows one, which may refuse with a `FeatureUnavailable` that names Windows | The offline [R2 journey](journeys/r2-clean-environment.md) (plan, accept, build, review, status) runs from the installed wheel in every platform job, with Attune AI absent | No copy-and-paste example: `work.json` needs a frozen effects manifest that no command writes. Native model planning and building are experimental (1 of 24 replies accepted before the contract correction, 12 of 12 after it; not a reliability rate) |
| Import another project's plan | `plan --import-plan PATH --allow-outside-project` ([R4](journeys/r4-legacy-spec-state.md)) | All three platforms | Eight retained fixtures and a conversion receipt per import | Import grants no authority. Acceptance is still a separate step |
| Scoped repair | `fix --goal --checkout --scope --probe` ([CLI guide](cli-guide.md#scoped-repair)) | Local POSIX Git checkouts. On Windows, experimental and unqualified beyond its CI tests | Repair tests; the fail-before, pass-after probe is bound to the task. On Windows, the effects backend's installed owner journey on Windows 2022 and 2025 | Existing regular files only: no creation, deletion, renames or linked worktrees. Use a dedicated checkout |
| Test a change | `test --project --scope` ([CLI guide](cli-guide.md#test-this-change)) | POSIX. Unqualified on Windows | Test-change tests; the preview is saved and accepted by checkpoint | Default pytest discovery only: no custom collectors or committed revision ranges |

## Inspect and recover

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

## Memory

Harness serves memory that is already in Redis, and it can save memory you
give it explicitly. **These are two separate paths: saved entries do not feed
automatic recall.**

| Journey | Entry point | Platform limit | Evidence | Where it stops, and what to do |
| --- | --- | --- | --- | --- |
| Read existing memories | `memory recall`, `resolve`, `refresh` over configured roots ([CLI guide](cli-guide.md#memory)) | POSIX only; on Windows the reader refuses | Every POSIX platform job reads a raw root from the installed wheel; the Windows jobs record the refusal | On Windows, use the POSIX profile through WSL2 |
| Automatic recall at session start or per prompt | `memory serve` from a SessionStart hook; `serve --for PROMPT` through `scripts/memory_prompt_hook.py` | All three; Windows and Redis-only configs serve curated nodes but no file pointers | Synthetic tests of provenance, and of inactive-node and `wrong`-verdict filtering. The path against a hydrated server passed once on a maintainer's machine | Consumes Redis that attune-ai's hydrate writer fills; Harness does not replace that writer. **Not yet observed in real fresh sessions (S3)** |
| Read Redis memory directly | `memory redis status\|digest\|related\|node\|search` (`[redis]` extra) | All three | Every platform job checks the unreachable-server report | Needs a hydrated Redis Stack. A pointer's `text` body is never served |
| Save a memory or task explicitly | `memory saved save\|search\|show\|revise\|forget\|complete` ([saving guide](memory-saving.md)) | POSIX only; Windows refuses before opening the store | Saved-store tests, including replay, conflicts and atomic replacement; native Windows durability and locking remain unqualified | Files are authoritative; Redis is an optional index. Saving a task records intent, not execution |
| Working memory | `memory scratch stash\|retrieve\|forget\|keys` | All three | File and Redis backends in every platform job | An unreachable Redis is reported, never replaced by the file store |

## Retrieval, hosts and extensions

| Journey | Entry point | Platform limit | Evidence | Where it stops, and what to do |
| --- | --- | --- | --- | --- |
| Voyage code retrieval | `[voyage]` extra, `VOYAGE_API_KEY`, `index plan\|build\|update\|inspect` ([Voyage guide](voyage-retrieval.md)) | Live calls recorded on macOS only | One fixed query through eight live stages (direct and signed-plugin paths agreed); offline replay in all six installed-wheel jobs | Paid calls. No general ranking-quality claim. A stage with unknown effects is not retried automatically |
| Claude Code plugin | `/plugin marketplace add Smart-AI-Memory/attune-harness` ([README](../README.md)) | Wherever Claude Code runs; the CLI must be installed separately | `tests/test_claude_plugin.py` keeps the manifests in step with the package, and a test checks the skill's commands against the CLI | Carries the Harness skill, `cross-review`, `roundtable` and `smart-test`, with no MCP server. The live-session receipt is a draft (#180) |
| Codex plugin | Packaged from a checkout ([Codex plugin guide](codex-plugin.md)) | Wherever Codex runs | `tests/test_codex_plugin_package.py` | Not in the wheel; plugin version 0.1.0 |
| MCP and A2A | `mcp-serve` (retrieval grants over stdio) | Local only | Independent-client receipts for MCP (2025-11-25 and 2026-07-28 profiles) and A2A 1.0 | No remote authentication and no automatic host installation |
| Signed Python plugins | `extension install\|inspect\|enable` | All three | Installed-wheel tests on six platform jobs: signatures, revocation, grants, import closure, subprocess bounds | Not an OS sandbox for hostile same-user code. Installing a plugin does not authorize it to run |

## Not carried yet

- `ship` and `reflect` are planned verbs; they do not exist.
- attune-ai's hydrate writer, its broader Claude Code workflows and multi-agent
  round-table parity stay in attune-ai. Keep it in its own environment
  ([migration guide](migration-from-attune-ai.md)).
- Remote A2A authentication; the `memory-native` extra for live memories
  (experimental, POSIX only, never exercised in CI).

## Observations still owed

Software checks do not stand in for these. The
[project plan](project-plan.md) schedules them for the two weeks after the
release:

- **S3:** memory recall and exclusion observed in real fresh sessions.
- **S6:** an installed walkthrough by a named non-programmer.
- **S9:** each migration row tried against the installed stable artifact.
- Ordinary use of the Claude Code plugin, recorded.

## Native Windows inventory — October 15, 2026

This audit supplements the release map above at source baseline
`017d1ba833acd0549d628e4b4f040b77b5e45594`. Parser inspection found 82 leaf
command paths across 32 top-level commands. Optional extras are `redis`,
`voyage`, `memory-native` and `all`; `all` includes Redis/Voyage but excludes
`memory-native`. The normal installed-wheel jobs install Redis/Voyage and
assert Anthropic is absent. They do not exercise the native SDK helper.

A completed journey, an expected refusal, a skipped test and an unobserved path
support different claims. The [baseline Windows 3.10](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/38267127140/job/114872025229)
and [Windows 3.12](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/38267127140/job/114872025322)
installed jobs completed the offline R2 build and review. Their file-memory
receipts explicitly report `posix-only refusal` with no successful tiers.
The qualifier can accept a build refusal on other runs; inspect the receipt.

| Command group | Refusal or boundary owner | Current native witness and remaining gap |
| --- | --- | --- |
| `init` profiles and repair/plan/roundtable starters | [init_cli.py](../src/attune_harness/init_cli.py), required starter inputs and shell rendering | Selected starter tests run; complete documented first-run, test and repair continuations are POSIX-skipped in [test_cold_start_journey.py](../tests/test_cold_start_journey.py) |
| `review-form`, `review`, `inspect-review`, `resume-review`, `reconcile-review`, `transfer-review`, `cancel-review` | [review_cli.py](../src/attune_harness/review_cli.py), registry/acceptance; [review_store.py](../src/attune_harness/review_store.py), native lease | Installed R2 review completes with deterministic assessment; this is software coverage, not live model quality |
| `plan`, imported plans, acceptance and `build` | [work_cli.py](../src/attune_harness/work_cli.py); [work_build.py](../src/attune_harness/work_build.py), roles/budgets/grants | Baseline installed R2 build completed; dependent build-to-test handoff is blocked by the testing owner |
| `fix` and assessment-to-repair | [repair.py](../src/attune_harness/repair.py), dedicated checkout, scope, probe and native admission | Effects owner tests pass; complete documented repair continuation remains Windows-skipped |
| `test`, including completed-task handoff | [test_change.py](../src/attune_harness/test_change.py), POSIX admission and override refusal; [task_handoff.py](../src/attune_harness/task_handoff.py), completed evidence | Windows feature is blocked; preview refusal is not test execution |
| `status`, `resume`, `reconcile-task`, `transfer-task`, `cancel-task` | [task_cli.py](../src/attune_harness/task_cli.py), profile dispatch and recovery | Selected native recovery tests run; testing recovery awaits native execution. Actual commands are `status` and `resume` |
| `source-review`, `roundtable` (eight actions each) | [consultation_cli.py](../src/attune_harness/consultation_cli.py); [consultation.py](../src/attune_harness/consultation.py), frozen source, checkpoint and explicit grants | Implemented bounded Harness consultation; selected consultation and native snapshot tests run. This does not qualify every Attune AI workflow |
| `memory capabilities`, `recall`, `resolve`, `refresh` | [memory_reader.py](../src/attune_harness/memory_reader.py), capture, root authority, expiry/scope/version | Windows refuses; raw, personal and curated tiers need successful installed witnesses |
| `memory serve` and prompt hook | [memory_serving.py](../src/attune_harness/memory_serving.py), authorized pointer/verdict reads | Installed witness covers skipped output; curated synthetic tests are separate. File pointers remain blocked |
| `memory redis` (five actions) | [memory_redis.py](../src/attune_harness/memory_redis.py), optional dependency/config/query bounds | Installed Windows checks cover disabled/unreachable outcomes; hydrated-server success needs separate evidence |
| `memory scratch` (five actions) | [memory_scratch.py](../src/attune_harness/memory_scratch.py), root/config/native locks | Installed file-store round trip completes; unreachable Redis never substitutes file storage |
| `memory saved` (eight actions), linked tasks and pending review | [memory_saved.py](../src/attune_harness/memory_saved.py), platform, linked identity, completion; [memory_saved_cli.py](../src/attune_harness/memory_saved_cli.py), pending filter | All Windows storage operations refuse. Equivalent durability/private ACL/locking proof precedes production implementation |
| `memory create`, `replay`, `inspect`, `execute` | [memory_context.py](../src/attune_harness/memory_context.py), host/job authority; [memory_native.py](../src/attune_harness/memory_native.py), native preflight | Offline worker tests are distinct from the actual SDK helper; native transport is blocked and absent from normal installed qualification |
| `code-config`, `index` (four actions), `retrieval-task`, provider `retrieve` | [voyage_cli.py](../src/attune_harness/voyage_cli.py); [voyage_provider.py](../src/attune_harness/voyage_provider.py), paid grant/key/SDK | Offline selected tests run; no live Windows provider qualification |
| Keyword `retrieve`, `verify` | [retrieval.py](../src/attune_harness/retrieval.py), [verification.py](../src/attune_harness/verification.py), dependency and bounded input guards | Installed successful and negative CLI witnesses exist |
| `mcp-serve`, `mcp-inspect` | [cli.py](../src/attune_harness/cli.py), profile conflicts; [mcp_server.py](../src/attune_harness/mcp_server.py), accepted grant/freshness | Installed MCP/workspace tests run; protocol checks alone do not establish a complete user journey |
| `extension` (seven actions) | [extension_cli.py](../src/attune_harness/extension_cli.py); [plugin_runtime.py](../src/attune_harness/plugin_runtime.py), signed imports/grants/SystemRoot | Native plugin probe completes; installing a bundle grants no execution authority |
| `spec intake`, `spec present` (four views) | [spec_cli.py](../src/attune_harness/spec_cli.py), accepted-result evidence | Selected intake/presentation tests run; native test-result production awaits the testing port |
| `triage-check`, `repair-economics`, `github-checks`, no-argument demo | [cli.py](../src/attune_harness/cli.py), bounded trusted exports | Selected operation/GitHub tests and installed demo run; none authorizes workflow dispatch |

The first full native source measurement in [PR #266](https://github.com/Smart-AI-Memory/attune-harness/pull/266)
reached pytest on Python 3.10 and 3.12, then both jobs were cancelled at the job
deadline without retained test output. That is an unresolved baseline, not a
passing Windows suite. The current revision fixes pipe readiness, preserves source
bytes and retains verbose output before the job deadline. Feature parity remains
open until successful native journeys and all required checks are recorded.
