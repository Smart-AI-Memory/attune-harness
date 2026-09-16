# Repository-first RAG implementation receipt

September 15, 2026. Harness `0.1.0.dev13`, local development build.

September 16 follow-up: [four Sol review fixes](sol-review-fix-receipt.md) update
the source budget, lifecycle, evaluator exit and qualification checks. The wheel
and measurements below remain the preserved September 15 evidence. Install a
new wheel in a separate environment before testing those fixes with `python -I`;
the historical installed environment has not been updated.

## Delivered

- `code-config` selects application code and tests, with repository Markdown
  opt-in. Structured configuration/schema files use explicit relative paths.
  Existing accepted configurations and index identities remain unchanged.
- Retrieval distinguishes verified source bytes from unverified answer support.
  Empty results explicitly report insufficient evidence. Nonempty candidates
  still require inspection; this does not implement semantic abstention.
- Optional `CodeEvidencePlugin` exposes `code_evidence_query` through the real
  Attune AI MCP server, using Harness's existing `RetrievalSession`. Scope,
  budgets, replay, source checks and lifecycle remain shared with Harness.
- The core CLI remains usable without Attune AI, Voyage or LanceDB installed.

See [usage and migration boundary](code-first-rag.md) and the
[design decisions](design-code-first-rag.md).

## Installation and qualification

Built wheel: `dist/code-rag-dev13/attune_harness-0.1.0.dev13-py3-none-any.whl`.
SHA-256:
`4ba9d72f9c0af49d688080c3b35f7c62a7c89abfcab96fb7f6f48cf3872f0500`.
All 35 installed Python modules matched the source used for the artifact.
The original five-file, 43-passage live index still passed generation, source
and database integrity checks under the installed package.

| Check | Result | Evidence |
|---|---|---|
| Installed wheel, real Attune dispatcher, deterministic provider | 14 passed | [JUnit](receipts/code-rag/installed-host-tests.xml) |
| Real Attune MCP subprocess discovery, call and clean shutdown | Passed; empty code selection, zero provider calls | [Receipt](receipts/code-rag/attune-mcp/receipt.json) |
| Live Voyage query through installed Attune MCP plugin | Passed; expected function ranked first, source bytes and behavior verified | [Live receipt](../.pilot/code-rag/live-attune/receipt.json) |
| Harness regression selection | 903 passing after the loopback retest; 12 skipped, 7 deselected | [Initial run](receipts/code-rag/regressions.xml), [loopback retest](receipts/code-rag/a2a-loopback-retest.xml) |
| Artifact identity and preserved generation | Passed | [Artifact receipt](receipts/code-rag/artifact.json) |

The initial regression run had 870 passes and 33 sandbox-denied loopback socket
failures. All 38 A2A tests then passed with loopback permission; five of those
already passed initially, giving 903 distinct passing cases. The 12 skips were
platform or absent-host checks; the seven deselections require historical frozen
campaign source hashes. Those old artifacts were preserved. The final additional
closed-session test is included in the separate 14-case installed-host run.

Host checks used Python 3.10.11, Attune AI 16.4.0 and its MCP SDK 1.29.1.
The `.venv-code-rag` environment inherits the machine's existing Attune packages;
it is not a clean dependency resolution. Its `pip check` reports the same two
conflicts as the base environment: Instructor expects older Jiter and newer
OpenAI packages. These unrelated dependencies were not changed. No remote
platform qualification or release publication was performed for dev13.

For the historical test source, the installed-host command was:

```sh
cd /private/tmp
/Users/patrickroebuck/attune-harness/.venv-code-rag/bin/python -I -m pytest -q \
  -o pythonpath= /Users/patrickroebuck/attune-harness/tests/test_code_rag.py
```

For the MCP subprocess check, run `scripts/check_code_rag_host.py` with this
interpreter and a new `--output` directory. The check uses a temporary Git
application containing only excluded Markdown, so it requires no provider key.

## Live evidence and prepared collection

The [earlier live accuracy check](voyage-accuracy-receipt.md) measured three
supported questions ranked first and one absent-answer control that did not
establish automatic abstention. It is not a general accuracy score.

At 20:59 UTC, a new live query through the installed dev13 Attune plugin passed.
Patrick explicitly authorized the five previously indexed files and up to two
API calls. The query asked which function rejects GitHub checks from another
commit. `github_checks.check_suggestions` ranked first. All returned source
bytes and hashes matched the accepted generation, and a local call independently
confirmed that a mismatched `head_sha` raises the expected `ValueError`.

The actual Attune MCP server discovered and called `code_evidence_query`, then
closed its session with a completed receipt. One query embedding consumed 13
tokens and one rerank request consumed 7,657 tokens. Both paid stages completed,
with no retries or new indexing calls. The total cost calculated from provider
usage and the recorded rate snapshot was **$0.00038441** before credits, below
the authorized estimate of $0.01. This is not an account billing statement.
The test reused the existing five-file, 43-passage index.

Evidence: [live receipt](../.pilot/code-rag/live-attune/receipt.json),
[returned passages](../.pilot/code-rag/live-attune/result.json), and
[authorized payload selection](../.pilot/code-rag/live-attune/authorization.json).
This establishes one successful live host query and its expected source behavior;
it does not establish general retrieval accuracy or generated-code quality.

Separately, `.pilot/code-rag/config.json` and `plan.json` prepare a broader
selection: 71 files, including 35 test files, 931 passages, and 30 embedding
requests. The advisory bytes/4 estimate is $0.01704819 before credits, using
the recorded rate snapshot. This is neither exact token usage nor a billing
quote. The plan includes explicit dirty/untracked-source selection and
`pyproject.toml`; it has made zero provider calls and is not a published index.

## Remaining migration boundary

This delivers the optional repository-evidence plugin and Harness entry point.
The desktop MCP configuration has not been switched. Attune's built-in
`rag_knowledge_query`, `rag-code-gen`, help and personal-memory consumers retain
their existing behavior. The legacy package and collection have not been
deleted. No source changes were made in the Attune AI repository.

Broader application-code evaluation and migration of those legacy consumers
remain separate work. Structured data is available as source context; exact
validation and application state decisions still belong to code and tests.
