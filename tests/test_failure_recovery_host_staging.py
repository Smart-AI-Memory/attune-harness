"""Passive sensor controls use actual owner effects, not a staging-prefix rule."""

# qualify: platform

import asyncio
import copy
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import os
from pathlib import Path
import stat
import sys
from threading import Event

import pytest


HERE = Path(__file__).resolve().parents[1] / "experiments/failure_recovery"
SPEC = importlib.util.spec_from_file_location("failure_recovery_staging", HERE / "__init__.py",
                                               submodule_search_locations=[str(HERE)])
PACKAGE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PACKAGE
SPEC.loader.exec_module(PACKAGE)
from failure_recovery_staging import bounds, fixture, host_staging, oracle, recorder, run, score, solutions
from attune_harness.work_runtime import build_work


def actual_owner(root, patch, *, fault=None):
    if os.name != "posix" or sys.implementation.name != "cpython":
        pytest.skip("The native Python rename sensor qualifies only CPython POSIX")
    trial, record = fixture.prepare_trial(root / "trial")
    app, state = trial / "app", trial / "task"
    protected = bounds.read_bytes(app / "tests/test_report.py")
    with fixture.isolated_profile(trial):
        asyncio.run(run.accept(state, record))
    prepared, release = Event(), Event()
    actual_fsync, actual_stat = os.fsync, os.stat
    renamed = {"source": None, "active": False}
    fired = False

    def prepared_fsync(fd):
        metadata = os.fstat(fd)
        if not prepared.is_set() and stat.S_ISREG(metadata.st_mode) and metadata.st_size == len(solutions.GOOD.encode()):
            prepared.set()
            if not release.wait(timeout=10):
                raise RuntimeError("Test controller did not release the prepared native write")
        return actual_fsync(fd)

    def fail_rename(event, args):
        # This is a deliberate independent fault injector, not the observer hook.
        if renamed["active"] and event == "os.rename" and args[0] == renamed["source"]:
            raise OSError("Controlled native rename failure")

    def build():
        with fixture.isolated_profile(trial):
            return build_work(state, allow_external=True, allow_native=False, allow_api_spend=False)

    patch.setattr(os, "fsync", prepared_fsync)
    with recorder.Recorder(app, trial / "observation", effect_plan=record["request"]["effects"]) as observer:
        observer.stop_requested.set()
        observer.thread.join(timeout=2)
        assert not observer.thread.is_alive()
        if fault == "capture":
            def unavailable(*args):
                raise SystemExit("Injected observer capture failure")
            patch.setattr(host_staging.Sensor, "record", unavailable)
        elif fault == "overflow":
            observer.sensor.limit = 0
        elif fault == "unregistered":
            observer.sensor.registered = False
        if fault == "rename":
            sys.addaudithook(fail_rename)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(build)
            try:
                assert prepared.wait(timeout=10), "Actual native writer did not prepare the expected source"
                temporary = next(path for path in (app / "src").iterdir() if path.name != "report.py")
                probe = temporary
                if fault == "foreign":
                    probe = app / "src/.harness-replace-lookalike"
                    probe.write_bytes(b"Foreign calibration effect, not native lineage\n")
                elif fault == "protected":
                    probe = app / "tests/test_report.py"
                elif fault == "reused":
                    release.set()
                    future.result(timeout=15)
                    probe.write_bytes(b"A later foreign entry reuses the exact former staging name\n")
                renamed["source"], renamed["active"] = temporary.name, fault == "rename"

                def disappearing_stat(path, *args, **kwargs):
                    nonlocal fired
                    if not fired and path == probe.name and kwargs.get("dir_fd") is not None:
                        fired = True
                        if fault in ("foreign", "protected", "reused"):
                            os.replace(probe, root / "calibration-retained-entry")
                        else:
                            release.set()
                            future.result(timeout=15)
                    return actual_stat(path, *args, **kwargs)

                with patch.context() as sampling:
                    sampling.setattr(os, "stat", disappearing_stat)
                    observer.sample()
                if fault == "protected":
                    os.replace(root / "calibration-retained-entry", app / "tests/test_report.py")
                release.set()
                result = future.result(timeout=15)
                observer.sample()  # A later full snapshot cannot manufacture lineage.
            finally:
                release.set()
                renamed["active"] = False
    assert fired
    report = recorder.read_report(trial / "observation")
    bound = host_staging.bind_host_staging(report, result, app)
    owner = run.owner_summary(result)
    checked = oracle.evaluate(app, oracle.cases(), trial / "test-independent-oracle")
    receipt = {"kind": "actual-offline-owner-host-staging-control", "fault": fault,
               "model_calls": 0, "ci_cause_reinterpreted": False, "owner_status": owner["status"],
               "owner_record_sha256": owner["record_sha256"], "oracle_passed": checked["passed"],
               "owner_record_path": owner["record_path"],
               "protected_unchanged": bounds.read_bytes(app / "tests/test_report.py") == protected,
               "gap_count": len(report["gaps"]), "host_sensor": report["host_sensor"],
               "lineage": bound["host_staging"],
               "qualified": score._observation_qualified(bound["before"], bound["after"], bound, owner["record_sha256"], owner["record_path"])}
    bounds.write_json(root / "receipt.json", receipt, bounds.MAX_EVIDENCE)
    return report, bound, result, receipt


