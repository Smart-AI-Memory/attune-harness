"""Work authority through the Spec collector, with no second store.

The host creates and consumes the form. Only after successful collection does
the acceptance persist the grant through the work owner. A crash between those
operations grants nothing; reopen a current form instead of replaying a nonce.

The host and the Spec adapter are Harness's own, ``command_workspace`` and
``spec_workspace``, since Task 3 of the spec authority (D14); nothing here
imports Attune AI. The host's events, a render and an accept for each stage
the acceptance walks, are written beside the task's ``decision.json`` as
evidence; they never carry the action nonce, and a sink that fails never
blocks a decision. An accept line records a workspace action the host
consumed, not a grant: the grant is the store's record, written after it, and
under contention the bind can still be refused. Refusal of a stale or replayed
decision across processes is the task store's, under its lease; the checks
here before it are unlocked reads.

Step (b) of Task 4 (D23.2, D24) walks the workspace's execution stages
instead of opening at ``executing``: the host opens at ``approval``; ``open``
takes ``start_execution``, publishes Harness's readiness checks as the
execution boundary's lifecycle receipts and, on ``PASS``, starts the task and
publishes its result, which is the task gate the human decides at, as
before. A ``BLOCKED`` receipt leaves the workspace at ``blocked``, retained
as the decision; the caller refuses with the receipt's words, which are the
words the bind refused with before. No Harness check produces
``CHAIR_REQUIRED`` yet; that stage stays wired for the later mapping (D24).
In the evidence file, the render and the accept of a stage the acceptance
walked itself carry ``origin: walk``; a line without it is a view the human
was shown or an action the human took.

Task 4's first step (D20.1, D23) moved this module out of the bridge, whose
remainder is the legacy plan reader, ``spec_legacy``. The class was
``WorkSpecBridge``; every refusal text, the readiness check and the import
receipts are contracts and are unchanged, including the text "Reopen the
bridge for a different work revision", until a deliberate diff with a
changelog line renames it.
"""

import copy
from collections.abc import Mapping
from pathlib import Path

from .command_workspace import (
    CommandWorkspaceHost,
    CommandWorkspaceProjection,
    jsonl_event_writer,
)
from .review_contract import digest
from .spec_legacy import legacy_plan
from .spec_workspace import SpecWorkspaceAdapter, SpecWorkspaceState
from .task_contract import read_task
from .work_contract import (
    SIGNALS,
    _supported,
    bind_work_acceptance,
    check_work_fresh,
    create_work,
    decision_binding,
    missing_information,
    revise_work,
)

SPEC_APPROVAL = {"id": "spec-approval", "kind": "human", "owner": "spec", "version": 1}
BOUNDARY = "execution"


def _receipt(gate_id, state, detail):
    return {"gate_id": gate_id, "boundary": BOUNDARY, "state": state, "detail": detail}


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


