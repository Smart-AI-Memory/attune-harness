"""Validated planning-review context carried into an accepted dependent build."""

import copy

from .review_contract import bounded_text, digest, fields


DISPOSITIONS = ("advisory", "address", "dismissed")


def target_binding(request: dict) -> dict:
    """Bind only the staged semantics named by the review-handoff contract."""
    return {
        key: copy.deepcopy(request[key])
        for key in ("intent", "tasks", "inputs", "artifact", "evidence")
    }


def _source_binding(request: dict, run: dict) -> dict:
    critique = run["participants"]["critic"]
    return {
        "task_id": request["task_id"],
        "revision": request["revision"],
        "participant": critique["participant_id"],
        "proposal_digest": digest(critique["proposal"]),
    }


def _validate_source(source: dict) -> None:
    fields(source, ("task_id", "revision", "participant", "proposal_digest"))
    bounded_text(source["task_id"], "review source task", 64)
    if type(source["revision"]) is not int or source["revision"] < 1:
        raise ValueError("Invalid review source revision")
    bounded_text(source["participant"], "review source participant", 64)
    if (
        not isinstance(source["proposal_digest"], str)
        or len(source["proposal_digest"]) != 64
        or any(c not in "0123456789abcdef" for c in source["proposal_digest"])
    ):
        raise ValueError("Invalid review source proposal digest")


def validate_shape(handoff: dict, request: dict) -> None:
    """Validate the extension and its current target without consulting sources."""
    fields(handoff, ("version", "target_digest", "source", "findings", "notes"))
    if type(handoff["version"]) is not int or handoff["version"] != 1:
        raise ValueError("Unsupported review_handoff version")
    if handoff["target_digest"] != digest(target_binding(request)):
        raise ValueError("Stale review_handoff target; stage again or clear it explicitly")
    _validate_source(handoff["source"])
    task_ids = {task["id"] for task in request["tasks"]}
    findings = handoff["findings"]
    if not isinstance(findings, list) or len(findings) > 32:
        raise ValueError("review_handoff findings must be a bounded list")
    seen = set()
    for finding in findings:
        fields(
            finding,
            (
                "id",
                "severity",
                "text",
                "evidence",
                "disposition",
                "rationale",
                "task_ids",
                "archived",
                "source",
            ),
        )
        bounded_text(finding["id"], "review finding id", 64)
        bounded_text(finding["text"], "review finding")
        if finding["id"] in seen:
            raise ValueError("Duplicate review_handoff finding")
        seen.add(finding["id"])
        if finding["severity"] not in ("low", "medium", "high"):
            raise ValueError("Invalid review_handoff severity")
        evidence = finding["evidence"]
        if (
            not isinstance(evidence, list)
            or not evidence
            or len(evidence) > 64
            or len(evidence) != len(set(evidence))
        ):
            raise ValueError("Review finding needs unique explicit evidence")
        for item in evidence:
            bounded_text(item, "review finding evidence")
        disposition = finding["disposition"]
        if disposition not in DISPOSITIONS:
            raise ValueError("Unknown review_handoff disposition")
        rationale = finding["rationale"]
        if disposition == "advisory":
            if rationale is not None:
                raise ValueError("Advisory review disposition cannot invent a rationale")
        else:
            bounded_text(rationale, "review disposition rationale")
        selected = finding["task_ids"]
        if (
            not isinstance(selected, list)
            or len(selected) > 32
            or len(selected) != len(set(selected))
            or set(selected) - task_ids
        ):
            raise ValueError("Review disposition names unknown or duplicate tasks")
        if type(finding["archived"]) is not bool or finding["archived"] != (
            not selected
        ):
            raise ValueError("Archived review findings must have no current task targets")
        if finding["source"] != handoff["source"]:
            raise ValueError("Review finding source differs from its retained critique")
        _validate_source(finding["source"])
    notes = handoff["notes"]
    if not isinstance(notes, list) or len(notes) > 64:
        raise ValueError("review_handoff notes must be a bounded list")
    for note in notes:
        fields(note, ("text", "source"))
        bounded_text(note["text"], "review advice")
        if note["source"] != handoff["source"]:
            raise ValueError("Review note source differs from its retained critique")
        _validate_source(note["source"])


