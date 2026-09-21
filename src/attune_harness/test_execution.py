"""Observed pytest outcomes using the existing supervised subprocess runner."""

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time

from . import process
from .review_contract import digest
from .test_scope import check_copy, copy_inputs, file_hash, fresh, module_name

WORKER = Path(__file__).with_name("_pytest_worker.py")


def artifact(directory: Path, name: str, data: bytes) -> dict:
    """Retain an immutable artifact before claiming completed execution."""
    path = directory / name
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        import os

        os.fsync(stream.fileno())
    return {
        "path": name,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def validate_artifacts(directory: Path, result: dict) -> None:
    """Prevent stale or missing output artifacts from satisfying a saved result."""
    for item in result["artifacts"]:
        if item["path"] not in ("stdout.txt", "stderr.txt", "pytest.json"):
            raise ValueError("Unsupported test artifact")
        path = directory / item["path"]
        if file_hash(path) != item["sha256"] or path.stat().st_size != item["bytes"]:
            raise ValueError("Test artifact changed since execution")


def classify(result: process.ProcessResult, observed: dict | None) -> tuple[str, str]:
    """Distinguish process completion, test execution and evidence failures."""
    if result.failure in (
        "timeout_effects_unknown",
        "cancelled_before_start",
        "cancelled_effects_unknown",
        "interrupted_effects_unknown",
    ):
        return "interrupted", result.failure
    if result.failure not in (None, "nonzero_exit"):
        return "blocked", result.failure or "process failure"
    if not observed:
        return "blocked", "Missing pytest observer evidence; inspect process output."
    if observed["collection_errors"] or observed["setup_errors"]:
        return (
            "blocked",
            "Collection, setup or teardown failed; inspect the environment and fixtures.",
        )
    if observed["exit_code"] != result.returncode or not observed["session_started"]:
        return "blocked", "Pytest evidence does not establish this process execution."
    if observed["collect_only"]:
        return "blocked", "Tests were collected only; no passing execution is claimed."
    if result.returncode == 2:
        return "interrupted", "Pytest execution was interrupted."
    if result.returncode not in (0, 1, 5):
        return "blocked", "Pytest could not execute the accepted check."
    if observed["failed"]:
        return (
            "failed",
            "Test assertions failed; investigate expected behavior before changing assertions.",
        )
    if result.returncode == 1:
        return (
            "blocked",
            "Pytest reported a failure without an observed failing test call.",
        )
    if result.returncode == 5 or observed["passed"] == 0 or not observed["collected"]:
        return (
            "no_tests",
            "No test call completed; collected or skipped tests are not passing execution.",
        )
    return (
        "passed",
        "Passed within the selected test scope; broader correctness is not established.",
    )


def observe(path: Path, request: dict, copied: Path) -> dict | None:
    """Validate the worker's structured report against host-owned execution inputs."""
    if not path.exists():
        return None
    if path.is_symlink() or path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("Invalid pytest evidence artifact")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        value["token"] != digest(request)
        or value["cwd"] != str(copied)
        or value["manifest"] != digest(request["snapshot"])
        or value["operation"] != request["task_id"] + ":pytest:1"
        or Path(value["interpreter"]).absolute()
        != Path(request["runner"]["interpreter"])
    ):
        raise ValueError("Foreign pytest evidence")
    if (
        type(value["exit_code"]) is not int
        or not isinstance(value["collected"], list)
        or any(not isinstance(node, str) for node in value["collected"])
        or not isinstance(value["module_origins"], dict)
    ):
        raise ValueError("Invalid pytest evidence structure")
    for name in (
        "calls",
        "passed",
        "failed",
        "skipped",
        "setup_errors",
        "collection_errors",
        "deselected",
    ):
        if type(value[name]) is not int or value[name] < 0:
            raise ValueError("Invalid pytest phase count")
    for name in ("collect_only", "session_started"):
        if type(value[name]) is not bool:
            raise ValueError("Invalid pytest mode")
    if value["calls"] < value["passed"] + value["failed"]:
        raise ValueError("Inconsistent test call evidence")
    if any(
        node.split("::")[0] not in request["selection"]["selected"]
        for node in value["collected"]
    ):
        raise ValueError("Pytest collected outside the selected test files")
    for source in request["selection"]["changed_files"]:
        if source.endswith(".py") and source.startswith("src/"):
            origin = value["module_origins"].get(module_name(source))
            if origin and origin != str(copied / source):
                raise ValueError(
                    f"Changed module loaded outside captured inputs: {source}"
                )
    return value


