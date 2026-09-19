# Shared memory adoption — design

Status: implementation plan approved by Patrick on 2026-09-17; All five tasks accepted; canonical completion revision 23. Live activation and release remain outside this plan.
Auto-run authorized for Tasks 2–5; pause on serious findings.

## Verified starting points

Read-only inspection used Harness HEAD
`fc65e74fc7c289f71f3a7d081dfe7c1be1238c33` (dirty) and Attune AI HEAD
`fe08f282fb0ad9cbb7eedf75af2597336576578e` (main, one unrelated untracked snapshot).
Neither checkout was switched, cleaned or updated. Attune AI collaboration
preflight passed 87 governance tests with two working-tree warnings and unchanged
repository status; remote freshness was not checked.

Attune AI implementation will use a new isolated checkout at
`/Users/patrickroebuck/attune-ai-memory-adoption`, branch
`codex/shared-memory-adoption`. The destination was absent during planning.
Task 1 verifies the baseline and applicable instructions after creating it;
the original main checkout is a read-only reference. Source paths in the table
below are relative to the owning repository, not a second copy under Harness.

The [isolated journey](../../research/memory-journey-results-2026-09-16.md) passed
253 central checks and four native calls. It exercised one note and a cooperating
wrapper around actual temporary FileStashBackend files. Its receipts and source
files remain frozen. It did not qualify a live memory service or receiving agent.

| Existing surface | Verified behavior relevant to adoption |
|---|---|
| AI `src/attune/memory/session_stash.py` | Five raw kinds; 500-character limit; sanitization; backend resolution; soft cwd recall ordering; unconfirmed upgrade writes can divert to file |
| AI `src/attune/memory/file_stash.py` | Actual append/search/forget; duplicate IDs possible; no expected-version update API |
| AI `src/attune/memory/personal.py` | Four document kinds, global/project roots, retrieval summaries, grounding/polish, provenance and staleness annotations; query also emits serve telemetry |
| AI `src/attune/memory/promotion.py` | Curated Markdown type mapping and review provenance; distinct from raw notes |
| AI `src/attune/memory/recall_digest.py` | Redis-derived curated serving; fetching also emits telemetry |
| AI `src/attune/memory/serve_telemetry.py` and `src/attune/telemetry/memory_events.py` | Local memory event sink, opt-outs and best-effort writes; serve counts support memory maintenance |
| AI `src/attune/telemetry/usage_tracker.py` and `usage_ping.py` | Local usage accounting and a separate default-off remote uploader; the singleton registers an exit-time upload hook |
| AI `src/attune/memory/provenance.py` | Untrusted-evidence framing and instruction-shape flags; ordinary procedural memory must not be discarded |
| AI `src/attune/mcp/memory_handlers.py` | Working/long-term and personal operations; documented ungoverned search path cannot be assumed safe for worker exposure |
| AI `src/attune/memory/unified.py` and its mixins | Existing keyed working-memory and persisted-pattern consumer, reached by MCP store/retrieve/forget; retained paths require their own baseline fixtures |
| AI `src/attune/cli_minimal.py` | Existing memory subcommand parser and handler dispatch; add a lazy `memory worker` route, retain current memory commands |
| AI `src/attune/cli_commands/memory_agent.py` | Existing Anthropic-specific raw-API agent, distinct from the new Luna worker |
| Harness `src/attune_harness/attune_bridge.py` | Existing explicitly activated Attune plugin pattern for retrieval; not a memory adapter |
| Harness `src/attune_harness/mcp_server.py` and `extensions.py` | Current retrieval-only bindings; memory operations cannot be enabled by silently widening these grants |

These are code observations, not new runtime/security qualification. No live
memory query, model call or mutation ran while drafting this plan.

## Shared ownership and staged integration

Proposed production modules:

- Harness `memory_contract.py`: provider-neutral records, source references,
  scoped proposals, separate logical kinds/security labels and adapter capabilities.
- Harness `memory_worker.py`: durable host policy, claimed jobs, routing, sampled
  review, current-state validation and explicit outcomes, reusing RunStore.
- Harness `memory_context.py`: scoped retrieval envelope, source pointers and
  generation validation for receiving agents.
- Harness `memory_cli.py`: an explicit memory entry point using the shared service.
- Harness `memory_bridge.py`: optional Attune AI plugin integration, following
  the existing bridge pattern without importing AI from the base package.
- AI `src/attune/memory/harness_adapter.py`: optional consumer of the shared core,
  mapping existing services and exposing only operations actually qualified.
