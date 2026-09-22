"""The compatibility fixture is the memory format contract (N4, D19): pinned by digest and shape.

``tests/fixtures/memory_compatibility.json`` came onto ``main`` from commit
``3230643`` of ``wip/local-snapshot-2026-09-19`` unchanged. The adapter-side
probes in ``test_memory_compatibility.py`` need attune-ai; these checks need
nothing, so every platform job sees the contract, and an edit to the file
fails here until the digest below is changed on purpose.
"""
# qualify: platform

import hashlib
import json
from pathlib import Path

FIXTURE = Path(__file__).parent / "fixtures" / "memory_compatibility.json"
DIGEST = "37ed7a15b2bf5ffa4f115317212a9ef8c491668654967315eb2a0670444b3bce"
OPTIONAL = {"documents": {"repeat", "tail"}}  # one document is repeated to a size with a tail marker
SECTIONS = {
    "raw": {"cwd", "id", "text", "type"},
    "documents": {"body", "path", "query", "root"},
    "curated": {"content", "path"},
    "digest_node": {"description", "edges", "future_field", "id", "name", "type", "updated_at"},
    "working": {"key", "value"},
    "pattern": {"content", "metadata", "pattern_id"},
}


def test_the_fixture_is_byte_identical_to_the_accepted_one():
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == DIGEST


def test_the_fixture_has_the_sections_and_keys_the_ladder_names():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert data["schema"] == 1 and "never live user memory" in data["purpose"]
    assert set(data) == {"schema", "purpose", *SECTIONS}
    for name, keys in SECTIONS.items():
        rows = data[name] if isinstance(data[name], list) else [data[name]]
        assert rows, name
        for row in rows:
            assert keys <= set(row) <= keys | OPTIONAL.get(name, set()), (name, sorted(row))
    assert len(data["raw"]) == 5 and len(data["documents"]) == 5
    assert len({row["id"] for row in data["raw"]}) == 5
    assert all(row["query"] for row in data["documents"])
    assert len({row["cwd"] for row in data["raw"]}) > 1  # the soft cwd ordering has something to order
