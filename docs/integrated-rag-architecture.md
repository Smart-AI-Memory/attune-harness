# ADR — Integrated RAG owned by Attune Harness

**Status:** Repository-first direction accepted; optional plugin implemented in dev13
**Date:** September 15, 2026
**Decider:** Patrick Roebuck

## Context

Patrick wants the new Voyage retrieval capability to run as part of
attune-harness and potentially attune-ai, replacing the older retrieval path.
The implementation already lives in Harness; it is not an implementation inside
the separately published `attune-rag` package.

### Verified installation identity

| Environment inspected | Installed packages | Current routing |
|---|---|---|
| `attune-harness/.venv-voyage` | Harness `0.1.0.dev12`, Voyage SDK `0.5.0`, LanceDB `0.38.0`, MCP `2.2.0`, attune-rag `1.2.0` | The live accuracy runner explicitly used this Python and Harness's Voyage backend |
| Default `attune` / `attune-rag` commands in the inspection shell | pyenv Python `3.10.11`; attune-ai `16.4.0`, attune-rag `1.2.0`, MCP `1.29.1`; Harness absent | Existing attune-ai consumers use the older attune-rag APIs |
| `attune-ai/.venv` | Editable attune-ai `16.4.0`, attune-rag `1.2.0`, MCP `1.29.1`; Harness absent | Development checkout; no Voyage adapter installed |

All 34 Harness Python files in `.venv-voyage` match the source and the dev12
wheel, SHA-256 `5c8e9b697bd8b0393b278fcadba9d91a6c14cc50a3b768bed1c53d3c6ac41e4c`.
The [accuracy run](voyage-accuracy-receipt.md) completed eight live Voyage calls.
The presence of attune-rag in that environment does not mean it served those
requests: the runner calls `retrieve_voyage`, and the stage receipts identify
the embedding and rerank operations.

The installed default CLI's RAG handler, code-generation workflow and model-tier
module match the corresponding attune-ai checkout files. Its plugin registry
differs only in type-import/annotation changes; the built-in discovery behavior
is the same. The cached Codex plugin declares `uvx --from attune-ai` with
`python -m attune.mcp.server`; this does not pin a package version. Inspection did
not identify a matching running interpreter, so the live connector's installed
version is **not established by the default CLI check**.

## Decision proposed

**September 15 update:** Patrick selected code as the primary collection, with
tests and explicit schema/configuration files and optional repository docs.
Dev13 implements that selection and an explicit Attune BasePlugin using the
same RetrievalSession. A real Attune MCP discovery/call/shutdown check passed
without changing the host's MCP 1.29.1: the session logic does not import the
standalone MCP 2.2.0 adapter. This qualifies the in-process alternative below
for that installed host, and supersedes the initial recommendation to require
a separate stdio process between the two packages. Full legacy-workflow
replacement and semantic answer-quality promotion remain separate work.
See [code-first usage](code-first-rag.md) and [receipt](code-first-rag-receipt.md).

Keep one retrieval implementation in **attune-harness**, presented to users as
an integrated RAG capability. Keep Voyage/LanceDB optional. Expose a stable
public interface around the existing accepted-scope/session behavior and add a
small attune-ai adapter that calls it. Do not create another implementation with
the same `attune_rag` import name.

Use an explicit, pinned Harness interpreter over stdio MCP for the initial
attune-ai integration. The two MCP SDK versions remain in separate environments.
An in-process Python adapter remains an option after dependency compatibility
and lifecycle semantics have been qualified. Harness must not depend on
attune-ai; dependency direction stays from the host adapter to Harness.

## Options considered

| Option | Complexity | Cost implications | Trade-off |
|---|---|---|---|
| **Harness module + thin host adapter — recommended** | Moderate integration work | Reuses the current index and provider implementation; adapter adds no provider calls itself | Shared behavior; host adapter and session lifecycle still need implementation |
| Evolve the standalone attune-rag library to own Voyage | Larger extraction/migration | Same provider rates; additional compatibility work | Preserves independent library distribution, but moves the already-tested implementation and its durable-stage contracts |
| Copy the implementation into each host | Easy initially, expensive to maintain | Separate caches/routing can cause duplicate work | Fixes, evidence rules and budget handling can diverge |

The strongest argument for retaining a standalone shared library is that RAG
could be useful independently of Harness. That is a valid future extraction if
independent consumers justify it; the current goal favors integrated ownership.

## Code-grounded migration constraints

1. Harness's base install includes attune-rag since 0.4.0 (before that, its `[rag]`, `[review]` and `[mcp]` extras did).
   Extension activation also checks its exact version unconditionally.
   Installing `[voyage]` does not remove those legacy dependencies. Make that
   boundary backend-aware before claiming a standalone Voyage-only plugin.
2. The existing `examples/extensions/attune_bridge.py` forwards to the legacy
   `retrieve_sources` function. It is an example, not the new Voyage integration.
3. attune-ai's `rag_knowledge_query` and `rag-code-gen` construct `RagPipeline`.
   The returned augmented prompts, citations and confidence fields differ from
   Harness's source-byte evidence reports; an explicit adapter is required.
4. attune-ai also imports attune-rag for lessons, personal memory, help data,
   faithfulness evaluation and model-tier settings. Removing the dependency
   immediately would affect more than application-code retrieval. Do not turn
   existing local memory/help operations into uploads as part of this migration.
5. attune-ai has explicit plugin registration and built-in discovery. A new
   package entry point alone will not activate an external plugin. Qualify its
   host registration, tool invocation, disabling and error behavior.
6. The live accuracy check is small and exposed missing-answer handling. Preserve
   local keyword behavior until representative replacement tests support each
   migration. Existing help-corpus thresholds cannot be applied to Voyage scores.

## Action items and acceptance

1. [ ] Make the Harness retrieval boundary backend-aware while preserving old
   accepted requests, frozen receipts and no-implicit-retry behavior. Verify the
   Voyage-only path without attune-rag installed.
2. [ ] Add and test explicit attune-ai adapter registration using a pinned Harness
   environment. A real host invocation must return the same source IDs/bytes and
   usage receipt; activation alone is not acceptance.
3. [ ] Preserve corpus selection, provider authorization, finite budgets,
   cancellation and per-run reuse. Report missing answers and provider failures
   explicitly. Shared installation does not imply shared query caches across runs.
4. [ ] Evaluate representative application questions and absent-answer cases,
   followed by matched coding tasks, before switching the normal coding route.
5. [ ] Inventory and migrate remaining old-package consumers, including ownership
   of model-tier settings. Deprecate/remove the old dependency only after their
   import, behavioral and corpus-specific checks pass.

## Verification performed for this proposal

Read actual source and installed distribution metadata; compared selected
attune-ai consumer modules and all Harness wheel modules. The attune-ai preflight
passed its 87 governance checks using its existing `.venv`, preserving its one
unrelated untracked snapshot. The first system-Python preflight could not import
attune; changing to the project's interpreter resolved that test-environment
issue. No installation, provider request, host configuration change or migration
was performed during this architecture review.
