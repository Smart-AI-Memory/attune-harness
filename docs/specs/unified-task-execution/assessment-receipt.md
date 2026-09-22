# Installed assessment software qualification

Task 5 qualifies assessment software on macOS arm64/Python 3.10.11. Native semantic/provider quality and Linux/Windows execution of the new task profile remain unrun. This permits the scoped repair implementation to proceed; it does not promote either full slice or complete the spec.

## Artifact and consumers

Fresh `.venv-task-assessment310`, installed from local pinned dependency wheels; `pip check` passed. Existing environments remained untouched. Python 3.12 setup was attempted but its cached PyYAML wheel was absent; no network dependency resolution was substituted.

Candidate wheel: `dist/task-execution-assessment/attune_harness-0.1.0.dev13-py3-none-any.whl`, SHA-256 `8fa259f391f64922bb7c41b5c6c9373f979fac3c2617918cb370e1f3c18bc76c`. Version identifies the current development line; this exact hash identifies the candidate. Built with system Python's installed build backend, without isolation/network. This is not a release or publish operation.

`scripts/qualify_task_execution.py` ran 15 isolated outside-checkout processes, verified all 40 installed module hashes against wheel and source, exercised accepted goal → paused → status → resume → completed replay for solo and independent review, and observed one independent command-peer invocation. The peer received no assessor narrative. Real forms/retrieval/verification libraries ran. Native/provider calls: zero.

Additional installed consumers: 12 legacy review cases and 23 recovery cases passed, including one observed local fixture effect. All 18 legacy help/parser routes remain covered by the focused source compatibility suite. No old record migration occurred.

## Failure sensitivity and timing

`scripts/check_task_mutations.py`: 5/5 guard mutations detected by 13 distinct test cases; unmodified control passed. Guards: assignment reply correlation, completed replay, source freshness, output budget, and reviewer isolation. Disposable copies only; working source unchanged.

30 installed presentations per condition: cold median 2.565 ms, warm 2.227 ms, bypass 2.474 ms. Five fresh-process calls median 148.654 ms. This is a modest in-process rendering saving, not evidence for a persistent disk cache or fewer model calls. Cache limit 16; avoided model calls zero; no questions were needed because accepted inputs were reused. Detailed dependency/lookup/build/render/freshness measurements are retained in `task5-installed/010-intake-comparison.json`.

## Retained evidence and limitations

Raw evidence lives under `docs/receipts/unified-task-execution/`: `task5-installed/summary.json`, `task5-mutations/summary.json`, `task5-legacy-review.json`, `task5-legacy-recovery.json`, and `task5-applicable-suite.xml`. The broader initial failures are retained in Task 3's receipt: localhost A2A fixtures could not run reliably here, and seven historical review-quality fixtures require their original artifact. Neither is relabeled as passing. Full applicable suite: **1,076 passed, 25 skipped**, excluding those two explicitly identified modules. Current task software acceptance makes no native provider or semantic accuracy claim.
