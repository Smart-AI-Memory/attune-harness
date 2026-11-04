"""Offline CSV fixture: actual owners and checks, no human/model performance claim."""

# qualify: platform

import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys

import pytest

from attune_harness import review_participants
from attune_harness.recovery import UnresolvedOperation
from attune_harness.task_contract import read_task
from attune_harness.work_contract import bind_work_acceptance, missing_information
from attune_harness.work_runtime import build_work

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "csv-evaluation"


def load(name):
    spec = importlib.util.spec_from_file_location(f"csv_fixture_{name}", EXAMPLE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fixture, oracle, reference = (load(name) for name in ("fixture", "oracle", "reference"))


@pytest.fixture(autouse=True)
def no_provider_dispatch(monkeypatch):
    def poison(*args, **kwargs):
        pytest.fail("CSV fixture attempted native or external participant dispatch")
    monkeypatch.setattr(review_participants, "NativeExchange", poison)
    monkeypatch.setattr(review_participants.ReviewExchange, "__call__", poison)


@pytest.fixture
def cases():
    return json.loads((EXAMPLE / "cases.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("scope", fixture.SCOPES)
def test_reference_passes_all_frozen_cases(cases, scope):
    result = oracle.evaluate(reference.export_csv, cases, scope)
    assert result["passed"]
    assert len(result["cases"]) == 6
    assert all(all(item["checks"].values()) for item in result["cases"])


def broken(kind):
    def candidate(rows, **kwargs):
        if kind == "all-records":
            kwargs["scope"] = "all_matching"
        if kind == "ignore-filter":
            for row in rows:
                row["status"] = kwargs["status"]
        text = reference.export_csv(rows, **kwargs)
        data = list(csv.reader(io.StringIO(text, newline="")))
        if kind == "reverse":
            data[1:] = reversed(data[1:])
        elif kind == "private-column":
            data = [row + ["private_notes"] for row in data]
        elif kind == "private-value" and len(data) > 1:
            data[1][1] = "PRIVATE-r1"
        elif kind == "wrong-header":
            data[0][0] = "identifier"
        elif kind == "no-header":
            data = data[1:]
        elif kind == "missing":
            return None
        elif kind == "exception":
            raise RuntimeError("Seeded failure")
        elif kind == "bad-quotes":
            return "\n".join(",".join(row) for row in data)
        output = io.StringIO(newline="")
        csv.writer(output).writerows(data)
        return output.getvalue()
    return candidate


@pytest.mark.parametrize("kind", ["all-records", "ignore-filter", "reverse", "private-column",
                                 "private-value", "wrong-header", "no-header", "missing",
                                 "exception", "bad-quotes"])
def test_seeded_exporter_failures_are_detected(cases, kind):
    result = oracle.evaluate(broken(kind), cases, "current_page")
    assert not result["passed"], kind
    assert len(result["cases"]) == 6


def test_candidate_cannot_change_later_expected_cases_via_input(cases):
    before = json.dumps(cases)
    def mutate(rows, **kwargs):
        rows.clear()
        return "id,title,status\r\n"
    assert not oracle.evaluate(mutate, cases, "current_page")["passed"]
    assert json.dumps(cases) == before


@pytest.mark.parametrize("variant,missing", [("correction", True), ("simple", True), ("fully-specified", False)])
def test_preparation_is_unaccepted_and_only_material_question_is_missing(tmp_path, variant, missing):
    root = tmp_path.resolve() / "trial"
    record = fixture.prepare(root, variant)
    assert record["status"] == "draft" and record["acceptance"] is None
    assert "build" not in record
    assert bool(missing_information(record["request"])) is missing
    assert len(record["request"]["intent"]["questions"]) == int(missing)
    assert record["request"]["effects"]["allowed"] == ["exporter.py"]
    assert record["request"]["effects"]["protected"] == fixture.PROTECTED
    assert all(p["adapter"] == "deterministic" for p in record["request"]["registry"]["participants"].values())
    with pytest.raises(ValueError, match="accepted work authority"):
        build_work(root / "task", exchange_factory=fixture.ScriptedProposal)
    if missing:
        with pytest.raises(ValueError, match="Unresolved material intent"):
            bind_work_acceptance(root / "task", fixture.synthetic_decision(record))


def test_correction_revises_every_effective_scope_and_preserves_history(tmp_path):
    root = tmp_path.resolve() / "trial"
    draft = fixture.prepare(root)
    initial = fixture.correct(root, "all_matching", draft["checkpoint_digest"])
    old_decision = fixture.synthetic_decision(initial)
    bind_work_acceptance(root / "task", old_decision)
    accepted = read_task(root / "task")
    corrected = fixture.correct(root, "current_page", accepted["checkpoint_digest"])
    assert corrected["acceptance"] is None
    assert corrected["history"][-1]["acceptance"] is not None
    request = corrected["request"]
    assert request["intent"]["questions"][0]["answer"] == "current_page"
    assert request["intent"]["acceptance"] == fixture.criteria("current_page")
    assert request["tasks"] == fixture.steps("current_page")
    assert all(v["probe"]["argv"][-1] == "current_page" for v in request["effects"]["verification"])
    assert corrected["history"][-1]["request"]["intent"]["questions"][0]["answer"] == "all_matching"
    before = (root / "task" / "record.json").read_bytes()
    with pytest.raises(ValueError, match="Stale"):
        fixture.correct(root, "all_matching", draft["checkpoint_digest"])
    with pytest.raises(ValueError, match="Stale"):
        bind_work_acceptance(root / "task", old_decision)
    assert (root / "task" / "record.json").read_bytes() == before
    assert read_task(root / "task")["request"] == request


def test_protected_oracle_change_blocks_build(tmp_path):
    root = tmp_path.resolve() / "trial"
    record = fixture.prepare(root, "fully-specified")
    bind_work_acceptance(root / "task", fixture.synthetic_decision(record))
    (root / "app" / "oracle.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    with pytest.raises(UnresolvedOperation, match="Checkout differs"):
        build_work(root / "task", exchange_factory=fixture.ScriptedProposal)


@pytest.mark.parametrize("variant,revisions", [("correction", 3), ("simple", 2), ("fully-specified", 1)])
def test_real_build_smoke_and_receipt(tmp_path, variant, revisions):
    root = tmp_path.resolve() / "trial"
    receipt = fixture.smoke(root, variant)
    assert receipt["passed"], read_task(root / "task").get("build")
    assert len(receipt["revisions"]) == revisions
    assert receipt["synthetic_acceptance"] is True and receipt["model_calls"] == 0
    assert all(receipt[key] is None for key in ("human_performance", "ai_performance", "token_usage"))
    record = read_task(root / "task")
    probes = [e for e in record["build"]["events"] if e["kind"] == "acceptance_probe"]
    assert len(probes) == 2 and all(e["result"]["passed"] for e in probes)
    for name, expected in json.loads((root / "manifest.json").read_text())["sha256"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected
    # Proposals are UTF-8 text; repository checkout CRLF is not a build byte contract.
    expected_proposal = (EXAMPLE / "reference.py").read_text(encoding="utf-8").encode("utf-8")
    assert (root / "app" / "exporter.py").read_bytes() == expected_proposal


def test_failed_proposal_stays_failed_in_owner_and_receipt(tmp_path, monkeypatch):
    class WrongScope(fixture.ScriptedProposal):
        def __call__(self, raw):
            response = json.loads(super().__call__(raw))
            payload = json.loads(response["action"]["text"])
            if "files" in payload:
                payload["files"][0]["text"] = payload["files"][0]["text"].replace(
                    'if scope == "current_page":', 'if False:')
                response["action"]["text"] = json.dumps(payload)
            return json.dumps(response)
    monkeypatch.setattr(fixture, "ScriptedProposal", WrongScope)
    root = tmp_path.resolve() / "trial"
    receipt = fixture.smoke(root)
    assert not receipt["passed"]
    assert read_task(root / "task")["build"]["status"] != "completed"
    assert (root / "receipt.json").is_file()


@pytest.mark.parametrize("phase", ["import", "call"])
@pytest.mark.parametrize("exit_code", [0, None, 7])
def test_candidate_exit_stays_failed_in_owner_and_receipt(tmp_path, monkeypatch, phase, exit_code):
    source = f"raise SystemExit({exit_code!r})\n"
    if phase == "call":
        source = "def export_csv(rows, **kwargs):\n    " + source

    class ExitingProposal(fixture.ScriptedProposal):
        def __call__(self, raw):
            response = json.loads(super().__call__(raw))
            payload = json.loads(response["action"]["text"])
            if "files" in payload:
                payload["files"][0]["text"] = source
                response["action"]["text"] = json.dumps(payload)
            return json.dumps(response)

    monkeypatch.setattr(fixture, "ScriptedProposal", ExitingProposal)
    root = tmp_path.resolve() / "trial"
    receipt = fixture.smoke(root)
    assert receipt["passed"] is False
    assert json.loads((root / "receipt.json").read_text(encoding="utf-8")) == receipt
    record = read_task(root / "task")
    assert record["build"]["status"] != "completed"
    probes = [e["result"] for e in record["build"]["events"] if e["kind"] == "acceptance_probe"]
    assert len(probes) == 1  # A failed task check must not reach final verification.
    probe = probes[0]
    assert probe["passed"] is False and probe["returncode"] == 1
    assert probe["failure"] == "nonzero_exit"  # Not a timeout or dispatch error.
    verdict = json.loads(probe["stdout"])
    assert verdict["passed"] is False
    if phase == "import":
        assert verdict["error"] == "SystemExit"
    else:
        assert len(verdict["cases"]) == 6
        assert all(not case["passed"] and case["error"] == "SystemExit"
                   for case in verdict["cases"])


def test_refuses_existing_relative_linked_or_unknown_destinations(tmp_path):
    existing = tmp_path.resolve() / "existing"
    existing.mkdir()
    (existing / "keep").write_text("preserve")
    with pytest.raises(FileExistsError):
        fixture.prepare(existing)
    assert (existing / "keep").read_text() == "preserve"
    with pytest.raises(ValueError, match="canonical"):
        fixture.prepare(Path("relative"))
    with pytest.raises(ValueError, match="Unknown"):
        fixture.prepare(tmp_path.resolve() / "unknown", "bogus")
    assert not (tmp_path / "unknown").exists()
    try:
        (tmp_path / "link").symlink_to(existing, target_is_directory=True)
    except OSError:
        pytest.skip("Creating directory symlinks is unavailable")
    with pytest.raises(ValueError, match="canonical"):
        fixture.prepare(tmp_path / "link" / "new")


def test_protected_oracle_process_reports_failure_without_implementation(tmp_path):
    root = tmp_path.resolve() / "trial"
    fixture.prepare(root)
    result = subprocess.run([sys.executable, "-B", "oracle.py", "current_page"],
                            cwd=root / "app", capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert not json.loads(result.stdout)["passed"]


def test_cli_smoke_has_no_provider_options(tmp_path):
    import os
    import attune_harness
    env = {**os.environ, "PYTHONPATH": str(Path(attune_harness.__file__).parent.parent)}
    output = tmp_path.resolve() / "cli"
    result = subprocess.run([sys.executable, "-B", str(EXAMPLE / "fixture.py"), "smoke", str(output)],
                            env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["kind"] == "offline-csv-software-check"
