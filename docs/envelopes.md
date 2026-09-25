# Envelopes

Every `attune-harness` verb prints one JSON object, the envelope. This page
is the compatibility surface the 1.0 changelog will point at: the top-level
keys, `schema_version`, `status` and exit code of every verb, and of every
subcommand of `extension`, `index`, `memory redis` and `memory scratch`, as
`tests/test_golden_envelopes.py` pins them. A change to a row here is a
deliberate diff; the test fails exactly the case whose id names the verb, and
`test_documented_table_matches` fails when this page and the test disagree.

Only key names, `schema_version` and `status` are pinned, never values such as
timestamps, digests or request ids. The **path** column says which envelope a
row pins, in 76 rows:

- **success** (56 rows): the verb did its work offline on a small fixture;
  a paused, cancelled or draft record is a success of its control verb.
- **refusal** (9 rows): an offline refusal on purpose. `build` before the work
  is accepted; `index build` without `--allow-provider`; `index update`,
  `index inspect` and `retrieval-task` naming a generation that was never
  built; `memory capabilities` with a config that is not the roots contract,
  refused by the default reader in its own words; `triage-check` and
  `github-checks` on an empty object; `memory scratch stash` with an
  `--expected-version` the stored record is not at, nothing written. Voyage
  is never called.
- **unavailable** (9 rows): a dependency or server this install does not
  have. The memory host route (`capabilities` through `execute`) with
  `reader: adapter` needs the attune-ai adapter, which no base or extra
  install carries; a configured Redis that refuses the connection.
- **disabled** (1 row): the memory config has no `scratch` section.
- **uncertain** (1 row): a write whose effect cannot be known. `memory scratch
  stash` when the record was written and the replace raised; the receipt
  carries the version and the stamp the write took, and says that the
  stash was not retried and nothing was diverted.

The four `-adapter` rows pin the memory host's success shapes over an
in-process double of the adapter's four-member contract (`binding`,
`capabilities`, `query`, `resolve`), since no install carries the adapter;
the four `-native` rows pin the same shapes through Harness's own reader,
the default since Phase 2 step 2.4 (D19), over a raw root.

Text-only Spec compose/presentation is checked in `test_spec_cli.py`.
Two other surfaces are not pinned here. `mcp-serve` speaks the MCP protocol on stdout and
prints no envelope, and `--help`/`--help-all` print text. Seven rows run on
POSIX only: `fix-intake`, `test-preview` and `status-test`, because the `test`
verb qualifies the POSIX execution profile and the repair probe fixture is a
POSIX one; and the four `-native` rows, because the native memory reader's
descriptor walk is POSIX-only at 0.5.0 (D19). A `-` in the `schema_version`
or `status` column means the envelope has no such key. The first freeze cycle
(4.1, D27.2) closed the gaps this page used to list: the feature-work verbs
(`plan`, `build` and their `status`, their refusals included) and every
result `memory scratch` returns gained `schema_version: 1`, and
`triage-check`, `repair-economics` and `github-checks` gained
`status: completed` on success and `schema_version: 1` on their refusals,
which the two refusal rows pin. `code-config` keeps no `status` on purpose:
its envelope is the retrieval config itself, which `index plan --config`
reads back and would refuse with a key it does not know. The `-` cells that
remain, the `demo` receipt, the memory host route's packets and refusals, and
the Redis reader's unreachable report, are the second freeze cycle's to close
or to rule exempt; the eight adapter-bound rows among them go with D28.

## Table

