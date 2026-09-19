# Shared memory adoption — decisions

Status: implementation plan approved by Patrick on 2026-09-17; All five tasks accepted; canonical completion revision 23. Live activation and release remain outside this plan.
Auto-run authorized for Tasks 2–5; pause on serious findings.

- **D1 — Accepted by Patrick:** adopt the successful memory-worker approach in
  both attune-ai and attune-harness.
- **D2 — Accepted priority:** memories are among Patrick's most useful and valued
  features. Preserve accumulated content and useful behavior when enabling Harness.
- **D3 — Accepted intended outcome:** Harness can use Attune AI's existing memories.
  Actual existing-format/receiving-agent compatibility remains to be demonstrated.
- **D4 — Carried forward:** Luna remains the sorter/routine-worker candidate;
  host routing, direct stronger handling of known difficult work and sampled review
  remain. Do not add a stronger router to repair an interface defect.
- **D5 — Proposed implementation:** one Harness-owned contract and worker, optional
  AI service/host adapters, read-in-place compatibility first, additive activation.
  Existing memory paths remain supported while individual new operations qualify.
- **D6 — Boundary:** the eight-note synthetic adapter is not the product feature
  set. Neither logical memory kinds nor valid citations establish security policy
  or semantic truth. Current-format access does not authorize data rewriting.
- **D7 — Execution status:** Patrick approved the concrete five-task ladder
  and beginning implementation on 2026-09-17, including optional packaging review. No approval of the unrelated scoping-only plan/build spec is implied.
  Publication, live activation, migration and new native campaigns retain their
  existing authorization requirements; do not manufacture additional gates.
- **D8 — Accepted telemetry direction:** remote-user usage collection is no
  longer needed. Retain useful local memory feedback, diagnostics and cost/usage
  accounting; do not equate telemetry with uploading. The shared worker must
  not depend on remote collection. Inventory and separately scope retirement of
  existing product-wide upload hooks and the hosted collector; none is removed
  by this planning change.

## Planning evidence

**D9 — Accepted telemetry clarification (2026-09-17):** Patrick chose A after
reopening the telemetry form: disable product-usage collection, preserve local
accounting and explicitly configured team coordination, shared memory and
operational reporting. This supersedes the briefly selected entirely-offline
option; no blanket network prohibition is authorized. Team features that reuse
the legacy usage uploader need purpose/destination separation before claiming
support. Existing Redis coordination/event streams are separate from usage_ping;
Task 4 must verify that distinction. This does not activate a new team service,
provider campaign, or shared-memory writer.

Attune AI's read-only collaboration preflight: 87 tests passed, 0 failures,
2 warnings for its existing dirty main checkout, repository status unchanged.
Source inspection establishes the seams in design.md. Frozen native/worker
receipts are preserved. No production code, live memory or host setting changed
during this planning increment.
