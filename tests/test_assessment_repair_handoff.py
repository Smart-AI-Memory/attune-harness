"""Structured assessment identity can feed repair without granting effects."""

import json
from pathlib import Path
import sys

import pytest

from attune_harness.review_store import RunStore
from attune_harness.task_contract import (
    accept_task,
    create_task,
    create_repair_task,
    read_task,
    revise_task,
)
from attune_harness.task_handoff import completed_assessment
from attune_harness.task_policies import execute_task
from test_review import case, change, scripted
from test_task_contract import draft, response


def assessment_payload(role="assessor"):
    findings = []
    if role == "assessor":
        findings.append(
            {
                "id": "quartz-source",
                "severity": "high",
                "text": "The implementation contradicts the selected evidence.",
                "evidence": ["project/guide.md links the retained policy"],
            }
        )
    return {
        "schema_version": 1,
        "kind": "assessment-findings-v1",
        "findings": findings,
        "notes": ["No additional repair candidate."],
    }


def complete_assessment(case, *, structured=True, provider=False):
    if structured:
        change(
            case[1],
            lambda value: value.update(
                participants={
                    name: {
                        "adapter": "command",
                        "command": [sys.executable, "-c", "raise SystemExit(9)"],
                        "timeout": 10,
                        "tools": ["retrieve", "verify"],
                        "max_turns": 3,
                        "max_tool_calls": 2,
                    }
                    for name in ("alpha", "beta")
                }
            ),
        )
    draft(
        case,
        plan="independent-review",
        result_profile="assessment-findings-v1" if structured else None,
    )
    submission = response(case[2])
    submission["permissions"]["external"] = structured
    submission['permissions']['provider'] = provider
    accept_task(case[2], submission)

    def action(packet):
        if not structured:
            text = "Narrative only; no repair identity was requested."
        else:
            text = json.dumps(assessment_payload(packet["turn"]["role"]))
        return {"kind": "final", "text": text}

    result = execute_task(case[2], exchange_factory=scripted(action))
    assert result["status"] == "completed"
    return result


@pytest.mark.parametrize("mode", ["deterministic", "evidence"])
def test_structured_profile_rejects_transports_that_rewrite_results(case, mode):
    if mode == "evidence":
        change(
            case[1],
            lambda value: value.update(
                participants={
                    name: {
                        "adapter": "claude",
                        "model": "configured-model",
                        "review_mode": "evidence",
                        "timeout": 10,
                        "tools": ["retrieve", "verify"],
                        "max_turns": 3,
                        "max_tool_calls": 2,
                    }
                    for name in ("alpha", "beta")
                }
            ),
        )
    with pytest.raises(ValueError, match="exact final-text transport"):
        draft(case, result_profile="assessment-findings-v1")
    assert not case[2].exists()


def test_structured_profile_allows_incomplete_draft_then_checks_selected_transport(case):
    record = create_task(
        case[0].parent,
        case[1],
        goal="Check the guide",
        plan="independent-review",
        directory=case[2],
        answers={
            "criteria": "Preserve uncertainty",
            "query": "quartz",
            "document": "project/guide.md",
            "context": "context.json",
            "corpus": "project",
        },
        result_profile="assessment-findings-v1",
    )
    assert record["request"]["answers"]["assessor"] is None
    assert record["request"]["answers"]["reviewer"] is None
    before = (case[2] / "record.json").read_bytes()
    with pytest.raises(ValueError, match="exact final-text transport"):
        revise_task(
            case[2],
            checkpoint=record["checkpoint_digest"],
            answers={"assessor": "alpha", "reviewer": "beta"},
        )
    assert (case[2] / "record.json").read_bytes() == before


