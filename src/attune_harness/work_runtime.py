"""Bounded planning and accepted file effects on the shared task journal."""

import copy
import time
from pathlib import Path

from .features import FeatureUnavailable, read_text, require_feature
from .recovery import RecoveryCursor, stable_id, validate_events
from .review import authorize_external
from .review_contract import FORMS_VERSION, bounded_text, digest, fields, parse_json
from .review_participants import ReviewExchange
from .review_store import RunStore
from .task_contract import read_task, safe_storage
from .task_runtime import dispatch_assignment, guarded_execution
from .work_contract import (
    PROFILE,
    _bindings,
    _items,
    _texts,
    _validate_choices,
    _validate_tasks,
    check_work_fresh,
    missing_information,
    revise_work,
    response_contract,
)

PLANNING_PROFILE = "feature-planning-v1"
PROTOCOL = (
    "Preserve the exact user goal, constraints and accepted criteria. Return a plan "
    "with kind, goal, tasks, coverage, choices and notes, or a critique with kind, "
    "findings and notes as described by output_schema. Do not ask answered questions. "
    "New choices must remain unselected; never change settled choices. "
    "Separate missing evidence from a defect and keep optional advice in notes. "
    "A plan is a proposal, not acceptance or evidence of execution."
)
PLAN_SCHEMA = {
    "kind": "plan",
    "goal": "the current user goal",
    "tasks": [
        {
            "id": "unique-id",
            "objective": "bounded step",
            "dependencies": ["preceding-task-id"],
            "outputs": ["exact path in scope"],
            "checks": ["observable assertion"],
        }
    ],
    "coverage": [{"criterion": "exact accepted criterion", "tasks": ["task-id"]}],
    "choices": [
        {
            "id": "new-choice-id",
            "question": "unresolved design question",
            "selected": None,
            "options": [
                {
                    "id": "option-id",
                    "proposal": "alternative",
                    "rationale": "why",
                    "evidence": ["known evidence"],
                    "uncertainty": ["disclosed unknown"],
                    "counter_case": "strongest reason against",
                }
            ],
        }
    ],
    "notes": ["optional advice or disclosed uncertainty"],
}
CRITIQUE_SCHEMA = {
    "kind": "critique",
    "findings": [
        {
            "id": "unique-id",
            "severity": "low|medium|high",
            "text": "concrete issue",
            "evidence": ["source or task reference"],
        }
    ],
    "notes": ["optional wording advice or disclosed uncertainty"],
}
PLANNER_PROTOCOL = (
    "Preserve the exact user goal, constraints and accepted criteria. Return only "
    "the plan described by output_schema. Map each exact criterion to actual tasks "
    "in coverage; write concrete task checks. The host adds the bound criterion "
    "text to those checks, so duplicate wording is unnecessary. Follow build_profile. "
    "Tests belong in checks/protected probes or a scoped test-file output; do not "
    "create outputless verification steps. Do not ask answered questions. Reserve "
    "choices for unresolved material intent, scope, compatibility or authority. "
    'Include every required field, including "choices": [] when there are no '
    "unresolved material choices; never omit choices or use null. An empty list "
    "does not answer, remove or change any existing human choice. "
    "Choose a supported approach for routine implementation details and put useful "
    "alternatives in notes. New material choices remain unselected; never change "
    "settled choices. Preserve legitimate uncertainty and separate optional advice. "
    "A plan is a proposal, not acceptance or execution evidence."
)
CRITIC_PROTOCOL = (
    "Critique the supplied plan against the exact accepted intent and build_profile. "
    "Return only the critique described by output_schema with evidence for findings. "
    "Distinguish contradictions, unmet requirements and unsupported guarantees. "
    "Accurately disclosed unknowns are not defects. Keep optional advice in notes. "
    "The host binds coverage criteria to task checks; no duplicate wording is needed. "
    "Do not invent human decision gates for routine implementation alternatives. "
    "Never claim human acceptance or execution."
)
BUILD_PROFILE = {
    "kind": "ordered-file-build",
    "outputs": "Each task produces at least one scoped file; each file has one producer.",
    "dependencies": "Every task after the first depends on the preceding task.",
    "reserved_task_id": "final",
    "verification": "Use task checks and protected probes; no outputless build steps.",
}


