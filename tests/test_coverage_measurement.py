"""Measurement must reach isolated children and reject incompatible evidence."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/measure_coverage.py'
spec = importlib.util.spec_from_file_location('measurement', SCRIPT)
measurement = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measurement)


@pytest.mark.parametrize('field', ['revision', 'sources', 'coverage_version', 'test_exit'])
def test_incompatible_or_failed_run_cannot_be_combined(field):
    expected = {'revision': 'a' * 40, 'sources': {'module.py': 'a' * 64},
                'coverage_version': measurement.VERSION}
    receipt = {**expected, 'test_exit': 0}
    measurement.compatible([receipt], expected)
    receipt[field] = 1 if field == 'test_exit' else 'different'
    with pytest.raises(ValueError):
        measurement.compatible([receipt], expected)


def test_startup_hook_measures_scrubbed_and_isolated_children(tmp_path):
    coverage = pytest.importorskip('coverage')
    venv = tmp_path / 'venv'
    subprocess.run([sys.executable, '-m', 'venv', '--without-pip', str(venv)], check=True)
    python = venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    site = Path(subprocess.check_output([str(python), '-c',
        'import sysconfig; print(sysconfig.get_path("purelib"))'], text=True).strip())
    # Supply the collector only to this disposable interpreter; no shared .pth edits.
    (site / 'collector_dependency.pth').write_text(str(Path(coverage.__file__).parent.parent)
                                                  + '\n', encoding='utf-8')
    target = tmp_path / 'target'
    target.mkdir()
    source = target / 'worker.py'
    source.write_text('import sys\nif "isolated" in sys.argv:\n    value = 1\nelse:\n    value = 2\n',
                      encoding='utf-8')
    config = tmp_path / 'coverage.ini'
    config.write_text(f'[run]\nbranch = true\nparallel = true\nsource = {target.as_posix()}\n'
                      f'data_file = {(tmp_path / ".coverage").as_posix()}\n', encoding='utf-8')
    hook = site / 'harness_measure_coverage.pth'
    hook.write_text(measurement.startup_hook(config), encoding='utf-8')
    clean = {key: os.environ[key] for key in ['SystemRoot'] if key in os.environ}
    for flags, argument in [([], 'normal'), (['-I'], 'isolated')]:
        subprocess.run([str(python), *flags, str(source), argument], env=clean, check=True,
                       capture_output=True, text=True)
    collector = coverage.Coverage(config_file=str(config))
    collector.combine(keep=True)
    collector.save()
    _, statements, _, missing, _ = collector.analysis2(str(source))
    assert set(statements) == {1, 2, 3, 5}
    assert missing == []
    assert len(list(tmp_path.glob('.coverage.*'))) >= 2
    assert 'COVERAGE_PROCESS_START' not in clean
    assert 'COVERAGE_PROCESS_CONFIG' not in clean
