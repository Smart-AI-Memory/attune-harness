<!--
DRAFTS for docs/opportunity-log.md. Four entries. None is appended or committed.

The log lives only on wip/local-snapshot-2026-09-19. The Redis entry was appended
there as local commit 4c057c1 (not pushed). To land any of these, append the
paragraph at the end of "Dated evidence and follow-through", after the Redis entry.
They follow that section's convention: unnumbered, dated, evidence first, candidate
follow-up, effort, and a closing line that the note authorizes nothing. Highest
assigned number today is O-36.

Suggested order of attention, which is not the order of urgency of each alone:
  4 (reconcile the lines) first. It is the only one where doing nothing loses a
    shipped fix at the next release.
  3 (gitignore) is five minutes and rides along with 4.
  1 (delete-sharing) and 2 (observe deadline) are genuine but can wait.

Every SHA, run ID and count below was read from git or the GitHub API on
2026-09-21. Statements marked as hypotheses were not tested.

Delete this comment block before landing.
-->

Unnumbered, 2026-09-21 (assign the next O-number at the next log review): open the
harness's own run-record readers with Windows delete-sharing. 0.1.0 shipped a bounded
fix (`8fc26a4`) for the defect that blocked the release: `RunStore.save()` replaced
`record.json` once with no retry, Windows refuses to replace a file another handle
has open, and the resulting `PersistenceError` stops all further dispatch in an MCP
session by design. The reproduction (scratch commit `8f59e9e`, run 35561326066)
failed on Windows with `[WinError 5] Access is denied` and passed on macOS and
Ubuntu. The shipped fix retries `os.replace` on `PermissionError` every 5 ms for up
to `REPLACE_RETRY_SECONDS = 2.0`, then fails closed as before. That treats the
symptom on the writer's side. The limit is stated in the 0.1.0 README and changelog:
a process that holds the record open for more than about two seconds still fails the
run. Part of the contention is the harness's own. `load_record` in
`review_store.py` reads through `features.read_text`, which uses `path.open('rb')`,
and Python's `open` on Windows does not request `FILE_SHARE_DELETE`, so every
harness reader (`status`, `resume`, recovery, the polling MCP test) is itself a
handle that blocks the replace for as long as it is open. Candidate follow-up: on
Windows only, open run records for reading with delete-sharing (through
`CreateFileW` with `FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE` and
`msvcrt.open_osfhandle`, stdlib only, no new dependency), leaving the POSIX path
untouched. Hypothesis, not tested: with the reader sharing delete access, the
writer's replace succeeds on the first attempt while the reader still holds its
handle, so harness readers stop contributing to the retry at all. Done when a
Windows-only test holds a harness-opened read handle indefinitely and `save()`
succeeds without entering the retry loop; the existing
`test_save_still_fails_closed_when_record_stays_open` still fails closed for a
handle opened without delete-sharing; and qualification is six of six green. This
does not help against third-party handles (an indexer, antivirus, an editor), which
is why the bounded retry stays. Whether to then shorten or keep the two-second
budget is a separate decision to make from evidence, not now. Effort:
small to medium; the change is a few lines but it is Windows-only file-handle code
in a fail-closed persistence path, and CI is the only place it can be verified.
Nothing is changed or authorized by this note.

Unnumbered, 2026-09-21 (assign the next O-number at the next log review): the 10 s
`observe` deadline in the MCP cancellation test.
`tests/test_mcp.py::test_sdk_cancellation_retains_started_call_receipt` polls for a
pending receipt through a local `observe` helper with a fixed deadline of 10 seconds
(`asyncio.get_running_loop().time() + 10`), inside an SDK client created with
`read_timeout_seconds=5`. When the Windows record-replace defect stopped dispatch,
the receipt never reached disk and the test spent its full 10 seconds before failing
(runs 35559398300 and 35560396368). The original failure message reported only the
saved record, which hid the cause; scratch commit `8f59e9e`, carried into `8fc26a4`,
made the timeout report what the tool call returned as well. The deadline was not
the defect. Junit timings ruled out a tight budget before the cause was known: the
sibling SDK test does spawn plus real calls in about 2.5 s on the same runners, and
after the fix this test took 2.1 to 3.0 s across four Windows jobs (runs 35562268487
and 35562701896). Two things remain worth a look. First, the deadline is a bare
literal with no stated relation to the code it waits on, and it now sits beside a
writer that may legitimately spend up to 2.0 s per save under contention, so several
contended saves in one test could approach 10 s on a slow runner and fail for a
reason that is not a defect. Second, a pass records nothing about how close it came.
Candidate follow-up: name the deadline as a constant with a comment stating what it
bounds and how it relates to `REPLACE_RETRY_SECONDS`; include elapsed time in the
timeout assertion message; and decide from a few weeks of junit timings whether 10 s
is right, rather than raising it pre-emptively, because a longer deadline would have
made this defect slower to notice, not easier to diagnose. Done when the constant and
message are in place and qualification is six of six green. Effort: small. Nothing
is changed or authorized by this note.

