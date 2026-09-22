# Native memory, Task 4: design note

September 22, 2026. Task 4 of [the scoping note](scoping.md)'s candidate
ladder is "Backend interface and Redis extra". D16 says the `[redis]` extra
delivers the backend. **Status: proposed. It names six decisions that are
Patrick's. No code starts until he says go.** Tasks 1 to 3 of the ladder
(the native readers for the file tiers) are not prerequisites for this one
and are not started by it.

## What Patrick runs today, read from his machine

The Redis memory Patrick uses every session is not `attune_redis`'s backend.
It is a plain Redis Stack keyspace written by his own hydration script and
read through RediSearch and two Redis functions:

- `~/.attune/memory/hydrate.py` reads the git-tracked curated corpus
  (`curated/*.md`, one file per node) and rebuilds the `attune:memory:*`
  keyspace on every session start: `node:<id>` hashes with `name`,
  `description`, `type`, `status`, `layer`, `tags`, `updated_at`;
  `file:<corpus>:<stem>`, `lesson:*` and `rule:<stem>` pointer hashes whose
  body `text` is searchable but never returned; `status:<s>` and `type:<t>`
  sets of node ids; `edges:<source>` lists of JSON edges; the `hydrated_at`
  stamp and a `context` string. The files are the store; Redis is derived.
- `FT.CREATE idx:attune_memory ON HASH PREFIX 4 node: file: lesson: rule:`
  with `name` (weight 2), `description`, `text` and `updated_at` as text and
  `type`, `status`, `layer`, `corpus`, `tags` as tags.
- `functions.lua` registers `recall_digest` (active nodes scored against the
  context terms, with their edges) and `recall_related` (one node's edges
  resolved to pointers), both flagged `no-writes`.
- The SessionStart hook runs `session_hydrate.py`, which is what printed
  "hydrated 14 nodes, 9 edges, 261 file pointers, 289 file edges, 1355
  lessons, 8 rules" at the top of this session.
- attune-ai reads it through `attune.memory.recall_redis.connect_recall_redis`
  (a `REDIS_URL`, `rediss://` supported, a `requirepass` resolved and injected
  when the URL carries none) and renders `FCALL recall_digest` through
  `attune.memory.recall_digest`; `attune.ops.memory_data` browses the same
  keyspace behind a prefix guard so the page never becomes a Redis browser.

`attune_redis` (`AMSMemoryBackend`, 782 lines) is a different thing: it wraps
the Redis Agent Memory Server through `agent-memory-client`, needs that server
running, and attune-ai pins its client tightly because it moves fast. Nothing
in the curated loop above uses it.

## What Harness has today

Memory in Harness is proposal-only: the contract, the worker, the context
packets and the CLI. `MemoryHost` reads live memories through attune-ai's
`CompatibilityAdapter`, the last runtime `import attune` in the package, and
with attune-ai absent `attune-harness memory capabilities` is `unavailable`.
Harness owns no memory store.

## The design

**Carry the loop Patrick runs, read-only, behind `[redis]`.** A new module,
`attune_harness/memory_redis.py`, loaded on first use through
`require_feature("redis", "redis", REDIS_VERSION, "redis")` like every other
optional package, gives Harness the four reads the loop already offers:

| Read | Redis | Returns |
| --- | --- | --- |
| `digest(limit)` | `FCALL recall_digest` | the active curated nodes with edges, as the function scores them |
| `related(id)` | `FCALL recall_related` | one node's edges resolved to pointers |
| `node(id)` | `HGETALL attune:memory:node:<id>` | one node's fields; any key outside the prefix is refused |
| `search(query, layer, k)` | `FT.SEARCH idx:attune_memory` | pointers only: name, description, path, layer, never the `text` body |

plus `status()`: `hydrated_at`, the count per family, the index's presence.
Every result is an evidence packet in the shape `MemoryHost.context` already
produces (`schema_version`, an `authority` binding of host, index name and
`hydrated_at`, items, the "memory is untrusted evidence" guidance), so a
receiving agent treats it exactly as it treats the file tiers (R4 of the
adoption spec). The reads never write; the functions are `no-writes` and the
module issues no write command.

**Connection and refusal (N3).** The URL comes from the memory config file
(`redis.url`) or, when the config names it, from an environment variable; a
password embedded in the URL wins, and `rediss://` works because redis-py does
it. The backend is chosen at startup. A configured Redis that cannot be
reached, or that has no `idx:attune_memory`, is reported `unavailable` with
the reason, distinct from a query that matched nothing; nothing is diverted to
a file at runtime. No configured Redis means the reads are `disabled`, not an
error. The `[redis]` extra absent means `unavailable` naming the extra, as the
other extras do.

