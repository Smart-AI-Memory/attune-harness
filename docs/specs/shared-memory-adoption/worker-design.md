# Shared worker implementation note

Task 1 accepted on 2026-09-17; Patrick authorized automatic continuation of
Tasks 2–5, with a pause for serious findings. Task 2 is now accepted: 63 checks
pass, 5/5 protection removals detected, and both independent findings closed.
Task 3 is accepted after independent closure of its final repair.

The core produces proposals, never storage effects. It takes a host-owned
snapshot, explicit grants and a sampling/routing policy. Sources carry owner and
security classification separately from logical memory kinds. All sources and
captured facts must pass exposure checks before any participant is invoked.
Unknown adapter capabilities, profiles and security labels fail closed.

Cases: routine success uses one worker; known difficulty starts with the stronger
profile; invalid routine output or needs_reasoning permits one escalation.
needs_evidence and needs_decision stop without that escalation. Every outcome
requires supplied citations; unchanged facts may be omitted or repeated exactly.
Sampled review can quarantine a confident but unsupported answer. Scope changes,
unknown citations, invalid changes, stale generations, duplicate claims and
uncertain dispatch/publication must prevent reuse. Host generations detect ABA.
Large source text is retained subject to explicit byte limits, never shortened.

Reuse RunStore's OS lock and fsync/replace record publication. Persist dispatch
intent before invoking a participant and never replay a claimed job. Bind the
participant profile, including its no-tools transport contract, into host policy.
Injected test participants are explicitly trusted host code, not a sandbox.
General native adapters are unavailable here until their actual isolation is
qualified; merely setting tools=[] in a prompt does not qualify them.

Evidence already run: the frozen sorter/citation/worker/journey experiments and
108 native receipts, followed by 24 current-service baseline checks and four
detected protection-removal probes. Task 2 adds deterministic routing, exposure,
persistence and stale-state tests. No new model campaign runs in this task.

Rejected: a stronger router for every job (duplicates successful routine work),
model-copied version fields (the repaired contract assigns this to the host), and
a second database (RunStore already provides the required job journal).

Storage boundary for Task 3: the current legacy file lock can break a live lock
after 30 seconds and has no versioned update API. Shared legacy directories
cannot acquire managed-mutation qualification merely from a new wrapper lock.
Keep their current readers/commands, and explicitly refuse unsupported new
mutations. Any qualified writable profile needs its own demonstrated concurrency
and uncertain-write behavior; this limitation must remain visible in the matrix.
