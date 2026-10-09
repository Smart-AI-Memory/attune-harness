"""Real retained-record journeys for opt-in consultation presentation."""
# qualify: platform

import json
import shlex

import pytest

from attune_harness import consultation as c
from attune_harness.consultation_output import evidence_view
from attune_harness.cli import main
from attune_harness.review_store import RunStore


def configuration(operation):
    participants = {'reviewer': {'adapter': 'command',
        'identity': {'provider': 'other', 'model': 'review-1'},
        'timeout': 10, 'command': ['never-launched']}}
    if operation == 'roundtable':
        participants['critic'] = {'adapter': 'command',
            'identity': {'provider': 'third', 'model': 'critic-1'},
            'timeout': 10, 'command': ['never-launched']}
    return {'schema_version': 1, 'question': 'Inspect frozen source',
            'author': {'provider': 'codex', 'model': 'gpt-6.1-sol'},
            'participants': participants, 'rounds': 1}


def prepare(tmp_path, operation):
    project = tmp_path / 'source'
    project.mkdir()
    (project / 'x.py').write_bytes(b'first = 1\nfrozen = 2\nlast = 3\n')
    config = tmp_path / 'config.json'
    config.write_text(json.dumps(configuration(operation)), encoding='utf-8')
    directory = tmp_path / 'a saved run'
    record = c.prepare(operation, project, ['x.py'], configuration(operation), directory)
    return project, directory, record, config


def complete(directory, record, failed=False):
    def offline(seat, *args):
        return {'status': 'failed' if failed else 'completed',
                'answer': None if failed else {'verdict': 'uncertain', 'summary': 'Inspect this claim',
                    'evidence': [{'path': 'x.py', 'line': 2, 'detail': 'A retained claim'}]},
                'identity': {'configured': seat['identity'],
                    'reported': {'provider': seat['identity']['provider'], 'reported_models': ['declared']},
                    'authenticated_model': False},
                'error': {'effects': 'unknown', 'detail': 'Seat timed out'} if failed else None,
                'process': None}
    return c.run(directory, record['contract_digest'], allow_external=True, dispatcher=offline)


def no_dispatch(*args, **kwargs):
    pytest.fail('A presentation command dispatched or resumed a consultation')


@pytest.mark.parametrize('operation', ['source-review', 'roundtable'])
@pytest.mark.parametrize('view', ['status', 'evidence'])
@pytest.mark.parametrize('failed', [False, True])
def test_json_bytes_exit_and_saved_record_stay_unchanged(tmp_path, capsys, monkeypatch, operation, view, failed):
    _, directory, prepared, _ = prepare(tmp_path, operation)
    record = complete(directory, prepared, failed)
    expected = record if view == 'status' else c.inspect_evidence(directory)
    original = (directory / 'record.json').read_bytes()
    monkeypatch.setattr(c, 'run', no_dispatch)
    args = [operation, view, str(directory)]
    expected_exit = 2 if failed else 0
    assert main(args) == expected_exit
    default = capsys.readouterr().out
    assert default == json.dumps(expected, indent=2, allow_nan=False) + '\n'
    assert main(args + ['--format', 'json']) == expected_exit
    assert capsys.readouterr().out == default
    assert main(args + ['--format', 'markdown']) == expected_exit
    readable = capsys.readouterr().out
    assert '**Turn status:** ' + ('failed' if failed else 'completed') in readable
    assert '**Authenticated model:** False' in readable
    assert ('Seat timed out' if failed else 'Inspect this claim') in readable
    assert (directory / 'record.json').read_bytes() == original
    assert c.load(directory)['checkpoint_digest'] == record['checkpoint_digest']


@pytest.mark.parametrize('operation', ['source-review', 'roundtable'])
@pytest.mark.parametrize('format_args', [[], ['--format', 'json'], ['--format', 'markdown']])
def test_prepare_persists_same_schema_no_dispatch_and_quotes_acceptance(tmp_path, capsys, monkeypatch, operation, format_args):
    project = tmp_path / 'source'; project.mkdir()
    (project / 'x.py').write_bytes('private = "é"\n'.encode('utf-8'))
    config = tmp_path / 'config.json'
    config.write_text(json.dumps(configuration(operation)), encoding='utf-8')
    directory = tmp_path / 'a saved run'
    monkeypatch.setattr(c, 'run', no_dispatch)
    assert main([operation, 'prepare', '--project', str(project), '--path', 'x.py',
                 '--config', str(config), '--run-dir', str(directory), *format_args]) == 0
    out = capsys.readouterr().out
    saved = c.load(directory)
    assert saved['events'] == saved['answers'] == []
    assert 'format' not in saved and 'format' not in saved['contract']
    if format_args == ['--format', 'markdown']:
        assert 'private =' not in out
        assert saved['contract_digest'] in out and saved['checkpoint_digest'] in out
        assert str(len('private = "é"\n'.encode('utf-8'))) + ' bytes' in out
        command = next(line for line in out.splitlines() if line.startswith('attune-harness '))
        assert shlex.split(command) == ['attune-harness', operation, 'run', '--accept',
                                       saved['contract_digest'], '--', str(directory)]
        assert '--allow-' not in command
    else:
        assert out == json.dumps(saved, indent=2, allow_nan=False) + '\n'


