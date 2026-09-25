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


def test_partial_build_progress_is_visible_before_supporting_detail(work):
    case = builds.prepare(work)
    builds.execute(case, max_operations=8)
    view = task_view.inspect(case[1])
    assert view["status"] == "paused" and view["completed"] == ["export"]
    objectives = {task["id"]: task["objective"] for task in view["tasks"]}
    for fmt in ("html", "markdown"):
        overview = task_view.render(view, fmt).split("Supporting detail", 1)[0]
        assert objectives["export"] in overview and objectives["wire"] in overview
        assert "Recorded passing checks" in overview
    (case[0] / "source.py").write_text("changed after passing check\n")
    stale = task_view.inspect(case[1])
    assert stale["status"] == "stale"
    for fmt in ("html", "markdown"):
        overview = task_view.render(stale, fmt).split("Supporting detail", 1)[0]
        assert "Prior checks need revalidation" in overview
        assert "Recorded passing checks" not in overview


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
        assert "<script>bad()" not in rendered and "\x1b" not in rendered and "\u202e" not in rendered
    page = Page()
    page.feed(task_view.render(view, "html"))
    assert_fixed_reply_assets(page, task_view.render(view, "html"))
    assert not {"a", "form", "iframe", "img"} & {t for t, _ in page.tags}
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
    assert_fixed_reply_assets(page, rendered)
    assert not {"img", "a", "form", "iframe"} & {t for t, _ in page.tags}
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


def assert_fixed_reply_assets(page, rendered):
    """Only the exact bundled script is executable, never any task-supplied text."""
    import base64
    import hashlib
    import re
    assert re.findall(r"<script>(.*?)</script>", rendered, re.S | re.I) == [task_view._REPLY_SCRIPT]
    assert sum(tag == "script" for tag, _ in page.tags) == 1
    assert sum(tag == "button" for tag, _ in page.tags) == 10
    assert all(not any(k.startswith("on") or k in ("src", "formaction") for k in attrs)
               for _, attrs in page.tags)
    csp = next(a["content"] for t, a in page.tags if a.get("http-equiv") == "Content-Security-Policy")
    digest = base64.b64encode(hashlib.sha256(task_view._REPLY_SCRIPT.encode()).digest()).decode()
    assert "script-src 'sha256-" + digest + "'" in csp
    assert "connect-src 'none'" in csp and "form-action 'none'" in csp


def briefing():
    return dict(title="Support export", context="People need findings at handoff.",
                goal="Make review findings usable by support.",
                desired_end_state="Support can explain what remains unresolved.",
                current_focus="Check the export layout.", done_when="The consumer can find each finding.")


def test_authored_briefing_is_attributed_and_preserves_authoritative_guidance(work):
    record = contracts.make(work)
    note = continuation(work, record, briefing=briefing())
    before = files_under(work[0].parent)
    view = task_view.inspect(work[2]["directory"], continuation=note)
    for fmt in ("html", "markdown"):
        text = task_view.render(view, fmt)
        assert "Goal" in text and "Desired end state" in text
        assert "Make review findings usable by support" in text
        assert "attributed summary" in text
        expected = task_view._literal(view["next_action"]) if fmt == "markdown" else task_view._escape(view["next_action"])
        assert expected in text
        assert "Export every finding" in text  # canonical intent remains inspectable
        assert "Your reply to the assistant" in text
    assert files_under(work[0].parent) == before


def test_historical_briefing_is_withheld(work):
    record = contracts.make(work)
    note = continuation(work, record, briefing=briefing())
    contracts.correction(work, intent={"goal": "A different saved goal"})
    view = task_view.inspect(work[2]["directory"], continuation=note)
    for fmt in ("html", "markdown"):
        text = task_view.render(view, fmt)
        assert "Make review findings usable by support" not in text
        assert "A different saved goal" in text
        assert "Historical note" in text


@pytest.mark.parametrize("bad", [None, {}, {**briefing(), "extra": "no"},
                                {**briefing(), "goal": ""}, {**briefing(), "goal": "é" * 1025}])
def test_briefing_rejects_unbounded_or_unknown_shape(work, bad):
    record = contracts.make(work)
    note = continuation(work, record, briefing=bad)
    with pytest.raises(ValueError):
        task_view.inspect(work[2]["directory"], continuation=note)


