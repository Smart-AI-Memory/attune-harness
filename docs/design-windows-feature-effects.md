# Windows feature and repair effects — design only

September 18, 2026. The installed Windows Job Object and writer-lease profile
qualifies process ownership, but repair and feature file effects still require
POSIX `dir_fd`, `O_NOFOLLOW`, replacement and parent-directory `fsync`. This
design defines the smallest coherent Windows file-effects profile. No Windows
effect implementation or native Windows observation is claimed here.

## Contract and seam

Introduce separate `windows-existing-utf8-v1` and
`windows-feature-effects-v1` manifests. Preserve every accepted POSIX
descriptor, snapshot and replay byte. Platform dispatch belongs at the
existing `repair.freeze`/`validate_scope`/`snapshot`/`replace_file` and
`work_effects.freeze`/`require_platform`/`validate_manifest`/`write_effect`/
`reconcile_effect` seams, with one Windows handle owner behind them. Both the
standalone repair runtime and the feature runtime must accept the new profile
only when the actual Windows primitive checks pass. `process.invoke` must pass
the already validated minimal explicit `environment` into its Windows gated
Job Object bootstrap and ultimately the requested process; its current
`environment is not None` branch rejects Windows. Child cleanup and bounded
stdout/stderr remain the existing Job Object owner's contract.
The Windows accepted probe environment should be exactly the present `PATH`,
`LANG`, `LC_ALL`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONNOUSERSITE=1` controls
plus frozen trusted-host `SystemRoot` if the native loader requires it.
Validate this finite map in `repair.validate_probe`, reject case-insensitive
duplicate keys, and pass the same values into bootstrap and target rather
than inheriting ambient provider/auth variables. Whether `SystemRoot` is
indispensable must be measured on the native runner before requiring it.

The scope remains an exclusively owned dedicated local checkout with a real
`.git` directory, separate task state, bounded UTF-8 files, accepted exact
paths, protected oracles, and no concurrent writer or hostile check program.
Reject UNC/network paths, unsupported volumes, alternate data streams,
device names, case-fold collisions, trailing-dot/space aliases, reparse
points at every ancestor and entry, and multiply linked files before any
effect. The Windows path parser must apply those checks to both accepted
paths and model proposals; it cannot rely on `PurePosixPath` alone.

Open the local volume root and descend one component at a time relative to
retained directory handles. `NtCreateFile` supports a `RootDirectory` handle
and `FILE_OPEN_REPARSE_POINT`; use `OBJ_DONT_REPARSE` so path parsing fails on
an encountered reparse point, then open the final entry itself and examine its
attributes, and reject it rather than traversing it. Keep root and parent
handles alive through each read/create/replace, and compare the volume serial
and full `FileIdInfo` identity to the accepted root/parent identity at each
phase. Check `FileStandardInfo.NumberOfLinks == 1` for files, regular-file
attributes, size and before/after metadata while reading. Enumerate under a
directory handle and reopen each listed entry relative to that handle before
hashing; never trust a path-only stat or the enumeration row as final content
identity. [NtCreateFile](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntcreatefile),
[OBJECT_ATTRIBUTES](https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_object_attributes),
[directory handles](https://learn.microsoft.com/en-us/windows/win32/fileio/obtaining-a-handle-to-a-directory),
[file identity and link count](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/ns-fileapi-by_handle_file_information).

Retain the whole-tree snapshot invariant. The Windows snapshot needs file
SHA-256 and bounded length, type, attributes/security policy, directory
identity and a stable per-path parent identity. Existing POSIX `mode` cannot
serve as a Windows ACL equivalence proof. A Windows manifest must freeze the
specific attribute/DACL policy it can preserve and reject unsupported
metadata or alternate streams; verified post-effects metadata belongs in the
durable effect receipt so resume compares observed after-images without
inventing deterministic file IDs. No `st_dev`/`st_ino` assumption is silently
reused on ReFS. All planned operations and protected files are validated
before the first write.

For replacement, create a unique sibling with create-new semantics through
the retained parent, write the exact bytes, flush the file handle, check the
old file's current identity/content/attributes, then perform same-parent
handle-relative replacement with `SetFileInformationByHandle`/`FileRenameInfoEx`
and `RootDirectory`. Treat any rename/share/flush error after prepared dispatch
as effects-unknown; reconcile by full snapshot and exact before/after bytes,
never replay automatically. For creation, use create-new file/directory under
the retained parent and reject collisions; record generated identity and
attributes only after durable observation. Native `ReplaceFileW` may be useful
for metadata merge, but it is path based, and its `WRITE_THROUGH` flag is
documented as unsupported; it cannot be substituted for the handle-bound
replacement and a tested durability rule.
[handle-relative rename](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_rename_info),
[ReplaceFileW limitations](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew),
[FlushFileBuffers](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers).
On lost acknowledgement, the replacement target has a new identity but no
completed journal result. Compare every non-target identity and protected
metadata to the accepted snapshot, compare the target's exact proposed bytes
and accepted attributes/DACL, then append the observed target identity to the
reconciled receipt. Do not fabricate a deterministic Windows after-entry from
proposal text alone.

The exact Windows durability claim must be decided by native tests. Flushing a
file handle is documented; treating a directory handle flush as equivalent to
POSIX parent `fsync`, or claiming power-loss durability from macOS simulation,
is not established. The honest first profile can guarantee atomic namespace
replacement and process-crash reconciliation on qualified local NTFS, while
classifying power-loss durability as unqualified until evidence supports it.
If the handle-relative rename or metadata-preservation behavior cannot be
proved on supported Windows builds, retain explicit unsupported status rather
than falling back to a path-based, check-then-write profile.

## Native qualification before support

First run a small real-Windows primitive spike before broad owner integration:
prove exact `NtCreateFile` and `FileRenameInfoEx` structure layouts and
information-class constants, access/share/delete flags, `RootDirectory` with
a single leaf, replacement under the retained parent, and observed
attributes/DACL preservation. If any primitive fails, stop before changing
task ownership or claiming support. API-name availability on macOS cannot
establish these behaviors.

The disposable experiment is `experiments/platform/windows_effects_probe.py`.
It uses a local NTFS temporary directory, retains real root/parent handles,
opens each Unicode leaf relative to its parent, verifies file identities,
hardlink and final reparse refusal, creates and flushes a sibling, and tries
`SetFileInformationByHandle(FileRenameInfoEx)` with a retained parent handle
and a single target leaf. It then discards any notion of a completed rename
result and independently observes the after-image through a new handle,
including bytes, identity, ordinary attributes and inherited DACL fingerprint.
Failure yields a nonzero exit and a JSON receipt with the exact NTSTATUS or
Win32 error. A passing default inherited DACL observation does not prove
preservation of a deliberately distinct target ACL. It also cannot prove
atomicity under concurrent readers or power-loss durability. The dedicated
`.github/workflows/windows-effects-primitive.yml` runs only on the isolated
`codex/windows-effects-probe-20260918` push or explicit dispatch, preserving
failed receipts for both Python 3.10 and 3.12; only a real runner result can
advance the profile design.

The first native run (`35415783622`, commit `cdc18f5850fb5608e7b0e7983115ed3a06e2fc7c`)
proved the preliminary environment, identity, hardlink and reparse checks but
failed replacement on both runtimes with Win32 error 87. Its rename payload
was two bytes smaller than Microsoft's documented minimum of
`sizeof(FILE_RENAME_INFORMATION) + FileNameLength` on the observed x64 layout.
The narrow second probe corrects the payload length while preserving the same
retained parent handle, `FileRenameInfoEx` class and flags. Until a native
rerun observes the after-image, replacement and Windows effects remain
unsupported. The first negative receipts are retained alongside the probe
evidence chain.

Build/install one frozen wheel outside source on actual Windows Python 3.10
and 3.12, local NTFS. Run both standalone repair and feature effects end to end:
exact replacement, new file/directory creation, protected oracle unchanged,
Unicode/spaced paths, case-fold aliases, ADS, reserved names, root/parent/file
reparse points, hardlinks, metadata/ACL differences, collision refusal,
bounded snapshot, staged failed control, interrupted write, lost
acknowledgement, explicit retry of unchanged preimage, after-image reconcile,
and a resumed job without duplicate writes. Assert root and parent identity,
full tree before/after, source/wheel import origins, no writes on intake
refusal, and no process descendants after timeout/cancellation. Exercise
`process.invoke(environment=...)` with a hostile ambient canary and verify
the actual child sees only the accepted minimal environment. Record OS build,
filesystem, runtime, and executable hashes with the receipts. Existing macOS
tests can check structural contracts but cannot qualify these native effects.

## Exact source touch points

- `repair.py`: `root_handle`, `parent_handle`, `read_file`, `snapshot`,
  `freeze`, `replace_file`, `reconcile_replacement`, `validate_scope`, and
  `validate_probe`'s finite environment; add a
  Windows primitive owner without changing POSIX serialization.
- `work_effects.py`: platform/profile dispatch, effect freeze, creation,
  replacement, reconciliation and `validate_journal`; derive expected Windows
  after-state from completed observed receipts.
- `process.py` and `windows.py`/`_windows_worker.py`: pass the validated
  environment through the gated Job Object child and retain cleanup semantics.
- `task_contract.py`/`task_policies.py` and `task_handoff.py` (standalone
  repair owner and completed provenance), `assessment_effects.completed_patches`,
  `work_contract.py`/`work_runtime.py`, and `work_build.py` (including its
  direct `after_entry` comparison): admit the new profile/observed receipts
  while preserving old accepted POSIX runs and exact recovery projection.
- `tests/test_task_repair_effects.py`, `tests/test_work_effects.py`,
  `tests/test_process.py`, and platform qualifier selections: add Windows
  native cases and keep the current POSIX-specific cases gated by platform.
