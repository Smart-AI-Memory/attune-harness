# Local documentation-review pilot

This opt-in workflow reviews `docs/e2-revision-receipt.md` in attune-harness.
It uses real Attune forms, keyword retrieval, strict document verification and
an explicitly selected local Ollama model for two independent narratives. The
narratives are unverified proposals. A completed workflow can correctly return
**unknown** when the document contains claims the verifier cannot establish.

Supported pilot profile: macOS arm64, Python 3.10.11, local POSIX storage, Ollama
0.31.1 and the already-installed `llama3.1:8b` artifact with digest
`46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e`.
Other operating systems, remote services and native Claude/Codex review journeys
are not qualified by this pilot. Nothing downloads a model or selects a paid
provider automatically. Model/server changes require a newly accepted profile
and fresh qualification; editing the pin alone is not that qualification.

## Install and run

From the attune-harness checkout, create a new environment:

```sh
python3 -m venv .venv-token-accounting
.venv-token-accounting/bin/python -m pip --isolated install --no-index --find-links dist/pilot-dependencies --find-links dist/token-dependencies -c requirements-workflow.lock -c requirements-tokens.lock 'dist/attune_harness-0.1.0.dev5-py3-none-any.whl[review,tokens]'
.venv-token-accounting/bin/python -m pip --isolated install --no-index --no-deps dist/dependencies/attune_harness_evidence_example-0.1.0-py3-none-any.whl
.venv-token-accounting/bin/python -m pip check
mkdir -p .pilot
.venv-token-accounting/bin/python -I -m attune_harness.llama_tokens --output .pilot/llama3.1-tokenizer.json
python3 scripts/pilot_review.py --python .venv-token-accounting/bin/python --work-dir .pilot/my-doc-review --max-output-tokens 2048 --tokenizer-file .pilot/llama3.1-tokenizer.json --local-model
```

The existing Ollama server must be running on literal loopback port 11434 with
that model. The peer disables proxies and redirects and checks the server and
model artifact before and after each generation. The CLI flag explicitly selects
two local generations with fixed seeds, temperature 0.2, context 16,384 and an
default output ceiling of 512 tokens each. The command above explicitly selects
2,048 output tokens and the qualified local tokenizer. Each generation records
its selected budget and counting mode. The tokenizer export reads metadata from
the existing local model; it neither downloads a model nor generates text. Use a
new profile output path; existing files are not overwritten.

`--tokenizer-file` uses the model's own vocabulary with local tiktoken 0.12.0 and
the qualified prompt template. It makes no provider calls. The current profile
is qualified only for the model digest/server version stated above. A missing
extra, changed file or different model fails visibly. Omitting the flag selects
the labeled conservative UTF-8 byte estimate; no automatic fallback occurs if an
explicitly selected tokenizer fails. For separate lead/reviewer budgets, include
`--max-output-tokens` in each accepted participant command profile.

The measured dev5 full-document pilot used 4,386 model tokens. Reserving 2,048 output
tokens and a 512-token margin leaves 9,438 of its 16,384 context tokens free.
Input-count differences from retained older runs can reflect changed corpus
metadata in the evidence envelope. The peer checks the server's reported count
against its local count after every generation and rejects disagreement. Server
truncation and context shifting are explicitly disabled.

Without the tokenizer, this input is still conservatively estimated at 15,338
bytes and fits only a small output budget (the 512-token default passes). Use the
qualified tokenizer for the larger budget; do not bypass the context guard.
A token budget is a ceiling, not a requested response length.

Dev4 removed the 3,000-character cap and fixed word-count instruction; dev5 keeps
those changes. Final narrative remains bounded at 32,768 UTF-8 bytes, including
the unverified-proposal label, with 65,536 bytes for its serialized JSON command
response. Nothing silently clips an input or output. A changed accepted command
profile requires a new run; the existing command timeout still applies.

See the [token-accounting receipt](token-accounting-receipt.md) and
[earlier output-boundary tests](output-budget-receipt.md) for the actual evidence.

The script creates its directory exclusively, accepts the selected request,
runs the lead's retrieval/verification and narrative, pauses, inspects the durable
checkpoint and resumes the independent reviewer. It checks that completed events
and accepted inputs survived unchanged, then replays completion without generating
again. The rest of the script rehearses extension upgrade/removal/rollback with
deterministic participants and actual feature calls. It expects the frozen E2
receipt's 9 verified, 0 refuted and 25 unknown claims; a changed document requires
reviewing and updating that pilot expectation explicitly.

