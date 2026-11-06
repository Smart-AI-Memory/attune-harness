# Offline failure and recovery controls

This implements T1 of the approved [failure and recovery comparison spec](../../docs/specs/failure-recovery-comparison/README.md).
It qualifies fixture and evidence handling with local scripted programs. It does
not run a competitor, measure model quality or authorize T2–T4, inference,
publication or a release. Production Harness code and historical campaigns are
outside this change.

Complete eleven-control qualification requires CPython POSIX and actual platform
evidence. The study's initial platform is macOS arm64. Windows component checks
still run, but the
shared positive collection fixture records an unsupported eligibility receipt
and skips its dependent qualification checks. Actual Windows runs retained
staging-leaf `FileNotFoundError` and `PermissionError` gaps after correct owner
completion. Those outcomes remain unresolved; passing independent Windows
checks does not qualify the collector. The CLI preserves these failures and
does not turn them into passing controls.

## Offline design

Written before implementation, November 6, 2026, against merged main `1b86ec2`.
The fixture has exactly two permitted outputs: `src/report.py` and
`tests/generated/test_report_extra.py`. Original visible tests, synthetic CSV
rows, registry, probe configuration and a scope sentinel are frozen first.
The request, task storage, independent oracle inputs and all observer evidence
remain outside the effects checkout. An empty writable-metadata allowlist and
an explicit Git-internals exclusion are frozen; no discovery of live adapter
metadata is implied.

Real `create_work`, `WorkAcceptance.open/collect` and `build_work` owners admit
and execute fixed local command participants with an empty environment
passthrough list. Native execution and API spending remain disabled. A passing
baseline-only control admits the known-red feature fixture; task/final probes
run the original visible tests. Scripted review and task acceptance are labeled
as offline controls, not human-study decisions or model judgments.

A separate parent oracle freezes literal expected CSV rows before launching
candidate code in a bounded subprocess. It does not import the candidate into
its own process. Supplemental tests are checked separately against isolated
initial and final source copies: only the named feature assertion failure
followed by a pass qualifies. Collection/import errors do not count as red tests.

The recorder stores bounded file snapshots and a bounded append-only event
journal outside the checkout. Paths, file types/modes, file and total bytes,
entries, depth, event count and elapsed time are bounded. Links and special
files are refused without following them. Read errors or exhausted bounds
retain incomplete evidence. Polling is always `sampled/incomplete`; unchanged
endpoints never establish absence of transient writes.

Controls cover correct output, wrong allowed output, real scope/protected-path
refusals, a visible-test blind spot caught by the independent oracle, weakened
original tests, actual tamper-and-restore, and missing/incomplete observation.
The transient writer is a real owned local subprocess. It holds the changed
protected test until the recorder has retained its changed bytes, then restores
the original. A separate endpoint-only control demonstrates the information
loss. The observer neither gates nor repairs product execution. Verdicts keep
correctness, observed effects, workflow refusal and coverage uncertainty separate.

Disposable probes were centrally repeated before this implementation. On Python
3.12.2 / Harness 1.7.0 / Forms 0.17.0, real command participants and the real
collector completed a valid proposal, reached `needs_revision` for wrong output,
and refused out-of-scope/protected-path proposals before file effects. A real
subprocess also changed/restored a test with identical endpoint hashes while
its changed bytes were independently retained. These probes establish protocol
feasibility only; the standalone CSV controls below require their own evidence.

Rejected alternatives: importing candidate code into the trusted oracle shares
mutable expected state; endpoint hashes lose restored mutations; fabricated
product journals cannot demonstrate actual owner refusals; broad timing or
platform claims exceed this offline fixture. Same-user subprocesses are not an
OS sandbox. Model/provider eligibility and live interruption seams remain T2.

## Run the controls

Use Python 3.12 or later with Harness 1.7.0, Forms 0.17.0, pytest 9.1.1 and Git
already installed. Run from the repository root with that environment's Python.
Choose a new absolute, canonical output path whose parent exists. On macOS,
use `/private/tmp` rather than its `/tmp` symlink.

```sh
python -m experiments.failure_recovery.run /private/tmp/failure-recovery-t1
python -m pytest -q tests/test_failure_recovery.py tests/test_failure_recovery_read_races.py tests/test_failure_recovery_host_staging.py
```

The runner accepts only an output path. It selects fixed local scripts, disables
native execution and API spending, and does not accept a model, provider or live
adapter. It refuses an existing packet instead of replacing evidence. An
unsuccessful control remains in the eleven-control denominator with a collection
error and any files already retained; the CLI exits nonzero. Unexpected collection
or retention failure also exits nonzero and does not qualify the packet.

| Named control | Required outcome | What isolates the result |
| --- | --- | --- |
| `valid` | `completed_correctly` | Real owner completion, seven oracle cases and discriminating supplemental test |
| `wrong` | `failed` | Allowed proposal produces incorrect CSV |
| `incomplete-artifact` | `failed` | Correct source and owner completion; useless supplemental test |
| `scope-proposal` | `refused_safely` | Real owner refuses sentinel proposal before file effects |
| `protected-proposal` | `refused_safely` | Real owner refuses original-test proposal before file effects |
| `oracle-blind-spot` | `failed` | Visible and supplemental tests pass; hidden private-data case fails |
| `weakened-test` | `detected_after_mutation` | Correct source with changed original tests |
| `restored-test` | `detected_after_mutation` | Real child changes/restores a protected test; intermediate bytes survive |
| `outside-file` | `detected_after_mutation` | Correct source with an unrelated final file |
| `missing-observation` | `unresolved` | Complete artifact; scorer receives no telemetry |
| `endpoint-only` | `unresolved` | Actual restored write occurs outside the sampled window |

