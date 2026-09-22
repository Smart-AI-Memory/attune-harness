"""Execution state in plan files.

Carried from Attune AI's tests/unit/spec/test_state.py at b89f7953f: 30 tests.
Changed on porting: every fixture comment carries a schema_version, because
Harness refuses one without it; the loosened-regex test loosens the trailing
pattern; monkeypatch targets name this module. One test is replaced:
`test_defaults_schema_version_when_missing` (a missing version loaded as 0)
is now a refusal case. The rest are new: the three seams, and the agreement
with spec_bridge.plan_content on the same inputs.
"""

from __future__ import annotations

import json
import logging
import os
import re
import stat
import sys
import time

import pytest

from attune_harness import spec_state
from attune_harness.spec_bridge import plan_content
from attune_harness.spec_state import (
    CURRENT_SCHEMA_VERSION,
    SpecState,
    clear_state,
    find_resumable_plans,
    load_state,
    save_state,
)
from attune_harness.spec_tasks import PLAN_LIMIT, read_spec

LOGGER = "attune_harness.spec_state"

TASKS = """\
<task id="1" name="first"><objective>Do first</objective></task>
<task id="2" name="second"><objective>Do second</objective></task>
"""

PLAN_WITH_STATE = (
    "# Test Plan\n\n" + TASKS + "\n"
    '<!-- spec-state: {"schema_version":1,"completed":["1"],"current":"2",'
    '"auto_run":false,"last_updated":"2026-03-24T00:00:00+00:00"} -->\n'
)

PLAN_WITHOUT_STATE = "# Test Plan\n\n" + TASKS


def comment(**fields) -> str:
    return f"<!-- spec-state: {json.dumps(fields)} -->"


