# Local review of Spec evidence handoff

Bounded advisory lane requested by Attune AI AGENTS.md's different-model review
rule for acceptance controls. Receipt types: evidence-chain and suite. No native
CLI/provider trial, remote tools, dependency installation or production edits.

Read `docs/design-spec-test-handoff.md`, the existing memory journey report and
current Git state. Review `src/attune_harness/spec_handoff.py` and the incremental
AI change in `/Users/patrickroebuck/attune-ai-memory-adoption/src/attune/spec/workspace.py`
against `/private/tmp/attune-spec-handoff-edit/workspace.py.before`. Both repos
contain unrelated preexisting dirty work. Do not change implementation files.

Look for false acceptance, missing freshness/identity checks, lost redo/risk
controls, malformed input, failure severity, persistence/resume regressions and
claims beyond the cooperating-owner boundary. The primary agent is adding real
boundary tests and isolated installed qualification in parallel. Reproduce concrete
findings locally when possible; distinguish demonstrated defects from suggestions.

Write findings and exact reproduction commands to
`docs/receipts/spec-test-handoff-2026-09-17/independent-review.md` and send its path.
Do not launch additional agents. Changes may be refined during review; re-read
the touched files before the final receipt. The primary agent will rerun evidence.

## Follow-up scope

The 24 boundary tests now pass. Review the related `test_scope.py` correction:
Git diff was refreshing the index during nominally read-only capture. The wrapper
now disables optional locks and diff.autoRefreshIndex. Freshness compares all
snapshot fields except the derived changed_paths selection hint, which can retain
stat-only dirt after identical bytes are restored. Review the new regression
tests in `tests/test_spec_handoff.py`, particularly content restoration and index
preservation. Inspect for any weakened source, index, config or producer binding.
Append a bounded follow-up disposition to the same review receipt. Use source
Harness plus source AI adoption on PYTHONPATH with the integrated Python runtime;
do not select zero tests or launch native trials. Implementation is otherwise
stable; the primary agent is formatting and preparing installed qualification.
