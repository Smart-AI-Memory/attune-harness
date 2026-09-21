"""Behavioral tests for the captured-change task; subprocesses use disposable repos."""

import json
import subprocess
import sys

import pytest

from attune_harness import test_change
from attune_harness.cli import main
from attune_harness.review_store import PersistenceError, RunStore, read_record
from attune_harness.task_contract import read_task
from attune_harness.task_policies import control_task, execute_task, inspect_task


def put(root, path, text):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    return target


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    put(root, ".gitignore", "__pycache__/\n.pytest_cache/\n")
    put(root, "src/demo/logic.py", "def answer():\n    return 42\n")
    put(
        root,
        "tests/test_logic.py",
        "from demo.logic import answer\ndef test_answer():\n    assert answer() == 42\n",
    )
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    put(
        root,
        "src/demo/logic.py",
        "# working-tree change\ndef answer():\n    return 42\n",
    )
    return root


def create(project, tmp_path, **kwargs):
    directory = tmp_path / "task"
    task = test_change.create_test_task(
        project,
        directory,
        scope=["src/demo/logic.py"],
        interpreter=sys.executable,
        **kwargs,
    )
    return directory, task


def accept(project, tmp_path, **kwargs):
    directory, task = create(project, tmp_path, **kwargs)
    test_change.accept_test_task(directory, task["checkpoint_digest"])
    return directory


def outcome(task):
    return task["presentation"]["current_result"]["outcome"]


def test_complete_preview_accept_status_resume_and_dirty_preservation(
    project, tmp_path
):
    put(project, "unrelated.txt", "valuable dirty work")
    directory, preview = create(project, tmp_path)
    shown = test_change.present_test_task(preview)
    assert outcome(shown) == "draft"
    assert "broader" in shown["presentation"]["markdown"]
    assert not (directory / "inputs").exists()
    assert (
        preview["request"]["selection"]["associations"]["tests/test_logic.py"]
        == "import relationship"
    )
    test_change.accept_test_task(directory, preview["checkpoint_digest"])
    result = execute_task(directory)
    assert outcome(result) == "passed"
    assert result["execution"]["result"]["pytest"]["passed"] == 1
    assert len(result["execution"]["events"]) == 1
    assert (project / "unrelated.txt").read_text() == "valuable dirty work"
    before = (directory / "record.json").read_bytes()
    assert outcome(inspect_task(directory)) == "passed"
    assert outcome(execute_task(directory)) == "passed"
    assert (directory / "record.json").read_bytes() == before
    assert not (project / "__pycache__").exists()


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("def test_failure():\n    assert False\n", "failed"),
        (
            'import pytest\ndef test_skip():\n    pytest.skip("not executed")\n',
            "no_tests",
        ),
        (
            'import pytest\n@pytest.mark.skip(reason="not executed")\ndef test_skip():\n    assert False\n',
            "no_tests",
        ),
        ("import missing_dependency_for_fixture\n", "blocked"),
        (
            'import pytest\n@pytest.fixture\ndef broken():\n    raise RuntimeError("setup")\ndef test_setup(broken):\n    pass\n',
            "blocked",
        ),
        ("def unrelated_function():\n    return 1\n", "no_tests"),
    ],
)
def test_real_pytest_outcomes(project, tmp_path, body, expected):
    put(project, "tests/test_logic.py", body)
    directory = accept(project, tmp_path)
    result = execute_task(directory)
    assert result["status"] == "completed"
    assert outcome(result) == expected
    assert result["presentation"]["next_action"]


def test_collection_only_is_not_passed_execution(project, tmp_path):
    directory = accept(project, tmp_path, pytest_args=["--collect-only", "-q"])
    result = execute_task(directory)
    assert outcome(result) == "blocked"
    assert result["execution"]["result"]["process"]["returncode"] == 0
    assert result["execution"]["result"]["pytest"]["calls"] == 0


def test_empty_selection_cannot_discover_unrelated_tests(project, tmp_path):
    (project / "tests/test_logic.py").unlink()
    put(
        project,
        "elsewhere/test_surprise.py",
        "def test_surprise():\n    assert False\n",
    )
    directory = accept(project, tmp_path)
    result = execute_task(directory)
    assert outcome(result) == "no_tests"
    assert result["execution"]["result"]["pytest"]["collected"] == []


