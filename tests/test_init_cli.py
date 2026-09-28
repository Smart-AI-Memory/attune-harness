"""``attune-harness init`` and the refusals that name it (first-run journey T3, R1 and R2)."""
# qualify: platform

import json
from pathlib import Path

import pytest

from attune_harness.cli import main
from attune_harness.init_cli import PROFILES, RegistryMissing, require_registry
from attune_harness.review_contract import load_registry


def run(capsys, *argv):
    code = main(list(argv))
    return code, json.loads(capsys.readouterr().out)


@pytest.mark.parametrize('profile', sorted(PROFILES))
def test_each_profile_writes_a_registry_the_reader_accepts(tmp_path, capsys, profile):
    code, envelope = run(capsys, 'init', '--profile', profile, '--project', str(tmp_path))
    assert code == 0 and envelope['status'] == 'created', envelope
    target = tmp_path / 'participants.json'
    assert envelope['path'] == str(target) and envelope['replaced'] is None
    registry = load_registry(target)
    assert sorted(registry['participants']) == envelope['participants'] == ['lead', 'reviewer']
    native = profile != 'demo'
    assert envelope['requires'] == {'allow_external': native, 'allow_native': native}
    assert ('may incur provider costs' in envelope['next_action']) is native
    if native:
        models = {item['model'] for item in registry['participants'].values()}
        assert len(models) == 2, 'a required native review needs a different model'


def test_default_is_the_offline_demo_in_the_current_directory(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, envelope = run(capsys, 'init')
    assert code == 0 and envelope['profile'] == 'demo'
    adapters = {item['adapter'] for item in load_registry(tmp_path / 'participants.json')['participants'].values()}
    assert adapters == {'deterministic'}


def test_an_existing_registry_is_refused_unchanged(tmp_path, capsys):
    target = tmp_path / 'participants.json'
    target.write_text('{"kept": true}\n', encoding='utf-8')
    code, envelope = run(capsys, 'init', '--project', str(tmp_path))
    assert code == 2 and envelope['status'] == 'failed', envelope
    assert '--force' in envelope['error']['detail'] and envelope['next_action']
    assert target.read_text(encoding='utf-8') == '{"kept": true}\n'


def test_force_keeps_the_old_registry_as_a_backup(tmp_path, capsys):
    target = tmp_path / 'participants.json'
    target.write_text('{"kept": true}\n', encoding='utf-8')
    code, envelope = run(capsys, 'init', '--project', str(tmp_path), '--force')
    assert code == 0 and envelope['replaced'] == str(tmp_path / 'participants.json.bak')
    assert (tmp_path / 'participants.json.bak').read_text(encoding='utf-8') == '{"kept": true}\n'
    load_registry(target)


def test_force_never_overwrites_an_earlier_backup(tmp_path, capsys):
    (tmp_path / 'participants.json').write_text('{"current": true}\n', encoding='utf-8')
    (tmp_path / 'participants.json.bak').write_text('{"older": true}\n', encoding='utf-8')
    code, envelope = run(capsys, 'init', '--project', str(tmp_path), '--force')
    assert code == 2 and 'already exists' in envelope['error']['detail']
    assert (tmp_path / 'participants.json').read_text(encoding='utf-8') == '{"current": true}\n'
    assert (tmp_path / 'participants.json.bak').read_text(encoding='utf-8') == '{"older": true}\n'


def test_a_missing_project_is_refused(tmp_path, capsys):
    code, envelope = run(capsys, 'init', '--project', str(tmp_path / 'absent'))
    assert code == 2 and 'not a directory' in envelope['error']['detail']
    assert not (tmp_path / 'absent').exists()


def test_require_registry_names_init_only_when_the_file_is_absent(tmp_path):
    with pytest.raises(RegistryMissing) as missing:
        require_registry(tmp_path / 'participants.json', tmp_path)
    assert 'attune-harness init --project' in missing.value.next_action
    assert str(tmp_path) in missing.value.next_action
    # A present file, valid or not, is left to the registry reader and its own words.
    (tmp_path / 'participants.json').write_text('not json', encoding='utf-8')
    require_registry(tmp_path / 'participants.json', tmp_path)


def test_review_intake_without_a_registry_names_init(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    code, envelope = run(capsys, 'review', '--goal', 'Check the guide', '--task-dir', str(tmp_path / 'task'))
    assert code == 2 and envelope['operation'] == 'task-intake'
    assert envelope['error'] == {'type': 'RegistryMissing',
                                 'detail': f'No participant registry at {tmp_path / "participants.json"} '
                                           "(--config 'participants.json' resolves against the working directory)"}
    assert 'attune-harness init' in envelope['next_action']
    assert not (tmp_path / 'task').exists()


def test_plan_without_a_project_or_config_names_both(tmp_path, capsys):
    (tmp_path / 'request.json').write_text('{}', encoding='utf-8')
    code = main(['plan', '--task-dir', str(tmp_path / 'task'), '--request', str(tmp_path / 'request.json')])
    envelope = json.loads(capsys.readouterr().out)
    assert code == 2 and envelope['next_action'].startswith('Pass --project with the project directory. ')
    assert 'attune-harness init' in envelope['next_action']


def test_plan_without_a_config_names_init(tmp_path, capsys):
    (tmp_path / 'request.json').write_text('{}', encoding='utf-8')
    code = main(['plan', '--task-dir', str(tmp_path / 'task'), '--request', str(tmp_path / 'request.json'),
                 '--project', str(tmp_path)])
    envelope = json.loads(capsys.readouterr().out)
    # The detail keeps its pinned words; the next action is what names init.
    assert code == 2 and envelope['error'] == {
        'type': 'ValueError', 'detail': 'New work requires --project and --config, without an old checkpoint'}
    assert 'attune-harness init' in envelope['next_action']
    assert not (tmp_path / 'task').exists()


def test_an_absolute_config_is_not_said_to_resolve(tmp_path, capsys):
    """Only a relative --config resolves against the working directory (T4 review)."""
    absent = tmp_path / 'elsewhere' / 'participants.json'
    code, envelope = run(capsys, 'review', '--goal', 'Check the guide', '--config', str(absent),
                         '--task-dir', str(tmp_path / 'task'))
    assert code == 2 and envelope['error']['detail'] == f'No participant registry at {absent}'
