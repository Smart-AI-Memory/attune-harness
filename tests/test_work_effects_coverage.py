"""Rejected authority must not dispatch a check or produce a file effect."""

import copy
import os

import pytest

from attune_harness import repair, work_effects
from attune_harness.recovery import UnresolvedOperation
from attune_harness.task_contract import read_task
from attune_harness.work_contract import revise_work
from test_work_effects import execute, prepare, reconcile, work

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX effect profile")


@pytest.mark.parametrize(
    "bad",
    ["duplicate_scope", "missing_protected", "empty_protected", "extra_parent",
     "invalid_mode", "invalid_directory", "duplicate_runner", "human_runner",
     "unprotected_oracle", "invalid_checks", "invalid_verification",
     "duplicate_verification", "unprotected_verification"],
)
def test_rejected_manifest_revision_preserves_accepted_authority(work, bad):
    case = prepare(work)
    request = case[2]["request"]
    plan = copy.deepcopy(request["effects"])
    if bad == "duplicate_scope":
        plan["allowed"].append(plan["allowed"][0])
    elif bad == "missing_protected":
        plan["protected"].append("missing.txt")
    elif bad == "empty_protected":
        plan["protected"] = []
    elif bad == "extra_parent":
        plan["parents"].append("unrelated")
    elif bad == "invalid_mode":
        plan["before"]["source.py"]["mode"] = -1
    elif bad == "invalid_directory":
        plan["before"][".git/"]["kind"] = "file"
    elif bad == "duplicate_runner":
        plan["checks"].append(copy.deepcopy(plan["checks"][0]))
    elif bad == "human_runner":
        plan["checks"][0]["control"]["kind"] = "human"
    elif bad == "unprotected_oracle":
        plan["checks"][0]["probe"]["oracle_paths"] = ["unrelated.txt"]
    elif bad == "invalid_checks":
        plan["checks"] = {}
    elif bad == "invalid_verification":
        plan["verification"] = {}
    else:
        runner = plan["checks"][0]
        check = {"task_id": "verify", "probe": copy.deepcopy(runner["probe"]),
                 "executable_sha256": runner["executable_sha256"]}
        plan["verification"] = [check]
        if bad == "duplicate_verification":
            plan["verification"].append(copy.deepcopy(check))
        else:
            check["probe"]["oracle_paths"] = ["unrelated.txt"]
    before = read_task(case[1])
    with pytest.raises(ValueError):
        revise_work(case[1], checkpoint=before["checkpoint_digest"], changes={"effects": plan})
    assert read_task(case[1]) == before
    assert repair.snapshot(request["effects"]) == request["effects"]["before"]
    assert "build" not in before


def test_unrelated_change_prevents_reconciliation_of_known_after_bytes(work, monkeypatch):
    case = prepare(work)
    original = work_effects.write_effect

    def lose_after(plan, item):
        receipt = original(plan, item)
        if item["kind"] == "replacement":
            raise OSError("lost replacement acknowledgment")
        return receipt

    with monkeypatch.context() as m:
        m.setattr(work_effects, "write_effect", lose_after)
        with pytest.raises(OSError, match="lost replacement"):
            execute(case)
    event = copy.deepcopy(read_task(case[1])["build"]["events"][-1])
    assert (case[0] / "source.py").read_text().endswith("return 2\n")
    unrelated = case[0] / "unrelated.txt"
    unrelated.write_bytes(b"owner edit after uncertain write\n")
    with pytest.raises(UnresolvedOperation, match="Unknown effect state"):
        reconcile(case, retry_before=True)
    assert read_task(case[1])["build"]["events"][-1] == event
    assert unrelated.read_bytes() == b"owner edit after uncertain write\n"
    assert not (case[0] / "pkg/sub/new.py").exists()
