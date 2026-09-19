"""Local reconstruction of a retained failure; scripted repair, zero native calls."""

import argparse
import asyncio
import copy
import importlib.util
from pathlib import Path
import time
from unittest.mock import patch

from attune_harness import review_participants, work_runtime
from attune_harness.review_contract import canonical, digest, parse_json
from attune_harness.spec_bridge import WorkSpecBridge
from attune_harness.task_contract import read_task
from attune_harness.task_handoff import completed_source
from attune_harness.work_contract import revise_work

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "repair_journey", HERE / "connected_journey.py"
)
driver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(driver)
read, write, sha = driver.read, driver.write, driver.native.sha
ORIGINAL = driver.ROOT / "docs/receipts/plan-build-fresh-journey-native-2026-09-18"
PREPARATION = (
    driver.ROOT / "docs/receipts/plan-build-fresh-journey-preparation-2026-09-18"
)
ARM = "luna-routine"
BAD = "[finding['status'] for finding in records[1:]]"
GOOD = "[record['finding']['status'] for record in records[1:]]"


def forbidden(*args, **kwargs):
    raise AssertionError("Native dispatch forbidden during local repair qualification")


def qualify(output, *, prepare_repair=False):
    started = time.monotonic()
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    protocol = read(PREPARATION / "protocol.json")
    original = {str(p): sha(p) for p in ORIGINAL.rglob("*") if p.is_file()}
    sources = {
        str(p): sha(p)
        for p in (
            Path(__file__),
            Path(driver.__file__),
            Path(work_runtime.__file__),
            HERE / "prepare.py",
            HERE / "comparison.py",
            HERE / "fixtures/acceptance.py",
            HERE / "fixtures/run_supplemental.py",
        )
    }
    write(
        output / "local-binding.json",
        {
            "native_calls_authorized": 0,
            "source_sha256": sources,
            "original_sha256": original,
            "mode": "Five unchanged retained replies; scripted repair and final reviewer",
        },
    )
    write(output / "control-grades.json", read(ORIGINAL / "control-grades.json"))
    write(
        output / "journey-driver-binding.json",
        {"driver_sha256": sha(Path(driver.__file__))},
    )
    seen = []

    def verify_local(_):
        assert all(sha(Path(p)) == h for p, h in sources.items())
        return copy.deepcopy(protocol)

    class Replay:
        last_identity = None

        def __init__(self, config, cwd, *, profile):
            self.cwd = cwd

        def __call__(self, raw):
            envelope = parse_json(raw, 512000)
            turn = envelope["turn"]
            role = turn["role"]
            assert role != "reviewer", "Original failure must stop before final review"
            suffix = role
            if role == "worker":
                suffix += "-" + str(driver.OUTPUTS.index(turn["step"]["outputs"][0]))
            source = ORIGINAL / "calls" / (ARM + "-" + suffix) / "decoded.json"
            payload = read(source)["payload"]
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
                    "retained_reference": str(source),
                    "retained_sha256": sha(source),
                }
            )
            self.last_identity = {"adapter": "local-replay", "native_dispatch": False}
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
        root, directory = Path(state["root"]), Path(state["work"])
        for _ in range(3):
            status = driver.plan_step(output, ARM, Replay)
        assert status["status"] == "completed"
        write(
            folder / "planning-grade.json",
            {
                "passed": True,
                "checkpoint": read_task(directory)["checkpoint_digest"],
                "method": "Original session-assistant grade reused; no new native assessment",
                "original_grade_sha256": sha(
                    ORIGINAL / "journeys" / ARM / "planning-grade.json"
                ),
            },
        )
        driver.stage(output, ARM)
        for _ in range(4):
            status = driver.build_step(output, ARM, Replay)
        assert status["completed"] == [state.get("first_step", "task-export-jsonl")]
        driver.steer(output, ARM)
        for _ in range(20):
            status = driver.build_step(output, ARM, Replay)
            if status["status"] != "paused":
                break
        assert status["status"] == "needs_revision", status
        assert len(seen) == 5
        write(output / "replayed-exchanges.json", seen)
        failed = read_task(directory)
        write(folder / "failed.json", failed)
        last_probe = failed["build"]["events"][-1]["result"]
        assert "KeyError: 'status'" in last_probe["stderr"]
        assert "Ran 4 tests" in last_probe["stderr"]
        failure_seconds = time.monotonic() - started
        try:
            completed_source(directory)
        except ValueError as error:
            incomplete = str(error)
        else:
            raise AssertionError("Incomplete source accepted")
        before = {p: sha(root / p) for p in driver.OUTPUTS}
        inodes = {p: (root / p).stat().st_ino for p in driver.OUTPUTS[:2]}
        tasks = copy.deepcopy(failed["request"]["tasks"])
        failure_line = next(
            line.strip()
            for line in last_probe["stderr"].splitlines()
            if line.startswith("KeyError:")
        )
        tasks[-1]["objective"] = (
            "Repair the existing supplemental test that failed with "
            + failure_line
            + ". Correct its nested finding-status access; preserve all four "
            "tests and existing assertions. The exporter and CLI are already "
            "verified and must remain unchanged."
        )
        tasks[-1]["checks"].append(
            "Read finding status from record['finding']['status']; preserve all existing assertions."
        )
        revised = revise_work(
            directory,
            checkpoint=failed["checkpoint_digest"],
            changes={"tasks": tasks},
            preserve_completed=True,
        )
        assert revised["history"][-1]["build"] == failed["build"]
        assert revised["acceptance"] is None
        assert revised["request"]["intent"]["scope"] == [driver.comparison.GENERATED]
        write(folder / "repair-draft.json", revised)
        try:
            work_runtime.build_work(
                directory,
                allow_external=True,
                allow_native=True,
                exchange_factory=forbidden,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Old grant authorized repair")

        async def accept_repair():
            bridge = WorkSpecBridge(
                directory,
                supported_controls=[
                    driver.work_effects.identity(c)
                    for c in revised["request"]["controls"]
                ],
            )
            view = await bridge.open(
                detail="Synthetic local repair acceptance; not Task 8 acceptance or native authority."
            )
            old_reply = read(folder / "corrected-decision.json")["response"]
            try:
                await bridge.collect(old_reply)
            except ValueError:
                pass
            else:
                raise AssertionError("Old decision authorized revised repair")
            reply = {
                "__elicitation_response__": True,
                "title": view.record.view.title,
                "view": view.record.view.id.value,
                "action": "approve_task",
                "confirmed": False,
                **view.record.binding.to_payload(),
            }
            receipt, accepted = await bridge.collect(reply)
            try:
                await bridge.collect(reply)
            except ValueError:
                pass
            else:
                raise AssertionError("Repair decision replay accepted")
            (folder / "repair-form.md").write_text(view.render.markdown)
            write(
                folder / "repair-decision.json",
                {
                    "response": reply,
                    "result": dict(receipt.result),
                    "old_decision_rejected": True,
                    "replay_rejected": True,
                },
            )
            return accepted

        accepted = asyncio.run(accept_repair())
        write(folder / "repair-accepted.json", accepted)
        if prepare_repair:
            assert all(sha(Path(p)) == h for p, h in original.items())
            prepared = {
                "status": "prepared-repair-awaiting-native-allocation",
                "native_calls": 0,
                "retained_replies": 5,
                "work": str(directory),
                "root": str(root),
                "checkpoint": accepted["checkpoint_digest"],
                "preserved_sha256": {p: before[p] for p in driver.OUTPUTS[:2]},
                "prepared_seconds": time.monotonic() - started,
                "limits": "Synthetic fixture acceptance does not authorize native dispatch.",
            }
            write(output / "prepared-repair.json", prepared)
            return prepared
        repair_seen = []

        class Repair:
            last_identity = {"adapter": "scripted-local", "native_dispatch": False}

            def __init__(self, config, cwd, *, profile):
                pass

            def __call__(self, raw):
                envelope = parse_json(raw, 512000)
                turn = envelope["turn"]
                if turn["role"] == "worker":
                    assert not repair_seen
                    assert turn["step"]["outputs"] == [driver.comparison.GENERATED]
                    current = turn["source_evidence"][driver.comparison.GENERATED]
                    assert current.count(BAD) == 1
                    payload = {
                        "schema_version": 2,
                        "files": [
                            {
                                "path": driver.comparison.GENERATED,
                                "before_sha256": turn["output_schema"]["files"][0][
                                    "before_sha256"
                                ],
                                "text": current.replace(BAD, GOOD),
                            }
                        ],
                    }
                else:
                    assert len(repair_seen) == 1 and turn["role"] == "reviewer"
                    payload = {
                        "kind": "critique",
                        "findings": [],
                        "notes": [
                            "Scripted local terminator; native final review remains unqualified."
                        ],
                    }
                repair_seen.append({"turn": turn, "payload": payload})
                return canonical(
                    {
                        "schema_version": 1,
                        "request_digest": envelope["request_digest"],
                        "action": {"kind": "final", "text": canonical(payload)},
                    }
                )

        for _ in range(12):
            done = work_runtime.build_work(
                directory,
                allow_external=True,
                allow_native=True,
                max_operations=1,
                exchange_factory=Repair,
            )
            if done["build"]["status"] != "paused":
                break
        write(output / "scripted-exchanges.json", repair_seen)
        write(folder / "repaired.json", done)
        assert done["build"]["status"] == "completed", done["build"].get("error")
        assert done["history"][-1]["build"] == failed["build"]
        assert len(repair_seen) == 2
        assert all(
            sha(root / p) == before[p] and (root / p).stat().st_ino == inodes[p]
            for p in driver.OUTPUTS[:2]
        )
        assert (
            root / "unrelated.txt"
        ).read_text() == "Unrelated dirty work must survive.\n"
        assert [
            e["item"]["path"]
            for e in done["build"]["events"]
            if e["kind"] == "file_effect"
        ] == [driver.comparison.GENERATED]
        handoff = completed_source(directory)
        assert handoff[1] == sorted(driver.OUTPUTS)
        assert (
            work_runtime.build_work(
                directory,
                allow_external=True,
                allow_native=True,
                exchange_factory=forbidden,
            )
            == done
        )
        target = root / driver.comparison.DOCUMENTATION
        source = target.read_bytes()
        target.write_bytes(source + b"\n# Later synthetic source change.\n")
        try:
            completed_source(directory)
        except ValueError as error:
            stale = str(error)
        else:
            raise AssertionError("Stale completed handoff accepted")
        finally:
            target.write_bytes(source)
        assert completed_source(directory) == handoff
    assert all(sha(Path(p)) == h for p, h in original.items())
    result = {
        "native_calls": 0,
        "retained_replies": 5,
        "scripted_repair_replies": 1,
        "scripted_reviewer_replies": 1,
        "status": "completed-local-repair-replay",
        "incomplete_handoff_rejected": incomplete,
        "stale_handoff_rejected": stale,
        "old_authority_rejected": True,
        "original_failure_preserved": True,
        "completed_workers_repeated": 0,
        "completed_output_effects_repeated": 0,
        "earlier_campaign_unchanged": True,
        "handoff": [str(handoff[0]), *handoff[1:]],
        "first_reproduced_failure_seconds": failure_seconds,
        "local_total_seconds": time.monotonic() - started,
        "limits": "Disposable reconstruction; synthetic decisions and scripted repair/review. No native recovery or Task 8 acceptance.",
    }
    write(output / "qualification.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--prepare-repair", action="store_true")
    args = parser.parse_args()
    print(canonical(qualify(args.output, prepare_repair=args.prepare_repair)))
