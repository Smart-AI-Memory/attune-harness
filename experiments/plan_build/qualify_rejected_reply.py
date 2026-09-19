"""Replay the original rejected native reply in a disposable work owner."""

import argparse
import importlib.util
from pathlib import Path
from unittest.mock import patch

from attune_harness import repair, review_participants, work_runtime
from attune_harness.review_contract import canonical, parse_json
from attune_harness.task_contract import read_task
from attune_harness.task_handoff import completed_source

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "rejected_reply_preparer", HERE / "qualify_repair_resume.py"
)
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)
ORIGINAL = (
    prepare.driver.ROOT
    / "docs/receipts/plan-build-repair-native-retry-2026-09-18/calls/luna-routine-worker-2/decoded.json"
)


def qualify(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    prepared = prepare.qualify(output / "prepared", prepare_repair=True)
    directory = Path(prepared["work"])
    initial = read_task(directory)
    payload = prepare.read(ORIGINAL)["payload"]
    seen = []

    class Retained:
        last_identity = {"adapter": "retained-local-replay", "native_dispatch": False}

        def __init__(self, config, cwd, *, profile):
            pass

        def __call__(self, raw):
            wire = parse_json(raw, 512000)
            turn = wire["turn"]
            assert not seen and turn["role"] == "worker"
            assert "Repair the existing supplemental test" in turn["step"]["objective"]
            assert "KeyError: 'status'" in turn["step"]["objective"]
            assert (
                payload["files"][0]["text"]
                == turn["source_evidence"][payload["files"][0]["path"]]
            )
            seen.append(turn)
            return canonical(
                {
                    "schema_version": 1,
                    "request_digest": wire["request_digest"],
                    "action": {"kind": "final", "text": canonical(payload)},
                }
            )

    with patch.object(review_participants, "NativeExchange", prepare.forbidden):
        for _ in range(2):
            paused = work_runtime.build_work(
                directory,
                allow_external=True,
                allow_native=True,
                max_operations=1,
                exchange_factory=Retained,
            )
        assert paused["build"]["status"] == "paused"
        assert read_task(directory) == paused
        prepare.write(output / "paused-readable.json", paused)
        failed = work_runtime.build_work(
            directory, allow_external=True, allow_native=True, exchange_factory=Retained
        )
        assert failed["build"]["status"] == "failed"
        assert "unchanged file" in failed["build"]["error"]["detail"]
        assert read_task(directory) == failed
        assert (
            work_runtime.build_work(
                directory,
                allow_external=True,
                allow_native=True,
                exchange_factory=prepare.forbidden,
            )
            == failed
        )
    assert len(seen) == 1
    assert (
        repair.snapshot(initial["request"]["effects"])
        == initial["request"]["effects"]["before"]
    )
    assert not any(e["kind"] == "file_effect" for e in failed["build"]["events"])
    try:
        completed_source(directory)
    except ValueError as error:
        completion = str(error)
    else:
        raise AssertionError("Rejected reply allowed completed handoff")
    prepare.write(output / "failed-readable.json", failed)
    prepare.write(
        output / "retained-exchange.json",
        {
            "turn": seen[0],
            "payload": payload,
            "original": str(ORIGINAL),
            "original_sha256": prepare.sha(ORIGINAL),
        },
    )
    result = {
        "native_calls": 0,
        "retained_repair_replies": 1,
        "paused_readable": True,
        "failed_readable": True,
        "repeated_participant_calls": 0,
        "file_effects": 0,
        "completion_rejected": completion,
        "repair_objective_contains_observed_failure": True,
        "original_trial_regraded": False,
    }
    prepare.write(output / "qualification.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    print(canonical(qualify(parser.parse_args().output)))
