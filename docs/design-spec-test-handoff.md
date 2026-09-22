# Bound Harness test evidence at Spec acceptance

2026-09-17. Patrick approved option A: local correction and qualification of the
existing test→Spec handoff. This continues the memory documentation journey; no
paid trial, active installation, release or unrelated cleanup is authorized.
Artifact tier: bounded extension of the existing qualification spec.

Observed counterexample: the installed Harness marks its result blocked after a
captured adapter source edit, while the previously rendered AI Spec form accepts.
An unchanged result and a newly published high-severity blocked result behave
correctly. The previous installed rehearsal, retained in the memory documentation
receipts, is the scratch experiment and failing acceptance case.

Add one typed, optional `test_evidence` reference to the existing Spec task receipt.
The trusted executor obtains it from Harness, which binds the completed test's
path, task identity, checkpoint and outcome, verifies its journal and artifacts,
and uses the existing source/producer/interpreter freshness check. Spec checks the
reference when publishing and immediately before every completion path, including
auto-run and explicit risk acknowledgment. Missing optional integration fails
closed for a bound receipt. A failed/no-tests result requires the existing high
gate; it cannot be published as ordinary success. The receipt is included in the
form's contract binding and persisted with existing accepted Spec receipts.

Keep legacy non-Harness Spec receipts readable without inventing freshness proof.
Executors publishing Harness evidence must use the new binding; arbitrary probe
strings cannot acquire that guarantee. Redo/fix actions remain usable after the
evidence becomes stale. Historical accepted receipts are not revalidated as if
they were new approvals. Reuse the current task store, SpecState and grammar;
do not add a gate store or ask a model to copy control metadata.

Qualify actual owner/collector boundaries: fresh pass, failed outcome/high gate,
source/test/config/producer changes, missing or malformed record, changed output,
changed checkpoint, summary/journal disagreement, wrong identity/path and missing
integration. Check fresh approval persistence/resume, replay, auto-run, risk
acknowledgment, redo recovery and no extra participant calls. Run source and
isolated wheel-installed checks; remove the completion guard in a disposable copy
and report how many negative cases detect it. Preserve the old counterexample.

Rejected: rechecking only at display (the reproduced gap is after display),
trusting arbitrary JSON prose or a cached result (not owner-validated evidence),
validating only record hashes (misses changed checkout), and changing the generic
form collector (evidence meaning belongs to the task and Spec owners). Freshness
is a cooperating-owner snapshot check at acceptance, not an adversarial filesystem
lock spanning all repositories and subsequent human work.

Qualification also reproduced Git's optional index refresh during the existing
test inventory: source bytes stayed identical but `.git/index` changed, making
the producing repair stale. Scratch instrumentation isolated `git diff` as the
writer: `--no-optional-locks` alone did not prevent it, while the command-local
`-c diff.autoRefreshIndex=false` did. Use both in the read-only capture wrapper
and prove index bytes stay unchanged when file
timestamps differ. This is necessary to make the freshness check itself read-only.
With refresh disabled, Git's name-only changed-path hint can also retain stat-only
differences after identical bytes are restored. Freshness therefore compares the
complete captured file/hash/mode/size, HEAD, staged-index and root identities,
excluding only that redundant selection hint. Actual input edits still fail;
timestamp-only changes do not manufacture a source revision.
