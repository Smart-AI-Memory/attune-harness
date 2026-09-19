"""Step an approved disposable native journey through existing work owners."""

import argparse
import asyncio
import copy
import importlib.util
from pathlib import Path
import tempfile

from attune_harness import work_effects, work_runtime
from attune_harness.review_contract import canonical, digest, parse_json
from attune_harness.spec_bridge import WorkSpecBridge
from attune_harness.task_contract import read_task
from attune_harness.task_handoff import completed_source
from attune_harness.work_contract import revise_work

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


native = load("connected_meter", Path(__file__).with_name("run_connected.py"))
comparison = load("comparison_fixture", Path(__file__).with_name("comparison.py"))
read, write = native.read, native.write
OUTPUTS = [comparison.EXPORT, comparison.DOCUMENTATION, comparison.GENERATED]
SUPPLEMENTAL_RUNNER = "run_supplemental.py"
CORRECTION = "Reconstruct the complete original receipt from the JSONL header and finding records and assert exact equality."


def context(output, arm):
    protocol = native.verify(output)
    grades = read(output / "control-grades.json")
    if grades.get("all_passed") is not True:
        raise ValueError("Review controls must pass before dependent journeys")
    binding = read(output / "journey-driver-binding.json")
    if native.sha(Path(__file__)) != binding["driver_sha256"]:
        raise ValueError("Qualified journey driver changed")
    spec = next(j for j in protocol["journeys"] if j["id"] == arm)
    folder = output / "journeys" / arm
    return protocol, spec, folder


def start(output, arm):
    protocol, spec, folder = context(output, arm)
    folder.mkdir(parents=True, exist_ok=False)
    scratch = (
        Path(tempfile.mkdtemp(prefix="connected-journey-", dir="/private/tmp"))
        / "prepared"
    )
    comparison.prepare(scratch)
    directory, root = scratch / "plan-work", scratch / "checkout"
    (root / SUPPLEMENTAL_RUNNER).write_bytes(
        (Path(__file__).parent / "fixtures" / SUPPLEMENTAL_RUNNER).read_bytes()
    )
    configuration = scratch / "participants.json"
    write(
        configuration,
        {
            "schema_version": 1,
            "participants": {
                role: protocol["profiles"][spec[role]]
                for role in ("planner", "critic", "worker", "reviewer")
            },
        },
    )
    record = read_task(directory)
    assignment = record["request"]["assignments"][0]
    assignments = [
        {**assignment, "role": role, "participant": role}
        for role in ("planner", "critic", "worker", "reviewer")
    ]
    template = read(native.PREP / "qualified/luna-routine/turns.json")[0]
    constraints = [
        *template["work"]["intent"]["constraints"],
        "The protected host runner selects checkout/src, verifies package import "
        "origins and discovers supplemental unittest tests. Tests may use ordinary "
        "package imports; they must not depend on importing acceptance.py.",
    ]
    record = revise_work(
        directory,
        checkpoint=record["checkpoint_digest"],
        changes={
            "assignments": assignments,
            "intent": {"constraints": constraints},
        },
    )
    state = {
        "work": str(directory),
        "root": str(root),
        "phase": "planning",
        "steered": False,
    }
    write(folder / "state.json", state)
    write(folder / "initial.json", record)
    return state


def factory(output, arm):
    protocol, spec, folder = context(output, arm)

    class Measured:
        last_identity = None

        def __init__(self, config, cwd, *, profile):
            self.config = config

        def __call__(self, raw):
            envelope = parse_json(raw, 512000)
            turn, role = envelope["turn"], envelope["turn"]["role"]
            assert self.config == protocol["profiles"][spec[role]]
            suffix = role
            if role == "worker":
                assert len(turn["step"]["outputs"]) == 1
                suffix += "-" + str(OUTPUTS.index(turn["step"]["outputs"][0]))
            call_id = arm + "-" + suffix
            payload = native.dispatch(output, call_id, spec[role], turn)
            self.last_identity = read(output / "calls" / call_id / "decoded.json")[
                "identity"
            ]
            return canonical(
                {
                    "schema_version": 1,
                    "request_digest": envelope["request_digest"],
                    "action": {"kind": "final", "text": canonical(payload)},
                }
            )

    return Measured


