# Full-code retrieval evaluation

September 15, 2026. Patrick approved the proposed 98-file Harness selection and
about 20 questions with expected answers recorded beforehand. This is a disposable
evaluation, with no production retrieval changes or model-generation calls.

## Frozen scope and cases

Select 35 source modules, 35 test files, 27 Python scripts and `pyproject.toml`.
Preserve the current dirty/untracked source snapshot explicitly, including hashes.
Prepare 20 natural-language questions: 17 answerable cases spanning selection,
retrieval, provider failure, host lifecycle, process supervision, native responses,
verification, economics, packaging and platform qualification; three absent-feature
controls. At least six questions require multiple evidence components, including
implementation-plus-test pairs. Freeze answers, required source byte spans and
scoring before any indexing or search. The expected answers never enter the index
or provider queries. These cases are author-selected with knowledge of the code;
they are not a blinded or statistically representative benchmark.

## Measurements and cases that must remain failures

Run identical questions over identical passages for local passage BM25, hybrid
dense/text retrieval, and hybrid plus Voyage reranking. Compare full required
evidence coverage at 5 and 10 results, component recall, first supporting rank,
source integrity, provider calls, latency and cost. Reuse each query embedding
for the hybrid baseline; do not buy another embedding for comparison. A matching
file or function name alone is insufficient: all frozen evidence fragments must
be covered. Missing-answer cases report unrelated candidates and explicit
abstention separately; never invent a score threshold after seeing their results.
No generated answers or generated-code quality are measured.

## Existing evidence and execution

The installed dev13 package passed 14 focused tests and a live Attune host query.
Local source planning resolves 98 files, 1,050 passages and 33 embedding requests,
with a bytes/4 indexing estimate of $0.02087898. The previous larger accuracy
sample was only three positive questions and one absent case over five files.
This campaign adds 20 query embeddings and 20 rerank requests, at most 73 new
provider calls in total, using the already configured Voyage key. Calls are
sequential and bounded; failures retain durable records and are not retried.
Provider rate-limit response headers, when supplied, guide pacing without changing
the account. Unknown paid effects stop the campaign. Previous artifacts remain
untouched. All runners and raw results live outside the 98 selected files.

## Rejected alternatives

- Repeating the successful smoke question alone cannot evaluate broader coverage.
- Indexing every repository artifact would include generated evidence and old
  experiments in the search target, contaminating the evaluation.
- Tuning the index, questions or success criteria after inspecting rankings would
  invalidate the comparison. Record misses and recommend subsequent changes instead.
