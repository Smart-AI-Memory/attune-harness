"""Run rendered arguments through real Windows shells and native Python.

The native child observes the arguments, so a shell expression or altered value
cannot pass merely because a second parser agrees with the renderer. Full
emitted Harness command journeys belong to test_cold_start_journey.

Supported directory arguments are Path-normalized before rendering. The raw
space-plus-terminal-backslash case separately records the known PS5.1 native
transport limitation; shell quoting alone does not fix every native argv form.
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


@pytest.fixture(params=['powershell.exe', 'pwsh.exe'], ids=['powershell-5.1', 'powershell-7'])
def powershell(request):
    """Require Windows PowerShell; report an unavailable optional PS7 honestly."""
    if request.param == 'powershell.exe':
        executable = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
        assert executable.is_file(), 'Windows PowerShell is required on the declared Windows profile'
        return str(executable), '5.1.'
    executable = shutil.which('pwsh.exe')
    if executable is None:
        pytest.skip('PowerShell 7 (pwsh.exe) is not installed or is not on PATH')
    return executable, '7.'


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
    pytest.param(PureWindowsPath('C:\\space path\\'), id='normalized-directory'),
    pytest.param(PureWindowsPath('C:\\'), id='drive-root'),
    pytest.param('$env:ATTUNE_QUOTE_CANARY', id='environment-variable'),
    pytest.param("$([IO.File]::WriteAllText($env:ATTUNE_QUOTE_MARKER,'expanded'))",
                 id='command-substitution'),
])
def test_rendered_argument_reaches_native_child_literally(tmp_path, powershell, value, request):
    """Legacy and modern shell transport must preserve value, position and effects."""
    executable, version_prefix = powershell
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
    script.write_text(
        "$ErrorActionPreference = 'Stop'\n"
        "$path = 'expanded-variable'\n"
        "$env:ATTUNE_QUOTE_ENGINE = $PSVersionTable.PSVersion.ToString()\n"
        "$env:ATTUNE_QUOTE_NATIVE_MODE = if ($PSVersionTable.PSVersion.Major -eq 5) "
        "{ 'Legacy' } else { [string]$PSNativeCommandArgumentPassing }\n"
        f'& {quote(sys.executable)} -I -B -X utf8 {quote(capture)} '
        f'before {quote(value)} after\n'
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
    assert observed['native_mode'] in ('Legacy', 'Windows', 'Standard'), observed
    expected = ['before', str(value), 'after']
    if (version_prefix == '5.1.' and observed['native_mode'] == 'Legacy'
            and isinstance(value, str) and value == 'C:\\space path\\'):
        # Keep execution, side effects and any new corruption strict. Only the
        # observed legacy corruption at this final argv comparison is expected.
        assert observed['argv'] in (expected, ['before', 'C:\\space path" after'])
        request.node.add_marker(pytest.mark.xfail(
            strict=True, raises=AssertionError,
            reason='PS5.1 legacy native transport corrupts a raw spaced string ending in backslash; '
                   'supported directory renderers use Path-normalized values'))
    assert observed['argv'] == expected
