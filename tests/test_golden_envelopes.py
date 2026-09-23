"""Golden envelopes: the top-level keys, schema_version, status and exit code of every CLI verb.

Every ``attune-harness`` verb prints one JSON object. Before 1.0 promises that
these envelopes stop changing, a change to one must be a deliberate diff:
each row of ``ENVELOPES`` pins one verb (or one subcommand) on the cheapest
deterministic fixture that yields an envelope, so renaming or dropping a
top-level key fails exactly the case whose id names the verb. Only key names,
``schema_version`` and ``status`` are compared, never values such as
timestamps, digests or request ids. ``docs/envelopes.md`` carries the same
table; ``test_documented_table_matches`` keeps the two honest.
"""

# qualify: platform

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from attune_harness import extensions as ext
from attune_harness import memory_redis
from attune_harness.cli import main
from attune_harness.memory_redis import MemoryRedisUnavailable, RedisMemory
from attune_harness.review import review
from attune_harness.review_store import PersistenceError, RunStore, read_record
from attune_harness.task_contract import accept_task, read_task
from attune_harness.task_policies import execute_task
from test_extensions import bundle  # noqa: F401  (fixture)
from test_github_checks import payload as github_payload
from test_memory_redis import SETTINGS as REDIS_SETTINGS, FakeError, FakeRedis
from test_operations import event as check_event, ledger as repair_ledger
from test_review import case, change, change_config, scripted  # noqa: F401  (fixture: case)
from test_task_contract import draft, response

POSIX_ONLY = pytest.mark.skipif(
    os.name != "posix", reason="the verb qualifies the POSIX execution profile only"
)
SIXTY_FOUR = "a" * 64
FORTY = "a" * 40

