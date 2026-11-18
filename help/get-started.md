<p class="help-course-action"><a class="help-featured-nav" href="/harness/learn/reporting/">Browse the six Harness tutorials</a></p>

Choose your starting point:

- For the reporting course, [set up the practice folder](#set-up-the-practice-folder). That setup includes its own Harness installation.
- For a quick local demo, [install Harness](#install-harness), then [check a local result](#check-a-local-result).

## Install Harness

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if needed.
[Harness 1.8.1 is published on PyPI](https://pypi.org/project/attune-harness/1.8.1/)
and requires Python 3.12 or later. Keep a working installation intact while
[checking an upgrade in a separate environment](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/installation.md#upgrade-and-keep-a-rollback-path).

Choose the commands for your terminal. On Windows, open **Windows PowerShell**
or **PowerShell 7** as your normal user. This route selects x64 Python explicitly,
including on an ARM64 Windows device where it runs under emulation.

```powershell
uv tool install --python cpython-3.12-windows-x86_64-none 'attune-harness==1.8.1'
```

Native Windows ARM64 Python requires separately built dependency wheels. See the
[current compatibility results](https://smartaimemory.com/harness/windows/) and
[other installation options](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/installation.md#install-181-with-pipx-or-a-virtual-environment).

On macOS or Linux, install with:

```sh
uv tool install --python 3.12 'attune-harness==1.8.1'
```

## Check a local result

```sh
attune-harness
```

Look for `"status": "verified"`. This is the local demo, not a completed course
build. You can complete the reporting exercise without an assistant account or
API key. If the command is not found, follow the
[uv tool path instructions](https://docs.astral.sh/uv/concepts/tools/#the-bin-directory).

## Set up the practice folder

Build and check an HTML report from six sample activity entries. You can
[preview the sample report](/harness/learn/reporting/assets/example/expected/activity-report.html).
The six lessons use one local project and need no API key. The sample shows what
you will build; viewing it does not verify your own installation or report.

### Check the prerequisites

You need **uv** and **Git** before preparing the practice project. Run:

```text
uv --version
git --version
```

Both commands must print a version. If either is missing, install
[uv](https://docs.astral.sh/uv/getting-started/installation/) or
[Git](https://git-scm.com/downloads), then open a new terminal and check again.
The next step selects Python 3.12 and installs Harness and pytest into a separate
course environment. Keep an existing working installation intact.

### Create the course environment

1. <a href="/harness/learn/reporting/assets/reporting-practice.zip" download>Download practice ZIP</a> and extract it into a new folder.
2. Open a terminal in the extracted folder that contains `practice.py` and
   `requirements-practice.txt`. Keep the extracted files together. Use a folder
   on your local drive, outside a shared or synchronized folder. On Windows,
   use a fixed local NTFS drive.
3. Follow the commands for your shell below. Stop if a command reports an error;
   do not continue to the next step. Use a fresh extracted folder if it already
   contains a `.venv` that you want to keep.

**Windows PowerShell 5.1 or 7**

Create the environment with x64 CPython 3.12:

```powershell
$COURSE_WORK = (Get-Location).Path
uv venv --python cpython-3.12-windows-x86_64-none .venv
```

After uv reports that it created the environment, install the course packages:

```powershell
$COURSE_PYTHON = Join-Path $COURSE_WORK '.venv\Scripts\python.exe'
uv pip install --python $COURSE_PYTHON -r requirements-practice.txt 'attune-harness==1.8.1'
```

Check the selected environment:

```powershell
& $COURSE_PYTHON -c "import sys, sysconfig; from importlib.metadata import version; print(sys.executable); print(sys.version); print(sysconfig.get_platform()); print('Harness', version('attune-harness')); print('pytest', version('pytest'))"
```

Look for Python 3.12, `win-amd64`, Harness 1.8.1 and pytest 9.1.1. The executable
must be inside this folder's `.venv`. No activation script or execution-policy
change is needed: the course calls this Python executable directly.

**macOS/Linux — Bash or Zsh**

```sh
COURSE_WORK="$(pwd -P)" &&
uv venv --python 3.12 .venv &&
COURSE_PYTHON="$COURSE_WORK/.venv/bin/python" &&
uv pip install --python "$COURSE_PYTHON" -r requirements-practice.txt 'attune-harness==1.8.1'
```

Then check the environment:

```sh
"$COURSE_PYTHON" -c "import sys; from importlib.metadata import version; print(sys.executable); print(sys.version); print('Harness', version('attune-harness')); print('pytest', version('pytest'))"
```

Look for Python 3.12, Harness 1.8.1 and pytest 9.1.1, with the executable inside
this folder's `.venv`. No activation is needed.

If you already have a separate compatible environment, set `COURSE_WORK` to the
extracted course folder and `COURSE_PYTHON` to that environment's full Python
path using your shell's syntax. Check its versions before continuing. The
[tested versions and results](/harness/learn/reporting/assets/compatibility.json)
identify actual recorded runs; installation alone does not qualify the course.

Keep this terminal open for lesson 2. Choose the same **Command shell** in the
course. You can run the rest of the reporting exercise offline. Lesson 2 first
prepares a draft; you review its checkpoint and authorize the build separately.
If preparation stops, keep the practice folder. Copy the exact command and
printed error when asking your assistant, teammate or
[Harness support](https://github.com/Smart-AI-Memory/attune-harness/issues) for help.
If the error names a `practice-diagnostics-*` folder, keep it too: `failure.json`
identifies the failed step, and `stdout.bin` and `stderr.bin` preserve the original
output for investigation. Agree on the next action before making another attempt.

<p class="help-course-action"><a class="help-featured-nav" href="/harness/learn/reporting/">Continue to the reporting course</a></p>

## Connect your assistant

This is optional for the local reporting exercise. Connect an assistant when
you are ready to work on your own project:

- [Set up Codex](https://github.com/Smart-AI-Memory/attune-harness#codex), then invoke `$attune-harness`.
- [Set up Claude Code](https://github.com/Smart-AI-Memory/attune-harness#claude-code).

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
  See the [installation guide](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/installation.md#install-181-with-pipx-or-a-virtual-environment)
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
