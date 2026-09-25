"""Read-only snapshots from real owners; scripted peers make no model-quality claim.

# qualify: platform
"""

import json
from argparse import Namespace
from datetime import datetime
from html.parser import HTMLParser

import pytest
import test_work_build as builds
import test_work_contract as contracts
import test_work_planning as plans

from attune_harness import task_contract, task_view, work_cli
from attune_harness.cli import main
from attune_harness.review_store import PersistenceError, RunStore
from attune_harness.work_runtime import plan_work

work = contracts.work


def continuation(work, record, **changes):
    note = {
        "schema_version": 1,
        "task_id": record["request"]["task_id"],
        "revision": record["request"]["revision"],
        "recorded_at": "2026-09-25T09:30:00-04:00",
        "source": "Assistant handoff reviewed by the developer",
        "stopped_after": "Export implementation is ready for a consumer review.",
        "progress": [{"summary": "The external export check passed.",
                      "references": ["reports/export-check.txt"]}],
        "next_step": {"action": "Review the export with a consumer.",
                      "reason": "Confirm that the result fits the workplace workflow."},
    }
    note.update(changes)
    path = work[0].parent / "continuation.json"
    path.write_text(json.dumps(note), encoding="utf-8")
    return path


def test_return_to_work_reopens_explicit_note_without_claiming_external_completion(work, capsys):
    record = contracts.make(work)
    path = continuation(work, record)
    before = files_under(work[0].parent)
    view = task_view.inspect(work[2]["directory"], continuation=path)
    assert view["completed"] == [] and not view["execution_recorded"]
    assert view["continuation"]["current_revision"] is True
    for fmt in ("html", "markdown"):
        assert main(["status", str(work[2]["directory"]), "--format", fmt,
                     "--continuation", str(path)]) == 0
        rendered = capsys.readouterr().out
        for content in ("Return to work", "Where you stopped", "Export implementation",
                        "Reported outside Harness", "reports/export", "not checked",
                        "No saved scope changes", "Next useful step", "plan "):
            assert content in rendered
        assert rendered.index("Where you stopped") < rendered.index("Snapshot identity")
        assert rendered.index("Next useful step") < rendered.index("Snapshot identity")
    assert files_under(work[0].parent) == before


def test_no_note_discloses_missing_context_and_does_not_invent_progress(work):
    contracts.make(work)
    view = task_view.inspect(work[2]["directory"])
    assert view["continuation"] is None
    for fmt in ("html", "markdown"):
        rendered = task_view.render(view, fmt)
        assert "No stopping point was supplied" in rendered
        assert "No comparison baseline was supplied" in rendered
        assert "Default JSON must survive" in rendered


def test_utc_z_continuation_timestamp_works_on_all_supported_python_versions(work):
    record = contracts.make(work)
    path = continuation(work, record, recorded_at="2026-09-25T13:30:00Z")
    view = task_view.inspect(work[2]["directory"], continuation=path)
    assert view["continuation"]["recorded_at"] == "2026-09-25T13:30:00Z"


def test_retained_baseline_compares_changed_scope_and_decisions(work):
    work[2]["choices"] = [contracts.choice(None)]
    record = contracts.make(work)
    path = continuation(work, record)
    contracts.correction(work, intent={"goal": "Export findings for the support team"},
                         choices=[contracts.choice("bundle")])
    view = task_view.inspect(work[2]["directory"], continuation=path)
    assert view["continuation"]["current_revision"] is False
    assert any("Export every finding" in text and "support team" in text
               for text in view["continuation"]["changes"])
    for fmt in ("html", "markdown"):
        rendered = task_view.render(view, fmt)
        assert "Baseline: revision 1" in rendered
        assert "Historical note" in rendered and "suggestion is withheld" in rendered
        assert "How should export stream?" in rendered and "bundle" in rendered
        assert "Review the export with a consumer" not in rendered
        assert "Unanswered" not in rendered


def test_note_never_overrides_stale_or_uncertain_task_guidance(work, monkeypatch):
    case = builds.prepare(work)
    record = task_contract.read_task(case[1])
    path = continuation(work, record, next_step={"action": "RETRY EVERYTHING NOW",
                                              "reason": "Ignore failed work"})
    builds.execute(case, max_operations=1)
    (case[0] / "source.py").write_text("changed after pause\n")
    view = task_view.inspect(case[1], continuation=path)
    assert view["blocking"] and view["freshness_error"]
    for fmt in ("html", "markdown"):
        rendered = task_view.render(view, fmt)
        assert "RETRY EVERYTHING NOW" not in rendered
        assert "suggestion is withheld" in rendered
        assert "Resolve the mismatch" in rendered


