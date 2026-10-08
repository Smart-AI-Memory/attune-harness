"""Roundtable starter journey, explicit models and unchanged refusal/write boundaries."""
# qualify: platform

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import attune_harness
from attune_harness import init_cli
from attune_harness import consultation_preflight as p
from attune_harness.cli import main


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(p.shutil, 'which', lambda binary: None)
    monkeypatch.setattr(p, '_probe', lambda *args: pytest.fail('unexpected process'))


def init(capsys, project, *extra, models=True):
    arguments = ['init', '--for', 'roundtable', '--project', str(project),
                 '--question', 'Review the frozen source']
    if models:
        arguments += ['--model', 'claude=fixture-claude', '--model', 'codex=fixture-codex']
    code = main([*arguments, *extra])
    return code, json.loads(capsys.readouterr().out)


def test_written_config_prepares_unchanged_without_dispatch(tmp_path, capsys):
    project = tmp_path / 'source with spaces'
    project.mkdir()
    (project / 'example.py').write_text('x = 1\n')
    registry = project / 'participants.json'
    registry.write_text('retained registry\n')
    directory = tmp_path / 'run'
    code, result = init(capsys, project, '--scope', 'example.py', '--task-dir', str(directory), '--rounds', '2')
    assert code == 0 and result['status'] == 'created'
    target = project / 'roundtable.json'
    config = json.loads(target.read_text())
    assert config['author'] == config['participants']['claude']['identity']
    assert config['rounds'] == 2
    assert config['participants']['codex']['identity'] == {'provider': 'codex', 'model': 'fixture-codex'}
    assert result['files'] == [str(target)] and result['profile'] is None
    assert result['preflight']['claude']['state'] == 'missing_binary'
    assert result['requires'] == {'allow_external': True, 'allow_native': True}
    assert registry.read_text() == 'retained registry\n' and not directory.exists()
    code = main(['roundtable', 'prepare', '--project', str(project), '--path', 'example.py',
                 '--config', str(target), '--run-dir', str(directory)])
    prepared = json.loads(capsys.readouterr().out)
    assert code == 0 and prepared['status'] == 'prepared'
    record = json.loads((directory / 'record.json').read_text())
    assert record['contract']['configuration'] == config and record['events'] == []
    assert record['contract']['budget']['max_calls'] == 4


def test_missing_model_names_exact_flag_and_writes_nothing(tmp_path, capsys):
    code, result = init(capsys, tmp_path, '--model', 'claude=fixture-claude', models=False)
    assert code == 2
    assert '--model codex=YOUR_EXPLICIT_MODEL_ID' in result['error']['detail']
    assert not (tmp_path / 'roundtable.json').exists()
    assert not (tmp_path / 'participants.json').exists()


@pytest.mark.parametrize('extra,detail', [
    (['--seats', 'claude'], '--seats'),
    (['--seats', 'claude,claude'], '--seats'),
    (['--seats', 'claude,codex,command'], '--seats'),
    (['--model', 'claude=other'], '--model'),
    (['--model', 'unselected=fixture'], '--model'),
    (['--model', 'broken'], '--model'),
    (['--model', 'codex='], '--model'),
    (['--author', 'absent'], '--author'),
    (['--timeout', '0'], 'timeout'),
    (['--timeout', '301'], 'timeout'),
    (['--timeout', 'nan'], 'timeout'),
    (['--question', ''], 'question'),
    (['--question', 'x' * 8193], 'question'),
    (['--effort', 'codex=high'], '--effort'),
    (['--profile', 'claude'], '--profile'),
    (['--goal', 'other route'], '--goal'),
    (['--interpreter', 'python'], '--interpreter'),
    (['--tests', 'test.py'], '--tests'),
])
def test_invalid_inputs_refuse_before_probes_or_write(tmp_path, capsys, monkeypatch, extra, detail):
    monkeypatch.setattr(p.shutil, 'which', lambda *args: pytest.fail('invalid config probed'))
    code, result = init(capsys, tmp_path, *extra)
    assert code == 2 and detail in result['error']['detail']
    assert not (tmp_path / 'roundtable.json').exists()


def test_model_alias_is_rejected_by_prepare_validation(tmp_path, capsys):
    code, result = init(capsys, tmp_path, '--model', 'claude=opus', '--model', 'codex=fixture', models=False)
    assert code == 2 and 'explicit model identifier' in result['error']['detail']
    assert not (tmp_path / 'roundtable.json').exists()


def test_third_seat_needs_effort_then_validates_author_and_models(tmp_path, capsys):
    arguments = ['--seats', 'claude,codex,antigravity', '--model', 'antigravity=fixture-agy']
    code, result = init(capsys, tmp_path, *arguments)
    assert code == 2 and '--effort antigravity=high' in result['error']['detail']
    code, result = init(capsys, tmp_path, *arguments, '--effort', 'antigravity=max', '--author', 'codex')
    assert code == 0
    config = json.loads((tmp_path / 'roundtable.json').read_text())
    assert config['author'] == config['participants']['codex']['identity']
    assert config['participants']['antigravity'] == {
        'adapter': 'antigravity', 'identity': {'provider': 'google-antigravity', 'model': 'fixture-agy'},
        'timeout': 120, 'effort': 'max'}
    assert result['participants'] == ['claude', 'codex', 'antigravity']


