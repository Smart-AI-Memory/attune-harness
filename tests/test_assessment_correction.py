"""Transport and evaluator-contract regressions; injected replies are not model grades."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "assessment_correction", ROOT / "experiments/assessment_quality/correction.py"
)
correction = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(correction)
base = correction.base
RUN_SPEC = importlib.util.spec_from_file_location(
    "run_correction", ROOT / "experiments/assessment_quality/run_correction.py"
)
runner = importlib.util.module_from_spec(RUN_SPEC)
RUN_SPEC.loader.exec_module(runner)


@pytest.fixture
def parent(tmp_path):
    wheel = tmp_path / "offline.whl"
    wheel.write_bytes(b"offline identity, not an installed wheel")
    directory = tmp_path / "parent"
    protocol = base.prepare(directory, wheel)
    base.write(directory / "ledger.json", {"calls": []})
    amended = copy.deepcopy(protocol)
    amended.update(
        parent=str(directory),
        parent_ledger_sha256=base.file_hash(directory / "ledger.json"),
    )
    target = directory / "grading-amendment"
    target.mkdir()
    base.write(target / "protocol.json", amended)
    base.write(
        target / "admission.json",
        {
            "protocol_sha256": base.digest(amended),
            "authorization": amended["authorization"],
        },
    )
    # Synthetic usage for proposal arithmetic, never reported as real charges.
    base.write(
        target / "ledger.json",
        {
            "calls": [
                {"id": "a01", "model": "gpt-6-astra", "estimated_credits": 5},
                {"id": "r01", "model": "gpt-5.6-sol", "estimated_credits": 2},
            ]
        },
    )
    base.write(
        directory / "manifest.json",
        {
            "sha256": {
                str(p.relative_to(directory)): base.file_hash(p)
                for p in directory.rglob("*.json")
            }
        },
    )
    return directory


@pytest.fixture
def prepared(parent, tmp_path):
    output = tmp_path / "correction"
    result = correction.prepare(output, parent)
    return output, result


def grades(fixture):
    rows = [
        {
            "id": name,
            "correct": True,
            "critical_miss": False,
            "unsupported_findings": [],
            "missed_defects": [],
            "rationale": "Offline grading-contract example",
        }
        for name in ("sample", "v1", "v2", "v3", "u1", "u2", "u3")
    ]
    by_id = {row["id"]: row for row in rows}
    by_id["v2"].update(
        correct=False, unsupported_findings=["invented birthday requirement"]
    )
    by_id["v3"].update(
        correct=False, critical_miss=True, missed_defects=["operational contradiction"]
    )
    by_id["u1"].update(
        correct=False, missed_defects=["required correction was made optional"]
    )
    by_id["u3"].update(
        correct=False,
        unsupported_findings=["key storage asserted as software without support"],
    )
    return {"grades": rows}


def test_installed_rehearsal_keeps_live_unavailable_and_retained_evidence_intact(
    prepared, parent
):
    output, result = prepared
    assert result == {
        "mode": "offline software checks only; semantic quality unmeasured",
        "proposal_sha256": base.digest(base.read(output / "proposal.json")),
        "fresh_case_transport_runs": 16,
        "retained_case_transport_runs": 16,
        "grading_packets": 8,
        "controls_per_packet": 6,
        "original_files_unchanged": correction.check_retained(parent),
        "provider_calls": 0,
    }
    assert not (output / "protocol.json").exists()
    assert not (output / "admission.json").exists()
    with pytest.raises(FileNotFoundError):
        base.execute(output)


def test_grader_evidence_equals_actual_assessor_evidence_and_is_blind(prepared):
    output, _ = prepared
    plan = base.read(output / "proposal.json")
    cases = {c["id"]: c for c in plan["fixture"]["cases"]}
    trials = {t["id"]: t for t in plan["trials"]}
    packets = base.read(output / "offline-grading-packets.json")
    seen = []
    for batch in packets["batches"]:
        assert len(batch["items"]) == 8
        assert len({trials[i["id"]]["case"] for i in batch["items"][:2]}) == 2
        for item in batch["items"][:2]:
            seen.append(item["id"])
            row = trials[item["id"]]
            case = cases[row["case"]]
            native = base.read(output / "offline/calls" / row["id"] / "request.json")
            task = json.loads(native["prompt"].split("\n", 1)[1])["attempt"]["task"]
            evidence = json.loads(task["objective"])
            assert plan["fixture"][row["arm"]] in evidence["objective"]
            assert (
                item["document"]["text"]
                == evidence["document"]["text"]
                == case["document"]
                + "\n\n[Cedar reference](references/cedar-source.md)\n"
            )
            assert item["references"] == evidence["references"]
            assert item["limited_tool_checks"] == evidence["limited_tool_checks"]
            assert item["judgment_scope"] == evidence["judgment_scope"]
            assert item["requirements"] == case["requirements"]
            assert "key" not in item and "arm" not in item and "family" not in item
            assert "objective" not in item and "expected" not in item
            assert str(output) not in json.dumps(item)
            assert correction.INJECTED in item["assessment"]
            assert all(
                check["semantic_ran"] is False for check in item["limited_tool_checks"]
            )
    assert sorted(seen) == sorted(trials)
    for control in packets["batches"][0]["items"][2:]:
        assert "expected" not in control


@pytest.mark.parametrize("field", ["document", "references", "limited_tool_checks"])
def test_lost_assessor_evidence_blocks_grading(prepared, field):
    output, _ = prepared
    plan = base.read(output / "proposal.json")
    row = plan["trials"][0]
    case = next(c for c in plan["fixture"]["cases"] if c["id"] == row["case"])
    path = output / "offline/calls" / row["id"] / "request.json"
    envelope = base.read(path)
    prefix, body = envelope["prompt"].split("\n", 1)
    native = json.loads(body)
    evidence = json.loads(native["attempt"]["task"]["objective"])
    evidence[field] = {"text": case["document"]} if field == "document" else []
    native["attempt"]["task"]["objective"] = json.dumps(evidence)
    envelope["prompt"] = prefix + "\n" + json.dumps(native)
    base.write(path, envelope)
    with pytest.raises(ValueError):
        correction.repair.supplied_item(
            output / "offline", {"id": row["id"], "text": correction.INJECTED}, case
        )


@pytest.mark.parametrize(
    "fault",
    [
        "optional_passed",
        "unknown_failed",
        "opposite_passed",
        "gap_mislabeled",
        "missing_control",
        "duplicate_control",
        "missing_sample",
    ],
)
def test_controls_reject_wrong_disposition_overcorrection_and_dropped_items(fault):
    fixture = base.read(correction.FIXTURE)
    packet = grades(fixture)
    correct = correction.decode_grades(json.dumps(packet), ["sample"], fixture)
    assert correct["sample"]["controls_pass"] is True
    rows = {r["id"]: r for r in packet["grades"]}
    if fault == "optional_passed":
        rows["u1"].update(correct=True, missed_defects=[])
    elif fault == "unknown_failed":
        rows["u2"].update(
            correct=False, unsupported_findings=["unknown treated as defect"]
        )
    elif fault == "opposite_passed":
        rows["u3"].update(correct=True, unsupported_findings=[])
    elif fault == "gap_mislabeled":
        rows["u1"]["critical_miss"] = True
    elif fault == "missing_control":
        packet["grades"].remove(rows["u2"])
    elif fault == "duplicate_control":
        rows["u2"]["id"] = "u1"
    else:
        packet["grades"].remove(rows["sample"])
    if fault in {"missing_control", "duplicate_control", "missing_sample"}:
        with pytest.raises(ValueError):
            correction.decode_grades(json.dumps(packet), ["sample"], fixture)
    else:
        assert (
            correction.decode_grades(json.dumps(packet), ["sample"], fixture)["sample"][
                "controls_pass"
            ]
            is False
        )


def test_failed_sample_is_not_rescued_by_passing_controls():
    fixture = base.read(correction.FIXTURE)
    packet = grades(fixture)
    packet["grades"][0].update(
        correct=False, missed_defects=["required correction missing"]
    )
    result = correction.decode_grades(json.dumps(packet), ["sample"], fixture)["sample"]
    assert result["controls_pass"] and not result["sample"]["correct"]


def test_proposed_counts_and_estimate_follow_comparison_roles(parent):
    plan = correction.proposal(parent)
    counts = {m: 0 for m in plan["proposed_allocation"]["max_calls_by_model"]}
    for profile in [r["family"] for r in plan["trials"]] + [
        b["profile"] for b in plan["grading_batches"]
    ]:
        counts[plan["profiles"][profile]["model"]] += 1
    assert counts == plan["proposed_allocation"]["max_calls_by_model"]
    assert sum(counts.values()) == plan["proposed_allocation"]["max_calls"] == 24
    assert plan["proposed_allocation"]["empirical_point_estimate"] == 48
    assert "authorization" not in plan
    assert not (
        {c["id"] for c in plan["fixture"]["cases"]}
        & {c["id"] for c in base.read(base.FIXTURES)["cases"]}
    )


def test_old_receipt_change_stops_preparation(parent, tmp_path):
    path = parent / "grading-amendment/ledger.json"
    path.write_text(path.read_text() + "\n")
    with pytest.raises(ValueError, match="Retained experiment evidence changed"):
        correction.prepare(tmp_path / "proposal", parent)
    assert not (tmp_path / "proposal").exists()


def test_missing_prior_credit_usage_is_not_estimated_as_zero(parent):
    path = parent / "grading-amendment/ledger.json"
    ledger = base.read(path)
    ledger["calls"][0]["estimated_credits"] = None
    base.write(path, ledger)
    manifest = base.read(parent / "manifest.json")
    manifest["sha256"]["grading-amendment/ledger.json"] = base.file_hash(path)
    base.write(parent / "manifest.json", manifest)
    with pytest.raises(ValueError, match="Unknown retained Codex credit usage"):
        correction.proposal(parent)


@pytest.fixture
def allocated(prepared, tmp_path, monkeypatch):
    from attune_harness import process

    def forbidden(*args, **kwargs):
        pytest.fail("Offline allocation test attempted a native process")

    monkeypatch.setattr(process, "invoke", forbidden)
    folder, _ = prepared
    base.write(
        folder / "manifest.json",
        {
            "sha256": {
                str(p.relative_to(folder)): base.file_hash(p)
                for p in folder.rglob("*")
                if p.is_file()
            }
        },
    )
    plan = base.read(folder / "proposal.json")
    approval = {
        "source": "offline test fixture only",
        "proposal_sha256": base.digest(plan),
        "allocation": plan["proposed_allocation"],
        "answer": "A — Run the bounded comparison (Recommended)",
    }
    output = tmp_path / "allocated"
    runner.prepare(folder, output, approval)
    return folder, output, approval


def simulated_native(argv, prompt, **options):
    from attune_harness.process import ProcessResult

    attempt = json.loads(prompt.split("\n", 1)[1])["attempt"]
    if attempt["role"] == "reviewer":
        items = json.loads(attempt["task"]["objective"])
        assert len(items) == 8 and all("expected" not in item for item in items)
        packet = grades(None)
        packet["grades"] = [r for r in packet["grades"] if r["id"] != "sample"] + [
            {
                "id": item["id"],
                "correct": True,
                "critical_miss": False,
                "unsupported_findings": [],
                "missed_defects": [],
                "rationale": "Offline injected grade",
            }
            for item in items[:2]
        ]
        text = json.dumps(packet)
    else:
        text = correction.INJECTED
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
        response = "\n".join(
            json.dumps(event)
            for event in [
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
    assert "OPENAI_API_KEY" not in options["environment"]
    assert "ANTHROPIC_API_KEY" not in options["environment"]
    return ProcessResult(argv, 0, response, "")


def test_allocated_pipeline_matches_grader_packets_and_prevents_replay(
    allocated, monkeypatch
):
    from attune_harness import process

    _, output, _ = allocated
    monkeypatch.setattr(process, "invoke", simulated_native)
    with pytest.raises(FileNotFoundError):
        runner.execute(output, "grade")
    runner.execute(output, "assess")
    with pytest.raises(ValueError, match="no automatic replay"):
        runner.execute(output, "assess")
    base.write(output / "lead-review.json", {"mode": "offline injected review"})
    runner.execute(output, "grade")
    result = runner.audit(output)
    assert result["calls"] == 24 and result["graded_outputs"] == 16
    assert result["controls_passed_by_batch"] == 8
    assert result["model_grading_floor"] == "met_pending_lead_reconciliation"
    assert result["promotion"] == "not_authorized"
    with pytest.raises(ValueError, match="no prior grade dispatch"):
        runner.execute(output, "grade")
    with pytest.raises(ValueError, match="ceiling exhausted"):
        base.admit(
            base.read(output / "protocol.json"),
            base.read(output / "ledger.json"),
            "gpt-6-astra",
            "unexpected",
        )
    ledger = base.read(output / "ledger.json")
    ledger["batches"][0]["grades"][next(iter(ledger["batches"][0]["grades"]))][
        "sample"
    ]["rationale"] = "altered"
    base.write(output / "ledger.json", ledger)
    with pytest.raises(ValueError, match="Grades differ"):
        runner.audit(output)


@pytest.mark.parametrize("field", ["answer", "allocation", "proposal_sha256"])
def test_mismatched_allocation_never_creates_admission(allocated, tmp_path, field):
    folder, _, approval = allocated
    approval[field] = "changed"
    output = tmp_path / "bad-allocation"
    with pytest.raises(ValueError, match="Explicit allocation"):
        runner.prepare(folder, output, approval)
    assert not output.exists()


def test_failed_controls_survive_audit_as_failure(allocated, monkeypatch):
    from attune_harness import process

    _, output, _ = allocated
    original_decode = runner.correction.decode_grades

    def failed_controls(*args):
        parsed = original_decode(*args)
        for row in parsed.values():
            row["controls_pass"] = False
        return parsed

    monkeypatch.setattr(process, "invoke", simulated_native)
    monkeypatch.setattr(runner.correction, "decode_grades", failed_controls)
    runner.execute(output, "assess")
    base.write(output / "lead-review.json", {"mode": "offline injected review"})
    runner.execute(output, "grade")
    result = runner.audit(output)
    assert result["controls_passed_by_batch"] == 0
    assert result["model_grading_floor"] == "revise_or_arbitrate"