class EffectStore:
    """Persist effects under the sole accepted task owner and writer lease."""

    def __init__(self, store, record):
        self.store, self.record = store, record

    def save(self, run):
        self.record["build"] = run
        self.store.save(self.record)


def completed_steps(record):
    """Project checked completion, not a model's claim or task status label."""
    run = record.get("build", {})
    return [
        t["id"]
        for t in record["request"]["tasks"]
        if any(
            e["operation_key"] == "probe:" + t["id"]
            and e["state"] == "completed"
            and e["result"]["passed"]
            for e in run.get("events", [])
        )
    ]


def _steer_build(record, changes, directory):
    """Archive a settled journal and reauthorize only its corrected pending suffix.

    Completed intent cannot be edited through this bounded operation. Broader
    rework needs an explicit new scope; no completed or uncertain work is erased.
    """
    from . import work_effects
    from .work_build import check_build_fresh, PROFILE as BUILD_PROFILE
    from .work_contract import _capture, _validate_request

    run = record["build"]
    if run.get("profile") != BUILD_PROFILE or run["status"] == "running":
        raise ValueError("Steering requires a stopped dependent build")
    if any(e["state"] != "completed" for e in run["events"]):
        raise ValueError("Reconcile unfinished operations before steering")
    check_build_fresh(record)
    old = record["request"]
    if (
        old["revision"] == 32
        or not isinstance(changes, dict)
        or set(changes) != {"tasks"}
    ):
        raise ValueError("This steering profile corrects pending tasks only")
    tasks = copy.deepcopy(changes["tasks"])
    _validate_tasks(tasks, old["intent"]["scope"])
    completed = completed_steps(record)
    prefix = old["tasks"][: len(completed)]
    if [t["id"] for t in prefix] != completed or tasks[: len(prefix)] != prefix:
        raise ValueError("Completed intent must remain unchanged")
    if (
        not completed
        or len(completed) >= len(old["tasks"])
        or len(completed) >= len(tasks)
    ):
        raise ValueError("Steering requires both completed and pending tasks")
    boundary = next(
        i
        for i, e in enumerate(run["events"])
        if e["operation_key"] == "probe:" + completed[-1]
    )
    if boundary != len(run["events"]) - 1:
        # A settled failure can be repaired under a new grant. Its original
        # journal remains intact; uncertain or partly applied steps cannot.
        failed = run["events"][-1]
        next_task = old["tasks"][len(prefix)]
        if not (
            run["status"] == "needs_revision"
            and failed["kind"] == "acceptance_probe"
            and failed["operation_key"] == "probe:" + next_task["id"]
            and failed["result"]["passed"] is False
            and failed["result"]["failure"] == "nonzero_exit"
        ):
            raise ValueError("Pause at a verified task boundary before correction")
        if len(tasks) != len(old["tasks"]) or any(
            task[key] != previous[key]
            for task, previous in zip(tasks[len(prefix) :], old["tasks"][len(prefix) :])
            for key in ("id", "outputs", "dependencies")
        ):
            raise ValueError(
                "Failed-task repair must retain task identities, outputs and dependencies"
            )
    pending = tasks[len(prefix) :]
    for task in pending:
        task["dependencies"] = [d for d in task["dependencies"] if d not in completed]
    outputs = [p for t in pending for p in t["outputs"]]
    preserved = [p for t in prefix for p in t["outputs"]]
    if set(outputs) & set(preserved):
        raise ValueError("Pending correction cannot overwrite preserved completion")
    plan = old["effects"]
    parents = [
        p
        for p in plan["parents"]
        if not (Path(plan["root"]) / p).exists()
        and any(name.startswith(p + "/") for name in outputs)
    ]
    effects = work_effects.freeze(
        Path(plan["root"]),
        outputs,
        parents,
        list(dict.fromkeys([*plan["protected"], *preserved])),
        [{k: c[k] for k in ("control", "probe")} for c in plan["checks"]],
        directory,
        verification=[
            {k: p[k] for k in ("task_id", "probe")}
            for p in plan["verification"]
            if p["task_id"] in [t["id"] for t in pending] + ["final"]
        ],
    )
    request = copy.deepcopy(old)
    request.update(revision=old["revision"] + 1, tasks=pending, effects=effects)
    request["intent"]["scope"] = outputs
    request["inputs"] = list(dict.fromkeys([*old["inputs"], *preserved]))
    request["evidence"] = _capture(request, directory)
    from .work_contract import select_authoring

    request["authoring"] = select_authoring(
        request["signals"], choices=request["choices"], tasks=pending
    )
    _validate_request(request)
    historical = {
        "request": copy.deepcopy(old),
        "acceptance": record["acceptance"],
        "build": record.pop("build"),
    }
    record["history"].append(historical)
    record.update(request=request, status="draft", acceptance=None, bindings={})
    return record


