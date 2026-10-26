# Library qualification

## Platforms

`.github/workflows/qualification.yml` builds and installs the wheel on the
following matrix. Each installed-wheel job runs
`python -I scripts/qualify_platform.py --output qualification` and uploads the
platform identity, installed source hashes, test output and JUnit results.
GitHub documents the [hosted runner labels and images][github-runners].

[github-runners]: https://docs.github.com/en/actions/reference/runners/github-hosted-runners

| Job | Runner | Python | Scope |
| --- | --- | --- | --- |
| `installed-library` | `ubuntu-latest`, `macos-latest` | 3.12 | Selected platform tests and installed-wheel journeys |
| `installed-library` | Windows Server 2022 (`windows-2022`) and 2025 (`windows-2025`) | 3.12 | Selected platform tests and installed-wheel journeys |
| `full-suite` | `ubuntu-latest` | 3.12 | Every test from the source tree |
| `full-suite` | Windows Server 2022 (`windows-2022`) and 2025 (`windows-2025`) | 3.12 | Every test from the source tree |

The development branch requires Python 3.12 or later. This matrix targets its
minimum supported interpreter without duplicate cells. Earlier Python 3.10
receipts retain their historical artifact/runtime identities; they do not qualify
this new minimum. Version 1.5.1 remains unchanged in source, and release/version
selection is separate from this compatibility change.

These hosted jobs provide Windows Server CI evidence. T8 also requires
separate Windows 11 standard-user installed-wheel validation.

The jobs exercise timeout, cancellation, bounded output, descendant termination,
lost acknowledgements, crash-released locks and explicit recovery. Windows uses
Job Objects with a gated bootstrap and native file locks. Its additional cases
cover owner death, failed job assignment, Unicode paths and reparse-point rejection.
The original dev10 Windows receipt records `unsupported`; dev11 is the first native
Windows implementation. Retain both versions' evidence when comparing support.
Model providers are not called by CI. These tests qualify the runner/platform and
adapter fixtures; native model behavior requires the separate frozen campaign.

The full-suite matrix runs plain `pytest` to catch tests outside the
installed-wheel selection. The required `Qualification` check passes only when
correctness lint, installed-wheel jobs, full-suite jobs and documentation links
pass. A documentation-only pull request can skip the platform matrix; lint and
links must still pass. A failed, cancelled, skipped or missing lint result fails
the aggregate check.

## Correctness lint

The `Correctness lint` job runs Ruff 0.14.4 on Ubuntu with Python 3.12. It checks
only `src/` and `scripts/` with the `E9`, `F63`, `F7` and `F82` rule families,
covering syntax and selected correctness errors such as undefined names,
invalid control flow and assertions that always pass. Ruff targets Python 3.12
syntax, matching the package's `>=3.12` requirement. It applies no automatic fixes
and adds no formatting or coverage gate.

Run the same check with the pinned Ruff version in a separate environment:

```sh
ruff check --no-cache --no-fix src scripts
```

Lint does not exercise runtime behavior, qualify a platform or measure model
quality. Source-suite, installed-wheel, native-memory and platform checks retain
their separate requirements.

## Source-suite and installed evidence

Each Windows full-source cell runs two concurrent supervised pytest partitions
through `scripts/run_source_suite.py --shards 2`. Module-path hashing keeps each
module's fixtures and test order together. Both processes collect the complete
suite; the driver checks matching collections, disjoint complete selections,
case start/end journals and successful process exits before reporting success.
Each child retains the 2,700-second deadline. A timeout or missing evidence fails
the whole cell even if pytest printed success. The `full-suite-*` artifact keeps
an aggregate `source-suite.json` plus each child's output, JUnit, collection and
timing records under `shard-0/` and `shard-1/`. Ubuntu and serial driver callers
keep their existing behavior. See the [design and baseline evidence](design-windows-source-suite-shards.md).