def second_task(work):
    import copy
    root, config, data = work
    second = copy.deepcopy(data)
    second["directory"] = data["directory"].parent / "second"
    second["intent"]["goal"] = "Review another task"
    contracts.make((root, config, second))
    return second["directory"]


def test_saved_tasks_navigation_is_bound_to_explicit_identities_and_read_only(work, capsys):
    contracts.make(work)
    other = second_task(work)
    before = files_under(work[0].parent)
    entries = task_view.inspect_saved_tasks(work[2]["directory"], [other])
    assert len(entries) == 2 and entries[0]["view"]["task_id"] != entries[1]["view"]["task_id"]
    for fmt in ("html", "markdown"):
        assert main(["status", str(work[2]["directory"]), "--include-task", str(other),
                     "--format", fmt]) == 0
        text = capsys.readouterr().out
        assert "Saved Tasks" in text and "Review another task" in text
        if fmt == "html":
            page = Page(); page.feed(text)
            ids = [a["id"] for _, a in page.tags if "id" in a]
            assert len(ids) == len(set(ids))
            links = [a["href"] for t, a in page.tags if t == "a"]
            assert len(links) == 4 and all(link[1:] in ids for link in links)
            assert all(link.startswith("#") for link in links)
        else:
            import re
            anchors = re.findall(r'<a id="([^"]+)"></a>', text)
            targets = re.findall(r'\]\(#([^)]+)\)', text)
            assert len(anchors) == 3 and len(anchors) == len(set(anchors))
            assert len(targets) == 6 and all(target in anchors for target in targets)
            assert targets[:2] == anchors[1:]
            assert text.index("# Saved Tasks") < text.index("# Return to work")
    assert files_under(work[0].parent) == before


def test_saved_tasks_refuses_duplicate_paths_and_marks_copied_owner_unavailable(work):
    import shutil
    contracts.make(work)
    directory = work[2]["directory"]
    with pytest.raises(ValueError, match="distinct"):
        task_view.inspect_saved_tasks(directory, [directory / "."])
    clone = directory.parent / "duplicate"
    shutil.copytree(directory, clone)
    entries = task_view.inspect_saved_tasks(directory, [clone])
    assert "Copied work cannot become another owner" in entries[1]["error"]
    html = task_view.render_saved_tasks(entries, "html")
    assert html.count('class="saved-task"') == 1 and "Unavailable task" in html


def test_saved_tasks_additional_failure_is_visible_and_does_not_hide_valid_work(work):
    contracts.make(work)
    missing = work[2]["directory"].parent / "absent<script>"
    entries = task_view.inspect_saved_tasks(work[2]["directory"], [missing])
    assert "error" in entries[1]
    for fmt in ("html", "markdown"):
        text = task_view.render_saved_tasks(entries, fmt)
        assert "Unavailable task" in text and "Export every finding" in text
        assert "absent<script>" not in text
    with pytest.raises(Exception):
        task_view.inspect_saved_tasks(missing, [work[2]["directory"]])


def test_saved_tasks_enforces_collection_bounds_and_json_compatibility(work, capsys, monkeypatch):
    contracts.make(work)
    directory = work[2]["directory"]
    with pytest.raises(ValueError, match="20"):
        task_view.inspect_saved_tasks(directory, [directory.parent / str(i) for i in range(20)])
    entries = task_view.inspect_saved_tasks(directory, [directory.parent / str(i) for i in range(19)])
    assert len(entries) == 20
    monkeypatch.setattr(task_view, "MAX_SAVED_TASK_BYTES", 10)
    with pytest.raises(ValueError, match="2 MiB"):
        task_view.inspect_saved_tasks(directory, [])
    assert main(["status", str(directory), "--include-task", str(directory.parent / "second")]) == 2
    assert "--include-task requires" in json.loads(capsys.readouterr().out)["error"]["detail"]


