"""Bounded sampled observation, never proof that unseen writes were absent."""

import math
from pathlib import Path
from threading import Event, Lock, Thread
import time

from . import bounds, host_staging

RECOVERY_PATHS = ("src/report.py", "tests/generated/test_report_extra.py")
MAX_CAPTURE_ATTEMPTS = 2
MAX_GAPS = 16


def recovery_policy():
    return {"id": "sampled-read-recovery-v2", "paths": list(RECOVERY_PATHS),
            "phase": "sample", "max_capture_attempts": MAX_CAPTURE_ATTEMPTS, "max_gaps": MAX_GAPS,
            "host_staging": host_staging.policy()}


def _acknowledged_gaps(report, events):
    """Validate acknowledgements without turning a later sample into lost history."""
    if report.get("schema_version") != 3 or report.get("recovery_policy") != recovery_policy():
        raise ValueError("Unknown observer recovery policy")
    host_staging.validate_sensor(report["host_sensor"])
    samples, attempts = report.get("samples"), report.get("capture_attempts")
    if (type(samples) is not int or not 1 <= samples <= bounds.MAX_SAMPLES + 1
            or type(attempts) is not int or not samples - 1 <= attempts <= MAX_CAPTURE_ATTEMPTS * min(samples, bounds.MAX_SAMPLES)):
        raise ValueError("Invalid observer capture count")
    gaps = report.get("gaps")
    if not isinstance(gaps, list) or len(gaps) > MAX_GAPS:
        raise ValueError("Invalid observer gaps")
    last_gap_time = -1
    for index, gap in enumerate(gaps):
        expected = {"id", "sample", "attempt", "phase", "path", "reason", "error", "monotonic_seconds"}
        if isinstance(gap, dict) and gap.get("error") == "EnumeratedLeafMissing":
            expected.add("enumeration")
        if (not isinstance(gap, dict)
                or set(gap) != expected
                or type(gap["id"]) is not int or gap["id"] != index
                or type(gap["sample"]) is not int or not 1 <= gap["sample"] <= min(samples, bounds.MAX_SAMPLES)
                or type(gap["attempt"]) is not int or gap["attempt"] not in (1, 2)
                or gap["phase"] not in ("before", "sample", "after")
                or any(not isinstance(gap[key], str) or not 1 <= len(gap[key]) <= 200 for key in ("reason", "error"))):
            raise ValueError("Invalid observer gap schema")
        if gap["path"] is not None:
            bounds.relative(gap["path"])
        timestamp = gap["monotonic_seconds"]
        if (type(timestamp) not in (int, float) or not math.isfinite(timestamp)
                or not 0 <= timestamp <= bounds.MAX_SECONDS or timestamp < last_gap_time):
            raise ValueError("Invalid observer gap time")
        last_gap_time = timestamp
        if "enumeration" in gap:
            host_staging.validate_enumeration(gap)
    acknowledged, replay = set(), {}
    previous_event_time = -1
    for event in events:
        for name in event["deleted"]:
            replay.pop(name, None)
        replay.update(event["changed"])
        if event["phase"] == "recovery":
            ack = event.get("recovery")
            expected = {"gap_id", "sample", "attempt", "snapshot_sha256"}
            if isinstance(ack, dict) and "host_intent_id" in ack:
                expected.add("host_intent_id")
            if (not isinstance(ack, dict) or set(ack) != expected
                    or type(ack["gap_id"]) is not int or not 0 <= ack["gap_id"] < len(gaps)
                    or ack["gap_id"] in acknowledged or type(ack["sample"]) is not int
                    or type(ack["attempt"]) is not int or ack["attempt"] != 2):
                raise ValueError("Invalid observer recovery acknowledgement")
            gap = gaps[ack["gap_id"]]
            atomic = (gap["path"] in RECOVERY_PATHS and gap["reason"] == "atomic_leaf_replacement"
                      and gap["error"] == "AtomicLeafReplacement" and "host_intent_id" not in ack
                      and replay.get(gap["path"], {}).get("kind") == "file")
            intent = host_staging.matching_intent(report["host_sensor"], gap, require_healthy=False)
            staging = (type(ack.get("host_intent_id")) is int and intent is not None
                       and intent["id"] == ack["host_intent_id"] and gap["path"] not in replay)
            if (gap["phase"] != "sample" or gap["attempt"] != 1 or not (atomic or staging)
                    or gap["sample"] != ack["sample"]
                    or not previous_event_time <= gap["monotonic_seconds"] <= event["monotonic_seconds"]
                    or any(other["sample"] == gap["sample"] and other["id"] != gap["id"] for other in gaps)
                    or ack["snapshot_sha256"] != bounds.sha(bounds.encoded(replay))):
                raise ValueError("Observer recovery does not bind an eligible failed read")
            acknowledged.add(ack["gap_id"])
        elif "recovery" in event:
            raise ValueError("Recovery acknowledgement needs its own snapshot event")
        previous_event_time = event["monotonic_seconds"]
    if attempts < len(events) + len(gaps):
        raise ValueError("Observer capture count omits retained samples or gaps")
    return acknowledged