# The compatibility surface. One row per pinned invocation:
#   (case id, path pinned, exit code, schema_version or None, status or None, sorted top-level keys)
# Paths: success, refusal (an offline refusal on purpose), unavailable (a dependency or server
# this install does not have), disabled (no configuration section). A change to a row is a
# deliberate diff; the 1.0 changelog points at docs/envelopes.md, which lists the same rows.
# fmt: off
ENVELOPES = (
    ('demo', 'success', 0, None, 'verified',
     ('check', 'error', 'output', 'participant_id', 'status', 'task')),
    ('review-form', 'success', 0, 1, 'ready',
     ('definition', 'form_revision', 'markdown', 'operation', 'request_id', 'schema_version',
      'status', 'submission')),
    ('review-legacy', 'success', 0, 1, 'completed',
     ('accepted', 'artifacts', 'checkpoint_digest', 'document_outcome', 'events',
      'external_execution_enabled', 'initial_retrieval', 'operation', 'participants',
      'preflight_verification', 'record_path', 'recovery', 'registry', 'request_id',
      'requirement_revision', 'retrieval_outcome', 'run_id', 'schema_version', 'status',
      'verification', 'verification_scope')),
    ('inspect-review', 'success', 0, 1, 'completed',
     ('accepted', 'artifacts', 'checkpoint_digest', 'document_outcome', 'events',
      'external_execution_enabled', 'initial_retrieval', 'operation', 'participants',
      'preflight_verification', 'record_path', 'recovery', 'registry', 'request_id',
      'requirement_revision', 'retrieval_outcome', 'run_id', 'schema_version', 'status',
      'verification', 'verification_scope')),
    ('transfer-review', 'success', 1, 1, 'paused',
     ('accepted', 'artifacts', 'checkpoint_digest', 'events', 'external_execution_enabled',
      'initial_retrieval', 'operation', 'participants', 'preflight_verification', 'record_path',
      'recovery', 'registry', 'request_id', 'requirement_revision', 'run_id', 'schema_version',
      'status', 'verification_scope')),
    ('resume-review', 'success', 0, 1, 'completed',
     ('accepted', 'artifacts', 'checkpoint_digest', 'document_outcome', 'events',
      'external_execution_enabled', 'initial_retrieval', 'operation', 'participants',
      'preflight_verification', 'record_path', 'recovery', 'registry', 'request_id',
      'requirement_revision', 'retrieval_outcome', 'run_id', 'schema_version', 'status',
      'verification', 'verification_scope')),
    ('reconcile-review', 'success', 1, 1, 'paused',
     ('accepted', 'artifacts', 'checkpoint_digest', 'events', 'external_execution_enabled',
      'initial_retrieval', 'operation', 'participants', 'preflight_verification', 'record_path',
      'recovery', 'registry', 'request_id', 'requirement_revision', 'run_id', 'schema_version',
      'status', 'verification_scope')),
    ('cancel-review', 'success', 1, 1, 'cancelled',
     ('accepted', 'artifacts', 'checkpoint_digest', 'error', 'events',
      'external_execution_enabled', 'initial_retrieval', 'operation', 'participants',
      'preflight_verification', 'record_path', 'recovery', 'registry', 'request_id',
      'requirement_revision', 'run_id', 'schema_version', 'status', 'verification_scope')),
    ('status-review', 'success', 0, 1, 'completed',
     ('accepted', 'artifacts', 'checkpoint_digest', 'document_outcome', 'events',
      'external_execution_enabled', 'initial_retrieval', 'operation', 'participants',
      'preflight_verification', 'record_path', 'recovery', 'registry', 'request_id',
      'requirement_revision', 'retrieval_outcome', 'run_id', 'schema_version', 'status',
      'verification', 'verification_scope')),
    ('review-goal-intake', 'success', 0, 1, 'accepted',
     ('answers', 'defaults_origin', 'definition', 'execution_status', 'intake_metrics', 'markdown',
      'note', 'operation', 'repair_contract', 'revision', 'schema_version', 'status', 'submission',
      'task_directory', 'task_id')),
    ('review-task-response', 'success', 0, 1, 'completed',
     ('acceptance', 'bindings', 'checkpoint_digest', 'events', 'execution', 'history', 'operation',
      'record_path', 'recovery', 'request', 'schema_version', 'status', 'task_profile')),
    ('status-task', 'success', 0, 1, 'paused',
     ('acceptance', 'bindings', 'checkpoint_digest', 'events', 'execution', 'history', 'operation',
      'record_path', 'recovery', 'request', 'schema_version', 'status', 'task_profile')),
    ('resume-task', 'success', 0, 1, 'completed',
     ('acceptance', 'bindings', 'checkpoint_digest', 'events', 'execution', 'history', 'operation',
      'record_path', 'recovery', 'request', 'schema_version', 'status', 'task_profile')),
    ('reconcile-task', 'success', 1, 1, 'paused',
     ('acceptance', 'bindings', 'checkpoint_digest', 'events', 'execution', 'history', 'operation',
      'record_path', 'recovery', 'request', 'schema_version', 'status', 'task_profile')),
    ('transfer-task', 'success', 1, 1, 'paused',
     ('acceptance', 'bindings', 'checkpoint_digest', 'events', 'execution', 'history', 'operation',
      'record_path', 'recovery', 'request', 'schema_version', 'status', 'task_profile')),
    ('cancel-task', 'success', 1, 1, 'cancelled',
     ('acceptance', 'bindings', 'checkpoint_digest', 'events', 'execution', 'history', 'operation',
      'record_path', 'recovery', 'request', 'schema_version', 'status', 'task_profile')),
    ('fix-intake', 'success', 0, 1, 'accepted',
     ('answers', 'defaults_origin', 'definition', 'execution_status', 'intake_metrics', 'markdown',
      'note', 'operation', 'repair_contract', 'revision', 'schema_version', 'status', 'submission',
      'task_directory', 'task_id')),
    ('test-preview', 'success', 1, 1, 'draft',
     ('checkpoint_digest', 'execution_evidence', 'operation', 'presentation', 'record_path',
      'schema_version', 'status', 'task_profile')),
    ('status-test', 'success', 0, 1, 'draft',
     ('checkpoint_digest', 'execution_evidence', 'operation', 'presentation', 'record_path',
      'schema_version', 'status', 'task_profile')),
    ('plan-request', 'success', 0, None, 'draft',
     ('advisory', 'authoring', 'authority', 'blocking', 'checkpoint_digest', 'completed',
      'controls', 'evidence', 'execution_evidence', 'intent', 'missing', 'next_action', 'note',
      'phase', 'preserved_completion', 'questions', 'record_path', 'revision', 'status', 'summary',
      'task_directory', 'task_id', 'tasks')),
    ('plan-decision', 'success', 0, None, 'draft',
     ('advisory', 'authoring', 'authority', 'blocking', 'checkpoint_digest', 'completed',
      'controls', 'decision', 'evidence', 'execution_evidence', 'intent', 'missing', 'next_action',
      'note', 'phase', 'preserved_completion', 'questions', 'record_path', 'revision', 'status',
      'summary', 'task_directory', 'task_id', 'tasks')),
    ('status-work', 'success', 0, None, 'draft',
     ('advisory', 'authoring', 'authority', 'blocking', 'checkpoint_digest', 'completed',
      'controls', 'evidence', 'execution_evidence', 'intent', 'missing', 'next_action', 'note',
      'phase', 'preserved_completion', 'questions', 'record_path', 'revision', 'status', 'summary',
      'task_directory', 'task_id', 'tasks')),
    ('build-draft', 'refusal', 2, None, 'failed',
     ('blocking', 'error', 'evidence', 'next_action', 'record_path', 'status', 'summary')),
    ('extension-discover', 'success', 0, 1, 'ready',
     ('bundle', 'operation', 'request_id', 'schema_version', 'status')),
    ('extension-install', 'success', 0, 1, 'disabled',
     ('artifact_digest', 'id', 'manifest', 'operation', 'revision', 'schema_version',
      'state_digest', 'status')),
    ('extension-enable', 'success', 0, 1, 'enabled',
     ('artifact_digest', 'id', 'manifest', 'operation', 'revision', 'schema_version',
      'state_digest', 'status')),
    ('extension-inspect', 'success', 0, 1, 'enabled',
     ('artifact_digest', 'id', 'manifest', 'operation', 'revision', 'schema_version',
      'state_digest', 'status')),
    ('extension-disable', 'success', 0, 1, 'disabled',
     ('artifact_digest', 'id', 'manifest', 'operation', 'revision', 'schema_version',
      'state_digest', 'status')),
    ('extension-replace', 'success', 0, 1, 'disabled',
     ('artifact_digest', 'id', 'manifest', 'operation', 'revision', 'schema_version',
      'state_digest', 'status')),
    ('extension-remove', 'success', 0, 1, 'removed',
     ('artifact_digest', 'id', 'manifest', 'operation', 'revision', 'schema_version',
      'state_digest', 'status')),
    ('code-config', 'success', 0, 1, None,
     ('allow_overlays', 'allow_untracked', 'batch_size', 'candidates', 'exclude', 'include',
      'index_dir', 'max_bytes', 'max_file_bytes', 'max_files', 'max_provider_calls',
      'max_request_bytes', 'passage_bytes', 'roots', 'schema_version', 'structured_paths')),
    ('index-plan', 'success', 0, 1, 'ready',
     ('config_digest', 'embedding_input_bytes', 'estimate_scope', 'estimated_embedding_cost_usd',
      'estimated_tokens', 'generation', 'manifest', 'operation', 'passages',
      'planned_embedding_calls', 'profile', 'provider_calls', 'rate_snapshot', 'request_id',
      'schema_version', 'status')),
    ('index-build', 'refusal', 2, 1, 'failed',
     ('error', 'operation', 'request_id', 'schema_version', 'status')),
    ('index-update', 'refusal', 2, 1, 'failed',
     ('error', 'operation', 'request_id', 'schema_version', 'status')),
    ('index-inspect', 'refusal', 2, 1, 'failed',
     ('error', 'operation', 'request_id', 'schema_version', 'status')),
    ('retrieval-task', 'refusal', 2, 1, 'failed',
     ('error', 'operation', 'request_id', 'schema_version', 'status')),
    ('triage-check', 'success', 0, 1, None,
     ('action', 'atomic_claim_required', 'dispatch_authorized', 'key', 'reason', 'schema_version')),
    ('repair-economics', 'success', 0, 1, None,
     ('eligible_cost_ranking', 'note', 'schema_version', 'scope', 'strategies')),
    ('github-checks', 'success', 0, 1, None,
     ('all_checks_passed', 'checks', 'note', 'repair_verified', 'repository', 'revision',
      'schema_version')),
    ('mcp-inspect', 'success', 0, 1, 'completed',
     ('accepted', 'completion_scope', 'events', 'identity_scope', 'max_calls', 'operation',
      'participant_id', 'profile', 'record_path', 'registry', 'request_id', 'requirement_revision',
      'schema_version', 'source_snapshot', 'status', 'tools')),
    ('verify', 'success', 0, 1, 'verified',
     ('artifacts', 'dependency', 'operation', 'passed', 'request_id', 'result', 'schema_version',
      'status')),
    ('retrieve', 'success', 0, 1, 'retrieved',
     ('corpus', 'dependency', 'k', 'operation', 'query', 'request_id', 'retriever',
      'schema_version', 'sources', 'status')),
    ('memory-capabilities', 'unavailable', 2, None, 'unavailable',
     ('detail', 'error', 'status')),
    ('memory-recall', 'unavailable', 2, None, 'unavailable',
     ('detail', 'error', 'status')),
    ('memory-resolve', 'unavailable', 2, None, 'unavailable',
     ('detail', 'error', 'status')),
    ('memory-refresh', 'unavailable', 2, None, 'unavailable',
     ('detail', 'error', 'status')),
    ('memory-create', 'unavailable', 2, None, 'unavailable',
     ('detail', 'error', 'status')),
    ('memory-replay', 'unavailable', 2, None, 'unavailable',
     ('detail', 'error', 'status')),
    ('memory-inspect', 'unavailable', 2, None, 'unavailable',
     ('detail', 'error', 'status')),
    ('memory-execute', 'unavailable', 2, None, 'unavailable',
     ('detail', 'error', 'status')),
    ('memory-capabilities-adapter', 'success', 0, None, None,
     ('context_refresh', 'mutation_status', 'native_worker', 'read', 'retained_paths',
      'worker_execution', 'worker_mutations')),
    ('memory-recall-adapter', 'success', 0, 1, 'available',
     ('authority', 'guidance', 'items', 'k', 'max_chars', 'operation', 'problems', 'query',
      'schema_version', 'status')),
    ('memory-resolve-adapter', 'success', 0, None, None,
     ('authority', 'classification', 'id', 'kind', 'locator', 'metadata', 'owner', 'scope',
      'text', 'version')),
    ('memory-refresh-adapter', 'success', 0, None, 'available',
     ('context', 'invalidated_ids', 'replaces', 'status')),
    ('memory-redis-status', 'success', 0, 1, 'ok',
     ('active_nodes', 'authority', 'guidance', 'items', 'layers', 'operation', 'schema_version',
      'status')),
    ('memory-redis-digest', 'success', 0, 1, 'ok',
     ('authority', 'guidance', 'items', 'limit', 'operation', 'schema_version', 'status')),
    ('memory-redis-related', 'success', 0, 1, 'ok',
     ('authority', 'guidance', 'id', 'items', 'operation', 'schema_version', 'status')),
    ('memory-redis-node', 'success', 0, 1, 'ok',
     ('authority', 'guidance', 'id', 'items', 'operation', 'schema_version', 'status')),
    ('memory-redis-search', 'success', 0, 1, 'ok',
     ('authority', 'guidance', 'items', 'k', 'layer', 'operation', 'query', 'schema_version',
      'status', 'total')),
    ('memory-redis-unreachable', 'unavailable', 2, None, 'unavailable',
     ('detail', 'error', 'status')),
    ('memory-scratch-capabilities', 'success', 0, None, 'ok',
     ('backend', 'location', 'operation', 'realtime', 'shared', 'status')),
    ('memory-scratch-stash', 'success', 0, None, 'ok',
     ('backend', 'expires_at', 'key', 'operation', 'status', 'stored_at')),
    ('memory-scratch-retrieve', 'success', 0, None, 'ok',
     ('backend', 'expires_at', 'key', 'operation', 'status', 'stored_at', 'value')),
    ('memory-scratch-forget', 'success', 0, None, 'ok',
     ('backend', 'forgotten', 'key', 'operation', 'status')),
    ('memory-scratch-keys', 'success', 0, None, 'ok',
     ('backend', 'keys', 'operation', 'pattern', 'status')),
    ('memory-scratch-disabled', 'disabled', 2, None, 'disabled',
     ('detail', 'status')),
)
# fmt: on

