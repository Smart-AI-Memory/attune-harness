# Hydration writer requirements

Status: **approved by Patrick, October 24, 2026**. Implementation may proceed
within these requirements and the retained gates. See the [addendum](README.md).

## H1 — One supported owner

Harness owns the source projection, Redis publication, packaged function assets,
diagnostics and session-start wrapper under the existing optional `[redis]` extra.
No runtime dependency on attune-ai, `attune-redis`, Agent Memory Server, a model
provider or the maintainer's scripts. Base commands continue to load without
Redis installed. Missing Redis support is `unavailable`, never an empty corpus.

## H2 — Explicit sources and unchanged records

The existing memory config authorizes owner, scope, classification and roots.
A separate, versioned sources file references those root IDs and selects the
curated, file, lesson and rule projections. No implicit home directory, project
path, environment search or root discovery. Source files and sidecars are never
rewritten, moved, promoted or deleted. Unknown metadata remains in the original
source, even when it has no Redis projection field.

Read sources with the native reader's authorized descriptor/native-handle
semantics, including Windows checks; never replace those with a plain `read_text`
fallback. Refuse traversal, symlinks, hard links, special files, changes during
capture, conflicting source authority, malformed records and identity collisions
before publication. Apply the existing 8 MiB per-file, 4,096-file and 64 MiB
snapshot bounds across all configured sources, including sidecars.

The reference writer's 32,768-character pointer-body indexing bound may be retained
as an explicit search-index bound. Inspect the complete captured record for
secrets first, report any indexing truncation, and preserve full source resolution.
It does not authorize shortening stored documents or silently omitting files.

## H3 — Compatible recall and separate projection selection

Keep the frozen legacy configuration and read contract unchanged. Native selection
is explicit; absent native state does not fall back to legacy Redis or files.
The native cache preserves the logical node/pointer fields, IDs, type/status
membership, edge meaning, ranking inputs, search schema and bounded result shapes
described in [formats](../formats.md). IDs from search round-trip through node;
related continues to support curated and file IDs only.

Curated active membership and file wrong-verdict exclusion apply at serve time,
using the selected generation and current authorized sidecars. Pointer bodies
remain searchable and never served. Existing saved-memory and scratch operations
and their namespaces are unchanged. The immutable compatibility fixture is not
edited or regenerated. Any intentional difference from the reference writer must
be named, tested and recorded before accepting that implementation task.

## H4 — Failure-safe, bounded publication

Build a complete isolated generation, validate its hashes, index readiness,
function identity and source/config binding, then publish by one conditional
active-manifest update. A concurrent publisher cannot overwrite an intervening
publication with a stale base token. Revalidate the source snapshot before switch.

Failure, timeout or termination before switch leaves the previous active
generation intact. Reconcile a lost acknowledgment by publication identity;
never blindly replay an uncertain switch. A native read uses one immutable
generation and verifies its selection before emitting a packet, or refuses it.
No result combines one generation's body with another's membership or provenance.

Bound generation count, bytes, staging duration and retired-cache retention.
Cleanup touches only proven writer-owned, unreferenced cache resources. Never
scan-delete `attune:memory:*`, replace the legacy function library, flush Redis,
or change server settings. Preserve the current and previous successful generation.
Writer-controlled failure safety does not claim survival of server data loss,
eviction or an operator deleting keys; report missing state as unavailable.

## H5 — Content and exposure boundaries

Check complete records and derived metadata, including edge descriptions, for
blocking secrets before any source content is sent to Redis. Characterize the
reference gate and the existing Harness detector; preserve their blocking cases
and document placeholder handling. An unsafe or malformed input refuses the
batch with sanitized diagnostics. Never echo secret values, source bodies,
password-bearing URLs or raw Redis error text that may contain them.

The configured Redis destination is an explicit exposure decision for the
authorized corpus; a dataset name alone does not establish tenant isolation.
No model calls, remote telemetry, Git synchronization or new provider exposure.
Recalled content remains untrusted evidence, never execution permission.

## H6 — Useful direct and hook diagnostics

Check is read-only, including Redis. Apply explicitly authorizes only projection
effects and returns machine-readable success, unchanged, refusal, unavailable or
uncertain results using existing CLI envelope/exit conventions. Record source and
config digests, generation, prior generation, completed UTC timestamp, counts per
layer, indexing bounds, skipped links and capability results without source bodies.

The packaged session wrapper has a ten-second total deadline, outputs only the
bounded serve banner on stdout and exits zero on handled failure. Direct apply
must not disguise failure as success. An older generation served after failed
hydration retains its timestamp and gets an explicit degraded stderr diagnostic.
Source hashes establish captured bytes, not freshness of a remote Git repository.

## H7 — Installed and host acceptance

Use synthetic, disposable corpora and Redis; never run failure injection against
the maintainer's live memory. Qualify the installed wheel, packaged Lua and CLI
with attune-ai absent. Check all four layers, empty and unavailable states,
malformed/unsafe inputs, concurrent publishers, crashes at publication boundaries,
search readiness, ambiguous identities, retention and reader generation changes.
Assert source bytes and the legacy Redis namespace/library stay unchanged.

Run targeted tests, the full suite and installed-wheel platform qualification.
Read Windows CI evidence before making Windows claims. Live Redis+Search behavior
needs a real disposable service; doubles cannot qualify atomic publication or
index readiness. Retain its exact server/client versions and configuration.

Observe new Claude Code and Codex sessions receiving provenance-bearing recall,
prompt recall where supported, and wrong/inactive-memory exclusion. Keep host
evidence separate. Missing host capability or access remains an explicit gap;
it cannot be closed with unit tests or a manual CLI invocation.

## H8 — Migration, rollback and review

Document a fresh-install path and an existing-user path in the README, CLI guide,
migration guide and Help source. The hydration documentation removes the claim
that this writer requires a running attune-ai installation. Keep release-status
cleanup and other workflow migrations outside this change unless needed for the
new hydration instructions.

Existing users keep the legacy writer/settings until their native projection and
host evidence are accepted. Switching an explicit config back to legacy selects
the untouched legacy cache, whose age is reported; it does not promise fresh data
after its writer stopped. No automatic edit to personal hooks, corpus locations,
Redis settings or frozen evidence. Obtain a different-model or Patrick review
covering the final `src/` head before any implementation merge is proposed.

## Non-goals

No corpus authoring/conversion, saved-memory auto-recall, correction promotion,
file-derived digest replacement, AMS integration, provider calls, automatic Git
pull/push, credential-inheritance remediation, Python-matrix expansion, lint or
coverage-policy changes. No merge, tag, release, workflow dispatch or production
rollout is authorized by this draft.

## Done when

H1–H8 have source-bound evidence or an explicit unresolved gate; unresolved gates
do not count as completion. A fresh Harness-only installation completes the
documented hydration/serving journey, both host observations are accepted, and
rollback leaves original sources and the legacy contract intact. Implementation
completion includes the proportional completion review; publication is separate.
