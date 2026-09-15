# Phase 6 local pilot — complete

2026-09-14. The supported local pilot is complete: clean installation, a real
attune-harness documentation review, checkpointed pause/resume, extension
upgrade/removal, failed-upgrade recovery, artifact rollback and package rollback.
[Machine-readable summary](receipts/phase6/summary.json),
[runnable journey](pilot-workflow.md), [migration decision](pilot-migration.md).
This qualifies an opt-in assisted workflow on the declared host. Native
multi-provider qualification and Patrick's preferred-path decision remain open.

## What ran

- **582 tests passed**, 1,835/1,966 statements covered (**93.34%**).
  [Suite](receipts/phase6/suite-dev3.txt), [coverage](receipts/phase6/coverage-dev3.json).
- **110 installed cases passed** across core, verification, retrieval, review,
  recovery, extensions, MCP and A2A. Every isolated profile's installed module
  hashes matched the wheel. The separate public Attune BasePlugin bridge also
  passed. [Qualification](receipts/phase6/qualification-dev3/summary.json).
- **2/2 eligible new tests fail** with the HTTP diagnostic handler removed in a
  disposable source copy. New-module tests are outside this mutation denominator.
  [Receipt](receipts/phase6/http-mutation.json).
- A **fresh offline install** reproduced the guide's dependency installation.
  All 47 dependency pins have compatible archived wheels and recorded hashes;
  four missing public wheels were downloaded from PyPI. An initial incompatible-
  cache selection failed and was corrected without relaxing pins.
  [Installation](receipts/phase6/clean-install-dev3.txt),
  [dependency artifacts](receipts/phase6/compatible-dependencies.json).
- The actual pilot passed **28 commands** with **two local model generations**.
  Both roles requested real retrieval and verification; the reviewer received no
  lead narrative. All 34 extracted claims and the complete document were supplied
  to both roles. The saved lead result survived pause/resume without another call.
  [Run](../.pilot/phase6-local-02/review/record.json),
  [audit](receipts/phase6/pilot-audit.json),
  [command/result summary](../.pilot/phase6-local-02/summary.json).
- **10 package rollback commands passed**: installed dev0, inspected the new
  completed record unchanged, completed the old deterministic review path with
  identical claim coverage, and restored dev3. All **58 original pilot files**
  remained byte-identical; no model call occurred during rollback.
  [Rollback receipt](receipts/phase6/rollback/summary.json).

The lifecycle pilot invoked the upgraded 0.1.1 retrieval tool, refused a changed
artifact for held work, restored the retained 0.1.0 bundle and resumed that work
without repeating completed events. An incompatible replacement preserved the
old disabled state. Removal blocked continuation and retained the user-data file.
The earlier installed recovery checks separately reran actual process-death,
ambiguous-effect, recovered-reply and writer-lock cases.

## Useful result and model limitation

The real document was `docs/e2-revision-receipt.md`, unchanged SHA256
`9bc74aadb3db44f6b510d1420fbe4ea5fa3963288f4ea16ced711adc4c8ee016`.
Strict verification found **9 verified, 0 refuted and 25 unknown** extracted
claims. The workflow correctly completed with an unknown document outcome and
exit 1. Missing truth sources for commands/counts remain visible; arbitrary
experimental claims and model prose are not certified by this verifier.

The lead narrative nevertheless mentioned refuted claims and framed general
availability prediction as a goal. Both assertions are unsupported by the supplied
evidence and the explicit narrowed contract. The reviewer more accurately described
the revision. These observations reinforce the E3 result: keep model narratives
as proposals for inspection and keep collaboration choices explicit. Successful
execution is not evidence of adequate unattended review quality.

Generation usage: lead 4,392 input / 122 output tokens, 15.942 model-reported
seconds; reviewer 4,392 / 131 tokens, 4.368 seconds. Both use the same model weights
with different seeds and identical evidence prompts. This is role isolation,
not diverse-model qualification. Human repair effort and comparative usability
remain unmeasured. No paid API or credential operation occurred.

## Retained failure and correction

The first live dev2 attempt returned HTTP 400 before producing a narrative.
A disposable prompt reproduced the server's grammar-parser failure. Removing the
schema's maxLength 3000 constraint made a second disposable probe succeed. Dev3
uses the simpler grammar while still enforcing the 3,000-character result bound,
512-token ceiling and prompt budget. The HTTP client now preserves bounded error
bodies. [Design and probe evidence](design-phase6-grammar-fix.md).

The failed run, dev2 wheel, both diagnostic requests, initial 580-test/110-case
qualification and passing final dev3 qualification remain retained. There was
one rejected request in the original pilot and one rejected diagnostic request;
the successful diagnostic and two final pilot calls are separate from E3's 480
calls. No failed event was silently resumed or discarded. The earlier 28-command
rehearsal was explicitly simulated and is not counted as live inference.

## Artifact and support boundary

Final wheel: `dist/attune_harness-0.1.0.dev3-py3-none-any.whl`  
SHA256: `1005160c7bd0c0063a8bb3db2d09f5b9079201cca75144b48073609b55fa4b74`.
The rebuild is byte-identical. [Artifact](receipts/phase6/artifact-dev3.json).
Dev0, dev1 and dev2 wheels remain preserved. Core requirements remain empty;
Attune forms 0.17.0, rag 1.2.0 and verify 0.6.0 are optional pinned integrations.

Qualified host: **macOS 26.6.2, arm64, Python 3.10.11**, local POSIX storage.
Ollama 0.31.1 / `llama3.1:8b` uses the exact model digest and settings documented
in the journey. MCP 2.2.0 retains local stdio receipts for 2025-11-25 and 2026-07-28,
including the preserved 1.29.1 client; A2A 1.0 retains its bounded local JSONRPC
receipts. Base attune-ai and its MCP 1.29.1 environment were not upgraded.

Windows/Linux, native Claude/Codex review, remote authentication, cross-machine
continuation and general model reliability are unqualified. M1 is an assisted
trial operated by Codex on Patrick's selected workflow; M2 preference is not
assumed. The old data/configuration and runtime remain available. No publishing,
global default change, public-interface removal or attune-ai retirement occurred.
