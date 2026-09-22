"""The <task> parser and the plan reader.

Carried from Attune AI's tests/unit/wizards/test_wizard_decomposer.py (the
parsing classes) and tests/unit/pipeline/test_spec_reader.py, at b89f7953f.
The decomposition tests that drive a model stayed behind with the decomposer.
"""

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


def test_a_bare_ampersand_between_blocks_falls_back_to_regex(caplog):
    tasks, messages = parse(
        caplog,
        '<task id="1"><objective>A</objective></task>\nNotes & caveats.\n<task id="2"><objective>B</objective></task>',
    )
    assert [t.task_id for t in tasks] == ["1", "2"]
    assert any("not well-formed" in m for m in messages)


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
