# Release runbook

How a release of `attune-harness` reaches PyPI, and the state it depends on that
is not in this repository. Written after 0.2.0, from what that release needed.

Agents prepare a release. Patrick approves each outward step and makes every
settings change himself. See [AGENTS.md](../AGENTS.md).

## State that lives outside the repository

Nothing in a checkout shows these. Check them before relying on them, and
update this table when they change.

| Where | Setting | Recorded value (September 22 unless noted) |
| --- | --- | --- |
| GitHub environment `pypi` | Branches allowed to deploy | `main` |
| GitHub environment `pypi` | Required reviewer | `silversurfer562` |
| GitHub environment `testpypi` | Branches allowed to deploy | `main` — changed by Patrick and verified through GitHub API September 27, 2026 |
| GitHub environment `testpypi` | Required reviewer | `silversurfer562` |
| Branch protection on `main` | Required checks | `Qualification` only, pinned to GitHub Actions. It is one verdict over the six platform jobs (Ubuntu, macOS and Windows on Python 3.10 and 3.12) and the full test suite on Ubuntu |
| Branch protection on `main` | Other rules | Branch must be up to date, signed commits, enforced for admins, pull request required with no approving review needed |
| PyPI project `attune-harness` | Trusted publisher | Must name this repository, `publish-pypi.yml` and the `pypi` environment. Uploads use OIDC; there is no API token |

Four things follow from that table.

