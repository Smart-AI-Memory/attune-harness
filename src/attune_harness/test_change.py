"""Testing policy under the shared task envelope, store and recovery cursor."""

import copy
import math
import os
from pathlib import Path
import re
import time
from uuid import UUID, uuid4

from .features import require_feature
from .recovery import RecoveryCursor, ReviewPaused, UnresolvedOperation, validate_events
from .review_contract import FORMS_VERSION, bounded_text, digest, fields
from .review_store import RunStore
from .test_execution import WORKER, run_tests, validate_artifacts
from .test_scope import capture, file_hash, fresh, select

PROFILE = "pytest-change-v1"
ALLOWED_ARGS = (
    "-q",
    "-v",
    "-s",
    "-x",
    "--collect-only",
    "--disable-warnings",
    "--tb=short",
    "--tb=long",
    "--tb=no",
    "-oaddopts=",
)


def create_test_task(
    project: Path | None,
    directory: Path,
    *,
    scope: list[str] | None = None,
    interpreter: str,
    tests: list[str] | None = None,
    test_root: str = "tests",
    goal: str = "Test this change",
    timeout: float = 60,
    max_output_bytes: int = 1024 * 1024,
    pytest_args: list[str] | None = None,
    plugins: list[str] | None = None,
    source_task: Path | None = None,
) -> dict:
    """Capture a coherent plan without executing tests or requesting a model."""
    started = time.monotonic()
    from .task_contract import safe_storage
    from .task_handoff import check_handoff, completed_source

    handoff = None
    if source_task is not None:
        if project is not None or scope is not None:
            raise ValueError(
                "Repair/build handoff derives project and scope; overrides are not allowed"
            )
        project, scope, handoff = completed_source(source_task)
    if project is None or not scope:
        raise ValueError("Provide project and change scope, or a completed repair task")

    if os.name != "posix":
        raise ValueError("Testing currently qualifies the POSIX execution profile")
    project = project.resolve(strict=True)
    directory = safe_storage(directory)
    if directory.resolve().is_relative_to(project) or directory.is_symlink():
        raise ValueError("Testing task directory must be outside the project")
    executable = Path(interpreter).absolute()
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise ValueError("Provide an existing executable Python interpreter")
    if (
        isinstance(timeout, bool)
        or not math.isfinite(timeout)
        or not 0 < timeout <= 3600
    ):
        raise ValueError("Test timeout must be in (0, 3600] seconds")
    if (
        type(max_output_bytes) is not int
        or not 1024 <= max_output_bytes <= 16 * 1024 * 1024
    ):
        raise ValueError("Test output limit must be 1 KiB to 16 MiB")
    arguments = list(pytest_args or ["-q"])
    if any(arg not in ALLOWED_ARGS for arg in arguments):
        raise ValueError(
            "Unsupported pytest argument; use the explicit target/plugin options"
        )
    plugins = list(plugins or [])
    if any(not re.fullmatch(r"[A-Za-z_][\w.]*(?:\.[\w]+)*", p) for p in plugins):
        raise ValueError("Invalid pytest plugin module")
    bounded_text(goal, "goal")
    snapshot = capture(project)
    selection = select(project, snapshot, scope, tests, test_root)
    if not fresh(snapshot):
        raise ValueError("Repository changed while capturing test intake")
    selection["intake_elapsed_seconds"] = time.monotonic() - started
    request = {
        "schema_version": 1,
        "task_id": str(uuid4()),
        "revision": 1,
        "project_root": str(project),
        "goal": goal,
        "snapshot": snapshot,
        "selection": selection,
        "budgets": {"max_operations": 1},
        "runner": {
            "interpreter": str(executable),
            "interpreter_sha256": file_hash(executable.resolve()),
            "worker_sha256": file_hash(WORKER),
            "timeout": timeout,
            "max_output_bytes": max_output_bytes,
            "pytest_args": arguments,
            "plugins": plugins,
        },
    }
    if handoff is not None:
        request["source_task"] = handoff
        check_handoff(request)
    # Validate the optional grammar dependency before creating a durable task.
    require_feature("attune-forms", "attune_forms", FORMS_VERSION, "review")
    directory.parent.mkdir(parents=True, exist_ok=True)
    store = RunStore(directory)
    record = {
        "schema_version": 1,
        "operation": "task",
        "task_profile": PROFILE,
        "status": "draft",
        "request": request,
        "record_path": str(store.path),
        "acceptance": None,
        "bindings": {},
        "events": [],
        "history": [],
        "recovery": {"profile": {"kind": "testing", "version": 1}},
    }
    with store.lease():
        store.save(record)
    return record