- AI `src/attune/cli_commands/memory_worker.py`: lazy CLI handler selected by
  `attune memory worker`, importing the shared implementation only when invoked.

The installed AI CLI route and the explicit `MemoryWorkerPlugin` launcher must
reach the shared durable worker. For MCP, register distinct scoped memory-worker
tools through `register_mcp_tools` on the actual Attune server; do not replace
`MemoryHandlersMixin` by implication. Installed tests enter through the real CLI
and MCP listing/call transport, observe the resulting worker record, then disable
the optional route and check the original commands.

Provider profiles remain configuration, with the measured Luna/high routine
candidate and Astra/xhigh stronger candidate. The shared contract does not require
either vendor. Reuse the repaired citation semantics and strict no-tools transport
profile where qualified; do not silently substitute Harness's general native
translator, whose own documentation does not promise tool isolation.

First deliver current-format recall and compare it with the existing path. Use
explicit roots/backend instances; isolate telemetry and caches during probes.
Personal and curated documents retain their format, corpus ownership and full
content. Redis/index results remain derived views. Retaining a source pointer
requires an actual scoped resolver, not a claim that a truncated excerpt is the
whole memory.

PersonalMemory's current combined query can deduplicate same-relative-path hits
across roots, and `forget_topic` covers both roots. The new reader therefore
queries explicit single-root instances and attaches a host-issued root identity
before merging results. A fixture with the same relative path and different
content in global/project roots must return both identities correctly. Personal
worker mutation stays unavailable until a root-bound exact-record API is
qualified; never map one-record deletion onto `forget_topic`.

| Tier | First adoption profile |
|---|---|
| Raw session findings | Current-format recall; managed note mutations only after strict service/concurrency qualification; other kinds keep existing operations until mapped |
| Personal documents | Root-bound shared recall and full-source resolution; existing authoring/forgetting remains the existing path, not a new worker mutation |
| Curated documents | Provenance-preserving read access and existing reviewed promotion; no automatic promotion |
| Keyed working memory | Retain current supported key/value path and test compatibility; worker access requires explicit backend/ownership capability |
| Persisted long-term patterns | Retain existing governed retrieval path and test compatibility; no direct use of the documented ungoverned search for worker exposure |

Task 1 may expand this inventory based on actual callers. A retained existing
path is not labeled newly worker-qualified, and an unsupported new operation
must not conceal that existing path.

Then deliver managed mutations only for the qualified service/backend combination.
Reuse sanitization and provenance policy through an explicit service seam; calling
the low-level file backend alone does not preserve those controls. Existing
`stash_entry` can divert an unconfirmed write, so it cannot simply be wrapped as
an exactly-once managed operation. Provide a strict explicit-backend operation
with visible uncertainty while preserving legacy call semantics. A new lock is
insufficient if an old writer can ignore it; qualify coexistence or refuse new
managed mutations for that configuration.

No package dependency cycle: Harness core never imports Attune AI; the optional
bridge is loaded only in an AI-capable environment. Installing the optional AI
worker support supplies a compatible Harness distribution. Standalone Harness
without the compatibility adapter reports that adapter unavailable rather than
creating an empty replacement corpus. Dependency versions are fixed when building
the first integration artifact, not guessed from the research environment.

## Preservation, migration and rollback

Reading existing records in place is the default design. Do not re-author,
reclassify, compress, delete or move a corpus merely to enable Harness. A necessary
format conversion would be a separate proposal with source/destination inventory,
content checks, retained originals and a demonstrated rollback.

The first product change is additive and explicitly selected. Existing commands,
recall hooks, personal memory, curated promotion and backend preferences continue
to work. The feature matrix distinguishes existing support, new read support,
proposed mutations and qualified mutations; partial worker coverage must never
be presented as loss of the other memory features.

Memory has two availability policies: user work continues if optional recall is
unavailable, with a legible degraded result; a governed mutation or evidence-bound
decision must stop when its required checks are unavailable. Neither policy grants
permission to expose a different corpus or make a second uncertain write.

## Strongest counter-case and verification

Extracting another shared abstraction could delay a simple useful integration
and leave two systems to maintain. Limit the extraction to the tested worker
contract and real service/context seams; prove current-memory reuse first and
keep storage ownership with existing services. No new database or perpetual
stronger router is proposed.

Use actual disposable files, selected legacy-format fixtures and isolated service
instances for the baseline. Compare full content and relevant retrieval results,
not only IDs or schema validity. Required negative cases include foreign/sensitive
content before model dispatch, secrets, missing sanitizer, source injection,
stale policy/version, duplicate/uncertain effects, partial deletion, incompatible
type mappings, unknown legacy fields and telemetry escaping the scratch root.

