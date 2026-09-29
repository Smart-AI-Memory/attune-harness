"""``--format markdown`` on the task verbs and ``status`` for every task (first-run journey T5, R5).

JSON stays the default. Markdown is the same envelope printed for people, and
its exit code is the one the JSON path returns: the parity cases below run each
verb both ways on one fixture.
"""
# qualify: platform

import json
import os
import subprocess
import sys

import pytest

from attune_harness.cli import main
from attune_harness.human_output import VERBS, markdown

POSIX_ONLY = pytest.mark.skipif(os.name != 'posix', reason='the test verb qualifies the POSIX execution profile only')


def both(capsys, argv):
    """Run ``argv`` as JSON and as Markdown; return (json code, envelope, markdown code, text)."""
    code = main(argv)
    envelope = json.loads(capsys.readouterr().out)
    rendered = main([*argv, '--format', 'markdown'])
    return code, envelope, rendered, capsys.readouterr().out


def repository(root):
    root.mkdir()
    (root / 'tests').mkdir()
    (root / 'calc.py').write_text('def add(a, b):\n    return a + b\n', encoding='utf-8')
    (root / 'tests' / 'test_calc.py').write_text('from calc import add\n\n\ndef test_add():\n    assert add(1, 1) == 2\n',
                                                 encoding='utf-8')
    git = ['git', '-C', str(root), '-c', 'commit.gpgsign=false', '-c', 'user.name=t', '-c', 'user.email=t@example.invalid']
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run([*git, 'add', '.'], check=True)
    subprocess.run([*git, 'commit', '-qm', 'base'], check=True)
    (root / 'calc.py').write_text('def add(a, b):\n    return b + a\n', encoding='utf-8')
    return root


def test_every_task_verb_takes_the_option_with_json_as_default():
    from attune_harness.cli import build_parser
    parser = build_parser()
    commands = parser._subparsers._group_actions[0].choices
    for verb in VERBS:
        option = next(a for a in commands[verb]._actions if '--format' in a.option_strings)
        assert option.default == 'json' and tuple(option.choices) == ('json', 'markdown'), verb


def test_markdown_prefers_the_envelopes_own_text():
    text = markdown({'status': 'draft', 'presentation': {'markdown': '## Test this change\n\nbody\n'},
                     'record_path': '/tmp/r.json'})
    assert text == '## Test this change\n\nbody\n\n**Saved record:** /tmp/r.json\n'


def test_markdown_without_text_renders_status_error_and_next_action():
    text = markdown({'status': 'failed', 'operation': 'task-intake',
                     'error': {'type': 'ValueError', 'detail': 'No participant registry'},
                     'next_action': 'Run init'})
    assert text.splitlines() == ['## task-intake', '', '**Status:** failed', '',
                                 '**Refused (ValueError):** No participant registry', '', '**Next:** Run init']


def test_plan_refusal_keeps_its_exit_code(tmp_path, capsys):
    (tmp_path / 'request.json').write_text('{}', encoding='utf-8')
    code, envelope, rendered, text = both(capsys, ['plan', '--task-dir', str(tmp_path / 'task'),
                                                   '--request', str(tmp_path / 'request.json')])
    assert code == rendered == 2 and envelope['status'] == 'failed'
    assert '**Refused (ValueError):**' in text and '**Next:**' in text and not text.lstrip().startswith('{')


def test_review_refusal_keeps_its_exit_code(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, 'isatty', lambda: False)
    code, envelope, rendered, text = both(capsys, ['review', '--goal', 'Check', '--task-dir', str(tmp_path / 't')])
    assert code == rendered == 2 and 'attune-harness init' in text


def test_build_refusal_keeps_its_exit_code(tmp_path, capsys):
    code, envelope, rendered, text = both(capsys, ['build', str(tmp_path / 'absent')])
    assert code == rendered == 2 and envelope['status'] == 'failed' and '**Refused' in text


@POSIX_ONLY
def test_test_preview_accept_and_status_in_markdown(tmp_path, capsys):
    repo = repository(tmp_path / 'repo')
    base = ['test', '--project', str(repo), '--scope', 'calc.py', '--interpreter', sys.executable]
    code = main([*base, '--task-dir', str(tmp_path / 'json-task')])
    envelope = json.loads(capsys.readouterr().out)
    rendered = main([*base, '--task-dir', str(tmp_path / 'md-task'), '--format', 'markdown'])
    text = capsys.readouterr().out
    assert code == rendered == 1 and envelope['status'] == 'draft'
    assert text.startswith('## Test this change') and '**Saved record:**' in text
    checkpoint = json.loads((tmp_path / 'md-task' / 'record.json').read_text(encoding='utf-8'))['checkpoint_digest']
    assert main(['test', '--task-dir', str(tmp_path / 'md-task'), '--checkpoint', checkpoint, '--accept',
                 '--format', 'markdown']) == 0
    assert 'passed' in capsys.readouterr().out
    for fmt in ('markdown', 'html'):
        assert main(['status', str(tmp_path / 'md-task'), '--format', fmt]) == 0
        out = capsys.readouterr().out
        assert ('## Test this change' in out) if fmt == 'markdown' else out.startswith('<!doctype html>')
    assert main(['resume', str(tmp_path / 'md-task'), '--format', 'markdown']) == 0
    assert capsys.readouterr().out.startswith('## Test this change')
    # JSON status is unchanged by any of this.
    assert main(['status', str(tmp_path / 'md-task')]) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'completed'


@POSIX_ONLY
def test_a_continuation_note_stays_feature_work_only(tmp_path, capsys):
    repo = repository(tmp_path / 'repo')
    main(['test', '--project', str(repo), '--scope', 'calc.py', '--interpreter', sys.executable,
          '--task-dir', str(tmp_path / 'task')])
    capsys.readouterr()
    (tmp_path / 'note.json').write_text('{}', encoding='utf-8')
    assert main(['status', str(tmp_path / 'task'), '--format', 'markdown', '--continuation', str(tmp_path / 'note.json')]) == 2
    assert 'feature-work-v1' in json.loads(capsys.readouterr().out)['error']['detail']


def test_interactive_intake_is_refused_in_markdown(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(sys.stdin, 'isatty', lambda: True)
    with pytest.raises(SystemExit) as error:
        main(['review', '--goal', 'Check', '--format', 'markdown'])
    assert error.value.code == 2 and 'interactive intake prompts' in capsys.readouterr().err
