"""Bounded local subprocesses with POSIX groups or Windows Job Object ownership."""

import math
from contextlib import ExitStack
import os
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Event


@dataclass(frozen=True)
class ProcessResult:
    argv: tuple[str, ...]
    returncode: int | None
    stdout: str
    stderr: str
    failure: str | None = None


def _kill_group(process: subprocess.Popen) -> None:
    for attempt in range(2):
        try:
            os.killpg(process.pid, signal.SIGKILL)
            break
        except ProcessLookupError:
            break
        except PermissionError as error:
            if attempt:
                raise
            # A rapidly exiting child can briefly deny group signalling on
            # macOS. Reap within a bounded grace period, then still check the
            # group: parent exit alone does not establish descendant cleanup.
            try:
                process.wait(timeout=0.1)
            except subprocess.TimeoutExpired:
                raise error
    process.wait()


def invoke(
    argv: tuple[str, ...], prompt: str, *, cwd: Path,
    timeout: float = 60, max_output_bytes: int = 1_048_576,
    cancel: Event | None = None, environment: dict[str, str] | None = None,
    capture_interrupt: bool = False,
) -> ProcessResult:
    """Run without shell expansion; preserve bounded diagnostics on failure.

    A timeout/cancel/limit after launch has unknown external effects. Polling
    bounds captured output, not instantaneous file growth. Not a security sandbox.
    """
    if os.name not in ("posix", "nt"):
        raise NotImplementedError("native supervision requires POSIX or Windows")
    if environment is not None:
        if os.name != 'posix':
            raise NotImplementedError('Explicit probe environments currently require POSIX')
        if not isinstance(environment, dict) or any(not isinstance(k, str) or not isinstance(v, str)
                or not k or '=' in k or '\x00' in k or '\x00' in v for k,v in environment.items()):
            raise ValueError('Environment must contain valid string entries')
    # Empty arguments are useful CLI values (e.g. --tools ""), except argv[0].
    if not argv or not argv[0] or any(not isinstance(arg, str) for arg in argv):
        raise ValueError("argv must contain an executable and string arguments")
    if isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be positive and finite")
    if type(max_output_bytes) is not int or max_output_bytes < 1:
        raise ValueError("max_output_bytes must be a positive integer")
    if cancel is not None and cancel.is_set():
        return ProcessResult(argv, None, "", "", "cancelled_before_start")
    with ExitStack() as stack, tempfile.TemporaryFile() as source, tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        source.write(prompt.encode("utf-8"))
        source.seek(0)
        job = None
        try:
            if os.name == 'nt':
                from .windows import WindowsJob
                job = stack.enter_context(WindowsJob())
                process = job.launch(argv, stdin=source, stdout=out, stderr=err, cwd=cwd)
            else:
                process = subprocess.Popen(argv, stdin=source, stdout=out, stderr=err,
                                           cwd=cwd, start_new_session=True, env=environment)
        except FileNotFoundError as error:
            return ProcessResult(argv, None, "", str(error), "not_found")
        except OSError as error:
            return ProcessResult(argv, None, "", str(error), "launch_failed")
        failure = None
        deadline = time.monotonic() + timeout
        try:
            while process.poll() is None:
                if os.fstat(out.fileno()).st_size + os.fstat(err.fileno()).st_size > max_output_bytes:
                    failure = "output_limit"
                elif cancel is not None and cancel.is_set():
                    failure = "cancelled_effects_unknown"
                elif time.monotonic() >= deadline:
                    failure = "timeout_effects_unknown"
                if failure:
                    break
                time.sleep(0.01)
        except KeyboardInterrupt:
            if not capture_interrupt:
                raise
            failure = 'interrupted_effects_unknown'
        finally:
            # Also stop descendants left behind by an exited parent.
            if job is not None:
                job.stop(process)
            else:
                _kill_group(process)
        if job is not None:
            failure = failure or job.launch_failure()
        if os.fstat(out.fileno()).st_size + os.fstat(err.fileno()).st_size > max_output_bytes:
            failure = failure or "output_limit"
        out.seek(0)
        err.seek(0)
        stdout = out.read(max_output_bytes)
        stderr = err.read(max_output_bytes - len(stdout))
        try:
            stdout.decode("utf-8")
            stderr.decode("utf-8")
        except UnicodeDecodeError:
            failure = failure or "invalid_utf8"
        return ProcessResult(argv, process.returncode,
                             stdout.decode("utf-8", errors="replace"),
                             stderr.decode("utf-8", errors="replace"),
                             failure or ("nonzero_exit" if process.returncode else None))
