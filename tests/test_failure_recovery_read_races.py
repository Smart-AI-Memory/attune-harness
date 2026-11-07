"""Real child writes qualify only the narrow, journal-bound read-race recovery."""

# qualify: platform

import copy
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest


HERE = Path(__file__).resolve().parents[1] / "experiments/failure_recovery"
SPEC = importlib.util.spec_from_file_location("failure_recovery_races", HERE / "__init__.py",
                                               submodule_search_locations=[str(HERE)])
PACKAGE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PACKAGE
SPEC.loader.exec_module(PACKAGE)
from failure_recovery_races import bounds, fixture, oracle, recorder, score, solutions


WRITER = '''from pathlib import Path
import os
import sys
import time
target, outside = map(Path, sys.argv[1:3])
count, same_bytes, operation = int(sys.argv[3]), sys.argv[4] == "True", sys.argv[5]
for index in range(count):
    deadline = time.monotonic() + 5
    while not (outside / ("go-" + str(index))).exists():
        if time.monotonic() >= deadline:
            raise SystemExit(2)
        time.sleep(0.001)
    data = target.read_bytes()
    if not same_bytes:
        data += b"\\n# allowed synthetic calibration write\\n"
    if operation == "atomic":
        replacement = target.with_name("owned-replacement.tmp")
        replacement.write_bytes(data)
        os.replace(replacement, target)
    else:
        target.write_bytes(data)
    (outside / ("done-" + str(index))).write_bytes(b"write complete\\n")
'''


def app_fixture(root):
    app = root / "app"
    (app / "src").mkdir(parents=True)
    (app / "tests").mkdir()
    (app / "src/report.py").write_bytes(solutions.GOOD.encode())
    (app / "tests/test_report.py").write_bytes(b"# frozen synthetic original test\n")
    return app


def stop_polling(observer):
    """Drive exact sample boundaries for this controlled local mechanism test."""
    observer.stop_requested.set()
    observer.thread.join(timeout=2)
    assert not observer.thread.is_alive()


def real_collision(root, monkeypatch, *, count=1, same_bytes=False,
                   path="src/report.py", operation="atomic", max_events=bounds.MAX_EVENTS):
    if os.name != "posix":
        pytest.skip("This real open-inode replacement window is a POSIX control")
    app = app_fixture(root)
    target = app / path
    protected_before = (app / "tests/test_report.py").read_bytes()
    writer = root / "writer.py"
    writer.write_text(WRITER, encoding="utf-8", newline="")
    process = subprocess.Popen([sys.executable, "-I", "-B", str(writer), str(target), str(root),
                                str(count), str(same_bytes), operation],
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               env=oracle.environment(root))
    actual_read, collisions = os.read, 0

    def collide(fd, size):
        nonlocal collisions
        opened, current = os.fstat(fd), target.stat()
        if collisions < count and (opened.st_dev, opened.st_ino) == (current.st_dev, current.st_ino):
            index = collisions
            collisions += 1
            (root / ("go-" + str(index))).write_bytes(b"replace during the actual read\n")
            deadline = time.monotonic() + 3
            while not (root / ("done-" + str(index))).exists():
                if time.monotonic() >= deadline:
                    raise RuntimeError("Owned writer did not acknowledge its write")
                time.sleep(0.001)
        return actual_read(fd, size)

    try:
        with recorder.Recorder(app, root / "observation", interval=0.1, max_events=max_events) as observer:
            stop_polling(observer)
            attempts_before = observer.capture_attempts
            with monkeypatch.context() as patch:
                patch.setattr(os, "read", collide)
                observer.sample()
            collision_attempts = observer.capture_attempts - attempts_before
            observer.sample()  # A later good sample must not heal an unacknowledged failure.
        stdout, stderr = process.communicate(timeout=3)
    except BaseException:
        process.kill()
        process.communicate()
        raise
    assert process.returncode == 0, (stdout, stderr)
    assert collisions == count
    report = recorder.read_report(root / "observation")
    checked = oracle.evaluate(app, oracle.cases(), root / "oracle")
    receipt = {"kind": "offline-POSIX-read-race-control", "ci_cause_established": False,
               "real_subprocess": True, "child_returncode": process.returncode,
               "collisions": collisions, "capture_attempts_during_collision": collision_attempts,
               "protected_unchanged": (app / "tests/test_report.py").read_bytes() == protected_before,
               "oracle_passed": checked["passed"], "gaps": report["gaps"],
               "recoveries": [e["recovery"] for e in report["events"] if e["phase"] == "recovery"],
               "qualified": score._observation_qualified(report["before"], report["after"], report),
               "coverage": report["coverage"], "absence_proved": report["absence_proved"], "model_calls": 0}
    bounds.write_json(root / "receipt.json", receipt)
    return report, checked, receipt


@pytest.mark.parametrize("same_bytes", [False, True])
def test_real_allowed_atomic_race_keeps_gap_and_bound_recovery(tmp_path, monkeypatch, same_bytes):
    report, checked, receipt = real_collision(tmp_path.resolve(), monkeypatch, same_bytes=same_bytes)
    assert checked["passed"] and receipt["protected_unchanged"] and receipt["qualified"]
    assert receipt["capture_attempts_during_collision"] == 2
    assert len(report["gaps"]) == len(receipt["recoveries"]) == 1
    gap, ack = report["gaps"][0], receipt["recoveries"][0]
    assert (gap["path"], gap["phase"], gap["attempt"], gap["reason"], gap["error"]) == (
        "src/report.py", "sample", 1, "atomic_leaf_replacement", "AtomicLeafReplacement")
    assert ack["gap_id"] == gap["id"] and ack["sample"] == gap["sample"] and ack["attempt"] == 2
    event = next(e for e in report["events"] if e["phase"] == "recovery")
    if same_bytes:
        assert event["changed"] == {} and event["deleted"] == []
    assert report["coverage"] == "sampled/incomplete" and report["absence_proved"] is False


