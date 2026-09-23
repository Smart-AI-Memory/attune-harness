"""Plan/build verbs over one work owner and the existing Spec decision grammar."""

import asyncio
import json
from pathlib import Path

from .features import read_text
from .recovery import UnresolvedOperation
from .review_contract import parse_json
from .task_contract import read_task
from .work_contract import SIGNALS, create_work, revise_work
from .work_runtime import (
    answer_planning,
    apply_planning_proposal,
    build_work,
    plan_work,
    planning_questions,
    reconcile_work_effect,
    work_status,
)


def add_commands(sub):
    plan = sub.add_parser(
        "plan", help="Define intent, review a proposal and accept its scope"
    )
    plan.add_argument(
        "--task-dir",
        type=Path,
        required=True,
        help="One work directory outside the project",
    )
    action = plan.add_mutually_exclusive_group()
    action.add_argument(
        "--request",
        type=Path,
        help="Create from intent/assignments JSON; no model call",
    )
    action.add_argument(
        "--answers", type=Path, help="Submit answers bound to the shown questions"
    )
    action.add_argument(
        "--decision",
        action="store_true",
        help="Retain current questions or the approval view; no approval or dispatch",
    )
    action.add_argument(
        "--revise",
        type=Path,
        help="Apply explicit JSON corrections to the current checkpoint",
    )
    action.add_argument(
        "--run",
        action="store_true",
        help="Ask configured planning participants for a proposal",
    )
    action.add_argument(
        "--stage",
        action="store_true",
        help="Stage a completed proposal as a new unaccepted draft",
    )
    action.add_argument(
        "--accept",
        action="store_true",
        help="Approve the exact --checkpoint through the Spec collector",
    )
    action.add_argument(
        "--reimport",
        action="store_true",
        help="Reimport an edited legacy artifact, losing its old grant",
    )
    plan.add_argument("--project", type=Path, help="Required with --request")
    plan.add_argument(
        "--config",
        type=Path,
        help="Explicit participant registry; required with --request",
    )
    plan.add_argument(
        "--import-plan",
        type=Path,
        help="Import legacy tasks alongside --request intent; never import approval",
    )
    plan.add_argument(
        "--preserve-completed",
        action="store_true",
        help="With --revise, retain a verified unchanged prefix",
    )
    plan.add_argument(
        "--checkpoint", help="Required for approval, staging, correction and reimport"
    )
    plan.add_argument(
        "--review-dispositions",
        type=Path,
        help="With --stage, JSON dispositions keyed by retained planning finding ID",
    )
    _dispatch_options(plan)
    build = sub.add_parser(
        "build", help="Execute the accepted plan and its protected checks"
    )
    build.add_argument("task_dir", type=Path)
    build.add_argument("--checkpoint", help="Expected current checkpoint")
    _dispatch_options(build)


def _dispatch_options(parser):
    parser.add_argument(
        "--allow-external",
        action="store_true",
        help="Authorize explicitly configured command participants",
    )
    parser.add_argument(
        "--allow-native",
        action="store_true",
        help="Separate authorization for configured native model calls",
    )
    parser.add_argument(
        "--max-operations",
        type=int,
        help="Pause after this many new durable operations",
    )


def _json(path):
    return parse_json(read_text(path, 1048576), 1048576)


def present(directory, *, inspect_only=False):
    record = read_task(directory)
    result = {
        **work_status(directory, _record=record),
        "task_directory": str(Path(record["record_path"]).parent),
        "intent": record["request"]["intent"],
        "authoring": record["request"]["authoring"],
        "tasks": record["request"]["tasks"],
        "controls": record["request"]["controls"],
        "record_path": record["record_path"],
    }
    if "legacy" in record["request"]:
        result["import_disclosures"] = record["request"]["legacy"]["unsupported"]
    if "review_handoff" in record["request"]:
        result["review_handoff"] = record["request"]["review_handoff"]
    run = record.get("build", record.get("planning", {}))
    result["phase"] = (
        "build"
        if "build" in record
        else "planning"
        if "planning" in record and record["status"] == "draft"
        else record["status"]
    )
    try:
        if inspect_only:
            from .work_build import check_build_fresh
            from .work_contract import check_work_fresh

            if "build" in record:
                check_build_fresh(record)
            else:
                check_work_fresh(record)
        if record["status"] == "draft":
            result["questions"] = planning_questions(directory)
    except (ValueError, OSError, UnresolvedOperation) as exc:
        if not inspect_only:
            raise
        result.update(status="stale", freshness_error=str(exc), questions=None)
    if "planning" in record:
        result["planning"] = record["planning"]
    if run.get("status") == "running" or any(
        e["phase"] == "dispatching" for e in run.get("events", [])
    ):
        result.update(
            status="unresolved",
            note="The owner may still be running. Inspection did not resume it.",
        )
    result["evidence"], result["advisory"] = _evidence(record)
    from .execution_evidence import work_execution_evidence

    result["execution_evidence"] = work_execution_evidence(record)
    if "error" in run:
        result["run_error"] = run["error"]
    result["summary"], result["blocking"], result["next_action"] = _guidance(
        record, result
    )
    result["note"] = result.get(
        "note",
        "Intent acceptance, execution evidence and paid dispatch permissions are separate.",
    )
    from .work_decisions import retained_decision

    decision = retained_decision(record, stale="freshness_error" in result)
    if decision is not None:
        result["decision"] = decision
    return result