def work_status(directory):
    """Read one owner, including preserved prior completion; never dispatch."""
    record = read_task(directory)
    if record["task_profile"] != PROFILE:
        raise ValueError("Expected a feature-work record")
    run = record.get("build", record.get("planning", {}))
    preserved = []
    for historical in record["history"]:
        if "build" in historical and all(
            historical["request"]["intent"][k] == record["request"]["intent"][k]
            for k in ("goal", "context", "constraints", "acceptance")
        ):
            preserved.extend(completed_steps(historical))
    return {
        "task_id": record["request"]["task_id"],
        "revision": record["request"]["revision"],
        "checkpoint_digest": record["checkpoint_digest"],
        "authority": record["status"],
        "status": run.get("status", record["status"]),
        "completed": completed_steps(record),
        "preserved_completion": preserved,
        "missing": missing_information(record["request"]),
    }


def _effect_owner(store, checkpoint):
    from .task_contract import load_task_registry
    from .work_effects import validate_request_effects

    record = read_task(store.directory)
    if record["checkpoint_digest"] != checkpoint or record["status"] != "accepted":
        raise ValueError("Effects require current accepted work authority")
    request = record["request"]
    if record["task_profile"] != PROFILE or not request.get("effects"):
        raise ValueError("No accepted effect manifest")
    registry, config = load_task_registry(request["config"]["path"])
    if registry != request["registry"] or config != request["config"]:
        raise ValueError("Accepted participant configuration changed")
    validate_request_effects(request)
    return record


def apply_work_effects(directory, checkpoint, proposal, *, max_operations=None):
    """Host entry point for one accepted batch; this is not task acceptance.

    Native worker dispatch, dependent task sequencing and the live Spec bridge
    are separate qualification boundaries. No worker selects its own checks.
    """
    from .recovery import ReviewPaused
    from .review_store import PersistenceError
    from .work_effects import (
        PROFILE as EFFECT_PROFILE,
        apply_effects,
        control_runners,
        operations,
        require_platform,
    )

    require_platform()
    store = RunStore(safe_storage(directory), existing=True)
    with store.lease():
        record = _effect_owner(store, checkpoint)
        request = record["request"]
        operations(request["effects"], proposal)
        control_runners(request)
        run = record.get("build")
        if run is not None and run["profile"] != EFFECT_PROFILE:
            raise ValueError(
                "Use the owning dependent-build runtime to resume this journal"
            )
        if run is None:
            check_work_fresh(record)
            run = dict(
                profile=EFFECT_PROFILE,
                request_digest=digest(request),
                proposal=copy.deepcopy(proposal),
                events=[],
                status="running",
                advisory=[],
            )
        elif run["proposal"] != proposal:
            raise ValueError("An effect batch cannot change during recovery")
        target = EffectStore(store, record)
        cursor = RecoveryCursor(run, target, max_operations)
        target.save(run)
        try:

            def ensure_current():
                from .task_contract import load_task_registry

                registry, config = load_task_registry(request["config"]["path"])
                if registry != request["registry"] or config != request["config"]:
                    raise ValueError("Accepted participant configuration changed")

            run["advisory"] = apply_effects(
                request, proposal, cursor, ensure_current=ensure_current
            )
        except PersistenceError:
            # A failed save may have reached disk. Never overwrite it blindly.
            raise
        except ReviewPaused:
            run["status"] = "paused"
        except BaseException:
            run["status"] = "unresolved"
            target.save(run)
            raise
        else:
            run["status"] = "completed"
        target.save(run)
        return record


def reconcile_work_effect(directory, checkpoint, event_id, *, retry_before=False):
    """Explicit host reconciliation; never infer permission from an unknown write."""
    from .work_effects import reconcile_effect, require_platform

    require_platform()
    if type(retry_before) is not bool:
        raise ValueError("Retry policy must be boolean")
    store = RunStore(safe_storage(directory), existing=True)
    with store.lease():
        record = _effect_owner(store, checkpoint)
        if "build" not in record:
            raise ValueError("No effect operation to reconcile")
        run = record["build"]
        reconcile_effect(
            record["request"]["effects"],
            run["events"],
            event_id,
            retry_before=retry_before,
        )
        run["status"] = "paused"
        store.save(record)
        return record


