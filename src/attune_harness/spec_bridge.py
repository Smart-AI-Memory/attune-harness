"""Connect work authority to the existing Spec collector, with no second store.

The host creates and consumes the form. Only after successful collection does
the bridge persist the grant through the work owner. A crash between those
operations grants nothing; reopen a current form instead of replaying a nonce.
"""

import copy
from collections.abc import Mapping
import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .features import read_text
from .review_contract import digest, parse_json
from .task_contract import read_task
from .work_contract import (
    SIGNALS,
    bind_work_acceptance,
    check_work_fresh,
    create_work,
    decision_binding,
    missing_information,
    revise_work,
)

SPEC_APPROVAL = {"id": "spec-approval", "kind": "human", "owner": "spec", "version": 1}


def plan_content(raw):
    """Exclude only the single trailing state comment owned by Spec persistence."""
    marker = "<!-- spec-state:"
    if marker not in raw:
        return raw.rstrip() + "\n"
    match = re.search(r"\n?<!-- spec-state:\s*(\{.*?\})\s*-->\s*\Z", raw, re.S)
    if raw.count(marker) != 1 or not match:
        raise ValueError("Malformed or misplaced Spec state comment")
    state = parse_json(match[1], 65536)
    if (
        not isinstance(state, dict)
        or type(state.get("schema_version")) is not int
        or state["schema_version"] not in (1, 2)
    ):
        raise ValueError("Unsupported Spec state comment")
    return raw[: match.start()].rstrip() + "\n"


def legacy_plan(path):
    """Use the existing parser; retain its fields and disclose everything ignored."""
    from attune.pipeline.spec_reader import read_spec

    raw = read_text(Path(path), 65536)
    content = plan_content(raw)
    blocks = re.findall(r"<task\b[^>]*>.*?</task>", content, re.S)
    if not blocks or len(blocks) != len(re.findall(r"<task\b", content)):
        raise ValueError("Legacy plan must contain complete nonempty task blocks")
    nodes = [ET.fromstring(block) for block in blocks]
    parsed = [task.to_dict() for task in read_spec(str(path))]
    if len(parsed) != len(nodes):
        raise ValueError("Legacy parser omitted a malformed task")
    known = {
        "objective",
        "files-to-create",
        "files-to-modify",
        "validation",
        "risks",
        "dependencies",
    }
    unsupported = []
    for node in nodes:
        for child in node:
            if child.tag not in known:
                unsupported.append(ET.tostring(child, encoding="unicode"))
        if set(node.attrib) - {"id", "name"}:
            unsupported.append("Unsupported task attributes: " + repr(node.attrib))
        nested = {
            "files-to-create": ("file", {"path"}),
            "files-to-modify": ("file", {"path"}),
            "validation": ("check", set()),
            "risks": ("risk", {"severity"}),
            "dependencies": ("dep", set()),
        }
        for group in node:
            if group.tag in nested:
                tag, attrs = nested[group.tag]
                for child in group:
                    if child.tag != tag or set(child.attrib) - attrs or list(child):
                        unsupported.append(
                            "Unmapped nested content: "
                            + ET.tostring(child, encoding="unicode")
                        )
    # Prose and ignored XML remain in the captured artifact, never silently lost.
    remainder = content
    for block in blocks:
        remainder = remainder.replace(block, "", 1)
    remainder = remainder.replace("<tasks>", "").replace("</tasks>", "").strip()
    if remainder:
        unsupported.append("Unmapped surrounding content: " + remainder)
    return {
        "path": str(Path(path).resolve()),
        "source_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
        "content": content,
        "tasks": parsed,
        "unsupported": unsupported,
        "approval_imported": False,
    }


def import_plan(
    project_root,
    config_path,
    *,
    path,
    directory,
    intent,
    assignments,
    controls=(),
    budget=None,
):
    """Import supported legacy task fields as a draft; old approval grants nothing."""
    root = Path(project_root).resolve()
    source = Path(path).absolute()
    if any(
        p.is_symlink() for p in (source, *source.parents)
    ) or not source.resolve().is_relative_to(root):
        raise ValueError("Legacy plan must be a regular file inside the project")
    legacy = legacy_plan(source)
    tasks = []
    for task in legacy["tasks"]:
        tasks.append(
            {
                "id": task["task_id"],
                "objective": task["objective"],
                "dependencies": task["dependencies"],
                "outputs": [
                    f["path"]
                    for key in ("files_to_create", "files_to_modify")
                    for f in task[key]
                ],
                "checks": task["validation_checks"],
            }
        )
    return create_work(
        root,
        config_path,
        directory=directory,
        intent=intent,
        signals={**dict.fromkeys(SIGNALS, False), "existing_artifact": "spec"},
        assignments=assignments,
        controls=controls,
        tasks=tasks,
        budget=budget,
        legacy=legacy,
    )


def reimport_plan(directory, *, checkpoint):
    """Refresh an edited imported artifact under the same owner, losing its grant."""
    record = read_task(directory)
    if record["checkpoint_digest"] != checkpoint or "legacy" not in record["request"]:
        raise ValueError("Reimport requires the current legacy work checkpoint")
    legacy = legacy_plan(record["request"]["legacy"]["path"])
    tasks = [
        {
            "id": t["task_id"],
            "objective": t["objective"],
            "dependencies": t["dependencies"],
            "outputs": [
                f["path"] for k in ("files_to_create", "files_to_modify") for f in t[k]
            ],
            "checks": t["validation_checks"],
        }
        for t in legacy["tasks"]
    ]
    return revise_work(
        directory, checkpoint=checkpoint, changes={"legacy": legacy, "tasks": tasks}
    )