def test_scope_associations_indirect_consumers_ambiguous_names_and_config(
    project, tmp_path
):
    put(project, "src/demo/caller.py", "from demo.logic import answer\n")
    put(project, "src/other/logic.py", "def answer():\n    return 9\n")
    put(
        project,
        "tests/test_caller.py",
        "from demo.caller import answer\ndef test_it():\n    assert answer() == 42\n",
    )
    put(project, "tests/other/test_logic.py", "def test_other():\n    assert True\n")
    put(project, "pytest.ini", "[pytest]\n")
    _, task = create(project, tmp_path)
    selected = task["request"]["selection"]
    assert selected["mode"] == "broader_fallback"
    assert len(selected["selected"]) == 3
    assert selected["associations"]["tests/test_caller.py"] == "import relationship"
    second = test_change.create_test_task(
        project,
        tmp_path / "config-task",
        scope=["pytest.ini"],
        interpreter=sys.executable,
    )
    assert second["request"]["selection"]["selected"] == selected["selected"]


def test_explicit_narrowing_discloses_excluded_checks(project, tmp_path):
    put(project, "tests/test_other.py", "def test_other():\n    assert True\n")
    _, task = create(project, tmp_path, tests=["tests/test_logic.py"])
    assert task["request"]["selection"]["excluded"] == ["tests/test_other.py"]
    assert task["request"]["selection"]["mode"] == "explicit"


def test_explicit_test_directory_includes_support_files_without_selecting_them(
    project, tmp_path
):
    put(project, "tests/conftest.py", "# fixture support\n")
    put(project, "tests/__init__.py", "")
    put(project, "tests/data.json", "{}")
    _, task = create(project, tmp_path, tests=["tests"])
    assert task["request"]["selection"]["selected"] == ["tests/test_logic.py"]
    with pytest.raises(ValueError, match="candidate"):
        test_change.create_test_task(
            project,
            tmp_path / "bad",
            scope=["src"],
            tests=["tests/conftest.py"],
            interpreter=sys.executable,
        )


@pytest.mark.parametrize(
    "path", ["src/demo/logic.py", "tests/test_logic.py", "pytest.ini"]
)
def test_stale_input_cannot_be_accepted(project, tmp_path, path):
    directory, task = create(project, tmp_path)
    put(project, path, "# new input\n")
    with pytest.raises(ValueError, match="Stale"):
        test_change.accept_test_task(directory, task["checkpoint_digest"])
    assert not (directory / "inputs").exists()


def test_stale_result_and_missing_output_are_visible_without_dispatch(
    project, tmp_path
):
    directory = accept(project, tmp_path)
    assert outcome(execute_task(directory)) == "passed"
    (directory / "stdout.txt").unlink()
    assert outcome(inspect_task(directory)) == "blocked"
    assert read_record(directory)["execution"]["result"]["outcome"] == "passed"
    with pytest.raises(ValueError):
        execute_task(directory)


def test_source_changes_after_execution_invalidate_reuse(project, tmp_path):
    directory = accept(project, tmp_path)
    execute_task(directory)
    put(project, "src/demo/logic.py", "changed = True\n")
    assert outcome(inspect_task(directory)) == "blocked"
    with pytest.raises(ValueError, match="Stale"):
        execute_task(directory)


@pytest.mark.parametrize("damage", ["foreign", "count", "origin", "malformed"])
def test_inconsistent_worker_evidence_never_passes(
    project, tmp_path, monkeypatch, damage
):
    from attune_harness import test_execution

    directory = accept(project, tmp_path)
    invoke = test_execution.process.invoke

    def alter(*args, **kwargs):
        result = invoke(*args, **kwargs)
        output = directory / "pytest.json"
        data = json.loads(output.read_text())
        if damage == "foreign":
            data["token"] = "another request"
        elif damage == "count":
            data["calls"] = -1
        elif damage == "origin":
            data["module_origins"]["demo.logic"] = "/installed/old/logic.py"
        output.write_text("{" if damage == "malformed" else json.dumps(data))
        return result

    monkeypatch.setattr(test_execution.process, "invoke", alter)
    result = execute_task(directory)
    assert result["execution"]["result"]["process"]["returncode"] == 0
    assert outcome(result) == "blocked"


def test_saved_artifact_and_worker_changes_invalidate_success(
    project, tmp_path, monkeypatch
):
    directory = accept(project, tmp_path)
    execute_task(directory)
    (directory / "stdout.txt").write_text("forged output")
    assert outcome(inspect_task(directory)) == "blocked"
    worker = put(tmp_path, "different_worker.py", "# replaced observer\n")
    monkeypatch.setattr(test_change, "WORKER", worker)
    with pytest.raises(ValueError, match="observer identity"):
        execute_task(directory)


