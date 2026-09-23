"""The <task> parser and the plan reader.

Carried from Attune AI's tests/unit/wizards/test_wizard_decomposer.py (the
parsing classes) and tests/unit/pipeline/test_spec_reader.py, at b89f7953f.
The decomposition tests that drive a model stayed behind with the decomposer.
"""
# qualify: platform

import logging

import pytest

from attune_harness import spec_tasks
from attune_harness.spec_tasks import DecomposedTask, parse_tasks, read_spec

LOGGER = "attune_harness.spec_tasks"


def parse(caplog, text):
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        tasks = parse_tasks(text)
    return tasks, [record.getMessage() for record in caplog.records]


def regex(caplog, text):
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        tasks = spec_tasks._parse_with_regex(text)
    return tasks, [record.getMessage() for record in caplog.records]


FULL = """
<tasks>
  <task id="1" name="add-auth">
    <objective>Add user authentication</objective>
    <files-to-create>
      <file path="src/auth.py">Authentication module</file>
    </files-to-create>
    <files-to-modify>
      <file path="src/app.py">Add auth middleware</file>
    </files-to-modify>
    <validation>
      <check>Auth endpoint returns 401 for unauthenticated</check>
    </validation>
    <risks>
      <risk severity="medium">May break existing sessions</risk>
    </risks>
    <dependencies>
      <dep>0</dep>
    </dependencies>
  </task>
</tasks>
"""


# ---- the data class ---------------------------------------------------------


def test_defaults_and_to_dict_shape():
    task = DecomposedTask(task_id="1", name="n", objective="o")
    assert task.to_dict() == {
        "task_id": "1",
        "name": "n",
        "objective": "o",
        "files_to_create": [],
        "files_to_modify": [],
        "validation_checks": [],
        "risks": [],
        "dependencies": [],
    }


def test_to_xml_round_trips_through_the_parser():
    [task] = parse_tasks(FULL)
    assert parse_tasks(task.to_xml())[0].to_dict() == task.to_dict()


def test_to_xml_defaults_for_missing_risk_fields_and_omits_empty_sections():
    task = DecomposedTask(
        task_id="1", name="n", objective="o", risks=[{"description": "d"}, {"severity": "high"}]
    )
    xml = task.to_xml()
    assert '<risk severity="medium">d</risk>' in xml and '<risk severity="high"></risk>' in xml
    assert (
        "<files-to-create>" not in xml and "<validation>" not in xml and "<dependencies>" not in xml
    )


# ---- parsing well-formed input -----------------------------------------------


def test_parse_single_task_with_every_section(caplog):
    tasks, messages = parse(caplog, FULL)
    assert messages == []
    [task] = tasks
    assert (task.task_id, task.name, task.objective) == ("1", "add-auth", "Add user authentication")
    assert task.files_to_create == [{"path": "src/auth.py", "description": "Authentication module"}]
    assert task.files_to_modify == [{"path": "src/app.py", "description": "Add auth middleware"}]
    assert task.validation_checks == ["Auth endpoint returns 401 for unauthenticated"]
    assert task.risks == [{"severity": "medium", "description": "May break existing sessions"}]
    assert task.dependencies == ["0"]


def test_parse_multiple_tasks_in_order():
    tasks = parse_tasks(
        '<tasks><task id="1" name="one"><objective>First</objective></task>'
        '<task id="2" name="two"><objective>Second</objective><dependencies><dep>1</dep></dependencies></task></tasks>'
    )
    assert [t.task_id for t in tasks] == ["1", "2"] and tasks[1].dependencies == ["1"]


def test_name_falls_back_to_the_id():
    assert parse_tasks('<task id="1"><objective>Test</objective></task>')[0].name == "1"


def test_markdown_fences_and_prose_around_the_blocks_are_ignored():
    text = 'Here is the decomposition:\n\n```xml\n<tasks>\n  <task id="1" name="fix-bug">\n    <objective>Fix the bug</objective>\n  </task>\n</tasks>\n```\n\nThat should do it!'
    [task] = parse_tasks(text)
    assert task.name == "fix-bug"


def test_single_quoted_and_reordered_attributes_parse(caplog):
    tasks, messages = parse(
        caplog,
        "<tasks><task id='1' name='quoted'><objective>A</objective></task>"
        '<task name="reordered" id="2" ><objective>B</objective></task></tasks>',
    )
    assert [(t.task_id, t.name, t.objective) for t in tasks] == [
        ("1", "quoted", "A"),
        ("2", "reordered", "B"),
    ]
    assert messages == []


