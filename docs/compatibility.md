# The compatibility list

Draft of the first freeze cycle, September 23, 2026 (the plan's 4.1;
[D25.2](specs/release-1.0/addendum-2026-09-23.md) and D27). What 1.0.0
promises not to change without a deprecation, surface by surface, each with
the guard that fails when it changes. Frozen means three things at once: this
list, a test that fails on a non-additive change to anything on it, and the
deprecation rule at the end for the change that is allowed anyway. Additive
changes stay free: a new verb, a new optional key, a new optional
configuration field. Free means no deprecation, not no diff: the guards fail
on any change to what they pin, additive ones included, and an additive
change rewrites the fixture on purpose with a changelog line. The content
freezes at `1.0.0rc1`; the promise takes effect at 1.0.0.

The second cycle now supplies the deprecation register/helper (D27.3) and
retrieval MCP/A2A protocol fixtures (section 6). The third cycle still adds the
candidate saved-state fixture (section 3) after the final plugin manifest fields.
This does not declare the content frozen before rc1. The envelope cells still marked `-` are listed in
[the freeze note's correction](specs/release-1.0/freeze-design.md).

## 1. The command line

Twenty-nine verbs, their subcommands, their positional arguments with how
many values each takes, their required options, accepted choices and defaults,
read from the parsers
themselves by
`attune_harness.cli_surface` and committed as
`tests/fixtures/compatibility/surface.json`. `tests/test_compatibility_surface.py`
fails when the parsers and the file disagree, and when this table and the
file disagree; `scripts/compatibility_surface.py --rows` regenerates the
table. The fixture also lists every option string, choice and default, so a new optional flag
fails the test too and is added by rewriting the fixture (additive, so no
deprecation). In the table a positional in brackets, `[request]`, is
optional; `name ...` takes one or more values and `[name ...]` zero or
more.

Patrick ruled choices and defaults into the 1.0 CLI contract before rc1.
`surface.json` records them for every argument, with path values distinguished
from strings. The dynamic `spec intake --project` default is the current
working directory, recorded as such rather than as the fixture writer's
absolute checkout path. Changing a choice or default fails the surface guard.

Exit codes are behaviour, not parser data: [the envelope table](envelopes.md)
pins them, row by row, for every verb that prints an envelope. Two print
none: `memory serve`, whose exit codes (0 on success and on every refusal,
for a session-start hook) are pinned by `tests/test_memory_redis.py`, and
`mcp-serve`, whose failure exit, 2, is pinned by `tests/test_mcp.py`; its
success exit, 0 when the client closes the stream, is not pinned yet. The
program's one option is `--help-all`. Workspace MCP accepts `--workspace`,
`--project` and `--state-dir`; retrieval still requires `--request`,
`--participant` and `--session-dir`, checked together before startup.
`spec intake --compose` and `spec present` return text, tested separately.

<!-- surface-rows -->
| Verb | Subcommands | Positionals | Required |
| --- | --- | --- | --- |
| `build` | - | `task_dir` | - |
| `cancel-review` | - | `run_dir` | `--checkpoint` `--reason` |
| `cancel-task` | - | `task_dir` | `--reason` |
| `code-config` | - | - | `--index-dir` `--repo` |
| `extension` | disable discover enable inspect install remove replace | - | - |
| `fix` | - | - | - |
| `github-checks` | - | `input` | `--repository` `--revision` |
| `index` | build inspect plan update | - | - |
| `inspect-review` | - | `run_dir` | - |
| `mcp-inspect` | - | `session_dir` | - |
| `mcp-serve` | - | - | - |
| `memory` | capabilities create execute inspect recall redis(digest node related search status) refresh replay resolve saved(complete forget list reindex revise save search show) scratch(capabilities forget keys retrieve stash) serve | - | `--config` |
| `plan` | - | - | `--task-dir` |
| `reconcile-review` | - | `run_dir` | `--checkpoint` `--event` one of `--reply`, `--retry-read-only` |
| `reconcile-task` | - | `task_dir` | `--event` one of `--observe-file`, `--reply`, `--retry-before`, `--retry-native`, `--retry-read-only` |
| `repair-economics` | - | `input` | - |
| `resume` | - | `task_dir` | - |
| `resume-review` | - | `run_dir` | `--checkpoint` `--config` `--request` |
| `retrieval-task` | - | - | `--config` `--generation` `--objective` |
| `retrieve` | - | `query` | one of `--corpus`, `--request` |
| `review` | - | `[request]` | - |
| `review-form` | - | - | - |
| `spec` | intake present | - | - |
| `status` | - | `task_dir` | - |
| `test` | - | - | `--task-dir` |
| `transfer-review` | - | `run_dir` | `--checkpoint` `--lead` `--reason` |
| `transfer-task` | - | `task_dir` | `--assessor` `--reason` |
| `triage-check` | - | `input` | - |
| `verify` | - | `document` | `--context` |
<!-- /surface-rows -->

`status` additionally accepts optional `--format json|markdown|html`. Default
and explicit JSON preserve the existing envelope. Markdown/HTML are bounded,
read-only snapshots for `feature-work-v1`, with no live refresh or new task
authority. Unsupported profiles and oversized views give a JSON error and exit 2.
`--continuation FILE` optionally supplies bounded, attributed pause context for
Markdown/HTML only. It does not extend the saved task schema or JSON envelope;
using it with JSON gives an explicit error rather than silently dropping context.
The optional `briefing` object adds six bounded, attributed summary fields to the
continuation note only. HTML now carries fixed local reply-preparation controls,
not task actions. Repeatable `--include-task TASK` adds an explicit bounded Saved
Tasks collection for HTML/Markdown; JSON refuses that option. The optional `design_review` note adds bounded external feedback and a discussion-only
question without changing saved authority. No saved-task
record schema or execution route changes.

## 2. Envelopes

[The envelope table](envelopes.md): rows pinned by
`tests/test_golden_envelopes.py`, each verb's top-level keys,
`schema_version`, `status` and exit code, values never. Every `status` value
a row shows is part of the contract; a new value on an existing verb is a
deliberate diff. `code-config` carries no `status` by design: its envelope is
the retrieval config that `index plan --config` reads back.

## 3. Configuration and saved state

Every record on disk carries a version, and every reader refuses what it does
not know. The fixture from the 1.0 era, the third cycle's, is the guard that
the 1.0 readers keep reading 1.0 records; until it lands, the golden rows and
each reader's own version check are.

| Format | Version today | Read by | Written by |
| --- | --- | --- | --- |
| Task record, `record.json` | `schema_version` 1; `task_profile` one of `assessment-intake-v1`, `feature-work-v1`, `pytest-change-v1`; `record_path` bound to its directory | `task_contract.read_task` | `plan`, `review`, `test`, `fix` |
| Run record | `schema_version` 1 | `review_store.read_record`, `review_contract` | the review verbs, `mcp-serve` |
| Plan state comment | schema 1 and 2 read, 2 written | `spec_state`, `spec_legacy` | `plan`, the spec journey |
| Worker proposal | schema 3, with 2 still accepted at one site | `work_build` | command participants |
| Effects manifest | `posix-feature-effects-v1`, `windows-feature-effects-v1`, with a `before` snapshot | `work_effects`, `windows_effects` | `work_effects.freeze` |
| Scratch record | `format: attune-harness/scratch`, `format_version` 2, `writer` and per-key `version`; legacy headerless `schema_version` 1 remains readable | `memory_scratch` | `memory scratch stash` |
| Saved memory/task store, `state.json` | `schema_version` 1; record revision/history, operation identities and index state; optional task `opportunity_review` checkpoint | `memory_saved.SavedStore` | `memory saved` mutation commands |
| Voyage paid-stage ledger and stage `record.json` | `schema_version` 1; recovery profiles `voyage-stage-ledger-v1` and `voyage-paid-stage-v1`, with durable stage identities, statuses and billing receipts | `review_store.read_record`, `voyage_provider.StageJournal` | `voyage_provider.StageJournal` during `index build` and retrieval |
| Extension manifest and state | `schema_version` 1; signed Python declarations include `grants`, `declares`, `code` and the `run` binding, with host-owned enable state | `extensions`, `plugin_runtime` | `extension install`, `enable` |
| Participants registry | `schema_version` 1 | `review_contract.load_registry` | the user |
| Memory config | `roots`, `redis`, `scratch`, `reader` and explicit `saved` sections | `memory_reader.roots_config`, `memory_saved_cli` and the backends | the user |
| Memory context packet | `schema_version` 1 | `memory_context.refresh` | `memory recall` |
| The attune-ai memory formats | frozen as read (D25.5/D28); [field and refusal contract](specs/native-memory/formats.md) | `memory_reader`, `memory_redis` | attune-ai's writers |

The candidate fixture must include both the current scratch format and saved
memory/task records, including deferred-review state. Their current reader tests
are not a substitute for a fixture written by the candidate. Saved task intent
references existing execution; it does not create a second execution owner.
The Voyage host-owned stage journal is also saved state: its completed stages
replay without a new paid call, while a dispatched stage refuses automatic
retry. The candidate fixture will capture this format with synthetic results;
the selected index's LanceDB files remain covered by index qualification.

## 4. Refusal texts

The user-visible words of every refusal are contracts since D20.1, pinned
where they arise: the gate tests, the golden refusal rows and the R2 journey.
A changed word is a deliberate diff with a changelog line.

## 5. The Python API

Seven names, `run`, `Task`, `Output`, `Check`, `Receipt`, `Status` and
`Participant`, with their parameters and defaults in
`tests/fixtures/compatibility/public_api.txt`; `tests/test_public_api.py`
runs the README's example as written, its two documented variants, pins that
`run` calls the participant once and never retries, and that
`Task.schema_version` accepts 1 and nothing else.

## 6. Protocols

MCP tool names and schemas per profile version, `2026-07-28` and
`2025-11-25`, and the A2A local profile, changed only with the protocol
version. `mcp-inspect` records the supported profiles; the SDK tests assert the
negotiated version. `tests/test_protocol_compatibility.py` compares the real
SDK/stdio tool listing
with `tests/fixtures/compatibility/mcp-2025-11-25.json` and its
`mcp-2026-07-28.json` sibling. They pin the built-in retrieval tool's name,
input/output schemas and digests, and annotations under each negotiated version.
Dynamic extension tools remain governed by their accepted manifests. Workspace
MCP has its separate `workspace-mcp.json` fixture and existing workspace tests.

`a2a-1.0.json` pins the local profile's operations, accepted/terminal task states,
and the independent example peer's agent card (only its ephemeral port is
normalized). The actual card check uses the existing POSIX peer fixture; the
state/operation guard runs on every platform. The existing A2A behavioral tests
still prove correlation and task handling. These are compatibility checks, not
remote-authentication or model-quality qualification.

## Outside the list

Envelope values, stderr text, module names, the experimental features'
contracts (their envelopes stay pinned; the deprecation promise does not
cover them, and the README says which), the receipt layouts under `docs/`,
and attune-ai's own keyspace, read as it is.

## The deprecation rule

A rename, a removal or a change of meaning on anything above ships only with
the old form still working for one minor release, a `deprecations` entry in
the envelope and a changelog line. The active register is `docs/deprecations.json`, initially empty (D27.3).
Each entry has exactly `surface`, `form`, `since`, `removal` and `replacement`.
Versions name stable releases; removal is no earlier than the next minor release
following `since`. `features.with_deprecation` copies a notice into the optional
`deprecations` list only when the deprecated-form branch calls it. Current forms
keep their envelopes unchanged. The helper does not remove or redirect a form:
the caller must retain the old behavior and add its changelog line.
`tests/test_deprecations.py` checks the active register, minimum notice period,
overdue entries and a synthetic alias. Remove an expired entry together with its
old form and retain its history in the changelog; runtime behavior does not read
files from the repository's `docs/` directory. After
`rc1`, a change to anything on the list restarts the candidate at the next
`rc` number, the runbook's rule (D27.7).
