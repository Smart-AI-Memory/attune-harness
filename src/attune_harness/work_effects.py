"""Bounded POSIX effects in a dedicated checkout, using the existing recovery log.

The caller is the trusted host. Checks are trusted programs, not a sandbox.
Concurrent writers and hostile programs are outside this exclusive-owner profile.
"""

import copy
import json
import os
from pathlib import Path, PurePosixPath

from . import repair
from .recovery import UnresolvedOperation, validate_events
from .review_contract import digest, fields, versioned

PROFILE = "posix-feature-effects-v1"
CONTROL_KEYS = ("id", "kind", "owner", "version")


def require_platform():
    from .features import FeatureUnavailable

    if os.name != "posix" or any(
        not hasattr(os, k) for k in ("O_NOFOLLOW", "O_DIRECTORY")
    ):
        raise FeatureUnavailable(
            "Build effects require the qualified POSIX handle profile"
        )


def identity(control):
    return {k: control[k] for k in CONTROL_KEYS}


def _paths(values, name, *, maximum=20):
    if (
        not isinstance(values, list)
        or len(values) > maximum
        or any(not isinstance(v, str) for v in values)
        or len(set(values)) != len(values)
    ):
        raise ValueError(f"Invalid {name} paths")
    for path in values:
        repair.relative(path)
        if any(p in repair.PROTECTED for p in PurePosixPath(path).parts):
            raise ValueError("Protected metadata cannot be an effect path")


def validate_manifest(plan):
    fields(
        plan,
        (
            "profile",
            "root",
            "root_identity",
            "allowed",
            "parents",
            "protected",
            "checks",
            "before",
            *(["verification"] if "verification" in plan else []),
        ),
    )
    if plan["profile"] != PROFILE or not Path(plan["root"]).is_absolute():
        raise ValueError("Unsupported build effect profile")
    fields(plan["root_identity"], ("device", "inode"))
    for name in ("allowed", "parents", "protected"):
        _paths(plan[name], name)
    if not plan["allowed"] or not plan["protected"]:
        raise ValueError(
            "Effects require explicit files and protected acceptance inputs"
        )
    if set(plan["allowed"]) & set(plan["protected"]):
        raise ValueError("Protected acceptance inputs cannot be edited")
    before = plan["before"]
    if not isinstance(before, dict) or len(before) > 1000:
        raise ValueError("Invalid effect snapshot")
    for path, value in before.items():
        repair.relative(path.rstrip("/"))
        fields(value, ("kind", "mode") if path.endswith("/") else ("sha256", "mode"))
        if type(value["mode"]) is not int or not 0 <= value["mode"] <= 0o7777:
            raise ValueError("Invalid snapshot mode")
        if path.endswith("/"):
            if value["kind"] != "directory":
                raise ValueError("Invalid directory snapshot")
        else:
            from .work_contract import _sha

            _sha(value["sha256"])
    needed = set()
    for path in plan["allowed"]:
        if path + "/" in before:
            raise ValueError("A directory cannot be a file target")
        for parent in PurePosixPath(path).parents:
            if str(parent) == ".":
                continue
            name = str(parent)
            if name in before or name in plan["allowed"]:
                raise ValueError("File target conflicts with a parent directory")
            if name + "/" not in before:
                needed.add(name)
    if set(plan["parents"]) != needed:
        raise ValueError("Missing parents must be explicitly and exactly authorized")
    for path in plan["protected"]:
        if path not in before:
            raise ValueError("Protected acceptance inputs must already exist")
    if not isinstance(plan["checks"], list) or len(plan["checks"]) > 32:
        raise ValueError("Invalid control runners")
    seen = set()
    for check in plan["checks"]:
        fields(check, ("control", "probe", "executable_sha256"))
        fields(check["control"], CONTROL_KEYS)
        from .work_contract import _sha, _validate_controls

        _validate_controls(
            [{**check["control"], "required": True, "phases": ["build"]}]
        )
        if (
            check["control"]["kind"] not in ("hook", "check")
            or check["control"]["id"] in seen
        ):
            raise ValueError("Only distinct trusted hook/check runners are supported")
        seen.add(check["control"]["id"])
        # Structural validation does not refresh historical executable identities.
        _sha(check["executable_sha256"])
        repair.validate_probe(
            Path(plan["root"]), plan["allowed"], check["probe"], check_executable=False
        )
        if set(check["probe"]["oracle_paths"]) - set(plan["protected"]):
            raise ValueError("Check inputs must be protected from worker edits")

    verification_probes(plan)


