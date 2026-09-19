# Voyage validation reuse

Status: task ladder approved for execution, September 16, 2026. Task 1 is in
progress; no task has yet been accepted. This is work in **attune-harness**,
not the legacy attune-rag package.

## Outcome

Remove the immediately repeated full-generation validation at retrieval entry
without weakening source freshness, scope, database integrity, paid-stage recovery,
or returned-evidence checks. Keep hybrid retrieval and Voyage reranking unchanged.

## Acceptance

- **R1 — One checked entry.** A metric probe reports one fewer full-generation
  check on each nonempty retrieval path: direct recompute 4 to 3, direct cache
  replay 3 to 2, session recompute 6 to 5, and session replay 5 to 4. Session setup
  remains one check. Empty-scope behavior remains a zero-provider no-results path.
- **R2 — Selection compatibility.** Behavioral tests retain structural, digest,
  normalized-path, generation and scope validation. The existing public
  load-selection function still validates fully and returns its input object.
  Accepted tasks, generation IDs, index files, receipts and public schemas remain
  compatible; an existing generation must not require rebuilding for this change.
- **R3 — Integrity boundaries.** Behavioral tests reject changed source bytes
  (including equal-length edits), changed Git revision, newly selected/deleted
  files, modified metadata/publication records and changed database text or
  vectors before dispatch or evidence delivery at the relevant boundary.
  Repeat/cache calls must validate again. A change introduced during embedding,
  candidate search or reranking must not cross the next existing guard.
- **R4 — Scope and effects.** Behavioral tests preserve exclusion before candidate
  text upload, finite tool/provider budgets, reserve-before-embedding behavior,
  full-budget completed-stage replay, and refusal to retry unknown paid effects.
  Zero provider permission must suffice when only completed stages are replayed.
- **R5 — Lifecycle.** The existing session, plugin, standalone MCP and recovery
  suites retain request/grant change detection, closure and persistence-failure
  behavior. Checks surrounding extension dispatch stay in place.
- **R6 — Failure-sensitive evidence.** A suite receipt records which relevant
  guard removals are detected and the number of new tests failing with each guard
  removed. Preserve failures; green unmodified tests alone do not prove a guard.
- **R7 — Artifact and timing.** Run baseline and changed implementations in
  separate processes with matching dependencies, fixtures, queries and cache
  states. Verify module hashes for a separately installed wheel, run its consumers
  outside the source tree, and retain timing samples and check counts. Repeat in
  reverse order during implementation qualification. Report inconclusive timing
  honestly; the six-query planning probe is not a speed guarantee.

## Scope

Production changes are limited to the selection-validation helper in
`src/attune_harness/voyage_index.py` and its retrieval caller in
`src/attune_harness/voyage_retrieval.py`. Tests, a reusable offline measurement
script, and this spec's verification report support those changes.

No session-wide cache, clock/mtime cache, hash-format migration, new provider call,
automatic exact-lookup fallback, query algorithm change, desktop configuration
switch, package release or legacy-package migration belongs to this increment.

The most important later product test remains paired real-application coding
tasks. A useful test application and genuine tasks have not yet been selected;
this does not block the offline latency increment.
