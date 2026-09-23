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
import json
import os
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

from .command_workspace import (
    EVENT_FILE_LIMIT,
    CommandWorkspaceHost,
    CommandWorkspaceProjection,
    jsonl_event_writer,
)
from .review_contract import digest
from .spec_legacy import legacy_plan, read_plan
from .spec_state import read_state_report
from .spec_workspace import SpecWorkspaceAdapter, SpecWorkspaceState
from .task_contract import read_task, safe_storage
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
# One JSON line per conversion of a plan outside the project, beside record.json,
# through the workspace events' writer and under its bound.
RECEIPTS = "import-receipts.jsonl"
RECEIPT_LIMIT = EVENT_FILE_LIMIT
# What a receipt learns only from the saved record, each value at its longest,
# so the room check before the save bounds the line the writer will see.
_LONGEST = {
    "task": {"task_id": "0" * 36, "revision": 32, "checkpoint_digest": "0" * 64},
    "time": "0" * 32,
}


def _receipt(gate_id, state, detail):
    return {"gate_id": gate_id, "boundary": BOUNDARY, "state": state, "detail": detail}


def _tasks(legacy):
    """The task store's shape of the plan's tasks.

    What the shape has no place for stays in the record's ``legacy`` block.
    """
    return [
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
        for task in legacy["tasks"]
    ]


def _read_for_receipt(path):
    """One read for both readers.

    The state goes through ``spec_state`` first, so a schema version this
    Harness does not read (1 and 2 only, R4) is refused with its next action;
    then the tasks through ``spec_legacy``, on the same text.
    """
    raw = read_plan(path)
    report = read_state_report(raw, str(path))
    return raw, report, legacy_plan(path, raw=raw)


def _outside(path, project_root):
    """Whether a bound plan lies outside the project, which only the explicit path allows."""
    return not Path(path).is_relative_to(project_root)


def _line(receipt):
    # As the writer serializes a line, so the room check measures what it will see.
    return (json.dumps(receipt, ensure_ascii=True, allow_nan=False, sort_keys=True) + "\n").encode(
        "ascii"
    )


def _conversion(conversion, *, given, raw, report, legacy, tasks):
    """The receipt of one conversion, before the record's identity and the time.

    What was read: the path as given (normalised by the command line) and as
    resolved, the file's digest and the content digest the record binds, the
    state comment as ``spec_state`` reads it, and whether a comment was
    present and, if the reader ignored it, why. What it became: each task in
    the store's shape, by count. What was left out: per task, the parsed
    fields the shape has no place for, which stay in the record's ``legacy``
    block; and the reader's disclosures by count, kind and digest, since the
    record keeps them in full in ``legacy.unsupported`` and a receipt that
    repeated them would grow with the plan's prose.
    """
    left_out = {}
    for task in legacy["tasks"]:
        fields = []
        if task["name"] != task["task_id"]:
            fields.append("name")
        if task["risks"]:
            fields.append("risks")
        if any(
            f["description"]
            for key in ("files_to_create", "files_to_modify")
            for f in task[key]
        ):
            fields.append("file descriptions")
        if fields:
            left_out[task["task_id"]] = fields
    disclosures = legacy["unsupported"]
    kinds = {"surrounding": 0, "nested": 0, "attributes": 0, "elements": 0}
    for item in disclosures:
        if item.startswith("Unmapped surrounding content: "):
            kinds["surrounding"] += 1
        elif item.startswith("Unmapped nested content: "):
            kinds["nested"] += 1
        elif item.startswith("Unsupported task attributes: "):
            kinds["attributes"] += 1
        else:
            kinds["elements"] += 1
    state = report["state"]
    spec_state = None
    if state is not None:
        spec_state = {
            "schema_version": state.schema_version,
            "completed": state.completed,
            "current": state.current,
            "auto_run": state.auto_run,
            "last_updated": state.last_updated,
            "task_receipts": len(state.task_receipts),
        }
    return {
        "schema_version": 1,
        "receipt": "legacy-plan-conversion",
        "conversion": conversion,
        "source": {
            "given": given,
            "resolved": legacy["path"],
            "sha256": legacy["source_sha256"],
            "content_sha256": legacy["content_sha256"],
            "bytes": len(raw.encode("utf-8")),
        },
        "state_comment": {
            "present": report["comment"],
            "schema_version": report["schema_version"],
            "ignored": report["ignored"],
        },
        "spec_state": spec_state,
        "mapped": [
            {
                "id": task["id"],
                "objective": bool(task["objective"]),
                "dependencies": len(task["dependencies"]),
                "outputs": len(task["outputs"]),
                "checks": len(task["checks"]),
            }
            for task in tasks
        ],
        "unmapped": {
            "fields": left_out,
            "disclosures": {
                "count": len(disclosures),
                "kinds": kinds,
                "sha256": digest(disclosures),
            },
        },
        "approval_imported": legacy["approval_imported"],
    }


