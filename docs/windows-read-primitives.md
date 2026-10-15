# Windows read primitives

`attune_harness.windows_reads.open_read_root()` provides read-only observations
for the Windows testing and file-memory ports. This helper does not enable those
features by itself. Each consumer continues to own its public records, version
tokens, allowed paths, selected-file limit and aggregate byte budget.

```python
from attune_harness.windows_reads import open_read_root

with open_read_root(source_root) as root:
    observed = root.read_many(
        ['notes/topic.md', 'notes/second.md'],
        max_files=2,
        max_bytes=8 * 1024 * 1024,
        max_total_bytes=16 * 1024 * 1024,
    )
    # Bind the consumer's own versions to each observation's entry and times.
```

The supplied root must be an absolute path below a fixed local NTFS drive
anchor. The helper checks the supplied spelling without calling `resolve()`.
It walks exact long names from the volume handle and retains every admitted
ancestor. Relative names use `/`. Device and UNC paths, dot components, ADS
syntax, reserved names, aliases, reparse points and multiply linked files refuse.
Native metadata also checks stream and security evidence. Source handles request
no write, create or delete access.

`root.entry` supplies copied root identity and metadata. `read()` returns a
`FileObservation` with `data`, `entry`, `times`, `sha256`, `size` and `mtime_ns`.
The entry includes the native volume/file identity, parent identity, attributes,
security hashes, link count, observed size and content SHA-256. The timestamp
mapping contains native creation, write and change ticks. These
[FILE_BASIC_INFO times](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_basic_info)
use 100-nanosecond intervals since 1601; `mtime_ns` converts the observed write
time to Unix nanoseconds. Last-access time is excluded because a read can affect
it. No generic serialized version token is defined here.

Each named open uses fresh, completed directory scans and checks the exact name
again after opening. Reads compare identity, metadata, size and native times
before and after capturing bounded bytes, then recheck the leaf and retained
ancestor/parent bindings. Discovery checks directory contents and bindings before
returning. There is no timestamp-based listing cache. Root operations are
serialized with a reentrant lock; a discovery selector can perform a read.
Context exit waits for active operations and closes the retained handles under
that same lock.

`read_many()` captures canonical named requests in one locked operation. Its file
count, per-file byte allowance and aggregate byte allowance are independent caller
bounds. It retains selected file and parent handles, completes each directory scan
before admission, and shares those observations only inside the operation. Before
returning, it compares retained file state, completes fresh directory scans,
reopens exact names and compares their identities and metadata, then scans again
and rechecks ancestor bindings. Directory timestamps alone never authorize reuse.
No scan or negative absence result survives the call. This avoids rescanning the
whole directory for every selected file while preserving final binding checks.

Discovery and capture remain separate APIs. Calling `files()` followed by
`read_many()` does not itself prove an atomic discovery snapshot; the consumer
must supply its discovery and selection contract. This additive API does not
resolve the T4 eligibility and raw-sidecar gates below. Individual `read()` calls
retain their existing fresh named-open checks.
As with the effects primitives, this detects observed changes without claiming
isolation from an arbitrary hostile concurrent writer.

Discovery counts only files accepted by `select`. Incidental entries and
subdirectories do not consume `max_files`, and the helper adds no incidental
entry cap. It returns the complete sorted selection. `Native.iter_names()`
finishes its scan before exposing an iterator, preventing a suspended scan from
sharing a directory cursor with another operation. The effects-facing
`Native.names()` and `canonical_child()` retain their historical 2,048-entry
bound and refusal behavior.

`FileNotFoundError` means a completed listing did not contain the name and the
read-only child probe returned `STATUS_NO_SUCH_FILE` (`0xC000000F`) or
`STATUS_OBJECT_NAME_NOT_FOUND` (`0xC0000034`), with the parent observation still
unchanged. These are the only accepted absence statuses from the
[NTSTATUS reference](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-erref/596a1078-e883-4972-9bbc-49e60bebca55).
A successful probe of an unlisted spelling is an alias or race and refuses.
An enumerated name that disappears is a freshness failure. Access failures,
`STATUS_OBJECT_PATH_NOT_FOUND`, stream failures and other native errors do not
become absence. An internal confirmed-missing marker crosses to public
`FileNotFoundError` only for that positive evidence; a `FileNotFoundError` from
metadata or enumeration becomes a safety `ValueError`. Nonfinal native operations
become `ValueError`; ordinary native
failures remain `OSError`, and unsupported platforms or volumes retain
`FeatureUnavailable`. For a multi-name batch, `FileNotFoundError` refuses the
whole batch at the first missing name; it does not identify a per-item absence
or prove that later requests are eligible. Never treat that refusal as an
optional sidecar being absent. Use `read()` or a single-name batch for that rule.

The qualification-selected `tests/test_windows_reads.py` exercises actual NTFS
handles on Windows. Its portable directory-parser fixtures test ABI-shaped
records and effects-bound preservation; they do not count as native filesystem
observations. Passing these tests does not qualify the later consumer ports or
change the README platform claims.

Consumer eligibility remains an explicit T4 gate. Current generic discovery
validates incidental entries as well as selected files. POSIX file-memory rejects
any corpus symlink, but ignores non-Markdown hardlinks that are not sidecars;
strict native discovery currently refuses those hardlinks. Windows stream/name
eligibility also needs its consumer decision before R3 closes. This primitive
does not establish parity for those input profiles. The raw-tier dangling
`findings.jsonl` exception remains a raw-owner responsibility; a generic
`ValueError` must never become absence.
