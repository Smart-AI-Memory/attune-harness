# Install Harness and get started

Updated on November 4, 2026, for Harness 1.7.0 preparation.

**Harness 1.7.0 is being prepared and is not published.** It requires Python
3.12 or later. Published 1.6.0 remains available; version 1.5.1 retains its
original Python 3.10 minimum. Before 1.7.0 publication, use the
[reviewed local-wheel route](#select-a-candidate-without-replacing-a-working-runtime)
in a separate environment. The 1.7.0 index-installation commands below apply
only after publication is verified.

Start with the base package; Redis and Voyage are optional. Keep a working runtime
and its saved records while checking a replacement. Read the [migration guide](migration.md)
and the [1.7.0 readiness record](release-readiness-1.7.0.md). The
[published 1.6.0 release record](../help/release-1.6.0.json) and
[historical preparation guide](release-preparation-1.6.0.md) retain their
original artifact identities and limits.

## Install the runtime

After 1.7.0 publication, install
[uv](https://docs.astral.sh/uv/getting-started/installation/) if it is not
already available. Explicitly select Python 3.12 when installing Harness:

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

If Harness is already installed, inspect its version and path before changing
it. A version-pinned `uv tool upgrade attune-harness` respects the existing pin;
install the newly selected version explicitly when you choose to update.
Preserve saved task directories and separately retained evidence environments.
Changing the tool version does not qualify migration of older saved work.

After publication, you can also install the base package with
[pipx](https://pipx.pypa.io/latest/reference/cli.html) with
`pipx install --python python3.12 'attune-harness==1.7.0'`, or use
`python -m pip install 'attune-harness==1.7.0'` in a dedicated Python 3.12
virtual environment. On Windows, select the full path to your Python 3.12
executable for pipx's `--python` option.

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

Expect Python `3.12.x`, package version `1.7.0`, then a JSON receipt with status
`verified` for the deterministic arithmetic example. If the listed environment is at a different
path, use its `bin/python` on macOS/Linux or `Scripts\python.exe` on Windows.
Substitute that same interpreter for `python` in module and fixture commands
in the linked guides; for example, use `"$harness_python" -m attune_harness.gui`
on macOS/Linux. The GUI still requires an existing registered task and the
documented launch options. Check the selected interpreter's version before
running those examples; no shell activation is needed.

## Choose optional integrations when needed

After publication, select a profile when installing or deliberately updating
your managed tool. For candidate checks, install the corresponding extra from
the exact local wheel instead:

| You need | Install |
| --- | --- |
| Forms, verification, local retrieval and the task workflows | `uv tool install --python 3.12 'attune-harness==1.7.0'` |
| Redis memory access, with a separately configured reachable Redis service | `uv tool install --python 3.12 'attune-harness[redis]==1.7.0'` |
| Voyage retrieval, with a Voyage API key and separate paid-call authority | `uv tool install --python 3.12 'attune-harness[voyage]==1.7.0'` |
| Both Redis and Voyage | `uv tool install --python 3.12 'attune-harness[all]==1.7.0'` |

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
host hooks; this candidate supplies no supported **`memory hydrate`** command,
generation publication/cleanup or automatic fresh-session delivery.

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
The [historical 1.5.1 preparation walkthroughs](tutorials-1.5.1.md#choose-a-walkthrough)
retain their original source, interpreter and fixture requirements. Existing
Help and tutorial references remain 1.6.0 or historical guidance; their separate
owner updates and publication are not established by this candidate guide.
Ask the agent or operator running Harness for a fresh practice form and its
complete private launcher link. Saving answers, approving the request and
executing work remain separate actions. Keep the launcher running while using
the form; saved work is stored in its task directory, not in the launcher URL.

## Verify your installation

Compare the selected version and interpreter with the checks above. The
[published 1.6.0 release record](../help/release-1.6.0.json)
identifies that release's source and distributions, not the 1.7.0 candidate.
Record the candidate's actual source commit, wheel SHA-256 and installed metadata
from the release owner. Use the [workflow guide](supported-journeys.md)
to choose a task and check its requirements. Earlier observations remain in the
[documentation archive](https://smartaimemory.com/harness/help/archive/).

<a id="validate-160-and-retain-rollback"></a>
<a id="validate-170-and-retain-rollback"></a>

## Upgrade and keep a rollback path

Inspect the current runtime and retain its environment. Check 1.7.0 in a
separate environment before switching your host integration. Before publication,
use the local-wheel route below. After publication, choose an unused path for
the index installation:

```sh
python3.12 -m venv .venv-harness-170
.venv-harness-170/bin/python -m pip install 'attune-harness==1.7.0'
.venv-harness-170/bin/python -c "from importlib.metadata import version; print(version('attune-harness'))"
.venv-harness-170/bin/python -m attune_harness
```

On Windows, use `py -3.12 -m venv .venv-harness-170` and
`.venv-harness-170\Scripts\python.exe` for each Python command. Expect version
`1.7.0` and a JSON receipt with a verified arithmetic result. Check the workflow
you need before switching a working installation. A pinned `uv tool upgrade`
respects its existing version pin; select 1.7.0 explicitly
when updating the managed tool.

Keep the old runtime and its original participant registry for rollback.
Version 1.5.1 retains its Python 3.10 minimum and rejects the new command
`environment` field. To roll back, select that retained runtime and its original
registry. Preserve saved tasks, approval records, memory sources, writers, hooks
and Redis data. See the [migration guide](migration.md) before replacing an
existing memory or host path.

## Select a candidate without replacing a working runtime

Before publication, obtain the exact reviewed 1.7.0 wheel path, source commit
and SHA-256 from the release owner. Verify the hash and choose a new Python 3.12
environment. Replace the example wheel path with the supplied absolute path:

```sh
python3.12 -m venv .venv-harness-170-candidate
.venv-harness-170-candidate/bin/python -m pip install '/absolute/path/attune_harness-1.7.0-py3-none-any.whl'
.venv-harness-170-candidate/bin/python -c "from importlib.metadata import version; print(version('attune-harness'))"
.venv-harness-170-candidate/bin/python -m attune_harness
```

On Windows, use `py -3.12 -m venv .venv-harness-170-candidate` and that
environment's `Scripts\python.exe` for each Python command. Expect metadata
`1.7.0` and the deterministic verified arithmetic receipt. These checks do not
qualify a workflow or provider account. For **`openai-plan`**, instead select the
required CPython 3.12.2 interpreter on macOS arm64 and install the explicit
`plan-oauth` extra as described in [participant funding](participant-funding.md).

An older wheel remains identified by its original version and source. After
publication, explicitly select `attune-harness==1.7.0` in a separate environment,
then compare both published distribution identities with that release's verified
publication evidence.

Keep the old runtime and original participant registry as the rollback path.
Use that runtime to inspect its older tasks. Do not edit approvals, copy a new
registry over the old one, delete Redis keys or assume reinstalling an older
package reverses effects or migrates saved work. See [migration and rollback](migration.md).
