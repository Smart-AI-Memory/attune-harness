# Disposable isolated note lifecycle

2026-09-16, local time. Patrick approved capture → recall → correct → forget
through the Luna worker, with explicit type mapping, duplicate prevention,
project isolation, stale-write rejection and refreshed recall. This increment
uses a real FileStashBackend in fresh temporary directories. It neither changes
production defaults nor reads/writes the user's memory stores.

Pre-code evidence: the preceding actual-adapter probe found duplicate records
for repeated IDs and cwd-based soft ordering across projects. Rechecked source
shows no expected-version write API; correction requires removal plus append.
The existing worker passed 211 checks, including exclusive job claims and
generation binding. Reuse those frozen worker/citation contracts and Harness
RunStore leases; do not edit prior experiments or sibling packages.

The adapter is a cooperative-writer, local-file prototype. A project has an
explicit, exclusively created directory containing its own backend and control
record. Only logical note → raw-session note is mapped; other kinds fail before
dispatch. A request selects one exact note ID. Evidence and facts must have the
selected project scope before reaching any participant. Scope never comes from
model prose, cwd ranking or inferred identity. Other project stores are not queried.
No security-sensitivity classification, service-wrapper sanitization or curated
promotion qualification is implied.

The disposable store is bounded to eight notes, 500 characters per note, eight
source references per note and ASCII identifiers of at most 64 characters.
Reject capacity or identifier violations before dispatch; validate the complete
resulting file-size bound again before any effect. Physical parsing rejects
hidden expired/malformed rows instead of silently dropping them on API reads.

The host records a monotonic project version, current fact provenance, a backend
fingerprint, pending write intent and completed operation IDs. Each proposal is
bound to its captured target/version and the current worker input/policy. Apply
requires a completed permitted operation and any sampled audit to be supported;
the candidate is independently re-normalized. A project OS lease serializes
snapshot/read/apply/reconcile among wrapper clients; the worker lease also covers
the short apply phase so grants cannot change mid-apply. Neither is held during
model calls. Two proposals from the same version cannot both overwrite it.

Persist an intent before backend effects. Use the public remember/forget APIs,
then verify actual records and bytes before publishing the new version. A repeated
operation returns its original disposition without calling the backend; conflicting
reuse is rejected. After a crash or uncertain acknowledgement, pending state blocks
recall and new work until explicit read-only reconciliation. If observed records
match the intended after-state, record completion without repeating effects. If
bytes match the before-state, record not-applied. Partial/foreign state remains
unresolved. No blind retry and no claim of atomic multi-file commit or power-loss
durability. Direct out-of-band writers do not honor this wrapper's lease and are
outside its concurrency guarantee; detected drift stops work.

Recalls reopen the actual project backend and return a version-bound context.
Old context handles are rejected after correction or forgetting. New participant
requests rebuild their evidence packet from current storage. This qualifies the
prototype's explicit refresh path, not retroactive erasure of already-loaded LLM
context or all host session hooks. Forgetting removes the note from active storage
and fresh recall; experiment/worker audit receipts retain their historical inputs.
Full history retention/erasure policy remains outside this synthetic experiment.

Offline acceptance: a complete lifecycle on actual temporary files; retries with
one physical ID and no resurrection after forgetting; conflicting operation IDs;
unmapped kinds and foreign evidence stopped before dispatch; contaminated backend
rejected; stale/ABA context; two real processes applying competing proposals;
host grant/policy change before apply; invalid or unaudited sampled proposal
rejected; before/after/partial write failures and explicit reconciliation without
repeating effects; unrelated note/project preserved; recorded source/contracts
remain unchanged. Invalid semantic content is still a sampling limitation.

Native acceptance: one fresh synthetic note journey. Three Luna/high workers
(capture, correction, forgetting), with correction preselected for Astra/xhigh
semantic review by host sampling. Each stage permits one existing policy
escalation: four planned calls, hard maximum seven. Per-call timeout 180 seconds,
campaign deadline 900 seconds, no automatic retry/provider fallback. Use the
existing Codex ChatGPT subscription transport, no direct API charges, new
credentials, Voyage or Anthropic calls. Freeze source hashes, fixtures, profiles,
schedule, sample and source rubrics before dispatch. Grade all initial/final
meaning and citations; count every attempt and audit. No production reliability,
workload-cost or latency claim follows from this one journey.

The runner saves synthetic worker/control/backend artifacts before removing its
temporary directories. Persistent receipt-write failure retains those directories
and reports their path for inspection; it must not destroy the only pending copy.

Rejected: passing preference/lesson through an incompatible taxonomy; treating
cwd as an access check; rewriting the production backend; inventing a replacement
memory database; holding locks across model work; treating model/ID agreement as
truth; retrying uncertain append operations; sharing this scratch store with
uncoordinated writers; silently invalidating the preceding failed campaigns.
