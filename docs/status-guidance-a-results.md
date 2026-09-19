# Opportunity A — verified plan/build guidance

September 18, 2026. **A is complete in the current Harness source. B remains
pending.** This changes CLI presentation only. No native calls, active plugin
upgrade, publication or changes to original experiment grades were performed.
Plan/build Tasks 1–7 remain accepted; native Task 8 remains open.

**Later September 18 follow-through:** Patrick subsequently authorized B, which
is now [implemented and verified separately](durable-decisions-b-results.md).
The A results and historical scope below remain the original closeout receipt.

## Result

[work_cli.py](../src/attune_harness/work_cli.py) now reports a concise summary,
whether progression is blocked, a valid next action, optional advice and pointers
to complete saved evidence. Stale drafts no longer suggest ordinary acceptance;
stale proposals, accepted work and completed builds also get inspection/correction
guidance. Uncertain execution takes priority over stale or resumable guidance.
Failed required checks stay blocking; optional checks and participant notes remain
separate. Completed planning is explicitly a draft proposal. Completed build copy
distinguishes protected checks from reviewer judgments and broader semantic claims.

Two compatibility cases have explicit next actions:

1. **Incomplete draft:** supply the missing required runner or planner, revise
   the draft, then request acceptance for its new checkpoint.
2. **Paused file-effect batch:** inspect the saved journal, then continue through
   its owning `apply_work_effects` API with the current checkpoint and unchanged
   proposal. Dependent `build`/`resume` commands cannot take over that journal.

Rejected saved replies are identified even at a pause before decoding: a durable
reply is not necessarily a valid proposal, and resume will not replace it.
Full findings/replies remain in the owner rather than being truncated to fit a
summary. Errors before a saved build retain their type/detail and exit code, with
a record reference when the owner can be inspected.

Existing authority, dispatch, recovery, persistence and exit-code policies are
unchanged. Readable `status` still exits 0, including blocked/stale states; the
added `blocking` field is presentation, not authorization. Freshness inspection
now identifies stale accepted/build evidence instead of displaying it as current.
See the [guidance field definitions](user-guidance-examples.md#implemented-in-source-planbuild-status-guidance-a).

## Verification

| Check | Actual result |
|---|---|
| Existing CLI baseline before production changes | 25 passed. Disposable probes reproduced stale acceptance advice, unavailable required runner with zero worker calls/no saved build, and optional advice on a completed build. |
| New guidance regressions | **29 passed.** Real local commands/files, actual Spec acceptance, validated saved journals and injected lost acknowledgments. |
| Work/runtime and adjacent compatibility suite | **476 passed**, one existing optional-runtime `ModelTier` deprecation warning, 71.13 seconds. Includes CLI cross-process journeys, authority/controls, file effects, planning, build, repair/resume, invalid replies, connected journeys and default compatibility. |
| Baseline sensitivity | **29/29 new cases fail** against an isolated copy of the original presentation. The original stale-advice defect is separately demonstrated by the raw probe. |
| Freshness guard mutation | **5/29 new cases fail** when only the stale-guidance precedence branch is removed in an isolated copy; the other 24 pass. The five failures cover draft, proposal, accepted, paused and completed work. |
| Static checks | Ruff lint and format checks pass for the changed production file and new tests. |
| Read-only status | Tests inspect twice, compare project/owner bytes and modification times (excluding Git internals), and forbid participant dispatch, check execution, file effects and saves. Evidence pointers are resolved against the complete saved record. |

The suite imported current Harness source, not the retained installed Harness.
Runtime: Python 3.12.13 at
`/private/tmp/attune-fresh-resolution-y74ui3g8/integrated/bin/python`;
the previously qualified Spec dependency came from
`/private/tmp/task7-installed-spec-n2emxesr/installed`.
Usage/version pings and tracking were disabled. No packages were upgraded.

Reproduce from the repository root while those retained dependencies exist:

```sh
ATTUNE_USAGE_PING=0 ATTUNE_VERSION_CHECK=0 DO_NOT_TRACK=1 \
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$PWD/src:/private/tmp/task7-installed-spec-n2emxesr/installed" \
/private/tmp/attune-fresh-resolution-y74ui3g8/integrated/bin/python -B -m pytest -q \
  tests/test_work_*.py tests/test_connected_journey.py \
  tests/test_task_compatibility.py tests/test_plan_build_default_compatibility.py

ruff check src/attune_harness/work_cli.py tests/test_work_guidance.py
ruff format --check src/attune_harness/work_cli.py tests/test_work_guidance.py
```

Local receipts: [final suite](receipts/status-guidance-a/verified-suite.txt),
[baseline probes](receipts/status-guidance-a/baseline.json),
[baseline sensitivity](receipts/status-guidance-a/baseline-suite.txt),
[guard mutation](receipts/status-guidance-a/mutation-suite.txt),
[runtime origins](receipts/status-guidance-a/runtime.json),
[source hashes](receipts/status-guidance-a/source-hashes.json) and
[presentation diff against the starting file](receipts/status-guidance-a/presentation.diff).
JUnit XML accompanies the three suite logs. Receipt files are local ignored
artifacts, matching the repository's existing convention.

## Limits and reflection

This qualifies local CLI guidance, not a new native model journey, installed
plugin rollout, human UX study or broader warning UI. Recovery remains bounded:
ordinary build rebasing and blind retries of uncertain calls/checks are not
available. Existing unsupported conditions remain blocked rather than acquiring
new bypasses. B and C–F, October release work and all paid trials remain outside
this task.

The useful finding was that run status alone is insufficient for next-action
copy. A completed planning run is still a proposal; a paused build may already
hold a rejected reply; a completed file batch is not a verified dependent build.
The adjustment was to read the existing validated evidence and use its existing
decoders/preflight rules, without adding another persisted state model. The
[pre-edit design note](design-status-guidance-a.md) records the original probes
and rejected alternatives. Existing modified/untracked work was retained; no
commit, reset, stash or publication was performed.
