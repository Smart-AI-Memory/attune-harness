# Hydration writer design

Status: **draft for Patrick's approval, October 24, 2026**. All choices below are
proposals. This is not authorization to edit `src/`. See [requirements](requirements.md).

## Source projection and configuration

Keep `memory --config` as the host authority and connection input. Extend its
Redis section additively with `projection: harness-v1` and a required dataset ID.
Absent `projection` preserves legacy mode. Native mode rejects an explicit legacy
`index`, arbitrary prefixes and unknown fields; cache names are derived internally.
Old Harness versions must refuse the new config rather than misread it.

The new sources file has only `schema_version` and `sources`. Each source has
`root_id`, `layer`, `corpus` and `path`. `root_id` must name an authorized personal
or curated root; raw findings are outside this writer. `path` is relative to that
root, with `.` allowed only as a directory selector; absolute paths and `..` are
refused. Curated/file sources select direct Markdown children; rules recurse;
lessons select one Markdown file. Exclude `MEMORY.md` from file pointers as the
reference does. Never use sources-file paths as independent authority.

Dataset/corpus IDs are 1–32 ASCII letters, digits, underscore or hyphen; native
generation IDs are opaque 32-character lowercase hex. Record IDs obey the existing
reader's 128-character bound. Reject duplicate projected IDs, including rules
with the same stem in different directories and file mappings with the same
corpus/stem. Distinct authorized roots never collapse because their paths match.

Example proposed complete `memory.json` for a POSIX qualification fixture. Fixture
setup must create these canonical directories; each platform substitutes its own
absolute paths. These values are synthetic and identify no real owner or service:

```json
{
  "schema_version": 1,
  "actor": "local-user",
  "owners": ["local-user"],
  "scopes": ["demo"],
  "classifications": ["internal"],
  "profiles": ["offline"],
  "roots": [
    {"id": "curated", "path": "/fixture/curated", "tier": "curated", "scope": "demo", "owner": "local-user", "classification": "internal"},
    {"id": "personal", "path": "/fixture/personal", "tier": "personal", "scope": "demo", "owner": "local-user", "classification": "internal"},
    {"id": "reference", "path": "/fixture/reference", "tier": "personal", "scope": "demo", "owner": "local-user", "classification": "internal"}
  ],
  "redis": {
    "url_env": "HARNESS_MEMORY_REDIS_URL",
    "password_env": "HARNESS_MEMORY_REDIS_PASSWORD",
    "projection": "harness-v1",
    "dataset": "demo"
  }
}
```

```json
{"schema_version": 1, "sources": [
  {"root_id": "curated", "layer": "curated", "corpus": "curated", "path": "."},
  {"root_id": "personal", "layer": "file", "corpus": "personal", "path": "."},
  {"root_id": "reference", "layer": "lesson", "corpus": "lessons", "path": "lessons.md"},
  {"root_id": "reference", "layer": "rule", "corpus": "rules", "path": "rules-tail"}
]}
```

The second block is `sources.json`. These are proposed schemas, not currently
valid 1.5.1 configuration or complete copy-and-run setup. Task 1 supplies source
files and connection variables, materializes the complete example at temporary
absolute paths and makes it an installed journey fixture.

## Behavior to adapt, reference or drop

| Reference behavior | Proposed disposition |
| --- | --- |
| Curated frontmatter: `curated`, `node_id`, `node_type`, `description`, `status`, `tags`, `updated_at`, `edges_json`; full body becomes description | Adapt the existing field mapping with explicit validation. No frontmatter conversion. Validate edge targets, duplicate IDs and malformed JSON before staging. |
| File metadata and body index; one top-level lesson bullet with its line; recursive rule pointers | Adapt with authorized capture, explicit source mapping and deterministic identity. Keep the existing searchable-body bound visible. |
| `[[link]]` edges, excluding `[[?forward-reference]]` | Adapt. Resolve in the same corpus first; otherwise require a unique target among explicitly configured corpora. Ambiguous targets refuse the batch; unresolved links are counted, not fabricated. This tightens the old first-match behavior. |
| Secret detection and known documentation placeholders | Reference and characterize. Reuse Harness detection where it preserves legacy blocking cases; add the missing cases without importing attune-ai. Refuse the batch instead of silently skipping unsafe records. Do not automatically substitute the reader's broader personal-data redaction policy. |
| `name` TEXT weight 2; `description`, `text`, `updated_at` TEXT; type/status/layer/corpus/tags TAG; sortable update time; vocabulary synonyms | Adapt the schema and existing synonym set. Qualify it against the supported real server; do not tune ranking in this task. |
| Curated digest overlap with up to 30 local context terms, newest-first ties; one-hop related pointers | Adapt into a separate, versioned native function bundle. Context uses bounded read-only cwd/branch/recent-subject inspection; absent Git yields reported degraded context, not hydration failure. Store its digest in the generation. |
| Hard-coded personal roots and attune-ai checkout freshness heuristics | Drop. Record captured source hashes and optional local Git revision information; missing remote-sync knowledge is unknown, not fresh. |
| Auto-pull, auto-push, attune-ai environment probe and live-keyspace delete/rebuild | Drop. No Git synchronization or ambient installation repair. |

Record final module-level adoption verdicts in implementation evidence. No private
corpus, logs, Git remote details or personal content enter fixtures or the wheel.

## Immutable generations and conditional publication

