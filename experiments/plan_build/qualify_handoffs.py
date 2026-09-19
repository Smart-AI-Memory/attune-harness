"""Offline replay of retained replies; native transport is explicitly forbidden."""

import argparse
import copy
import importlib.util
from pathlib import Path
from unittest.mock import patch

from attune_harness import review_participants, work_runtime
from attune_harness.recovery import UnresolvedOperation
from attune_harness.review_contract import canonical, digest
from attune_harness.task_contract import read_task

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "connected_handoff_driver", HERE / "connected_journey.py"
)
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
read, write = driver.read, driver.write
ORIGINAL = driver.ROOT / "docs/receipts/plan-build-connected-native-2026-09-18"
ARM = "astra-reference"


def qualify(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    protocol = read(driver.native.PREP / "protocol.json")
    specification = next(j for j in protocol["journeys"] if j["id"] == ARM)
    bound = {
        p: driver.native.sha(p)
        for p in (
            Path(__file__),
            Path(driver.__file__),
            Path(work_runtime.__file__),
            HERE / "comparison.py",
            HERE / "prepare.py",
            HERE / "fixtures" / "acceptance.py",
            HERE / "fixtures" / driver.SUPPLEMENTAL_RUNNER,
        )
    }
    write(
        output / "local-binding.json",
        {
            "native_calls_authorized": 0,
            "mode": "Retained original replies; scripted final reviewer; local only",
            "source_sha256": {str(p): h for p, h in bound.items()},
        },
    )
    write(
        output / "control-grades.json",
        {
            "all_passed": True,
            "method": "Previously graded original controls, not fresh reviewer evidence",
            "original_sha256": driver.native.sha(ORIGINAL / "control-grades.json"),
        },
    )
    assert read(ORIGINAL / "control-grades.json")["all_passed"]
    write(
        output / "journey-driver-binding.json",
        {"driver_sha256": driver.native.sha(Path(driver.__file__))},
    )
    seen = []

    def forbidden(*args, **kwargs):
        raise AssertionError("Native dispatch forbidden during local qualification")

    def verify_local(_):
        assert all(driver.native.sha(p) == h for p, h in bound.items())
        return copy.deepcopy(protocol)

    class Replay:
        last_identity = None

        def __init__(self, config, cwd, *, profile):
            self.config = config

        def __call__(self, raw):
            envelope = driver.parse_json(raw, 512000)
            turn = envelope["turn"]
            role = turn["role"]
            assert self.config == protocol["profiles"][specification[role]]
            if role == "reviewer":
                payload = {
                    "kind": "critique",
                    "findings": [],
                    "notes": [
                        "Scripted replay terminator only; not fresh native review."
                    ],
                }
                reference = None
            else:
                suffix = role
                if role == "worker":
                    index = driver.OUTPUTS.index(turn["step"]["outputs"][0])
                    suffix += "-" + str(index)
                reference = ORIGINAL / "calls" / (ARM + "-" + suffix) / "decoded.json"
                payload = read(reference)["payload"]
                if role == "worker":
                    inspection = read(
                        ORIGINAL
                        / "journeys"
                        / ARM
                        / (ARM + "-" + suffix + "-inspection.json")
                    )
                    assert inspection["payload_digest"] == digest(payload)
                    assert inspection["inspected_before_execution"]
            seen.append(
                {
                    "role": role,
                    "turn": turn,
                    "payload": payload,
                    "retained_reference": str(reference) if reference else None,
                    "retained_sha256": (
                        driver.native.sha(reference) if reference else None
                    ),
                }
            )
            write(output / "replayed-exchanges.json", seen)
            self.last_identity = {
                "adapter": "local-replay" if reference else "scripted-local",
                "native_dispatch": False,
            }
            return canonical(
                {
                    "schema_version": 1,
                    "request_digest": envelope["request_digest"],
                    "action": {"kind": "final", "text": canonical(payload)},
                }
            )

    with (
        patch.object(driver.native, "verify", verify_local),
        patch.object(driver.native, "dispatch", forbidden),
        patch.object(review_participants, "NativeExchange", forbidden),
    ):
        state = driver.start(output, ARM)
        folder = output / "journeys" / ARM
        for _ in range(3):
            status = driver.plan_step(output, ARM, Replay)
        assert status["status"] == "completed", read(folder / "planning.json")
        record = read_task(state["work"])
        write(
            folder / "planning-grade.json",
            {
                "passed": True,
                "checkpoint": record["checkpoint_digest"],
                "method": "Reuse original session-assistant plan grade; not new grading",
                "original_grade_sha256": driver.native.sha(
                    ORIGINAL / "journeys" / ARM / "planning-grade.json"
                ),
            },
        )
        driver.stage(output, ARM)
        accepted = read_task(state["work"])
        runner = Path(state["root"]) / driver.SUPPLEMENTAL_RUNNER
        original_runner = runner.read_bytes()
        runner.write_bytes(original_runner + b"\n# Synthetic drift.\n")
        try:
            driver.build_step(output, ARM, Replay)
        except (ValueError, UnresolvedOperation) as error:
            drift_error = str(error)
        else:
            raise AssertionError("Changed protected runner allowed accepted execution")
        assert read_task(state["work"]) == accepted
        assert len(seen) == 2
        runner.write_bytes(original_runner)
        write(
            output / "changed-runner.json",
            {"blocked": True, "error": drift_error, "journal_unchanged": True},
        )
        for _ in range(4):
            status = driver.build_step(output, ARM, Replay)
        assert status["completed"] == ["exporter"], status
        driver.steer(output, ARM)
        for _ in range(20):
            status = driver.build_step(output, ARM, Replay)
            if status["status"] == "completed":
                break
            assert status["status"] == "paused", read(folder / "build.json")
        assert status["status"] == "completed", status
        completed = driver.finish(output, ARM)
    assert [s["role"] for s in seen] == [
        "planner",
        "critic",
        "worker",
        "worker",
        "worker",
        "reviewer",
    ]
    luna = read(ORIGINAL / "calls/luna-routine-planner/decoded.json")["payload"]
    request = read(ORIGINAL / "journeys/luna-routine/initial.json")["request"]
    try:
        work_runtime.validate_reply(luna, request, "planner", contract_version=2)
    except ValueError as error:
        luna_error = str(error)
    else:
        raise AssertionError("Original malformed Luna reply was silently normalized")
    result = {
        "native_calls": 0,
        "replayed_native_replies": 5,
        "scripted_reviewer_replies": 1,
        "completed_replay": completed,
        "changed_runner_blocked": drift_error,
        "original_luna_reply_rejected": luna_error,
        "source_preservation": "Original model payloads and closed campaign unchanged",
        "limits": "Local replay, not fresh native compliance or review. Synthetic correction remains redundant with the original plan.",
    }
    write(output / "qualification.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    print(canonical(qualify(parser.parse_args().output)))
