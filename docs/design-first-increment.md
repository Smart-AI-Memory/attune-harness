# First local increment: standalone execution contract

Status: bounded implementation experiment, not a production-ready harness.

Claim: a package independent of attune-ai and provider SDKs can accept an immutable task, invoke a participant, and distinguish returned output from independently checked acceptance. This tests package independence, not model interoperability.

Cases: valid output accepted; plausible but wrong output rejected; participant exception; verifier exception; malformed participant return; malformed verifier return; invalid or empty task fields; unsupported schema revision. Exceptions carry diagnostics and never become verified completion. Task identifiers, accepted requirements and revision survive execution unchanged. Verification is a caller-supplied check, not a model's own success assertion.

Scratch evidence before code: checked wheel/build/setuptools availability; new destination did not exist; a disposable two-case probe showed transport completion can coexist with rejected acceptance. That probe illustrates the state distinction only; behavioral and installed-wheel checks must establish the implemented claim.

Scope: immutable in-memory task and receipt; synchronous participant protocol; injected verifier; deterministic demonstration. No persistence, arbitrary tool execution, permissions engine, automatic retries, cancellation, native SDK adapters, or global configuration changes. Those remain later increments in the phased plan.

Alternative: start by moving Attune's roundtable runtime. Rejected for this increment because it would entangle packaging and existing roster semantics before proving a minimal independent boundary. Another alternative is an internal module; the separate wheel experiment tests the stronger isolation claim first, without yet proving migration cost is lower.

Receipt: targeted behavioral tests with coverage; build wheel locally; install into a fresh venv without dependencies; invoke from outside the source tree with PYTHONPATH removed; assert wrong output is rejected and neither attune nor provider SDKs is importable. A generated successful demo alone is insufficient.