The `testpypi` environment now permits `main`, and its required reviewer remains
`silversurfer562` (both verified September 27). The previous branch restriction
was a deployment blocker; changing it did not publish a candidate. 0.2.0 hit the
same problem on `pypi`: the only allowed branch had been deleted as merged.
Before deleting a branch, check whether an environment still depends on it.

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
   adds a `## X.Y.Z` heading to `CHANGELOG.md`, pins README links to the
   `vX.Y.Z` tag, and sets the same version in both `plugin/attune-harness`
   manifests; `tests/test_claude_plugin.py` fails until they match. It does not
   touch `.claude-plugin/marketplace.json`: that catalog serves Claude Code
   users from `main`, and it points at a release tag that does not exist yet
   (step 9). Build locally and run `twine check --strict`, then install the
   wheel and run `scripts/check_installed.py --mode core`.
   **Documentation readiness is part of preparation for every new version
   publication.** Update affected official topics and their help, tutorial and
   deck derivatives against the candidate's code and reproducible tests. Record
   the tested version, examples, expected results, limits and checked links;
   distinguish changed content from unchanged content explicitly reviewed for
   this version. Retain or explicitly supersede relevant older-version guidance.
   Use the small [documentation readiness record](#documentation-readiness),
   coordinate with each content owner, and include it in the release PR evidence
   before requesting publication. Link/build checks support this review; they
   do not establish that a walkthrough is semantically correct. A website/help
   publication remains a separately authorized outward step.
2. **Merge.** The squash commit on `main` is the release SHA. Use all 40
   characters everywhere below.
3. **Wait for qualification on that SHA.** The push to `main` starts it. The
   publish workflow refuses a SHA without a passing Library qualification run.
   A release branch under a pull request has one full run, the push run: its
   pull-request run stops at the classifier and the link check (O-64), so
   there is one run to read per push, and it is the push run.
4. **Rehearse the gate.** Dispatch `publish-pypi.yml` from `main` with
   `publish=false`. It runs the whole release gate and never touches the
   environment, so it cannot upload anything. A change to that workflow's
   own action pins or steps is exercised nowhere else, so a rehearsal is
   owed after any such change, before the next `publish=true`.
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
9. **Point the Claude plugin at the tag.** A pull request sets the plugin
   entry in `.claude-plugin/marketplace.json` to the new tag: `ref` to
   `vX.Y.Z`, `sha` to the release SHA, and `version` and `metadata.version` to
   `X.Y.Z`. Claude Code reads that catalog from `main` and installs the plugin
   from the pinned commit, so users get the released skills and never an
   unreleased `main`. `tests/test_claude_plugin.py` checks the pin against the
   tag when tags are present. Users receive it on their next marketplace
   update, because the version changed.
10. **Reopen development.** A pull request moves `main` to the next `.dev0`
   version, so a build from `main` cannot be mistaken for the release.

## Documentation readiness

Official documentation must be updated with each new version publication.
Complete this small record during the release runbook's preparation step, before
requesting publication. Use the release PR description or its linked review
artifact; no new workflow or release system is required.

### Ground the review

Versioned code and reproducible tests establish the behavior an instruction can
claim. Approved project policies and the style guide govern requirements and
presentation. Project-specific approved exceptions take precedence over general
[Google developer documentation guidance](https://developers.google.com/style).
If code, policy or an example conflicts, record the discrepancy and resolve it
with the responsible owner before calling the content ready. Current code does
not automatically approve a policy change; do not edit policy to make it agree.

### Record affected topics once

Start with the candidate's changed behavior, dependency pins, compatibility and
deprecations. Identify its canonical topics, then their actual published or
prepared derivatives. Do not invent derivatives or generate every format.

| Canonical topic/source | Candidate version and code/test evidence | Disposition | Derivatives and owners | Walkthrough result and limits | Older guidance |
| --- | --- | --- | --- | --- | --- |
| Path or stable topic ID | Exact version/commit; reproducible check or retained receipt | Changed, or unchanged but reviewed for this version | Help route, tutorial/deck ID or editorial item; owner; changed/reviewed/pending/not applicable | Observed result; platform/input boundary; semantic review performed or still pending | Retained versioned link, or replacement and explicit supersession |

For the existing four walkthroughs, the tutorial lane owns
`docs/tutorials-1.3.0.md` and its action tables. A prepared local copy is not a
public release source. The topic set covers Navigation (deck title **Start and
continue work**), Specification Workflow, Four Workflows and Session Continuity.
Coordinate with that owner before refreshing help or deck projections. Preserve
the procedure, example, expected result, limits and tested-version record as one
unit. Help, self-paced tutorials and class materials can adapt their framing;
articles, posts and future books can add editorial context around the same unit.

### Close the preparation record

1. Update affected canonical instructions, exact control names, literal inputs,
   examples, dependency/integration guidance and limitations for the candidate.
   Mark unchanged topics as reviewed only after checking their behavior.
2. Reproduce changed task walkthroughs on the candidate, or cite retained
   evidence only when its inputs and behavior remain applicable. State what was
   not tested; do not promote a software check into a model-quality claim.
3. Coordinate the actual derivative updates with their owners. For generated
   projections, record upstream source path/commit/hash and run the drift check.
   Do not hand-edit the generated derivative to conceal a canonical discrepancy.
4. Check local links, version links and the relevant documentation/site build.
   Record these results separately from the explicit walkthrough review.
5. Retain useful old-version guidance with version labels, or name its
   replacement and supersession. A new main/prototype page is not released help.
6. Include the topic record, review outcome and remaining publication decisions
   in the release PR evidence. Report any pending official-doc update before
   requesting release approval. Package and website publishing retain their
   existing authorization boundaries.

The first Help Center is prepared separately in the existing Attune-AI website
repository. Its topic manifest and pinned walkthrough provenance support these
records; an unpublished local route or reviewed branch is not a live help URL.

## Things that look wrong and are not

- **The publish run's sdist hash differs from the rehearsal's.** The workflow
  sets `SOURCE_DATE_EPOCH` to the commit's time, which makes the wheel
  reproducible: two local builds of one commit gave the same wheel hash. The
  setuptools sdist ignores it. Every tar member carries a checkout or build
  time, and the gzip header carries the build time, so the `.tar.gz` differs on
  every build while its file list and contents stay the same. A wheel hash can
  still move if setuptools releases between the two runs, because the build
  takes `setuptools>=77` unpinned. The hashes that matter are the ones from the
  run that published. Making the sdist reproducible is recorded as a goal in
  [the collaboration plan](agent-collaboration-plan.md).
- **`pip` cannot find the new version right after a successful publish.** PyPI's
  index is cached. For 0.2.0 the versioned JSON endpoint had the files at once
  and the simple index listed them about 30 seconds later. Retry before
  concluding the publish failed.
- **A pull request that was green says it is behind.** Another merge landed
  first. Update the branch and wait for the checks again.
- **A platform job fails in "Build and install library" with `No matching
  distribution found for setuptools>=77 (from versions: none)`.** The runner
  got an empty index page, not a real resolution failure; 0.4.0's reopen saw
  it once on Windows 3.10. Wait for the run to finish, then
  `gh run rerun <run-id> --failed`; a rerun request while the run is still
  going is refused.
- **`SHA256SUMS` in `release-evidence` names the files as `dist/<name>`.**
  Check it from the directory that holds `dist/`, and compare basenames
  against PyPI's `urls[].filename`.

## Automating the steps

0.4.0 ran steps 2 to 9 from scripts, with Patrick's authorization for the
environment approval ("approve the deployment for me"), which the run's
approval comment records. What those scripts learned, for the next ones:

- Find a run for a commit with `gh run list --commit <sha>`; `gh run list
  --jq` takes no `--arg`.
- `gh pr checks` exits 8 while any check is pending; under `set -e` a
  `var=$(gh pr checks …)` assignment kills the script.
- Approving the environment is `POST
  /repos/{owner}/{repo}/actions/runs/{run}/pending_deployments` with
  `{"environment_ids": [<id>], "state": "approved", "comment": …}`; the
  response is a list of environment objects. Read the environment id from
  `GET /repos/{owner}/{repo}/environments/pypi`. Do not pipe that response
  through `--jq` expecting an object: the parse error stopped the 0.4.0 and
  0.5.0 finish scripts after the approval had already succeeded, and steps 7
  to 9 ran by hand both times. `scripts/release_approve.sh <run> "<comment>"`
  does the call, checks the exit status and prints the environment names.
- Verify the tag with `git tag -v` into a file, then grep the file; piping
  into `grep -q` under `pipefail` ends the pipeline with the signal `git`
  gets when `grep` closes early.
- Wrap the tag message with `fold -s` and strip the leading space `fold`
  leaves on continuation lines.

## Production PyPI release candidates

Production PyPI accepts final versions and release candidates such as
`1.0.0rc1`. The production gate requires a clean checkout at the exact approved
commit, matching package metadata and changelog, successful qualification for
that commit, and an unused PyPI version. Development, alpha, beta, post-release
and local versions are refused. TestPyPI retains its separate RC-only route.

For `1.0.0rc1`, follow the release steps above with `target=pypi`. First run
the build-only rehearsal (`publish=false`), then the authorized publication
(`publish=true`) from the same reviewed main commit. Preserve the environment
approval and verify both published files against the publishing run's
`release-evidence/SHA256SUMS`; rehearsal hashes do not establish published bytes.
Create the GitHub release as a prerelease and attach those verified files.

Install the candidate explicitly in a fresh environment:

```sh
pipx install 'attune-harness[all]==1.0.0rc1'
```

An unpinned installation normally selects the stable release. Record the release
SHA, publication run and attempt, both artifact hashes and the verified-install
time before starting the candidate observation period. Production publication
does not waive the 14-day observation period, non-programmer walkthrough or
separate stable-release decision. The TestPyPI procedure below remains available
for rehearsals; it is not the destination selected for this candidate.

## TestPyPI rehearsal

The 1.0 compatibility content freezes when `rc1` is published. During the
candidate period, a change to a frozen golden row, CLI surface, public API
signature, protocol fixture, saved-format fixture or its reader starts a new
candidate at the next `rc` number, with a changelog line explaining the change
(D27.7). Preparing an unpublished candidate-version wheel and its fixture does
not start the observation period or authorize publication.

`target=testpypi` takes a release-candidate version such as `X.Y.Zrc1`, and
`pyproject.toml` has to carry that version. Prepare the candidate version and
changelog in a reviewed pull request, merge through `main`, and wait for that
exact main commit's qualification to pass. Dispatch the publication workflow
from `main` with that same full `release_sha`, as the current repository rules
require; `main` must still point at it. The TestPyPI environment must allow
`main`, with its required reviewer retained. Changing that setting is Patrick's
action and does not authorize a dispatch or upload.

For `1.0.0rc1`, use this order. These commands are templates, not an approval to
dispatch or publish:

1. On a clean checkout of the final reviewed `main`, record its full 40-character
   SHA. Verify `pyproject.toml` says `1.0.0rc1`, `CHANGELOG.md` has the exact
   `## 1.0.0rc1` heading, the candidate wheel's packaged runtime files,
   entry points and the `Name`, `Version`, `Requires-Python`, `Requires-Dist` and
   `Provides-Extra` metadata match the retained fixture writer, and a successful **push-to-main**
   Library qualification run reports this exact SHA. Recheck the TestPyPI version
   slot immediately before dispatch. Also confirm the `testpypi` environment
   still permits `main` and requires Patrick, and the TestPyPI trusted publisher
   names this repository, `publish-pypi.yml` and that environment. The preflight
   records a qualification run but does **not** require its conclusion to be
   successful; a provisional preflight receipt is not release approval. The
   rc1 `Development Status :: 4 - Beta` classifier changes distribution
   metadata from the unpublished fixture writer. It does not change those
   runtime fields; do not require whole-wheel or whole-`METADATA` byte equality.
   Read the matching push runs, then inspect the successful run's aggregate
   `Qualification` check and six platform receipts:

   ```sh
   git fetch origin main
   RC_RELEASE_SHA=$(git rev-parse HEAD)
   test "$(git status --porcelain)" = ""
   test "$(git rev-parse origin/main)" = "$RC_RELEASE_SHA"
   gh run list --repo Smart-AI-Memory/attune-harness --workflow qualification.yml --commit "$RC_RELEASE_SHA" --event push --json databaseId,headSha,event,status,conclusion,url
   ```
2. After Patrick explicitly authorizes the **build-only rehearsal dispatch**, run
   from that checkout:

   ```sh
   gh workflow run publish-pypi.yml --repo Smart-AI-Memory/attune-harness --ref main -f release_sha="$RC_RELEASE_SHA" -f version=1.0.0rc1 -f target=testpypi -f publish=false
   ```

   The workflow rejects a dispatch whose actual `GITHUB_SHA` differs from
   `release_sha`. Inspect that run's conclusion, `release-evidence` preflight,
   `distributions` and SHA-256 file list. `publish=false` has no TestPyPI
   environment job and uploads nothing. A newly built sdist can have a different
   hash even at the same commit; the artifacts from this run are rehearsal
   evidence, not the hashes to verify a later publication.
3. After the rehearsal passes and Patrick separately authorizes the **TestPyPI
   publication dispatch**, recheck `main`, the version slot and qualification;
   dispatch with the same exact version and the then-current reviewed main SHA:

   ```sh
   git fetch origin main
   test "$(git rev-parse origin/main)" = "$RC_RELEASE_SHA"
   gh workflow run publish-pypi.yml --repo Smart-AI-Memory/attune-harness --ref main -f release_sha="$RC_RELEASE_SHA" -f version=1.0.0rc1 -f target=testpypi -f publish=true
   ```

   The build job produces a new manifest binding both distribution hashes to
   this publishing run ID and attempt. Patrick reviews the queued `testpypi`
   deployment before OIDC upload. Approval of the deployment and publication
   consume the version slot; neither the rehearsal nor this document authorizes
   them. Inspect the publishing run's `distributions` and `release-evidence`
   artifacts, and require its `verify_testpypi` job to pass.
4. Verify the published files against the **publishing run's** manifest. Download
   that run's `release-evidence` artifact into a fresh directory, then from the
   same release checkout run:

   ```sh
   (
   set -e
   PUBLISH_RUN_ID=REPLACE_WITH_APPROVED_PUBLISH_RUN_ID
   gh run download "$PUBLISH_RUN_ID" --repo Smart-AI-Memory/attune-harness --name release-evidence --dir release-evidence
   python3 scripts/check_testpypi_rehearsal.py fetch --manifest release-evidence/artifact-manifest.json --output rc1-download --receipt rc1-download.json
   python3 -c 'from pathlib import Path; import sys; p = Path(".venv-rc1"); sys.exit("Refusing to reuse existing .venv-rc1" if p.exists() or p.is_symlink() else 0)'
   python3 -m venv .venv-rc1
   .venv-rc1/bin/python -m pip --isolated --disable-pip-version-check install --index-url https://pypi.org/simple/ -c requirements-workflow.lock -c requirements-voyage.lock -c requirements-mcp.lock -c requirements-tokens.lock -c requirements-redis.lock rc1-download/attune_harness-1.0.0rc1-py3-none-any.whl
   .venv-rc1/bin/python -m pip check
   python3 scripts/check_installed.py --python .venv-rc1/bin/python --mode all --report rc1-installed.json
   .venv-rc1/bin/python -I -c 'import importlib.metadata; assert importlib.metadata.version("attune-harness") == "1.0.0rc1"'
   )
   ```

   `fetch` reads TestPyPI's exact version JSON, refuses a different file
   inventory, size, hash or file host, and saves the verified wheel and sdist.
   Installing that local wheel with dependencies from PyPI avoids a mixed-index
   resolution. The workflow separately installs both downloaded distributions
   into fresh environments and runs the core installed check. On Windows use
   `py -3.12 -m venv .venv-rc1` and `.venv-rc1\Scripts\python.exe` for the
   environment Python. In PowerShell, first run
   `if (Test-Path -LiteralPath .venv-rc1) { throw 'Refusing to reuse existing .venv-rc1' }`;
   do not proceed if it refuses. The POSIX subshell above also stops on any
   failed step without deleting a prior environment. Native memory/saved POSIX
   limitations still apply.
5. Record the release SHA, publication run and attempt, published wheel and
   sdist hashes, TestPyPI download receipt and verified-install time. Only then
   start the 14-day candidate observation clock. No production PyPI release or
   stable-1.0 decision follows automatically.

This replaces the older instruction to dispatch a candidate from a `release/...`
branch. Historical release-branch runs remain evidence; they are not the current
publication procedure. 0.2.0 skipped TestPyPI: packaging had not changed since
0.1.0, and the build job already installs the wheel and runs the installed check
before any upload.
The TestPyPI route is also appropriate when packaging metadata, the build backend
or the workflow itself changes.
