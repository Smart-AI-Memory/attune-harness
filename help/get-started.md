## Choose a starting path

- [**Check the CLI**](#install-harness-170). Use uv to install the command-line
  interface, then run a short local check. Use Bash on macOS or Linux, or
  PowerShell on Windows.
- [**Build your first offline report**](/harness/learn/1.7.0-preparation/setup.html).
  Review a plan, run a practice build, and check the HTML report. For command
  practice, use Bash or another POSIX shell on macOS or Linux with uv and Git.
  Course setup installs Harness in its own environment. Download the files and
  packages during setup, then run the practice offline.

## Install Harness 1.7.0

Harness 1.7.0 requires Python 3.12 or later. Install
[uv](https://docs.astral.sh/uv/getting-started/installation/) if needed, then use
its managed environment for the CLI. Version 1.7.0 is available on
[PyPI](https://pypi.org/project/attune-harness/1.7.0/#files). If you already use
Harness, [check the update in a separate environment](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/installation.md#upgrade-and-keep-a-rollback-path)
before switching.

Run these commands in Bash on macOS/Linux or PowerShell on Windows.
On Windows, the release checks used x64 Python. The binary-only base install
cannot complete on native Windows ARM64 with Python 3.12. See the
[release record](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.7.0)
for the tested Windows configurations.

```sh
uv tool install --python 3.12 'attune-harness==1.7.0'
uv tool list --show-paths
attune-harness --help
```

**Expected result:** The tool list shows Harness `1.7.0`, and help lists
**`init`**, **`plan`**, **`build`**, **`review`**, **`fix`**, **`test`**, **`status`**
and **`resume`**. If the command is unavailable, follow uv's instructions for
adding its executable directory to your path.

The Python runtime and your assistant's integration are separate installations.
Attune AI is not required. The [installation guide](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/installation.md)
covers pipx, virtual environments and selecting the same interpreter for module
commands.

## Check a local result

Run the installed CLI without arguments to check a local result:

```sh
attune-harness
```

**Expected result:** A JSON receipt with `"status": "verified"` and
`"participant_id": "deterministic-demo"`. The demonstration uses a local worker
and an independent check of `2 + 2`; it needs no API key and makes no model call.
This checks the demonstration and does not measure model quality.

Use the same command in Windows PowerShell. No separate environment activation
or PowerShell activation-policy change is needed. For an alternative setup that
selects Python directly, follow the [interpreter instructions](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/installation.md#select-python-for-module-and-fixture-examples).

## Build your first report offline

Open [Get ready for the course](/harness/learn/1.7.0-preparation/setup.html) to
set up an isolated practice environment, then follow **Build your first report**.
You review a plan, authorize a local build, and check an HTML report from six
sample entries. The lesson uses fixed local commands and needs no API key,
assistant plugin or model call. Download the package and example files before
working offline.

## Connect your assistant

Connect the host you use for your project to the runtime you checked above:

- **Codex:** Follow the reviewed [standalone skill instructions](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/cli-guide.md#codex-skill)
  or [source plugin guide](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/codex-plugin.md).
  After setup, invoke `$attune-harness` and describe your goal.
- **Claude Code:** Read the existing [plugin setup instructions](https://github.com/Smart-AI-Memory/attune-harness/blob/main/README.md#claude-code).
  The marketplace selects the 1.7.0 skills pinned to the released source.
  Installing the Python runtime does not update an existing host plugin;
  refresh the marketplace and verify your selected plugin's version and source.
- **Other integrations or direct commands:** Use the reviewed [CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/cli-guide.md)
  for participant configuration, MCP setup and command arguments. Run
  `attune-harness COMMAND --help` for the selected command.

Your host supplies the conversation and configured model access. Review the
configured participants and authorize paid calls separately.

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

## Keep a working setup

Preserve your working runtime, registry, saved tasks, memory sources, writer and
host hooks while validating a replacement. The [migration guide](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/migration.md)
explains how to assess an existing setup.

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
for those guides. The managed 1.7.0 installation above does not activate a
1.5.1 Python environment or supply the example checkout.

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
artifact identities and original evidence. Use another shell for the managed
1.7.0 CLI above, or run `deactivate` when finished with the practice environment.

## Sources and verification

The [1.7.0 release record](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.7.0)
identifies the released source, wheel and source archive, hosted qualification
and verified index installation.
Setup links use maintained repository documentation; the release record retains
the immutable software identity. Each linked historical walkthrough keeps its
stated version, source and observation limits. Repository fixtures are not
included in the wheel.

Qualification checks do not establish model quality or consistent recall across
fresh, resumed or delegated agents. The new writer and cross-agent recall
experiments remain separate from this release.
