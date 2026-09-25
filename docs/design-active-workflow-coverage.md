# Active workflow coverage

The goal is 90% overall line coverage, with branch coverage reported separately.
There is no per-module 100% requirement. Keep the production denominator intact;
do not exclude legacy or platform modules merely to improve the percentage.

## Baseline and probes

At `9cb41c5` (source/tests unchanged by `94f88f2`), macOS/Python 3.10 measured
11,523/13,623 statements (84.58%) and 4,500/5,842 branch exits (77.03%).
2,648 tests passed and 75 skipped. Subprocess coverage was not enabled. These are
local measurements, not Windows coverage or native-model quality evidence.

Disposable installed-CLI probes exercised wrong output, repeated completed-task
resume and changed source after success. All seven assertions passed: bad output
failed, repeated resume preserved the record and dispatch count, and stale source
blocked reuse without changing the source. A completed lifecycle is distinct from
the current result: callers must read the latter. No production mutation ran.

## Cases to add

- Review handoff: retain finding/evidence identity through stage, freeze and build;
  reject altered source, target or dispositions; archive removed task findings;
  prevent a repair from repurposing retained task outputs; isolate turn copies.
- Repair/effects: reject unauthorized paths and modified probes, distinguish
  expected before/after bytes from unknown effects, preserve unrelated changes,
  and stop dispatch when authority or evidence is invalid.
- Memory host/worker: use temporary native-reader roots and offline proposals;
  refuse expanded authority and escaping job paths, retain failed proposals,
  separate missing evidence from reasoning escalation and avoid duplicate work.
- CLI/evidence boundaries: exercise real public entry points where their behavior
  is not established by the above tests; distinguish missing measurement in child
  interpreters from missing behavioral checks.

New tests should assert outcomes, retained bytes and dispatch counts, not mirror
implementation branches. Use selected guard-removal probes in disposable copies
to check that high-consequence assertions can detect the intended regression.
Report discovered bugs separately before expanding a test-only change into a fix.

## Boundaries and alternatives

Start with active workflow paths, then remeasure. Stop to assess diminishing
returns if reaching 90% requires dormant provider integrations, retired artifacts
or artificial platform simulations. Native/paid calls and live memory changes are
outside this work. Preserve historical receipts, environments and fixtures.

Rejected: chasing the lowest percentages regardless of relevance, broad mocks
that manufacture success, or changing exclusions to make the target pass. These
would improve a number without establishing the behaviors users depend on.
