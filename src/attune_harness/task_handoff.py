"""Bind a completed repair to a separately accepted testing task."""

from pathlib import Path
import re

from .review_contract import bounded_text, digest, fields, parse_json, versioned


ASSESSMENT_FINDINGS_PROFILE = "assessment-findings-v1"
ASSESSMENT_SEVERITIES = ("low", "medium", "high")


def validate_assessment_payload(value: dict) -> dict:
    """Validate the optional structured result without granting repair authority."""
    fields(value, ("schema_version", "kind", "findings", "notes"))
    versioned(value)
    if value["kind"] != ASSESSMENT_FINDINGS_PROFILE:
        raise ValueError("Unsupported assessment result profile")
    if not isinstance(value["findings"], list) or len(value["findings"]) > 32:
        raise ValueError("Assessment findings must be a bounded list")
    if not isinstance(value["notes"], list) or len(value["notes"]) > 16:
        raise ValueError("Assessment notes must be a bounded list")
    for note in value["notes"]:
        bounded_text(note, "assessment note")
    seen = set()
    for finding in value["findings"]:
        fields(finding, ("id", "severity", "text", "evidence"))
        bounded_text(finding["id"], "assessment finding id", 64)
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", finding["id"]):
            raise ValueError("Assessment finding ID must be a stable lowercase identifier")
        bounded_text(finding["text"], "assessment finding")
        if finding["id"] in seen:
            raise ValueError("Duplicate assessment finding ID")
        seen.add(finding["id"])
        if finding["severity"] not in ASSESSMENT_SEVERITIES:
            raise ValueError("Invalid assessment finding severity")
        evidence = finding["evidence"]
        if not isinstance(evidence, list) or not evidence or len(evidence) > 8:
            raise ValueError("Assessment finding needs bounded explicit evidence")
        for item in evidence:
            bounded_text(item, "assessment finding evidence")
    return value


def completed_assessment(
    directory: Path,
    finding_ids: list[str],
    *,
    repair_scope: dict | None = None,
    _repair_record: dict | None = None,
) -> tuple[Path, dict]:
    """Bind selected findings to the actual completed assessment journal."""
    from .task_contract import PROFILE, check_fresh, read_task, safe_storage
    from .task_policies import AssessmentPolicy

    directory = safe_storage(directory)
    task = read_task(directory)
    request = task["request"]
    if (
        task["task_profile"] != PROFILE
        or "repair" in request
        or request.get("result_profile") != ASSESSMENT_FINDINGS_PROFILE
        or task["status"] != "completed"
    ):
        raise ValueError("Repair handoff requires a completed structured assessment")
    if (
        not isinstance(finding_ids, list)
        or not finding_ids
        or len(finding_ids) > 32
        or any(not isinstance(value, str) or not value for value in finding_ids)
        or len(finding_ids) != len(set(finding_ids))
    ):
        raise ValueError("Select unique assessment finding IDs")
    if _repair_record is None:
        check_fresh(task)
    else:
        from .assessment_effects import check_fresh as check_effect_fresh
        frozen = _repair_record['request']['repair']['source_assessment']['index_identity']
        check_effect_fresh(task, _repair_record, frozen)
    run = task["execution"]
    if run.get("integration") != AssessmentPolicy(task).integrate(run):
        raise ValueError("Assessment integration differs from its owner projection")
    assignments = run["recovery"]["assignments"]
    results = []
    findings = {}
    for role, assignment in assignments.items():
        participant = run["participants"].get(role, {})
        events = [
            event
            for event in run["events"]
            if event.get("kind") == "participant_turn"
            and event.get("participant_id") == assignment["participant_id"]
            and event.get("attempt_id") == assignment["attempt_id"]
        ]
        if len(events) != 1:
            raise ValueError("Assessment lacks a unique completed participant result")
        event = events[0]
        action = event.get("result", {}).get("action", {})
        if (
            event.get("state") != "completed"
            or action.get("kind") != "final"
            or participant.get("participant_id") != assignment["participant_id"]
            or participant.get("attempt_id") != assignment["attempt_id"]
            or participant.get("status") != "completed"
            or participant.get("text") != action.get("text")
        ):
            raise ValueError("Assessment participant summary differs from its journal")
        payload = validate_assessment_payload(parse_json(action["text"]))
        results.append(
            {
                "role": role,
                "participant_id": assignment["participant_id"],
                "attempt_id": assignment["attempt_id"],
                "event_id": event["event_id"],
                "payload": payload,
            }
        )
        for finding in payload["findings"]:
            finding_id = finding["id"]
            if finding_id in findings:
                raise ValueError("Assessment finding IDs are ambiguous across participants")
            findings[finding_id] = {
                **finding,
                "role": role,
                "participant_id": assignment["participant_id"],
                "attempt_id": assignment["attempt_id"],
                "event_id": event["event_id"],
            }
    unknown = [finding_id for finding_id in finding_ids if finding_id not in findings]
    if unknown:
        raise ValueError("Selected assessment finding is unavailable")
    overlapping = repair_scope is not None and _assessment_input_overlap(request, repair_scope)
    binding = {
        "kind": "completed-assessment-v1",
        "record_path": task["record_path"],
        "task_id": request["task_id"],
        "project_root": request["project_root"],
        "request_digest": digest(request),
        "checkpoint_digest": task["checkpoint_digest"],
        "result_digest": digest(results),
        "findings": [findings[finding_id] for finding_id in finding_ids],
    }
    if overlapping:
        from .assessment_effects import PROFILE as effects_profile, index_identity
        binding.update(kind=effects_profile, effect_scope_digest=digest(repair_scope),
                       index_identity=index_identity(request['registry'].get('retrieval')))
    validate_assessment_handoff(binding)
    return Path(request["project_root"]), binding


