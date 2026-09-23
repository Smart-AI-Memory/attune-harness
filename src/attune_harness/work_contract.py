"""Feature-work intent and host-owned authority; no dispatch or build effects.

The Spec bridge supplies already-collected decisions. This module checks their
binding, not the authenticity of an arbitrary caller or a model's assertions.
"""

import copy
import hashlib
import re
from pathlib import Path, PurePosixPath
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL

from .features import read_text
from .review_contract import bounded_text, digest, fields, versioned
from .review_store import RunStore, checkpoint_digest
from .task_contract import DEFAULT_BUDGETS, budgets, load_task_registry, safe_storage

PROFILE = "feature-work-v1"
ROLES = ("planner", "critic", "specialist", "worker", "reviewer")
SIGNALS = (
    "multi_session",
    "multi_pr",
    "design_ambiguity",
    "irreversible_choice",
    "premise_decision",
    "cold_handoff",
    "dependent_changes",
    "authorization_risk",
    "retained_data_risk",
    "compatibility_risk",
    "xml_consumer",
)
RECOVERY = {"profile": {"kind": PROFILE, "version": 1}}
INTENT_FIELDS = ("goal", "context", "scope", "constraints", "acceptance", "questions")
EDITABLE = (
    "intent",
    "signals",
    "choices",
    "assignments",
    "controls",
    "tasks",
    "inputs",
    "artifact",
    "budgets",
    "effects",
    "legacy",
)
EXTENSIONS = ("review_handoff",)


def _items(value, name, limit=64):
    if not isinstance(value, list) or len(value) > limit:
        raise ValueError(f"{name} must be a list of at most {limit} items")
    return value


def _texts(value, name):
    for item in _items(value, name):
        bounded_text(item, name)
    if len(value) != len(set(value)):
        raise ValueError(f"Duplicate {name}")


def _identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", value):
        raise ValueError("Invalid identifier")


def _path(value):
    bounded_text(value, "relative path", 512)
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or str(path) != value
        or value == "."
        or any(
            p in ("..", ".git", ".hg", ".svn", ".attune-harness") for p in path.parts
        )
        or "\\" in value
        or "\x00" in value
    ):
        raise ValueError("Expected a canonical relative file path outside metadata")
    return path


def select_authoring(signals: dict, *, choices: list, tasks: list) -> dict:
    """Choose by explicit work facts and consumer requirements, never file count."""
    fields(signals, (*SIGNALS, "existing_artifact"))
    if any(type(signals[key]) is not bool for key in SIGNALS):
        raise ValueError("Authoring signals require explicit booleans")
    if signals["existing_artifact"] not in (None, "prompt", "xml", "spec"):
        raise ValueError("Unknown existing artifact requirement")
    spec = [key for key in SIGNALS[:5] if signals[key]]
    if any(choice["selected"] is None for choice in choices):
        spec.append("unresolved_choice")
    xml = [key for key in SIGNALS[5:] if signals[key]]
    if any(task["dependencies"] for task in tasks):
        xml.append("task_dependencies")
    existing = signals["existing_artifact"]
    if spec or existing == "spec":
        return {
            "tier": "spec",
            "reasons": spec + (["existing_spec"] if existing == "spec" else []),
        }
    if xml or existing == "xml":
        return {
            "tier": "xml",
            "reasons": xml + (["existing_xml"] if existing == "xml" else []),
        }
    return {
        "tier": "prompt",
        "reasons": ["bounded_work_without_spec_or_xml_requirement"],
    }


def _validate_intent(intent):
    fields(intent, INTENT_FIELDS)
    if intent["goal"] is not None:
        bounded_text(intent["goal"], "goal")
    for key in ("context", "scope", "constraints", "acceptance"):
        _texts(intent[key], key)
    for path in intent["scope"]:
        _path(path)
    seen = set()
    for question in _items(intent["questions"], "questions", 16):
        fields(question, ("id", "question", "answer", "material"))
        _identifier(question["id"])
        if question["id"] in seen or type(question["material"]) is not bool:
            raise ValueError("Duplicate question or nonboolean materiality")
        seen.add(question["id"])
        bounded_text(question["question"], "question")
        if question["answer"] is not None:
            bounded_text(question["answer"], "answer")


