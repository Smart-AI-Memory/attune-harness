"""``attune-harness init`` and the refusals that name it (first-run journey T3, R1 and R2)."""
# qualify: platform

import json
from pathlib import Path

import pytest

from attune_harness.cli import main
from attune_harness.init_cli import PROFILES, RegistryMissing, quote, require_registry
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
    assert ('review with native participants needs --allow-external;' in envelope['next_action']) is native
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


# Starter files T2: init --for fix writes the probe fix reads (R1).

import os
import subprocess
import sys

from attune_harness import repair

POSIX_ONLY = pytest.mark.skipif(os.name != 'posix', reason='fix qualifies the POSIX repair profile only')


def checkout(root):
    """A committed checkout whose one test fails; running it would leave ``ran.txt``."""
    root.mkdir()
    (root / 'tests').mkdir()
    (root / 'calc.py').write_text('def add(a, b):\n    return a - b\n', encoding='utf-8')
    (root / 'tests' / 'test_calc.py').write_text(
        'import pathlib\npathlib.Path("ran.txt").write_text("ran")\nfrom calc import add\n\n\n'
        'def test_add():\n    assert add(2, 2) == 4\n', encoding='utf-8')
    git = ['git', '-C', str(root), '-c', 'commit.gpgsign=false', '-c', 'user.name=T', '-c', 'user.email=t@example.invalid']
    subprocess.run(['git', 'init', '-q', str(root)], check=True, capture_output=True)
    subprocess.run([*git, 'add', '.'], check=True, capture_output=True)
    subprocess.run([*git, 'commit', '-qm', 'baseline'], check=True, capture_output=True)
    return root


def init_fix(capsys, root, *extra, scope=('calc.py',), tests=('tests/test_calc.py',), python=sys.executable):
    return run(capsys, 'init', '--for', 'fix', '--project', str(root), '--scope', *scope,
               '--interpreter', str(python), '--tests', *tests, *extra)