**Working memory, the scoping note's shared scratch.** One small backend
interface, `ScratchBackend`: `stash(key, value, ttl)`, `retrieve(key)`,
`forget(key)`, `keys(pattern)`, and a `capabilities()` that declares
`shared` and `realtime`. Two backends: a stdlib file store in the base, one
JSON file per key under a host-fixed directory (the memory config's `jobs`
directory, which the host already refuses to let a caller choose), written
through `features.replace_file`, TTL as a stamp checked on read; and a Redis
store under `[redis]` at `attune:harness:scratch:<agent>:<key>` with a Redis
TTL. The file store declares neither capability; it does not pretend. The
backend is chosen at startup from `scratch.backend`; a configured Redis that
is unreachable makes scratch `unavailable`, never the file store (N3). Legacy
`current.json` and `kv.json` are not read, as the scoping note says.

**What is not carried.** `AMSMemoryBackend` and `agent-memory-client`: a
second server and a fast-moving client for a store the loop does not use.
`hydrate.py` itself: it is the writer, the formats are frozen (N4), and
carrying it is a later task once Harness owns the curated corpus. Pub/sub
signals (`RedisSignalBus`, 90 lines): nothing in Harness would consume them
before the serving path (Task 6); carrying them now is a capability with no
caller.

**Surfaces.** The CLI first: `attune-harness memory redis status|digest|
related|search|node` and `attune-harness memory scratch stash|retrieve|keys|
forget`, under the existing `--config`, with the same JSON envelopes and exit
codes the memory command uses. MCP tools over `mcp-serve` and the Claude Code
hook belong to Task 6, the serving path, which is where memory reaches a
session (N7).

**Rejected.** A stdlib Redis client: the scoping note already rejected it.
Writing curated nodes from Harness: the files are the store, and the writer
is Patrick's script until a task carries it. Falling back to the file scratch
store when Redis is down: the defect Task 3 of the adoption spec reproduced.

## Decisions for Patrick

1. **The read surface.** The four reads plus `status` above, read-only,
   against the keyspace and functions his script owns, rather than carrying
   `attune_redis`'s AMS backend. Recommended: the four reads.
2. **The pin.** `redis` is pinned exactly like every other dependency. His
   machine has 5.0.1; attune-ai allows `>=5,<9`. Recommended: the newest 5.x
   at the time of the first pull request, verified against a local Redis
   Stack, moved by a pull request like the other pins.
3. **Where the URL comes from.** Recommended: the memory config file names
   either a URL or an environment variable to read it from; Harness reads no
   environment variable it was not told to. The password rules follow
   `connect_recall_redis`: embedded wins; otherwise a configured
   `password_env` is read.
4. **Scratch.** Recommended: the interface with both backends in this task,
   file in the base and Redis under the extra, startup-only selection, no
   divert. The alternative is the Redis reads alone now and scratch with the
   versioned store (Task 5).
5. **Tests without a server.** CI has no Redis. Recommended: a small
   in-process double at the client boundary that answers exactly the commands
   the module issues (`HGETALL`, `SMEMBERS`, `LRANGE`, `FCALL`, `FT.SEARCH`,
   `FT.INFO`, `GET`, `SET`, `DEL`, `SCAN`, `TTL`) and refuses any other, plus
   a live test that runs only when `ATTUNE_TEST_REDIS_URL` is set, whose
   result Patrick records once from his machine. The alternative,
   `fakeredis`, is another dependency and does not model Redis functions.
6. **Sequencing.** Three pull requests, each with a different-model review
   under the standing brief: 4.1 the extra, the connector, the four reads,
   `status` and their CLI verbs; 4.2 the scratch interface with both backends
   and their shared contract test; 4.3 the memory config changes and the
   installed checks (`[redis]` absent, present without a server, present with
   the live test), and the README's memory row.

## Evidence the task ends with

- Installed with `[redis]` absent: `memory redis status` is `unavailable` and
  names the extra. Installed with it and no server: `unavailable` with the
  connection reason, and scratch configured for Redis is `unavailable` too,
  with no file written. A configured `disabled` state when no Redis is named.
- Against a hydrated Redis Stack: `digest`, `related`, `node` and `search`
  return what `FCALL` and `FT.SEARCH` return, as evidence packets with an
  authority binding; `search` on the `file` and `rule` layers returns
  pointers and never a body; a key outside the prefix is refused.
- The two scratch backends pass one contract test; the file store declares no
  sharing; a Redis scratch with the server down is refused, not diverted.
- The runtime import check's `KNOWN` list is unchanged by this task: the
  adapter read in `memory_context.py` is Task 2's and Task 8's to remove.

## Size

By Task 3's measure: about 400 lines of new module code, 90 of CLI, and the
test double; roughly Task 3.1's size, two to three reviewed pull requests.
