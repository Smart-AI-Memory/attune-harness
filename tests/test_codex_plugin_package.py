"""Exercise the distributed plugin package and its no-overwrite boundary."""
# qualify: platform

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/package_codex_plugin.py"


def test_package_from_another_directory_carries_complete_skill(tmp_path):
    destination = tmp_path / "attune-harness"
    subprocess.run([sys.executable, str(SCRIPT), str(destination)], cwd=tmp_path, check=True)
    manifest = json.loads((destination / ".codex-plugin/plugin.json").read_text())
    assert manifest["name"] == "attune-harness"
    assert manifest["interface"]["displayName"] == "Attune Harness"
    assert manifest["skills"] == "./skills/"
    source = ROOT / ".agents/skills/attune-harness"
    expected = {str(p.relative_to(source)): p.read_bytes() for p in source.rglob("*") if p.is_file()}
    installed = destination / "skills/attune-harness"
    assert {str(p.relative_to(installed)): p.read_bytes() for p in installed.rglob("*") if p.is_file()} == expected
    assert (destination / "LICENSE").read_bytes() == (ROOT / "LICENSE").read_bytes()
    assert sorted(p.name for p in destination.iterdir()) == [".codex-plugin", "LICENSE", "skills"]


def test_existing_package_is_preserved(tmp_path):
    destination = tmp_path / "attune-harness"
    destination.mkdir()
    sentinel = destination / "user-file"
    sentinel.write_bytes(b"preserve me")
    result = subprocess.run([sys.executable, str(SCRIPT), str(destination)], cwd=tmp_path, capture_output=True)
    assert result.returncode != 0
    assert list(destination.iterdir()) == [sentinel]
    assert sentinel.read_bytes() == b"preserve me"
