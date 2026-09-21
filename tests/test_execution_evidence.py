"""Durable executor inputs and actual dispatch origins stay inspectable."""

import copy
import hashlib
from pathlib import Path

import pytest
import test_test_change as testing
import test_work_build as builds
import test_work_contract as contracts
import test_work_effects as effects
import test_work_planning as planning

from attune_harness import recovery, work_effects
from attune_harness.execution_evidence import work_execution_evidence
from attune_harness.review_contract import digest
from attune_harness.review_store import RunStore
from attune_harness.task_contract import read_task
from attune_harness.task_policies import execute_task
from attune_harness.test_change import public_test_task
from attune_harness.work_build import validate_build
from attune_harness.work_cli import present
from attune_harness.work_runtime import (
    apply_planning_proposal,
    plan_work,
    validate_planning,
)

work = contracts.work
project = testing.project


@pytest.fixture(autouse=True)
def reset_peers():
    planning.Scripted.seen = []
    planning.Scripted.mutate = None
    builds.Worker.seen = []
    builds.Worker.mutation = None


def resolve(value, pointer):
    for token in pointer.strip("/").split("/") if pointer else []:
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def runtime_switch(monkeypatch):
    actual = recovery.capture_runtime_origin
    selected = {"path": "/runtime-a/python"}

    def capture(names):
        value = actual(names)
        value["interpreter"]["path"] = selected["path"]
        return value

    monkeypatch.setattr(recovery, "capture_runtime_origin", capture)
    return selected


def test_planning_resume_records_each_actual_runtime_and_history_stays_visible(
    work, monkeypatch
):
    planning.add_critic(work)
    contracts.make(work)
    runtime = runtime_switch(monkeypatch)
    paused = plan_work(
        work[2]["directory"], exchange_factory=planning.Scripted, max_operations=1
    )
    first = copy.deepcopy(paused["planning"]["events"][0]["runtime_origin"])
    assert first["attempt"] == 1
    assert first["interpreter"]["path"] == "/runtime-a/python"

    runtime["path"] = "/runtime-b/python"
    completed = plan_work(work[2]["directory"], exchange_factory=planning.Scripted)
    origins = [event["runtime_origin"] for event in completed["planning"]["events"]]
    assert origins[0] == first
    assert origins[1]["interpreter"]["path"] == "/runtime-b/python"
    for module in origins[1]["modules"]:
        assert hashlib.sha256(Path(module["path"]).read_bytes()).hexdigest() == module[
            "sha256"
        ]

    staged = apply_planning_proposal(
        work[2]["directory"], checkpoint=completed["checkpoint_digest"]
    )
    shown = present(work[2]["directory"])
    historical = next(
        run
        for run in shown["execution_evidence"]["runs"]
        if run["run_pointer"].startswith("/history/")
    )
    historical_request = resolve(staged, historical["request_pointer"])
    assert historical["request_digest"] == digest(historical_request)
    assert historical["operations"][0]["runtime_origin"]["value"] == first


def test_planning_legacy_resume_does_not_backfill_current_runtime(work, monkeypatch):
    planning.add_critic(work)
    contracts.make(work)
    paused = plan_work(
        work[2]["directory"], exchange_factory=planning.Scripted, max_operations=1
    )
    run = paused["planning"]
    original_digest = run["events"][0]["request_digest"]
    run.pop("capture_policy")
    for event in run["events"]:
        event.pop("runtime_origin")
    store = RunStore(work[2]["directory"], existing=True)
    with store.lease():
        store.save(paused)

    monkeypatch.setattr(
        recovery,
        "capture_runtime_origin",
        lambda names: pytest.fail("legacy resume attempted provenance backfill"),
    )
    completed = plan_work(work[2]["directory"], exchange_factory=planning.Scripted)
    assert completed["planning"]["events"][0]["request_digest"] == original_digest
    assert all("runtime_origin" not in event for event in completed["planning"]["events"])
    evidence = work_execution_evidence(completed)["runs"][0]
    assert evidence["capture_policy"] == {
        "status": "unavailable",
        "reason": "legacy run",
    }


@pytest.mark.parametrize(
    "tamper",
    [
        "missing",
        "hash",
        "attempt",
        "bool_attempt",
        "bool_version",
        "bool_policy",
        "null_policy",
        "null_origin",
        "legacy_forgery",
    ],
)
def test_malformed_or_forged_dispatch_origins_are_rejected(work, tamper):
    contracts.make(work)
    record = plan_work(work[2]["directory"], exchange_factory=planning.Scripted)
    run = copy.deepcopy(record["planning"])
    event = run["events"][0]
    if tamper == "missing":
        event.pop("runtime_origin")
    elif tamper == "hash":
        event["runtime_origin"]["modules"][0]["sha256"] = "not-a-digest"
    elif tamper == "attempt":
        event["runtime_origin"]["attempt"] = 2
    elif tamper == "bool_attempt":
        event["runtime_origin"]["attempt"] = True
    elif tamper == "bool_version":
        event["runtime_origin"]["version"] = True
    elif tamper == "bool_policy":
        run["capture_policy"]["version"] = True
    elif tamper == "null_policy":
        run["capture_policy"] = None
    elif tamper == "null_origin":
        event["runtime_origin"] = None
    else:
        run.pop("capture_policy")
    with pytest.raises(ValueError, match="origin|capture"):
        validate_planning(run, record["request"])