def plan_step(output, arm, exchange_factory=None):
    _, _, folder = context(output, arm)
    state = read(folder / "state.json")
    assert state["phase"] == "planning"
    record = work_runtime.plan_work(
        state["work"],
        allow_external=True,
        allow_native=True,
        max_operations=1,
        exchange_factory=exchange_factory or factory(output, arm),
    )
    write(folder / "planning.json", record)
    return {"phase": "planning", "status": record["planning"]["status"]}


async def accept(folder, directory, control, label):
    bridge = WorkSpecBridge(
        directory, supported_controls=[work_effects.identity(control)]
    )
    view = await bridge.open(
        detail="Synthetic fixture acceptance within the approved comparison; not Task 8 acceptance."
    )
    reply = {
        "__elicitation_response__": True,
        "title": view.record.view.title,
        "view": view.record.view.id.value,
        "action": "approve_task",
        "confirmed": False,
        **view.record.binding.to_payload(),
    }
    result, record = await bridge.collect(reply)
    try:
        await bridge.collect(reply)
    except ValueError:
        pass
    else:
        raise AssertionError("Replayed decision accepted")
    write(
        folder / (label + "-decision.json"),
        {"response": reply, "result": dict(result.result), "replay_rejected": True},
    )
    (folder / (label + "-form.md")).write_text(view.render.markdown)
    return record


def stage(output, arm):
    _, _, folder = context(output, arm)
    state = read(folder / "state.json")
    assert state["phase"] == "planning"
    directory, root = Path(state["work"]), Path(state["root"])
    record = read_task(directory)
    assert record["planning"]["status"] == "completed"
    grade = read(folder / "planning-grade.json")
    if (
        grade.get("passed") is not True
        or grade.get("checkpoint") != record["checkpoint_digest"]
    ):
        raise ValueError(
            "Current native planning needs evidence-backed semantic assessment"
        )
    record = work_runtime.apply_planning_proposal(
        directory, checkpoint=record["checkpoint_digest"]
    )
    tasks = record["request"]["tasks"]
    assert [t["outputs"] for t in tasks] == [[path] for path in OUTPUTS]
    control = record["request"]["controls"][0]
    arguments = [
        [
            "-m",
            "unittest",
            "acceptance.Feature.test_unknown_refuted_and_advisory_notes_survive",
        ],
        ["acceptance.py"],
        [SUPPLEMENTAL_RUNNER],
    ]
    verification = [
        {"task_id": t["id"], "probe": comparison.probe(args)}
        for t, args in zip(tasks, arguments)
    ]
    verification[2]["probe"]["oracle_paths"].append(SUPPLEMENTAL_RUNNER)
    verification.append(
        {"task_id": "final", "probe": comparison.probe(["acceptance.py"])}
    )
    effects = work_effects.freeze(
        root,
        OUTPUTS,
        ["tests/generated"],
        [
            "plan.md",
            "acceptance.py",
            "samples/api.py",
            "samples/empty.py",
            SUPPLEMENTAL_RUNNER,
        ],
        [
            {
                "control": work_effects.identity(control),
                "probe": comparison.probe(["acceptance.py", "--baseline"]),
            }
        ],
        directory,
        verification=verification,
    )
    record = revise_work(
        directory, checkpoint=record["checkpoint_digest"], changes={"effects": effects}
    )
    record = asyncio.run(accept(folder, directory, control, "initial"))
    state.update(phase="build", first_step=tasks[0]["id"])
    write(folder / "state.json", state)
    write(folder / "accepted.json", record)
    return {"phase": "build", "status": record["status"]}


