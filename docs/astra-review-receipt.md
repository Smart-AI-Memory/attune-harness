# Astra reviewer selection — dev8 receipt

September 15, 2026. **Dev8 configuration implemented and installed. The subsequently
authorized live test failed on a copied request digest.** See the [dev9 repair and
successful retest](native-evidence-review-receipt.md) for the current outcome.

Patrick requested changing the actual Harness reviewer to GPT-6 Astra at extra-high
reasoning, then confirmed the work. The [design](design-astra-review.md) preceded
the source changes. This increment changes explicit worker selection and establishes
its software behavior. It does not report a new semantic accuracy score.

## What changed

- Workspace [participants.json](../participants.json) selects `astra-lead` and
  `astra-reviewer`, both native Codex, `gpt-6-astra`, `reasoning_effort: xhigh`.
- The Codex adapter passes `--model gpt-6-astra` and
  `-c 'model_reasoning_effort="xhigh"'` on every configured native call.
- New `review-form` and `review` commands default to `./participants.json`.
  Explicit `--config` remains authoritative. Resume still requires its explicit,
  unchanged registry, accepted request and checkpoint.
- Reasoning effort is optional and Codex-only. Invalid values and use with another
  adapter are rejected. Omission preserves the prior invocation; the selected
  native provider can reject model-specific unsupported effort values.
- The request record retains requested model/effort and actual dispatch arguments.
  Current Codex JSONL does not attest server model/effort identity; no such identity
  is invented from the request or a model's self-report.

This uses the existing native action-review protocol, not the Ollama passage
contract. Historical Llama profiles and accepted runs remain preserved. An explicit
old config still selects its old model; a Codex app model change alone is not a
worker-profile change. There is no fallback to Llama or another provider.

## Validation

| Check | Result |
|---|---:|
| Full software suite | **780 passed** |
| Targeted native/review/recovery suite | **227 passed** |
| New behavioral cases | **22 passed** |
| Targeted mutations detected | **7/7** |
| New cases detecting at least one mutation | **13/22** |
| Installed review/recovery checks | **35 passed** |
| Installed default/explicit Astra form checks | **2 passed** |
| Installed source modules matching working source | **24/24** |

The behavioral journey checks all six native dispatch argument lists and their
retained metadata using an injected deterministic transport. It also proves that
changed effort invalidates acceptance and blocks paused continuation, invalid
selection fails, and old native invocations retain their behavior. These are
software checks, not frontier-model generations.

[Full suite](receipts/astra-review/full-tests.txt) ·
[Mutation evidence](receipts/astra-review/mutations/summary.json) ·
[Installed profile](receipts/astra-review/installed-profile.json) ·
[Installed review](receipts/astra-review/installed-review.json) ·
[Installed recovery](receipts/astra-review/installed-recovery.json)

## Installed artifact

Use `/Users/patrickroebuck/attune-harness/.venv-astra-review/bin/attune-harness`.
The new isolated environment was installed offline from the dev8 wheel and pinned
local review dependencies. No provider SDK or new credentials were installed.

Wheel: [attune_harness-0.1.0.dev8-py3-none-any.whl](../dist/attune_harness-0.1.0.dev8-py3-none-any.whl).
SHA-256: `e4fedc68ea7a76ae28d2fae63448859dadd248d75617c784a44825b764840c70`.
The rebuild is byte-identical. [Artifact identity](receipts/astra-review/artifact.json)
and [final preservation audit](receipts/astra-review/final-audit.json) retain the
installation/source checks and hashes of all 5,814 historical artifacts.

## Prepared live test and authorization history

One synthetic documentation review is prepared with the workspace Astra profile,
up to **six native invocations**, **300 seconds per turn**, no Harness retries and
no model fallback. It uses the existing Codex sign-in without reading or changing
credentials. It contains a deliberately incorrect worker-success acceptance rule
and an explicitly unmeasured possible cost benefit:

- [Document to review](receipts/astra-review/live-01/corpus/guide.md)
- [Reference policy](receipts/astra-review/live-01/corpus/reference.md)
- [Accepted request](receipts/astra-review/live-01/request.json)
- [Frozen test definition](receipts/astra-review/live-01/freeze.json)

Automatic approval review rejected the external execution: the reviewer switch
was authorized, but it required specific approval to send this payload to the
authenticated Codex/Astra destination with possible provider-side processing and
usage cost. The command never started. No indirect execution, credential workaround
or substitute provider was attempted. [Recorded block](receipts/astra-review/live-approval-block.json)

After explicit approval, the prepared command is:

```sh
.venv-astra-review/bin/python -I docs/receipts/astra-review/live-smoke.py --execute
```

Patrick subsequently instructed “build and test using the new astra configuration,”
resolving that approval block. Three dev8 native invocations ran: the lead requested
retrieval and verification, then supplied a substantively correct review with a
shortened response digest. The coordinator rejected it; the reviewer never ran.
[Failed result and retained raw calls](receipts/astra-review/live-01/summary.json)

The [dev9 evidence-mode repair](native-evidence-review-receipt.md) completed the same
scenario with two further calls. The earlier Llama-based **2/36** quality pass
result stays unchanged; a matched Astra benchmark and independent semantic grading
remain outstanding. The original approval-block JSON is historical evidence, not
a current pending permission request.
