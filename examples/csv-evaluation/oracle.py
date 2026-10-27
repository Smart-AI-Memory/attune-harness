"""Protected, deterministic CSV checks. Candidate execution is not sandboxed."""

import copy
import csv
import importlib.util
import io
import json
from pathlib import Path
import sys


def evaluate(candidate, fixture, scope):
    if scope not in ("current_page", "all_matching"):
        raise ValueError("Resolve export scope before verification")
    # Capture literal expectations before calling candidate code. Do not derive
    # expected IDs by reimplementing the candidate's filtering/pagination logic.
    rows = {row["id"]: row for row in fixture["rows"]}
    headers = fixture["headers"]
    results = []
    for case in fixture["cases"]:
        expected = [headers] + [[rows[key][column] for column in headers]
                                for key in case[scope]]
        checks = dict.fromkeys(("text_output", "no_private_values", "headers",
                                "rows_order_and_values"), False)
        error = None
        try:
            text = candidate(copy.deepcopy(fixture["rows"]), status=case["status"],
                             page=case["page"], page_size=case["page_size"], scope=scope)
            checks["text_output"] = isinstance(text, str) and len(text) <= 65536
            if not checks["text_output"]:
                raise ValueError("Exporter must return bounded CSV text")
            checks["no_private_values"] = not any(
                row["private_notes"] in text for row in fixture["rows"])
            actual = list(csv.reader(io.StringIO(text, newline=""), strict=True))
            checks["headers"] = bool(actual) and actual[0] == headers
            checks["rows_order_and_values"] = actual == expected
        except Exception as exc:
            # Candidate failure is a failed case, never a missing/omitted result.
            error = type(exc).__name__
        results.append({"case": case["id"], "checks": checks,
                        "passed": all(checks.values()), "error": error})
    return {"schema_version": 1, "scope": scope, "cases": results,
            "passed": all(result["passed"] for result in results)}


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: oracle.py current_page|all_matching")
    root = Path(__file__).resolve().parent
    fixture = json.loads((root / "cases.json").read_text(encoding="utf-8"))
    try:
        spec = importlib.util.spec_from_file_location("csv_candidate", root / "exporter.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = evaluate(module.export_csv, fixture, sys.argv[1])
    except Exception as exc:
        result = {"schema_version": 1, "passed": False, "error": type(exc).__name__}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
