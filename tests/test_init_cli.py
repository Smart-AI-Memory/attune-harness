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
    git = ['git', '-C', str(root), '-c', 'commit.gpgsign=false', '-c', 'maintenance.auto=false',
           '-c', 'user.name=T', '-c', 'user.email=t@example.invalid']
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
    # The Windows repair backend names its own profile.
    ('missing-scope', f'Accepted {"Windows " if os.name == "nt" else ""}paths must be existing regular files'),
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
        # Renamed, not deleted: Git's read-only objects and background maintenance race a delete.
        (root / '.git').rename(root.parent / 'moved-git')
    code, envelope = init_fix(capsys, root, **options)
    assert code == 2 and envelope['error']['detail'] == detail, envelope
    assert not (root / 'probe.json').exists() and not (root / 'participants.json').exists()


def test_for_fix_needs_its_three_options_and_they_need_it(tmp_path, capsys):
    root = checkout(tmp_path.resolve() / 'repo')
    code, envelope = run(capsys, 'init', '--for', 'fix', '--project', str(root), '--scope', 'calc.py')
    assert code == 2 and envelope['error']['detail'] == 'init --for fix needs --scope, --interpreter and --tests'
    code, envelope = run(capsys, 'init', '--project', str(root), '--scope', 'calc.py')
    assert code == 2 and envelope['error']['detail'] == '--scope, --interpreter, --tests, --goal and --task-dir need --for'
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


def test_the_files_init_writes_count_against_the_entry_bound(tmp_path, capsys, monkeypatch):
    from attune_harness import init_cli
    root = checkout(tmp_path.resolve() / 'repo')
    entries = len(repair.freeze(root, ['calc.py'], json.loads(json.dumps({
        'argv': [sys.executable, '-m', 'pytest'], 'cwd': '.', 'timeout': 30, 'max_output_bytes': 8192,
        'environment': {'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1',
                        **({'SystemRoot': os.environ.get('SystemRoot', r'C:\Windows')} if os.name == 'nt' else {})},
        'oracle_paths': ['tests/test_calc.py']})), tmp_path.resolve() / 'state')['before'])
    monkeypatch.setattr(init_cli, 'MAX_ENTRIES', entries + 1)  # room for one new file, not two
    code, envelope = init_fix(capsys, root)
    assert code == 2 and envelope['error']['detail'] == 'Checkout exceeds bounded repair profile', envelope
    assert not (root / 'probe.json').exists() and not (root / 'participants.json').exists()
    monkeypatch.setattr(init_cli, 'MAX_ENTRIES', entries + 2)  # exactly at the bound is allowed
    code, envelope = init_fix(capsys, root)
    assert code == 0, envelope


def test_a_task_directory_that_would_contain_the_checkout_is_not_used(tmp_path, capsys, monkeypatch):
    home = tmp_path.resolve() / 'home'
    root = checkout_at = home / 'harness-tasks' / 'repo-fix' / 'repo'
    checkout_at.parent.mkdir(parents=True)
    checkout(root)
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('USERPROFILE', str(home))
    code, envelope = init_fix(capsys, root)
    assert code == 0 and quote(root.parent / 'repo-fix-task') in envelope['next_action'], envelope


@POSIX_ONLY
def test_a_dangling_registry_link_is_refused_not_replaced(tmp_path, capsys):
    root = checkout(tmp_path.resolve() / 'repo')
    (root / 'participants.json').symlink_to(tmp_path / 'nowhere.json')
    code, envelope = init_fix(capsys, root)
    assert code == 2 and (root / 'participants.json').is_symlink(), envelope
    assert not (root / 'probe.json').exists()


# Starter files T3: init --for plan writes a frozen work request (R2).

# The Windows effects backend names its own profile.
MISSING_TEST = ('Windows protected inputs must be existing files' if os.name == 'nt'
                else 'Protected acceptance inputs must already exist')


def init_plan(capsys, root, tasks, *extra, goal='Repair addition', scope=('calc.py',),
              tests=('tests/test_calc.py',), python=sys.executable):
    task_dir = () if tasks is None else ('--task-dir', str(tasks))
    return run(capsys, 'init', '--for', 'plan', '--goal', goal, '--project', str(root), '--scope', *scope,
               '--interpreter', str(python), '--tests', *tests, *task_dir, *extra)


def preview_work(capsys, envelope):
    import shlex
    command = envelope['next_action'].split(': ', 1)[1].split('. Writing the request', 1)[0]
    return run(capsys, *shlex.split(command)[1:])


