"""Repair, test the captured change, and inspect saved work through native shells.

The installed-wheel qualifier carries this module on Windows/Python 3.12.
The same journey runs as a POSIX control in the other platform jobs. Every CLI
invocation starts a fresh process outside the fixture's dedicated checkout.
"""
# qualify: platform

import base64
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from attune_harness.init_cli import quote
from attune_harness.review_contract import digest
from attune_harness.task_contract import read_task
from test_cold_start_journey import CLI, ROOT, environment, failing_repository, harness


def run_cli(arguments, cwd, engine):
    """Use the installed console script through a fresh instance of the named shell."""
    if engine == 'posix-control':
        return harness(arguments, cwd)
    executable = (Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
                  if engine == 'powershell.exe' else shutil.which(engine))
    assert executable and Path(executable).is_file(), f'T6 requires {engine} on Windows'
    major = 5 if engine == 'powershell.exe' else 7
    command = '& ' + ' '.join(quote(value) for value in [str(CLI), *arguments])
    script = (
        "$ErrorActionPreference = 'Stop'\n"
        f"if ($PSVersionTable.PSVersion.Major -ne {major}) {{ throw 'Unexpected shell version' }}\n"
        '[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)\n'
        f'{command}\nexit $LASTEXITCODE\n'
    )
    encoded = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
    result = subprocess.run(
        [str(executable), '-NoLogo', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
        cwd=cwd, env=environment(), input='', capture_output=True, text=True,
        encoding='utf-8', timeout=120,
    )
    output = result.stdout + result.stderr
    assert result.stdout, output
    return result.returncode, json.loads(result.stdout), output


def file_bytes(root):
    """Capture project or saved-task files while excluding Git's mutable bookkeeping."""
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob('*')
            if path.is_file() and '.git' not in path.relative_to(root).parts}


@pytest.mark.parametrize('engine', ['powershell.exe', 'pwsh.exe'] if os.name == 'nt' else ['posix-control'])
@pytest.mark.parametrize('directory_name', ['plain', "space's $literal` café 雪"])
def test_repair_handoff_and_saved_status(tmp_path, engine, directory_name, record_property):
    """A completed repair supplies immutable provenance to one captured pytest execution."""
    home = tmp_path.resolve() / directory_name
    home.mkdir()
    project = failing_repository(home / 'project')
    repair_dir, test_dir = home / 'repair-task', home / 'test-task'
    registry = json.loads((ROOT / 'examples/starter/participants.json').read_text(encoding='utf-8'))
    for participant in registry['participants'].values():
        participant['command'][0] = sys.executable
    config = project / 'participants.json'
    config.write_text(json.dumps(registry), encoding='utf-8')
    record_property('shell', engine)
    record_property('python', sys.version)
    record_property('harness', importlib.metadata.version('attune-harness'))

    code, initialized, output = run_cli(
        ['init', '--for', 'fix', '--project', str(project), '--scope', 'calc.py',
         '--interpreter', sys.executable, '--tests', 'tests/test_calc.py'], home, engine,
    )
    assert code == 0 and initialized['status'] == 'created', output
    original = file_bytes(project)
    probe = json.loads((project / 'probe.json').read_text(encoding='utf-8'))
    assert probe['timeout'] == 30
    code, preview, output = run_cli(
        ['fix', '--goal', 'Repair addition', '--project', str(project), '--checkout', str(project),
         '--scope', 'calc.py', '--probe', str(project / 'probe.json'), '--config', str(config),
         '--worker', 'lead', '--reviewer', 'reviewer', '--review', 'required',
         '--criteria', 'Pass the frozen probe without changing its oracle', '--task-dir', str(repair_dir)],
        home, engine,
    )
    assert code == 1 and preview['status'] == 'draft', output
    assert file_bytes(project) == original
    submission = preview['submission']
    submission['accepted'] = True
    submission['permissions'] = {'external': True, 'provider': False}
    response = home / 'repair-response.json'
    response.write_text(json.dumps(submission), encoding='utf-8')
    code, repaired, output = run_cli(
        ['fix', '--task-dir', str(repair_dir), '--task-response', str(response)], home, engine,
    )
    assert code == 0 and repaired['status'] == 'completed', output
    repair = read_task(repair_dir)
    execution = repair['execution']
    assert execution['before_probe']['passed'] is False
    assert execution['after_probe']['passed'] is True
    assert execution['review']['verdict'] == 'approve'
    assert all(event['attempts'] == 1 for event in execution['events'])
    expected = {**original, 'calc.py': original['calc.py'].replace(b'a - b', b'a + b')}
    assert file_bytes(project) == expected
    saved_repair = file_bytes(repair_dir)

    code, preview, output = run_cli(
        ['test', '--from-task', str(repair_dir), '--interpreter', sys.executable,
         '--timeout', '30', '--task-dir', str(test_dir)], home, engine,
    )
    assert code == 1 and preview['presentation']['current_result']['outcome'] == 'draft', output
    captured = read_task(test_dir)
    assert captured['request']['project_root'] == str(project)
    assert captured['request']['selection']['scope'] == ['calc.py']
    assert captured['request']['source_task'] == {
        'kind': 'completed-repair-v1', 'record_path': repair['record_path'],
        'task_id': repair['request']['task_id'], 'request_digest': digest(repair['request']),
        'checkpoint_digest': repair['checkpoint_digest'],
        'artifact_digest': execution['integration']['artifact_digest'],
        'probe_digest': execution['integration']['probe_digest'],
    }
    code, tested, output = run_cli(
        ['test', '--task-dir', str(test_dir), '--checkpoint', preview['checkpoint_digest'], '--accept'],
        home, engine,
    )
    assert code == 0 and tested['presentation']['current_result']['outcome'] == 'passed', output
    task = read_task(test_dir)
    assert task['execution']['result']['pytest']['passed'] == 1
    assert task['request']['runner']['timeout'] == 30
    assert len(task['execution']['events']) == 1
    assert task['execution']['events'][0]['attempts'] == 1
    assert file_bytes(project) == expected
    assert file_bytes(repair_dir) == saved_repair
    saved_test = file_bytes(test_dir)

    for _ in range(2):
        code, status, output = run_cli(['status', str(repair_dir)], home, engine)
        assert code == 0 and status['status'] == 'completed', output
        code, status, output = run_cli(['status', str(test_dir)], home, engine)
        assert code == 0 and status['presentation']['current_result']['outcome'] == 'passed', output
        assert file_bytes(repair_dir) == saved_repair
        assert file_bytes(test_dir) == saved_test
        assert file_bytes(project) == expected
