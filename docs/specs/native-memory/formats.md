# Frozen legacy memory formats

D25.5 and D28 freeze these formats **as the native reader reads them**.
`MemoryHost` accepts only `reader: native` (also the default). The raw and
file document tiers are read-only; the Redis interface issues no writes.
This contract does not freeze Harness's separately versioned saved-memory or
scratch stores. It does not qualify model quality or native worker transports.

## Authority and access

The config has exactly `schema_version: 1`, `actor`, `owners`, `scopes`,
`classifications`, `profiles`, and `roots`, after `reader`, `redis` and `scratch`
sections are set aside. Each root has `id`, canonical absolute `path`, `tier`
(`raw`, `personal` or `curated`), `scope`, `owner` and `classification`.
Roots must be authorized by the host's scope/owner/classification lists.
The complete root config digest binds every handle. Root ids are unique,
1–64 letters, digits, underscore or hyphen. No ambient root discovery occurs.

File access uses a POSIX descriptor walk with no-follow on each component.
Existing symlink sources, hard links, nonregular files, authority changes and
sources changing during reads are refused. A dangling `findings.jsonl` symlink
is treated as an absent raw file (an empty result), preserving the frozen behavior. Windows reads return the explicit POSIX qualification
refusal. No source is truncated to fit a limit or silently rewritten.

## Raw findings

`<root>/findings.jsonl` is UTF-8 JSON Lines. Blank lines are ignored; every
other line is an object. `id` is a nonempty string unique within the file;
`text` is a string; `topics` defaults to an empty list and must be a list.
`cwd` must equal the root's scope for the row to be served. `ts` is a numeric
timestamp (finite numeric strings accepted); an unreadable or nonfinite timestamp
expires the row.
Rows older than 30 days are expired. Unknown stored fields remain metadata.
One `type:` topic gives the kind; missing or ambiguous type topics give `unknown`.

Nonblank queries rank by token overlap plus a three-day recency half-life;
ties preserve file order. Blank queries rank newest first. The whole file is
bounded to 8 MiB. A handle's locator contains `root_id` and `record_id`, and
its version binds the file content digest and file identity/timestamps/size.
A second capture detects changes during recall. Resolve rechecks expiry,
`cwd`, identity and version, returning the full original text.

## Personal and curated documents

Each root supplies `**/*.md` with UTF-8 text and optional YAML frontmatter.
Frontmatter `owner`, `scope` and `classification`, when present, must match
the root. The complete source remains available at resolve, including unknown
frontmatter fields and links. The strict content gate refuses exposure of text
or metadata that would require redaction, and does not sanitize saved bytes.

Every source is at most 8 MiB; a query snapshot contains at most 4,096 Markdown
files and 64 MiB total including sidecars. Snapshot copies preserve mtimes.
The pinned attune-rag keyword retriever retrieves twice `k`, de-duplicating
results by path. The file stem supplies kind; locator contains `root_id` and
relative `path`. Resolve returns full source, not a retrieval snippet.

Two optional sidecars contribute to every document handle's version:

- `summaries_by_path.json`: path-keyed summaries used by the retriever.
- `.verdicts.jsonl`: verdict records keyed by `stem`, with `verdict`, `digest`,
  `who` and `at`. The last readable verdict per stem controls the annotation;
  a matching content digest binds a verdict to its text. Wrong verdicts and
  stale verification are visible evidence, not execution authority.

Source versions bind content and file identity/timestamps/size. Sidecar
absence is also versioned. Changing a source or either sidecar invalidates
an old handle. Provenance and staleness annotations are produced by
`memory_controls`; the native reader never emits attune-ai telemetry.

Host recall and refresh carry a bounded selection of these generated annotations
in each document item's `metadata`, alongside the excerpt and handle. Document
resolve recomputes annotations from the captured source and verdict bytes bound
to the handle. This preserves specific WRONG/stale warnings without forwarding
arbitrary frontmatter into the context packet or treating provenance as authority.

## Hydrated Redis keyspace

The fixed prefix is `attune:memory:`. Redis Stack supplies:

