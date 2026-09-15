# Portable contract and qualification map

Status: partial contract and bounded local implementation. Neither roadmap Phase
0 nor Phase 1 is complete. The current package supports synchronous participant
exchange, local verification/retrieval and a bounded Phase 2 evidence-review
coordinator with forms, scoped tool dispatch and saved run records. A bounded local
Phase 3 profile adds resume, reconciliation, cancellation and lead assignment.
Live workflow qualification and fleet migration remain outstanding. See
[recovery-workflow-receipt.md](recovery-workflow-receipt.md).

## Observed integration seams

Read-only source inspected at `/Users/patrickroebuck/.codex/worktrees/593b/attune-ai`,
HEAD `fe08f282fb0ad9cbb7eedf75af2597336576578e`. These are local observations;
remote freshness and a complete overlapping-work inventory are outstanding.
No attune-ai source changed.

| Surface | Observed source and callers | Integration consequence |
|---|---|---|
| Roster | `roundtable/rotation.py:CANONICAL_SEATS`; workspace, producing, skeptic, countersign, gate_triage callers | A configurable label cannot qualify arbitrary participants |
| Dispatch | `roundtable/routine.py:SEAT_RECIPES`; review, diagnosis/panel, diagnosis/fix_loop, classes/sitting | Introduce an adapter at the call boundary; preserve workflow/finding ownership |
| Receipt accounting | `roundtable/workspace.py` checks receipt seat sets against canonical seats | Portable receipts cannot be substituted without explicit translation |
| Plugins | `plugins/base.py:BasePlugin` exposes initialize, on_activate, register_workflows, register_mcp_tools | Reuse public entry points; do not copy plugin machinery |
| Lead and handoff authority | `docs/specs/feature-lead-governance/requirements.md` R2 and transfer rules | Provider-level authority stays with its registry; local role/session/attempt identity does not grant authority |

Host-interaction and handoff implementation callers still need a complete inventory
before an Attune integration. The separate-wheel vs internal-module comparison and
first real Attune public adapter remain outstanding.

## Profile qualification

These are evidence states, not an implemented capability registry. Declaration,
local availability and verified behavior must be recorded separately, keyed by
adapter/runtime version and probe. A changed version invalidates qualification.

| Profile | Declared scope | Available in this package | Verified scope / missing evidence |
|---|---|---|---|
| In-process Participant | Task → Output | Yes | Deterministic execution/check separation |
| JsonParticipant envelope v1 | Bound Attempt → strict text response | Yes | Identity correlation, malformed response rejection, local single-use dispatch |
| attune-verify 0.6.0 | Markdown + declared context → strict evidence report | Optional verify extra | Real-library positive/negative/unknown checks and independent installed CLI journeys |
| attune-rag 1.2.0 | Local corpus + query → ranked source references | Optional rag extra | Real keyword retrieval, no results, source hashes, isolated installed CLI journeys |
| attune-forms 0.17.0 | Explicit headless review request → validated form response | Optional review extra | Real intake/rendering; missing, declined, stale and invalid submissions rejected |
| Review turn v1 | Accepted revision → bounded tool/final action | Optional review journey; core contract | Real feature calls from deterministic and independent command peers; native leads tested with injected transports; live qualification pending |
| Claude native | Candidate lead and reviewer | Experimental CLI translator | Fixture checks pass; live invocation rejected for insufficient credit on the CLI-selected auth source |
| Codex native | Candidate lead and reviewer | Experimental CLI translator | Live arithmetic/structured response and independent acceptance passed on CLI 0.153.4; broader feature/lifecycle qualification outstanding |
| Direct model | Candidate additional participant | Command extension seam, no provider-specific transport | Provider transport and live receipt outstanding |
| ACP / MCP / A2A | Candidate standard boundaries | No implementation | Supported-version selection and independent interoperability outstanding |

Missing mandatory features make the affected operation unavailable. Rich native
features cannot substitute for them. JSON fixture success qualifies only the
local envelope decoder, not any named provider or protocol. Caller-provided
participant identity is asserted, not authenticated.

## State cases and ownership

The existing Receipt status is an aggregate. `output` retained on verifier failure
shows execution returned while acceptance did not complete. It is not durable
execution state. The following lifecycle design is proposed unless marked tested.

