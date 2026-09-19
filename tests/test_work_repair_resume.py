"""A failed task retains its journal and needs fresh authority before repair."""

import asyncio
import copy

import pytest
import test_work_build as builds
import test_work_controls as controls

from attune_harness.spec_bridge import WorkSpecBridge
from attune_harness.task_contract import read_task
from attune_harness.task_handoff import completed_source
from attune_harness.work_contract import revise_work
from attune_harness.work_runtime import completed_steps

work = builds.work
reset_worker = builds.reset_worker


def failed_case(work):
    case = builds.prepare(work)

    def wrong(payload, turn, peer):
        if turn["role"] == "worker" and turn["step"]["id"] == "wire":
            payload["files"][0]["text"] = "def value():\n    return 43\n"

    builds.Worker.mutation = wrong
    failed = builds.execute(case)
    assert failed["build"]["status"] == "needs_revision"
    assert completed_steps(failed) == ["export"]
    builds.Worker.mutation = None
    return case, failed


def revise(case, record, tasks=None):
    tasks = copy.deepcopy(record["request"]["tasks"] if tasks is None else tasks)
    tasks[-1]["objective"] = "Repair the failed step while preserving verified work"
    return revise_work(
        case[1],
        checkpoint=record["checkpoint_digest"],
        changes={"tasks": tasks},
        preserve_completed=True,
    )


def test_failed_step_requires_acceptance_and_reruns_required_controls(work):
    case, failed = failed_case(work)
    before = {p: (case[0] / p).read_bytes() for p in (builds.EXPORT, builds.GENERATED)}
    inode = (case[0] / builds.EXPORT).stat().st_ino
    with pytest.raises(ValueError, match="completed dependent build"):
        completed_source(case[1])
    revised = revise(case, failed)
    assert revised["status"] == "draft" and revised["acceptance"] is None
    assert revised["history"][-1]["build"] == failed["build"]
    assert revised["request"]["intent"]["scope"] == ["source.py"]
    assert revised["request"]["effects"]["before"]["source.py"][
        "sha256"
    ] == builds.repair.sha(b"def value():\n    return 43\n")
    with pytest.raises(ValueError):
        builds.execute(case)
    assert len(builds.Worker.seen) == 2

    async def accept():
        bridge = WorkSpecBridge(
            case[1],
            supported_controls=[
                builds.work_effects.identity(c) for c in revised["request"]["controls"]
            ],
        )
        view = await bridge.open()
        reply = controls.response(view)
        with pytest.raises(ValueError):
            await bridge.collect({**reply, "revision": reply["revision"] - 1})
        assert read_task(case[1])["status"] == "draft"
        await bridge.collect(reply)
        with pytest.raises(ValueError):
            await bridge.collect(reply)

    asyncio.run(accept())
    # The original control checks the original default. For this generic fixture,
    # the failed implementation changed that default, so rerunning it must block.
    result = builds.execute(case)
    assert result["build"]["status"] == "unresolved"
    assert "Build control failed" in result["build"]["error"]["detail"]
    assert len(builds.Worker.seen) == 2
    assert all((case[0] / p).read_bytes() == data for p, data in before.items())
    assert (case[0] / builds.EXPORT).stat().st_ino == inode


@pytest.mark.parametrize("change", ["id", "outputs", "dependencies"])
def test_failed_repair_cannot_reinterpret_the_failed_task(work, change):
    case, failed = failed_case(work)
    tasks = copy.deepcopy(failed["request"]["tasks"])
    tasks[-1][change] = {
        "id": "replacement",
        "outputs": [builds.GENERATED],
        "dependencies": [],
    }[change]
    saved = (case[1] / "record.json").read_bytes()
    with pytest.raises(ValueError):
        revise(case, failed, tasks)
    assert (case[1] / "record.json").read_bytes() == saved


def test_failed_first_step_cannot_be_reclassified_as_preserved_completion(work):
    case = builds.prepare(work)

    def wrong(payload, turn, peer):
        if turn["role"] == "worker":
            payload["files"][0]["text"] = "def answer():\n    return 0\n"

    builds.Worker.mutation = wrong
    failed = builds.execute(case)
    assert failed["build"]["status"] == "needs_revision"
    assert completed_steps(failed) == []
    with pytest.raises(ValueError, match="completed and pending"):
        revise(case, failed)


def test_final_review_failure_cannot_be_reclassified_as_pending_test_repair(work):
    case = builds.prepare(work)

    def high(payload, turn, peer):
        if turn["role"] == "reviewer":
            payload["findings"] = [
                {
                    "id": "defect",
                    "severity": "high",
                    "text": "Synthetic unresolved review finding",
                    "evidence": ["source.py"],
                }
            ]

    builds.Worker.mutation = high
    failed = builds.execute(case)
    assert failed["build"]["status"] == "needs_revision"
    tasks = copy.deepcopy(failed["request"]["tasks"])
    tasks.append({**tasks[-1], "id": "extra", "dependencies": ["wire"]})
    with pytest.raises(ValueError, match="completed and pending"):
        revise(case, failed, tasks)


def test_timed_out_task_is_not_a_settled_repair_boundary(work):
    case = builds.prepare(work, accept=False)
    effects = copy.deepcopy(case[2]["request"]["effects"])
    probe = effects["verification"][1]["probe"]
    probe["argv"] = [probe["argv"][0], "-B", "-c", "import time; time.sleep(2)"]
    probe["timeout"] = 1
    record = revise_work(
        case[1], checkpoint=case[2]["checkpoint_digest"], changes={"effects": effects}
    )
    builds.contracts.accept(
        work,
        record,
        supported_controls=[
            builds.work_effects.identity(c) for c in record["request"]["controls"]
        ],
    )
    stopped = builds.execute(case)
    assert stopped["build"]["status"] == "unresolved"
    assert completed_steps(stopped) == ["export"]
    saved = (case[1] / "record.json").read_bytes()
    with pytest.raises(ValueError, match="verified task boundary"):
        revise(case, stopped)
    assert (case[1] / "record.json").read_bytes() == saved


def test_retained_generated_test_failure_completes_only_as_local_repair(tmp_path):
    import importlib.util
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[1]
        / "experiments/plan_build/qualify_repair_resume.py"
    )
    spec = importlib.util.spec_from_file_location("repair_qualification", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.qualify(tmp_path / "qualification")
    assert result["native_calls"] == 0
    assert result["status"] == "completed-local-repair-replay"
    assert result["original_failure_preserved"]
    assert result["completed_workers_repeated"] == 0
    assert result["completed_output_effects_repeated"] == 0


@pytest.mark.parametrize("path", [builds.EXPORT, "source.py", "oracle.py"])
def test_failed_repair_rejects_changed_artifacts(work, path):
    case, failed = failed_case(work)
    target = case[0] / path
    target.write_bytes(target.read_bytes() + b"\n# Changed after failure.\n")
    saved = (case[1] / "record.json").read_bytes()
    with pytest.raises((ValueError, builds.UnresolvedOperation)):
        revise(case, failed)
    assert (case[1] / "record.json").read_bytes() == saved
