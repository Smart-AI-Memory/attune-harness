"""A Spec receipt cannot turn stale or unfinished test evidence into authority."""
# qualify: platform

import copy
import os

import pytest

from attune_harness import spec_handoff, test_change
from attune_harness.review_store import RunStore
from attune_harness.task_contract import read_task
from attune_harness.task_policies import execute_task
from test_test_change import accept, create, project, put  # noqa: F401

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX testing producer")


@pytest.mark.parametrize("accepted", [False, True])
def test_unfinished_test_cannot_be_exported_to_spec(project, tmp_path, accepted):
    directory, task = create(project, tmp_path)
    if accepted:
        test_change.accept_test_task(directory, task["checkpoint_digest"])
    before = (directory / "record.json").read_bytes()
    with pytest.raises(ValueError, match="completed Harness testing task"):
        spec_handoff.bind_test_evidence(directory)
    assert (directory / "record.json").read_bytes() == before
    assert not (directory / "pytest.json").exists()


@pytest.mark.parametrize("outcome", ["passed", "failed"])
def test_spec_binding_preserves_actual_outcome_and_does_not_rerun(
    project, tmp_path, outcome
):
    if outcome == "failed":
        put(project, "tests/test_logic.py", "def test_failure():\n    assert False\n")
    directory = accept(project, tmp_path)
    execute_task(directory)
    before = (directory / "record.json").read_bytes()
    binding = spec_handoff.bind_test_evidence(directory)
    assert binding["outcome"] == outcome
    spec_handoff.check_test_evidence(binding)
    assert (directory / "record.json").read_bytes() == before
    assert len(read_task(directory)["execution"]["events"]) == 1


@pytest.mark.parametrize("damage", ["source", "stdout", "summary"])
def test_changed_evidence_refuses_spec_binding_without_rewriting_history(
    project, tmp_path, damage
):
    directory = accept(project, tmp_path)
    execute_task(directory)
    binding = spec_handoff.bind_test_evidence(directory)
    if damage == "source":
        put(project, "src/demo/logic.py", "def answer():\n    return 0\n")
    elif damage == "stdout":
        (directory / "stdout.txt").write_text("replacement output")
    else:
        record = read_task(directory)
        # Keep the completed journal intact; forge only its convenience summary.
        record["execution"]["result"] = copy.deepcopy(record["execution"]["result"])
        record["execution"]["result"]["outcome"] = "failed"
        RunStore(directory, existing=True).save(record)
    before = (directory / "record.json").read_bytes()
    with pytest.raises(ValueError):
        spec_handoff.check_test_evidence(binding)
    assert (directory / "record.json").read_bytes() == before


@pytest.mark.parametrize("field,value", [
    ("task_id", "different-task"),
    ("checkpoint_digest", "0" * 64),
    ("outcome", "failed"),
])
def test_well_formed_foreign_binding_does_not_match_real_receipt(
    project, tmp_path, field, value
):
    directory = accept(project, tmp_path)
    execute_task(directory)
    binding = spec_handoff.bind_test_evidence(directory)
    binding[field] = value
    before = (directory / "record.json").read_bytes()
    with pytest.raises(ValueError, match="changed after the Spec gate"):
        spec_handoff.check_test_evidence(binding)
    assert (directory / "record.json").read_bytes() == before


@pytest.mark.parametrize("field,value", [
    ("kind", "completed-feature-v1"), ("record_path", "relative/record.json"),
    ("record_path", "/tmp/unrelated.json"), ("task_id", ""),
    ("checkpoint_digest", "unbound"), ("outcome", "approved"),
])
def test_malformed_portable_binding_is_refused_before_loading(tmp_path, field, value):
    binding = {"kind": "harness-test-v1", "record_path": str(tmp_path / "record.json"),
               "task_id": "test-task", "checkpoint_digest": "a" * 64, "outcome": "passed"}
    binding[field] = value
    with pytest.raises(ValueError, match="Invalid Harness test evidence binding"):
        spec_handoff.check_test_evidence(binding)
    assert list(tmp_path.iterdir()) == []


def test_wrong_checkpoint_and_unaccepted_execution_never_dispatch(project, tmp_path):
    directory, task = create(project, tmp_path)
    before = (directory / "record.json").read_bytes()
    with pytest.raises(ValueError, match="Stale or already accepted"):
        test_change.accept_test_task(directory, "0" * 64)
    with pytest.raises(ValueError, match="Accept the test preview"):
        test_change.execute_test_task(directory)
    assert (directory / "record.json").read_bytes() == before
    test_change.accept_test_task(directory, task["checkpoint_digest"])
    accepted = (directory / "record.json").read_bytes()
    with pytest.raises(ValueError, match="Stale testing checkpoint"):
        test_change.execute_test_task(directory, checkpoint="0" * 64)
    assert (directory / "record.json").read_bytes() == accepted
    assert not (directory / "pytest.json").exists()