@pytest.fixture(scope="module")
def positive(tmp_path_factory):
    root = tmp_path_factory.mktemp("actual-host-staging").resolve()
    with pytest.MonkeyPatch.context() as patch:
        return actual_owner(root, patch)


def test_actual_owner_lineage_needs_intent_snapshot_and_native_completion(positive):
    report, bound, result, receipt = positive
    assert receipt["owner_status"] == "completed" and receipt["oracle_passed"] and receipt["protected_unchanged"]
    assert receipt["qualified"] and len(report["gaps"]) == 1
    gap = report["gaps"][0]
    assert gap["error"] == "EnumeratedLeafMissing" and gap["reason"] == "enumerated_leaf_missing"
    assert gap["enumeration"]["parent_before"] == gap["enumeration"]["parent_after"]
    assert report["gaps"] == bound["gaps"] and len(bound["host_staging"]["bindings"]) == 1
    assert not recorder.gaps_acknowledged(report, receipt["owner_record_sha256"], receipt["owner_record_path"])
    assert not recorder.gaps_acknowledged(bound, "0" * 64, receipt["owner_record_path"])
    assert not recorder.gaps_acknowledged(bound, receipt["owner_record_sha256"])
    assert recorder.gaps_acknowledged(bound, receipt["owner_record_sha256"], receipt["owner_record_path"])
    assert report["coverage"] == "sampled/incomplete" and report["absence_proved"] is False
    assert result["request"]["effects"]["allowed"] == fixture.OUTPUTS
    assert report["host_sensor"]["policy"]["metadata_permission_added"] is False


@pytest.mark.parametrize("fault", ["capture", "overflow", "unregistered", "foreign", "protected", "reused"])
def test_observer_or_unattributed_failure_does_not_change_owner_or_qualify(tmp_path, monkeypatch, fault):
    _, bound, _, receipt = actual_owner(tmp_path.resolve(), monkeypatch, fault=fault)
    assert receipt["owner_status"] == "completed" and receipt["oracle_passed"] and receipt["protected_unchanged"]
    assert receipt["gap_count"] and not receipt["qualified"]
    assert bound["coverage"] == "sampled/incomplete" and bound["absence_proved"] is False
    if fault == "foreign":
        assert bound["gaps"][0]["path"] == "src/.harness-replace-lookalike"
        assert not any(intent["source"] == bound["gaps"][0]["path"] for intent in bound["host_sensor"]["intents"])
    if fault == "capture":
        assert bound["host_sensor"]["failed"]


def test_actual_failed_rename_intent_is_not_a_completed_effect(tmp_path, monkeypatch):
    report, bound, _, receipt = actual_owner(tmp_path.resolve(), monkeypatch, fault="rename")
    assert report["host_sensor"]["intents"]
    assert receipt["owner_status"] != "completed" and not receipt["qualified"]
    assert bound["host_staging"]["unknown"] and bound["host_staging"]["bindings"] == []


