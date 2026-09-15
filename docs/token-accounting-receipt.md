# Model-aware token accounting — 2026-09-14

**Implemented and qualified locally in 0.1.0.dev5.** The real documentation pilot
now completes with its full input and **2,048 output tokens reserved**, using
the installed model's vocabulary and the qualified prompt template. Each input
was **4,386 tokens**, matching Ollama's reported count exactly. With a 512-token
margin, **9,438 tokens remain** in the 16,384-token context. The former byte
estimate was 15,338 and would reject this output budget.

This is a larger permitted output budget, not a guaranteed answer length. The
two pilot narratives used 67 and 69 generated tokens. Their prose remains
unverified. The document retains **9 verified, 0 refuted and 25 unknown** claims;
the original E2 receipt's SHA256 remains
`9bc74aadb3db44f6b510d1420fbe4ea5fa3963288f4ea16ced711adc4c8ee016`.

## Changes and boundaries

- Optional `attune-harness[tokens]` uses **tiktoken 0.12.0 locally**, with explicit
  vocabulary data. It performs no provider calls or implicit downloads. The
  portable core and ordinary review extra remain independent of this dependency.
- `python -m attune_harness.llama_tokens --output NEW_FILE` exports metadata from
  the already-installed model. `--tokenizer-file` selects it in an accepted peer
  or pilot command. The loader checks an exact profile hash and model/server pin.
- Counting covers the complete text-only system/user/assistant template and BOS,
  then reserves the requested output tokens plus the existing 512-token margin.
  No evidence is omitted or rewritten to fit. The server is explicitly told not
  to truncate input or shift context.
- Every generation receipt records counting mode, profile identity, input count
  or estimate, output reservation and remaining capacity. A rejected context
  budget retains this accounting before any model request.
- If no tokenizer is selected, the prior byte estimate remains available and is
  labeled `conservative_utf8_bytes`. A selected tokenizer never silently falls
  back: missing dependencies, corrupt profiles or unsupported pins fail visibly.
- A server input count that disagrees with the qualified tokenizer is a failed
  invocation with raw output retained and no automatic retry. Reported input
  counts may not consume the reserved output capacity even in byte mode.
- Existing **32,768-byte UTF-8 narrative** and **65,536-byte JSON response** limits
  are unchanged. The unverified-proposal label counts toward narrative size.

Qualification is deliberately narrow: local macOS arm64/Python 3.10.11,
`llama3.1:8b`, model digest
`46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`,
Ollama **0.31.1**, and the exact exported vocabulary/template. Another model,
template, server or tokenizer version needs its own qualification. This does
not establish native Claude/Codex support, broad tokenizer portability or model
reliability. No global configuration or preferred-path decision was changed.

## Evidence

| Check | Result |
|---|---|
| Full suite | **654 passed**, including **39 new cases**; **94.36%** statement coverage (1,959/2,076). |
| Model-count regression fixtures | Seven retained server-reported counts match offline, including Unicode, code, whitespace, an empty system message, NUL and special markers. |
| Boundaries | Exact input-token capacity passes; one extra token fails before model access. Invalid reserves/counts, oversized metadata/profile/input and wrong identity fail explicitly. |
| Failure evidence | Count drift, unavailable tokenizer and context rejection retain failures/accounting without retry or silent byte fallback. |
| Targeted mutations | **11/11 introduced regressions detected; 31/39 new cases fail under at least one relevant mutation.** Disposable copies only; this is not an exhaustive mutation score. |
| Installed regression | **110 checks pass** across core, feature tools, review/recovery, extensions, MCP and A2A, plus the separate public Attune bridge. |
| Installed tokenizer | Three additional checks pass: core has no tokenizer dependency; explicit selection without the extra fails before setup; installed token counting matches all seven retained cases offline. |
| Real documentation pilot | **28 commands pass**, including two independent generations, pause/inspect/resume, completion replay and extension upgrade/removal/rollback. |
| Fresh count calibration | Unicode/code case **87 local = 87 server tokens**; empty-system/special-marker case **41 = 41**. Both complete normally. |

Raw receipts: [suite](receipts/token-accounting/suite.txt),
[coverage](receipts/token-accounting/coverage.json),
[targeted mutations](receipts/token-accounting/mutations/summary.json),
[installed qualification](receipts/token-accounting/qualification/summary.json),
[installed tokenizer checks](receipts/token-accounting/installed-token-checks.json),
[pilot commands and outcomes](receipts/token-accounting/pilot-output.txt), and
[fresh calibration](receipts/token-accounting/live-counts/summary.json).
The complete pilot, prompts and generations remain in `.pilot/token-accounting-dev5`.
Its completed record is historical evidence; subsequent documentation edits can
change corpus hashes and therefore small details of the next prompt's count.

The pre-code offline probe counted **4,383 tokens** in the older dev4 prompt,
exactly matching that run. The dev5 prompt's corpus digest and document count
differ, accounting for the changed token count without changing the reviewed
document's bytes. The initial scratch
ID-prefix comparison was false because the returned context omits the automatic
BOS; that raw exploratory result was retained rather than called a passing ID
comparison. The qualification checks server input **counts** directly.
[Design and scratch evidence](design-token-accounting-increment.md).

Total new inference: **four local generations; zero paid API calls**. Metadata
exports and offline counting make no generation calls. Seven pinned tokenizer
dependency wheels were downloaded for the clean isolated installation; **no
model was downloaded**. No credentials or frozen research environments changed.

## Artifact and use

Wheel: `dist/attune_harness-0.1.0.dev5-py3-none-any.whl`.
SHA256: `26826256205bd21300d7cf66bb2c7fce7b047d6570c5b1a38476ca69448b477c`.
Its rebuild is byte-identical. All **22** installed production modules match
the wheel and source; dev0 through dev4 wheel hashes remain unchanged.
[Artifact identity](receipts/token-accounting/artifact.json).

The tokenizer profile is exported data, not a bundled model dependency. Its
qualified SHA256 is
`73892438d8a0c3e3ac85d94d5c77f57beda339f2a9c4e1129ff68faa742af01f`.
The [dependency manifest](receipts/token-accounting/token-dependencies.json)
records pinned wheels and hashes; `requirements-tokens.lock` pins their versions.

The updated [pilot guide](pilot-workflow.md) includes installation, export and a
2,048-token workflow command. Existing environments/runs remain preserved.
Reproduce tests without generation:

```sh
.venv-token-accounting/bin/python -m pytest tests/test_token_accounting.py tests/test_output_budget.py -q
.venv-token-accounting/bin/python -m pytest -q
python3 scripts/check_token_accounting_mutations.py --python .venv-token-accounting/bin/python --output /private/tmp/harness-token-mutations-new
```

The optional live count calibration makes exactly two local generation requests
and requires a fresh output directory:

```sh
.venv-token-accounting/bin/python -I scripts/check_token_counts_live.py --tokenizer-file docs/receipts/token-accounting/exported-tokenizer.json --work-dir /private/tmp/harness-token-counts-new --local-model
```

The implementation was checked against [Ollama v0.31.1 generation and rendering](https://github.com/ollama/ollama/blob/v0.31.1/server/routes.go)
and [Meta's Llama tokenizer reference](https://github.com/meta-llama/llama3/blob/main/llama/tokenizer.py).
The actual local receipts above establish support for the selected artifact;
source inspection alone is not a compatibility claim.