def run_tests(request: dict, directory: Path, *, cancel=None) -> dict:
    """Execute one accepted snapshot and retain its real process/pytest evidence."""
    started = time.monotonic()
    copied = directory / "inputs"
    copy_inputs(request["snapshot"], copied)
    check_copy(request["snapshot"], copied)
    if not fresh(request["snapshot"]):
        raise ValueError("Stale source before test dispatch")
    runner = request["runner"]
    worker_output = directory / "pytest.json"
    if worker_output.exists() or worker_output.is_symlink():
        raise ValueError("Pytest evidence destination already exists")
    # Avoid an empty file list accidentally invoking pytest's whole-project discovery.
    paths = request["selection"]["selected"]
    if not paths:
        paths = [".attune-empty-tests"]
        (copied / paths[0]).mkdir()
    argv = (
        runner["interpreter"],
        "-B",
        str(WORKER),
        str(copied),
        str(worker_output),
        digest(request),
        digest(request["snapshot"]),
        request["task_id"] + ":pytest:1",
        "--rootdir",
        str(copied),
        "-p",
        "no:cacheprovider",
        *sum((["-p", plugin] for plugin in runner["plugins"]), []),
        *runner["pytest_args"],
        *paths,
    )
    environment = {
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "ATTUNE_USAGE_PING": "0",
        "ATTUNE_VERSION_CHECK": "0",
    }
    result = process.invoke(
        argv,
        "",
        cwd=copied,
        timeout=runner["timeout"],
        max_output_bytes=runner["max_output_bytes"],
        environment=environment,
        cancel=cancel,
        capture_interrupt=True,
    )
    artifacts = [
        artifact(directory, "stdout.txt", result.stdout.encode("utf-8")),
        artifact(directory, "stderr.txt", result.stderr.encode("utf-8")),
    ]
    observed, evidence_error = None, None
    try:
        observed = observe(worker_output, request, copied)
        check_copy(request["snapshot"], copied)
        if not fresh(request["snapshot"]):
            raise ValueError("Original source/test/config changed during execution")
        if file_hash(WORKER) != runner["worker_sha256"]:
            raise ValueError("Pytest observer changed during execution")
        if (
            file_hash(Path(runner["interpreter"]).resolve())
            != runner["interpreter_sha256"]
        ):
            raise ValueError("Interpreter changed during execution")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        evidence_error = str(exc)
    if worker_output.exists() and not worker_output.is_symlink():
        artifacts.append(
            {
                "path": "pytest.json",
                "sha256": file_hash(worker_output),
                "bytes": worker_output.stat().st_size,
            }
        )
    outcome, detail = classify(result, observed)
    if evidence_error:
        outcome, detail = "blocked", evidence_error
    return {
        "outcome": outcome,
        "detail": detail,
        "request_digest": digest(request),
        "snapshot_digest": digest(request["snapshot"]),
        "process": {
            k: v for k, v in asdict(result).items() if k not in ("stdout", "stderr")
        },
        "cwd": str(copied),
        "environment": environment,
        "pytest": (
            {k: v for k, v in observed.items() if k != "module_origins"}
            if observed
            else None
        ),
        "artifacts": artifacts,
        "output_complete": result.failure not in ("output_limit", "invalid_utf8"),
        "elapsed_seconds": time.monotonic() - started,
        "model_calls": 0,
    }