def verification_probes(plan):
    checks = plan.get("verification", [])
    if not isinstance(checks, list) or len(checks) > 33:
        raise ValueError("Invalid build verification probes")
    seen = set()
    for check in checks:
        fields(check, ("task_id", "probe", "executable_sha256"))
        from .work_contract import _identifier, _sha

        _identifier(check["task_id"])
        _sha(check["executable_sha256"])
        if check["task_id"] in seen:
            raise ValueError("Duplicate task verification")
        seen.add(check["task_id"])
        repair.validate_probe(
            Path(plan["root"]), plan["allowed"], check["probe"], check_executable=False
        )
        if set(check["probe"]["oracle_paths"]) - set(plan["protected"]):
            raise ValueError("Verification inputs must be protected")
    return {c["task_id"]: c for c in checks}


def freeze(
    root, allowed, parents, protected, checks, state_directory, *, verification=()
):
    """Prepare an effect manifest before accepting the containing work revision."""
    root, state = Path(root).absolute(), Path(state_directory).resolve()
    if state.is_relative_to(root) or root.is_relative_to(state):
        raise ValueError("Effect checkout and task state must be disjoint")
    if not (root / ".git").is_dir() or (root / ".git").is_symlink():
        raise ValueError("Build effects require a dedicated local Git checkout")
    plan = dict(
        profile=PROFILE,
        root=str(root),
        root_identity=repair.identity(root.stat()),
        allowed=copy.deepcopy(allowed),
        parents=copy.deepcopy(parents),
        protected=copy.deepcopy(protected),
        checks=[],
        before={},
    )
    plan["before"] = repair.snapshot(plan)
    for check in checks:
        fields(check, ("control", "probe"))
        repair.validate_probe(root, allowed, check["probe"])
        plan["checks"].append(
            {
                **copy.deepcopy(check),
                "executable_sha256": repair.sha(
                    Path(check["probe"]["argv"][0]).read_bytes()
                ),
            }
        )
    if verification:
        plan["verification"] = []
        for check in verification:
            fields(check, ("task_id", "probe"))
            repair.validate_probe(root, allowed, check["probe"])
            plan["verification"].append(
                {
                    **copy.deepcopy(check),
                    "executable_sha256": repair.sha(
                        Path(check["probe"]["argv"][0]).read_bytes()
                    ),
                }
            )
    validate_manifest(plan)
    with repair.root_handle(plan) as fd:
        for name in allowed:
            if name in plan["before"]:
                with repair.parent_handle(fd, name) as (parent, leaf):
                    raw, _ = repair.read_file(parent, leaf, limit=repair.MAX_FILE)
                    raw.decode("utf-8")
    return plan


def validate_request_effects(request):
    plan = request.get("effects")
    if plan is None:
        return
    validate_manifest(plan)
    if plan["root"] != request["project_root"] or set(plan["allowed"]) - set(
        request["intent"]["scope"]
    ):
        raise ValueError("Effects exceed the accepted project or intent scope")
    artifact = request["artifact"]
    if artifact is not None and artifact not in plan["protected"]:
        raise ValueError("Authoring artifact must be a protected acceptance input")
    for path, sha in request["evidence"].items():
        if plan["before"].get(path, {}).get("sha256") != sha:
            raise ValueError("Effect preimages disagree with work evidence")
    controls = [c for c in request["controls"] if "build" in c["phases"]]
    for check in plan["checks"]:
        if check["control"] not in [identity(c) for c in controls]:
            raise ValueError("Runner is not bound to a declared build control")


