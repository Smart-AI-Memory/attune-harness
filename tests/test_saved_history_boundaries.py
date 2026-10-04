"""Corrupt retained history must not be served or repaired by a later write."""
# qualify: platform

import json
import os

import pytest

from attune_harness.memory_saved import SavedError, SavedStore
from test_memory_saved import request, SCOPE

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX saved-store profile")


@pytest.mark.parametrize("damage", [
    "initial_operation", "revision_status", "history_scope", "history_identity",
    "current_summary", "missing_replay", "replay_digest", "index_status",
])
def test_corrupt_history_refuses_reads_and_new_writes_without_repair(tmp_path, damage):
    store = SavedStore(tmp_path / "store")
    first = store.save(request())["record"]
    store.revise(first["id"], {"content": "Revised by the user"}, SCOPE, "two", 1)
    path = store.root / "state.json"
    state = json.loads(path.read_text())
    record = state["records"][first["id"]]
    if damage == "initial_operation":
        record["history"][0]["operation"] = "revise"
    elif damage == "revision_status":
        record["status"] = "withdrawn"
        record["history"][-1]["record"]["status"] = "withdrawn"
    elif damage == "history_scope":
        record["history"][0]["record"]["scope"] = {"kind": "project", "project": str(tmp_path)}
    elif damage == "history_identity":
        record["history"][0]["record"]["id"] = "00000000-0000-4000-8000-000000000000"
    elif damage == "current_summary":
        record["content"] = "Invented current value"
    elif damage == "missing_replay":
        del state["operations"]["one"]
    elif damage == "replay_digest":
        state["operations"]["one"]["digest"] = "z" * 64
    else:
        state["index"][first["id"]] = "invented"
    path.write_text(json.dumps(state))
    before = path.read_bytes()
    restarted = SavedStore(store.root)
    for operation in (
        lambda: restarted.get(first["id"], SCOPE),
        lambda: restarted.save(request("three")),
    ):
        with pytest.raises(SavedError) as caught:
            operation()
        assert caught.value.code == "corrupt"
        assert caught.value.outcome == "not_committed"
        assert path.read_bytes() == before


def test_reused_request_cannot_overwrite_or_resurrect_withdrawn_memory(tmp_path):
    store = SavedStore(tmp_path / "store")
    original = store.save(request())
    identity = original["record"]["id"]
    store.forget(identity, SCOPE, "forget", 1)
    before = (store.root / "state.json").read_bytes()
    changed = request()
    changed["content"] = "Different meaning for the same request ID"
    with pytest.raises(SavedError) as caught:
        store.save(changed)
    assert caught.value.code == "conflict"
    assert store.save(request()) == original
    assert store.list(SCOPE) == []
    assert store.get(identity, SCOPE, include_withdrawn=True)["status"] == "withdrawn"
    assert (store.root / "state.json").read_bytes() == before