| Case | Path | Exit | `schema_version` | `status` | Top-level keys |
|---|---|---|---|---|---|
| `demo` | success | 0 | - | `verified` | `check` `error` `output` `participant_id` `status` `task` |
| `review-form` | success | 0 | 1 | `ready` | `definition` `form_revision` `markdown` `operation` `request_id` `schema_version` `status` `submission` |
| `review-legacy` | success | 0 | 1 | `completed` | `accepted` `artifacts` `checkpoint_digest` `document_outcome` `events` `external_execution_enabled` `initial_retrieval` `operation` `participants` `preflight_verification` `record_path` `recovery` `registry` `request_id` `requirement_revision` `retrieval_outcome` `run_id` `schema_version` `status` `verification` `verification_scope` |
| `inspect-review` | success | 0 | 1 | `completed` | `accepted` `artifacts` `checkpoint_digest` `document_outcome` `events` `external_execution_enabled` `initial_retrieval` `operation` `participants` `preflight_verification` `record_path` `recovery` `registry` `request_id` `requirement_revision` `retrieval_outcome` `run_id` `schema_version` `status` `verification` `verification_scope` |
| `transfer-review` | success | 1 | 1 | `paused` | `accepted` `artifacts` `checkpoint_digest` `events` `external_execution_enabled` `initial_retrieval` `operation` `participants` `preflight_verification` `record_path` `recovery` `registry` `request_id` `requirement_revision` `run_id` `schema_version` `status` `verification_scope` |
| `resume-review` | success | 0 | 1 | `completed` | `accepted` `artifacts` `checkpoint_digest` `document_outcome` `events` `external_execution_enabled` `initial_retrieval` `operation` `participants` `preflight_verification` `record_path` `recovery` `registry` `request_id` `requirement_revision` `retrieval_outcome` `run_id` `schema_version` `status` `verification` `verification_scope` |
| `reconcile-review` | success | 1 | 1 | `paused` | `accepted` `artifacts` `checkpoint_digest` `events` `external_execution_enabled` `initial_retrieval` `operation` `participants` `preflight_verification` `record_path` `recovery` `registry` `request_id` `requirement_revision` `run_id` `schema_version` `status` `verification_scope` |
| `cancel-review` | success | 1 | 1 | `cancelled` | `accepted` `artifacts` `checkpoint_digest` `error` `events` `external_execution_enabled` `initial_retrieval` `operation` `participants` `preflight_verification` `record_path` `recovery` `registry` `request_id` `requirement_revision` `run_id` `schema_version` `status` `verification_scope` |
| `status-review` | success | 0 | 1 | `completed` | `accepted` `artifacts` `checkpoint_digest` `document_outcome` `events` `external_execution_enabled` `initial_retrieval` `operation` `participants` `preflight_verification` `record_path` `recovery` `registry` `request_id` `requirement_revision` `retrieval_outcome` `run_id` `schema_version` `status` `verification` `verification_scope` |
| `review-goal-intake` | success | 0 | 1 | `accepted` | `answers` `defaults_origin` `definition` `execution_status` `intake_metrics` `markdown` `note` `operation` `repair_contract` `revision` `schema_version` `status` `submission` `task_directory` `task_id` |
| `review-task-response` | success | 0 | 1 | `completed` | `acceptance` `bindings` `checkpoint_digest` `events` `execution` `history` `operation` `record_path` `recovery` `request` `schema_version` `status` `task_profile` |
| `status-task` | success | 0 | 1 | `paused` | `acceptance` `bindings` `checkpoint_digest` `events` `execution` `history` `operation` `record_path` `recovery` `request` `schema_version` `status` `task_profile` |
| `resume-task` | success | 0 | 1 | `completed` | `acceptance` `bindings` `checkpoint_digest` `events` `execution` `history` `operation` `record_path` `recovery` `request` `schema_version` `status` `task_profile` |
| `reconcile-task` | success | 1 | 1 | `paused` | `acceptance` `bindings` `checkpoint_digest` `events` `execution` `history` `operation` `record_path` `recovery` `request` `schema_version` `status` `task_profile` |
| `transfer-task` | success | 1 | 1 | `paused` | `acceptance` `bindings` `checkpoint_digest` `events` `execution` `history` `operation` `record_path` `recovery` `request` `schema_version` `status` `task_profile` |
| `cancel-task` | success | 1 | 1 | `cancelled` | `acceptance` `bindings` `checkpoint_digest` `events` `execution` `history` `operation` `record_path` `recovery` `request` `schema_version` `status` `task_profile` |
| `fix-intake` | success | 0 | 1 | `accepted` | `answers` `defaults_origin` `definition` `execution_status` `intake_metrics` `markdown` `note` `operation` `repair_contract` `revision` `schema_version` `status` `submission` `task_directory` `task_id` |
| `test-preview` | success | 1 | 1 | `draft` | `checkpoint_digest` `execution_evidence` `operation` `presentation` `record_path` `schema_version` `status` `task_profile` |
| `status-test` | success | 0 | 1 | `draft` | `checkpoint_digest` `execution_evidence` `operation` `presentation` `record_path` `schema_version` `status` `task_profile` |
| `plan-request` | success | 0 | 1 | `draft` | `advisory` `authoring` `authority` `blocking` `checkpoint_digest` `completed` `controls` `evidence` `execution_evidence` `intent` `missing` `next_action` `note` `phase` `preserved_completion` `questions` `record_path` `revision` `schema_version` `status` `summary` `task_directory` `task_id` `tasks` |
| `plan-decision` | success | 0 | 1 | `draft` | `advisory` `authoring` `authority` `blocking` `checkpoint_digest` `completed` `controls` `decision` `evidence` `execution_evidence` `intent` `missing` `next_action` `note` `phase` `preserved_completion` `questions` `record_path` `revision` `schema_version` `status` `summary` `task_directory` `task_id` `tasks` |
| `status-work` | success | 0 | 1 | `draft` | `advisory` `authoring` `authority` `blocking` `checkpoint_digest` `completed` `controls` `evidence` `execution_evidence` `intent` `missing` `next_action` `note` `phase` `preserved_completion` `questions` `record_path` `revision` `schema_version` `status` `summary` `task_directory` `task_id` `tasks` |
| `build-draft` | refusal | 2 | 1 | `failed` | `blocking` `error` `evidence` `next_action` `record_path` `schema_version` `status` `summary` |
| `extension-discover` | success | 0 | 1 | `ready` | `bundle` `operation` `request_id` `schema_version` `status` |
| `extension-install` | success | 0 | 1 | `disabled` | `artifact_digest` `id` `manifest` `operation` `revision` `schema_version` `state_digest` `status` |
| `extension-enable` | success | 0 | 1 | `enabled` | `artifact_digest` `id` `manifest` `operation` `revision` `schema_version` `state_digest` `status` |
| `extension-enable-plugin` | success | 0 | 1 | `enabled` | `artifact_digest` `id` `manifest` `operation` `plugin` `revision` `schema_version` `state_digest` `status` |
| `extension-inspect` | success | 0 | 1 | `enabled` | `artifact_digest` `id` `manifest` `operation` `revision` `schema_version` `state_digest` `status` |
| `extension-disable` | success | 0 | 1 | `disabled` | `artifact_digest` `id` `manifest` `operation` `revision` `schema_version` `state_digest` `status` |
| `extension-replace` | success | 0 | 1 | `disabled` | `artifact_digest` `id` `manifest` `operation` `revision` `schema_version` `state_digest` `status` |
| `extension-remove` | success | 0 | 1 | `removed` | `artifact_digest` `id` `manifest` `operation` `revision` `schema_version` `state_digest` `status` |
| `code-config` | success | 0 | 1 | - | `allow_overlays` `allow_untracked` `batch_size` `candidates` `exclude` `include` `index_dir` `max_bytes` `max_file_bytes` `max_files` `max_provider_calls` `max_request_bytes` `passage_bytes` `roots` `schema_version` `structured_paths` |
| `index-plan` | success | 0 | 1 | `ready` | `config_digest` `embedding_input_bytes` `estimate_scope` `estimated_embedding_cost_usd` `estimated_tokens` `generation` `manifest` `operation` `passages` `planned_embedding_calls` `profile` `provider_calls` `rate_snapshot` `request_id` `schema_version` `status` |
| `index-build` | refusal | 2 | 1 | `failed` | `error` `operation` `request_id` `schema_version` `status` |
| `index-update` | refusal | 2 | 1 | `failed` | `error` `operation` `request_id` `schema_version` `status` |
| `index-inspect` | refusal | 2 | 1 | `failed` | `error` `operation` `request_id` `schema_version` `status` |
| `retrieval-task` | refusal | 2 | 1 | `failed` | `error` `operation` `request_id` `schema_version` `status` |
| `triage-check` | success | 0 | 1 | `completed` | `action` `atomic_claim_required` `dispatch_authorized` `key` `reason` `schema_version` `status` |
| `repair-economics` | success | 0 | 1 | `completed` | `eligible_cost_ranking` `note` `schema_version` `scope` `status` `strategies` |
| `github-checks` | success | 0 | 1 | `completed` | `all_checks_passed` `checks` `note` `repair_verified` `repository` `revision` `schema_version` `status` |
| `triage-check-refusal` | refusal | 2 | 1 | `failed` | `error` `schema_version` `status` |
| `github-checks-refusal` | refusal | 2 | 1 | `failed` | `error` `schema_version` `status` |
| `mcp-inspect` | success | 0 | 1 | `completed` | `accepted` `completion_scope` `events` `identity_scope` `max_calls` `operation` `participant_id` `profile` `record_path` `registry` `request_id` `requirement_revision` `schema_version` `source_snapshot` `status` `tools` |
| `mcp-inspect-workspace` | success | 0 | 1 | `completed` | `calls_completed` `calls_failed` `calls_started` `completion_scope` `dropped_events` `identity_scope` `max_calls` `model_calls` `operation` `participant_id` `pending` `profile` `project` `provider` `record_path` `request_id` `schema_version` `status` `tools` |
| `spec-intake` | success | 0 | - | - | `areas` `form` `taken_slugs` |
| `verify` | success | 0 | 1 | `verified` | `artifacts` `dependency` `operation` `passed` `request_id` `result` `schema_version` `status` |
| `retrieve` | success | 0 | 1 | `retrieved` | `corpus` `dependency` `k` `operation` `query` `request_id` `retriever` `schema_version` `sources` `status` |
| `memory-capabilities` | unavailable | 2 | - | `unavailable` | `detail` `error` `status` |
| `memory-recall` | unavailable | 2 | - | `unavailable` | `detail` `error` `status` |
| `memory-resolve` | unavailable | 2 | - | `unavailable` | `detail` `error` `status` |
| `memory-refresh` | unavailable | 2 | - | `unavailable` | `detail` `error` `status` |
| `memory-create` | unavailable | 2 | - | `unavailable` | `detail` `error` `status` |
| `memory-replay` | unavailable | 2 | - | `unavailable` | `detail` `error` `status` |
| `memory-inspect` | unavailable | 2 | - | `unavailable` | `detail` `error` `status` |
| `memory-execute` | unavailable | 2 | - | `unavailable` | `detail` `error` `status` |
| `memory-capabilities-adapter` | success | 0 | - | - | `context_refresh` `mutation_status` `native_worker` `read` `reader` `retained_paths` `worker_execution` `worker_mutations` |
| `memory-recall-adapter` | success | 0 | 1 | `available` | `authority` `guidance` `items` `k` `max_chars` `operation` `problems` `query` `schema_version` `status` |
| `memory-resolve-adapter` | success | 0 | - | - | `authority` `classification` `id` `kind` `locator` `metadata` `owner` `scope` `text` `version` |
| `memory-refresh-adapter` | success | 0 | - | `available` | `context` `invalidated_ids` `replaces` `status` |
| `memory-capabilities-native` | success | 0 | - | - | `context_refresh` `mutation_status` `native_worker` `read` `reader` `retained_paths` `worker_execution` `worker_mutations` |
| `memory-recall-native` | success | 0 | 1 | `available` | `authority` `guidance` `items` `k` `max_chars` `operation` `problems` `query` `schema_version` `status` |
| `memory-resolve-native` | success | 0 | - | - | `authority` `classification` `id` `kind` `locator` `metadata` `owner` `scope` `text` `version` |
| `memory-refresh-native` | success | 0 | - | `available` | `context` `invalidated_ids` `replaces` `status` |
| `memory-capabilities-invalid` | refusal | 2 | - | `failed` | `detail` `error` `status` |
| `memory-redis-status` | success | 0 | 1 | `ok` | `active_nodes` `authority` `guidance` `items` `layers` `operation` `schema_version` `status` |
| `memory-redis-digest` | success | 0 | 1 | `ok` | `authority` `guidance` `items` `limit` `operation` `schema_version` `status` |
| `memory-redis-related` | success | 0 | 1 | `ok` | `authority` `guidance` `id` `items` `operation` `schema_version` `status` |
| `memory-redis-node` | success | 0 | 1 | `ok` | `authority` `guidance` `id` `items` `operation` `schema_version` `status` |
| `memory-redis-search` | success | 0 | 1 | `ok` | `authority` `guidance` `items` `k` `layer` `operation` `query` `schema_version` `status` `total` |
| `memory-redis-unreachable` | unavailable | 2 | - | `unavailable` | `detail` `error` `status` |
| `memory-scratch-capabilities` | success | 0 | 1 | `ok` | `backend` `location` `operation` `realtime` `schema_version` `shared` `status` |
| `memory-scratch-stash` | success | 0 | 1 | `ok` | `backend` `expires_at` `format` `format_version` `key` `operation` `schema_version` `status` `stored_at` `version` `writer` |
| `memory-scratch-stash-refused` | refusal | 2 | 1 | `failed` | `backend` `detail` `error` `expected_version` `key` `operation` `schema_version` `status` `version` |
| `memory-scratch-stash-uncertain` | uncertain | 2 | 1 | `uncertain` | `backend` `detail` `error` `key` `operation` `schema_version` `status` `stored_at` `version` |
| `memory-scratch-retrieve` | success | 0 | 1 | `ok` | `backend` `expires_at` `format` `format_version` `key` `operation` `schema_version` `status` `stored_at` `value` `version` `writer` |
| `memory-scratch-forget` | success | 0 | 1 | `ok` | `backend` `forgotten` `key` `operation` `schema_version` `status` |
| `memory-scratch-keys` | success | 0 | 1 | `ok` | `backend` `keys` `operation` `pattern` `schema_version` `status` |
| `memory-scratch-disabled` | disabled | 2 | 1 | `disabled` | `detail` `schema_version` `status` |