| Key or API | Read contract |
|---|---|
| `node:<id>` hashes | Curated node fields `name`, `description`, `type`, `status`, `layer`, `tags`, `updated_at` |
| `file:<corpus>:<stem>`, `lesson:<line>`, `rule:<stem>` hashes | Pointer fields `name`, `description`, `type`, `layer`, `corpus`, `path`, `line`, `status`, `updated_at`; pointer `text` is searchable but never served |
| `status:<s>` sets | Membership, including active curated nodes |
| `edges:<id>` lists | Related-node edges consumed by the function library |
| `hydrated_at` | Hydration stamp included in the authority binding |
| `idx:attune_memory` | Search index over this fixed keyspace |
| `attune_memory` library | `recall_digest` and `recall_related`, declared `no-writes` |

Bare curated ids and family-qualified pointer ids round-trip through `node`.
`related` supports curated and file ids, refusing lesson or rule ids. Query
text is at most 512 characters, result limits at most 100, replies at most
1 MiB. `serve` defaults to eight digest nodes, 4,000 characters and 240 per
line. Redis packets are untrusted evidence; reissue a read instead of passing
them to `memory refresh`. Missing config is `disabled`; missing dependencies,
an unreachable server, index or function library are `unavailable`, without
fallback to files. Empty results remain distinct from unavailable service.

## Status and refusal contract

The file reader returns `available` for successful nonempty results, `empty`
for successful zero results, `partial` when items are returned alongside root failures,
and `unavailable` when root failures leave no items. Host recall adds schema/operation,
query/bounds, authority and guidance. A host refusal prints `failed` and exits
2. Selecting any reader other than native returns exactly:
`Memory reader must be 'native'`.

The reader's literal refusal text is preserved below, including historical
wording containing “adapter”; D28 does not rename these established errors.
Generic schema/type validators additionally report the invalid field or shape.

- `Adapter authority changed; construct a new adapter`
- `At least one explicit memory root is required`
- `Corpus exceeds 64 MiB query snapshot limit; narrow the root`
- `Corpus exceeds snapshot file limit; narrow the root`
- `Document corpus contains symlinks`
- `Duplicate root identity`
- `Foreign or stale source authority`
- `Invalid memory query or result bound`
- `Invalid root identity`
- `Malformed or duplicate raw identity; exact retrieval unavailable`
- `Malformed raw record`
- `Memory root is outside host authority`
- `Memory root must be a canonical absolute path without symlinks`
- `Raw source changed during retrieval`
- `Raw source expired; refresh context`
- `Raw source scope changed`
- `Retrieval metadata changed; refresh context`
- `Root changed or unavailable`
- `Scoped descriptor reads are currently qualified only on POSIX`
- `Source changed during retrieval; refresh context`
- `Source changed while being read`
- `Source escapes its authorized root`
- `Source exceeds read limit; select a narrower source`
- `Source must be a regular file without hard links`
- `Source read limit is outside the file bound`
- `Source security metadata conflicts with root authority`
- `Source security metadata must be an object`
- `Source was corrected, deleted or replaced; refresh context`
- `Symlink source is not authorized`
- `Tier uses its existing governed path; no new adapter capability`
- `Unknown root identity`
- `Unknown security classification`
- `Unreadable source security metadata`
- `Unterminated source security metadata`
- `Worker mutations unavailable for legacy stores; use existing governed memory commands`
- `query must be a non-empty string`

## Executable witness and reverse writer constraint

`tests/fixtures/memory_compatibility.json` is byte-identical to the fixture
introduced from `3230643` of `wip/local-snapshot-2026-09-19`. Its SHA-256 is
`37ed7a15b2bf5ffa4f115317212a9ef8c491668654967315eb2a0670444b3bce`.
`tests/test_memory_fixture_contract.py` pins its digest and shape on every
platform. It is the sole retained witness of attune-ai behavior; native reader,
document-format and Redis tests exercise the supported reader contract.
The old cross-checkout differential and runtime adapter are removed.

On attune-ai's side, findings are written by `attune/memory/file_stash.py`
and `atomic_io.py`; documents and sidecars by `personal.py` and `verdict_log.py`;
the Redis keyspace by the maintainer's `~/.attune/memory/hydrate.py` and
`functions.lua`. **A writer change to these formats requires a compatible
Harness reader change first.** The writers do not have to stop. This reverse
constraint must be carried beside those writers by their owner; this change
does not modify another repository or a maintainer's hydration scripts.

`attune_bridge.py` was already removed after 0.2.0. No Harness change is
needed for attune-ai's absent `harness` extra or attune-redis's attune-ai
dependency: Harness consumes the keyspace without importing either package.