TABLE = {row[0]: row for row in ENVELOPES}
SCENARIOS = {}


def scenario(case_id, *marks):
    """Register the function that drives one pinned invocation and returns (exit code, envelope)."""

    def register(fn):
        SCENARIOS[case_id] = pytest.param(fn, id=case_id, marks=marks)
        return fn

    return register


def git(root, *args):
    hooks = root.parent / "no-hooks"
    hooks.mkdir(exist_ok=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            f"core.hooksPath={hooks}",
            *args,
        ],
        check=True,
        capture_output=True,
    )


def repository(root, files):
    root.mkdir()
    for name, text in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
    git(root, "add", ".")
    git(root, "commit", "-qm", "fixture")
    return root


def write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


class World:
    """One verb run: the fixtures, the in-process CLI and its parsed stdout."""

    def __init__(self, tmp_path, monkeypatch, capsys, case, bundle):
        self.tmp, self.monkeypatch, self.capsys = tmp_path, monkeypatch, capsys
        self.case, self.bundle = case, bundle
        self.request, self.config, self.run_dir = case
        self.root = self.request.parent  # the review fixture's project root
        self.task = self.run_dir  # a fresh directory the task fixtures create

    def run(self, argv):
        code = main([str(a) for a in argv])
        return code, json.loads(self.capsys.readouterr().out)

    # Shared journeys, each cheap and offline.
    def paused_review(self):
        change_config(
            self.case, lambda d: d["participants"].update(gamma=dict(d["participants"]["alpha"]))
        )
        _, paused = self.run(
            [
                "review",
                self.request,
                "--config",
                self.config,
                "--run-dir",
                self.run_dir,
                "--max-operations",
                "4",
            ]
        )
        assert paused["status"] == "paused"
        return paused

    def paused_task(self, boundary=2, **kwargs):
        draft(self.case, **kwargs)
        accept_task(self.task, response(self.task))
        return execute_task(self.task, max_operations=boundary)

    def installed_extension(self):
        state = self.tmp / "extension-state"
        return state, ext.install(self.bundle, state)

    def work(self):
        project = self.tmp / "work-project"
        project.mkdir()
        (project / "source.py").write_text("def value():\n    return 1\n", encoding="utf-8")
        (project / "plan.md").write_text("Preserve all findings.\n", encoding="utf-8")
        participant = {"adapter": "deterministic", "tools": [], "max_turns": 1, "max_tool_calls": 0}
        config = write_json(
            self.tmp / "work-participants.json",
            {"schema_version": 1, "participants": {"local": participant, "critic": participant}},
        )
        budget = {"max_operations": 20, "max_attempts": 1, "max_output_bytes": 10000}
        request = write_json(
            self.tmp / "work-request.json",
            {
                "intent": {
                    "goal": "Export every finding",
                    "context": ["Default JSON must survive"],
                    "scope": ["source.py", "export.py"],
                    "constraints": ["Preserve unknown claims"],
                    "acceptance": ["CLI exports every finding"],
                    "questions": [],
                },
                "assignments": [
                    {
                        "role": "planner",
                        "participant": "local",
                        "output_contract": "Bounded plan with observable checks",
                        "budgets": budget,
                    }
                ],
                "inputs": ["source.py"],
                "artifact": "plan.md",
                "budget": budget,
            },
        )
        directory = self.tmp / "work"
        return directory, [
            "plan",
            "--task-dir",
            directory,
            "--request",
            request,
            "--project",
            project,
            "--config",
            config,
        ]

    def test_project(self):
        root = repository(
            self.tmp / "test-project",
            {
                ".gitignore": "__pycache__/\n.pytest_cache/\n",
                "src/demo/logic.py": "def answer():\n    return 42\n",
                "tests/test_logic.py": "from demo.logic import answer\ndef test_answer():\n    assert answer() == 42\n",
            },
        )
        (root / "src/demo/logic.py").write_text(
            "# changed\ndef answer():\n    return 42\n", encoding="utf-8"
        )
        directory = self.tmp / "test-task"
        return directory, [
            "test",
            "--project",
            root,
            "--task-dir",
            directory,
            "--scope",
            "src/demo/logic.py",
            "--interpreter",
            sys.executable,
        ]

    def index_config(self):
        from attune_harness.voyage_sources import config

        root = repository(
            self.tmp / "app",
            {
                "app.py": 'def save_cart():\n    return "persisted"\n',
                "README.md": "# App\n\nSelected application conventions.\n",
            },
        )
        cfg = config(
            {
                "schema_version": 1,
                "roots": [{"repo_id": "app", "path": str(root)}],
                "index_dir": str(self.tmp / "index"),
            },
            self.tmp,
        )
        return write_json(self.tmp / "index-config.json", cfg)

    def memory_config(self, value):
        self.monkeypatch.delenv("ATTUNE_MEMORY_WORKER", raising=False)
        return ["memory", "--config", write_json(self.tmp / "memory.json", value)]

    def memory_host(self):
        # The current-memory adapter lives in attune-ai, which no base or extra install carries;
        # pin the unavailable report the same way on every machine.
        self.monkeypatch.setitem(sys.modules, "attune", None)
        return self.memory_config({"roots": []})

    def faked_adapter(self):
        """The adapter's four-member contract as an in-process double.

        The success envelopes are Harness's own shapes (memory_context.py) over
        whatever object answers `binding`, `capabilities()`, `query()` and
        `resolve()`; pinning them here is the contract the native reader of
        Phase 2 must satisfy, on every platform, with attune-ai absent.
        """
        import types

        binding = {"roots": "double", "digest": "0" * 8}
        item = dict(id="doc-1", locator="root/doc.md", version="v1", authority=binding,
                    text="Quartz retention policy: keep audit logs ninety days.", kind="reference",
                    metadata={"path": "root/doc.md"}, scope="project", owner="patrick",
                    classification="internal")

        class CompatibilityAdapter:
            def __init__(self, config):
                self.binding = binding

            def capabilities(self):
                return dict(read=["raw", "personal", "curated"], worker_mutations=[],
                            mutation_status="unavailable", retained_paths=[])

            def query(self, query, k=10):
                return dict(status="available", items=[dict(item)], problems=[],
                            authority=binding, capabilities=self.capabilities())

            def resolve(self, handle):
                return dict(item)

        package = types.ModuleType("attune")
        memory = types.ModuleType("attune.memory")
        adapter = types.ModuleType("attune.memory.harness_adapter")
        adapter.CompatibilityAdapter = CompatibilityAdapter
        package.memory, memory.harness_adapter = memory, adapter
        for name, module in (("attune", package), ("attune.memory", memory),
                             ("attune.memory.harness_adapter", adapter)):
            self.monkeypatch.setitem(sys.modules, name, module)
        return self.memory_config({"roots": []})

    def fake_redis(self):
        self.monkeypatch.setattr(
            memory_redis,
            "connect",
            lambda settings, **k: RedisMemory(FakeRedis(), settings, "h", errors=(FakeError,)),
        )
        return self.memory_config({"redis": REDIS_SETTINGS}) + ["redis"]

    def file_scratch(self):
        root = self.tmp / "scratch"
        root.mkdir()
        return self.memory_config({"scratch": {"backend": "file", "root": str(root)}}) + ["scratch"]


