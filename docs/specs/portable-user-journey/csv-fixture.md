# Offline CSV workflow fixture

## Scope and authorization

Patrick authorized the executable CSV fixture after the performance-plan update,
with no live or paid trials. This implements the fixture prerequisite only, not
T2–T5, human collection, new host adapters or a model-quality benchmark. The
existing [performance protocol](performance-evaluation.md) and design R1/R3/R7
remain the requirements. The implementation stays in examples and tests; it
does not change the shipped Harness APIs or retained campaign evidence.

## Design before implementation

Prepare a new disposable Git checkout, outside its saved task directory, with
synthetic report rows, an unfinished exporter and protected literal test cases.
Use the actual Harness work owner and frozen effects manifest. Keep one material
page/all-records question unresolved in the correction and simple variants; the
fully specified variant has none. Persist answers and corrections with the
current checkpoint, revising intent, criteria, tasks and verification together.

An explicit offline smoke command uses a fixed known-good proposal through the
real build owner. Its acceptance is labeled synthetic, never a participant's
decision; its receipt identifies software-fixture evidence and leaves human/AI
performance and token usage unmeasured. A preparation-only command accepts and
dispatches nothing. Neither command accepts a model or provider configuration.

Protected checks compare parsed CSV against literal expected row identities and
values, not against another invocation of the candidate's filtering logic.
Cover page selection after filtering, ordering, no private columns/values,
commas, quotes, multiline Unicode, alternate filters, partial and empty pages,
and empty results. Seed failures for stale all-records scope, ignored filters,
private data, ordering, malformed quoting, wrong headers and missing output.
Negative owner tests cover unresolved acceptance, stale correction/acceptance,
unaccepted execution and protected-file tampering.

Existing evidence inspected before implementation: `test_work_build.py` uses
scripted proposals with actual host file effects and protected subprocess
checks; `scripts/check_installed.py` constructs the required frozen manifest.
No new CSV experiment has run at this design checkpoint. Rejected alternative:
testing only a standalone CSV function would omit correction and authority;
running a live model would exceed this task's explicit boundary.

## Completion criteria

- Preparation refuses existing/noncanonical destinations and creates an
  unaccepted draft in a new, bounded, synthetic checkout.
- A documented offline command executes the real correction/acceptance/build
  lifecycle with no provider/native/command participant calls.
- Passing and seeded failing exporters exercise protected checks, with failures
  retained as failures and no retries or edits to make them pass.
- Tests verify history, current scope, stale refusal, protected data and receipts.
- Receipts identify their evidence type and hash retained files; no claims about
  human effort, model effectiveness, comparative advantage or zero-token trials.
- Targeted and broader verification results and remaining limits are recorded.
- Completion review: complete for this offline fixture; see the finding below.

## Run and inspect

Use the [example instructions](../../../examples/csv-evaluation/README.md) for
preparation-only and offline smoke commands. The fixture's correction seam is
explicitly scripted; it does not establish chat/form equivalence or a live host
collector. No shipped API, compatibility declaration or platform qualification
changes as a result of this fixture.

## Verification and evidence limits

The 25 targeted fixture tests pass from source and against the locally installed
candidate wheel. All 10 seeded exporter defects are detected. A standalone
installed-wheel smoke run completes the three-revision correction case with two
passing protected probes, each checking six CSV cases. The receipt explicitly
records synthetic acceptance, no model calls and unmeasured human/AI/token metrics.
The candidate wheel is a local build, not a published release.

The oracle is independent of candidate filtering code and protected from worker
edits, but its cases are visible to the build participant. Passing these fixed
checks does not establish generalization to held-out tasks. The next collection
step must address that limitation alongside real people, matched variants,
instrumentation and qualified host/model integration. No collection is authorized.

Installed-platform verification on macOS completed with 3,195 passed, 182 skipped,
one failed and 19 setup errors. The disposable environment inherited Anthropic
SDK 0.71.0 instead of the native-memory owner's required 1.6.0; the setup errors
reproduce before test execution. The plugin-bootstrap failure reports that
`tiktoken` is absent from the isolated bootstrap's admitted local site directory,
although it is inherited from the global environment. Post-suite installed/native
checks did not run. This is not platform qualification; Windows was not observed.
No production source or environment pins were changed to conceal these failures.
The separate full-suite attempt encountered the same SDK/plugin failures and was
intentionally interrupted after progress reached 79%. Pytest then raised a
temporary-fixture teardown error; no completed full-suite result is claimed.
Before merge, use a clean environment with the repository's pinned dependencies
and review successful CI evidence. Do not treat targeted fixture success as a
substitute for that broader gate.

## Completion review

### Early-exit correction: October 29, 2026

Review of PR #321 found that `SystemExit(0)` during candidate import or export
could terminate the oracle before it emitted results. The process exit code
then caused a passing probe and completed receipt without any verified CSV.
The correction handles `SystemExit` at both candidate boundaries. Import exits
produce a failed verdict; export-call exits produce failed case results. Both
return a nonzero oracle exit code. Interrupt handling and the general Harness
runner remain unchanged; this is not a sandbox for hostile candidate code.

Six regression cases cover import and call exits with codes `0`, `None` and `7`
through the real build owner. They check the saved failed receipt, non-completed
build, failed probe, structured error and absence of final verification. All six
failed against the original oracle; all 31 fixture tests pass after the fix,
including the existing known-good smoke cases. The same 31 tests pass through
the Harness **`test`** workflow. These are offline software checks, not live or
paid trials. Broader qualification remains a separate gate.

The contract and user lenses refine J4: failed candidate execution must remain
visible as failed evidence before human or AI performance can be evaluated.
This closes the reproduced `SystemExit` gap, not the documented live-collection,
host-integration or hostile-code limitations. No duplicate opportunity entry is
needed. The first user-visible improvement is a failed receipt instead of false
completion when the candidate exits early. This correction authorizes no trials.

### Original fixture review

The goal remains better human–AI work, with costs evaluated after performance.
The user lens now has an executable correction and artifact check; R3's contract
lens has stale-decision and obsolete-acceptance tests. The next-step lens sharpens
existing J4: a protected, visible oracle establishes workflow behavior, not
held-out performance or human comprehension. Its follow-up stays in the existing
performance protocol rather than a duplicate opportunity-log item. The first
user-visible question remains whether a real person's correction survives the
display, saved scope and final artifact. This fixture verifies only the scripted
owner/artifact portion. Live collection remains unauthorized.
