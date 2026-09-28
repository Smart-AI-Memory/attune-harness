"""The offline candidate writer refuses unsafe output before creating state."""

import hashlib
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import compat_writer_recipe as recipe  # noqa: E402


@pytest.mark.parametrize("name", ("../attune-compat-escape", "C:/attune-compat-drive"))
def test_writer_refuses_noncanonical_or_drive_output(monkeypatch, name):
    monkeypatch.setattr(sys, "argv", ["compat_writer_recipe.py", "--output", name])
    with pytest.raises(ValueError, match="generic /private/tmp"):
        recipe.main()


def test_writer_refuses_ambient_provider_key_before_writing(monkeypatch):
    if os.name != "posix" or not Path("/private/tmp").is_dir():
        pytest.skip("Writer output root is POSIX /private/tmp")
    root = Path("/private/tmp") / f"attune-compat-test-{uuid4().hex}"
    monkeypatch.setattr(sys, "argv", ["compat_writer_recipe.py", "--output", str(root)])
    monkeypatch.setenv("ANTHROPIC_API_KEY", "synthetic-test-token")
    with pytest.raises(RuntimeError, match="Unset ANTHROPIC_API_KEY"):
        recipe.main()
    assert not root.exists()


def test_writer_receipt_records_incremental_bytes_and_failure(tmp_path):
    root = tmp_path / "capture"
    root.mkdir()
    (root / "writer-receipt.json").write_text('{"families":{}}\n', encoding="utf-8")
    data = b'{"schema_version":1,"status":"draft"}\r\n'
    output = root / "work" / "record.json"
    output.parent.mkdir()
    output.write_bytes(data)

    recipe._mark(root, "work", ("work/record.json",))
    receipt = json.loads((root / "writer-receipt.json").read_text(encoding="utf-8"))
    assert receipt["families"]["work"] == {
        "outcome": "written",
        "outputs": {"work/record.json": {
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data), "schema_version": 1, "status": "draft",
        }},
    }

    recipe._mark(root, "review", ("review/record.json",), failure="ValueError")
    receipt = json.loads((root / "writer-receipt.json").read_text(encoding="utf-8"))
    assert receipt["families"]["review"] == {
        "outcome": "failed", "outputs": {}, "error_type": "ValueError",
    }
    assert receipt["families"]["work"]["outputs"]["work/record.json"]["sha256"] == hashlib.sha256(data).hexdigest()