def repair_inputs(case, *, allowed=("app.py",), source=None, finding_ids=None, directory=None):
    project = case[0].parent
    checkout = project / "project"
    (checkout / ".git").mkdir(exist_ok=True)
    (checkout / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (checkout / "probe.py").write_text("assert True\n", encoding="utf-8")
    probe = {
        "argv": [sys.executable, "-B", "probe.py"],
        "cwd": ".",
        "timeout": 10,
        "max_output_bytes": 4096,
        "environment": {
            "PATH": "/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        },
        "oracle_paths": ["probe.py"],
    }
    return create_repair_task(
        project,
        case[1],
        goal="Repair the selected implementation defect",
        checkout=checkout,
        allowed=list(allowed),
        probe=probe,
        worker="alpha",
        criteria="Preserve the documented behavior and pass the frozen probe",
        reviewer="beta",
        directory=directory or project / "repair",
        source_assessment=source,
        finding_ids=finding_ids,
    )


def test_completed_assessment_binding_retains_actual_selected_result(case):
    assessment = complete_assessment(case)
    repair = repair_inputs(
        case, source=case[2], finding_ids=["quartz-source"]
    )
    binding = repair["request"]["repair"]["source_assessment"]
    selected = binding["findings"]
    assert binding["task_id"] == assessment["request"]["task_id"]
    assert binding["checkpoint_digest"] == assessment["checkpoint_digest"]
    assert [(item["id"], item["role"]) for item in selected] == [
        ("quartz-source", "assessor")
    ]
    assert selected[0]["participant_id"] == "alpha"
    assert repair["request"]["answers"]["goal"].startswith("Repair")
    assert repair["request"]["repair"]["scope"]["allowed"] == ["app.py"]
    accepted = accept_task(Path(repair["record_path"]).parent, response(Path(repair["record_path"]).parent))
    assert accepted["status"] == "accepted"


@pytest.mark.parametrize(
    "structured,finding_ids,match",
    [
        (False, ["quartz-source"], "structured assessment"),
        (True, ["unknown"], "unavailable"),
        (True, ["quartz-source", "quartz-source"], "unique"),
    ],
)
def test_legacy_unknown_and_duplicate_finding_selection_are_refused(
    case, structured, finding_ids, match
):
    complete_assessment(case, structured=structured)
    with pytest.raises(ValueError, match=match):
        repair_inputs(case, source=case[2], finding_ids=finding_ids)
    assert not (case[0].parent / "repair").exists()


@pytest.mark.parametrize("mutation", ["summary", "event"])
def test_assessment_projection_and_journal_must_agree(case, mutation):
    complete_assessment(case)
    stored = read_task(case[2])
    if mutation == "summary":
        stored["execution"]["integration"]["scope"] = "forged"
    else:
        event = next(
            item
            for item in stored["execution"]["events"]
            if item["kind"] == "participant_turn"
        )
        event["result"]["action"]["text"] = json.dumps(
            {**assessment_payload(), "notes": ["forged journal"]}
        )
    RunStore(case[2], existing=True).save(stored)
    with pytest.raises(ValueError):
        completed_assessment(case[2], ["quartz-source"])


@pytest.mark.parametrize("mutation", ["source", "owner", "binding"])
def test_repair_acceptance_rechecks_assessment_owner(case, mutation):
    complete_assessment(case)
    repair = repair_inputs(
        case, source=case[2], finding_ids=["quartz-source"]
    )
    repair_dir = Path(repair["record_path"]).parent
    submission = response(repair_dir)
    if mutation == "source":
        (case[0].parent / "context.json").write_text(
            '{"schema_version":1,"project_root":"project","changed":true}\n',
            encoding="utf-8",
        )
    elif mutation == "owner":
        (case[2] / "record.json").unlink()
    else:
        stored = read_task(repair_dir)
        stored["request"]["repair"]["source_assessment"]["findings"][0][
            "text"
        ] = "Caller-forged finding"
        RunStore(repair_dir, existing=True).save(stored)
    with pytest.raises((ValueError, FileNotFoundError, RuntimeError)):
        accept_task(repair_dir, submission)


@pytest.mark.parametrize("allowed", [("guide.md",), ("reference.md",)])
def test_repair_scope_uses_effect_aware_binding_for_assessment_inputs(case, allowed):
    complete_assessment(case)
    record = repair_inputs(
        case, allowed=allowed, source=case[2], finding_ids=["quartz-source"]
    )
    binding = record['request']['repair']['source_assessment']
    assert binding['kind'] == 'completed-assessment-effects-v1'
    assert binding['index_identity'] is None


def test_assessment_binding_is_project_local(case, tmp_path):
    complete_assessment(case)
    other = tmp_path / "other"
    other.mkdir()
    checkout = other / "checkout"
    checkout.mkdir()
    (checkout / ".git").mkdir()
    (checkout / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (checkout / "probe.py").write_text("assert True\n", encoding="utf-8")
    probe = {
        "argv": [sys.executable, "-B", "probe.py"],
        "cwd": ".",
        "timeout": 10,
        "max_output_bytes": 4096,
        "environment": {
            "PATH": "/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        },
        "oracle_paths": ["probe.py"],
    }
    with pytest.raises(ValueError, match="same project"):
        create_repair_task(
            other,
            case[1],
            goal="Repair",
            checkout=checkout,
            allowed=["app.py"],
            probe=probe,
            worker="alpha",
            criteria="Pass",
            reviewer="beta",
            directory=other / "repair",
            source_assessment=case[2],
            finding_ids=["quartz-source"],
        )