def gaps_acknowledged(report, owner_sha=None, owner_path=None):
    try:
        return (_acknowledged_gaps(report, report.get("events", [])) == set(range(len(report["gaps"])))
                and host_staging.lineage_qualified(report, owner_sha, owner_path))
    except (KeyError, TypeError, ValueError):
        return False


class Recorder:
    def __init__(self, app, output, *, interval=0.01, seconds=60, max_events=bounds.MAX_EVENTS, effect_plan=None):
        if (not math.isfinite(interval) or not 0.001 <= interval <= 0.1
                or not math.isfinite(seconds) or not 0 < seconds <= bounds.MAX_SECONDS
                or type(max_events) is not int or not 1 <= max_events <= bounds.MAX_EVENTS):
            raise ValueError("Invalid observation bounds")
        self.app = bounds.directory(app)
        self.output = bounds.external_directory(output, app, create=True)
        (self.output / "blobs").mkdir()
        self.interval, self.seconds, self.max_events = interval, seconds, max_events
        self.stop_requested, self.lock = Event(), Lock()
        self.events, self.gaps = [], []
        self.previous = self.before = self.after = None
        self.samples = self.capture_attempts = self.journal_bytes = self.blob_bytes = 0
        self.exhausted = False
        self.started = time.monotonic()
        self.sensor = host_staging.Sensor(self.app, effect_plan, self.started)
        self.thread = None

    def _save(self, facts, contents, phase, recovery=None):
        change = {name: value for name, value in facts.items() if self.previous is None or self.previous.get(name) != value}
        deleted = sorted(set(self.previous or ()) - set(facts))
        if not change and not deleted and phase == "sample":
            return True
        event = {"sequence": len(self.events), "phase": phase,
                 "monotonic_seconds": time.monotonic() - self.started, "changed": change, "deleted": deleted}
        if recovery is not None:
            event["recovery"] = {**recovery, "snapshot_sha256": bounds.sha(bounds.encoded(facts))}
        line = bounds.encoded(event)
        pending = {value["sha256"]: contents[name] for name, value in change.items() if value["kind"] == "file"
                   and not (self.output / "blobs" / (value["sha256"] + ".bin")).exists()}
        if (len(self.events) >= self.max_events or self.journal_bytes + len(line) > bounds.MAX_JOURNAL
                or self.blob_bytes + sum(map(len, pending.values())) > bounds.MAX_BLOBS):
            self.exhausted = True
            self.stop_requested.set()
            return False
        for digest, data in pending.items():
            bounds.write_bytes(self.output / "blobs" / (digest + ".bin"), data)
            self.blob_bytes += len(data)
        with (self.output / "events.jsonl").open("ab") as stream:
            stream.write(line)
            stream.flush()
        self.journal_bytes += len(line)
        self.events.append(event)
        self.previous = facts
        return True

    def sample(self, phase="sample"):
        with self.lock:
            if self.exhausted:
                return
            self.samples += 1
            recovery = None
            for attempt in range(1, MAX_CAPTURE_ATTEMPTS + 1):
                if self.samples > bounds.MAX_SAMPLES or time.monotonic() - self.started > self.seconds:
                    self.exhausted = True
                    self.stop_requested.set()
                    return
                try:
                    self.capture_attempts += 1
                    facts, contents = bounds.capture(self.app)
                    saved = self._save(facts, contents, "recovery" if recovery else phase, recovery)
                    if saved and phase == "before":
                        self.before = facts
                    if saved and phase == "after":
                        self.after = facts
                    return
                except (OSError, ValueError) as exc:
                    path = exc.path if isinstance(exc, (bounds.AtomicLeafReplacement, bounds.CaptureError, bounds.EnumeratedLeafMissing)) else None
                    gap = {"id": len(self.gaps), "sample": self.samples, "attempt": attempt, "phase": phase,
                           "path": path, "reason": str(exc)[:200] or type(exc).__name__,
                           "error": exc.error if isinstance(exc, bounds.CaptureError) else type(exc).__name__,
                           "monotonic_seconds": time.monotonic() - self.started}
                    if isinstance(exc, bounds.EnumeratedLeafMissing):
                        gap["enumeration"] = {key: value - self.started if key.endswith("seconds") else value
                                              for key, value in exc.witness.items()}
                    self.gaps.append(gap)
                    if len(self.gaps) >= MAX_GAPS:
                        self.exhausted = True
                        self.stop_requested.set()
                        return
                    if (attempt == 1 and phase == "sample" and isinstance(exc, bounds.AtomicLeafReplacement)
                            and path in RECOVERY_PATHS):
                        recovery = {"gap_id": gap["id"], "sample": self.samples, "attempt": 2}
                        continue
                    if attempt == 1 and phase == "sample" and isinstance(exc, bounds.EnumeratedLeafMissing):
                        intent = host_staging.matching_intent(self.sensor.snapshot(), gap)
                        if intent is not None and path not in (self.before or {}):
                            recovery = {"gap_id": gap["id"], "sample": self.samples, "attempt": 2,
                                        "host_intent_id": intent["id"]}
                            continue
                    return

    def __enter__(self):
        self.sample("before")
        self.sensor.activate()
        def poll():
            while not self.stop_requested.wait(self.interval):
                self.sample()
        self.thread = Thread(target=poll, name="offline-file-observer", daemon=True)
        self.thread.start()
        return self

    def wait_for(self, name, digest, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self.lock:
                if any(e["changed"].get(name, {}).get("sha256") == digest for e in self.events):
                    return True
            if self.stop_requested.wait(0.005):
                break
        return False

    def __exit__(self, *_):
        self.sensor.deactivate()
        self.stop_requested.set()
        self.thread.join(timeout=2)
        if self.thread.is_alive():
            self.exhausted = True
        self.sample("after")
        journal = bounds.read_bytes(self.output / "events.jsonl", bounds.MAX_JOURNAL) if (self.output / "events.jsonl").exists() else b""
        result = {"schema_version": 3, "kind": "sampled-file-observer", "coverage": "sampled/incomplete", "absence_proved": False,
                  "unobserved": ["writes between samples", "Git internals"], "gaps": self.gaps,
                  "recovery_policy": recovery_policy(), "capture_attempts": self.capture_attempts,
                  "host_sensor": self.sensor.snapshot(),
                  "exhausted": self.exhausted, "samples": self.samples, "event_count": len(self.events),
                  "journal_sha256": bounds.sha(journal), "before": self.before, "after": self.after,
                  "finished": not self.thread.is_alive()}
        bounds.write_json(self.output / "report.json", result, maximum=bounds.MAX_EVIDENCE)


def read_report(output):
    output = bounds.directory(output)
    report = bounds.read_json(output / "report.json", bounds.MAX_EVIDENCE)
    journal = bounds.read_bytes(output / "events.jsonl", bounds.MAX_JOURNAL) if (output / "events.jsonl").exists() else b""
    if bounds.sha(journal) != report["journal_sha256"]:
        raise ValueError("Observer journal identity changed")
    events = [bounds.parse_json(line.decode("utf-8"), bounds.MAX_JOURNAL) for line in journal.splitlines()]
    if (len(events) != report["event_count"] or len(events) > bounds.MAX_EVENTS
            or [e["sequence"] for e in events] != list(range(len(events)))):
        raise ValueError("Observer sequence is missing or duplicated")
    replay = {}
    last_time = -1
    endpoints = {}
    for index, event in enumerate(events):
        expected = {"sequence", "phase", "monotonic_seconds", "changed", "deleted"}
        if event.get("phase") == "recovery":
            expected.add("recovery")
        if (set(event) != expected
                or type(event["sequence"]) is not int or event["phase"] not in ("before", "sample", "after", "recovery")
                or not isinstance(event["changed"], dict) or not isinstance(event["deleted"], list)
                or len(event["changed"]) > bounds.MAX_ENTRIES or len(event["deleted"]) > bounds.MAX_ENTRIES
                or len(set(event["deleted"])) != len(event["deleted"])
                or set(event["changed"]) & set(event["deleted"])):
            raise ValueError("Invalid observer event schema")
        timestamp = event["monotonic_seconds"]
        if (type(timestamp) not in (int, float) or not math.isfinite(timestamp)
                or not 0 <= timestamp <= bounds.MAX_SECONDS or timestamp < last_time):
            raise ValueError("Invalid observer time ordering")
        last_time = timestamp
        phase = event["phase"]
        if phase in ("before", "after"):
            if phase in endpoints or (phase == "before" and index != 0) or (phase == "after" and index != len(events) - 1):
                raise ValueError("Invalid observer endpoint ordering")
        for name in [*event["changed"], *event["deleted"]]:
            bounds.relative(name)
        for fact in event["changed"].values():
            if (not isinstance(fact, dict) or fact.get("kind") not in ("file", "directory")
                    or type(fact.get("mode")) is not int or not 0 <= fact["mode"] <= 0o7777
                    or set(fact) != ({"kind", "mode", "bytes", "sha256"} if fact["kind"] == "file" else {"kind", "mode"})):
                raise ValueError("Invalid observer file fact")
            if fact["kind"] == "file":
                digest = fact["sha256"]
                if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                    raise ValueError("Invalid observer blob identity")
                data = bounds.read_bytes(output / "blobs" / (digest + ".bin"))
                if bounds.sha(data) != digest:
                    raise ValueError("Observer blob changed")
                if type(fact["bytes"]) is not int or fact["bytes"] != len(data):
                    raise ValueError("Observer blob size changed")
        for name in event["deleted"]:
            if name not in replay:
                raise ValueError("Observer deleted an unknown path")
            del replay[name]
        replay.update(event["changed"])
        if len(replay) > bounds.MAX_ENTRIES:
            raise ValueError("Observer tree entry budget exhausted")
        if phase in ("before", "after"):
            endpoints[phase] = dict(replay)
    if any(report.get(phase) != endpoints.get(phase) for phase in ("before", "after")):
        raise ValueError("Observer endpoint differs from its journal")
    _acknowledged_gaps(report, events)
    return {**report, "events": events}
