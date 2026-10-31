## Install Harness 1.6.0

Harness 1.6.0 requires Python 3.12 or later. Install
[uv](https://docs.astral.sh/uv/getting-started/installation/) if needed, then use
its managed environment for the CLI. The package-index commands on this page
require 1.6.0 to be published. For an unpublished candidate, use the release
owner's exact qualified wheel in a separate environment and keep your working
installation.

Run these commands in Bash on macOS/Linux or PowerShell on Windows.

```sh
uv tool install --python 3.12 'attune-harness==1.6.0'
uv tool list --show-paths
attune-harness --help
```

**Expected result:** The tool list shows Harness `1.6.0`, and help lists
**`init`**, **`plan`**, **`build`**, **`review`**, **`fix`**, **`test`**, **`status`**
and **`resume`**. If the command is unavailable, follow uv's instructions for
adding its executable directory to your path.

The Python runtime and your assistant's integration are separate installations.
Attune AI is not required. The [installation guide](https://github.com/Smart-AI-Memory/attune-harness/blob/e56a09829583993b0ec747886b93cc807650308b/docs/installation.md)
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
selects Python directly, follow the [interpreter instructions](https://github.com/Smart-AI-Memory/attune-harness/blob/e56a09829583993b0ec747886b93cc807650308b/docs/installation.md#select-python-for-module-and-fixture-examples).

## Connect your assistant

Connect the host you use for your project to the runtime you checked above:

- **Codex:** Follow the reviewed [standalone skill instructions](https://github.com/Smart-AI-Memory/attune-harness/blob/e56a09829583993b0ec747886b93cc807650308b/docs/cli-guide.md#codex-skill)
  or [source plugin guide](https://github.com/Smart-AI-Memory/attune-harness/blob/e56a09829583993b0ec747886b93cc807650308b/docs/codex-plugin.md).
  After setup, invoke `$attune-harness` and describe your goal.
- **Claude Code:** Read the existing [plugin setup instructions](https://github.com/Smart-AI-Memory/attune-harness/blob/e56a09829583993b0ec747886b93cc807650308b/README.md#claude-code).
  The published marketplace remains pinned to 1.5.1. Installing the 1.6.0 Python
  runtime does not update that plugin; verify the selected integration before
  using it for 1.6.0 work.
- **Other integrations or direct commands:** Use the reviewed [CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/e56a09829583993b0ec747886b93cc807650308b/docs/cli-guide.md)
  for participant configuration, MCP setup and command arguments. Run
  `attune-harness COMMAND --help` for the selected command.

Your host supplies the conversation and configured model access. Review the
configured participants and authorize paid calls separately.

## Choose goal-driven development

Read [How people and AI work together](https://github.com/Smart-AI-Memory/attune-harness/blob/e56a09829583993b0ec747886b93cc807650308b/docs/cli-guide.md#how-people-and-ai-work-together)
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
The [plan-and-build guide](https://github.com/Smart-AI-Memory/attune-harness/blob/e56a09829583993b0ec747886b93cc807650308b/docs/cli-guide.md#plan-and-build)
explains that procedure. If you already have a supported Markdown plan, follow
the [plan import instructions](https://github.com/Smart-AI-Memory/attune-harness/blob/e56a09829583993b0ec747886b93cc807650308b/docs/cli-guide.md#importing-a-plan-from-another-project)
and review the imported scope before acceptance.

## Keep a working setup

Preserve your working runtime, registry, saved tasks, memory sources, writer and
host hooks while validating a replacement. The [migration guide](https://github.com/Smart-AI-Memory/attune-harness/blob/e56a09829583993b0ec747886b93cc807650308b/docs/migration.md)
explains how to assess an existing setup.

The [1.5.1 guide](/harness/help/1-5-1/) and [release record](/harness/help/release-1.5.1.json)
retain that release's installation procedure, source and artifact identities.
The [documentation archive](/harness/help/archive/) keeps older walkthroughs
and their original limits.

## Sources and verification

These instructions use the reviewed [1.6.0 preparation source](https://github.com/Smart-AI-Memory/attune-harness/tree/e56a09829583993b0ec747886b93cc807650308b).
Source links identify that revision; they do not assert publication or new
platform qualification. The linked workflow guides retain their stated 1.5.1
identities and historical observations. Repository examples named by those
walkthroughs are not included in the wheel; use each walkthrough's stated source
and fixtures.