def test_test_writes_stay_in_copy_and_cannot_manufacture_pass(project, tmp_path):
    put(
        project,
        "tests/test_logic.py",
        'from pathlib import Path\ndef test_write():\n    Path("src/demo/logic.py").write_text("changed = True")\n',
    )
    original = (project / "src/demo/logic.py").read_bytes()
    directory = accept(project, tmp_path)
    assert outcome(execute_task(directory)) == "blocked"
    assert (project / "src/demo/logic.py").read_bytes() == original


def test_full_output_beyond_old_limit_and_overflow(project, tmp_path):
    put(
        project,
        "tests/test_logic.py",
        'def test_output():\n    print("x" * 18000 + "END_MARKER")\n',
    )
    directory = accept(project, tmp_path, pytest_args=["-q", "-s"])
    result = execute_task(directory)
    assert outcome(result) == "passed"
    assert "END_MARKER" in (directory / "stdout.txt").read_text()
    assert (directory / "stdout.txt").stat().st_size > 10240
    task = test_change.create_test_task(
        project,
        tmp_path / "limited",
        scope=["src/demo/logic.py"],
        interpreter=sys.executable,
        pytest_args=["-q", "-s"],
        max_output_bytes=1024,
    )
    test_change.accept_test_task(tmp_path / "limited", task["checkpoint_digest"])
    limited = execute_task(tmp_path / "limited")
    assert outcome(limited) == "blocked"
    assert limited["execution"]["result"]["output_complete"] is False


def test_timeout_is_retained_and_never_repeated(project, tmp_path):
    put(
        project,
        "tests/test_logic.py",
        "import time\ndef test_wait():\n    time.sleep(30)\n",
    )
    directory = accept(project, tmp_path, timeout=0.15)
    assert outcome(execute_task(directory)) == "interrupted"
    before = (directory / "record.json").read_bytes()
    assert outcome(execute_task(directory)) == "interrupted"
    assert (directory / "record.json").read_bytes() == before


def test_pause_resume_reuses_completed_operation(project, tmp_path):
    marker = tmp_path / "count.txt"
    put(
        project,
        "tests/test_logic.py",
        f'from pathlib import Path\ndef test_count():\n    p=Path({str(marker)!r})\n    p.write_text(p.read_text()+"x" if p.exists() else "x")\n',
    )
    directory = accept(project, tmp_path)
    assert outcome(execute_task(directory, max_operations=1)) == "paused"
    assert marker.read_text() == "x"
    assert outcome(execute_task(directory)) == "passed"
    assert marker.read_text() == "x"


def test_crash_after_dispatch_never_uses_read_only_retry(
    project, tmp_path, monkeypatch
):
    from attune_harness import test_execution

    directory = accept(project, tmp_path)

    def crash(*args, **kwargs):
        raise RuntimeError("host crashed after durable dispatch")

    monkeypatch.setattr(test_execution.process, "invoke", crash)
    with pytest.raises(RuntimeError):
        execute_task(directory)
    task = read_task(directory)
    assert task["execution"]["events"][0]["phase"] == "dispatching"
    assert outcome(execute_task(directory)) == "interrupted"
    with pytest.raises(ValueError, match="may have effects"):
        control_task(directory, "reconcile", retry_read_only=True)
    cancelled = control_task(directory, "cancel", reason="inspect before new task")
    assert cancelled["status"] == "cancelled"
    assert "effects remain unresolved" in cancelled["presentation"]["markdown"]


def test_failed_dispatch_persistence_prevents_execution(project, tmp_path, monkeypatch):
    directory = accept(project, tmp_path)
    original = RunStore.save

    def reject(self, record):
        events = record.get("execution", {}).get("events", [])
        if events and events[0]["phase"] == "dispatching":
            raise PersistenceError("disk unavailable")
        return original(self, record)

    monkeypatch.setattr(RunStore, "save", reject)
    with pytest.raises(PersistenceError):
        execute_task(directory)
    assert not (directory / "inputs").exists()


def test_storage_and_scope_rejected_before_any_effect(project, tmp_path):
    with pytest.raises(ValueError, match="outside"):
        test_change.create_test_task(
            project, project / "task", scope=["src"], interpreter=sys.executable
        )
    with pytest.raises(ValueError, match="relative"):
        test_change.create_test_task(
            project, tmp_path / "task", scope=["../secret"], interpreter=sys.executable
        )
    assert not (tmp_path / "task").exists()


