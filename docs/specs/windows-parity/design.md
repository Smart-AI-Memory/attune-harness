# Windows parity design and acceptance

**Status: approved for staged implementation.** See [scope and journey walk](README.md) and [tasks](tasks.md).
Requirements describe intended behavior; none is evidence of implementation.

## R1: A complete platform inventory

Inventory every public CLI journey, installed extra and platform guard. Record
each supported input profile, dependency, command owner, current refusal, native
witness and remaining gap. Include `fix`, dependent `build`, test handoffs,
file-memory serving, saved linked-task inspection and pending review, in addition
to the four explicit POSIX-only owners.

Acceptance: the inventory agrees with the parser and current source. The full
source suite runs on Windows Python 3.10/3.12 alongside existing qualification.
An expected safety refusal has its own test. No whole feature is skipped merely
to obtain a green Windows job. Native-only and privilege-dependent cases list
their actual coverage and reasons; a missing required case blocks parity.

## R2: Native test execution and handoff

Keep captured Git input, selection, copy integrity, runtime hashes, pytest
observation, output bounds and the single-dispatch recovery contract. Validate
Windows path aliases and reparse components rather than trusting string paths.
Keep Git output decoding and path serialization explicit without changing old
record digests. Do not globally replace historical native paths with POSIX paths.

Use an absolute interpreter and worker. Pass a finite Windows environment with
one validated host SystemRoot, disabled plugin autoload, existing telemetry
controls and explicit text transport. Do not inherit PATH, Python startup flags
or provider credentials just to make the child start. Preserve POSIX behavior.

Acceptance: actual pytest pass, assertion failure, collection/setup failure,
zero tests, collect-only, cancellation and timeout have distinct truthful
outcomes. Prove protected inputs remain unchanged, test writes stay in the copy,
invalid evidence cannot manufacture success, and repeated status/resume never
dispatch again. Complete `fix`/`build` to `test --from-task` with bound provenance
on native Windows, including Unicode and spaces.

## R3: Native file-memory reads and serving

Reuse read-only retained NTFS handles, exact long names, metadata/stream checks
and bounded reads. Walk every ancestor from the volume anchor; do not resolve a
junction away before checking the supplied path. Open no source for writing.
Discover Markdown through retained directory handles; path globbing alone is
not the Windows safety argument.

Preserve current POSIX version tokens. Windows versions bind content hash,
volume/file identity, size, LastWriteTime and ChangeTime observed before and
after the read. Convert the observed write timestamp for document snapshot
mtimes and age annotations; raw TTL/ranking continue to use each record's `ts`.
`Native.metadata` omits timestamps, so copying that entry
alone is insufficient. Confirm file-time semantics against
[FILE_BASIC_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_basic_info).

Confirm absence separately from access failure, alias rejection, reparse points
and concurrent changes. Missing optional sidecars retain their existing absent
meaning. Translate native nonfinal/read-race failures into existing reader
problem envelopes: one bad root can yield partial/unavailable, and an unsafe
pointer remains suppressed instead of raising outside the serving boundary.
Include unsupported-volume `FeatureUnavailable` in the serving refusal boundary.
Preserve the frozen raw-format absence rule: missing `findings.jsonl`, including
a dangling symlink, yields empty raw results without reading its target.

Acceptance: raw, personal and curated recall, complete-source resolve, refresh,
security labels, ranking/TTL and verdict annotations behave as on POSIX. Test
source/sidecar correction, appearance, deletion, timestamp-only change and
same-byte replacement. Native attacks cover root/parent/leaf swaps, junctions,
hard links, ADS, device/UNC paths, aliases and case collisions, without reading
outside sentinels. Test the full 4,096-Markdown-file boundary in one directory
and nested directories; keep the 8 MiB per-file and 64 MiB snapshot limits.
Approved D2 requires Windows to match these limits and preserve existing data
formats; a lower initial Windows capacity profile is not authorized.
Any new directory-enumeration bound needs an explicit compatibility decision;
do not change the effects profile's historical bounds globally.

## R4: Saved-store locking, privacy and commit