def test_real_second_race_stays_unresolved_after_later_good_samples(tmp_path, monkeypatch):
    report, checked, receipt = real_collision(tmp_path.resolve(), monkeypatch, count=2)
    assert checked["passed"] and receipt["protected_unchanged"]
    assert receipt["capture_attempts_during_collision"] == 2
    assert [g["attempt"] for g in report["gaps"]] == [1, 2]
    assert receipt["recoveries"] == [] and not receipt["qualified"]
    assert report["before"] is not None and report["after"] is not None


def test_recovery_snapshot_must_fit_and_be_persisted(tmp_path, monkeypatch):
    report, checked, receipt = real_collision(tmp_path.resolve(), monkeypatch, max_events=1)
    assert checked["passed"] and receipt["protected_unchanged"]
    assert len(report["gaps"]) == 1 and report["exhausted"] and report["after"] is None
    assert receipt["recoveries"] == [] and not receipt["qualified"]


@pytest.mark.parametrize("path,operation", [("tests/test_report.py", "atomic"), ("src/report.py", "inplace")])
def test_real_protected_or_inplace_change_is_not_retried(tmp_path, monkeypatch, path, operation):
    report, _, receipt = real_collision(tmp_path.resolve(), monkeypatch, path=path, operation=operation)
    assert receipt["capture_attempts_during_collision"] == 1
    assert len(report["gaps"]) == 1 and report["gaps"][0]["path"] == path
    assert not receipt["qualified"] and receipt["recoveries"] == []


def test_generic_read_failure_never_recovers_from_a_later_snapshot(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    app = app_fixture(root)
    with recorder.Recorder(app, root / "observation") as observer:
        stop_polling(observer)
        attempts_before = observer.capture_attempts
        with monkeypatch.context() as patch:
            def refuse(_):
                raise OSError("persistent generic read refusal")
            patch.setattr(bounds, "capture", refuse)
            observer.sample()
        assert observer.capture_attempts - attempts_before == 1
        observer.sample()
    report = recorder.read_report(root / "observation")
    assert report["gaps"][0]["error"] == "OSError" and report["gaps"][0]["path"] is None
    assert not recorder.gaps_acknowledged(report)
    assert not score._observation_qualified(report["before"], report["after"], report)


@pytest.mark.parametrize("mutation", ["orphan", "duplicate", "snapshot", "protected", "generic", "attempt", "later", "count"])
def test_forged_recovery_acknowledgements_are_rejected(tmp_path, monkeypatch, mutation):
    root = tmp_path.resolve()
    report, _, _ = real_collision(root, monkeypatch)
    events = copy.deepcopy(report.pop("events"))
    recovery = next(e for e in events if e["phase"] == "recovery")
    if mutation == "orphan":
        recovery["recovery"]["gap_id"] = 99
    elif mutation == "duplicate":
        events.insert(events.index(recovery) + 1, copy.deepcopy(recovery))
    elif mutation == "snapshot":
        recovery["recovery"]["snapshot_sha256"] = "0" * 64
    elif mutation == "protected":
        report["gaps"][0]["path"] = "tests/test_report.py"
    elif mutation == "generic":
        report["gaps"][0]["error"] = "OSError"
    elif mutation == "attempt":
        recovery["recovery"]["attempt"] = 1
    elif mutation == "count":
        report["capture_attempts"] = 0
    else:
        intervening = copy.deepcopy(recovery)
        intervening["phase"] = "sample"
        intervening.pop("recovery")
        intervening["monotonic_seconds"] = (report["gaps"][0]["monotonic_seconds"] + recovery["monotonic_seconds"]) / 2
        events.insert(events.index(recovery), intervening)
    for index, event in enumerate(events):
        event["sequence"] = index
    raw = b"".join(bounds.encoded(event) for event in events)
    (root / "observation/events.jsonl").write_bytes(raw)
    report["event_count"], report["journal_sha256"] = len(events), bounds.sha(raw)
    (root / "observation/report.json").write_bytes(bounds.encoded(report))
    with pytest.raises(ValueError, match="recovery|capture count"):
        recorder.read_report(root / "observation")


def test_an_unacknowledged_gap_is_preserved_as_incomplete_evidence(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    report, _, _ = real_collision(root, monkeypatch)
    events = report.pop("events")
    event = next(e for e in events if e["phase"] == "recovery")
    event["phase"] = "sample"
    event.pop("recovery")
    raw = b"".join(bounds.encoded(event) for event in events)
    (root / "observation/events.jsonl").write_bytes(raw)
    report["journal_sha256"] = bounds.sha(raw)
    (root / "observation/report.json").write_bytes(bounds.encoded(report))
    reread = recorder.read_report(root / "observation")
    assert reread["gaps"] == report["gaps"] and not recorder.gaps_acknowledged(reread)
    assert not score._observation_qualified(reread["before"], reread["after"], reread)


def test_recovery_policy_is_frozen_in_the_packet(tmp_path):
    root = (tmp_path / "packet").resolve()
    protocol = fixture.prepare_packet(root)
    assert protocol["observer_recovery"] == recorder.recovery_policy()
    assert protocol["observer_recovery"]["paths"] == fixture.OUTPUTS
    protocol["observer_recovery"]["max_capture_attempts"] = 3
    (root / "protocol.json").write_bytes(bounds.encoded(protocol))
    (root / "freeze.json").write_bytes(bounds.encoded({"protocol_sha256": bounds.sha(bounds.encoded(protocol))}))
    with pytest.raises(ValueError, match="recovery policy"):
        fixture.verify_packet(root)
