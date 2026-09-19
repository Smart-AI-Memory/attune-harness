# Current-memory adapter implementation note

Task 2 is accepted through the approved auto-run policy: 63 tests, five detected
protection-removal probes, and both independent-review findings repaired/closed.

Implementation verification additionally binds source handles to device/inode,
mtime/ctime/size and content digest. POSIX descriptor walks refuse symlink swaps,
hard links and nonregular files. Existing readers rank private temporary snapshots
of authorized bytes; originals stay unchanged. Source bytes and timestamps are
captured from the same held descriptor, closing the directory-swap age race. Snapshots preserve summary and
review sidecars and original modification times, so retrieval and age/provenance
do not change merely because the reader was isolated. Sidecar changes invalidate
document handles. Bounds are 8 MiB per file, 4096 Markdown files and 64 MiB per
document query snapshot; over-limit roots are visibly unavailable. Only macOS
has been tested. These reads are unavailable on non-POSIX platforms pending a
separate implementation/qualification; no Linux filesystem qualification is claimed.

The adapter reads explicit existing roots in place. Root identity plus record
identity prevents cross-root collisions. Scope/owner/classification are explicit
host configuration, never inferred from a model's logical kind. Raw rows must
match an authorized cwd exactly; legacy cwd ordering is not isolation. Personal
and curated documents retain full bytes, frontmatter, links and provenance.
Keyed memory and governed pattern retrieval retain their existing paths.

Cases: root collisions; long records; unknown metadata; absent RAG; missing roots;
empty results; malformed raw rows; exact scope; source path traversal and symlink
escape; source corrected/deleted after retrieval; unavailable sanitizer; secrets;
unknown classifications; provider profiles outside policy; lost write acknowledgment.

The actual disposable legacy-lock probe held one writer active, aged its lock
file, and obtained a second writer lock. Existing file writes also have no CAS
and may divert a lost acknowledgment into another tier. Therefore shared legacy
directories qualify for new reads, not worker mutations. This follows the approved
Task 3 rule: configurations without proven serialization/versioning remain
unavailable for new managed mutations. No separate replacement corpus is created.

Add an explicit-backend strict stash seam that reuses the existing sanitizer,
rejects truncation, makes one call only, reports acknowledged/refused/uncertain,
and never diverts. This is not an exactly-once managed commit and does not grant
worker write capability. Preserve the original function/defaults for old callers.

For honest availability, add a keyword-only strict query option to PersonalMemory:
existing callers retain best-effort behavior; the new reader receives underlying
errors rather than confusing a broken service with an empty corpus. This is a
same-boundary expansion of the planned adapter seam, needed by Task 4's degraded
status requirement. Verify its default behavior and changed lines centrally.

Rejected: fixing every legacy writer during integration (requires a separately
qualified writer-protocol rollout), a new parallel memory database, and mapping
exact deletion to broad forget_topic. The support matrix must say worker mutations
are unavailable on current legacy stores; original memory operations remain.

Task 3 central verification: 162 checks pass and 6/6 protection removals are
detected. The third review found an age-binding race, repaired and centrally
verified after that review. Patrick directed one focused independent closure check;
its differential reproduction was centrally rerun and the finding closed. Task 3
is accepted; see [review disposition](task3-review.md).

## Integration checkpoint — 2026-09-17

Task 4's functional reviewer surfaced a maintainability gate failure in the
already implemented adapter: `CompatibilityAdapter.query` combines raw snapshot
retrieval with multi-root result aggregation. Reproduce the repository's
complexity gate before editing. If confirmed, extract the existing raw-read
branch into one private helper, retaining the source/version checks, exact item
mapping and per-root error handling. Keep document retrieval and all public
contracts unchanged. Re-run adapter/integration tests and the repository gate;
request a focused equivalence review of this refactor. This corrects the approved
implementation, not an additional memory capability or a review-gate waiver.

The full quality/gates run also rejected the new broad exception handler. Handle
expected filesystem, content-validation and missing-dependency failures per root
with `OSError`, `ValueError` and `ImportError`. Let unexpected programming defects
reach the host's explicit failed response. Verify both cases; keep the ratchet
baseline unchanged. The first final-gate run had 677 passes and this one failure;
record the targeted repair receipt separately instead of claiming the original
full run was green.

After removing the adapter's broad read catch, the same ratchet exposed the
strict stash seam's intentional catch. An explicitly injected backend may commit
then raise its own exception type. Preserve the existing single-call
`uncertain` result and no retry/diversion behavior. Document the one additional
catch in the ratchet's existing exception mechanism (session_stash 14 → 15),
with a custom exception raised after a real disposable file write as evidence.
The independent follow-up reviews this exact gate exception; it does not qualify
omitted authorization/security work.

## Bounded host-review repair — 2026-09-17

A legal host-state replacement retains earlier job snapshots. The new inspection
route checked only the current run envelope before returning an older snapshot;
a synthetic regression showed the old owner's job could be returned to a host
configured for the new owner. Authorize the actual job envelope and policy at
inspection and replay-result return, and immediately before consuming replay
responses. This also handles a host-state replacement between the initial check
and claiming a job. Preserve the journal and decline the request when its saved
snapshot exceeds current actor/owner/scope/classification/profile authority.
Do not delete history or change the shared worker's existing persistence API.
Verify all configured dimensions, the existing successful paths, and a normal
host-state transition during claim. No live corpus or native model is involved.
