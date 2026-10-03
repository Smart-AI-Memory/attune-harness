# Shared source review and bounded roundtable

This additive layer is callable by either coding host through the same CLI.
It does not replace documentary `review`, repair, Spec approval or merge rules.
The chair owns acceptance; participant answers remain proposals.

## Boundary and cases

Prepare captures explicitly selected UTF-8 files into a bounded, hashed source
snapshot and stores the named author, participants, question and call budget.
Source review requires one reviewer with a different provider/model pair;
roundtable requires two or three distinct pairs and one or two rounds. The first
round is independent. Subsequent turns see the completed preceding round, never
the chair's lean. Each answer includes a verdict and source evidence. Findings
and disagreement survive without a paid synthesis or an automatic promotion.

Refuse aliases with the same configured model identity, symlinks, escaped paths,
repository metadata, oversized sources, excessive rounds, stale acceptance,
copied records and changed snapshot contents. Native identity is recorded as
requested and runtime-reported separately: Codex currently reports a thread,
not a model, so an authenticated actual-model claim is unavailable. Command
participants declare a provider/model and implement the existing JSON exchange
protocol; their identity is self-reported, never authenticated.

Use `RunStore`'s exclusive directory, atomic checkpoint and writer lease, and
`RecoveryCursor`'s saved-before-dispatch journal. Completed turns replay without
calls. An interrupted dispatch remains unresolved; resume cannot repeat it.
Reconciliation may abandon an uncertain run, preserving its journal, but cannot
assert that inference or charges did not occur. A paused run can continue its
remaining accepted turns. Cancellation is accepted between turns or through
the supervised owner's cancellation signal. No model supplies authority.

## Evidence before code

The October 1 audit's real subprocess probe reproduces A1: ordinary Claude
exit-1 structured refusal becomes `nonzero_exit`, losing its refusal marker.
Correct that classification while keeping timeout/cancellation/truncation
unknown, and test the real runner. A2 is unrelated starter-file preflight and
remains recorded rather than silently modifying the open rollback PR.

Read-only seam probes inspected `NativeExchange`, `JsonParticipant`,
`RecoveryCursor.perform` and `RunStore`. The cursor persists `dispatching`
before calling and refuses replay of uncertain operations; failure metadata
for new profiles needs retention inside the consultation result boundary.
Claude `auth status` reports API-key authentication, not subscription-only
execution. No live inference has been performed by these probes.

## Alternatives and limits

### Independent review corrections, October 1

The frozen implementation's configured GPT-6 Astra review reproduced a stripped
`recovery` marker disabling the legacy conditional checkpoint check, followed
by a second actual command dispatch. Consultation must require its exact
recovery profile and validate the checkpoint unconditionally. Removing/changing
the marker, journal, status or result must refuse before another call.

The same review injected a source-to-symlink swap between precheck and open and
captured outside-scope bytes. Capture must traverse from a filesystem anchor
through stable directory/file handles, refusing links at open. Test leaf,
parent and root swaps, a retained parent renamed after open, and special files.
POSIX uses descriptor-relative no-follow opens; Windows reuses the existing
fixed-local-NTFS handle-relative reader with canonical-name, no-reparse,
single-link and no-alternate-stream eligibility. Windows execution remains a
CI evidence requirement; the macOS tests cannot qualify it.

The completed journal result must also project into `answers` before a pause is
reported. This improves inspection without dispatching or altering authority.

### Live Opus review corrections, October 1

The requested and reported `claude-opus-5-5` review found that supervised
in-flight cancellation was caught as a generic failure. Classify only the
process owner's explicit cancellation failures as cancelled; retain the stopped
process and unknown external effects, and refuse further dispatch. A set signal
alone must not relabel a provider failure. Exercise a real waiting subprocess.
Abandonment records the previous status so a failed run remains inspectable.
Evidence line bounds count LF/CRLF source lines; embedded form-feed, vertical-tab
or Unicode separators must not invent editor lines. Test those bytes explicitly.

The proposed pause-before-journal defect is not reproduced: the actual
`RecoveryCursor.perform` raises `ReviewPaused` only after saving a completed
result. Keep the existing pause/replay journey as the regression. Windows CI
correctly refused reparse points and retained CRLF bytes; fix the tests' LF
fixture and platform-specific refusal wording without normalizing source bytes.

Rejected separate host implementations: they duplicate scope and replay rules.
Rejected porting the 703-line visual adapter as the execution authority: the
workspace nonce validates interaction but is not a durable provider journal.
Thin Markdown skills invoke the shared CLI first; visual adapter parity remains
separate. No OS sandbox or provider-enforced dollar cap is claimed. Call count,
timeout and output limits bound software execution; paid dispatch still needs
the user's concrete budget and permission. No fallback or automatic retry.

## Journey to validate

| Command | Refusal boundary | Earlier output satisfies it |
| --- | --- | --- |
| `source-review prepare` / `roundtable prepare` | Invalid identity, scope or budget | Explicit host-owned JSON configuration and selected source paths |
| `... run --accept DIGEST` | Stale contract, no provider authority, uncertain turn | Prepare returns the exact contract digest; chair grants dispatch |
| `... status` | Changed checkpoint or copied owner | Original exclusive run directory and immutable contract |
| `... run --accept DIGEST` after pause | Completed/failed/cancelled or uncertain run | Only a paused/prepared run with matching contract resumes; completed turns replay |
| `... abandon --checkpoint DIGEST` | Stale checkpoint or active writer | Fresh status and original owner's stopped process; journal retained |

Tests must exercise these refusals and the complete command journey before
claiming software support. Installed-wheel qualification, independent different-
model review and observed live host journeys remain separate evidence gates.
