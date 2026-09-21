"""Observed and frozen identity in the Windows effects backend qualifier."""
import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    'windows_backend_qualifier', ROOT / 'experiments/platform/qualify_windows_effects_backend.py')
qualifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qualifier)


def tree(root, files):
    root.mkdir()
    for name, body in files.items():
        (root / name).write_bytes(body)
    return root


def frozen(files):
    return {name: hashlib.sha256(body.replace(b'\r\n', b'\n')).hexdigest() for name, body in files.items()}


FILES = {'a.py': b'A = 1\n', 'b.py': b'B = 2\n'}


def test_observed_identity_records_hashes_and_compares_with_nothing(tmp_path):
    package, sources = tree(tmp_path / 'installed', FILES), tree(tmp_path / 'source', FILES)
    rows = qualifier.module_identity(package, sources)
    assert {name: row['git_lf_sha256'] for name, row in rows.items()} == frozen(FILES)


def test_observed_identity_follows_a_changed_module(tmp_path):
    changed = {**FILES, 'a.py': b'A = 3\n', 'c.py': b'C = 4\n'}
    package, sources = tree(tmp_path / 'installed', changed), tree(tmp_path / 'source', changed)
    assert set(qualifier.module_identity(package, sources)) == set(changed)


@pytest.mark.parametrize('installed', [{**FILES, 'a.py': b'A = 9\n'}, {'a.py': FILES['a.py']}])
def test_installed_package_must_be_this_checkout_in_either_mode(tmp_path, installed):
    package, sources = tree(tmp_path / 'installed', installed), tree(tmp_path / 'source', FILES)
    with pytest.raises(ValueError, match='this checkout'):
        qualifier.module_identity(package, sources)
    with pytest.raises(ValueError, match='this checkout'):
        qualifier.module_identity(package, sources, frozen(FILES))


def test_frozen_identity_accepts_exactly_the_frozen_bytes(tmp_path):
    package, sources = tree(tmp_path / 'installed', FILES), tree(tmp_path / 'source', FILES)
    assert set(qualifier.module_identity(package, sources, frozen(FILES))) == set(FILES)


@pytest.mark.parametrize('current', [{**FILES, 'a.py': b'A = 3\n'}, {**FILES, 'c.py': b'C = 4\n'}])
def test_frozen_identity_refuses_drift_and_says_not_to_regenerate(tmp_path, current):
    package, sources = tree(tmp_path / 'installed', current), tree(tmp_path / 'source', current)
    with pytest.raises(ValueError, match='frozen source manifest') as refusal:
        qualifier.module_identity(package, sources, frozen(FILES))
    assert 'Do not regenerate' in str(refusal.value) and 'Patrick' in str(refusal.value)


def test_blank_dispatch_input_means_absent():
    assert qualifier.optional_path('') is None
    assert qualifier.optional_path('docs/manifest.json') == Path('docs/manifest.json')