def _receipt_room(task_directory, receipt):
    """Refuse, before the record is saved, a receipt the writer would refuse after it.

    The writer refuses a symlinked or hard-linked file and a line that would
    pass its bound, and its open fails on a file that is not regular. Each is
    checked here first, with the receipt's unknown values at their longest,
    so the common case is refused with nothing written. What can still fail
    after the save, a race or the lock, ``_record_conversion`` reports.
    """
    target = Path(task_directory) / RECEIPTS
    if target.is_symlink() or target.parent.is_symlink():
        raise ValueError(
            f"Conversion receipt cannot be written: {target} is, or sits in, a symlink. "
            "Nothing was changed. Remove the link; the next conversion starts a new "
            "receipts file."
        )
    size = 0
    if target.exists():
        if not target.is_file():
            raise ValueError(
                f"Conversion receipt cannot be written: {target} is not a regular file. "
                "Nothing was changed. Move it aside; the next conversion starts a new "
                "receipts file."
            )
        detail = target.stat()
        if detail.st_nlink > 1:
            raise ValueError(
                f"Conversion receipt cannot be written: {target} has more than one link. "
                "Nothing was changed. Remove the other link, or move the file aside; the "
                "next conversion starts a new receipts file."
            )
        size = detail.st_size
    longest = {
        **receipt,
        "time": _LONGEST["time"],
        "task": {**_LONGEST["task"], "record_path": str(target.with_name("record.json"))},
    }
    if size + len(_line(longest)) > RECEIPT_LIMIT:
        raise ValueError(
            f"Conversion receipt would not fit: {target} would pass {RECEIPT_LIMIT} bytes. "
            "Nothing was changed. Move the receipts file aside to archive it; the next "
            "conversion starts a new one."
        )


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
    allow_outside_project=False,
):
    """Import supported legacy task fields as a draft; old approval grants nothing.

    The plan is a regular file inside the project, unless
    ``allow_outside_project`` names one outside it explicitly (spec authority
    Task 5; D4, D20.3): then it is read once through ``spec_state`` and
    ``spec_legacy``, a symlink followed and both spellings recorded, and the
    conversion leaves a receipt beside the record, its room checked before
    the record is saved. A plan the flag names that resolves inside the
    project is refused, so that a receipt follows the record, the bound plan
    outside the project, and never the flag. Either way the plan is only read.
    """
    root = Path(project_root).resolve()
    source = Path(path).absolute()
    if allow_outside_project:
        resolved = source.resolve()
        if resolved.is_relative_to(root):
            raise ValueError(
                f"Legacy plan resolves inside the project: {resolved}. "
                "Import that path without --allow-outside-project."
            )
        raw, report, legacy = _read_for_receipt(source)
        tasks = _tasks(legacy)
        receipt = _conversion(
            "import", given=os.fspath(path), raw=raw, report=report, legacy=legacy, tasks=tasks
        )
        _receipt_room(safe_storage(directory), receipt)
    else:
        if any(
            p.is_symlink() for p in (source, *source.parents)
        ) or not source.resolve().is_relative_to(root):
            raise ValueError("Legacy plan must be a regular file inside the project")
        legacy = legacy_plan(source)
        tasks = _tasks(legacy)
    record = create_work(
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
    if allow_outside_project:
        _record_conversion(record, receipt)
    return record


def reimport_plan(directory, *, checkpoint):
    """Refresh an edited imported artifact under the same owner, losing its grant."""
    record = read_task(directory)
    if record["checkpoint_digest"] != checkpoint or "legacy" not in record["request"]:
        raise ValueError("Reimport requires the current legacy work checkpoint")
    request = record["request"]
    path = request["legacy"]["path"]
    # The record decides: only the explicit path binds a plan outside the
    # project, and every conversion of such a task leaves a receipt, whatever
    # is beside the record on disk (D4).
    receipted = _outside(path, request["project_root"])
    if receipted:
        raw, report, legacy = _read_for_receipt(Path(path))
        tasks = _tasks(legacy)
        receipt = _conversion(
            "reimport", given=path, raw=raw, report=report, legacy=legacy, tasks=tasks
        )
        _receipt_room(Path(record["record_path"]).parent, receipt)
    else:
        legacy = legacy_plan(path)
        tasks = _tasks(legacy)
    revised = revise_work(
        directory, checkpoint=checkpoint, changes={"legacy": legacy, "tasks": tasks}
    )
    if receipted:
        _record_conversion(revised, receipt)
    return revised


def _record_conversion(record, receipt):
    """Append the receipt beside the record, with the record's identity and the time.

    One JSON line through the same locked writer as the workspace events, so a
    second conversion is a second line, never an overwrite. The room was
    checked before the save; a failure that still happens here is reported
    with the revision that landed and the way to get its receipt. The plan
    itself is never written (D4).
    """
    request = record["request"]
    line = {
        **receipt,
        "time": datetime.now(timezone.utc).isoformat(),
        "task": {
            "task_id": request["task_id"],
            "revision": request["revision"],
            "record_path": record["record_path"],
            "checkpoint_digest": record["checkpoint_digest"],
        },
    }
    try:
        jsonl_event_writer(Path(record["record_path"]).with_name(RECEIPTS))(line)
    except (ValueError, OSError) as exc:
        raise ValueError(
            f"The conversion landed as revision {request['revision']} with checkpoint "
            f"{record['checkpoint_digest']}, but its receipt was not written: {exc}. "
            f"Inspect {RECEIPTS} beside the record and remove or move it aside, then "
            "reimport with this checkpoint to record the receipt."
        ) from exc


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
