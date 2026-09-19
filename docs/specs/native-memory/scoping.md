# Native memory — scoping note

Status: scoping draft, 2026-09-19. Not an approved plan. No task below is
authorized, started or scheduled. Successor to
[shared memory adoption](../shared-memory-adoption/requirements.md), which stays
unchanged as the accepted record of the adapter architecture and its evidence.

## Why this exists

Harness is the successor to attune-ai, and memory is among Patrick's most valued
features. The accepted adoption gave Harness the contract, worker, context packets
and CLI, but the adapter that actually reads memories lives in attune-ai
(`attune.memory.harness_adapter`) and uses attune-ai's services. The 2026-09-19
installed build check confirmed the consequence: with attune-ai absent,
`attune-harness memory capabilities` reports `unavailable` and exits 2. Harness has
no packaging dependency on attune-ai, but its memory feature has a functional one.
A successor cannot retire its predecessor while that holds.

## Direction Patrick set on 2026-09-19

- **N1.** Incorporate memory natively in Harness and cut the functional tie to
  attune-ai.
- **N2.** Port the reader, not the whole memory system. The accepted spec's narrow
  cut applies: read existing formats in place, with the sanitizer and provenance
  checks. Grounding, polish, promotion authoring and other attune-ai surface are
  not carried over by default.
- **N3.** The base is stdlib-only, provided Redis and its benefits are not
  sacrificed. Stdlib-only file implementations live in the base; Redis sits behind
  an optional `[redis]` extra, loaded lazily like the existing Voyage and MCP
  extras. Patrick wants the Redis solution and a fallback for people who do not run
  Redis. The backend is chosen at startup from configuration. A configured but
  unreachable Redis is reported as unavailable; a write is never diverted to the
  file backend at runtime. That divert is the defect Task 3 of the adoption spec
  reproduced in the legacy stash.
- **N4.** The Task 1 compatibility fixtures become the format contract. While
  attune-ai still writes memories, its memory formats are in maintenance mode: no
  format changes.
- **N5.** Two copies of security-sensitive code are acceptable only as a bounded
  transition, with explicit tasks to end it (see the ladder).
- **N6.** This is a new spec. The predecessor's evidence is bound to the adapter
  architecture and is not retrofitted.
- **N7.** Memory must reach agent sessions, not only be readable. Patrick's
  experience of the feature, mostly in Claude Code, is a model volunteering that a
  memory influenced it. In attune-ai that comes from hooks injecting memory at
  session start and on recall. Readers and a CLI alone would ship the feature
  without the benefit.
- **N8.** Corrections are an intake stage, not enforcement. Patrick has used memory
  to catch a model before it repeats a behavior. That is steering through context,
  not training: it works only when served, and similarity or recency recall does
  not fire because the model is about to act. The intended lifecycle is memory
  first, then the instruction file if the behavior recurs, then a mechanical gate
  if it matters enough, with a human review deciding each promotion.

## What moves, what stays

| Area | Proposed handling |
|---|---|
| Raw session findings, personal documents, curated documents | Native stdlib readers in Harness; read in place; root identity plus record identity preserved |
| Sanitizer, provenance and instruction-shape checks | Ported, with differential tests against attune-ai's implementation while both exist |
| Retrieval ranking over documents | Through the existing optional `rag` extra; absent extra is reported, never an empty corpus |
| Working memory (shared scratch) | Native capability behind one small backend interface: stdlib file store by default, Redis under the `[redis]` extra. Each backend declares its capabilities; the file store does not pretend to offer cross-machine sharing, signals or semantic search. Legacy `current.json` and `kv.json` are not read: scratch data has no accumulated value |
| Redis semantic search, coordination signals, curated recall digest | `[redis]` extra. Without Redis the digest needs a file-derived equivalent or is reported unavailable |
| Persisted patterns | Deferred; stays on the attune-ai path. It runs through a security subsystem whose encryption was never qualified and whose policy lets unstamped INTERNAL records be read cross-user. Patterns are reached only by explicit MCP calls, not injected, so they are unlikely to be the source of the influence Patrick has seen. Likely exit at retirement: reviewed promotion of valuable patterns into curated documents, under its own proposal. Reopen if the pattern audit log shows regular retrievals |
| Serving memory into agent sessions | New native work (N7); see the ladder |
| Corrections lifecycle and review | New native work (N8); see the ladder |
| Grounding, polish, promotion authoring, memory-agent | Stay in attune-ai unless a later decision ports them |
| Contract, worker, context, CLI, bridge | Already in Harness; unchanged |

## Redis, checked in source on 2026-09-19