def _assessment_input_overlap(request: dict, repair_scope: dict) -> bool:
    root = Path(repair_scope["root"])
    allowed = {(root / path).resolve() for path in repair_scope["allowed"]}
    evidence = request["evidence"]
    if 'context' in evidence and Path(evidence['context']['path']).resolve() in allowed:
        raise ValueError('Verification context is immutable repair authority')
    captured = {
        Path(value["path"]).resolve()
        for name, value in evidence.items()
        if name in ("document", "context")
    }
    retrieval = evidence.get("retrieval")
    if retrieval and retrieval["mode"] == "keyword":
        corpus = Path(retrieval["root"]).resolve()
        captured.update((corpus / path).resolve() for path in retrieval["sources"])
    elif retrieval and retrieval["mode"] == "voyage":
        from .voyage_index import read_generation
        selection = request['registry']['retrieval']
        _, metadata = read_generation(selection['config'], selection['generation'])
        roots = {item['repo_id']: Path(item['root']).resolve()
                 for item in metadata['manifest']['repositories']}
        captured.update((roots[item['repo_id']] / item['path']).resolve()
                        for item in metadata['manifest']['files'])
    return bool(allowed & captured)


def _reject_assessment_input_overlap(request: dict, repair_scope: dict) -> None:
    if _assessment_input_overlap(request, repair_scope):
        raise ValueError("Repair scope overlaps immutable assessment evidence")


