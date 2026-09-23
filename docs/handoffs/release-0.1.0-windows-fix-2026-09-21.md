# Handoff: attune-harness 0.1.0, Windows record-replace fix, then release

Written 2026-09-21 (early hours), updated 2026-09-21 05:30Z after steps 1 to 5 were
completed. Supersedes the "Next: production 0.1.0" section of
`first-pypi-release-2026-09-19.md`. **Nothing is published to production PyPI**
(`https://pypi.org/pypi/attune-harness/0.1.0/json` returned 404 at 05:28Z).
This note authorizes nothing. Every command below needs Patrick's approval, and the
publish approval is Patrick's alone.

## PUBLISHED: attune-harness 0.1.0 is live on PyPI (2026-09-21 05:36:50Z)

This section supersedes every "nothing is published" and "step 6 remains" statement
below, which are kept as the record of the state before the publish.

- Run 35564794974 on `8fc26a42524ddabc3f11d86b64863616297f4fd1`, dispatched and
  approved by Patrick: `build` success, `publish` success, the two TestPyPI jobs
  skipped. One attempt, no re-runs.
- pypi.org JSON API, simple index and project page all return 200. Not yanked,
  `requires_python >=3.10`, extras `tokens, verify, rag, voyage, review, mcp,
  memory-native`.
- Files on PyPI match the run's `distributions` artifact byte for byte:
  - `attune_harness-0.1.0-py3-none-any.whl`, 232774 bytes, sha256
    `384373db9ca3c34b1f508cb9d584bbbe5533651546b3b348c57eeaabf3a9139d`
  - `attune_harness-0.1.0.tar.gz`, 198231 bytes, sha256
    `500d2b239aec261758b53e682cc9bf044371afae937b24c5162ed8ead1c4ef81`
- Clean install in a fresh venv from pypi.org (`pip install attune-harness==0.1.0`,
  macOS, Python 3.10): version `0.1.0`, zero runtime dependencies installed,
  `review_store._replace` present with `REPLACE_RETRY_SECONDS = 2.0`, and
  `attune-harness --help` runs.
- The version number `0.1.0` is now spent forever. The tag `v0.1.0` must not move
  again: it is what the published README's links resolve to.

Still open: delete scratch branch `diag/windows-record-replace`; opportunity-log
entries listed under "After the release"; optionally a GitHub Release on `v0.1.0`;
merge or otherwise reconcile `release/0.1.0rc1-packaging` with `main`.

## Where things stand before the publish (as of 2026-09-21 05:30Z)

**Steps 1 to 5 are done. Only step 6, Patrick's `publish=true` dispatch, remains.**

- Release line: `release/0.1.0rc1-packaging`, head
  `8fc26a42524ddabc3f11d86b64863616297f4fd1` (GPG-signed, pushed). One commit on top
  of `c4fc89d`: the Windows record-replace fix, its tests, the changelog bullet and
  the README limit sentence.
- Tag `v0.1.0` points at `8fc26a4` on origin (tag object `c89990c`, moved by Patrick
  at about 05:04Z; the previous tag object was `4022bbf` on `c4fc89d`). No GitHub
  Release is attached to the tag.
- Qualification on `8fc26a4`, six of six green both times: push run 35562701896 and
  tag-triggered run 35563215691. The tag run is the latest for the SHA, which is the
  one the preflight reads. Nothing in progress.
- Dry run (`target=pypi`, `publish=false`) on `8fc26a4`: run 35563615952, `build`
  success, `publish`, `publish_testpypi` and `verify_testpypi` skipped. Built
  `attune_harness-0.1.0-py3-none-any.whl` and `attune_harness-0.1.0.tar.gz`.
- History on the old SHA `c4fc89d`, for the record: qualification passed once
  (35558946155), dry run passed (35559262075), then two Windows-only qualification
  failures, 35559398300 (3.12) and 35560396368 (3.10), both on
  `tests/test_mcp.py::test_sdk_cancellation_retains_started_call_receipt`. Dispatch
  35559725080 at 04:05Z failed in `build` with "Latest qualification for the release
  SHA did not pass": the preflight gate working as designed. `c4fc89d` is superseded;
  do not publish from it.
