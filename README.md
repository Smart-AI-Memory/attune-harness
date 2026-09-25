# Attune Harness

**Run an agent's work, check it independently, and keep a receipt of which happened.**

> **Status: 0.6.0, alpha.** Interfaces, configuration formats and CLI commands may
> change before 1.0. What is and is not qualified is
> [listed below](#what-is-qualified-and-what-is-not), not implied.

On September 18, 2026 I ran twelve model-written implementations of a small JSONL
exporter through Harness. Nine behaved correctly under the full check. The other three passed when their serializer
was tested directly, and failed when run through the real command line, which is the
only way anyone would ever use them
([results](https://github.com/Smart-AI-Memory/attune-harness/blob/v0.6.0/docs/plan-build-native-results.md)).

That gap is what Harness is for. A participant produces output: a model, a command,
or your own code. A check you supply, separate from the participant, decides whether
the output counts. You get back a receipt that says which. The participant's account
of its own work is recorded. It is never the evidence.

## A wrong answer comes back rejected

```sh
pipx install attune-harness
```

or `uv tool install attune-harness`, or `pip install attune-harness` into an
environment of its own. That installs everything the review, test, MCP and
acceptance journeys need. Python 3.10 or later. No provider SDK, no API key, and
no attune-ai installation. Harness and attune-ai cannot share one environment:
they pin different lines of the MCP SDK, and installing Harness over attune-ai
replaces attune-ai's; an isolated install avoids that, and `mcp-serve` says so
if it finds the two side by side.

```python
from attune_harness import Check, Output, Task, run

class Worker:
    def run(self, task: Task) -> Output:
        return Output("4")

receipt = run(
    Task("addition", "Compute 2 + 2", ("Return the integer result",)),
    "example-worker",
    Worker(),
    lambda task, output: Check(output.text == "4", "Compared with independent arithmetic"),
)
print(receipt.status.value)  # verified
```

Change the worker to return `"5"` and the same call returns `rejected`, with the
output and the check's evidence still attached. If the participant or the check
raises, the status is `failed` and the receipt names the stage and the error. `run`
executes once. It never retries on its own.

`python -m attune_harness` runs the installed demonstration and prints a JSON receipt.

## The CLI applies the same contract to larger work

```text
attune-harness --help

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
[CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v0.6.0/docs/cli-guide.md).

## Use Attune Harness in Codex

This repository includes an [Attune Harness skill](.agents/skills/attune-harness/SKILL.md)
for the existing `plan`, `build`, `review`, `fix`, `test`, `status` and `resume`
workflows. Invoke `$attune-harness` and describe the task; the agent prepares the
CLI inputs and reports the saved evidence. It preserves the workflow's scope and
execution permissions. The older `/attune` command belongs to Attune AI.

For an **Attune Harness** entry in Codex Plugins, use the
[plugin packaging and installation guide](docs/codex-plugin.md). You can also use
[standalone skill discovery](docs/cli-guide.md#codex-skill) in this checkout or
another project. Installing the Python package alone installs neither integration.

## What the install carries

| You want | Install |
| --- | --- |
| The contracts and CLI; the evidence-review, test, acceptance and MCP journeys: forms (`attune-forms` 0.17.0), document claim verification (`attune-verify` 0.6.0), local Markdown retrieval with source hashes (`attune-rag` 1.2.0), MCP stdio serving (`mcp` 2.2.0) and token counting (`tiktoken` 0.12.0). No model calls | `pip install attune-harness` |
| Read the Redis memory a hydration keeps warm: the recall digest, related nodes, one record, full-text search over the index (`redis` 5.3.1); read-only, the `text` body of a file, lesson or rule pointer is never served; needs a reachable Redis Stack with the hydration's index and function library. Also the Redis backend for working memory (`memory scratch`), shared across processes and machines; the file backend is in the base | `pip install 'attune-harness[redis]'` |
| Repository-first retrieval on Voyage embeddings. Needs a Voyage API key, makes paid calls | `pip install 'attune-harness[voyage]'` |
| Both of the above in one word: the Redis reader and Voyage retrieval. The experimental extra below stays explicit | `pip install 'attune-harness[all]'` |
| Experimental: memory proposals from a Claude model over a pinned, data-only Anthropic API transport (`anthropic` 1.6.0, `httpx2` 2.13.0). POSIX only, needs `ANTHROPIC_API_KEY`, makes paid calls | `pip install 'attune-harness[memory-native]'` |

Before 0.4.0 the base had no dependencies and `verify`, `rag`, `review`, `mcp`
and `tokens` were extras; they were empty from 0.4.0 and are gone since 0.6.0,
so an install that still names one gets pip's warning that the extra does not
exist and the base install; drop the bracket.
Every dependency is pinned exactly and loaded on first use, so a wheel installed
without its dependencies still returns an actionable unavailable report for each
missing piece instead of a traceback. Keep the quotes around an extra: zsh and
bash treat square brackets as glob characters.

## What is qualified and what is not

I would rather you find the limits here than in your own checkout. Green software
tests and model quality are different claims, and this project keeps them apart.

| Area | Qualified | Not qualified |
| --- | --- | --- |
| Platforms | CI builds and installs the wheel on macOS, Ubuntu and Windows with Python 3.10 and 3.12, and exercises timeouts, cancellation, bounded output, crash-released locks and recovery ([guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v0.6.0/docs/qualification.md)) | Other Python versions are outside the matrix. On Windows, a process that holds a run's `record.json` open for more than about two seconds still fails that run closed |
| Models | CI calls no model provider. Native Claude and Codex adapters have recorded comparisons | Native planning and building are experimental. In the September 18, 2026 comparison the original reply contract accepted 1 of 24 replies; after the contract was corrected it accepted 12 of 12. Two repetitions per role do not establish a reliability rate |
| `fix` and `test` | Local POSIX Git checkouts, regular files, default pytest discovery | File creation, deletion and renames, linked worktrees, custom pytest collectors, committed revision ranges |
| `fix` on Windows | Nothing yet. New in 0.2.0 and experimental: `fix` runs on a fixed local NTFS volume instead of refusing, and its native tests pass in CI on windows-2022 and windows-2025 ([design note](https://github.com/Smart-AI-Memory/attune-harness/blob/v0.6.0/docs/design-windows-effect-backend.md)) | Everything beyond those tests: deletion and renames, files with their own ACL or nonstandard attributes, files over 64 KiB, crash recovery, concurrent writers, power-loss durability, and any run against a real project. `test` on Windows is unchanged and unqualified |
| Isolation | Commands and probes run as supervised processes with deadlines and bounded output | **This is not a security sandbox.** Use a dedicated checkout and commands you trust |
| Receipts | Receipts retain the task, output and check evidence locally | They are local values, not signed attestations. Constructing a `Receipt` directly certifies nothing |
| Plan acceptance | Core imports, help and the library run standalone. `plan --accept` runs from the base install with no Attune AI; CI exercises its gate with Attune AI blocked | Acceptance through a live MCP host; CI submits the console approval |
| Protocols | MCP (2025-11-25 and 2026-07-28 profiles) and A2A 1.0 have local independent-client receipts | Remote authentication, arbitrary executable plugins and automatic host installation |
| Memory | `memory recall`, `resolve` and `refresh` read explicit `raw`, `personal` and `curated` roots with Harness's own reader, nothing from attune-ai on the path; the raw tier needs only the standard library and the document tiers attune-rag from the base install; CI reads a raw root from the installed wheel on every POSIX platform job and from the `--no-deps` release gate, and the document tiers where attune-rag is installed; the Windows jobs record the reader's refusal. attune-ai's adapter stays selectable with `"reader": "adapter"` until the transition ends. With the `redis` extra, `memory redis` reads a hydrated Redis Stack keyspace: digest, related, node and search, as evidence packets; a pointer's `text` body is never served, a curated node's own record is. `memory serve` checks active curated membership before printing the digest, includes source and untrusted-evidence framing, and exits 0 whether or not Redis answers. `serve --for PROMPT` searches prompt terms and suppresses file pointers with a `wrong` verdict or without an authorized verdict scope; a UserPromptSubmit bridge is documented in the CLI guide. `memory scratch` is working memory, bounded JSON under short keys with an optional time to live: a file store in the base that declares no sharing, or the Redis store with the extra; the backend is chosen at startup and an unreachable Redis is never replaced by the file store. CI exercises the extra absent and the extra present with no server on all three platforms; the path against a hydrated server passed once on a maintainer's machine on 2026-09-22 and runs only where `ATTUNE_TEST_REDIS_URL` is set | The native reader is POSIX-only: on Windows it reports the refusal instead of reading, until the Phase 4 decision. The reader matches attune-ai's adapter on result sets, top results and item metadata in a differential that runs only where that adapter's checkout exists. The `memory-native` extra ships in the wheel but is experimental and not activated for live memories. The native transport is POSIX only, accepts two exact model IDs, refuses any other SDK version, and is never exercised in CI |
| Roadmap | | `ship` and `reflect` are planned routes and do not exist yet |

## Harness and attune-ai

Harness is the successor I am building to
[attune-ai](https://pypi.org/project/attune-ai/). It starts from a constraint
attune-ai never had: it runs with no provider SDK and no attune-ai installation.
The Attune libraries it does use, forms, claim verification and local retrieval,
are part of the install, pinned exactly, and each loads only when the command that
needs it runs, so what the install adds is visible and nothing calls a model
unless you install an extra that does.

attune-ai is still where cross-session memory, the Claude Code plugin and the
multi-agent workflows live. Harness does not replace those today. If that is what
you need, install attune-ai, in its own environment: the two pin different lines
of the MCP SDK and cannot share one.

## Links

- [Qualification guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v0.6.0/docs/qualification.md)
- [CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v0.6.0/docs/cli-guide.md)
- [Portable contract](https://github.com/Smart-AI-Memory/attune-harness/blob/v0.6.0/docs/portable-contract.md)
- [Repository](https://github.com/Smart-AI-Memory/attune-harness) and
  [issues](https://github.com/Smart-AI-Memory/attune-harness/issues)

**Apache License 2.0.**

Built by Patrick Roebuck, working with Codex and Claude.