@pytest.mark.parametrize('operation', ['source-review', 'roundtable'])
@pytest.mark.parametrize('view', ['status', 'evidence'])
def test_assessed_citations_show_frozen_source_after_live_file_removed(tmp_path, capsys, monkeypatch, operation, view):
    project, directory, initial, _ = prepare(tmp_path, operation)
    done = complete(directory, initial)
    assessed = c.assess_citation(directory, done['checkpoint_digest'], 0, 'reviewer', 0,
                                'rejected', 'Frozen line does not establish that claim')
    (project / 'x.py').unlink()
    original = (directory / 'record.json').read_bytes()
    monkeypatch.setattr(c, 'run', no_dispatch)
    assert main([operation, view, str(directory), '--format', 'markdown']) == 0
    out = capsys.readouterr().out
    assert '1: first = 1\n2: frozen = 2\n3: last = 3' in out
    assert '**Support:** rejected (advisory host assessment)' in out
    assert 'Frozen line does not establish that claim' in out
    assert assessed['checkpoint_digest'] in out
    assert (directory / 'record.json').read_bytes() == original


@pytest.mark.parametrize('format_args', [[], ['--format', 'json'], ['--format', 'markdown']])
def test_mismatched_owner_refuses_with_same_exit_and_no_mutation(tmp_path, capsys, format_args):
    _, directory, _, _ = prepare(tmp_path, 'source-review')
    original = (directory / 'record.json').read_bytes()
    assert main(['roundtable', 'status', str(directory), *format_args]) == 2
    out = capsys.readouterr().out
    assert 'Command does not match the saved consultation' in out
    assert (directory / 'record.json').read_bytes() == original


@pytest.mark.parametrize('view', ['status', 'evidence'])
def test_unresolved_journal_is_not_hidden_by_readable_projection(tmp_path, capsys, view):
    _, directory, initial, _ = prepare(tmp_path, 'source-review')
    def interrupted(*args):
        raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        c.run(directory, initial['contract_digest'], allow_external=True, dispatcher=interrupted)
    before = (directory / 'record.json').read_bytes()
    assert main(['source-review', view, str(directory), '--format', 'markdown']) == 2
    out = capsys.readouterr().out
    assert '**Status:** unresolved' in out
    assert 'Unresolved journal entry' in out and 'effects remain unknown' in out
    assert 'No retained participant turns.' in out
    assert (directory / 'record.json').read_bytes() == before


def test_old_running_status_retains_persisted_status_and_checkpoint(tmp_path, capsys):
    _, directory, record, _ = prepare(tmp_path, 'source-review')
    record['status'] = 'running'
    RunStore(directory, existing=True).save(record)
    original = (directory / 'record.json').read_bytes()
    assert main(['source-review', 'status', str(directory), '--format', 'markdown']) == 2
    out = capsys.readouterr().out
    assert '**Status:** unresolved' in out and '**Persisted status:** running' in out
    assert (directory / 'record.json').read_bytes() == original


@pytest.mark.parametrize('operation', ['source-review', 'roundtable'])
def test_run_surface_does_not_accept_presentation_or_gain_authority(capsys, operation):
    with pytest.raises(SystemExit) as error:
        main([operation, 'run', 'unused', '--accept', 'a' * 64, '--format', 'markdown'])
    assert error.value.code == 2
    assert 'unrecognized arguments: --format markdown' in capsys.readouterr().err


def test_markdown_evidence_uses_one_snapshot_while_json_retains_original_route(tmp_path, capsys, monkeypatch):
    _, directory, initial, _ = prepare(tmp_path, 'source-review')
    done = complete(directory, initial)
    original_view = c.inspect_evidence(directory)
    assert evidence_view(done) == original_view
    inspected = []
    def concurrent_inspection(*args):
        inspected.append(True)
        return {**original_view, 'checkpoint_digest': 'newer-checkpoint', 'claims': []}
    monkeypatch.setattr(c, 'inspect_evidence', concurrent_inspection)
    assert main(['source-review', 'evidence', str(directory), '--format', 'markdown']) == 0
    out = capsys.readouterr().out
    assert not inspected
    assert done['checkpoint_digest'] in out and 'newer-checkpoint' not in out
    assert 'A retained claim' in out
    assert '**Support:** unchecked (no host assessment recorded)' in out
    assert main(['source-review', 'evidence', str(directory)]) == 0
    assert inspected == [True]
    assert json.loads(capsys.readouterr().out)['checkpoint_digest'] == 'newer-checkpoint'