Each child has a distinct canonical temporary root outside the checkout, with
its own pytest base directory. Standard temporary-directory variables and
nested pytest use that root. The receipts record these runner-local paths for
failure inspection. Separate namespaces prevent peer cleanup and temporary-file
churn from interfering with native directory-stability checks.
The parent keeps the system temporary base to preserve native filesystem and
permission behavior. Each child receives its own `RUNNER_TEMP` so nested drivers
also stay within that namespace; the hosted runner scratch base is not substituted
for the system temporary base.

### Windows instrumented installed coverage

Supplemental Windows coverage uses two supervised whole-module partitions of
the installed-wheel selection. The measurement script enables this mode
explicitly; ordinary installed qualification, POSIX coverage and the source
runner keep their existing modes. The workflow, dependencies, exclusions and
operation limits remain unchanged.

Both pytest children collect the same selection after the existing `-k` filter.
Module-path hashing assigns each admitted case to one child while preserving
module order. The aggregate requires matching admitted lists, disjoint complete
subsets, exact-once case start/end journals and successful terminal/JUnit
accounting, including skips and subtests. It derives counts from the admitted
cases rather than a fixed historical total.

Each child runs outside the checkout with a separate temporary root, pytest base
directory and retained stdout/stderr files. Each verifies its actual imported
noneditable wheel, RECORD, source hashes and measured inputs before and after
the suite. A parent's import check cannot substitute for either child witness.
Windows Job Objects own the process trees. A failed launch, unknown ownership,
nonzero exit, incomplete evidence or expired deadline fails the aggregate;
later zero exits cannot clear that failure.

The parent starts one 2,520-second monotonic deadline before dispatch. Both
collections, execution and active aggregate verification share the remaining
time. The 2,700-second platform wrapper and 50-minute hosted job remain
unchanged. Parent dispatch/deadline clocks and each pytest journal epoch are
retained separately; journal positions do not establish remaining parent time.
The active supervisor and measurement readback share one finite parent/worker
clock contract: ordered dispatches, matching remaining time, and reaps before a
successful finish inside the deadline. Failed cleanup can retain later timestamps
without clearing the failure. Bootstrap and pytest PIDs identify separate roles.
Native/Redis/R2 postchecks stay in the parent and run once after successful
aggregation. The plugin-probe receipt is copied once from its admitted owning
module's partition; missing or duplicate probe evidence fails aggregation.

The `coverage-windows-latest` artifact retains `installed-suite.json`,
`partition-context.json` and both `shard-*` diagnostic trees under
`instrumented-platform/`. Failed or drifted aggregates cannot produce a
successful coverage receipt. Earlier serial coverage artifacts remain
historical evidence. Instrumented checks do not qualify native platform behavior,
model quality or host acceptance; those requirements keep their separate gates.

Each platform job also runs the R2 clean-environment journey from the installed
wheel, through `scripts/check_installed.py`: plan, accept, build, review and
status with `attune` absent and no model called. The platform receipt's
`r2_journey` records each step's outcome; on Windows the build's refusal, if it
refuses, is recorded in the platform's own words rather than skipped. The
sequence is in [the R2 journey](journeys/r2-clean-environment.md).

The installed-wheel selection also includes Voyage budget/replay checks,
evaluator CLI status checks, plugin lifecycle tests and host qualification
boundary fixtures. `tests/test_code_rag_host_check.py` compiles the actual host
check script with optimization levels 0 and 1 and supplies invalid result,
usage and session evidence. Explicit runtime checks must reject it in both modes;
`python -O` and `PYTHONOPTIMIZE=1` must not remove qualification checks. The
boundary fixtures run with Harness's MCP dependency alone. The five real Attune
dispatcher cases in `tests/test_code_rag.py` were removed with the module they
tested; they skipped whenever Attune AI was absent, so CI never ran them.

