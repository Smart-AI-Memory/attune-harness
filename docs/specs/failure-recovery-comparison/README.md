# Failure and recovery: Harness, Superpowers and native Claude Code

**Status: D1–D6 approved November 6, 2026; T1 offline work authorized.**
Patrick authorized the offline fixture and controls with no live model calls.
T2–T4, live trials, spending and publication remain separately gated.
Prepared November 6, 2026 against Harness main
`9310486409fbe61529a45706b6073c52eb8e463f`. The released runtime is
[1.7.0](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.7.0),
source `5159e7a79fbdb84d2982937716043b142534e6e9`; runtime and package metadata
are unchanged between those revisions. No competitor was installed or run to
prepare this specification.

## Outcome

Give a developer inspectable evidence of how each workflow handles an attempted
scope violation, attempted test tampering, a clean pause and an abrupt
interruption. Show what prevented a bad effect, what detected one, what survived
and what a person had to do to continue. A result may favor any arm or establish
no meaningful difference.

This is a comparison of complete workflows on a small synthetic task, not an
isolated model evaluation. It does not establish general reliability, security,
OS isolation, lower cost or market superiority.

Read [the design](design.md), [proposed decisions](decisions.md) and
[ordered tasks](tasks.md). Patrick's direct approval covers D1–D6 and T1 only;
it grants no live model calls, account operations, spending or publication.

## Requirements and acceptance

| ID | Requirement | Done when |
| --- | --- | --- |
| R1 | Freeze a fair comparison | Installed identities, effective host settings, task facts, model/role configuration, permissions, budgets and scenario order are recorded before scored attempts. Required differences are disclosed. |
| R2 | Separate prevention from detection | Each case records model behavior, host/workflow refusals, observed effects, independent observer findings and human interventions separately. Missing telemetry stays unknown. |
| R3 | Distinguish pause from uncertain interruption | The two interruption scenarios have different trigger evidence and recovery criteria; a missing stop confirmation blocks continuation. |
| R4 | Protect the independent verdict | A separate oracle and original test hashes determine outcomes. Product completion prose, exit status and observer intervention cannot manufacture a pass. |
| R5 | Preserve every assigned attempt | The report includes all attempts, failures, non-exercised challenges, timeouts and inadmissible injections, with original records and denominators. |
| R6 | Make the result understandable | A reader can identify accepted scope, observed violation, checking coverage, recovery limits and required next action from a concise report linked to raw evidence. |
| R7 | Qualify collection before live work | Offline controls expose defective recording/scoring and each arm's actual trigger/resume seam is verified before its live campaign. Scripted replies never count as model-performance evidence. |

## Scope and limits

Use one machine and five scenarios in three arms: Harness, Superpowers and
native Claude Code. First qualify fixtures and recording without model calls.
The proposed live pilot contains **15 assigned attempts**, one per arm/scenario,
and needs a separate exact model/funding/budget decision. No numeric outcome is
claimed now. Initial platform: macOS arm64; record the actual OS and interpreter.
No Windows, cross-host handoff, team population or statistical superiority claim
follows from it. Experimental Claude agent teams are not a fourth arm.

Do not change Harness production code, weaken competitor controls, edit retained
campaigns, install into a retained working environment or collect private project
data. If a required measurement cannot be obtained without a product change,
report the gap and stop that affected task for a scope decision.

## Current command-owner walk and input flow

These are source-checked operations for the future implementation, not a
copy-and-run campaign. Fixture preparation and the observation controller do not
exist yet. T1/T2 must produce their concrete paths, manifests and tested commands.
This table checks current product prerequisites; it does not claim that the
whole comparison journey has executed. Local source links cite refusal owners;
closed-source Claude behavior is labeled documented rather than assigned an
invented public `raise`.

### Harness

Use an isolated installed 1.7.0 runtime and a small standalone clone with a real
`.git` directory. A linked worktree does not meet this effects profile. Use
canonical paths; `/private/tmp` is usable on macOS where `/tmp` is a symlink.

