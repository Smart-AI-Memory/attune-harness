"""Behavioral controls for the worker screen; all participants are local replays."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "repair_models_test", ROOT / "experiments/plan_build/repair_models.py"
)
screen = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(screen)


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    folder = tmp_path_factory.mktemp("repair-screen")
    screen.prepare(folder)
    return folder


def inspect(payload, *, semantic=True):
    return {
        "payload_digest": screen.digest(payload),
        "inspected_before_execution": True,
        "safe_to_execute": True,
        "semantic_passed": semantic,
        "method": "Synthetic known control, not native semantic review",
    }


@pytest.mark.parametrize("case", screen.CASES, ids=lambda c: c["id"])
def test_actual_failures_and_reference_repairs(prepared, case):
    folder = prepared / "cases" / case["id"]
    before = [screen.read(p) for p in (folder / "before").glob("*/result.json")]
    assert len(before) == 2 and any(not r["passed"] for r in before)
    result = screen.read(folder / "reference-evaluation/evaluation.json")
    assert result["passed"] and result["test_counts_preserved"]
    assert result["native_calls"] == 0
    assert result["roles"] == ["worker", "reviewer"]
    assert all(p["passed"] for p in result["probes"])
    assert result["unrelated_and_protected_preserved"]
    assert result["no_repeat"] and result["stale_rejected"]


def test_alternative_correct_repair_is_not_graded_by_exact_patch(prepared, tmp_path):
    folder = prepared / "cases/nested-status"
    original = (folder / "fixture" / screen.TEST).read_text()
    payload = screen.proposal(
        folder,
        original.replace(
            screen.prior.BAD,
            "[finding['finding']['status'] for finding in records[1:]]",
        ),
    )
    result = screen.evaluate(
        folder, payload, tmp_path / "alternative", inspect(payload)
    )
    assert result["passed"]


@pytest.mark.parametrize("kind", ["unchanged", "wrong-scope", "wrong-preimage"])
def test_rejected_proposals_never_complete(prepared, tmp_path, kind):
    folder = prepared / "cases/nested-status"
    text = screen.read(folder / "reference.json")["text"]
    payload = screen.proposal(folder, text)
    if kind == "unchanged":
        payload["files"][0]["text"] = (folder / "fixture" / screen.TEST).read_text()
    elif kind == "wrong-scope":
        payload["files"][0]["path"] = "acceptance.py"
    else:
        payload["files"][0]["before_sha256"] = "0" * 64
    result = screen.evaluate(
        folder, payload, tmp_path / kind, inspect(payload, semantic=False)
    )
    assert not result["passed"] and result["status"] == "failed"
    assert result["roles"] == ["worker"] and not result["probes"]
    assert result["incomplete_rejected"] and result["unrelated_and_protected_preserved"]


def test_green_but_weakened_test_is_not_a_success(prepared, tmp_path):
    folder = prepared / "cases/nested-status"
    text = screen.read(folder / "reference.json")["text"]
    # Keep four tests and valid syntax, but remove the complete finding assertion.
    start = text.index(
        "        self.assertEqual(\n            [record['finding'] for record"
    )
    end = text.index("\n    def test_empty", start)
    text = text[:start] + text[end:]
    payload = screen.proposal(folder, text)
    result = screen.evaluate(
        folder, payload, tmp_path / "weakened", inspect(payload, semantic=False)
    )
    assert result["status"] == "completed" and result["test_counts_preserved"]
    assert all(p["passed"] for p in result["probes"])
    assert not result["passed"]  # Semantic preservation is separate from green tests.


def test_test_removal_is_detected_even_with_erroneous_semantic_clearance(
    prepared, tmp_path
):
    folder = prepared / "cases/nested-status"
    text = screen.read(folder / "reference.json")["text"]
    start = text.index("    def test_unknown_refuted")
    end = text.index("    def test_empty", start)
    payload = screen.proposal(folder, text[:start] + text[end:])
    result = screen.evaluate(folder, payload, tmp_path / "removed", inspect(payload))
    assert result["status"] == "completed"
    assert not result["test_counts_preserved"] and not result["passed"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("payload_digest", "0" * 64),
        ("inspected_before_execution", False),
        ("safe_to_execute", False),
    ],
)
def test_uninspected_source_cannot_execute(prepared, tmp_path, field, value):
    folder = prepared / "cases/nested-status"
    payload = screen.proposal(folder, screen.read(folder / "reference.json")["text"])
    inspection = {**inspect(payload), field: value}
    with pytest.raises(ValueError, match="Inspect|cleared"):
        screen.evaluate(folder, payload, tmp_path / "never-created", inspection)
    assert not (tmp_path / "never-created").exists()


def test_changed_frozen_inputs_are_rejected_before_replay(prepared, tmp_path):
    import shutil

    folder = tmp_path / "changed"
    shutil.copytree(prepared / "cases/nested-status", folder)
    (folder / "fixture" / screen.TEST).write_text("Changed after preparation\n")
    with pytest.raises(ValueError, match="Frozen case changed"):
        screen.construct(folder, tmp_path / "never-created")
    assert not (tmp_path / "never-created").exists()


def test_matched_turns_allocation_and_existing_spend_meter(prepared):
    protocol = screen.read(prepared / "protocol.json")
    assert protocol["native_calls"] == 0 and protocol["native_authorization"] is False
    assert not (prepared / "authorization.json").exists()
    assert len(protocol["trials"]) == 18
    for case in screen.CASES:
        rows = [r for r in protocol["trials"] if r["case"] == case["id"]]
        for model in screen.MODELS:
            assert {r["repetition"] for r in rows if r["model"] == model} == {1, 2}
        turn = screen.read(prepared / "cases" / case["id"] / "owner/turn.json")
        assert turn["response_contract"] == 2 and turn["tools"] == []
        assert turn["remaining_turns"] == 1 and turn["remaining_tool_calls"] == 0
        assert "reference.json" not in turn["source_evidence"]
    budget = protocol["budget"]
    meter = {
        "max_calls": 18,
        "max_calls_by_model": budget["max_calls_by_model"],
        "reservations": budget["reserve_before_next_call"],
        "budget_credits": 150,
    }
    ledger = {"calls": []}
    for trial in protocol["trials"]:
        screen.driver.native.base.admit(meter, ledger, trial["model"], trial["id"])
        ledger["calls"].append(
            {
                "id": trial["id"],
                "model": trial["model"],
                "adapter": "codex",
                "state": "observed",
                "estimated_credits": 1,
            }
        )
    with pytest.raises(ValueError, match="ceiling"):
        screen.driver.native.base.admit(meter, ledger, screen.MODELS[0], "overflow")
    unresolved = copy.deepcopy(ledger)
    unresolved["calls"][0]["state"] = "unresolved"
    with pytest.raises(ValueError, match="Unresolved"):
        screen.driver.native.base.admit(meter, unresolved, screen.MODELS[0], "never")


def test_eighteen_dispatches_use_the_same_case_turn_and_existing_meter(
    prepared, tmp_path, monkeypatch
):
    from attune_harness import process, work_build

    native = screen.driver.native
    # A synthetic allocation lives only in this test's temporary directory.
    screen.write(prepared / "decision-binding.json", {"artifacts": {}})
    screen.write(
        prepared / "manifest.json",
        {
            "sha256": {
                str(p.relative_to(prepared)): screen.sha(p)
                for p in prepared.rglob("*")
                if p.is_file() and p.name != "manifest.json"
            }
        },
    )
    monkeypatch.setattr(native, "PREP", prepared)
    captured = []
    turns = {
        case["id"]: screen.read(prepared / "cases" / case["id"] / "owner/turn.json")
        for case in screen.CASES
    }

    def fake(argv, prompt, **kwargs):
        attempt = json.loads(prompt.split("\n", 1)[1])["attempt"]
        turn = json.loads(attempt["task"]["objective"])
        case = next(name for name, frozen in turns.items() if turn == frozen)
        assert 'service_tier="default"' in argv
        assert 'forced_login_method="chatgpt"' in argv
        assert "read-only" in argv
        assert not any(
            k in kwargs["environment"] for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY")
        )
        assert not list(Path(kwargs["cwd"]).iterdir())
        captured.append((case, turn))
        folder = prepared / "cases" / case
        payload = screen.proposal(
            folder, screen.read(folder / "reference.json")["text"]
        )
        result = "\n".join(
            json.dumps(row)
            for row in [
                {"type": "thread.started", "thread_id": "synthetic"},
                {"type": "turn.started"},
                {
                    "type": "item.completed",
                    "item": {
                        "type": "agent_message",
                        "text": json.dumps({"text": json.dumps(payload)}),
                    },
                },
                {
                    "type": "turn.completed",
                    "usage": {
                        "input_tokens": 26000,
                        "cached_input_tokens": 0,
                        "output_tokens": 1600,
                    },
                },
            ]
        )
        return process.ProcessResult(argv, 0, result, "")

    monkeypatch.setattr(process, "invoke", fake)
    output = tmp_path / "synthetic-native"
    native.admit(
        output, "Synthetic test allocation; subprocess is replaced, zero paid calls."
    )
    for row in screen.read(prepared / "protocol.json")["trials"]:
        payload = native.dispatch(output, row["id"], row["model"], turns[row["case"]])
        request = screen.read(prepared / "cases" / row["case"] / "owner/accepted.json")[
            "request"
        ]
        work_build.decode(
            {"kind": "final", "text": screen.canonical(payload)},
            request,
            "worker",
            request["tasks"][0],
            contract_version=2,
        )
    assert len(captured) == 18
    ledger = screen.read(output / "ledger.json")
    assert len(ledger["calls"]) == 18
    assert all(
        r["state"] == "observed" and r["estimated_credits"] is not None
        for r in ledger["calls"]
    )
    with pytest.raises(ValueError, match="ceiling"):
        native.dispatch(output, "overflow", screen.MODELS[0], turns["nested-status"])
    assert len(captured) == 18
