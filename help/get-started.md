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

## Build your first report offline

[Set up the reporting course](/harness/learn/reporting/setup.html) to download
the example files and prepare a practice environment with the current release.
Then follow the six lessons to plan, build, and check an HTML report. The
exercise needs no API key.

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

- If you already use Harness, [check the update in a separate environment](https://github.com/Smart-AI-Memory/attune-harness/blob/main/README.md#upgrade-and-keep-a-rollback-path)
  before switching. See the [migration guide](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/migration.md)
  for saved tasks, memory, and host settings.
- If your shell can't find the command, [add the uv tool directory to your path](https://docs.astral.sh/uv/concepts/tools/#tool-executables).
  See the [installation guide](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/installation.md#install-with-pipx-or-a-virtual-environment)
  for pipx and virtual environments.
- Check the [supported Windows configurations](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/supported-journeys.md#windows-capabilities-and-reliability)
  and [optional integrations](https://github.com/Smart-AI-Memory/attune-harness/blob/main/README.md#optional-integrations)
  if you need them.

## Sources and verification

Find the [archived practice setup](/harness/help/1-5-1/#prepare-the-151-practice-examples)
and other historical walkthroughs in the [documentation archive](/harness/help/archive/).

Read the [changelog](https://github.com/Smart-AI-Memory/attune-harness/blob/main/CHANGELOG.md)
for changes and deprecation notices. If an upgrade requires action, see the
[migration guide](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/migration.md).
The [release history](https://github.com/Smart-AI-Memory/attune-harness/releases)
identifies the source and artifacts for each published version. Historical
walkthroughs keep their original versions and verification limits.
