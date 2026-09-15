# Configurable output budget — 2026-09-14

Implemented in **0.1.0.dev4**: the local review peer no longer imposes a
3,000-character cap or a fixed word count. `--max-output-tokens` selects the
output-token ceiling in an accepted participant command or the pilot launcher.
The default remains 512. The existing transport allows **32,768 UTF-8 bytes** of
final narrative, including the unverified-proposal label, and 65,536 bytes for
the serialized JSON response. The peer now checks that transport before saving
a successful receipt. It retains failures and raw generations, without clipping
or automatic retries. [Design and actual before-code probe](design-output-budget-increment.md).

Generation options are copied per invocation and saved with the exact request.
The client replaces its old 1,024-token output ceiling with a context budget:
prompt/system UTF-8 bytes + output tokens + 512 framing tokens must fit the
selected context, at most 16,384. This is a conservative estimate, not an exact
tokenizer. Invalid scalar budgets fail before setup; oversized inputs fail before
model access. Changing a paused workflow's accepted budget requires a new run.

## Test evidence

| Check | Observed result |
|---|---|
| Complete suite | **615 passed**, including 33 new output-budget cases; 1,862/1,979 statements covered (**94.09%**). |
| Longer-response fixture | A 4,160-character / 480-word review survives unchanged. Installed dev3 rejected the same text. |
| Narrative boundary | Exact 32,768-byte ASCII and emoji narratives pass; one additional byte fails, including label overhead. |
| JSON transport | Escaping that exceeds 65,536 wire bytes fails even when narrative bytes fit; raw evidence remains available. |
| Configuration | Default 512 and custom 1,024/2,048 budgets reach generation and receipts independently; invalid budgets do not dispatch. |
| Context and exhaustion | Exact context boundary passes; an additional input byte fails before access. Token-exhausted output is retained as failed even when it contains parseable JSON. |
| Acceptance | Changing the accepted command's budget cannot resume saved work or reach dispatch. |
| Installed artifact | **110 checks pass** across core, evidence tools, review/recovery, extensions, MCP and A2A; the separate public Attune bridge also passes. |
| Targeted mutations | **9/9 deliberately introduced regressions detected** in disposable source copies. **28/33 new cases fail under at least one relevant mutation.** This is a targeted check, not an exhaustive mutation score. |

Raw evidence: [suite](receipts/output-budget/suite.txt),
[coverage](receipts/output-budget/coverage.json),
[installed qualification](receipts/output-budget/qualification/summary.json),
[mutation cases and commands](receipts/output-budget/mutations/summary.json).
The five cases unaffected by the selected mutations still pass normally; the
9/9 result does not mean every new test independently detects every missing guard.

## Actual local trials

Two disposable probes ran the installed wheel outside the source tree against
the already installed, pinned `llama3.1:8b` on Ollama 0.31.1:

- **2,048-token ceiling:** completed normally and passed the transport decoder.
  The model chose **54 generated tokens, 291 review characters and 41 words**,
  despite the fixture asking for a long review. This proves end-to-end budget
  forwarding, **not live generation beyond 3,000 characters**. The longer-response
  evidence above is deterministic. A ceiling cannot force a model's answer length.
- **8-token ceiling:** stopped at exactly 8 tokens with `done_reason=length`.
  The peer retained the failed generation and returned failure without retrying.

[Live commands, sizes and outcomes](receipts/output-budget/live/summary.json)
link to the exact requests, raw output and generation receipts. These are
fictional test inputs, not verified project findings.

The existing real documentation pilot also passes on dev4: **28 commands**, two
independent local generations, pause/inspect/resume, completion replay, extension
upgrade rejection/replacement/removal and artifact rollback. It preserves the
document hash `9bc74aadb3db44f6b510d1420fbe4ea5fa3963288f4ea16ced711adc4c8ee016`
and **9 verified, 0 refuted, 25 unknown** claims. The accepted 512-token budget
appears in both commands and generation receipts. Saved input/system size is
15,338 bytes; a 2,048-token ceiling would exceed the conservative context budget
for this particular document. Use a smaller scoped input for that larger ceiling.
See [pilot summary](receipts/output-budget/pilot-output.txt) and the full local
run in `.pilot/output-budget-dev4`. Later documentation edits do not change this
completed historical record. Narratives remain unverified proposals.

Total for this increment: **four local generations, zero paid API calls**, no
downloads or credential operations. No new native-provider/platform or model
reliability qualification is claimed.

## Artifact and reproduction

Wheel: `dist/attune_harness-0.1.0.dev4-py3-none-any.whl`.
SHA256: `89c37766c4b9f577e668dd09b331c1fce7f6834aec11451aac2a923445ec941a`.
Its rebuild is byte-identical, and all 21 installed production modules match the
wheel and source. Dev0 through dev3 wheel hashes are unchanged; frozen research
environments and archived E3 sources are retained.
[Artifact identity](receipts/output-budget/artifact.json).

From the checkout, deterministic tests make no model calls:

```sh
.venv-mcp2-probe/bin/python -m pytest tests/test_output_budget.py -q
.venv-mcp2-probe/bin/python -m pytest -q
python3 scripts/check_output_budget_mutations.py --python .venv-mcp2-probe/bin/python --output /private/tmp/harness-budget-mutations-new
```

The optional live reproduction makes exactly two local generation requests;
choose a fresh output directory and use the installed dev4 environment:

```sh
python3 scripts/check_output_budget_live.py --python .venv-output-budget/bin/python --work-dir /private/tmp/harness-budget-live-new --local-model
```

Local output can vary; the script records whether it exceeded the old cap rather
than requiring or retrying until that occurs. The normal
[pilot guide](pilot-workflow.md) describes installation and per-workflow settings.
