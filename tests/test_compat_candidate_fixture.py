"""A candidate-written 1.0 fixture remains readable without granting new authority."""
# qualify: platform

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compat_capture import relocate_paths  # noqa: E402


FIXTURE = Path(__file__).parent / "fixtures" / "compat-1.0"
FILES = FIXTURE / "files"
WRITER = "ca5d9ee80ce6884d786acb4ad4cfe42ff246861e"
WHEEL_SHA256 = "18cda1a30c54f8143225007e80aac0a1bda211d2fcc49a07a3ab521272cc517f"


def manifest() -> dict:
    return json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))


def assert_raw_bytes() -> None:
    captured = manifest()
    assert captured["schema_version"] == 1
    assert captured["capture"] == "byte_inventory_only"
    assert captured["record_writer"] == "not_verified_by_capture_tool"
    assert captured["provenance"] == {
        "distribution": "attune-harness", "version": "1.0.0rc1",
        "wheel_sha256": WHEEL_SHA256, "writer_source_commit": WRITER,
        "verified_package_files": 97,
    }
    assert len(captured["files"]) == 33
    assert {p.relative_to(FILES).as_posix() for p in FILES.rglob("*") if p.is_file()} == set(captured["files"])
    for name, observation in captured["files"].items():
        raw = (FILES / name).read_bytes()
        assert observation == {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def copy_path_free(tmp_path: Path, prefixes: tuple[str, ...]) -> Path:
    """Copy untouched format records for portable readers on every OS."""
    assert_raw_bytes()
    target = tmp_path / "path-free"
    target.mkdir()
    names = [name for name in manifest()["files"] if name.startswith(prefixes)]
    assert names
    for name in names:
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FILES / name, destination)
    return target


def test_raw_capture_matches_manifest_and_writer_observations():
    assert_raw_bytes()
    captured = manifest()
    writer = json.loads((FILES / "writer-receipt.json").read_text(encoding="utf-8"))
    assert writer["schema_version"] == 1
    assert writer["writer"]["version"] == "1.0.0rc1"
    assert writer["writer"]["distribution"] == "attune-harness"
    assert writer["network"] == "socket connections refused; provider keys absent"
    assert writer["extension_signature"] == "unsigned disabled declaration only"
    assert set(writer["families"]) == {
        "work", "effects", "review", "test", "plan", "memory",
        "extension-unsigned-disabled", "voyage-offline",
    }
    outputs = {name: observed for family in writer["families"].values()
               for name, observed in family["outputs"].items()}
    assert all(family["outcome"] == "written" for family in writer["families"].values())
    assert len(outputs) == 19
    for name, observation in outputs.items():
        assert observation["sha256"] == captured["files"][name]["sha256"]
        assert observation["bytes"] == captured["files"][name]["bytes"]


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _relocate_json(target: Path, name: str, old_root: Path, pointers: set[str],
                   *, checkpoint: bool = False) -> dict:
    from attune_harness.review_store import checkpoint_digest

    path = target / name
    original = json.loads(path.read_text(encoding="utf-8"))
    moved = relocate_paths(original, allowed=pointers, requested=pointers,
                           old_root=old_root, new_root=target)
    if checkpoint:
        moved["checkpoint_digest"] = checkpoint_digest(moved)
    _write_json(path, moved)
    return moved


