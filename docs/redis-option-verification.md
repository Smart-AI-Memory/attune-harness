# Redis option: requirements and real-service verification

The Redis option provides keyword recall from an already hydrated index, shared
working state, and an optional saved-record mirror. These are separate paths.
Installing `attune-harness[redis]` installs the Python client; it does not install,
start, secure or hydrate a Redis service. See the
[operation requirements](cli-guide.md#redis-requirements) before selecting a path.

## Configure the existing option

For hydrated recall, configure exactly one of `redis.url` and `redis.url_env`.
The optional `password_env` supplies a password when the URL has none. Use
`rediss://` for a service that you have configured for TLS; TLS was not exercised
in the check below. Keep connection details out of committed configuration.

Legacy recall requires Redis Functions, Search hash indexes and the existing
`attune:memory:*` projection, configured search index (default `idx:attune_memory`)
and `attune_memory` function library. The library supplies `recall_digest` and
`recall_related`. Keep the
existing writer that creates them. Plain Redis can support scratch and saved
mirroring while refusing hydrated recall because Search or its required state
is absent. Server reachability alone does not mean recall is ready.

With an existing authorized memory configuration and populated legacy service,
inspect it through the installed CLI:

```sh
attune-harness memory --config memory.json redis status
attune-harness memory --config memory.json redis search memory --k 5
attune-harness memory --config memory.json serve --for memory
```

Search and related-record results carry provenance. File, lesson and rule pointer
bodies are searchable but are not returned in Redis packets or banners. File
pointers served for a prompt also require authorized roots and current verdict
checks. A matching path in Redis does not grant file access.

Current development also has explicit `harness-v1` generation reads; see the
[generation reader](specs/native-memory/hydration-generation-reader.md). The seeded
reader check below does not supply its unfinished writer. It does not change
legacy selection automatically.

For scratch, choose `scratch.backend: redis`, a namespace and the explicit Redis
connection. TTL expiry and expected-version updates operate on that shared store.
Use expected versions for all competing writers; unconditional writes retain
overwrite behavior. A lost write acknowledgement can leave an uncertain outcome
and must not trigger a blind retry. Persistence, eviction and backups are server
operations, not consequences of installing the extra.

The [saved-record mirror](memory-saving.md#optional-redis-index) instead uses
`saved.redis` with `url_env` and `namespace`. Files remain authoritative, and saved
search reads those files. Service failure reports pending mirror work while the
committed record remains readable; reindex retries the projection. This mirror
does not add saved entries to automatic recall or provide a Redis search API.

## October 30, 2026 verification

This is evidence for 1.6.0 preparation, not a published 1.6.0 artifact or an approval
to release. The verified development baseline is
`d0849441c6420b73baa796cf80f7bdf3c1ed4fec`; its package metadata still says 1.5.1.
Changes to Redis source, dependencies or final release artifacts require matching
qualification before carrying this evidence forward.

| Input | Observed identity |
| --- | --- |
| Platform | macOS 27.0.1, arm64; CPython 3.12.2 |
| Python client | redis-py 5.3.1, the current pinned extra |
| Real service | Redis 7.4.7 with Search 2.10.20; separate Redis 7.4.7 process without Search |
| Isolation | Two owned processes on separate ephemeral loopback ports; private configuration, AOF and source directories; synthetic records only |
| Persistence for this check | AOF enabled, `appendfsync always`, snapshots disabled, `maxmemory-policy noeviction` |
| Installed artifact | Noneditable wheel; all 112 Harness payloads matched the retained wheel and candidate source |

Retained wheel SHA-256:

```text
9e5b4a72aa013a7994ec92c4d38ce0a102e8eb67b4770e580122f757ae59f2fd
```

The installed-wheel probe passed 77 assertions. The two existing opt-in live
tests also passed against the disposable service as checkout/source regressions.
The verification used the existing synthetic generation fixture, plus a separately
recorded legacy seed with three active curated nodes to satisfy the existing
legacy live test. Frozen fixtures and existing writer code were unchanged.

| Path | Real-service observation |
| --- | --- |
| Legacy and generation reads | `status`, digest, curated/file node, related and full-text search returned valid packets through the installed CLI. Generation provenance matched the seeded manifest. |
| Serving | Digest and prompt banners stayed within the declared character bound; inactive records and current `wrong` file pointers were excluded while a valid curated result remained. Pointer bodies were absent. |
| Read preservation | Seeded `attune:*` key values matched before and after the positive read/serve sequence. This comparison does not cover every internal Search or function-library state. |
| Missing or incompatible state | Plain Redis without Search, missing legacy function library, foreign generation binding and missing completed-generation marker produced unavailable results. |
| Authentication failure | Supplying a synthetic password to a disposable server with no password configured produced an explicit unavailable result. Successful password-protected service access was not tested. |
| Shared scratch | Plain Redis supported actual TTL expiry. Two independent clients attempted the same expected-version update: one succeeded, one was refused, and the stored version advanced once. The test did not force overlapping `WATCH` transactions. |
| Saved mirror | Upsert and revision reached Redis; withdrawal removed the projection while retaining file history. During service outage a committed save stayed readable with pending indexing. Reindex reported indexed after recovery; an independent clean restart/readback matched the active record exactly and confirmed the withdrawn key remained absent. |
| Outage and stalled service | A stopped service produced explicit failure; `serve` emitted no stdout, reported skipped recall on stderr and exited zero. A real `CLIENT PAUSE` stall exercised the same bounded failure path, followed by successful recall after the pause ended. |
| Clean restart | Redis loaded its private AOF and retained the acknowledged scratch value. Both owned services were stopped after the checks. |

The hook's successful process exit is not proof that an agent received memory or
the degraded-status message. The check records CLI stdout/stderr and software
behavior. Actual host delivery remains a separate acceptance requirement.

## Limits and release boundary

- The fixture was seeded directly. Its source/context hashes are explicit
  synthetic placeholders; this does not test source capture, hydration publication,
  cleanup or the new RedisVL writer.
- This is keyword and context-overlap recall, not an embedding/vector quality test.
- A clean SIGTERM/restart is not crash, power-loss or high-availability evidence.
  Lost acknowledgements and uncertain writes were not induced on the real service.
- TLS, successful password/ACL configuration, remote networks, Windows service
  installation, DNS stalls and general timing distributions were not qualified.
  One observed bounded stall is not a universal latency guarantee.
- No Claude/Codex startup settings changed. Fresh, resumed and delegated-agent
  recall, cross-machine source resolution and model usefulness remain unverified.
- No production Redis, personal corpus, paid model call, release or migration was
  part of this verification. The new writer and cross-agent comparison experiments
  remain separate and approval-gated.

Full probe sources, outputs, key snapshots, server logs, failed initial probe and
artifact identities are retained privately under the dated Redis-option receipt.
The first probe failed because its CLI invocation emitted no command output; the
corrected probe used the installed console entry point. That harness correction
did not change product source. The final run additionally required a nonempty
valid banner in the `wrong`-pointer case and retained the key snapshots.