- GitHub environment `pypi`: protected. Required reviewer `silversurfer562`, branch
  policy `release/0.1.0rc1-packaging` (custom policy, branch type). Re-read through
  the API at 05:30Z. Note the policy is branch-typed, and the dispatch ref is the
  release branch, so this matches.
- pypi.org pending trusted publisher: created by Patrick (`attune-harness`,
  `Smart-AI-Memory/attune-harness`, `publish-pypi.yml`, environment `pypi`).
- Extras pins verified on PyPI: `httpx2==2.13.0`, `anthropic==1.6.0`.

## The defect (confirmed)

`RunStore.save()` in `src/attune_harness/review_store.py` did one `os.replace(temp,
record.json)` with no retry. Windows refuses to replace a file while any other handle
has it open. A reader (`status`, the polling test, antivirus, an indexer) colliding
with a save raised `PersistenceError`, which by design stops all further dispatch in
an MCP session. The pending receipt then never reached disk, and the MCP test waited
its full 10 seconds for it.

Evidence: scratch branch `diag/windows-record-replace`, commit `8f59e9e` (test only),
run 35561326066. The store-level reproduction failed on Windows with
`[WinError 5] Access is denied: '...tmp...' -> '...record.json'` and passed on macOS
and Ubuntu. Junit timings had already ruled out a tight budget: the sibling SDK test
does spawn plus real calls in about 2.5 s on the same runners.

## The fix (now on the release line as `8fc26a4`)

Commit `d74d1d1` on `diag/windows-record-replace`, carried to the release line with
the three files byte-identical:

- `review_store.py`: new `_replace()` helper. POSIX path unchanged. On Windows, retry
  `os.replace` on `PermissionError` every 5 ms for up to `REPLACE_RETRY_SECONDS = 2.0`,
  then re-raise, so `save()` still raises `PersistenceError` and dispatch still stops.
- `tests/test_recovery.py`: `test_save_survives_concurrent_readers` (one realistic
  polling reader, 200 saves) and Windows-only
  `test_save_still_fails_closed_when_record_stays_open` (bounded retry still fails
  closed, old record intact, no temp file left).
- `tests/test_mcp.py` (from `8f59e9e`): on timeout the cancellation test now reports
  what the tool call returned, not only the record.

**Status of the fix run: green.** Run 35562268487 on `d74d1d1`, six of six jobs.
Neither expected failure (a test patching `os.replace`, or a `review_store.py` hash
comparison) occurred. `tests.xml` from both Windows jobs, on the fix run and again on
release run 35562701896, shows 471 tests, 0 failures, 7 skipped, and all three key
tests run rather than skipped: `test_save_survives_concurrent_readers`,
`test_save_still_fails_closed_when_record_stays_open` and
`test_sdk_cancellation_retains_started_call_receipt`. The cancellation test now
finishes in 2 to 3 s instead of reaching its 10 s deadline.

Known remaining limit, to state honestly: a process holding the run record open for
more than about two seconds on Windows still fails the run closed. The fuller fix
(harness readers opening the record with Windows delete-sharing) belongs in the
opportunity log, not in this release.

## Steps, in order (1 to 5 done, 6 remains)

1. **Done.** Fix run green on `d74d1d1`: run 35562268487.
2. **Done.** Release-line commit `8fc26a42524ddabc3f11d86b64863616297f4fd1` on top of
   `c4fc89d`, files added by name, GPG-signed, pushed 04:56Z. `CHANGELOG.md` gained a
   "Fixed" bullet, and "Same runtime as 0.1.0rc1" became "The 0.1.0rc1 runtime plus
   one fix" because the old sentence was no longer true. The `## 0.1.0` heading the
   preflight matches is unchanged. `README.md`, Platforms row, "Not qualified"
   column, now states the two-second limit.
3. **Done.** Qualification on push: run 35562701896, six green.
4. **Done.** Tag `v0.1.0` moved to `8fc26a4` by Patrick (about 05:04Z). Tag-triggered
   qualification: run 35563215691, six green.
