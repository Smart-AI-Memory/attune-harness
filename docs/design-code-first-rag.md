# Code-first Attune RAG

September 15, 2026. Patrick approved repository-first retrieval: application
code, tests, schemas and configuration; repository documentation is optional.
This is the implementation note for the bounded integration, not authorization
to delete other packages' data or to publish a release.

## Cases and acceptance

1. A new `code-config` command selects supported source languages and tests,
   with Markdown only when requested. Structured files use explicit relative
   paths; they never implicitly include JSON receipts or runtime ledgers.
   Existing normalized configurations and immutable generations retain their
   digests. Reject traversal, symlinks and secret/environment directories.
2. New retrieval results declare byte-checked provenance separately from answer
   support. Candidates require source inspection; an empty selection declares
   insufficient evidence. No score threshold is invented from one negative case.
3. *Removed after 0.2.0; see D8 in the
   [spec authority addendum](specs/spec-authority/addendum-2026-09-21.md).*
   An optional Attune BasePlugin delegates to the same accepted RetrievalSession
   as Harness. Its own tool is `code_evidence_query`; paths and budgets are fixed
   by the launcher. Activation, actual host dispatch, reuse, disable/close,
   exhausted budgets and changed sources must be exercised. A failed paid
   operation cannot silently fall back to the old document collection.
4. CLI and installed-wheel tests run with real Git/LanceDB and deterministic
   injected providers. Existing live Voyage results establish provider
   compatibility only. A new installed Attune host invocation must preserve
   source IDs, hashes and usage, without changing its MCP SDK.

## Evidence before implementation

The current source selects Python and Markdown by default and excludes all JSON.
The existing live check retrieved code correctly for three positive questions;
its missing-answer control returned unrelated candidates. The key smoke test
passed both providers. Attune preflight passed 87 checks. Attune's plugin registry
supports explicit BasePlugin registration; its MCP server dispatches registered
plugin handlers. RetrievalSession itself does not import the MCP SDK: that import
is confined to the standalone server adapter. In-process reuse can therefore be
qualified without installing Harness's MCP extra into Attune's environment.

## Decisions

Keep one engine in Harness, expose it through an optional Attune plugin, and
qualify the in-process boundary before recommending it. Retain the separate
stdio server for other coding-agent hosts. Do not copy the engine into
attune-rag, change model-tier ownership, or reinterpret old accepted requests.
The legacy package's help/memory consumers remain until separately migrated.
Default semantic answer acceptance is rejected: correct source bytes do not
prove that a passage answers a question. A broader coding-quality evaluation
remains distinct from this implementation receipt.
