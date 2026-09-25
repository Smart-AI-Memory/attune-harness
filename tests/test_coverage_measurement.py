"""Measurement must reach isolated children and reject incompatible evidence."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/measure_coverage.py'
spec = importlib.util.spec_from_file_location('measurement', SCRIPT)
measurement = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measurement)


@pytest.mark.parametrize('field', ['revision', 'sources', 'input_hashes',
                                   'coverage_version', 'pytest_version', 'test_exit', 'input_drift'])
def test_incompatible_or_failed_run_cannot_be_combined(field):
    expected = {'revision': 'a' * 40, 'sources': {'module.py': 'a' * 64},
                'input_hashes': {'tests/test_example.py': 'b' * 64},
                'coverage_version': measurement.VERSION, 'pytest_version': '9.1.1'}
    receipt = {**expected, 'test_exit': 0, 'input_drift': False}
    measurement.compatible([receipt], expected)
    receipt[field] = 1 if field == 'test_exit' else True if field == 'input_drift' else 'different'
    with pytest.raises(ValueError):
        measurement.compatible([receipt], expected)


def test_legacy_receipt_without_input_binding_is_incompatible():
    expected = {'revision': 'a' * 40, 'sources': {}, 'input_hashes': {},
                'coverage_version': measurement.VERSION, 'pytest_version': '9.1.1'}
    old = {'revision': expected['revision'], 'sources': {},
           'coverage_version': measurement.VERSION, 'test_exit': 0}
    with pytest.raises(ValueError, match='executed input bytes'):
        measurement.compatible([old], expected)


@pytest.mark.parametrize('name', ['tests/test_example.py', 'tests/fixtures/data.json',
                                  'scripts/qualify_platform.py', 'scripts/measure_coverage.py',
                                  'examples/a2a/peer.py', 'experiments/voyage/evaluate.py',
                                  'docs/receipts/sample.json', 'pyproject.toml',
                                  'conftest.py', '.pytest.toml', 'README.md',
                                  'participants.json',
                                  '.github/workflows/publish-pypi.yml',
                                  'plugin/attune-harness/manifest.json',
                                  'AGENTS.md'])
def test_same_revision_changed_execution_input_refuses_compatible_receipt(tmp_path, monkeypatch, name):
    root = tmp_path / 'checkout'
    root.mkdir()
    source = root / 'src/attune_harness'
    source.mkdir(parents=True)
    (source / 'module.py').write_text('VALUE = 1\n', encoding='utf-8')
    for path in ('tests/test_example.py', 'tests/fixtures/data.json',
                 'scripts/qualify_platform.py', 'scripts/measure_coverage.py',
                 'examples/a2a/peer.py', 'experiments/voyage/evaluate.py',
                 'docs/receipts/sample.json', 'pyproject.toml', 'conftest.py',
                 '.pytest.toml', 'README.md', 'participants.json',
                 '.github/workflows/publish-pypi.yml',
                 'plugin/attune-harness/manifest.json', 'AGENTS.md'):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('original\n', encoding='utf-8')
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(root), '-c', 'maintenance.auto=false',
                    '-c', 'commit.gpgsign=false', '-c', 'user.name=Fixture',
                    '-c', 'user.email=fixture@example.invalid',
                    'commit', '-qm', 'Identity baseline'], check=True)
    monkeypatch.setattr(measurement, 'ROOT', root)
    monkeypatch.setattr(measurement, 'SOURCE', source)
    frozen = measurement.identity()
    receipt = {**frozen, 'test_exit': 0, 'input_drift': False}
    measurement.compatible([receipt], frozen)
    (root / name).write_text('changed at same HEAD\n', encoding='utf-8')
    assert measurement.identity()['revision'] == frozen['revision']
    assert measurement.inputs_stable(frozen, source) is False
    with pytest.raises(ValueError, match='executed input bytes'):
        measurement.compatible([receipt], measurement.identity())


@pytest.mark.parametrize('name', ['tests/new_test.py', 'conftest.py', 'pytest.toml',
                                  'docs/new-fixture.md',
                                  'plugin/attune-harness/new.json',
                                  '.github/workflows/other.yml', 'setup.py'])
def test_new_untracked_input_changes_identity(tmp_path, monkeypatch, name):
    root = tmp_path / 'checkout'
    (root / 'tests').mkdir(parents=True)
    (root / 'scripts').mkdir()
    (root / 'examples').mkdir()
    (root / 'experiments').mkdir()
    (root / 'docs').mkdir()
    (root / 'src/attune_harness').mkdir(parents=True)
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    monkeypatch.setattr(measurement, 'ROOT', root)
    first = measurement.input_hashes()
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('new input\n', encoding='utf-8')
    second = measurement.input_hashes()
    assert name not in first
    assert second[name]


def test_symlinked_fixture_is_refused(tmp_path, monkeypatch):
    root = tmp_path / 'checkout'
    (root / 'tests').mkdir(parents=True)
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    target = tmp_path / 'outside.py'
    target.write_text('private = True\n', encoding='utf-8')
    try:
        (root / 'tests/foreign.py').symlink_to(target)
    except OSError:
        pytest.skip('Platform does not permit symlink creation')
    monkeypatch.setattr(measurement, 'ROOT', root)
    with pytest.raises(ValueError, match='symlinks'):
        measurement.input_hashes()


@pytest.mark.parametrize('changed', ['checkout_test', 'installed_package'])
def test_successful_child_with_postrun_input_drift_retains_incompatible_receipt(tmp_path, monkeypatch, changed):
    import attune_harness

    root = tmp_path / 'checkout'
    for part in ('tests', 'scripts', 'examples', 'experiments', 'docs',
                 'src/attune_harness'):
        (root / part).mkdir(parents=True)
    test = root / 'tests/test_example.py'
    test.write_text('def test_example(): pass\n', encoding='utf-8')
    source = root / 'src/attune_harness'
    (source / '__init__.py').write_text('VALUE = 1\n', encoding='utf-8')
    installed = tmp_path / 'installed/attune_harness'
    installed.mkdir(parents=True)
    (installed / '__init__.py').write_text('VALUE = 1\n', encoding='utf-8')
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(root), '-c', 'maintenance.auto=false',
                    '-c', 'commit.gpgsign=false', '-c', 'user.name=Fixture',
                    '-c', 'user.email=fixture@example.invalid',
                    'commit', '-qm', 'Identity baseline'], check=True)
    site = tmp_path / 'site'
    site.mkdir()
    monkeypatch.setattr(measurement, 'ROOT', root)
    monkeypatch.setattr(measurement, 'SOURCE', source)
    monkeypatch.setattr(attune_harness, '__file__', str(installed / '__init__.py'))
    monkeypatch.setattr(measurement, 'sys', SimpleNamespace(prefix='dedicated',
                        base_prefix='base', executable=sys.executable))
    monkeypatch.setattr(measurement, 'sysconfig', SimpleNamespace(get_path=lambda _: str(site)))
    monkeypatch.setattr(measurement, 'report', lambda *_: None)

    def successful_child(argv, **kwargs):
        if changed == 'checkout_test':
            test.write_text('def test_example(): assert False\n', encoding='utf-8')
        else:
            (installed / '__init__.py').write_text('VALUE = 2\n', encoding='utf-8')
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(measurement, 'subprocess', SimpleNamespace(
        run=successful_child, check_output=subprocess.check_output,
        CalledProcessError=subprocess.CalledProcessError, STDOUT=subprocess.STDOUT))
    output = tmp_path / 'result'
    frozen = measurement.identity()
    assert measurement.measure(output, 'full') == 1
    receipt = json.loads((output / 'manifest.json').read_text())
    assert receipt['test_exit'] == 0
    assert receipt['input_drift'] is True
    if changed == 'installed_package':
        assert measurement.identity() == frozen  # Only the installed bytes moved.
    assert not (site / 'harness_measure_coverage.pth').exists()
    with pytest.raises(ValueError, match='input-drifted'):
        measurement.compatible([receipt], receipt)


def test_startup_hook_measures_scrubbed_and_isolated_children(tmp_path, monkeypatch):
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
    monkeypatch.setattr(measurement, 'SOURCE', target)
    config = measurement.configuration(tmp_path, [])
    hook = site / 'harness_measure_coverage.pth'
    hook.write_text(measurement.startup_hook(config), encoding='utf-8')
    clean = {key: os.environ[key] for key in ['SystemRoot'] if key in os.environ}
    for flags, argument in [([], 'normal'), (['-I'], 'isolated')]:
        run = subprocess.run([str(python), *flags, str(source), argument], env=clean, check=True,
                             capture_output=True, text=True)
        assert run.stderr == ''
    unrelated = subprocess.run([str(python), '-c', 'print(42)'], env=clean, check=True,
                               capture_output=True, text=True)
    assert unrelated.stdout == '42\n'
    assert unrelated.stderr == ''
    collector = coverage.Coverage(config_file=str(config))
    collector.combine(keep=True)
    collector.save()
    _, statements, _, missing, _ = collector.analysis2(str(source))
    assert set(statements) == {1, 2, 3, 5}
    assert missing == []
    assert len(list(tmp_path.glob('.coverage.*'))) >= 2
    assert 'COVERAGE_PROCESS_START' not in clean
    assert 'COVERAGE_PROCESS_CONFIG' not in clean