def _evidence(record):
    """Small projections of validated receipts; full findings stay in the owner."""
    phase = "build" if "build" in record else "planning"
    run = record.get(phase, {})
    evidence = {"record_path": record["record_path"], "checks": [], "reviews": []}
    advisory = list(run.get("advisory", []))
    if run:
        evidence["run_pointer"] = "/" + phase

    def review(proposal, pointer, source):
        findings = proposal.get("findings", [])
        evidence["reviews"].append(
            {
                "source": source,
                "blocking_findings": sum(f["severity"] == "high" for f in findings),
                "other_findings": sum(f["severity"] != "high" for f in findings),
                "pointer": pointer,
            }
        )
        if proposal.get("notes"):
            advisory.append(
                {
                    "source": source,
                    "kind": "optional_notes",
                    "count": len(proposal["notes"]),
                    "pointer": pointer,
                }
            )

    if phase == "planning":
        for role, participant in run.get("participants", {}).items():
            if "proposal" in participant:
                review(
                    participant["proposal"],
                    f"/planning/participants/{role}/proposal",
                    role,
                )
    for index, event in enumerate(run.get("events", [])):
        if event["state"] != "completed":
            continue
        pointer = f"/{phase}/events/{index}/result"
        if event["kind"] in ("acceptance_probe", "build_control"):
            evidence["checks"].append(
                {
                    "operation": event["operation_key"],
                    "passed": event["result"]["passed"],
                    "failure": event["result"]["failure"],
                    "pointer": pointer,
                }
            )
        elif phase == "build" and event["kind"] == "participant_turn":
            for key, participant in run.get("participants", {}).items():
                if participant["attempt_id"] != event["attempt_id"]:
                    continue
                from .work_build import build_response_contract, decode

                role, _, task_id = key.partition(":")
                step = next(
                    (t for t in record["request"]["tasks"] if t["id"] == task_id),
                    {"id": "final"},
                )
                try:
                    proposal = decode(
                        event["result"]["action"],
                        record["request"],
                        role,
                        step,
                        contract_version=build_response_contract(run),
                    )
                except ValueError as exc:
                    evidence["rejected_reply"] = {
                        "source": role,
                        "detail": str(exc),
                        "pointer": pointer + "/action/text",
                    }
                else:
                    if role == "reviewer":
                        review(proposal, pointer + "/action/text", role)
                break
    return evidence, advisory


