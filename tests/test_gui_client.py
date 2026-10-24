# qualify: platform
"""Mandatory, dependency-free regression checks for the shipped browser script."""
import shutil
import subprocess
import sys
from pathlib import Path

from browser_process import read_browser_output, run_browser_process

import pytest
from attune_harness.gui_forms import FORM_SCRIPT
from attune_harness.gui_forms_intake import INTAKE_SCRIPT
from attune_harness.gui import INTAKE_BOOTSTRAP


@pytest.mark.parametrize('script,runner_name', [(FORM_SCRIPT, 'gui_forms.cjs'), (INTAKE_SCRIPT, 'gui_forms_intake.cjs')], ids=['development', 'intake'])
def test_shipped_browser_form_regressions(tmp_path, script, runner_name, record_property):
    node = shutil.which('node')
    assert node, 'GUI client verification requires Node.js; install Node and rerun (no skip).'
    source = tmp_path / 'forms.js'
    source.write_text(script, encoding='utf-8')
    runner = Path(__file__).parent / 'client' / runner_name
    diagnostics = tmp_path / 'browser-progress.jsonl'
    command = [node, str(runner), str(source)]
    command.append(str(diagnostics))
    # Allow bounded Windows Node startup without retrying the regression.
    timeout = 60 if sys.platform == 'win32' else 30
    try:
        result = run_browser_process(command, tmp_path, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        # pytest retains failure capture in tests.txt and failure JUnit output.
        # Keep the original timeout/cleanup; diagnostics must never mask it.
        details = [f'Browser regression timed out: {runner_name}; limit={error.timeout}s']
        try:
            with diagnostics.open(encoding='utf-8') as trace:
                details.append('Node progress (first 16384 characters):\n' + trace.read(16384))
        except OSError as diagnostic_error:
            details.append(f'Node progress unavailable: {type(diagnostic_error).__name__}')
        for label, output in [('stdout', error.stdout), ('stderr', error.stderr)]:
            if isinstance(output, bytes):
                output = output.decode('utf-8', errors='replace')
            details.append(f'Partial {label} (last 4096 characters): {output[-4096:] if output else "<empty>"}')
        message = '\n'.join(details)
        print(message)
        if hasattr(error, 'add_note'):  # Python 3.11+: retained in failure JUnit too.
            error.add_note(message)
        raise
    finally:
        record_property('browser_process', read_browser_output(tmp_path / 'browser-process.json', 65536))
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'client regressions passed' in result.stdout


@pytest.mark.parametrize('script', [FORM_SCRIPT, INTAKE_SCRIPT], ids=['development', 'intake'])
def test_shipped_browser_form_instructions(tmp_path, script):
    node = shutil.which('node')
    assert node, 'GUI client verification requires Node.js; install Node and rerun (no skip).'
    source = tmp_path / 'forms.js'
    source.write_text(script, encoding='utf-8')
    runner = Path(__file__).parent / 'client' / 'gui_form_instructions.cjs'
    result = subprocess.run([node, str(runner), str(source)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'client regressions passed' in result.stdout


@pytest.mark.parametrize('mode', [
    'fragment', 'stored', 'missing', 'read-denied', 'read-property-denied',
    'write-denied', 'write-property-denied', 'first-fetch-fails',
])
def test_shipped_intake_bootstrap(tmp_path, mode):
    node = shutil.which('node')
    assert node, 'GUI client verification requires Node.js; install Node and rerun (no skip).'
    source = tmp_path / 'app.js'
    source.write_text(INTAKE_BOOTSTRAP, encoding='utf-8')
    runner = Path(__file__).parent / 'client' / 'gui_intake_bootstrap.cjs'
    result = subprocess.run([node, str(runner), str(source), mode],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'client regressions passed' in result.stdout


def test_shipped_browser_handoff_client(tmp_path):
    node = shutil.which('node')
    assert node, 'GUI client verification requires Node.js; install Node and rerun (no skip).'
    source = tmp_path / 'app.js'
    source.write_text(INTAKE_BOOTSTRAP, encoding='utf-8')
    runner = Path(__file__).parent / 'client' / 'gui_browser_navigation.cjs'
    result = subprocess.run([node, str(runner), str(source)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'client regressions passed' in result.stdout


def test_shipped_intake_saved_answers(tmp_path):
    node = shutil.which('node')
    assert node, 'GUI client verification requires Node.js; install Node and rerun (no skip).'
    source = tmp_path / 'forms.js'
    source.write_text(INTAKE_SCRIPT, encoding='utf-8')
    runner = Path(__file__).parent / 'client' / 'gui_intake_summary.cjs'
    result = subprocess.run([node, str(runner), str(source)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'client regressions passed' in result.stdout


def test_shipped_approval_question_answer_preview(tmp_path):
    node = shutil.which('node')
    assert node, 'GUI client verification requires Node.js; install Node and rerun (no skip).'
    source = tmp_path / 'forms.js'
    source.write_text(INTAKE_SCRIPT, encoding='utf-8')
    runner = Path(__file__).parent / 'client' / 'gui_approval_preview.cjs'
    result = subprocess.run([node, str(runner), str(source)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'client regressions passed' in result.stdout


def test_shipped_saved_request_inspection(tmp_path):
    node = shutil.which('node')
    assert node, 'GUI client verification requires Node.js.'
    source = tmp_path / 'forms.js'
    source.write_text(INTAKE_SCRIPT, encoding='utf-8')
    runner = Path(__file__).parent / 'client' / 'gui_saved_request.cjs'
    result = subprocess.run([node, str(runner), str(source)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'client regressions passed' in result.stdout


def test_shipped_direct_form_journey(tmp_path):
    node = shutil.which('node')
    assert node, 'GUI client verification requires Node.js.'
    source = tmp_path / 'forms.js'
    source.write_text(INTAKE_SCRIPT, encoding='utf-8')
    runner = Path(__file__).parent / 'client' / 'gui_direct_form.cjs'
    result = subprocess.run([node, str(runner), str(source)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'client regressions passed' in result.stdout


def test_shipped_reload_recovery_and_view_ownership(tmp_path):
    node = shutil.which('node')
    assert node, 'GUI client verification requires Node.js.'
    source = tmp_path / 'forms.js'
    source.write_text(INTAKE_SCRIPT, encoding='utf-8')
    runner = Path(__file__).parent / 'client' / 'gui_reload_recovery.cjs'
    result = subprocess.run([node, str(runner), str(source)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'client regressions passed' in result.stdout