def _validate_choices(choices):
    seen = set()
    for choice in _items(choices, "choices", 16):
        fields(choice, ("id", "question", "options", "selected"))
        _identifier(choice["id"])
        if choice["id"] in seen:
            raise ValueError("Duplicate choice")
        seen.add(choice["id"])
        bounded_text(choice["question"], "choice question")
        options = set()
        if len(_items(choice["options"], "options", 8)) < 2:
            raise ValueError("A genuine choice requires at least two alternatives")
        for option in choice["options"]:
            fields(
                option,
                (
                    "id",
                    "proposal",
                    "rationale",
                    "evidence",
                    "uncertainty",
                    "counter_case",
                ),
            )
            _identifier(option["id"])
            if option["id"] in options:
                raise ValueError("Duplicate alternative")
            options.add(option["id"])
            for key in ("proposal", "rationale", "counter_case"):
                bounded_text(option[key], key)
            for key in ("evidence", "uncertainty"):
                _texts(option[key], key)
        if choice["selected"] is not None and choice["selected"] not in options:
            raise ValueError("Selected alternative is unknown")


def _validate_controls(controls):
    seen = set()
    for control in _items(controls, "controls", 32):
        fields(control, ("id", "kind", "owner", "version", "required", "phases"))
        _identifier(control["id"])
        bounded_text(control["owner"], "control owner", 256)
        if (
            control["id"] in seen
            or control["kind"] not in ("host", "hook", "check", "human", "guidance")
            or type(control["version"]) is not int
            or control["version"] < 1
            or type(control["required"]) is not bool
        ):
            raise ValueError("Invalid or duplicate control")
        seen.add(control["id"])
        _texts(control["phases"], "control phases")
        if not control["phases"] or set(control["phases"]) - {
            "plan",
            "build",
            "accept",
        }:
            raise ValueError("Unknown or empty control phases")


def response_contract(run):
    """Absent version retains the original journal's prompt and decoder."""
    version = run.get("response_contract", 1)
    if type(version) is not int or version not in (1, 2):
        raise ValueError("Unsupported response contract")
    return version


def _validate_tasks(tasks, scope):
    seen = set()
    for task in _items(tasks, "tasks", 32):
        fields(task, ("id", "objective", "dependencies", "outputs", "checks"))
        _identifier(task["id"])
        bounded_text(task["objective"], "task objective")
        for key in ("dependencies", "outputs", "checks"):
            _texts(task[key], key)
        if (
            task["id"] in seen
            or set(task["dependencies"]) - seen
            or not task["checks"]
            or set(task["outputs"]) - set(scope)
        ):
            raise ValueError(
                "Tasks need unique IDs, preceding dependencies, scoped outputs and checks"
            )
        seen.add(task["id"])


def _validate_request(request):
    fields(
        request,
        (
            "schema_version",
            "task_id",
            "revision",
            "project_root",
            *(k for k in EDITABLE if k not in ("effects", "legacy") or k in request),
            "registry",
            "config",
            "evidence",
            "authoring",
            *(k for k in EXTENSIONS if k in request),
        ),
    )
    versioned(request)
    if "legacy" in request:
        legacy = request["legacy"]
        fields(
            legacy,
            (
                "path",
                "source_sha256",
                "content_sha256",
                "content",
                "tasks",
                "unsupported",
                "approval_imported",
            ),
        )
        if (
            legacy["approval_imported"] is not False
            or not Path(legacy["path"]).is_absolute()
        ):
            raise ValueError("Imported plan cannot grant authority")
        _sha(legacy["source_sha256"])
        if (
            hashlib.sha256(legacy["content"].encode()).hexdigest()
            != legacy["content_sha256"]
        ):
            raise ValueError("Imported plan content binding differs")
    if str(UUID(request["task_id"])) != request["task_id"]:
        raise ValueError("Invalid work identity")
    if type(request["revision"]) is not int or not 1 <= request["revision"] <= 32:
        raise ValueError("Invalid work revision")
    if (
        not isinstance(request["project_root"], str)
        or not Path(request["project_root"]).is_absolute()
    ):
        raise ValueError("Project root must be absolute")
    _validate_intent(request["intent"])
    _validate_choices(request["choices"])
    _validate_controls(request["controls"])
    _validate_tasks(request["tasks"], request["intent"]["scope"])
    if request["authoring"] != select_authoring(
        request["signals"], choices=request["choices"], tasks=request["tasks"]
    ):
        raise ValueError("Authoring selection differs from work requirements")
    budgets(request["budgets"])
    fields(request["config"], ("path", "sha256"))
    if (
        not isinstance(request["config"]["path"], str)
        or not Path(request["config"]["path"]).is_absolute()
    ):
        raise ValueError("Configuration path must be absolute")
    _sha(request["config"]["sha256"])
    # The configured registry was validated on capture. Reading retained history
    # must not consult mutable external configuration or retrieval services.
    registry = request["registry"]
    fields(registry, ("schema_version", "participants"))
    versioned(registry)
    from .review_contract import validate_registry

    validate_registry(registry, Path(request["config"]["path"]), minimum_participants=1)
    roles = set()
    for assignment in _items(request["assignments"], "assignments", 5):
        fields(assignment, ("role", "participant", "output_contract", "budgets"))
        role = assignment["role"]
        if role not in ROLES or role in roles:
            raise ValueError("Unknown or duplicate assignment role")
        roles.add(role)
        if assignment["participant"] not in registry["participants"]:
            raise ValueError("Unknown assigned participant; no fallback")
        bounded_text(assignment["output_contract"], "output contract")
        selected_budget = budgets(assignment["budgets"])
        if any(v > request["budgets"][k] for k, v in selected_budget.items()):
            raise ValueError("Assignment budget exceeds the work budget")
    _texts(request["inputs"], "input paths")
    paths = list(request["inputs"])
    if request["artifact"] is not None:
        _path(request["artifact"])
        paths.append(request["artifact"])
    for path in paths:
        _path(path)
    fields(request["evidence"], set(paths))
    for value in request["evidence"].values():
        _sha(value)
    from .work_effects import validate_request_effects

    validate_request_effects(request)
    if "review_handoff" in request:
        from .work_review_handoff import validate_shape

        validate_shape(request["review_handoff"], request)


