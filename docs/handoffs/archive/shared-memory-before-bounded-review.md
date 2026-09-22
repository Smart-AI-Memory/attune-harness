# Shared memory adoption handoff

## Latest checkpoint — overnight continuation, 2026-09-17

**Paused at Task 4 gate revision 19; Tasks 1–3 remain accepted (3/5).**
The active plan comment remains current=4, auto_run=true; no risk acknowledgement
or Task 4 acceptance was collected. The heartbeat is paused for the unresolved
review decision. Read [the persistent gate](../specs/shared-memory-adoption/task4-gate.md)
and [verification/support matrix](../specs/shared-memory-adoption/verification.md).
Do not resume a refused review through another channel or interpret functional
review as covering the omitted scope.

Completed since the earlier checkpoint:

- Corrected refresh status: partial/unavailable now produces exit 2 through both
  actual CLIs. Four regression cases detect restoration of the old behavior.
- Source tests: 122 entrypoint/CLI checks before final adapter maintenance;
  final 221 memory checks after all repairs. Full quality/gate suite: 678 passed.
  Collaboration preflight: 87 passed. Pinned lint/format and whitespace checks pass.
- Refactored the existing raw-read branch to satisfy the complexity ratchet;
  read failures catch specific expected types. Unexpected defects reach host
  failed JSON. The strict single-write boundary still reports arbitrary backend
  post-commit exceptions as uncertain, without retry/diversion. Its documented
  baseline exception 14→15 was independently reviewed with a custom after-write
  regression. No other exception allowance changed.
- Changed AI dispatch/handler coverage: 100%; final adapter 225/247 = 91.09%.
  Four temporary protection removals caused eight expected test failures;
  the separate shutdown positive control reached the intercepted uploader only
  with the usage guard removed. All 108 frozen native receipts remain unchanged.
- Sol/high ordinary functional review closed the refresh P2. The scoped
  maintainability/gate-exception review returned no findings. Exact independent
  probes rerun centrally. Neither covers authorization/security; the original
  broader review's automated safety refusal is preserved and is still a gate gap.
- Task 5 preparation only: rebuilt wheels, three fresh isolated installations,
  both generated CLI entry points and actual MCP transport, 145 installed checks,
  24 legacy checks with the new route disabled, 11 module hash comparisons.
  Dependencies reused from an installed path without editable hooks; fresh
  dependency resolution and other platforms are not claimed. Final artifacts:
  Harness SHA f347a41fc90a7a8db56fff9d361fb4b92eba9b38fa048cb871dd599325f9829a;
  AI SHA 10e18684f521a4ebc56d3280bd408599d8d7fffa6e58c87d789ab1fe140ae91b.
- R5 review ledger updated in the isolated AI worktree. Opportunity log now also
  records packaging metadata maintenance and fuller preflight diagnostics.

All receipts: `docs/receipts/shared-memory-adoption-task4/`. The two independent
review files, reproducer scripts, full gate logs, failed attempts and installed
module/package records are retained. Progress JSON binds final source hashes.
No live memories, provider calls, publication or activation occurred.

Next: resolve the missing broader independent review (or an explicit chair
change to acceptance requirements), collect the bound Task 4 action through the
canonical workspace, save any returned state, then resume sequential Task 5.
Do not automatically choose `acknowledge_risk`. The ready installed evidence
can be reused only while its bound source/artifact hashes still match.


## Goal

Use one shared memory worker from attune-harness and attune-ai while preserving
existing useful memories and keeping control at the host boundary.

## Acceptance criteria

The approved five-task ladder is in `.claude/plans/shared-memory-adoption.md`;
requirements and boundaries are in `docs/specs/shared-memory-adoption/`.
Reading existing formats comes first. Installed integration, qualified effects
and receiving-agent context follow. Live activation/release are outside approval.

## Scope and assumptions

- Harness: current dirty `codex/update-session-starter`, HEAD
  `fc65e74fc7c289f71f3a7d081dfe7c1be1238c33`; preserve unrelated work.
- AI: isolated `/Users/patrickroebuck/attune-ai-memory-adoption`, branch
  `codex/shared-memory-adoption`, HEAD
  `fe08f282fb0ad9cbb7eedf75af2597336576578e`; original main untouched.
- Active lead is Codex. Required different-model reviews use bounded advisory
  lanes with central receipts; no separate API/native campaigns are authorized.

## Current state

- Patrick explicitly approved the five-task plan and beginning implementation
  through the form on 2026-09-17, acknowledging optional packaging review.
- Tasks 1–3 are accepted. The final timestamp repair was independently closed
  in one user-directed focused check; the lead reran its differential probe and
  both targeted tests centrally. Task 4 is in progress under the existing auto-run policy.
