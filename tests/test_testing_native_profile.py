"""# qualify: platform — real captured-change execution on supported hosts."""

import json
import os

from attune_harness import test_execution
from attune_harness.task_policies import execute_task
from test_test_change import accept, outcome, project, put  # noqa: F401


def test_execution_environment_uses_host_values_without_ambient_search(monkeypatch):
    monkeypatch.setenv("SystemRoot", r"\\synthetic.invalid\share\Windows")
    monkeypatch.setenv("PATH", "synthetic-search-decoy")
    monkeypatch.setenv("PYTHONPATH", "synthetic-import-decoy")
    monkeypatch.setenv("HARNESS_T3_ENV_DECOY", "synthetic")
    observed = test_execution.execution_environment()
    common = {
        "LANG": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "ATTUNE_USAGE_PING": "0",
        "ATTUNE_VERSION_CHECK": "0",
    }
    if os.name == "nt":
        assert set(observed) == set(common) | {"SystemRoot", "PYTHONUTF8"}
        assert observed["PYTHONUTF8"] == "1"
        assert observed["SystemRoot"] != os.environ["SystemRoot"]
        assert observed["SystemRoot"][1:3] == ":\\"
        assert {k: v for k, v in observed.items() if k in common} == common
    else:
        assert observed == {"PATH": "/usr/bin:/bin", **common}


def test_real_observer_preserves_unicode_and_finite_environment(
    project, tmp_path, monkeypatch, record_property
):
    destination = tmp_path / "repository caf\u00e9's"
    project.rename(destination)
    project = destination
    monkeypatch.setenv("HARNESS_T3_ENV_DECOY", "synthetic")
    put(project, "pytest.ini", "[pytest]\naddopts = -s\n")
    put(
        project,
        "tests/test_logic.py",
        "import json, os, sys\n"
        "from demo.logic import answer\n"
        "def test_answer():\n"
        "    assert answer() == 42\n"
        "    assert 'HARNESS_T3_ENV_DECOY' not in set(os.environ)\n"
        "    assert 'PYTHONPATH' not in set(os.environ)\n"
        "    assert sys.stdout.encoding.lower().replace('-', '') == 'utf8'\n"
        "    print('\\U0001f680 caf\\u00e9')\n"
        "    print('T3_KEYS=' + json.dumps(sorted(os.environ)))\n",
    )
    directory = accept(project, tmp_path)
    result = execute_task(directory)
    assert outcome(result) == "passed"
    saved = result["execution"]["result"]
    assert saved["pytest"]["passed"] == 1 and saved["model_calls"] == 0
    stdout = (directory / "stdout.txt").read_text(encoding="utf-8")
    assert "\U0001f680 caf\u00e9" in stdout
    keys = json.loads(next(line[8:] for line in stdout.splitlines() if line.startswith("T3_KEYS=")))
    record_property("effective_environment_keys", json.dumps(keys))
    record_property("requested_environment", json.dumps(saved["environment"]))
    assert "HARNESS_T3_ENV_DECOY" not in keys and "PYTHONPATH" not in keys
    before = (directory / "record.json").read_bytes()
    assert outcome(execute_task(directory)) == "passed"
    assert (directory / "record.json").read_bytes() == before