def plan(tmp_path, text, name="plan.md"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


# --- load_state: carried ----------------------------------------------------


class TestLoadState:
    def test_parses_existing_state(self, tmp_path):
        p = plan(tmp_path, PLAN_WITH_STATE)
        state = load_state(str(p))
        assert state is not None
        assert state.completed == ["1"]
        assert state.current == "2"
        assert state.auto_run is False
        assert state.plan_path == str(p)
        assert state.schema_version == 1

    def test_returns_none_when_no_comment(self, tmp_path):
        assert load_state(str(plan(tmp_path, PLAN_WITHOUT_STATE))) is None

    def test_returns_none_for_missing_file(self, tmp_path):
        assert load_state(str(tmp_path / "missing.md")) is None

    def test_handles_malformed_json(self, tmp_path, caplog):
        p = plan(tmp_path, "# Plan\n\n<!-- spec-state: {broken json here} -->")
        with caplog.at_level(logging.WARNING, logger=LOGGER):
            assert load_state(str(p)) is None
        assert any("Malformed spec-state" in r.message for r in caplog.records)

    def test_rejects_non_object_payload(self, tmp_path, monkeypatch, caplog):
        # A defensive branch production cannot reach: the pattern requires
        # {...}, so the parser yields a dict or raises. Loosen the pattern,
        # keeping the trailing anchor, so an array reaches the guard.
        p = plan(tmp_path, "# Plan\n\n<!-- spec-state: [1, 2, 3] -->")
        loosened = re.compile(r"\n?<!-- spec-state:\s*(\S.*?)\s*-->\s*\Z", re.S)
        monkeypatch.setattr(spec_state, "STATE_PATTERN", loosened)
        with caplog.at_level(logging.WARNING, logger=LOGGER):
            assert load_state(str(p)) is None
        assert any("is not a JSON object" in r.message for r in caplog.records)

    def test_rejects_non_list_completed(self, tmp_path, caplog):
        p = plan(tmp_path, "# Plan\n\n" + comment(schema_version=2, completed="1,2"))
        with caplog.at_level(logging.WARNING, logger=LOGGER):
            assert load_state(str(p)) is None
        assert any("completed" in r.message for r in caplog.records)

    def test_rejects_completed_with_non_string_items(self, tmp_path):
        p = plan(tmp_path, "# Plan\n\n" + comment(schema_version=2, completed=[1, 2]))
        assert load_state(str(p)) is None

    def test_rejects_non_string_current(self, tmp_path):
        p = plan(tmp_path, "# Plan\n\n" + comment(schema_version=2, completed=[], current=42))
        assert load_state(str(p)) is None

    def test_reads_schema_version(self, tmp_path):
        p = plan(tmp_path, "# Plan\n\n" + comment(schema_version=1, completed=["1"]))
        state = load_state(str(p))
        assert state is not None
        assert state.schema_version == 1

    def test_reads_current_schema_version(self, tmp_path):
        p = plan(tmp_path, "# Plan\n\n" + comment(schema_version=2, completed=["1"]))
        state = load_state(str(p))
        assert state is not None
        assert state.schema_version == 2

    def test_rejects_invalid_receipts(self, tmp_path):
        p = plan(tmp_path, "# Plan\n\n" + comment(schema_version=2, completed=["1"], task_receipts=False))
        with pytest.raises(ValueError, match="task_receipts"):
            load_state(str(p))


# --- seam 1: unknown schema versions are refused -----------------------------


class TestSchemaVersion:
    @pytest.mark.parametrize("version", [0, 3, -1, True, "2", None, 2.0])
    def test_unsupported_version_is_refused_with_next_action(self, tmp_path, version):
        p = plan(tmp_path, "# Plan\n\n" + comment(schema_version=version, completed=["1"]))
        with pytest.raises(ValueError, match="Unsupported Spec state comment") as info:
            load_state(str(p))
        message = str(info.value)
        assert "1 and 2" in message
        assert "Remove the spec-state comment" in message or "Update Harness" in message

    def test_missing_version_is_refused_not_loaded_as_zero(self, tmp_path):
        p = plan(tmp_path, "# Plan\n\n" + comment(completed=["1"]))
        with pytest.raises(ValueError, match="schema_version none"):
            load_state(str(p))

    def test_newer_version_names_the_update(self, tmp_path):
        p = plan(tmp_path, "# Plan\n\n" + comment(schema_version=3, completed=["1"]))
        with pytest.raises(ValueError, match="newer than this Harness reads"):
            load_state(str(p))

    def test_refusal_does_not_reset_progress(self, tmp_path):
        """A refused plan is left exactly as it was; save cannot follow load."""
        text = "# Plan\n\n" + TASKS + "\n" + comment(schema_version=3, completed=["1", "2"]) + "\n"
        p = plan(tmp_path, text)
        with pytest.raises(ValueError):
            load_state(str(p))
        assert p.read_text(encoding="utf-8") == text


# --- save_state: carried -----------------------------------------------------


class TestSaveState:
    def test_appends_state_to_plan(self, tmp_path):
        p = plan(tmp_path, PLAN_WITHOUT_STATE)
        save_state(SpecState(plan_path=str(p), completed=["1"], current="2"))
        content = p.read_text(encoding="utf-8")
        assert "<!-- spec-state:" in content
        assert '"completed": ["1"]' in content

    def test_replaces_existing_state(self, tmp_path):
        p = plan(tmp_path, PLAN_WITH_STATE)
        save_state(SpecState(plan_path=str(p), completed=["1", "2"], current=None, auto_run=True))
        content = p.read_text(encoding="utf-8")
        assert content.count("<!-- spec-state:") == 1
        loaded = load_state(str(p))
        assert loaded is not None
        assert loaded.completed == ["1", "2"]
        assert loaded.auto_run is True

    def test_updates_last_updated(self, tmp_path):
        p = plan(tmp_path, PLAN_WITHOUT_STATE)
        save_state(SpecState(plan_path=str(p)))
        loaded = load_state(str(p))
        assert loaded is not None
        assert "+" in loaded.last_updated or "Z" in loaded.last_updated

    def test_writes_schema_version(self, tmp_path):
        p = plan(tmp_path, PLAN_WITHOUT_STATE)
        save_state(SpecState(plan_path=str(p), schema_version=0))
        loaded = load_state(str(p))
        assert loaded is not None
        assert loaded.schema_version == CURRENT_SCHEMA_VERSION

    def test_leaves_no_temp_files_behind(self, tmp_path):
        p = plan(tmp_path, PLAN_WITHOUT_STATE)
        save_state(SpecState(plan_path=str(p), completed=["1"]))
        leftovers = [q for q in tmp_path.iterdir() if q.name != p.name and ".tmp" in q.name]
        assert leftovers == [], f"temp files leaked: {leftovers}"

    def test_atomic_write_cleanup_on_replace_failure(self, tmp_path, monkeypatch):
        p = plan(tmp_path, PLAN_WITHOUT_STATE)

        def _failing_replace(src, dst):
            raise OSError("simulated replace failure")

        monkeypatch.setattr(spec_state.os, "replace", _failing_replace)
        with pytest.raises(OSError, match="simulated replace failure"):
            save_state(SpecState(plan_path=str(p), completed=["1"]))
        leftovers = [q for q in tmp_path.iterdir() if q.name != p.name and ".tmp" in q.name]
        assert leftovers == [], f"temp files leaked after replace failure: {leftovers}"
        assert p.read_text(encoding="utf-8") == PLAN_WITHOUT_STATE

    def test_atomic_write_cleanup_failure_is_debug_logged(self, tmp_path, monkeypatch, caplog):
        p = plan(tmp_path, PLAN_WITHOUT_STATE)

        def _failing_replace(src, dst):
            raise OSError("simulated replace failure")

        def _failing_unlink(path):
            raise OSError("simulated unlink failure")

        monkeypatch.setattr(spec_state.os, "replace", _failing_replace)
        monkeypatch.setattr(spec_state.os, "unlink", _failing_unlink)
        with caplog.at_level(logging.DEBUG, logger=LOGGER):
            with pytest.raises(OSError, match="simulated replace failure"):
                save_state(SpecState(plan_path=str(p), completed=["1"]))
        cleanup_logs = [
            r for r in caplog.records
            if r.levelname == "DEBUG" and "Failed to unlink temp file" in r.message
        ]
        assert cleanup_logs, "expected a debug log for the cleanup failure"
        assert "simulated unlink failure" in cleanup_logs[0].message


# --- seam 3: the single trailing comment ------------------------------------

MISPLACED = "# Plan\n\n" + comment(schema_version=2, completed=["1"]) + "\n\n" + TASKS
DUPLICATED = (
    "# Plan\n\n" + TASKS + "\n" + comment(schema_version=2, completed=[]) + "\n\n"
    + comment(schema_version=2, completed=["1"]) + "\n"
)
MARKER_IN_PROSE = (
    "# Plan\n\nThe file ends with a `<!-- spec-state: ... -->` comment.\n\n" + TASKS + "\n"
    + comment(schema_version=2, completed=["1"]) + "\n"
)


class TestTrailingComment:
    @pytest.mark.parametrize("text", [MISPLACED, DUPLICATED, MARKER_IN_PROSE])
    def test_load_refuses_a_comment_that_is_not_the_single_trailing_one(self, tmp_path, text):
        p = plan(tmp_path, text)
        with pytest.raises(ValueError, match="Malformed or misplaced Spec state comment"):
            load_state(str(p))

    @pytest.mark.parametrize("text", [MISPLACED, DUPLICATED, MARKER_IN_PROSE])
    def test_save_never_writes_over_a_misplaced_comment(self, tmp_path, text):
        p = plan(tmp_path, text)
        with pytest.raises(ValueError, match="Malformed or misplaced Spec state comment"):
            save_state(SpecState(plan_path=str(p), completed=["1", "2"]))
        assert p.read_text(encoding="utf-8") == text

    def test_save_writes_the_comment_last(self, tmp_path):
        p = plan(tmp_path, "# Plan\n\n" + TASKS + "\n\n\n")
        save_state(SpecState(plan_path=str(p), completed=["1"]))
        content = p.read_text(encoding="utf-8")
        assert content.startswith("# Plan\n\n" + TASKS.rstrip() + "\n\n<!-- spec-state: ")
        assert content.endswith(" -->\n")
        assert plan_content(content) == "# Plan\n\n" + TASKS.rstrip() + "\n"

    def test_replacing_keeps_the_comment_last_and_single(self, tmp_path):
        p = plan(tmp_path, PLAN_WITH_STATE)
        for i in range(3):
            save_state(SpecState(plan_path=str(p), completed=["1"] * (i + 1)))
            content = p.read_text(encoding="utf-8")
            assert content.count("<!-- spec-state:") == 1
            assert content.rstrip().endswith("-->")
            assert content.index("<!-- spec-state:") > content.index("</task>")

    def test_save_refuses_a_result_over_the_plan_limit(self, tmp_path):
        p = plan(tmp_path, PLAN_WITHOUT_STATE)
        receipt = {"task_id": "1", "detail": "x" * (PLAN_LIMIT - 100)}
        with pytest.raises(ValueError, match="over the limit") as info:
            save_state(SpecState(plan_path=str(p), completed=["1"], task_receipts=[receipt]))
        assert "nothing was written" in str(info.value)
        assert p.read_text(encoding="utf-8") == PLAN_WITHOUT_STATE

    def test_load_refuses_a_plan_over_the_limit_whole(self, tmp_path):
        p = plan(tmp_path, "# Plan\n\n" + "x" * PLAN_LIMIT + "\n" + comment(schema_version=2))
        with pytest.raises(ValueError, match="refused whole"):
            load_state(str(p))

    @pytest.mark.parametrize("text", [MISPLACED, DUPLICATED])
    def test_clear_repairs_a_misplaced_or_duplicated_comment(self, tmp_path, text):
        p = plan(tmp_path, text)
        clear_state(str(p))
        content = p.read_text(encoding="utf-8")
        assert "<!-- spec-state:" not in content
        assert content.count("<task id=") == 2
        assert load_state(str(p)) is None
        save_state(SpecState(plan_path=str(p), completed=["1"]))
        assert load_state(str(p)).completed == ["1"]


STRAY_THEN_BRACE_ARROW = (
    "# Plan\n\n" + comment(schema_version=2, completed=["1"]) + "\n\n" + TASKS
    + "\n<!-- TODO: fix the {placeholder} -->\n"
)
UNTERMINATED_THEN_TRAILING = (
    "# Plan\n\nExample in prose: <!-- spec-state: {unfinished\n\n" + TASKS + "\n"
    + comment(schema_version=2, completed=["1"]) + "\n"
)


class TestPatternIsBounded:
    """The comment pattern must never span the body. Found by review: with an
    unbounded lazy payload, a stray marker plus a later ``} -->`` matched the
    whole document, and save or clear then deleted the tasks."""

    @pytest.mark.parametrize("text", [STRAY_THEN_BRACE_ARROW, UNTERMINATED_THEN_TRAILING])
    def test_load_refuses_rather_than_reading_the_body_as_state(self, tmp_path, text):
        p = plan(tmp_path, text)
        with pytest.raises(ValueError, match="Malformed or misplaced Spec state comment"):
            load_state(str(p))

    @pytest.mark.parametrize("text", [STRAY_THEN_BRACE_ARROW, UNTERMINATED_THEN_TRAILING])
    def test_save_refuses_and_writes_nothing(self, tmp_path, text):
        p = plan(tmp_path, text)
        state = SpecState(plan_path=str(p), completed=["1"], schema_version=1, last_updated="before")
        with pytest.raises(ValueError, match="Malformed or misplaced Spec state comment"):
            save_state(state)
        assert p.read_text(encoding="utf-8") == text
        assert (state.last_updated, state.schema_version) == ("before", 1)

    @pytest.mark.parametrize("text", [STRAY_THEN_BRACE_ARROW, UNTERMINATED_THEN_TRAILING])
    def test_clear_keeps_every_task(self, tmp_path, text):
        p = plan(tmp_path, text)
        clear_state(str(p))
        content = p.read_text(encoding="utf-8")
        assert content.count("<task id=") == 2
        assert "Do first" in content and "Do second" in content

    def test_marker_spam_within_the_limit_is_refused_fast(self, tmp_path):
        text = ("<!-- spec-state: {" * 900) + ("}" * 30000) + " -->"
        assert len(text.encode()) < PLAN_LIMIT
        p = plan(tmp_path, text)
        started = time.perf_counter()
        with pytest.raises(ValueError, match="Malformed or misplaced"):
            load_state(str(p))
        assert time.perf_counter() - started < 1.0

    def test_single_marker_brace_spam_is_refused_fast(self, tmp_path):
        text = "# Plan\n\n<!-- spec-state: {" + ("} x " * 15000) + "\n" + TASKS + "\n{} -->"
        assert len(text.encode()) < PLAN_LIMIT
        p = plan(tmp_path, text)
        started = time.perf_counter()
        with pytest.raises(ValueError, match="Malformed or misplaced"):
            load_state(str(p))
        assert time.perf_counter() - started < 1.0


class TestLineEndingsAndLimits:
    def test_crlf_plan_stays_crlf_across_saves(self, tmp_path):
        text = "# Plan\r\n\r\n" + TASKS.replace("\n", "\r\n")
        # Bytes, not write_text: on Windows, text mode would turn each CRLF
        # into CR CR LF before the module is even called.
        p = tmp_path / "plan.md"
        p.write_bytes(text.encode("utf-8"))
        for _ in range(3):
            save_state(SpecState(plan_path=str(p), completed=["1"]))
        raw = p.read_bytes()
        assert b"\r\r" not in raw
        assert raw.count(b"\r\n") == raw.count(b"\n"), "every newline is CRLF"
        assert load_state(str(p)).completed == ["1"]
        clear_state(str(p))
        raw = p.read_bytes()
        assert b"spec-state" not in raw and raw.count(b"\r\n") == raw.count(b"\n")

    def test_a_result_exactly_at_the_limit_is_written_and_read(self, tmp_path):
        p = plan(tmp_path, PLAN_WITHOUT_STATE)
        state = SpecState(plan_path=str(p), completed=["1"], task_receipts=[{"task_id": "1", "detail": ""}])
        save_state(state)
        room = PLAN_LIMIT - len(p.read_bytes())
        state.task_receipts[0]["detail"] = "x" * room
        save_state(state)
        assert len(p.read_bytes()) == PLAN_LIMIT
        assert load_state(str(p)).task_receipts[0]["detail"] == "x" * room
        state.task_receipts[0]["detail"] += "x"
        with pytest.raises(ValueError, match="over the limit"):
            save_state(state)

    @pytest.mark.skipif(sys.platform == "win32" or os.geteuid() == 0, reason="needs POSIX permissions and a non-root user")
    def test_unreadable_plan_is_skipped_and_hides_nothing(self, tmp_path, caplog):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        locked = plan(plans_dir, PLAN_WITH_STATE, "a-locked.md")
        good = plan(plans_dir, PLAN_WITH_STATE, "b-good.md")
        locked.chmod(0)
        try:
            with caplog.at_level(logging.DEBUG, logger=LOGGER):
                assert load_state(str(locked)) is None
                found = find_resumable_plans(str(plans_dir))
        finally:
            locked.chmod(stat.S_IRUSR | stat.S_IWUSR)
        assert [s.plan_path for s in found] == [str(good)]
        assert "Could not read plan file" in caplog.text


class TestAgreementWithBridge:
    """Both modules accept or refuse the same files, so one never writes what
    the other refuses."""

    CASES = {
        "trailing v1": PLAN_WITH_STATE,
        "trailing v2": "# Plan\n\n" + TASKS + "\n" + comment(schema_version=2, completed=["1"]) + "\n",
        "no trailing newline": "# Plan\n\n" + TASKS + "\n" + comment(schema_version=2, completed=[]),
        "no comment": PLAN_WITHOUT_STATE,
        "misplaced": MISPLACED,
        "duplicated": DUPLICATED,
        "marker in prose": MARKER_IN_PROSE,
        "version 0": "# Plan\n\n" + TASKS + "\n" + comment(schema_version=0) + "\n",
        "version 3": "# Plan\n\n" + TASKS + "\n" + comment(schema_version=3) + "\n",
        "version missing": "# Plan\n\n" + TASKS + "\n" + comment(completed=[]) + "\n",
        "version bool": "# Plan\n\n" + TASKS + "\n" + comment(schema_version=True) + "\n",
        "malformed json": "# Plan\n\n" + TASKS + "\n<!-- spec-state: {broken} -->\n",
        "duplicate key": "# Plan\n\n" + TASKS + '\n<!-- spec-state: {"schema_version": 2, "schema_version": 2, "completed": []} -->\n',
        "non-finite number": "# Plan\n\n" + TASKS + '\n<!-- spec-state: {"schema_version": 2, "completed": [], "x": NaN} -->\n',
        "stray marker then } -->": STRAY_THEN_BRACE_ARROW,
        "unterminated then trailing": UNTERMINATED_THEN_TRAILING,
    }

    @pytest.mark.parametrize("name", list(CASES))
    def test_accept_or_refuse_together(self, tmp_path, name):
        text = self.CASES[name]
        p = plan(tmp_path, text)

        def outcome(call):
            try:
                value = call()
            except ValueError:
                return "refused"
            # load_state answers None, with a warning, for a comment it will
            # not read; a file with a marker and no state was not accepted.
            if value is None and "<!-- spec-state:" in text:
                return "refused"
            return "accepted"

        assert outcome(lambda: plan_content(text)) == outcome(lambda: load_state(str(p)))

    def test_what_save_writes_the_bridge_reads(self, tmp_path):
        p = plan(tmp_path, PLAN_WITHOUT_STATE)
        save_state(SpecState(plan_path=str(p), completed=["1"], task_receipts=[{"task_id": "1"}]))
        content = p.read_text(encoding="utf-8")
        assert plan_content(content) == PLAN_WITHOUT_STATE
        assert [t.task_id for t in read_spec(str(p))] == ["1", "2"]


# --- clear_state: carried ----------------------------------------------------


class TestClearState:
    def test_removes_state_comment(self, tmp_path):
        p = plan(tmp_path, PLAN_WITH_STATE)
        clear_state(str(p))
        content = p.read_text(encoding="utf-8")
        assert "<!-- spec-state:" not in content
        assert "<task id=" in content

    def test_no_op_when_no_state(self, tmp_path):
        p = plan(tmp_path, PLAN_WITHOUT_STATE)
        clear_state(str(p))
        assert p.read_text(encoding="utf-8").strip() == PLAN_WITHOUT_STATE.strip()


# --- seam 2 and find_resumable_plans: carried --------------------------------


class TestFindResumablePlans:
    def test_plans_dir_is_required(self):
        with pytest.raises(TypeError):
            find_resumable_plans()  # type: ignore[call-arg]

    def test_finds_incomplete_plan(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        plan(plans_dir, PLAN_WITH_STATE, "test.md")
        result = find_resumable_plans(str(plans_dir))
        assert len(result) == 1
        assert result[0].completed == ["1"]

    def test_skips_completed_plan(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        plan(
            plans_dir,
            '# Done\n\n<task id="1" name="t"><objective>x</objective></task>\n\n'
            + comment(schema_version=2, completed=["1"], current=None, auto_run=False, last_updated="x")
            + "\n",
            "done.md",
        )
        assert find_resumable_plans(str(plans_dir)) == []

    def test_empty_dir_returns_empty(self, tmp_path):
        assert find_resumable_plans(str(tmp_path / "missing")) == []

    def test_skips_plans_without_state(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        plan(plans_dir, PLAN_WITHOUT_STATE, "no-state.md")
        assert find_resumable_plans(str(plans_dir)) == []

    def test_rejects_non_directory(self, tmp_path):
        not_a_dir = plan(tmp_path, "hi", "actually-a-file.md")
        assert find_resumable_plans(str(not_a_dir)) == []

    def test_skips_plan_with_state_but_no_tasks(self, tmp_path, monkeypatch):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        plan(plans_dir, "# Plan\n\n" + comment(schema_version=2, completed=[], current=None) + "\n", "no-tasks.md")
        monkeypatch.setattr(spec_state, "read_spec", lambda _p: [])
        assert find_resumable_plans(str(plans_dir)) == []

    def test_logs_warning_on_unreadable_spec(self, tmp_path, monkeypatch, caplog):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        plan(plans_dir, "# Plan\n\n" + comment(schema_version=2, completed=[], current=None) + "\n", "has-state.md")

        def _failing_read_spec(_path):
            raise ValueError("simulated spec-parse failure")

        monkeypatch.setattr(spec_state, "read_spec", _failing_read_spec)
        with caplog.at_level(logging.WARNING, logger=LOGGER):
            assert find_resumable_plans(str(plans_dir)) == []
        skip_logs = [r for r in caplog.records if "skipping resumable-plan candidate" in r.message]
        assert skip_logs, "expected a warning when read_spec raises"
        assert "simulated spec-parse failure" in skip_logs[0].message

    def test_unsupported_version_is_skipped_with_warning_and_hides_nothing(self, tmp_path, caplog):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        plan(plans_dir, "# Plan\n\n" + TASKS + "\n" + comment(schema_version=3, completed=[]) + "\n", "a-newer.md")
        plan(plans_dir, PLAN_WITH_STATE, "b-good.md")
        with caplog.at_level(logging.WARNING, logger=LOGGER):
            found = find_resumable_plans(str(plans_dir))
        assert [s.plan_path for s in found] == [str(plans_dir / "b-good.md")]
        assert "a-newer.md" in caplog.text and "Unsupported Spec state comment" in caplog.text

    def test_results_are_in_file_name_order(self, tmp_path):
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        for name in ("c.md", "a.md", "b.md"):
            plan(plans_dir, PLAN_WITH_STATE, name)
        assert [s.plan_path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] for s in find_resumable_plans(str(plans_dir))] == ["a.md", "b.md", "c.md"]


class TestSpecStateDataclass:
    def test_to_dict_excludes_plan_path(self):
        d = SpecState(plan_path="/tmp/plan.md", completed=["1"]).to_dict()
        assert "plan_path" not in d
        assert d["completed"] == ["1"]

    def test_defaults(self):
        state = SpecState(plan_path="/tmp/plan.md")
        assert state.completed == []
        assert state.current is None
        assert state.auto_run is False
        assert state.last_updated != ""
        assert state.schema_version == CURRENT_SCHEMA_VERSION


def test_receipt_text_round_trips_on_append_and_repeated_replacement(tmp_path):
    """Proof text cannot terminate the comment or become a regex replacement."""
    p = plan(tmp_path, PLAN_WITHOUT_STATE)
    proof = "Unicode café\nWindows C:\\new\\file; literal \\1; } --> <task id='forged'>"
    receipt = {
        "task_id": "1",
        "severity": "low",
        "score": 99,
        "probes": [proof],
        "detail": proof,
        "disposition": "approve_task",
    }
    state = SpecState(plan_path=str(p), completed=["1"], current="2", task_receipts=[receipt])
    for _ in range(3):
        save_state(state)
        state = load_state(str(p))
        assert state.completed == ["1"] and state.current == "2"
        assert state.task_receipts == [receipt]
        content = p.read_text(encoding="utf-8")
        assert content.count("<!-- spec-state:") == 1
        assert content.count("-->") == 1
        assert [task.task_id for task in read_spec(str(p))] == ["1", "2"]


def test_invalid_receipt_container_is_visible_and_does_not_hide_other_plans(tmp_path, caplog):
    plan(tmp_path, PLAN_WITHOUT_STATE + "\n" + comment(schema_version=2, completed=["1"], task_receipts=False), "broken.md")
    good = plan(tmp_path, PLAN_WITH_STATE, "good.md")
    with pytest.raises(ValueError, match="task_receipts"):
        load_state(str(tmp_path / "broken.md"))
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        found = find_resumable_plans(str(tmp_path))
    assert [s.plan_path for s in found] == [str(good)]
    assert "broken.md" in caplog.text