def build_work(*args, **kwargs):
    """Shared work entry point; the dependent-build policy owns its journal."""
    from .work_build import build_work as execute

    return execute(*args, **kwargs)


def _roles(request):
    return [
        a
        for role in ("planner", "critic")
        for a in request["assignments"]
        if a["role"] == role
    ]


def validate_reply(
    payload: dict, request: dict, role: str, *, contract_version=1
) -> None:
    """Check retained intent/criteria and proposal shape; not semantic entailment."""
    response_contract({"response_contract": contract_version})
    if role == "critic":
        fields(payload, ("kind", "findings", "notes"))
        if payload["kind"] != "critique":
            raise ValueError("Critic must return a critique, never approval")
        seen = set()
        for finding in _items(payload["findings"], "findings", 32):
            fields(finding, ("id", "severity", "text", "evidence"))
            bounded_text(finding["id"], "finding id", 64)
            bounded_text(finding["text"], "finding")
            _texts(finding["evidence"], "finding evidence")
            if (
                finding["id"] in seen
                or finding["severity"] not in ("low", "medium", "high")
                or not finding["evidence"]
            ):
                raise ValueError(
                    "Findings need unique identities, severity and explicit evidence"
                )
            seen.add(finding["id"])
    else:
        fields(payload, ("kind", "goal", "tasks", "coverage", "choices", "notes"))
        if payload["kind"] != "plan" or payload["goal"] != request["intent"]["goal"]:
            raise ValueError(
                "Planning response changed the goal or requested another intake"
            )
        _validate_tasks(payload["tasks"], request["intent"]["scope"])
        if not payload["tasks"]:
            raise ValueError("A plan must contain executable tasks")
        if contract_version == 2:
            from .work_build import validate_steps

            validate_steps(payload["tasks"])
        tasks = {t["id"]: t for t in payload["tasks"]}
        criteria = request["intent"]["acceptance"]
        seen = set()
        for row in _items(payload["coverage"], "criterion coverage"):
            fields(row, ("criterion", "tasks"))
            _texts(row["tasks"], "criterion tasks")
            criterion = row["criterion"]
            if (
                criterion not in criteria
                or criterion in seen
                or not row["tasks"]
                or any(
                    t not in tasks
                    or (contract_version == 1 and criterion not in tasks[t]["checks"])
                    for t in row["tasks"]
                )
            ):
                raise ValueError(
                    "Criterion coverage must name actual tasks and retained checks"
                )
            seen.add(criterion)
        if seen != set(criteria):
            raise ValueError("Plan omitted an explicit acceptance criterion")
        _validate_choices(payload["choices"])
        settled = {c["id"]: c for c in request["choices"]}
        for choice in payload["choices"]:
            if choice["id"] in settled or choice["selected"] is not None:
                raise ValueError(
                    "A participant cannot replace or decide a human choice"
                )
    _texts(payload["notes"], "advisory notes")


def demonstration_reply(turn: dict) -> dict:
    """Deterministic software fixture, explicitly not model planning competence."""
    if turn["role"] == "critic":
        return {
            "kind": "critique",
            "findings": [],
            "notes": ["Deterministic fixture; no semantic model review."],
        }
    intent = turn["work"]["intent"]
    tasks = [
        {
            "id": "implement",
            "objective": intent["goal"],
            "dependencies": [],
            "outputs": intent["scope"],
            "checks": intent["acceptance"],
        }
    ]
    return {
        "kind": "plan",
        "goal": intent["goal"],
        "tasks": tasks,
        "coverage": [
            {"criterion": c, "tasks": ["implement"]} for c in intent["acceptance"]
        ],
        "choices": [],
        "notes": ["Deterministic fixture; no native planning competence established."],
    }