def _sha(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("Invalid SHA-256 identity")


def _capture(request, directory):
    root = Path(request["project_root"])
    if not root.is_dir() or root.resolve() != root:
        raise ValueError("Project must remain an existing resolved directory")
    if directory.is_relative_to(root) or root.is_relative_to(directory):
        raise ValueError("Feature-work state must be outside the project")
    paths = request["inputs"] + (
        [request["artifact"]] if request["artifact"] is not None else []
    )
    result = {}
    for name in paths:
        _path(name)
        path = root / name
        if (
            any(part.is_symlink() for part in (path, *path.parents))
            or not path.is_file()
        ):
            raise ValueError(
                "Work evidence must be regular files without symlink traversal"
            )
        raw = read_text(path, 65536)
        result[name] = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return result


def missing_information(request: dict) -> list:
    """Return only unsupplied material intent; optional uncertainty is retained."""
    intent = request["intent"]
    missing = [key for key in ("goal", "scope", "acceptance") if not intent[key]]
    missing += [
        "question:" + q["id"]
        for q in intent["questions"]
        if q["material"] and q["answer"] is None
    ]
    missing += [
        "choice:" + c["id"] for c in request["choices"] if c["selected"] is None
    ]
    return missing


def create_work(
    project_root,
    config_path,
    *,
    directory,
    intent: dict,
    signals: dict,
    choices=(),
    assignments=(),
    controls=(),
    tasks=(),
    inputs=(),
    artifact=None,
    budget=None,
    effects=None,
    legacy=None,
) -> dict:
    """Capture a local work proposal without granting effects or provider calls."""
    root, target = Path(project_root).resolve(), safe_storage(directory)
    registry, config = load_task_registry(config_path)
    # Extensions/retrieval need their own later operation qualification.
    fields(registry, ("schema_version", "participants"))
    request = {
        "schema_version": 1,
        "task_id": str(uuid4()),
        "revision": 1,
        "project_root": str(root),
        "intent": copy.deepcopy(intent),
        "signals": copy.deepcopy(signals),
        "choices": copy.deepcopy(list(choices)),
        "assignments": copy.deepcopy(list(assignments)),
        "controls": copy.deepcopy(list(controls)),
        "tasks": copy.deepcopy(list(tasks)),
        "inputs": list(inputs),
        "artifact": artifact,
        "budgets": budgets(budget if budget is not None else DEFAULT_BUDGETS),
        "registry": registry,
        "config": config,
    }
    _validate_intent(request["intent"])
    if legacy is not None:
        request["legacy"] = copy.deepcopy(legacy)
    if effects is not None:
        request["effects"] = copy.deepcopy(effects)
    _validate_choices(request["choices"])
    _validate_tasks(request["tasks"], request["intent"]["scope"])
    request["authoring"] = select_authoring(
        request["signals"], choices=request["choices"], tasks=request["tasks"]
    )
    request["evidence"] = _capture(request, target)
    _validate_request(request)
    target.parent.mkdir(parents=True, exist_ok=True)
    store = RunStore(target)
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
        "recovery": copy.deepcopy(RECOVERY),
    }
    with store.lease():
        store.save(record)
    return record


