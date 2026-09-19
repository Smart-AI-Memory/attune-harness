"""Execute captured, unchanged real adapter source against temporary records."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def backend(tmp_path):
    root = Path(__file__).resolve().parents[1]
    source = root / "adapter/file_stash.py"
    identity = json.loads((root / "adapter/identity.json").read_text())
    assert hashlib.sha256(source.read_bytes()).hexdigest() == identity["sha256"]
    import attune.memory.atomic_io as atomic

    assert (
        hashlib.sha256(Path(atomic.__file__).read_bytes()).hexdigest()
        == identity["atomic_io_sha256"]
    )
    spec = importlib.util.spec_from_file_location("captured_file_stash", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    store = module.FileStashBackend(base_dir=tmp_path / "synthetic-memories")
    for project in ("cedar", "elm"):
        assert store.remember(
            "Synthetic violet project note.",
            memory_id=project,
            topics=["cwd:" + project],
        )
    yield store
    store.close()


@pytest.mark.parametrize("method", ["search", "recent"])
def test_project_preference_keeps_foreign_records(backend, method):
    records = (
        backend.search("violet", cwd="cedar")
        if method == "search"
        else backend.recent(cwd="cedar")
    )
    assert [item["id"] for item in records] == ["cedar", "elm"]


def test_unknown_project_does_not_hide_other_projects(backend):
    for records in (
        backend.search("violet", cwd="absent-project"),
        backend.recent(cwd="absent-project"),
    ):
        assert {item["id"] for item in records} == {"cedar", "elm"}
