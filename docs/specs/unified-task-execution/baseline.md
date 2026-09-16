# Task 1 baseline — unified task execution

Status: accepted on offline evidence, 2026-09-16; **1/8 tasks accepted**. Baseline artifacts were committed as `e546cc6` before production changes. This increment adds measurement and compatibility artifacts, not production runtime behavior.

## Reproduce and retained evidence

Source HEAD: `ce61c18ac396c91e5441ac34f218e41c942df593`, branch `codex/update-session-starter`. Measured with Python 3.12.13 at `.venv-voyage312/bin/python`, forms 0.17.0, verify 0.6.0, RAG 1.2.0 and MCP 2.2.0. Source and loaded library paths/hashes are in the receipt. No environment was upgraded.

```sh
PYTHONPATH=src .venv-voyage312/bin/python -B experiments/task_execution/baseline.py --output docs/receipts/unified-task-execution/new-baseline-directory --samples 50 --process-samples 20
```

Output must not already exist. The runner blocks native-model and Voyage-provider construction, runs a fixed local subprocess peer for effect recovery, and retains failures before checking expected behavior. The frozen run is [task1-baseline-v2](../../receipts/unified-task-execution/task1-baseline-v2/summary.json): 54 CLI captures, all 18 help routes, 154 hash-verified artifacts, zero live-provider attempts. Earlier probe runs remain retained; v2 adds genuine untouched paused/uncertain runs at their original paths and complete measurement-source identities. No runtime was optimized between these authoring runs.

The existing unrelated `tests/test_voyage.py`, Voyage starter, and Voyage profiling script were hashed before and after the run. All 42 captured source/measurement files were unchanged at final integrity verification. [Integrity receipt](../../receipts/unified-task-execution/task1-integrity.json).

## Frozen behavior

| Case | Execution status | Document / retrieval result | CLI exit |
|---|---|---|---|
| Valid link and matching evidence | completed | verified / retrieved | 0 |
| Missing referenced file | completed | refuted / retrieved | 1 |
| No supported claims | completed | unknown / retrieved | 1 |
| No matching evidence | completed | verified / no_results | 1 |
| Declined, stale or missing intake | failed | no run directory created | 2 |
| Pause after two operations | paused | preserved checkpoint | 1 |
| Resume matching pause | completed | verified / retrieved | 0 |
| Reuse completed record | completed | identical record bytes, no new dispatch | 0 |
| Stale checkpoint | failed | no continuation | 2 |
| Cancel stopped run | cancelled | no rollback claim | 1 |
| Transfer stopped lead | paused | new accepted participant; resumes successfully | 1, then 0 |
| Peer writes then exits before acknowledgement | failed | dispatching effect remains uncertain | 2 |
| Resume that uncertain effect | unresolved | no second peer write | 2 |
| Reconcile correlated saved reply | paused | exact effect accepted as completed | 1 |
| Resume reconciled run | completed | peer effect count remains one | 0 |

The ordinary deterministic review has 13 journal events: preflight verification, initial retrieval, six participant turns, four participant-requested tools, and final verification. Those repeated operations are existing policy behavior; this baseline does not label them all redundant or approve their removal. Participant text explicitly states that no model judgment was performed.

Genuine retained records are named in `summary.json`: `clean/run`, `frozen-paused/run`, and `frozen-uncertain/run`. Each retains its original absolute request/config/source paths, accepted digests and operation identities. Snapshot copies document intermediate states but do not bypass the existing copied-directory restriction. The reconciliation demonstration and the separately retained uncertain fixture each wrote exactly once; neither made a provider call.

## Complete command disposition baseline

Every command's actual `--help` output is retained, including arguments and exit status. The following captures add operation behavior; negative fixtures are explicit, not represented as successful operational qualification.

| Current command(s) | Operation captures / existing behavioral owner |
|---|---|
| review-form, review | Actual form, clean/refuted/unknown/no-evidence/intake cases; test_review and test_review_boundaries |
| inspect-review, resume-review | Actual completed inspection, paused/completed/stale/uncertain continuation; test_recovery |
| reconcile-review, transfer-review, cancel-review | Actual recovered-reply reconciliation, accepted lead transfer and stopped-run cancellation; test_recovery |
| retrieve, verify | Actual keyword retrieval and supported-claim verification |
| extension | Actual bundle discovery; lifecycle covered by test_extensions |
| code-config | Actual configuration preparation |
| index, retrieval-task | Invalid configuration rejection captured; successful generation/intake and freshness behavior covered by the current Voyage suites |
| triage-check | Actual bounded suggestion with dispatch_authorized=false; test_operations |
| repair-economics | Invalid ledger rejection captured; valid/missing-cost cases covered by test_operations |
| github-checks | Actual empty complete export; does not falsely report all checks passed |
| mcp-inspect | Actual completed local retrieval-session inspection |
| mcp-serve | Invalid intake refused without protocol stdout; real stdio/service cases covered by test_mcp |

