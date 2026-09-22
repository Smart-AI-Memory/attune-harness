# Shared memory adoption

Status: implementation plan approved by Patrick on 2026-09-17; All five tasks accepted; canonical completion revision 23. Live activation and release remain outside this plan.
Auto-run authorized for Tasks 2–5; pause on serious findings. No live memory migration authorized
by this document. Owning project: attune-harness; consumer: attune-ai.

## Outcome and user direction

Both products use one maintained memory-worker contract: Luna handles routine
sorting and maintenance, explicit host rules route known difficult work to a
stronger participant, and sampled semantic review checks confident mistakes.
Harness can use the memories accumulated through Attune AI. Their continued
usefulness, meaning, provenance and discoverability are first-class acceptance
criteria, not a cleanup opportunity.

Patrick selected adoption in both products, emphasized that memories are among
his most valuable features, and confirmed reuse of Attune AI memories by Harness.
The first integration priority is reading existing memory formats in place.
Preserve existing command behavior and data while qualifying new worker operations.

## Acceptance

- **R1 — Preserve useful memory.** Existing raw-session, personal-document,
  curated-memory, keyed working-memory and persisted-pattern fixtures remain
  readable through their supported paths. Full
  source content, identifiers, scope, provenance, type and links are retained.
  Summaries are retrieval aids, never replacements for source records. Test long
  documents, corrections, contradictory/superseded evidence, global/project
  overlap (including identical relative paths in different roots), references
  and legitimate procedural instructions. Root identity is part of record
  identity; never collapse distinct records merely because paths match. No arbitrary
  trimming or forced conversion into the prototype's short-note schema.
- **R2 — One shared worker.** Production contract/routing/state code belongs to
  Harness; the Attune AI integration consumes it. Production imports no module
  from experiments. Harness's base remains dependency-free; storage/provider
  packages load through explicit optional adapters. An absent optional adapter
  is reported as unavailable and does not silently claim an empty memory corpus.
- **R3 — Preserve the tested controls.** Host-owned input/version binding,
  exact operation scope, duplicate prevention, evidence checks, explicit task
  routing, separate reasoning/evidence/decision outcomes and sampled review
  remain enforced. Known difficult work routes directly to the stronger role;
  successful routine work is not routinely repeated by that role. No cost or
  general model-quality claim follows from the existing small trials.
- **R4 — Guard the real boundary.** Security/sensitivity, applicable sanitization,
  owner/project scope and permitted provider exposure are checked before sending
  memory to a worker and before effects. Logical kinds are separate from security
  classifications. Recalled content stays evidence, not action authority. Existing
  curated-promotion decisions are preserved. A blocked write does not block the
  unrelated user task or bypass controls through another backend.
- **R5 — Safe effects and coexistence.** Apply only on an adapter with demonstrated
  version/concurrency, identity and operation-replay behavior. Explicitly reconcile
  uncertain effects; do not infer absence from a missing acknowledgment or divert
  an uncertain write to a second store. Characterize legacy writers that bypass
  new locks before enabling shared mutation. State deletion's exact tier/record
  scope; invalidate refreshed context without claiming historical erasure.
- **R6 — Useful receiving-agent context.** Both entry points deliver current
  authorized facts plus retrievable source/provenance to the consuming agent.
  The stronger agent can receive relevant memory without being its sorter.
  Corrections and deletions invalidate old context handles; disconnected services,
  stale data, partial retrieval and omitted context are distinguishable from no
  matching memory. Compare relevant hits and retained meaning with the baseline.
- **R7 — Installed qualification and rollback.** Build and test actual installed
  consumers outside source trees. The common core must import without Attune AI;
  Attune AI's original memory features must work without the new optional worker.
  Disabling the new route restores the prior path without data conversion.
  Qualify platform-sensitive locking and paths on each claimed platform.
  Enter installed tests through `attune memory worker` and the Harness CLI,
  plus the explicitly activated Attune MCP plugin where advertised; direct
  adapter instantiation alone is insufficient product-integration evidence.
- **R8 — Keep telemetry's useful local purposes.** Preserve local memory-serving
  feedback, reliability diagnostics and usage/cost accounting where applicable,
  including their existing opt-outs. Remote-user usage collection is no longer
  a requirement and must not be introduced as a dependency of the shared worker.
  Trace emitters and consumers by purpose; verify local behavior with isolated
  sinks and no usage uploads from the new route, including process shutdown.
  Required durable operation records remain distinct from optional telemetry.
  Retirement of the existing product-wide uploader and hosted collection endpoint
  is a separate follow-up; this plan does not claim they have been removed.

## Done when

One optional shared worker is usable from both products; current-format recall
passes the above checks using disposable data. New managed worker mutations are
unavailable on current legacy stores, which lack qualified serialization (see
[adapter-design.md](adapter-design.md)); a qualified writer protocol is a separate
follow-up. All existing memory capabilities retain an available supported path, with
an explicit matrix of which new adapter operations are qualified. Installed
receipts identify actual source/dependency versions and limitations. Live rollout,
release and any data conversion are separately identifiable actions, never implied
by passing unit tests. The existing plan/build draft remains outside this scope.

The tiny experiment's eight-note/500-character limits are experimental limits,
not product requirements. Capability limits must be explicit and must not make
existing memories disappear. More kinds/backends can retain their current path
until equivalent worker integration is demonstrated.