def test_hostile_briefing_and_handoff_stay_literal(work):
    record = contracts.make(work)
    attack = '</textarea><script>alert(2)</script><img src=x onerror=alert(3)>\u202e'
    note = continuation(work, record, briefing={k: attack for k in briefing()})
    view = task_view.inspect(work[2]["directory"], continuation=note)
    rendered = task_view.render(view, "html")
    page = Page(); page.feed(rendered)
    assert_fixed_reply_assets(page, rendered)
    assert not {"img", "iframe", "form", "a"} & {tag for tag, _ in page.tags}
    assert "\u202e" not in rendered
    assert view["task_id"] in rendered and "not a checkpoint acceptance" in rendered


def test_markdown_collection_escapes_hostile_index_titles(work):
    attack = '[outside](https://invalid.example) <a id="saved-tasks">bad</a>'
    work[2]["intent"]["goal"] = attack
    contracts.make(work)
    other = second_task(work)
    text = task_view.render_saved_tasks(task_view.inspect_saved_tasks(work[2]["directory"], [other]), "markdown")
    assert text.count('<a id="saved-tasks"></a>') == 1
    assert '[outside](' not in text
    assert '<a id="saved-tasks">bad' not in text
    assert '[← Saved tasks](#saved-tasks)' in text


def design_review(**changes):
    value = dict(presentation_revision="5", next_question="Which entrance should we try next?",
                 feedback=[dict(criterion="Briefing comprehension", status="observed",
                                observation="The reader understood the goal.", references=["review-notes.md"]),
                           dict(criterion="Independent discovery", status="unverified",
                                observation="No independent test yet.", references=[])])
    value.update(changes)
    return value


def test_design_feedback_and_next_question_are_attributed_read_only_and_discussion_only(work):
    record = contracts.make(work)
    note = continuation(work, record, briefing=briefing(), design_review=design_review())
    before = files_under(work[0].parent)
    view = task_view.inspect(work[2]["directory"], continuation=note)
    assert view["blocking"]  # design discussion must not make the build ready
    for fmt in ("html", "markdown"):
        text = task_view.render(view, fmt)
        for content in ("Feedback already recorded", "observed", "unverified",
                        "The reader understood the goal", "Which entrance should we try next?",
                        "discussion only", "not authenticated acceptance", "Presentation revision"):
            assert content in text
        escape = task_view._literal if fmt == "markdown" else task_view._escape
        assert escape(view["captured_at"]) in text and escape(view["continuation"]["recorded_at"]) in text
        assert view["continuation"]["sha256"] in text
        assert view["completed"] == []
    handoff = task_view._handoff(view)
    assert "does not authorize implementation" in handoff
    assert str(work[2]["directory"]) in handoff
    assert view["task_id"] in handoff
    assert files_under(work[0].parent) == before


@pytest.mark.parametrize("state", ["historical", "stale", "completed"])
def test_design_question_never_survives_a_stale_or_completed_owner(work, state):
    record = contracts.make(work)
    note = continuation(work, record, design_review=design_review())
    if state == "historical":
        contracts.correction(work, intent={"goal": "Changed scope"})
    view = task_view.inspect(work[2]["directory"], continuation=note)
    if state == "stale":
        view["freshness_error"] = "Evidence changed"
    if state == "completed":
        view["status"] = "completed"
    for fmt in ("html", "markdown"):
        text = task_view.render(view, fmt)
        assert "Which entrance should we try next?" not in text
        assert "question is withheld" in text
        assert "The reader understood the goal" in text  # retained, not erased
    assert "Discussion" not in task_view._handoff(view)


def test_feedback_without_a_new_question_does_not_invent_a_decision(work):
    record = contracts.make(work)
    note = continuation(work, record, design_review=design_review(next_question=None))
    view = task_view.inspect(work[2]["directory"], continuation=note)
    text = task_view.render(view, "html")
    assert "Feedback already recorded" in text
    assert "Next design decision" not in text and "Discuss next decision" not in text


@pytest.mark.parametrize("bad", [None, {}, design_review(extra="no"),
    design_review(presentation_revision=""), design_review(presentation_revision="é" * 33),
    design_review(next_question=""), design_review(next_question="é" * 1025),
    design_review(feedback=[design_review()["feedback"][0]] * 7),
    design_review(feedback=[dict(criterion="x", status="passed", observation="x", references=[])]),
    design_review(feedback=[dict(criterion="x", status="observed", observation="x", references=["x"] * 7)]),
    design_review(feedback=[dict(criterion="x", status="observed", observation="x", references=[], extra=True)])])
