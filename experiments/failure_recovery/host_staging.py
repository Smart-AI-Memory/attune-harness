"""Passive POSIX host-rename intent and subsequent native-effect lineage checks."""

import copy
import marshal
import math
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import time

from attune_harness import repair, work_effects
from attune_harness.review_contract import digest
from attune_harness.task_contract import read_task

from . import bounds

PATHS = ("src/report.py", "tests/generated/test_report_extra.py")
MAX_INTENTS = 16
ORIGINAL_REPAIR = repair.replace_file
ORIGINAL_CODE = ORIGINAL_REPAIR.__code__
ORIGIN_PATH = Path(repair.__file__).resolve()
ORIGIN_SHA = bounds.sha(bounds.read_bytes(ORIGIN_PATH, bounds.MAX_RETAINED_FILE))
CODE_SHA = bounds.sha(marshal.dumps(ORIGINAL_CODE))
_ACTIVE = None
_INSTALLED = False


def policy():
    return {"id": "native-replacement-lineage-v2", "backend": "cpython-posix-os.rename-audit",
            "max_intents": MAX_INTENTS, "paths": list(PATHS), "metadata_permission_added": False,
            "intent_is_completion": False, "unknown_content_reconstructed": False,
            "intent_window": "enumeration_started<=intent<=missing_leaf",
            "exclusive_gap_cause_proved": False, "path_incarnation_history": "unknown",
            "missing_contents": "unknown", "recovered": "snapshot usability only",
            "max_report_bytes": bounds.MAX_EVIDENCE}


def identity(value):
    return {"device": value.st_dev, "inode": value.st_ino, "mode": value.st_mode}


def _audit(event, args):
    """Never propagate an observer exception into the owner's operation."""
    sensor = _ACTIVE
    if sensor is None:
        return
    frame = None
    try:
        if event == "attune.failure_recovery.audit_probe":
            if args == (sensor.probe,):
                sensor.registered = True
        elif event == "os.rename":
            frame = sys._getframe(1)
            sensor.record(args, frame)
    except BaseException:
        try:
            sensor.failed = True
        except BaseException:
            pass
    finally:
        del frame