def validate_test_task(record: dict, directory: Path) -> dict:
    """Validate testing records separately from legacy assessment/repair formats."""
    fields(
        record,
        (
            "schema_version",
            "operation",
            "task_profile",
            "status",
            "request",
            "record_path",
            "acceptance",
            "bindings",
            "events",
            "history",
            "recovery",
            "checkpoint_digest",
            *(["execution"] if "execution" in record else []),
        ),
    )
    request = record["request"]
    if (
        record["operation"] != "task"
        or record["task_profile"] != PROFILE
        or record["recovery"] != {"profile": {"kind": "testing", "version": 1}}
        or record["record_path"] != str(directory.absolute() / "record.json")
        or record["events"]
        or record["history"]
    ):
        raise ValueError("Invalid testing task identity/profile")
    if record["status"] not in (
        "draft",
        "accepted",
        "running",
        "completed",
        "paused",
        "unresolved",
        "cancelled",
    ):
        raise ValueError("Invalid testing task state")
    fields(
        request,
        (
            "schema_version",
            "task_id",
            "revision",
            "project_root",
            "goal",
            "snapshot",
            "selection",
            "budgets",
            "runner",
            *(["source_task"] if "source_task" in request else []),
        ),
    )
    if "source_task" in request:
        from .task_handoff import validate_handoff

        validate_handoff(request["source_task"])
    if str(UUID(request["task_id"])) != request["task_id"] or request["revision"] != 1:
        raise ValueError("Invalid testing request identity")
    if (
        directory.resolve().is_relative_to(Path(request["project_root"]).resolve())
        or request["snapshot"]["root"] != request["project_root"]
        or request["budgets"] != {"max_operations": 1}
    ):
        raise ValueError("Invalid testing scope/storage")
    if record["status"] == "draft":
        if (
            record["acceptance"] is not None
            or record["bindings"]
            or "execution" in record
        ):
            raise ValueError("Draft testing intake cannot carry execution authority")
    elif record["acceptance"] != {
        "accepted": True,
        "request_digest": digest(request),
    } or record["bindings"] != {"testing": digest(request)}:
        raise ValueError("Testing acceptance does not bind the request")
    if "execution" in record:
        run = record["execution"]
        if (
            run["run_id"] != request["task_id"]
            or run["operation"] != "test"
            or run["request_digest"] != digest(request)
            or run["status"] != record["status"]
        ):
            raise ValueError("Execution does not match testing intake")
        validate_events(run, kinds=("pytest_execution",))
        if len(run["events"]) > 1:
            raise ValueError("Testing request permits only one dispatch")
        for event in run["events"]:
            if (
                event["operation_key"] != "pytest:1"
                or event["effect_class"] != "unknown"
            ):
                raise ValueError("Invalid testing operation authority")
            if event["state"] == "completed" and event["result"][
                "request_digest"
            ] != digest(request):
                raise ValueError("Testing result belongs to another request")
    elif record["status"] not in ("draft", "accepted"):
        raise ValueError("Testing state requires an execution record")
    return record


def check_test_fresh(record: dict) -> None:
    """Reject changed repository, interpreter or observer before accepting/replaying."""
    request = record["request"]
    from .task_handoff import check_handoff

    check_handoff(request)
    if not fresh(request["snapshot"]):
        raise ValueError(
            "Stale source/test/config snapshot; create and accept a new test task"
        )
    if (
        file_hash(WORKER) != request["runner"]["worker_sha256"]
        or file_hash(Path(request["runner"]["interpreter"]).resolve())
        != request["runner"]["interpreter_sha256"]
    ):
        raise ValueError("Stale interpreter/observer identity")


def accept_test_task(directory: Path, checkpoint: str) -> dict:
    """Accept exactly the saved preview; no tests are executed here."""
    from .task_contract import read_task, safe_storage

    directory = safe_storage(directory)
    store = RunStore(directory, existing=True)
    with store.lease():
        record = validate_test_task(read_task(directory), directory)
        if record["status"] != "draft" or checkpoint != record["checkpoint_digest"]:
            raise ValueError("Stale or already accepted test preview")
        check_test_fresh(record)
        record["acceptance"] = {
            "accepted": True,
            "request_digest": digest(record["request"]),
        }
        record["bindings"] = {"testing": digest(record["request"])}
        record["status"] = "accepted"
        store.save(record)
    return record