def control_runners(request):
    """Availability is checked for every required control before any command."""
    checks = request["effects"]["checks"]
    active, advisory = [], []
    for control in request["controls"]:
        if control == {
            "id": "spec-approval",
            "kind": "human",
            "owner": "spec",
            "version": 1,
            "required": True,
            "phases": ["accept"],
        }:
            continue  # Work acceptance validates its retained actual collector receipt.
        if control["required"] and set(control["phases"]) - {"build"}:
            raise ValueError(
                "Required planning/acceptance control execution is not qualified here"
            )
        if "build" not in control["phases"]:
            continue
        runner = next((c for c in checks if c["control"] == identity(control)), None)
        if runner is None:
            if control["required"]:
                raise ValueError("Required build control has no qualified runner")
            advisory.append({"id": control["id"], "status": "unavailable"})
        else:
            active.append((control, runner))
    return active, advisory


def decode_proposal(proposal, plan):
    # Apply the established parser's finite-size and duplicate-key constraints.
    proposal = repair.parse_json(json.dumps(proposal), 1048576)
    fields(proposal, ("schema_version", "files"))
    versioned(proposal)
    files, seen = proposal["files"], set()
    if not isinstance(files, list) or not 1 <= len(files) <= 20:
        raise ValueError("Effect proposal needs 1–20 files")
    for item in files:
        fields(item, ("path", "before_sha256", "text"))
        path = repair.relative(item["path"])
        if path not in plan["allowed"] or path in seen:
            raise ValueError("Effect proposal exceeds accepted file scope")
        seen.add(path)
        before = plan["before"].get(path, {}).get("sha256")
        if item["before_sha256"] != before:
            raise ValueError("Effect proposal has a stale preimage")
        if (
            not isinstance(item["text"], str)
            or len(item["text"].encode("utf-8")) > repair.MAX_FILE
        ):
            raise ValueError("Effect file exceeds the UTF-8 byte limit")
        if repair.sha(item["text"].encode("utf-8")) == before:
            raise ValueError("Effect proposal contains an unchanged file")
    return proposal


def operations(plan, proposal):
    files = decode_proposal(proposal, plan)["files"]
    needed = {str(p) for f in files for p in PurePosixPath(f["path"]).parents}
    parents = sorted(set(plan["parents"]) & needed, key=lambda p: (p.count("/"), p))
    return [{"kind": "directory", "path": p} for p in parents] + [
        {"kind": "replacement" if f["path"] in plan["before"] else "creation", **f}
        for f in files
    ]


def after_entry(plan, item):
    if item["kind"] == "directory":
        return item["path"] + "/", {"kind": "directory", "mode": 0o755}
    return item["path"], {
        "sha256": repair.sha(item["text"].encode("utf-8")),
        "mode": plan["before"].get(item["path"], {}).get("mode", 0o644),
    }


def expected_snapshot(plan, events):
    expected = copy.deepcopy(plan["before"])
    for event in events:
        if event["kind"] == "file_effect" and event["state"] == "completed":
            key, value = after_entry(plan, event["item"])
            expected[key] = value
    return expected


def validate_probe_result(result, plan, artifact):
    """A completed command receipt must agree with its actual process outcome."""
    fields(
        result,
        (
            "argv",
            "returncode",
            "stdout",
            "stderr",
            "failure",
            "passed",
            "plan_digest",
            "artifact_digest",
            "isolation",
        ),
    )
    if (
        result["argv"] != plan["probe"]["argv"]
        or result["plan_digest"] != digest(plan)
        or result["artifact_digest"] != artifact
        or type(result["passed"]) is not bool
        or (result["returncode"] is not None and type(result["returncode"]) is not int)
        or result["passed"] != (result["returncode"] == 0 and result["failure"] is None)
        or any(not isinstance(result[k], str) for k in ("stdout", "stderr"))
    ):
        raise ValueError("Control result does not match its accepted invocation")