def relocate(fixture: Path, target: Path) -> dict:
    """Copy raw files, then rewrite only listed owner paths and reader derivations."""
    from attune_harness import memory_saved
    from attune_harness.review_contract import digest
    from attune_harness.review_store import checkpoint_digest
    from attune_harness.work_contract import _bindings, decision_binding

    assert fixture == FIXTURE and not target.exists()
    assert_raw_bytes()
    source_files = fixture / "files"
    old_record = json.loads((source_files / "work-draft/record.json").read_text(encoding="utf-8"))
    old_root = Path(old_record["record_path"]).parent.parent
    assert old_root.parent == Path("/private/tmp") and old_root.name.startswith("attune-compat-")
    target.mkdir()
    for name in manifest()["files"]:
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_files / name, destination)

    draft = _relocate_json(target, "work-draft/record.json", old_root,
                           {"/request/project_root", "/request/config/path", "/record_path"}, checkpoint=True)
    decision_path = target / "work-draft/decision.json"
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    decision["work"] = decision_binding(draft)
    decision["digest"] = digest({k: v for k, v in decision.items() if k != "digest"})
    _write_json(decision_path, decision)

    accepted = _relocate_json(target, "work-accepted/record.json", old_root,
                              {"/request/project_root", "/request/config/path", "/record_path",
                               "/acceptance/decision/record_path"})
    accepted["bindings"] = _bindings(accepted["request"])
    draft_view = {**{k: v for k, v in accepted.items() if k != "build"},
                  "status": "draft", "acceptance": None, "bindings": {}}
    draft_view["checkpoint_digest"] = checkpoint_digest(draft_view)
    binding = decision_binding(draft_view)
    for key, value in binding.items():
        accepted["acceptance"]["decision"][key] = value
    accepted["checkpoint_digest"] = checkpoint_digest(accepted)
    _write_json(target / "work-accepted/record.json", accepted)
    decision_path = target / "work-accepted/decision.json"
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    decision["work"] = binding
    decision["response"] = relocate_paths(decision["response"], allowed={"/record_path"},
                                           requested={"/record_path"}, old_root=old_root, new_root=target)
    decision["digest"] = digest({k: v for k, v in decision.items() if k != "digest"})
    _write_json(decision_path, decision)

    completed = _relocate_json(target, "review-completed/record.json", old_root,
                               {"/record_path"}, checkpoint=True)
    paused = _relocate_json(target, "review-paused/record.json", old_root,
                            {"/record_path"}, checkpoint=True)
    _relocate_json(target, "test-draft/record.json", old_root,
                   {"/request/project_root", "/request/snapshot/root", "/record_path"}, checkpoint=True)
    _relocate_json(target, "effects/manifest.json", old_root, {"/root"})
    extension = _relocate_json(target, "extension-disabled/record.json", old_root, {"/manifest"})
    extension["state_digest"] = digest({k: v for k, v in extension.items() if k != "state_digest"})
    _write_json(target / "extension-disabled/record.json", extension)
    config = _relocate_json(target, "memory-config.json", old_root,
                            {"/roots/0/path", "/roots/1/path", "/roots/2/path",
                             "/scratch/root", "/saved/root"})

    saved_path = target / "saved-store/state.json"
    saved = json.loads(saved_path.read_text(encoding="utf-8"))
    tasks = [value for value in saved["records"].values() if value["kind"] == "task"]
    assert len(tasks) == 1 and set(saved["operations"]) == {"save-memory", "revise-memory", "save-task"}
    task_id = tasks[0]["id"]
    paths = {
        "/operations/save-task/record/execution/directory",
        "/operations/save-task/record/history/0/record/execution/directory",
        "/operations/save-task/record/history/0/record/scope/project",
        "/operations/save-task/record/scope/project",
        f"/records/{task_id}/execution/directory",
        f"/records/{task_id}/history/0/record/execution/directory",
        f"/records/{task_id}/history/0/record/scope/project",
        f"/records/{task_id}/scope/project",
    }
    saved = relocate_paths(saved, allowed=paths, requested=paths, old_root=old_root, new_root=target)
    stored = saved["operations"]["save-task"]["record"]
    assert stored["revision"] == 1 and stored["history"][0]["operation"] == "save"
    value = {key: item for key, item in stored.items() if key not in ("id", "revision", "status", "history")}
    payload = {"operation": "save", "request_id": "save-task", "value": value,
               "id": None, "scope": None, "expected_revision": None}
    saved["operations"]["save-task"]["digest"] = hashlib.sha256(memory_saved._json(payload)).hexdigest()
    _write_json(saved_path, saved)
    return {"old_root": old_root, "completed": completed, "paused": paused, "config": config,
            "saved_task_id": task_id}


