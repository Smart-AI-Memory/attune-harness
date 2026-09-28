#!/usr/bin/env python3
"""Write synthetic 1.0 compatibility candidates with an installed wheel, offline.

Run with ``python -I`` from a fresh environment where the unpublished writer
wheel is installed. This produces inputs and writer outputs, not a frozen
fixture. Review the output and capture it with ``compat_capture.py`` afterward.
"""

from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import re


VERSION = "1.0.0rc1"
FORBIDDEN_ENV = ("VOYAGE_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY")


def _offline() -> None:
    for name in FORBIDDEN_ENV:
        if os.environ.get(name):
            raise RuntimeError(f"Unset {name} before offline compatibility writing")

    def refused(*_args, **_kwargs):
        raise RuntimeError("Offline compatibility writer refused a network connection")

    socket.socket.connect = refused
    socket.socket.connect_ex = refused
    socket.create_connection = refused


def _installed_origin() -> dict:
    import attune_harness
    import attune_voyage_plugin

    if metadata.version("attune-harness") != VERSION:
        raise RuntimeError("Installed Harness version is not the candidate writer version")
    packages = {"attune_harness": attune_harness, "attune_voyage_plugin": attune_voyage_plugin}
    origins = {}
    for name, package in packages.items():
        origin = Path(package.__file__).resolve()
        if "site-packages" not in origin.parts or "src" in origin.parts:
            raise RuntimeError(f"{name} is not an installed wheel package")
        origins[name] = str(origin)
    return {"distribution": "attune-harness", "version": VERSION, "package_origins": origins}


def _json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _mark(root: Path, family: str, paths: tuple[str, ...], *, failure: str | None = None) -> None:
    """Save attributable output after each family, including a failed attempt."""
    receipt_path = root / "writer-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    files = {}
    for pattern in paths:
        matches = sorted(root.glob(pattern))
        if not matches and failure is None:
            raise RuntimeError(f"Writer family {family} did not create {pattern}")
        for path in matches:
            if not path.is_file() or path.is_symlink():
                raise RuntimeError("Writer output is not a regular non-link file")
            relative = path.relative_to(root).as_posix()
            raw = path.read_bytes()
            observation = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
            if path.suffix == ".json":
                try:
                    parsed = json.loads(raw)
                except (UnicodeError, ValueError):
                    parsed = None
                if isinstance(parsed, dict):
                    observation.update({key: parsed[key] for key in ("status", "schema_version", "format_version")
                                        if key in parsed})
            files[relative] = observation
    receipt["families"][family] = {"outcome": "failed" if failure else "written",
                                   "outputs": files, **({"error_type": failure} if failure else {})}
    _json(receipt_path, receipt)


def _git_project(root: Path) -> None:
    root.mkdir()
    subprocess.run(("git", "init", "-q", str(root)), check=True, timeout=10)
    (root / ".gitignore").write_text("__pycache__/\n.pytest_cache/\n", encoding="utf-8")


def _work(root: Path, config: Path) -> dict:
    from attune_harness.work_contract import SIGNALS, bind_work_acceptance, create_work, decision_binding
    from attune_harness.work_decisions import retain_decision

    project = root / "work-project"
    _git_project(project)
    (project / "source.py").write_text("def answer():\n    return 42\n", encoding="utf-8")
    (project / "plan.md").write_text("Keep the source behavior.\n", encoding="utf-8")
    budget = {"max_operations": 20, "max_attempts": 1, "max_output_bytes": 10000}
    data = {
        "intent": {"goal": "Preserve the answer", "context": ["Synthetic compatibility project"],
                   "scope": ["source.py"], "constraints": ["No network"],
                   "acceptance": ["Existing test remains green"], "questions": []},
        "signals": {**dict.fromkeys(SIGNALS, False), "existing_artifact": None},
        "assignments": [{"role": "planner", "participant": "local",
                         "output_contract": "Bounded plan with checks", "budgets": budget}],
        "inputs": ["source.py"], "artifact": "plan.md", "budget": budget,
    }
    draft = create_work(project, config, directory=root / "work-draft", **data)
    retain_decision(draft, {"kind": "spec", "markdown": "Approve this synthetic work draft."})
    pending = create_work(project, config, directory=root / "work-accepted", **data)
    decision = {**decision_binding(pending), "accepted": True,
                "source": {"owner": "spec", "reference": "synthetic-approval",
                           "disposition": "approve_task"}}
    retain_decision(pending, {"kind": "spec", "markdown": "Approve this synthetic work draft."},
                    response=decision)
    accepted = bind_work_acceptance(root / "work-accepted", decision)
    return {"project": project, "draft": draft, "accepted": accepted}


