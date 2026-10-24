# Install Harness and get started

Updated on October 23, 2026.

This guide prepares installation of `attune-harness` 1.5.1. Python 3.10 or
later is required. Start with the base package: it includes forms, document
verification, local Markdown retrieval, MCP serving and token counting. Redis
and Voyage are optional integrations.

**Check release availability.** The index-install commands below require 1.5.1
to be published on PyPI. While 1.5.1 is unpublished, use
`uv tool install 'attune-harness==1.5.0'`, or follow the
[published 1.5.0 package reference](https://pypi.org/project/attune-harness/1.5.0/).
For candidate validation, substitute the reviewed local 1.5.1 wheel for the package
specifier, for example `uv tool install /absolute/path/to/attune_harness-1.5.1-py3-none-any.whl`.
Retain its source and hash; a version string does not identify a final artifact.
Preserve saved work and retained evidence environments when selecting a runtime.

## Install the runtime

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if it is not
already available. Then install Harness:

```sh
uv tool install 'attune-harness==1.5.1'
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

Expect `attune-harness v1.5.1` in the tool list and the command help with
`init`, `plan`, `build`, `review`, `fix`, `test`, `status` and `resume`.
If the command is not found, follow uv's reported executable-directory guidance
or its tool guide before continuing.

If Harness is already installed, inspect its version and path before changing
it. A version-pinned `uv tool upgrade attune-harness` respects the existing pin;
install the newly selected version explicitly when you choose to update.
Preserve saved task directories and separately retained evidence environments.
Changing the tool version does not qualify migration of older saved work.

You can also install the base package with
`pipx install 'attune-harness==1.5.1'`, or use
`pip install 'attune-harness==1.5.1'` in a dedicated virtual environment.

## Select Python for module and fixture examples

The `attune-harness` command uses the managed runtime. Commands such as
`python -m attune_harness.gui` and source-checkout fixture scripts also need
that runtime's interpreter; an unrelated `python` command may not contain
Harness. Use the environment path shown beside `attune-harness` in
`uv tool list --show-paths`.

For a normal uv installation, select it on macOS or Linux:

```sh
harness_python="$(uv tool dir)/attune-harness/bin/python"
"$harness_python" -c "import importlib.metadata; print(importlib.metadata.version('attune-harness'))"
"$harness_python" -m attune_harness
```

On Windows, use PowerShell:

```powershell
$harnessPython = Join-Path (uv tool dir) 'attune-harness\Scripts\python.exe'
& $harnessPython -c "import importlib.metadata; print(importlib.metadata.version('attune-harness'))"
& $harnessPython -m attune_harness
```

Expect version `1.5.1`, then a JSON receipt with status `verified` for the
deterministic arithmetic example. If the listed environment is at a different
path, use its `bin/python` on macOS/Linux or `Scripts\python.exe` on Windows.
Substitute that same interpreter for `python` in module and fixture commands
in the linked guides; for example, use `"$harness_python" -m attune_harness.gui`
on macOS/Linux. The GUI still requires an existing registered task and the
documented launch options. Check the selected interpreter's version before
running those examples; no shell activation is needed.

## Choose optional integrations when needed

Select a profile when installing or deliberately updating your managed tool:

| You need | Install |
| --- | --- |
| Forms, verification, local retrieval and the task workflows | `uv tool install 'attune-harness==1.5.1'` |
| Redis memory access, with a separately configured reachable Redis service | `uv tool install 'attune-harness[redis]==1.5.1'` |
| Voyage retrieval, with a Voyage API key and separate paid-call authority | `uv tool install 'attune-harness[voyage]==1.5.1'` |
| Both Redis and Voyage | `uv tool install 'attune-harness[all]==1.5.1'` |

Selecting another profile changes that tool's environment; it does not start a
Redis service, configure credentials or authorize model calls. `all` excludes
experimental native memory. For that separate profile and its platform limits,
see the [CLI guide](cli-guide.md) and [qualification guide](qualification.md).

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

Choose a [practice walkthrough](tutorials-1.5.1.md#choose-a-walkthrough)
and read its source, interpreter and fixture requirements before starting.
Ask the agent or operator running Harness for a fresh practice form and its
complete private launcher link. Saving answers, approving the request and
executing work remain separate actions. Keep the launcher running while using
the form; saved work is stored in its task directory, not in the launcher URL.

## Verify your installation

Compare your selected version and interpreter with the checks above. The
[1.5.1 readiness record](release-readiness-1.5.1.md) identifies the reviewed
source, local validation and remaining release checks. After publication,
compare the published distribution identity and index installation with that
evidence. The [workflow guide](supported-journeys.md) describes
capabilities and reliability requirements for the workflow you choose. Keep
existing saved tasks and evidence environments when updating an installation.