def validate_source(handoff: dict, request: dict, history: list) -> None:
    """Require a complete, ordered projection of the retained critic proposal."""
    validate_shape(handoff, request)
    source = handoff["source"]
    if source["task_id"] != request["task_id"]:
        raise ValueError("Review source belongs to another work owner")
    item = next(
        (
            historical
            for historical in history
            if historical["request"]["revision"] == source["revision"]
        ),
        None,
    )
    run = item.get("planning", {}) if item is not None else {}
    critic = run.get("participants", {}).get("critic", {})
    proposal = critic.get("proposal")
    if (
        item is None
        or item["request"]["task_id"] != source["task_id"]
        or run.get("status") != "completed"
        or critic.get("status") != "completed"
        or critic.get("participant_id") != source["participant"]
        or not isinstance(proposal, dict)
        or digest(proposal) != source["proposal_digest"]
    ):
        raise ValueError("review_handoff source is missing, stale or foreign")
    projected_findings = [
        {key: finding[key] for key in ("id", "severity", "text", "evidence")}
        for finding in handoff["findings"]
    ]
    if projected_findings != proposal["findings"]:
        raise ValueError("review_handoff must retain every source finding in order")
    if [note["text"] for note in handoff["notes"]] != proposal["notes"]:
        raise ValueError("review_handoff must retain every source note in order")


def validate_transition(handoff: dict, request: dict, history: list) -> None:
    """Prove introduction, unchanged carry, or the one trusted repair projection."""
    if not history:
        raise ValueError("review_handoff has no preceding planning revision")
    previous = history[-1]
    old_request = previous["request"]
    old_handoff = old_request.get("review_handoff")
    run = previous.get("planning", {})
    fresh_stage = (
        handoff["source"]["revision"] == old_request["revision"]
        and run.get("status") == "completed"
    )
    if fresh_stage:
        planner = run.get("participants", {}).get("planner", {}).get("proposal", {})
        tasks = copy.deepcopy(planner.get("tasks"))
        if run.get("response_contract", 1) == 2 and isinstance(tasks, list):
            by_id = {task["id"]: task for task in tasks}
            for coverage in planner.get("coverage", []):
                for task_id in coverage["tasks"]:
                    checks = by_id[task_id]["checks"]
                    if coverage["criterion"] not in checks:
                        checks.append(coverage["criterion"])
        if (
            request["tasks"] != tasks
            or request["choices"]
            != old_request["choices"] + planner.get("choices", [])
            or any(
                request[key] != old_request[key]
                for key in ("intent", "inputs", "artifact", "evidence")
            )
        ):
            raise ValueError("review_handoff was not introduced by fresh staging")
        return
    if old_handoff is None:
        raise ValueError("review_handoff was not introduced by fresh staging")
    if handoff["target_digest"] == old_handoff["target_digest"]:
        if handoff != old_handoff:
            raise ValueError("Carried review_handoff changed without fresh staging")
        return
    if previous.get("acceptance") is None or "build" not in previous:
        raise ValueError("Changed review_handoff target lacks trusted repair history")
    completed = [
        task["id"]
        for task in old_request["tasks"]
        if any(
            event["operation_key"] == "probe:" + task["id"]
            and event["state"] == "completed"
            and event["result"]["passed"]
            for event in previous["build"]["events"]
        )
    ]
    prefix = old_request["tasks"][: len(completed)]
    pending = old_request["tasks"][len(completed) :]
    if (
        not completed
        or [task["id"] for task in prefix] != completed
        or [(task["id"], task["outputs"]) for task in request["tasks"]]
        != [(task["id"], task["outputs"]) for task in pending]
        or any(
            request["intent"][key] != old_request["intent"][key]
            for key in ("goal", "context", "constraints", "acceptance", "questions")
        )
        or request["artifact"] != old_request["artifact"]
    ):
        raise ValueError("Changed review_handoff target is not a trusted pending repair")
    if handoff != project_for_repair(old_handoff, old_request, request):
        raise ValueError("Changed review_handoff differs from trusted repair projection")


