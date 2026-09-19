"""Behavioral qualification with real bounded subprocesses; no paid providers."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Thread
import time

import pytest

SCRIPT = Path(__file__).with_name("control.py")
spec = importlib.util.spec_from_file_location("isolated_response_controls", SCRIPT)
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


def argv(code):
    return [sys.executable, "-B", "-c", code]


def create(tmp_path, code="print('response')", **kwargs):
    options = dict(argv=argv(code), label="Repair test", cwd=tmp_path,
                   warning_seconds=.05, timeout_seconds=4, notification_backend="inbox")
    options.update(kwargs)
    return control.create(tmp_path / "jobs", **options)


def wait_for(job, predicate, timeout=6):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        value = control.status(job)
        if predicate(value):
            return value
        time.sleep(.02)
    pytest.fail("Job did not reach expected state: " + repr(control.status(job)))


def complete(job):
    return wait_for(job, lambda view: view["phase"] in control.TERMINAL)


def test_wait_is_same_attempt_and_warning_does_not_fail_correctness(tmp_path):
    marker = tmp_path / "dispatches"
    code = f"from pathlib import Path; import time; p=Path({str(marker)!r}); p.write_text(p.read_text()+'x' if p.exists() else 'x'); time.sleep(.35); print('ok')"
    job = create(tmp_path, code, validator=argv("import sys; assert sys.stdin.read() == 'ok\\n'"))
    view = wait_for(job, lambda v: v["warning"])
    assert view["phase"] == "responding" and view["correctness"] == "unknown"
    for _ in range(3):
        control.action(job, "wait")
    result = complete(job)
    assert result["phase"] == "passed" and result["correctness"] == "passed_configured_checks"
    assert result["soft_limit_exceeded"]
    assert result["responsiveness"] == "within_budget" and marker.read_text() == "x"
    with pytest.raises(ValueError, match="already claimed"):
        # Wait for ownership release; completion publication precedes cleanup.
        wait_for(job, lambda v: not control.owner_active(job))
        control.worker(job)
    assert marker.read_text() == "x"


def test_notify_detaches_client_survives_exit_and_waits_for_validation(tmp_path):
    parent = tmp_path / "jobs"
    cmd = [sys.executable, "-B", str(SCRIPT), "start", "--jobs", str(parent), "--cwd", str(tmp_path),
           "--label", "Detached repair", "--warn-after", ".05", "--timeout", "5", "--notify-backend", "inbox",
           "--validator-json", json.dumps(argv("import time,sys; time.sleep(.3); assert sys.stdin.read()=='ok\\n'")),
           "--", *argv("import time; time.sleep(.2); print('ok')")]
    client = subprocess.run(cmd, capture_output=True, text=True, timeout=3, check=True)
    job = Path(client.stdout.strip())
    for _ in range(3):
        control.action(job, "notify")
    validating = wait_for(job, lambda v: v["phase"] == "validating")
    assert "validation is running" in validating["message"]
    assert not (job / "notification.json").exists()
    finished = wait_for(job, lambda v: v["notification"] == "inbox_ready")
    assert finished["phase"] == "passed"
    notice = (job / "notification.json").read_bytes()
    control.action(job, "notify")
    assert (job / "notification.json").read_bytes() == notice


def test_cancel_before_start_dispatches_nothing(tmp_path):
    marker = tmp_path / "unexpected"
    job = create(tmp_path, f"from pathlib import Path; Path({str(marker)!r}).write_text('ran')", spawn=False)
    requested = control.action(job, "cancel")
    assert requested["phase"] == "queued" and requested["cancel_requested"]
    control.worker(job)
    result = control.status(job)
    assert result["phase"] == "cancelled_before_start" and not result["response_dispatched"]
    assert not marker.exists() and not (job / "response.json").exists()


def test_cancel_running_retains_partial_output_and_does_not_validate(tmp_path):
    job = create(tmp_path, "import time; print('partial',flush=True); time.sleep(10)",
                 validator=argv("raise AssertionError('should not validate')"))
    wait_for(job, lambda v: v["warning"])
    requested = control.action(job, "cancel")
    assert requested["cancel_requested"] and "requested" in requested["message"]
    result = complete(job)
    assert result["phase"] == "cancelled_effects_unknown" and not result["validation_dispatched"]
    assert "partial" in control.read(job / "response.json")["stdout"]
    assert result["cost"] == "unavailable"


def test_cancel_during_validation_never_claims_acceptance(tmp_path):
    job = create(tmp_path, validator=argv("import time; print('checking',flush=True); time.sleep(10)"))
    wait_for(job, lambda v: v["phase"] == "validating")
    control.action(job, "cancel")
    result = complete(job)
    assert result["phase"] == "cancelled_effects_unknown" and result["correctness"] == "unknown"


def test_late_cancel_preserves_finished_result(tmp_path):
    job = create(tmp_path, validator=argv("import sys; assert sys.stdin.read()"))
    result = complete(job)
    assert result["phase"] == "passed"
    before = (job / "state.json").read_bytes()
    view = control.action(job, "cancel")
    assert view["phase"] == "passed" and not view["cancel_requested"]
    assert before == (job / "state.json").read_bytes()


@pytest.mark.parametrize("cancel_first", [True, False])
def test_completion_cancel_order_has_one_terminal_outcome(tmp_path, cancel_first):
    job = create(tmp_path, spawn=False)
    state = control.read(job / "state.json")
    state.update(phase="responding", response_dispatched=True)
    control.write(job / "state.json", state)
    operations = [lambda: control.action(job, "cancel"), lambda: control.finish(job, "ready", time.monotonic())]
    if not cancel_first:
        operations.reverse()
    for operation in operations:
        operation()
    result = control.status(job)
    assert result["phase"] == ("cancelled_effects_unknown" if cancel_first else "ready")
    assert not result["validation_dispatched"]


def test_simultaneous_notify_completion_produces_one_notice(tmp_path):
    job = create(tmp_path, spawn=False)
    calls = [lambda: control.action(job, "notify") for _ in range(4)]
    calls.append(lambda: control.finish(job, "ready", time.monotonic()))
    threads = [Thread(target=call) for call in calls]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2)
        assert not thread.is_alive()
    assert control.status(job)["notification"] == "inbox_ready"
    assert control.read(job / "notification.json")["phase"] == "ready"


def test_timeout_is_operational_failure_and_preserves_output(tmp_path):
    job = create(tmp_path, "import time; print('partial',flush=True); time.sleep(10)", timeout_seconds=.2)
    result = complete(job)
    assert result["phase"] == "timed_out_effects_unknown"
    assert result["correctness"] == "unknown" and result["responsiveness"] == "deadline_exceeded"
    assert "partial" in control.read(job / "response.json")["stdout"]


def test_total_deadline_includes_validation(tmp_path):
    job = create(tmp_path, "import time; time.sleep(.15); print('ok')", timeout_seconds=.3,
                 validator=argv("import time; time.sleep(.4)"))
    result = complete(job)
    assert result["phase"] == "timed_out_effects_unknown" and result["validation_dispatched"]
    assert result["elapsed_seconds"] < 1


def test_response_exit_zero_is_not_correctness_without_validator(tmp_path):
    job = create(tmp_path)
    result = complete(job)
    assert result["phase"] == "ready" and result["correctness"] == "unknown"


def test_failed_validation_notifies_failure(tmp_path):
    job = create(tmp_path, validator=argv("import sys; sys.exit(1)"))
    control.action(job, "notify")
    result = wait_for(job, lambda v: v["notification"] == "inbox_ready")
    assert result["phase"] == "rejected" and result["correctness"] == "failed_configured_checks"
    assert control.read(job / "notification.json")["phase"] == "rejected"


def test_notification_capability_is_explicit(tmp_path):
    job = create(tmp_path, spawn=False, notification_backend="none")
    assert {o["action"] for o in control.status(job)["options"]} == {"wait", "cancel"}
    with pytest.raises(ValueError, match="no notification"):
        control.action(job, "notify")


def test_desktop_failure_leaves_inbox_and_does_not_repeat(tmp_path, monkeypatch):
    monkeypatch.setattr(control, "desktop_supported", lambda: True)
    job = create(tmp_path, spawn=False, notification_backend="desktop")
    called = []
    def failed(argv, **kwargs):
        called.append(argv)
        return subprocess.CompletedProcess(argv, 1, "", "unavailable")
    monkeypatch.setattr(control.subprocess, "run", failed)
    control.action(job, "notify")
    control.finish(job, "ready", time.monotonic())
    control.action(job, "notify")
    assert control.status(job)["notification"] == "desktop_failed_inbox_ready"
    assert len(called) == 1 and (job / "notification.json").is_file()


def test_inspection_of_lost_owner_does_not_resume_or_write(tmp_path):
    job = create(tmp_path, spawn=False)
    state = control.read(job / "state.json")
    state.update(phase="responding", started_at=time.time()-10, started_monotonic=time.monotonic()-10)
    control.write(job / "state.json", state)
    before = {p.name:p.read_bytes() for p in job.iterdir()}
    view = control.status(job)
    assert view["phase"] == "unresolved" and view["options"] == []
    assert {p.name:p.read_bytes() for p in job.iterdir()} == before


def test_changed_spec_is_rejected_before_dispatch(tmp_path):
    job = create(tmp_path, spawn=False)
    spec = control.read(job / "spec.json")
    spec["argv"] = argv("print('modified')")
    control.write(job / "spec.json", spec)
    control.worker(job)
    assert control.status(job)["phase"] == "unresolved" and not (job / "response.json").exists()


@pytest.mark.parametrize("field,value", [("warning_seconds",0), ("warning_seconds",float('nan')),
                         ("timeout_seconds",True), ("warning_seconds",5)])
def test_invalid_limits_do_not_start_jobs(tmp_path, field, value):
    with pytest.raises(ValueError):
        create(tmp_path, **{field:value})
    assert not (tmp_path / "jobs").exists()


def test_console_warns_once_and_noninteractive_wait_does_not_restart(tmp_path, monkeypatch, capsys):
    job = create(tmp_path,"import time; time.sleep(.4); print('ok')")
    monkeypatch.setattr(sys.stdin,"isatty",lambda:False)
    result = control.console(job)
    output = capsys.readouterr().out
    assert output.count("taking longer than expected") == 1
    assert result["phase"] == "ready"


def test_cancel_before_validator_launch_preserves_response_effects(tmp_path, monkeypatch):
    job = create(tmp_path, validator=argv("print('check')"), spawn=False)
    real_invoke = control.invoke
    calls = []
    def cancel_validator(command, prompt, **kwargs):
        calls.append(command)
        if len(calls) == 2:
            kwargs["cancel"].set()
        return real_invoke(command, prompt, **kwargs)
    monkeypatch.setattr(control, "invoke", cancel_validator)
    control.worker(job)
    assert control.status(job)["phase"] == "cancelled_effects_unknown"
    assert control.read(job / "response.json")["stdout"] == "response\n"
    assert control.read(job / "validation.json")["failure"] == "cancelled_before_start"


@pytest.fixture
def terminal_input(monkeypatch):
    incoming, outgoing = os.pipe()
    with os.fdopen(incoming) as reader, os.fdopen(outgoing, "w") as writer:
        monkeypatch.setattr(reader, "isatty", lambda: True)
        monkeypatch.setattr(sys, "stdin", reader)
        yield writer


@pytest.mark.parametrize("choice,phase", [("1", "ready"), ("2", "responding"), ("3", "cancelled_effects_unknown")])
def test_console_choices_control_same_attempt(tmp_path, terminal_input, capsys, choice, phase):
    job = create(tmp_path, "import time; time.sleep(.8); print('ok')")
    terminal_input.write(choice + "\n")
    terminal_input.flush()
    result = control.console(job)
    assert result["phase"] == phase and result["id"] == job.name
    output = capsys.readouterr().out
    assert output.count("taking longer than expected") == 1
    assert "Finish in background — save notice" in output
    assert "Notify me when finished" not in output
    if choice == "2":
        result = wait_for(job, lambda v: v["notification"] == "inbox_ready")
        assert result["phase"] == "ready"


def test_terminal_completion_does_not_wait_for_a_user_choice(tmp_path, terminal_input, capsys):
    job = create(tmp_path, "import time; time.sleep(.45); print('ok')")
    result = control.console(job)
    assert result["phase"] == "ready"
    assert "Choice [1]" in capsys.readouterr().out


def test_ctrl_c_at_choice_detaches_without_cancelling(tmp_path, terminal_input, monkeypatch, capsys):
    job = create(tmp_path, "import time; time.sleep(.5); print('ok')")
    def interrupted(job):
        raise KeyboardInterrupt
    monkeypatch.setattr(control, "read_choice", interrupted)
    result = control.console(job)
    assert not result["cancel_requested"] and result["phase"] == "responding"
    assert "Detached" in capsys.readouterr().out
    assert complete(job)["phase"] == "ready"
