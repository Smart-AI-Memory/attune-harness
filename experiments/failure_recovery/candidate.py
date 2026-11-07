"""Subprocess boundary: receive case inputs only, never expected outputs."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys


class BoundedText(io.StringIO):
    def write(self, text):
        if self.tell() + len(text) > 16384:
            raise ValueError("Candidate diagnostics exceeded bound")
        return super().write(text)


def main():
    try:
        raw = sys.stdin.buffer.read(32769)
        if len(raw) > 32768:
            raise ValueError("Case input exceeded bound")
        case = json.loads(raw)
        with contextlib.redirect_stdout(BoundedText()), contextlib.redirect_stderr(BoundedText()):
            spec = importlib.util.spec_from_file_location("trial_candidate", Path(sys.argv[1]))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            text = module.export_csv(case["rows"], **case["arguments"])
        if not isinstance(text, str) or len(text.encode("utf-8")) > 16384:
            raise ValueError("Candidate must return bounded CSV text")
        result = {"schema_version": 1, "returned": True, "csv": text}
    except (Exception, SystemExit) as exc:
        result = {"schema_version": 1, "returned": False, "error": type(exc).__name__}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
