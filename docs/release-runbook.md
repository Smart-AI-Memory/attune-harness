# Release runbook

How a release of `attune-harness` reaches PyPI, and the state it depends on that
is not in this repository. Written after 0.2.0, from what that release needed.

Agents prepare a release. Patrick approves each outward step and makes every
settings change himself. See [AGENTS.md](../AGENTS.md).

## State that lives outside the repository

Nothing in a checkout shows these. Check them before relying on them, and
update this table when they change.

| Where | Setting | Value on 2026-09-21 |
| --- | --- | --- |
| GitHub environment `pypi` | Branches allowed to deploy | `main` |
| GitHub environment `pypi` | Required reviewer | `silversurfer562` |
| GitHub environment `testpypi` | Branches allowed to deploy | `codex/testpypi-rc-20260918`, which no longer exists |
| GitHub environment `testpypi` | Required reviewer | `silversurfer562` |
| Branch protection on `main` | Required checks | `Qualification` only, pinned to GitHub Actions. It is one verdict over the six Library qualification jobs: Ubuntu, macOS and Windows on Python 3.10 and 3.12 |
| Branch protection on `main` | Other rules | Branch must be up to date, signed commits, enforced for admins, pull request required with no approving review needed |
| PyPI project `attune-harness` | Trusted publisher | Must name this repository, `publish-pypi.yml` and the `pypi` environment. Uploads use OIDC; there is no API token |

Four things follow from that table.

The `testpypi` environment cannot deploy until its allowed branch is changed. A
TestPyPI rehearsal will build and then be rejected at the publish job. 0.2.0 hit
the same problem on `pypi`: the only allowed branch had been deleted as merged,
and nothing in the repository said the environment depended on it. Before
deleting a release branch, check both environments.

Do not change the required check back to the six platform names. A pull request
that only touches documentation skips the platform jobs, so those names never
report for it, and it could never merge. `Qualification` always reports, and it
fails unless the platform jobs passed or were skipped for a pull request the
classifier found documentation-only. Pushes to `main` never skip, so every
commit there has a full run, and the release gate reads only those. The reasons
are in the comments in `.github/workflows/qualification.yml`.

Required approvals is 0 on purpose. Every agent acts through Patrick's one
GitHub account, so requiring an approval today would block every pull request.
[The collaboration plan](agent-collaboration-plan.md) records the option that
changes this, and the order it has to be done in.

"Isolated Windows effects backend qualification" is not a required check. It
runs on pushes to `main` and on pull requests that touch the backend's inputs,
and a failure there does not block a merge.

Read the environments without changing them:

```bash
gh api repos/Smart-AI-Memory/attune-harness/environments/pypi/deployment-branch-policies --jq '[.branch_policies[].name]'
```

## Steps

1. **Prepare.** One pull request sets the final `version` in `pyproject.toml`,
   adds a `## X.Y.Z` heading to `CHANGELOG.md`, and pins README links to the
   `vX.Y.Z` tag. Build locally and run `twine check --strict`, then install the
   wheel and run `scripts/check_installed.py --mode core`.
2. **Merge.** The squash commit on `main` is the release SHA. Use all 40
   characters everywhere below.
3. **Wait for qualification on that SHA.** The push to `main` starts it. The
   publish workflow refuses a SHA without a passing Library qualification run.
4. **Rehearse the gate.** Dispatch `publish-pypi.yml` from `main` with
   `publish=false`. It runs the whole release gate and never touches the
   environment, so it cannot upload anything.
5. **Publish.** Dispatch again with `publish=true`:

   ```bash
   gh workflow run publish-pypi.yml --ref main -f release_sha=<40-char SHA> -f version=X.Y.Z -f target=pypi -f publish=true
   ```

   `main` must still point at the release SHA, because the workflow requires the
   dispatched commit to equal `release_sha`. The build job runs, then the run
   pauses on the `pypi` environment.
6. **Approve.** Patrick opens the run page, chooses Review deployments, and
   approves. This is the irreversible step: a version number on PyPI can never
   be reused, even after deleting the release.
7. **Verify.** Compare PyPI's SHA-256 for both files with the `SHA256SUMS` in
   that run's `release-evidence` artifact, then install from the index and run
   `scripts/check_installed.py`.
8. **Tag and release.** Create a signed annotated tag `vX.Y.Z` at the release
   SHA, push it, and create the GitHub Release from it with `--verify-tag`,
   attaching the two files from the publish run. Do this straight after step 7:
   the README on PyPI links to the tag, and those links return 404 until it
   exists.
9. **Reopen development.** A pull request moves `main` to the next `.dev0`
   version, so a build from `main` cannot be mistaken for the release.

## Things that look wrong and are not

- **The publish run's hashes differ from the rehearsal's.** Builds are not
  reproducible: `SOURCE_DATE_EPOCH` is not set, so every archive timestamp
  differs. In 0.2.0 the file lists and every file's content were identical. The
  hashes that matter are the ones from the run that published.
- **`pip` cannot find the new version right after a successful publish.** PyPI's
  index is cached. For 0.2.0 the versioned JSON endpoint had the files at once
  and the simple index listed them about 30 seconds later. Retry before
  concluding the publish failed.
- **A pull request that was green says it is behind.** Another merge landed
  first. Update the branch and wait for the checks again.

## TestPyPI rehearsal

`target=testpypi` takes a release-candidate version such as `X.Y.Zrc1`, and
`pyproject.toml` has to carry that version, so it needs its own commit and
branch. Name the branch `release/...`: pushes qualify only on `main` and
`release/**`, and the rehearsal gate needs a push or dispatch run on the commit. 0.2.0 skipped it: packaging had not changed since 0.1.0, and the build
job already installs the wheel and runs the installed check before any upload.
Use it when packaging metadata, the build backend or the workflow itself changes.
