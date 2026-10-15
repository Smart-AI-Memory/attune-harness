"""Pure source/wheel checks: no driver main, account, GUI or native execution."""
import base64
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'experiments/platform' / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = load('t2_account_inputs_pure', 'check_windows_saved_store_account_inputs_v2.py')
driver = load('t2_driver2_pure', 'windows_saved_store_combined_driver_v2.py')


def test_driver_has_only_reviewed_two_literal_changes():
    raw = (ROOT / 'experiments/platform/windows_saved_store_combined_driver_v2.py').read_bytes()
    original = raw.replace(b"NATIVE_SHA = 'ffc46d2f054a7bcf6c95230551a87fb5c73d9992ecebdde9497d2226d0763139'",
                           b"NATIVE_SHA = '0773b47241140cd01a8c27277a735212dc219c507919c8b39a477270560791d6'")
    original = original.replace(b"'experiment': 'combined_saved_store_observations_v2'",
                                b"'experiment': 'combined_saved_store_observations_v1'")
    assert hashlib.sha256(original).hexdigest() == 'e3aa0931328aabd2541b64b21f717c478b8121278dc7d10bb597e0cb0cf41937'
    checker.driver_binding(raw)
    assert driver.AGGREGATE_SECONDS == 150


@pytest.mark.parametrize('payload,digest', [('ORIGINAL_PAYLOAD', 'b233497ffe18973eca3a4db29b2eca7ee5269c4ae2ef78429a8cf10db1ce7355'),
                                           ('NAMESPACE_PAYLOAD', 'f326803457453fccf02b795144ef1a48986c4c7068eef87aa56d21591ddd643e')])
def test_payloads_remain_exact(payload, digest):
    raw = driver.payload_bytes(getattr(driver, payload), digest)
    assert hashlib.sha256(raw).hexdigest() == digest
    compile(raw, payload, 'exec')


def test_exact_manifest_and_changed_manifest_refusal():
    raw = (ROOT / 'experiments/platform/windows_saved_store_source_manifest_v2.json').read_bytes()
    assert len(checker.manifest(raw)['modules']) == 113
    with pytest.raises(ValueError, match='manifest_identity'):
        checker.manifest(raw + b' ')


@pytest.fixture
def sources(tmp_path):
    modules = {}
    tree = []
    for number in range(113):
        path = (f'src/attune_harness/module_{number}.py' if number < 106
                else f'src/attune_voyage_plugin/module_{number}.py')
        raw = f'constant = {number}\n'.encode()
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        modules[path] = {'sha256': hashlib.sha256(raw).hexdigest(), 'git_blob': blob, 'bytes': len(raw)}
        tree.append(f'100644 blob {blob}\t{path}\n')
    for path in ['LICENSE', 'README.md', 'pyproject.toml']:
        raw = (path + '\n').encode()
        (tmp_path / path).write_bytes(raw)
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        modules[path] = {'sha256': hashlib.sha256(raw).hexdigest(), 'git_blob': blob, 'bytes': len(raw)}
        tree.append(f'100644 blob {blob}\t{path}\n')
    return tmp_path, modules, ''.join(tree).encode()


def test_exact_116_source_rows(sources):
    repo, modules, tree = sources
    rows = checker.source_rows(repo, modules, tree)
    assert len(rows) == 116 and all(row['matched'] for row in rows)


@pytest.mark.parametrize('change', ['content', 'crlf', 'missing', 'head_blob', 'extra_tree', 'missing_tree', 'mode'])
def test_116_source_negative_controls(sources, change):
    repo, modules, tree = sources
    first = next(iter(modules))
    if change == 'content':
        (repo / first).write_bytes(b'mutated = True\n')
    elif change == 'crlf':
        (repo / first).write_bytes((repo / first).read_bytes().replace(b'\n', b'\r\n'))
    elif change == 'missing':
        (repo / first).rename(repo / (first + '.retained'))
    elif change == 'head_blob':
        tree = tree.replace(modules[first]['git_blob'].encode(), b'0' * 40, 1)
    elif change == 'extra_tree':
        tree += b'100644 blob ' + b'1' * 40 + b'\tsrc/attune_harness/extra.py\n'
    elif change == 'missing_tree':
        tree = b'\n'.join(tree.split(b'\n')[1:])
    else:
        tree = tree.replace(b'100644', b'120000', 1)
    if change in ('extra_tree', 'missing_tree', 'mode'):
        with pytest.raises(ValueError):
            checker.source_rows(repo, modules, tree)
    else:
        rows = checker.source_rows(repo, modules, tree)
        assert len(rows) == 116 and sum(not row['matched'] for row in rows) == 1
        if change == 'missing':
            assert rows[0]['failure_type'] == 'FileNotFoundError'




def test_driver_changed_refuses_before_any_import():
    raw = (ROOT / 'experiments/platform/windows_saved_store_combined_driver_v2.py').read_bytes()
    with pytest.raises(ValueError, match='driver_identity'):
        checker.driver_binding(raw + b'\nraise AssertionError("must not execute")\n')


def test_retained_report_refused(tmp_path):
    report = tmp_path / 'retained.json'
    report.write_text('keep')
    with pytest.raises(ValueError, match='retained_report'):
        checker.execute(tmp_path, tmp_path / 'missing', tmp_path / 'driver', report)
    assert report.read_text() == 'keep'


RECORD = 'attune_harness-1.4.0.dist-info/RECORD'


def record_bytes(entries):
    rows = []
    for name, raw in entries.items():
        if name != RECORD:
            digest = hashlib.sha256(raw).digest()
            rows.append([name, 'sha256=' + base64.urlsafe_b64encode(digest).decode().rstrip('='), str(len(raw))])
    rows.append([RECORD, '', ''])
    text = io.StringIO()
    csv.writer(text).writerows(rows)
    return text.getvalue().encode()