| Case / transition | Owner and required behavior | Probe / current status |
|---|---|---|
| New attempt → dispatch → output → verified or rejected | Core runner; independent Check determines acceptance | Tested, correct/wrong arithmetic |
| Exchange failure → failed with diagnostic | Adapter; never infer effect-free failure | Tested timeout; effect reconciliation unavailable |
| Output → verifier failure | Core retains output and assignment, never verifies | Tested |
| Same adapter → second dispatch | Adapter refuses before exchange | Tested after success and failure; no cross-instance/process deduplication |
| Changed task/revision/attempt/role/version → old response | Adapter rejects request digest mismatch before verification | Tested; correlation is not authorization |
| Pending authorization → late grant after task changes | Authority owner must bind grant to accepted operation revision | Proposed; no authorization endpoint exists here |
| Running → cancel request → terminal or unresolved | Runtime adapter observes completion/effects before reporting cancelled | Proposed; cancellation unsupported |
| Completed → cancel | Preserve completion; report cancellation too late | Proposed; cannot test until lifecycle exists |
| Unknown effects → retry | Reconciliation owner blocks uncontrolled repeat | Proposed; no automatic retries, durable guard outstanding |
| Future stored capsule → load | Persistence owner preserves compatible data, rejects unsupported control | New local recovery profile preserves optional fields and rejects future control versions; old records remain inspectable, cross-machine capsules remain outstanding |
| Artifact reference → transfer | Artifact owner supplies resolvable reference, digest and access scope | Proposed; no artifact transfer implemented |

## Requirement-to-probe trace

C identifiers match `docs/research/agent-harness-communications.md` in the source
checkout above. Partial evidence must not be counted as completion of the row.

| Requirement | Owner / observable failure | Probe and disposition |
|---|---|---|
| C8 acceptance differs from completion | Core / wrong result called verified | Correct/wrong answers and verifier failure tested |
| C9 delayed authorization | Authority owner / stale grant authorizes changed operation | Stale request correlation tested; real grants outstanding |
| C10 output expands scope | Tool/authority owner / peer text changes policy | Review dispatch rejects ungranted tools, path arguments and exhausted budgets; JSON output cannot mutate the accepted registry |
| C11 advertised capability fails | Adapter registry / false verified support | Optional feature absence/version/load failure reported unavailable; full runtime registry qualification outstanding |
| C12 protocol versions | Protocol adapters / accepted confused with complete | MCP stdio 2025-11-25/2026-07-28 and local A2A 1.0 JSONRPC have independent-peer receipts; ACP and remote authenticated profiles remain open |
| C13 future fields | Persistence / lost continuation fields | Strict wire response rejects extras; review inspection preserves optional fields, rejects future schema versions; capsule continuation outstanding |
| C14 provider failure | Native adapter / fabricated result or silent paid fallback | Injected timeout and real Claude credit failure keep diagnostics; remaining native diagnoses outstanding |
| C15 truncated or large output | Adapter / incomplete result called clean | Truncation and UTF-8 byte boundary tested; transport allocation bounds outstanding |
| C19 required capability removed | Registry / native features conceal missing portable guarantee | Proposed qualification failure probe; registry not implemented |

Local tool-operation envelopes preserve verification evidence and hashed
artifact/source references. The review turn protocol now dispatches scoped tools
against an accepted request and explicit registry. Live model qualification,
artifact transfer, portable cancellation and effect reconciliation remain
outstanding. New review records persist prepared/dispatching/completed operations
and stop after write failures. Explicit local resume replays completed evidence
under an OS writer lock and matching checkpoint/input hashes; uncertain dispatch
requires constrained reconciliation. Inspection never retries or resumes. The native POSIX runner has
local cancellation/timeout probes; they do not establish provider cancellation or
external-effect reconciliation. Check.evidence is a description,
not a transferable artifact reference or signed attestation.

## Bounded review profile

See [review workflow](review-workflow.md) for exact JSON limits, registry entries,
tool arguments, status/exit semantics and storage behavior. Lead and reviewer
receive independent contexts; narrative results remain distinct from the reviewed
document's strict verification outcome. The native shim encodes action JSON inside
the existing text exchange, with one fresh process per turn. It is not ACP/MCP
interoperability or native-session resumption. Configured command executables and
verification manifests remain trusted code; dispatch scope is not an OS sandbox.