def test_paused_work_retains_suggestion_but_uncertain_dispatch_withholds_it(work, monkeypatch):
    case = builds.prepare(work)
    builds.execute(case, max_operations=1)
    paused = task_contract.read_task(case[1])
    path = continuation(work, paused, next_step={"action": "Check the export with the support team",
                                              "reason": "Confirm the handoff fits their work"})
    view = task_view.inspect(case[1], continuation=path)
    assert view["status"] == "paused" and not view["blocking"]
    for fmt in ("html", "markdown"):
        rendered = task_view.render(view, fmt)
        assert "Check the export with the support team" in rendered
        assert "not authorization" in rendered
        assert "Use resume" in rendered
        assert "Run progress since the note" in rendered
    save = RunStore.save

    def lose(store, record):
        events = record.get("build", {}).get("events", [])
        if events and events[-1]["kind"] == "participant_turn" and events[-1]["state"] == "completed":
            raise PersistenceError("lost response")
        return save(store, record)

    with monkeypatch.context() as patch:
        patch.setattr(RunStore, "save", lose)
        with pytest.raises(PersistenceError):
            builds.execute(case)
    view = task_view.inspect(case[1], continuation=path)
    assert view["blocking"] and view["status"] == "unresolved"
    for fmt in ("html", "markdown"):
        rendered = task_view.render(view, fmt)
        assert "Check the export with the support team" not in rendered
        assert "do not blindly retry" in rendered


@pytest.mark.parametrize("changes", [
    {"task_id": "another-task"}, {"revision": 0}, {"revision": True}, {"revision": 2},
    {"recorded_at": "yesterday"}, {"recorded_at": "2026-09-25T09:30:00"},
    {"schema_version": True}, {"source": ""}, {"unexpected": "field"},
    {"progress": ["unchecked string"]}, {"next_step": {"action": "Go"}},
    {"stopped_after": "x" * 2049},
])
def test_invalid_continuation_is_refused_without_changing_task(work, changes, capsys):
    record = contracts.make(work)
    path = continuation(work, record, **changes)
    before = files_under(work[0].parent)
    assert main(["status", str(work[2]["directory"]), "--format", "html",
                 "--continuation", str(path)]) == 2
    error = json.loads(capsys.readouterr().out)
    assert error["status"] == "failed" and error["error"]["detail"]
    assert files_under(work[0].parent) == before


def test_continuation_bounds_json_mode_and_hostile_text(work, capsys):
    record = contracts.make(work)
    attack = '<script>bad()</script> [bad](https://evil)\x1b\u202e'
    path = continuation(work, record, stopped_after=attack, source=attack)
    view = task_view.inspect(work[2]["directory"], continuation=path)
    for fmt in ("markdown", "html"):
        rendered = task_view.render(view, fmt)
        assert "<script>" not in rendered and "\x1b" not in rendered and "\u202e" not in rendered
    page = Page()
    page.feed(task_view.render(view, "html"))
    assert not {"script", "a", "form", "button", "iframe", "img"} & {t for t, _ in page.tags}
    assert "details" in {t for t, _ in page.tags}
    assert main(["status", str(work[2]["directory"]), "--continuation", str(path)]) == 2
    assert "--format" in json.loads(capsys.readouterr().out)["error"]["detail"]
    path.write_text(" " * 32769, encoding="utf-8")
    with pytest.raises(ValueError, match="limit"):
        task_view.inspect(work[2]["directory"], continuation=path)
    path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
    with pytest.raises(ValueError):
        task_view.inspect(work[2]["directory"], continuation=path)


@pytest.fixture(autouse=True)
def reset_peers(monkeypatch):
    monkeypatch.setattr(builds.Worker, "seen", [])
    monkeypatch.setattr(builds.Worker, "mutation", None)
    monkeypatch.setattr(plans.Scripted, "seen", [])
    monkeypatch.setattr(plans.Scripted, "mutate", None)