`scripts/check_code_rag_host.py` is a historical caller through Attune AI's
dispatcher: it launches `attune_harness.attune_bridge`, removed after 0.2.0
(D8 in the [spec authority addendum](specs/spec-authority/addendum-2026-09-21.md)).
It cannot complete a current host check. Its selected test checks mocked
failure-boundary evidence; it is not a real host qualification receipt. The
script and test remain as historical artifacts. Any replacement host check
needs its own scope and evidence; the current MCP profile tests qualify their
declared paths separately.

The signed Python plugin qualification on unreleased main covers signatures,
revocation, effective grants, cooperating import closure, bounded subprocesses
and host-owned journals in the installed-wheel matrix above. The Voyage live
comparison used one fixed public-corpus
query and eight stages total across two paths (four matching request/result
pairs), with identical normalized SDK and signed
plugin requests/results and five ranked sources. CI replays normalized recorded
responses and a synthetic interruption offline across the installed-wheel
matrix. These receipts
do not qualify arbitrary plugins, hostile same-user code as an OS sandbox,
general ranking quality, raw HTTP capture or live provider calls on each OS.
See [the recorded fixture](../tests/fixtures/voyage-live-recorded/README.md),
[reviewed PR #161](https://github.com/Smart-AI-Memory/attune-harness/pull/161)
and [historical six-platform installed-wheel run](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/36340878620).

The [September 16 fix receipt](sol-review-fix-receipt.md) distinguishes local
source regression results from historical installed-host evidence.

## Accuracy and worker qualification

The model campaign is frozen on dev10, separately from the dev11 platform work.
Use the preserved dev10 environment with the review extra. On a fresh clone,
commit `c2fa34038483ec7a028a50f554bf1a95e54039a5` contains that version; build and
install it in an isolated environment before invoking the campaign. This is
historical campaign guidance; do not overwrite its frozen dev10 environment to
run a comparison.

```sh
python -I experiments/opportunities/campaign.py prepare --out /absolute/new-run
# Inspect the frozen cases, protocol and inputs before external execution.
python -I experiments/opportunities/campaign.py execute --out /absolute/new-run
python -I experiments/opportunities/campaign.py score --out /absolute/new-run
```

Execution is explicit: it invokes the signed-in Codex CLI and the pinned local
Ollama model, up to 64 native calls and six local calls. It never downloads a model,
switches authentication, invokes an API fallback or repeats an existing campaign.
Retain an interrupted run; a `dispatching` record may represent a consumed call.

The eight review cases cover clean text, critical contradictions, missing evidence
and explicit uncertainty. Direct Astra, two Astra roles and a Sol/Astra team receive
identical projected evidence. All arms select xhigh and a 1000-token skills catalog
budget; context comparison uses two extra fresh Astra calls with/without that budget.
Skills, user/project instructions and runtime controls stay enabled. The budget
affects catalog description space, not the complete model context or access policy.

A fresh Sol invocation audits the key before seeing candidate outputs. Separate
per-case Sol calls grade anonymous outputs; the implementation author then audits
the judgments. Same-family model errors remain possible, and this is not independent
human grading. In the September 15 run, the author graded anonymous outputs before
reading Sol's grades and the role mapping; disagreements remain explicit in the
[results](opportunities-implementation-report.md). Eight synthetic cases with one repetition are screening evidence,
not a reliable estimate of production error rate. Do not promote a team or cheaper
model because of green software tests alone.

Six log cases separately evaluate Sol and pinned Llama diagnosis. Three small JSON
configuration repairs are checked by exact host comparisons against a frozen key;
Sol gets one attempt, then Astra only after a rejected repair. These narrow tasks
do not qualify arbitrary documentation rewriting or test-code repair.

Historical campaigns and installed environments remain preserved locally under
`docs/receipts/`; they are intentionally excluded from the Git repository. Some
historical experiment tests require those local artifacts. CI selects portable and
native contract tests that do not depend on unpublished receipts.

Configuration behavior: [official Codex reference](https://learn.chatgpt.com/docs/config-file/config-reference).
CI structure: [GitHub matrix documentation](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/run-job-variations).
