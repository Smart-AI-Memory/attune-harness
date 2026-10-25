"""The declared minimum and live package jobs share one compatibility policy."""

from pathlib import Path
import tomllib

from packaging.specifiers import SpecifierSet
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def project():
    return tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))['project']


@pytest.mark.parametrize('version,accepted', [
    ('3.10', False), ('3.11', False), ('3.12', True), ('3.12.13', True),
])
def test_declared_interpreter_minimum(version, accepted):
    assert (version in SpecifierSet(project()['requires-python'])) is accepted


def test_supported_classifier_matches_current_minimum():
    metadata = project()
    assert metadata['requires-python'] == '>=3.12'
    assert 'Programming Language :: Python :: 3.12' in metadata['classifiers']
    assert 'Programming Language :: Python :: 3.10' not in metadata['classifiers']
    assert 'Programming Language :: Python :: 3.11' not in metadata['classifiers']


def workflow(name):
    return yaml.safe_load((ROOT / '.github/workflows' / name).read_text(encoding='utf-8'))['jobs']


def cells(job):
    matrix = job['strategy']['matrix']
    values = [(os_name, version) for os_name in matrix.get('os', [])
              for version in matrix.get('python', [])]
    values.extend((row['os'], row['python']) for row in matrix.get('include', []))
    assert len(values) == len(set(values)), 'Duplicate OS/interpreter job after dropping older Python'
    return set(values)


def test_installed_and_source_jobs_keep_existing_platforms_at_the_new_minimum():
    jobs = workflow('qualification.yml')
    assert cells(jobs['installed-library']) == {
        (name, '3.12') for name in ['ubuntu-latest', 'macos-latest', 'windows-2022', 'windows-2025']}
    assert cells(jobs['full-suite']) == {
        (name, '3.12') for name in ['ubuntu-latest', 'windows-2022', 'windows-2025']}
    assert next(step['with']['python-version'] for step in jobs['doc-links']['steps']
                if 'setup-python' in step.get('uses', '')) == '3.12'


def test_supplemental_and_native_jobs_keep_their_platform_profiles():
    coverage = workflow('coverage.yml')['measure']
    assert set(coverage['strategy']['matrix']['os']) == {'ubuntu-latest', 'macos-latest', 'windows-latest'}
    assert next(step['with']['python-version'] for step in coverage['steps']
                if 'setup-python' in step.get('uses', '')) == '3.12'
    assert cells(workflow('native-memory-offline.yml')['native-memory-offline']) == {
        (name, '3.12') for name in ['ubuntu-latest', 'windows-2022', 'windows-2025']}
    assert cells(workflow('windows-effects-backend.yml')['installed-owner-journey']) == {
        (name, '3.12') for name in ['windows-2022', 'windows-2025']}
