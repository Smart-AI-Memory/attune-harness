# Recover and transfer a local review

New review runs support checkpointed continuation. A resumed run reuses completed
participant/tool results; it never silently repeats a possibly executed operation.
This implementation supports one local POSIX run directory and the original input
paths. It does not move project artifacts between machines or grant provider-level
governance authority. Phase 2 records remain inspectable but cannot be resumed.

## Run the prepared example

From the Harness directory with the prepared installed environment:

```sh
.venv-review-check/bin/python -I examples/recovery/continue_review.py --run-dir /tmp/attune-recovery-example
```

Choose a directory that does not already exist. This example pauses a deterministic
review, transfers its lead to another accepted participant, resumes, transfers back,
and finishes. It checks that the accepted revision stays identical. The run and
evidence remain at the selected path. No model is called.

## Operator commands

```sh
attune-harness review request.json --config participants.json --run-dir new-run --max-operations 4
attune-harness inspect-review new-run
attune-harness resume-review new-run --request request.json --config participants.json --checkpoint CHECKPOINT_DIGEST
```

Use the exact checkpoint_digest from the latest inspection. Each mutation changes
it; old decisions fail before changing the record. `--max-operations` optionally
pauses after 1–100 newly completed operations. Replayed operations do not consume
that budget. Accepted participant turn/tool budgets remain in force across resumes.
A paused command exits 1; failed/unavailable/unresolved controls exit 2. Completed
review exit codes retain the document/retrieval outcome rules in the
[review workflow](review-workflow.md).

Resume requires the original request and registry again. Their accepted revision,
document/context hashes and the complete bounded Markdown source snapshot must
match. Missing/wrong feature dependencies fail visibly. Native or command profiles
require `--allow-external` on each execution call; a stored switch is not reused as
credential or spending approval. Completed runs are returned without invoking any
participants. Inspection and completed-run replay are historical evidence, not a
fresh verification of external state.

All mutation commands acquire a nonblocking OS file lock. A second owner receives
busy immediately; a dead process's lock is released by the OS. The lock file is
retained, because removing its inode could let competing owners acquire different
locks. A copied run directory is rejected for mutation. Do not bypass the binding
by editing record_path or copying a record back over another owner. Record files
are trusted local state; hashes detect stale/corrupt content, not malicious writers.

## Uncertain operations

Each event stores an operation key, event ID, effect class, attempt count, state,
dispatch phase and correlated result. The transitions are:

```text
prepared → dispatching → completed
                  ↘ failed / interrupted: reconcile before continuation
```

The prepared checkpoint is saved first. The dispatching checkpoint is saved before
the call starts. If only prepared work remains after an interruption, resumption
may dispatch it. A completed event is replayed without dispatch. A dispatching or
failed event blocks until explicitly reconciled; process exit alone does not prove
that no effects occurred. Writes use fsync and atomic replacement. Failed writes
stop dispatch, and inspection reports persisted running state as unresolved.

Two bounded reconciliation paths are available:

```sh
attune-harness reconcile-review new-run --checkpoint CHECKPOINT_DIGEST --event EVENT_ID --reply recovered-reply.json
attune-harness reconcile-review new-run --checkpoint CHECKPOINT_DIGEST --event EVENT_ID --retry-read-only
```

A recovered reply must be a valid, strictly correlated review-turn response.
Only participant replies can be attached this way. The raw reply, file hash and
operator-supplied provenance are retained; it is not authenticated model identity.
Attaching a reply executes nothing. On resume, normal grants, argument checks and
verification still apply, so a recovered reply cannot authorize a new tool.

The retry path permits one extra attempt only for a known read-only operation:
local retrieval or the exact built-in deterministic participant. Injected/custom
participants, native/command transports and verification are conservatively treated
as potentially effectful. Trusted verification manifests can execute code. Their
uncertain operations cannot use this retry path. No arbitrary effect reconciliation,
automatic retries or exactly-once guarantee is implemented.

Verification results are replayed as evidence from their original checks. The
snapshot covers the accepted document/context bytes and local Markdown sources;
it does not snapshot an interpreter, installed modules, external services or every
mutable input a verification manifest can reference. No freshness claim for those
external targets is added by resume. Unsupported uncertain verification work stays
blocked; it cannot be declared safe merely to finish the journey.

## Lead transfer and cancellation

```sh
attune-harness transfer-review new-run --checkpoint CHECKPOINT_DIGEST --lead OTHER_PARTICIPANT --reason "Continue the accepted review"
attune-harness cancel-review new-run --checkpoint CHECKPOINT_DIGEST --reason "Abandon this attempt"
```

Transfer selects a different identity already present in the accepted registry,
distinct from the reviewer. It requires every existing event to be completed and
must precede reviewer execution. This experiment permits at most two transfers.
The old lead's completed events and narrative remain in the record; the receiving
lead gets a new attempt with its declared budgets and bounded continuation context.
That context preserves the accepted request, artifact references, operator reason
and prior lead work/effects. Reasons and narratives are asserted context; accepted
tool grants remain owned by the registry. The original accepted revision is not
rewritten. The reviewer continues to receive an independent context.

Cancellation abandons a stopped run and preserves uncertain effects. It does not
kill an active owner, roll back external changes or make them safe to retry. A busy
owner must first stop; a cancelled run cannot resume. Cancellation after completion
returns the original completion unchanged. Optional unknown record data is retained;
future control versions and invalid event states are rejected.

## Qualification boundary

The local fault suite covers prepared/dispatching/result-write interruptions,
concurrent ownership, process death, recovered replies, bounded read-only retries,
stale decisions, changed inputs, terminal states and transfer. The 24-case transfer
matrix uses four evidence cases × three checkpoints × two directions. It is a
deterministic adaptation, not the full E1 experiment across four task types with
repeated live models and an existing-handoff baseline. Live Phase 2 qualification,
cross-machine artifact transfer and the broader E1 comparison remain outstanding.