Unnumbered, 2026-09-21 (assign the next O-number at the next log review):
`docs/handoffs/` is ignored on one branch only. Both release handoff notes
(`first-pypi-release-2026-09-19.md` and `release-0.1.0-windows-fix-2026-09-21.md`)
state that `docs/handoffs/` is gitignored. That is true only on
`wip/local-snapshot-2026-09-19`, where `.gitignore` line 30 reads `docs/handoffs/`.
`main` and `release/0.1.0rc1-packaging` have no such rule: on both, the directory
shows as untracked (`?? docs/handoffs/`), as does `docs/reflections/` in the main
checkout. The notes were written while the `wip` branch was checked out, which is
how the claim came to be recorded as general. No file from the directory is tracked
on any of the three branches, and nothing leaked: the 0.1.0 release commits added
files by name, as the handoff instructed. The exposure is that the repository is
public and the directory holds session notes, run IDs, draft articles and
qualification output, so a single `git add -A` or `git add docs` on `main` or a
release branch would publish them. Candidate follow-up: add `docs/handoffs/` (and
decide about `docs/reflections/`) to `.gitignore` on `main`, so every branch cut
from it inherits the rule. Do not add it to the published release line by itself: a
commit there starts a qualification run and moves the branch head away from the
tagged, published SHA for no product benefit; let it arrive through whatever
reconciles the lines. Until then the working rule stands: add files by name. Done
when `git status` on a fresh checkout of `main` with a populated `docs/handoffs/`
shows a clean tree, and the two handoff notes no longer make the general claim
(the 2026-09-21 note's worktree copy is already corrected). Effort: small. Nothing
is changed or authorized by this note.

Unnumbered, 2026-09-21 (assign the next O-number at the next log review): the
published 0.1.0 source is on no line that future work starts from. Three lines
diverge from the same merge base, `7eabe58`, and none contains another. `main` is 3
commits ahead of the base (`da99bb3`, `3607e4f`, `82efb27`, all CI registration) and
reports version `0.1.0.dev13`. `release/0.1.0rc1-packaging` is 5 ahead (`ff05cfa`,
`361bdcb`, `afa415f`, `c4fc89d`, `8fc26a4`), reports `0.1.0`, and its head is the
commit published to PyPI by run 35564794974 and tagged `v0.1.0`.
`wip/local-snapshot-2026-09-19` is 24 ahead, reports `0.1.0.dev14`, and is the only
line carrying this log, `docs/specs/native-memory/scoping.md` and the
`docs/handoffs/` ignore rule. The consequence that matters: the Windows
record-replace fix exists only on the release line. `review_store.py` on `main` and
on `wip` has no `_replace` helper and no `REPLACE_RETRY_SECONDS`. A 0.2.0 cut from
either would ship without a fix that 0.1.0 has and would reintroduce the Windows
failure that blocked this release. Neither has the `## 0.1.0` changelog entry or the
PyPI README. `main` additionally lacks `LICENSE` and `docs/cli-guide.md`; `wip` has
its own copies of both, which were not compared with the release line's. The tag keeps the published source reachable, so nothing is lost today;
the risk is at the next release. A trial merge of the release line into `main`
(`git merge-tree`, nothing written) reports two conflicts. One is
`.github/workflows/publish-pypi.yml`, add/add: `main` deliberately carries an inert
registration stub, which is why the guardrail says never to dispatch from `main`,
while the release line carries the real workflow. That conflict needs a decision,
not a mechanical resolution: keep the stub on `main` and the real workflow only on
release branches, or promote the real one and rely on the `pypi` environment's
branch policy and required reviewer. The other is `tests/test_mcp.py`, a content
conflict. `wip` against the release line was not trial-merged. Candidate follow-up:
decide which line is the trunk for 0.2.0, then bring the five release commits onto
it (merge, so the published SHA stays an ancestor, in preference to cherry-picks
that would make the fix look new), resolve the workflow question explicitly, set the
next development version, and qualify the result. Separately decide what becomes of
`wip`'s 24 commits. The release branch itself should stay where it is: the `pypi`
environment's branch policy names it, the published README's links resolve through
`v0.1.0`, and that tag must not move again. Done when a single line contains
`8fc26a4` as an ancestor, carries the Windows fix, this log and the scoping note,
reports a development version above `0.1.0`, and passes qualification six of six;
and the workflow decision is written down where the guardrails live. Effort: medium;
the merges are small but the workflow decision and the fate of `wip` are judgment
calls, and everything lands on a public default branch. Nothing is merged, moved or
authorized by this note.