def test_parser_and_regex_paths_agree_field_for_field(caplog):
    text = (
        '```xml\n<task id="3" name="full"><objective>Add auth</objective>'
        '<files-to-create><file path="src/auth.py">Auth module</file></files-to-create>'
        '<files-to-modify><file path="src/app.py">Wire it</file></files-to-modify>'
        "<validation><check>401 when anonymous</check><check>200 when signed in</check></validation>"
        '<risks><risk severity="high">Session break</risk></risks>'
        "<dependencies><dep>1</dep><dep>2</dep></dependencies></task>\n```"
    )
    tasks, messages = parse(caplog, text)
    assert messages == []
    assert tasks[0].to_dict() == spec_tasks._parse_with_regex(text)[0].to_dict()


def test_inline_markup_is_kept_and_text_is_decoded_once():
    assert (
        parse_tasks('<task id="1"><objective>Use <code>x</code> here</objective></task>')[
            0
        ].objective
        == "Use <code>x</code> here"
    )
    [task] = parse_tasks(
        '<task id="1"><files-to-modify><file path="a.py"><change location="f">def f(x) -> int: pass</change>'
        " then <code>&lt;div&gt;</code></file></files-to-modify></task>"
    )
    assert (
        task.files_to_modify[0]["description"]
        == '<change location="f">def f(x) -> int: pass</change> then <code><div></code>'
    )
    [task] = parse_tasks(
        '<task id="1"><objective><change location="say &quot;hi&quot; &amp; wave">x</change></objective></task>'
    )
    assert task.objective == '<change location="say &quot;hi&quot; & wave">x</change>'


def test_entities_decode_on_the_parser_path_only():
    text = '<task id="1"><objective>A &amp; B</objective></task>'
    assert parse_tasks(text)[0].objective == "A & B"
    assert spec_tasks._parse_with_regex(text)[0].objective == "A &amp; B"


def test_a_task_nested_in_a_description_is_body_text_not_a_task(caplog):
    tasks, messages = parse(
        caplog,
        '<task id="1"><objective>Emit blocks like <task id="example"><objective>x</objective></task></objective></task>'
        '<task id="2"><objective>real</objective></task>',
    )
    assert [t.task_id for t in tasks] == ["1", "2"]
    assert tasks[0].objective.startswith('Emit blocks like <task id="example">')
    assert any("Task 1: 1 nested <task> element(s) kept as body text" in m for m in messages)


def test_attribute_less_children_are_dropped_with_a_warning(caplog):
    tasks, messages = parse(
        caplog,
        '<task id="1"><objective>x</objective><files-to-create><file>src/no_path.py</file></files-to-create>'
        "<risks><risk>no severity</risk></risks></task>",
    )
    assert tasks[0].files_to_create == [] and tasks[0].risks == []
    assert any("Task 1: 1 <file tag(s) present but 0 parsed" in m for m in messages)
    assert any("Task 1: 1 <risk tag(s) present but 0 parsed" in m for m in messages)


def test_a_task_without_an_id_is_skipped_with_a_warning(caplog):
    tasks, messages = parse(
        caplog, '<task name="anon"><objective>x</objective></task><task id="2"></task>'
    )
    assert [t.task_id for t in tasks] == ["2"]
    assert any("no id attribute" in m for m in messages)


def test_no_task_block_at_all(caplog):
    tasks, messages = parse(caplog, "Some non-XML response")
    assert tasks == [] and messages == ["No <task> elements found in decomposition response"]


# ---- the regex fallback and its warnings -----------------------------------


def test_prose_between_blocks_is_never_parsed_so_both_tasks_stay_on_the_parser_path(caplog):
    # O-58: a bare & in a note between two tasks used to drop the whole plan to
    # the regex path, where entities stop being decoded. Each block is parsed
    # on its own now, so the prose is never seen and both tasks decode.
    tasks, messages = parse(
        caplog,
        '<task id="1"><objective>R&amp;D</objective></task>\nNotes & caveats: R&D <next>.\n'
        '<task id="2"><objective>B &amp; C</objective></task>',
    )
    assert [(t.task_id, t.objective) for t in tasks] == [("1", "R&D"), ("2", "B & C")]
    assert messages == []


def test_a_rejected_block_falls_back_alone_and_the_other_block_still_decodes(caplog):
    tasks, messages = parse(
        caplog,
        '<task id="1"><objective>A & B</objective></task>\n<task id="2"><objective>C &amp; D</objective></task>',
    )
    assert [(t.task_id, t.objective) for t in tasks] == [("1", "A & B"), ("2", "C & D")]
    assert [m for m in messages if "not well-formed" in m and "falling back" in m]
    assert len(messages) == 1