# The bare invocation and the legacy review family.


@scenario("demo")
def _(w):
    return w.run([])


@scenario("review-form")
def _(w):
    return w.run(["review-form", "--config", w.config])


@scenario("review-legacy")
def review_legacy(w):
    return w.run(["review", w.request, "--config", w.config, "--run-dir", w.run_dir])


@scenario("inspect-review")
def _(w):
    review_legacy(w)
    return w.run(["inspect-review", w.run_dir])


@scenario("transfer-review")
def _(w):
    paused = w.paused_review()
    return w.run(
        [
            "transfer-review",
            w.run_dir,
            "--checkpoint",
            paused["checkpoint_digest"],
            "--lead",
            "gamma",
            "--reason",
            "Continue",
        ]
    )


@scenario("resume-review")
def _(w):
    paused = w.paused_review()
    return w.run(
        [
            "resume-review",
            w.run_dir,
            "--request",
            w.request,
            "--config",
            w.config,
            "--checkpoint",
            paused["checkpoint_digest"],
        ]
    )


@scenario("reconcile-review")
def _(w):
    def stop(data):
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        review(
            w.request,
            w.config,
            w.run_dir,
            exchange_factory=scripted({"kind": "final", "text": "never"}, stop),
        )
    record = read_record(w.run_dir)
    event = record["events"][-1]
    reply = write_json(
        w.tmp / "reply.json",
        {
            "schema_version": 1,
            "request_digest": event["request_digest"],
            "action": {"kind": "final", "text": "Recovered"},
        },
    )
    return w.run(
        [
            "reconcile-review",
            w.run_dir,
            "--checkpoint",
            record["checkpoint_digest"],
            "--event",
            event["event_id"],
            "--reply",
            reply,
        ]
    )