def derive(request: dict, run: dict, target: dict, dispositions=None) -> dict:
    """Derive a host-owned handoff from one completed, validated planning run."""
    critic = run.get("participants", {}).get("critic")
    if critic is None:
        if dispositions not in (None, {}):
            raise ValueError("Review dispositions require a retained critic proposal")
        return None
    proposal = critic["proposal"]
    source = _source_binding(request, run)
    dispositions = {} if dispositions is None else copy.deepcopy(dispositions)
    if not isinstance(dispositions, dict):
        raise ValueError("Review dispositions must be an object keyed by finding ID")
    finding_ids = [finding["id"] for finding in proposal["findings"]]
    if set(dispositions) - set(finding_ids):
        raise ValueError("Review dispositions contain an unknown finding ID")
    all_tasks = [task["id"] for task in target["tasks"]]
    findings = []
    for finding in proposal["findings"]:
        selected = dispositions.get(finding["id"])
        if selected is None:
            disposition, rationale, task_ids = "advisory", None, all_tasks
        else:
            fields(selected, ("disposition", "rationale", "task_ids"))
            disposition = selected["disposition"]
            rationale = selected["rationale"]
            task_ids = selected["task_ids"]
            if isinstance(task_ids, list) and not task_ids:
                raise ValueError(
                    "A staged review disposition must target at least one current task"
                )
        findings.append(
            {
                **copy.deepcopy(finding),
                "disposition": disposition,
                "rationale": rationale,
                "task_ids": copy.deepcopy(task_ids),
                "archived": not task_ids,
                "source": copy.deepcopy(source),
            }
        )
    handoff = {
        "version": 1,
        "target_digest": digest(target_binding(target)),
        "source": source,
        "findings": findings,
        "notes": [
            {"text": note, "source": copy.deepcopy(source)}
            for note in proposal["notes"]
        ],
    }
    validate_shape(handoff, target)
    return handoff


def project_for_repair(handoff: dict, old_request: dict, new_request: dict) -> dict:
    """Retain dispositions while narrowing original task targets to pending work."""
    validate_shape(handoff, old_request)
    old_by_id = {task["id"]: task for task in old_request["tasks"]}
    new_by_id = {task["id"]: task for task in new_request["tasks"]}
    for task_id, task in new_by_id.items():
        previous = old_by_id.get(task_id)
        if previous is None or previous["outputs"] != task["outputs"]:
            raise ValueError("Review repair cannot rename or repurpose a retained task")
    projected = copy.deepcopy(handoff)
    for finding in projected["findings"]:
        finding["task_ids"] = [
            task_id for task_id in finding["task_ids"] if task_id in new_by_id
        ]
        finding["archived"] = not finding["task_ids"]
    projected["target_digest"] = digest(target_binding(new_request))
    validate_shape(projected, new_request)
    return projected


def freeze(request: dict) -> dict:
    """Create the marker that alone authorizes review context in new build turns."""
    handoff = request.get("review_handoff")
    if handoff is None:
        return None
    validate_shape(handoff, request)
    return {
        "version": 1,
        "request_digest": digest(request),
        "payload": copy.deepcopy(handoff),
    }


def validate_frozen(marker: dict, request: dict) -> None:
    fields(marker, ("version", "request_digest", "payload"))
    if type(marker["version"]) is not int or marker["version"] != 1:
        raise ValueError("Unsupported frozen review_handoff version")
    if marker["request_digest"] != digest(request):
        raise ValueError("Frozen review_handoff belongs to another accepted request")
    if request.get("review_handoff") != marker["payload"]:
        raise ValueError("Frozen review_handoff differs from accepted review context")
    validate_shape(marker["payload"], request)


def turn_context(marker: dict, role: str, step: dict) -> dict:
    """Project the frozen payload; never look up a newer planning revision."""
    payload = marker["payload"]
    if role == "reviewer":
        findings = payload["findings"]
    else:
        findings = [
            finding
            for finding in payload["findings"]
            if step["id"] in finding["task_ids"]
        ]
    return {
        "version": 1,
        "source": copy.deepcopy(payload["source"]),
        "findings": copy.deepcopy(findings),
        "notes": copy.deepcopy(payload["notes"]),
    }