class Sensor:
    def __init__(self, app, plan, started):
        self.app, self.plan = app, None
        self.started = started
        self.intents, self.parents = [], {}
        self.failed = self.overflow = self.registered = False
        self.supported = os.name == "posix" and sys.implementation.name == "cpython"
        self.probe = object()
        self.limit = MAX_INTENTS
        self.manifest = None
        try:
            if not self.supported or plan is None:
                return
            self.plan = copy.deepcopy(plan)
            if (len(bounds.encoded(self.plan)) > bounds.MAX_EVIDENCE or self.plan["profile"] != work_effects.PROFILE
                    or self.plan["root"] != str(app) or self.plan["allowed"] != list(PATHS)
                    or repair.replace_file is not ORIGINAL_REPAIR or ORIGINAL_REPAIR.__code__ is not ORIGINAL_CODE):
                raise ValueError("Unsupported accepted effect plan")
            work_effects.validate_manifest(self.plan)
            self.manifest = digest(self.plan)
            with repair.root_handle(self.plan) as root:
                for path in PATHS:
                    with repair.parent_handle(root, path) as (parent, _):
                        value = os.fstat(parent)
                        if not stat.S_ISDIR(value.st_mode):
                            raise ValueError("Expected a parent directory")
                        self.parents[path] = identity(value)
        except BaseException:
            self.failed = True

    def activate(self):
        global _ACTIVE, _INSTALLED
        try:
            if not self.supported or self.plan is None or self.failed:
                return
            if repair.replace_file is not ORIGINAL_REPAIR or ORIGINAL_REPAIR.__code__ is not ORIGINAL_CODE:
                raise ValueError("Native replacement code changed")
            if _ACTIVE is not None:
                raise ValueError("A host sensor is already active")
            _ACTIVE = self
            if not _INSTALLED:
                sys.addaudithook(_audit)
                _INSTALLED = True
            sys.audit("attune.failure_recovery.audit_probe", self.probe)
            if not self.registered:
                self.failed = True
        except BaseException:
            self.failed = True

    def deactivate(self):
        global _ACTIVE
        if _ACTIVE is self:
            _ACTIVE = None

    def record(self, args, frame):
        if frame.f_code is not ORIGINAL_CODE:
            return
        values = frame.f_locals
        plan, item = values["plan"], values["item"]
        if plan.get("root") != str(self.app):
            return
        if self.failed or self.overflow:
            return
        if len(self.intents) >= self.limit:
            self.overflow = True
            return
        source, destination, source_fd, destination_fd = args
        target = item["path"]
        if any(intent["target"] == target for intent in self.intents):
            raise ValueError("Native replacement intent is duplicated")
        if (repair.replace_file is not ORIGINAL_REPAIR or ORIGINAL_REPAIR.__code__ is not ORIGINAL_CODE or target not in PATHS
                or digest(plan) != self.manifest or plan["profile"] != work_effects.PROFILE
                or set(item) != {"path", "before_sha256", "text"}
                or item["before_sha256"] != self.plan["before"][target]["sha256"]
                or type(source_fd) is not int or source_fd != destination_fd or source_fd != values["parent"]
                or not isinstance(source, str) or "/" in source or bounds.relative(source) != source
                or source != values["temporary"] or destination != values["leaf"]
                or destination != PurePosixPath(target).name
                or identity(os.fstat(source_fd)) != self.parents[target]
                or repair.identity(os.fstat(values["root"])) != self.plan["root_identity"]):
            raise ValueError("Rename did not match the accepted native replacement")
        raw = item["text"].encode("utf-8")
        if len(raw) > bounds.MAX_FILE or values["raw"] != raw:
            raise ValueError("Unbounded replacement input")
        prepared = os.stat(source, dir_fd=source_fd, follow_symlinks=False)
        if (not stat.S_ISREG(prepared.st_mode) or prepared.st_nlink != 1 or prepared.st_size != len(raw)
                or prepared.st_dev != self.parents[target]["device"] or stat.S_IMODE(prepared.st_mode) != values["mode"]):
            raise ValueError("Native staging source identity is unsupported")
        path = bounds.relative(str(PurePosixPath(target).parent / source))
        if path in PATHS or path in self.plan["protected"]:
            raise ValueError("Staging source overlaps a declared file")
        self.intents.append({"id": len(self.intents), "source": path, "target": target,
                             "monotonic_seconds": time.monotonic() - self.started, "parent_identity": dict(self.parents[target]),
                             "source_identity": identity(prepared),
                             "before_sha256": item["before_sha256"], "after_sha256": bounds.sha(raw),
                             "manifest_digest": self.manifest})

    def snapshot(self):
        return {"policy": policy(), "supported": self.supported, "registered": self.registered,
                "failed": self.failed, "overflow": self.overflow, "manifest_digest": self.manifest,
                "origin": {"path": str(ORIGIN_PATH), "sha256": ORIGIN_SHA, "code_sha256": CODE_SHA},
                "intents": copy.deepcopy(self.intents)}


def matching_intent(sensor, gap, *, require_healthy=True):
    if ((require_healthy and (not sensor.get("supported") or not sensor.get("registered")
                             or sensor.get("failed") or sensor.get("overflow"))) or sensor.get("policy") != policy()
            or gap.get("error") != "EnumeratedLeafMissing" or gap.get("phase") != "sample"
            or gap.get("attempt") != 1 or gap.get("reason") != "enumerated_leaf_missing"):
        return None
    witness = gap.get("enumeration", {})
    matches = [intent for intent in sensor["intents"]
               if intent["source"] == gap["path"]
               and intent["parent_identity"] == witness.get("parent_before") == witness.get("parent_after")
               and intent["source_identity"]["inode"] == witness.get("entry_inode")
               and witness.get("enumeration_started_seconds", float("inf")) <= witness.get("enumeration_finished_seconds", -1)
               <= witness.get("missing_seconds", -1)
               and witness.get("enumeration_started_seconds", float("inf")) <= intent["monotonic_seconds"]
               <= witness.get("missing_seconds", -1)]
    return matches[0] if len(matches) == 1 else None


def validate_enumeration(gap):
    witness = gap["enumeration"]
    if (not isinstance(witness, dict) or set(witness) != {"parent_before", "parent_after", "entry_inode", "enumeration_started_seconds",
                                                        "enumeration_finished_seconds", "missing_seconds"}
            or witness["parent_before"] != witness["parent_after"]
            or type(witness["entry_inode"]) is not int or witness["entry_inode"] < 0):
        raise ValueError("Invalid enumeration witness")
    parent = witness["parent_before"]
    if (not isinstance(parent, dict) or set(parent) != {"device", "inode", "mode"}
            or any(type(value) is not int or value < 0 for value in parent.values()) or not stat.S_ISDIR(parent["mode"])):
        raise ValueError("Invalid enumeration parent")
    times = [witness[key] for key in ("enumeration_started_seconds", "enumeration_finished_seconds", "missing_seconds")]
    if (any(type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= bounds.MAX_SECONDS for value in times)
            or times != sorted(times) or times[-1] > gap["monotonic_seconds"]):
        raise ValueError("Invalid enumeration time")