def test_a_stray_close_tag_keeps_the_whole_plan_fallback_and_its_warnings(caplog):
    # The tags do not balance, so the region is parsed as one document as
    # before and the fallback describes the whole plan.
    tasks, messages = parse(
        caplog,
        '<task id="1"><objective>A</objective></task></task>\n<task id="2"><objective>B</objective></task>',
    )
    assert [t.task_id for t in tasks] == ["1", "2"]
    assert any("not well-formed" in m for m in messages)


def test_a_spaced_close_tag_on_a_rejected_block_still_recovers_the_task(caplog):
    # Review finding: _TASK_EDGE accepted "</task >" but the block regex did
    # not, so a rejected block closed that way vanished. Both accept it now.
    tasks, messages = parse(
        caplog,
        '<task id="1"><objective>A & B</objective></task >\n<task id="2"><objective>C</objective></task>',
    )
    assert [(t.task_id, t.objective) for t in tasks] == [("1", "A & B"), ("2", "C")]
    assert not any("No <task> elements" in m for m in messages)


def test_a_comment_in_the_region_keeps_the_whole_plan_path(caplog):
    # Review finding: the edge scan does not read comments, so a self-closing
    # task plus a comment containing </task> mis-split. Any comment or CDATA
    # in the region now takes the whole-region path, as before this change.
    text = (
        '<task id="1"/>\n<!-- reviewer: the close is </task> -->\n'
        '<task id="2"><objective>B</objective></task>'
    )
    assert spec_tasks._top_level_blocks(text) is None
    tasks, _ = parse(caplog, text)
    assert [(t.task_id, t.objective) for t in tasks] == [("1", ""), ("2", "B")]


def test_a_self_closing_task_is_a_block_of_its_own(caplog):
    tasks, messages = parse(caplog, '<task id="1"/>\nR&D\n<task id="2"><objective>B &amp; C</objective></task>')
    assert [(t.task_id, t.objective) for t in tasks] == [("1", ""), ("2", "B & C")]
    assert messages == []


def test_orphaned_task_content_between_blocks_is_still_reported(caplog):
    tasks, messages = parse(
        caplog,
        '<task id="1"><objective>A</objective></task>\n<objective>lost</objective>\n'
        '<task id="2"><objective>B</objective></task>',
    )
    assert [t.task_id for t in tasks] == ["1", "2"]
    assert any("outside any <task> block (<objective>) - 2 task(s) parsed" in m for m in messages)


def test_a_block_neither_path_can_read_is_reported_as_dropped_not_as_an_empty_plan(caplog):
    tasks, messages = parse(
        caplog,
        "<task id='1'><objective>A & B</objective></task>\n<task id=\"2\"><objective>C</objective></task>",
    )
    assert [t.task_id for t in tasks] == ["2"]
    assert any(m.startswith("Task block rejected by the parser and unmatched by the fallback - dropped: <task id='1'>") for m in messages)
    assert not any("No <task> elements" in m or "0 task(s) parsed" in m for m in messages)


def test_a_tasks_wrapper_does_not_defeat_the_per_block_fix(caplog):
    tasks, messages = parse(
        caplog,
        '<tasks>\n<task id="1"><objective>R&amp;D</objective></task>\nNotes & caveats.\n'
        '<task id="2"><objective>B</objective></task>\n</tasks>',
    )
    assert [(t.task_id, t.objective) for t in tasks] == [("1", "R&D"), ("2", "B")]
    assert messages == []


def test_an_unbalanced_plan_still_reports_orphans_outside_the_region(caplog):
    tasks, messages = parse(
        caplog,
        '<file path="x">lost</file>\n<task id="1"><objective>A</objective>\n<task id="2"><objective>B</objective></task>',
    )
    assert any("outside any <task> block" in m and "<file>" in m for m in messages)


def test_a_tasks_tag_inside_a_body_does_not_defeat_the_per_block_fix(caplog):
    # Review mutation: without the word boundary in the edge scan, "<tasks>"
    # in a body counts as an opening and the region stops splitting.
    tasks, messages = parse(
        caplog,
        '<task id="1"><objective>see <tasks/> list</objective></task>\nR&D\n'
        '<task id="2"><objective>B &amp; C</objective></task>',
    )
    assert [(t.task_id, t.objective) for t in tasks] == [("1", "see <tasks /> list"), ("2", "B & C")]
    assert messages == []


