# Memory serving: implementation design, September 24, 2026

Implements Phase 3.3 under [D21](decisions-2026-09-23.md). The
[session observations](observations-2026-09-24.md) record Patrick's feedback
and his decision to restore missing workflows immediately after 0.6.0.
This note does not claim a completed week of dogfooding or a real hook receipt.

## Contract and cases

- SessionStart keeps Redis `recall_digest` ranking. Prompt mode adds
  `memory serve --for PROMPT`, using the existing escaped full-text search,
  at most 512 query characters and 100 candidates. Both filter before limiting
  the output. Empty or excessive prompts produce no memory, never a fallback
  to the unrelated global digest. No prompt is printed in the banner.
- Curated nodes must still belong to `attune:memory:status:active` when the
  host checks the candidate IDs in one bounded `SMISMEMBER` read. Membership
  failure produces no banner. This is a read-time check, not a lease on the
  memory's future status.
- A file pointer must have a path inside exactly one configured, authorized
  personal or curated root; its ID stem must match the path stem. Redis
  `corpus` is not authority. Roots use the existing native-reader contract,
  with no inferred home directory or new config field. Unmapped or ambiguous
  pointers are omitted. Redis-only configurations still serve curated nodes.
- Read `.verdicts.jsonl` through the native reader's bounded descriptor walk,
  once per relevant root. Missing logs mean no recorded verdict; malformed,
  unreadable, symlinked or hard-linked logs suppress that root's pointers.
  Apply the last valid record's verdict per stem: `wrong` suppresses regardless
  of digest or age. Do not infer other lifecycle rules. Bound total sidecar
  bytes to 8 MiB. Lessons and rules retain their existing pointer semantics.
- The compact banner identifies Redis, hydration and retrieval method, says
  the contents are untrusted evidence rather than instructions, and asks the
  receiving model to disclose influence by memory ID. Keep node-line and
  character budgets, including the existing header/footer floor. Flatten
  control characters in all displayed metadata. Pointer `text` is never shown.
- Failures leave stdout empty and the hook exits zero. Direct diagnostic
  `memory redis` reads retain their contracts. No writes, hydration changes,
  MCP surface, paid calls or new dependencies.

## Disposable experiment and alternatives

A scratch in-process Redis double returned a `withdrawn` digest row while
its active set contained only `n1` and `n2`. Baseline `serve` printed the
withdrawn row and issued no membership read. This establishes the independent
filter gap without touching live memory.

Rejected: trusting Lua alone (does not protect search or a stale response);
reading a directory supplied only by Redis (not host authority); adding a new
corpus mapping (existing explicit roots already define authority); calling
`latest_verdicts(path)` directly (unbounded read, follows links, suppresses
read errors); treating an unreadable log as empty (can revive tombstones).

## Acceptance and release evidence

Tests cover stale digest/search results, no surviving candidates, membership
failure, missing/invalid/oversized verdicts, last-verdict wins, stem mismatch,
root traversal/overlap and symlinks, prompt escaping/bounds, pointer-body
exclusion, sanitized provenance, and unchanged diagnostic reads. Then run the
full suite and the installed-wheel platform qualification; Windows must show
its existing descriptor-reader refusal, not claim POSIX equivalence.

Still required before closing 3.3: a real fresh session gets the provenance
banner, its prompt hook gets related memory, and corrected/inactive examples
stop appearing. Synthetic tests do not stand in for this receipt. Independent
review covers the implementation before merge. PyPI upload is not authorized
by the instruction to prepare it.