def execute_test_task(
    directory: Path,
    *,
    checkpoint: str | None = None,
    max_operations: int | None = None,
    cancel=None,
) -> dict:
    """Dispatch once or reuse completed evidence; uncertain effects stay unresolved."""
    from .task_policies import TaskExecutionStore
    from .task_contract import read_task, safe_storage

    directory = safe_storage(directory)
    store = RunStore(directory, existing=True)
    with store.lease():
        task = validate_test_task(read_task(directory), directory)
        if checkpoint is not None and checkpoint != task["checkpoint_digest"]:
            raise ValueError("Stale testing checkpoint")
        if task["status"] == "draft":
            raise ValueError("Accept the test preview before execution")
        if task["status"] == "cancelled":
            return present_test_task(task)
        check_test_fresh(task)
        run = task.setdefault(
            "execution",
            {
                "schema_version": 1,
                "operation": "test",
                "run_id": task["request"]["task_id"],
                "request_digest": digest(task["request"]),
                "status": "running",
                "events": [],
            },
        )
        adapter = TaskExecutionStore(store, task)
        cursor = RecoveryCursor(run, adapter, max_operations)
        if run["status"] == "completed":
            validate_artifacts(directory, run["result"])
            return present_test_task(task)
        run["status"] = "running"
        adapter.save(run)
        try:
            result = cursor.perform(
                "pytest:1",
                "pytest_execution",
                lambda: run_tests(task["request"], directory, cancel=cancel),
                effect_class="unknown",
            )
            validate_artifacts(directory, result)
            try:
                check_test_fresh(task)
            except (OSError, ValueError) as exc:
                result = {**result, "outcome": "blocked", "detail": str(exc)}
        except ReviewPaused:
            run["status"] = "paused"
        except (UnresolvedOperation, OSError, ValueError) as exc:
            from .review_store import PersistenceError

            if isinstance(exc, PersistenceError):
                raise
            run.update(status="unresolved", error=str(exc))
        else:
            run.update(status="completed", result=result)
            run.pop("error", None)
        adapter.save(run)
    return present_test_task(task)


def control_test_task(
    directory: Path, action: str, *, checkpoint=None, **kwargs
) -> dict:
    """Allow cancellation; never certify test effects as safe read-only retries."""
    if action != "cancel":
        raise ValueError(
            "Dispatched tests may have effects. Inspect/cancel, then accept a new test task; no automatic retry or transfer."
        )
    from .task_contract import read_task, safe_storage

    directory = safe_storage(directory)
    store = RunStore(directory, existing=True)
    with store.lease():
        task = validate_test_task(read_task(directory), directory)
        if task["status"] == "draft":
            raise ValueError("Draft testing intake has no execution to cancel")
        if checkpoint is not None and checkpoint != task["checkpoint_digest"]:
            raise ValueError("Stale testing checkpoint")
        if task["status"] not in ("completed", "cancelled"):
            bounded_text(kwargs.get("reason"), "cancellation reason")
            if "execution" not in task:
                task["execution"] = {
                    "schema_version": 1,
                    "operation": "test",
                    "run_id": task["request"]["task_id"],
                    "request_digest": digest(task["request"]),
                    "events": [],
                    "status": "cancelled",
                }
            task["execution"].update(
                status="cancelled", cancellation_reason=kwargs["reason"]
            )
            task["status"] = "cancelled"
            store.save(task)
    return present_test_task(task)


