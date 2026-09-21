# Windows file-effects backend from the observed native primitive

September 18, 2026. This is an implementation design, not a Windows effects
qualification. It supersedes the rename selection in
`design-windows-feature-effects.md`; that document remains the pre-probe record.
The immutable [native success chain](receipts/release-readiness-current/windows-feature-effects/primitive-native-success-chain.json)
binds run 35416700935, commit `4d98fa93968b77d9ecffcd247c976fca12621783`,
and separately hashed Python 3.10/3.12 receipts. Both runners saw Win32
`SetFileInformationByHandle(FileRenameInfoEx=22)` reject a retained parent
with error 87. They saw `NtSetInformationFile(FileRenameInformationEx=65)`
with a retained parent and single target leaf replace successfully in cases
B/C/D, and classic class 10 in E; independent reopened-handle after-images
confirmed exact bytes, new target identity, unchanged root/parent/protected
identities, and ordinary attributes/inherited DACL. Null-root case F is a
diagnostic control and cannot qualify handle-relative production behavior.
This is only a scratch local-NTFS primitive observation. Distinct target ACL,
nonstandard attributes, directory creation, process-crash recovery, concurrent
atomicity, power-loss durability, and integration remain unqualified.

## Profile and admission

Add `windows-existing-utf8-v1` and `windows-feature-effects-v1` profiles
without changing POSIX profile constants, accepted snapshots, event results,
prompt bytes, or journal validation. Dispatch only by the accepted plan's
profile and actual `os.name == 'nt'`; the converse fails closed. Keep the
standalone repair and feature owners, recovery cursor, operation budgets,
required controls and freshness checks. A Windows plan is frozen before
acceptance and carries a versioned policy marker, canonical checkout root,
root volume+128-bit file ID, explicit allowed/protected paths, full before
snapshot, and fixed probe executable hash. No accepted request can switch
profiles by revising a journal. Old POSIX runs remain readable on their
qualified platform with their exact historical projection.

The first eligible volume is a fixed local NTFS drive-letter volume; reject
UNC, network, removable, ReFS and uncertain filesystem identity. Require a
dedicated real `.git` directory and task state outside the checkout. The
root, each path ancestor and each traversed entry must be opened with
retained handles. Use `NtCreateFile` with a parent `RootDirectory`, a single
leaf, `OBJ_DONT_REPARSE` and `FILE_OPEN_REPARSE_POINT`; observe type,
`FileIdInfo`, `FileStandardInfo`, `FileBasicInfo`, security and streams from
the opened handle. Do not rely on `Path.stat()` or a string path between
authority check and effect. Bootstrap the root from the fixed volume root
one component at a time and compare its frozen identity. Reject reparse
points, multiply linked files, alternate data streams, deleted/pending
entries, unsupported editable-file attributes, custom editable-file DACLs,
casefold or short-name *path references*,
trailing space/dot, colon, reserved device names, and noncanonical separators
before dispatch. Enumeration must be complete and bounded (1000 entries,
16 MiB total file bytes), and reopen every enumerated leaf relative to its
parent before hashing. Canonical proposal paths receive the same validation
as accepted paths. If a metadata category cannot be observed reliably, refuse
the plan before any write. Do not reject a legitimate long filename merely
because NTFS assigned it an 8.3 alias: reject a request whose component is
not byte-for-byte the enumerated long name. Immutable `.git`, directory and
protected entries may carry hidden/system/readonly attributes; freeze their
observed attributes, security and identities and require exact preservation,
while rejecting reparse points and unsupported streams everywhere.

The initial replacement eligibility is deliberately narrow: existing single
link UTF-8 file ≤64 KiB, ordinary archive/normal attributes, no alternate
streams, and an inherited-only DACL. Observe the target security descriptor
read-only: reject `SE_DACL_PROTECTED`, any non-inherited ACE, absent/null DACL,
or inability to parse every ACE. This is an explicit policy check, not a
comparison of the parent and child DACL hashes (their ACE flags can differ).
Freeze the exact target DACL and full owner/group/DACL security fingerprints.
The prepared sibling must have those same fingerprints and accepted attributes after creation; otherwise stop
before rename and retain an effect-attempt/cleanup receipt; this is not a
zero-write intake refusal. Distinct target DACL/attributes are rejected,
rather than promised preservation. File creation and missing-directory creation have
separate eligibility and native tests; a profile can reject those operations
until their handle-relative `FILE_CREATE`/collision/metadata observations
pass on both Windows runtimes. This must be explicit to intake, never a
runtime fallback to path-based writes.

