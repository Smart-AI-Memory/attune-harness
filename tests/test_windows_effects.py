"""Saved Windows effect projection plus actual local-NTFS primitive journeys."""

import copy
import json
import os
import sys

import pytest

from attune_harness import repair, work_effects, windows_effects as windows
from attune_harness.recovery import UnresolvedOperation
from attune_harness.task_contract import accept_task, create_repair_task, read_task
from attune_harness.task_policies import execute_task
from test_review import scripted
from test_task_contract import response
import test_work_contract as contracts
import test_work_effects as effect_tests

work = contracts.work


def _id(number):
    return {"volume": 7, "file_id": f"{number:032x}"}


def _entry(number, parent=1, text="old", *, attributes=32):
    raw = text.encode("utf-8")
    return {"kind": "file", "identity": _id(number),
            "parent_identity": _id(parent), "attributes": attributes,
            "dacl_sha256": "a" * 64, "security_sha256": "b" * 64,
            "links": 1, "size": len(raw), "sha256": repair.sha(raw)}


def _synthetic():
    root = {"kind": "directory", "identity": _id(1), "attributes": 16,
            "dacl_sha256": "a" * 64, "security_sha256": "b" * 64, "links": 1}
    return {"profile": windows.FEATURE_PROFILE,
            "before": {"": root, "source.py": _entry(2)}}


def test_windows_saved_result_projects_observed_identity_only():
    plan = _synthetic()
    item = {"kind": "replacement", "path": "source.py",
            "before_sha256": repair.sha(b"old"), "text": "new"}
    result = {"path": "source.py", "entry": _entry(3, text="new")}
    event = {"kind": "file_effect", "state": "completed", "item": item,
             "result": result}
    expected = windows.expected_snapshot(plan, [event], kind="file_effect")
    assert expected["source.py"]["identity"] == _id(3)
    for bad in (
        {"identity": _id(2)}, {"parent_identity": _id(9)},
        {"security_sha256": "c" * 64}, {"attributes": 2},
        {"sha256": repair.sha(b"wrong")},
    ):
        forged = copy.deepcopy(event)
        forged["result"]["entry"].update(bad)
        with pytest.raises(ValueError):
            windows.expected_snapshot(plan, [forged], kind="file_effect")


def test_windows_paths_reject_alias_syntax_and_reserved_names():
    for path in ("CON", "folder/AUX.txt", "a\\b", "a//b", "name:stream",
                 "trailing. ", "file.", "../escape", "A/b?c"):
        with pytest.raises(ValueError):
            windows.relative(path)
    assert windows.relative("folder/Unicode space α.py") == "folder/Unicode space α.py"


def test_windows_saved_manifests_reject_bool_version_and_mixed_case_scope():
    base = _synthetic()
    base['before']['oracle.txt'] = _entry(4, text='protected')
    plan = {**base, 'snapshot_version': 1, 'root': 'C:\\checkout',
            'root_identity': _id(1), 'allowed': ['source.py'],
            'parents': [], 'protected': ['oracle.txt'], 'checks': []}
    work_effects.validate_manifest(plan)
    bad = copy.deepcopy(plan)
    bad['snapshot_version'] = True
    with pytest.raises(ValueError):
        work_effects.validate_manifest(bad)
    bad = copy.deepcopy(plan)
    bad['allowed'] = ['.GIT/config']
    with pytest.raises(ValueError):
        work_effects.validate_manifest(bad)


@pytest.fixture
def native_checkout(tmp_path):
    root = tmp_path / "checkout"
    root.mkdir()
    (root / ".git").mkdir()
    (root / "source.py").write_text("old", encoding="utf-8")
    (root / "oracle.txt").write_text("protected", encoding="utf-8")
    probe = {"argv": [sys.executable, "-c", "print('checked')"],
             "cwd": ".", "timeout": 10, "max_output_bytes": 4096,
             "environment": {"SystemRoot": os.environ["SystemRoot"],
                             "PYTHONDONTWRITEBYTECODE": "1",
                             "PYTHONNOUSERSITE": "1"},
             "oracle_paths": ["oracle.txt"]}
    return root, tmp_path / "task", probe