def validate_sensor(sensor):
    keys = {"policy", "supported", "registered", "failed", "overflow", "manifest_digest", "origin", "intents"}
    if (not isinstance(sensor, dict) or set(sensor) != keys or sensor["policy"] != policy()
            or any(type(sensor[key]) is not bool for key in ("supported", "registered", "failed", "overflow"))
            or not isinstance(sensor["intents"], list) or len(sensor["intents"]) > MAX_INTENTS
            or not isinstance(sensor["origin"], dict) or set(sensor["origin"]) != {"path", "sha256", "code_sha256"}
            or not isinstance(sensor["origin"]["path"], str) or len(sensor["origin"]["path"]) > 1000):
        raise ValueError("Invalid host rename sensor")
    sha = lambda value: isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    if (any(not sha(sensor["origin"][key]) for key in ("sha256", "code_sha256"))
            or (sensor["manifest_digest"] is not None and not sha(sensor["manifest_digest"]))):
        raise ValueError("Invalid host origin identity")
    previous, sources, targets = -1, set(), set()
    for index, intent in enumerate(sensor["intents"]):
        if (not isinstance(intent, dict) or set(intent) != {"id", "source", "target", "monotonic_seconds", "parent_identity", "source_identity",
                                                           "before_sha256", "after_sha256", "manifest_digest"}
                or type(intent["id"]) is not int or intent["id"] != index or intent["target"] not in PATHS
                or any(not sha(intent[key]) for key in ("before_sha256", "after_sha256", "manifest_digest"))
                or intent["manifest_digest"] != sensor["manifest_digest"]):
            raise ValueError("Invalid host rename intent")
        bounds.relative(intent["source"])
        if (intent["source"] in PATHS or PurePosixPath(intent["source"]).parent != PurePosixPath(intent["target"]).parent
                or intent["source"] in sources or intent["target"] in targets):
            raise ValueError("Host rename intent is ambiguous")
        sources.add(intent["source"])
        targets.add(intent["target"])
        for key, predicate in (("parent_identity", stat.S_ISDIR), ("source_identity", stat.S_ISREG)):
            value = intent[key]
            if (not isinstance(value, dict) or set(value) != {"device", "inode", "mode"}
                    or any(type(item) is not int or item < 0 for item in value.values()) or not predicate(value["mode"])):
                raise ValueError("Invalid host file identity")
        if intent["source_identity"]["device"] != intent["parent_identity"]["device"]:
            raise ValueError("Native staging source is on a different device")
        timestamp = intent["monotonic_seconds"]
        if (type(timestamp) not in (float, int) or not math.isfinite(timestamp)
                or not 0 <= timestamp <= bounds.MAX_SECONDS or timestamp < previous):
            raise ValueError("Invalid host intent time")
        previous = timestamp


def lineage_qualified(report, owner_sha, owner_path):
    needed = {e["recovery"]["gap_id"] for e in report.get("events", [])
              if "host_intent_id" in e.get("recovery", {})}
    if not needed:
        return True
    evidence = report.get("host_staging", {})
    if (not isinstance(evidence, dict) or set(evidence) != {"owner_record_sha256", "record_path", "bindings", "unknown"}
            or owner_sha is None or owner_path is None or evidence["owner_record_sha256"] != owner_sha
            or evidence["record_path"] != owner_path or evidence["unknown"] != []
            or not isinstance(evidence["bindings"], list) or len(evidence["bindings"]) != len(needed)):
        return False
    try:
        path = Path(owner_path)
        if not path.is_absolute() or path.name != "record.json":
            return False
        actual = read_task(path.parent)
        if bounds.sha(bounds.encoded(actual)) != owner_sha or actual["record_path"] != owner_path:
            return False
        recomputed = bind_host_staging(report, actual, Path(actual["request"]["effects"]["root"]))["host_staging"]
        return (recomputed == evidence and recomputed["unknown"] == []
                and {binding["gap_id"] for binding in recomputed["bindings"]} == needed
                and all(report["after"].get(binding["target"], {}).get("sha256") == binding["after_sha256"]
                        for binding in recomputed["bindings"]))
    except Exception:
        return False


