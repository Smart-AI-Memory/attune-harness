# Native Windows execution and recovery

Status: bounded opportunity-5 implementation, 2026-09-15. GitHub now supplies
actual Windows runners; the earlier reason for deferring Windows probes is resolved.

Cases: correct stdout/stderr and exit code; launch failure; timeout/cancel; oversized
or invalid output; ordinary descendants surviving their direct parent; owner crash;
concurrent writer refusal and lock release after death; Unicode/spaced paths; resumed
review does not repeat completed work. Reparse-point lock files must be rejected.

Before-code evidence: local source confirms POSIX-only process and lease branches.
The first GitHub matrix executes Windows portable checks and explicitly verifies
that boundary. Microsoft's Job Objects documentation establishes child inheritance,
nested jobs and kill-on-last-handle-close; AssignProcessToJobObject must precede
launching user code. Python exposes nonblocking Windows byte-range file locking.
Native behavior remains unqualified until the new Windows tests actually run.

Design: keep the POSIX path. A Windows Job Object owns a tiny trusted bootstrap;
the bootstrap waits for a private start gate, so no requested command can run
before successful job assignment. Closing the noninherited job handle terminates
ordinary descendants, including after parent death. The bootstrap passes argv and
stdio without shell interpolation. Failed assignment stops before opening the gate.
Use Windows nonblocking byte locks for the existing single-writer lease, opening
the lock with reparse-point handling and rejecting reparse targets.

Limits: process supervision is not a security sandbox; out-of-band remote effects
remain unknown. Crash/recovery probes do not establish power-loss durability or
network-filesystem semantics. Old Windows versions and breakaway-capable external
services are outside the tested runner matrix.

Reject taskkill-by-PID: PID reuse and parent-exit races weaken descendant cleanup.
Reject writing a custom full process launcher: a gated trusted bootstrap lets
Python keep argv quoting and inherited standard streams consistent.

Preserve dev10 and its in-flight installed-model campaign. Build this addition as
dev11 in a separate environment. Run installed native tests on GitHub Windows,
macOS and Linux before claiming support; retain failed runs and their fixes.

References: [Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects),
[AssignProcessToJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject),
[Python Windows locks](https://docs.python.org/3/library/msvcrt.html#msvcrt.locking).
