# Task 3 review disposition

Tasks 1–3 are accepted. On 2026-09-17, the final timestamp finding was
independently closed and its executable reproduction rerun centrally. The
canonical workspace accepted Task 3 under the existing auto-run policy at
revision 17; the returned completed-task state is persisted in the XML plan.
Tasks 4 and 5 have not started.

| Round | Reviewer | Finding and disposition |
|---|---|---|
| 1 | gpt-5.6-sol/high | Metadata keys containing secret material were not guarded; CRLF/BOM frontmatter could bypass security labels. Both accepted and repaired. |
| 2 | gpt-5.6-sol/high | Earlier findings independently closed. Source identity, scope and snapshot protections checked. |
| 3 | gpt-5.6-sol/high | The added summary/verdict preservation path reread source mtime by pathname after descriptor capture. A directory swap and restoration could make a 100-day-old memory appear 0 days old. Accepted and repaired after this review; final repair has central verification only. |

## Repair and initial evidence

The final repair returns mtime from the same held descriptor that supplies source
bytes and version identity. Snapshot creation never rereads source mtime by name.
The deterministic regression swaps directories only during the vulnerable stat,
then restores the original before version validation. Reintroducing that stat in
a disposable source copy reproduces `0 == 100`; the repaired implementation
preserves the correct 100-day age. No user's memory was accessed or modified.

Central evidence: 162 passing checks (41 adapter cases and 121 existing memory
checks), six of six protection-removal probes detected, changed executable-line
coverage above 85% in each changed production module, pinned Ruff/Black checks.
Machine-readable results and source hashes:
`docs/receipts/shared-memory-adoption-task3/verification.json`.

## Initial pause at the review cap

At the time of the initial receipt, Patrick's standing review-cap rule said that at three rounds, remaining findings
go to the chair with options, never another automatic review round. His current
auto-run approval also requires a pause on serious findings. We retained
the high-severity gate for disposition and did not claim independent closure.
No extra review was launched until Patrick directed closing the remaining gap.

The initial option to accept the disclosed review limit was superseded by
Patrick's choice to close the verification gap first.

Legacy stores still lack qualified versioned serialization. New worker mutations
remain unavailable; existing memory commands and stored content remain intact.

## Reopened verification — 2026-09-17

After the cap and missing independent recheck were disclosed, Patrick selected
"A — Close Task 3’s verification gap first (Recommended)." This authorizes one
focused closure check of the timestamp repair beyond the cap; it does not change
the standing cap or authorize repeated broad reviews. The canonical `fix_retry`
action was collected at revision 16; no task acceptance was inferred from that choice.

The reviewer must independently reproduce the age-spoofing case, compare the
repaired and deliberately regressed implementations, bind results to current
source hashes, and state whether this finding is closed. The lead reruns that
executable evidence centrally. Existing service/regression and protection-removal
receipts remain applicable only while their source hashes still match.

This separates the repaired defect, central test evidence, independent closure,
and acceptance policy. The previous "score 100" was a test pass percentage, not
an overall quality grade. No generic score is used as proof that review is closed.

## Closure and acceptance

The independent script uses a different fixture and attacks snapshot timestamp
assignment while the root directory points to another tree, restoring it before
version validation. Repaired behavior preserves age 73 days and the existing
check-before-acting status. Restoring the vulnerable pathname-stat behavior in
the same probe produces age 0 and settled status. Both runs retain the original
source bytes and mtimes, resolve the complete source, and retrieve using an
existing summary-only search term. Network attempts: zero.

The lead inspected and reran the exact script, then reran both targeted tests:
2 passed. The existing 162-check and 6/6 protection-removal evidence matches
unchanged production source hashes. All three reported findings are independently
closed. Scope is synthetic temporary data on macOS, using the actual local RAG
and memory services; this does not establish installed/native/live qualification.

Receipts: `timestamp-closure-central.json`, `timestamp-closure-reproducer.py`,
`closure-suite.txt`, and `acceptance.json` under
`docs/receipts/shared-memory-adoption-task3/`. The previous gate, retry decision,
and pre-closure verification receipt remain for history.

Patrick subsequently clarified that he is willing to lift the three-pass rule
when there is an opportunity to progress and wants such opportunities pointed
out proactively. Three rounds are a checkpoint; bounded, useful exceptions are
brought forward rather than silently discarded or treated as unlimited review.