def _guidance(record, result):
    """Presentation precedence only; authority and recovery remain with the owner."""
    run = record.get("build", record.get("planning", {}))
    phase = result["phase"]
    state = result["status"]
    failed = [c for c in result["evidence"]["checks"] if not c["passed"]]
    required = {c["id"] for c in record["request"]["controls"] if c["required"]}
    blocking_checks = [
        c
        for c in failed
        if c["operation"].startswith("probe:")
        or c["operation"].removeprefix("control:") in required
    ]
    uncertain = (
        run.get("status") == "running"
        or any(e["phase"] == "dispatching" for e in run.get("events", []))
        or any(c["failure"] != "nonzero_exit" for c in failed)
        or (run.get("status") == "unresolved" and not blocking_checks)
    )
    if uncertain:
        return (
            "Execution is uncertain; saved evidence does not establish a safe retry.",
            True,
            "Inspect the saved journal and any running owner before acting. Reconcile only supported file observations with reconcile-task; do not blindly retry calls or checks.",
        )
    if "freshness_error" in result:
        action = (
            "Inspect changed files and saved evidence. Retain the build journal; ordinary rebasing is unsupported. Resolve the mismatch before further work."
            if "build" in record
            else "Inspect changed inputs and refresh the draft with plan --revise (or --reimport for an edited legacy plan), using this checkpoint and a current effect manifest where needed. Review the new draft before acceptance."
        )
        return (
            "Saved evidence is stale; it cannot authorize the next action or establish current completion.",
            True,
            action,
        )
    if blocking_checks:
        return (
            "A required control or protected check failed; progress is blocked.",
            True,
            "Inspect the failed check in the saved evidence and correct the cause within approved scope. Retain verified completion; resume does not rerun a settled failed check. Use a supported correction and new acceptance before further execution.",
        )
    if "rejected_reply" in result["evidence"]:
        return (
            "A saved participant reply fails the response contract; progress is blocked.",
            True,
            "Inspect the rejected reply and its validation detail in the saved evidence. Use a supported correction or new accepted scope; resume will not replace the saved reply.",
        )
    if state == "unresolved":
        return (
            "Execution remains unresolved.",
            True,
            "Inspect and reconcile the saved operation before further execution; do not blindly retry.",
        )
    if phase == "accepted":
        from .features import FeatureUnavailable
        from .work_build import preflight

        try:
            preflight(record["request"])
        except (ValueError, FeatureUnavailable) as exc:
            result["readiness_error"] = str(exc)
            return (
                "Work scope is accepted, but build requirements are unavailable or incomplete.",
                True,
                "Inspect readiness_error. Supply the required tasks, runners and verification in a corrected draft, then obtain acceptance for the new checkpoint before build.",
            )
        return (
            "Work scope is accepted and ready for build.",
            False,
            "Use build with this task directory and --checkpoint, supplying only explicitly authorized dispatch flags.",
        )
    if state == "completed":
        if phase == "planning":
            return (
                "Planning proposal completed; work is still a draft.",
                True,
                "Review the proposal, then use plan --stage with this checkpoint; review the staged draft before acceptance.",
            )
        from .work_build import PROFILE

        if run.get("profile") != PROFILE:
            return (
                "File effects completed; dependent build verification is not established.",
                False,
                "Inspect the saved effect evidence before deciding on further verification.",
            )
        return (
            "Build completed: protected checks passed and no high-severity reviewer finding blocks completion.",
            False,
            "Review the saved checks, reviewer findings and any optional advice. No build retry is needed; passing checks do not prove every semantic claim.",
        )
    if state == "paused":
        from .work_effects import PROFILE as EFFECT_PROFILE

        if run.get("profile") == EFFECT_PROFILE:
            return (
                "File effects paused; the saved batch is incomplete.",
                False,
                "Inspect the saved batch and continue through its owning file-effect API. Dependent build/resume cannot take over this journal.",
            )
        return (
            f"{phase.capitalize()} paused at a saved operation boundary; progress is retained.",
            False,
            "Use resume with this task directory and --checkpoint, retaining the saved dispatch permissions, when ready to continue within the accepted allowance.",
        )
    if state == "needs_revision":
        return (
            "The planning critic reported a high-severity finding; revision is required."
            if phase == "planning"
            else "The reviewer reported a high-severity finding; revision is required.",
            True,
            "Inspect the retained findings and their evidence. Resolve them in a supported correction before staging or further execution; repeating the settled run will not clear them.",
        )
    if state in ("failed", "unavailable", "cancelled"):
        return (
            f"{phase.capitalize()} {state}; completion is not established.",
            True,
            "Inspect the saved error and journal. Correct the cause through a supported revision or new accepted scope; repeating a terminal run will not repair it.",
        )
    if result["missing"]:
        return (
            "Work needs missing intent or decisions before acceptance.",
            True,
            "Supply the missing answers against this checkpoint using plan --answers.",
        )
    from .work_accept import SPEC_APPROVAL
    from .work_contract import _supported

    supported = [SPEC_APPROVAL] + [
        c["control"]
        for c in record["request"].get("effects", {}).get("checks", [])
        if c["control"] != SPEC_APPROVAL
    ]
    try:
        _supported(record["request"]["controls"], supported)
        if not any(a["role"] == "planner" for a in record["request"]["assignments"]):
            raise ValueError("A planner assignment is required")
    except ValueError as exc:
        result["readiness_error"] = str(exc)
        return (
            "Draft acceptance is blocked by an unavailable required control or assignment.",
            True,
            "Inspect readiness_error and correct the draft's required controls or assignments before requesting acceptance.",
        )
    return (
        "Draft ready for review; work is not yet accepted.",
        True,
        "Review this work record; use plan --accept with this exact --checkpoint.",
    )


