# Install Harness and get started

Updated on November 16, 2026.

This guide describes Harness 1.8.1, which is in preparation and requires
Python 3.12 or later. Use the [candidate-wheel steps](#check-the-181-candidate)
before publication. Run the package-index commands below only after
[PyPI lists 1.8.1](https://pypi.org/project/attune-harness/1.8.1/).
The [1.8.1 readiness record](release-readiness-1.8.1.md) identifies the candidate
artifacts and checks. For the current published release, use the
[1.8.0 installation guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.8.0/docs/installation.md).

Follow the [README quickstart](../README.md#install-181) to install with uv and
check a local result. If you already use Harness,
[keep a rollback path](#upgrade-and-keep-a-rollback-path).

Start with the base package. Add [optional integrations](../README.md#optional-integrations)
when you need them. The
[published 1.6.0 release record](../help/release-1.6.0.json) and
[historical preparation guide](release-preparation-1.6.0.md) retain their
original artifact identities and limits.

<a id="install-with-pipx-or-a-virtual-environment"></a>
<a id="install-180-with-pipx-or-a-virtual-environment"></a>

## Install 1.8.1 with pipx or a virtual environment

After publication, install an isolated CLI with
[pipx](https://pipx.pypa.io/latest/reference/cli.html):

```sh
pipx install --python python3.12 'attune-harness==1.8.1'
attune-harness
```

On Windows, use the full path to your Python 3.12 executable for `--python`.

To install in a new, dedicated virtual environment on macOS or Linux after
publication, run:

```sh
python3.12 -m venv .venv-harness-181
.venv-harness-181/bin/python -m pip install 'attune-harness==1.8.1'
.venv-harness-181/bin/python -m attune_harness
```

On Windows, create the environment with `py -3.12 -m venv .venv-harness-181`
and use `.venv-harness-181\Scripts\python.exe` for the two module commands.
The demonstration prints a JSON receipt with `"status": "verified"`. For
platform requirements, see the [Windows capability table](supported-journeys.md#windows-capabilities-and-reliability).

<a id="install-the-runtime"></a>

## Install the 1.7.0 runtime

Use 1.7.0 when reproducing the versioned Help Center walkthroughs and archived
course that name it. The maintained reporting course records its tested runtimes
in the [compatibility results](../training/reporting/assets/compatibility.json).
The [1.7.0 release record](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.7.0)
lists the published files, their hashes and the checks that ran.

If Harness is already installed, inspect its version and path with
`uv tool list --show-paths`. Follow
[Upgrade and keep a rollback path](#upgrade-and-keep-a-rollback-path) before
switching a working installation.

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if needed.
Select Python 3.12 when installing Harness.

On Windows, the release checks used x64 Python. The binary-only base install
cannot complete on native Windows ARM64 with Python 3.12. See the
[release record](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.7.0)
for the tested configurations.

```sh
uv tool install --python 3.12 'attune-harness==1.7.0'
```

uv manages an isolated environment and exposes the `attune-harness` command;
you do not need to create or activate a project virtual environment. See
[uv's tool guide](https://docs.astral.sh/uv/guides/tools/) for how it manages
executables and dependencies. Keep Harness and Attune AI in separate
environments: they require different MCP SDK versions.

Check the selected installation:

```sh
uv tool list --show-paths
attune-harness --help
```

Expect `attune-harness v1.7.0` in the tool list and the command help with
`init`, `plan`, `build`, `review`, `fix`, `test`, `status` and `resume`.
If the command is not found, follow uv's reported executable-directory guidance
or its tool guide before continuing.

You can also install the base package with
[pipx](https://pipx.pypa.io/latest/reference/cli.html) with
`pipx install --python python3.12 'attune-harness==1.7.0'`, or use
`python -m pip install 'attune-harness==1.7.0'` in a dedicated Python 3.12
virtual environment. On Windows, select the full path to your Python 3.12
executable for pipx's `--python` option.

## Build your first report offline

After checking the installation,
[preview the course from source](../training/README.md#preview-the-course).
Open **Get ready for the course**, then follow **Build your first report**.
The setup creates a separate environment for the published Harness package
and pytest. Download the example and dependencies before working offline.

The lesson uses a disposable Git project and fixed local commands. You
review and accept a plan, authorize the build separately, then check the
resulting HTML report. You can complete it without connecting an assistant,
configuring an API key or calling a model.

## Select Python for module and fixture examples

The `attune-harness` command uses the managed runtime. Commands such as
`python -m attune_harness.gui` and source-checkout fixture scripts also need
that runtime's interpreter; an unrelated `python` command may not contain
Harness. Use the environment path shown beside `attune-harness` in
`uv tool list --show-paths`.

For a normal uv installation, select it on macOS or Linux:

```sh
harness_python="$(uv tool dir)/attune-harness/bin/python"
"$harness_python" --version
"$harness_python" -c "import importlib.metadata; print(importlib.metadata.version('attune-harness'))"
"$harness_python" -m attune_harness
```

On Windows, use PowerShell:

```powershell
$harnessPython = Join-Path (uv tool dir) 'attune-harness\Scripts\python.exe'
& $harnessPython --version
& $harnessPython -c "import importlib.metadata; print(importlib.metadata.version('attune-harness'))"
& $harnessPython -m attune_harness
```

Expect the Python and Harness versions you selected, then a JSON receipt with
status `verified` for the deterministic arithmetic example. If the listed environment is at a different
path, use its `bin/python` on macOS/Linux or `Scripts\python.exe` on Windows.
Substitute that same interpreter for `python` in module and fixture commands
in the linked guides; for example, use `"$harness_python" -m attune_harness.gui`
on macOS/Linux. The GUI still requires an existing registered task and the
documented launch options. Check the selected interpreter's version before
running those examples; no shell activation is needed.

## Choose optional integrations when needed

After 1.8.1 is published, select a profile when installing or deliberately
updating your managed tool. Before publication, keep the working published
profile; use the separate candidate-wheel steps to evaluate the base package.

| You need | Install |
| --- | --- |
| Forms, verification, local retrieval and the task workflows | `uv tool install --python 3.12 'attune-harness==1.8.1'` |
| Redis memory access, with a separately configured reachable Redis service | `uv tool install --python 3.12 'attune-harness[redis]==1.8.1'` |
| Voyage retrieval, with a Voyage API key and separate paid-call authority | `uv tool install --python 3.12 'attune-harness[voyage]==1.8.1'` |
| Both Redis and Voyage | `uv tool install --python 3.12 'attune-harness[all]==1.8.1'` |

Selecting another profile changes that tool's environment; it does not start a
Redis service, configure credentials or authorize model calls. `all` excludes
both experimental `memory-native` and `plan-oauth`. The separate
**`openai-plan`** adapter requires the explicit `plan-oauth` extra and currently
admits only macOS arm64 / CPython 3.12.2. See
[participant funding](participant-funding.md) for its setup and unqualified live
account, quota and billing boundaries. For native memory and other platform
limits, see the [CLI guide](cli-guide.md) and
[qualification guide](qualification.md).
The Redis profile installs the pinned Python client. Check the
[operation-specific Redis requirements](cli-guide.md#redis-requirements): hydrated
recall needs Search, Functions and existing indexed records; scratch and the saved
mirror have different requirements. The hydration capture, secret-check and
payload-accounting primitives in 1.7.0 are groundwork. Keep existing writers and
host hooks. A supported **`memory hydrate`** command, generation publication and
cleanup, and automatic fresh-session delivery remain unfinished.

## Connect the agent and open a first task

The Python runtime and the agent integration are separate installations.
Choose the host you use:

- **Codex:** Follow the [Harness plugin guide](codex-plugin.md), or the
  [standalone skill instructions](cli-guide.md#codex-skill). Confirm that the
  selected integration uses the runtime checked above.
- **Claude Code:** Follow the [README's marketplace instructions](../README.md#use-harness-with-codex-claude-or-other-models).
  The marketplace installs the skills; the runtime remains separately installed.
- **Direct CLI:** Read [checks and receipts](cli-guide.md#checks-and-receipts)
  or use `attune-harness COMMAND --help` for the chosen task.

Choose a task in the [goals guide](https://smartaimemory.com/harness/help/goals/).
For a historical walkthrough, use the version and example checkout it names.
Ask the agent or operator running Harness for a fresh practice form and its
complete private launcher link. Saving answers, approving the request and
executing work remain separate actions. Keep the launcher running while using
the form; saved work is stored in its task directory, not in the launcher URL.

## Verify your installation

Compare the selected version and interpreter with the checks above. During
preparation, use the exact wheel hash, source and platform evidence in the
[1.8.1 readiness record](release-readiness-1.8.1.md). After publication, compare
with the [1.8.1 release](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.8.1)
as well. A verified arithmetic result does not qualify every workflow or platform.
The [1.8.0 release](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.8.0)
retains that version's distribution hashes and checks. Earlier observations remain in the
[documentation archive](https://smartaimemory.com/harness/help/archive/).

<a id="validate-160-and-retain-rollback"></a>
<a id="validate-170-and-retain-rollback"></a>

## Upgrade and keep a rollback path

Inspect the current runtime and retain its environment before switching your
host integration. During preparation, follow [Check the 1.8.1 candidate](#check-the-181-candidate).
After 1.8.1 is published, check it in a separate environment with the commands
below. Use an unused path. For a historical walkthrough, keep the runtime it
names, including the [1.7.0 setup](#install-the-170-runtime).

```sh
python3.12 -m venv .venv-harness-181
.venv-harness-181/bin/python -m pip install 'attune-harness==1.8.1'
.venv-harness-181/bin/python -c "from importlib.metadata import version; print(version('attune-harness'))"
.venv-harness-181/bin/python -m attune_harness
```

On Windows, use `py -3.12 -m venv .venv-harness-181` and
`.venv-harness-181\Scripts\python.exe` for each Python command. Expect version
`1.8.1` and a JSON receipt with a verified arithmetic result. Check the workflow
you need before switching a working installation. A pinned `uv tool upgrade`
respects its existing version pin; select 1.8.1 explicitly
when updating the managed tool.

Keep the old runtime and its original participant registry for rollback.
Version 1.5.1 retains its Python 3.10 minimum and rejects the new command
`environment` field. To roll back, select that retained runtime and its original
registry. Preserve saved tasks, approval records, memory sources, writers, hooks
and Redis data. See the [migration guide](migration.md) before replacing an
existing memory or host path.

## Reproduce the pre-release setup

<a id="select-a-candidate-without-replacing-a-working-runtime"></a>

To reproduce a preparation result, follow the
[installation guide at the release tag](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.7.0/docs/installation.md#select-a-candidate-without-replacing-a-working-runtime)
with the exact rehearsal wheel and interpreter named in the observation.
Use the published wheel for a new installation.

## Check the 1.8.1 candidate

Use the exact wheel identified in the [1.8.1 readiness record](release-readiness-1.8.1.md)
once it is available. Match its SHA-256 to that record before installing.
Keep your working runtime and use an unused environment path. Run one command
at a time from the folder containing the wheel; stop if a command fails.

On macOS or Linux:

```sh
python3.12 -m venv .venv-harness-181-candidate
.venv-harness-181-candidate/bin/python -m pip install ./attune_harness-1.8.1-py3-none-any.whl
.venv-harness-181-candidate/bin/python -c "from importlib.metadata import version; print(version('attune-harness'))"
.venv-harness-181-candidate/bin/python -m attune_harness
```

On Windows, replace the example path with your selected x64 Python 3.12
executable. Check the version and platform first; continue only when they show
Python 3.12 and `win-amd64`. Then create the candidate environment:

```powershell
$HarnessPython = 'C:\path\to\Python312\python.exe'
& $HarnessPython -c "import sys, sysconfig; print(sys.version); print(sysconfig.get_platform())"
& $HarnessPython -m venv .venv-harness-181-candidate
& '.\.venv-harness-181-candidate\Scripts\python.exe' -m pip install .\attune_harness-1.8.1-py3-none-any.whl
& '.\.venv-harness-181-candidate\Scripts\python.exe' -c "from importlib.metadata import version; print(version('attune-harness'))"
& '.\.venv-harness-181-candidate\Scripts\python.exe' -m attune_harness
```

Use the PowerShell call operator `&` before a variable or quoted executable
path. A launcher version tag alone does not establish the interpreter architecture.

Expect `1.8.1` and a JSON receipt with status `verified`. The arithmetic example
makes no model calls. Record the wheel hash, source commit, Python version and
architecture, operating system and result. This checks the local installation;
read the readiness record and [Windows capability table](supported-journeys.md#windows-capabilities-and-reliability)
for the separately tested workflows and remaining limits.

## Check the 1.8.0 candidate

To reproduce the 1.8.0 release preparation, use the wheel from the reviewed
build. Match its SHA-256 to the build record before installing. Keep the
published 1.7.0 environment available.
For example, from the directory containing the wheel, use a new environment
on macOS or Linux:

```sh
python3.12 -m venv .venv-harness-180
.venv-harness-180/bin/python -m pip install ./attune_harness-1.8.0-py3-none-any.whl
.venv-harness-180/bin/python -c "from importlib.metadata import version; print(version('attune-harness'))"
.venv-harness-180/bin/python -m attune_harness
```

Expect `1.8.0` and a JSON receipt with status `verified`. This arithmetic
example makes no model calls. Record the wheel hash, source commit and
platform with the result. See the [1.8.0 readiness record](release-readiness-1.8.0.md)
for the remaining qualification and publication steps.

For a new installation after 1.8.1 is published, follow
[Install 1.8.1 with pipx or a virtual environment](#install-181-with-pipx-or-a-virtual-environment).
Before publication, use the [published 1.8.0 guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.8.0/docs/installation.md)
or evaluate the separate [1.8.1 candidate](#check-the-181-candidate).
