"""Offline index integrity and recovery; injected providers never access a service."""

import copy
from pathlib import Path

import pytest

from attune_harness import voyage_index as index
from attune_harness import voyage_retrieval as retrieval
from attune_harness.review_contract import digest
from attune_harness.review_store import read_record
from attune_harness.voyage_provider import PaidStageUnresolved, StageJournal, embeddings
from attune_harness.voyage_sources import collect, snapshot
from test_voyage import built, corpus, git


@pytest.mark.parametrize("fault", ["publication", "config", "generation", "database", "metadata_link"])
def test_corrupt_publication_blocks_retrieval_before_provider(built, tmp_path, fault):
    _, selected, provider = built
    cfg, identity = selected["config"], selected["generation"]
    directory, metadata = index.read_generation(cfg, identity)
    marker = index.read_json(directory / "published.json")
    if fault == "publication":
        marker["receipt_digest"] = "0" * 64
        index.write_json(directory / "published.json", marker)
    elif fault in ("config", "generation"):
        if fault == "config":
            metadata["config"]["candidates"] = 1
        else:
            metadata["passages"][0]["passage_id"] = "0" * 64
        index.write_json(directory / "manifest.json", metadata)
        marker["metadata_digest"] = digest(metadata)
        index.write_json(directory / "published.json", marker)
    elif fault == "database":
        (directory / "db/passages.lance").rename(directory / "retained-passages.lance")
    else:
        original = directory / "manifest.json"
        original.rename(directory / "retained-manifest.json")
        original.symlink_to(directory / "retained-manifest.json")
    provider.calls.clear()
    with pytest.raises(ValueError):
        retrieval.retrieve_voyage(selected, "save_cart", work_dir=tmp_path / "blocked",
                                  allow_provider=True, provider=provider)
    assert provider.calls == []
    assert not (tmp_path / "blocked").exists()


def test_inspect_reports_ready_then_stale_without_refreshing_index(built):
    root, selected, provider = built
    cfg, identity = selected["config"], selected["generation"]
    directory, _ = index.read_generation(cfg, identity)
    retained = (directory / "published.json").read_bytes()
    provider.calls.clear()
    before = index.inspect_index(cfg, identity)
    assert before["status"] == "ready" and before["provider_calls"] == 0
    # A new revision invalidates reuse even when selected file bytes stay identical.
    git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
        "commit", "--allow-empty", "-m", "revision changed")
    after = index.inspect_index(cfg, identity)
    assert after["status"] == "stale" and after["provider_calls"] == 0
    with pytest.raises(ValueError, match="Stale index"):
        index.selection(cfg, identity)
    assert (directory / "published.json").read_bytes() == retained
    assert provider.calls == []


def test_unpublished_provider_failure_is_inspectable_and_not_retried(corpus, monkeypatch):
    _, cfg, provider = corpus
    calls = []

    def fail(*args):
        calls.append(args)
        raise TimeoutError("PRIVATE provider payload")

    monkeypatch.setattr(provider, "embed", fail)
    identity = index.index_plan(cfg)["generation"]
    for _ in range(2):
        with pytest.raises(PaidStageUnresolved):
            index.build_index(cfg, allow_provider=True, provider=provider)
    inspected = index.inspect_index(cfg, identity)
    assert inspected["status"] == "unpublished"
    assert inspected["stages"][0]["status"] == "unresolved"
    assert inspected["stages"][0]["error"]["type"] == "TimeoutError"
    assert "PRIVATE" not in str(inspected)
    assert len(calls) == 1
    assert not (Path(cfg["index_dir"]) / "generations" / identity / "published.json").exists()


@pytest.mark.parametrize("fault", ["digest", "passage"])
def test_invalid_cached_evidence_is_not_reused_or_refetched(built, tmp_path, fault):
    _, selected, provider = built
    work = tmp_path / "run"
    result = retrieval.retrieve_voyage(selected, "save_cart", work_dir=work,
                                        allow_provider=True, provider=provider)
    key = digest({"selection": selected, "query": "save_cart", "k": 3})
    path = work / (key + ".json")
    saved = index.read_json(path)
    saved["result"]["sources"][0]["excerpt"] = "forged evidence"
    if fault == "passage":
        saved["digest"] = digest(saved["result"])
    index.write_json(path, saved)
    provider.calls.clear()
    with pytest.raises(ValueError, match="cache digest|accepted passage"):
        retrieval.retrieve_voyage(selected, "save_cart", work_dir=work,
                                  allow_provider=True, provider=provider)
    assert provider.calls == []
    assert result["sources"][0]["excerpt"] != "forged evidence"
    assert read_record(work)["invocations"][-1]["state"] == "prepared"