def validate_assessment_handoff(binding: dict) -> None:
    from .assessment_effects import PROFILE as effects_profile
    effect_aware = binding.get('kind') == effects_profile
    fields(
        binding,
        (
            "kind",
            "record_path",
            "task_id",
            "project_root",
            "request_digest",
            "checkpoint_digest",
            "result_digest",
            "findings",
            *(['effect_scope_digest', 'index_identity'] if effect_aware else []),
        ),
    )
    if (
        binding["kind"] not in ("completed-assessment-v1", effects_profile)
        or not isinstance(binding["record_path"], str)
        or not Path(binding["record_path"]).is_absolute()
        or Path(binding["record_path"]).name != "record.json"
        or not isinstance(binding["task_id"], str)
        or not binding["task_id"]
        or not isinstance(binding["project_root"], str)
        or not Path(binding["project_root"]).is_absolute()
        or not isinstance(binding["findings"], list)
        or not binding["findings"]
        or len(binding["findings"]) > 32
    ):
        raise ValueError("Invalid assessment handoff identity")
    for name in ("request_digest", "checkpoint_digest", "result_digest",
                 *(['effect_scope_digest'] if effect_aware else [])):
        if not isinstance(binding[name], str) or not re.fullmatch("[0-9a-f]{64}", binding[name]):
            raise ValueError("Invalid assessment handoff digest")
    if effect_aware and binding['index_identity'] is not None:
        index = binding['index_identity']
        fields(index, ('selection_digest', 'publication_sha256', 'receipt_sha256', 'metadata_digest'))
        if any(not isinstance(v, str) or not re.fullmatch('[0-9a-f]{64}', v) for v in index.values()):
            raise ValueError('Invalid historical index identity')
    selected = set()
    for finding in binding["findings"]:
        fields(
            finding,
            (
                "id",
                "severity",
                "text",
                "evidence",
                "role",
                "participant_id",
                "attempt_id",
                "event_id",
            ),
        )
        validate_assessment_payload(
            {
                "schema_version": 1,
                "kind": ASSESSMENT_FINDINGS_PROFILE,
                "findings": [
                    {key: finding[key] for key in ("id", "severity", "text", "evidence")}
                ],
                "notes": [],
            }
        )
        for name in ("role", "participant_id", "attempt_id", "event_id"):
            bounded_text(finding[name], f"assessment finding {name}")
        if finding["id"] in selected:
            raise ValueError("Duplicate selected assessment finding")
        selected.add(finding["id"])


def check_assessment_handoff(request: dict, *, record: dict | None = None) -> None:
    binding = request["repair"].get("source_assessment")
    if binding is None:
        return
    validate_assessment_handoff(binding)
    from .assessment_effects import PROFILE as effects_profile
    effect_aware = binding['kind'] == effects_profile
    if effect_aware:
        if record is None or record['request'] != request:
            raise ValueError('Effect-aware assessment requires its repair owner')
        if binding['effect_scope_digest'] != digest(request['repair']['scope']):
            raise ValueError('Effect-aware assessment is bound to another repair scope')
    else:
        from .task_contract import read_task
        source = read_task(Path(binding['record_path']).parent)
        _reject_assessment_input_overlap(source['request'], request['repair']['scope'])
    current_project, current = completed_assessment(
        Path(binding["record_path"]).parent,
        [finding["id"] for finding in binding["findings"]],
        repair_scope=request["repair"]["scope"],
        _repair_record=record if effect_aware else None,
    )
    if current != binding or str(current_project) != request["project_root"]:
        raise ValueError("Stale or foreign assessment handoff; create a new repair task")


def completed_source(directory: Path) -> tuple[Path, list[str], dict]:
    """Normalize missing/uncertain producer evidence at the existing Spec boundary."""
    from .recovery import UnresolvedOperation

    try:
        return _completed_source(directory)
    except (KeyError, TypeError, UnresolvedOperation) as exc:
        raise ValueError(
            f"Invalid or stale completed producer evidence: {exc}"
        ) from exc