Keep schema version 1, canonical UTF-8 bytes, optimistic revisions, withdrawn
history, operation digests and replay results. Records/history/replay/index
metadata remain one authoritative state file. Redis remains a rebuildable,
optional index; its failure never redirects storage or loses authoritative data.

A native storage helper owns retained directory handles, exclusive create/open,
bounded read/write, persistent lock, replacement and flush. Keep validation and
mutation logic in `SavedStore`. Create missing components relative to admitted
parents. Reject reparse points, hardlinked state/lock/temp files, ADS, aliases
and metadata paths. Define the ACL policy for newly created private store
objects; inherited ACLs alone do not prove the intent of POSIX 0700/0600.
Do not rewrite permissions on an existing user directory without a decision.

Use one persistent lock identity. Acquire a nonblocking exclusive byte-range
lock with bounded retries; do not share deletion of the lock or replace it.
Close/unlock on all exits, and prove process-death recovery with distinct
processes. `Native.child` currently permits all sharing, so reusing it unchanged
does not establish this ownership guarantee. Check the native contract against
[LockFileEx](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-lockfileex).

Write a create-new sibling, complete all bytes and flush it, then replace through
the retained directory. Verify the observed after-state. Preserve the difference
between a failure before commit and an uncertain outcome after dispatch; the
same request ID recovers an observed commit without duplication.

### Durability proof gate

