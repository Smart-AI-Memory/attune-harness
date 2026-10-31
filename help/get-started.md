## Install Harness 1.6.0

Harness 1.6.0 requires Python 3.12 or later. Install
[uv](https://docs.astral.sh/uv/getting-started/installation/) if needed, then use
its managed environment for the CLI. Version 1.6.0 is available on
[PyPI](https://pypi.org/project/attune-harness/1.6.0/). Keep your working
installation and saved records while checking a replacement.

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

## Connect your assistant

Connect the host you use for your project to the runtime you checked above:

- **Codex:** Follow the reviewed [standalone skill instructions](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/cli-guide.md#codex-skill)
  or [source plugin guide](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/codex-plugin.md).
  After setup, invoke `$attune-harness` and describe your goal.
- **Claude Code:** Read the existing [plugin setup instructions](https://github.com/Smart-AI-Memory/attune-harness/blob/main/README.md#claude-code).
  The marketplace selects the 1.6.0 skills pinned to the released source.
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

## Sources and verification

The [1.6.0 release record](/harness/help/release-1.6.0.json) identifies the
[released source](https://github.com/Smart-AI-Memory/attune-harness/tree/af2159516a67172cc8f2a1ff62213296b1b67112),
wheel and source archive, hosted qualification and verified index installation.
Setup links use maintained repository documentation; the release record retains
the immutable software identity. Each linked historical walkthrough keeps its
stated version, source and observation limits. Repository fixtures are not
included in the wheel.

Qualification checks do not establish model quality or consistent recall across
fresh, resumed or delegated agents. The new writer and cross-agent recall
experiments remain separate from this release.