## Source ownership before consolidation

| Responsibility | Existing owner | Migration evidence required later |
|---|---|---|
| Legacy accepted form and registry | review_contract.review_form / accept_request | Preserve validation/revision behavior; new intake must not create a second acceptance authority |
| Request/source preparation | review.prepare_review | Preserve artifact/source/grant binding on new tasks and legacy continuation |
| Participant loop, tools and integration | review.execute_review | New policies and legacy routes must share dispatch while retaining results/exit semantics |
| Transport and evidence policy | review_participants.ReviewExchange, native.NativeExchange | Reuse the adapter boundary and preserve actual invocation counts |
| Journal and continuation | recovery.RecoveryCursor / resume_review | Preserve completed/unknown effects and operation identities |
| Atomic records and leases | review_store.RunStore | One durable record owner per task |
| Paid retrieval stages | voyage_provider.StageJournal and voyage_retrieval | Preserve paid-stage semantics; a similar interface alone does not justify deleting the journal |
| CLI projections | cli, review_cli, extension_cli, voyage_cli | Keep all old routes callable and deterministic routes model-free |

There is one existing legacy review orchestration loop, not 18 implementations. **Zero duplicate execution paths are retired by Task 1.** Later receipts must identify actual removed responsibilities, not count renamed commands as maintenance savings. The dependency-free synchronous core remains a separate supported boundary.

## Intake timing baseline

Raw samples are retained in [timings.json](../../receipts/unified-task-execution/task1-baseline-v2/timings.json). These are sequential local observations, not a comparative optimization result.

| Operation | Samples | Median ms | p95 ms |
|---|---:|---:|---:|
| Build form schema, warm process | 50 | 0.171 | 0.309 |
| Render Markdown, warm process | 50 | 0.015 | 0.043 |
| Complete review_form, warm process | 50 | 0.906 | 1.151 |
| Validate accepted request, warm process | 50 | 2.416 | 2.830 |
| Fresh guarded process running review-form | 20 | 227.052 | 230.531 |

Fresh-process time includes the probe and poison-boundary setup as well as startup, imports, output transfer and the form. OS filesystem caches may remain warm. This is not an isolated startup-overhead estimate and not user-visible host latency. Actual screen presentation, conversational question counts, network transport, model quality, human time and billed cost remain unmeasured. No cache-savings claim follows from these numbers. They support measuring process/interaction overhead before building a persistent rendering cache.

## Verification and remaining review

- The selected review/recovery/native-evidence/Voyage/operations/extensions/MCP suite passed **371 tests in 34.64 seconds**. This run included the first 27 new compatibility cases.
- After adding the immutable-output-directory check, the final [compatibility suite](../../receipts/unified-task-execution/task1-compatibility.json) passed **28 tests**. This overlaps the earlier suite; the counts are not additive.
- A [disposable mutation](../../receipts/unified-task-execution/task1-mutation-retry.json) removed the completed-review verdict exit guard. **1/1 mutation detected; 3/4 selected new cases failed**, while the original cases passed. An initial probe path assertion stopped before pytest; its failed receipt is retained separately.
- The frozen manifest, original paused/completed/uncertain record states and unchanged source were independently checked after the run.

The standard Attune task-quality workflow invokes paid code-review/security agents; it was not run under this offline task's scope. No skipped review is reported as passed and no model-derived quality score is fabricated. Patrick selected offline acceptance after the 28 compatibility tests were rerun and all 154 frozen artifacts and 36 production modules were verified unchanged. The canonical collector accepted `approve_task` at workspace `spec-a783c8d9ea154f23a68e04f7effe23a3`, revision 2. Its numeric field explicitly denoted observed compatibility-test pass percentage (28/28 × 100), not a paid review or semantic-quality score. Installed-artifact, native-provider and comparative semantic qualification remain later tasks.
