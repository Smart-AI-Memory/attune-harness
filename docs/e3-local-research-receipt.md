# E3 local collaboration research — revise

2026-09-14. All **144 real workflow trials** ran on the installed dev1 wheel:
12 diagnostic tasks × four strategies × three repeats. The independent auditor
checked frozen inputs, archived executor sources, stage routing, reviewer
isolation, exact prompts/seeds, raw replies and recorded token usage before
scoring. [Analysis](receipts/e3-local/analysis.json),
[execution record](receipts/e3-local/run-01/execution-summary.json),
[retained failures](receipts/e3-local/failures.json).

| Strategy | Correct / 36 | Critical misses | Failed trials | Model calls | Median tokens | Median seconds |
|---|---:|---:|---:|---:|---:|---:|
| Solo | 22 | 2 | 0 | 36 | 247.5 | 1.959 |
| Fixed cross-review | 21 | 3 | 0 | 108 | 904 | 6.038 |
| Fixed roundtable | 22 | 1 | 1 | 180 | 1,607 | 9.676 |
| Adaptive | 22 | 2 | 2 | 156 | 1,604 | 9.638 |

The predeclared best fixed baseline is roundtable. Adaptive has equal completed-
correct count, **one extra critical miss**, only **0.19%** lower median tokens and
**0.40%** lower median latency. Disposition: **revise**. Do not promote adaptive
routing to a production default. Neither strategy agreement nor call completion
establishes correctness: all strategies missed or invented findings on this set.
Three invalid findings arrays failed strict response validation and remained in
all scoring denominators; no generation was retried or omitted.

The 2,000-replicate paired task-cluster bootstrap reselected the best fixed
baseline within each family-stratified resample. Descriptive 95% intervals:
correct-count difference [0, 0]; additional critical misses [0, 3]; median-token
reduction [-78.74%, 2.72%]; median-latency reduction [-61.91%, 1.76%]. These are
exploratory intervals on a small convenience set, not population guarantees.
The degenerate correctness interval reflects these particular paired outcomes.
Paid-cost reduction is undefined because both conditions have zero API charges.
Human repair effort and local compute/energy cost were not measured.

## Boundaries and reproducibility

There were **480 local generation requests**, no human intervention during the
campaign and **zero paid API calls**. Elapsed campaign time: 966.24 seconds.
The earlier disposable arithmetic call succeeded, but the separate installed
three-call calibration incorrectly rejected `17 + 25 = 42`; both results are
retained. No prompts, routing rules or scoring thresholds changed after freezing.
The calibration is excluded from the 144 trials and 480 campaign calls.

Model: local `llama3.1:8b`, Q4_K_M, Ollama 0.31.1; exact model digest
`46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`.
Settings and seeds: [frozen protocol](../experiments/e3_local/protocol.json).
Roles share the same model weights. This does not qualify native Claude/Codex,
diverse-model collaboration, general coding tasks or human preference.

Wheel: `dist/attune_harness-0.1.0.dev1-py3-none-any.whl`, SHA256
`4521aa9e093ba5391b77aeeb88eebd4ffd23d084993597d3ce756b5c01a9a537`.
The core-only `.venv-e3-local` environment imported all 20 modules from installed
site-packages; their hashes matched the archived source. [Artifact](receipts/e3-local/artifact.json).
The new adapter/executor tests passed 44 cases and the full suite passed 567.
The prior dev0 artifact and environments remain preserved.

```sh
python3 -I experiments/e3_local/analyze.py docs/receipts/e3-local/run-01 --output /private/tmp/e3-local-reanalysis.json
```

This reanalysis makes no model calls. For optional live reproduction, first run
`python3 scripts/restore_e3_snapshot.py --directory /private/tmp/e3-snapshot`.
That preparation also makes no model calls and restores the archived executor,
20-module dev1 source and frozen inputs. Use the preserved `.venv-e3-local/bin/python`
with the restored `experiments/e3_local/run.py`, its `--python` argument pointing
to that absolute interpreter, and a new `--output` directory. The current dev3
source intentionally differs and must not be substituted for the frozen source.
The restored workspace was checked to prepare 144 trials and match the installed
dev1 module hashes. A new live campaign makes up to 504 generation requests and
preserves failures. The original synthetic campaign and its input
hashes remain untouched. See [design](design-e3-local-increment.md),
[calibration](receipts/e3-local/calibration/record.json) and
[freeze](receipts/e3-local/freeze.json).

## Phase 5 decision

The bounded research now has retained dispositions for all required ideas:
E1 **inconclusive** beyond its passing local recovery precursor; original E2
**revise**, with its replacement **adopted only as a narrowed local call-bound
contract**; E3 and C16 adaptive policy **revise** for this local model/task profile.
Phase 5's bounded research decision work is complete. Broader E1 model/human
comparisons, paid-cost evaluation and native-provider obligations remain
unqualified; an inconclusive disposition does not count as passing those claims.
Proceed with explicit collaboration choices and a bounded Phase 6 pilot.
