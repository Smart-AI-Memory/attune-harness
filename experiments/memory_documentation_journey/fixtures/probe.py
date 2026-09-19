"""Actual behavioral witness; the reviewer owns documentation semantics."""

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile

root = Path(__file__).resolve().parent
source = root / "adapter/file_stash.py"
identity = json.loads((root / "adapter/identity.json").read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest() == identity["sha256"]
spec = importlib.util.spec_from_file_location("captured_file_stash", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory(prefix="memory-doc-repair-probe-") as temporary:
    backend = module.FileStashBackend(base_dir=Path(temporary) / "synthetic")
    for project in ("cedar", "elm"):
        assert backend.remember(
            "Synthetic violet project note.",
            memory_id=project,
            topics=["cwd:" + project],
        )
    observed = {
        "search": [r["id"] for r in backend.search("violet", cwd="cedar")],
        "recent": [r["id"] for r in backend.recent(cwd="cedar")],
    }
    assert observed == {"search": ["cedar", "elm"], "recent": ["cedar", "elm"]}
    backend.close()
# Compare the documented example's data, never execute document contents.
# This is an explicit fixture example requirement, not an exact prose oracle.
examples = re.findall(
    r"```json\s*\n(.*?)\n```", (root / "guide.md").read_text(), re.DOTALL
)
assert len(examples) == 1, "Keep the single documented JSON example of returned IDs"
assert (
    json.loads(examples[0]) == observed
), "Documented project-filtering example contradicts actual adapter results"
print(
    json.dumps(
        {
            "behavior": observed,
            "source_sha256": identity["sha256"],
            "documentation_semantics": "not certified by this probe",
        }
    )
)
