"""Validate measurement inputs and schedules without collecting timing samples."""

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import random
import sys
from types import ModuleType, SimpleNamespace
import zipfile

import pytest


@pytest.fixture
def helper():
    path = Path(__file__).resolve().parents[1] / 'scripts/measure_inspection_timing.py'
    spec = importlib.util.spec_from_file_location('inspection_timing_controls', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_wheel(path, package, files, version='0.17.0', *, include_wheel=True):
    with zipfile.ZipFile(path, 'w') as wheel:
        for name, value in files.items():
            wheel.writestr(f'{package}/{name}', value)
        metadata = f'{package}-{version}.dist-info/'
        wheel.writestr(metadata + 'METADATA',
                       f'Name: {package.replace("_", "-")}\nVersion: {version}\n')
        if include_wheel:
            wheel.writestr(metadata + 'WHEEL', 'Wheel-Version: 1.0\nTag: py3-none-any\n')


@pytest.fixture
def forms_install(helper, tmp_path, monkeypatch):
    site = tmp_path / 'site-packages'
    package = site / 'attune_forms'
    files = {'__init__.py': 'NAME = "forms"\n',
             'render.py': 'VALUE = 1\n',
             'templates/preview.html': '<p>preview</p>\n'}
    for name, value in files.items():
        path = package / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding='utf-8')
    metadata = site / 'attune_forms-0.17.0.dist-info'
    metadata.mkdir()
    (metadata / 'METADATA').write_text('Name: attune-forms\nVersion: 0.17.0\n')
    (metadata / 'WHEEL').write_text('Wheel-Version: 1.0\nTag: py3-none-any\n')
    distribution = importlib.metadata.PathDistribution(metadata)
    module = ModuleType('attune_forms')
    module.__file__ = str(package / '__init__.py')
    monkeypatch.setitem(sys.modules, 'attune_forms', module)
    original = importlib.metadata.distribution
    monkeypatch.setattr(importlib.metadata, 'distribution',
                        lambda name: distribution if name == 'attune-forms' else original(name))
    wheel = tmp_path / 'forms.whl'
    write_wheel(wheel, 'attune_forms', files)
    return SimpleNamespace(package=package, metadata=metadata, distribution=distribution,
                           module=module, wheel=wheel, files=files)


def preflight_args(helper, forms_install, tmp_path, monkeypatch):
    """Provide a matching Harness artifact so refusals exercise the Forms guard."""
    baseline = tmp_path / 'baseline'
    source = baseline / 'src/attune_harness'
    installed = tmp_path / 'harness-site/attune_harness'
    for root in (source, installed):
        root.mkdir(parents=True)
        (root / '__init__.py').write_text('NAME = "harness"\n')
    metadata = installed.parent / 'attune_harness-1.5.0.dist-info'
    metadata.mkdir()
    (metadata / 'METADATA').write_text('Name: attune-harness\nVersion: 1.5.0\n')
    (metadata / 'WHEEL').write_text('Wheel-Version: 1.0\nTag: py3-none-any\n')
    distribution = importlib.metadata.PathDistribution(metadata)
    module = ModuleType('attune_harness')
    module.__file__ = str(installed / '__init__.py')
    monkeypatch.setitem(sys.modules, 'attune_harness', module)
    monkeypatch.setattr(importlib.metadata, 'distribution',
                        lambda name: forms_install.distribution if name == 'attune-forms'
                        else distribution)
    monkeypatch.setattr(helper, 'git', lambda root, *args:
                        b'pinned-revision\n' if args[0] == 'rev-parse' else b'')
    monkeypatch.setattr(helper, 'prepare',
                        lambda *args: pytest.fail('Measurement setup must not start'))
    wheel = tmp_path / 'harness.whl'
    write_wheel(wheel, 'attune_harness', {'__init__.py': 'NAME = "harness"\n'}, '1.5.0')
    return argparse.Namespace(baseline=baseline, revision='pinned-revision', wheel=wheel,
                              forms_wheel=forms_install.wheel, output=tmp_path / 'output',
                              repetitions=20, cold_repetitions=10, seed=20261022)


def test_forms_identity_covers_import_origin_artifact_and_package_data(helper, forms_install):
    identity = helper.forms_identity(forms_install.wheel)
    assert identity['version'] == '0.17.0'
    assert identity['imported_origin'] == str((forms_install.package / '__init__.py').resolve())
    assert identity['installed_package'] == str(forms_install.package.resolve())
    assert set(identity['files']) == set(forms_install.files)
    assert identity['files']['templates/preview.html'] == hashlib.sha256(
        forms_install.files['templates/preview.html'].encode()).hexdigest()
    assert identity['wheel_sha256'] == hashlib.sha256(forms_install.wheel.read_bytes()).hexdigest()


