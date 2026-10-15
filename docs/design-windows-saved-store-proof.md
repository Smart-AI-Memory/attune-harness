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

## First native observation

[Run 38769182112](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/38769182112)
at head `9433b05d3bc393bbdfdb05a6959060b647da0f5a` failed before Python
initialization in all four server/Python combinations. CreateProcessAsUser and
suspended Job Object assignment succeeded; the child exited with `0xC0000142`
(DLL initialization failed). Retained artifacts contain launcher and job
assignment facts only. There is no saved-storage or durability observation.

The next bounded experiment changes an empty desktop string to NULL, which
inherits the launcher's existing desktop under the documented API contract.
It does not change a desktop DACL or grant the child new privileges. Target-token
and process-exit receipts distinguish a launcher failure from child Python
failure. This is a hypothesis, not an established diagnosis; another failure of
this launch approach triggers strategy review before a third attempt. The first
run's evidence remains unchanged.

## Revised strategy after the second startup failure

[Run 38769648634](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/38769648634)
at `31e578a5cc085e5df60cf6e2b9ca9cd52c022432` also returned `0xC0000142`
before Python in every combination. The target token had medium integrity,
Administrators deny-only and only SeChangeNotify enabled, but retained
TokenIsElevated=true from the built-in Administrator account. No storage API
result was observed. The two-attempt trip-wire stops this launcher strategy.

The next source-independent path uses an already non-elevated medium primary
token, as on the existing Windows 11 guest. A new explicit current-standard mode
refuses an elevated, high-integrity or privileged process. It uses the existing
Job Object bootstrap and inherits that actual primary token into the proof;
it neither creates a restricted token nor impersonates an administrator.
Receipts name existing-standard-primary-v1 and retain the actual token facts.
Root reviews this mode before execution; it cannot qualify the missing server
standard-user fixture by itself.

A separately reviewable CI proposal may provision one disposable local standard
account per ephemeral job, launch its actual primary process and clean only
recorded scratch resources. This is an account/credential route requiring
Patrick's explicit approval. No proposal script is enabled or executed as part
of preparing it. No production saved-storage work proceeds.


## Existing-standard desktop observations and remaining semantic gate

A retained dataset from the unchanged `c2aa750` proof on Windows 11 build 26200
uses an actual non-elevated medium primary token. OS ARM64 runs AMD64 Python
3.12.10 under emulation. The coordinator retained the dataset and the proof
author independently read it, ran its receipt validator and checked its source
hash. Fifty aggregate normal flush observations returned both status values
zero. Eight distinct writers preserved nine history entries including the seed;
eight identical IDs preserved two including the seed and seven replays. Five
process-kill boundaries retained whole before/after images and same-ID retry.
This is desktop primitive evidence; server standard-user observations remain
absent, and no sudden-power-loss experiment occurred.

The unchanged proof SHA-256 is
`b233497ffe18973eca3a4db29b2eca7ee5269c4ae2ef78429a8cf10db1ce7355`;
the retained receipt is
`5a96f4c615e97825c4a90f2772b77ef2baa083a3a11147abb95f7ba809c25ecd`;
and its archive is
`ba61b42290c4791d50c6026a0f557757f8fed621dee53ef254bc4ff75542e963`.
These records remain unchanged. Later workflow/proposal revisions do not alter
which source the historical observations exercised.

Microsoft's [MS-FSA directory-flush algorithm](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fsa/0de7dc40-9627-437e-a4df-c4696cdc3d02)
requires stable persistent attributes, directory metadata/structure and physical
storage flushing. Its [product behavior, footnote 80](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fsa/4e3695bd-7574-4f24-a223-b4679c065b63)
limits the directory-persistence behavior to NTFS; other file systems can return
success without performing it. Mapping this SMB object-store algorithm to the
local user-mode normal native directory flush is an explicit semantic inference
for independent review, supported by the synchronous native flush and IRP
metadata contracts. It is not an established production equivalence claim.

A separate coverage gap remains: the proof creates its output/scratch ancestors
with pathname mkdir and does not flush each new entry's parent. Its immediate
store-parent flush cannot qualify durable publication of the entire new path.
A production port must preserve the POSIX per-created-component barrier. Adding
write-through options would be a new protocol requiring its own review and
observations; the existing receipts do not exercise those options. T2 remains
unpassed and every receipt retains production_port_allowed=false.

## Disabled CI proposal and compilation-only evidence

The PR now includes a separate disabled standard-account proposal and a checker
that parses it as data and compiles only its literal C# into memory. The
coordinator reviewed revision 2's exact source and its independent primary /
teardown failure reports, whole-job-empty deadline, exact-SID cleanup gates,
credential disposal and non-secret cleanup ledger. This is a source review;
native parser/compiler evidence is still owed at this revision.

The new workflow step invokes only the checker with a pinned proposal digest.
It does not invoke the fixture's execution switch, a helper method, account or
credential operations, GUI security objects, or another identity. It retains
`saved-store-proposal-parse-compile.json` before the retired legacy proof route
still reports blocked. Two narrow Git attributes preserve the reviewed PS1
bytes on Windows. A parser/compiler success would establish syntax and C#
compilation only; it cannot authorize or qualify the account fixture or T2.

Receipt searches before this workflow revision found no retained path/hash pin
for the new workflow or proposal sources. The two prior server startup failures
remain valid observations of their original Git heads; they contain no storage
evidence. No historical experiment or receipt is regenerated or rewritten.
The account/credential route remains disabled pending Patrick's explicit OK.