def write_effect(plan, item):
    """No collision overwrite on creation; replacement reuses the qualified owner."""
    if item["kind"] == "replacement":
        repair.replace_file(
            plan, {k: item[k] for k in ("path", "before_sha256", "text")}
        )
    else:
        with repair.root_handle(plan) as root:
            with repair.parent_handle(root, item["path"]) as (parent, leaf):
                if item["kind"] == "directory":
                    os.mkdir(leaf, mode=0o755, dir_fd=parent)
                    fd = os.open(
                        leaf,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        dir_fd=parent,
                    )
                else:
                    fd = os.open(
                        leaf,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                        0o600,
                        dir_fd=parent,
                    )
                try:
                    if item["kind"] != "directory":
                        raw = memoryview(item["text"].encode("utf-8"))
                        while raw:
                            size = os.write(fd, raw)
                            if size <= 0:
                                raise OSError("Creation made no write progress")
                            raw = raw[size:]
                    os.fchmod(fd, 0o755 if item["kind"] == "directory" else 0o644)
                    os.fsync(fd)
                finally:
                    os.close(fd)
                os.fsync(parent)
    key, value = after_entry(plan, item)
    return {"path": key, "entry": value}


def apply_effects(request, proposal, cursor, *, ensure_current=lambda: None):
    plan = request["effects"]
    require_platform()
    validate_request_effects(request)
    ops = operations(plan, proposal)  # Validate every file before the first effect.
    runners, advisory = control_runners(request)
    if len(ops) + len(runners) > request["budgets"]["max_operations"]:
        raise ValueError("Effect batch exceeds the accepted operation budget")
    if any(e["phase"] == "dispatching" for e in cursor.record["events"]):
        raise UnresolvedOperation(
            "Uncertain operation requires explicit reconciliation"
        )
    advisory = run_controls(request, cursor, ensure_current=ensure_current)
    for item in ops:
        ensure_current()
        repair.assert_snapshot(plan, expected_snapshot(plan, cursor.record["events"]))
        cursor.perform(
            "effect:" + item["path"],
            "file_effect",
            lambda item=item: write_effect(plan, item),
            effect_class="file_" + item["kind"],
            item=item,
            manifest_digest=digest(plan),
        )
    ensure_current()
    repair.assert_snapshot(plan, expected_snapshot(plan, cursor.record["events"]))
    return advisory


def run_controls(request, cursor, *, ensure_current=lambda: None):
    """Execute/reuse this batch's bound controls before governed operations."""
    plan = request["effects"]
    runners, advisory = control_runners(request)
    expected = expected_snapshot(plan, cursor.record["events"])
    repair.assert_snapshot(plan, expected)
    for control, runner in runners:
        ensure_current()
        repair.validate_probe(Path(plan["root"]), plan["allowed"], runner["probe"])
        if (
            repair.sha(Path(runner["probe"]["argv"][0]).read_bytes())
            != runner["executable_sha256"]
        ):
            raise ValueError("Accepted control executable changed")
        probe_plan = {**plan, **{k: runner[k] for k in ("probe", "executable_sha256")}}
        result = cursor.perform(
            "control:" + control["id"],
            "build_control",
            lambda p=probe_plan: repair.run_probe(p, expected),
            effect_class="unknown",
            runner=runner,
            manifest_digest=digest(plan),
        )
        if not result["passed"]:
            if control["required"] or result["failure"] not in (None, "nonzero_exit"):
                raise UnresolvedOperation(
                    "Build control failed or has uncertain effects"
                )
            advisory.append({"id": control["id"], "status": "failed", "result": result})
    return advisory