- Task 2 core is dependency-free and proposal-only. Native participants and new
  legacy-store worker mutations remain unavailable pending qualification.
- Task 3 adds explicit-root raw/personal/curated readers and a strict stash seam
  in the isolated AI worktree. Original memory commands and corpora remain intact.
- Patrick clarified that three review rounds are a checkpoint and wants bounded
  opportunities for progress surfaced proactively; willingness to extend is not
  unlimited automatic review authorization.
- Remote-user usage collection is no longer needed. Preserve useful local
  telemetry. New-route shutdown upload exclusion remains Task 4; product-wide
  sender and hosted-collector retirement are separate scope.
- Canonical workspace: `spec-461d7dcb00604997b9ac1110d4df773b`.
  Embedded plan state is the durable resume authority; preserve current receipts.
  Task 4 started at revision 18. Task 3 accepted at revision 17 after retry revision 16. The consumed gate at
  revision 15 is historical. The acceptance receipt is
  `docs/receipts/shared-memory-adoption-task3/acceptance.json`.
- Verification method is offline service/mutation checks plus different-model
  review. The legacy provider-backed pipeline runner was not run or claimed green.

## Verification

| Claim | Probe | Result |
|---|---|---|
| Isolated AI checkout is a sound baseline | Existing collaboration preflight | 87 passed; original-main warning only; worktree stayed clean |
| Existing formats retain useful content | Actual disposable readers and RAG pipeline in `tests/test_memory_compatibility.py` | 24 passed |
| Negative cases detect removed protections | Four guard/emitter removals in temporary source copies | 4/4 detected; 5/24 cases sensitive |
| Review gaps addressed | Sol/high evidence-chain review and targeted recheck | Four findings closed; no Task 1 blocker |
| Task 2 shared worker | Host routing, attempt binding and negative cases | 63 passed; 5/5 protection removals detected; independent findings closed |
| Task 3 current-service adapter | Real disposable services, scoped snapshots and age-race regression | 162 passed; 6/6 protection removals detected; adapter coverage 90.95%, changed existing seams 100% |
| Prior experiments preserved | Existing worker/journey source and receipt hash verifier | 108 native receipts unchanged |

## Next action

Resolve Task 4’s open review disposition using the latest checkpoint above.
Task 5 has prepared installed evidence but has not started or been accepted
canonically. Live activation and release remain outside approval.

## Overnight continuation — 2026-09-17

Patrick asked to continue while he sleeps. Heartbeat automation
`complete-shared-memory-adoption` is ACTIVE, hourly, attached to this task.
It should remain quiet on unchanged status and pause when work completes or a
required user decision prevents further useful progress. No new routine approval
is needed for Tasks 4–5. Live activation/release/provider campaigns remain outside
approval. Existing auto-run still pauses on unresolved serious findings.

Telemetry: Patrick's final choice was **A**, preserving explicitly configured
team operations while disabling product-usage collection. The earlier B/offline
choice was reopened and superseded; do not enforce a blanket network ban.
`memory_cli.configure_process` suppresses only ATTUNE_USAGE_PING and redirects
structlog to stderr for JSON protocol integrity. Redis coordination and local
memory feedback are explicitly tested; team reuse of usage_ping still requires
purpose/destination separation and is not newly qualified.

Task 4 implementation now exists in Harness memory_context.py, memory_cli.py,
memory_bridge.py plus CLI registration; AI has a lazy memory-worker CLI handler,
parser/early dispatch and optional harness dependency. Actual both CLI subprocess
journeys and the Attune MCP stdio plugin call one worker and persist inspectable
jobs. This worker execution is explicitly **offline response replay**, not active
Luna/native dispatch or a storage mutation engine. Context uses full-source
handles and explicit replace-all refresh; it cannot erase already-loaded model
history. Existing keyed/pattern/other team memory paths remain their original
operations.

Latest central tests: 8 integration checks passed in 8.37s; 100 new/existing AI CLI
checks passed in 0.98s. These include legacy upload opt-in through actual process
exit, a guard-removal positive control, local accounting, team signal emission,
correction/deletion invalidation, full source resolution, durable CLI/MCP jobs and
absence/disabled optional route behavior. Source hashes/progress are saved in
`docs/receipts/shared-memory-adoption-task4/progress.json`.

Historical state (superseded by the failed-attempt receipt below): Sol/high
agent `/root/shared_memory_adoption_review` was running Task 4 review round 1 (evidence-chain + behavioral/suite); it was asked to preserve its receipt
at `/private/tmp/memory-task4-review.json`. Read the result, reproduce findings
centrally, repair within scope, then gather changed-code coverage and targeted
negative receipts before canonical acceptance. Do not assume current tests imply
Task 4 completion. Avoid unlimited review; raise bounded progress opportunities
as Patrick requested.