def _turn(request, role, run):
    assignment = _bindings(request)["assignments"][role]
    turn = {
        "task_id": request["task_id"],
        "attempt_id": assignment["assignment_id"],
        "turn_id": stable_id(assignment["assignment_id"], PLANNING_PROFILE),
        "requirement_revision": digest(request),
        "participant_id": assignment["participant"],
        "role": role,
        "operation_profile": PLANNING_PROFILE,
        "protocol": PROTOCOL,
        "objective": request["intent"]["goal"],
        "tools": [],
        "history": [],
        "remaining_tool_calls": 0,
        "remaining_turns": 1,
        "output_schema": PLAN_SCHEMA if role == "planner" else CRITIQUE_SCHEMA,
        "work": {
            k: copy.deepcopy(request[k])
            for k in ("intent", "choices", "signals", "authoring", "tasks")
        },
        "output_contract": assignment["output_contract"],
        "source_evidence": run["source_evidence"],
        "proposal": (
            run["participants"].get("planner", {}).get("proposal")
            if role == "critic"
            else None
        ),
    }
    if response_contract(run) == 2:
        turn.update(
            response_contract=2,
            protocol=PLANNER_PROTOCOL if role == "planner" else CRITIC_PROTOCOL,
            build_profile=copy.deepcopy(BUILD_PROFILE),
        )
    return turn


class PlanningStore:
    """Project journal saves into the sole owning task checkpoint."""

    def __init__(self, store, record):
        self.store, self.record = store, record
        self.directory, self.path = store.directory, store.path

    def save(self, run):
        if len(run["events"]) > self.record["request"]["budgets"]["max_operations"]:
            from .review_store import PersistenceError

            raise PersistenceError("Planning operation budget exhausted")
        self.record["planning"] = run
        self.store.save(self.record)


def validate_planning(run: dict, request: dict) -> None:
    """Validate persisted planning and its linkage without reloading old sources."""
    fields(
        run,
        (
            "profile",
            "request_digest",
            "status",
            "events",
            "participants",
            "source_evidence",
            "questions",
            "permissions",
            "metrics",
            *(["error"] if "error" in run else []),
            *(["response_contract"] if "response_contract" in run else []),
        ),
    )
    contract_version = response_contract(run)
    if run["profile"] != PLANNING_PROFILE or run["request_digest"] != digest(request):
        raise ValueError("Planning journal belongs to another work revision")
    if run["status"] not in (
        "running",
        "paused",
        "unresolved",
        "unavailable",
        "failed",
        "needs_input",
        "needs_revision",
        "completed",
    ):
        raise ValueError("Unknown planning status")
    fields(run["permissions"], ("external", "native"))
    if any(type(v) is not bool for v in run["permissions"].values()):
        raise ValueError("Planning permissions require explicit booleans")
    if not isinstance(run["participants"], dict) or set(run["participants"]) - {
        "planner",
        "critic",
    }:
        raise ValueError("Unknown planning participant role")
    fields(run["source_evidence"], request["evidence"])
    for path, raw in run["source_evidence"].items():
        import hashlib

        if (
            not isinstance(raw, str)
            or hashlib.sha256(raw.encode("utf-8")).hexdigest()
            != request["evidence"][path]
        ):
            raise ValueError("Captured planning evidence differs from bound inputs")
    if run["questions"] != missing_information(request):
        raise ValueError("Planning questions must reflect only missing material intent")
    fields(run["metrics"], ("first_useful_seconds", "elapsed_seconds"))
    if any(type(v) not in (float, int) or v < 0 for v in run["metrics"].values()):
        raise ValueError("Invalid planning timing")
    validate_events(run, kinds=("participant_turn",))
    if len(run["events"]) > request["budgets"]["max_operations"]:
        raise ValueError("Planning exceeds work budget")
    roles = _roles(request)
    if len(run["events"]) > len(roles):
        raise ValueError("Planning permits one attempt per selected role")
    for index, event in enumerate(run["events"]):
        role = roles[index]["role"]
        turn = _turn(request, role, run)
        expected = {
            "participant_id": turn["participant_id"],
            "attempt_id": turn["attempt_id"],
            "turn_id": turn["turn_id"],
            "request_digest": digest(turn),
            "operation_key": turn["turn_id"],
        }
        if event["attempts"] != 1 or any(
            event.get(k) != v for k, v in expected.items()
        ):
            raise ValueError("Saved planning operation does not bind the assignment")
        config = request["registry"]["participants"][turn["participant_id"]]
        allowed_effects = (
            ("unknown", "read_only")
            if config["adapter"] == "deterministic"
            else ("unknown",)
        )
        if event["effect_class"] not in allowed_effects:
            raise ValueError("Planning event understates external effects")
        if event["state"] == "completed":
            fields(event["result"], ("action", "identity"))
    for role, outcome in run["participants"].items():
        fields(
            outcome,
            (
                "participant_id",
                "attempt_id",
                "adapter",
                "status",
                "last_identity",
                *(["proposal"] if "proposal" in outcome else []),
            ),
        )
        assignment = next((a for a in roles if a["role"] == role), None)
        if (
            assignment is None
            or outcome["participant_id"] != assignment["participant"]
            or outcome["attempt_id"] != _turn(request, role, run)["attempt_id"]
        ):
            raise ValueError("Planning outcome differs from assigned identity")
        if outcome["adapter"] != request["registry"]["participants"][
            assignment["participant"]
        ]["adapter"] or outcome["status"] not in (
            "running",
            "completed",
            "paused",
            "failed",
            "unavailable",
            "unresolved",
        ):
            raise ValueError("Unsupported planning participant state")
        if "proposal" in outcome:
            validate_reply(
                outcome["proposal"], request, role, contract_version=contract_version
            )
            event = next(
                (e for e in run["events"] if e["attempt_id"] == outcome["attempt_id"]),
                None,
            )
            if (
                not event
                or event["state"] != "completed"
                or _decode(
                    event["result"]["action"],
                    request,
                    assignment,
                    contract_version=contract_version,
                )
                != outcome["proposal"]
            ):
                raise ValueError("Planning proposal has no matching completed reply")
    if run["status"] == "needs_input" and (not run["questions"] or run["events"]):
        raise ValueError("Question presentation cannot claim participant execution")
    if run["status"] in ("completed", "needs_revision"):
        if (
            run["questions"]
            or len(run["events"]) != len(roles)
            or not roles
            or roles[0]["role"] != "planner"
            or any(
                run["participants"].get(a["role"], {}).get("status") != "completed"
                or "proposal" not in run["participants"][a["role"]]
                for a in roles
            )
        ):
            raise ValueError("Planning completion lacks required attributed results")
        high = any(
            f["severity"] == "high"
            for f in run["participants"]
            .get("critic", {})
            .get("proposal", {})
            .get("findings", [])
        )
        if (run["status"] == "needs_revision") != high:
            raise ValueError("Planning status conceals a high-severity finding")


