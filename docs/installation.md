# Install Harness and get started

Use this guide for the released `attune-harness` 1.4.0 runtime. Python 3.10 or
later is required. Start with the base package: it includes forms, document
verification, local Markdown retrieval, MCP serving and token counting. Redis
and Voyage are optional integrations.

## Install the runtime

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if it is not
already available. Then install Harness:

```sh
uv tool install 'attune-harness==1.4.0'
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

Expect `attune-harness v1.4.0` in the tool list and the command help with
`init`, `plan`, `build`, `review`, `fix`, `test`, `status` and `resume`.
If the command is not found, follow uv's reported executable-directory guidance
or its tool guide before continuing.

If Harness is already installed, inspect its version and path before changing
it. A version-pinned `uv tool upgrade attune-harness` respects the existing pin;
install the newly selected version explicitly when you choose to update.
Preserve saved task directories and separately retained evidence environments.
Changing the tool version does not qualify migration of older saved work.

You can also install the base package with
`pipx install 'attune-harness==1.4.0'`, or use
`pip install 'attune-harness==1.4.0'` in a dedicated virtual environment.

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

Expect version `1.4.0`, then a JSON receipt with status `verified` for the
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
| Forms, verification, local retrieval and the task workflows | `uv tool install 'attune-harness==1.4.0'` |
| Redis memory access, with a separately configured reachable Redis service | `uv tool install 'attune-harness[redis]==1.4.0'` |
| Voyage retrieval, with a Voyage API key and separate paid-call authority | `uv tool install 'attune-harness[voyage]==1.4.0'` |
| Both Redis and Voyage | `uv tool install 'attune-harness[all]==1.4.0'` |

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

Practice the [1.4.0 forms walkthrough](tutorials-next-release-candidate.md#save-and-approve-a-clear-work-request).
Ask the agent or operator running Harness for a fresh practice form and its
complete private launcher link. Saving answers, approving the request and
executing work remain separate actions. Keep the launcher running while using
the form; saved work is stored in its task directory, not in the launcher URL.

## What was checked

On October 12, 2026, the actual published 1.4.0 wheel was installed on macOS
arm64 with Python 3.10.11 using both a fresh dependency-complete `[all]`
environment and a separate uv 0.11.28 base tool environment. All 105 runtime
modules matched the published source. Both environments passed the existing
29-case offline CLI check and plan/accept/build/review/status journey with
zero model calls. The base environment correctly reported Redis as absent.

The base installation resolved 48 distributions and `[all]` resolved 93,
excluding installer packages, on that machine. Counts vary by environment;
this comparison does not establish equal feature coverage or measured speed.

The release also passed the six installed-platform profiles described in the
[qualification guide](qualification.md). Those profiles are separate from
this Mac uv experiment. A fresh uv install on Linux or Windows, an existing-tool
upgrade, native browser comprehension and saved-work migration were not
established by the experiment. The published
[release](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.4.0)
links the exact source, publishing run and archive checksums.