def test_the_unsplit_guard_keeps_comment_text_out_of_the_parser(caplog):
    # Review mutation: with the guard removed, a comment holding "<task >"
    # becomes a block and the parser warns about a task with no id.
    tasks, messages = parse(
        caplog,
        '<task id="1"><objective>A</objective></task><!-- <task > </task> --><task id="2"><objective>B</objective></task>',
    )
    assert [t.task_id for t in tasks] == ["1", "2"]
    assert not any("no id attribute" in m for m in messages)


def test_top_level_blocks_keep_a_nested_example_inside_its_block():
    nested = '<task id="1"><objective>See <task id="x">ex</task></objective></task>'
    assert spec_tasks._top_level_blocks(nested + '\nprose\n<task id="2">B</task>') == [
        nested,
        '<task id="2">B</task>',
    ]
    assert spec_tasks._top_level_blocks('<task id="1"><objective>A</objective>') is None
    assert spec_tasks._top_level_blocks('</task><task id="1"><objective>A</objective></task>') is None


def test_well_formed_tasks_on_the_regex_path_emit_no_warnings(caplog):
    tasks, messages = regex(
        caplog,
        '<task id="1" name="ok"><objective>All tags parsed</objective>'
        '<files-to-create><file path="a.py">A</file></files-to-create>'
        '<files-to-modify><file path="b.py">B</file></files-to-modify>'
        '<validation><check>passes</check></validation><risks><risk severity="low">none</risk></risks>'
        "<dependencies><dep>0</dep></dependencies></task>",
    )
    assert len(tasks) == 1 and messages == []


def test_regex_path_warns_when_a_task_falls_outside_every_block(caplog):
    tasks, messages = regex(
        caplog,
        '<tasks><task id="1" name="kept"><objective>Parsed</objective></task>'
        "<task id='2' name='dropped'><objective>Lost to single quotes</objective>"
        '<files-to-create><file path="src/lost.py">never seen</file></files-to-create></task></tasks>',
    )
    assert [t.task_id for t in tasks] == ["1"]
    [message] = [m for m in messages if "outside any <task> block" in m]
    assert "(<file>, <objective>)" in message and "1 task(s) parsed" in message


def test_regex_path_reports_orphaned_content_even_with_no_tasks(caplog):
    tasks, messages = regex(caplog, "<task id='1'><objective >x</objective></task>")
    assert tasks == []
    assert messages[0] == "No <task> elements found in decomposition response"
    assert "outside any <task> block (<objective>) - 0 task(s) parsed" in messages[1]
    caplog.clear()
    tasks, messages = parse(caplog, "<task id='1'><objective >x</objective></task>")
    assert tasks[0].objective == "x" and messages == []


def test_a_missing_close_tag_swallows_the_next_task_and_both_warnings_reach_the_caller(caplog):
    text = '<task id="1"><objective>First, never closed</objective>\n<task id="2"><objective>Second</objective></task>'
    tasks, messages = parse(caplog, text)
    assert [t.task_id for t in tasks] == ["1"]
    assert any("not well-formed" in m and "falling back" in m for m in messages)
    assert any("Task 1: body contains another <task> opening" in m for m in messages)


# ---- hostile input: the five cases from Task 1's test ------------------------


LAUGHS = (
    '<?xml version="1.0"?><!DOCTYPE t [<!ENTITY a "'
    + "ha" * 50
    + '">'
    + "".join(f'<!ENTITY {chr(98 + i)} "' + f"&{chr(97 + i)};" * 10 + '">' for i in range(7))
    + ']>\n<task id="1"><objective>&h;</objective></task>'
)
EXTERNAL = '<?xml version="1.0"?><!DOCTYPE t [<!ENTITY x SYSTEM "file:///etc/passwd">]>\n<task id="1"><objective>&x;</objective></task>'
QUADRATIC = (
    '<?xml version="1.0"?><!DOCTYPE t [<!ENTITY a "'
    + "A" * 20000
    + '">]>\n<task id="1"><objective>'
    + "&a;" * 2000
    + "</objective></task>"
)
INSIDE = '<task id="1"><objective><!DOCTYPE t [<!ENTITY a "boom">]>&a;</objective></task>'


