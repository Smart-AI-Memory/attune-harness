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
row pins, in 71 rows:

- **success** (55 rows): the verb did its work offline on a small fixture;
  a paused, cancelled or draft record is a success of its control verb.
- **refusal** (6 rows): an offline refusal on purpose. `build` before the work
  is accepted; `index build` without `--allow-provider`; `index update`,
  `index inspect` and `retrieval-task` naming a generation that was never
  built; `memory capabilities` with a config that is not the roots contract,
  refused by the default reader in its own words. Voyage is never called.
- **unavailable** (9 rows): a dependency or server this install does not
  have. The memory host route (`capabilities` through `execute`) with
  `reader: adapter` needs the attune-ai adapter, which no base or extra
  install carries; a configured Redis that refuses the connection.
- **disabled** (1 row): the memory config has no `scratch` section.

The four `-adapter` rows pin the memory host's success shapes over an
in-process double of the adapter's four-member contract (`binding`,
`capabilities`, `query`, `resolve`), since no install carries the adapter;
the four `-native` rows pin the same shapes through Harness's own reader,
the default since Phase 2 step 2.4 (D19), over a raw root.

Two verbs are not pinned. `mcp-serve` speaks the MCP protocol on stdout and
prints no envelope, and `--help`/`--help-all` print text. Seven rows run on
POSIX only: `fix-intake`, `test-preview` and `status-test`, because the `test`
verb qualifies the POSIX execution profile and the repair probe fixture is a
POSIX one; and the four `-native` rows, because the native memory reader's
descriptor walk is POSIX-only at 0.5.0 (D19). A `-` in the `schema_version` or
`status` column means the envelope has no such key: the feature-work verbs
(`plan`, `build` and their `status`) and `memory scratch` carry no
`schema_version`, and `code-config`, `triage-check`, `repair-economics` and
`github-checks` carry no `status`.

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
| `plan-request` | success | 0 | - | `draft` | `advisory` `authoring` `authority` `blocking` `checkpoint_digest` `completed` `controls` `evidence` `execution_evidence` `intent` `missing` `next_action` `note` `phase` `preserved_completion` `questions` `record_path` `revision` `status` `summary` `task_directory` `task_id` `tasks` |
| `plan-decision` | success | 0 | - | `draft` | `advisory` `authoring` `authority` `blocking` `checkpoint_digest` `completed` `controls` `decision` `evidence` `execution_evidence` `intent` `missing` `next_action` `note` `phase` `preserved_completion` `questions` `record_path` `revision` `status` `summary` `task_directory` `task_id` `tasks` |
| `status-work` | success | 0 | - | `draft` | `advisory` `authoring` `authority` `blocking` `checkpoint_digest` `completed` `controls` `evidence` `execution_evidence` `intent` `missing` `next_action` `note` `phase` `preserved_completion` `questions` `record_path` `revision` `status` `summary` `task_directory` `task_id` `tasks` |
| `build-draft` | refusal | 2 | - | `failed` | `blocking` `error` `evidence` `next_action` `record_path` `status` `summary` |
| `extension-discover` | success | 0 | 1 | `ready` | `bundle` `operation` `request_id` `schema_version` `status` |
| `extension-install` | success | 0 | 1 | `disabled` | `artifact_digest` `id` `manifest` `operation` `revision` `schema_version` `state_digest` `status` |
| `extension-enable` | success | 0 | 1 | `enabled` | `artifact_digest` `id` `manifest` `operation` `revision` `schema_version` `state_digest` `status` |
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
| `triage-check` | success | 0 | 1 | - | `action` `atomic_claim_required` `dispatch_authorized` `key` `reason` `schema_version` |
| `repair-economics` | success | 0 | 1 | - | `eligible_cost_ranking` `note` `schema_version` `scope` `strategies` |
| `github-checks` | success | 0 | 1 | - | `all_checks_passed` `checks` `note` `repair_verified` `repository` `revision` `schema_version` |
| `mcp-inspect` | success | 0 | 1 | `completed` | `accepted` `completion_scope` `events` `identity_scope` `max_calls` `operation` `participant_id` `profile` `record_path` `registry` `request_id` `requirement_revision` `schema_version` `source_snapshot` `status` `tools` |
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
| `memory-scratch-capabilities` | success | 0 | - | `ok` | `backend` `location` `operation` `realtime` `shared` `status` |
| `memory-scratch-stash` | success | 0 | - | `ok` | `backend` `expires_at` `key` `operation` `status` `stored_at` |
| `memory-scratch-retrieve` | success | 0 | - | `ok` | `backend` `expires_at` `key` `operation` `status` `stored_at` `value` |
| `memory-scratch-forget` | success | 0 | - | `ok` | `backend` `forgotten` `key` `operation` `status` |
| `memory-scratch-keys` | success | 0 | - | `ok` | `backend` `keys` `operation` `pattern` `status` |
| `memory-scratch-disabled` | disabled | 2 | - | `disabled` | `detail` `status` |

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
- `memory-scratch-retrieve`: `memory --config scratch retrieve KEY`
- `memory-scratch-forget`: `memory --config scratch forget KEY`
- `memory-scratch-keys`: `memory --config scratch keys PATTERN`
- `memory-scratch-disabled`: `memory --config scratch capabilities` with no `scratch` section