## Invocations

What each case runs, in the order of the table.

- `demo`: `attune-harness` (no command; the deterministic demo receipt)
- `review-form`: `review-form --config`
- `review-legacy`: `review REQUEST --config --run-dir` (legacy form, deterministic adapter)
- `inspect-review`: `inspect-review RUN_DIR`
- `transfer-review`: `transfer-review RUN_DIR --checkpoint --lead --reason` on a paused run
- `resume-review`: `resume-review RUN_DIR --request --config --checkpoint` on a paused run
- `reconcile-review`: `reconcile-review RUN_DIR --checkpoint --event --reply` after an interrupted turn
- `cancel-review`: `cancel-review RUN_DIR --checkpoint --reason` on a paused run
- `status-review`: `status RUN_DIR` on a legacy review record
- `review-goal-intake`: `review --goal ... --accept --intake-only` (task intake)
- `review-task-response`: `review --task-response --task-dir` (accepted intake, executed)
- `status-task`: `status TASK_DIR` on a paused assessment
- `resume-task`: `resume TASK_DIR` on a paused assessment
- `reconcile-task`: `reconcile-task TASK_DIR --checkpoint --event --reply` after a lost acknowledgement
- `transfer-task`: `transfer-task TASK_DIR --assessor --reason` on a paused independent review
- `cancel-task`: `cancel-task TASK_DIR --reason` on a paused assessment
- `fix-intake`: `fix --goal --checkout --scope --probe ... --accept --intake-only` (POSIX only)
- `test-preview`: `test --project --task-dir --scope --interpreter` (the preview; POSIX only)
- `status-test`: `status TASK_DIR` on a test preview (POSIX only)
- `plan-request`: `plan --task-dir --request --project --config`
- `plan-decision`: `plan --task-dir --decision` on a draft
- `status-work`: `status TASK_DIR` on feature work
- `build-draft`: `build TASK_DIR` on a draft that was never accepted
- `extension-discover`: `extension discover MANIFEST`
- `extension-install`: `extension install MANIFEST --state-dir`
- `extension-enable`: `extension enable --state-dir --checkpoint`
- `extension-enable-plugin`: `extension enable --state-dir --checkpoint --registry` on a signed plugin bundle, with a scratch key
- `extension-inspect`: `extension inspect --state-dir`
- `extension-disable`: `extension disable --state-dir --checkpoint`
- `extension-replace`: `extension replace --state-dir --checkpoint --manifest`
- `extension-remove`: `extension remove --state-dir --checkpoint`
- `code-config`: `code-config --repo --index-dir` (the prepared config is the envelope)
- `index-plan`: `index plan --config`
- `index-build`: `index build --config` without `--allow-provider`
- `index-update`: `index update --config --base-generation` with an unknown base generation
- `index-inspect`: `index inspect --config --generation` with an unknown generation
- `retrieval-task`: `retrieval-task --config --generation --objective` with an unknown generation
- `triage-check`: `triage-check INPUT`
- `repair-economics`: `repair-economics INPUT`
- `github-checks`: `github-checks INPUT --repository --revision`
- `triage-check-refusal`: `triage-check INPUT` on an empty object
- `github-checks-refusal`: `github-checks INPUT --repository --revision` on an empty object
- `mcp-inspect`: `mcp-inspect SESSION_DIR` on a finished retrieval session
- `verify`: `verify DOCUMENT --context`
- `retrieve`: `retrieve QUERY --corpus`
- `memory-capabilities`: `memory --config capabilities` without attune-ai
- `memory-recall`: `memory --config recall QUERY` without attune-ai
- `memory-resolve`: `memory --config resolve HANDLE` without attune-ai
- `memory-refresh`: `memory --config refresh CONTEXT` without attune-ai
- `memory-create`: `memory --config create RUN_ID --envelope --policy` without attune-ai
- `memory-replay`: `memory --config replay RUN_ID JOB_ID --replies` without attune-ai
- `memory-inspect`: `memory --config inspect RUN_ID JOB_ID` without attune-ai
- `memory-execute`: `memory --config execute RUN_ID JOB_ID` without attune-ai
- `memory-capabilities-adapter`: `memory --config capabilities` over an in-process double of the adapter's four-member contract
- `memory-recall-adapter`: `memory --config recall QUERY --k 3` over the double
- `memory-resolve-adapter`: `memory --config resolve HANDLE` with a handle the double's recall returned
- `memory-refresh-adapter`: `memory --config refresh CONTEXT` with the packet the double's recall returned
- `memory-capabilities-native`: `memory --config capabilities` with the default reader over a raw root (POSIX only)
- `memory-recall-native`: `memory --config recall QUERY --k 2` over the raw root (POSIX only)
- `memory-resolve-native`: `memory --config resolve HANDLE` with a handle the native recall returned (POSIX only)
- `memory-refresh-native`: `memory --config refresh CONTEXT` with the packet the native recall returned (POSIX only)
- `memory-capabilities-invalid`: `memory --config capabilities` with the default reader and a config that is not the roots contract
- `memory-redis-status`: `memory --config redis status` (in-process double of a hydrated keyspace)
- `memory-redis-digest`: `memory --config redis digest --limit`
- `memory-redis-related`: `memory --config redis related ID`
- `memory-redis-node`: `memory --config redis node ID`
- `memory-redis-search`: `memory --config redis search QUERY --layer --k`
- `memory-redis-unreachable`: `memory --config redis status` with a configured Redis that refuses
- `memory-scratch-capabilities`: `memory --config scratch capabilities` (file backend)
- `memory-scratch-stash`: `memory --config scratch stash KEY --value --ttl`
- `memory-scratch-stash-refused`: `memory --config scratch stash KEY --value --expected-version` with a version the stored record is not at
- `memory-scratch-stash-uncertain`: `memory --config scratch stash KEY --value` with the replace refused after the record was written (in-process)
- `memory-scratch-retrieve`: `memory --config scratch retrieve KEY`
- `memory-scratch-forget`: `memory --config scratch forget KEY`
- `memory-scratch-keys`: `memory --config scratch keys PATTERN`
- `memory-scratch-disabled`: `memory --config scratch capabilities` with no `scratch` section