def decision_binding(record: dict) -> dict:
    """Project current identity for the owning Spec collector; this grants nothing."""
    request = record["request"]
    return {
        "schema_version": 1,
        "task_id": request["task_id"],
        "revision": request["revision"],
        "request_digest": digest(request),
        "record_path": record["record_path"],
        "checkpoint_digest": record["checkpoint_digest"],
    }


def _supported(controls, supported):
    _items(supported, "supported controls", 32)
    for item in supported:
        fields(item, ("id", "kind", "owner", "version"))
        _validate_controls([{**item, "required": True, "phases": ["accept"]}])
    if len({c["id"] for c in supported}) != len(supported):
        raise ValueError("Duplicate supported control")
    for control in controls:
        identity = {k: control[k] for k in ("id", "kind", "owner", "version")}
        if control["required"] and identity not in supported:
            raise ValueError(f"Unavailable required control: {control['id']}")


def _bindings(request):
    identity = {
        "task_id": request["task_id"],
        "revision": request["revision"],
        "request_digest": digest(request),
    }
    assignments = {}
    for item in request["assignments"]:
        role = item["role"]
        assignments[role] = {
            **identity,
            **copy.deepcopy(item),
            "assignment_id": str(
                uuid5(NAMESPACE_URL, digest({**identity, "role": role}))
            ),
            "configuration": copy.deepcopy(
                request["registry"]["participants"][item["participant"]]
            ),
        }
    return {
        "contract": identity,
        "assignments": assignments,
        "effect_classes": (
            ["file_creation", "file_directory", "file_replacement"]
            if request.get("effects")
            else []
        ),
    }


def _validate_acceptance(record):
    if record["status"] == "draft":
        if record["acceptance"] is not None or record["bindings"] != {}:
            raise ValueError("Draft work cannot retain accepted authority")
        return
    acceptance = record["acceptance"]
    fields(
        acceptance,
        (
            "decision",
            "supported_controls",
            *(["collector"] if "collector" in acceptance else []),
        ),
    )
    decision = acceptance["decision"]
    fields(decision, (*decision_binding(record), "accepted", "source"))
    draft = {
        **{k: v for k, v in record.items() if k != "build"},
        "status": "draft",
        "acceptance": None,
        "bindings": {},
    }
    draft["checkpoint_digest"] = checkpoint_digest(draft)
    expected = decision_binding(draft)
    if (
        decision["accepted"] is not True
        or type(decision["revision"]) is not int
        or type(decision["schema_version"]) is not int
        or any(decision[k] != v for k, v in expected.items())
    ):
        raise ValueError("Stale or foreign Spec decision binding")
    fields(decision["source"], ("owner", "reference", "disposition"))
    source = decision["source"]
    if source["owner"] != "spec" or source["disposition"] not in (
        "approve_plan",
        "approve_task",
        "auto_run_remaining",
    ):
        raise ValueError("Acceptance requires an owning Spec decision")
    bounded_text(source["reference"], "Spec decision reference")
    if "collector" in acceptance:
        receipt = acceptance["collector"]
        fields(receipt, ("response", "result", "adapter_version"))
        if (
            digest(receipt["response"]) != source["reference"]
            or receipt["result"].get("disposition") != source["disposition"]
            or receipt["result"].get("completed") != [record["request"]["task_id"]]
            or type(receipt["adapter_version"]) is not int
        ):
            raise ValueError(
                "Spec collector receipt differs from the accepted decision"
            )
    if (
        any(
            c
            == {
                "id": "spec-approval",
                "kind": "human",
                "owner": "spec",
                "version": 1,
                "required": True,
                "phases": ["accept"],
            }
            for c in record["request"]["controls"]
        )
        and "collector" not in acceptance
    ):
        raise ValueError("Required human control needs the actual collector receipt")
    if missing_information(record["request"]):
        raise ValueError("Unresolved material intent prevents acceptance")
    if not any(a["role"] == "planner" for a in record["request"]["assignments"]):
        raise ValueError("A planner assignment is required")
    _supported(record["request"]["controls"], acceptance["supported_controls"])
    if record["bindings"] != _bindings(record["request"]):
        raise ValueError("Work bindings differ from the accepted contract")