def test_existing_config_force_and_backup_are_preserved(tmp_path, capsys):
    target = tmp_path / 'roundtable.json'
    target.write_text('old config\n')
    code, result = init(capsys, tmp_path)
    assert code == 2 and '--force' in result['error']['detail']
    assert target.read_text() == 'old config\n'
    code, result = init(capsys, tmp_path, '--force')
    assert code == 0 and result['replaced'] == str(tmp_path / 'roundtable.json.bak')
    assert (tmp_path / 'roundtable.json.bak').read_text() == 'old config\n'
    before = target.read_bytes()
    code, result = init(capsys, tmp_path, '--force')
    assert code == 2 and 'already exists' in result['error']['detail']
    assert target.read_bytes() == before


@pytest.mark.parametrize('error', [OSError('synthetic full disk'), KeyboardInterrupt()])
def test_failed_replacement_removes_its_backup_and_can_retry(tmp_path, capsys, monkeypatch, error):
    target, backup = tmp_path / 'roundtable.json', tmp_path / 'roundtable.json.bak'
    original = b'old config\n'
    target.write_bytes(original)
    with monkeypatch.context() as patch:
        def failed_write(*args, **kwargs):
            assert backup.read_bytes() == original
            raise error
        patch.setattr(init_cli, 'write_report', failed_write)
        if isinstance(error, KeyboardInterrupt):
            with pytest.raises(KeyboardInterrupt):
                init(capsys, tmp_path, '--force')
            capsys.readouterr()
        else:
            code, result = init(capsys, tmp_path, '--force')
            assert code == 2 and result['error']['detail'] == 'synthetic full disk'
    assert target.read_bytes() == original and not backup.exists()
    code, result = init(capsys, tmp_path, '--force')
    assert code == 0 and result['status'] == 'created'
    assert backup.read_bytes() == original


def test_preexisting_backup_is_never_removed_or_overwritten(tmp_path, capsys, monkeypatch):
    target, backup = tmp_path / 'roundtable.json', tmp_path / 'roundtable.json.bak'
    target.write_bytes(b'old config\n')
    backup.write_bytes(b'retained backup\n')
    monkeypatch.setattr(init_cli, 'write_report', lambda *args: pytest.fail('must refuse before write'))
    code, result = init(capsys, tmp_path, '--force')
    assert code == 2 and 'already exists' in result['error']['detail']
    assert target.read_bytes() == b'old config\n' and backup.read_bytes() == b'retained backup\n'


@pytest.mark.parametrize('name', ['-x', '-file with spaces.py', 'file with spaces.py'])
def test_actual_printed_command_prepares_dash_and_space_paths(tmp_path, capsys, name):
    project = tmp_path / 'source with spaces'
    project.mkdir()
    names = [name] if name.startswith('-') else [name, 'another file.py']
    for selected in names:
        (project / selected).write_text('selected synthetic source\n')
    directory = tmp_path / 'run with spaces'
    scope = [f'--scope={name}'] if name.startswith('-') else ['--scope', *names]
    code, result = init(capsys, project, *scope, '--task-dir', str(directory))
    assert code == 0
    config = (project / 'roundtable.json').read_bytes()
    # Execute the printed shell command unchanged through this test's actual
    # source/wheel CLI, not whichever daily tool happens to be on the host PATH.
    launchers = tmp_path / 'bin'
    launchers.mkdir()
    script = launchers / 'cli.py'
    package_root = str(Path(attune_harness.__file__).parent.parent)
    script.write_text(f'import sys\nsys.path.insert(0, {package_root!r})\n'
                      'from attune_harness.cli import main\nraise SystemExit(main())\n')
    if os.name == 'nt':
        launcher = launchers / 'attune-harness.cmd'
        launcher.write_text(f'@"{sys.executable}" "{script}" %*\n')
    else:
        launcher = launchers / 'attune-harness'
        launcher.write_text(f'#!/bin/sh\nexec {init_cli.quote(sys.executable)} '
                            f'{init_cli.quote(script)} "$@"\n')
        launcher.chmod(0o700)
    environment = {k: v for k, v in os.environ.items() if not k.startswith(
        ('ANTHROPIC_', 'CLAUDE_CODE_OAUTH', 'CLAUDE_CODE_USE_', 'AWS_', 'GOOGLE_', 'OPENAI_'))}
    environment.pop('PYTHONPATH', None)
    environment['PATH'] = str(launchers) + os.pathsep + environment.get('PATH', '')
    prepared = subprocess.run(result['next_action'], shell=True, cwd=tmp_path,
                              env=environment, capture_output=True, text=True, timeout=30)
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    assert json.loads(prepared.stdout)['status'] == 'prepared'
    record = json.loads((directory / 'record.json').read_text())
    assert record['events'] == [] and set(record['contract']['snapshot']['files']) == set(names)
    assert (project / 'roundtable.json').read_bytes() == config


def test_bad_run_location_refuses_without_writes(tmp_path, capsys):
    code, result = init(capsys, tmp_path, '--task-dir', str(tmp_path / 'run'))
    assert code == 2 and 'outside the source checkout' in result['error']['detail']
    assert not (tmp_path / 'roundtable.json').exists()
    code, result = init(capsys, tmp_path, '--task-dir', str(tmp_path.parent / 'absent-parent/run'))
    assert code == 2 and 'existing parent' in result['error']['detail']


@pytest.mark.parametrize('extra', [['--question', 'text'], ['--model', 'claude=fixture'],
                                  ['--rounds', '1'], ['--timeout', '120'], ['--seats', 'claude,codex']])
def test_roundtable_flags_do_not_silently_change_other_init_routes(tmp_path, capsys, extra):
    code = main(['init', '--project', str(tmp_path), *extra])
    result = json.loads(capsys.readouterr().out)
    assert code == 2 and '--for roundtable' in result['error']['detail']
    assert not (tmp_path / 'participants.json').exists()