## Operation, snapshot, and recovery

Replacement: open and recheck root/parent/target identity, bytes and metadata;
create a unique sibling with `NtCreateFile(FILE_CREATE)` through that parent;
write exact bytes and `FlushFileBuffers`; recheck the old target and prepared
sibling; call `NtSetInformationFile` class 65 with flags 3, retained parent
handle and exact UTF-16 single target leaf. Treat return 0 as completed
dispatch; `STATUS_PENDING`/other nonfinal positive values and any exception
after the prepared event are effects-unknown. For synchronous negative status,
the returned NTSTATUS is authoritative, but observe the full after-image
before permitting an explicit retry. Record the returned status and
`IO_STATUS_BLOCK.Status` separately; do not infer success from the latter.
Close handles and clean an unrenamed temp only after observing that it still
has the prepared identity. Never claim a parent-directory flush or power-loss
durability from the file flush.

An observed Windows snapshot entry contains type, volume+file ID,
parent identity, attributes, DACL and owner/group/DACL fingerprints, link count, byte count and
SHA-256 for files. Directory entries omit unstable directory size. The
versioned Windows snapshot has a separate root entry with its full identity,
type, attributes, DACL and link count; root metadata is compared on every
freshness check. It includes protected inputs and unrelated files as well.
Completed effect results contain the exact observed post-entry, including
the new file ID; it cannot be derived from proposal bytes. On replay,
`expected_snapshot` projects *completed recorded results* into the accepted
before snapshot; validate each result against its item, parent and expected
text hash. Standalone repair receipts keep their existing path/hash/byte
fields and add a versioned observed after-entry only for the Windows profile.
`assessment_effects.completed_patches` and `work_build` compare the
profile-specific result, without relaxing the POSIX equality checks.

For a dispatching event with no completed result, independently resnapshot
the entire checkout. Compare all non-target identities and metadata exactly
with the expected prior state. The target can be (a) the exact accepted
before-entry, allowing *explicit* bounded retry if requested, or (b) exact
proposed bytes with accepted ordinary attributes/DACL and a new observed
identity, allowing reconciliation to append the actual result. Anything
partial, missing, colliding, or altered outside the target remains unresolved.
Creation reconciliation likewise checks absence versus exact new entry and
parent identity; directory creation cannot be projected deterministically.
An orphan prepared sibling after a failed dispatch is not silently ignored:
it appears in the full snapshot and needs explicit operator resolution.
The guarantee is process-crash after-image observation under exclusive owner,
not crash-proof durability or concurrent-writer isolation.

`repair.validate_probe` accepts only a finite Windows map with
`PYTHONDONTWRITEBYTECODE=1`, `PYTHONNOUSERSITE=1`, optional accepted
`PATH`/`LANG`/`LC_ALL`, and exactly one `SystemRoot`; reject casefold duplicate
keys and NUL. The executable remains absolute and outside the checkout. The
process owner separately passes the *exact copied map* to bootstrap and
target; `environment=None` retains legacy inheritance. No ambient merge.

## Source seams and qualification gate

Implement native handle/metadata operations in one platform-gated module.
`repair.py` dispatches freeze/snapshot/replacement/reconciliation/scope/probe;
`work_effects.py` dispatches manifest/creation/journal/projection/reconcile;
`task_contract.py` admits the new repair profile; `work_build.py` compares
the observed result; `assessment_effects.py` retains the profile-specific
completed repair result. Check `task_policies.py` and `task_handoff.py` for
unchanged-owner assumptions. Do not edit `process.py`, `windows.py`, or
`_windows_worker.py` in this lane; the parent owns exact environment transport.

First run structural and copied-source mutation tests locally without
pretending macOS qualifies native behavior. Then build a frozen wheel and run
native installed tests on isolated Windows Python 3.10 and 3.12: real
standalone repair and feature replacement, file/directory creation or
explicit pre-dispatch refusal, Unicode/spaces, collision and metadata
refusal with zero writes, path aliases/ADS/reparse/hardlinks, required check,
whole-tree protected oracle, lost-ack after-image reconciliation, before
retry, pause/resume and byte-identical POSIX preservation. Bind executed
source/wheel bytes, runner OS/NTFS identity and before/after receipts. Only
those passing installed journeys can move a Windows effect profile from
implemented to qualified. Missing process environment support or any
unproven effect kind remains explicitly unavailable.