`attune_redis` declares `attune-ai>=3.5.0`, `agent-memory-client` and `redis` as
dependencies, so Redis support is currently tied to attune-ai in packaging. Its
package docstring states that submodule imports are kept free of `attune` so another
environment can import them; only `plugin.py` needs the attune framework. The
backend therefore looks portable, and cutting the tie is a packaging question, not a
rewrite. Options to weigh: move the backend into Harness under the `[redis]` extra,
or republish `attune-redis` without the hard attune-ai dependency. Not yet verified:
that `memory.py`, `config.py` and `signals.py` import cleanly with attune-ai absent.
A stdlib Redis client is rejected; it would reimplement connection, auth and TLS
handling for no user benefit.

## Owner-authored rules versus recalled evidence

The adoption spec's R4 says recalled content stays evidence, not action authority,
and the provenance code frames instruction-shaped memories as untrusted. That is a
sound defense against injected instructions. It also works against N8, where Patrick
deliberately uses memory to direct the model. Both needs are valid and should be
separated: a correction Patrick authored is an owner-authored rule with a recorded
author and scope; anything else recalled remains evidence. How that authorship is
established and protected from forgery is a design question for the successor spec,
not settled here.

## Candidate task ladder

Sequential where a task consumes the previous result. Ordering and scope are
proposals for the successor spec, not commitments.

1. **Map the dependency.** Record exactly which attune-ai calls the current adapter
   makes, per tier, and which of them the narrow reader needs. Confirm the fixtures
   cover each.
2. **Native readers.** Stdlib readers for the three file tiers. Done when the
   existing compatibility fixtures pass in an installed environment with attune-ai
   absent, and results match the adapter path where both are available.
3. **Port the controls.** Sanitizer and provenance checks in Harness, guarded by
   differential tests: same inputs through both implementations, same outcomes.
   This is the N5 duplication guard.
4. **Backend interface and Redis extra.** One working-memory interface with declared
   capabilities. Reach the Redis backend without attune-ai; lazy import; startup-only
   backend selection per N3. Absence and disconnection are reported distinctly from
   no matching memory.
5. **Native versioned store and writer protocol.** Absorbs the
   [writer-protocol follow-up](../shared-memory-adoption/design.md): design
   versioned serialization natively instead of qualifying legacy writers. The file
   working-memory backend is the first tenant, because losing scratch data is
   harmless while the design is proven. Legacy stores stay read-in-place; no
   conversion without a separate proposal.
6. **Serving path (N7).** Deliver current authorized memory into Claude Code and
   Codex sessions through hooks or plugin integration. Done when a fresh session
   receives relevant memory without an explicit command, the model's disclosure of
   a memory's influence is preserved as a requirement, and corrected or forgotten
   memories stop being served. Closes the adoption spec's unqualified automatic
   receiving-agent refresh.
7. **Corrections lifecycle and review (N8).** Corrections become a distinct kind.
   A duplicate correction increments a recurrence count instead of being discarded,
   because it means the behavior came back. Serving may bind a correction to the
   event it concerns, such as a pre-tool hook before a push, rather than relying on
   similarity recall. A review lists each correction with age, serve count from the
   existing local telemetry, recurrence count and matched gate or review findings,
   and proposes keep, promote to the instruction file, draft a gate, or retire.
   Patrick decides through the existing forms grammar. Promotion produces a proposed
   edit or a drafted task; nothing promotes itself. Done when a recurring synthetic
   correction is surfaced for review and an accepted promotion produces the proposed
   instruction-file edit.
8. **Switch the default.** `attune-harness memory` uses the native reader; the
   attune-ai adapter remains selectable as a fallback. Installed qualification with
   attune-ai absent, and rollback to the adapter path without data conversion.
9. **End the transition (N5).** Declare attune-ai memory formats frozen; remove the
   differential tests and the adapter fallback once attune-ai stops writing; settle
   the fate of `attune_bridge.py`, the `harness` extra and `attune-redis`'s
   attune-ai dependency.

## Consequences for work already in flight

- The `codex/shared-memory-adoption` branch in attune-ai becomes a transitional
  bridge. Merging it to attune-ai main is optional, not a goal.
- The urgency to publish Harness to PyPI came from unblocking `uv lock` for that
  branch. That urgency is gone. Publishing `0.1.0.dev14` remains worthwhile on its
  own terms and is unaffected by this note.
- The test-named product modules follow-up in the opportunity log is independent.

## Open questions

- Does the pattern audit log show regular retrievals? If so, the deferral of
  persisted patterns is reopened.
- What can honestly count as a recurrence signal beyond a repeated correction, and
  how are gate failures matched to a correction without guessing?
- How is an owner-authored rule distinguished from forged instruction-shaped
  content in a memory store?
- Does cross-platform reading need qualifying? The current adapter's reads are
  POSIX-only and tested on macOS.
- Where do the local memory-serving feedback and accounting events live once the
  reader is native?
- What is the retirement signal for attune-ai's writers: a date, a version, or an
  observed period with no writes?

No protocol, schema, storage format, hook, migration, release or schedule is
selected by this note.