def _completed_source(directory: Path) -> tuple[Path, list[str], dict]:
    """Dispatch qualified repair/feature producers without inventing test authority."""
    from .task_contract import read_task, safe_storage

    directory = safe_storage(directory)
    task = read_task(directory)
    if task.get("task_profile") != "feature-work-v1":
        return completed_repair(directory)
    from .work_build import PROFILE, check_build_fresh, validate_build
    from .work_effects import expected_snapshot

    run = task.get("build", {})
    if (
        task["status"] != "accepted"
        or run.get("profile") != PROFILE
        or run.get("status") != "completed"
    ):
        raise ValueError("Testing handoff requires a completed dependent build")
    request = task["request"]
    verified = validate_build(run, request)
    check_build_fresh(task)
    artifact = digest(expected_snapshot(request["effects"], run["events"]))
    if (
        verified is None
        or not verified["probe"]["passed"]
        or verified["probe"]["artifact_digest"] != artifact
    ):
        raise ValueError("Feature handoff lacks its current protected verification")
    binding = {
        "kind": "completed-feature-v1",
        "record_path": task["record_path"],
        "task_id": request["task_id"],
        "request_digest": digest(request),
        "checkpoint_digest": task["checkpoint_digest"],
        "artifact_digest": artifact,
        "probe_digest": digest(verified["probe"]),
    }
    scope = set(request["effects"]["allowed"])
    from .work_runtime import completed_steps

    for historical in task["history"]:
        completed = completed_steps(historical)
        for step in historical["request"]["tasks"]:
            if step["id"] in completed:
                scope.update(
                    p for p in step["outputs"] if p in request["effects"]["protected"]
                )
    return Path(request["project_root"]), sorted(scope), binding


def completed_repair(directory: Path) -> tuple[Path, list[str], dict]:
    """Read current host-owned repair evidence without dispatch or new authority."""
    from .recovery import UnresolvedOperation

    try:
        return _completed_repair(directory)
    except (KeyError, TypeError, UnresolvedOperation) as exc:
        raise ValueError(f"Invalid or stale completed repair evidence: {exc}") from exc


def _completed_repair(directory: Path) -> tuple[Path, list[str], dict]:
    from .repair import expected_snapshot
    from .task_contract import PROFILE, check_fresh, read_task, safe_storage

    directory = safe_storage(directory)
    task = read_task(directory)
    request = task["request"]
    if (
        task["task_profile"] != PROFILE
        or "repair" not in request
        or task["status"] != "completed"
    ):
        raise ValueError("Testing handoff requires a completed repair task")
    check_fresh(task)
    run = task["execution"]
    integrated = run.get("integration", {})
    scope = request["repair"]["scope"]
    artifact = digest(expected_snapshot(scope, run["events"]))
    _check_probe(run, scope, "before", digest(scope["before"]))
    probe = _check_probe(run, scope, "after", artifact)
    if (
        integrated.get("acceptance_status") != "verified_within_probe_scope"
        or probe.get("passed") is not True
        or run.get("before_probe", {}).get("passed") is not False
        or integrated.get("artifact_digest") != artifact
        or integrated.get("probe_digest") != digest(probe)
        or integrated.get("review_policy") != request["repair"]["review"]
    ):
        raise ValueError(
            "Repair handoff lacks current artifact/probe acceptance evidence"
        )
    if request["repair"]["review"] != "none":
        review = run.get("review", {})
        _check_review(run, review)
        if (
            review.get("verdict") != "approve"
            or review.get("findings") != []
            or review.get("artifact_digest") != artifact
            or review.get("probe_digest") != digest(probe)
            or integrated.get("review") != review
        ):
            raise ValueError("Repair handoff lacks its accepted independent review")
    # The completed patch was host-validated and the final snapshot rechecked above.
    changed = sorted(item["path"] for item in run["patch"]["replacements"])
    if (
        not changed
        or len(changed) != len(set(changed))
        or not set(changed) <= set(scope["allowed"])
    ):
        raise ValueError("Repair handoff has invalid replacement scope")
    applied = [
        event["patch"]
        for event in run["events"]
        if event["kind"] == "replacement" and event["state"] == "completed"
    ]
    if sorted(applied, key=lambda item: item["path"]) != sorted(
        run["patch"]["replacements"], key=lambda item: item["path"]
    ):
        raise ValueError(
            "Repair handoff patch differs from completed replacement evidence"
        )
    binding = {
        "kind": "completed-repair-v1",
        "record_path": task["record_path"],
        "task_id": request["task_id"],
        "request_digest": digest(request),
        "checkpoint_digest": task["checkpoint_digest"],
        "artifact_digest": artifact,
        "probe_digest": digest(probe),
    }
    return Path(scope["root"]), changed, binding


