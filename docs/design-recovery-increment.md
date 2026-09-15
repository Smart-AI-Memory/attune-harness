# Local recovery and lead transfer

Status: executable bounded Phase 3 increment, authorized by Patrick's “go”.
Done when: an interrupted review resumes from completed evidence without repeating
completed operations; uncertain dispatch blocks; constrained reconciliation and
two-way lead transfer preserve accepted work; installed CLI fault journeys pass.
No provider calls, auth changes, global governance changes or background work.

Baseline: 252 tests passed. Disposable scratch probe: a second process could not
acquire a nonblocking POSIX flock while the owner held it; acquisition succeeded
after release. Existing Phase 2 records retain tool arguments/results but lack a
prepared-versus-dispatched boundary and therefore cannot safely be auto-migrated.

Read-only handoff inventory at attune-ai fe08f282fb0ad9cbb7eedf75af2597336576578e:
handoff.packet render/parse owns the existing Markdown packet; handoff.verify.drift
checks current Git state; memory_link handles optional memory. Its completed spec
separates verified facts from asserted context and grants no authority. Harness
keeps that distinction. This workspace is not a Git repository, so its recovery
record uses accepted input/source hashes rather than invented Git provenance.
It does not copy the Markdown packet implementation or create another memory store.

Design: add a recovery profile to new review records while retaining schema 1
inspection of older records. Persist stable operation keys, deterministic turn IDs,
attempt identity and phases prepared → dispatching → completed. Replay reconstructs
the loop from completed events without calling their participants/tools. Prepared
work is safe to dispatch; dispatching/failed work is unresolved until reconciled.
Completed evidence is reused only with matching accepted request, registry, engine
profile, dependency versions and source snapshot. Optional record data is retained.

All mutations use one nonblocking OS lock per run directory. OS release after a
crash avoids guessing about stale PID files. Mutations require the checkpoint
digest returned by inspection: a stale resume/reconciliation/transfer cannot act
on a newer run. Hashes detect stale/corrupt state, not malicious authorized writers.
Recovery mutations initially support POSIX; unsupported platforms fail explicitly.

Resume takes the original request/config again and requires a fresh external-use
switch for external participants. It preserves budgets and accepted constraints.
An optional operation budget deliberately pauses at a saved boundary for controlled
continuation. There is no automatic retry of uncertain work. Reconciliation may
attach a strictly correlated recovered participant reply (retained with provenance)
or explicitly authorize one retry of a known read-only operation. Verification
manifests and external transports can execute code: their unknown effects cannot
be declared safe merely because a process failed. Cancellation abandons unresolved
work without claiming its external effects were undone; late cancellation preserves
completion. The lock prevents mutation while an owner is executing.

Transfer is an explicit local task assignment to another participant already in
the accepted registry, before reviewer execution. It requires no unresolved event,
preserves the original request/revision, archives prior lead evidence and creates
a fresh bounded attempt. A bounded continuation context carries prior lead work,
constraints, artifacts and observed effects to the receiver; it is data, not a
grant. The reviewer still receives independent context. At most two transfers
are allowed in this experiment; live authority transfer stays with its owner.

Cases: pause/resume at every operation; death before dispatch, after effects but
before acknowledgement, and during record replacement; concurrent owners; stale
checkpoint and altered inputs/registry; duplicate recovered reply; wrong digest,
future schema, old records and extra optional data; retry denial/bounds; cancelled
and completed states; transfer in both directions with uncertain effects blocked.
Compare no-repeat continuation with Phase 2's inspect-only behavior on deterministic
fixtures. Live E1 repetitions and moving artifacts across machines remain unprobed.

Rejected: treating every failed local call as effect-free; trusted verification
commands and provider invocation make that false. Rejected: copying a run into a
new directory to resume; that allows two owners to repeat work. Rejected: adding a
workflow server or a second handoff/memory implementation for one local workflow.