@scenario("cancel-review")
def _(w):
    paused = w.paused_review()
    return w.run(
        [
            "cancel-review",
            w.run_dir,
            "--checkpoint",
            paused["checkpoint_digest"],
            "--reason",
            "Stop",
        ]
    )


@scenario("status-review")
def _(w):
    review_legacy(w)
    return w.run(["status", w.run_dir])


# The task verbs: assessment intake and execution, repair intake, the captured-change test.


@scenario("review-goal-intake")
def _(w):
    return w.run(
        [
            "review",
            "--goal",
            "Check the guide",
            "--project",
            w.root,
            "--config",
            w.config,
            "--task-dir",
            w.task,
            "--criteria",
            "Identify unsupported claims",
            "--query",
            "quartz retention policy",
            "--document",
            "project/guide.md",
            "--context",
            "context.json",
            "--corpus",
            "project",
            "--assessor",
            "alpha",
            "--accept",
            "--intake-only",
        ]
    )


@scenario("review-task-response")
def _(w):
    draft(w.case)
    return w.run(
        [
            "review",
            "--task-response",
            write_json(w.tmp / "response.json", response(w.task)),
            "--task-dir",
            w.task,
        ]
    )


@scenario("status-task")
def _(w):
    w.paused_task()
    return w.run(["status", w.task])


