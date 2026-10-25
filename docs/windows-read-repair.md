# Bounded Windows reads and metadata-witness diagnostics

Two Windows jobs in [qualification run 40205967961](https://github.com/Smart-AI-Memory/attune-harness/actions/runs/40205967961)
failed in code identical to its qualified main. One record poll raised
`PermissionError` opening `record.json`. A separate raw-link test raised a
metadata-change refusal in its after-query witness, before recording the reader
result. Neither artifact establishes the underlying Windows mechanism.

## Record reads

Retry only `PermissionError` on Windows, within a two-second monotonic budget
and with at most a five-millisecond wait between attempts. Each attempt repeats
the original complete regular-file, byte-bound and UTF-8 read. Persistent denial
still raises; other failures and POSIX behavior retain their existing handling.
The budget bounds retries, not an individual blocking operating-system call.

A disposable control experiment used the exact original reader with injected
open denials and a fake clock. Fifteen controls showed a transient denial
propagating in the original, recovery on the proposed second attempt, bounded
persistent failure, and unchanged encoding, size and other refusal behavior.
This was not a native Windows reproduction or a diagnosis of the failed run.
Reject catching the error only in the test poller: the production reader is the
owner of this input boundary. Request and qualification timeouts stay unchanged.

## Metadata witness

Keep the production guard and every existing assertion. Test-only instrumentation
copies Basic-info samples and intermediate attributes already returned by existing
calls, labels the current query or witness, and emits them on a metadata refusal.
It must forward calls and return values unchanged and make no additional filesystem
reads. Record the reader packet immediately after the query, before an after-query
witness can fail. Diagnostics can affect scheduling; a later passing run alone
does not explain the retained failure.

Controls cover sample copying, original exceptions, call/return identity, phase
labels, bounded diagnostic retention and the exact guard comparisons. Reject
retrying admission, replacing the witness or relaxing assertions without evidence.

## Qualification boundary

Require focused controls, the full suite, an installed-wheel qualifier, independent
source review and fresh Windows CI. Report diagnostic observations separately from
any demonstrated repair. This change does not qualify Windows desktop acceptance,
general platform parity or the planned hydration writer.
