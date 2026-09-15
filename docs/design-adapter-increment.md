# Adapter boundary experiment

Status: disposable local experiment, authorized by the request to continue the
portable contract and adapter work. No native adapter is qualified by this work.

Outcome: carry an immutable accepted task, requirement revision, attempt ID and
bounded participant identity across an injected JSON exchange; reject responses
for a different request before invoking independent verification. Preserve the
existing synchronous API. Done when deterministic fault cases and an independent
installed-wheel consumer pass without provider dependencies.

Cases: correct and incorrect answers; stale task/revision/attempt/participant;
unsupported envelope version; malformed, duplicate-key, truncated, oversized or
extra-field results; exchange failure; repeated invocation; verifier failure.
The adapter is single-use, including after exchange failure. This limits local
replay only; it provides neither durable deduplication nor effect reconciliation.
Any exception after dispatch may conceal effects, so callers must not infer that
retrying is safe. Roles describe the assignment and grant no permissions.

Experiments actually run before source edits: baseline 17 tests passed (98.75%
statement coverage); wheel rebuilt and installed without dependencies in a fresh
venv; positive demo and negative independent consumer passed outside the tree.
A disposable standard-library JSON probe showed duplicate keys silently overwrite
earlier values, whereas truncated JSON raises JSONDecodeError. Therefore reject
duplicate keys explicitly. No native runtime or paid model experiments ran.

Design: frozen Attempt wraps the existing Task with explicit requirement revision,
participant ID, role and adapter version. A canonical request digest correlates
the complete envelope with its response; it is not authentication or authority.
JsonParticipant implements the existing Participant protocol using an injected
string-in/string-out exchange. Its execute helper returns the attempt alongside
the existing Receipt, keeping identity available on both success and failure.
Strict envelope v1 uses a UTF-8 response byte limit and rejects unknown fields;
this is a local experiment format, not MCP, ACP, A2A or a persistence format.

Rejected alternative: launch native CLIs directly now. Without qualified output
and lifecycle behavior that would conflate a working process with a portable
adapter. Rejected alternative: expand the original runner into a lifecycle engine;
the synchronous experiment cannot honestly provide cancellation or recovery yet.
