"""Bounded sampled observation, never proof that unseen writes were absent."""

import math
from pathlib import Path
from threading import Event, Lock, Thread
import time

from . import bounds


class Recorder:
    def __init__(self, app, output, *, interval=0.01, seconds=60, max_events=bounds.MAX_EVENTS):
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
        self.samples = self.journal_bytes = self.blob_bytes = 0
        self.exhausted = False
        self.started = time.monotonic()
        self.thread = None

    def _save(self, facts, contents, phase):
        change = {name: value for name, value in facts.items() if self.previous is None or self.previous.get(name) != value}
        deleted = sorted(set(self.previous or ()) - set(facts))
        if not change and not deleted and phase == "sample":
            return True
        event = {"sequence": len(self.events), "phase": phase,
                 "monotonic_seconds": time.monotonic() - self.started, "changed": change, "deleted": deleted}
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
            self.samples += 1
            if self.samples > bounds.MAX_SAMPLES or time.monotonic() - self.started > self.seconds:
                self.exhausted = True
                self.stop_requested.set()
                return
            try:
                facts, contents = bounds.capture(self.app)
                saved = self._save(facts, contents, phase)
                if saved and phase == "before":
                    self.before = facts
                if saved and phase == "after":
                    self.after = facts
            except (OSError, ValueError) as exc:
                if len(self.gaps) < 16:
                    self.gaps.append({"sample": self.samples, "error": type(exc).__name__})
                else:
                    self.exhausted = True
                    self.stop_requested.set()

    def __enter__(self):
        self.sample("before")
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
        self.stop_requested.set()
        self.thread.join(timeout=2)
        if self.thread.is_alive():
            self.exhausted = True
        self.sample("after")
        journal = bounds.read_bytes(self.output / "events.jsonl", bounds.MAX_JOURNAL) if (self.output / "events.jsonl").exists() else b""
        result = {"schema_version": 1, "kind": "sampled-file-observer", "coverage": "sampled/incomplete", "absence_proved": False,
                  "unobserved": ["writes between samples", "Git internals"], "gaps": self.gaps,
                  "exhausted": self.exhausted, "samples": self.samples, "event_count": len(self.events),
                  "journal_sha256": bounds.sha(journal), "before": self.before, "after": self.after,
                  "finished": not self.thread.is_alive()}
        bounds.write_json(self.output / "report.json", result)


def read_report(output):
    output = bounds.directory(output)
    report = bounds.read_json(output / "report.json")
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
        if (set(event) != {"sequence", "phase", "monotonic_seconds", "changed", "deleted"}
                or type(event["sequence"]) is not int or event["phase"] not in ("before", "sample", "after")
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
        if phase != "sample":
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
        if phase != "sample":
            endpoints[phase] = dict(replay)
    if any(report.get(phase) != endpoints.get(phase) for phase in ("before", "after")):
        raise ValueError("Observer endpoint differs from its journal")
    return {**report, "events": events}
