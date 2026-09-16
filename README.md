# Attune Harness

A portable, extensible runtime for multi-model agents, under development.

The standalone core runs participants and independently checks their results.
Optional integrations provide Attune forms, local retrieval, verification and a
coordinated evidence-review CLI. Experimental Claude/Codex and JSON command
adapters connect participants. Native review qualification is recorded separately
from software tests; Claude's retry remains on hold.
No provider SDK or attune-ai installation is required by the core.

Dev13 adds [repository-first Attune RAG](docs/code-first-rag.md): application
code and tests, explicitly selected schemas/configuration, optional documentation,
and an Attune AI plugin using the shared Voyage engine. It builds on Dev12's
local indexes, hybrid search, standard reranking, and source/cost receipts. The dependency-free core
and deterministic structured tools remain available. See the
[implementation receipt](docs/voyage-retrieval-receipt.md) for the qualified scope.

## Task-oriented evidence review

Install `.[review]`, then supply one goal and the source/participant choices. Missing
answers are collected interactively; headless runs return a bound intake form.
Explicit acceptance executes the assessment. For example, from a project with
`docs/guide.md`, a trusted verification context and a participant registry:

```sh
attune-harness review --goal "Check the guide against project evidence" \
  --project . --config participants.json --document docs/guide.md \
  --context context.json --corpus docs --query "retention policy" \
  --criteria "Identify unsupported claims and preserve uncertainty" \
  --assessor alpha --accept
attune-harness status .attune-harness/tasks/<task-id>
attune-harness resume .attune-harness/tasks/<task-id>
```

Use `--plan independent-review --reviewer beta` for a separate assignment;
`--allow-external` explicitly enables configured command/native participants.
`--intake-only` prepares accepted inputs without executing. `--pause-after 2`
creates a durable interruption for later resume. A completed assessment can report
a refuted or unknown document; participant narratives remain unverified proposals.
The JSON includes the task directory and identity.

`reconcile-task`, `transfer-task`, and `cancel-task` expose bounded recovery controls.
`--help` lists every advanced command. All 18 legacy routes remain available,
including positional `review request.json --config ... --run-dir ...` and its
original status/exit semantics. Plan/build/ship are not implemented task journeys.
See the [assessment receipt](docs/specs/unified-task-execution/assessment-receipt.md)
for installed software evidence and outstanding native-model qualification.

## Scoped repair

`fix` replaces explicitly listed existing UTF-8 files in an exclusively owned,
bounded POSIX checkout with a local `.git` directory. Keep task state outside that
checkout. Creation, deletion, renames, symlinks/hardlinks, linked Git worktrees and
Windows repair effects are outside this first profile. The entire checkout is
bounded to 1,000 entries and 16 MiB, including protected metadata.

Prepare a trusted probe JSON before the worker runs:

```json
{
  "argv": ["/absolute/path/to/python", "probe.py"],
  "cwd": ".",
  "timeout": 30,
  "max_output_bytes": 8192,
  "environment": {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"},
  "oracle_paths": ["probe.py"]
}
```

```sh
attune-harness fix --goal "Repair addition" --project /path/to/parent \
  --checkout /path/to/parent/dedicated-clone --scope src/math.py \
  --probe /path/to/probe.json --config /path/to/participants.json \
  --worker alpha --reviewer beta --review required \
  --criteria "The frozen acceptance probe passes without changing its oracle" \
  --accept --allow-external
```

Repair uses the same status/resume controls. `--review none` explicitly selects no
review; both requested and required review must complete with no unresolved
objections. A required native reviewer must select a different configured model.
The worker returns a replacement proposal; the host applies it and retains the
failed-before/passed-after probe evidence. Native participant tool grants remain
read-only. Trusted command peers and probes are supervised processes, **not a
security sandbox**; use a dedicated checkout and trusted commands.

For an uncertain file write, `reconcile-task <task> --event <id> --observe-file`
records an observed matching after-image. `--retry-before` permits one retry only
when the original bytes remain. Unexpected bytes stay unresolved; cancellation
never rolls back later edits. Unknown probe effects are not automatically retried.
See the [repair receipt](docs/specs/unified-task-execution/repair-receipt.md) for the
exact tested profile and pending native qualification.

## Library quickstart

Requires Python 3.10 or later. Install from this checkout:

```sh
python -m pip install .
python -m attune_harness
# Optional forms, retrieval and document verification:
python -m pip install '.[review]'
```

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