def validate_work_task(record: dict, directory: Path) -> dict:
    """Read this version explicitly; retained old profiles keep their own validator."""
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
            *(["planning"] if "planning" in record else []),
            *(["build"] if "build" in record else []),
        ),
    )
    versioned(record)
    if record["operation"] != "task" or record["task_profile"] != PROFILE:
        raise ValueError("Unsupported work profile")
    if record["record_path"] != str(directory / "record.json"):
        raise ValueError("Copied work cannot become another owner")
    if (
        record["status"] not in ("draft", "accepted")
        or record["events"] != []
        or record["recovery"] != RECOVERY
    ):
        raise ValueError("Unsupported feature-work runtime state")
    _validate_request(record["request"])
    if "build" in record:
        from .work_effects import validate_journal

        if record["status"] != "accepted" or not record["request"].get("effects"):
            raise ValueError("Build effects require accepted effect authority")
        if record["build"].get("profile") == "feature-build-v1":
            from .work_build import validate_build

            validate_build(record["build"], record["request"])
        else:
            validate_journal(record["build"], record["request"])
    if "planning" in record:
        from .work_runtime import validate_planning

        if record["status"] != "draft":
            raise ValueError(
                "Stage the planning proposal before accepting its new draft"
            )
        validate_planning(record["planning"], record["request"])
    history = _items(record["history"], "history", 31)
    if len(history) != record["request"]["revision"] - 1:
        raise ValueError("Work history must retain every preceding revision")
    for index, item in enumerate(history):
        fields(
            item,
            (
                "request",
                "acceptance",
                *(["planning"] if "planning" in item else []),
                *(["build"] if "build" in item else []),
            ),
        )
        previous = item["request"]
        _validate_request(previous)
        if previous["revision"] != index + 1 or any(
            previous[k] != record["request"][k] for k in ("task_id", "project_root")
        ):
            raise ValueError("Work history identity mismatch")
        prior = {
            **{k: v for k, v in record.items() if k not in ("planning", "build")},
            **item,
            "history": history[:index],
            "status": "accepted" if item["acceptance"] is not None else "draft",
            "bindings": _bindings(previous) if item["acceptance"] is not None else {},
        }
        _validate_acceptance(prior)
        if "build" in item:
            from .work_build import validate_build

            if item["acceptance"] is None:
                raise ValueError("Historical build lacks original authority")
            validate_build(item["build"], previous)
        if "planning" in item:
            from .work_runtime import validate_planning

            if item["acceptance"] is not None:
                raise ValueError("Planning history cannot claim human acceptance")
            validate_planning(item["planning"], previous)
        if "review_handoff" in previous:
            from .work_review_handoff import validate_source, validate_transition

            validate_source(previous["review_handoff"], previous, history[:index])
            validate_transition(previous["review_handoff"], previous, history[:index])
    if "review_handoff" in record["request"]:
        from .work_review_handoff import validate_source, validate_transition

        validate_source(record["request"]["review_handoff"], record["request"], history)
        validate_transition(
            record["request"]["review_handoff"], record["request"], history
        )
    _validate_acceptance(record)
    return record


def check_work_fresh(record: dict) -> None:
    """Check captured inputs, artifact and selected configuration before authority."""
    request = record["request"]
    if "legacy" in request:
        from .spec_legacy import legacy_plan

        current = legacy_plan(request["legacy"]["path"])
        if current["content_sha256"] != request["legacy"]["content_sha256"]:
            raise ValueError("Imported plan changed; revise and reaccept")
    registry, config = load_task_registry(request["config"]["path"])
    if (
        registry != request["registry"]
        or config != request["config"]
        or _capture(request, Path(record["record_path"]).parent) != request["evidence"]
    ):
        raise ValueError("Stale work evidence; revise before accepting")
    if request.get("effects"):
        from .repair import assert_snapshot

        assert_snapshot(request["effects"], request["effects"]["before"])