def _check_probe(run: dict, scope: dict, phase: str, artifact: str) -> dict:
    """A summary cannot substitute for the probe actually journaled by the host."""
    probe = run[f"{phase}_probe"]
    events = [
        event for event in run["events"] if event["operation_key"] == f"probe:{phase}"
    ]
    if len(events) != 1:
        raise ValueError("Repair handoff lacks a unique journaled probe")
    event = events[0]
    passed = phase == "after"
    if (
        event["kind"] != "acceptance_probe"
        or event["state"] != "completed"
        or event["result"] != probe
        or event["plan_digest"] != digest(scope)
        or event["artifact_digest"] != artifact
        or probe["plan_digest"] != digest(scope)
        or probe["artifact_digest"] != artifact
        or probe["argv"] != scope["probe"]["argv"]
        or probe["passed"] is not passed
        or type(probe["returncode"]) is not int
        or (probe["returncode"] != 0 if passed else probe["returncode"] <= 0)
        or probe["failure"] != (None if passed else "nonzero_exit")
    ):
        raise ValueError(
            "Repair handoff probe summary contradicts its journal or outcome"
        )
    return probe


def _check_review(run: dict, review: dict) -> None:
    """Require the recorded reviewer response, projection and summary to agree."""
    assignment = run["recovery"]["assignments"]["reviewer"]
    participant = run["participants"]["reviewer"]
    events = [
        event
        for event in run["events"]
        if event["operation_key"] == assignment["attempt_id"] + ":turn:0"
    ]
    if len(events) != 1:
        raise ValueError("Repair handoff lacks its journaled reviewer response")
    event = events[0]
    if (
        event["kind"] != "participant_turn"
        or event["state"] != "completed"
        or any(
            event[name] != assignment[name] or participant[name] != assignment[name]
            for name in ("participant_id", "attempt_id")
        )
        or participant["status"] != "completed"
        or event["result"]["action"]["kind"] != "final"
        or event["result"]["action"]["text"] != participant["text"]
        or parse_json(participant["text"]) != review
    ):
        raise ValueError(
            "Repair handoff review summary contradicts its journaled response"
        )


def validate_handoff(binding: dict) -> None:
    """Validate the additive reference without reading or granting its authority."""
    fields(
        binding,
        (
            "kind",
            "record_path",
            "task_id",
            "request_digest",
            "checkpoint_digest",
            "artifact_digest",
            "probe_digest",
        ),
    )
    if (
        binding["kind"] not in ("completed-repair-v1", "completed-feature-v1")
        or not isinstance(binding["record_path"], str)
        or not Path(binding["record_path"]).is_absolute()
        or Path(binding["record_path"]).name != "record.json"
        or not isinstance(binding["task_id"], str)
        or not binding["task_id"]
    ):
        raise ValueError("Invalid repair handoff identity")
    for name in (
        "request_digest",
        "checkpoint_digest",
        "artifact_digest",
        "probe_digest",
    ):
        if not isinstance(binding[name], str) or not re.fullmatch(
            "[0-9a-f]{64}", binding[name]
        ):
            raise ValueError("Invalid repair handoff digest")


def check_handoff(request: dict) -> None:
    """Reject a changed producer or an overridden checkout/scope on every reuse."""
    if "source_task" not in request:
        return
    binding = request["source_task"]
    validate_handoff(binding)
    root, changed, current = completed_source(Path(binding["record_path"]).parent)
    if (
        current != binding
        or str(root) != request["project_root"]
        or changed != request["selection"]["scope"]
    ):
        raise ValueError(
            "Stale or overridden repair handoff; create a new accepted test task"
        )