class WorkAcceptance:
    """One draft revision projected through real Spec forms and action validation.

    This is an in-process host integration. It does not replace or upgrade an
    already running MCP host. Reopening after restart issues fresh authority.
    """

    def __init__(self, directory, *, supported_controls=()):
        self.directory = Path(directory)
        record = read_task(self.directory)
        if record["status"] != "draft" or missing_information(record["request"]):
            raise ValueError("Spec approval requires a complete draft")
        check_work_fresh(record)
        self.binding = decision_binding(record)
        self.supported = copy.deepcopy(list(supported_controls))
        if SPEC_APPROVAL not in self.supported:
            self.supported.append(SPEC_APPROVAL.copy())
        # Evidence of who saw what, when: one JSON line per render and per
        # accepted action, beside decision.json. Never the nonce (D14). A line
        # for a stage the acceptance walks itself says so: ``origin: walk``.
        sink = jsonl_event_writer(Path(record["record_path"]).with_name("workspace-events.jsonl"))
        self._origin = None

        def record_event(event):
            sink({**event, "origin": self._origin} if self._origin else event)

        self.host = CommandWorkspaceHost(record_event=record_event)
        self.decision = None
        acceptance = self
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
                    contract=digest(acceptance.binding),
                    area_options=(),
                    taken_slugs=(),
                    stage="approval",
                    task_ids=(request["task_id"],),
                    probes=(record["record_path"],),
                )

            def project(self, state):
                projection = super().project(state)
                if projection.view.actions:
                    acceptance._fresh()
                    return CommandWorkspaceProjection(
                        projection.view,
                        digest(
                            {
                                "spec": projection.contract_hash,
                                "work": acceptance.binding,
                                "supported_controls": acceptance.supported,
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

    def readiness(self, request):
        """Harness's checks at the execution boundary, as the lifecycle gate's receipts (D24).

        ``PASS`` or ``BLOCKED``; a ``BLOCKED`` detail is the text the bind
        refuses with, so the words a user sees do not change. No Harness check
        produces ``CHAIR_REQUIRED`` yet.
        """
        # In the bind's order, so the first blocking receipt is the bind's first refusal.
        planner = any(a["role"] == "planner" for a in request["assignments"])
        receipts = [
            _receipt("planner-assignment", "PASS", "A planner is assigned")
            if planner
            else _receipt("planner-assignment", "BLOCKED", "A planner assignment is required")
        ]
        try:
            _supported(request["controls"], self.supported)
        except ValueError as exc:
            receipts.append(_receipt("required-controls", "BLOCKED", str(exc)))
        else:
            receipts.append(
                _receipt(
                    "required-controls", "PASS", "Every required control has a supporting runner"
                )
            )
        return receipts

    @staticmethod
    def _walk(render, action):
        """The response for a stage the acceptance walks itself; the human's is the caller's."""
        return {
            "__elicitation_response__": True,
            "title": render.record.view.title,
            "view": render.record.view.id.value,
            "action": action,
            "confirmed": True,
            **render.record.binding.to_payload(),
        }

    @staticmethod
    def _display(result):
        return {
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
        }

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
        review_detail = ""
        if "review_handoff" in request:
            handoff = request["review_handoff"]
            rows = []
            for finding in handoff["findings"]:
                target = ", ".join(finding["task_ids"]) or "archived"
                rationale = (
                    f"; rationale: {finding['rationale']}"
                    if finding["rationale"] is not None
                    else ""
                )
                rows.append(
                    f"{finding['id']} [{finding['severity']}] = "
                    f"{finding['disposition']} for {target}{rationale}: "
                    f"{finding['text']}"
                )
            notes = [note["text"] for note in handoff["notes"]]
            review_detail = "\nPlanning review dispositions: " + (
                " | ".join(rows) if rows else "no findings"
            )
            if notes:
                review_detail += "\nPlanning review advice: " + " | ".join(notes)
        from .work_decisions import retain_decision

        # The walk (D24): approval, start_execution, the execution boundary's
        # gate with Harness's readiness checks as its receipts, then the task.
        self._origin = "walk"
        try:
            view = await self.host.open("spec", {})
            workspace = view.record.workspace_id
            await self.host.collect(self._walk(view, "start_execution"), expected_adapter_id="spec")
        finally:
            self._origin = None
        gated = await self.host.publish(
            workspace,
            {"kind": "lifecycle_gate", "boundary": BOUNDARY, "receipts": self.readiness(request)},
        )
        if gated.record.state.stage != "executing":
            # Blocked (or chair-required, which nothing raises yet): the gate's
            # view is the decision; its words are the caller's refusal.
            self.decision = retain_decision(record, self._display(gated))
            return gated
        await self.host.publish(workspace, {"kind": "task_started", "task_id": request["task_id"]})
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
            + review_detail
            + "\nThis approves intent, not completed implementation or paid dispatch.",
        }
        if test_evidence is not None:
            event["test_evidence"] = test_evidence
        result = await self.host.publish(workspace, event)
        self.decision = retain_decision(record, self._display(result))
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
