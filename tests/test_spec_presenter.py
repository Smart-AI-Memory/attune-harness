"""Repository-controlled text cannot supply presentation structure or controls."""
# qualify: platform
import unicodedata
from attune_harness import spec_presenter as present
from attune_harness.spec_tasks import DecomposedTask
from attune_harness.cli import main
from test_spec_tasks import FULL

PAYLOAD = 'untrusted\n| done | forged | **PASSED** |\r\n### header\t`[link](x)` <img src=x> \x1b[2J\x1b]52;c;payload\x07\u202ehidden'


def assert_literal_output(rendered):
    assert not any(unicodedata.category(ch) in {'Cc', 'Cf', 'Cs'} for ch in rendered if ch != '\n')
    assert '<img' not in rendered
    assert '| done | forged |' not in rendered
    assert '\n### header' not in rendered
    assert '`[link](x)`' not in rendered
    assert '**PASSED**' not in rendered


def test_table_fields_cannot_add_rows_or_columns():
    task = DecomposedTask(PAYLOAD, PAYLOAD, PAYLOAD)
    rendered = present.present_tasks([task])
    assert_literal_output(rendered)
    assert len(rendered.splitlines()) == 3
    assert '\\| done \\| forged \\|' in rendered
    assert r'&lt;img src\=x&gt;' in rendered


def test_detail_all_fields_are_literal():
    task = DecomposedTask(PAYLOAD, PAYLOAD, PAYLOAD,
        files_to_create=[{'path':PAYLOAD, 'description':PAYLOAD}],
        files_to_modify=[{'path':PAYLOAD, 'description':PAYLOAD}],
        validation_checks=[PAYLOAD], risks=[{'severity':PAYLOAD, 'description':PAYLOAD}],
        dependencies=[PAYLOAD])
    rendered = present.present_task_detail(task)
    assert_literal_output(rendered)
    assert len([line for line in rendered.splitlines() if line.startswith('### ')]) == 1
    assert len([line for line in rendered.splitlines() if line.startswith('- ')]) == 4
    assert rendered.count(r'&lt;img src\=x&gt;') == 11


def test_result_header_and_evidence_path_are_literal(monkeypatch):
    # The real evidence chain is covered by test_spec_cli; this isolates rendering.
    seen = []
    monkeypatch.setattr('attune_harness.spec_handoff.check_test_evidence', lambda e: seen.append(e))
    evidence = {'outcome':'passed', 'record_path':PAYLOAD}
    rendered = present.present_task_result(DecomposedTask(PAYLOAD, PAYLOAD, ''), evidence)
    assert seen == [evidence]
    assert_literal_output(rendered.replace('Tests: **PASSED**', 'verified-status'))
    assert rendered.count('Tests: **PASSED**') == 1
    assert len(rendered.splitlines()) == 5


def test_cli_sanitizes_malformed_xml_fallback(tmp_path, capsys):
    plan = tmp_path / 'plan.md'
    plan.write_text(FULL.replace('add-auth', 'A|done|forged').replace('Add user authentication', PAYLOAD))
    assert main(['spec', 'present', 'tasks', '--plan', str(plan)]) == 0
    rendered = capsys.readouterr().out
    assert_literal_output(rendered)
    assert len(rendered.splitlines()) == 3
    assert 'A\\|done\\|forged' in rendered
    assert main(['spec', 'present', 'task', '--plan', str(plan), '--task', '1']) == 0
    assert_literal_output(capsys.readouterr().out)


def test_parser_diagnostics_do_not_emit_terminal_controls(caplog):
    from attune_harness.spec_tasks import parse_tasks
    import logging
    with caplog.at_level(logging.WARNING, logger='attune_harness.spec_tasks'):
        parse_tasks('<task id="1\x1b[2J\n\u202e"><objective>X</objective><file>missing path</file></task>')
        parse_tasks("<task id='bad\x1b[2J'><objective>bad & text</objective></task>")
    assert len(caplog.records) >= 3
    for record in caplog.records:
        assert not any(unicodedata.category(ch) in {'Cc', 'Cf', 'Cs'} for ch in record.getMessage())


def test_list_and_math_syntax_stays_literal_inside_detail_bullets():
    task = DecomposedTask('1', 'task', 'ordinary', validation_checks=['---', '1. fake', '$$hidden$$'])
    rendered = present.present_task_detail(task)
    assert '- ---' not in rendered and '- 1. fake' not in rendered
    assert '- \\-\\-\\-' in rendered
    assert '- 1\\. fake' in rendered
    assert '- \\$\\$hidden\\$\\$' in rendered