@scenario("resume-task")
def _(w):
    w.paused_task()
    return w.run(["resume", w.task])


@scenario("reconcile-task")
def _(w):
    draft(w.case)
    accept_task(w.task, response(w.task))
    original = RunStore.save

    def lose_acknowledgement(store, record):
        events = record.get("execution", {}).get("events", [])
        if any(e["kind"] == "participant_turn" and e["state"] == "completed" for e in events):
            raise PersistenceError("lost acknowledgement")
        return original(store, record)

    with w.monkeypatch.context() as m:
        m.setattr(RunStore, "save", lose_acknowledgement)
        with pytest.raises(PersistenceError):
            execute_task(
                w.task, exchange_factory=scripted({"kind": "final", "text": "Recovered assessment"})
            )
    persisted = read_task(w.task)
    event = persisted["execution"]["events"][-1]
    reply = write_json(
        w.tmp / "reply.json",
        {
            "schema_version": 1,
            "request_digest": event["request_digest"],
            "action": {"kind": "final", "text": "Recovered assessment"},
        },
    )
    return w.run(
        [
            "reconcile-task",
            w.task,
            "--checkpoint",
            persisted["checkpoint_digest"],
            "--event",
            event["event_id"],
            "--reply",
            reply,
        ]
    )


@scenario("transfer-task")
def _(w):
    change(w.config, lambda d: d["participants"].update(gamma=dict(d["participants"]["alpha"])))
    w.paused_task(boundary=3, plan="independent-review")
    return w.run(["transfer-task", w.task, "--assessor", "gamma", "--reason", "Fresh assessment"])


@scenario("cancel-task")
def _(w):
    w.paused_task()
    return w.run(["cancel-task", w.task, "--reason", "Stop"])


@scenario("fix-intake", POSIX_ONLY)
def _(w):
    checkout = w.root / "checkout"
    checkout.mkdir()
    (checkout / ".git").mkdir()  # the repair contract wants a dedicated checkout; it never runs git
    (checkout / "app.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (checkout / "probe.py").write_text(
        "from app import add\nassert add(2, 3) == 5\n", encoding="utf-8"
    )
    probe = write_json(
        w.tmp / "probe.json",
        {
            "argv": [sys.executable, "-B", "probe.py"],
            "cwd": ".",
            "timeout": 10,
            "max_output_bytes": 4096,
            "environment": {
                "PATH": "/usr/bin:/bin",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
            },
            "oracle_paths": ["probe.py"],
        },
    )
    participant = {"adapter": "deterministic", "tools": [], "max_turns": 1, "max_tool_calls": 0}
    registry = write_json(
        w.tmp / "repair-registry.json",
        {"schema_version": 1, "participants": {"worker": participant, "reviewer": participant}},
    )
    return w.run(
        [
            "fix",
            "--goal",
            "Correct addition",
            "--project",
            w.root,
            "--config",
            registry,
            "--checkout",
            checkout,
            "--scope",
            "app.py",
            "--probe",
            probe,
            "--criteria",
            "2+3=5",
            "--worker",
            "worker",
            "--reviewer",
            "reviewer",
            "--task-dir",
            w.tmp / "repair",
            "--accept",
            "--intake-only",
        ]
    )


@scenario("test-preview", POSIX_ONLY)
def _(w):
    _, argv = w.test_project()
    return w.run(argv)


@scenario("status-test", POSIX_ONLY)
def _(w):
    directory, argv = w.test_project()
    w.run(argv)
    return w.run(["status", directory])


# Feature work: plan, its decision preview, status, and build's refusal before acceptance.


@scenario("plan-request")
def _(w):
    _, argv = w.work()
    return w.run(argv)


@scenario("plan-decision")
def _(w):
    directory, argv = w.work()
    w.run(argv)
    return w.run(["plan", "--task-dir", directory, "--decision"])


@scenario("status-work")
def _(w):
    directory, argv = w.work()
    w.run(argv)
    return w.run(["status", directory])


@scenario("build-draft")
def _(w):
    directory, argv = w.work()
    w.run(argv)
    return w.run(["build", directory])


