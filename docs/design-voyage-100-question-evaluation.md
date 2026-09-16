# 100-question code retrieval evaluation

Status: authorized disposable experiment, 2026-09-15. No production changes.

## Outcome

Measure source retrieval across more Harness capabilities using 80 fresh answerable
questions and 20 missing-answer controls. Preserve the original 20-case experiment.
Reuse its current 98-file, 1,050-passage index without indexing or changing sources.

## Method

Record questions, expected answers, minimal supporting byte spans, and accepted
alternative evidence before any new provider request. Review requirements against
the question wording; do not require unrelated facts. All required criteria must
be covered, but any predeclared evidence alternative may satisfy a criterion.
Expected answers and experiment code stay outside the indexed scope.

Compare local BM25, hybrid retrieval, and the installed Voyage reranker using the
same query embedding and candidate pool. Primary measure is full required support
within five passages; secondary is support within ten. Report missing-answer
controls separately: returned candidates do not establish answer support.
No model-generated answers or coding outcomes are measured. Cases are authored
with source knowledge and clustered by topic, not a random independent sample.

## Execution and acceptance

Validate scoring locally, freeze all 100 cases and runner hashes, then make at
most 100 query embedding and 100 reranking calls. Use five independent 20-query
work directories to respect the existing immutable config's 40-call limit.
Use verified account limits from the earlier experiment. Estimated cost is $0.07,
based on its measured query usage; the estimate is not a billing ceiling.
Stop on unresolved provider effects, preserve durable receipts, and never retry
unknown paid work automatically. Verify source/index integrity before and after.

Done when all 100 cases have raw evidence, paired scores, per-category summaries,
usage/cost receipts, missing-answer results, and a written recommendation with
limitations. Any unresolved failure is reported explicitly. No automatic promotion.