Run installed integration and receiving-context probes in both products. Native
consumer tests require a separately frozen packet with exact profiles, calls,
rubrics and timeout/spend bounds under applicable authorization. The four completed
journey calls do not authorize a new campaign or prove natural-workload savings.
Initial planning and deterministic integration work need no paid provider calls.

## Telemetry by purpose

Patrick clarified and accepted on 2026-09-17 that the restriction concerns
product-usage collection, not all outbound data. Preserve explicitly configured
team coordination, shared memory and operational reporting. Existing Redis
EventStreamer/CoordinationSignals paths use a separate transport; verify they
remain functional when the usage ping is disabled. A custom usage-ping endpoint
does not by itself establish a team-operation purpose; team features reusing that
legacy uploader require separation and remain outside the new support claim.

Patrick confirmed that collecting usage information from remote users is no
longer needed. Preserve useful local memory-serving feedback, diagnostics and
cost accounting, with existing opt-outs. The shared worker does not require
remote usage collection. Trace startup and shutdown paths as well as direct
calls: the existing UsageTracker singleton registers a separate opt-in uploader
at exit. Do not accidentally activate that path just to obtain local accounting.

Use isolated sinks and intercepted transports to prove the new path keeps local
events working without usage uploads, including with legacy upload opt-in enabled.
This distinction does not prohibit explicitly authorized model-provider calls.
Optional telemetry failure must not cost a recall result; mandatory durable
operation/version records are control state and retain their stronger guarantees.
Track product-wide uploader and hosted-endpoint retirement separately. No existing
upload setting, deployed service or collected data changed during this planning.

## Follow-up: qualified writer protocol for legacy stores

Recorded on 2026-09-19 during post-acceptance review. This is the work that would
unblock new managed worker mutations; it is not part of the accepted five-task
ladder and adds no release blocker to it.

Task 3's disposable legacy-lock probe held one writer active, aged its lock file,
and a second writer obtained the lock. Existing file writes have no expected-version
update, can produce duplicate identifiers, and may divert a lost acknowledgment
into another tier (see [adapter-design.md](adapter-design.md)). The shared route
therefore qualifies current legacy directories for reads only, and the strict stash
seam reports acknowledged/refused/uncertain without granting worker write capability.
Until this follow-up is delivered, the worker's routine sorting and maintenance role
can propose and replay decisions but cannot apply them to existing stores.

Questions to settle when this work becomes timely:

- What serialization and versioning can every writer honor, including legacy
  callers that ignore a new lock, without converting or moving the corpus?
- How are record identity and operation replay demonstrated per R5, and how is an
  uncertain effect reconciled rather than retried or diverted?
- What root-bound exact-record API lets personal documents be corrected or removed
  without mapping onto cross-root `forget_topic`?
- Which tier qualifies first, and what disposable concurrent-writer evidence on each
  claimed platform would justify changing its row in the support matrix?

Read-in-place, preserved existing commands and conversion-free rollback continue to
apply. No protocol, schema, migration or schedule is selected by this note.

## Deferred: user, project and team access separation

Patrick identified this as a future need on 2026-09-17 and explicitly said it is
not immediate. Retain it for later design work; do not expand the current task
ladder or introduce a new release blocker. Existing owner/scope/exposure checks
in the approved requirements still apply now.

Starting distinction: a memory's project relevance, owner and permitted audience
are separate dimensions. A user's project-specific note can remain private;
putting it in a project folder or ranking it for that project is not permission
to expose it to teammates. The legacy raw stash's cwd ranking demonstrates why
storage organization alone cannot establish this boundary.

Questions to investigate when this work becomes timely:

- How is a caller's identity established and bound to authorization, separately
  from labels supplied in a request or record?
- How should private user-wide, private project-specific and explicitly shared
  team knowledge coexist without copying personal preferences into the product?
- How are sharing, role changes and revocation represented and enforced across
  CLI, MCP, agent delegation and backend operations?
- Which retrieved excerpts, indexes, caches and receiving-agent contexts inherit
  restrictions, and what can actually be invalidated after access changes?
- Which cross-user/project and revoke-after-retrieval cases would demonstrate
  separation using installed consumers rather than configuration checks alone?

Reuse the existing research and adapter evidence, then consult applicable primary
industry and academic sources for a concrete design question. Compare approaches
in bounded experiments before choosing an implementation. No new identity
service, storage schema, migration, sharing action or research campaign is
selected by this note.
