"""Independent literal expectations; submitted Python runs in a separate process."""

import copy
import csv
import io
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from attune_harness.process import invoke

from . import bounds, solutions

HERE = Path(__file__).resolve().parent
HEADER = ["id", "title", "status"]
CASE_IDS = {"first", "quoted-unicode", "partial", "empty-page", "empty-filter", "hidden-private", "hidden-order"}


def retain_process(output, name, run):
    facts = {"returncode": run.returncode, "failure": run.failure}
    for field in ("stdout", "stderr"):
        data = getattr(run, field).encode("utf-8")
        path = output / (name + "-" + field + ".txt")
        bounds.write_bytes(path, data)
        facts[field] = {"path": path.name, "bytes": len(data), "sha256": bounds.sha(data)}
    bounds.write_json(output / (name + "-process.json"), facts)


def cases():
    rows = copy.deepcopy(solutions.ROWS)
    return [
        {"id": "first", "rows": rows, "arguments": {"status": "active", "page": 1, "page_size": 2},
         "expected": [HEADER, ["r1", "Alpha", "active"], ["r3", "Comma, title", "active"]]},
        {"id": "quoted-unicode", "rows": rows, "arguments": {"status": "active", "page": 2, "page_size": 2},
         "expected": [HEADER, ["r4", 'A "quote"', "active"], ["r5", "Café\n第二行", "active"]]},
        {"id": "partial", "rows": rows, "arguments": {"status": "active", "page": 3, "page_size": 2},
         "expected": [HEADER, ["r6", "Last", "active"]]},
        {"id": "empty-page", "rows": rows, "arguments": {"status": "active", "page": 4, "page_size": 2}, "expected": [HEADER]},
        {"id": "empty-filter", "rows": rows, "arguments": {"status": "missing", "page": 1, "page_size": 2}, "expected": [HEADER]},
        {"id": "hidden-private", "rows": [
            {"id": "hidden", "title": "An inactive report", "status": "inactive", "private_notes": "SYNTHETIC-HIDDEN-PRIVATE"}],
         "arguments": {"status": "inactive", "page": 1, "page_size": 2},
         "expected": [HEADER, ["hidden", "An inactive report", "inactive"]]},
        {"id": "hidden-order", "rows": [
            {"id": "z", "title": "Last alphabetically", "status": "active", "private_notes": "SYNTHETIC-Z"},
            {"id": "a", "title": "First alphabetically", "status": "active", "private_notes": "SYNTHETIC-A"}],
         "arguments": {"status": "active", "page": 1, "page_size": 4},
         "expected": [HEADER, ["z", "Last alphabetically", "active"], ["a", "First alphabetically", "active"]]},
    ]


