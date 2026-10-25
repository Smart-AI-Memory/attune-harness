# Harness-owned hydration writer — native-memory addendum

Status: **implementation approved by Patrick, October 24, 2026**. Patrick approved
the specification and implementation plan after draft PR #310 was presented.
Task 1 is active. Merge, release, spending and production-rollout gates remain.

## Outcome and review boundary

A fresh Harness installation can project explicitly authorized Markdown memory
into Redis and serve it into an agent session, with attune-ai absent. Markdown
remains the source of truth. The writer manages a derived cache only.

Read [requirements](requirements.md), [design](design.md) and the sequential
[implementation plan](tasks.md). The proposed command names and configuration
below do not exist in 1.5.1. This draft makes no runtime qualification claim.

## Relationship to earlier decisions

The [Task 4 design](../task-4-design.md), accepted by
[D18](../decisions-2026-09-22.md#d18-the-six-task-4-decisions-all-as-recommended),
left hydration external. The [format contract](../formats.md) froze what the
legacy reader consumes; it did not promise a packaged writer. This addendum
proposes carrying hydration now, preserving legacy configurations and source
formats. It does not rewrite either historical document.

Approval would authorize a new, opt-in `harness-v1` Redis projection and the reader
support it needs. The old `attune:memory:` prefix, index, function library and
read behavior remain the default for existing configurations. This exception to
the fixed-prefix design is explicit: the new writer does not rebuild live legacy
keys. It is not a conversion of stored Markdown or a new authoritative store.

The [shared-memory requirements](../../shared-memory-adoption/requirements.md)
still supply the preservation, authority, explicit failure and installed-journey
principles. Their old mutation restrictions concerned source stores; this proposal
permits only its own derived Redis projection. Saved-memory capture, scratch,
promotion and the corrections lifecycle remain separate.

## Verified starting point

Checked against Harness `5929c18c542a667a8a175a06b67ca5f2f571b73a`, the fetched
`origin/main`, on October 24, 2026:

- [Redis reads](../../../../src/attune_harness/memory_redis.py#L50-L76) use fixed
  key families and a library; [connection](../../../../src/attune_harness/memory_redis.py#L247-L266)
  requires both the search index and library even for a digest.
- [Serving](../../../../src/attune_harness/memory_redis.py#L455-L493) does not
  hydrate. It returns a banner or an explicit reason. The
  [host filter](../../../../src/attune_harness/memory_serving.py) independently
  checks active membership and authorized file pointers with wrong-verdict
  suppression. The filter currently imports the legacy prefix directly.
- The installed writer is the maintainer's standalone `~/.attune/memory/`
  repository, not a Python import from attune-ai. Its wrapper pulls and sometimes
  pushes that repository, runs hydration, loads Lua and warms recall. The loader
  hard-codes source locations, clears the legacy keyspace, writes a timestamp,
  and then recreates the search index. Neither script was executed here.
- The installed sources inspected have SHA-256 digests below. They are reference
  inputs, not new frozen receipts or files to redistribute with personal content.

| Reference source | SHA-256 |
| --- | --- |
| `~/.attune/memory/hydrate.py` | `396949aa08f81ca2c208dfa64d4e869be7feccf6e8713c2b3ad2ce90db6f6345` |
| `~/.attune/memory/session_hydrate.py` | `c84fe4ec5d4e2545d0000002442b8c8319bb4bb608e1753de37c3edd0181a333` |
| `~/.attune/memory/functions.lua` | `6d5b32469451ce28fbd031bce01caf12320511712c7ca7d53df24f9f8445403d` |

The linked executive-review artifact required sign-in and was not read. The
pasted findings were checked where relevant. No production Redis mutation,
credential-exposure test, paid call or fresh-host observation ran. attune-ai's
deprecation is Patrick's supplied product direction, not a conclusion drawn from
the old migration guide. The cited source lines describe this baseline commit.

## Proposed command journey and refusal walk

All paths below are qualification-fixture paths, populated before the first
command: `memory.json` contains authorized canonical roots and native Redis
selection; `sources.json` maps those roots; their source files exist. Redis is
disposable and explicitly configured, with Search and Functions support. The
installed interpreter has Harness and the pinned Redis extra, with attune-ai absent.
Outputs and receipts live outside source roots. Neither check nor apply calls
`connect()` to bootstrap an empty cache: they use `open_client()` so a missing
projection is a valid first-run state.

This is a static walk, not an execution receipt. Existing `raise` sites are linked
below. New refusals have no source site yet; their proposed owner and required
tests are identified rather than inventing a citation. Task 1 must turn each into
a failing acceptance case before implementation; Task 4 walks the installed
commands and records the actual new refusal sites before this journey is shipped.

| Order and command | Refusal owner and conditions | How the preceding inputs satisfy them |
| --- | --- | --- |
| 1. `attune-harness memory --config /fixture/memory.json hydrate --sources /fixture/sources.json --check` (proposed) | Existing `read_json` uses bounded [regular-file reads](../../../../src/attune_harness/features.py#L81-L94). Root authority is checked by [NativeReader](../../../../src/attune_harness/memory_reader.py#L69-L110); source capture refuses [escape, links, unsafe files, oversize and changed reads](../../../../src/attune_harness/memory_reader.py#L157-L207). Connection uses [explicit URL resolution](../../../../src/attune_harness/memory_redis.py#L112-L129) and [open_client](../../../../src/attune_harness/memory_redis.py#L137-L164). Proposed `memory_hydration` validators refuse unknown source fields, collisions, unsupported server capabilities and unsafe content. | Fixture setup supplies valid UTF-8 JSON, complete authority lists, real canonical directories, unique IDs, supported records and the exact named connection variables. Check reports hashes/counts/capabilities and performs no Redis writes. Native `projection`/`dataset` config validation is new work; 1.5.1 currently refuses those keys. |
| 2. `attune-harness memory --config /fixture/memory.json hydrate --sources /fixture/sources.json --apply` (proposed) | The same checks run again; check output is not approval or a reusable capture. Proposed publication owner refuses stale source capture, incomplete index, function mismatch, full cache budget and compare-and-set conflict. A lost publication acknowledgment is `uncertain` until reconciled. | Apply rereads the same source/config bytes, captures the current publication token before staging and verifies the complete staged generation before switching. First run expects an absent active token, not an existing legacy index. A refusal leaves the prior active generation selected. |
| 3. `attune-harness memory --config /fixture/memory.json redis status` | Existing [hydration preflight](../../../../src/attune_harness/memory_redis.py#L247-L266) refuses missing index/library. New native selection also refuses absent, malformed or foreign manifests and incomplete generations. | Successful apply publishes the generation's validated index, function identity, completed timestamp, counts and authority binding together. Native connection resolves that generation; it never requires the legacy index or library. |
| 4. `attune-harness memory --config /fixture/memory.json serve` | Existing [serve handling](../../../../src/attune_harness/memory_redis.py#L455-L493) distinguishes unavailable and empty results and catches failures. [Filtering](../../../../src/attune_harness/memory_serving.py#L85-L117) can suppress every candidate. Native reads must also reject a generation change before emitting a packet. | The fixture includes an active curated node; the native filter uses the selected generation's membership set. No source-root authority is inferred from Redis. The emitted banner preserves provenance, limits and untrusted-evidence guidance. |
| 5. `attune-harness memory --config /fixture/memory.json serve --for aurora` | Existing search refuses empty or excessive query text and escapes operators in [search](../../../../src/attune_harness/memory_redis.py#L323-L365). File pointers require authorized roots and verdict reads in [FileVerdicts](../../../../src/attune_harness/memory_serving.py#L16-L82). | The seeded query is nonempty and within 512 characters; the projected file pointer resolves inside exactly one configured personal root. A second fixture changes its verdict to `wrong`; that pointer must then be absent. Pointer `text` must never be printed. |
| 6. `python -m attune_harness.memory_hydration_hook --config /fixture/memory.json --sources /fixture/sources.json` (proposed) | New hook owner bounds apply plus serve, suppresses child JSON from stdout, reports degraded hydration and exits zero after any handled failure. No installed hook owner exists yet. | Uses the same installed interpreter and validated config. A successful apply or verified unchanged generation proceeds to serve. On failure, serving an older usable generation carries an explicit degraded diagnostic and its original timestamp. The whole wrapper, including argument/config errors, is tested. |
| 7. Fresh Claude Code and Codex sessions | A process-level wrapper pass is not host delivery. The current [Claude example](../../../cli-guide.md#memory) does not install hooks; no Harness Codex automatic startup hook is established by this draft. | Use disposable host profiles where supported. Record each host/version, actual startup mechanism, delivered banner and exclusion cases. Unsupported automatic startup remains an explicit acceptance gap, not a fabricated hook configuration or a silently substituted manual command. |

## Approval requested

Patrick approved the requirements, generation-based design, opt-in reader extension
and task sequence. Merge, release, workflow dispatch, paid calls, production
hydration and changes to personal host settings remain separate gates.

Read-only Task 1 discovery found supported `SessionStart` surfaces in both hosts:
[OpenAI hook documentation](https://learn.chatgpt.com/docs/hooks) documents startup
context delivery and hook trust, and
[Claude Code hooks](https://code.claude.com/docs/en/hooks) documents the matching
event. Installed Codex CLI 0.153.4 and Claude Code 2.1.293 both have an existing
standalone hydration startup entry. This establishes a usable integration surface,
not a receipt for the new wrapper or permission to change those settings.

Planning checks and unresolved observations are recorded in the draft PR. For
this planning milestone, completion review found the first user-facing gap to be
fresh-session recall already tracked under O-03/O-04/O-12 in the
[opportunity log](../../../opportunity-log.md#current-register). H7 and Task 4
carry that evidence requirement forward; no duplicate backlog item is added.
This review grants no implementation or rollout authority.
