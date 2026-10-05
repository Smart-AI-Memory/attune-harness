# qualify: platform
"""Mandatory, dependency-free regression checks for the shipped browser script."""
import shutil
import subprocess
from pathlib import Path

from attune_harness.gui_forms import FORM_SCRIPT


def test_shipped_browser_form_regressions(tmp_path):
    node = shutil.which('node')
    assert node, 'GUI client verification requires Node.js; install Node and rerun (no skip).'
    source = tmp_path / 'forms.js'
    source.write_text(FORM_SCRIPT, encoding='utf-8')
    runner = Path(__file__).parent / 'client' / 'gui_forms.cjs'
    result = subprocess.run([node, str(runner), str(source)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'client regressions passed' in result.stdout
