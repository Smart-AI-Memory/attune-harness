# Attune Harness

**Run agent tasks, check the results independently, and keep the evidence.**

Attune Harness checks work from AI agents, commands, or your own code against
criteria you supply. Each run returns a receipt with the output, check result,
and any errors.

In a JSONL exporter experiment, checks through the real command line caught
three defects that serializer-only tests missed.
[Read the experiment and its limits](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/plan-build-native-results.md).
For a small working example, see [how checks and receipts work](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/cli-guide.md#checks-and-receipts).

**1.3.0 · `plan` and `fix` start from a command.** The v1 compatibility contract is in effect;
experimental features and platform limits are listed below. [Release notes](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/release-notes-1.3.0.md).
[Qualification status](#what-is-qualified-and-what-is-not).

[Install Attune Harness](#installation) · [User guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/cli-guide.md)

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
applies the effects, and checks fixed in advance decide the outcome. `fix` is the
clearest example: it freezes an acceptance probe before the worker starts, applies
the worker's proposed replacement itself, and keeps the failed-before and
passed-after probe evidence. A saved task can be inspected with `status` and
continued with `resume`; completed operations replay from saved evidence instead of
running again.

Reaching outside the process takes explicit permission. External command
participants need `--allow-external`, and native model participants also need
`--allow-native`. **Approving a plan does not authorize paid calls.**

Many of these commands are there for the agent and its integrations to call.
Learning their syntax is not the price of entry, and `attune-harness COMMAND --help`
covers direct use. Full usage, exit codes and recovery controls are in the
[CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/cli-guide.md).

## Use Harness with Codex, Claude, or other models

This repository includes an [Attune Harness skill](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/.agents/skills/attune-harness/SKILL.md)
for the existing `plan`, `build`, `review`, `fix`, `test`, `status` and `resume`
workflows. Invoke `$attune-harness` and describe the task; the agent prepares the
CLI inputs and reports the saved evidence. It preserves the workflow's scope and
execution permissions. The older `/attune` command belongs to Attune AI.

For an **Attune Harness** entry in Codex Plugins, use the
[plugin packaging and installation guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/codex-plugin.md). You can also use
[standalone skill discovery](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/cli-guide.md#codex-skill) in this checkout or
another project. Installing the Python package alone installs neither integration.

In **Claude Code**, add this repository as a plugin marketplace, then install the
plugin. It carries the Harness skill plus `cross-review` and `smart-test`, and
it calls the `attune-harness` command installed above:

```text
/plugin marketplace add Smart-AI-Memory/attune-harness
/plugin install attune-harness@attune-harness
```

Claude Code does not read the `.agents/skills/` folder that Codex discovers, so
this plugin is how the skill reaches it. Installing the plugin authorizes no
paid calls.

## Installation

```sh
pipx install 'attune-harness[all]==1.3.0'
```

or `uv tool install 'attune-harness[all]==1.3.0'`, or `pip install 'attune-harness[all]==1.3.0'`
into an environment of its own. This is the recommended install: everything the
review, test, MCP and acceptance journeys need, plus Redis and Voyage retrieval.
Python 3.10 or later. The [worked example](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/cli-guide.md#checks-and-receipts) needs no API key or attune-ai installation;
Voyage retrieval needs a Voyage API key and makes paid calls.
Harness and attune-ai cannot share one environment:
they pin different lines of the MCP SDK, and installing Harness over attune-ai
replaces attune-ai's; an isolated install avoids that, and `mcp-serve` says so
if it finds the two side by side.

### What the install carries

| You want | Install |
| --- | --- |
| **Recommended:** the base package plus the Redis reader and Voyage retrieval. The experimental extra below stays explicit | `pip install 'attune-harness[all]==1.3.0'` |
| The contracts and CLI; the evidence-review, test, acceptance and MCP journeys: forms (`attune-forms` 0.17.0), document claim verification (`attune-verify` 0.6.0), local Markdown retrieval with source hashes (`attune-rag` 1.2.0), MCP stdio serving (`mcp` 2.2.0) and token counting (`tiktoken` 0.12.0). No model calls | `pip install 'attune-harness==1.3.0'` |
| Read the Redis memory a hydration keeps warm: the recall digest, related nodes, one record, full-text search over the index (`redis` 5.3.1); read-only, the `text` body of a file, lesson or rule pointer is never served; needs a reachable Redis Stack with the hydration's index and function library. Also the Redis backend for working memory (`memory scratch`), shared across processes and machines; the file backend is in the base | `pip install 'attune-harness[redis]==1.3.0'` |
| Repository-first retrieval on Voyage embeddings. Needs a Voyage API key, makes paid calls | `pip install 'attune-harness[voyage]==1.3.0'` |
| Experimental: memory proposals from a Claude model over a pinned, data-only Anthropic API transport (`anthropic` 1.6.0, `httpx2` 2.13.0). POSIX only, needs `ANTHROPIC_API_KEY`, makes paid calls | `pip install 'attune-harness[memory-native]==1.3.0'` |

Before 0.4.0 the base had no dependencies and `verify`, `rag`, `review`, `mcp`
and `tokens` were extras; they were empty from 0.4.0 and are gone since 0.6.0,
so an install that still names one gets pip's warning that the extra does not
exist and the base install; drop the bracket.
Every dependency is pinned exactly and loaded on first use, so a wheel installed
without its dependencies still returns an actionable unavailable report for each
missing piece instead of a traceback. Keep the quotes around an extra: zsh and
bash treat square brackets as glob characters.

## Your first five minutes

From a Git project with an uncommitted change and a virtual environment that
has pytest, after the install above:

<!-- journey: first-run -->
```sh
cd your-project
attune-harness init
attune-harness test --project . --scope src/example.py --interpreter .venv/bin/python --task-dir ../test-task --format markdown
attune-harness review --goal "Check README.md against project evidence" --intake-only
```

`init` writes a `participants.json` with two offline demo participants. `test`
previews exactly which tests it will run for your change and saves that plan;
accept it with the checkpoint it prints to run them. `review` shows the intake
form for an evidence review: the document, its evidence and who assesses it.
Nothing here calls a model. CI runs these commands, as written, on every
platform job.

## What is qualified and what is not

I would rather you find the limits here than in your own checkout. Green software
tests and model quality are different claims, and this project keeps them apart.

| Area | Qualified | Not qualified |
| --- | --- | --- |
| Platforms | CI builds and installs the wheel on macOS, Ubuntu and Windows with Python 3.10 and 3.12, and exercises timeouts, cancellation, bounded output, crash-released locks and recovery ([guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/qualification.md)) | Other Python versions are outside the matrix. On Windows, a process that holds a run's `record.json` open for more than about two seconds still fails that run closed |
| Models | CI calls no model provider. Native Claude and Codex adapters have recorded comparisons | Native planning and building are experimental. In the September 18, 2026 comparison the original reply contract accepted 1 of 24 replies; after the contract was corrected it accepted 12 of 12. Two repetitions per role do not establish a reliability rate |
| `fix` and `test` | Local POSIX Git checkouts, regular files, default pytest discovery | File creation, deletion and renames, linked worktrees, custom pytest collectors, committed revision ranges |
| `fix` on Windows | Nothing yet. New in 0.2.0 and experimental: `fix` runs on a fixed local NTFS volume instead of refusing, and its native tests pass in CI on windows-2022 and windows-2025 ([design note](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/design-windows-effect-backend.md)) | Everything beyond those tests: deletion and renames, files with their own ACL or nonstandard attributes, files over 64 KiB, crash recovery, concurrent writers, power-loss durability, and any run against a real project. `test` on Windows is unchanged and unqualified |
| Isolation | Commands and probes run as supervised processes with deadlines and bounded output | **This is not a security sandbox.** Use a dedicated checkout and commands you trust |
| Receipts | Receipts retain the task, output and check evidence locally | They are local values, not signed attestations. Constructing a `Receipt` directly certifies nothing |
| Plan acceptance | Core imports, help and the library run standalone. `plan --accept` runs from the base install with no Attune AI; CI exercises its gate with Attune AI blocked | Acceptance through a live MCP host; CI submits the console approval |
| Protocols | MCP (2025-11-25 and 2026-07-28 profiles) and A2A 1.0 have local independent-client receipts | Remote authentication and automatic host installation |
| Signed Python plugins (1.0.0rc1) | The declared cooperating-plugin profile checks signatures and revocation, effective grants, import closure, bounded subprocesses and host-owned journals. The installed-wheel tests passed on macOS, Ubuntu and Windows with Python 3.10 and 3.12 ([qualification](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/qualification.md)). | This is not an OS sandbox for hostile same-user code. An explicitly accepted artifact receives only its accepted effective grants; paid dispatch needs separate authority. Installation does not authorize execution. Arbitrary plugins, remote authentication and automatic installation are not qualified |
| Voyage plugin path (1.0.0rc1) | One fixed public-corpus query completed eight live stages total across two paths (four matching request/result pairs). The direct SDK and signed-plugin paths produced identical normalized requests/results and five ranked sources. Offline replay of recorded results and a synthetic interrupted stage passed in the six installed-wheel jobs ([recorded fixture](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/tests/fixtures/voyage-live-recorded/README.md)). | This does not establish general ranking or model quality, capture raw HTTP responses, or imply a live provider call on every platform. A dispatched stage with unknown effects is not retried automatically |
| Memory | `memory recall`, `resolve` and `refresh` read explicit `raw`, `personal` and `curated` roots with Harness's own reader, nothing from attune-ai on the path; the raw tier needs only the standard library and the document tiers attune-rag from the base install; CI reads a raw root from the installed wheel on every POSIX platform job and from the `--no-deps` release gate, and the document tiers where attune-rag is installed; the Windows jobs record the reader's refusal. The [legacy formats](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/specs/native-memory/formats.md) are frozen as read; `native` is the only reader. With the `redis` extra, `memory redis` reads a hydrated Redis Stack keyspace: digest, related, node and search, as evidence packets; a pointer's `text` body is never served, a curated node's own record is. `memory serve` checks active curated membership before printing the digest, includes source and untrusted-evidence framing, and exits 0 whether or not Redis answers. `serve --for PROMPT` searches prompt terms and suppresses file pointers with a `wrong` verdict or without an authorized verdict scope; a UserPromptSubmit bridge is documented in the CLI guide. `memory scratch` is working memory, bounded JSON under short keys with an optional time to live: a file store in the base that declares no sharing, or the Redis store with the extra; the backend is chosen at startup and an unreachable Redis is never replaced by the file store. CI exercises the extra absent and the extra present with no server on all three platforms; the path against a hydrated server passed once on a maintainer's machine on 2026-09-22 and runs only where `ATTUNE_TEST_REDIS_URL` is set | The native reader is POSIX-only: on Windows it reports the refusal instead of reading, until the Phase 4 decision. The immutable native format fixture pins the compatibility contract. The `memory-native` extra ships in the wheel but is experimental and not activated for live memories. The native transport is POSIX only, accepts two exact model IDs, refuses any other SDK version, and is never exercised in CI |
| Roadmap | | `ship` and `reflect` are planned routes and do not exist yet |

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

The [migration guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/migration-from-attune-ai.md) lists each
journey, its current boundary and what to keep using while a successor is qualified.

## Links

- [Qualification guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/qualification.md)
- [CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/cli-guide.md)
- [Portable contract](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/portable-contract.md)
- [Repository](https://github.com/Smart-AI-Memory/attune-harness) and
  [issues](https://github.com/Smart-AI-Memory/attune-harness/issues)

**Apache License 2.0.**

Built by Patrick Roebuck, working with Codex and Claude.

## Graphical companion status

GUI delivery is deferred to 1.4.0. The 1.3.0 module launcher and imported server
refuse before task, listener or browser effects. Experimental GUI code/assets
remain packaged but unavailable; CLI owners and static task snapshots remain
available. M2/M3/M4 and human acceptance gates still govern future GUI delivery.
See the [release notes](https://github.com/Smart-AI-Memory/attune-harness/blob/v1.3.0/docs/release-notes-1.3.0.md).
