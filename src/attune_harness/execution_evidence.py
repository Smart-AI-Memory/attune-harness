"""Read-only pointers into retained executor inputs, results and host origins."""

import copy
from pathlib import Path

from .review_contract import digest


def _resolve(value, pointer):
    current = value
    if pointer == "":
        return current
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("Invalid execution evidence JSON pointer")
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            if not token.isdigit() or int(token) >= len(current):
                raise ValueError("Execution evidence points outside its record")
            current = current[int(token)]
        elif isinstance(current, dict) and token in current:
            current = current[token]
        else:
            raise ValueError("Execution evidence points outside its record")
    return current


def _ref(record, label, pointer, **extra):
    _resolve(record, pointer)
    return {"label": label, "pointer": pointer, **extra}


def _run_evidence(record, run, run_pointer, request, request_pointer, phase):
    operations = []
    for index, event in enumerate(run.get("events", [])):
        event_pointer = f"{run_pointer}/events/{index}"
        references = [
            _ref(record, "request at dispatch", request_pointer),
            _ref(record, "saved event binding", event_pointer),
        ]
        if "source_evidence" in run:
            references.append(
                _ref(record, "captured sources", run_pointer + "/source_evidence")
            )
        if phase == "build" and event["kind"] == "participant_turn":
            participant_key = next(
                (
                    key
                    for key, outcome in run.get("participants", {}).items()
                    if outcome.get("attempt_id") == event.get("attempt_id")
                ),
                "",
            )
            role, _, task_id = participant_key.partition(":")
            task_index = next(
                (i for i, task in enumerate(request["tasks"]) if task["id"] == task_id),
                None,
            )
            if role == "worker" and task_index is not None:
                references.append(
                    _ref(record, "accepted step", f"{request_pointer}/tasks/{task_index}")
                )
            elif role == "reviewer":
                references.append(
                    _ref(
                        record,
                        "accepted review criteria",
                        request_pointer + "/intent/acceptance",
                    )
                )
        if event["kind"] == "build_control":
            control_index = next(
                (
                    i
                    for i, item in enumerate(request["effects"].get("checks", []))
                    if item["control"]["id"]
                    == event["operation_key"].removeprefix("control:")
                ),
                None,
            )
            runner_pointer = (
                f"{request_pointer}/effects/checks/{control_index}"
                if control_index is not None
                else event_pointer + "/runner"
            )
            references.append(_ref(record, "accepted control runner", runner_pointer))
        elif event["kind"] == "file_effect":
            references.append(_ref(record, "proposed file effect", event_pointer + "/item"))
        elif event["kind"] == "acceptance_probe":
            verification_index = next(
                (
                    i
                    for i, item in enumerate(
                        request["effects"].get("verification", [])
                    )
                    if item["task_id"]
                    == event["operation_key"].removeprefix("probe:")
                ),
                None,
            )
            probe_pointer = (
                f"{request_pointer}/effects/verification/{verification_index}"
                if verification_index is not None
                else request_pointer + "/effects"
            )
            references.append(_ref(record, "accepted verification probe", probe_pointer))

        category = (
            "host_check"
            if event["kind"] in ("build_control", "acceptance_probe")
            else "file_effect"
            if event["kind"] == "file_effect"
            else "model_response"
        )
        operation = {
            "operation": event["operation_key"],
            "kind": event["kind"],
            "category": category,
            "event_pointer": event_pointer,
            "executor_input": {
                "representation": "reconstructed from retained inputs",
                "digest": event.get(
                    "request_digest",
                    event.get("plan_digest", event.get("manifest_digest")),
                ),
                "references": references,
                "prior_event_prefix": {
                    "pointer": run_pointer + "/events",
                    "length": index,
                },
            },
            "runtime_origin": (
                {
                    "status": "recorded",
                    "pointer": event_pointer + "/runtime_origin",
                    "value": copy.deepcopy(event["runtime_origin"]),
                    "meaning": "origin file bytes observed at dispatch; not in-memory bytecode proof",
                }
                if "runtime_origin" in event
                else {
                    "status": "unavailable",
                    "reason": (
                        "operation is prepared and has not been dispatched"
                        if event["phase"] == "prepared"
                        else "legacy run did not capture dispatch origins"
                    ),
                }
            ),
            "result": {"status": "unavailable"},
        }
        if event["state"] == "completed":
            result_pointer = event_pointer + "/result"
            operation["result"] = {"status": "completed", "pointer": result_pointer}
            if category == "host_check":
                result = event["result"]
                attempted_only = result.get("failure") in (
                    "not_found",
                    "launch_failed",
                    "cancelled_before_start",
                )
                operation["result"].update(
                    passed=result["passed"],
                    failure=result["failure"],
                    argv={
                        "status": "attempted" if attempted_only else "executed",
                        "pointer": result_pointer + "/argv",
                    },
                )
                if event["kind"] == "build_control":
                    operation["executor_input"]["proposed_argv"] = {
                        "pointer": runner_pointer + "/probe/argv"
                    }
                elif verification_index is not None:
                    operation["executor_input"]["proposed_argv"] = {
                        "pointer": probe_pointer + "/probe/argv"
                    }
            elif category == "model_response":
                operation["participant_reported_adapter_identity"] = {
                    "pointer": result_pointer + "/identity",
                    "value": copy.deepcopy(event["result"].get("identity")),
                    "meaning": "adapter-reported identity; not host runtime provenance",
                }
                operation["result"]["meaning"] = (
                    "completed transport response; owner validation determines whether its judgment was accepted"
                )
        prior = []
        for r_index, reconciliation in enumerate(event.get("reconciliations", [])):
            previous = reconciliation["previous"]
            if "runtime_origin" in previous:
                pointer = f"{event_pointer}/reconciliations/{r_index}/previous/runtime_origin"
                prior.append({"pointer": pointer, "value": copy.deepcopy(_resolve(record, pointer))})
        if prior:
            operation["prior_dispatch_origins"] = prior
        operations.append(operation)
    return {
        "phase": phase,
        "run_pointer": run_pointer,
        "request_pointer": request_pointer,
        "request_digest": digest(request),
        "capture_policy": (
            {"status": "recorded", "pointer": run_pointer + "/capture_policy"}
            if "capture_policy" in run
            else {"status": "unavailable", "reason": "legacy run"}
        ),
        "operations": operations,
    }