@pytest.mark.skipif(os.name != "nt", reason="requires real local NTFS")
def test_native_repair_replacement_and_lost_ack_observation(native_checkout):
    root, state, probe = native_checkout
    plan = repair.freeze(root, ["source.py"], probe, state)
    before_id = plan["before"]["source.py"]["identity"]
    item = {"path": "source.py", "before_sha256": repair.sha(b"old"),
            "text": "new"}
    result = repair.replace_file(plan, item)
    assert result["after_entry"]["identity"] != before_id
    assert result["after_sha256"] == repair.sha(b"new")
    event = {"kind": "replacement", "phase": "dispatching", "state": "pending",
             "attempts": 1, "patch": item}
    evidence = repair.reconcile_replacement(plan, event, events=[event])
    assert evidence["status"] == "observed_after_image"
    assert event["result"]["after_entry"]["identity"] == result["after_entry"]["identity"]
    assert event["result"]["native_rename"] == {
        "transmission": "unknown", "observation_only": True}
    repair.assert_snapshot(plan, repair.expected_snapshot(plan, [event]))
    assert (root / "oracle.txt").read_text() == "protected"


@pytest.mark.skipif(os.name != "nt", reason="requires real local NTFS")
def test_native_before_retry_and_non_target_change_refusal(native_checkout):
    root, state, probe = native_checkout
    plan = repair.freeze(root, ["source.py"], probe, state)
    item = {"path": "source.py", "before_sha256": repair.sha(b"old"), "text": "new"}
    event = {"kind": "replacement", "phase": "dispatching", "state": "pending",
             "attempts": 1, "patch": item}
    with pytest.raises(UnresolvedOperation):
        repair.reconcile_replacement(plan, event, events=[event])
    repair.reconcile_replacement(plan, event, events=[event], retry_before=True)
    assert event["phase"] == "prepared" and event["attempts"] == 2
    event.update(phase="dispatching")
    (root / "oracle.txt").write_text("changed", encoding="utf-8")
    with pytest.raises(UnresolvedOperation):
        repair.reconcile_replacement(plan, event, events=[event], retry_before=True)


@pytest.mark.skipif(os.name != "nt", reason="requires real local NTFS")
def test_native_feature_directory_file_and_replacement(native_checkout):
    root, state, _ = native_checkout
    plan = work_effects.freeze(root, ["source.py", "new/created.py"], ["new"],
                               ["oracle.txt"], [], state)
    events = []
    items = [
        {"kind": "directory", "path": "new"},
        {"kind": "creation", "path": "new/created.py",
         "before_sha256": None, "text": "created"},
        {"kind": "replacement", "path": "source.py",
         "before_sha256": repair.sha(b"old"), "text": "new"},
    ]
    for item in items:
        repair.assert_snapshot(plan, work_effects.expected_snapshot(plan, events))
        result = work_effects.write_effect(plan, item)
        events.append({"kind": "file_effect", "state": "completed",
                       "item": item, "result": result})
    repair.assert_snapshot(plan, work_effects.expected_snapshot(plan, events))
    assert (root / "new" / "created.py").read_text() == "created"
    assert (root / "source.py").read_text() == "new"
    assert (root / "oracle.txt").read_text() == "protected"


@pytest.mark.skipif(os.name != "nt", reason="requires real local NTFS")
def test_native_hardlink_and_path_alias_refuse_before_write(native_checkout):
    root, state, probe = native_checkout
    os.link(root / "source.py", root / "source-link.py")
    with pytest.raises(ValueError):
        repair.freeze(root, ["source.py"], probe, state)
    (root / "source-link.py").unlink()
    with pytest.raises(ValueError):
        repair.freeze(root, ["SOURCE.PY"], probe, state)
    assert (root / "source.py").read_text() == "old"