Current POSIX storage flushes the file, renames, then flushes the parent at
[memory_saved.py:308–311](../../../src/attune_harness/memory_saved.py#L308).
The existing Windows effects module explicitly excludes power-loss durability.
Reusing its write/rename sequence is not a justified equivalent.

T2 investigates a documented non-administrator namespace-flush protocol, including
whether `NtFlushBuffersFileEx` with normal flags is usable on an appropriately
opened parent after replacement. Microsoft's
[NtFlushBuffersFileEx contract](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntflushbuffersfileex)
describes normal data/metadata flush and storage synchronization; it does not
by itself establish the complete proposed user-mode directory protocol. Retain
access rights, statuses, identity, before/after bytes and the supported argument.
[ReplaceFileW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew)
does not support its write-through flag, and a volume-wide
[FlushFileBuffers](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers)
requires administrator privileges. Neither is an accepted shortcut.

CI crash injection proves process-crash behavior, not sudden-power-loss behavior.
Approved D3 requires equivalent durability under standard user permissions before
production saved-storage implementation. If a supported equivalent cannot be
justified, stop saved-storage work and bring Patrick the retained evidence and
alternatives. Independent approved work may continue. An app-crash-only profile
is not approved as a fallback.

Acceptance after T2: eight concurrent independent saves retain every commit;
eight identical requests sharing one ID all return the same record/revision
and leave one history entry; changed input with that ID conflicts. Competing expected-revision updates have
one winner. Kill at preparation, file flush, rename and pre-response boundaries;
restart/retry yields a whole valid before/after state and no duplicate history.
Inject flush/rename/acknowledgement failures and preserve uncertain outcomes.
Run the complete CLI lifecycle in the README, corruption and byte-bound tests,
linked-task identity checks, pending-review retention and unavailable-index cases.

## R5: Experimental native memory transport

Keep endpoint, SDK pins, model/effort allowlist, system prompt, schemas, canonical
JSON and exposure rules. Add one validated trusted-host SystemRoot only on
Windows; preserve the POSIX map. Scrub ambient proxy, Python-path, provider and
unrelated secret variables. Denied overrides continue to refuse before dispatch.

Use explicit UTF-8 binary helper I/O while preserving the five-entry saved argv
required by [memory_native.py:558](../../../src/attune_harness/memory_native.py#L558).
Do not add `-X utf8` without descriptor compatibility work. Current canonical JSON
escapes non-ASCII characters, so Unicode corruption has not been demonstrated.
The requirement is an explicit transport contract and a native regression.

Acceptance: the actual Job Object bootstrap launches the installed helper.
A test-only trusted child wrapper installs an in-memory HTTP responder and
fail-closed socket guards before calling the real `helper_main`; a parent
monkeypatch cannot cross the isolated child boundary. Record its actual
five-entry argv/runtime and separately witness production-bootstrap refusal
behavior. Add no fake-provider config, endpoint or switch to production.
The real pinned SDK consumes synthetic response bytes; assert exact request,
Unicode round trip, hashes, usage and replay evidence.
Host canaries prove the finite environment. Exercise timeout with descendant
cleanup, bad response/limits, runtime mismatch, missing SDK/key, denied overrides
and authority refusal without SDK transport retries, redispatch after uncertain
outcomes or fabricated success. Preserve authorized reasoning escalation and
sampled semantic audits. The test receipt records positive offline SDK requests,
zero live provider requests and zero live model calls, supported by child guards;
do not change the production envelope's provider-transmission uncertainty.
Core/no-extra tests remain meaningful;
dedicated SDK tests install the existing `memory-native` pins without live access.

### Authorized live acceptance check

D4 authorizes controlled paid Windows validation after
the offline checks pass. Exercise the installed production helper and real
provider endpoint with synthetic input, an existing allowed model/profile,
bounded input/output and a defined call count. Do not introduce a new provider,
change model pins or upload project/private context to obtain a passing check.

Patrick authorized necessary spending for this Windows compatibility process
with a $50 total ceiling on October 15, 2026. This is one shared process budget,
not $50 per agent, PR, model, run or retry. It is a ceiling, not a requirement to
spend it. The authorization replaces the proposed separate per-run spending
approval gate within this scope; do not ask again for already-authorized calls.

Before dispatch, identify the exact Windows/Python/runtime, synthetic request,
allowed model, token limits, call count and current pricing. Reserve a
conservative maximum cost in one coordinated process ledger. Actual spending
plus outstanding reservations plus the next reservation must remain at or below
$50. Count failed billable attempts and retain full reservations for unknown or
in-flight costs until reconciled. Refuse a dispatch whose upper cost bound is
unknown or exceeds the remaining cap. Keep existing account/provider limits in
force; this approval does not imply an account top-up or additional budget.

Retain usage, request/result binding and the observed end-to-end outcome. Stop
on uncertainty or failure; no automatic retry or provider fallback. A corrected
planned attempt within the same scope and remaining budget does not need new
spending approval; unresolved prior effects still stop redispatch. Keep paid
calls outside routine CI. A successful smoke test qualifies
the observed production integration on that Windows configuration; it is not
evidence of model quality or all Windows configurations.

## R6: Shell and documented journeys

Printed commands must preserve literal paths containing spaces, apostrophes,
dollar signs, backticks and non-ASCII text. Test them in the actual declared
shell: Windows PowerShell and PowerShell 7, including legacy and modern native
argument transport. CRT
argument escaping is not shell escaping. Keep POSIX commands unchanged.

Execute documented init, review, fix, plan/build, test, memory and saved-store
journeys from outside the source checkout against the installed wheel. Preserve
explicit preview/acceptance and external/native grants. No JSON filename, output
digest or current command is guessed. WSL is not a native Windows witness.

## R7: Evidence and compatibility

Retain wheel and installed-source hashes, dependency versions, OS build, machine,
filesystem, commands, phase timings, outcomes and skips. Full-suite success,
installed-wheel qualification, SDK compatibility and live model quality remain
separate claims. Read native Windows CI; macOS mocks do not qualify Windows.
Under approved D1, also retain successful Windows 11 desktop installed-wheel
journey results with Python 3.10/3.12 and standard user permissions. Desktop
validation is required before declaring parity and is reported separately from
Windows Server 2022/2025 CI.

Keep the compatibility fixtures, old receipts, accepted state and historical
POSIX token bytes unchanged. Search retained receipts before changing workflow
or experiment inputs. Add new evidence beside old evidence; never regenerate a
receipt to match changed code. Every source PR gets different-model or Patrick
review of its final source head, plus the required suite/wheel checks.

## R8: Truthful completion and recovery

Before advertising parity, update README, qualification guide, CLI guide,
supported journeys and install guidance together. Correct the existing saved
storage platform claim during T1. Record genuine remaining input restrictions;
do not replace an OS-wide refusal with a silent weaker path. Finish the
completion review with verified evidence and useful follow-up boundaries.
