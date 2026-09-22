# Spec test handoff: local correction qualified

2026-09-17. Patrick's option A authorized the bounded repair following the
[memory documentation journey](memory-documentation-journey.md). The previously
rendered Spec form now rejects acceptance when its bound Harness test evidence
changes or disappears. Fresh acceptance and historical resume continue to work.
This is software qualification; native semantic judgment and Patrick's actual
Spec acceptance remain pending.

## Implementation and boundary

Harness now owns `bind_test_evidence()` and `check_test_evidence()` in
`src/attune_harness/spec_handoff.py`. The existing task owner validates the
completed journal, request, checkpoint, source/test/config snapshot, producing
repair and output artifacts. A typed reference binds that evidence to the existing
Spec task receipt. The current AI Spec adapter validates it at publication and
immediately before completion, including approval, auto-run and risk acknowledgment.
Every nonpassing outcome requires the existing high-severity gate; stale evidence
cannot be acknowledged into completion. Redo/fix recovery remains available.

The trusted executor supplies `test_evidence=bind_test_evidence(test_directory)`
and includes its `record_path` in the displayed `probes` when publishing a
`task_result`. The memory and connected-journey executors now do this. The binding
participates in the form contract and is persisted with accepted receipts through
the existing SpecState store. Old accepted receipts remain readable without a
live Harness dependency or treating past approval as a new decision.

Legacy unbound generic receipts still work; a probe string alone does not acquire
this freshness guarantee. The executor handoff remains explicit. This change adds
no scheduler, gate store, automatic plan/build implementation or memory mutation.
Checks cover cooperating owners and do not lock an adversarial filesystem through
the later persistence transaction.

Qualification exposed a second real defect: Git diff could refresh `.git/index`
during inspection and make producing repair evidence stale. The capture wrapper
now disables optional index writes. Freshness excludes only the derived
`changed_paths` hint, which can retain stat-only differences after identical bytes
are restored. Full file inventory, content, size, mode, HEAD, staged entries, root
identity and producer checks remain bound. Index preservation and actual content
changes have explicit negative tests.

## Evidence

| Check | Result |
| --- | --- |
| Source Harness handoff, memory journey, connected journey and testing suites | **97 passed**, no skips or expected failures |
| Source AI Spec workspace and state | **80 passed** |
| Isolated installed Harness handoff and both journeys | **59 passed** |
| Isolated installed AI Spec workspace and state | **80 passed** |
| Different-model review | Sol found no remaining actionable issue; independently ran all 25 handoff checks |
| Collaboration preflight, centrally repeated | **87 passed**, no failures; existing dirty-checkout warnings retained |
| Changed executable-line coverage | Harness helper **31/32 (96.875%)**; Spec changes **31/32 (96.875%)**; capture correction **2/2 (100%)** |
| Completion-guard removal in a disposable installed copy | **13 tests detected the defect**, 12 positive/other controls still passed; unmodified control **25/25 passed** |
| Index-protection removal in a disposable installed copy | Its regression failed on changed index bytes |
| Formatting and lint | Black and Ruff passed on changed Harness code/tests; AI owning file also passed |
| Preservation | **153** original journey receipts, **713** prior comparison receipts and **7** frozen experiment files verified unchanged |

The installed rehearsal executes the actual adapter through three pytest tests,
repairs only `guide.md`, preserves the correct control and unrelated dirty work,
persists the fresh synthetic Spec receipt, rejects replay and rejects the old form
after a captured source change. Its six participant responses are scripted; all
collector submissions are explicitly synthetic. No additional paid/native trial
was dispatched. The advisory code review is separate from that trial allocation.

One installed run measured **0.0044 s** from preparation start to the actual adapter
finding, **0.255 s** from assessment invocation to the first durable scripted
finding, **3.228 s** to the first Spec gate and **3.408 s** total. These are local
rehearsal timings, not model reasoning, desktop display or user waiting-time data.

## Runtime, receipts and limits

Both candidate wheels were built offline from current source copies and installed
with `--no-index --no-deps` into a fresh temporary target. The existing qualified
Python 3.12 dependency environment supplied dependencies. This checks the new
packages together; it does not repeat fresh dependency resolution or qualify
other platforms. Existing plugin/active installations remain unchanged. No live
memory stores were opened. The original adapter and SpecState source are unchanged.

- [Installed result](receipts/spec-test-handoff-2026-09-17/installed-rehearsal/result.json)
- [Durable synthetic Spec form](receipts/spec-test-handoff-2026-09-17/installed-rehearsal/work/spec-fresh/gate.md)
- [Suite results](receipts/spec-test-handoff-2026-09-17/suite-summary.json), [coverage](receipts/spec-test-handoff-2026-09-17/changed-coverage.json) and [mutation commands](receipts/spec-test-handoff-2026-09-17/mutation-commands.json)
- [Independent review](receipts/spec-test-handoff-2026-09-17/independent-review.md)
- [Wheel identities](receipts/spec-test-handoff-2026-09-17/build-install.json), [installed module origins](receipts/spec-test-handoff-2026-09-17/installed-origins.json) and [preservation](receipts/spec-test-handoff-2026-09-17/preservation.json)
- [Design](design-spec-test-handoff.md) and [original stale-approval counterexample](receipts/memory-documentation-journey-2026-09-17/example-backed-prepared/work/spec-stale/stale-decision-counterexample.json)

Failed development runs are retained and labeled in the receipt index. An existing
workflow deprecation warning remains. The source AI test hook attempted to append
its optional local test-tracking file outside the writable sandbox and reported a
permission warning; the 80 Spec tests completed successfully. This is separate
from acceptance-state persistence, which is exercised in temporary roots.

The next native sample remains the previously proposed six-call allocation. It
requires a frozen controller, current evidence packet and explicit spend approval;
no previous paid allocation is implicitly renewed. Broader live memory, team,
plan/build and release qualifications remain in their existing owning tasks.
Patrick's Harness publication/AI deprecation leaning is recorded in the
[release direction](harness-release-readiness-direction.md), without declaring
either product transition completed or approved for release.
