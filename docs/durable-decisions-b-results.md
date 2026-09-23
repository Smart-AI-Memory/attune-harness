# Opportunity B — durable decision text verified

September 18, 2026. **A and B are complete in the current checkout's CLI/Spec
source.** A's files matched its original 476-test receipt before B began, and
the combined verification now passes 492 tests. The active installed plugin was
not upgraded. No native/provider calls, publication, C–F or release work ran.

## Result

- `WorkAcceptance.open()` (then `WorkSpecBridge.open()`) retains the exact existing renderer's Markdown,
  choices, consequences and bound response template **before returning the form
  for collection**. A delayed response must match that retained current display
  and still pass the original Spec collector's checks.
- `plan --decision` explicitly prepares and retains questions or a complete
  draft's approval view. It does not accept work, dispatch a participant or change
  the task checkpoint. Plan mutations that display missing questions retain
  those questions as well.
- The latest display lives in `decision.json` beside the authoritative work
  record. Read-only `status` exposes its text and path as current, collected,
  historical or unavailable. Old work without the artifact remains readable.
- Partial planning answers refresh the checkpoint and retain remaining questions.
  Stale answer files cannot be applied to the new field mapping. Replaced Spec
  displays, changed work/source/config and consumed replies cannot be silently
  rebound to current work. High-risk confirmation and required controls remain.
- Known collector results are retained without treating them as proof of saved
  work acceptance. Persistence failures stop the grant; the work record remains
  authoritative. Status never recreates a form or revives expired host authority.

Production changes are confined to
[work_decisions.py](../src/attune_harness/work_decisions.py),
[spec_legacy.py](../src/attune_harness/spec_legacy.py) (then `spec_bridge.py`) and
[work_cli.py](../src/attune_harness/work_cli.py). Work request/record schemas,
checkpoint calculation, planning answer validation and build execution were not
changed. [Design note](design-durable-decisions-b.md);
[user-facing usage and state definitions](user-guidance-examples.md#implemented-in-source-durable-decision-text-b).

## Verification

| Check | Actual result |
|---|---|
| Pre-edit actual-Spec probe | Opening rendered a complete bound decision but saved no artifact. A delayed same-host response was accepted and its duplicate rejected. The work checkpoint stayed unchanged. |
| New B regressions | **16 passed.** Actual local Spec collection, retained text with the render object discarded, a separate-process status read, partial planning answers, replaced/stale replies, explicit confirmation, non-grant acknowledgment, write failures, corrupt/symlink/foreign displays and CLI compatibility. |
| Combined work/runtime and adjacent compatibility suite | **492 passed**, zero skipped/errors/failures, 70.38 seconds. Includes all 29 A regressions and work authority, controls, effects, build, planning, response contracts, repair/resume, connected journeys and default compatibility. |
| Guard-removal check | **1/16 new tests fails** with the current-display response-binding check removed in an isolated source copy; 15 pass. The failing case demonstrates actual acceptance of a replaced reply in the same host, not a message-only difference. |
| Read-only status | Repeated status checks preserve owner/artifact bytes and modification times, with saves, artifact writes and Spec-host creation forbidden. |
| Static and documentation checks | Ruff lint/format pass on the three changed production files and new tests; local documentation links and receipt hashes checked. |

Both passing suites reported the existing optional-runtime `ModelTier`
deprecation warning. The final 16-case rerun followed removal of a brittle
error-message assertion from the restart test; it now checks rejection and
unchanged authority regardless of which existing guard rejects the expired
workspace. The mutation receipt counts the remaining behavioral failure only.

The tests used current Harness source with the retained Python 3.12.13 runtime:
`/private/tmp/attune-fresh-resolution-y74ui3g8/integrated/bin/python`.
The previously qualified optional Spec dependency came from
`/private/tmp/task7-installed-spec-n2emxesr/installed`. No dependencies were
upgraded; usage/version pings and tracking were disabled.

```sh
ATTUNE_USAGE_PING=0 ATTUNE_VERSION_CHECK=0 DO_NOT_TRACK=1 \
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$PWD/src:/private/tmp/task7-installed-spec-n2emxesr/installed" \
/private/tmp/attune-fresh-resolution-y74ui3g8/integrated/bin/python -B -m pytest -q \
  tests/test_work_*.py tests/test_connected_journey.py \
  tests/test_task_compatibility.py tests/test_plan_build_default_compatibility.py

ruff check src/attune_harness/work_decisions.py src/attune_harness/spec_bridge.py \
  src/attune_harness/work_cli.py tests/test_work_decisions.py
ruff format --check src/attune_harness/work_decisions.py src/attune_harness/spec_bridge.py \
  src/attune_harness/work_cli.py tests/test_work_decisions.py
```

Local receipts: [baseline probe](receipts/durable-decisions-b/baseline.json),
[combined suite](receipts/durable-decisions-b/verified-suite.txt),
[final new-test suite](receipts/durable-decisions-b/decisions-suite.txt),
[guard mutation](receipts/durable-decisions-b/mutation-suite.txt),
[runtime](receipts/durable-decisions-b/runtime.json),
[final source hashes](receipts/durable-decisions-b/source-hashes.json) and
[diff against the start of B](receipts/durable-decisions-b/implementation.diff).
JUnit XML accompanies the suite logs. These are local ignored receipt files,
following the repository's existing convention.

## Boundaries and reflection

This retains the **latest** display, not an archive of every form. Its state
describes saved text, not whether a native panel is currently visible. A host
restart preserves text but not its in-memory action authority; reopen before
responding. The atomic JSON artifact was tested across process restart; this is
not a storage power-loss qualification or a native UI lifetime experiment.

The original disappearing-form incident remains unreproduced. No native form
timer, selectable input preference, automatic host UI integration or general
natural-language action router was added. Existing planning answer JSON and
the actual Spec collector remain the response paths. Native Task 8 remains open.

The important integration finding was that retaining a reply template is not
enough: the same host can still hold an earlier workspace after a replacement
view opens. Comparing the response with the retained current display prevents
that older workspace from silently becoming the chosen decision. Removing that
comparison causes the new behavioral regression to fail.

Patrick authorized a worktree or commit if needed. This implementation stayed in
the saved checkout because it depends on existing uncommitted plan/build work.
No worktree, commit, reset, stash or publication was needed. Existing work and
original experiment receipts/grades were preserved; A and B have focused local
diffs and verification receipts for review.