def bind_host_staging(report, owner_record, app):
    """Return new evidence; an intent or a caller-supplied flag cannot complete it."""
    result = copy.deepcopy(report)
    sensor = report.get("host_sensor", {})
    lineage = {"owner_record_sha256": bounds.sha(bounds.encoded(owner_record)), "record_path": owner_record.get("record_path"),
               "bindings": [], "unknown": []}
    result["host_staging"] = lineage
    needed = [e for e in report.get("events", []) if e.get("recovery", {}).get("host_intent_id") is not None]
    try:
        if owner_record != read_task(Path(owner_record["record_path"]).parent):
            raise ValueError("Owner record differs from its native validated record")
        native_record = True
    except Exception:
        native_record = False
    for acknowledgement in needed:
        ack = acknowledgement["recovery"]
        try:
            gap = report["gaps"][ack["gap_id"]]
            intent = matching_intent(sensor, gap)
            if not native_record or intent is None or intent["id"] != ack["host_intent_id"]:
                raise ValueError("No unique native rename intent")
            plan = owner_record["request"]["effects"]
            if (digest(plan) != intent["manifest_digest"] or plan["root"] != str(app)
                    or repair.replace_file is not ORIGINAL_REPAIR or ORIGINAL_REPAIR.__code__ is not ORIGINAL_CODE
                    or bounds.sha(bounds.read_bytes(ORIGIN_PATH, bounds.MAX_RETAINED_FILE)) != ORIGIN_SHA
                    or sensor["origin"] != {"path": str(ORIGIN_PATH), "sha256": ORIGIN_SHA, "code_sha256": CODE_SHA}):
                raise ValueError("Native owner origin or accepted plan changed")
            matches = [event for event in owner_record["build"]["events"]
                       if event.get("kind") == "file_effect" and event.get("item", {}).get("path") == intent["target"]]
            if len(matches) != 1:
                raise ValueError("Replacement completion is missing or duplicated")
            event = matches[0]
            item, origin = event["item"], event["runtime_origin"]
            origins = [module for module in origin["modules"] if module["name"] == "attune_harness.repair"]
            expected = {"path": intent["target"], "entry": {"sha256": intent["after_sha256"],
                        "mode": plan["before"][intent["target"]]["mode"]}}
            if (event["state"] != "completed" or event["phase"] != "completed"
                    or event["attempts"] != 1 or origin["attempt"] != 1
                    or event["effect_class"] != "file_replacement" or item["kind"] != "replacement"
                    or event["operation_key"] != "effect:" + intent["target"]
                    or event["manifest_digest"] != intent["manifest_digest"]
                    or item["before_sha256"] != intent["before_sha256"]
                    or bounds.sha(item["text"].encode("utf-8")) != intent["after_sha256"]
                    or event["result"] != expected
                    or origins != [{"name": "attune_harness.repair", "path": str(ORIGIN_PATH), "sha256": ORIGIN_SHA}]
                    or intent["source"] in report["before"] or intent["source"] in report["after"]):
                raise ValueError("Native completion does not establish staging lineage")
            with repair.root_handle(plan) as root:
                with repair.parent_handle(root, intent["target"]) as (parent, leaf):
                    if identity(os.fstat(parent)) != intent["parent_identity"]:
                        raise ValueError("Native replacement parent identity changed")
                    try:
                        os.stat(PurePosixPath(intent["source"]).name, dir_fd=parent, follow_symlinks=False)
                    except FileNotFoundError:
                        pass
                    else:
                        raise ValueError("Native staging source survives")
                    final, mode = repair.read_file(parent, leaf, limit=bounds.MAX_FILE)
                    if (bounds.sha(final) != intent["after_sha256"] or mode != expected["entry"]["mode"]
                            or identity(os.stat(leaf, dir_fd=parent, follow_symlinks=False)) != intent["source_identity"]
                            or identity(os.fstat(parent)) != intent["parent_identity"]):
                        raise ValueError("Native replacement after-image changed")
            lineage["bindings"].append({"gap_id": gap["id"], "intent_id": intent["id"],
                                         "event_id": event["event_id"], "target": intent["target"],
                                         "source": intent["source"], "after_sha256": intent["after_sha256"]})
        except (KeyError, TypeError, ValueError, OSError) as exc:
            lineage["unknown"].append({"gap_id": ack.get("gap_id"), "error": type(exc).__name__})
    return result