| Order and operation | Owner refusal | Input flow that satisfies it |
| --- | --- | --- |
| 1. Prepare clone, external interpreter, tests and registry | [Freeze](../../../src/attune_harness/work_effects.py#L247-L265) refuses overlapping task storage and requires a real Git directory; [probe validation](../../../src/attune_harness/repair.py#L127-L165) bounds interpreter, tests and environment. | T1 supplies a committed fixture, interpreter outside the clone with pytest installed, existing visible tests and external storage. Write and validate the real proposal-capable registry at `<clone>/participants.json` before freezing; use that same path for **`plan --config`**. |
| 2. **`init --for plan`** with explicit goal, scope, interpreter, tests and task directory | [Starter validation](../../../src/attune_harness/init_cli.py#L328-L367) rejects missing inputs and existing request/task paths; [storage](../../../src/attune_harness/task_contract.py#L69-L84) rejects links and metadata paths. | Step 1 supplies nonempty goal; output scope `src/report.py` and `tests/generated/test_report_extra.py`; protected oracle `tests/test_report.py`; and a new task locator. Init preserves the existing registry. The generated request stays beside, not inside, the frozen clone. Verify returned worker/reviewer IDs before preview. |
| 3. **`plan --request … --project … --config … --task-dir …`** | [CLI validation](../../../src/attune_harness/work_cli.py#L570-L598) and [capture](../../../src/attune_harness/work_contract.py#L340-L365) require valid request, project/config, real evidence and external task storage. | Consume the actual starter output, unchanged fixture and selected registry. Save the displayed checkpoint and full scope. Preview creates no acceptance or dispatch authority. |
| 4. **`plan --accept --task-dir TASK --checkpoint CURRENT`** | [CLI parsing](../../../src/attune_harness/work_cli.py#L31-L36) requires the task directory; [acceptance](../../../src/attune_harness/work_cli.py#L479-L480) refuses a different checkpoint; [intent validation](../../../src/attune_harness/work_contract.py#L587-L595) refuses incomplete intent; [freshness](../../../src/attune_harness/work_contract.py#L717-L727) refuses changed inputs. | Inspect step 3. Reuse its task directory, checkpoint and complete intent. Install normal base dependencies, including the accepted Forms version; a minimal no-dependency runtime cannot perform this acceptance journey. |
| 5. **`build TASK --allow-external --allow-native`** | [Effect ownership](../../../src/attune_harness/work_runtime.py#L311-L318), [preflight](../../../src/attune_harness/work_build.py#L98-L128) and [dispatch checks](../../../src/attune_harness/work_build.py#L744-L760) require accepted scope, protected probes, distinct roles and explicit dispatch authority. | Step 4 supplies current acceptance. T2 must validate Claude planner/worker/reviewer configuration with empty workflow tool lists. The default review registry and demonstration reviewer are not live comparison participants. Native funding remains inherited/unverified; spec approval grants no inference authority. |
| 6. **`status TASK`**, before any continuation | [Read-only status](../../../src/attune_harness/work_runtime.py#L281-L303) reports retained state; a successful inspection is not a successful build. | Capture saved events, file identity, checking evidence and errors. Confirm owned processes stopped and classify the actual boundary. |
| 7. **`resume TASK --checkpoint CURRENT --allow-external --allow-native`**, only if admissible | [Resume validation](../../../src/attune_harness/work_build.py#L795-L817) refuses changed permissions and unresolved dispatch; [recovery](../../../src/attune_harness/recovery.py#L196-L220) reuses completed results rather than blindly repeating them. | Step 6 supplies current status. Use the same authority and current checkpoint. Uncertain work does not become admissible merely by supplying flags. The [current reconciliation owner](../../../src/attune_harness/work_effects.py#L730-L742) settles file effects, not interrupted acceptance probes: C4 may correctly remain unresolved. Preserve that result rather than manufacturing a completed check or replacing the task. |

The starter emits one task, with task and final protected verification. Choose
any `--max-operations` pause point from that fixture's observed event sequence;
do not guess a number or describe the resulting settled pause as a crash.

### Superpowers inside Claude Code

Pin Superpowers 7.0.2 at
`22f0b463e7a5e579904dd6211a520321035526f7`. Its
[documented author marketplace](https://github.com/obra/superpowers/blob/22f0b463e7a5e579904dd6211a520321035526f7/README.md#L56-L82)
provides `/plugin marketplace add obra/superpowers-marketplace` followed by
`/plugin install superpowers@superpowers-marketplace`. Record the installed
commit: the marketplace Git URL itself is not pinned. At research time the
official Claude marketplace selected 7.0.0, not 7.0.2. Installation and update
actions are future work, not preparation performed for this spec.

There is no Superpowers **`plan`**, **`build`** or **`resume`** CLI. The host
invokes skills and their helpers.

| Order and operation | Owner refusal or instruction | Input flow that satisfies it |
| --- | --- | --- |
| 1. Invoke brainstorming, then writing-plans in Claude Code | [Design approval](https://github.com/obra/superpowers/blob/22f0b463e7a5e579904dd6211a520321035526f7/skills/brainstorming/SKILL.md#L269-L283) and [plan review](https://github.com/obra/superpowers/blob/22f0b463e7a5e579904dd6211a520321035526f7/skills/writing-plans/SKILL.md#L179-L204) are skill instructions, not inspected executable refusals. | Supply identical task facts, approve the resulting bounded design/plan and record the approvals. Freeze SDD execution mode before scored attempts. |
| 2. Use its normal worktree workflow and SDD workspace | [Worktree guidance](https://github.com/obra/superpowers/blob/22f0b463e7a5e579904dd6211a520321035526f7/skills/using-git-worktrees/SKILL.md#L16-L132) requires isolation checks and handling failing baselines; [sdd-workspace guards](https://github.com/obra/superpowers/blob/22f0b463e7a5e579904dd6211a520321035526f7/skills/subagent-driven-development/scripts/sdd-workspace#L35-L102) require a real plan and working tree. | The committed fixture and reviewed plan exist. Record the actual resulting checkout/root and ledger path; do not observe the original clone while the product writes in a new worktree. |
| 3. Extract task, implement, commit and review | [task-brief](https://github.com/obra/superpowers/blob/22f0b463e7a5e579904dd6211a520321035526f7/skills/subagent-driven-development/scripts/task-brief#L19-L105) refuses missing/malformed tasks; [review-package](https://github.com/obra/superpowers/blob/22f0b463e7a5e579904dd6211a520321035526f7/skills/subagent-driven-development/scripts/review-package#L21-L41) rejects invalid or empty commit ranges. | Use the generated English `Task` heading, capture BASE before implementation and commit before generating its review package. Retain normal reviewer loops and task state. |
| 4. Inspect and continue through the host session and matching ledger | [Resume instructions](https://github.com/obra/superpowers/blob/22f0b463e7a5e579904dd6211a520321035526f7/skills/subagent-driven-development/references/resuming.md#L1-L12) direct the agent to skip recorded completed tasks and continue fix rounds. | Preserve the plan, ignored workspace, `progress.md` and Git history. Do not clean ignored state. A task commit without the matching completion ledger is not the clean-pause trigger. |

Inline execution is a different supported mode: its
[task-done helper](https://github.com/obra/superpowers/blob/22f0b463e7a5e579904dd6211a520321035526f7/skills/executing-plans/scripts/task-done#L12-L55)
runs the test command and appends completion only after exit zero. Do not claim
that Superpowers has no executable checks. Switching to inline execution after
observing SDD results requires a new campaign or an explicitly reported deviation.

### Native Claude Code and shared host operations

Pin [Claude Code 2.1.318](https://github.com/anthropics/claude-code/releases/tag/v2.1.318)
in all arms. The following flags and controls come from
[official CLI documentation](https://code.claude.com/docs/en/cli-reference),
[permissions](https://code.claude.com/docs/en/permissions) and
[checkpointing](https://code.claude.com/docs/en/checkpointing). Public
implementation-level `raise` citations are unavailable for this host.

| Order and operation | Documented precondition or limit | Input flow that satisfies it |
| --- | --- | --- |
| 1. **`claude --version`** | The study, not Claude itself, refuses a different binary/version. | T2 records absolute executable path, version and artifact hash before and after attempts; background updates are disabled in the trial profile. |
| 2. Start with **`claude --session-id UUID --model MODEL --permission-mode plan --settings PROFILE`** | Session ID must be a valid UUID and settings must be valid; Plan mode excludes source edits. | T2 supplies unique UUID, authorized exact model and validated profile. These are unresolved deployment values, not commands ready for collection. Inspect **`/permissions`** and all effective inherited settings. |
| 3. Review the plan, then use **`claude --resume UUID --model MODEL --permission-mode default --settings PROFILE`** | A persisted discoverable session is required. `default` explicitly selects Manual permissions; it is not every account's natural default. | Record human plan acceptance and mode transition separately. Keep persistence and ordinary subagents enabled. Do not pass `--fork-session` or `--no-session-persistence` in the native or Superpowers lead. |
| 4. Clean pause or separately controlled abrupt termination | **Ctrl+C** interrupts an operation; it does not establish crash recovery. | For the clean scenario, first observe completed task/check evidence. For the abrupt scenario use the qualified external controller and check-start barrier from the design. Confirm stop before reading/resuming as an exclusive writer. |
| 5. Resume the exact UUID with the same explicit flags | A conversation resume is not restoration of running processes or automatic rollback. **`/rewind`** only restores supported tracked edits. | Inspect files, preserved tests and saved context first. Record any human reconciliation and real resumed behavior. Bash-only and many subagent-only edits are outside checkpoint restoration coverage. |

## Verification and remaining gate

Patrick approved D1–D6 and selected T1 after reviewing this draft. This spec
records source inspection only; it does not record completed implementation.
T1/T2 must exercise concrete adapter commands and
injection triggers; unsupported cells cannot be silently replaced by mocks.
Live work additionally waits for exact runtime/profile eligibility, approved
models/funding, a spending ceiling and the frozen campaign manifest.

**Completion review: complete for this spec draft.** The private review records
the source-bound recovery limit, fairness findings and their disposition.
Implementation milestones require their own completion reviews; no comparison
result or implementation approval is recorded here.
