"""Protected runner for this disposable src-layout experiment, not a sandbox."""

import importlib
from pathlib import Path
import sys
import unittest


def main():
    root = Path(__file__).resolve().parent
    source = root / "src"
    sys.path.insert(0, str(source))
    origins = {
        "attune_harness": "attune_harness/__init__.py",
        "attune_harness.documentation": "attune_harness/documentation.py",
        "attune_harness.documentation_export": "attune_harness/documentation_export.py",
    }
    for name, relative in origins.items():
        module = importlib.import_module(name)
        expected = source / relative
        if Path(module.__file__).resolve() != expected:
            raise RuntimeError(f"Fixture import origin mismatch: {name}")
        print(f"Fixture import: {name} = {expected}", flush=True)
    suite = unittest.defaultTestLoader.discover(
        str(root / "tests/generated"), pattern="test_export.py"
    )
    if suite.countTestCases() == 0:
        raise RuntimeError("No supplemental tests collected")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
