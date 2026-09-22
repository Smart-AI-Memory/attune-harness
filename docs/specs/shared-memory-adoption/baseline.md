# Existing memory compatibility baseline

Status: Task 1 implemented for review; not accepted. No production worker,
live memory migration or activation. Tests use disposable synthetic records.

## What was exercised

The isolated Attune AI checkout is
`/Users/patrickroebuck/attune-ai-memory-adoption`, branch
`codex/shared-memory-adoption`, at
`fe08f282fb0ad9cbb7eedf75af2597336576578e`. It was created after Patrick's
plan/start approval. Its AGENTS.md matches the inspected original. Preflight:
87 passed in 5.62 seconds, one warning about the untouched dirty original main.
The initial sandboxed preflight could not create its `.empathy` test fixture;
the authorized retry passed and its Git status remained clean.

`tests/fixtures/memory_compatibility.json` holds synthetic examples and expected
meaning. `tests/test_memory_compatibility.py` exercises real readers and local
storage; RAG uses its actual installed keyword pipeline. Every destination is
explicit or relocated to a temporary root. Network attempts and personal-memory
author/polish loading fail the tests; no model participant is constructed.

| Tier and existing consumer | Exercised boundary | Finding / obligation for the adapter |
|---|---|---|
| Raw findings: Stop stash hook, session recall/forget hook, memory CLI | JSONL fixtures → `FileStashBackend` → query-based `recall_entries` and SessionStart's query-less `recent_entries`; real sanitizer before stash | All five kinds and correction evidence remain readable. `cwd` is soft ordering, so foreign hits still appear. Missing `recent` capability and a genuinely empty store both return `[]`; new adapters must distinguish them. Preserve unknown stored fields even though recall does not expose them. |
| Personal documents: memory CLI and MCP personal handlers | Existing Markdown → actual `PersonalMemory.query`; private `_resolve_hit_path` plus direct byte inspection | All four document kinds remain findable. Full long source survives and is privately resolvable; public query only returns an excerpt/path. A scoped public full-source resolver is still Task 4 work. Combined roots deduplicate by relative path; separate explicit roots preserve both sources. |
| Curated memories: personal retrieval; derived Redis digest | Existing frontmatter/body → curated parser and personal keyword retrieval; injected-client derived JSON → real digest parser and local emitter | Type, links, review provenance and unknown fields remain in source bytes. Derived node identity/type/description/edges survive parsing. Source-to-Redis hydration and a live Redis transport remain unqualified. |
| Keyed working memory: UnifiedMemory through MCP store/retrieve | Existing `sessions/current.json` → `FileSessionMemory`; existing `kv.json` → `FileStashBackend` | Reopening retains nested values and source bytes. These are actual downstream stores, not a probe of UnifiedMemory auto-initialization or the installed MCP transport. |
| Persisted patterns: UnifiedMemory through MCP persist/recall | Existing pattern JSON → `SecureMemDocsIntegration.retrieve_pattern` with explicit store/audit roots | Content and metadata survive; a stamped foreign workspace is refused. Unstamped INTERNAL legacy records remain readable cross-user by existing policy, so compatibility alone cannot qualify worker exposure. Encryption is deliberately disabled in this synthetic baseline and is not qualified. |

An injected lost-acknowledgment backend writes to one real disposable FileStash
store and returns false. The real legacy service then writes the same record ID
to a second disposable FileStash store and reports success. This demonstrates why
Task 3 needs a strict service seam; a boolean wrapper cannot prove one effect.
The test replaces only fallback construction to ensure it cannot reach the live
default store. New `SessionStashEntry` construction also truncates at 500 chars,
while existing longer stored records remain readable: do not re-author them just
to make a new adapter record.

## Telemetry purpose map

| Purpose | Existing emitter / consumer | Adoption treatment |
|---|---|---|
| Memory-serving frequency | `memory/serve_telemetry.py`: `PersonalMemory.query`, `recall_digest` and `serve_counts`; hook sibling `_memory_telemetry.py` | Preserve local events and maintenance inputs. Real local append/read and opt-outs are checked. |
| Rejection/deletion feedback | `telemetry/memory_events.py`, called from `session_stash._record_rejection`; hook sibling writer | Preserve local feedback. The baseline exercises the real writer and common local sink. |
| Tokens/cost/latency accounting | `telemetry/usage_tracker.py`, `usage.jsonl` and derived summaries | Preserve useful local accounting. A direct instance records synthetic counters without registering a shutdown uploader; no model call is made. |
| Remote-user usage collection | `telemetry/usage_ping.py`; `UsageTracker.get_instance` exit hook; CLI consent prompt and telemetry commands; `config/sections/telemetry.py` | No longer required. Task 4 must prove the new route does not upload, including shutdown and legacy opt-in. The existing product-wide sender/consent/config retirement is separate work. |
| Hosted collection | Uploader names `https://smartaimemory.com/api/usage/` | Source configuration observed only; deployment, reachability and collected data were not inspected or changed. Retire separately with the owning website scope. |
| Durable operation/security records | New worker version/effect records; existing pattern audit | Required controls are distinct from optional telemetry. Their absence must not be treated as an optional logging failure. |

## Verification and limits

Use the explicit Attune checkout on PYTHONPATH with the existing interpreter:

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=/Users/patrickroebuck/attune-ai-memory-adoption/src \
/Users/patrickroebuck/attune-ai/.venv/bin/python -B -m pytest \
  -p no:cacheprovider tests/test_memory_compatibility.py -q --tb=short
```

The optional dependencies must be installed for this qualification; skipped
cases in a dependency-free Harness environment do not qualify compatibility.
Task 1 passes 24 cases. Four disposable guard/emitter removals are all detected;
five of the 24 cases fail under at least one removal. The source trees and
frozen experimental files were not modified by those mutation runs. Focused
Ruff error checks pass. The Sol/high evidence-chain review raised four findings;
all were fixed and its targeted recheck found no remaining Task 1 blocker.
Receipts and source hashes are in `docs/receipts/shared-memory-adoption-task1/`.

Task 1 verification uses these offline behavioral checks, mutation probes and
different-model review. The legacy `PipelineOrchestrator` provider-backed quality
runner was not used: it launches separate code-review/security-audit provider
workflows and uses `uv run` for tests, outside this approved offline execution
method. No pass or numeric review grade is claimed for that runner. Any displayed
Task 1 completion score describes 24/24 baseline checks, not a model quality score
or qualification of the future adapter. This method is disclosed at task acceptance.

This baseline does not qualify production adapter security, installed CLI/MCP
dispatch, encrypted records, live Redis/AMS, concurrent managed updates, context
refresh, deployment, or native model behavior. Those remain Tasks 2–5. Existing
fixture observations must not be labeled guarantees for the new worker.
