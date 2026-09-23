# Handoff: attune-harness first PyPI release

Written 2026-09-19, updated at the end of the evening session the same day.
State is safe to leave. **The TestPyPI rehearsal is complete. Nothing is published
to production PyPI.**

## Where things stand

- Release branch: `release/0.1.0rc1-packaging`
- Release commit: `afa415f03d43e2321545dd106072d10b1b41eac0`
- Version on that commit: `0.1.0rc1`
- `codex/testpypi-rc-20260918` was fast-forwarded to `afa415f` and pushed.
  Qualification passed on it (run 35462277579).
- **`0.1.0rc1` is live on TestPyPI**, published by run 35476747591 from
  `codex/testpypi-rc-20260918`. `build`, `publish_testpypi` and `verify_testpypi`
  succeeded; `publish` (production) was correctly skipped. The index returns 200
  for `https://test.pypi.org/pypi/attune-harness/0.1.0rc1/json`. The `rc1` slot on
  TestPyPI is spent.
- TestPyPI trusted publisher: added by Patrick on 2026-09-19 (`attune-harness`,
  `Smart-AI-Memory/attune-harness`, `publish-pypi.yml`, environment `testpypi`).
- PyPI (production) pending trusted publisher: reported registered for
  `publish-pypi.yml`, environment `pypi`. **Not visually re-verified this session.**
- GitHub environments: `testpypi` exists; `pypi` does not exist yet.
- `publish-pypi.yml` is the only publishing route. It is not on the
  `wip/local-snapshot-2026-09-19` branch; read it with
  `git show origin/codex/testpypi-rc-20260918:.github/workflows/publish-pypi.yml`.
- Evidence from earlier in the day: `docs/receipts/release-prep-2026-09-19/report.txt`
  and `docs/receipts/pypi-build-check-2026-09-19/`.

## What the rehearsal taught (read before the production run)

1. **"Registered" must mean "I can see the row."** Two attempts failed with
   `invalid-publisher` because test.pypi.org had no trusted publisher at all. The
   one registered earlier was on pypi.org, which is a separate site and account.
   Before the production run, open the pypi.org Publishing page and read the row.
2. **Never `gh run rerun --failed` on this workflow.** The publish job asserts
   `manifest['workflow_run_attempt'] == GITHUB_RUN_ATTEMPT` (workflow line 151).
   A failed-jobs re-run reuses the build from attempt 1, so the assertion can never
   pass. After any failure, fix the cause and dispatch a fresh run.
3. **Read the failed log before acting.** `gh run view <id> -R
   Smart-AI-Memory/attune-harness --log-failed`, filtered for Docker pull noise,
   named the cause each time. The job list alone did not.
4. **Pin the repo in `gh` commands** with `-R Smart-AI-Memory/attune-harness`.
   Patrick's shell is often in `attune-ai`, where the run IDs 404.
5. The run name shows as "Release workflow registration (inert on default branch)"
   because GitHub takes the display name from main's stub. The run itself uses the
   real workflow on the dispatching branch.

Failed runs for the record: 35462095551 (environment branch rule), 35462519274
(attempt 1 `invalid-publisher`; later attempts hit the run-attempt assertion).

## Next: production 0.1.0 (each step is Patrick's decision)

1. **Version and README decision.** The current README says "release candidate, not
   production-ready" and "not yet published to PyPI". Decide whether `0.1.0` final
   is right. A replacement README is drafted at
   `docs/handoffs/README-draft-0.1.0.md`; it states limits in one "qualified / not
   qualified" table and assumes `0.1.0`, alpha. Its header comment lists six checks,
   including that its links are pinned to a `v0.1.0` tag that does not exist yet and
   that its opening numbers need Patrick's confirmation.
2. **Create the `pypi` environment** with Patrick as required reviewer (Settings,
   Environments), before any dispatch. Without it GitHub auto-creates an unprotected
   one. Consider restricting it to the release branch, as `testpypi` is.
3. **One commit on the release line:** bump `0.1.0rc1` to `0.1.0`, swap in the new
   README, and add `docs/cli-guide.md`. That file is committed on the `wip` branch
   (`a3b3934`), not on the release line, and must be carried over (for example
   `git checkout wip/local-snapshot-2026-09-19 -- docs/cli-guide.md`), or the new
   README's link 404s.
4. **Re-qualify the new SHA:** Library qualification must pass, then a dry run with
   `target=pypi`, `publish=false`.
5. **Verify the pypi.org publisher row by eye** (lesson 1).
6. **Dispatch with `publish=true`, `target=pypi`, `version=0.1.0`, the new SHA**,
   then approve under Review deployments. A production version number can never be
   reused, even after deletion, so steps 4 and 5 are where the care goes.

## Guardrails

- The workflow rejects `.dev` and `rc` versions for production, and non-rc versions
  for TestPyPI. Do not work around it.
- Never dispatch from `main`; its copy of the workflow is an inert stub.
- Always dry-run (`publish=false`) on a new SHA before a real run.
- No partial re-runs (lesson 2).
- `0.1.0.dev14` on the snapshot branch is not a release version.

## Committed after the session (2026-09-19, late)

- `a3b3934` on `wip/local-snapshot-2026-09-19`, pushed to origin:
  `docs/opportunity-log.md` (two unnumbered entries: pinned actions target Node.js
  20; `ubuntu-latest` moves to Ubuntu 26 from 2026-10-19) and the new
  `docs/cli-guide.md`.
- attune-ai: stray usage-signals snapshot committed as `e15576fa7` on
  `chore/usage-signals-snapshot-2026-09-11`, pushed; PR not yet opened.
- `docs/handoffs/` was not gitignored when this was written; the claim below
  was true only on the wip snapshot branch. Since the pull request that closed
  O-43 (September 23, 2026) the rule is on `main`, tracked files stay tracked,
  and a new note is added by name with `git add -f`. This file, the session
  starter and the README draft were on disk only, until they were added by name.

## Known content gap in the README plan

The draft README drops the old README's long tail: the Dev10 to Dev13 notes, the
Astra and Fable review profiles, the Llama retirement, the local pilot, the JSON and
native adapter notes, verify/retrieve, review-form, recovery, extensions, MCP, A2A
and the memory integration section. `docs/cli-guide.md` does not hold these. Most
already have their own linked docs, but the summaries themselves would survive only
in Git history. Decide whether to move them into a `docs/development-notes.md`
before the swap.

## Unrelated work recorded the same day

- Native memory scoping note: `docs/specs/native-memory/scoping.md`.
- Opportunity log: test-named product modules (needs an O-number).
