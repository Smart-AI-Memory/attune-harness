# qualify: platform
"""Mandatory, dependency-free regression checks for the shipped browser script."""
import shutil
import subprocess
from pathlib import Path

import pytest
from attune_harness.gui_forms import FORM_SCRIPT
from attune_harness.gui_forms_intake import INTAKE_SCRIPT
from attune_harness.gui import INTAKE_BOOTSTRAP


@pytest.mark.parametrize('script,runner_name', [(FORM_SCRIPT, 'gui_forms.cjs'), (INTAKE_SCRIPT, 'gui_forms_intake.cjs')])
def test_shipped_browser_form_regressions(tmp_path, script, runner_name):
    node = shutil.which('node')
    assert node, 'GUI client verification requires Node.js; install Node and rerun (no skip).'
    source = tmp_path / 'forms.js'
    source.write_text(script, encoding='utf-8')
    runner = Path(__file__).parent / 'client' / runner_name
    result = subprocess.run([node, str(runner), str(source)], capture_output=True, text=True, timeout=30)
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