@pytest.mark.parametrize('case', ['editable', 'no-wheel', 'modified-python', 'modified-data',
                                 'extra-file', 'missing-file', 'shadowed-origin',
                                 'mismatched-artifact', 'wrong-version', 'artifact-no-wheel'])
def test_forms_refusals_precede_output_creation(helper, forms_install, tmp_path, monkeypatch, case):
    args = preflight_args(helper, forms_install, tmp_path, monkeypatch)
    if case == 'editable':
        (forms_install.metadata / 'direct_url.json').write_text(json.dumps(
            {'dir_info': {'editable': True}, 'url': 'file:///disposable-source'}))
    elif case == 'no-wheel':
        (forms_install.metadata / 'WHEEL').unlink()
    elif case == 'modified-python':
        (forms_install.package / 'render.py').write_text('VALUE = 2\n')
    elif case == 'modified-data':
        (forms_install.package / 'templates/preview.html').write_text('<p>changed</p>\n')
    elif case == 'extra-file':
        (forms_install.package / 'unrecorded.py').write_text('VALUE = 1\n')
    elif case == 'missing-file':
        (forms_install.package / 'render.py').unlink()
    elif case == 'shadowed-origin':
        shadow = tmp_path / 'shadow/__init__.py'
        shadow.parent.mkdir()
        shadow.write_text(forms_install.files['__init__.py'])
        forms_install.module.__file__ = str(shadow)
    elif case == 'mismatched-artifact':
        write_wheel(forms_install.wheel, 'attune_forms',
                    {**forms_install.files, 'render.py': 'VALUE = 2\n'})
    elif case == 'wrong-version':
        write_wheel(forms_install.wheel, 'attune_forms', forms_install.files, '0.18.0')
    else:
        write_wheel(forms_install.wheel, 'attune_forms', forms_install.files, include_wheel=False)
    with pytest.raises(ValueError, match='attune-forms'):
        helper.measure(args)
    assert not args.output.exists()


def test_forms_artifact_is_retained_and_copy_drift_is_refused(helper, forms_install, tmp_path):
    identity = helper.forms_identity(forms_install.wheel)
    output = tmp_path / 'retained'
    output.mkdir()
    retained = helper.retain_forms_wheel(forms_install.wheel, output, identity['wheel_sha256'])
    assert retained.read_bytes() == forms_install.wheel.read_bytes()
    assert helper.forms_identity(retained) == identity
    write_wheel(forms_install.wheel, 'attune_forms',
                {**forms_install.files, 'render.py': 'VALUE = 2\n'})
    with pytest.raises(ValueError, match='changed while retaining'):
        helper.retain_forms_wheel(forms_install.wheel, output, identity['wheel_sha256'])


def test_worker_refuses_identity_drift_before_loading_timed_targets(helper, forms_install, monkeypatch):
    monkeypatch.setattr(helper, 'load_targets',
                        lambda: pytest.fail('Timed targets must not load after identity drift'))
    with pytest.raises(ValueError, match='Worker attune-forms identity'):
        helper.worker({'forms_wheel': str(forms_install.wheel), 'forms_identity_digest': 'wrong'})


@pytest.mark.parametrize('repetitions', [2, 3, 19, 20, 21])
def test_warm_pairs_are_balanced_separately_from_the_first_pair(helper, repetitions):
    schedule = helper.pair_schedule(repetitions, 20261022)
    assert len(schedule) == repetitions + 1
    assert all(len(pair) == 2 and set(pair) == {False, True} for pair in schedule)
    warm_first = [pair[0] for pair in schedule[1:]]
    assert abs(warm_first.count(True) - warm_first.count(False)) <= 1
    if repetitions == 20:
        assert warm_first.count(True) == warm_first.count(False) == 10
    assert schedule[0] == helper.pair_schedule(2, 20261022)[0]


def test_pair_schedule_is_seeded_without_changing_global_random_state(helper):
    before = random.getstate()
    assert helper.pair_schedule(20, 20261022) == helper.pair_schedule(20, 20261022)
    assert helper.pair_schedule(20, 0)[1:] != helper.pair_schedule(20, 1)[1:]
    assert random.getstate() == before
