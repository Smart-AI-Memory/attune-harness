"""Prepare the offline report exercise without accepting or running its plan."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / 'training' / '1.7.0-preparation' / 'assets' / 'example'
STARTER = ROOT / 'examples' / 'starter' / 'worker.py'
CORRECT = 'total_minutes += minutes'
UNFINISHED = 'total_minutes -= minutes'
ENTRY_POINT = 'if __name__ == "__main__":\n    raise SystemExit(main())'
PORTABLE_ENTRY_POINT = (
    'if __name__ == "__main__":\n'
    '    sys.stdout.reconfigure(encoding="utf-8", newline="\\n")\n'
    '    raise SystemExit(main())'
)


def prepare(destination):
    destination = destination.absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError('Choose a new practice directory; existing work is preserved.')
    if destination.parent.resolve(strict=True) != destination.parent:
        raise ValueError('Choose a practice directory under a canonical local parent.')

    report = (SAMPLE / 'report.py').read_text(encoding='utf-8')
    if report.count(CORRECT) != 1 or report.count(ENTRY_POINT) != 1:
        raise ValueError('The sample report no longer matches the expected starter source.')
    # The frozen tests compare stdout byte-for-byte, including line endings.
    report = report.replace(ENTRY_POINT, PORTABLE_ENTRY_POINT).replace(CORRECT, UNFINISHED)

    project = destination / 'project'
    project.mkdir(parents=True)
    for name in ('data', 'expected', 'tests'):
        shutil.copytree(SAMPLE / name, project / name,
                        ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache', '*.pyc'))
    shutil.copyfile(SAMPLE / 'pytest.ini', project / 'pytest.ini')
    (project / 'report.py').write_text(report, encoding='utf-8', newline='\n')

    seat = {
        'adapter': 'command',
        'command': [sys.executable, '-I', '-X', 'utf8', '-B', '-c',
                    STARTER.read_text(encoding='utf-8'), 'report.py', UNFINISHED, CORRECT],
        'timeout': 30, 'tools': [], 'max_turns': 1, 'max_tool_calls': 0,
        'environment': {'profile': 'command-env-v1', 'passthrough': []},
    }
    registry = project / 'participants.json'
    registry.write_text(json.dumps({'schema_version': 1, 'participants': {
        'lead': seat, 'reviewer': seat,
    }}, indent=2) + '\n', encoding='utf-8')
    protected = sorted(path.relative_to(project).as_posix()
                       for path in project.rglob('*') if path.is_file() and path != project / 'report.py')

    hooks = destination / 'no-hooks'
    hooks.mkdir()
    # The example must not inherit a caller's repository, worktree or index.
    git_env = {key: value for key, value in os.environ.items() if not key.upper().startswith('GIT_')}
    git_env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=str(hooks / 'gitconfig'))
    subprocess.run(['git', 'init', '--quiet', '--template=', str(project)], check=True, env=git_env)
    subprocess.run(['git', '-C', str(project), 'config', '--local', 'core.autocrlf', 'false'],
                   check=True, env=git_env)
    git = ['git', '-C', str(project), '-c', 'commit.gpgsign=false',
           '-c', f'core.hooksPath={hooks}', '-c', 'user.name=Offline practice',
           '-c', 'user.email=practice@example.invalid']
    subprocess.run([*git, 'add', '--force', '--', 'report.py', *protected], check=True, env=git_env)
    subprocess.run([*git, 'commit', '-qm', 'Prepare the offline reporting fixture\n\n'
                    'Co-Authored-By: GPT-6 (Codex) <codex@openai.com>'], check=True, env=git_env)

    subprocess.run([
        sys.executable, '-I', '-m', 'attune_harness', 'init', '--for', 'plan',
        '--goal', 'Complete the activity report', '--project', str(project),
        '--scope', 'report.py', '--interpreter', sys.executable, '--tests',
        'tests/test_report.py', 'tests/test_html_report.py', '--task-dir', str(destination / 'task'),
    ], check=True, env=git_env)
    request = destination / 'task.work.json'
    work = json.loads(request.read_text(encoding='utf-8'))
    work['effects']['protected'] = protected
    request.write_text(json.dumps(work, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    prepare(parser.parse_args().destination)