def validate_journal(run, request):
    fields(
        run, ("profile", "request_digest", "proposal", "events", "status", "advisory")
    )
    if (
        run["profile"] != PROFILE
        or run["request_digest"] != digest(request)
        or run["status"] not in ("running", "paused", "completed", "unresolved")
    ):
        raise ValueError("Effect journal does not match the accepted work")
    plan = request["effects"]
    ops = operations(plan, run["proposal"])
    runners, _ = control_runners(request)
    expected = [
        ("control:" + c["id"], "build_control", "unknown", {"runner": r})
        for c, r in runners
    ]
    expected += [
        ("effect:" + i["path"], "file_effect", "file_" + i["kind"], {"item": i})
        for i in ops
    ]
    validate_events(run, kinds=("build_control", "file_effect"))
    if len(run["events"]) > len(expected):
        raise ValueError("Unexpected effect operation")
    for index, event in enumerate(run["events"]):
        key, kind, effect, detail = expected[index]
        if any(
            event.get(k) != v
            for k, v in dict(
                operation_key=key,
                kind=kind,
                effect_class=effect,
                manifest_digest=digest(plan),
                **detail,
            ).items()
        ):
            raise ValueError("Effect operation was rebound or reordered")
        if event["state"] != "completed" and index != len(run["events"]) - 1:
            raise ValueError("Effect after an unresolved operation")
        if kind == "build_control" and event["state"] == "completed":
            result = event["result"]
            runner = detail["runner"]
            probe_plan = {
                **plan,
                **{k: runner[k] for k in ("probe", "executable_sha256")},
            }
            validate_probe_result(result, probe_plan, digest(plan["before"]))
            control = runners[index][0]
            if (
                not result["passed"]
                and (control["required"] or result["failure"] != "nonzero_exit")
                and (index != len(run["events"]) - 1 or run["status"] == "completed")
            ):
                raise ValueError("Effect completion cannot bypass a failed control")
        if kind == "file_effect" and event["state"] == "completed":
            path, entry = after_entry(plan, event["item"])
            if event["result"] != {"path": path, "entry": entry}:
                raise ValueError("Effect result does not match the proposed bytes")
    if run["status"] == "completed" and (
        len(run["events"]) != len(expected)
        or any(e["state"] != "completed" for e in run["events"])
    ):
        raise ValueError("Incomplete effect batch cannot claim completion")


def reconcile_effect(plan, events, event_id, *, retry_before=False):
    """Observe the whole checkout. Partial/colliding/foreign bytes stay unresolved."""
    event = next((e for e in events if e["event_id"] == event_id), None)
    if (
        event is None
        or event["kind"] != "file_effect"
        or event["phase"] != "dispatching"
    ):
        raise ValueError("Only an unresolved file effect can be reconciled here")
    before = expected_snapshot(plan, events)
    after = copy.deepcopy(before)
    path, entry = after_entry(plan, event["item"])
    after[path] = entry
    actual = repair.snapshot(plan)
    previous = copy.deepcopy(event)
    if actual == after:
        with repair.root_handle(plan) as root:
            with repair.parent_handle(root, event["item"]["path"]) as (parent, leaf):
                fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
                os.fsync(parent)
        event.update(
            state="completed", phase="completed", result={"path": path, "entry": entry}
        )
    elif actual == before and retry_before and event["attempts"] < 2:
        event.update(state="pending", phase="prepared", attempts=event["attempts"] + 1)
    else:
        raise UnresolvedOperation(
            "Unknown effect state or explicit bounded retry required"
        )
    event.pop("error", None)
    event.pop("effects", None)
    event.setdefault("reconciliations", []).append(
        {
            "previous": previous,
            "evidence": "operator-requested full checkout observation",
            "snapshot_digest": digest(actual),
            "retry_before": retry_before,
        }
    )
    return event
