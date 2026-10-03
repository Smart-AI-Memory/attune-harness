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

## 6. The checkout rewrites line endings

**Symptom.** A test that pins a fixture by SHA-256 passed on macOS and
Ubuntu and failed on both Windows jobs with a different digest for the same
committed file. **Why.** The Windows runners check out with `core.autocrlf`
on, so every file Git classifies as text is written with `\r\n`; the bytes
on disk are not the bytes in the repository. **Do.** Mark fixtures that are
compared by bytes with `-text` in `.gitattributes` so no conversion happens,
and hash line-ending-normalised bytes as the backstop for a clone made
without the attribute. **Where.** `.gitattributes`,
`tests/test_memory_fixture_contract.py` (#79).

Signed plugin bundles need the same protection. A manifest or skill converted
from LF to CRLF changes its artifact digest, so a previously signed bundle
refuses with "Plugin artifact changed after it was signed". Preserve the
manifest, skill and archive bytes from signing through installation; mark
the signed text files `-text` before signing when keeping them in Git. Do
not normalize an already signed bundle to make it pass: restore the original
bytes, or deliberately sign the changed artifact again. **Where.**
`extensions.discover`, `plugin_signing.verify_bundle` (#118),
[signed plugin guidance](executable-plugin-run.md).

## 7. GPG discovery can select the working directory

**Symptom.** A local `gpg.exe` or `gpg.bat` is selected instead of the intended
verifier, or Git for Windows' GPG is reported missing because it is not on
PATH. **Why.** Python 3.10/3.11 `shutil.which` prefers the working directory
on Windows; Git for Windows also ships GPG outside the usual PATH. **Do.**
Use `plugin_signing.find_gpg`, which searches absolute PATH entries directly,
then known install locations, and returns an absolute executable. Inspect the
recorded verifier path if discovery surprises you; install GnuPG or add its
directory to PATH when it is absent. **Where.**
`plugin_signing.find_gpg`, `known_gpg_locations`,
`tests/test_plugin_signing.py` (#118).

## 8. GPG builds disagree about home-directory paths

**Symptom.** Git for Windows' GPG cannot start its agent when given
`C:\\Users\\...` or `C:/Users/...` as `--homedir`. **Why.** Its MSYS build
treats paths without a leading slash as relative when composing lock-file
names. Native Windows GPG uses drive-qualified paths. **Do.** Use
`plugin_signing.probe_gpg` and `gpg_path`: MSYS receives `/c/Users/...`,
native GPG receives `C:/Users/...`. Forward slashes alone do not fix the
MSYS case. Cygwin's `/cygdrive/c/` spelling is not handled. Verification uses
a private home with `--no-options`, not the user's keyring or option files.
**Where.** `plugin_signing.gpg_path`, `probe_gpg`, and the verifier-home
spy test in `tests/test_plugin_signing.py` (#118).

## 9. A drive-relative capture path can escape its root

**Symptom.** A capture entry such as `C:x` looks relative but names a Windows
drive; `C:/x` is also invalid as a capture member. **Why.** POSIX path parsing
does not recognize Windows drives, while Windows distinguishes a drive's
current directory from its root. **Do.** Capture members use canonical
relative POSIX names such as `task/record.json`, with no drive, backslash or
traversal. Keep the absolute capture root separate from its member names.
The capture validator rejects Windows drives on every host, so producing a
capture on POSIX does not make a drive-qualified member portable.
**Where.** `scripts/compat_capture.py` (`_relative`) and
`tests/test_compat_capture.py`.

## 10. Suite and CI job deadlines are different budgets

**Symptom.** An installed qualification suite exits 124 while the hosted job
still has time left. **Why.** `qualify_platform.py` allows 900 seconds
(15 minutes) for its selected suite, while the installed qualification job
allows 20 minutes for setup, checks and evidence upload. Individual operation
deadlines still apply. **Do.** Read the retained receipt and test timings;
distinguish a suite timeout from an assertion failure or the outer job's
timeout. A larger job budget does not extend the suite budget. Investigate
recurring overruns before changing a deadline.

Supplemental coverage is a separate measurement. Windows temporarily has a
1,200-second instrumented suite budget, a 1,380-second measurement-wrapper
budget, and a 30-minute hosted job budget while recurring overruns are
investigated. The full POSIX measurement retains its 1,200-second wrapper
and 25-minute hosted job. Normal installed qualification remains at 900
seconds, and individual operation deadlines remain unchanged. A successful
instrumented measurement does not constitute platform qualification.
**Where.**
`scripts/qualify_platform.py`, `scripts/measure_coverage.py`,
`.github/workflows/qualification.yml`, `.github/workflows/coverage.yml`,
[qualification guide](qualification.md),
[coverage measurement guide](coverage-measurement.md).

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
- **A copied Python binary may not start (macOS).** python-build-standalone
  (uv's Python, and so this repo's usual venv) links a shared
  `libpython` through `@executable_path/../lib`, so a copy of the binary
  outside its install aborts in dyld with `-6` before running a line. The code
  signature is not the cause; appending to the copy afterwards is fine. A test
  that copies an interpreter must put the base prefix's `libpython*` beside
  it. `test_interpreter_drift_is_detected_without_modifying_installed_python`
  does. CI never showed it: the full suite runs only on Linux.
