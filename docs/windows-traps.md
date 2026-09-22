# Windows traps

Each of these cost a review finding or a failed platform job in September
2026, and none was in anyone's head until then. One entry each: the symptom,
why Windows differs, what to do, and where the fix lives. Read this against
any change that touches files, names, processes or the console; step 5 of
[the review brief](review-brief.md) points here. macOS shares the second trap,
so it is not only the Windows runner that shows these.

## 1. Append tears lines

**Symptom.** A JSONL file with one process's line split by another's, only on
the Windows runner. **Why.** The C runtime emulates `O_APPEND` as a seek to
the end followed by a write, under a lock that is local to the process; POSIX
`O_APPEND` positions and writes atomically for each call. **Do.** Take a
cross-process lock before the write: `msvcrt.locking` at an offset past any
plausible file size (`1 << 40` reaches `LockFileEx` with the full 64-bit
offset), `LK_NBLCK` with a bounded retry, `flock` non-blocking elsewhere, and
`lseek` to the end yourself before writing rather than trusting the runtime's
re-seek. **Where.** `command_workspace.jsonl_event_writer` (#61).

## 2. File names fold case

**Symptom.** Two keys differing only by case became one file and one of them
vanished from a listing. NTFS and the default APFS both do this. **Why.** The
file system is case-insensitive and case-preserving; the second name opens
the first file. **Do.** Never let a user-supplied string be a file name.
Percent-encode everything outside `[a-z0-9_.-]`, upper-case letters included,
and test with `A` and `a` stored side by side. **Where.**
`memory_scratch.FileScratch._name` (#67).

## 3. Device names are files everywhere

**Symptom.** A key named `CON`, `NUL`, `PRN`, `AUX`, `COM1` to `COM9` or
`LPT1` to `LPT9` passed validation. On Windows a path ending in one of these,
with or without an extension, opens the device, in any directory. **Do.**
Prefix every generated name so it is never bare (`k-` in the scratch store),
or refuse the names outright, and test them by name and by round trip.
**Where.** `memory_scratch.FileScratch._name` (#67).

## 4. Replace fails while another process holds the file

**Symptom.** `os.replace` raised `PermissionError`, and a refusal message the
tests had never seen appeared on the losing side of a race. **Why.** A
Windows open denies delete sharing by default, so a rename over a file
another process has open is refused; POSIX renames the directory entry and
the other process keeps its handle. **Do.** Retry the replace for a bounded
time, two seconds like the other retries in the codebase, through
`features.replace_file`, and list the resulting refusal wherever two
processes can race. The README's known limit, that a process holding a run's
`record.json` open for more than about two seconds fails that run closed, is
this trap at the run store. **Where.** `features.replace_file`,
`review_store._replace` (#61).

## 5. Console scripts live under `Scripts\`

**Symptom.** An installed check looked for `python.parent / 'attune-harness'`
and crashed on the Windows 3.12 job. **Why.** POSIX puts console scripts in
`bin/` beside `python`; Windows puts `attune-harness.exe` in `Scripts\`,
beside a venv's `python.exe` or one level below an interpreter installed at
a root such as the hosted tool cache. **Do.** Resolve the entry point through
`check_installed.console_script`, which tries all four places. **Where.**
`scripts/check_installed.py` (#68).

## Also worth remembering

- **Text mode translates newlines.** A writer that must produce exact bytes
  opens in binary; the event writer does, with `os.O_BINARY` guarded by
  `hasattr` because POSIX has no such flag.
- **`fcntl` and `O_NOFOLLOW` are POSIX.** Import `fcntl` inside a guard and
  `getattr(os, 'O_NOFOLLOW', 0)`; the platform jobs are the first place an
  unguarded import fails.
- **Symlinks need a privilege.** Tests that create a symlink skip on Windows
  without it; a symlink check in the code still runs, and the parent-directory
  pre-check is the part that works everywhere.
- **Subprocess tests prepend to `PYTHONPATH`** rather than replacing it, use
  `-u` for unbuffered pipes, and kill children in a `finally`; an overlap that
  depends on interpreter start-up timing is not an overlap on a slow runner,
  so release the children together on a barrier (stdin) instead.
- **A stale installed check is a Windows failure first.** The Windows jobs
  run the installed wheel from outside the source tree with `-I`; a path
  assumption the macOS job tolerates fails there.