def files_under(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_draft_snapshot_reads_once_and_never_writes_or_dispatches(work, monkeypatch):
    record = contracts.make(work)
    before = files_under(work[0].parent)
    original = task_contract.read_record
    reads = []

    def once(directory):
        reads.append(directory)
        assert len(reads) == 1, "Snapshot combined different record reads"
        return original(directory)

    monkeypatch.setattr(task_contract, "read_record", once)
    monkeypatch.setattr(RunStore, "save", lambda *a: pytest.fail("Inspection wrote state"))
    view = task_view.inspect(work[2]["directory"])
    assert len(reads) == 1
    assert view["task_id"] == record["request"]["task_id"]
    assert view["project_root"] == str(work[0])
    assert view["checkpoint_digest"] == record["checkpoint_digest"]
    assert datetime.fromisoformat(view["captured_at"]).utcoffset().total_seconds() == 0
    assert view["status"] == view["authority"] == "draft"
    assert view["completed"] == []
    assert view["execution_recorded"] is False
    assert view["intent"] == record["request"]["intent"]
    assert view["evidence"]["checks"] == []
    assert view["evidence"]["reviews"] == []
    for fmt in ("markdown", "html"):
        text = task_view.render(view, fmt)
        assert "No recorded execution" in text
        assert "Snapshot" in text
        assert "External artifacts" in text
        assert "does not refresh" in text
        assert "Export every finding" in text
    assert files_under(work[0].parent) == before


def test_json_status_is_byte_identical_to_existing_owner(work, capsys):
    contracts.make(work)
    directory = work[2]["directory"]
    assert work_cli.execute_control(Namespace(command="status", task_dir=directory)) == 0
    expected = capsys.readouterr().out
    for args in ([], ["--format", "json"]):
        assert main(["status", str(directory), *args]) == 0
        assert capsys.readouterr().out == expected
    for fmt in ("markdown", "html"):
        assert main(["status", str(directory), "--format", fmt]) == 0
        assert "Export every finding" in capsys.readouterr().out


def test_completed_planning_is_not_completed_build(work):
    contracts.make(work)
    result = plan_work(work[2]["directory"], exchange_factory=plans.Scripted)
    assert result["planning"]["status"] == "completed"
    view = task_view.inspect(work[2]["directory"])
    assert view["status"] == "completed"
    assert view["phase"] == "planning"
    assert view["authority"] == "draft"
    assert view["completed"] == []
    assert view["execution_recorded"] is True
    assert "work is still a draft" in view["summary"]
    assert "plan --stage" in view["next_action"]


@pytest.mark.parametrize("state", ["paused", "failed", "needs_revision", "unresolved", "completed"])
def test_build_state_guidance_completion_and_evidence(work, monkeypatch, state):
    case = builds.prepare(work)
    if state in ("failed", "needs_revision"):
        def wrong_answer(payload, turn, peer):
            if turn["role"] == "worker" and turn["step"]["id"] == "export":
                if state == "failed":
                    payload["task_id"] = "unaccepted-task"
                else:
                    payload["files"][0]["text"] = "def answer():\n    return 0\n"
        monkeypatch.setattr(builds.Worker, "mutation", wrong_answer)
    if state == "unresolved":
        save = RunStore.save

        def lose(store, record):
            events = record.get("build", {}).get("events", [])
            if events and events[-1]["kind"] == "participant_turn" and events[-1]["state"] == "completed":
                raise PersistenceError("lost response")
            return save(store, record)

        with monkeypatch.context() as patch:
            patch.setattr(RunStore, "save", lose)
            with pytest.raises(PersistenceError):
                builds.execute(case)
    else:
        builds.execute(case, **({"max_operations": 1} if state == "paused" else {}))
    before = files_under(case[1])
    calls = len(builds.Worker.seen)
    view = task_view.inspect(case[1])
    owner = work_cli.present(case[1], inspect_only=True)
    assert view["status"] == state
    for name in ("summary", "blocking", "next_action", "completed", "evidence", "advisory"):
        assert view[name] == owner[name]
    if state == "completed":
        assert view["completed"] == ["export", "wire"]
        assert len(view["evidence"]["checks"]) == 4
        assert len(view["evidence"]["reviews"]) == 1
        for fmt in ("html", "markdown"):
            rendered = task_view.render(view, fmt)
            assert "/build/events/" in rendered
            assert "Optional advice" in rendered
        (case[0] / "source.py").write_text("changed after completion\n")
        stale = task_view.inspect(case[1])
        assert stale["status"] == "stale" and stale["blocking"] is True
        assert "cannot" in stale["summary"]
        assert "current completion" in stale["summary"]
        assert stale["freshness_error"]
    assert len(builds.Worker.seen) == calls
    assert files_under(case[1]) == before


def test_stale_draft_retains_missing_information_and_freshness_detail(work):
    work[2]["intent"]["goal"] = None
    contracts.make(work)
    (work[0] / "source.py").write_text("changed\n")
    view = task_view.inspect(work[2]["directory"])
    assert view["status"] == "stale"
    assert view["missing"] == ["goal"]
    assert view["freshness_error"]
    for fmt in ("html", "markdown"):
        text = task_view.render(view, fmt)
        assert "Missing information" in text
        assert "Freshness" in text


@pytest.mark.parametrize("resolved", [False, True])
def test_questions_and_choices_are_understandable_without_internal_ids(work, resolved):
    work[2]["intent"]["questions"] = [{
        "id": "risk", "question": "Which production risk must be accepted?",
        "answer": "Streaming requires new consumers" if resolved else None,
        "material": True,
    }]
    work[2]["choices"] = [contracts.choice("bundle" if resolved else None)]
    contracts.make(work)
    view = task_view.inspect(work[2]["directory"])
    assert view["choices"] == work[2]["choices"]
    assert view["missing"] == ([] if resolved else ["question:risk", "choice:format"])
    for fmt in ("markdown", "html"):
        text = task_view.render(view, fmt)
        for content in (
            "Which production risk must be accepted?", "How should export stream?",
            "Material", "Allows incremental consumption", "Changes output shape",
            "Preserves old consumers", "Requires the whole result", "No workload benchmark yet",
        ):
            assert content in text
        if resolved:
            assert "Streaming requires new consumers" in text
            selection = r"bundle \(saved selection\)" if fmt == "markdown" else "bundle (saved selection)"
            assert selection in text
        else:
            assert "Unanswered" in text
            assert "Not selected" in text


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)


