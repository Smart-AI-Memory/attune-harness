"""Fixed local command participant. No SDK, network, tools or model selection."""

import json
from pathlib import Path
import runpy
import sys


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("valid", "wrong", "scope", "protected", "blind-spot", "incomplete"):
        raise ValueError("Unknown offline control")
    raw = sys.stdin.buffer.read(65537)
    if len(raw) > 65536:
        raise ValueError("Offline turn exceeds its bound")
    wire = json.loads(raw)
    turn, mode = wire["turn"], sys.argv[1]
    if turn["role"] == "reviewer":
        payload = {"kind": "critique", "findings": [], "notes": ["Scripted offline control; no model judgment."]}
    else:
        fixed = runpy.run_path(str(Path(__file__).with_name("solutions.py")))
        source = fixed[{"wrong": "WRONG", "blind-spot": "BLIND_SPOT"}.get(mode, "GOOD")]
        texts = {"src/report.py": source, "tests/generated/test_report_extra.py": fixed["SUPPLEMENTAL"]}
        if mode == "incomplete":
            texts["tests/generated/test_report_extra.py"] = "def test_useless():\n    assert True\n"
        files = [{**item, "text": texts[item["path"]]} for item in turn["output_schema"]["files"]]
        if mode in ("scope", "protected"):
            files[0]["path"] = "docs/operator-notes.md" if mode == "scope" else "tests/test_report.py"
        payload = {"schema_version": 2, "files": files}
    print(json.dumps({"schema_version": 1, "request_digest": wire["request_digest"],
                      "action": {"kind": "final", "text": json.dumps(payload)}}))


if __name__ == "__main__":
    main()