# The extension lifecycle.


@scenario("extension-discover")
def _(w):
    return w.run(["extension", "discover", w.bundle])


@scenario("extension-install")
def _(w):
    return w.run(["extension", "install", w.bundle, "--state-dir", w.tmp / "extension-state"])


@scenario("extension-enable")
def _(w):
    state, first = w.installed_extension()
    return w.run(
        ["extension", "enable", "--state-dir", state, "--checkpoint", first["state_digest"]]
    )


@scenario("extension-inspect")
def _(w):
    state, first = w.installed_extension()
    ext.mutate(state, first["state_digest"], "enable")
    return w.run(["extension", "inspect", "--state-dir", state])


@scenario("extension-disable")
def _(w):
    state, first = w.installed_extension()
    enabled = ext.mutate(state, first["state_digest"], "enable")
    return w.run(
        ["extension", "disable", "--state-dir", state, "--checkpoint", enabled["state_digest"]]
    )


@scenario("extension-replace")
def _(w):
    state, first = w.installed_extension()
    return w.run(
        [
            "extension",
            "replace",
            "--state-dir",
            state,
            "--checkpoint",
            first["state_digest"],
            "--manifest",
            w.bundle,
        ]
    )


@scenario("extension-remove")
def _(w):
    state, first = w.installed_extension()
    return w.run(
        ["extension", "remove", "--state-dir", state, "--checkpoint", first["state_digest"]]
    )


# Repository-first retrieval: the offline plan, and the refusals that keep Voyage out.


@scenario("code-config")
def _(w):
    repo = w.tmp / "code-repo"
    repo.mkdir()
    (repo / "cart.py").write_text("def save_cart():\n    return True\n", encoding="utf-8")
    return w.run(["code-config", "--repo", repo, "--index-dir", w.tmp / "code-index"])


@scenario("index-plan")
def _(w):
    return w.run(["index", "plan", "--config", w.index_config()])


@scenario("index-build")
def _(w):
    return w.run(["index", "build", "--config", w.index_config()])  # no --allow-provider


@scenario("index-update")
def _(w):
    return w.run(["index", "update", "--config", w.index_config(), "--base-generation", SIXTY_FOUR])


@scenario("index-inspect")
def _(w):
    return w.run(["index", "inspect", "--config", w.index_config(), "--generation", SIXTY_FOUR])


@scenario("retrieval-task")
def _(w):
    return w.run(
        [
            "retrieval-task",
            "--config",
            w.index_config(),
            "--generation",
            SIXTY_FOUR,
            "--objective",
            "Find persistence code",
        ]
    )


# Operations, checks, MCP receipts, verification and keyword retrieval.


@scenario("triage-check")
def _(w):
    return w.run(
        [
            "triage-check",
            write_json(
                w.tmp / "event.json",
                {"event": check_event(), "handled_keys": [], "max_attempts": 2},
            ),
        ]
    )


@scenario("repair-economics")
def _(w):
    return w.run(["repair-economics", write_json(w.tmp / "ledger.json", repair_ledger())])


@scenario("github-checks")
def _(w):
    return w.run(
        [
            "github-checks",
            write_json(w.tmp / "checks.json", github_payload()),
            "--repository",
            "fixture/project",
            "--revision",
            FORTY,
        ]
    )


@scenario("mcp-inspect")
def _(w):
    from attune_harness.mcp_server import RetrievalSession

    state, first = w.installed_extension()
    enabled = ext.mutate(state, first["state_digest"], "enable")

    def bind(config):
        config["extensions"] = {
            "evidence": {"state_dir": str(state), "artifact_digest": enabled["artifact_digest"]}
        }
        for item in config["participants"].values():
            item["tools"] = ["evidence.search"]

    change_config(w.case, bind)
    session = w.tmp / "mcp-session"
    scope = RetrievalSession(w.request, w.config, "alpha", session)
    scope.save()
    scope.finish()
    return w.run(["mcp-inspect", session])


@scenario("verify")
def _(w):
    return w.run(["verify", w.root / "project" / "guide.md", "--context", w.root / "context.json"])


@scenario("retrieve")
def _(w):
    return w.run(["retrieve", "quartz retention policy", "--corpus", w.root / "project"])


# Memory: the host route (unavailable without attune-ai), the Redis reads against the
# in-process double, and the file scratch store.


@scenario("memory-capabilities")
def _(w):
    return w.run(w.memory_host() + ["capabilities"])


@scenario("memory-recall")
def _(w):
    return w.run(w.memory_host() + ["recall", "quartz"])


@scenario("memory-resolve")
def _(w):
    return w.run(w.memory_host() + ["resolve", w.tmp / "handle.json"])


@scenario("memory-refresh")
def _(w):
    return w.run(w.memory_host() + ["refresh", w.tmp / "context.json"])


@scenario("memory-capabilities-adapter")
def _(w):
    return w.run(w.faked_adapter() + ["capabilities"])


@scenario("memory-recall-adapter")
def _(w):
    return w.run(w.faked_adapter() + ["recall", "quartz", "--k", "3"])