## Local recovery profile

See [recovery workflow](recovery-workflow.md). The accepted task revision is preserved
across local lead assignments. Transfer carries prior lead evidence as context and
uses only the accepted registry's grants. No provider-level authority moves. Saved
turn IDs and operation keys keep reconstructed requests correlated; completed
results are not dispatched again. Prepared work can start, uncertain work cannot
be guessed safe. A recovered participant reply is validated and attributed; one
explicit extra retry is allowed only for a known read-only operation. Cancellation
does not roll back effects, and late cancellation preserves completed state.

The checkpoint digest rejects stale control requests; it is not authentication.
Copied run directories cannot acquire new execution ownership. Local input and
Markdown-source hashes are rechecked; arbitrary external verification targets are
not snapshotted. New control versions fail closed, while optional data survives.
POSIX locking is qualified locally; cross-machine and Windows recovery are not.

## Local data-only extension profile

[Extension contract and commands](extension-workflow.md) define a bounded Phase 4
increment. Accepted registries bind extension identity, state directory and exact
manifest/skill digest. Namespaced grants dispatch only to the existing read-only
retrieval adapter. Activation is declaration/dependency validation; invocation
receipts bind actual results to an artifact and corpus, not general availability.

Install starts disabled; explicit replacement requires disabled state. Removal
preserves data as a tombstone. Invocation holds the same process lease used by
lifecycle mutation, so a concurrent disable/remove reports busy until the call
settles. Paused work cannot invoke a disabled, removed or changed artifact. Old
completed evidence remains inspectable. These local controls do not establish
MCP/A2A interoperability, executable-plugin isolation or cross-machine ownership.
Extension-enabled recovery profiles include `extensions: 1`; old unextended
profiles retain their prior behavior. Existing public Attune BasePlugin seams are
characterized through an explicit bridge, without changing Attune host registries.

## Qualified local protocol boundaries

[MCP](mcp-workflow.md) projects accepted retrieval grants through SDK 2.2.0,
retaining the existing budget, source snapshots and extension lifecycle checks.
The qualified revisions are 2025-11-25 and 2026-07-28. A local launcher selects
the principal; MCP clientInfo is not authentication. Started reads settle under
cancellation; pending sessions are inspect-only and cannot automatically resume.

[A2A](a2a-workflow.md) projects the core JSON attempt through a pinned A2A 1.0
JSONRPC interface on literal loopback HTTP. One data artifact carries a correlated
response. Independent verification can reject an answer in a completed peer task.
Lost acknowledgements never cause automatic resubmission; known tasks allow
explicit read-only refresh and one cancellation attempt. These are separate
exchange records, not review-roster or cross-process recovery integration.
Local card pins and operation grants do not qualify production authentication.

## E2 availability distinction

[The frozen local comparison](e2-capability-evidence-receipt.md) produced **revise**
for promoting version-bound historical success to current verified availability.
An unchanged descriptor missed an injected runtime failure on both command-review
and MCP. Dependency/lifecycle/grant changes were detected and upgrades invalidated
old evidence, but those checks could not certify the next call. Production keeps
declarations distinct from scoped observations and still checks every invocation.
No general availability cache was added. The full 24-cell matrix and its two false
verified claims are retained rather than treated as successful qualification.

[The revised E2 contract](e2-revision-receipt.md) now passes its frozen local
comparison. Current checks permit an invocation; success is recorded only for
that invocation, with its scope, record and result correlation. History remains
matching/stale/invalid/absent context and cannot supply cached output or verified
availability. Both working calls and post-success failures remain visible.
This adopts the narrower evidence contract, not the original availability claim.

## Phase 5 evidence boundary

[The local E1 precursor](phase5-evaluation-receipt.md) preserves accepted requests
across installed Attune packet transport and Harness capsule continuation.
All 48 mechanical cases pass. Capsule completion requires explicit reconciliation
for lost acknowledgements; a saved effect is not repeated. A successful packet
handoff is not an executable workflow or a failed task. This comparison cannot
establish general recovery superiority or lower human effort. E3's prepared
144-trial campaign and synthetic scorer do not qualify a collaboration policy;
model outcomes, cost, human repair and uncertainty remain unmeasured.