@pytest.fixture
def relocated(tmp_path):
    target = tmp_path.resolve() / "candidate"
    context = relocate(FIXTURE, target)
    yield target, context
    assert_raw_bytes()


@pytest.mark.skipif(os.name != "posix", reason="candidate writer used POSIX saved/effects profile")
def test_relocated_task_and_review_readers_preserve_authority_boundaries(relocated):
    from attune_harness.recovery import resume_review
    from attune_harness.review_store import inspect_run
    from attune_harness.task_contract import read_task
    from attune_harness.test_change import check_test_fresh
    from attune_harness.work_contract import check_work_fresh
    from attune_harness.work_decisions import retained_decision

    target, context = relocated
    draft = read_task(target / "work-draft")
    accepted = read_task(target / "work-accepted")
    assert draft["status"] == "draft" and accepted["status"] == "accepted"
    check_work_fresh(accepted)
    assert retained_decision(draft)["state"] == "current"
    assert retained_decision(accepted)["state"] == "historical"
    test = read_task(target / "test-draft")
    assert test["status"] == "draft"
    with pytest.raises(ValueError, match="Git input unavailable"):
        check_test_fresh(test)
    assert inspect_run(target / "review-completed")["status"] == "completed"
    assert inspect_run(target / "review-paused")["status"] == "paused"

    def no_participant(*_args, **_kwargs):
        pytest.fail("Retained review attempted participant dispatch")

    completed_path = target / "review-completed/record.json"
    before = completed_path.read_bytes()
    resumed = resume_review(target / "review-completed", target / "review-request.json",
                            target / "participants.json", context["completed"]["checkpoint_digest"],
                            exchange_factory=no_participant)
    assert resumed["status"] == "completed" and completed_path.read_bytes() == before
    with pytest.raises(ValueError, match="Accepted request, registry or source snapshot changed"):
        resume_review(target / "review-paused", target / "review-request.json",
                      target / "participants.json", context["paused"]["checkpoint_digest"],
                      exchange_factory=no_participant)


@pytest.mark.skipif(os.name != "posix", reason="candidate writer used POSIX saved/effects profile")
def test_relocated_effects_memory_and_extension(relocated, monkeypatch):
    from attune_harness.extensions import inspect_extension
    from attune_harness.memory_reader import NativeReader, roots_config, RAW_TTL_SECONDS
    from attune_harness import memory_reader
    from attune_harness.memory_saved import SavedStore
    from attune_harness.repair import assert_snapshot
    from attune_harness.work_effects import validate_manifest

    target, context = relocated
    effect = json.loads((target / "effects/manifest.json").read_text(encoding="utf-8"))
    validate_manifest(effect)
    with pytest.raises(ValueError, match="Checkout identity changed"):
        assert_snapshot(effect, effect["before"])
    assert inspect_extension(target / "extension-disabled")["status"] == "disabled"
    scope = {"kind": "project", "project": str(target / "work-project")}
    store = SavedStore(target / "saved-store")
    rows = store.list(scope)
    assert len(rows) == 1 and rows[0]["id"] == context["saved_task_id"]
    assert rows[0]["opportunity_review"]["status"] == "pending"
    assert rows[0]["execution_status"] == "draft"
    assert len(store.list({"kind": "global"})) == 1

    reader = NativeReader(roots_config(context["config"]))
    raw = json.loads((target / "memory-roots/raw/findings.jsonl").read_text(encoding="utf-8"))
    assert RAW_TTL_SECONDS == 30 * 24 * 3600
    stamp = raw["ts"]
    with monkeypatch.context() as clock:
        clock.setattr(memory_reader.time, "time", lambda: stamp + 24 * 3600)
        packet = reader.query("Quartz memory note", k=10)
        assert packet["status"] == "available" and not packet["problems"]
        assert {item["id"] for item in packet["items"]} == {"raw:M1", "personal:note.md"}
        assert {item["id"] for item in reader.query("Quartz rule", k=10)["items"]} == {
            "raw:M1", "curated:rule.md"}
    with monkeypatch.context() as clock:
        clock.setattr(memory_reader.time, "time", lambda: stamp + 31 * 24 * 3600)
        assert {item["id"] for item in reader.query("Quartz memory note", k=10)["items"]} == {
            "personal:note.md"}