@pytest.mark.parametrize("mutation", ["missing-completion", "duplicate-completion", "origin", "manifest", "item", "duplicate-intent"])
def test_missing_or_forged_lineage_does_not_qualify(positive, mutation):
    original, _, actual, receipt = positive
    report, record = copy.deepcopy(original), copy.deepcopy(actual)
    effect = next(e for e in record["build"]["events"] if e["kind"] == "file_effect" and e["item"]["path"] == "src/report.py")
    if mutation == "missing-completion":
        record["build"]["events"].remove(effect)
    elif mutation == "duplicate-completion":
        record["build"]["events"].append(copy.deepcopy(effect))
    elif mutation == "origin":
        next(module for module in effect["runtime_origin"]["modules"] if module["name"] == "attune_harness.repair")["sha256"] = "0" * 64
    elif mutation == "manifest":
        effect["manifest_digest"] = "0" * 64
    elif mutation == "item":
        effect["item"]["text"] += "# altered derivative\n"
    else:
        intent = copy.deepcopy(report["host_sensor"]["intents"][0])
        intent["id"] = len(report["host_sensor"]["intents"])
        report["host_sensor"]["intents"].append(intent)
    bound = host_staging.bind_host_staging(report, record, Path(record["request"]["effects"]["root"]))
    assert not recorder.gaps_acknowledged(bound, receipt["owner_record_sha256"], receipt["owner_record_path"])


def test_ancestor_or_bare_old_error_cannot_be_used_as_a_leaf_witness(positive):
    report, _, actual, receipt = positive
    bare = copy.deepcopy(report)
    bare["gaps"][0].pop("enumeration")
    bare["gaps"][0]["error"] = "FileNotFoundError"
    bare["gaps"][0]["reason"] = "old unbound missing entry"
    bound = host_staging.bind_host_staging(bare, actual, Path(actual["request"]["effects"]["root"]))
    assert not recorder.gaps_acknowledged(bound, receipt["owner_record_sha256"], receipt["owner_record_path"])
    changed = copy.deepcopy(report)
    changed["gaps"][0]["enumeration"]["parent_after"]["inode"] += 1
    assert not recorder.gaps_acknowledged(changed, receipt["owner_record_sha256"], receipt["owner_record_path"])


@pytest.mark.parametrize("mutation", ["event-id", "source-origin", "record-path"])
def test_forged_bound_json_with_real_owner_hash_is_not_completion(positive, mutation):
    report, valid, _, receipt = positive
    forged = copy.deepcopy(report)  # This observer report has only a pending intent.
    forged["host_staging"] = copy.deepcopy(valid["host_staging"])
    if mutation == "event-id":
        forged["host_staging"]["bindings"][0]["event_id"] = "invented-no-native-event"
    elif mutation == "source-origin":
        forged["host_sensor"]["origin"]["sha256"] = "0" * 64
    else:
        forged["host_staging"]["record_path"] += ".foreign"
    assert not recorder.gaps_acknowledged(forged, receipt["owner_record_sha256"], receipt["owner_record_path"])


def test_mutating_cached_function_code_invalidates_existing_lineage(positive):
    _, bound, _, receipt = positive
    original = host_staging.ORIGINAL_REPAIR.__code__
    assert recorder.gaps_acknowledged(bound, receipt["owner_record_sha256"], receipt["owner_record_path"])
    try:
        host_staging.ORIGINAL_REPAIR.__code__ = (lambda plan, item: None).__code__
        assert not recorder.gaps_acknowledged(bound, receipt["owner_record_sha256"], receipt["owner_record_path"])
    finally:
        host_staging.ORIGINAL_REPAIR.__code__ = original


def test_changed_source_origin_copy_invalidates_lineage(positive, tmp_path, monkeypatch):
    _, bound, _, receipt = positive
    copied = tmp_path / "changed-origin.py"
    copied.write_bytes(bounds.read_bytes(host_staging.ORIGIN_PATH, bounds.MAX_RETAINED_FILE) + b"\n# changed origin copy\n")
    monkeypatch.setattr(host_staging, "ORIGIN_PATH", copied)
    assert not recorder.gaps_acknowledged(bound, receipt["owner_record_sha256"], receipt["owner_record_path"])