## Stored formats

The envelopes above are what the verbs print. What the stores write is a
second surface: a record that another writer, or a later Harness, must
read. Each stored format is listed here with its name, its version, its
fields and what a reader must accept; a change to one is a deliberate diff,
and Phase 4's freeze (4.1) points the 1.0 changelog at this list. The
scratch record is its first entry (native memory Task 5, plan task 3.4,
D21.6).

### `attune-harness/scratch`, version 2

One record per key, written by `memory scratch stash`. On the file backend
it is the file `k-<encoded key>.json` under `<root>/scratch/<namespace>/`,
where every character of the key outside `[a-z0-9_.-]` is percent-encoded
and an encoded key longer than 200 characters is cut to 183 characters plus
`-` and the first 16 hex characters of the key's SHA-256
(`FileScratch._name`); on Redis it is the key
`attune:harness:scratch:<namespace>:<key>`. The same JSON on both; the file
ends it with a newline. The record is one line of compact JSON, ASCII only,
no NaN, with its fields in this order, so the header opens the record:

| Field | Value |
|---|---|
| `format` | `"attune-harness/scratch"` |
| `format_version` | `2` |
| `writer` | `"<distribution> <version>"` read from the package metadata, for example `"attune-harness 0.6.0.dev0"`; the bare distribution name when the metadata cannot be read |
| `version` | an integer from 1: the successful stashes since the key was last absent. `stash --expected-version N` writes only when the stored record is at `N`; `0` means no record. The count is exact only when every writer to the key passes an expected version: a stash without one reads the record only to count and then overwrites unconditionally, a record a compare-and-set landed a moment before included |
| `key` | the key: 1 to 128 characters of `[A-Za-z0-9_.:-]` |
| `value` | the value as canonical JSON (keys sorted, finite numbers), up to 64 KiB, nested no deeper than the interpreter reads |
| `stored_at` | a UTC stamp: `YYYY-MM-DDTHH:MM:SS`, an optional fraction of one to six digits, then `+00:00` as `datetime.isoformat()` writes an aware UTC time, or `Z`; nothing else |
| `expires_at` | a UTC stamp in the same grammar, or `null` |

What a reader must accept: version 2 as above, and **version 1**, the record
0.4.0 and 0.5.0 wrote, which has exactly the fields `schema_version` (`1`),
`key`, `value`, `stored_at` and `expires_at`, keys sorted, and no header. A
version 1 record is read in place: `retrieve` reports it with
`format_version` 1 and `writer` and `version` `null`; a read never rewrites
it; a `stash --expected-version` over it is refused, since it carries no
version to compare; and the first plain `stash` over it writes version 2 at
record version 1. A record of any other shape is foreign: a later
`format_version`, a `format_version` or `version` that is not an integer
(`2.0`, `true`), a stamp outside the grammar above (naive, another offset, a
space for the `T`), or a value nested deeper than the interpreter reads. A
foreign record is not served and nothing is inferred from it; `keys` skips
it and removes only what has expired; nothing raises; a plain `stash`
writes over it and `forget` removes it, as before. The files in
`tests/fixtures/scratch_legacy_v1/` are version 1 records as 0.5.0's code
wrote them; `tests/test_memory_scratch.py` pins them by digest and reads
them through this code.
