# Attune Harness

**Turn a goal into a plan, put agents to work, and check the results.**

Use Harness with your assistant in Codex or Claude Code to plan a change,
review a document, repair files, run tests or return to saved work. Describe
what you want to accomplish. Your assistant helps prepare the work, presents
what needs your review and uses Harness to carry out the steps you authorize.

Harness keeps a **receipt**: the output, check results and any errors from a run.
You can inspect what happened and use that record when you continue later.

**Harness 1.6.0 · Python 3.12 or later**

This README describes version 1.6.0. Check the
[package index](https://pypi.org/project/attune-harness/) for publication status.
Versioned source links resolve when the `v1.6.0` tag is available; the existing
Help Center retains its published version labels.

[Install](#installation) · [Connect your assistant](#use-harness-with-codex-claude-or-other-models) · [Choose a task](#choose-your-first-task) · [Help Center](#help-center)

Updated on October 30, 2026.

## What changes in 1.6.0

- **Keep work moving on Windows.** Use the supported build, repair and testing
  workflows, with clearer saved recovery guidance when child-process shutdown
  cannot be confirmed. Bounded retries for brief record-access denials remain
  available; persistent errors are reported.
- **Choose which credentials your commands receive.** Enable
  [environment filtering](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.6.0/docs/command-environments.md)
  for a command participant, then give it the API key it needs while leaving
  unrelated credentials out of its environment.
- **See which memory snapshot supplied your results.** The new optional memory
  reader includes snapshot and source identifiers with its results, helping you
  trace the information it retrieved.
- **Get from installation to your first result.** The guides explain how to set
  up Harness, check that it works, and return to your previous setup if needed.
  Older instructions are clearly labeled.

<a id="plan-build-review-fix-and-test"></a>

## What you can do

| Your goal | How Harness helps |
| --- | --- |
| **Plan a change** | Develop the goal, affected files, tasks and checks before implementation. |
| **Build from a plan** | Give configured agents the accepted tasks and inspect their work against the agreed checks. |
| **Review a document** | Compare its claims with your criteria and supporting sources. |
| **Repair existing files** | Check a proposed repair against a test fixed before the repair begins. |
| **Test a code change** | Preview the selected tests, then inspect their output and results. |
| **Continue saved work** | Read the saved decisions and results before choosing the next action. |

Start with the [workflow guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.6.0/docs/supported-journeys.md)
to choose a procedure and see what it needs.

## Installation

### Install 1.6.0

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if needed,
then install Harness 1.6.0 in its own managed environment. These index commands
require 1.6.0 to be published. To evaluate an unpublished candidate, use the
exact qualified local wheel supplied by the release owner and keep your working
installation.

```sh
uv tool install --python 3.12 'attune-harness==1.6.0'
uv tool list --show-paths
attune-harness --help
```

**Expected result:** The tool list shows Harness `1.6.0`, and help lists
**`init`**, **`plan`**, **`build`**, **`review`**, **`fix`**, **`test`**, **`status`**
and **`resume`**. If the command is unavailable, follow uv's instructions for
adding its executable directory to your path. These examples explicitly select
Python 3.12; Harness 1.6.0 requires Python 3.12 or later.

The Python package and your assistant's integration are separate installations.
The [installation guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.6.0/docs/installation.md)
covers pipx, virtual environments and selecting the same interpreter for module
commands. Keep a working installation while evaluating a candidate.

### Keep a working installation

Install the replacement in a separate environment before switching a working
setup. Published 1.5.1 remains a rollback option with its original Python 3.10
minimum and configuration. A private repair wheel whose metadata says `1.5.1`
is not a 1.6.0 distribution. Keep each candidate's source and wheel identities
with its qualification evidence.

### Check a local result

You can check the published package without an API key or a model call:

```sh
python3.12 -m venv .venv-harness-160
.venv-harness-160/bin/python -m pip install 'attune-harness==1.6.0'
.venv-harness-160/bin/python -c "from importlib.metadata import version; print(version('attune-harness'))"
.venv-harness-160/bin/python -m attune_harness
```

On Windows, create the environment with `py -3.12 -m venv .venv-harness-160` and
use `.venv-harness-160\Scripts\python.exe` for each Python command. Directly
selecting that executable does not require PowerShell activation-policy changes.

**Expected result:** The version is `1.6.0`. The demonstration returns a JSON
receipt with a verified arithmetic result. It uses a local worker and an
independent arithmetic check. This is a first installation check, not a claim
that every shown shell command was exercised verbatim on every platform.

## Use Harness with Codex, Claude, or other models

Once the runtime is installed, connect the assistant you use for your project.
Harness supplies workflow instructions; your host supplies the conversation
and configured model access.

### Codex

Follow the [Codex plugin guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.6.0/docs/codex-plugin.md)
to prepare and install the Harness workflow plugin. The [standalone skill guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.6.0/docs/cli-guide.md#codex-skill)
provides another setup option.

After setup, invoke `$attune-harness` and describe your goal.

### Claude Code

Add the marketplace and install the plugin:

```text
/plugin marketplace add Smart-AI-Memory/attune-harness
/plugin install attune-harness@attune-harness
```

The plugin includes Harness workflows, cross-review, roundtable and smart-test
instructions. It calls the separately installed `attune-harness` runtime.

### Other integrations and direct commands

Use the [CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.6.0/docs/cli-guide.md)
for command-based integrations, MCP setup, arguments and exit codes. Run
`attune-harness COMMAND --help` for one command or `attune-harness --help-all`
for the broader tool list.

<a id="your-first-five-minutes"></a>

## Choose your first task

Start with a small goal in a project you know. For example, ask your assistant:

> Use Harness to help me plan an update to this project. Help me define the
> goal, affected files and checks before we build.

Or:

> Use Harness to review README.md against the project sources. Show me which
> claims are supported and which need attention.

Your assistant prepares the inputs for the selected workflow. Review the proposed
scope, configured participants and checks before accepting the work. Accepting a
plan records the agreed work; starting a build is a separate action. Paid model
calls require their own permission and credentials.

You can also use the commands directly:

| Command | Purpose |
| --- | --- |
| **`init`** | Prepare starter files for a supported workflow. |
| **`plan`** | Develop a plan and accept its scope. |
| **`build`** | Execute accepted tasks and their protected checks. |
| **`review`** | Assess a document against selected evidence. |
| **`fix`** | Repair scoped existing files against a fixed check. |
| **`test`** | Test a captured change and retain the results. |
| **`status`** | Inspect saved progress and results. |
| **`resume`** | Continue authorized remaining work. |

For a hands-on example, choose a task in the [Help goals guide](https://smartaimemory.com/harness/help/goals/).
Each procedure supplies its setup, steps and expected result.

### Preview a task from the command line

In a POSIX shell, start from the parent of a Git project named `your-project`.
The project must have an existing commit, no `participants.json`, and an
uncommitted change in `src/example.py`. Its `.venv/bin/python` interpreter must
have pytest installed, and `attune-harness` must be available on your path.
The sibling directory `../test-task` must not already exist. The commands run
from the repository root after `cd`.

<!-- journey: first-run -->
```sh
cd your-project
attune-harness init
attune-harness test --project . --scope src/example.py --interpreter .venv/bin/python --task-dir ../test-task --format markdown
attune-harness review --goal "Check README.md against project evidence" --intake-only
```

**Expected result:** **`init`** writes starter participant configuration.
**`test`** previews the selected tests and saves the plan for your review;
**`review --intake-only`** prepares the review intake. These commands do not
run a model. Preview and intake-only draft commands can return exit status `1`
with their expected draft result. This example's executable journey is checked
on POSIX; it does not establish that the interpreter path works unchanged on
Windows.

## Advanced planning for Spec-Driven Development

Use a specification when the work needs more structure than a short request.
Harness connects requirements to tasks, decisions and checks.

1. **Define the intent.** Record the goal, context, affected files, constraints
   and acceptance criteria.
2. **Develop and challenge the plan.** A configured planner proposes tasks;
   a configured critic examines them against your requirements.
3. **Connect tasks to checks.** Identify what will show that each task met its
   requirements and which tasks depend on earlier work.
4. **Review and accept the scope.** Inspect the proposed work before starting
   the build. Use **`status`** to inspect saved decisions and progress.

The [plan-and-build guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.6.0/docs/cli-guide.md#plan-and-build)
explains the procedure. You can also [import a supported Markdown plan](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.6.0/docs/cli-guide.md#importing-a-plan-from-another-project)
from another project and review it before acceptance.

<a id="150-scope-full-windows-parity-deferred"></a>
<a id="windows-capabilities-and-remaining-limits"></a>

## Work on Windows

Harness includes Windows implementations for captured testing, build and repair
effects, memory-file reads, saved memory and task storage. Fixed local NTFS and
the route's other input checks still apply. If process shutdown is uncertain,
inspect the saved record and original process effects before continuing; an
error does not prove termination or rollback.

Choose a workflow in the [Windows capability table](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.6.0/docs/supported-journeys.md#windows-capabilities-and-reliability).
It explains the local NTFS setup and the process, storage and recovery conditions
that matter for each task. Check those requirements before relying on concurrent
writes, interruption recovery or power-loss durability.

The merged repair passed installed-package and full-source checks on both
Windows Server 2022 and 2025 with Python 3.12 in PR #320. Separate supplemental
coverage passed in the `windows-latest` job. Windows 11 observations
are a separate standard-user smoke on ARM hardware using x64 Python emulation;
they do not qualify native ARM64 or all desktop and PowerShell workflows.

The linked guides define supported workflows and remaining storage and recovery limits. The [Windows reliability reference](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.6.0/docs/windows-reliability.md)
provides the detailed requirements and evidence.

<a id="what-the-install-carries"></a>

## Optional integrations

Start with the base package. It includes forms, document verification, local
Markdown retrieval, testing, MCP serving and token counting. The following
package selections require the 1.6.0 distribution on your package index.

| You need | Package to select |
| --- | --- |
| Base workflows | `attune-harness==1.6.0` |
| Redis-backed memory with an existing configured service | `attune-harness[redis]==1.6.0` |
| Voyage retrieval with your API key | `attune-harness[voyage]==1.6.0` |
| Both Redis and Voyage | `attune-harness[all]==1.6.0` |

For example, to install the Redis client integration:

```sh
uv tool install --python 3.12 'attune-harness[redis]==1.6.0'
```

Keep quotes around package names containing extras. The `all` profile combines
Redis and Voyage; native-memory proposals use a separate experimental profile.
The [dependency guide](https://smartaimemory.com/harness/help/dependencies/)
lists the exact pins, service requirements and optional provider setup.
Installing an extra does not configure a service or authorize paid calls.
The existing Redis paths passed bounded disposable-service checks during 1.6.0
preparation. The [requirements and verification record](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.6.0/docs/redis-option-verification.md)
identifies the tested development wheel, operations and limits. Use qualification
evidence that identifies the exact wheel hash you install; a dependency pin or
offline check alone does not establish a successful live service operation.

### Grant one command the credential it needs

For example, a trusted command participant can declare:

```json
"environment": {"profile": "command-env-v1", "passthrough": ["SERVICE_TOKEN"]}
```

Set `SERVICE_TOKEN` in the dispatching host's environment without putting its
value in the configuration or shared logs. Use an existing absolute executable
path and the participant's normal preparation/acceptance flow. Missing named
variables refuse dispatch. The profile filters environment inheritance; it is
not an operating-system sandbox.

Legacy configurations still work. The runtime notice and deprecation register
agree on first notice in 1.6.0 and removal no earlier than 1.7.0. Legacy full
inheritance remains accepted during that compatibility window.

## Upgrade and keep a rollback path

When 1.6.0 becomes available, install it in a separate Python 3.12 environment before switching a working
setup. Keep your previous runtime, original participant configuration, saved tasks,
memory sources and writer/hook settings.

Version 1.5.1 retains its original Python 3.10 minimum and rejects the new command
`environment` field. To return to that version, select its retained runtime and
original configuration. Keep saved approvals and Redis data unchanged. Inspect older saved tasks with
their original runtime first; reinstalling an older package does not undo file
effects or prove that a newer saved task can safely resume in that version.

The [migration guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.6.0/docs/migration.md)
covers command-environment grants, memory-reader selection and retained
Attune AI setups. The v1 compatibility contract remains in effect.

<a id="harness-and-attune-ai"></a>

## Keep your existing memory setup working

Harness can read configured memory files, read an existing Redis memory index
and save memories explicitly. The optional 1.6.0 generation reader also identifies
the snapshot and source associated with its results.

Keep the writer and host hooks that maintain and deliver your existing memory.
A new Redis projection writer and RedisVL adoption are outside 1.6.0. The new reader does not
install a writer or arrange automatic recall in a fresh
session. Saving a memory and making it available for session recall are separate
steps. Follow the [memory guidance](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.6.0/docs/cli-guide.md#memory)
for the path you use.

Harness succeeds the deprecated Attune AI and runs without an Attune AI
installation. If you retain Attune AI for an existing workflow, keep it in a
separate environment: the packages require different MCP SDK versions.

<a id="graphical-companion-status"></a>

## Browser forms

Use the forms companion to answer questions in an existing task draft, save your
answers, review the request and inspect its accepted content. Ask the person or
agent running Harness for the complete private launcher link and keep the local
launcher running while using the form.

Saving answers, approving a request and opening a saved form do not execute
work. Browser build dispatch and execution resume are unavailable in this
implementation; use the supported CLI workflow after inspecting its saved scope. Follow the [forms guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.6.0/docs/supported-journeys.md#inspect-and-recover)
for setup and available controls.

<a id="what-is-qualified-and-what-is-not"></a>
<a id="evidence-and-reliability"></a>

## Understand the results

Read the receipt to see the output, check results and errors. For a document
review, distinguish the source checks from the model's judgments. For a repair
or build, inspect the agreed checks and their results before deciding what to do
next.

Use **`status`** before continuing saved work. If an operation was interrupted
or its effects are uncertain, inspect the recovery guidance before trying it
again. Trusted commands should run in a dedicated checkout; process supervision
is not an operating-system sandbox.

The [published 1.5.1 release record](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.5.1)
identifies that version's source and distributions. Final 1.6.0 artifacts and
release evidence remain a separate release gate. The [qualification guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.6.0/docs/qualification.md)
explains what the software checks cover.

<a id="links"></a>

## Help Center

For the published package, start with [Get started with Harness 1.5.1](https://smartaimemory.com/harness/help/1-5-1/),
then choose a task in the [goals guide](https://smartaimemory.com/harness/help/goals/).
The guides explain setup, steps and expected results. Their published version
and historical records remain unchanged during 1.6.0 preparation; no new
1.6.0 Help route is claimed here.

The [documentation archive](https://smartaimemory.com/harness/help/archive/)
keeps earlier guides, release records and screenshots under their original
version labels. Use those labels to distinguish historical observations from
current instructions.

[Repository](https://github.com/Smart-AI-Memory/attune-harness) · [Issues](https://github.com/Smart-AI-Memory/attune-harness/issues) · [CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.6.0/docs/cli-guide.md)

**Apache License 2.0.**

Built by Patrick Roebuck, working with Codex and Claude.

Contact: [patrick.roebuck@smartaimemory.com](mailto:patrick.roebuck@smartaimemory.com).