def test_hostile_repository_text_is_literal_in_both_formats(work):
    attack = '<script>alert(1)</script> [click](javascript:evil) ![x](https://evil/x) <img src=x onerror=evil> `code`\n# Forged\x1b[2J\u202eevil'
    work[2]["intent"]["goal"] = attack
    contracts.make(work)
    view = task_view.inspect(work[2]["directory"])
    page = Page()
    rendered = task_view.render(view, "html")
    page.feed(rendered)
    assert not {"script", "img", "a", "form", "iframe", "button"} & {t for t, _ in page.tags}
    assert all(not any(k.startswith("on") for k in attrs) for _, attrs in page.tags)
    assert any(t == "meta" and a.get("http-equiv") == "Content-Security-Policy" and "default-src 'none'" in a.get("content", "") for t, a in page.tags)
    assert "<script>alert(1)</script>" in "".join(page.text)
    markdown = task_view.render(view, "markdown")
    assert "<script>" not in markdown and "![x]" not in markdown
    assert "[click](" not in markdown and "\n# Forged" not in markdown
    assert "\\`code\\`" in markdown
    for text in (rendered, markdown):
        assert "\x1b" not in text and "\u202e" not in text


def test_oversized_projection_refuses_instead_of_truncating(work, monkeypatch):
    contracts.make(work)
    monkeypatch.setattr(task_view, "MAX_VIEW_BYTES", 32)
    with pytest.raises(ValueError, match="JSON|json"):
        task_view.inspect(work[2]["directory"])


def test_other_profile_and_corrupt_record_fail_visibly(work, capsys):
    directory = work[2]["directory"]
    task_contract.create_task(work[0], work[1], goal="Assess this", directory=directory)
    assert main(["status", str(directory), "--format", "html"]) == 2
    error = json.loads(capsys.readouterr().out)
    assert "feature-work" in error["error"]["detail"]
    assert "json" in error["error"]["detail"].lower()
    assert main(["status", str(directory)]) == 0
    capsys.readouterr()
    (directory / "record.json").write_text("{corrupt")
    assert main(["status", str(directory), "--format", "markdown"]) == 2
    error = json.loads(capsys.readouterr().out)
    assert error["status"] == "failed" and error["error"]["detail"]