def _decode(action, request, assignment, *, contract_version=1):
    fields(action, ("kind", "text"))
    if action["kind"] != "final":
        raise ValueError("Planning participants cannot invoke tools")
    bounded_text(
        action["text"], "planning reply", assignment["budgets"]["max_output_bytes"]
    )
    payload = parse_json(action["text"], assignment["budgets"]["max_output_bytes"])
    validate_reply(
        payload, request, assignment["role"], contract_version=contract_version
    )
    return payload


def plan_work(
    directory,
    *,
    checkpoint=None,
    allow_external=False,
    allow_native=False,
    max_operations=None,
    exchange_factory=ReviewExchange,
) -> dict:
    """Plan a draft using explicit dispatch permissions; never accept or build it."""
    if type(allow_external) is not bool or type(allow_native) is not bool:
        raise ValueError("Dispatch permissions must be booleans")
    started = time.monotonic()
    store = RunStore(safe_storage(directory), existing=True)
    with store.lease():
        record = read_task(store.directory)
        if record["task_profile"] != PROFILE or record["status"] != "draft":
            raise ValueError(
                "Planning requires a draft; accepted contract only awaits its qualified build runtime"
            )
        if checkpoint is not None and checkpoint != record["checkpoint_digest"]:
            raise ValueError("Stale planning checkpoint")
        check_work_fresh(record)
        request = record["request"]
        if "planning" in record and record["planning"]["status"] in (
            "completed",
            "needs_revision",
            "needs_input",
            "failed",
            "unavailable",
        ):
            return record
        if "planning" not in record:
            record["planning"] = {
                "profile": PLANNING_PROFILE,
                "response_contract": 2,
                "request_digest": digest(request),
                "status": "running",
                "events": [],
                "participants": {},
                "source_evidence": {
                    p: read_text(Path(request["project_root"]) / p, 65536)
                    for p in request["evidence"]
                },
                "questions": missing_information(request),
                "permissions": {"external": allow_external, "native": allow_native},
                "metrics": {"first_useful_seconds": 0.0, "elapsed_seconds": 0.0},
            }
        run = record["planning"]
        validate_planning(run, request)
        if run["permissions"] != {"external": allow_external, "native": allow_native}:
            raise ValueError("Resume cannot change planning dispatch authority")
        adapter = PlanningStore(store, record)
        cursor = RecoveryCursor(run, adapter, max_operations)
        run["status"] = "running"
        run.pop("error", None)
        adapter.save(run)

        def steps():
            if run["questions"]:
                run["status"] = "needs_input"
                return
            selected = _roles(request)
            if not selected or selected[0]["role"] != "planner":
                raise FeatureUnavailable("Planning requires a configured planner")
            if (
                len(selected) == 2
                and selected[0]["participant"] == selected[1]["participant"]
            ):
                raise ValueError(
                    "Planner and critic require distinct participant identities"
                )
            if request["budgets"]["max_operations"] < len(selected):
                raise ValueError(
                    "Planning operation budget cannot cover selected assignments"
                )
            for control in request["controls"]:
                if control["required"] and "plan" in control["phases"]:
                    raise FeatureUnavailable(
                        f"Required planning control has no qualified runner: {control['id']}"
                    )
            configurations = {
                a["role"]: request["registry"]["participants"][a["participant"]]
                for a in selected
            }
            authorize_external(configurations, allow_external)
            if not allow_native and any(
                c["adapter"] in ("claude", "codex") for c in configurations.values()
            ):
                raise FeatureUnavailable(
                    "Native planning needs explicit trial authorization; no fallback"
                )
            for config in configurations.values():
                if config["tools"] or config.get("review_mode"):
                    raise ValueError(
                        "Planning profile does not grant review tools or evidence policy"
                    )
            for assignment in selected:
                check_work_fresh(record)
                role, config = assignment["role"], configurations[assignment["role"]]
                turn = _turn(request, role, run)
                outcome = {
                    "participant_id": assignment["participant"],
                    "attempt_id": turn["attempt_id"],
                    "adapter": config["adapter"],
                    "status": "running",
                    "last_identity": None,
                }
                run["participants"][role] = outcome
                exchange = exchange_factory(
                    config, Path(request["project_root"]), profile=PLANNING_PROFILE
                )
                response = dispatch_assignment(
                    cursor, turn["turn_id"], turn, config, exchange, outcome
                )
                check_work_fresh(record)
                proposal = _decode(
                    response["action"],
                    request,
                    assignment,
                    contract_version=response_contract(run),
                )
                outcome.update(status="completed", proposal=proposal)
                if not run["metrics"]["first_useful_seconds"]:
                    run["metrics"]["first_useful_seconds"] = (
                        run["metrics"]["elapsed_seconds"] + time.monotonic() - started
                    )
                adapter.save(run)
            high = any(
                f["severity"] == "high"
                for f in run["participants"]
                .get("critic", {})
                .get("proposal", {})
                .get("findings", [])
            )
            run["status"] = "needs_revision" if high else "completed"

        guarded_execution(run, adapter, steps)
        if any(
            e["state"] != "completed" and e["phase"] != "prepared"
            for e in run["events"]
        ):
            run["status"] = "unresolved"
        run["metrics"]["elapsed_seconds"] += time.monotonic() - started
        if run["questions"]:
            run["metrics"]["first_useful_seconds"] = run["metrics"]["elapsed_seconds"]
        adapter.save(run)
        return record