def _effects(root: Path, project: Path) -> None:
    from attune_harness.work_effects import freeze

    manifest = freeze(project, ["source.py"], [], ["plan.md"], [], root / "effects-state")
    _json(root / "effects" / "manifest.json", manifest)


def _reviews(root: Path, config: Path) -> None:
    from attune_harness.review import review
    from attune_harness.review_contract import load_registry, review_form

    project = root / "review-project"
    project.mkdir()
    (project / "guide.md").write_text("[Quartz retention policy](reference.md)", encoding="utf-8")
    (project / "reference.md").write_text("Quartz retention policy is synthetic evidence.", encoding="utf-8")
    _json(root / "context.json", {"schema_version": 1, "project_root": "review-project"})
    form = review_form(load_registry(config))["submission"]
    form.update(accepted=True, answers={"objective": "Check evidence", "query": "quartz retention policy",
                                        "document": "review-project/guide.md", "context": "context.json",
                                        "corpus": "review-project", "lead": "alpha", "reviewer": "beta"})
    request = root / "review-request.json"
    _json(request, form)
    completed = review(request, config, root / "review-completed")
    paused = review(request, config, root / "review-paused", max_operations=2)
    if completed["status"] != "completed" or paused["status"] != "paused":
        raise RuntimeError("Deterministic review did not write completed and paused records")


def _test_change(root: Path) -> None:
    from attune_harness.test_change import create_test_task

    project = root / "test-project"
    _git_project(project)
    (project / "src" / "demo").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "src" / "demo" / "logic.py").write_text("def answer():\n    return 42\n", encoding="utf-8")
    (project / "tests" / "test_logic.py").write_text("def test_answer():\n    assert 42 == 42\n", encoding="utf-8")
    subprocess.run(("git", "-C", str(project), "add", "."), check=True, timeout=10)
    subprocess.run(("git", "-C", str(project), "-c", "user.name=Fixture", "-c",
                    "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false",
                    "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture"),
                   check=True, timeout=10)
    # The testing intake captures a real working-tree change against HEAD.
    (project / "src" / "demo" / "logic.py").write_text(
        "# working-tree change\ndef answer():\n    return 42\n", encoding="utf-8")
    create_test_task(project, root / "test-draft", scope=["src/demo/logic.py"],
                     interpreter=sys.executable, goal="Verify synthetic behavior")


def _plan(root: Path) -> None:
    from attune_harness.spec_state import SpecState, save_state

    path = root / "plan-state" / "plan.md"
    path.parent.mkdir()
    path.write_text('# Synthetic plan\n\n<task id="1" name="first"><objective>Do first</objective></task>\n',
                    encoding="utf-8")
    save_state(SpecState(str(path)))


def _memory(root: Path, owner: dict) -> None:
    from attune_harness.memory_saved import SavedStore
    from attune_harness.memory_scratch import FileScratch

    scratch_root = root / "scratch-store"
    scratch_root.mkdir()
    FileScratch(scratch_root).stash("compat-note", {"answer": 42})
    store = SavedStore(root / "saved-store")
    source = {"author": "synthetic-user", "reference": "compatibility fixture"}
    memory = store.save({"request_id": "save-memory", "kind": "memory", "scope": {"kind": "global"},
                         "title": "Synthetic memory", "content": "Keep the answer", "source": source})["record"]
    store.revise(memory["id"], {"content": "Keep the answer 42"}, {"kind": "global"},
                 "revise-memory", 1)
    scope = {"kind": "project", "project": str(owner["project"])}
    store.save({"request_id": "save-task", "kind": "task", "scope": scope,
                "title": "Return to synthetic task", "content": "Inspect retained work",
                "source": source, "next_action": "Inspect the owning work record",
                "execution": {"directory": str(root / "work-draft"),
                              "task_id": owner["draft"]["request"]["task_id"]},
                "opportunity_review": {"status": "pending", "goal": "Review follow-up options",
                                       "progress": "Inputs captured", "evidence": [],
                                       "reason": "Deferred to candidate observation",
                                       "next_action": "Inspect the evidence and finish the review"}})

    raw, personal, curated = (root / "memory-roots" / name for name in ("raw", "personal", "curated"))
    for directory in (raw, personal, curated):
        directory.mkdir(parents=True)
    (raw / "findings.jsonl").write_text(json.dumps({"id": "M1", "text": "Quartz memory note",
                                                   "topics": ["type:note"], "cwd": "compat-project",
                                                   "ts": time.time()}) + "\n", encoding="utf-8")
    (personal / "note.md").write_text("# Quartz\n\nA synthetic memory note.\n", encoding="utf-8")
    (curated / "rule.md").write_text("# Quartz rule\n\nRetain evidence before claims.\n", encoding="utf-8")
    _json(root / "memory-config.json", {
        "schema_version": 1, "actor": "fixture", "owners": ["fixture"],
        "scopes": ["compat-project", "global"], "classifications": ["internal"],
        "profiles": ["claude"], "reader": "native",
        "roots": [{"id": name, "path": str(directory), "tier": name,
                   "scope": "compat-project" if name == "raw" else "global",
                   "owner": "fixture", "classification": "internal"}
                  for name, directory in (("raw", raw), ("personal", personal), ("curated", curated))],
        "scratch": {"backend": "file", "root": str(scratch_root), "namespace": "harness"},
        "saved": {"root": str(root / "saved-store")},
    })


