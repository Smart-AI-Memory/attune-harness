"""Scripted participants for local transport rehearsal; no model judgment."""

import json
from pathlib import Path
import sys
import time

packet = json.load(sys.stdin)
turn = packet["turn"]
repair = turn.get("repair")
if repair is None:
    # Assert supplied references contain the inspected implementation before
    # simulating a response. A fixture key never substitutes for source delivery.
    references = json.dumps(turn["initial_retrieval"])
    assert "soft boost for same-project findings" in references
    assert "records.sort" in references
    bad = "Every alternative memory backend guarantees" in turn["document"]["text"]
    answer = (
        "Required corrections: the only-project guarantee contradicts the supplied "
        "FileStashBackend source and two-project probe: search boosts matching cwd "
        "and recent orders it first, while both retain foreign records. Replace "
        "isolation with retrieval preference. The guarantee about every alternative "
        "backend lacks supplied support and must be qualified, removed or "
        "substantiated. Other backends remain unknown; do not assert they lack "
        "isolation. Optional wording advice: none. This is a scripted rehearsal."
        if bad
        else "Accepted within the supplied evidence: ranking and foreign-project "
        "visibility are stated correctly; other backends are accurately unknown. "
        "No required correction. Optional wording advice: none. This is a "
        "scripted rehearsal, not model qualification or human acceptance."
    )
elif turn["role"] == "worker":
    answer = json.dumps(
        {
            "schema_version": 1,
            "replacements": [
                {
                    "path": "guide.md",
                    "before_sha256": repair["before_hashes"]["guide.md"],
                    "text": Path(sys.argv[2]).read_text(),
                }
            ],
        }
    )
else:
    answer = json.dumps(
        {
            "schema_version": 1,
            "artifact_digest": repair["artifact_digest"],
            "probe_digest": repair["probe_digest"],
            "verdict": "approve",
            "findings": [],
        }
    )
response = {
    "schema_version": 1,
    "request_digest": packet["request_digest"],
    "action": {"kind": "final", "text": answer},
}
with open(sys.argv[1], "a") as stream:
    stream.write(
        json.dumps(
            {"request": packet, "response": response, "monotonic": time.monotonic()}
        )
        + "\n"
    )
print(json.dumps(response))
