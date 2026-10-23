# Supplemental coverage measurement

Coverage is a testing guide, with 90% overall line coverage as a goal and branch
coverage reported separately. It does not replace the uninstrumented qualification
workflow, qualify model quality, or make every module's 90% a release requirement.

## Design and experiment

### Receipt input binding repair

The receipt records SHA-256 for every tracked file in the checkout, plus
untracked files under test, script, example, experiment, documentation, plugin,
skill and workflow trees and recognized root pytest configuration files.
This covers collected tests, fixture bytes, the measurement collector, the
platform qualification driver and subprocess examples. Symlinks in those input
trees and tracked files are refused. The input map and installed package hashes
are captured before execution and compared after the child exits; a changed or
unreadable input marks the receipt incompatible,
even when pytest exits successfully. Combining requires this input map and an
explicit no-drift marker, so older manifests remain readable but cannot be
combined as equivalent evidence. Generated Python caches are excluded because
they are interpreter outputs rather than executed inputs. The pre/post checks
do not detect a transient edit restored during execution; the receipt binds
the observed input bytes, not complete execution provenance.
The supplemental workflow therefore runs on every pull request: a path filter
could omit an executed tracked fixture. This costs three instrumented runner
jobs even for a documentation-only change; the ordinary qualification gate
remains authoritative.

The owned `test_work_build` fixture disables Git automatic maintenance for its
baseline commit. That keeps a transient Git lock from racing the production
snapshot; production snapshot failure remains fail closed.

Measure real Python children even when Harness replaces their environment or uses
`-I`. Keep production argv, environment policies and source bytes unchanged. Keep
all source modules in the denominator. Retain each platform's result separately;
combine only successful runs of the same commit, source and execution-input hashes,
pytest version and collector version, with no post-run drift.
The supplemental workflow disables checkout newline conversion on its disposable
runners so Windows and POSIX measure identical source bytes. A CRLF-converted
checkout is rejected by the combiner rather than silently normalized.

A disposable macOS/Python 3.10 experiment ran the existing test-change and MCP
suites: 61 passed. A virtualenv startup hook measured 50/52 statements in the
pytest worker and 139/156 in the MCP server; the denominator remained 13,623.
These are observed test paths, not new behavioral tests or Windows evidence.

The collector uses public coverage.py start/save APIs through a temporary `.pth`
file in a dedicated virtualenv. Normal subprocess environment propagation cannot
reach every scrubbed child. Changing production isolation to pass collector
variables, or calling helpers directly merely to fill lines, was rejected.

## Run locally

Build and install the current wheel, its locked test dependencies, pytest 9.1.1
and coverage 7.13.5 in a **new disposable virtualenv**. Never use a retained or
shared environment: its Python startup is instrumented while the suite runs.
Then use that environment's Python:

```sh
python scripts/measure_coverage.py --output /absolute/new/coverage-result
```

The output must be new and outside the checkout. On Windows use `--suite platform`
for the platform test selection already exercised by qualification. POSIX uses the
full suite. The collector verifies that installed wheel source matches the checkout,
uses a private temporary directory, and removes its own startup hook on exit.
An abrupt kill may leave the hook: retire that disposable environment.

Outputs include the test transcript, JSON/HTML line and branch reports, raw data,
and a manifest naming the source revision, source and execution-input hashes,
platform, suite, exit status and post-run drift status.
A failed suite remains failed even if its partial coverage report exists. The
supplemental CI jobs upload those files without imposing a coverage threshold.
Test execution and the outer CI job have separate limits:

| Measurement | Test execution budget | Outer CI job |
| --- | --- | --- |
| Linux full suite | 1,200 seconds | 25 minutes |
| macOS full suite | One shared 1,500-second deadline across two supervised module partitions | 30 minutes |
| Windows platform selection | 2,520 seconds inside the platform driver; 2,700 seconds for its measurement wrapper | 50 minutes |

The outer jobs leave time for environment setup, report generation and artifact
upload. These measurement limits do not change individual operation deadlines.
Uninstrumented installed-wheel qualification retains 1,800 seconds on Windows
and 900 seconds on POSIX, with separate 35-minute and 20-minute CI jobs.
Instrumented results do not qualify a platform. A timeout leaves failed or
unfinished evidence that cannot be combined.

The macOS full suite uses the existing source-suite supervisor and module
partition verifier. Both workers must collect the same complete suite, select
disjoint module partitions whose union covers that collection, and record every
selected case starting and ending exactly once. Both must finish successfully
with valid JUnit results. Dispatch, worker setup and execution consume one
shared deadline; a delayed worker receives only the remaining time. Expiry or a
failed worker cancels its sibling. The supervisor drains both workers before
the measurement removes its startup hook. A late successful exit cannot clear
an expired deadline. This changes scheduling, not the tests, coverage denominator
or ordinary Windows source-suite supervision, and does not guarantee a speedup.

Before launch, the root manifest records the execution topology, shared budget,
supervisor receipt and both partition evidence paths. The workers write live
diagnostics under `instrumented-platform/shard-0/` and
`instrumented-platform/shard-1/`, which the existing workflow uploads recursively.
This retains partial files without requiring a final copy, provided the hosted
job reaches its artifact upload step. Failed, incomplete or input-drifted
partitions cannot proceed to coverage reporting or combination.

The full POSIX measurement retains `test-timings.jsonl` and `slow-stacks.txt`
using the same Python watchdog as platform qualification. Each test and phase
start is written immediately, with outcomes and durations added as they finish.
After a timeout, inspect the last event to identify the active case and its
setup, call or teardown phase. Slow tests retain Python stacks after 60 seconds.
The workflow uploads the journal even when pytest cannot finish its JUnit file.
Each worker also writes failed setup, call and teardown details immediately to
`failed-phases.jsonl`, bounded to 64 records and 1 MiB. Truncation is explicit;
captured streams, environment variables and local variables are omitted.
The watchdog needs the GIL and cannot sample a C extension that holds it;
collection time before the first case also has no per-test stack. These
diagnostics preserve the independent process deadline and coverage admission
checks. They do not establish why an earlier run timed out or correct its speed.

Combine downloaded result directories at that exact source revision:

```sh
python scripts/measure_coverage.py --output /absolute/new/combined \
  --combine /absolute/linux-result /absolute/windows-result /absolute/macos-result
```

Combining requires the pinned collector and rejects a different revision, altered
source, altered test/fixture/driver bytes, or a failed/unfinished suite. Older
receipts without execution-input hashes cannot be combined. Keep the individual platform reports beside
the union: execution on one OS does not establish behavior on another.

## Limits

Python children using `-S`, another uninstrumented interpreter, or abrupt termination
before saving can remain unmeasured. Empty-child coverage warnings are disabled
to preserve application stderr; incomplete raw data warnings remain visible.
Startup tracing adds overhead and imports;
uninstrumented qualification remains the authority for platform behavior. The
Windows selection differs from the POSIX full suite. Neither an instrumented
platform receipt nor its combined coverage percentage expands qualification claims.
