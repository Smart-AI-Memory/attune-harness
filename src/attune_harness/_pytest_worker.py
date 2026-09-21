"""Pytest observer launched with the selected interpreter, not imported by Harness."""

import json
import os
from pathlib import Path
import sys
import tempfile


def main() -> int:
    """Observe actual pytest phases and persist an execution-local report."""
    root, output, token, manifest, operation, *arguments = sys.argv[1:]
    root = Path(root).resolve()
    sys.path[:0] = [str(root / "src"), str(root)]
    import pytest

    data = {
        "token": token,
        "manifest": manifest,
        "operation": operation,
        "collected": [],
        "deselected": 0,
        "calls": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "setup_errors": 0,
        "collection_errors": 0,
        "collect_only": False,
        "session_started": False,
        "pytest_version": pytest.__version__,
        "python": sys.version,
        "interpreter": sys.executable,
        "cwd": str(root),
    }

    class Observer:
        def pytest_configure(self, config):
            if config.inipath and not config.inipath.resolve().is_relative_to(root):
                raise pytest.UsageError(
                    "Pytest configuration is outside captured inputs"
                )
            if set(config.getini("python_files")) != {"test_*.py", "*_test.py"}:
                raise pytest.UsageError(
                    "Custom pytest file discovery is outside this profile"
                )

        def pytest_sessionstart(self, session):
            data["session_started"] = True
            data["collect_only"] = bool(session.config.option.collectonly)

        def pytest_collection_finish(self, session):
            data["collected"] = [item.nodeid for item in session.items]

        def pytest_deselected(self, items):
            data["deselected"] += len(items)

        def pytest_collectreport(self, report):
            data["collection_errors"] += int(report.failed)

        def pytest_runtest_logreport(self, report):
            if report.when == "call":
                data["calls"] += 1
                data["passed"] += int(report.passed)
                data["failed"] += int(report.failed)
            elif report.failed:
                data["setup_errors"] += 1
            if report.skipped:
                data["skipped"] += 1

    code = int(pytest.main(arguments, plugins=[Observer()]))
    data["exit_code"] = code
    data["module_origins"] = {
        name: str(Path(module.__file__).resolve())
        for name, module in list(sys.modules.items())
        if isinstance(getattr(module, "__file__", None), str)
    }
    # The host supplies a new output location; no checkout file is overwritten.
    destination = Path(output)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destination.parent, delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, destination)  # Atomic publication, exclusive destination.
    finally:
        if temporary is not None:
            temporary.unlink()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
