<!--
DRAFT README for the first PyPI release. Written 2026-09-19. The live README.md is untouched.

Before this replaces README.md on the release line, check:

1. LINK BASE. Every link is absolute and pinned to a tag:
   https://github.com/Smart-AI-Memory/attune-harness/blob/v0.1.0/
   That tag does not exist yet. Either create it at the release commit, or
   search-and-replace "blob/v0.1.0" with "blob/main" (main is currently behind the
   working line, so some targets would 404 there).
2. docs/cli-guide.md DOES NOT EXIST YET. This draft moves the long per-command
   usage out of the README. Create that file from the current README sections
   "Plan and build", "Task-oriented evidence review", "Test this change",
   "Scoped repair" and "AI tools, integrations and existing scripts", verbatim.
3. BRANCH. Facts were read from wip/local-snapshot-2026-09-19 (pyproject extras,
   docs paths). Confirm the extras table and every linked doc against the release
   commit before publishing.
4. THE OPENING NUMBERS come from docs/plan-build-native-results.md (12 worker
   replies, 9 passing behaviour, 3 CLI defects) and the opportunity log entry O-19.
   Confirm I have read those correctly; you ran it, I did not.
5. STATUS LINE assumes the version decision lands on 0.1.0 final with an alpha
   classifier. Change it if you decide otherwise.
6. The attune-ai paragraph and the closing credit are my wording of your position.
   Edit freely.

Delete this comment before publishing.
-->

# Attune Harness

**Run an agent's work, check it independently, and keep a receipt of which happened.**

> **Status: 0.1.0, alpha.** Interfaces, configuration formats and CLI commands may
> change before 1.0. What is and is not qualified is
> [listed below](#what-is-qualified-and-what-is-not), not implied.

On September 18, 2026 I ran twelve model-written implementations of a small JSONL
exporter through Harness. Nine passed. The other three passed when their serializer
was tested directly, and failed when run through the real command line, which is the
only way anyone would ever use them
([results](https://github.com/Smart-AI-Memory/attune-harness/blob/v0.1.0/docs/plan-build-native-results.md)).

That gap is what Harness is for. A participant produces output: a model, a command,
or your own code. A check you supply, separate from the participant, decides whether
the output counts. You get back a receipt that says which. The participant's account
of its own work is recorded. It is never the evidence.

## A wrong answer comes back rejected

```sh
pip install attune-harness
```

The core has no dependencies and needs Python 3.10 or later. No provider SDK, no
API key, and no attune-ai installation.

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
[CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v0.1.0/docs/cli-guide.md).

## Install only what you use

| You want | Install |
| --- | --- |
| The core contracts and CLI, with no dependencies | `pip install attune-harness` |
| Document claim verification (`attune-verify` 0.6.0) | `pip install 'attune-harness[verify]'` |
| Local Markdown retrieval with source hashes, no model calls (`attune-rag` 1.2.0) | `pip install 'attune-harness[rag]'` |
| The evidence-review and test journeys: forms, retrieval and verification together | `pip install 'attune-harness[review]'` |
| Accepted retrieval grants served over MCP stdio (`mcp` 2.2.0) | `pip install 'attune-harness[mcp]'` |
| Repository-first retrieval on Voyage embeddings | `pip install 'attune-harness[voyage]'` |
| Token counting (`tiktoken` 0.12.0) | `pip install 'attune-harness[tokens]'` |

Extras pin exact versions as of 0.1.0. Keep the quotes: zsh and bash treat square
brackets as glob characters. When an extra is missing, the command that needs it
returns an actionable unavailable report instead of a traceback.

## What is qualified and what is not

I would rather you find the limits here than in your own checkout. Green software
tests and model quality are different claims, and this project keeps them apart.

| Area | Qualified | Not qualified |
| --- | --- | --- |
| Platforms | CI builds and installs the wheel on macOS, Ubuntu and Windows with Python 3.10 and 3.12, and exercises timeouts, cancellation, bounded output, crash-released locks and recovery ([guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v0.1.0/docs/qualification.md)) | Other Python versions are outside the matrix |
| Models | CI calls no model provider. Native Claude and Codex adapters have recorded comparisons | Native planning and building are experimental. In the September 18, 2026 comparison the original reply contract accepted 1 of 24 replies; after the contract was corrected it accepted 12 of 12. Two repetitions per role do not establish a reliability rate |
| `fix` and `test` | Local POSIX Git checkouts, regular files, default pytest discovery | Windows repair effects, file creation, deletion and renames, linked worktrees, custom pytest collectors, committed revision ranges |
| Isolation | Commands and probes run as supervised processes with deadlines and bounded output | **This is not a security sandbox.** Use a dedicated checkout and commands you trust |
| Receipts | Receipts retain the task, output and check evidence locally | They are local values, not signed attestations. Constructing a `Receipt` directly certifies nothing |
| Plan acceptance | Core imports, help and the library run standalone | `plan --accept` needs the optional Attune AI Spec runtime in the same environment |
| Protocols | MCP (2025-11-25 and 2026-07-28 profiles) and A2A 1.0 have local independent-client receipts | Remote authentication, arbitrary executable plugins and automatic host installation |
| Memory | An integration plan is accepted and qualified in a temporary install | Not released, and not activated for live memories |
| Roadmap | | `ship` and `reflect` are planned routes and do not exist yet |

## Harness and attune-ai

Harness is the successor I am building to
[attune-ai](https://pypi.org/project/attune-ai/). It starts from a constraint
attune-ai never had: the core must run with no provider SDK and nothing else from
the Attune family installed. The Attune libraries come in as extras, where you can
see exactly what each one adds.

attune-ai is still where cross-session memory, the Claude Code plugin and the
multi-agent workflows live. Harness does not replace those today. If that is what
you need, install attune-ai.

## Links

- [Qualification guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v0.1.0/docs/qualification.md)
- [CLI guide](https://github.com/Smart-AI-Memory/attune-harness/blob/v0.1.0/docs/cli-guide.md)
- [Portable contract](https://github.com/Smart-AI-Memory/attune-harness/blob/v0.1.0/docs/portable-contract.md)
- [Repository](https://github.com/Smart-AI-Memory/attune-harness) and
  [issues](https://github.com/Smart-AI-Memory/attune-harness/issues)

**Apache License 2.0.**

Built by Patrick Roebuck, working with Codex and Claude.
