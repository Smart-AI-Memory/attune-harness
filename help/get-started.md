## Install Harness

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if needed.
Harness requires Python 3.12 or later.

```sh
uv tool install --python 3.12 attune-harness
```

## Check a local result

```sh
attune-harness
```

Look for `"status": "verified"`. The demo runs locally and needs no API key.

## Connect your assistant

- [Set up Codex](https://github.com/Smart-AI-Memory/attune-harness#codex), then invoke `$attune-harness`.
- [Set up Claude Code](https://github.com/Smart-AI-Memory/attune-harness#claude-code).

## Choose goal-driven development

Read [How people and AI work together](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/cli-guide.md#how-people-and-ai-work-together)
to understand your decisions and the AI's role in carrying out accepted work.

Start with a small outcome in a project you know. For example, ask your assistant:

<div class="help-prompt">
<p class="help-eyebrow">Starter prompt</p>
<p data-copy-prompt>Use Harness to help me plan an update to this project. Help me define the goal, affected files and checks before we build.</p>
</div>

Use [Plan a change](/harness/help/goals/#feature-request) to prepare a clear
request, or [browse all goals](/harness/help/goals/) to choose review, repair,
testing or saved work. The existing goals guide keeps its stated version and
historical screenshots; its prompts and review points help you choose the work.

Review the proposed scope, participants and checks before accepting it. Accepting
a plan records the agreed work; starting a build is a separate action. Use
**`status`** to inspect saved decisions before continuing.

## Choose spec-driven development

Use a specification when the work needs more structure than a short request.
Follow [Create a spec with roundtable help](/harness/help/goals/#project-spec)
for an existing worked example and review points. The worksheet records proposed
wording; copying a prompt or preparing a draft does not dispatch a model,
approve the spec or start implementation.

A reviewed spec still needs a supported, accepted plan before a build can start.
The [plan-and-build guide](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/cli-guide.md#plan-and-build)
explains that procedure. If you already have a supported Markdown plan, follow
the [plan import instructions](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/cli-guide.md#importing-a-plan-from-another-project)
and review the imported scope before acceptance.

## Build your first report offline

The six-lesson reporting course uses Harness 1.7.0. Open
[Get ready for the 1.7.0 course](/harness/learn/1.7.0-preparation/setup.html) to
create its separate practice environment, then follow **Build your first report**.
You review a plan, authorize a local build, and check an HTML report from six
sample entries. Download the package and example files before working offline.

## Keep a working setup

- If you already use Harness, [check the update in a separate environment](https://github.com/Smart-AI-Memory/attune-harness/blob/main/README.md#upgrade-and-keep-a-rollback-path)
  before switching. See the [migration guide](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/migration.md)
  for saved tasks, memory, and host settings.
- If your shell can't find the command, [add the uv tool directory to your path](https://docs.astral.sh/uv/concepts/tools/#tool-executables).
  See the [installation guide](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/installation.md#install-with-pipx-or-a-virtual-environment)
  for pipx and virtual environments.
- Check the [supported Windows configurations](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/supported-journeys.md#windows-capabilities-and-reliability)
  and [optional integrations](https://github.com/Smart-AI-Memory/attune-harness/blob/main/README.md#optional-integrations)
  if you need them.

The [1.5.1 guide](/harness/help/1-5-1/) and [release record](/harness/help/release-1.5.1.json)
retain that release's installation procedure, source and artifact identities.
The [documentation archive](/harness/help/archive/) keeps older walkthroughs
and their original limits.

## Prepare the 1.5.1 practice examples

The [Start and continue](/harness/help/start-and-continue/),
[Plan and accept](/harness/help/plan-and-accept/),
[Research](/harness/help/research/) and
[Save and resume](/harness/help/save-and-resume/) practice guides retain their
published 1.5.1 commands and historical observations. Use this separate setup
for those guides.

Open a fresh POSIX shell on macOS or Linux and choose an unused working directory.
On macOS, use a canonical path under `/private/tmp` rather than the `/tmp` symlink.
Run:

```sh
PRACTICE="$PWD/harness-1.5.1-practice"
mkdir "$PRACTICE"
cd "$PRACTICE"
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install 'attune-harness==1.5.1'
git clone --no-checkout https://github.com/Smart-AI-Memory/attune-harness.git release-source
R="$(cd release-source && pwd -P)"
git -C "$R" checkout --detach ebb5b03b8a4398325df7ddabd28c08186451452e
python -c "from importlib.metadata import version; assert version('attune-harness') == '1.5.1'; print(version('attune-harness'))"
python -m attune_harness
```

**Expected result:** Version `1.5.1`, a verified local demonstration receipt, and
`R` naming the absolute source checkout for that same release. Keep this shell
open for the practice guide. Its task directories belong beside `release-source`,
outside the checkout. The examples are source files, not wheel contents.

These are POSIX practice instructions, not a new Windows shell qualification.
The [1.5.1 release record](/harness/help/release-1.5.1.json) retains its exact
artifact identities and original evidence. Use another shell for your regular
CLI, or run `deactivate` when finished with the practice environment.

## Sources and verification

Read the [changelog](https://github.com/Smart-AI-Memory/attune-harness/blob/main/CHANGELOG.md)
for changes and deprecation notices. If an upgrade requires action, see the
[migration guide](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/migration.md).
The [release history](https://github.com/Smart-AI-Memory/attune-harness/releases)
identifies the source and artifacts for each published version. Historical
walkthroughs keep their original versions and verification limits.