def apply_planning_proposal(directory, *, checkpoint: str) -> dict:
    """Host stages a current proposal as a new draft revision, without acceptance."""
    record = read_task(directory)
    if checkpoint != record["checkpoint_digest"]:
        raise ValueError("Stale planning proposal checkpoint")
    run = record.get("planning", {})
    if run.get("status") != "completed":
        raise ValueError("Only a completed planning proposal can be staged")
    check_work_fresh(record)
    proposal = run["participants"]["planner"]["proposal"]
    tasks = copy.deepcopy(proposal["tasks"])
    if response_contract(run) == 2:
        validate_reply(proposal, record["request"], "planner", contract_version=2)
        by_id = {t["id"]: t for t in tasks}
        for coverage in proposal["coverage"]:
            for task_id in coverage["tasks"]:
                checks = by_id[task_id]["checks"]
                if coverage["criterion"] not in checks:
                    checks.append(coverage["criterion"])
    return revise_work(
        directory,
        checkpoint=checkpoint,
        changes={
            "tasks": tasks,
            "choices": record["request"]["choices"] + proposal["choices"],
        },
        require_fresh=True,
    )


def planning_questions(directory) -> dict:
    """Project focused missing information through the existing form renderer."""
    record = read_task(directory)
    check_work_fresh(record)
    request = record["request"]
    labels = {
        "goal": "What should this work accomplish?",
        "scope": "Which exact files are in scope?",
        "acceptance": "What observable result establishes success?",
    }
    labels.update(
        {"question:" + q["id"]: q["question"] for q in request["intent"]["questions"]}
    )
    labels.update({"choice:" + c["id"]: c["question"] for c in request["choices"]})
    missing = missing_information(request)
    if not missing:
        return {
            "checkpoint_digest": record["checkpoint_digest"],
            "definition": None,
            "markdown": "",
            "missing": [],
        }
    form_fields = []
    for index, name in enumerate(missing):
        field = {
            "id": f"answer_{index}",
            "text": labels[name],
            "type": "text_input",
            "required": True,
        }
        if name in ("scope", "acceptance"):
            field["text"] += " Enter one item per line."
        if name.startswith("choice:"):
            choice = next(c for c in request["choices"] if "choice:" + c["id"] == name)
            field.update(
                type="single_select",
                options=[
                    f"{o['id']} — {o['proposal']}. Rationale: {o['rationale']}. "
                    f"Counter-case: {o['counter_case']}. Evidence: {', '.join(o['evidence']) or 'not supplied'}. "
                    f"Uncertainty: {', '.join(o['uncertainty']) or 'none stated'}."
                    for o in choice["options"]
                ],
            )
        form_fields.append(field)
    definition = {"title": "Clarify the work", "fields": form_fields}
    library = require_feature("attune-forms", "attune_forms", FORMS_VERSION, "review")
    markdown = library.form_to_markdown(library.form_from_dict(definition))
    return {
        "checkpoint_digest": record["checkpoint_digest"],
        "definition": definition,
        "markdown": markdown,
        "missing": missing,
        "field_map": {f"answer_{index}": name for index, name in enumerate(missing)},
    }


