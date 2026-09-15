# E2 fix: evidence belongs to an invocation

2026-09-14. **Disposition: adopt the narrowed call-bound contract for the local
profile.** The replacement passes its frozen criteria. It does not predict
general availability, serve cached tool output or introduce a production cache.
The original cache hypothesis remains **revise**, with its evidence retained.

[Design before implementation](design-e2-revision.md),
[frozen revised protocol](../experiments/e2_revision/protocol.json),
[freeze and original-source hashes](receipts/e2-revision/freeze.json),
[independent audit](receipts/e2-revision/audit.json).

## What changed

The replacement in [policy.py](../experiments/e2_revision/policy.py) separates:

- **Current permission to attempt:** declarations, grants, lifecycle and exact
  dependency checks permit or refuse an invocation. Permission does not predict success.
- **Historical evidence:** matching, stale, invalid or absent. Saved observations
  copy their data so later caller changes cannot alter the historical snapshot.
- **Actual invocation result:** success/failure belongs to the requested call.
  Success requires matching scope before and after, the expected run directory,
  a completed durable target event, matching arguments/result and, for MCP, matching
  structured and textual wire content. A previous invocation's record cannot
  substitute for the new one. Only this call's result is returned.

Both plans and completed results keep general availability **unverified**. A
later failure remains a failure even immediately after a matching successful
observation. Missing or stale history alone does not block authorized useful work.
Denied operations do not dispatch through the revised consumer.

The experiment's consumer executes the requested operation once. A separate
oracle invocation exists solely to validate the read-only fixture; the proposed
consumer does not probe and then assume a subsequent operation will succeed.
The implementation is a disposable policy/consumer experiment, not a new
production authorization boundary. Existing Harness already uses call-time
guards and call-bound evidence, so its production source needed no cache patch.

## Frozen comparison and results

The unchanged original cache and revised policy each ran in twelve fresh cells:
six states across command-review and MCP SDK 2.2.0 stdio/2026-07-28. Plans were
saved in separate processes before invocation/oracle results. Both revised
working cells additionally received a new runtime failure after success without
changing the descriptor. Missing-dependency cases used the existing isolated
environment with attune-rag code and metadata absent.

| Check | Observed |
|---|---:|
| Independent main cells audited | 24/24 |
| Original cache false verified-availability claims | 2 |
| Revised pre-call usability/verified-availability claims | 0 |
| Revised post-call general-availability claims | 0 |
| Working current results delivered | 2/2 |
| Upgraded current results delivered | 2/2 |
| Prior upgrade history marked stale | 2/2 |
| Broken-runtime failures reported without old output | 2/2 |
| Missing/disabled/denied cases with no consumer dispatch | 6/6 |
| Success-then-failure cases reported correctly | 2/2 |
| Unnecessary rejections / false observed success | 0 / 0 |

[Raw rows](receipts/e2-revision/run-01/rows.json) retain every cell. Each directory
includes decisions, observations, raw/durable records and process chronology.
The audit independently checks installed-module hashes against the qualified
wheel, artifact/source hashes, durable records against returned summaries,
MCP content, decision ordering and all acceptance arithmetic. It does not import
the revised policy. There were **43 selected-participant target dispatches** across
qualification, requested calls and evaluation oracles, including the added fault
checks. Coordinator preflight and reviewer activity is outside that metric.
No timing, cost, model-quality or cross-host superiority is claimed.

All frozen targets passed. This is a new, narrower result; the original
general-availability requirement was not relaxed retroactively or declared met.
All files under experiments/e2 remain byte-identical to their frozen baseline.

## Validation and retained corrections

**523 tests passed**, including **44 new policy checks**, at **94.50% production
statement coverage**. [Suite](receipts/e2-revision/suite.txt),
[new tests](receipts/e2-revision/evaluator-tests.txt),
[coverage](receipts/e2-revision/coverage.json).
New tests accompany new experiment code; no existing-production mutation fraction
is owed. The tests cover both command and MCP evidence, stale result substitution,
misleading history, grant/lifecycle/dependency denial, changed scope and mismatched
durable responses. Two initial tests exposed shared references in historical
snapshots; copying observation data fixed them. The initial failing test output
is retained at evaluator-tests-initial.txt in the receipt directory.

The initial audit incorrectly compared pre-upgrade qualification evidence with
the new artifact. The final audit checks historical evidence against its original
descriptor and current calls against the current descriptor. Its first failure,
final source copy and final source SHA256 are retained. This was an auditor
correction, not a protocol/threshold change or a rerun of the matrix. The archived
matrix sources include the initial auditor; the final audit identifies its own
corrected source hash separately.

The qualified wheel is unchanged:
`c07d974a0eb4da5d9a90111d9148654a3967e251367bf6ac072dc7703799b27c`.
The prior 110 installed protocol checks were not rerun. This comparison itself
used installed Harness and real local command/MCP boundaries.

## Reproduce

From the Harness root, choose a fresh output directory:

```sh
.venv-mcp2-probe/bin/python -m pytest tests/test_e2_revision.py -q
python3 -I experiments/e2_revision/evaluate.py \
  --python .venv-mcp2-probe/bin/python \
  --missing-python .venv-e2-no-rag/bin/python \
  --output /private/tmp/harness-e2-revised
python3 -I experiments/e2_revision/audit.py \
  /private/tmp/harness-e2-revised --output /private/tmp/harness-e2-revised-audit.json
.venv-mcp2-probe/bin/python -m pytest -q --cov=attune_harness \
  --cov-report=json:docs/receipts/e2-revision/coverage.json
```

No provider calls, downloads, credential operations, global environment changes,
publication or sibling-project edits occurred. The full suite uses local A2A
loopback fixtures. Phase 5's remaining E1/E3/C16 real-model and human-effort
comparisons and broader Phase 4 host qualification remain open.
