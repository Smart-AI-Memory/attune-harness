# Saved-store Windows feasibility proof

October 15, 2026. This is T2's disposable experiment, not a production storage
backend or a saved-store qualification. Production `memory_saved.py` and the
existing Windows effects primitives stay unchanged.

The question is whether a standard-user process on fixed local NTFS can combine
private objects, one persistent lock identity, file flushing, handle-relative
replacement and a justified namespace-flush protocol equivalent to the existing
POSIX file-flush/rename/parent-flush sequence. A successful process-kill test
cannot establish sudden-power-loss durability.

## Cases and observations

- Run in a restricted primary-token child with Administrators deny-only,
  medium integrity and privileged capabilities disabled. Record effective token
  facts; refuse to label an elevated runner's own operations standard-user.
- Create scratch directories/files with an explicit protected DACL granting the
  current user and SYSTEM full control. Inspect owner, group and every ACE;
  inherited broad access is not private storage.
- Retain admitted NTFS ancestors. Create/open a persistent single-link lock
  without delete sharing. Prove contention across processes, explicit release,
  deletion refusal while held and release after process death.
- Record exact return and I/O statuses for normal `NtFlushBuffersFileEx` on
  file and writable directory handles before/after same-directory replacement.
  Keep refusals as observations; never substitute a file-only flush silently.
- Use two complete bounded JSON after-images containing current state, history
  and replay identities. Concurrent native writers and repeated request IDs
  exercise the prospective single-file commit shape. Kill a writer at prepared,
  flushed, renamed and pre-response boundaries and inspect whole before/after
  images and same-ID retry.
- Record Unicode/space paths, installed-wheel module hashes, OS/build, Python,
  filesystem, token, statuses and outcome. Keep all scratch activity under a new
  test directory and retain the receipt instead of tuning old evidence.

No native experiment has run at the time this note is written. Read-only source
inspection established that `SavedStore._write` flushes the payload, atomically
replaces `state.json`, then flushes its parent. The existing Windows helper
flushes the payload and renames but expressly excludes power-loss durability.

## Supported argument and gate

Microsoft documents normal `NtFlushBuffersFileEx` as writing cached data and
metadata and synchronizing storage. Its directory access requirements and
namespace coverage need an explicit argument plus observations in user mode.
Record both API return status and I/O status; a successful syscall alone does
not establish a whole durability protocol. `LockFileEx` documents exclusive
locking and OS release after close/death, with resource-dependent release time.

- [Native flush contract](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntflushbuffersfileex)
- [LockFileEx](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-lockfileex)
- [Restricted tokens](https://learn.microsoft.com/en-us/windows/win32/secauthz/restricted-tokens)
- [CreateProcessAsUserW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessasuserw)

Rejected alternatives: `ReplaceFileW` has an unsupported write-through flag;
volume-wide `FlushFileBuffers` requires administrator access; file-only flush
and process-crash recovery silently narrow the current saved commit promise.
An inherited DACL does not establish the intended POSIX 0700/0600 privacy.

The proof runner can pass its observation/consistency checks while its durability
gate remains blocked. Every receipt says production storage is not authorized
by the experiment. T5 waits for reviewed equivalence, or Patrick's explicit
decision supported by these receipts. Completion review: pending.

## Run and inspect

Build and install the wheel without dependencies in a fresh virtual environment.
Run `python -I experiments/platform/windows_saved_store_proof.py --output NEW_DIR`
on native Windows. The new PR/main workflow runs Windows Server 2022 and 2025
with Python 3.10 and 3.12; it never dispatches a workflow manually. The experiment
imports the installed primitive and rejects editable/source-tree installations.

The elevated launcher only constructs a restricted primary token and starts a
suspended child. It assigns that child to the existing kill-on-close Job Object
before resuming it. Timeout terminates the job; cancellation closes the owning
launcher handle, containing descendant writers too. The child performs every
storage observation with Administrators deny-only, medium integrity and no
enabled privilege except SeChangeNotify. This is a recorded restricted-token
profile, not a claim that a separate standard-user account was provisioned.

Read `launcher.json`, `supervisor-job.json`, `receipt.json` and any `failure.json`.
Normal native flush observations are appended immediately to per-process JSONL
files, and immutable phase checkpoints retain preceding observations if a later
consistency case fails. Retained syscall refusals count as blocked feasibility,
even when the observation runner passes. The synthetic `proof_schema` format is
deliberately separate from production saved schema version 1.

Local checks before the first native run: 26 evidence/claim tests pass serially;
the pure wheel builds and its Windows primitive imports under isolated Python
3.10 with no dependencies. These are structural/import checks, not Windows
observations. The native receipt and reviewed semantic argument remain owed.
