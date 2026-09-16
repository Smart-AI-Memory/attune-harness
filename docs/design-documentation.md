# Code-grounded documentation: first increment

Authorized scope: one Python module's API documentation, source references,
explicit claim checks, and source drift detection. No package retirement or
paid model execution is part of this increment.

The workflow owns an immutable snapshot of explicitly selected code and test
files. AST inspection derives top-level public function signatures and class
names without importing or executing project code. A deterministic author is
available by default. An injected author can supply structured claims; an
optional reviewer receives that same snapshot and draft, returning advisory
feedback. Reviewer agreement cannot change deterministic claim outcomes.

Supported claims are symbol existence and exact AST-normalized function
signatures. Behavioral prose remains unknown, including prose copied from
docstrings: source text and passing unrelated tests do not establish behavior.
Each claim carries a file and line interval, validated against the snapshot.
The rendered artifact has a JSON receipt containing claims, outcomes, source
hashes, and reviewer notes. A drift check compares the current selected files
with these hashes. Missing/changed files mean review is needed. This is selected
source drift, not transitive dependency tracking or proof of semantic accuracy.

Cases: real and invented symbols, wrong signatures, missing/out-of-range
citations, unsupported behavioral claims, a reviewer accepting an invalid claim,
changed/deleted sources, paths escaping the declared root, and malformed author
output. Tests exercise these boundaries with synthetic repositories; a local
example generates documentation for Harness's public API with no model calls.

Sequence: snapshot -> author -> deterministic checks -> optional reviewer ->
render and receipt. No retries, concurrent authors, generated-code execution,
or automatic publishing. A model team must justify its incremental quality and
cost against this single-author baseline before becoming a default.

Disposable AST probe: an async function with positional-only arguments,
keyword-only defaults, and a return annotation preserved these in `ast.unparse`
and supplied a 1..2 source interval. No project import was needed.

Rejected for now: restoring the full retired Author package, moving all legacy
checkers immediately, or claiming retrieval/citations guarantee accuracy. The
existing Voyage engine can select candidate files upstream; explicit full-file
snapshots keep this small increment usable offline and independent of a provider.
