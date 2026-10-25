# Hydration generation reader

October 25, 2026. This implements the reader prerequisite in the
[approved hydration-writer addendum](https://github.com/Smart-AI-Memory/attune-harness/pull/310).
Source head: `86bc9f64df8509c64eefc2ccc6bc79ca1f477fbb`.
The writer, conditional publication, cleanup and session-start wrapper remain
later tasks. Existing installations should retain their current writer until
the complete replacement journey is accepted.

## Explicit selection

The existing memory authority config still supplies the authorized roots,
actor, owners, scopes and classifications. Add this Redis fragment only when
testing a matching native generation:

```json
{
  "redis": {
    "url_env": "HARNESS_MEMORY_REDIS_URL",
    "projection": "harness-v1",
    "dataset": "demo"
  }
}
```

Use exactly one of `url` and `url_env`. Optional `password_env` retains its
existing meaning. Dataset names contain 1–32 ASCII letters, digits, underscores
or hyphens. Native selection rejects an explicit `index` or arbitrary prefix.
Native URLs accept `redis://` or `rediss://`, with at most one numeric `db`
query parameter. Other query options are refused before connection because
redis-py gives them precedence over the reader's connection controls.

Without native selection, the existing legacy configuration continues to use
`attune:memory:*`, `idx:attune_memory` and the `attune_memory` function library.
Missing or incompatible native state returns unavailable; it does not select
another backend.

## Read contract

The [contract owner](../../../src/attune_harness/memory_hydration_contract.py)
defines the exact manifest and source-mapping schemas. The active manifest is
stored at `attune:harness:hydration:<dataset>:active`. It names a generation
whose resources use these names:

| Resource | Name |
| --- | --- |
| Record and metadata prefix | `attune:harness:hydration:<dataset>:<generation>:` |
| Generation manifest marker | `<prefix>manifest` |
| Search index | `idx:attune_harness_memory:<dataset>:<generation>` |
| Function library | `attune_harness_memory_v1` |
| Digest function | `harness_recall_digest_v1` |
| Related function | `harness_recall_related_v1` |

The [reader](../../../src/attune_harness/memory_hydration_redis.py) checks the
manifest schema, current host-authority binding, matching generation marker,
index prefixes, source identifiers, field types, document count, index readiness
and installed Lua digest. It adds generation, binding and source digest to packet
provenance and checks the active selection again before returning the packet.
A selection change refuses the read; the caller can reissue it.

The reader uses a dedicated connection without retries, clamps socket timeouts
to its five-second operation budget and rejects packets larger than 1 MiB.
This budget has offline timeout-setting tests; actual DNS and stalled-socket
duration remain unqualified. The packaged Lua functions declare `no-writes`.
Reader commands do not publish data or load functions.

Existing serving filters use the selected generation's active membership and
the current authorized sidecars. Pointer bodies remain searchable and are
excluded from returned packets and banners. The frozen legacy fixture remains
byte-identical. The synthetic
[native fixture](../../../tests/fixtures/hydration/contract.json) contains two
curated nodes and one file, lesson and rule record; it is not a source-capture
or writer-publication fixture.

## Independent review and verification

Requested reviewer: GPT-6 Astra. Author: GPT-6.1 Sol. Independently attested
runtime model identity was unavailable. The initial review of `4a02b51` requested
four fixes: sanitize URL parser errors, prevent URL timeout overrides, validate
index source identifiers and sanitize status parser errors. Commit `c729052`
implements these fixes with maintained regression tests. Delta review found one
additional active-count parser leak; commit `86bc9f6` fixes it. Astra approved
that source delta with no remaining findings. Its independent API/CLI status
regressions passed all eight cases, and all 130 snapshot hashes matched.

| Check | Observed result |
| --- | --- |
| Contract, native reader, legacy Redis and serving tests | 137 passed, 1 skipped on Python 3.12; the skipped case needs live legacy Redis |
| Wheel contents | Every packaged Python and Lua source matched the checkout; installed imports succeeded with attune-ai absent |
| Installed disposable Redis+Search | Redis 7.4.7, Search 2.10.20, redis-py 5.3.1; status, digest, curated node, file node, related and search passed; digest and prompt serving passed; every Redis key value was unchanged |
| Frozen legacy fixture | SHA-256 `37ed7a15b2bf5ffa4f115317212a9ef8c491668654967315eb2a0670444b3bce` |
| Full suite and installed platform qualification | Pending |

The tested wheel SHA-256 is
`1f4756a9cea351a2274c70e05daabc400851211db43d6bd4a4ab9e942653cc6f`.
Its packaged Lua SHA-256 is
`1d8caab5270cf45f47fd7873575ad1f9ef9619addb722271c6b701ee0ce31733`.
Local receipts bind the wheel, installed sources, fixture and disposable probe;
the pull request records their locations. Older development probes remain
historical evidence and do not qualify this source head.

Windows CI, fresh Claude Code and Codex session delivery, actual socket stalls,
missing non-index generation keys and publication/cleanup races remain
unverified. Successful reader checks do not complete the hydration writer or
qualify automatic recall in either host.