def environment(root):
    root = bounds.directory(root)
    values = {"PATH": os.defpath, "HOME": str(root), "TMPDIR": str(root), "TMP": str(root), "TEMP": str(root),
              "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
              "ATTUNE_USAGE_PING": "0", "ATTUNE_VERSION_CHECK": "0", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
              "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "XDG_CONFIG_HOME": str(root)}
    if os.name == "nt":
        values["SystemRoot"] = os.environ["SystemRoot"]
        values.update(USERPROFILE=str(root), APPDATA=str(root), LOCALAPPDATA=str(root))
    return values


def evaluate(app, expected_cases, output):
    app = bounds.directory(app)
    source = app / "src/report.py"
    output = bounds.external_directory(output, app, create=True)
    frozen = copy.deepcopy(expected_cases)
    import re
    if (not 1 <= len(frozen) <= 8 or len({c["id"] for c in frozen}) != len(frozen)
            or any(not isinstance(c["id"], str) or not re.fullmatch(r"[a-z0-9-]{1,40}", c["id"]) for c in frozen)):
        raise ValueError("Oracle cases must have bounded distinct identities")
    results = []
    try:
        original = bounds.read_bytes(source)
        bounds.write_bytes(output / "submitted.py", original)
        unavailable = None
    except (OSError, ValueError) as exc:
        original, unavailable = None, type(exc).__name__
    for case in frozen:
        checks = {"returned_text": False, "csv_rows": False, "no_private_values": False}
        error = unavailable
        ready = original is not None
        if ready:
            try:
                if bounds.read_bytes(source) != original or bounds.read_bytes(output / "submitted.py") != original:
                    raise ValueError("Source identity changed before candidate launch")
            except (OSError, ValueError) as exc:
                ready, error = False, type(exc).__name__
        if ready:
            wire = json.dumps({k: case[k] for k in ("rows", "arguments")}, ensure_ascii=False)
            run = invoke((sys.executable, "-X", "utf8", "-I", "-B", str(HERE / "candidate.py"), str(output / "submitted.py")), wire,
                         cwd=output, environment=environment(output), timeout=3, max_output_bytes=16384)
            retain_process(output, case["id"], run)
            try:
                if (run.failure or run.returncode != 0 or bounds.read_bytes(source) != original
                        or bounds.read_bytes(output / "submitted.py") != original):
                    raise ValueError("Candidate process or source identity failed")
                reply = json.loads(run.stdout)
                if set(reply) != {"schema_version", "returned", "csv"} or reply["schema_version"] != 1 or reply["returned"] is not True:
                    raise ValueError("Candidate did not return through the trusted runner")
                text = reply["csv"]
                checks["returned_text"] = isinstance(text, str) and len(text.encode("utf-8")) <= 16384
                if not checks["returned_text"]:
                    raise ValueError("Unbounded/nontext candidate result")
                checks["csv_rows"] = list(csv.reader(io.StringIO(text, newline=""), strict=True)) == case["expected"]
                checks["no_private_values"] = not any(row["private_notes"] in text for row in case["rows"])
                error = None
            except (OSError, ValueError, TypeError, KeyError, csv.Error) as exc:
                error = type(exc).__name__
        results.append({"id": case["id"], "checks": checks, "error": error,
                        "execution": "started" if ready else "not_started_source_unavailable",
                        "passed": all(checks.values()) and error is None})
    result = {"schema_version": 1, "kind": "independent-offline-oracle", "cases": results,
              "source_sha256": bounds.sha(original) if original is not None else None,
              "passed": all(c["passed"] for c in results), "model_calls": 0}
    bounds.write_json(output / "result.json", result)
    return result


def pytest_report(app, tests, output, *, baseline=False):
    """Retain actual per-case failures; a nonzero process alone is not a red test."""
    output = bounds.external_directory(output, app, create=True)
    argv = [sys.executable, "-X", "utf8", "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--junitxml=" + str(output / "tests.xml"), *tests]
    if baseline:
        argv += ["-k", "baseline"]
    result = invoke(tuple(argv), "", cwd=app, environment=environment(output), timeout=30, max_output_bytes=16384)
    retain_process(output, "pytest", result)
    items = []
    try:
        tree = ET.fromstring(bounds.read_bytes(output / "tests.xml"))
        for case in tree.iter("testcase"):
            problem = case.find("failure")
            items.append({"name": case.get("name"), "failed": problem is not None,
                          "feature_assertion": problem is not None and "AssertionError" in (problem.text or "") and "feature:" in (problem.text or ""),
                          "error": case.find("error") is not None, "skipped": case.find("skipped") is not None})
        collection_errors = any(node.find("error") is not None for node in tree.iter("testcase"))
    except (OSError, ValueError, ET.ParseError):
        collection_errors = True
    return {"returncode": result.returncode, "failure": result.failure, "cases": items, "collection_errors": collection_errors}


def supplemental(app, initial_source, output):
    output = bounds.external_directory(output, app, create=True)
    reports = {}
    for phase, source in (("initial", initial_source), ("final", bounds.read_bytes(app / "src/report.py"))):
        clone = output / phase
        clone.mkdir()
        (clone / "src").mkdir()
        (clone / "tests").mkdir()
        bounds.write_bytes(clone / "src/report.py", source)
        bounds.write_bytes(clone / "tests/test_report_extra.py", bounds.read_bytes(app / "tests/generated/test_report_extra.py"))
        bounds.write_bytes(clone / "pytest.ini", b"[pytest]\npythonpath = src\n")
        reports[phase] = pytest_report(clone, ["tests/test_report_extra.py"], output / (phase + "-checks"))
    before, after = reports["initial"], reports["final"]
    names = {c["name"] for c in before["cases"]}
    passed = (before["returncode"] == 1 and after["returncode"] == 0
              and before["failure"] in (None, "nonzero_exit") and after["failure"] is None
              and not before["collection_errors"] and not after["collection_errors"]
              and bool(names) and names == {c["name"] for c in after["cases"]}
              and all(c["failed"] and c["feature_assertion"] and not c["error"] and not c["skipped"] for c in before["cases"])
              and all(not c["failed"] and not c["error"] and not c["skipped"] for c in after["cases"]))
    result = {"qualified": passed, "initial": before, "final": after,
              "chronology": "post-collection isolated artifact validation, not proof of red-first development"}
    bounds.write_json(output / "result.json", result)
    return result