def build_step(output, arm, exchange_factory=None):
    _, _, folder = context(output, arm)
    state = read(folder / "state.json")
    assert state["phase"] == "build"
    directory = Path(state["work"])
    record = read_task(directory)
    if not state["steered"] and work_runtime.completed_steps(record) == [
        state["first_step"]
    ]:
        raise ValueError(
            "Verified first step reached; apply the prepared pending-task correction"
        )
    # A paid call cannot flow straight into execution of uninspected model source.
    for path in (output / "calls").glob(arm + "-worker-*/decoded.json"):
        inspected = folder / (path.parent.name + "-inspection.json")
        if not inspected.exists() or read(inspected).get("payload_digest") != digest(
            read(path)["payload"]
        ):
            raise ValueError(
                "Inspect retained native source before the next file/test operation"
            )
    record = work_runtime.build_work(
        directory,
        allow_external=True,
        allow_native=True,
        max_operations=1,
        exchange_factory=exchange_factory or factory(output, arm),
    )
    write(folder / "build.json", record)
    return {
        "phase": "build",
        "status": record["build"]["status"],
        "completed": work_runtime.completed_steps(record),
        "last_event": record["build"]["events"][-1]["kind"],
    }


def steer(output, arm):
    _, _, folder = context(output, arm)
    state = read(folder / "state.json")
    assert not state["steered"]
    directory = Path(state["work"])
    record = read_task(directory)
    assert work_runtime.completed_steps(record) == [state["first_step"]]
    tasks = copy.deepcopy(record["request"]["tasks"])
    tasks[-1]["checks"].append(CORRECTION)
    before = native.sha(Path(state["root"]) / comparison.EXPORT)
    record = revise_work(
        directory,
        checkpoint=record["checkpoint_digest"],
        changes={"tasks": tasks},
        preserve_completed=True,
    )
    assert record["acceptance"] is None
    try:
        work_runtime.build_work(directory, allow_external=True, allow_native=True)
    except ValueError:
        pass
    else:
        raise AssertionError("Correction retained prior authority")
    record = asyncio.run(
        accept(folder, directory, record["request"]["controls"][0], "corrected")
    )
    state.update(steered=True, preserved_export_sha256=before)
    write(folder / "state.json", state)
    write(folder / "corrected.json", record)
    return {
        "phase": "build",
        "status": "reaccepted",
        "completed_export_preserved": True,
    }


def finish(output, arm):
    _, _, folder = context(output, arm)
    state = read(folder / "state.json")
    directory, root = Path(state["work"]), Path(state["root"])
    record = read_task(directory)
    assert record["build"]["status"] == "completed"
    assert native.sha(root / comparison.EXPORT) == state["preserved_export_sha256"]
    assert (
        root / "unrelated.txt"
    ).read_text() == "Unrelated dirty work must survive.\n"
    completed_source(directory)

    def no_repeat(*a, **kw):
        raise AssertionError("Completed journey repeated a participant call")

    work_runtime.build_work(
        directory, allow_external=True, allow_native=True, exchange_factory=no_repeat
    )
    write(folder / "completed.json", record)
    target = root / comparison.DOCUMENTATION
    target.write_text(target.read_text() + "\n# Later synthetic source change.\n")
    try:
        completed_source(directory)
    except ValueError as error:
        stale = str(error)
    else:
        raise AssertionError("Stale completed handoff accepted")
    result = {
        "status": "completed",
        "preserved_export": True,
        "unrelated_work_preserved": True,
        "repeated_calls": 0,
        "stale_handoff_rejected": stale,
        "task8_accepted": False,
    }
    write(folder / "result.json", result)
    state["phase"] = "completed"
    write(folder / "state.json", state)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("start", "plan_step", "stage", "build_step", "steer", "finish"),
    )
    parser.add_argument("output", type=Path)
    parser.add_argument("arm", choices=("luna-routine", "astra-reference"))
    parser.add_argument("--preparation", type=Path, default=native.PREP)
    args = parser.parse_args()
    native.PREP = args.preparation.resolve()
    print(canonical(globals()[args.action](args.output, args.arm)))
