"""The cold-start journey: every task verb from a fresh install (first-run journey, R6).

Each case starts in an empty temporary directory, with no participant
registry and no ``ATTUNE_*`` variable but the two that switch off usage pings
and version checks, and runs the installed ``attune-harness`` console script
the way a new user would. In the platform jobs that is the wheel installed into
the runner's fresh environment; in the full suite it is the editable install.

Journeys documented with a ``<!-- journey: NAME -->`` tag run exactly as the
documentation writes them (``scripts/doc_journeys.py``), each case
substituting the documented placeholders with its own paths. A journey the spec requires that does not
work yet is a strict ``xfail`` naming the task that fixes it, raising
``AssertionError`` only: when that task lands the case passes, the strict
``xfail`` fails, and the task removes the mark. A crash of any other kind is
never absorbed as an expected failure. See
``docs/specs/first-run-journey/tasks.md``.
"""
# qualify: platform

import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


doc_journeys = _load('doc_journeys')
CLI = _load('check_installed').console_script(Path(sys.executable))
POSIX_ONLY = pytest.mark.skipif(os.name != 'posix', reason='the test verb qualifies the POSIX execution profile only')


def pending(task, reason):
    """A journey the spec requires that does not work yet; ``task`` fixes it."""
    return pytest.mark.xfail(strict=True, raises=AssertionError, reason=f'{task}: {reason}')


def environment():
    """The caller's environment without Attune settings, telemetry kept off."""
    env = {key: value for key, value in os.environ.items() if not key.startswith('ATTUNE_')}
    env.update(ATTUNE_USAGE_PING='0', ATTUNE_VERSION_CHECK='0', PYTHONIOENCODING='utf-8')
    return env


def harness(args, cwd):
    """Run the installed console script; return the exit code, the envelope (or None) and the raw output."""
    # An empty pipe, never the runner's stdin: Windows reports an inherited console, and even
    # NUL, as a terminal, which would start review's interactive intake prompts.
    result = subprocess.run([str(CLI), *args], cwd=cwd, env=environment(), capture_output=True,
                            input='', text=True, encoding='utf-8', timeout=120)
    try:
        envelope = json.loads(result.stdout)
    except ValueError:
        envelope = None
    return result.returncode, envelope, result.stdout + result.stderr


def split(command):
    """A printed command line as argv, read the way this platform's shell reads it."""
    if os.name == 'posix':
        return shlex.split(command)
    return [token[1:-1] if len(token) > 1 and token[0] == token[-1] == '"' else token
            for token in shlex.split(command, posix=False)]


def git_repository(root):
    """A small committed project, then an uncommitted change to ``calc.py`` and ``src/example.py``."""
    root.mkdir()
    (root / 'tests').mkdir()
    (root / 'src').mkdir()
    (root / 'calc.py').write_text('def add(a, b):\n    return a + b\n', encoding='utf-8')
    (root / 'src' / 'example.py').write_text('VALUE = 1\n', encoding='utf-8')
    (root / 'tests' / 'test_calc.py').write_text('from calc import add\n\n\ndef test_add():\n    assert add(2, 2) == 4\n',
                                                 encoding='utf-8')
    hooks = root.parent / 'no-hooks'
    hooks.mkdir(exist_ok=True)
    git = ['git', '-C', str(root), '-c', 'commit.gpgsign=false', '-c', f'core.hooksPath={hooks}',
           '-c', 'user.name=Journey', '-c', 'user.email=journey@example.invalid']
    subprocess.run(['git', 'init', '-q', str(root)], check=True, capture_output=True)
    subprocess.run([*git, 'add', '.'], check=True, capture_output=True)
    subprocess.run([*git, 'commit', '-qm', 'baseline'], check=True, capture_output=True)
    (root / 'calc.py').write_text('def add(a, b):\n    return b + a\n', encoding='utf-8')
    (root / 'src' / 'example.py').write_text('VALUE = 2\n', encoding='utf-8')
    return root


@pytest.fixture
def home(tmp_path):
    """An empty working directory; the task store refuses to traverse macOS's symlinked temporary root."""
    directory = tmp_path.resolve() / 'home'
    directory.mkdir()
    return directory


def test_documented_journeys_are_tagged():
    """The tags this test runs exist; losing one would silently drop its journey."""
    assert {'checks-and-receipts', 'test-this-change', 'review-bundled-example'} <= set(doc_journeys.journeys())


def test_demo(home):
    result = subprocess.run([sys.executable, '-m', 'attune_harness'], cwd=home, env=environment(),
                            capture_output=True, text=True, encoding='utf-8', timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)['status'] == 'verified'