def test_design_review_refuses_unknown_unbounded_or_misleading_shape(work, bad):
    record = contracts.make(work)
    note = continuation(work, record, design_review=bad)
    with pytest.raises(ValueError):
        task_view.inspect(work[2]["directory"], continuation=note)


def test_role_headings_and_definitions_agree_across_formats_and_have_unique_help_targets(work):
    contracts.make(work)
    view = task_view.inspect(work[2]["directory"])
    text = task_view.render(view, "html")
    page = Page(); page.feed(text)
    assert sum(t == "h2" and a.get("class") == "role-label" for t, a in page.tags) == 6
    ids = [a["id"] for _, a in page.tags if "id" in a]
    assert len(ids) == len(set(ids))
    for _, attrs in page.tags:
        if attrs.get("class") == "role-help":
            assert attrs["aria-describedby"] in ids and attrs["aria-controls"] in ids
    markdown = task_view.render(view, "markdown")
    for label, definition in task_view._ROLES.values():
        assert "## " + label in markdown and definition in markdown
        assert definition in "".join(page.text)
    assert "<details><summary>Full saved goal" not in text
    assert "Full goal and briefing structure" in text


def test_hostile_feedback_and_question_cannot_inject_controls_or_script(work):
    record = contracts.make(work)
    attack = '</textarea><SCRIPT>evil()</SCRIPT><img src=x onerror=evil>'
    review = design_review(next_question=attack)
    review["feedback"][0]["observation"] = attack
    note = continuation(work, record, design_review=review)
    view = task_view.inspect(work[2]["directory"], continuation=note)
    text = task_view.render(view, "html")
    page = Page(); page.feed(text)
    assert_fixed_reply_assets(page, text)
    assert not any(t == "img" for t, _ in page.tags)
    assert attack in "".join(page.text)
    assert "<SCRIPT>" not in task_view.render(view, "markdown")


def test_partial_feedback_is_supported_without_becoming_observed_or_complete(work):
    record = contracts.make(work)
    review = design_review()
    review['feedback'][0]['status'] = 'partial'
    note = continuation(work, record, design_review=review)
    view = task_view.inspect(work[2]['directory'], continuation=note)
    for fmt in ('html', 'markdown'):
        assert 'partial: The reader understood the goal' in task_view.render(view, fmt)
    assert view['completed'] == []


@pytest.mark.parametrize('field', ['criterion', 'observation', 'reference'])
def test_feedback_text_accepts_exact_byte_limit_and_refuses_one_byte_over(work, field):
    record = contracts.make(work)
    review = design_review()
    exact = 'é' * 1024
    def set_value(value):
        if field == 'reference':
            review['feedback'][0]['references'] = [value]
        else:
            review['feedback'][0][field] = value
    set_value(exact)
    note = continuation(work, record, design_review=review)
    task_view.inspect(work[2]['directory'], continuation=note)
    set_value(exact + 'x')
    note = continuation(work, record, design_review=review)
    with pytest.raises(ValueError):
        task_view.inspect(work[2]['directory'], continuation=note)


def test_glossary_definitions_remain_visible_without_disclosures_or_javascript(work):
    class VisibleText(HTMLParser):
        def __init__(self):
            super().__init__()
            self.hidden = []
            self.text = []
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag not in ('meta', 'input', 'br', 'hr', 'img', 'link'):
                self.hidden.append('hidden' in attrs or tag in ('script', 'style')
                                   or (tag == 'details' and 'open' not in attrs))
        def handle_endtag(self, tag):
            self.hidden.pop()
        def handle_data(self, data):
            if not any(self.hidden):
                self.text.append(data)
    record = contracts.make(work)
    note = continuation(work, record, briefing=briefing())
    page = VisibleText()
    page.feed(task_view.render(task_view.inspect(work[2]['directory'], continuation=note), 'html'))
    visible = ''.join(page.text)
    assert 'Export every finding' in visible  # full canonical goal, not the authored summary
    for _, definition in task_view._ROLES.values():
        assert definition in visible
