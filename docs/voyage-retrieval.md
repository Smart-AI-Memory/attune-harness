# Voyage context for coding agents

Dev12 adds application-source retrieval using `voyage-code-4`, local LanceDB,
and `rerank-2.5`. It returns exact source passages and usage receipts. It does not
edit code or certify that an agent's interpretation is correct.

## Install and configure

```sh
python -m pip install -c requirements-voyage.lock '.[voyage]'
# Add MCP or the existing review workflow when needed:
python -m pip install -c requirements-voyage.lock -c requirements-mcp.lock '.[voyage]'
```

Create an API key in the [Voyage dashboard](https://dashboard.voyageai.com/organization/api-keys).
The variable must be exported in the terminal that launches Harness. In zsh,
this prompt keeps the secret out of command history:

```zsh
read -rs "VOYAGE_API_KEY?Paste Voyage API key: "
export VOYAGE_API_KEY
printf '\n'
```

Check presence without printing the key:

```sh
python -c 'import os; print("Key exported" if os.environ.get("VOYAGE_API_KEY", "").strip() else "Key missing")'
```

This checks export, not authentication. A separate application or terminal does
not automatically inherit this shell's environment. No `.env` loader or secret
file scanning is performed.

Example `retrieval-config.json` (paths are relative to that file):

```json
{
  "schema_version": 1,
  "roots": [{"repo_id": "my-app", "path": "/absolute/path/to/my-app"}],
  "index_dir": "/absolute/path/to/local-index",
  "include": ["src/**/*.py", "tests/**/*.py", "docs/**/*.md"],
  "exclude": [],
  "allow_overlays": false,
  "allow_untracked": false,
  "max_provider_calls": 128
}
```

Use Git repository roots with a HEAD revision. By default, selection includes
tracked Python and Markdown files, at most 1,000 files/16 MiB, with a 256 KiB
per-file bound. Dirty selected files require `allow_overlays: true`; untracked
files separately require `allow_untracked: true`. Unsupported extensions,
repository metadata, environments and common generated directories are excluded.
JSON ledgers are not embedded. Symlinks, invalid UTF-8 and oversized input fail
visibly. Other selected code extensions use explicitly labeled line chunks.

## Plan, build and refresh

```sh
attune-harness index plan --config retrieval-config.json
attune-harness index build --config retrieval-config.json --allow-provider
attune-harness index inspect --config retrieval-config.json --generation GENERATION
attune-harness index update --config retrieval-config.json --base-generation GENERATION --allow-provider
```

`plan` makes zero provider calls and prints the selected files, hashes, passage
count, expected full-build calls and an advisory token/cost estimate. Review the
selection before `--allow-provider`, which authorizes uploads and paid calls.
Parent directories must exist. Builds publish an immutable generation only after
all embeddings, database rows and indexes are saved. Updates reuse identical
embedding inputs and omit deleted passages. An unchanged generation makes zero
calls. Existing generations and receipts remain available.

Use the returned generation digest explicitly. Retrieval never silently follows
a new generation or rebuilds an index. A source edit or revision change requires
an update and a newly accepted task. `inspect` can show an unpublished build and
its stage receipts; inspection makes no provider calls.

## Give a coding agent retrieval access

```sh
attune-harness retrieval-task --config retrieval-config.json --generation GENERATION \
  --objective "Locate the persistence code and its tests" > task.json
```

Review the normalized configuration, scope and tool-call budget in `task.json`;
set `accepted` to `true`. `scope.repo_ids` selects accepted repositories;
`scope.exclude_paths` can exclude exact `{repo_id, path}` pairs. The task needs
no reviewed Markdown document or verification manifest.

```sh
attune-harness retrieve "Where is the cart saved?" --request task.json \
  --session-dir retrieval-session --k 3 --allow-provider

# The coding agent can instead connect this stdio MCP server:
attune-harness mcp-serve --request task.json --participant coding-agent \
  --session-dir mcp-session --allow-provider
```

Session directories are new, exclusive owners. The `harness.retrieve` MCP tool
accepts only `query` and `k` (1–20). Tool arguments cannot change paths, models,
scope, permissions or budgets. The session validates source bytes and accepted
grants before each call. Each invocation consumes the tool budget, including
evidence reuse; repeated identical queries in the same session incur zero new
provider calls. CLI invocations create separate sessions; do not treat a new
session as a continuation of a prior paid failure.

Dense and full-text searches receive the same exact scope filter. Identifier
matching supplements lexical search. RRF merges candidates; at most 50 distinct
passages go to the standard reranker. Results include repo/revision, relative
path, source and passage hashes, exact UTF-8 byte offsets, display lines, scores,
and original text. Ranking scores do not establish truth or answer absence.

## Existing reviews and extensions

Install `[review,voyage]`. Copy the generated task's `retrieval` object into the
participant registry as its optional `retrieval` field. Exclude the reviewed
document in `scope.exclude_paths`, regenerate the review form, and accept it.
The review's `corpus` must be one selected application root. Registry changes
invalidate the old form revision.

```sh
attune-harness review-form --config participants-voyage.json
attune-harness review request.json --config participants-voyage.json \
  --run-dir review-run --allow-provider --allow-external
attune-harness resume-review review-run --request request.json \
  --config participants-voyage.json --checkpoint CHECKPOINT --allow-provider --allow-external
```

`--allow-external` authorizes configured participants; `--allow-provider`
authorizes Voyage. The two permissions are separate. Two-role reviews reuse
identical retrieval evidence. Extensions delegate through that same backend and
record the actual dependency. Multiple passages in one file retain distinct
identities and original byte positions. Legacy forms, keyword results and
version-1 recovery profiles keep their existing behavior.

## Receipts, failures and budgets

Index stage receipts live under `generations/GENERATION/stages/`; query receipts
live under `SESSION/retrieval-work/stages/`. Each has a durable stage ledger and
individual records. Completed provider results can replay after a local failure.
An interrupted/invalid provider response has unknown billing and blocks automatic
retry. Missing recorded stages cannot reset the budget. The old
`--retry-read-only` option cannot repeat paid retrieval work.

For a new nonempty query, `max_provider_calls` must cover both the query
embedding and its required rerank before the embedding can dispatch. If only
one slot remains, retrieval refuses with zero new provider calls. A prepared
embedding already occupies a slot and also needs rerank capacity before it can
continue. Completed stages still replay for free, including when the call budget
is full and only the final result cache was lost. Empty evidence needs no calls.

Retain the entire run/index directory. After an uncertain provider dispatch,
inspect its records and account activity before deliberately starting another
operation. No provider cancellation or billing rollback is claimed. Recovery
requires the original directories, accepted configuration and unchanged sources.

The pinned SDK's connection retries and high-level retries are disabled;
redirects are refused, requests have a 60-second timeout, and responses are
bounded. Payload limits reserve overhead for SDK fields. Run records stay within
8 MiB; retrieved evidence is bounded before dispatch when predictable. Large
vectors live in hashed sidecars/database rows, outside review checkpoints.

Token estimates use UTF-8 bytes/4, a versioned approximation. They are **not a
hard USD ceiling**. Call and request-byte limits are enforced; provider-reported
tokens price actual successful stages. Missing usage remains unknown. The rate
snapshot is September 15, 2026: embeddings $0.12/M, reranking $0.05/M, excluding
credits. [Voyage pricing](https://docs.voyageai.com/docs/pricing)

The original scenario remains $1.20 initial indexing, $1.63/month for 1,000
searches, or $15.24/month for 10,000 searches. It assumes 10M initial tokens, 1M
updated tokens/month, 100 query tokens and 50 passages of 500 tokens per search.
Actual selected code and call receipts determine actual costs.

Explicitly choose the existing keyword route to stop using Voyage:

```sh
attune-harness retrieve "retention policy" --corpus docs
```

Preserve older accepted registries and generations for inspection. There is no
automatic fallback from a failed Voyage request.

See [implementation evidence](voyage-retrieval-receipt.md), the
[September 16 budget and lifecycle fixes](sol-review-fix-receipt.md), the
[design note](design-voyage-retrieval.md), and the
[evaluation protocol](../experiments/voyage/README.md). Software checks and the
small live smoke test do not by themselves justify routine-use promotion.