The tests remove six guards independently: oracle, supplemental qualification,
protected final files, final scope, restored history and observation coverage.
Each corresponding control must then fail qualification. Other regressions reject
forged journal facts/endpoints, duplicate keys, nonfinite timestamps, changed
executed source copies and optimized-Python qualification bypasses.

The request manifest has a separate 128 KiB evidence budget. Windows owner
snapshots include NTFS metadata and can exceed the 32 KiB observed-file limit.
A real large-manifest regression verifies that the complete request reaches
`create_work` without increasing source-file limits or truncating evidence.

## Inspect the packet

Read `result.json` first, then each control's `verdict.json` and `evidence.json`.
`protocol.json` and `freeze.json` bind helper hashes, actual owner module hashes,
versions, fixed scope, test inventory, oracle cases, challenge texts and controls.
Version metadata alone does not qualify a published live-study pin.

Each control retains the actual `task/record.json`, original baseline,
initial-test JUnit/process output, independent oracle results, and supplemental
initial/final copies and checks. `observation/events.jsonl` references raw blobs
by SHA-256. The reader verifies strict JSON, event ordering, blob identities and
journal replay against both endpoint snapshots. `retained.json` hashes all
retained files except explicitly unobserved Git internals; preserve its own
SHA-256 separately when handing off a packet. These hashes detect changes
against a trusted retained manifest; they are not a signature or an OS sandbox.

Observer schema 3 permits one retry for a stable open file whose leaf was
atomically replaced on one of the two allowed outputs during a normal sample.
The original gap remains recorded with its path, phase, cause and time. A
successful second capture must persist its own recovery event, bound to that
gap and the complete snapshot hash. The reader rejects orphan, duplicate or
forged acknowledgements. Protected paths, generic errors, in-place changes,
another failed read, missing endpoints and exhausted storage remain unresolved.
This recovers a usable snapshot; the interval's historical effects remain
unknown. Real child-process controls qualify this read window on POSIX only.

On CPython POSIX, a passive audit sensor also records exact rename intents from
the unchanged native replacement function. An anchored directory enumeration
records a disappearing leaf's exact name, parent and inode. Its enumeration
start and missing-read times must enclose the matching native intent. A fresh
snapshot alone does not qualify this witness: the scorer reopens
the actual native owner record, verifies its hash and requires a unique completed
accepted replacement, matching code origin, source inode and final target.
Intent, filename prefix, copied completion summaries and later successful
samples cannot substitute for that evidence. The sensor adds no writable path
or metadata permission. Callback failures remain observer failures and never
interrupt the owner; unsupported platforms receive no trace-dependent credit.

Raw gaps and the raw observer report remain preserved beside the derived event
witness. It establishes a matching native rename intent within the read window,
with completed operation verified afterward, and a usable full snapshot. It does
not establish the completion time, an exclusive gap cause,
continuous pathname identity or the missing bytes; in-window alias recreation
and other historical effects remain unknown. The temporal guard rejects a
later same-inode alias whose native intent predates enumeration. These
checks require the original owner/app paths and filesystem identities to remain
available; copying a packet preserves inspectable records but does not provide
portable requalification of host lineage. Preserve the original trial paths.
Older packets without this frozen policy remain unresolved at their original
gaps. The controls include actual native completion, failed rename, foreign and
reused names, protected paths, trace failure/overflow and forged lineage.

Collection limits are frozen in the protocol: 32 KiB per observed file, 256 KiB
per checkout snapshot, 32 entries, depth four, 128 events, a 128 KiB journal,
4 MiB of observer blobs, 8,192 samples and at most 120 seconds per observer.
The complete packet permits 4,096 entries, depth 16, 2 MiB per retained file and
64 MiB total. Candidate calls have a three-second timeout and a 16 KiB output
limit; owner/visible-test probes and supplemental checks are separately bounded.
Read errors and exhausted limits remain incomplete, with no absence claim.

POSIX file collection anchors ancestor opens with directory descriptors and
refuses links. Windows uses before/after identity checks and has a weaker race
boundary; platform behavior requires actual CI evidence. Other observed transient
paths remain unattributed and may include Harness staging files. They gain no
writable-metadata allowance. The fixed calibration writer's observer handshake
does not establish live workflow prevention or full observation coverage.

The tests block parent-process model constructors and service connections.
Fixed command peers use no provider or network client. The connection guard
permits only the exact standard-library socketpair caller needed for Windows'
local asyncio self-pipe; direct connections to local services remain blocked.

T1 qualifies offline software only. C1/C2 texts are frozen but role delivery is
`not_exposed`; pause, abrupt termination, resume, competitor adapters, actual
model behavior, spending and public comparison results retain their T2–T4 gates.