def bind_work_acceptance(
    directory, decision: dict, *, supported_controls=(), collector=None
) -> dict:
    """Bind a trusted host's collected Spec decision, without creating another gate."""
    from .task_contract import read_task

    store = RunStore(safe_storage(directory), existing=True)
    with store.lease():
        record = read_task(store.directory)
        if record["task_profile"] != PROFILE or record["status"] != "draft":
            raise ValueError(
                "Work must be an unaccepted draft; do not replay a decision"
            )
        check_work_fresh(record)
        record.update(
            status="accepted",
            acceptance={
                "decision": copy.deepcopy(decision),
                "supported_controls": copy.deepcopy(list(supported_controls)),
            },
            bindings=_bindings(record["request"]),
        )
        if collector is not None:
            record["acceptance"]["collector"] = copy.deepcopy(collector)
        validate_work_task(record, store.directory)
        check_work_fresh(record)
        store.save(record)
        return record


def revise_work(
    directory,
    *,
    checkpoint: str,
    changes=None,
    require_fresh=False,
    preserve_completed=False,
    _review_handoff=...,
) -> dict:
    """Refresh evidence or correct supplied fields; changed work loses its grant."""
    from .task_contract import read_task

    store = RunStore(safe_storage(directory), existing=True)
    with store.lease():
        record = read_task(store.directory)
        if (
            record["task_profile"] != PROFILE
            or checkpoint != record["checkpoint_digest"]
        ):
            raise ValueError("Stale work checkpoint or unsupported profile")
        if type(require_fresh) is not bool:
            raise ValueError("Freshness policy must be boolean")
        if "build" in record:
            if preserve_completed:
                from .work_runtime import _steer_build

                record = _steer_build(record, changes, store.directory)
                validate_work_task(record, store.directory)
                store.save(record)
                return record
            raise ValueError(
                "Retain the effect journal; build rebasing is not yet qualified"
            )
        if require_fresh:
            check_work_fresh(record)
        if "planning" in record and any(
            e["phase"] != "prepared" and e["state"] != "completed"
            for e in record["planning"]["events"]
        ):
            raise ValueError(
                "Uncertain planning attempt must be reconciled before correction"
            )
        changes = copy.deepcopy({} if changes is None else changes)
        if not isinstance(changes, dict) or set(changes) - set(EDITABLE + EXTENSIONS):
            raise ValueError("Unknown work correction fields")
        old = copy.deepcopy(record["request"])
        request = record["request"]
        if "intent" in changes:
            intent = changes.pop("intent")
            if not isinstance(intent, dict) or set(intent) - set(INTENT_FIELDS):
                raise ValueError("Unknown intent correction fields")
            request["intent"].update(intent)
        handoff_change = changes.pop("review_handoff", ...)
        if handoff_change is None:
            request.pop("review_handoff", None)
        elif handoff_change is not ...:
            raise ValueError(
                "review_handoff can only be derived by fresh planning staging"
            )
        if _review_handoff is not ...:
            request["review_handoff"] = copy.deepcopy(_review_handoff)
        request.update(changes)
        request["registry"], request["config"] = load_task_registry(
            request["config"]["path"]
        )
        _validate_intent(request["intent"])
        _validate_choices(request["choices"])
        _validate_tasks(request["tasks"], request["intent"]["scope"])
        request["authoring"] = select_authoring(
            request["signals"], choices=request["choices"], tasks=request["tasks"]
        )
        request["evidence"] = _capture(request, store.directory)
        if "legacy" in request:
            from .spec_legacy import legacy_plan

            current = legacy_plan(request["legacy"]["path"])
            if current["content_sha256"] != request["legacy"]["content_sha256"]:
                # A changed plan cannot retain tasks parsed from its former bytes.
                raise ValueError("Reimport the edited legacy plan explicitly")
        if require_fresh and any(
            request[k] != old[k] for k in ("evidence", "config", "registry")
        ):
            raise ValueError("Stale proposal inputs cannot be rebound as fresh work")
        _validate_request(request)
        if request == old and record.get("planning", {}).get("status") != "completed":
            return record
        if old["revision"] == 32:
            raise ValueError("Work revision limit reached")
        historical = {"request": old, "acceptance": record["acceptance"]}
        if "planning" in record:
            historical["planning"] = record.pop("planning")
        record["history"].append(historical)
        request["revision"] += 1
        record.update(status="draft", acceptance=None, bindings={})
        validate_work_task(record, store.directory)
        store.save(record)
        return record