The [GitHub library](https://github.com/Smart-AI-Memory/attune-harness) is private.
This is a development package; no PyPI publication is implied. The CI workflow
tests the installed library on macOS, Linux and Windows and records actual
capabilities. Dev11 adds Windows Job Object supervision and native writer locks;
the [qualification guide](docs/qualification.md) distinguishes platform execution
checks from model-provider qualification.

Dev10 adds [deterministic triage, GitHub check imports, and repair economics](docs/operations.md).
The [qualification guide](docs/qualification.md) explains the frozen model comparisons
and native platform checks. Raw historical receipts are retained locally and excluded
from Git; historical receipt links may require the original workspace.

The [September 15 results](docs/opportunities-implementation-report.md) record the
eight-case model comparison, narrow worker failures and six successful native CI
jobs. They separate software reliability from model accuracy.

This workspace's [review profile](participants.json) now selects **GPT-6 Astra,
extra-high reasoning** for both lead and reviewer, with a 1000-token skills catalog
budget. The native adapter passes the model and effort
explicitly to Codex and uses `review_mode: evidence`: the host retrieves/verifies
evidence and binds response identifiers; each model role writes one review.
New `review-form` and `review` commands use `./participants.json`
unless `--config` selects another registry. See the [Astra setup](docs/astra-review.md)
and [execution receipt](docs/native-evidence-review-receipt.md). Native execution still requires
`--allow-external`; changing the model, effort or catalog budget requires a newly
accepted review. Resume an older run with its original registry; the changed
profile cannot silently replace an accepted configuration.

The [Fable-led profile](docs/fable-review.md) selects Fable 5.1 with an Astra
reviewer as the next candidate. It is configured but not live-qualified. Patrick
retired Llama from the intended workflow on September 15; its retained experiments
provide historical comparison evidence.

The historical [local documentation-review pilot](docs/pilot-workflow.md) uses pinned
Ollama inference, real Attune evidence tools and checkpointed continuation.
It retains two independent narratives as unverified proposals and preserves
unknown document claims. See the [migration boundaries](docs/pilot-migration.md)
before selecting it as a daily workflow. No paid-provider fallback is provided.

Run the installed demonstration with `python -m attune_harness`.
It prints a JSON receipt; wrong output is rejected rather than called complete.
Run development checks with `python -m pytest tests`.

See `docs/design-first-increment.md` for scope and verification design, and
`docs/harness-phased-plan.md` for the wider roadmap. Direct construction of a
receipt is not certification; receipts are local values, not signed attestations.
The core Participant interface executes in-process without isolation or recovery.

The JSON boundary supplies `attune_harness.adapters.Attempt` and
`JsonParticipant`: an injected JSON exchange bound to one accepted task/revision
and one attempt. Responses must match the full request digest and pass strict
decoding before independent verification. Each adapter instance dispatches once;
this is not durable deduplication or authentication.

See [portable contract](docs/portable-contract.md) for capability/state cases and
outstanding guarantees, and [native experiment](docs/native-adapter-experiment.md)
for the next qualification steps. After installing the wheel, run
`python -I examples/json_exchange.py` for the independent deterministic consumer.

`attune_harness.native.NativeExchange` supplies a Claude or Codex exchange for
`JsonParticipant`. It retains native session identity and raw process diagnostics.
The POSIX runner supports deadlines, cancellation and bounded output capture;
these do not establish durable recovery or tool isolation. See
[native receipt](docs/native-build-receipt.md) for the tested support boundary.
`examples/native_probe.py` is the explicit entry point for an authenticated
arithmetic probe; it saves the result and raw evidence to a requested directory.

The local feature workflow now supports optional `verify` and `rag` extras:

```sh
attune-harness verify guide.md --context context.json --output verification.json
attune-harness retrieve "retention policy" --corpus docs --output sources.json
```

Verification preserves strict verified/refuted/unknown outcomes and per-claim
library evidence. Retrieval returns ranked local Markdown sources with hashes;
it makes no model calls. Missing extras return actionable unavailable reports.
See [local workflow](docs/local-workflow.md) for the prepared example, install
commands, exit codes, dependency pins and evidence boundaries.

The optional `review` extra combines attune-forms, attune-rag and attune-verify:

```sh
attune-harness review-form --config participants.json
attune-harness review request.json --config participants.json --run-dir new-run --allow-external
attune-harness inspect-review new-run
```

A submitted form selects distinct lead and reviewer identities. Each participant
gets bounded retrieval/verification calls; the coordinator saves pending work,
tool results, independent narratives and the document's strict verification result.
`completed` describes the workflow, not the correctness of arbitrary review prose.
The prepared deterministic example makes no model calls. External commands and
native adapters require explicit `--allow-external` selection. Inspection does not
resume a run or retry an uncertain operation. See [review workflow](docs/review-workflow.md)
and [implementation receipt](docs/review-workflow-receipt.md).

New runs also support checkpointed resumption, constrained reconciliation,
local lead transfer and cancellation. Completed operations are replayed from their
saved evidence; uncertain external effects block resumption. Accepted inputs and
source hashes must still match. These controls use POSIX file locks and remain
local to the original run directory. See [recovery workflow](docs/recovery-workflow.md)
for commands, the deterministic two-way transfer example and qualification limits.

Explicit data-only extension bundles can contribute a portable skill and a
namespaced retrieval tool. The local lifecycle CLI binds exact artifact bytes,
checks compatibility, and supports enable/disable/removal while preserving user
data. Review grants and corpus scope still control each invocation. A separately
built example plugin and an explicit Attune BasePlugin bridge exercise this
boundary. See [extension workflow](docs/extension-workflow.md) and its
[receipt](docs/extension-workflow-receipt.md).

The optional `mcp` extra pins SDK 2.2.0 and exposes accepted retrieval grants over
stdio. Legacy 2025-11-25 and current 2026-07-28 profiles have independent-client
receipts. See [MCP workflow](docs/mcp-workflow.md).

The dependency-free `A2AExchange` connects the core JSON participant to an
explicitly pinned local A2A 1.0 peer. It retains task/artifact identity, refuses
automatic resubmission after acknowledgement loss, and supports explicit refresh
and cancellation for a known task. See [A2A workflow](docs/a2a-workflow.md).
These protocol receipts are local; remote authentication, arbitrary executable
plugins and automatic host installation remain unqualified.