@pytest.mark.parametrize(
    "text, expected",
    [
        (LAUGHS, "&h;"),
        (EXTERNAL, "&x;"),
        (QUADRATIC, "&a;" * 2000),
        (INSIDE, '<!DOCTYPE t [<!ENTITY a "boom">]>&a;'),
        (
            '<!DOCTYPE r [<!ENTITY lol "lol">]><task id="1"><objective>&lol;</objective></task>',
            "&lol;",
        ),
    ],
)
def test_entity_declarations_never_reach_the_parser_and_nothing_expands(caplog, text, expected):
    # Only the <task> region is parsed, so a DOCTYPE before it is never seen and
    # one inside it is not well-formed. Either way the regex path takes over and
    # the entity reference is kept as the literal text the author wrote.
    tasks, messages = parse(caplog, text)
    assert [t.task_id for t in tasks] == ["1"]
    assert tasks[0].objective == expected
    assert any("not well-formed" in m and "falling back" in m for m in messages)


def test_the_wrapper_not_the_cut_is_what_keeps_an_entity_from_expanding(caplog):
    # Parsed as a bare document, an internal subset is legal and the entity
    # expands. Wrapped in a root element, the same bytes are not well-formed.
    text = '<!DOCTYPE r [<!ENTITY lol "expanded">]><task id="1"><objective>&lol;</objective></task>'
    import xml.etree.ElementTree as ET
    assert ET.fromstring(text).find("objective").text == "expanded"
    with pytest.raises(ET.ParseError):
        ET.fromstring(f"<r>{text}</r>")
    tasks, messages = parse(caplog, text)
    assert tasks[0].objective == "&lol;"
    assert any("falling back" in m for m in messages)


def test_a_plan_nested_thousands_deep_parses_without_exhausting_the_stack():
    depth = 9000
    text = '<task id="1"><objective>' + "<a>" * depth + "x" + "</a>" * depth + "</objective></task>"
    assert len(text) < spec_tasks.PLAN_LIMIT
    [task] = parse_tasks(text)
    assert task.objective.startswith("<a><a>") and task.objective.endswith("</a></a>")


def test_a_lone_surrogate_in_a_direct_call_falls_back_instead_of_escaping(caplog):
    tasks, messages = parse(caplog, '<task id="1"><objective>a\ud800b</objective></task>')
    assert [t.task_id for t in tasks] == ["1"]
    assert any("falling back" in m for m in messages)


def test_thousands_of_unclosed_blocks_finish_quickly():
    import time
    text = '<task id="1">' * 4000
    start = time.perf_counter()
    assert parse_tasks(text) == []
    # About 1 s here; the limit only has to catch the quadratic path doubling.
    assert time.perf_counter() - start < 10.0


def test_a_normal_task_still_parses_beside_the_hostile_cases():
    assert (
        parse_tasks('<task id="1"><objective>Fix &amp; test</objective></task>')[0].objective
        == "Fix & test"
    )


# ---- the reader -------------------------------------------------------------


def test_read_spec_reads_a_plan_file(tmp_path):
    plan = tmp_path / "plan.md"
    plan.write_text("# Plan\n\nSome prose.\n" + FULL + "\nMore prose.\n", encoding="utf-8")
    [task] = read_spec(str(plan))
    assert task.name == "add-auth" and task.files_to_create[0]["path"] == "src/auth.py"


@pytest.mark.parametrize("content", ["", "# Just a heading\n\nNo tasks here.\n"])
def test_read_spec_returns_empty_for_a_plan_with_no_tasks(tmp_path, content):
    plan = tmp_path / "plan.md"
    plan.write_text(content, encoding="utf-8")
    assert read_spec(str(plan)) == []


def test_read_spec_refuses_an_empty_path_and_a_missing_file(tmp_path):
    with pytest.raises(ValueError, match="non-empty string"):
        read_spec("")
    with pytest.raises(FileNotFoundError, match="Plan file not found"):
        read_spec(str(tmp_path / "missing.md"))


def test_read_spec_refuses_an_oversize_plan_whole(tmp_path):
    plan = tmp_path / "plan.md"
    plan.write_text(
        '<task id="1"><objective>' + "x" * spec_tasks.PLAN_LIMIT + "</objective></task>\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="exceeds its limit of 65536 bytes"):
        read_spec(str(plan))


def test_read_spec_goes_through_path_validation(monkeypatch, tmp_path):
    seen = []

    def spy(path, allowed_dir=None):
        seen.append(path)
        return tmp_path / "plan.md"

    monkeypatch.setattr(spec_tasks, "validate_file_path", spy)
    (tmp_path / "plan.md").write_text(
        '<task id="1"><objective>x</objective></task>', encoding="utf-8"
    )
    assert len(read_spec("anything")) == 1 and seen == ["anything"]