@POSIX_ONLY
def test_for_plan_writes_a_request_beside_the_task_directory_that_previews_and_accepts(tmp_path, capsys):
    root, tasks = checkout(tmp_path.resolve() / 'repo'), tmp_path.resolve() / 'tasks' / 'starter-plan'
    code, envelope = init_plan(capsys, root, tasks)
    assert code == 0 and envelope['status'] == 'created', envelope
    request_path = tmp_path.resolve() / 'tasks' / 'starter-plan.work.json'
    assert envelope['files'] == [str(root / 'participants.json'), str(request_path)]
    assert envelope['path'] == str(root / 'participants.json') and envelope['replaced'] is None
    assert not tasks.exists(), 'plan makes the task directory; init only names it'
    assert not (root / 'ran.txt').exists(), 'init must not run the probe (Q4)'
    request = json.loads(request_path.read_text(encoding='utf-8'))
    assert request['intent'] == {'goal': 'Repair addition', 'context': [], 'scope': ['calc.py'], 'constraints': [],
                                 'acceptance': ['tests/test_calc.py passes'], 'questions': []}
    assert {a['role']: a['participant'] for a in request['assignments']} == {
        'planner': 'lead', 'worker': 'lead', 'reviewer': 'reviewer'}
    assert request['tasks'] == [{'id': 'change', 'objective': 'Repair addition', 'dependencies': [],
                                 'outputs': ['calc.py'], 'checks': ['tests/test_calc.py passes']}]
    assert request['inputs'] == ['calc.py'] and request['controls'] == []
    from attune_harness.work_contract import SIGNALS
    assert request['signals'] == {**dict.fromkeys(SIGNALS, False), 'existing_artifact': None}
    assert request['budget'] == {'max_operations': 100, 'max_attempts': 1, 'max_output_bytes': 32768}
    effects = request['effects']
    assert effects['root'] == str(root) and effects['allowed'] == ['calc.py']
    assert effects['protected'] == ['tests/test_calc.py'] and effects['parents'] == []
    assert [check['task_id'] for check in effects['verification']] == ['change', 'final']
    assert 'participants.json' in effects['before'], 'the registry is written before the freeze'
    code, draft = preview_work(capsys, envelope)
    assert code == 0 and draft['status'] == 'draft' and not draft['questions']['missing'], draft
    code, accepted = run(capsys, 'plan', '--task-dir', str(tasks), '--accept', '--checkpoint', draft['checkpoint_digest'])
    assert code == 0 and accepted['status'] == 'accepted', accepted
    assert 'readiness_error' not in accepted, 'build preflight accepts the request'


@POSIX_ONLY
def test_a_new_file_in_a_new_directory_is_authorized_with_its_parents(tmp_path, capsys):
    root, tasks = checkout(tmp_path.resolve() / 'repo'), tmp_path.resolve() / 'tasks' / 'new'
    code, envelope = init_plan(capsys, root, tasks, scope=('calc.py', 'pkg/sub/extra.py'))
    assert code == 0, envelope
    request = json.loads(Path(envelope['files'][-1]).read_text(encoding='utf-8'))
    assert request['effects']['parents'] == ['pkg', 'pkg/sub'] and request['inputs'] == ['calc.py']
    code, draft = preview_work(capsys, envelope)
    assert code == 0 and draft['status'] == 'draft', draft