def test_path_free_plan_and_scratch_read_on_every_platform(tmp_path):
    from attune_harness.memory_scratch import FileScratch
    from attune_harness.spec_state import load_state

    target = copy_path_free(tmp_path, ("plan-state/", "scratch-store/"))
    assert load_state(str(target / "plan-state/plan.md")).schema_version == 2
    assert FileScratch(target / "scratch-store").retrieve("compat-note")["format_version"] == 2
    assert_raw_bytes()


def test_path_free_voyage_journal_replays_or_refuses_on_every_platform(tmp_path):
    from attune_harness.voyage_provider import PaidStageUnresolved, StageJournal, embeddings

    target = copy_path_free(tmp_path, ("voyage-completed/", "voyage-dispatching/"))

    class NoProvider:
        def embed(self, *_args):
            pytest.fail("Retained Voyage stage attempted provider dispatch")

    cfg = {"max_request_bytes": 8192, "max_provider_calls": 1}
    request = {"texts": ["synthetic quartz"], "input_type": "query"}
    for name in ("voyage-completed", "voyage-dispatching"):
        directory = target / name
        before = {p.relative_to(directory).as_posix(): p.read_bytes() for p in directory.rglob("record.json")}
        journal = StageJournal(directory, cfg, allow_provider=False, provider=NoProvider())
        if name == "voyage-completed":
            _, receipt = journal.perform("embed", request, lambda value: embeddings(value, 1))
            assert receipt["replayed"] is True
            assert receipt["new_tokens"] == 0 and receipt["new_cost_usd"] == 0.0
        else:
            with pytest.raises(PaidStageUnresolved, match="No automatic retry"):
                journal.perform("embed", request, lambda value: embeddings(value, 1))
        assert {p.relative_to(directory).as_posix(): p.read_bytes()
                for p in directory.rglob("record.json")} == before
    assert_raw_bytes()


@pytest.mark.skipif(os.name != "posix", reason="candidate owner paths use POSIX")
def test_candidate_relocation_refuses_unknown_pointer_and_escape(tmp_path):
    raw = json.loads((FILES / "work-draft/record.json").read_text(encoding="utf-8"))
    old_root = Path(raw["record_path"]).parent.parent
    target = tmp_path.resolve() / "candidate"
    with pytest.raises(ValueError, match="Unknown"):
        relocate_paths(raw, allowed={"/record_path"}, requested={"/request/project_root"},
                       old_root=old_root, new_root=target)
    bad = {"record_path": str(old_root.parent / "outside-record.json")}
    with pytest.raises(ValueError, match="escapes"):
        relocate_paths(bad, allowed={"/record_path"}, requested={"/record_path"},
                       old_root=old_root, new_root=target)
    assert_raw_bytes()


@pytest.mark.skipif(os.name != "posix", reason="candidate owner paths use POSIX")
def test_relocated_checkpoint_tampering_refuses_reader(relocated):
    from attune_harness.review_store import inspect_run

    target, _ = relocated
    path = target / "review-completed/record.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["status"] = "paused"
    _write_json(path, record)
    with pytest.raises(ValueError, match="Run checkpoint digest does not match its contents"):
        inspect_run(target / "review-completed")
