"""Offline experiment controller checks: no provider calls allowed."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "quality_trial", ROOT / "experiments/assessment_quality/trial.py"
)
trial = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trial)
REPAIR_SPEC = importlib.util.spec_from_file_location(
    "grade_repair", ROOT / "experiments/assessment_quality/grade_repair.py"
)
repair = importlib.util.module_from_spec(REPAIR_SPEC)
REPAIR_SPEC.loader.exec_module(repair)


@pytest.fixture
def packet(tmp_path, monkeypatch):
    from attune_harness import process

    def forbidden(*a, **kw):
        pytest.fail("Offline check attempted native process")

    monkeypatch.setattr(process, "invoke", forbidden)
    wheel = tmp_path / "fixture.whl"
    wheel.write_bytes(b"offline identity fixture")
    directory = (tmp_path / "packet").resolve()
    trial.prepare(directory, wheel)
    return directory


def good_grades():
    values = [
        {
            "id": name,
            "correct": True,
            "critical_miss": False,
            "unsupported_findings": [],
            "missed_defects": [],
            "rationale": "fixture explanation",
        }
        for name in ("sample", "v1", "v2", "v3")
    ]
    values[2].update(
        correct=False, unsupported_findings=["invented birthday requirement"]
    )
    values[3].update(
        correct=False, critical_miss=True, missed_defects=["encryption contradiction"]
    )
    return {"grades": values}


def fake_process(argv, prompt, **options):
    from attune_harness.process import ProcessResult

    packet = json.loads(prompt.split("\n", 1)[1])
    attempt = packet["attempt"]
    if attempt["role"] == "reviewer":
        items = json.loads(attempt["task"]["objective"])
        assert set(items[0]) == {
            "id",
            "document",
            "reference",
            "requirements",
            "assessment",
        }
        assert "key" not in items[0] and "arm" not in items[0]
        text = json.dumps(good_grades())
    else:
        evidence = json.loads(attempt["task"]["objective"])
        assert evidence["references"][0]["text"].startswith("# Cedar reference")
        text = "Offline fixture assessment; native inference has not occurred."
    model = argv[argv.index("--model") + 1]
    if model.startswith("claude"):
        response = json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "session_id": "offline",
                "structured_output": {"text": text},
                "modelUsage": {model: {}},
                "usage": {"input_tokens": 100, "output_tokens": 10},
            }
        )
    else:
        assert 'service_tier="default"' in argv
        assert 'forced_login_method="chatgpt"' in argv
        response = "\n".join(
            json.dumps(v)
            for v in [
                {"type": "thread.started", "thread_id": "offline"},
                {"type": "turn.started"},
                {
                    "type": "item.completed",
                    "item": {
                        "type": "agent_message",
                        "text": json.dumps({"text": text}),
                    },
                },
                {
                    "type": "turn.completed",
                    "usage": {
                        "input_tokens": 100,
                        "cached_input_tokens": 0,
                        "output_tokens": 10,
                    },
                },
            ]
        )
    assert "ANTHROPIC_API_KEY" not in options["environment"]
    assert "OPENAI_API_KEY" not in options["environment"]
    return ProcessResult(argv, 0, response, "")


def test_freeze_and_admission_bind_content_roles_and_runner(packet):
    p = trial.verify(packet)
    assert len(p["trials"]) == 32 and p["max_calls"] == 64
    assert p["budget_credits"] == 250
    p["fixture"]["cases"][0]["key"] = {}
    trial.write(packet / "protocol.json", p)
    with pytest.raises(ValueError, match="admission"):
        trial.verify(packet)


@pytest.mark.parametrize(
    "fault", ["unknown", "inflight", "budget", "duplicate", "model_ceiling"]
)
def test_admission_stops_before_dispatch(packet, fault):
    p = trial.verify(packet)
    call = {
        "id": "previous",
        "state": "observed",
        "adapter": "codex",
        "model": "gpt-6-astra",
        "estimated_credits": 1,
    }
    ledger = {"calls": [call]}
    if fault == "unknown":
        call["estimated_credits"] = None
    elif fault == "inflight":
        call["state"] = "dispatching"
    elif fault == "budget":
        call["estimated_credits"] = 241
    elif fault == "duplicate":
        call["id"] = "next"
    else:
        ledger["calls"] = [{**call, "id": str(i)} for i in range(16)]
    with pytest.raises(ValueError):
        trial.admit(p, ledger, "gpt-6-astra", "next")


def test_usage_does_not_assume_missing_cache_zero_or_double_count_reasoning():
    assert (
        trial.estimate("gpt-6-astra", {"input_tokens": 100, "output_tokens": 10})
        is None
    )
    usage = {
        "input_tokens": 100,
        "cached_input_tokens": 20,
        "output_tokens": 10,
        "reasoning_output_tokens": 7,
    }
    assert trial.estimate("gpt-6-astra", usage) == pytest.approx(0.033)


@pytest.mark.parametrize(
    "fault", ["wrong_type", "contradiction", "missing", "duplicate", "failed_control"]
)
def test_grades_fail_closed_or_retain_control_failure(fault):
    data = good_grades()
    if fault == "wrong_type":
        data["grades"][0]["correct"] = "true"
    elif fault == "contradiction":
        data["grades"][0]["critical_miss"] = True
    elif fault == "missing":
        data["grades"].pop()
    elif fault == "duplicate":
        data["grades"][1]["id"] = "sample"
    else:
        data["grades"][1]["correct"] = False
        assert not trial.controls_pass(trial.decode_grade(json.dumps(data)))
        return
    with pytest.raises(ValueError):
        trial.decode_grade(json.dumps(data))


def test_complete_installed_task_and_grader_pipeline_offline(packet, monkeypatch):
    from attune_harness import process

    monkeypatch.setattr(process, "invoke", fake_process)
    trial.execute(packet)
    result = trial.audit(packet)
    assert result["calls"] == 64 and result["controls_passed"] == 32
    assert result["model_grading_floor"] == "met_pending_assistant_audit"
    assert result["billed_dollars"] is None and result["human_grading"] is None
    with pytest.raises(ValueError, match="no replay"):
        trial.execute(packet)
    ledger = trial.read(packet / "ledger.json")
    ledger["grades"][0]["grades"]["sample"]["correct"] = False
    trial.write(packet / "ledger.json", ledger)
    with pytest.raises(ValueError, match="Grades differ"):
        trial.audit(packet)


def test_missing_source_prevents_first_native_call(packet):
    protocol = trial.verify(packet)
    case = protocol["fixture"]["cases"][0]
    meter = trial.Meter(packet, protocol, {"calls": []})
    factory = meter.factory("a01", case)
    exchange = factory(protocol["profiles"]["codex"], packet)
    with pytest.raises(ValueError, match="reference missing"):
        exchange(json.dumps({"turn": {"initial_retrieval": {"sources": []}}}))
    assert meter.ledger["calls"] == []


def test_intent_saved_before_native_and_interrupted_call_not_replayed(
    packet, monkeypatch
):
    from attune_harness import process
    from attune_harness.process import ProcessResult

    def interrupted(argv, prompt, **kw):
        ledger = trial.read(packet / "ledger.json")
        assert (
            len(ledger["calls"]) == 1 and ledger["calls"][0]["state"] == "dispatching"
        )
        return ProcessResult(argv, -9, "", "", "timeout_effects_unknown")

    monkeypatch.setattr(process, "invoke", interrupted)
    with pytest.raises(ValueError, match="did not complete"):
        trial.execute(packet)
    ledger = trial.read(packet / "ledger.json")
    assert ledger["status"] == "stopped" and len(ledger["calls"]) == 1
    assert ledger["calls"][0]["state"] == "unresolved"
    with pytest.raises(ValueError, match="no replay"):
        trial.execute(packet)


def test_credentials_removed_only_in_child_environment(monkeypatch):
    import os

    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        monkeypatch.setenv(key, "offline-placeholder")
    env = trial.subscription_environment()
    assert (
        "OPENAI_API_KEY" not in env
        and os.environ["OPENAI_API_KEY"] == "offline-placeholder"
    )
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://invalid.example")
    with pytest.raises(ValueError, match="routing"):
        trial.subscription_environment()


@pytest.fixture
def stopped_packet(packet, monkeypatch):
    from attune_harness import process

    monkeypatch.setattr(process, "invoke", fake_process)
    original = repair.base.Meter.native

    def stop_after_43(self, call_id, adapter, **kwargs):
        if call_id == "g12":
            raise ValueError("offline controlled stop")
        return original(self, call_id, adapter, **kwargs)

    with monkeypatch.context() as context:
        context.setattr(repair.base.Meter, "native", stop_after_43)
        with pytest.raises(ValueError, match="controlled stop"):
            repair.base.execute(packet)
    assert len(repair.read(packet / "ledger.json")["calls"]) == 43
    return packet


def fake_amended_grade(argv, prompt, **options):
    from attune_harness.process import ProcessResult

    request = json.loads(prompt.split("\n", 1)[1])
    items = json.loads(request["attempt"]["task"]["objective"])
    samples = [item for item in items if item["id"] not in {"v1", "v2", "v3"}]
    assert len(samples) == 2
    for item in samples:
        assert (
            "[Cedar reference](references/cedar-source.md)" in item["document"]["text"]
        )
        assert item["references"][0]["sha256"] and item["limited_tool_checks"]
        assert set(item) == {
            "id",
            "document",
            "references",
            "limited_tool_checks",
            "judgment_scope",
            "requirements",
            "assessment",
        }
    good = good_grades()["grades"]
    text = json.dumps(
        {"grades": [{**good[0], "id": item["id"]} for item in samples] + good[1:]}
    )
    model = argv[argv.index("--model") + 1]
    if model.startswith("claude"):
        raw = json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "session_id": "offline",
                "structured_output": {"text": text},
                "modelUsage": {model: {}},
                "usage": {"input_tokens": 100, "output_tokens": 10},
            }
        )
    else:
        raw = "\n".join(
            json.dumps(v)
            for v in [
                {"type": "thread.started", "thread_id": "offline"},
                {"type": "turn.started"},
                {
                    "type": "item.completed",
                    "item": {
                        "type": "agent_message",
                        "text": json.dumps({"text": text}),
                    },
                },
                {
                    "type": "turn.completed",
                    "usage": {
                        "input_tokens": 100,
                        "cached_input_tokens": 0,
                        "output_tokens": 10,
                    },
                },
            ]
        )
    return ProcessResult(argv, 0, raw, "")


def test_amendment_preserves_complete_evidence_budget_and_old_receipts(
    stopped_packet, monkeypatch
):
    from attune_harness import process

    parent = stopped_packet
    old_ledger = (parent / "ledger.json").read_bytes()
    output = parent / "grading-amendment"
    p = repair.prepare(parent, output)
    assert len(p["batches"]) == 16
    assert len({s["id"] for b in p["batches"] for s in b["samples"]}) == 32
    cases = {t["id"]: t["case"] for t in p["trials"]}
    for batch in p["batches"]:
        assert len({cases[s["id"]] for s in batch["samples"]}) == 2
        for sample in batch["samples"]:
            assert sample["document"]["path"] == "guide.md"
            assert "objective" not in sample and "arm" not in sample
            saved = repair.read(parent / "calls" / sample["id"] / "request.json")
            native = json.loads(saved["prompt"].split("\n", 1)[1])
            visible = json.loads(native["attempt"]["task"]["objective"])
            assert sample["document"]["text"] == visible["document"]["text"]
            assert sample["references"] == visible["references"]
            assert sample["limited_tool_checks"] == visible["limited_tool_checks"]
            assert sample["judgment_scope"] == visible["judgment_scope"]
    monkeypatch.setattr(process, "invoke", fake_amended_grade)
    repair.execute(output)
    audit = repair.audit(output)
    assert audit["total_calls"] == 59 and audit["graded_outputs"] == 32
    assert audit["discarded_initial_grading_calls"] == 11
    assert audit["controls_passed_by_batch"] == 16
    assert (parent / "ledger.json").read_bytes() == old_ledger
    with pytest.raises(ValueError, match="no automatic replay"):
        repair.execute(output)
    ledger = repair.read(output / "ledger.json")
    ledger["calls"][0]["estimated_credits"] = 0
    repair.write(output / "ledger.json", ledger)
    with pytest.raises(ValueError, match="accounting"):
        repair.audit(output)


def test_missing_assessor_evidence_is_rejected_before_grade_dispatch(stopped_packet):
    p = repair.base.verify(stopped_packet)
    ledger = repair.read(stopped_packet / "ledger.json")
    row = ledger["assessments"][0]
    case_id = next(t["case"] for t in p["trials"] if t["id"] == row["id"])
    case = next(c for c in p["fixture"]["cases"] if c["id"] == case_id)
    path = stopped_packet / "calls" / row["id"] / "request.json"
    envelope = repair.read(path)
    prefix, encoded = envelope["prompt"].split("\n", 1)
    request = json.loads(encoded)
    evidence = json.loads(request["attempt"]["task"]["objective"])
    evidence["limited_tool_checks"] = []
    request["attempt"]["task"]["objective"] = json.dumps(evidence)
    envelope["prompt"] = prefix + "\n" + json.dumps(request)
    repair.write(path, envelope)
    with pytest.raises(ValueError, match="host-check"):
        repair.supplied_item(stopped_packet, row, case)


def test_amended_grade_identifiers_cannot_drop_or_duplicate_outputs():
    good = good_grades()["grades"]
    rows = [{**good[0], "id": "a01"}, {**good[0], "id": "a02"}] + good[1:]
    assert set(repair.decode(json.dumps({"grades": rows}), ["a01", "a02"])) == {
        "a01",
        "a02",
    }
    rows[1]["id"] = "a01"
    with pytest.raises(ValueError, match="identities"):
        repair.decode(json.dumps({"grades": rows}), ["a01", "a02"])
