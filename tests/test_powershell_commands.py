"""Run rendered arguments through real Windows shells and native Python.

The native child observes the arguments, so a shell expression or altered value
cannot pass merely because a second parser agrees with the renderer. Full
emitted Harness command journeys belong to test_cold_start_journey.

Raw trailing backslashes must survive legacy native transport, including when
an argument is attached to an option. Supported directories also exercise Path
normalization; neither route may consume the following option or argument.
"""
# qualify: platform

import json
import os
from pathlib import Path, PureWindowsPath
import shutil
import subprocess
import sys

import pytest

from attune_harness.init_cli import quote


pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Requires real Windows PowerShell')


@pytest.fixture(params=[
    pytest.param(('powershell.exe', None), id='powershell-5.1'),
    pytest.param(('pwsh.exe', 'Windows'), id='powershell-7-windows'),
    pytest.param(('pwsh.exe', 'Standard'), id='powershell-7-standard'),
    pytest.param(('pwsh.exe', 'Legacy'), id='powershell-7-legacy'),
])
def powershell(request):
    """Require Windows PowerShell; report an unavailable optional PS7 honestly."""
    engine, mode = request.param
    if engine == 'powershell.exe':
        executable = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
        assert executable.is_file(), 'Windows PowerShell is required on the declared Windows profile'
        return str(executable), '5.1.', mode
    executable = shutil.which('pwsh.exe')
    if executable is None:
        pytest.skip('PowerShell 7 (pwsh.exe) is not installed or is not on PATH')
    return executable, '7.', mode


@pytest.mark.parametrize('value', [
    pytest.param(r'C:\space path\document.txt', id='spaces'),
    pytest.param(r"C:\apostrophe'path\document.txt", id='apostrophe'),
    pytest.param(r'C:\dollar$path\document.txt', id='dollar'),
    pytest.param(r'C:\backtick`npath\document.txt', id='backtick'),
    pytest.param('C:\\café 雪\\document.txt', id='unicode'),
    pytest.param('C:\\left‘quote\\document.txt', id='left-smart-single-quote'),
    pytest.param('C:\\right’quote\\document.txt', id='right-smart-single-quote'),
    pytest.param('C:\\low‚quote\\document.txt', id='low-smart-single-quote'),
    pytest.param('C:\\reversed‛quote\\document.txt', id='reversed-smart-single-quote'),
    pytest.param("C:\\mixed'‘’‚‛quote\\document.txt", id='adjacent-mixed-single-quotes'),
    pytest.param('C:\\smart“”„quotes\\document.txt', id='smart-double-quotes'),
    pytest.param("C:\\café' $path `n [literal] (round); &more\\document.txt", id='combined'),
    pytest.param('C:\\space path\\', id='trailing-backslash'),
    pytest.param('C:\\space path\\\\', id='two-trailing-backslashes'),
    pytest.param('C:\\space path\\\\\\', id='three-trailing-backslashes'),
    pytest.param('C:\\plain\\', id='no-space-trailing-backslash'),
    pytest.param('C:\\tab\tpath\\', id='tab-trailing-backslash'),
    pytest.param('C:\\no\u00a0break\\', id='unicode-space-trailing-backslash'),
    pytest.param("C:\\café'‘’‚‛ $path `n (round); &more\\", id='combined-trailing-backslash'),
    pytest.param('relative scope\\', id='relative-trailing-backslash'),
    pytest.param(PureWindowsPath('C:\\space path\\'), id='normalized-directory'),
    pytest.param(PureWindowsPath('C:\\'), id='drive-root'),
    pytest.param('$env:ATTUNE_QUOTE_CANARY', id='environment-variable'),
    pytest.param("$([IO.File]::WriteAllText($env:ATTUNE_QUOTE_MARKER,'expanded'))",
                 id='command-substitution'),
])
@pytest.mark.parametrize('prefix', ['', '--path='], ids=['argument', 'attached-option'])
def test_rendered_argument_reaches_native_child_literally(tmp_path, powershell, value, prefix):
    """Legacy and modern shell transport must preserve value, position and effects."""
    executable, version_prefix, mode = powershell
    capture = tmp_path / 'capture.py'
    capture.write_text(
        'import json, os, sys\n'
        'print(json.dumps({"argv": sys.argv[1:], '
        '"engine": os.environ["ATTUNE_QUOTE_ENGINE"], '
        '"native_mode": os.environ["ATTUNE_QUOTE_NATIVE_MODE"]}, ensure_ascii=True))\n',
        encoding='utf-8',
    )
    marker = tmp_path / 'unexpected-expansion.txt'
    script = tmp_path / 'invoke.ps1'
    # A BOM makes Windows PowerShell 5.1 read the same Unicode source as PS7.
    # Give expansions observable values and keep the side-effect canary inside
    # this test's temporary directory even when the renderer is broken.
    mode_setup = f"$PSNativeCommandArgumentPassing = '{mode}'\n" if mode else ''
    script.write_text(
        "$ErrorActionPreference = 'Stop'\n"
        'Set-StrictMode -Version Latest\n'
        f'{mode_setup}'
        "$path = 'expanded-variable'\n"
        "$env:ATTUNE_QUOTE_ENGINE = $PSVersionTable.PSVersion.ToString()\n"
        "$env:ATTUNE_QUOTE_NATIVE_MODE = if ($PSVersionTable.PSVersion.Major -eq 5) "
        "{ 'Legacy' } else { [string]$PSNativeCommandArgumentPassing }\n"
        f'& {quote(sys.executable)} -I -B -X utf8 {quote(capture)} '
        f'before {prefix}{quote(value)} --config after\n'
        'exit $LASTEXITCODE\n',
        encoding='utf-8-sig',
    )
    environment = dict(os.environ, ATTUNE_QUOTE_CANARY='expanded-environment',
                       ATTUNE_QUOTE_MARKER=str(marker))
    result = subprocess.run(
        [executable, '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
         '-File', str(script)],
        cwd=tmp_path, env=environment, input='', capture_output=True, text=True,
        encoding='utf-8', errors='replace', timeout=30,
    )
    output = result.stdout + result.stderr
    assert not marker.exists(), f'Shell evaluated the literal argument: {output}'
    assert result.returncode == 0, output
    observed = json.loads(result.stdout)
    assert observed['engine'].startswith(version_prefix), observed
    assert observed['native_mode'] == (mode or 'Legacy'), observed
    assert observed['argv'] == ['before', prefix + str(value), '--config', 'after']