def test_for_fix_writes_the_registry_and_a_probe_the_owner_accepts(tmp_path, capsys):
    root = checkout(tmp_path.resolve() / 'repo')
    code, envelope = init_fix(capsys, root)
    assert code == 0 and envelope['status'] == 'created', envelope
    registry, probe_path = root / 'participants.json', root / 'probe.json'
    assert envelope['files'] == [str(registry), str(probe_path)]
    assert envelope['path'] == str(registry) and envelope['profile'] == 'demo' and envelope['replaced'] is None
    probe = json.loads(probe_path.read_text(encoding='utf-8'))
    assert probe['argv'] == [str(Path(sys.executable).absolute()), '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                             'tests/test_calc.py']
    assert probe['cwd'] == '.' and probe['oracle_paths'] == ['tests/test_calc.py']
    repair.validate_probe(root, ['calc.py'], probe, windows_profile=os.name == 'nt')
    assert not (root / 'ran.txt').exists(), 'init must not run the probe (Q4)'


def test_for_fix_leaves_an_existing_registry_alone(tmp_path, capsys):
    root = checkout(tmp_path.resolve() / 'repo')
    run(capsys, 'init', '--project', str(root))
    before = (root / 'participants.json').read_bytes()
    code, envelope = init_fix(capsys, root)
    assert code == 0 and envelope['files'] == [str(root / 'probe.json')], envelope
    assert envelope['profile'] is None and envelope['participants'] == ['lead', 'reviewer']
    assert (root / 'participants.json').read_bytes() == before


def test_an_existing_probe_needs_force_and_keeps_a_backup(tmp_path, capsys):
    root = checkout(tmp_path.resolve() / 'repo')
    (root / 'probe.json').write_text('{"old": true}', encoding='utf-8')
    code, envelope = init_fix(capsys, root)
    assert code == 2 and 'pass --force to replace it' in envelope['error']['detail'], envelope
    assert (root / 'probe.json').read_text(encoding='utf-8') == '{"old": true}'
    code, envelope = init_fix(capsys, root, '--force')
    assert code == 0 and envelope['replaced'] == str(root / 'probe.json.bak'), envelope
    assert (root / 'probe.json.bak').read_text(encoding='utf-8') == '{"old": true}'
    code, envelope = init_fix(capsys, root, '--force')
    assert code == 2 and 'move it before replacing the probe' in envelope['error']['detail'], envelope


@pytest.mark.parametrize('case, detail', [
    ('oracle-in-scope', 'Acceptance oracle cannot be in replacement scope'),
    ('interpreter-inside', 'Probe executable must be outside editable checkout'),
    ('missing-interpreter', 'Probe requires a bounded argv with an existing absolute executable'),
    ('missing-scope', 'Accepted paths must be existing regular files'),
    ('protected-scope', 'Protected state/metadata cannot be replaced'),
    ('not-a-checkout', 'Repair requires a dedicated checkout with local .git directory'),
    pytest.param('hard-link', 'Repair requires bounded regular files with one hard link', marks=POSIX_ONLY),
    pytest.param('bare-name-not-on-path', 'Interpreter not found on PATH: no-such-python-here', marks=POSIX_ONLY),
])
def test_what_the_owner_refuses_is_refused_in_its_words(tmp_path, capsys, case, detail):
    root = checkout(tmp_path.resolve() / 'repo')
    options = {}
    if case == 'oracle-in-scope':
        options['scope'] = ('calc.py', 'tests/test_calc.py')
    elif case == 'interpreter-inside':
        (root / 'python').write_bytes(Path(sys.executable).read_bytes()[:16])
        options['python'] = root / 'python'
    elif case == 'missing-interpreter':
        options['python'] = tmp_path / 'no-such-python'
    elif case == 'missing-scope':
        options['scope'] = ('absent.py',)
    elif case == 'protected-scope':
        options['scope'] = ('.git/config',)
    elif case == 'hard-link':
        os.link(root / 'calc.py', tmp_path / 'second-name.py')
    elif case == 'bare-name-not-on-path':
        options['python'] = 'no-such-python-here'
    else:
        import shutil
        shutil.rmtree(root / '.git')
    code, envelope = init_fix(capsys, root, **options)
    assert code == 2 and envelope['error']['detail'] == detail, envelope
    assert not (root / 'probe.json').exists() and not (root / 'participants.json').exists()


def test_for_fix_needs_its_three_options_and_they_need_it(tmp_path, capsys):
    root = checkout(tmp_path.resolve() / 'repo')
    code, envelope = run(capsys, 'init', '--for', 'fix', '--project', str(root), '--scope', 'calc.py')
    assert code == 2 and envelope['error']['detail'] == 'init --for fix needs --scope, --interpreter and --tests'
    code, envelope = run(capsys, 'init', '--project', str(root), '--scope', 'calc.py')
    assert code == 2 and envelope['error']['detail'] == '--scope, --interpreter and --tests need --for fix'
    assert not (root / 'participants.json').exists()


def test_for_and_force_are_distinct_options(tmp_path, capsys):
    """Before --for existed, argparse read ``--for`` as an abbreviation of ``--force``."""
    from attune_harness.cli import build_parser
    args = build_parser().parse_args(['init', '--for', 'fix'])
    assert args.starter == 'fix' and args.force is False
    args = build_parser().parse_args(['init', '--force'])
    assert args.starter is None and args.force is True


def test_without_for_the_envelope_is_unchanged(tmp_path, capsys):
    code, envelope = run(capsys, 'init', '--project', str(tmp_path))
    assert code == 0 and list(envelope) == ['schema_version', 'operation', 'status', 'path', 'profile',
                                            'participants', 'requires', 'replaced', 'next_action']


def test_a_bare_interpreter_name_is_found_on_path(tmp_path, capsys, monkeypatch):
    root = checkout(tmp_path.resolve() / 'repo')
    monkeypatch.setenv('PATH', str(Path(sys.executable).parent) + os.pathsep + os.environ.get('PATH', ''))
    code, envelope = init_fix(capsys, root, python=Path(sys.executable).name)
    assert code == 0, envelope
    argv0 = json.loads((root / 'probe.json').read_text(encoding='utf-8'))['argv'][0]
    assert Path(argv0).is_absolute() and Path(argv0).name == Path(sys.executable).name


@POSIX_ONLY
def test_the_next_action_previews_the_repair_as_printed(tmp_path, capsys, monkeypatch):
    import shlex
    root = checkout(tmp_path.resolve() / 'repo')
    monkeypatch.setenv('HOME', str(tmp_path.resolve() / 'home'))
    code, envelope = init_fix(capsys, root)
    command = envelope['next_action'].split(': ', 1)[1].split('. Accepting it', 1)[0]
    assert str(tmp_path.resolve() / 'home' / 'harness-tasks' / 'repo-fix') in command
    code, preview = run(capsys, *shlex.split(command)[1:])
    assert code == 1 and preview['status'] == 'draft', preview


# The review of T2: what init accepts, the fix it prints accepts too.

def preview(capsys, envelope):
    import shlex
    command = envelope['next_action'].split(': ', 1)[1].split('. Accepting it', 1)[0]
    return run(capsys, *shlex.split(command)[1:])


@POSIX_ONLY
def test_a_symlinked_project_is_written_resolved_and_previews(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path.resolve() / 'home'))
    real = checkout(tmp_path.resolve() / 'real')
    (tmp_path / 'link').symlink_to(real, target_is_directory=True)
    code, envelope = init_fix(capsys, tmp_path / 'link')
    assert code == 0 and envelope['files'] == [str(real / 'participants.json'), str(real / 'probe.json')], envelope
    code, draft = preview(capsys, envelope)
    assert code == 1 and draft['status'] == 'draft', draft