def test_build_status_separates_inputs_checks_results_and_adapter_identity(
    work, monkeypatch
):
    case = builds.prepare(work)
    completed = builds.execute(case)
    validate_build(completed["build"], completed["request"])
    before = (case[1] / "record.json").read_bytes()
    monkeypatch.setattr(
        recovery,
        "capture_runtime_origin",
        lambda names: pytest.fail("status attempted a runtime capture"),
    )
    shown = present(case[1])
    assert (case[1] / "record.json").read_bytes() == before
    run = next(
        item
        for item in shown["execution_evidence"]["runs"]
        if item["phase"] == "build"
    )
    check = next(item for item in run["operations"] if item["category"] == "host_check")
    model = next(item for item in run["operations"] if item["category"] == "model_response")
    assert check["result"]["passed"] is True
    assert check["result"]["argv"]["status"] == "executed"
    assert check["executor_input"]["proposed_argv"]["pointer"] != check["result"][
        "argv"
    ]["pointer"]
    assert model["participant_reported_adapter_identity"]["value"]["adapter"] == (
        "scripted-local"
    )
    saved = read_task(case[1])
    for operation in run["operations"]:
        resolve(saved, operation["event_pointer"])
        for reference in operation["executor_input"]["references"]:
            resolve(saved, reference["pointer"])
        if operation["result"]["status"] == "completed":
            resolve(saved, operation["result"]["pointer"])


def test_standalone_retry_retains_prior_origin_and_captures_new_attempt(
    work, monkeypatch
):
    case = effects.prepare(work)
    runtime = runtime_switch(monkeypatch)

    def stop(plan, item):
        raise OSError("before the effect")

    with monkeypatch.context() as patch:
        patch.setattr(work_effects, "write_effect", stop)
        with pytest.raises(OSError, match="before the effect"):
            effects.execute(case)
    failed = read_task(case[1])
    event = failed["build"]["events"][-1]
    prior = copy.deepcopy(event["runtime_origin"])
    reconciled = effects.reconcile(case, retry_before=True)
    prepared = reconciled["build"]["events"][-1]
    assert prepared["phase"] == "prepared" and "runtime_origin" not in prepared
    assert prepared["reconciliations"][0]["previous"]["runtime_origin"] == prior

    runtime["path"] = "/runtime-b/python"
    completed = effects.execute(case)
    retried = next(
        item
        for item in completed["build"]["events"]
        if item["event_id"] == event["event_id"]
    )
    assert retried["runtime_origin"]["attempt"] == 2
    assert retried["runtime_origin"]["interpreter"]["path"] == "/runtime-b/python"
    projected = work_execution_evidence(completed)["runs"][0]
    operation = next(
        item
        for item in projected["operations"]
        if item["operation"] == retried["operation_key"]
    )
    assert operation["prior_dispatch_origins"][0]["value"] == prior
    forged = copy.deepcopy(completed["build"])
    forged_event = next(
        item for item in forged["events"] if item["event_id"] == event["event_id"]
    )
    forged_event["reconciliations"][0]["previous"]["attempts"] = True
    with pytest.raises(ValueError, match="origin"):
        work_effects.validate_journal(forged, completed["request"])


def test_paused_pytest_status_references_completed_event_artifact(project, tmp_path):
    directory = testing.accept(project, tmp_path)
    paused = execute_task(directory, max_operations=1)
    assert testing.outcome(paused) == "paused"
    evidence = public_test_task(paused)["execution_evidence"]
    operation = evidence["operation"]
    assert operation["status"] == "completed"
    assert operation["result"]["pointer"] == "/execution/events/0/result"
    observer = operation["pytest_observer"]
    assert observer["status"] == "recorded"
    assert observer["module_origins_json_pointer"] == "/module_origins"
    assert resolve(paused, observer["artifact_metadata_pointer"])["path"] == "pytest.json"


def test_invalid_pytest_observer_artifact_never_claims_module_origins(project, tmp_path):
    directory = testing.accept(project, tmp_path)
    completed = execute_task(directory)
    malformed = copy.deepcopy(completed)
    malformed["execution"]["events"][0]["result"]["pytest"] = None
    malformed["execution"]["result"]["pytest"] = None
    shown = public_test_task(testing.test_change.present_test_task(malformed))
    observer = shown["execution_evidence"]["operation"]["pytest_observer"]
    assert observer["status"] == "invalid"
    assert "module_origins_json_pointer" not in observer
    assert resolve(malformed, observer["artifact_metadata_pointer"])["path"] == (
        "pytest.json"
    )