def answer_planning(directory, response: dict) -> dict:
    """Bind supplied answers to the shown draft; preserve unknowns and other fields."""
    fields(response, ("schema_version", "checkpoint_digest", "answers"))
    from .review_contract import versioned

    versioned(response)
    record = read_task(directory)
    if (
        record["status"] != "draft"
        or response["checkpoint_digest"] != record["checkpoint_digest"]
    ):
        raise ValueError("Stale or accepted planning question response")
    shown = planning_questions(directory)
    if not shown["missing"]:
        raise ValueError("No material questions remain; do not repeat intake")
    answers = response["answers"]
    if not isinstance(answers, dict) or set(answers) - set(shown["field_map"]):
        raise ValueError("Unknown planning answer fields")
    supplied = {k: v for k, v in answers.items() if v is not None}
    library = require_feature("attune-forms", "attune_forms", FORMS_VERSION, "review")
    for field in shown["definition"]["fields"]:
        if field["id"] in supplied:
            library.collect_form_response(
                library.form_from_dict(
                    {"title": "Clarify the work", "fields": [field]}
                ),
                {field["id"]: supplied[field["id"]]},
                template_id="harness-work-planning-v1",
            )
    intent, choices = copy.deepcopy(record["request"]["intent"]), copy.deepcopy(
        record["request"]["choices"]
    )
    for key, value in supplied.items():
        name = shown["field_map"][key]
        bounded_text(value, "planning answer")
        if name in ("scope", "acceptance"):
            intent[name] = [line.strip() for line in value.splitlines() if line.strip()]
        elif name == "goal":
            intent["goal"] = value
        elif name.startswith("question:"):
            next(q for q in intent["questions"] if "question:" + q["id"] == name)[
                "answer"
            ] = value
        else:
            choice = next(c for c in choices if "choice:" + c["id"] == name)
            field = next(f for f in shown["definition"]["fields"] if f["id"] == key)
            choice["selected"] = choice["options"][field["options"].index(value)]["id"]
    return revise_work(
        directory,
        checkpoint=record["checkpoint_digest"],
        changes={"intent": intent, "choices": choices},
    )