async def _accept(directory, checkpoint):
    from .work_accept import WorkAcceptance

    record = read_task(directory)
    if checkpoint != record["checkpoint_digest"]:
        raise ValueError("Approval requires the exact displayed work checkpoint")
    runners = record["request"].get("effects", {}).get("checks", [])
    supported = [c["control"] for c in runners]
    # The forms package renders the decision; without the review extra the
    # host's loader raises FeatureUnavailable with the install hint.
    acceptance = WorkAcceptance(directory, supported_controls=supported)
    view = await acceptance.open(
        detail="Explicit console approval of the current work intent."
    )
    state = view.record.state
    if state.stage != "task_gate":
        # The execution gate did not pass (D24): the first blocking receipt's
        # words are the refusal, the words the bind refused with before.
        blocked = [r.detail for r in state.lifecycle_receipts if r.state in ("BLOCKED", "REVISE")]
        raise ValueError(blocked[0] if blocked else "Spec execution gate awaits the chair")
    response = {
        "__elicitation_response__": True,
        "title": view.record.view.title,
        "view": view.record.view.id.value,
        "action": "approve_task",
        "confirmed": False,
        **view.record.binding.to_payload(),
    }
    receipt, accepted = await acceptance.collect(response)
    if accepted is None:
        raise ValueError("Spec did not grant work authority")
    return {"decision_markdown": view.render.markdown, "receipt": dict(receipt.result)}


async def _preview_decision(directory, checkpoint):
    from .work_accept import WorkAcceptance
    from .work_decisions import retain_questions

    record = read_task(directory)
    if record["status"] != "draft":
        raise ValueError("Decision preview requires a draft")
    if checkpoint is not None and checkpoint != record["checkpoint_digest"]:
        raise ValueError("Decision preview requires the current checkpoint")
    shown = planning_questions(directory)
    if shown["missing"]:
        retain_questions(record, shown)
    else:
        if "planning" in record:
            raise ValueError(
                "Resolve or stage the planning run before previewing acceptance"
            )
        supported = [
            c["control"] for c in record["request"].get("effects", {}).get("checks", [])
        ]
        await WorkAcceptance(directory, supported_controls=supported).open()


