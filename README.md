# Attune Harness

Updated on October 22, 2026.

**Run agent tasks, check the results independently, and keep the evidence.**

Attune Harness checks work from AI agents, commands, or your own code against
criteria you supply. Each run returns a receipt with the output, check result,
and any errors.

For a small working example, see [checks and receipts](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/cli-guide.md#checks-and-receipts).

**Current release: [1.5.0](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.5.0)** · [PyPI package](https://pypi.org/project/attune-harness/1.5.0/)

**Next release: 1.5.1 (in preparation).** The planned maintenance release improves
plugin signature validation and makes completed document-assessment evidence
easier to inspect. Read the [draft release notes](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/release-notes-1.5.1.md)
and [readiness record](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/release-readiness-1.5.1.md) for the changes and
remaining checks. The installation commands below select published 1.5.0.

The v1 compatibility contract remains in effect.

[Install](#installation) · [Help Center](https://smartaimemory.com/harness/help/) ·
[Spec-Driven Development](#advanced-planning-for-spec-driven-development) ·
[User guide](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/supported-journeys.md) ·
[1.5.0 release notes](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.5.0/docs/release-notes-1.5.0.md)

## Help Center

The [Harness Help Center](https://smartaimemory.com/harness/help/) brings together
step-by-step guides, expected results, troubleshooting and command references.
Harness owns the [Help Center source and static build](https://github.com/Smart-AI-Memory/attune-harness/blob/main/help/README.md). Its
1.5.0 guides and portable export are maintained here; the existing public site
will switch to that export in a separate website change.
Start with [Get started with Harness 1.5.0](https://smartaimemory.com/harness/help/1-5-0/)
to install the release and check a local result. Use
[AI tools and integrations](https://smartaimemory.com/harness/help/ai-tools-and-integrations/)
to find commands by task, follow their order and understand where approval is
needed.

For hands-on practice, choose a
[walkthrough](https://github.com/Smart-AI-Memory/attune-harness/blob/77d5b2b4fe9f3c6285a5b535f4e735103f7e192d/docs/tutorials-1.5.0-candidate.md#choose-a-walkthrough).
Each records its tested setup, steps and expected result; use that setup for its
examples.

## Advanced planning for Spec-Driven Development

Harness connects requirements, planning, scoped implementation and verification.
Use **`plan`** to develop the work contract, then **`build`** to execute accepted work.

- **Define the intent.** Record the goal, context, file scope, constraints and
  acceptance criteria. Harness selects plain-prompt, XML or specification-backed
  authoring from explicit work requirements.
- **Develop and challenge the plan.** A configured planner proposes tasks; a
  configured critic examines the proposal against its requirements before you
  stage and accept it.
- **Connect requirements to tasks.** Map acceptance criteria to dependent tasks
  and their checks. Import supported Markdown plans with a receipt that records
  the conversion; importing a plan does not carry over approval.
- **Approve a precise scope.** Accept the exact checkpoint before building, with
  protected verification commands fixed in advance. Inspect saved decisions,
  progress and evidence with **`status`**, and continue saved work with **`resume`**.

See [Plan and build](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/cli-guide.md#plan-and-build)
for the workflow and
[plan imports](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/cli-guide.md#importing-a-plan-from-another-project)
for bringing an existing specification into Harness.

<a id="150-scope-full-windows-parity-deferred"></a>

## Windows capabilities in 1.5.0

Windows includes captured test execution, native file-memory reads, saved memory
and task storage, and experimental native-memory transport. Use the
[capability and reliability table](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/supported-journeys.md#windows-capabilities-and-reliability)
to check the available functionality and process-completion, storage and recovery
requirements for your workflow.

## Plan, build, review, fix, and test

```text
attune-harness --help

Getting started
  init         Write a starter participant registry

Task execution
  plan         Define intent and accept its scope
  build        Execute accepted tasks and protected checks
  review       Assess a document against project evidence
  fix          Repair scoped files and check the result
  test         Test a captured change and retain the evidence

Task controls
  status       Inspect a saved task
  resume       Continue a saved task

AI tools and integration
  --help-all   Browse operational tools and compatibility commands
```

Every verb follows one pattern. You accept a scope before anything runs, the host
applies the effects, and checks fixed in advance decide the outcome. **`fix`** is the
clearest example: it freezes an acceptance probe before the worker starts, applies
the worker's proposed replacement itself, and keeps the failed-before and
passed-after probe evidence. A saved task can be inspected with **`status`** and
continued with **`resume`**; completed operations replay from saved evidence instead of
running again.

Reaching outside the process takes explicit permission. External command
participants need `--allow-external`, and native model participants also need
`--allow-native`. **Approving a plan does not authorize paid calls.**

> [!NOTE]
> Many of these commands are there for the agent and its integrations to call.
> Learning their syntax is not the price of entry, and `attune-harness COMMAND --help`
> covers direct use. Full usage, exit codes and recovery controls are in the
> [CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/cli-guide.md).

## Use Harness with Codex, Claude, or other models

This repository includes an [Attune Harness skill](https://github.com/Smart-AI-Memory/attune-harness/blob/ca55b3aa39c0b8e003c0523244db9da14f901d23/.agents/skills/attune-harness/SKILL.md)
for the existing **`plan`**, **`build`**, **`review`**, **`fix`**, **`test`**, **`status`** and **`resume`**
workflows. Invoke `$attune-harness` and describe the task; the agent prepares the
CLI inputs and reports the saved evidence. It preserves the workflow's scope and
execution permissions. The older `/attune` command belongs to Attune AI.

For an **Attune Harness** entry in Codex Plugins, use the
[plugin packaging and installation guide](https://github.com/Smart-AI-Memory/attune-harness/blob/ca55b3aa39c0b8e003c0523244db9da14f901d23/docs/codex-plugin.md). You can also use
[standalone skill discovery](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/cli-guide.md#codex-skill) in this checkout or
another project. Installing the Python package alone installs neither integration.

In **Claude Code**, add this repository as a plugin marketplace, then install the
plugin. It carries the Harness skill plus `cross-review`, `roundtable` and
`smart-test`, and
it calls the `attune-harness` command installed above:

```text
/plugin marketplace add Smart-AI-Memory/attune-harness
/plugin install attune-harness@attune-harness
```

Claude Code does not read the `.agents/skills/` folder that Codex discovers, so
this plugin is how the skill reaches it. Installing the plugin authorizes no
paid calls.

## Installation

Install the current release in an isolated tool environment:

```sh
uv tool install 'attune-harness==1.5.0'
```

uv keeps Harness and its dependencies isolated and provides the `attune-harness`
command. The base includes forms, verification, local retrieval, review, test,
MCP and acceptance dependencies. Add Redis or Voyage when needed; `all` includes
both. Inspect the selected tool and check that its command is available:

```sh
uv tool list --show-paths
attune-harness --help
```

If Harness is already installed, inspect its version and path before selecting
1.5.0 explicitly. Preserve saved task directories and retained evidence
environments; changing the tool version does not qualify saved-work migration.
The [installation guide](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/installation.md)
covers environment selection and agent setup for 1.5.0.

Python 3.10 or later. The [worked example](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/cli-guide.md#checks-and-receipts) needs no API key or attune-ai installation;
Voyage retrieval needs a Voyage API key and makes paid calls.
Harness and attune-ai cannot share one environment:
they pin different lines of the MCP SDK, and installing Harness over attune-ai
replaces attune-ai's; an isolated install avoids that, and **`mcp-serve`** says so
if it finds the two side by side.

### What the install carries

| You want | Install |
| --- | --- |
| **Recommended base:** the contracts and CLI; the evidence-review, test, acceptance and MCP journeys: forms (`attune-forms` 0.17.0), document claim verification (`attune-verify` 0.6.0), local Markdown retrieval with source hashes (`attune-rag` 1.2.0), MCP stdio serving (`mcp` 2.2.0) and token counting (`tiktoken` 0.12.0). No model calls | `pip install 'attune-harness==1.5.0'` |
| Read the Redis memory a hydration keeps warm: the recall digest, related nodes, one record, full-text search over the index (`redis` 5.3.1); read-only, the `text` body of a file, lesson or rule pointer is never served; needs a reachable Redis Stack with the hydration's index and function library. Also the Redis backend for working memory (`memory scratch`), shared across processes and machines; the file backend is in the base | `pip install 'attune-harness[redis]==1.5.0'` |
| Repository-first retrieval on Voyage embeddings. Needs a Voyage API key, makes paid calls | `pip install 'attune-harness[voyage]==1.5.0'` |
| The base plus both Redis and Voyage; experimental native memory stays separate | `pip install 'attune-harness[all]==1.5.0'` |
| Experimental: memory proposals from a Claude model over a pinned, data-only Anthropic API transport (`anthropic` 1.6.0, `httpx2` 2.13.0). Needs `ANTHROPIC_API_KEY` and separate paid-call authority; live native-memory acceptance remains open | `pip install 'attune-harness[memory-native]==1.5.0'` |

Every dependency is pinned exactly and loaded on first use, so a wheel installed
without its dependencies still returns an actionable unavailable report for each
missing piece instead of a traceback. Keep the quotes around an extra: zsh and
bash treat square brackets as glob characters.

## Your first five minutes

Follow [Get started with Harness 1.5.0](https://smartaimemory.com/harness/help/1-5-0/)
for installation and a local check. Then use the
[user guide](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/supported-journeys.md)
to choose a workflow. For a practice form, ask the person or agent running
Harness for its complete private link and keep the local launcher running.

For a quick preview in a project you have already prepared:

From a Git project with an uncommitted change and a virtual environment that
has pytest, after the install above:

<!-- journey: first-run -->
```sh
cd your-project
attune-harness init
attune-harness test --project . --scope src/example.py --interpreter .venv/bin/python --task-dir ../test-task --format markdown
attune-harness review --goal "Check README.md against project evidence" --intake-only
```

**`init`** writes a `participants.json` with two offline demo participants. **`test`**
previews exactly which tests it will run for your change and saves that plan;
accept it with the checkpoint it prints to run them. **`review`** shows the intake
form for an evidence review: the document, its evidence and who assesses it.
Nothing here calls a model. CI runs these commands, as written, on every
platform job.

For a consultation, use `init --for roundtable --question "Review the selected source"`
with an explicit `--model claude=YOUR_CLAUDE_MODEL_ID` and
`--model codex=YOUR_CODEX_MODEL_ID`. It writes `roundtable.json`, reports local
seat preflight and prints the next prepare command. See the
[roundtable starter and participant mapping](https://github.com/Smart-AI-Memory/attune-harness/blob/ca55b3aa39c0b8e003c0523244db9da14f901d23/docs/model-consultation.md#initialize-a-roundtable).

<a id="what-is-qualified-and-what-is-not"></a>

## Evidence and reliability

Use these records to check your installation and workflow:

- [1.5.0 release record](https://github.com/Smart-AI-Memory/attune-harness/releases/tag/v1.5.0): published source, wheel and source archive hashes, and installed-package checks.
- [Supported journeys](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/supported-journeys.md): available workflows, evidence and reliability requirements.
- [Qualification guide](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/qualification.md): the CI matrix and installed-wheel procedure.

Software checks establish the behavior they exercise; model quality and live
provider acceptance require their own evidence. Receipts retain local task,
output and check evidence; they are not signed attestations. Run trusted
commands in a dedicated checkout: process supervision is not a security sandbox.

## Harness and attune-ai

Harness is the successor I am building to
[attune-ai](https://pypi.org/project/attune-ai/). It starts from a constraint
attune-ai never had: it runs with no provider SDK and no attune-ai installation.
The Attune libraries it does use, forms, claim verification and local retrieval,
are part of the install, pinned exactly, and each loads only when the command that
needs it runs. Installing an extra does not call a model; invoking a paid
provider path requires separate permission and credentials.

Harness can read and save memory through its documented paths. Attune AI still
provides the hydrate writer and broader Claude Code and multi-agent workflows;
Harness does not replace those today. If you need them, keep attune-ai in its
own environment: the two pin different lines of the MCP SDK and cannot share one.

Use the [workflow guide](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/supported-journeys.md)
to choose a Harness entry point and check its requirements before replacing an
existing Attune AI workflow.

## Links

- [Installation guide](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/installation.md)
- [CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/cli-guide.md)
- [Portable contract](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/portable-contract.md)
- [Repository](https://github.com/Smart-AI-Memory/attune-harness) and
  [issues](https://github.com/Smart-AI-Memory/attune-harness/issues)

**Apache License 2.0.**

Built by Patrick Roebuck, working with Codex and Claude.

<a id="graphical-companion-status"></a>

## Browser forms

Open a registered draft, save answers, approve a request and inspect its accepted
content through the forms companion. Saving and approving a request do not
execute work. Launch it with the selected Harness interpreter and keep its
local server running. See the [forms workflow](https://github.com/Smart-AI-Memory/attune-harness/blob/main/docs/supported-journeys.md#inspect-and-recover)
for setup and the available controls.