def work_execution_evidence(record):
    """Project current and retained historical work journals without dispatch."""
    result = {
        "schema_version": 1,
        "record_path": record["record_path"],
        "current_request": {
            "pointer": "/request",
            "digest": digest(record["request"]),
        },
        "current_checkpoint": {
            "pointer": "/checkpoint_digest",
            "digest": record["checkpoint_digest"],
        },
        "runs": [],
    }
    for phase in ("planning", "build"):
        if phase in record:
            result["runs"].append(
                _run_evidence(record, record[phase], "/" + phase, record["request"], "/request", phase)
            )
    for index, historical in enumerate(record.get("history", [])):
        for phase in ("planning", "build"):
            if phase in historical:
                base = f"/history/{index}"
                result["runs"].append(
                    _run_evidence(
                        record,
                        historical[phase],
                        base + "/" + phase,
                        historical["request"],
                        base + "/request",
                        phase,
                    )
                )
    return result


def test_execution_evidence(task, *, artifacts_valid):
    """Reference existing pytest inputs and artifacts without copying their payload."""
    evidence = {
        "schema_version": 1,
        "record_path": task["record_path"],
        "request": {"pointer": "/request", "digest": digest(task["request"])},
        "checkpoint": {
            "pointer": "/checkpoint_digest",
            "digest": task["checkpoint_digest"],
        },
        "executor_input": {
            "runner": {"pointer": "/request/runner", "digest": digest(task["request"]["runner"])},
            "snapshot": {"pointer": "/request/snapshot", "digest": digest(task["request"]["snapshot"])},
        },
        "operation": {"status": "unavailable"},
    }
    run = task.get("execution")
    if not run or not run.get("events"):
        return evidence
    event = run["events"][0]
    evidence["operation"] = {
        "status": event["state"],
        "event_pointer": "/execution/events/0",
        "result": {"status": "unavailable"},
    }
    if event["state"] != "completed":
        return evidence
    result = event["result"]
    result_pointer = "/execution/events/0/result"
    evidence["operation"]["result"] = {"status": "completed", "pointer": result_pointer}
    artifact_index = next(
        (i for i, item in enumerate(result.get("artifacts", [])) if item.get("path") == "pytest.json"),
        None,
    )
    if artifact_index is None or not artifacts_valid:
        evidence["operation"]["pytest_observer"] = {
            "status": "unavailable",
            "reason": "pytest.json is missing or failed artifact validation",
        }
    elif result.get("pytest") is None:
        metadata_pointer = f"{result_pointer}/artifacts/{artifact_index}"
        evidence["operation"]["pytest_observer"] = {
            "status": "invalid",
            "reason": "pytest.json was retained for diagnostics but its observer payload did not validate",
            "artifact_metadata_pointer": metadata_pointer,
            "artifact_path": str(Path(task["record_path"]).parent / "pytest.json"),
        }
    else:
        metadata_pointer = f"{result_pointer}/artifacts/{artifact_index}"
        evidence["operation"]["pytest_observer"] = {
            "status": "recorded",
            "artifact_metadata_pointer": metadata_pointer,
            "artifact_path": str(Path(task["record_path"]).parent / "pytest.json"),
            "module_origins_json_pointer": "/module_origins",
        }
    process = result.get("process")
    if isinstance(process, dict) and "argv" in process:
        attempted_only = process.get("failure") in (
            "not_found",
            "launch_failed",
            "cancelled_before_start",
        )
        evidence["operation"]["process_argv"] = {
            "status": "attempted" if attempted_only else "executed",
            "pointer": result_pointer + "/process/argv",
        }
    return evidence