def _extension(root: Path) -> None:
    from attune_voyage_plugin.bundle import build
    from attune_harness.extensions import install

    bundle = root / "voyage-bundle"
    build(bundle)
    install(bundle / "manifest.json", root / "extension-disabled")


def _journals(root: Path) -> None:
    from attune_harness.voyage_provider import (PaidStageInterrupted, PaidStageUnresolved,
                                                 StageJournal, embeddings)
    from attune_harness.voyage_sources import PROFILE

    cfg = {"max_request_bytes": 8192, "max_provider_calls": 1}
    request = {"texts": ["synthetic quartz"], "input_type": "query"}

    class Completed:
        calls = 0

        def embed(self, _texts, _input_type):
            self.calls += 1
            return {"vectors": [[1.0] + [0.0] * (PROFILE["dimensions"] - 1)],
                    "total_tokens": 2}

    class Interrupted:
        calls = 0

        def embed(self, _texts, _input_type):
            self.calls += 1
            raise PaidStageInterrupted("synthetic stopped child")

    completed = Completed()
    StageJournal(root / "voyage-completed", cfg, allow_provider=True, provider=completed).perform(
        "embed", request, lambda value: embeddings(value, 1))
    if completed.calls != 1:
        raise RuntimeError("Synthetic completed stage did not write exactly once")
    stopped = Interrupted()
    try:
        StageJournal(root / "voyage-dispatching", cfg, allow_provider=True, provider=stopped).perform(
            "embed", request, lambda value: embeddings(value, 1))
    except PaidStageUnresolved:
        pass
    else:
        raise RuntimeError("Synthetic interruption was not refused")
    if stopped.calls != 1:
        raise RuntimeError("Synthetic interruption did not enter the dispatch boundary")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = args.output.absolute()
    if (os.name != "posix" or root != root.resolve() or
            root.parent != Path("/private/tmp") or
            not re.fullmatch(r"attune-compat-[a-z0-9-]+", root.name)):
        raise ValueError("Writer output must be a generic /private/tmp/attune-compat-* path on POSIX")
    if root.exists() or root.is_symlink():
        raise FileExistsError(root)
    _offline()
    origin = _installed_origin()
    root.mkdir()
    _json(root / "writer-receipt.json", {"schema_version": 1, "writer": origin,
                                         "families": {}, "network": "socket connections refused; provider keys absent",
                                         "extension_signature": "unsigned disabled declaration only"})
    _json(root / "participants.json", {
        "schema_version": 1, "participants": {
            name: {"adapter": "deterministic", "tools": ["retrieve", "verify"],
                   "max_turns": 3, "max_tool_calls": 2}
            for name in ("local", "alpha", "beta")}})
    config = root / "participants.json"
    operations = (
        ("work", lambda: _work(root, config),
         ("work-draft/record.json", "work-draft/decision.json",
          "work-accepted/record.json", "work-accepted/decision.json")),
        ("effects", lambda: _effects(root, owner["project"]), ("effects/manifest.json",)),
        ("review", lambda: _reviews(root, config),
         ("review-completed/record.json", "review-paused/record.json")),
        ("test", lambda: _test_change(root), ("test-draft/record.json",)),
        ("plan", lambda: _plan(root), ("plan-state/plan.md",)),
        ("memory", lambda: _memory(root, owner),
         ("scratch-store/scratch/harness/*.json", "saved-store/state.json")),
        ("extension-unsigned-disabled", lambda: _extension(root),
         ("voyage-bundle/manifest.json", "voyage-bundle/SKILL.md", "voyage-bundle/code.zip",
          "extension-disabled/record.json")),
        ("voyage-offline", lambda: _journals(root),
         ("voyage-completed/record.json", "voyage-completed/*/record.json",
          "voyage-dispatching/record.json", "voyage-dispatching/*/record.json")),
    )
    owner = None
    for family, write, paths in operations:
        try:
            result = write()
            if family == "work":
                owner = result
            _mark(root, family, paths)
        except Exception as exc:
            _mark(root, family, paths, failure=type(exc).__name__)
            raise
    print(json.dumps({"output": str(root), "version": VERSION, "writer_receipt": "writer-receipt.json"}))


if __name__ == "__main__":
    main()
