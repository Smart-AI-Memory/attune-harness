# Application retrieval evaluation

Status: evaluation tooling and source-grounded questions prepared. A
[four-question live subset](../../docs/voyage-accuracy-receipt.md) completed on
September 15: three positive questions and one absent-answer control over the
five-file smoke index. The full campaign and matched application-change
experiment have not run.

`heldout.json` contains 48 questions about existing Harness source and 12 absent
feature controls. Questions cover 12 related symbol families; they are **not 60
independent application tasks**. `tuning.json` supplies four separate questions.
Expected symbols were selected from code before any live retrieval output.
Tests resolve every symbol against current source. Freeze the selected source
generation and oracle spans before tuning or running the campaign.

```sh
python -I experiments/voyage/evaluate.py freeze --config evaluation-config.json \
  --generation GENERATION --cases experiments/voyage/heldout.json --output heldout-run
python -I experiments/voyage/evaluate.py run --output heldout-run --allow-provider
```

Use repo ID `attune-harness` and explicitly include the Python source files named
in the questions. The freeze binds actual source hashes and byte spans to each
expected symbol. It refuses missing/ambiguous symbols. A campaign preserves
failed and unrun cases and refuses to overwrite results. Provider responses and
usage stay in the same durable retrieval receipts as production.

The CLI exits zero after a successful freeze (`frozen`) or complete run
(`completed`). An `incomplete` campaign exits 1 while still printing its JSON
report and saving `results.json` with failed and unrun cases. Treat that nonzero
exit as a failed campaign; inspect the report and stage receipts before deciding
on further work. The existing refusal to overwrite results still applies.

Compare passage BM25/identifier search, hybrid search, and hybrid plus standard
reranking with identical passages, scope and ten returned results. Query
embeddings are shared between hybrid variants, avoiding duplicate comparison
charges. The current Markdown-prefix keyword backend has no applicable gold
subset in this Python-symbol packet; measure it on a separate Markdown packet.

Metrics include symbol recall@5/10, reciprocal rank and nDCG@10 with duplicate
symbol appearances credited once. Symbol overlap is a discovery measure, not
proof that the returned passage answers the question. Absent-answer cases
report returned candidates separately. Voyage scores do not provide a qualified
abstention rule. Inspect exact returned bytes and judge answer support separately.
Do not aggregate only successful cases or claim uncertain costs are zero.

## Required product evaluation before promotion

The small Harness smoke checks provider compatibility. The packet above measures
internal developer-code discovery. To assess Attune's benefit for vibe
engineering, freeze real application feature/fix tasks and independent acceptance
tests, using the same agent/model, starting revision, time and token budgets:

1. Baseline: direct file reads, exact symbol/path lookup and targeted search.
2. Treatment: the same tools plus accepted Voyage retrieval.
3. Separate checkouts, blinded review of final patches and withheld regression
   checks where feasible. Preserve failed attempts and unsupported edits.
4. Report independently accepted changes, critical misses, regressions, total
   model/retrieval cost and time per accepted change. Keep exact structured
   check/triage/economics operations as zero-provider-call controls.

Do not recommend routine adoption from citation validity, vendor benchmarks, a
single smoke test or synthetic-provider tests. Tied, worse or inconclusive
results retain that disposition. A representative application corpus, coding
task oracle and separately authorized downstream model calls remain necessary
for this product comparison.