class WorkSpecBridge:
    """One draft revision projected through real Spec forms and action validation.

    This is an in-process host integration. It does not replace or upgrade an
    already running MCP host. Reopening after restart issues fresh authority.
    """

    def __init__(self, directory, *, supported_controls=()):
        from attune.elicitation.command_workspace import (
            CommandWorkspaceHost,
            CommandWorkspaceProjection,
        )
        from attune.spec.workspace import SpecWorkspaceAdapter, SpecWorkspaceState

        self.directory = Path(directory)
        record = read_task(self.directory)
        if record["status"] != "draft" or missing_information(record["request"]):
            raise ValueError("Spec approval requires a complete draft")
        check_work_fresh(record)
        self.binding = decision_binding(record)
        self.supported = copy.deepcopy(list(supported_controls))
        if SPEC_APPROVAL not in self.supported:
            self.supported.append(SPEC_APPROVAL.copy())
        self.host = CommandWorkspaceHost()
        self.decision = None
        bridge = self
        request = record["request"]

        class Adapter(SpecWorkspaceAdapter):
            @staticmethod
            def _artifact_section(state):
                return {
                    "heading": "Work artifact",
                    "tone": "success",
                    "blocks": [
                        {
                            "kind": "evidence",
                            "items": [
                                {
                                    "label": "Bound work revision",
                                    "value": record["record_path"],
                                    "status": "complete",
                                }
                            ],
                        }
                    ],
                }

            def create(self, intake, *, prior_state=None):
                if intake or prior_state is not None:
                    raise ValueError("Reopen the bridge for a different work revision")
                return SpecWorkspaceState(
                    outcome=request["intent"]["goal"],
                    done_when="; ".join(request["intent"]["acceptance"]),
                    area="harness",
                    slug="work",
                    contract=digest(bridge.binding),
                    area_options=(),
                    taken_slugs=(),
                    stage="executing",
                    task_ids=(request["task_id"],),
                    current=request["task_id"],
                    probes=(record["record_path"],),
                )

            def project(self, state):
                projection = super().project(state)
                if projection.view.actions:
                    bridge._fresh()
                    return CommandWorkspaceProjection(
                        projection.view,
                        digest(
                            {
                                "spec": projection.contract_hash,
                                "work": bridge.binding,
                                "supported_controls": bridge.supported,
                            }
                        ),
                    )
                return projection

        self.host.register(Adapter(Path(request["project_root"])))

    def _fresh(self):
        record = read_task(self.directory)
        if decision_binding(record) != self.binding or record["status"] != "draft":
            raise ValueError("Work changed after the Spec decision was displayed")
        check_work_fresh(record)
        return record

    async def open(
        self,
        *,
        severity="low",
        probes=(),
        detail="Review this work intent and its exact effect scope.",
        test_evidence=None,
    ):
        """Display evidence separately from the explicit human grant."""
        record = self._fresh()
        request = record["request"]
        view = await self.host.open("spec", {})
        event = {
            "kind": "task_result",
            "task_id": request["task_id"],
            "severity": severity,
            "score": 0,
            "probes": [record["record_path"], *probes],
            "detail": detail
            + "\nGoal: "
            + request["intent"]["goal"]
            + "\nScope: "
            + ", ".join(request["intent"]["scope"])
            + "\nAccept when: "
            + "; ".join(request["intent"]["acceptance"])
            + "\nThis approves intent, not completed implementation or paid dispatch.",
        }
        if test_evidence is not None:
            event["test_evidence"] = test_evidence
        result = await self.host.publish(view.record.workspace_id, event)
        from .work_decisions import retain_decision

        self.decision = retain_decision(
            record,
            {
                "kind": "spec",
                "title": result.record.view.title,
                "markdown": result.render.markdown,
                "actions": [
                    {
                        "id": action.id,
                        "label": action.label,
                        "consequence": action.consequence,
                        "requires_explicit_choice": action.requires_explicit_choice,
                    }
                    for action in result.record.view.actions
                ],
                "response_template": {
                    "__elicitation_response__": True,
                    "title": result.record.view.title,
                    "view": result.record.view.id.value,
                    "action": None,
                    "confirmed": False,
                    **result.record.binding.to_payload(),
                },
            },
        )
        return result

    async def collect(self, payload):
        """Consume the existing collector response, then persist current authority."""
        from .work_decisions import require_current_decision, retain_decision

        record = self._fresh()
        if self.decision is None:
            raise ValueError(
                "Open and retain the decision before collecting a response"
            )
        require_current_decision(record, self.decision["digest"])
        template = self.decision["display"]["response_template"]
        if not isinstance(payload, Mapping) or any(
            payload.get(key) != value
            for key, value in template.items()
            if key not in ("action", "confirmed")
        ):
            raise ValueError(
                "Response does not match the retained decision; reopen the current decision"
            )
        result = await self.host.collect(payload, expected_adapter_id="spec")
        retain_decision(
            self._fresh(),
            self.decision["display"],
            response={"action": result.action, "result": dict(result.result)},
            expected=self.decision["digest"],
        )
        if result.result.get("disposition") not in (
            "approve_task",
            "auto_run_remaining",
        ):
            return result, None  # redo/high risk acknowledgment is never a build grant.
        self._fresh()
        decision = {
            **self.binding,
            "accepted": True,
            "source": {
                "owner": "spec",
                "reference": digest(dict(payload)),
                "disposition": result.result["disposition"],
            },
        }
        return result, bind_work_acceptance(
            self.directory,
            decision,
            supported_controls=self.supported,
            collector={
                "response": dict(payload),
                "result": dict(result.result),
                "adapter_version": result.record.adapter_version,
            },
        )
