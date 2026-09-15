# MCP local retrieval profile — design before implementation

2026-09-14. Continue Phase 4, then the independent A2A experiment. This note covers
the MCP boundary first. Done: pinned SDK/selected revision, real process/client
interop, scoped feature results, malformed/denied/stale/lifecycle/cancellation
cases, installed receipts, no provider or credential operations.

Baseline: 366 tests passed. Installed MCP Python SDK 1.29.1 advertises 2025-11-25.
A disposable `/tmp/harness-mcp-disposable.py` launched an SDK server and independent
SDK client over stdio: initialize selected 2025-11-25, tools/list returned the
probe schema, tools/call returned matching structured/text content, and boolean
`k` was rejected against integer JSON Schema. Existing `Server.call_tool`
validates input/output schemas; returning a raw CallToolResult bypasses its output
validation, so success should return a dict through the normal validation path.

Use the SDK's public low-level Server with explicit schemas rather than a second
JSON-RPC implementation. Add an optional `mcp` extra with exact SDK 1.29.1 and the
existing review dependencies. Core imports/install remain SDK-free. Bind one
accepted review request, participant grants and original source snapshot at
startup; require a retrieval-only participant (retrieve and/or contributed
retrieval tools). The local process launcher supplies identity/scope; self-reported
MCP clientInfo is not authentication. No HTTP listener, OAuth or credential setup.

Prefix portable names with `harness.`. Reject unknown paths/fields, wrong numeric
types, missing/ungranted/disabled/upgraded tools and changed accepted inputs.
Expose a fixed startup tool list and no listChanged claim. Call-time checks remain
authoritative. Serialize calls and count dispatched calls against the accepted
participant budget. Persist dispatch/result events in a new, exclusive local
session directory using existing atomic RunStore/lease. Completed calls contain
artifact/corpus evidence. Pending calls after process death stay inspect-only;
there is no automatic replay or cross-session budget promise.

Run bounded-input, read-only feature work in an AnyIO worker thread with default
cancellation shielding: a started local call settles and records its result even
if the requester cancels. Cancellation/transport closure is not proof the call
never ran. No hard filesystem-I/O deadline is promised; client timeouts and
process shutdown bound the client wait. Tests include cancellation before result
and observing the durable result, plus disconnect/shutdown. Lifecycle mutation
still respects the extension lease. Never label arbitrary prose verified.

Reject FastMCP coercion/default-extra behavior for this profile in favor of
explicit JSON Schemas and existing exact argument validation. Do not broaden to
verification manifests, arbitrary server commands, native tool configuration,
remote transports or SDK upgrades while qualifying this first boundary.

Primary references: [SDK 1.29.1](https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/v1.29.1/README.md),
[MCP lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle),
[tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools).
The supported revision is deliberately selected, not claimed newest. MCP builder
skill guidance supplies schema/annotation/discovery checks. Its model-based
quality evaluations remain unrun under the existing no-provider-call constraint;
local protocol tests do not establish language-model usability.

## SDK 2.2.0 qualification decision (after the baseline)

Patrick asked about the available upgrade and specifically attune-harness. The
published current SDK is 2.2.0 (2026-09-07); the separate Attune installation does
not constrain Harness's new optional adapter. Target 2.2.0 for Harness after
replaying the scope/receipt cases against it. Keep the 1.29.1 baseline and test a
legacy SDK client against the new server. Existing attune-ai and its SDK remain
unchanged. Baseline evidence: 387 tests passed; server source and lock retained
under `receipts/mcp-v1-baseline/` before migration.

An isolated 2.2.0 install confirmed constructor callbacks replace low-level
handler decorators; input/output validation and error-result wrapping must be
explicit. Protocol types use snake_case attributes and ClientSession.initialize
still negotiates the legacy profile. Use Client for the 2026 profile. Preserve
shared retrieval scope/storage; replace only the SDK projection. Test legacy
2025-11-25 plus new 2026-07-28 rather than treating an SDK version bump as proof.
Disable optional telemetry middleware in the local server; no exporters or
credentials are configured. Pin dependency closure after tests, keeping the
existing workflow pins where compatible.

[Published release](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.2.0),
[migration](https://py.sdk.modelcontextprotocol.io/migration/),
[low-level contract](https://py.sdk.modelcontextprotocol.io/advanced/low-level-server/),
[protocol versions](https://py.sdk.modelcontextprotocol.io/protocol-versions/).
The original 1.29.1 plan above records the tested starting point, not the new pin.
