# E2 capability-evidence experiment

2026-09-14. **Disposition: revise.** Historical success plus matching versions
and scope is insufficient to claim current verified availability. The candidate
cache remains an experiment; production retains its existing call-time guards
and call-bound evidence. This is an E2 result, not full Phase 4 completion.

**Follow-up fix:** the [revised call-bound contract](e2-revision-receipt.md) passes
its new frozen local criteria. It labels history without predicting availability
and returns only the requested invocation's result. The original experiment and
its **revise** disposition below are preserved.

[Frozen protocol](../experiments/e2/protocol.json), [design before implementation](design-e2-increment.md),
[raw matrix](receipts/e2/run-01/summary.json), [independent audit](receipts/e2/audit.json).

## What ran

Six states × two adapter types × two policies = **24 evaluated cells**, with no
infrastructure failures. Each cell used new files, installed Harness, a healthy
qualification call, a separately saved policy decision and an independent fresh
oracle process. Four upgrade cells also received the preregistered requalification
and another oracle call. The audit verified decision-before-oracle order, actual
wire/record outcomes, artifact/source hashes and all metric arithmetic. There
were **40 selected-participant target dispatches**, including four failed MCP
retrievals; coordinator preflight/reviewer calls are outside that count.

The adapters were the real review coordinator with an independent JSON command
participant, and MCP SDK 2.2.0 stdio/2026-07-28 with an independent stdlib client.
Missing-dependency cells used a separate environment with both attune-rag code
and metadata absent, while MCP/forms/Harness remained installed. Runtime breakage
was an explicit exception injected into the fixture process's retriever after a
successful observation. Package/artifact versions, accepted inputs, schemas and
source hashes remained unchanged in those cells. No installed library file was
modified, and this seeded fault is not reported as a discovered product defect.

The declaration-only policy makes a deliberately naive usability prediction from
the manifest. **Existing Harness labels this declared, not verified.** The cache
candidate promotes an earlier successful call to `verified_available` only while
its recorded descriptor matches and current grants/lifecycle/dependencies permit
use. That promotion is what the experiment tests.

## Full matrix

Each policy cell below links to its retained row, with its saved decision and
oracle files in the same directory. “Yes” is an independently checked real
retrieval. “No” is the intended refusal or runtime failure at the adapter boundary.

| Adapter | Seeded state | Oracle usable | Declaration-only prediction | Version-bound cache |
|---|---|---|---|---|
| Command review | Working | Yes | [Usable](receipts/e2/run-01/00/row.json) | [Verified available](receipts/e2/run-01/06/row.json) |
| Command review | Advertised but broken | No | [Usable — false](receipts/e2/run-01/01/row.json) | [Verified available — false](receipts/e2/run-01/07/row.json) |
| Command review | Dependency missing | No | [Usable — false](receipts/e2/run-01/02/row.json) | [Unavailable](receipts/e2/run-01/08/row.json) |
| Command review | Upgraded | Yes | [Usable](receipts/e2/run-01/03/row.json) | [Needs probe; usable after requalification](receipts/e2/run-01/09/row.json) |
| Command review | Disabled | No | [Usable — false](receipts/e2/run-01/04/row.json) | [Denied](receipts/e2/run-01/10/row.json) |
| Command review | Permission denied | No | [Usable — false](receipts/e2/run-01/05/row.json) | [Denied](receipts/e2/run-01/11/row.json) |
| MCP stdio | Working | Yes | [Usable](receipts/e2/run-01/12/row.json) | [Verified available](receipts/e2/run-01/18/row.json) |
| MCP stdio | Advertised but broken | No | [Usable — false](receipts/e2/run-01/13/row.json) | [Verified available — false](receipts/e2/run-01/19/row.json) |
| MCP stdio | Dependency missing | No | [Usable — false](receipts/e2/run-01/14/row.json) | [Unavailable](receipts/e2/run-01/20/row.json) |
| MCP stdio | Upgraded | Yes | [Usable](receipts/e2/run-01/15/row.json) | [Needs probe; usable after requalification](receipts/e2/run-01/21/row.json) |
| MCP stdio | Disabled | No | [Usable — false](receipts/e2/run-01/16/row.json) | [Denied](receipts/e2/run-01/22/row.json) |
| MCP stdio | Permission denied | No | [Usable — false](receipts/e2/run-01/17/row.json) | [Denied](receipts/e2/run-01/23/row.json) |

