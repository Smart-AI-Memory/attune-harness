# Next native adapter experiment

Status: translators and deterministic process probes implemented; live provider
comparison partial: Codex arithmetic passed; Claude returned insufficient credit.
See [live-probe-receipt.md](live-probe-receipt.md) for exact evidence and scope.
Keep implementations disposable until qualified.
Use the same accepted Task and Attempt for the bounded arithmetic/review fixture,
with a fresh attempt ID for each invocation. Never run competing side-effecting
adapters concurrently. Native sessions/model IDs must be captured separately from
participant role and authority.

1. Record local CLI/SDK version and help, and verify current official supported
   schemas. Do not infer structured-output support from a process launching.
2. Build one native Claude and one native Codex translator to the local exchange
   boundary. Have the trusted translator bind the request digest; do not rely on
   model-generated identity as authentication. Record raw native output separately.
3. For each, test correct output, malformed/truncated output, nonzero exit, timeout,
   missing access and cancellation. A timeout leaves effects unknown unless the
   runtime proves otherwise. Preserve actionable native diagnostics.
4. Repeat with candidate ACP integrations only after supported revisions are
   verified. Compare feature invocation, human interaction, cancellation,
   reconnect and actual identity, not just text delivery.
5. Characterize one direct-model participant using the same contract. Retain
   provider-specific imports in optional integrations. No fallback provider call
   is implied by an unavailable adapter.
6. Record exact versions, reproducible commands, fixture revision, raw output,
   costs and limitations. A deterministic injected exchange provides decoder
   evidence only. Choose a substrate after this comparison.

Two approved native calls are recorded in the live probe receipt; no further
model calls occurred during the local feature milestone. The supported
platform/protocol matrix remains open. The synchronous
injected exchange is sufficient for the present text-boundary experiment, not a
choice of production orchestration substrate.

Reproduce the dependency-free fixture after installing the wheel:

```sh
python -I /Users/patrickroebuck/attune-harness/examples/json_exchange.py
```

It exercises the actual adapter and independent verifier, then verifies that a
second dispatch is refused. Its output is not a native integration receipt.