5. **Done.** Dry run 35563615952: `build` success, three publish jobs skipped.
6. **Patrick's decision, not yet taken.** First open the pypi.org Publishing page and
   read the pending-publisher row by eye (`attune-harness`,
   `Smart-AI-Memory/attune-harness`, `publish-pypi.yml`, environment `pypi`). Then:
   ```sh
   gh workflow run publish-pypi.yml -R Smart-AI-Memory/attune-harness \
     --ref release/0.1.0rc1-packaging \
     -f release_sha=8fc26a42524ddabc3f11d86b64863616297f4fd1 -f version=0.1.0 -f target=pypi -f publish=true
   ```
   Approve under Review deployments. After it finishes:
   `curl -s -o /dev/null -w "%{http_code}\n" https://pypi.org/pypi/attune-harness/0.1.0/json`
   should print 200. Before dispatching, confirm no new qualification run has started
   on `8fc26a4` (any new push or tag move starts one, and the preflight reads the
   latest).

Observed durations: qualification 4.5 to 5 minutes (Windows jobs set the pace), dry
run about 30 seconds, the TestPyPI publish about 2 minutes plus approval wait.

## Guardrails

- Never `gh run rerun --failed` on `publish-pypi.yml`. After any failure, read
  `--log-failed`, fix the cause, dispatch fresh.
- Never dispatch from `main`; its workflow copy is an inert stub.
  **Changes once the reconcile PR merges (Patrick's decision, 2026-09-21):** `main`
  will carry the real workflow, byte-identical to `v0.1.0`, because the 0.1.0 line
  ships a test that asserts on its content and the stub would leave `main` red.
  Publishing from `main` stays blocked by GitHub itself: the `pypi` and `testpypi`
  environments require `silversurfer562` as reviewer and restrict deployments to a
  named non-`main` branch. A future release branch must be added to the `pypi`
  environment's branch policy before it can publish. Local branch
  `claude/reconcile-release-0.1.0-into-main`: merge `f492fb8`, `46472ac`
  (`0.2.0.dev0`, ignore rules), `e12ba94` (workflow).
- Always dry-run (`publish=false`) on a new SHA before a real run.
- Do not dispatch `publish=true` while any qualification run for the SHA is in
  progress or failed.
- A production version number can never be reused. The tag can be moved; the PyPI
  version cannot.
- Pin `-R Smart-AI-Memory/attune-harness` on `gh` commands. Patrick's shell often
  starts in `attune-ai`.
- pytest output for qualification is in the uploaded artifact's `tests.txt` and
  `tests.xml`, not in the job log.
- Local note: Patrick's pyenv Python has `mcp 1.29.1`; the harness pins `mcp==2.2.0`,
  so MCP SDK tests fail locally at `initialize`. CI is the reference.

## After the release

- Opportunity log: Windows delete-sharing for the harness's own record readers; the
  10 s `observe` deadline in the MCP cancellation test; Node.js 20 action pins;
  `ubuntu-latest` moving to Ubuntu 26 on 2026-10-19.
- The extra named `memory-native` is a pinned Anthropic API transport for memory
  proposals, not the Redis-backed native memory direction. The name is permanent once
  0.1.0 publishes.
- Delete the scratch branch `diag/windows-record-replace` once the fix is on the
  release line.
- `docs/handoffs/` was **not** gitignored when this was written, contrary to
  what this note and the 2026-09-19 note said; it stayed out of commits only
  because files were added by name. The rule is on `main` since the pull
  request that closed O-43 (September 23, 2026): the directory and
  `docs/reflections/` are ignored, files already tracked stay tracked, and a new
  note is added by name with `git add -f`.
- The Claude session of 2026-09-21 ran in the worktree
  `.claude/worktrees/windows-pypi-release-handoff-dba493`, now switched to
  `release/0.1.0rc1-packaging`. The session could not edit files in the main
  checkout, so this updated note was written in the worktree's `docs/handoffs/`.
  Copy it over the main-checkout original if it has not been already.
- The agent's own forced tag move was refused by the Claude Code permission
  classifier as destructive git. Force tag moves will need Patrick's hands, or a
  Bash permission rule, in future sessions.