def test_run_cannot_change_accepted_scope(built, tmp_path):
    _, selected, provider = built
    work = tmp_path / "run"
    retrieval.retrieve_voyage(selected, "save_cart", work_dir=work,
                              allow_provider=True, provider=provider)
    before = read_record(work)
    changed = copy.deepcopy(selected)
    changed["scope"]["exclude_paths"] = [{"repo_id": "app", "path": "README.md"}]
    provider.calls.clear()
    with pytest.raises(ValueError, match="different accepted scope"):
        retrieval.retrieve_voyage(changed, "save_cart", work_dir=work,
                                  allow_provider=True, provider=provider)
    assert read_record(work) == before
    assert provider.calls == []


@pytest.mark.parametrize("fault", ["ledger", "stage", "config"])
def test_missing_billing_history_never_resets_provider_budget(corpus, tmp_path, fault):
    _, cfg, provider = corpus
    directory = tmp_path / "stages"
    journal = StageJournal(directory, cfg, allow_provider=True, provider=provider)
    journal.perform("embed", {"texts": ["one"], "input_type": "query"}, lambda v: embeddings(v, 1))
    if fault == "ledger":
        (directory / "record.json").rename(directory / "retained-ledger.json")
    elif fault == "stage":
        stage = directory / read_record(directory)["stages"][0]
        (stage / "record.json").rename(stage / "retained-record.json")
    else:
        cfg = {**cfg, "max_provider_calls": cfg["max_provider_calls"] + 1}
    provider.calls.clear()
    with pytest.raises((PaidStageUnresolved, ValueError)):
        StageJournal(directory, cfg, allow_provider=True, provider=provider)
    assert provider.calls == []


def test_index_source_changed_during_embedding_remains_unpublished(corpus, monkeypatch):
    root, cfg, provider = corpus
    identity = index.index_plan(cfg)["generation"]
    original = provider.embed

    def changed(*args):
        result = original(*args)
        (root / "app.py").write_text("owner_change = True\n", encoding="utf-8")
        return result

    monkeypatch.setattr(provider, "embed", changed)
    with pytest.raises(ValueError, match="sources changed during indexing"):
        index.build_index(cfg, allow_provider=True, provider=provider)
    directory = Path(cfg["index_dir"]) / "generations" / identity
    assert not (directory / "published.json").exists()
    stages = read_record(directory / "stages")["stages"]
    assert all(read_record(directory / "stages" / s)["status"] == "completed" for s in stages)
    assert (root / "app.py").read_text() == "owner_change = True\n"


@pytest.mark.parametrize("limit", ["max_files", "max_bytes"])
def test_corpus_budget_rejection_precedes_provider_work(corpus, limit):
    _, cfg, provider = corpus
    cfg[limit] = 1
    with pytest.raises(ValueError, match="corpus exceeds"):
        index.build_index(cfg, allow_provider=True, provider=provider)
    assert provider.calls == []
    assert not Path(cfg["index_dir"]).exists()


def test_invalid_python_is_retained_as_exact_unparsed_evidence(corpus):
    root, cfg, _ = corpus
    raw = b"def broken(:\n    return 1\n"
    (root / "app.py").write_bytes(raw)
    _, passages = collect(cfg)
    selected = [p for p in passages if p["path"] == "app.py"]
    assert b"".join(p["excerpt"].encode() for p in selected) == raw
    assert all(p["chunk_method"] == "python-lines-unparsed" for p in selected)


def test_source_symlink_cannot_escape_selected_root(corpus, tmp_path):
    root, cfg, _ = corpus
    outside = tmp_path / "outside.py"
    outside.write_text("private = True\n", encoding="utf-8")
    (root / "escape.py").symlink_to(outside)
    cfg["allow_untracked"] = True
    with pytest.raises(ValueError, match="escapes selected"):
        snapshot(cfg)
    assert outside.read_text() == "private = True\n"
