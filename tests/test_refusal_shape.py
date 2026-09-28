"""One refusal shape for the task verbs (first-run journey T6, R2).

A rejected combination of valid options prints a JSON refusal with ``error``
and ``next_action`` on stdout and still exits 2, as argparse's usage error did.
Unknown flags and malformed arguments stay argparse errors.
"""
# qualify: platform

import json

import pytest

from attune_harness.cli import main


def refused(capsys, argv):
    with pytest.raises(SystemExit) as exit:
        main(argv)
    output = capsys.readouterr()
    return exit.value.code, output.out, output.err


@pytest.mark.parametrize(('argv', 'words'), [
    (['fix', '--goal', 'Repair'], 'Fix requires --goal, --checkout, --scope and --probe'),
    (['fix', '--task-response', 'r.json'], 'Fix response requires --task-dir'),
    (['review'], 'Legacy review requires request and --run-dir'),
    (['review', '--goal', 'x', '--task-response', 'r.json'], '--goal and --task-response are mutually exclusive'),
    (['review', '--task-response', 'r.json', '--task-dir', 't', '--config', 'c.json'], 'saved registry'),
    (['review', 'r.json', '--run-dir', 'd', '--plan', 'solo'], 'Task intake options require --goal or --task-response'),
])
def test_a_rejected_combination_is_an_envelope_on_stdout(capsys, argv, words):
    code, out, err = refused(capsys, argv)
    envelope = json.loads(out)
    assert code == 2 and not err
    assert envelope['status'] == 'failed' and envelope['operation'] == 'task-intake'
    assert envelope['error']['type'] == 'UsageError' and words in envelope['error']['detail']
    assert envelope['next_action'].startswith(('See attune-harness', 'Name the completed'))


def test_the_finding_pair_names_how_to_select_findings(capsys, tmp_path):
    code, out, _ = refused(capsys, ['fix', '--goal', 'g', '--checkout', str(tmp_path), '--scope', 'a.py',
                                    '--probe', 'p.json', '--finding-id', 'F1'])
    assert code == 2 and json.loads(out)['next_action'].startswith('Name the completed assessment')


def test_an_unknown_flag_stays_an_argparse_error(capsys):
    code, out, err = refused(capsys, ['fix', '--no-such-flag'])
    assert code == 2 and not out and 'unrecognized arguments' in err


def test_markdown_shows_a_refusal_that_exits(capsys):
    code, out, _ = refused(capsys, ['fix', '--goal', 'Repair', '--format', 'markdown'])
    assert code == 2 and out.startswith('## task-intake')
    assert '**Refused (UsageError):**' in out and '**Next:** See attune-harness fix --help' in out


def test_intake_failures_always_name_a_next_action(capsys, tmp_path):
    (tmp_path / 'participants.json').write_text('not json', encoding='utf-8')
    code = main(['review', '--goal', 'x', '--config', str(tmp_path / 'participants.json'),
                 '--task-dir', str(tmp_path / 'task'), '--intake-only'])
    envelope = json.loads(capsys.readouterr().out)
    assert code == 2 and envelope['next_action'].startswith('Inspect the error')


def test_control_failures_name_a_next_action(capsys, tmp_path):
    # A failing status is not told to run status again (T6 review).
    assert main(['status', str(tmp_path / 'absent')]) == 2
    assert json.loads(capsys.readouterr().out)['next_action'].startswith(f'Check that {tmp_path / "absent"}')
    assert main(['resume', str(tmp_path / 'absent')]) == 2
    assert 'attune-harness status' in json.loads(capsys.readouterr().out)['next_action']


def test_test_refusal_names_a_next_action(capsys, tmp_path):
    assert main(['test', '--task-dir', str(tmp_path / 'task')]) == 2
    envelope = json.loads(capsys.readouterr().out)
    assert envelope['status'] == 'blocked' and 'preview' in envelope['next_action']
