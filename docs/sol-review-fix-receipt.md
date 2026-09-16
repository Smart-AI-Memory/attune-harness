# Four Sol review fixes — September 16, 2026

All four confirmed medium-severity findings from the
[Sol cross-review](cross-review-sol-2026-09-16.md) are fixed in the current
`codex/voyage-retrieval` workspace. The implementation was done directly in the
current session. There was no additional model review or Fix CLI run.

## Changes

| Finding | Result | Regression coverage |
|---|---|---|
| Query embedding spent before rerank budget refusal | New and prepared embeddings check capacity for the required rerank before dispatch. Completed stages replay freely at a full budget. | Fresh and partially spent budgets, prepared continuation, exact-budget completion and replay after losing the final cache. |
| Host exception saved a completed lifecycle | Exceptions leaving plugin activation mark the session unresolved, propagate and stop further calls. | RuntimeError, KeyboardInterrupt and asyncio cancellation outside search; existing successful lifecycle tests remain green. |
| Incomplete evaluator exited zero | CLI exits 1 for incomplete campaigns, preserving printed/saved JSON and failed/unrun cases; freeze and completed runs exit 0. | Real subprocesses for freeze, denied-provider failure and cached successful campaigns. |
| Optimized Python removed qualification assertions | Explicit runtime checks reject invalid host evidence with optimization enabled. | Eight invalid boundary fixtures plus one valid fixture at optimization levels 0 and 1. |

The [design note](design-sol-review-fixes.md) records the implementation choices.
The new host fixture suite is included in `scripts/qualify_platform.py`, and the
existing Voyage mutation probe now matches the changed budget check. Usage docs,
evaluation instructions, qualification guidance and review dispositions are updated.

## Verification

All checks used deterministic providers, cached results or controlled host
fixtures. No live Voyage, Anthropic or other model calls were made.

- Before implementation, the 27 new cases produced **15 failures and 12 passes**
  against the original source. The optimized-host failures were specific to
  optimization; normal assertions still rejected those fixtures.
- The affected source/integration selection passed **340 tests** in
  `.venv-code-rag`, with one existing Attune ModelTier deprecation warning.
- After extending the evaluator cases to cover the freeze CLI too, all **five
  evaluator tests** passed again.
- Standalone MCP and the new host boundary suite passed **41 tests** in
  `.venv-mcp2-probe` (MCP 2.2.0). Eighteen host cases overlap the first selection:
  **363 distinct tests passed** across the two environments.

The four fixes were individually disabled in disposable source copies. **4/4
mutations were detected; 23/27 new cases failed with their guards removed.**
The four passing controls verify completed-stage replay, completed evaluation,
and valid host fixtures under both compilation modes.

| Removed fix | Failed / selected cases |
|---|---:|
| Required rerank capacity | 3 / 4 |
| Interrupted host lifecycle | 3 / 3 |
| Incomplete evaluator exit | 1 / 2 |
| Host qualification checks | 16 / 18 |

The existing Voyage scope, source-hash, replay and budget mutation checks also
detected **4/4** removed guards. Mutations never touched the working source.

## Reproduction and evidence

From the repository root, with the required optional dependencies installed:

```sh
.venv-code-rag/bin/python -m pytest -q \
  tests/test_voyage.py tests/test_code_rag.py tests/test_voyage_evaluation.py \
  tests/test_code_rag_host_check.py tests/test_voyage_integration.py \
  tests/test_documentation.py tests/test_review.py tests/test_grounded_review.py \
  tests/test_passage_review.py tests/test_recovery.py tests/test_extensions.py
.venv-mcp2-probe/bin/python -m pytest -q \
  tests/test_mcp.py tests/test_code_rag_host_check.py
.venv-code-rag/bin/python scripts/qualify_voyage_mutations.py \
  --output /absolute/new-mutation-results
```

Local raw evidence is retained under
[`docs/receipts/fix-sol-findings-20260916/`](receipts/fix-sol-findings-20260916/):
[before tests](receipts/fix-sol-findings-20260916/before-tests.xml),
[affected suite](receipts/fix-sol-findings-20260916/after-tests.xml),
[final evaluator cases](receipts/fix-sol-findings-20260916/final-evaluator-tests.xml),
[MCP 2 checks](receipts/fix-sol-findings-20260916/mcp2-tests.xml),
[mutation results](receipts/fix-sol-findings-20260916/mutations.json), and
[existing mutation results](receipts/fix-sol-findings-20260916/existing-voyage-mutations/mutations.json).
The directory also holds original file snapshots, the attributed fix diff and
final source/index preservation checks. These raw artifacts remain local and
ignored by Git under the existing evidence policy.

This receipt verifies source fixes and local fixtures. No new wheel installation,
remote platform qualification, live retrieval campaign or release was performed.
Earlier installed environments, wheels and frozen experiment receipts remain
preserved; they do not contain these fixes. At verification time, these fixes
and the pre-existing workspace changes were still uncommitted.
