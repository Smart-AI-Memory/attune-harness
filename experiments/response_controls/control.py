"""Isolated POSIX console response controls; no implicit model calls or retries."""

import argparse
from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path
import select
import subprocess
import sys
from threading import Event, Thread
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from attune_harness.process import invoke

TERMINAL = frozenset({"ready", "passed", "rejected", "failed", "cancelled_before_start",
                      "cancelled_effects_unknown", "timed_out_effects_unknown", "unresolved"})
PHASE_TEXT = {
    "queued": "The owner is starting; validation has not started.",
    "responding": "Still waiting for a response; validation has not started.",
    "validating": "The response arrived; the configured validation is running.",
    "ready": "Response received. No validator was configured; correctness is unknown.",
    "passed": "The configured validation passed. This does not establish broader correctness.",
    "rejected": "The response failed the configured validation.",
    "failed": "The response command failed. See retained diagnostics.",
    "cancelled_before_start": "Cancelled before the response command started.",
    "cancelled_effects_unknown": "Local execution stopped after cancellation. External effects and charges may remain.",
    "timed_out_effects_unknown": "The time budget expired. External effects and charges may remain.",
    "unresolved": "The owner or cleanup did not finish reliably. Inspect before another attempt.",
}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    path = Path(path)
    temporary = path.with_name("." + path.name + "." + uuid4().hex)
    payload = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()
    try:
        with temporary.open("xb") as stream:
            os.chmod(temporary, 0o600)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def lock(directory, name="control", blocking=True):
    if os.name != "posix":
        raise ValueError("This console prototype requires POSIX ownership locks")
    import fcntl
    fd = os.open(Path(directory) / ("." + name + ".lock"), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        yield
    finally:
        os.close(fd)


def directory(path):
    path = Path(path).absolute()
    if path.is_symlink() or not path.is_dir():
        raise ValueError("Expected an existing job directory, not a symlink")
    for name in ("spec.json", "state.json", "control.json"):
        if (path / name).is_symlink():
            raise ValueError("Job records cannot be symlinks")
    return path


def valid_argv(value):
    if (not isinstance(value, list) or not value or len(value) > 64
            or not all(isinstance(s, str) and "\x00" not in s for s in value)
            or not value[0] or not Path(value[0]).is_absolute()):
        raise ValueError("Use an absolute executable and a bounded list of string arguments")
    return value


def positive(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError(name + " must be positive and finite")


def desktop_supported():
    return sys.platform == "darwin" and Path("/usr/bin/osascript").is_file()


def create(parent, *, argv, label, cwd, warning_seconds, timeout_seconds,
           validator=None, prompt="", notification_backend="none", spawn=True):
    """An explicit start creates one owned attempt; actions never call this."""
    valid_argv(argv)
    if validator is not None:
        valid_argv(validator)
    positive(warning_seconds, "Warning interval")
    positive(timeout_seconds, "Time budget")
    if warning_seconds >= timeout_seconds:
        raise ValueError("Warning interval must precede the hard deadline")
    if not isinstance(label, str) or not label.strip() or len(label) > 160 or not label.isprintable():
        raise ValueError("Use a short printable task label")
    if not isinstance(prompt, str) or len(prompt.encode()) > 1_048_576:
        raise ValueError("Prompt must be bounded text")
    if notification_backend not in ("none", "inbox", "desktop"):
        raise ValueError("Unsupported notification capability")
    if notification_backend == "desktop" and not desktop_supported():
        raise ValueError("Desktop notification is unavailable; select inbox or none")
    cwd = Path(cwd).resolve(strict=True)
    if not cwd.is_dir():
        raise ValueError("Working directory must be a directory")
    parent = Path(parent).absolute()
    if parent.is_symlink():
        raise ValueError("Job parent cannot be a symlink")
    parent.mkdir(parents=True, exist_ok=True)
    job = parent / uuid4().hex
    job.mkdir(mode=0o700)
    spec = dict(version=1, id=job.name, label=label, argv=argv, validator=validator,
                cwd=str(cwd), prompt=prompt, warning_seconds=warning_seconds,
                timeout_seconds=timeout_seconds, notification_backend=notification_backend,
                runner_sha256=hashlib.sha256((ROOT / "src/attune_harness/process.py").read_bytes()).hexdigest())
    write(job / "spec.json", spec)
    write(job / "state.json", dict(version=1, id=job.name, phase="queued", submitted_at=time.time(),
          started_at=None, started_monotonic=None, finished_at=None, elapsed_seconds=0, correctness="unknown",
          notification="not_requested", response_dispatched=False,
          validation_dispatched=False, cost="unavailable", label=label,
          warning_seconds=warning_seconds, timeout_seconds=timeout_seconds,
          notification_backend=notification_backend,
          spec_sha256=hashlib.sha256((job / "spec.json").read_bytes()).hexdigest()))
    write(job / "control.json", dict(cancel_requested=False, notify_requested=False))
    for name in (".owner.lock", ".control.lock"):
        with (job / name).open("xb"):
            pass
    if spawn:
        try:
            with (job / "owner.log").open("xb") as log:
                subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "_worker", str(job)],
                                 stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                 start_new_session=True, close_fds=True)
        except OSError as error:
            finish(job, "failed", None, error=str(error))
    return job