def test_the_default_task_directory_is_under_home_and_outside_the_checkout(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    monkeypatch.setenv('USERPROFILE', str(tmp_path / 'home'))  # Path.home() on Windows
    root = checkout(tmp_path.resolve() / 'repo')
    code, envelope = init_plan(capsys, root, None)
    assert code == 0, envelope
    tasks = tmp_path.resolve() / 'home' / 'harness-tasks' / 'repo-plan'
    assert envelope['files'][-1] == str(tasks.with_name('repo-plan.work.json'))
    assert f'--task-dir {quote(tasks)}' in envelope['next_action']


@pytest.mark.parametrize('case, detail', [
    ('oracle-in-scope', 'Acceptance oracle cannot be in replacement scope'),
    ('interpreter-inside', 'Probe executable must be outside editable checkout'),
    ('missing-test', MISSING_TEST),
    ('not-a-checkout', 'Build effects require a dedicated local Git checkout'),
    ('task-dir-inside', 'Effect checkout and task state must be disjoint'),
    ('task-dir-exists', 'Task directory already exists: {tasks}; plan needs a new one, so choose another --task-dir'),
    ('one-participant', 'Registry requires 2–16 participants'),
    ('empty-goal', 'init --for plan needs --goal, --scope, --interpreter and --tests'),
])
def test_what_plan_and_build_refuse_is_refused_and_nothing_is_left(tmp_path, capsys, case, detail):
    root, tasks = checkout(tmp_path.resolve() / 'repo'), tmp_path.resolve() / 'tasks' / 'refused'
    options = {}
    if case == 'oracle-in-scope':
        options['scope'] = ('calc.py', 'tests/test_calc.py')
    elif case == 'interpreter-inside':
        (root / 'python').write_bytes(Path(sys.executable).read_bytes()[:16])
        options['python'] = root / 'python'
    elif case == 'missing-test':
        options['tests'] = ('tests/test_absent.py',)
    elif case == 'not-a-checkout':
        (root / '.git').rename(root.parent / 'moved-git')  # see the fix refusals above
    elif case == 'task-dir-inside':
        tasks = root / 'tasks'
    elif case == 'task-dir-exists':
        tasks.mkdir(parents=True)
    elif case == 'one-participant':
        (root / 'participants.json').write_text(json.dumps(
            {'schema_version': 1, 'participants': {'lead': PROFILES['demo']['lead']}}), encoding='utf-8')
    elif case == 'empty-goal':
        options['goal'] = ''
    kept = (root / 'participants.json').read_bytes() if case == 'one-participant' else None
    code, envelope = init_plan(capsys, root, tasks, **options)
    assert code == 2 and envelope['error']['detail'].startswith(detail.format(tasks=tasks)), envelope
    assert not tasks.with_name(tasks.name + '.work.json').exists()
    if kept is None:
        assert not (root / 'participants.json').exists(), 'a refused init removes the registry it wrote'
    else:
        assert (root / 'participants.json').read_bytes() == kept


def test_an_existing_request_needs_force_and_keeps_a_backup(tmp_path, capsys):
    root, tasks = checkout(tmp_path.resolve() / 'repo'), tmp_path.resolve() / 'tasks' / 'again'
    tasks.parent.mkdir()
    request_path = tasks.with_name('again.work.json')
    request_path.write_text('{"old": true}', encoding='utf-8')
    code, envelope = init_plan(capsys, root, tasks)
    assert code == 2 and 'pass --force to replace it' in envelope['error']['detail'], envelope
    assert not (root / 'participants.json').exists()
    code, envelope = init_plan(capsys, root, tasks, '--force')
    assert code == 0 and envelope['replaced'] == str(request_path) + '.bak', envelope
    assert Path(envelope['replaced']).read_text(encoding='utf-8') == '{"old": true}'


def test_for_plan_needs_its_options_and_fix_refuses_plans_options(tmp_path, capsys):
    root = checkout(tmp_path.resolve() / 'repo')
    code, envelope = run(capsys, 'init', '--for', 'plan', '--project', str(root), '--scope', 'calc.py')
    assert code == 2 and envelope['error']['detail'] == 'init --for plan needs --goal, --scope, --interpreter and --tests'
    code, envelope = init_fix(capsys, root, '--goal', 'Repair addition')
    assert code == 2 and envelope['error']['detail'] == '--goal and --task-dir need --for plan', envelope
    code, envelope = run(capsys, 'init', '--project', str(root), '--goal', 'Repair addition')
    assert code == 2 and 'need --for' in envelope['error']['detail'], envelope
    assert not (root / 'participants.json').exists() and not (root / 'probe.json').exists()


@pytest.mark.parametrize('names, worker, reviewer', [
    (('alpha', 'lead', 'reviewer'), 'lead', 'reviewer'),
    (('alpha', 'beta', 'reviewer'), 'alpha', 'reviewer'),
    (('alpha', 'beta', 'gamma'), 'alpha', 'beta'),
])
def test_lead_and_reviewer_are_preferred_then_the_sorted_order(tmp_path, capsys, names, worker, reviewer):
    root, tasks = checkout(tmp_path.resolve() / 'repo'), tmp_path.resolve() / 'tasks' / 'choice'
    registry = {'schema_version': 1, 'participants': {name: PROFILES['demo']['lead'] for name in names}}
    (root / 'participants.json').write_text(json.dumps(registry), encoding='utf-8')
    code, envelope = init_plan(capsys, root, tasks)
    assert code == 0, envelope
    request = json.loads(tasks.with_name('choice.work.json').read_text(encoding='utf-8'))
    assert {a['role']: a['participant'] for a in request['assignments']} == {
        'planner': worker, 'worker': worker, 'reviewer': reviewer}


def test_a_refusal_never_removes_a_registry_init_did_not_write(tmp_path, capsys):
    root, tasks = checkout(tmp_path.resolve() / 'repo'), tmp_path.resolve() / 'tasks' / 'kept'
    run(capsys, 'init', '--project', str(root))
    before = (root / 'participants.json').read_bytes()
    code, envelope = init_plan(capsys, root, tasks, tests=('tests/test_absent.py',))
    assert code == 2 and envelope['error']['detail'] == MISSING_TEST, envelope
    assert (root / 'participants.json').read_bytes() == before


@pytest.mark.parametrize('case', [
    'backup-exists', 'request-is-a-directory',
    pytest.param('request-is-a-dangling-link', marks=POSIX_ONLY),
    'parent-is-a-file',
    pytest.param('parent-is-unwritable', marks=POSIX_ONLY),
    'over-the-read-limit', 'preflight-refuses',
])
def test_every_refusal_after_the_registry_is_written_removes_it(tmp_path, capsys, monkeypatch, case):
    root, tasks = checkout(tmp_path.resolve() / 'repo'), tmp_path.resolve() / 'tasks' / 'late'
    request_path, extra = tasks.with_name('late.work.json'), ('--force',)
    tasks.parent.mkdir()
    if case == 'backup-exists':
        request_path.write_text('{"old": true}', encoding='utf-8')
        request_path.with_name('late.work.json.bak').write_text('{}', encoding='utf-8')
    elif case == 'request-is-a-directory':
        request_path.mkdir()
    elif case == 'request-is-a-dangling-link':
        request_path.symlink_to(tmp_path / 'nowhere')
    elif case == 'parent-is-a-file':
        tasks = tasks.parent / 'file' / 'late'
        request_path = tasks.with_name('late.work.json')
        tasks.parent.write_text('', encoding='utf-8')
    elif case == 'parent-is-unwritable':
        if os.geteuid() == 0:
            pytest.skip('root writes through a read-only directory')
        tasks.parent.chmod(0o500)
    elif case == 'over-the-read-limit':
        monkeypatch.setattr('attune_harness.work_cli.REQUEST_LIMIT', 4096)
    else:
        def refuse(request):
            raise ValueError('preflight refused')
        monkeypatch.setattr('attune_harness.work_build.preflight', refuse)
    try:
        code, envelope = init_plan(capsys, root, tasks, *extra)
    finally:
        if case == 'parent-is-unwritable':
            tasks.parent.chmod(0o700)
    assert code == 2 and envelope['status'] == 'failed', envelope
    if case == 'over-the-read-limit':
        assert envelope['error']['detail'].endswith('over the 4096 bytes plan --request reads; '
                                                    'the effects manifest lists every file in the checkout')
    assert not (root / 'participants.json').exists(), 'a refused init removes the registry it wrote'
    if case in ('over-the-read-limit', 'preflight-refuses', 'parent-is-unwritable'):
        assert not request_path.exists() and not request_path.with_name('late.work.json.bak').exists()


def test_the_read_limit_is_measured_on_the_bytes_written(tmp_path, capsys, monkeypatch):
    root = checkout(tmp_path.resolve() / 'repo')
    code, envelope = init_plan(capsys, root, tmp_path.resolve() / 'probe' / 'size')
    assert code == 0, envelope
    written = Path(envelope['files'][-1]).stat().st_size
    (root / 'participants.json').unlink()  # so each run below writes the same registry first
    monkeypatch.setattr('attune_harness.work_cli.REQUEST_LIMIT', written)
    code, envelope = init_plan(capsys, root, tmp_path.resolve() / 'at' / 'size')
    assert code == 0, envelope
    assert Path(envelope['files'][-1]).stat().st_size == written
    (root / 'participants.json').unlink()
    monkeypatch.setattr('attune_harness.work_cli.REQUEST_LIMIT', written - 1)
    code, envelope = init_plan(capsys, root, tmp_path.resolve() / 'over' / 'size')
    assert code == 2 and f'would be {written} bytes' in envelope['error']['detail'], envelope


def test_a_failed_write_keeps_the_old_request_and_removes_its_backup(tmp_path, capsys, monkeypatch):
    root, tasks = checkout(tmp_path.resolve() / 'repo'), tmp_path.resolve() / 'tasks' / 'late'
    tasks.parent.mkdir()
    request_path = tasks.with_name('late.work.json')
    request_path.write_text('{"old": true}', encoding='utf-8')
    from attune_harness import init_cli
    real = init_cli.write_report
    def failing(path, value, *args):
        if Path(path) == request_path:
            raise OSError('disk full')
        return real(path, value, *args)
    monkeypatch.setattr(init_cli, 'write_report', failing)
    code, envelope = init_plan(capsys, root, tasks, '--force')
    assert code == 2 and envelope['error']['detail'] == 'disk full', envelope
    assert request_path.read_text(encoding='utf-8') == '{"old": true}'
    assert not request_path.with_name('late.work.json.bak').exists() and not (root / 'participants.json').exists()


def test_a_refusal_removes_the_directories_it_made_for_the_request(tmp_path, capsys, monkeypatch):
    root, tasks = checkout(tmp_path.resolve() / 'repo'), tmp_path.resolve() / 'a' / 'b' / 'late'
    from attune_harness import init_cli
    real = init_cli.write_report
    def failing(path, value, *args):
        if Path(path).name == 'late.work.json':
            raise OSError('disk full')
        return real(path, value, *args)
    monkeypatch.setattr(init_cli, 'write_report', failing)
    code, envelope = init_plan(capsys, root, tasks)
    assert code == 2, envelope
    assert not (tmp_path / 'a').exists()


def test_an_existing_registry_names_the_assignments(tmp_path, capsys):
    root, tasks = checkout(tmp_path.resolve() / 'repo'), tmp_path.resolve() / 'tasks' / 'kept'
    registry = {'schema_version': 1, 'participants': {'alpha': PROFILES['demo']['lead'],
                                                      'beta': PROFILES['demo']['reviewer']}}
    (root / 'participants.json').write_text(json.dumps(registry), encoding='utf-8')
    code, envelope = init_plan(capsys, root, tasks)
    assert code == 0 and envelope['files'] == [str(tasks.with_name('kept.work.json'))], envelope
    assert envelope['profile'] is None
    request = json.loads(tasks.with_name('kept.work.json').read_text(encoding='utf-8'))
    assert {a['role']: a['participant'] for a in request['assignments']} == {
        'planner': 'alpha', 'worker': 'alpha', 'reviewer': 'beta'}


@POSIX_ONLY
def test_a_checkout_changed_before_the_preview_names_init(tmp_path, capsys):
    root, tasks = checkout(tmp_path.resolve() / 'repo'), tmp_path.resolve() / 'tasks' / 'changed'
    code, envelope = init_plan(capsys, root, tasks)
    assert code == 0, envelope
    (root / 'calc.py').write_text('def add(a, b):\n    return 0\n', encoding='utf-8')
    code, refused = preview_work(capsys, envelope)
    assert code == 2 and refused['error'] == {'type': 'ValueError',
                                              'detail': 'Effect preimages disagree with work evidence'}, refused
    assert 'init --for plan' in refused['next_action'] and '--force' in refused['next_action']


@POSIX_ONLY
def test_a_checkout_changed_before_acceptance_names_init(tmp_path, capsys):
    root, tasks = checkout(tmp_path.resolve() / 'repo'), tmp_path.resolve() / 'tasks' / 'stale'
    code, envelope = init_plan(capsys, root, tasks)
    code, draft = preview_work(capsys, envelope)
    assert code == 0, draft
    (root / 'calc.py').write_text('def add(a, b):\n    return 0\n', encoding='utf-8')
    code, refused = run(capsys, 'plan', '--task-dir', str(tasks), '--accept', '--checkpoint', draft['checkpoint_digest'])
    assert code == 2 and refused['error']['type'] == 'ValueError', refused
    assert 'init --for plan' in refused['next_action'] and 'a new --task-dir' in refused['next_action']


def test_for_plan_task_dir_and_tests_stay_distinct_options():
    from attune_harness.cli import build_parser
    args = build_parser().parse_args(['init', '--for', 'plan', '--task-dir', 'x', '--tests', 't.py'])
    assert args.task_dir == Path('x') and args.tests == ['t.py'] and args.starter == 'plan'
    with pytest.raises(SystemExit):  # ambiguous, as the changelog says
        build_parser().parse_args(['init', '--t', 'x'])
