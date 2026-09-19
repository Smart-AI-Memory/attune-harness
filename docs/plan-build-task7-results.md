# Plan/build Task 7 — installed verbs

Tasks 1–7 are accepted. The actual Spec workspace automatically accepted Task 7
at revision 24 under Patrick’s existing non-high continuation choice. Task 7 adds `plan` and `build` to the compact command
catalog and connects status/resume/file reconciliation to the same current work
record. No existing route was removed. Explicit approval uses the actual Spec
collector; external/native dispatch retains separate authorization.

The installed console-script journey ran seven separate invocations outside both
repositories: create, propose, stage, accept, build/pause, status and resume. The
same work identity survived every process. Its scripted planner and build peers
made four command calls; protected checks passed and unrelated dirty work remained
unchanged. The initial intake returned in 128 ms and the planning command in 169 ms
in this single local fixture. These figures exclude native inference and desktop
presentation; they do not measure the user's experienced form latency.

Both Harness and the optional Spec owner were built as isolated wheels for the
complete installed journey. Their module hashes match the selected sources. The
active environment/MCP host was not changed. Help and base imports work under
Python isolation with optional packages unavailable, without invoking a model.

## Evidence

- **909 distinct source checks are now passing**: the broad run passed 908
  and exposed one transport-fixture failure; the repaired combined 45-check run
  passes, including that failure. No skips or xfails.
- **908 distinct installed Harness checks are now passing**: 907 passed in the
  broad run; the final 105-check run passes with both Harness and Spec installed
  as isolated wheels, including the repaired transport test. Earlier passing
  checks and the original failure remain separately retained.
- All three CLI guard removals are detected: stale explicit approval checkpoint,
  conflicting creation options and misuse of completed-work preservation.
- New command policy has 91.28% statement coverage; changed existing command
  modules have 87.5–100% changed-line coverage.
- Installed command transcripts, the durable Spec form, work record and result
  are retained under `docs/receipts/plan-build-task7-2026-09-18/`.

The first scripted planner reply claimed every task covered a criterion that only
one task actually checked. The existing contract rejected that assertion. The
fixture now names only tasks retaining the exact check; enforcement is unchanged.

The broader regression run also exposed an existing MCP test's dependency on
import order: the SDK's default stderr could retain a pytest capture stream with
no file descriptor. Disabling global capture alone was insufficient when an
earlier test used its own capture fixture. The transport test now owns an explicit
real log stream. This changes the test fixture, not memory behavior or product
telemetry. Original failed runs and the isolated successful transport check remain
available alongside the final combined tests.

## Supported boundary

Request JSON, bound answers, proposal staging, explicit checkpoint approval,
legacy import/reimport and pending-step correction are supported. Build remains
a bounded ordered POSIX chain with protected fixed checks. Status does not resume
work, and stale drafts remain inspectable. Native calls require separate explicit
permission; this task made none. Feature transfer/cancel and broader post-effect
goal rebasing remain visibly unsupported; no older feature was subtracted.

No independent model review, provider-backed quality pipeline, paid/native trial,
active installation, live memory change or release ran. Next is Task 8's offline
comparison preparation and separate native allocation decision.
