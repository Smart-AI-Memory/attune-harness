"""One atomic replace under src/, with the Windows retry (O-59).

``features.replace_file`` retries ``os.replace`` for a bounded time on Windows
while a reader holds the target open; the run store had it, the plan state
writer and the Voyage index writer called ``os.replace`` once. Every writer
goes through it now, and this file keeps it that way.
"""
# qualify: platform

import json
import re
from pathlib import Path

from attune_harness import features, spec_state, voyage_index


def test_every_replace_under_src_goes_through_replace_file():
    # repair.py is the one exception: the effects host replaces through
    # directory descriptors (src_dir_fd/dst_dir_fd), POSIX-only by design,
    # and Windows has its own windows_effects.replace_file.
    root = Path(features.__file__).parent
    callers = sorted(
        p.name for p in root.glob("*.py") if re.search(r"\bos\.replace\(", p.read_text(encoding="utf-8"))
    )
    assert callers == ["features.py", "repair.py"]


def _recording(monkeypatch, module):
    calls = []

    def recorded(source, target, **named):
        calls.append((Path(source), Path(target)))
        return features.replace_file(source, target, **named)

    monkeypatch.setattr(module, "replace_file", recorded)
    return calls


def test_plan_state_is_written_through_replace_file(tmp_path, monkeypatch):
    calls = _recording(monkeypatch, spec_state)
    target = tmp_path / "plan.md"
    target.write_text("old\n", encoding="utf-8")
    spec_state._atomic_write_text(target, "new\r\nline\r\n")
    assert target.read_bytes() == b"new\r\nline\r\n"
    assert [t for _, t in calls] == [target]
    assert calls[0][0].parent == tmp_path and not calls[0][0].exists()


def test_voyage_index_metadata_is_written_through_replace_file(tmp_path, monkeypatch):
    calls = _recording(monkeypatch, voyage_index)
    target = tmp_path / "index.json"
    voyage_index.write_json(target, {"b": 1, "a": [1, 2]})
    assert json.loads(target.read_text(encoding="utf-8")) == {"a": [1, 2], "b": 1}
    assert [t for _, t in calls] == [target]
    assert not calls[0][0].exists()
