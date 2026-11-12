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

## Set up the practice folder

Build and check an HTML report from six sample activity entries. You can
[preview the sample report](/harness/learn/reporting/assets/example/expected/activity-report.html).
The six lessons use one local project and need no API key.

1. <a href="/harness/learn/reporting/assets/reporting-practice.zip" download>Download practice ZIP</a> and extract it into a new folder.
2. Open a terminal in the extracted folder that contains `practice.py`. Use
   Bash or Zsh on macOS or Linux. Install Git if needed.
3. Run these commands to set up a separate environment with Harness and pytest.

```sh
COURSE_WORK="$(pwd -P)" &&
uv venv --python 3.12 .venv &&
uv pip install --python .venv/bin/python -r requirements-practice.txt &&
. .venv/bin/activate
```

If you already have a separate practice environment with Harness and pytest,
activate it and run `COURSE_WORK="$(pwd -P)"` from the extracted folder. See the
[tested versions and results](/harness/learn/reporting/assets/compatibility.json).

Keep this terminal open for lesson 2. You can run the rest of the exercise offline.

<p class="help-course-action"><a class="help-featured-nav" href="/harness/learn/reporting/">Continue to the reporting course</a></p>

## Choose goal-driven development

Read [How people and AI work together](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/cli-guide.md#how-people-and-ai-work-together)
to understand your decisions and the AI's role in carrying out accepted work.

Start with a small outcome in a project you know. Ask your assistant to help
prepare the plan for your review.

<div class="help-prompt">
<p class="help-prompt-label">Example prompt</p>
<p data-copy-prompt>Use Harness to help me plan an update to this project. Help me define the goal, affected files and checks before we build.</p>
</div>

Use [Plan a change](/harness/help/goals/#feature-request) to prepare your
request. [Browse all goals](/harness/help/goals/) to find a guide for review,
repair, testing, or saved work.

Review the proposed scope, participants, and checks before accepting the plan.
Authorize the build when you are ready to start it.

<p class="help-tip"><strong>Tip</strong> Use <strong><code>status</code></strong> to inspect saved decisions before continuing.</p>

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