The preliminary Harness wheel exists at
`/private/tmp/attune-memory-adoption-wheels/attune_harness-0.1.0.dev13-py3-none-any.whl`.
Its metadata was checked before adding the AI optional extra. Rebuild final
artifacts after review; Task 5 must install outside source trees and verify hashes,
consumer paths, rollback and support limits. `python -m build` is unavailable in
the AI venv (namespace package only); `setuptools.build_meta.build_wheel` worked.
No environment or release installation has been activated.

Verification runtime: `/Users/patrickroebuck/attune-ai/.venv/bin/python -B`,
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 ATTUNE_USAGE_PING=0
ATTUNE_VERSION_CHECK=0`, PYTHONPATH Harness/src:isolatedAI/src, pytest
`-o addopts= -o pythonpath= -p no:cacheprovider`. MCP here uses an SDK expecting
`timedelta` for `read_timeout_seconds` (not an integer). No live network is needed.
AI writes require sandbox escalation; original AI checkout is unchanged except
its pre-existing untracked usage-signals snapshot. Do not overwrite old staging
scripts over current sources.

Task 4 review update: the review agent failed to complete after an automated
safety refusal. No findings or approval were returned. Preserve
`docs/receipts/shared-memory-adoption-task4/review-attempt-1.json`; the failed
attempt is not a completed review. Continue unaffected verification within the
existing plan, without bypassing the refusal or silently waiving review.
Task 4 remains unaccepted. Do not assume the earlier running-review status means
a receipt will arrive.

Patrick requested a session reflection. The local portable review form is
`docs/reflections/session-2026-09-17/review.md`, with exact candidate claims and
destinations in sibling `review.json`. At revision 2, he explicitly accepted
items 3, 4, 5, 6, 7 and 9; they are saved with their references in `kept.md`.
Item 3 is also saved as a global feedback memory with its index pointer; the
memory corpus lint passed (0 violations across 132 files). Items 1–2 remain
unreviewed; item 8 is revised to explicitly value experiments as directional
evidence, with exact wording awaiting disposition. Prior spec decisions remain
valid regardless of reflection status.
Patrick separately authorized debugging apparent hover-triggered disappearance.
The investigation is in `docs/research/form-visibility-2026-09-17.md`.
His latest release clarification is decisive: preserve useful features; this is
his portfolio piece. Refine and integrate the organic product using credible
industry/academic evidence and local verification. The assistant's earlier
scope-reduction A/B/C choice is withdrawn. See
`docs/harness-release-readiness-direction.md`; do not silently drop useful
capabilities or interpret this direction as release authorization.
Patrick also directed element-by-element focus with reflection at meaningful
intervals. The global preference is `feedback_spec_element_reflection.md`.
The existing hourly heartbeat now includes this cadence and capability
preservation. Reflect on evidence, failed assumptions and the concrete next-step
adjustment; verify integration as well as each element. Do not introduce routine
approval gates or replace independent review with self-reflection.
Patrick clarified that reflection should use the session's rich context for
shared learning, including deeper understanding without an immediate code
change. Retain important reasoning and corrections. Do not turn each insight
into an ad hoc feature. Extensibility through plugins should preserve a clean,
learnable interface through the shared grammar; see `docs/design-navigation.md`.
User/project/team access separation is a future need, explicitly not immediate.
Questions are parked in the shared-memory design's deferred section. Do not
expand the current ladder or weaken its existing ownership/scope checks.
Patrick explicitly requested logging opportunities during continued work.
Maintain `docs/opportunity-log.md` with evidence, benefit, bounded next step and
priority. Preserve completed historical opportunity reports; do not mix private
user preferences into this project log or turn logged ideas into approval.
The forms connector render was blocked by automatic approval review; local
Markdown was used without sending the content to another connector.

Patrick also asked about form latency. Latest local receipt:
`docs/receipts/unified-task-execution/task2-intake-timing-final/summary.json`:
30 samples/mode; construction/validation medians cold 2.0814585 ms, warm cached
1.8415835 ms, bypass 2.120271 ms. This excludes model/transport/visible paint.
Latest located Codex visible trial: original AI
`docs/probes/host-surface-parity/host-native-trials-2026-09-07.md`, approx 6.5 s
request-to-visible in one trial including assistant dispatch; no distribution.
There is no valid single aggregate dynamic/cached/grammar latency score. The
Sept 16 Forms synthetic event experiment measured an instrumentation boundary,
not user-facing speed. These receipts do not explain today's disappearing forms.