def test_symlink_parent_rejected_before_creating_task(project, tmp_path):
    target = tmp_path / "real"
    target.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        test_change.create_test_task(
            project, alias / "task", scope=["src"], interpreter=sys.executable
        )
    assert not (target / "task").exists()


def test_change_scope_distinguishes_clean_files_and_staged_deletions(project, tmp_path):
    put(project, "src/demo/clean.py", "value = 1\n")
    subprocess.run(["git", "-C", str(project), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(project),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "-qm",
            "clean",
        ],
        check=True,
    )
    with pytest.raises(ValueError, match="working-tree change"):
        create(project, tmp_path)
    assert not (tmp_path / "task").exists()
    subprocess.run(
        ["git", "-C", str(project), "rm", "src/demo/logic.py"],
        check=True,
        capture_output=True,
    )
    task = test_change.create_test_task(
        project, tmp_path / "deleted", scope=["src"], interpreter=sys.executable
    )
    assert task["request"]["selection"]["changed_files"] == ["src/demo/logic.py"]
    assert task["request"]["snapshot"]["files"]["src/demo/logic.py"] is None


def test_custom_discovery_is_explicitly_outside_first_profile(project, tmp_path):
    put(project, "pytest.ini", "[pytest]\npython_files = check_*.py\n")
    put(project, "tests/check_missing.py", "def test_fail():\n    assert False\n")
    directory = accept(project, tmp_path)
    result = execute_task(directory)
    assert outcome(result) == "blocked"
    assert result["execution"]["result"]["pytest"]["calls"] == 0
    assert "Custom pytest file discovery" in (directory / "stderr.txt").read_text()


@pytest.mark.parametrize("config", ["ini", "toml", "precedence"])
def test_explicit_default_discovery_config_executes_normally(project, tmp_path, config):
    if config in ("ini", "precedence"):
        put(project, "pytest.ini", "[pytest]\npython_files = test_*.py *_test.py\n")
    if config == "toml":
        put(
            project,
            "pyproject.toml",
            '[tool.pytest.ini_options]\npython_files = ["test_*.py", "*_test.py"]\n',
        )
    if config == "precedence":
        put(
            project,
            "pyproject.toml",
            '[tool.pytest.ini_options]\npython_files = ["check_*.py"]\n',
        )
    directory = accept(project, tmp_path)
    assert outcome(execute_task(directory)) == "passed"


def test_capture_race_and_symlink_input_prevent_intake(project, tmp_path, monkeypatch):
    real = test_change.select

    def race(*args):
        result = real(*args)
        put(project, "pytest.ini", "[pytest]\n")
        return result

    monkeypatch.setattr(test_change, "select", race)
    with pytest.raises(ValueError, match="changed while capturing"):
        create(project, tmp_path)
    assert not (tmp_path / "task").exists()
    (project / "alias").symlink_to(project / "src/demo/logic.py")
    with pytest.raises(ValueError, match="Symlink"):
        create(project, tmp_path)


def test_saved_acceptance_rejects_overrides(project, tmp_path, capsys):
    directory, task = create(project, tmp_path)
    assert (
        main(
            [
                "test",
                "--task-dir",
                str(directory),
                "--accept",
                "--checkpoint",
                task["checkpoint_digest"],
                "--timeout",
                "5",
            ]
        )
        == 2
    )
    assert "no input overrides" in capsys.readouterr().out
    assert read_task(directory)["status"] == "draft"


def test_cli_full_journey_and_nonzero_failure_exit(project, tmp_path, capsys):
    directory = tmp_path / "cli-task"
    args = [
        "test",
        "--project",
        str(project),
        "--task-dir",
        str(directory),
        "--scope",
        "src/demo/logic.py",
        "--interpreter",
        sys.executable,
    ]
    assert main(args) == 1
    preview = json.loads(capsys.readouterr().out)
    assert (
        main(
            [
                "test",
                "--task-dir",
                str(directory),
                "--accept",
                "--checkpoint",
                preview["checkpoint_digest"],
            ]
        )
        == 0
    )
    executed = json.loads(capsys.readouterr().out)
    assert outcome(executed) == "passed"
    assert main(["status", str(directory)]) == 0
    assert outcome(json.loads(capsys.readouterr().out)) == "passed"
    assert main(["resume", str(directory)]) == 0
    capsys.readouterr()
    put(project, "tests/test_logic.py", "def test_fail():\n    assert False\n")
    args[args.index(str(directory))] = str(tmp_path / "failure-task")
    assert main([*args, "--accept"]) == 1
    assert outcome(json.loads(capsys.readouterr().out)) == "failed"