@POSIX_ONLY
def test_a_symlinked_home_gives_a_task_directory_fix_accepts(tmp_path, capsys, monkeypatch):
    (tmp_path / 'real-home').mkdir()
    (tmp_path / 'home').symlink_to(tmp_path / 'real-home', target_is_directory=True)
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    root = checkout(tmp_path.resolve() / 'repo')
    code, envelope = init_fix(capsys, root)
    assert str(tmp_path.resolve() / 'real-home' / 'harness-tasks' / 'repo-fix') in envelope['next_action']
    code, draft = preview(capsys, envelope)
    assert code == 1 and draft['status'] == 'draft', draft


def test_the_task_directory_is_never_inside_the_checkout(tmp_path, capsys, monkeypatch):
    root = checkout(tmp_path.resolve() / 'repo')
    monkeypatch.setenv('HOME', str(root))
    monkeypatch.setenv('USERPROFILE', str(root))
    code, envelope = init_fix(capsys, root)
    assert code == 0 and quote(tmp_path.resolve() / 'repo-fix-task') in envelope['next_action'], envelope


@POSIX_ONLY
def test_a_one_participant_registry_previews_without_review(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path.resolve() / 'home'))
    root = checkout(tmp_path.resolve() / 'repo')
    (root / 'participants.json').write_text(json.dumps({'schema_version': 1, 'participants': {
        'solo': PROFILES['demo']['lead']}}), encoding='utf-8')
    code, envelope = init_fix(capsys, root)
    assert code == 0 and envelope['participants'] == ['solo'], envelope
    assert '--worker solo --review none' in envelope['next_action']
    code, draft = preview(capsys, envelope)
    assert code == 1 and draft['status'] == 'draft', draft


@POSIX_ONLY
def test_a_scope_name_with_a_space_survives_the_printed_command(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path.resolve() / 'home'))
    root = checkout(tmp_path.resolve() / 'repo')
    (root / 'my calc.py').write_text('X = 1\n', encoding='utf-8')
    subprocess.run(['git', '-C', str(root), 'add', 'my calc.py'], check=True, capture_output=True)
    subprocess.run(['git', '-C', str(root), '-c', 'commit.gpgsign=false', '-c', 'user.name=T',
                    '-c', 'user.email=t@example.invalid', 'commit', '-qm', 'x'], check=True, capture_output=True)
    code, envelope = init_fix(capsys, root, scope=('my calc.py',))
    assert code == 0, envelope
    code, draft = preview(capsys, envelope)
    assert code == 1 and draft['status'] == 'draft', draft


def test_requires_names_native_participants_in_a_kept_registry(tmp_path, capsys):
    root = checkout(tmp_path.resolve() / 'repo')
    run(capsys, 'init', '--profile', 'claude', '--project', str(root))
    code, envelope = init_fix(capsys, root)
    assert code == 0 and envelope['requires'] == {'allow_external': True, 'allow_native': True}, envelope


def test_force_refuses_a_probe_that_is_not_a_regular_file(tmp_path, capsys):
    root = checkout(tmp_path.resolve() / 'repo')
    (root / 'probe.json').mkdir()
    code, envelope = init_fix(capsys, root, '--force')
    assert code == 2 and envelope['error']['detail'] == f'Not a regular file: {root / "probe.json"}', envelope


@POSIX_ONLY
def test_the_probe_environment_is_the_frozen_minimum(tmp_path, capsys):
    root = checkout(tmp_path.resolve() / 'repo')
    init_fix(capsys, root)
    probe = json.loads((root / 'probe.json').read_text(encoding='utf-8'))
    assert probe['environment'] == {'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1', 'PATH': '/usr/bin:/bin'}



def test_the_printed_worker_is_lead_even_when_it_does_not_sort_first(tmp_path, capsys):
    root = checkout(tmp_path.resolve() / 'repo')
    (root / 'participants.json').write_text(json.dumps({'schema_version': 1, 'participants': {
        'alpha': PROFILES['demo']['reviewer'], 'lead': PROFILES['demo']['lead']}}), encoding='utf-8')
    code, envelope = init_fix(capsys, root)
    assert code == 0 and '--worker lead --reviewer alpha --review required' in envelope['next_action'], envelope