@pytest.mark.skipif(os.name != "nt", reason="requires real local NTFS")
def test_native_mixed_case_protected_directory_cannot_be_edited(native_checkout):
    root, state, probe = native_checkout
    (root / ".git").rename(root / ".GIT")
    (root / ".GIT" / "config").write_text("protected", encoding="utf-8")
    with pytest.raises(ValueError):
        repair.freeze(root, [".GIT/config"], probe, state)
    with pytest.raises(ValueError):
        work_effects.freeze(root, [".GIT/config"], [], ["oracle.txt"], [], state)
    assert (root / ".GIT" / "config").read_text() == "protected"


@pytest.mark.skipif(os.name != "nt", reason="requires real local NTFS")
def test_native_accepted_repair_owner_runs_failed_then_passing_probe(tmp_path):
    project = tmp_path / 'project'
    checkout = project / 'checkout'
    checkout.mkdir(parents=True)
    (checkout / '.git').mkdir()
    (checkout / 'source.py').write_text('VALUE = 1\n', encoding='utf-8')
    (checkout / 'probe.py').write_text('from source import VALUE\nassert VALUE == 2\n', encoding='utf-8')
    registry = project / 'participants.json'
    registry.write_text(json.dumps({'schema_version': 1, 'participants': {
        'worker': {'adapter': 'deterministic', 'tools': [], 'max_turns': 1,
                   'max_tool_calls': 0}}}), encoding='utf-8')
    probe = {'argv': [sys.executable, '-B', 'probe.py'], 'cwd': '.',
             'timeout': 15, 'max_output_bytes': 4096,
             'environment': {'SystemRoot': os.environ['SystemRoot'],
                             'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1'},
             'oracle_paths': ['probe.py']}
    directory = project / 'task'
    draft = create_repair_task(project, registry, goal='Correct VALUE',
        checkout=checkout, allowed=['source.py'], probe=probe, worker='worker',
        criteria='The frozen probe must pass', review='none', directory=directory)
    assert draft['request']['repair']['scope']['profile'] == windows.REPAIR_PROFILE
    accepted = accept_task(directory, response(directory))
    before_hash = accepted['request']['repair']['scope']['before']['source.py']['sha256']
    def action(packet):
        assert packet['turn']['role'] == 'worker'
        return {'kind': 'final', 'text': json.dumps({'schema_version': 1,
            'replacements': [{'path': 'source.py', 'before_sha256': before_hash,
                              'text': 'VALUE = 2\n'}]})}
    completed = execute_task(directory, exchange_factory=scripted(action))
    assert completed['status'] == 'completed'
    assert completed['execution']['before_probe']['passed'] is False
    assert completed['execution']['after_probe']['passed'] is True
    assert (checkout / 'source.py').read_text(encoding='utf-8') == 'VALUE = 2\n'
    assert read_task(directory)['status'] == 'completed'


@pytest.mark.skipif(os.name != "nt", reason="requires real local NTFS")
def test_native_accepted_work_owner_creates_and_replaces(work, monkeypatch):
    case = effect_tests.prepare(work, controls=[], runner=False)
    checked = []
    original_gate = work_effects.require_platform

    def accepted_gate(plan=None):
        assert plan is not None, "The owner must load accepted effects before platform admission"
        checked.append(plan['profile'])
        return original_gate(plan)

    monkeypatch.setattr(work_effects, 'require_platform', accepted_gate)
    result = effect_tests.execute(case)
    root = case[0]
    assert result['build']['status'] == 'completed'
    assert (root / 'pkg' / 'sub' / 'new.py').read_text() == 'answer = 42\n'
    assert (root / 'source.py').read_text().endswith('return 2\n')
    assert (root / 'plan.md').read_text() == 'Preserve all findings and default JSON.\n'
    from attune_harness.work_runtime import reconcile_work_effect
    with pytest.raises(ValueError, match='Only an unresolved file effect'):
        reconcile_work_effect(case[1], result['checkpoint_digest'], 'missing')
    assert checked == [windows.FEATURE_PROFILE] * 3