def present_test_task(task: dict) -> dict:
    """Project current evidence through the grammar; preserve historical receipts."""
    result = copy.deepcopy(task)
    request = task["request"]
    current = task.get("execution", {}).get("result")
    current = (
        copy.deepcopy(current)
        if current
        else {"outcome": task["status"], "detail": "No completed execution receipt."}
    )
    try:
        check_test_fresh(task)
        if "artifacts" in current:
            validate_artifacts(Path(task["record_path"]).parent, current)
    except (OSError, ValueError) as exc:
        current = {
            "outcome": "blocked",
            "detail": str(exc),
            "historical_result_retained": True,
        }
    if task["status"] in ("running", "unresolved"):
        current = {
            "outcome": "interrupted",
            "detail": "Execution may still be running or effects are unresolved. Inspect/cancel before a newly accepted task; resume will not repeat it.",
        }
    if task["status"] == "cancelled" and any(
        event["phase"] == "dispatching"
        for event in task.get("execution", {}).get("events", [])
    ):
        current = {
            "outcome": "interrupted",
            "detail": "Task cancelled; dispatched test effects remain unresolved. Cancellation did not roll them back. Inspect before accepting a new task.",
        }
    next_action = {
        "failed": "Investigate the failure against the intended behavior; do not weaken assertions.",
        "no_tests": "Analyze the test gap, then propose tests with an explicit write boundary.",
        "blocked": "Inspect missing or stale evidence and the environment before a new accepted run.",
        "interrupted": "Inspect the stopped or uncertain attempt before creating a new test task.",
    }.get(current["outcome"])

    def listed(paths):
        value = ", ".join(paths[:5])
        if len(paths) > 5:
            value += f"; {len(paths) - 5} more (complete list in saved record)"
        return value

    items = [
        {"label": "Change scope", "value": listed(request["selection"]["scope"])},
        {
            "label": "Changed files",
            "value": listed(request["selection"]["changed_files"]),
        },
        {
            "label": "Selected tests",
            "value": str(len(request["selection"]["selected"])),
        },
        {
            "label": "Test files",
            "value": listed(request["selection"]["selected"]) or "None",
        },
        {"label": "Selection", "value": request["selection"]["reason"]},
        {
            "label": "Excluded tests",
            "value": listed(request["selection"]["excluded"])
            or "None in the captured test directory",
        },
        {
            "label": "Missing evidence",
            "value": " ".join(request["selection"]["missing_evidence"]),
        },
        {"label": "Command interpreter", "value": request["runner"]["interpreter"]},
        {
            "label": "Output",
            "value": ", ".join(a["path"] for a in current.get("artifacts", []))
            or "Not available",
        },
    ]
    observed = current.get("pytest")
    if observed:
        items.append(
            {
                "label": "Observed tests",
                "value": f"{len(observed['collected'])} collected; {observed['passed']} passed; {observed['failed']} failed; {observed['skipped']} skipped; {observed['deselected']} deselected",
            }
        )
    items.append({"label": "Saved record", "value": task["record_path"]})
    if next_action:
        items.append({"label": "Suggested next action", "value": next_action})
    if "source_task" in request:
        source = request["source_task"]
        items.append(
            {
                "label": "Producing repair",
                "value": source["task_id"] + " — " + source["record_path"],
            }
        )
    library = require_feature("attune-forms", "attune_forms", FORMS_VERSION, "review")
    definition = {
        "id": "preview" if task["status"] == "draft" else "receipt",
        "title": request["goal"],
        "summary": current["outcome"] + ": " + current["detail"],
        "sections": [
            {
                "heading": "Test scope and evidence",
                "blocks": [{"kind": "evidence", "items": items}],
            }
        ],
    }
    view = library.workspace_from_dict(definition)
    result["presentation"] = {
        "definition": definition,
        "markdown": library.workspace_to_markdown(view),
        "current_result": current,
        "next_action": next_action,
        "accept_checkpoint": (
            task["checkpoint_digest"] if task["status"] == "draft" else None
        ),
    }
    result["presentation"]["timings"] = {
        "intake_seconds": request["selection"]["intake_elapsed_seconds"],
        "execution_seconds": current.get("elapsed_seconds"),
        "model_calls": 0,
    }
    return result


def public_test_task(task: dict) -> dict:
    """Keep console output readable while linking the full authoritative record."""
    value = {
        key: copy.deepcopy(task[key])
        for key in (
            "schema_version",
            "operation",
            "task_profile",
            "status",
            "record_path",
            "checkpoint_digest",
            "presentation",
        )
    }
    observed = value["presentation"]["current_result"].get("pytest")
    if observed:
        observed["collected_count"] = len(observed.pop("collected"))
    return value


def exit_code(task: dict) -> int:
    """Expose test outcome separately from successful task persistence."""
    outcome = task["presentation"]["current_result"]["outcome"]
    return (
        0
        if outcome == "passed"
        else (
            1
            if outcome
            in ("failed", "no_tests", "draft", "accepted", "paused", "cancelled")
            else 2
        )
    )