Outputs stay under the selected work directory:

- `review/record.json`: accepted request, full native evidence, both narratives,
  checkpoint and completed operations.
- `first-result.json`: the lead result before the explicit pause/resume.
- `generations/*/record.json`: exact model prompts, pins, raw replies and usage.
- `commands/*.json`: actual commands, exits, timings and responses.
- `summary.json`: observed pilot outcomes and ownership limitations.

Inspect without any model calls:

```sh
.venv-token-accounting/bin/python -I -m attune_harness inspect-review .pilot/my-doc-review/review
```

Exit 1 for this completed review means the evidence is incomplete, not that the
process crashed. Inspect the structured coverage and claims. The verifier checks
its supported extracted claims; it does not certify the numerical experimental
results or arbitrary prose. The model receives the complete document, all claim
subjects/statuses/locations and retrieved excerpts, with full tool evidence kept
in the record. Oversized input fails before inference instead of being silently
cut down. The reviewer sees its own tool history and no lead narrative.

## Recovery and diagnostics

For a manually paused run, inspect first and use its current checkpoint:

```sh
attune-harness resume-review RUN --request REQUEST --config CONFIG --checkpoint DIGEST --allow-external
```

Keep the original paths, accepted registry and document/corpus bytes. A completed
run is historical evidence. A changed corpus, extension artifact or stale digest
cannot be silently accepted during continuation. An uncertain model command is
not retried automatically: inspect its saved generation and coordinator event,
then use the bounded [reconciliation procedure](recovery-workflow.md). Do not
remove a generation receipt to force another call. A duplicate receipt is an
explicit stop, not a cached answer for a new invocation.

| Symptom | Action |
|---|---|
| `unavailable` dependency | Check the pinned installation with `pip check`; use the matching extra in the isolated environment. |
| Model/server pin mismatch | Preserve the run; restore the accepted local artifact/server or qualify a new profile for a new run. |
| Prompt/context budget exceeded | Start a new accepted review with a smaller document or lower output-token ceiling; retain the rejected run. |
| Tokenizer/profile unavailable or count mismatch | Keep the failed record; restore the exact qualified profile and dependency or accept a new byte-budget workflow. No silent fallback or retry. |
| Generation truncated, malformed or timed out | Inspect the raw generation receipt and pending event; no automatic retry or fallback. |
| Stale checkpoint or busy writer | Inspect the latest record and actual owner; do not edit hashes or remove the lock file. |
| Extension disabled/changed/removed | Restore the exact retained bundle where supported, or accept a new request in a new run. |
| `unknown` document claims | Examine their locations and missing truth sources; do not mark them verified to get exit 0. |

## Extension upgrade and rollback

Keep the original bundle in place. Disable its registration, inspect, replace
with the new manifest using the latest `state_digest`, then enable. Accept a new
registry binding for the changed artifact before new work. A rejected replacement
leaves the old disabled state intact; re-enable that original state. To roll back
an accepted upgrade, disable, replace with the retained original manifest and
enable again. Held work can resume only when its original binding/input snapshot
matches. The pilot checks all these transitions and invokes the upgraded tool.

Removal leaves a tombstone and preserves user data. It blocks a paused run's
next dispatch. A removed registration cannot be re-enabled; install into a new
state directory and accept a new request. Do not edit the old state to resurrect it.

## Package rollback and migration

Keep dev0 through dev5 wheels separately. The pilot does not alter the base
Python environment or attune-ai. To roll back an isolated review environment:

```sh
.venv-token-accounting/bin/python -m pip --isolated install --no-index --no-deps --force-reinstall dist/attune_harness-0.1.0.dev0-py3-none-any.whl
.venv-token-accounting/bin/python -I -m attune_harness inspect-review .pilot/my-doc-review/review
```

Dev0 can inspect the saved review; it does not contain the new Ollama peer. Use
the previous deterministic/native command configuration only under its own
qualification and authorization, or reinstall the retained dev5 wheel. Preserve
unfinished model runs and restore their matching artifact before continuation.
No record conversion, shared-state dual writing, global configuration switch or
attune-ai retirement is part of this pilot.

Patrick owns the migration decision. Codex operates this first pilot on his
selected real workflow. This establishes an assisted trial, not evidence that
Patrick personally operated it or prefers it. Subsequent workflows move one at a
time with their own skills, data access and recovery receipts. The migration
report records which steps are complete and which decisions remain open.