def execute(args):
    """Explicit verbs never choose a participant, spend budget or accept by default."""
    try:
        extra = {}
        if args.command == "build":
            build_work(
                args.task_dir,
                checkpoint=args.checkpoint,
                allow_external=args.allow_external,
                allow_native=args.allow_native,
                max_operations=args.max_operations,
            )
        else:
            if args.review_dispositions is not None and not args.stage:
                raise ValueError("--review-dispositions requires --stage")
            if args.preserve_completed and args.revise is None:
                raise ValueError("--preserve-completed requires --revise")
            if args.request is None and any(
                (args.project, args.config, args.import_plan)
            ):
                raise ValueError("Creation options require --request")
            if not args.run and (
                args.allow_external
                or args.allow_native
                or args.max_operations is not None
            ):
                raise ValueError("Dispatch options require an explicit --run")
            if args.request is not None:
                if (
                    args.project is None
                    or args.config is None
                    or args.checkpoint is not None
                ):
                    raise ValueError(
                        "New work requires --project and --config, without an old checkpoint"
                    )
                data = _json(args.request)
                allowed = {
                    "intent",
                    "signals",
                    "choices",
                    "assignments",
                    "controls",
                    "tasks",
                    "inputs",
                    "artifact",
                    "budget",
                    "effects",
                }
                if (
                    not isinstance(data, dict)
                    or set(data) - allowed
                    or "intent" not in data
                ):
                    raise ValueError(
                        "Request must contain intent and supported authoring fields"
                    )
                if args.import_plan:
                    from .work_accept import import_plan

                    if set(data) - {"intent", "assignments", "controls", "budget"}:
                        raise ValueError(
                            "Legacy import derives tasks and artifact provenance"
                        )
                    import_plan(
                        args.project,
                        args.config,
                        path=args.import_plan,
                        directory=args.task_dir,
                        **data,
                    )
                else:
                    data.setdefault(
                        "signals",
                        {**dict.fromkeys(SIGNALS, False), "existing_artifact": None},
                    )
                    create_work(
                        args.project, args.config, directory=args.task_dir, **data
                    )
            elif args.decision:
                asyncio.run(_preview_decision(args.task_dir, args.checkpoint))
            elif args.answers:
                if args.checkpoint:
                    raise ValueError("Answers carry their own checkpoint")
                answer_planning(args.task_dir, _json(args.answers))
            elif args.run:
                plan_work(
                    args.task_dir,
                    checkpoint=args.checkpoint,
                    allow_external=args.allow_external,
                    allow_native=args.allow_native,
                    max_operations=args.max_operations,
                )
            elif args.stage or args.accept or args.revise or args.reimport:
                if not args.checkpoint:
                    raise ValueError(
                        "This action requires --checkpoint from the displayed work"
                    )
                if args.stage:
                    apply_planning_proposal(
                        args.task_dir,
                        checkpoint=args.checkpoint,
                        review_dispositions=(
                            _json(args.review_dispositions)
                            if args.review_dispositions is not None
                            else None
                        ),
                    )
                elif args.accept:
                    extra = asyncio.run(_accept(args.task_dir, args.checkpoint))
                elif args.reimport:
                    from .work_accept import reimport_plan

                    reimport_plan(args.task_dir, checkpoint=args.checkpoint)
                else:
                    revise_work(
                        args.task_dir,
                        checkpoint=args.checkpoint,
                        changes=_json(args.revise),
                        preserve_completed=args.preserve_completed,
                    )
        result = {**present(args.task_dir), **extra}
        if (
            args.command == "plan"
            and any(
                (
                    args.request,
                    args.answers,
                    args.revise,
                    args.reimport,
                    args.stage,
                    args.run,
                )
            )
            and result.get("questions", {}).get("missing")
        ):
            from .work_decisions import retain_questions, retained_decision

            record = read_task(args.task_dir)
            retain_questions(record, result["questions"])
            result["decision"] = retained_decision(record)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return exit_code(result)
    except Exception as exc:
        return _error(exc, args.task_dir)


def exit_code(result):
    if result["status"] in ("draft", "accepted", "completed", "needs_input"):
        return 0
    return 1 if result["status"] in ("paused", "cancelled") else 2


def _error(exc, directory=None):
    result = {
        "status": "unresolved" if isinstance(exc, UnresolvedOperation) else "failed",
        "error": {"type": type(exc).__name__, "detail": str(exc)},
        "summary": "The requested action could not complete; inspect the error before continuing.",
        "blocking": True,
        "next_action": "Inspect the error and any saved journal before choosing a valid action. Do not blindly retry uncertain operations.",
    }
    try:
        current = present(directory, inspect_only=True) if directory else None
    except Exception:
        current = None  # Never conceal the original failure with an inspection error.
    if current:
        result.update(record_path=current["record_path"], evidence=current["evidence"])
        for key in ("readiness_error", "freshness_error"):
            if key in current:
                result[key] = current[key]
        if current["blocking"] and (
            current["status"]
            in (
                "stale",
                "unresolved",
                "needs_revision",
                "failed",
                "unavailable",
                "cancelled",
            )
            or "readiness_error" in current
        ):
            result["next_action"] = current["next_action"]
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 2


def execute_control(args):
    """Route existing control verbs to their qualified feature-work operations."""
    try:
        if args.command == "resume":
            from .task_policies import execute_task

            execute_task(
                args.task_dir,
                checkpoint=args.checkpoint,
                max_operations=args.max_operations,
                allow_external=args.allow_external,
                allow_native=args.allow_native,
            )
        elif args.command == "reconcile-task":
            if (
                args.reply
                or args.retry_read_only
                or not (args.observe_file or args.retry_before)
            ):
                raise ValueError(
                    "Feature work currently reconciles explicit file observations only"
                )
            if not args.checkpoint:
                raise ValueError(
                    "Feature reconciliation requires the current --checkpoint"
                )
            reconcile_work_effect(
                args.task_dir,
                args.checkpoint,
                args.event,
                retry_before=args.retry_before,
            )
        elif args.command != "status":
            raise ValueError(
                "This control is not qualified for feature work; pause at a durable operation boundary"
            )
        result = present(args.task_dir, inspect_only=args.command == "status")
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0 if args.command == "status" else exit_code(result)
    except Exception as exc:
        return _error(exc, args.task_dir)