@scenario("memory-resolve-adapter")
def _(w):
    base = w.faked_adapter()
    _, packet = w.run(base + ["recall", "quartz"])
    return w.run(base + ["resolve", write_json(w.tmp / "handle.json", packet["items"][0]["handle"])])


@scenario("memory-refresh-adapter")
def _(w):
    base = w.faked_adapter()
    _, packet = w.run(base + ["recall", "quartz"])
    return w.run(base + ["refresh", write_json(w.tmp / "context.json", packet)])


@scenario("memory-create")
def _(w):
    return w.run(
        w.memory_host()
        + [
            "create",
            "run-1",
            "--envelope",
            w.tmp / "envelope.json",
            "--policy",
            w.tmp / "policy.json",
        ]
    )


@scenario("memory-replay")
def _(w):
    return w.run(
        w.memory_host() + ["replay", "run-1", "job-1", "--replies", w.tmp / "replies.json"]
    )


@scenario("memory-inspect")
def _(w):
    return w.run(w.memory_host() + ["inspect", "run-1", "job-1"])


@scenario("memory-execute")
def _(w):
    return w.run(w.memory_host() + ["execute", "run-1", "job-1"])


@scenario("memory-redis-status")
def _(w):
    return w.run(w.fake_redis() + ["status"])


@scenario("memory-redis-digest")
def _(w):
    return w.run(w.fake_redis() + ["digest", "--limit", "2"])


@scenario("memory-redis-related")
def _(w):
    return w.run(w.fake_redis() + ["related", "n1"])


@scenario("memory-redis-node")
def _(w):
    return w.run(w.fake_redis() + ["node", "n1"])


@scenario("memory-redis-search")
def _(w):
    return w.run(w.fake_redis() + ["search", "runbook", "--layer", "curated", "--k", "1"])


@scenario("memory-redis-unreachable")
def _(w):
    def refuse(settings, **k):
        raise MemoryRedisUnavailable("Redis memory at h is unreachable: refused")

    w.monkeypatch.setattr(memory_redis, "connect", refuse)
    return w.run(w.memory_config({"redis": REDIS_SETTINGS}) + ["redis", "status"])


@scenario("memory-scratch-capabilities")
def _(w):
    return w.run(w.file_scratch() + ["capabilities"])


@scenario("memory-scratch-stash")
def _(w):
    return w.run(
        w.file_scratch()
        + ["stash", "plan:current", "--value", '{"task": "golden"}', "--ttl", "120"]
    )


@scenario("memory-scratch-retrieve")
def _(w):
    base = w.file_scratch()
    w.run(base + ["stash", "plan:current", "--value", "1"])
    return w.run(base + ["retrieve", "plan:current"])


@scenario("memory-scratch-forget")
def _(w):
    base = w.file_scratch()
    w.run(base + ["stash", "plan:current", "--value", "1"])
    return w.run(base + ["forget", "plan:current"])


@scenario("memory-scratch-keys")
def _(w):
    base = w.file_scratch()
    w.run(base + ["stash", "plan:current", "--value", "1"])
    return w.run(base + ["keys", "plan:*"])


@scenario("memory-scratch-disabled")
def _(w):
    return w.run(w.memory_config({"roots": []}) + ["scratch", "capabilities"])


def test_every_scenario_is_pinned():
    assert sorted(SCENARIOS) == sorted(
        TABLE
    ), "every scenario has one row and every row one scenario"


@pytest.mark.parametrize("drive", list(SCENARIOS.values()))
def test_envelope(drive, request, tmp_path, monkeypatch, capsys, case, bundle):
    case_id = request.node.callspec.id
    monkeypatch.chdir(tmp_path)
    code, envelope = drive(World(tmp_path, monkeypatch, capsys, case, bundle))
    assert isinstance(
        envelope, dict
    ), f"{case_id} printed a JSON {type(envelope).__name__}, not one object"
    observed = (
        code,
        envelope.get("schema_version"),
        envelope.get("status"),
        tuple(sorted(envelope)),
    )
    expected = TABLE[case_id][2:]
    assert observed == expected, (
        f"{case_id}: the envelope changed; if that is deliberate, update ENVELOPES and docs/envelopes.md.\n"
        f"  expected {expected!r}\n  observed {observed!r}"
    )


DOC = Path(__file__).resolve().parents[1] / "docs" / "envelopes.md"


def test_documented_table_matches():
    if not DOC.is_file():
        pytest.skip("docs/envelopes.md is not part of this checkout")
    rows = {}
    for line in DOC.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 6 and cells[0].startswith("`") and cells[0].endswith("`"):
            rows[cells[0].strip("`")] = cells
    assert sorted(rows) == sorted(TABLE), "docs/envelopes.md lists exactly the pinned cases"
    for case_id, (_, path, code, schema, status, keys) in TABLE.items():
        documented = rows[case_id]
        assert documented[1] == path, f"{case_id}: path column"
        assert documented[2] == str(code), f"{case_id}: exit code column"
        assert documented[3] == (
            "-" if schema is None else str(schema)
        ), f"{case_id}: schema_version column"
        assert documented[4] == (
            "-" if status is None else f"`{status}`"
        ), f"{case_id}: status column"
        assert tuple(re.findall(r"`([^`]+)`", documented[5])) == keys, f"{case_id}: keys column"