Redis transactions serialize commands but do not roll back runtime failures;
putting the old rebuild in `MULTI/EXEC` is insufficient. See the official
[transaction semantics](https://redis.io/docs/latest/develop/using-commands/transactions/).

Use a Harness-owned namespace, separate from the legacy one:

| Resource | Proposed identity |
| --- | --- |
| Active manifest | `attune:harness:hydration:<dataset>:active` |
| Generation data | `attune:harness:hydration:<dataset>:<generation>:` followed by the existing logical key families |
| Search index | `idx:attune_harness_memory:<dataset>:<generation>` |
| Function library | Versioned `attune_harness_memory_v1` with distinct native function names |

1. Validate complete config and capture sources with content/identity hashes. Read
   the current active token before building. Check capabilities without requiring
   an existing cache. Compare the complete input/context/function digest with the
   active generation; a verified match returns unchanged without staging.
2. Reserve a bounded staging slot under the dataset's ownership registry. Build
   new hashes, memberships, edges and context at a unique generation prefix.
   Create its search index. Never alter a published generation.
3. Verify the exact schema/prefix, expected document counts, index completion and
   indexing failures, plus representative digest/search/related round trips.
   [FT.INFO](https://redis.io/docs/latest/commands/ft.info/) exposes readiness and
   failure information; test its supported-version reply shapes. A successful
   `FT.CREATE` alone is insufficient.
4. Revalidate source/config capture, then conditionally publish one manifest with
   schema version, generation, prior generation, input/context/function digests,
   authority binding, layer counts and UTC completion time. A small atomic CAS
   operation compares the original token and staging ownership before replacing
   the active value. All error checks precede its single publication write.
5. If acknowledgment is lost, read and compare the generation/publication identity.
   Confirmed identity means published; confirmed unchanged token means unpublished;
   an intervening publication or unavailable server remains uncertain. Do not retry
   an uncertain switch as a new operation.

Native readers derive key/index names from validated dataset/generation IDs; they
do not trust arbitrary manifest paths or function names. Resolve one manifest per
operation, bind all reads and filtering to it, and recheck the active token before
emitting. An intervening switch produces an explicit unavailable/stale result,
not a mixed packet or an unbounded retry. Legacy reader behavior remains intact.

The new library must not `FUNCTION LOAD REPLACE` an existing differing bundle.
Load a missing version, or verify the exact existing source identity; a mismatch
refuses publication. Install assets in the wheel and verify their digests. A
future function revision gets a distinct supported identity, not an in-place
replacement under readers. Scripts/functions receive only derived bounded keys.

## Retention, deadlines and recovery

Proposed initial bounds: at most four generation slots per dataset; the existing
64 MiB source-capture budget; a 64 MiB serialized projection budget per generation;
a 30-second direct-apply deadline; a five-second native read deadline; a ten-second
whole-hook deadline. These are safety limits to test, not measured latency claims.
Search-index/server overhead is additional and reported where available.

The registry serializes staging reservations, retirement and publication. Preserve
the active and immediately previous successful generation. Unpublished staging
ownership expires after five minutes; retirement has a 30-second read grace.
Cleanup can reclaim only registered, expired staging or older retired generations,
and only after atomically preventing them from publishing and checking they are
neither active nor previous. No TTL is applied to active/previous data. A full
budget refuses new staging if safe reclamation is impossible. Fault tests must
cover cleanup racing publication and readers; do not claim safety from age alone.

These guarantees concern this writer's actions. Qualify against a disposable
Redis with eviction disabled and record persistence/eviction settings; do not
change the user's server policy. Server loss or eviction can make state
unavailable. Missing keys, a malformed manifest or an incompatible function bundle
never triggers automatic rebuild, cross-backend fallback or legacy-library repair
inside a read command.

## CLI and host boundary

Add **`memory hydrate`**, requiring exactly one of `--check` or `--apply` plus
`--sources`. Check performs no Redis writes, including function/index setup.
Apply reparses/revalidates everything; check is not a stored permission token.
Keep the sources schema outside the frozen roots config.

Use existing JSON envelope conventions: `ok` with `published` or `unchanged`
detail; `failed` for refused input, `unavailable` for missing capability and
`uncertain` for an unconfirmed effect. Direct failures exit 2. Include sanitized
reason codes and hashes/counts; never raw server exceptions that can contain data.

Package a module wrapper that bounds apply plus serve and emits only the existing
banner to stdout. A failed hydration can serve a confirmed older generation with
explicit stderr degradation and its original timestamp. If publication is
uncertain, reconcile first; unavailable or inconsistent state produces no banner.
The wrapper exits zero even on invalid arguments/config and child timeout. Use the
selected installed interpreter; do not depend on a checkout-relative script.
Clamp both child deadlines to the shared remaining time; a direct apply's
30-second limit cannot override the ten-second wrapper limit. When no budget
remains to reconcile or serve, emit only the failure diagnostic and exit zero.

Claude Code and Codex installation instructions follow actual tested discovery
and startup mechanisms. No private settings are edited by installation. Codex
automatic delivery is an evidence obligation, not an assumed hook API. If an
automatic surface is unavailable, stop that acceptance item and report the gap;
changing the promised journey needs Patrick's decision.

## Rollback and alternatives

Keep the old writer and cache while validating the new projection. Explicitly
select legacy config to return to its unchanged read path. Do not automatically
restore an older native generation after a failure: it may revive withdrawn
memory. Recovery preserves evidence and requires a fresh capture/publication or a
separately authorized rollback decision.

Rejected: deleting the live namespace before rebuilding; treating `MULTI/EXEC`
as rollback; silently adopting an unrelated legacy library/index; changing stored
Markdown; a second supported external-writer package; using model calls to parse
sources; and claiming automatic Codex delivery from a successful CLI subprocess.