def test_documented_checks_and_receipts(home):
    (code,) = doc_journeys.commands(doc_journeys.journeys()['checks-and-receipts'])
    result = subprocess.run([sys.executable, '-c', code], cwd=home, env=environment(),
                            capture_output=True, text=True, encoding='utf-8', timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == 'verified'


@pytest.fixture
def tested_change(home):
    """The documented test journey's first two commands, run as written: preview, then accept."""
    repo = git_repository(home / 'repo')  # the documented scope, src/example.py, is one of its changes
    task = home / 'test-task'
    table = {'/path/to/repo': str(repo), '/path/to/venv/bin/python': sys.executable,
             '/path/outside/repo/test-task': str(task)}
    preview, accept, *rest = doc_journeys.commands(doc_journeys.journeys()['test-this-change'])
    code, envelope, output = harness(shlex.split(doc_journeys.substitute(preview, table))[1:], home)
    assert (code, envelope and envelope['status']) == (1, 'draft'), output
    table['<preview-checkpoint>'] = envelope['checkpoint_digest']
    code, envelope, output = harness(shlex.split(doc_journeys.substitute(accept, table))[1:], home)
    assert code == 0 and envelope['status'] == 'completed', output
    assert envelope['presentation']['current_result']['outcome'] == 'passed', output
    return task, table, rest


@POSIX_ONLY
def test_documented_test_this_change(home, tested_change):
    """Preview, accept, status and resume, as the CLI guide writes them."""
    task, table, (status, resume) = tested_change
    code, envelope, output = harness(shlex.split(doc_journeys.substitute(status, table))[1:], home)
    assert code == 0 and envelope['status'] == 'completed', output
    code, envelope, output = harness(shlex.split(doc_journeys.substitute(resume, table))[1:], home)
    assert code == 0 and envelope['status'] == 'completed', output


def test_documented_review_bundled_example(home):
    """The CLI guide's bundled review example, run as written from a copy of ``examples/``."""
    shutil.copytree(ROOT / 'examples', home / 'examples')
    change, review = doc_journeys.commands(doc_journeys.journeys()['review-bundled-example'])
    assert change == 'cd examples/local-workflow'
    table = {'/path/outside/repo/review-task': str(home / 'review-task')}
    code, envelope, output = harness(split(doc_journeys.substitute(review, table))[1:],
                                     home / 'examples' / 'local-workflow')
    assert code == 0 and envelope['status'] == 'completed', output


# First-run journey T3: a registry from init, and refusals that name it.

def test_init_writes_a_working_registry(home):
    """``init`` writes the registry, and its next action runs exactly as printed."""
    (home / 'guide.md').write_text('# Guide\n\nThe answer is 42.\n', encoding='utf-8')
    code, envelope, output = harness(['init', '--profile', 'demo'], home)
    assert code == 0 and envelope['status'] == 'created', output
    assert json.loads((home / 'participants.json').read_text(encoding='utf-8'))['schema_version'] == 1
    command = envelope['next_action'].split(': ', 1)[1]
    code, intake, output = harness(split(command)[1:], home)
    assert code == 1 and intake['status'] == 'draft', output
    assert intake['operation'] == 'task-intake' and intake['markdown'].startswith('## Evidence assessment'), output


def test_review_without_a_registry_names_init(home):
    (home / 'guide.md').write_text('# Guide\n\nThe answer is 42.\n', encoding='utf-8')
    code, envelope, output = harness(['review', '--goal', 'Check the guide', '--document', 'guide.md',
                                      '--task-dir', str(home.parent / 'review-task')], home)
    assert code == 2 and envelope, output
    assert 'attune-harness init' in (envelope.get('next_action') or ''), output


def test_plan_without_a_registry_names_init(home):
    (home / 'request.json').write_text(json.dumps({'intent': {'goal': 'Add a subtract function'}}), encoding='utf-8')
    code, envelope, output = harness(['plan', '--task-dir', str(home.parent / 'plan-task'),
                                      '--request', 'request.json', '--project', '.'], home)
    assert code == 2 and envelope, output
    assert 'attune-harness init' in (envelope.get('next_action') or ''), output


# First-run journey T4: a path refusal says how the path was read.

def test_path_refusal_explains_resolution(home):
    project = home / 'project'
    project.mkdir()
    (project / 'guide.md').write_text('# Guide\n', encoding='utf-8')
    (home / 'context.json').write_text(json.dumps({'schema_version': 1, 'project_root': 'project'}), encoding='utf-8')
    (home / 'participants.json').write_text((ROOT / 'examples' / 'review' / 'participants.json').read_text(encoding='utf-8'),
                                            encoding='utf-8')
    code, envelope, output = harness(['review', '--goal', 'Check the guide', '--project', 'project',
                                      '--document', 'guide.md', '--context', 'context.json', '--corpus', '.',
                                      '--query', 'guide', '--criteria', 'Identify unsupported claims',
                                      '--assessor', 'sample-lead', '--task-dir', str(home / 'review-task'),
                                      '--accept'], home)
    assert code == 2 and envelope, output
    detail = envelope['error']['detail']
    assert '--project' in detail and str(project) in detail, detail
    assert "context 'context.json' resolves against --project" in detail, detail
    assert 'working directory' in detail, detail


# The journeys that do not work from a fresh install yet. Each passes when its task lands.


@POSIX_ONLY
@pending('T5', 'status renders Markdown for feature-work-v1 only')
def test_status_markdown_for_a_test_task(home, tested_change):
    task, _, _ = tested_change
    code, _, output = harness(['status', str(task), '--format', 'markdown'], home)
    assert code == 0 and output.startswith('## Test this change'), output


@POSIX_ONLY
@pending('T5', 'the task verbs have no --format markdown')
def test_test_verb_prints_markdown_on_request(home):
    repo = git_repository(home / 'repo')
    code, _, output = harness(['test', '--project', str(repo), '--scope', 'calc.py', '--interpreter', sys.executable,
                               '--task-dir', str(home / 'test-task'), '--format', 'markdown'], home)
    assert code == 1 and output.startswith('## Test this change'), output


@pending('T6', 'fix rejects an incomplete request with argparse usage text, not an envelope')
def test_fix_with_only_a_goal_returns_an_envelope(home):
    code, envelope, output = harness(['fix', '--goal', 'Make add handle strings',
                                      '--task-dir', str(home.parent / 'fix-task')], home)
    assert code == 2 and envelope, output
    assert envelope['status'] == 'failed' and envelope.get('next_action'), output
