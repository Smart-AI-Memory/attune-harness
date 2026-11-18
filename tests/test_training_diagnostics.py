"""Retain useful preparation failures without executing a Harness workflow."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


COURSE = Path(__file__).resolve().parents[1] / "training" / "reporting"


@pytest.fixture
def helper():
    spec = importlib.util.spec_from_file_location("practice_diagnostics", COURSE / "practice.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def python_command(code):
    return [sys.executable, "-I", "-B", "-X", "utf8", "-c", code]


def failure_files(parent):
    directories = list(parent.glob("practice-diagnostics-*"))
    assert len(directories) == 1
    directory = directories[0]
    return directory, json.loads((directory / "failure.json").read_text(encoding="utf-8"))


def snapshot(directory):
    return {path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in directory.rglob("*") if path.is_file()}


def test_nonzero_child_retains_raw_unicode_and_bounded_structured_refusal(tmp_path, monkeypatch, helper):
    stdout = json.dumps({"status": "failed", "error": {
        "type": "ValueError", "detail": "Choose caf\u00e9.\nDo not overwrite.\x1b\x07" + "x" * 1000,
    }}, ensure_ascii=False).encode("utf-8") + b"\r\n"
    stderr = b"private diagnostic bytes: \xff\x00\r\npartial\r"
    command = python_command(
        f"import sys; sys.stdout.buffer.write({stdout!r}); "
        f"sys.stderr.buffer.write({stderr!r}); raise SystemExit(2)"
    )
    monkeypatch.setattr(helper, "_check_runtime", lambda: helper._run(
        command, "Harness could not prepare the practice request", step="prepare-request",
    ))
    destination = tmp_path.resolve() / "practice"
    with pytest.raises(ValueError) as caught:
        helper.prepare(destination)
    message = str(caught.value)
    assert "exited with code 2" in message
    assert "Harness reported: Choose caf\u00e9. Do not overwrite." in message
    assert "\x1b" not in message and "\x07" not in message
    assert "private diagnostic bytes" not in message and "x" * 601 not in message
    directory, receipt = failure_files(destination.parent)
    assert str(directory) in message and sys.executable in message
    assert (directory / "stdout.bin").read_bytes() == stdout
    assert (directory / "stderr.bin").read_bytes() == stderr
    assert receipt["outcome"] == "nonzero_exit"
    assert receipt["step"] == "prepare-request" and receipt["exit_code"] == 2
    assert receipt["python"] == sys.executable and receipt["elapsed_seconds"] > 0
    assert not any(receipt["partial_artifacts"].values())
    assert not destination.exists()


def test_launch_failure_keeps_actionable_git_guidance_and_records_no_exit(tmp_path, monkeypatch, helper):
    missing = str(tmp_path / "missing-git")
    monkeypatch.setattr(helper, "_check_runtime", lambda: helper._run(
        [missing, "--version"], "Install Git and make it available on PATH before starting the course",
        step="check-git",
    ))
    with pytest.raises(ValueError, match="Install Git.*could not start.*FileNotFoundError"):
        helper.prepare(tmp_path.resolve() / "practice")
    directory, receipt = failure_files(tmp_path)
    assert receipt["outcome"] == "launch_failure" and receipt["exit_code"] is None
    assert receipt["exception"] == "FileNotFoundError"
    assert (directory / "stdout.bin").read_bytes() == b""
    assert (directory / "stderr.bin").read_bytes() == b""


def test_timeout_retains_partial_bytes_and_does_not_claim_effects_are_known(tmp_path, monkeypatch, helper):
    stdout = "caf\u00e9 \u6771\u4eac\r\n".encode("utf-8")
    stderr = b"partial stderr \xff\r\n"
    command = python_command(
        "import sys, time; "
        f"sys.stdout.buffer.write({stdout!r}); sys.stdout.buffer.flush(); "
        f"sys.stderr.buffer.write({stderr!r}); sys.stderr.buffer.flush(); time.sleep(30)"
    )
    monkeypatch.setattr(helper, "_check_runtime", lambda: helper._run(
        command, "Harness could not prepare the practice request", step="prepare-request", timeout=1,
    ))
    with pytest.raises(ValueError, match="exceeded its 1-second limit; partial effects are unknown"):
        helper.prepare(tmp_path.resolve() / "practice")
    directory, receipt = failure_files(tmp_path)
    assert (directory / "stdout.bin").read_bytes() == stdout
    assert (directory / "stderr.bin").read_bytes() == stderr
    assert receipt["outcome"] == "timeout" and receipt["exit_code"] is None
    assert receipt["timeout_seconds"] == 1 and receipt["elapsed_seconds"] >= 1
    assert receipt["exception"] == "TimeoutExpired"


def test_failed_request_preserves_partial_project_and_refuses_second_attempt(tmp_path, monkeypatch, helper):
    destination = tmp_path.resolve() / "practice"
    monkeypatch.setattr(helper, "_check_runtime", lambda: "1.8.1")
    original_run = helper._run
    calls = []

    def run(command, failure, **kwargs):
        calls.append((command, kwargs))
        if kwargs["step"] == "prepare-request":
            assert kwargs["timeout"] == 30
            assert command[:6] == [sys.executable, "-I", "-B", "-X", "utf8", "-m"]
            command = python_command(
                "from pathlib import Path; "
                f"Path({str(destination / 'task.work.json')!r}).write_bytes(b'partial request'); "
                "print('request preparation failed'); raise SystemExit(2)"
            )
        return original_run(command, failure, **kwargs)

    monkeypatch.setattr(helper, "_run", run)
    with pytest.raises(ValueError, match="no plan was accepted or BUILD requested"):
        helper.prepare(destination)
    directory, receipt = failure_files(destination.parent)
    assert directory.parent == destination.parent
    assert receipt["partial_artifacts"] == {
        "project": True, "project/.git": True, "task.work.json": True,
        "task": False, "task/record.json": False, "prepared.json": False,
    }
    assert receipt["accepted"] is False and receipt["build_started"] is False
    assert receipt["model_calls"] == 0
    assert [kwargs["step"] for _, kwargs in calls] == [
        "git-init", "git-add", "git-commit", "prepare-request",
    ]
    assert not any("diagnostics" in path for path in snapshot(destination))
    project = destination / "project"
    registry = json.loads((project / "participants.json").read_text(encoding="utf-8"))
    for participant in registry["participants"].values():
        assert participant["timeout"] == 30
        assert participant["command"][:3] == [sys.executable, "-B", "-c"]
        assert participant["environment"] == {"profile": "command-env-v1", "passthrough": []}
    before = snapshot(destination.parent)
    calls.clear()
    with pytest.raises(ValueError, match="existing work is preserved"):
        helper.prepare(destination)
    assert snapshot(destination.parent) == before and calls == []


@pytest.mark.parametrize("stream", [b"not JSON\x1b[31m", b'{"error":{"detail":"not a failure"}}'])
def test_unstructured_child_output_is_saved_without_echoing_to_terminal(tmp_path, monkeypatch, helper, stream):
    monkeypatch.setattr(helper, "_check_runtime", lambda: helper._run(
        python_command(f"import sys; sys.stdout.buffer.write({stream!r}); raise SystemExit(3)"),
        "Could not prepare the practice request", step="prepare-request",
    ))
    with pytest.raises(ValueError) as caught:
        helper.prepare(tmp_path.resolve() / "practice")
    assert "Harness reported:" not in str(caught.value) and "\x1b" not in str(caught.value)
    directory, _ = failure_files(tmp_path)
    assert (directory / "stdout.bin").read_bytes() == stream


def test_preflight_python_uses_utf8_without_overriding_environment_or_help_deadline(monkeypatch, helper):
    commands = []

    def run(command, **kwargs):
        commands.append((command, kwargs))
        if command[-1] != "--help":
            return subprocess.CompletedProcess(command, 0, stdout=b"")
        verb = command[-2]
        options = {name: f"  {name}\n" for name in helper._COURSE_OPTIONS[verb]}
        if verb == "init":
            options["--for"] = "  --for {fix,plan,roundtable}\n"
        if verb == "status":
            options["--format"] = "  --format {json,markdown,html}\n"
        return subprocess.CompletedProcess(command, 0, stdout=("  task_dir\n" + "".join(options.values())).encode())

    monkeypatch.setattr(helper, "version", lambda _: "1.8.1")
    monkeypatch.setattr(helper.subprocess, "run", run)
    assert helper._check_runtime() == "1.8.1"
    assert len(commands) == 6
    for command, kwargs in commands:
        assert kwargs["timeout"] == 10 and "env" not in kwargs and "text" not in kwargs
        if command[0] == sys.executable:
            assert command[:5] == [sys.executable, "-I", "-B", "-X", "utf8"]


@pytest.mark.parametrize("newline", [b"\r\n", b"\r"], ids=["windows-crlf", "lone-cr"])
def test_preflight_accepts_real_child_help_with_universal_newlines(monkeypatch, helper, newline):
    # Emit exact bytes from a real child, including the positional declaration
    # that Windows prints with CRLF. No Harness request or workflow is created.
    help_bytes = newline.join([
        b"  task_dir", b"  --for {fix,plan,roundtable}", b"  --goal GOAL",
        b"  --project PROJECT", b"  --scope SCOPE", b"  --interpreter PYTHON",
        b"  --tests TESTS", b"  --task-dir TASK", b"  --request REQUEST",
        b"  --config CONFIG", b"  --accept  Accept this plan", b"  --checkpoint CHECKPOINT",
        b"  --allow-external  Allow the saved participants", b"  --format {json,markdown,html}", b"",
    ])
    original_run = subprocess.run
    help_calls = []

    def run(command, **kwargs):
        if command[-1] == "--help":
            help_calls.append(command[-2])
            result = original_run(python_command(
                f"import sys; sys.stdout.buffer.write({help_bytes!r})"
            ), **kwargs)
            assert result.stdout == help_bytes
            return result
        return original_run(command, **kwargs)

    monkeypatch.setattr(helper, "version", lambda _: "1.8.1")
    monkeypatch.setattr(helper.subprocess, "run", run)
    assert helper._check_runtime() == "1.8.1"
    assert help_calls == ["init", "plan", "build", "status"]


def test_diagnostic_write_failure_does_not_hide_original_failure(tmp_path, monkeypatch, helper):
    monkeypatch.setattr(helper, "_check_runtime", lambda: helper._run(
        [str(tmp_path / "missing-git")], "Install Git", step="check-git",
    ))

    def cannot_save(*args):
        raise PermissionError("cannot save")

    monkeypatch.setattr(helper, "_save_failure", cannot_save)
    with pytest.raises(ValueError, match="Install Git.*Diagnostics could not be saved.*PermissionError"):
        helper.prepare(tmp_path.resolve() / "practice")


def test_real_cli_keeps_original_failure_with_legacy_stderr_and_unicode_path(tmp_path):
    parent = tmp_path.resolve() / "\u6771\u4eac"
    parent.mkdir()
    empty_path = tmp_path / "empty-path"
    empty_path.mkdir()
    # CPython uses backslash replacement for stderr, even when a strict legacy
    # codec is requested. Exercise the actual entry point and its diagnostic path.
    environment = {**os.environ, "PATH": str(empty_path), "PYTHONIOENCODING": "cp1252:strict"}
    result = subprocess.run([
        sys.executable, "-B", str(COURSE / "practice.py"), str(parent / "practice"),
    ], capture_output=True, env=environment, timeout=20)
    assert result.returncode == 2 and result.stdout == b""
    message = result.stderr.decode("cp1252")
    assert "Install Git" in message and "could not start" in message
    assert "Inspect the local diagnostics" in message
    assert "UnicodeEncodeError" not in message and "Traceback" not in message
    assert "\\u6771\\u4eac" in message
    _, receipt = failure_files(parent)
    assert receipt["step"] == "check-git" and receipt["outcome"] == "launch_failure"
    assert not (parent / "practice").exists()