def owner_active(job):
    import fcntl
    fd = os.open(Path(job) / ".owner.lock", os.O_RDONLY | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        return False
    except BlockingIOError:
        return True
    finally:
        os.close(fd)


def status(path):
    """Read current state without resuming, charging, or altering the attempt."""
    job = directory(path)
    state, control = read(job / "state.json"), read(job / "control.json")
    phase = state["phase"]
    elapsed = state["elapsed_seconds"]
    if phase not in TERMINAL and state["started_at"] is not None:
        elapsed = max(0, time.monotonic() - state["started_monotonic"])
    orphan = phase not in TERMINAL and not owner_active(job) and (
        state["started_at"] is not None or time.time() - state["submitted_at"] > 2)
    visible_phase = "unresolved" if orphan else phase
    warning = not orphan and phase not in TERMINAL and elapsed >= state["warning_seconds"]
    options = []
    if visible_phase not in TERMINAL:
        options = [{"action": "wait", "label": "Keep waiting"}]
        if state["notification_backend"] != "none":
            options.append({"action": "notify", "label": "Notify me when finished" if state["notification_backend"] == "desktop" else "Finish in background — save notice",
                            "delivery": state["notification_backend"]})
        options.append({"action": "cancel", "label": "Cancel"})
    return {**state, "phase": visible_phase, "persisted_phase": phase,
            "elapsed_seconds": elapsed, "warning": warning,
            "message": ("Cancellation requested; waiting for the owner to stop." if control["cancel_requested"] and visible_phase not in TERMINAL else PHASE_TEXT[visible_phase]),
            "options": options, "cancel_requested": control["cancel_requested"],
            "soft_limit_exceeded": elapsed >= state["warning_seconds"],
            "responsiveness": "deadline_exceeded" if elapsed >= state["timeout_seconds"] else "within_budget" if phase in TERMINAL else "pending",
            "job_directory": str(job)}


def action(path, choice):
    job = directory(path)
    if choice not in ("wait", "notify", "cancel"):
        raise ValueError("Choose wait, notify or cancel")
    with lock(job):
        state, control, spec = read(job / "state.json"), read(job / "control.json"), read(job / "spec.json")
        if choice == "notify":
            if spec["notification_backend"] == "none":
                raise ValueError("This host has no notification capability")
            control["notify_requested"] = True
            write(job / "control.json", control)
        elif choice == "cancel" and state["phase"] not in TERMINAL:
            control["cancel_requested"] = True
            write(job / "control.json", control)
    if choice == "notify":
        notify(job)
    return status(job)


def stage(job, phase):
    with lock(job):
        control, state = read(job / "control.json"), read(job / "state.json")
        if control["cancel_requested"]:
            return False
        state["phase"] = phase
        state["response_dispatched" if phase == "responding" else "validation_dispatched"] = True
        write(job / "state.json", state)
        return True


def finish(job, phase, started, **details):
    with lock(job):
        state, control = read(job / "state.json"), read(job / "control.json")
        if state["phase"] in TERMINAL:
            return
        if control["cancel_requested"] and phase in ("ready", "passed", "rejected"):
            phase = "cancelled_effects_unknown" if state["response_dispatched"] else "cancelled_before_start"
        state.update(details, phase=phase, finished_at=time.time(),
                     elapsed_seconds=max(0, time.monotonic() - started) if started is not None else 0,
                     correctness="passed_configured_checks" if phase == "passed" else "failed_configured_checks" if phase == "rejected" else "unknown")
        write(job / "state.json", state)
    notify(job)


def notify(job):
    """Persist one notice; desktop requests are at most once, never auto-retried."""
    with lock(job):
        state, control, spec = read(job / "state.json"), read(job / "control.json"), read(job / "spec.json")
        if not control["notify_requested"] or state["phase"] not in TERMINAL or state["notification"] != "not_requested":
            return
        notice = {"id": state["id"], "label": spec["label"], "phase": state["phase"],
                  "message": PHASE_TEXT[state["phase"]], "created_at": time.time()}
        write(job / "notification.json", notice)
        state["notification"] = "inbox_ready" if spec["notification_backend"] == "inbox" else "desktop_request_pending"
        write(job / "state.json", state)
    if spec["notification_backend"] == "desktop":
        # User strings are arguments to a fixed script, never AppleScript source.
        script = 'on run argv\ndisplay notification (item 1 of argv) with title "Attune Harness"\nend run'
        try:
            result = subprocess.run(["/usr/bin/osascript", "-e", script, spec["label"] + ": " + notice["message"]],
                                    capture_output=True, text=True, timeout=10, check=False)
            delivery = "desktop_request_sent" if result.returncode == 0 else "desktop_failed_inbox_ready"
        except (OSError, subprocess.TimeoutExpired):
            delivery = "desktop_failed_inbox_ready"
        with lock(job):
            state = read(job / "state.json")
            state["notification"] = delivery
            write(job / "state.json", state)


def failure_phase(result):
    if result.failure == "cancelled_before_start":
        return "cancelled_before_start"
    if result.failure == "cancelled_effects_unknown":
        return "cancelled_effects_unknown"
    if result.failure == "timeout_effects_unknown":
        return "timed_out_effects_unknown"
    if result.failure == "interrupted_effects_unknown":
        return "unresolved"
    return "failed"


def worker(path):
    job = directory(path)
    with lock(job, "owner", blocking=False):
        # A crashed invocation is unresolved, never automatically relaunched.
        try:
            with (job / ".claimed").open("xb"):
                pass
        except FileExistsError:
            raise ValueError("This attempt was already claimed; inspection cannot retry it")
        spec = read(job / "spec.json")
        if hashlib.sha256((job / "spec.json").read_bytes()).hexdigest() != read(job / "state.json")["spec_sha256"]:
            finish(job, "unresolved", None, error="Accepted command specification changed")
            return
        current = hashlib.sha256((ROOT / "src/attune_harness/process.py").read_bytes()).hexdigest()
        if current != spec["runner_sha256"]:
            finish(job, "unresolved", None, error="Bound runner changed before execution")
            return
        started = time.monotonic()
        with lock(job):
            state = read(job / "state.json")
            state["started_at"] = time.time()
            state["started_monotonic"] = started
            write(job / "state.json", state)
        cancel, done = Event(), Event()

        def observe_cancel():
            while not done.is_set():
                try:
                    if read(job / "control.json")["cancel_requested"]:
                        cancel.set()
                        return
                except (OSError, ValueError):
                    cancel.set()
                    return
                done.wait(.1)

        observer = Thread(target=observe_cancel, name="response-cancellation", daemon=True)
        observer.start()

        def run(argv, prompt, name):
            remaining = spec["timeout_seconds"] - (time.monotonic() - started)
            if remaining <= 0:
                finish(job, "timed_out_effects_unknown", started)
                return None
            result = invoke(tuple(argv), prompt, cwd=Path(spec["cwd"]), timeout=remaining,
                            max_output_bytes=1_048_576, cancel=cancel, capture_interrupt=True)
            write(job / (name + ".json"), asdict(result))
            return result

        try:
            if not stage(job, "responding"):
                finish(job, "cancelled_before_start", started)
                return
            response = run(spec["argv"], spec["prompt"], "response")
            if response is None:
                return
            if response.failure or response.returncode != 0:
                finish(job, failure_phase(response), started)
                return
            if spec["validator"] is None:
                finish(job, "ready", started)
                return
            if not stage(job, "validating"):
                finish(job, "cancelled_effects_unknown", started)
                return
            checked = run(spec["validator"], response.stdout, "validation")
            if checked is not None:
                phase = "passed" if checked.failure is None and checked.returncode == 0 else "rejected" if checked.failure == "nonzero_exit" else failure_phase(checked)
                # A validator cancelled before its launch does not undo the response.
                if phase == "cancelled_before_start":
                    phase = "cancelled_effects_unknown"
                finish(job, phase, started)
        except BaseException as error:
            finish(job, "unresolved", started, error=type(error).__name__ + ": " + str(error))
        finally:
            done.set()
            observer.join(timeout=1)


def read_choice(job):
    """Keep observing completion while the user considers the terminal choices."""
    print("Choice [1]: ", end="", flush=True)
    while True:
        if status(job)["phase"] in TERMINAL:
            print()
            return None
        if select.select([sys.stdin], [], [], .2)[0]:
            return sys.stdin.readline().strip() or "1"


def detach(job):
    print("Detached from the console; the same attempt may continue. Inspect or cancel: " + str(job))
    return status(job)


def console(job):
    warned = False
    while True:
        view = status(job)
        if view["phase"] in TERMINAL:
            print(json.dumps(view, indent=2))
            return view
        if view["warning"] and not warned:
            warned = True
            print(f"\n{view['label']} is taking longer than expected ({view['elapsed_seconds']:.1f}s).")
            print(view["message"])
            print("Work already processed may still incur cost. Current cost is unavailable.")
            if not sys.stdin.isatty():
                print("Noninteractive session: continuing this attempt. Use status/notify/cancel from another terminal.")
            else:
                choices = {str(i): option for i, option in enumerate(view["options"], 1)}
                for key, option in choices.items():
                    print(f"{key}. {option['label']}" + (f" ({option['delivery']})" if "delivery" in option else ""))
                try:
                    picked = read_choice(job)
                except KeyboardInterrupt:
                    return detach(job)
                if picked is None:
                    continue
                if picked not in choices:
                    print("Unrecognized choice; keeping the same attempt running.")
                else:
                    choice = choices[picked]["action"]
                    current = action(job, choice)
                    if choice == "notify":
                        print("Continuing independently. Completion notice: " + str(Path(job) / "notification.json"))
                        return current
        try:
            time.sleep(.2)
        except KeyboardInterrupt:
            return detach(job)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start")
    start.add_argument("--jobs", type=Path, required=True)
    start.add_argument("--cwd", type=Path, default=Path.cwd())
    start.add_argument("--label", required=True)
    start.add_argument("--warn-after", type=float, required=True)
    start.add_argument("--timeout", type=float, required=True)
    start.add_argument("--validator-json", help="Explicit validator argv as JSON; receives response on stdin")
    start.add_argument("--notify-backend", choices=("none", "inbox", "desktop"), default="none")
    start.add_argument("--attach", action="store_true")
    start.add_argument("argv", nargs=argparse.REMAINDER)
    for command in ("status", "wait", "notify", "cancel", "_worker"):
        commands.add_parser(command).add_argument("job", type=Path)
    args = parser.parse_args()
    if args.command == "start":
        argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
        job = create(args.jobs, argv=argv, label=args.label, cwd=args.cwd,
                     warning_seconds=args.warn_after, timeout_seconds=args.timeout,
                     validator=json.loads(args.validator_json) if args.validator_json else None,
                     notification_backend=args.notify_backend)
        print(str(job), flush=True)
        if args.attach:
            console(job)
    elif args.command == "_worker":
        worker(args.job)
    elif args.command == "wait":
        console(args.job)
    else:
        print(json.dumps(status(args.job) if args.command == "status" else action(args.job, args.command), indent=2))


if __name__ == "__main__":
    main()