| Metric | Declaration-only | Version-bound cache |
|---|---:|---:|
| Evaluated cells | 12 | 12 |
| False usable predictions | 8 | 2 |
| False **verified availability** claims | 0 — makes no such claim | 2 |
| Unnecessary rejections | 0 | 0 |
| Usable cases deferred for a new probe | 0 | 2 |
| Working cases accepted | 2/2 | 2/2 |
| Prior upgrade evidence invalidated | Not applicable — no evidence cache | 2/2 |
| Upgrades usable after fresh qualification | 2/2 | 2/2 |

The candidate detects missing dependencies, denied access and disabled state,
and correctly invalidates upgraded evidence. Both working cases remain usable.
It still makes two false verified claims when a backend breaks without a visible
descriptor change. The frozen zero-false-verified-claims criterion therefore
fails. We did not change the criteria, add a TTL, exclude those failures or rerun
until a preferred result appeared. The safe production declaration semantics
make no verified claim, which is why the two error columns must remain separate.

## Resulting design decision

Retain version-bound observations as evidence of **that call**, with its arguments,
artifact, dependency and corpus identity. Retain current scope/lifecycle checks
and truthful invocation failures. Do not introduce a production availability
cache that promotes historical success to a guarantee of the next call. When
an upgrade changes context, require fresh qualification rather than transferring
old evidence. A fresh probe can add a new observation; it cannot eliminate the
possibility of failure between that probe and use.

This keeps the current simpler implementation. A future registry may index
declarations, scoped observations, explicit denials and needs-probe states, but
must preserve those meanings and earn any stronger availability claim in a new
frozen experiment. E2's local comparison now has a disposition; the rejected
candidate's availability requirement is not declared satisfied.

## Validation and reproduction

**445 tests passed**, including 18 new adversarial evaluator tests. Production
statement coverage remains **1,666/1,763 (94.50%)**; subprocess execution is not
included in coverage hits. [Suite](receipts/e2/suite.txt),
[evaluator tests](receipts/e2/evaluator-tests.txt), [coverage](receipts/e2/coverage.json).
No production source or existing test was edited. New experiment code owes no
existing-code mutation fraction. The previous installed/protocol qualification
remains attached to the unchanged wheel; no new 110-case regression run is claimed.

Baseline wheel SHA-256:
`c07d974a0eb4da5d9a90111d9148654a3967e251367bf6ac072dc7703799b27c`.
Frozen source protocol SHA-256:
`2bf737927b70683408c451404babeb2cf5f4955c5571eb3020aacf1af5376c76`.
The evaluator checks both before running and checks its source hashes again at
completion. [Freeze receipt](receipts/e2/freeze.json),
[experiment source hashes](receipts/e2/run-01/source-hashes.json).

From the checkout, using the already prepared isolated environments:

```sh
.venv-mcp2-probe/bin/python -m pytest tests/test_e2_experiment.py -q
.venv-mcp2-probe/bin/python -I experiments/e2/evaluate.py --python .venv-mcp2-probe/bin/python --missing-python .venv-e2-no-rag/bin/python --output docs/receipts/e2/new-run
python3 -I experiments/e2/audit.py docs/receipts/e2/new-run --output docs/receipts/e2/new-audit.json
```

The output directory must be new; previous runs cannot be overwritten. Recreating
the no-rag environment requires no downloads:

```sh
python3 -I experiments/e2/prepare_environment.py --source-python .venv-mcp2-probe/bin/python --output-venv .venv-e2-fresh --receipt docs/receipts/e2/fresh-environment.json
```

This helper was itself exercised against a second fresh environment;
[absence checks](receipts/e2/environment-reproduction.json) passed. It refuses
to replace an existing environment. Only the qualified environment's local
packages are copied, excluding attune-rag and its metadata.

No provider calls, credential operations, downloads, external network requests,
host registration, sibling edits or publication occurred in E2. The full suite
used its already established local A2A loopback fixtures under automatic sandbox
approval. No tests were skipped. No different-model review ran. Findings apply
to this deterministic local matrix, not model quality, authenticated hosts,
time-dependent reliability or statistical superiority.

Phase 4 remains open for broader host/authenticated integration. E1/live-model
obligations and E3 collaboration-value trials remain open; no paid trial was run.