def wheel_data(sources):
    repo, inputs, _ = sources
    entries = {p.removeprefix('src/'): (repo / p).read_bytes() for p in inputs if p.startswith('src/')}
    entries.update({
        'attune_harness-1.4.0.dist-info/licenses/LICENSE': (repo / 'LICENSE').read_bytes(),
        'attune_harness-1.4.0.dist-info/METADATA': b'Metadata-Version: 2.4\nName: attune-harness\nVersion: 1.4.0\n',
        'attune_harness-1.4.0.dist-info/WHEEL': b'Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n',
        'attune_harness-1.4.0.dist-info/entry_points.txt': b'[console_scripts]\nattune-harness = attune_harness.cli:main\n',
        'attune_harness-1.4.0.dist-info/top_level.txt': b'attune_harness\nattune_voyage_plugin\n',
    })
    entries[RECORD] = record_bytes(entries)
    members = {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
                      'install_destination': 'site-packages/' + name} for name, raw in entries.items()}
    assert len(entries) == 119
    return entries, members


def write_wheel(repo, entries, duplicate=False, symlink=False):
    wheel = repo / 'attune_harness-1.4.0-py3-none-any.whl'
    with zipfile.ZipFile(wheel, 'w') as archive:
        for n, (name, raw) in enumerate(entries.items()):
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = (0o120777 if symlink and n == 0 else 0o100644) << 16
            archive.writestr(info, raw)
        if duplicate:
            name = next(iter(entries))
            archive.writestr(name, entries[name])
    return wheel


def test_exact_119_wheel_members_and_record(sources):
    repo, _, _ = sources
    entries, members = wheel_data(sources)
    rows = checker.wheel_rows(write_wheel(repo, entries), members)
    assert len(rows) == 119 and all(row['matched'] and row['record_matched'] for row in rows)
    assert len([row for row in rows if row['path'].startswith('attune_voyage_plugin/')]) == 7


@pytest.mark.parametrize('extra', [
    't2_unreviewed.pth',
    'attune_harness-1.4.0.data/purelib/t2_unreviewed.pth',
    'attune_harness-1.4.0.data/scripts/t2_startup.exe',
    'attune_harness/injected.pyd',
    'attune_harness/injected.pyc',
    'attune_harness/injected.PY',
    'attune_harness/MODULE_0.PY',  # Windows destination collides with reviewed module_0.py.
    'attune_harness/../t2_escape.py',
    'attune_harness\\t2_alias.py',
])
def test_extra_startup_relocation_extension_and_alias_refused(sources, extra):
    repo, _, _ = sources
    entries, members = wheel_data(sources)
    entries[extra] = b'import unreviewed_startup\n'
    entries[RECORD] = record_bytes(entries)  # Internally valid RECORD cannot authorize extra code.
    with pytest.raises(ValueError):
        checker.wheel_rows(write_wheel(repo, entries), members)


@pytest.mark.parametrize('target', [
    'attune_harness/module_0.py',
    'attune_voyage_plugin/module_106.py',
    'attune_harness-1.4.0.dist-info/entry_points.txt',
    'attune_harness-1.4.0.dist-info/METADATA',
    'attune_harness-1.4.0.dist-info/WHEEL',
    'attune_harness-1.4.0.dist-info/top_level.txt',
    'attune_harness-1.4.0.dist-info/licenses/LICENSE',
])
def test_changed_executable_or_metadata_with_coherent_record_refused(sources, target):
    repo, _, _ = sources
    entries, members = wheel_data(sources)
    entries[target] += b'changed\n'
    entries[RECORD] = record_bytes(entries)
    rows = checker.wheel_rows(write_wheel(repo, entries), members)
    row = next(row for row in rows if row['path'] == target)
    assert row['record_matched'] and not row['matched']


@pytest.mark.parametrize('change', ['missing_member', 'duplicate_zip', 'symlink', 'uppercase_replacement',
                                     'record_hash', 'record_size', 'record_missing', 'record_extra',
                                     'record_duplicate', 'record_self_hash'])
def test_complete_inventory_and_record_negative_controls(sources, change):
    repo, _, _ = sources
    entries, members = wheel_data(sources)
    duplicate = symlink = False
    if change == 'missing_member':
        entries.pop(next(iter(entries)))
    elif change == 'duplicate_zip':
        duplicate = True
    elif change == 'symlink':
        symlink = True
    elif change == 'uppercase_replacement':
        first = next(iter(entries))
        entries[first.upper()] = entries.pop(first)
        entries[RECORD] = record_bytes(entries)
    else:
        rows = list(csv.reader(io.StringIO(entries[RECORD].decode())))
        if change == 'record_hash':
            rows[0][1] = 'sha256=wrong'
        elif change == 'record_size':
            rows[0][2] = '1'
        elif change == 'record_missing':
            rows = rows[1:]
        elif change == 'record_extra':
            rows.append(['attune_harness-1.4.0.data/purelib/hidden.pth', 'sha256=wrong', '1'])
        elif change == 'record_duplicate':
            rows.append(rows[0])
        else:
            rows[-1][1:] = ['sha256=wrong', '1']
        text = io.StringIO()
        csv.writer(text).writerows(rows)
        entries[RECORD] = text.getvalue().encode()
    wheel = write_wheel(repo, entries, duplicate, symlink)
    if change in ('record_hash', 'record_size'):
        rows = checker.wheel_rows(wheel, members)
        assert not all(row['matched'] for row in rows)
    else:
        with pytest.raises(ValueError):
            checker.wheel_rows(wheel, members)
