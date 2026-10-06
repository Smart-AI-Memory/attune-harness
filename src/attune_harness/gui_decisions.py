"""Bounded GUI adapter for existing draft intake and live owner decisions.

This adapter has no dispatch path. Retained forms are evidence; only this
process's live collectors can consume a browser response.
"""

import asyncio
import secrets

from .task_contract import read_task
from .work_accept import WorkAcceptance
from .work_contract import PROFILE, check_work_fresh, missing_information
from .work_decisions import require_current_decision, retain_questions
from .work_runtime import answer_planning, planning_questions


GUI_ACTIONS = {"approve_task", "redo_task"}


class Decisions:
    """Used serially by the companion's single HTTP request thread."""

    def __init__(self, tasks):
        self.tasks = {secrets.token_urlsafe(16): path for path in tasks}
        self.live = {}
        self.loop = asyncio.new_event_loop()

    def close(self):
        self.live.clear()
        self.loop.close()

    def _record(self, task):
        if not isinstance(task, str) or task not in self.tasks:
            raise ValueError("Unknown registered task")
        path = self.tasks[task]
        if path.resolve() != path or not path.is_dir():
            raise ValueError("Registered task moved; relaunch from its canonical path")
        return read_task(path)

    @staticmethod
    def _draft(record):
        if record["task_profile"] != PROFILE or record["status"] != "draft":
            raise ValueError("Only feature-work drafts support GUI decisions")
        if "planning" in record or "build" in record:
            raise ValueError("Resolve or stage the saved run before opening a decision")
        check_work_fresh(record)

    @staticmethod
    def _draft_heading(record):
        return ("Draft saved — more answers needed" if missing_information(record["request"])
                else "Draft saved — ready for review")

    @staticmethod
    def _draft_next_step(record):
        return ("continue intake" if missing_information(record["request"])
                else "review this intent")

    def inspect(self):
        result = []
        for task in self.tasks:
            try:
                record = self._record(task)
                item = {"task": task, "checkpoint": record["checkpoint_digest"],
                        "label": record.get("request", {}).get("intent", {}).get("goal") or "Unfinished draft",
                        "status": record["status"], "heading": "Saved task", "available": False}
                if record["task_profile"] == PROFILE and record["status"] == "accepted":
                    item["heading"] = "Intent accepted"
                    item["note"] = "Intake and intent review are complete. No further intent form is needed; execution remains separate."
                else:
                    if record["task_profile"] == PROFILE and record["status"] == "draft":
                        item["heading"] = "Draft saved"
                    try:
                        self._draft(record)
                        item["available"] = True
                        item["heading"] = self._draft_heading(record)
                        item["note"] = (f"Next: {self._draft_next_step(record)}. "
                                        "Click “Open current form” below. No model calls.")
                    except (ValueError, OSError) as exc:
                        item["note"] = str(exc)
            except (ValueError, OSError) as exc:
                item = {"task": task, "label": "Unavailable saved task", "heading": "Saved task unavailable", "available": False,
                        "status": "unavailable", "note": str(exc)}
            result.append(item)
        return result

    def open(self, task, checkpoint):
        record = self._record(task)
        self._draft(record)
        if checkpoint != record["checkpoint_digest"]:
            raise ValueError("Task changed; refresh before opening its decision")
        # One live decision per task. A second tab invalidates the first even
        # if retaining an identical question form produces the same digest.
        self.live.pop(task, None)
        shown = planning_questions(self.tasks[task])
        bridge = None
        if shown["missing"]:
            decision = retain_questions(record, shown)
        else:
            supported = [c["control"] for c in record["request"].get("effects", {}).get("checks", [])]
            bridge = WorkAcceptance(self.tasks[task], supported_controls=supported)
            self.loop.run_until_complete(bridge.open())
            decision = bridge.decision
        identity = secrets.token_urlsafe(24)
        self.live[task] = (identity, checkpoint, decision, bridge)
        # Browser never supplies an owner binding or a path. The live bridge
        # retains its response template server-side, exactly as displayed.
        display = {k: v for k, v in decision["display"].items() if k != "response_template"}
        if bridge is not None:
            display["actions"] = [a for a in display["actions"] if a["id"] in GUI_ACTIONS]
        request = record["request"]
        return {"task": task, "checkpoint": checkpoint, "decision": identity, "display": display,
                "summary": {"intent": request["intent"], "choices": request["choices"],
                            "authoring": request["authoring"], "effects": request.get("effects")}}

    def submit(self, task, checkpoint, decision, response):
        record = self._record(task)
        self._draft(record)
        live = self.live.get(task)
        if not live or (decision, checkpoint) != live[:2] or checkpoint != record["checkpoint_digest"]:
            raise ValueError("Decision expired or changed; inspect and reopen it")
        # Submission attempts are single-use, including uncertain writes.
        # Never replay after a failed collection or a lost HTTP response.
        self.live.pop(task)
        _, _, saved, bridge = live
        require_current_decision(record, saved["digest"])
        if not isinstance(response, dict):
            raise ValueError("Decision response must be an object")
        if bridge is None:
            if set(response) != {"answers"} or not isinstance(response["answers"], dict) or not any(
                value is not None and value != "" for value in response["answers"].values()
            ):
                raise ValueError("Supply at least one answer, then reopen to continue")
            saved = answer_planning(self.tasks[task], {"schema_version": 1, "checkpoint_digest": checkpoint,
                                                     "answers": response["answers"]})
            message = (f"Answers saved. Next: {self._draft_next_step(saved)}. "
                       "Click “Open current form” in Saved work above.")
            heading = self._draft_heading(saved)
        else:
            if set(response) != {"action", "confirmed"} or type(response["confirmed"]) is not bool:
                raise ValueError("Choose an action from the displayed decision")
            actions = {action["id"] for action in saved["display"]["actions"]} & GUI_ACTIONS
            if not isinstance(response["action"], str) or response["action"] not in actions:
                raise ValueError("Action is not available in the displayed decision")
            _, accepted = self.loop.run_until_complete(bridge.collect(
                {**saved["display"]["response_template"], **response}
            ))
            message = ("Intent accepted. Implementation and paid dispatch are not authorized by this decision."
                       if accepted is not None else "Response recorded; work remains unaccepted. Click “Open current form” in Saved work above to continue.")
            heading = "Intent accepted" if accepted is not None else self._draft_heading(record)
        return {"message": message, "heading": heading}
