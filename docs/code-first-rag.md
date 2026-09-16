# Attune RAG anchored in repository code

Dev13 provides a repository-first entry point to the Voyage implementation in
Harness. A separately maintained document collection is not required. Index the
application being built; index Harness/Attune sources when asking about them.

## Select code, tests and configuration

```sh
attune-harness code-config --repo /absolute/path/to/application \
  --repo-id application --index-dir /absolute/path/to/index \
  --structured-path pyproject.toml \
  --structured-path schemas/settings.json > retrieval-config.json
attune-harness index plan --config retrieval-config.json
```

The generated selection covers supported code extensions, including tests.
Add `--include-docs` for repository Markdown. Repeat `--structured-path` for
specific JSON, TOML, YAML, INI, CFG, XML or Go module files. These must be exact
repository-relative paths, not globs. JSON receipts and state ledgers are not
automatically included. Explicit exclusions also apply to structured files.
Environment files/directories remain excluded, and source symlinks are rejected.

Inspect the plan's exact files, hashes and estimated cost. Selected dirty files
require `allow_overlays: true`; selected untracked files independently require
`allow_untracked: true`. The defaults refuse both. Structured text is contextual
evidence; actual schema validation, field lookups and status decisions remain
deterministic operations.

Load your local key in the shell that will run Harness:

```sh
set -a
source /absolute/path/to/attune-harness/.env.voyage
set +a
attune-harness index build --config retrieval-config.json --allow-provider
```

The key file is not scanned or loaded automatically by Harness. Provider calls
use only the exported `VOYAGE_API_KEY`. No key belongs in a task or index config.

## Accept a task and retrieve

```sh
attune-harness retrieval-task --config retrieval-config.json \
  --generation GENERATION_FROM_BUILD --objective "Find the implementation and its tests" > task.json
```

Review the scope and budget; set `accepted` to `true`. Then:

```sh
attune-harness retrieve "Where is the cart saved?" --request task.json \
  --session-dir NEW_SESSION_DIRECTORY --allow-provider
```

Each result carries source revision, path, line/byte range and hashes.
`evidence_basis.source_integrity` describes the byte check.
`answer_support: not_established` means these are candidates to inspect, not a
verified answer. If they do not support the answer, say insufficient evidence.
An empty result has `answer_support: insufficient_evidence`. There is no
calibrated semantic abstention threshold yet. Behavioral claims require tests.
The system neither creates a new document collection nor generates an answer.

## Use inside Attune AI

Install the Harness wheel and its `[voyage]` extra in a compatible Attune AI
environment. Do not add Harness's `[mcp]` extra there: the host keeps its own
MCP SDK. This in-process route was tested with Attune AI 16.4.0 and MCP 1.29.1.
Other host versions require qualification.

After exporting the key, launch the real Attune MCP server with its extra tool:

```sh
python -I -m attune_harness.attune_bridge --request /absolute/path/to/task.json \
  --session-dir /absolute/path/to/NEW_SESSION_DIRECTORY --allow-provider
```

Select this launcher as the host's MCP command to expose `code_evidence_query`
alongside Attune's tools. The new tool accepts only `query` and `k`; it cannot
change repositories, models, permissions or budgets. It delegates to the same
RetrievalSession as Harness. Repeated queries within the session reuse evidence;
closing or failing the session stops further calls. A session directory is used
once. A restart requires a deliberate new session; it does not continue unknown
paid work or restore a spent budget.

An exception leaving `activate()` records the session as `unresolved`, even if
it occurs in host setup or serving outside `search()`. This includes cancellation
and keyboard interrupts; the original exception propagates. Normal exit records
completion unless an earlier search failed. Both paths close the session to
further calls.

The local qualified interpreter is `.venv-code-rag/bin/python`. That environment
inherits this machine's existing Attune packages; it is not a clean dependency
resolution. See the receipt for its pre-existing dependency conflicts. Its frozen
installed wheel predates the [September 16 source fixes](sol-review-fix-receipt.md).
Qualify a newly built wheel in a separate environment to use those fixes through
the `python -I` launcher.

For embedding in a Python host, use `CodeEvidencePlugin` from
`attune_harness.attune_bridge` inside its `activate()` context manager, register
it with `PluginRegistry`, and construct the Attune MCP server while it is active.
The plugin uses Attune's existing plugin-handler convention, as its Redis plugin
does. It does not patch built-in handler dispatch or replace generation workflows.

Other coding agents can continue using `attune-harness mcp-serve` in Harness's
MCP 2.2.0 environment. Both adapters share the same retrieval implementation.

## Migration boundary

Use `code_evidence_query` for implementation evidence. The existing
`rag_knowledge_query`, `rag-code-gen`, help and personal-memory paths keep their
existing contracts. Their legacy package still owns model settings and other
consumers, so it has not been uninstalled or had its collection deleted.
The new code path never falls back to that collection after a Voyage failure.
Switching the active desktop MCP configuration and routing old generation
workflows are separate from making this optional plugin available.

See [design](design-code-first-rag.md), [implementation receipt](code-first-rag-receipt.md),
and the [earlier live accuracy check](voyage-accuracy-receipt.md).

The subsequent [98-file evaluation](voyage-full-code-evaluation.md) records
20 frozen questions, comparative retrieval coverage, actual provider usage and
remaining gaps in implementation/test retrieval and missing-answer handling.

The [100-question evaluation](voyage-100-question-evaluation.md) reuses that index
with 80 fresh answerable questions and 20 missing-answer controls. It includes
frozen expected evidence, paired baseline comparisons, per-capability results,
measured API costs, and qualifications for scoring misses.
