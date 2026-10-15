"""Pure data/guard controls; never execute PowerShell, a CLI or a backend."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import sysconfig
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'experiments/platform/windows_saved_store_build_preflight_v1.ps1'
WORKFLOW = ROOT / '.github/workflows/windows-saved-store-build-safe-preflight.yml'


def literal(name):
    rows = re.findall(r'\$' + name + " = @'\n(.*?)\n'@", SCRIPT.read_text(), re.S)
    assert len(rows) == 1
    return rows[0]


@pytest.mark.parametrize('change', [None, 'cwd', 'search', 'origin', 'home', 'path', 'userbase', 'unknown', 'user_site'])
def test_actual_startup_query_rejects_original_repo_and_ambient_routes(tmp_path, monkeypatch, capsys, change):
    repo, cwd, tools = tmp_path / 'repo', tmp_path / 'owned', tmp_path / 'tools'
    for path in [repo, cwd, tools]:
        path.mkdir()
    environment = {'PYTHONNOUSERSITE': '1', 'pythonLocation': 'do-not-emit-this-value',
                   'Python_ROOT_DIR': 'do-not-emit-this-value', 'Python2_ROOT_DIR': 'do-not-emit-this-value',
                   'Python3_ROOT_DIR': 'do-not-emit-this-value'}
    if change in ['home', 'path', 'userbase', 'unknown']:
        environment[{'home': 'PythonHome', 'path': 'pythonpath', 'userbase': 'PYTHONUSERBASE', 'unknown': 'PYTHONINSPECT'}[change]] = 'do-not-emit-this-value'
    flags = {name: getattr(sys.flags, name) for name in dir(sys.flags)
             if not name.startswith('_') and isinstance(getattr(sys.flags, name), int)}
    flags['no_user_site'] = 0 if change == 'user_site' else 1
    with monkeypatch.context() as patch:
        patch.setattr(sys, 'argv', ['-c', str(repo), str(cwd)])
        patch.setattr(sys, 'path', [str(repo if change == 'search' else cwd)])
        patch.setattr(sys, 'flags', SimpleNamespace(**flags))
        patch.setattr(os, 'environ', environment)
        patch.setattr(os, 'getcwd', lambda: str(repo if change == 'cwd' else cwd))
        patch.setattr(importlib.util, 'find_spec', lambda name: SimpleNamespace(origin=str((repo if change == 'origin' else tools) / (name + '.py'))))
        with pytest.raises(SystemExit) as result:
            exec(compile(literal('query'), 'reviewed-startup-query', 'exec'), {})
    observed = json.loads(capsys.readouterr().out)
    assert result.value.code == (0 if change is None else 41)
    assert len(observed['checks']) == 6
    assert all(observed['checks'].values()) == (change is None)
    assert 'do-not-emit-this-value' not in json.dumps(observed)
    assert len(observed['setup_action_metadata_key_names']) == 4


@pytest.mark.parametrize('change', [None, 'content', 'count', 'missing', 'installer_record'])
def test_installed_query_checks_118_shipped_files_and_names_record_limit(tmp_path, monkeypatch, capsys, change):
    site = tmp_path / 'site'
    site.mkdir()
    members = {}
    for number in range(118):
        name = f'attune_harness/module_{number}.py'
        raw = f'value={number}\n'.encode()
        path = site / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(raw)
        members[name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    record = 'attune_harness-1.4.0.dist-info/RECORD'
    members[record] = {'sha256': '0' * 64, 'bytes': 1}
    if change == 'content':
        (site / next(iter(members))).write_bytes(b'wrong')
    if change == 'missing':
        (site / next(iter(members))).rename(tmp_path / 'retained-original')
    if change == 'count':
        members.pop(next(iter(members)))
    if change == 'installer_record':
        path = site / record
        path.parent.mkdir()
        path.write_text('installer rewrites RECORD; archive RECORD was checked before install')
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps({'wheel_members': members}))
    with monkeypatch.context() as patch:
        patch.setattr(sys, 'argv', ['-c', str(manifest)])
        patch.setattr(sysconfig, 'get_paths', lambda: {'purelib': str(site)})
        if change == 'missing':
            with pytest.raises(FileNotFoundError):
                exec(compile(literal('installedQuery'), 'reviewed-installed-query', 'exec'), {})
            return
        with pytest.raises(SystemExit) as result:
            exec(compile(literal('installedQuery'), 'reviewed-installed-query', 'exec'), {})
    observed = json.loads(capsys.readouterr().out)
    assert result.value.code == (42 if change in ['content', 'count'] else 0)
    assert observed['installer_rewritten_record_compared'] is False
    assert observed['package_or_native_imported'] is False


def test_all_accepted_v3b_files_remain_byte_identical():
    pins = {
        '.gitattributes': '1cf8827a8b0ab0724e7b0031a241930aa7b0edcf9adb7d813f17b3a624e79fe5',
        '.github/workflows/windows-saved-store-reviewed-execution.yml': '30e11a181edf79eecb0667686d2da540fe9c7047829dc31ddaa50e23d88dfc6e',
        'experiments/platform/windows_saved_store_combined_driver_v2.py': 'b61a452cb8f59862cee4a366510b74c73544d62e83dc4a81288e28b82e717ca0',
        'experiments/platform/windows_saved_store_source_manifest_v2.json': 'd6e80ebd18c19d5b17b35bfdd4c0dc521a24e1dbb0a18eeba14247fcd7e875d8',
        'experiments/platform/check_windows_saved_store_account_inputs_v2.py': '7fc6169c570d65d4493d70443ca27cb643d9127d8a3c416ac7cd7636388eb6be',
        'experiments/platform/project_windows_saved_store_build_v1.py': '3a3aa7a53cdb53b8421d6116bdd0160757967b3472e6a39052987971828f20d8',
        'tests/test_windows_saved_store_account_inputs_v2.py': '6fbe500f7bee3945a3e2817241b805464a9c8b127124b5b54fb6589843827382',
        'tests/test_windows_saved_store_build_projection.py': '1bc16cf178c99a5ba6940849cb493ccac82c576578f6dc5c386193cb1db5e181',
    }
    for path, digest in pins.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest


def test_safe_workflow_canonicalizes_all_pinned_bytes_and_has_only_four_safe_cells():
    text = WORKFLOW.read_text()
    assert 'workflow_dispatch' not in text and 'branches: [main]' in text
    assert 'os: [windows-2022, windows-2025]' in text and "python: ['3.10', '3.12']" in text
    assert 'cancel-in-progress: false' in text and 'if: always()' in text
    assert 'git -c core.autocrlf=false checkout-index --force -- @($expected.Keys)' in text
    assert hashlib.sha256(SCRIPT.read_bytes()).hexdigest() in text
    assert '-ExecuteApprovedFixture' not in text and '-ExecuteReviewedGuiLease' not in text
    assert 'if: ${{ false }}' in (ROOT / '.github/workflows/windows-saved-store-reviewed-execution.yml').read_text()
    assert '--noconftest' in text and 'PYTEST_DISABLE_PLUGIN_AUTOLOAD' in text


def test_safe_script_has_finite_capture_refusal_and_no_account_or_native_entry():
    text = SCRIPT.read_text()
    assert re.findall(r'&\s+\$(\w+)', text) == ['ControllerPython', 'basePython', 'basePython', 'basePython', 'runtimePython']
    for forbidden in ['DllImport', 'CreateProcessAsUser', 'LogonUser', 'ExecuteApprovedFixture', 'T2PrivateGuiLease']:
        assert forbidden not in text
    assert '131072-text.Length' in text and 'process.Kill(true)' in text
    assert 'result.StreamsCompleted=Task.WaitAll' in text and 'DiscardedCharacters -ne 0' in text
    assert text.index('$report.commands += $row; Save-Json') < text.index('$row.capture = [T2BuildCaptureV1]::Run')
    assert "'capture-negative'" in text and 't2_build_capture_stderr' in text and 'sys.exit(47)' in text
    assert '[IO.FileMode]::CreateNew' in text and '$existing -icontains $name' in text
    assert "@('setup.py','setup.cfg','venv.py','pip.py','sitecustomize.py','usercustomize.py')" in text
    assert 'Remove-Item' not in text and 'EnvironmentVariableTarget' not in text
    assert text.index('& $ControllerPython -I -c') < text.index('$env:PYTHONHOME = $Repo') < text.index('$env:PYTHONHOME = $null')
    assert text.index('$env:PYTHONPATH = $Repo') < text.index('$env:PYTHONPATH = $null')
    assert text.index('$env:PYTHONUSERBASE = $Repo') < text.index('$env:PYTHONUSERBASE = $null')
    assert text.index('$env:PYTHONPATH = $null') < text.index('Set-Location -LiteralPath $fixtureCwd') < text.index('& $basePython -m venv')
    assert text.index('post_source_observations = @(Observe-Pins)') < text.index("'startup-child'")
    assert 'wheel_rows.Count -ne 119' in text and 'source_rows.Count -ne 116' in text
    assert 'installer_rewritten_record_compared' in text and 'canary_markers' in text
