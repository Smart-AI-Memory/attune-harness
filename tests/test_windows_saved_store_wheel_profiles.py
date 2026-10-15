"""Finite wheel-profile data controls; no backend, PowerShell or account execution."""
import ast
import base64
import builtins
import copy
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
from types import SimpleNamespace
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / 'experiments/platform'
MANIFEST = PLATFORM / 'windows_saved_store_source_manifest_v3.json'
FIXTURE = ROOT / 'tests/fixtures/windows_saved_store_wheel_metadata_v1.json'
spec = importlib.util.spec_from_file_location('t2_wheel_profiles_data', PLATFORM / 'check_windows_saved_store_account_inputs_v3.py')
CHECKER = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CHECKER)
INVENTORY = CHECKER.manifest(MANIFEST.read_bytes())
METADATA = 'attune_harness-1.4.0.dist-info/METADATA'
RECORD = 'attune_harness-1.4.0.dist-info/RECORD'
PAIR = {METADATA, RECORD}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def record_bytes(members):
    original = base64.b64decode(json.loads(FIXTURE.read_text())['members_base64'][RECORD])
    order = [row[0] for row in csv.reader(io.StringIO(original.decode())) if row[0] != RECORD]
    names = [name for name in order if name in members] + sorted(set(members) - set(order) - {RECORD})
    rows = []
    for name in names:
        raw = members[name]
        encoded = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip('=')
        rows.append(f'{name},sha256={encoded},{len(raw)}\n')
    rows.append(f'{RECORD},,\n')
    return ''.join(rows).encode()


def frozen_members(platform):
    metadata = json.loads(FIXTURE.read_text())['members_base64']
    assert len(metadata) == 5
    members = {name: base64.b64decode(raw) for name, raw in metadata.items()}
    members.update({name.removeprefix('src/'): (ROOT / name).read_bytes() for name in INVENTORY['modules']})
    members['attune_harness-1.4.0.dist-info/licenses/LICENSE'] = (ROOT / 'LICENSE').read_bytes()
    assert len(members) == 119 and set(members) == set(INVENTORY['wheel_members'])
    for name, raw in members.items():
        expected = INVENTORY['wheel_members'][name]
        assert digest(raw) == expected['sha256'] and len(raw) == expected['bytes']
    assert record_bytes(members) == members[RECORD]
    if platform == 'nt':
        assert b'\r' not in members[METADATA]
        members[METADATA] = members[METADATA].replace(b'\n', b'\r\n')
        members[RECORD] = record_bytes(members)
        for name in PAIR:
            expected = INVENTORY['wheel_platform_pairs']['nt_crlf'][name]
            assert digest(members[name]) == expected['sha256'] and len(members[name]) == expected['bytes']
    return members


def wheel(tmp_path, members, duplicate=None):
    path = tmp_path / 'attune_harness-1.4.0-py3-none-any.whl'
    with zipfile.ZipFile(path, 'w') as archive:
        for name, raw in members.items():
            archive.writestr(name, raw)
        if duplicate is not None:
            archive.writestr(duplicate, members[duplicate])
    return path


def expected(monkeypatch, platform):
    monkeypatch.setattr(CHECKER, 'os', SimpleNamespace(name=platform))
    return CHECKER.platform_members(INVENTORY)


@pytest.mark.parametrize('platform,profile', [('posix', 'posix_lf'), ('nt', 'nt_crlf')])
def test_frozen_positive_pair_and_complete_record(tmp_path, monkeypatch, platform, profile):
    name, members = expected(monkeypatch, platform)
    assert name == profile
    rows = CHECKER.wheel_rows(wheel(tmp_path, frozen_members(platform)), members)
    assert len(rows) == 119 and all(row['matched'] and row['record_matched'] for row in rows)
    assert len(set(INVENTORY['wheel_members']) - PAIR) == 117


@pytest.mark.parametrize('candidate,platform', [('posix', 'nt'), ('nt', 'posix')])
def test_wrong_platform_refuses_exact_other_pair(tmp_path, monkeypatch, candidate, platform):
    _, members = expected(monkeypatch, platform)
    rows = CHECKER.wheel_rows(wheel(tmp_path, frozen_members(candidate)), members)
    assert all(row['record_matched'] for row in rows)
    assert {row['path'] for row in rows if not row['matched']} == PAIR


@pytest.mark.parametrize('metadata_platform,record_platform', [('posix', 'nt'), ('nt', 'posix')])
@pytest.mark.parametrize('platform', ['posix', 'nt'])
def test_mixed_pairs_refuse(tmp_path, monkeypatch, metadata_platform, record_platform, platform):
    candidate = frozen_members(metadata_platform)
    candidate[RECORD] = frozen_members(record_platform)[RECORD]
    _, members = expected(monkeypatch, platform)
    rows = CHECKER.wheel_rows(wheel(tmp_path, candidate), members)
    assert not all(row['matched'] for row in rows)
    assert not next(row for row in rows if row['path'] == METADATA)['record_matched']


@pytest.mark.parametrize('platform', ['posix', 'nt'])
@pytest.mark.parametrize('change', ['metadata_byte', 'third_newline_variant', 'other117_byte'])
def test_valid_record_cannot_admit_unpinned_bytes(tmp_path, monkeypatch, platform, change):
    candidate = frozen_members(platform)
    name = METADATA if change != 'other117_byte' else 'attune_harness/__init__.py'
    candidate[name] += b'x' if change != 'third_newline_variant' else b'\r\r\n'
    candidate[RECORD] = record_bytes(candidate)
    _, members = expected(monkeypatch, platform)
    rows = CHECKER.wheel_rows(wheel(tmp_path, candidate), members)
    assert all(row['record_matched'] for row in rows)
    assert {row['path'] for row in rows if not row['matched']} == {name, RECORD}


@pytest.mark.parametrize('platform', ['posix', 'nt'])
def test_record_one_byte_cannot_be_ignored(tmp_path, monkeypatch, platform):
    candidate = frozen_members(platform)
    candidate[RECORD] += b'\n'
    _, members = expected(monkeypatch, platform)
    with pytest.raises(ValueError, match='wheel_record_row_refused'):
        CHECKER.wheel_rows(wheel(tmp_path, candidate), members)


@pytest.mark.parametrize('name', ['startup.pth', 'attune_harness-1.4.0.data/purelib/startup.pth',
                                  'attune_harness/extra.pyd', 'attune_harness/extra.pyc',
                                  'ATTUNE_HARNESS/__init__.py', 'attune_harness/extra.py'])
def test_valid_record_cannot_admit_extra_executable_routes(tmp_path, monkeypatch, name):
    candidate = frozen_members('nt')
    candidate[name] = b'extra startup code\n'
    candidate[RECORD] = record_bytes(candidate)
    _, members = expected(monkeypatch, 'nt')
    with pytest.raises(ValueError):
        CHECKER.wheel_rows(wheel(tmp_path, candidate), members)


def test_duplicate_destination_refused(tmp_path, monkeypatch):
    candidate = frozen_members('nt')
    _, members = expected(monkeypatch, 'nt')
    with pytest.warns(UserWarning, match='Duplicate name'):
        path = wheel(tmp_path, candidate, duplicate='attune_harness/__init__.py')
    with pytest.raises(ValueError, match='wheel_destination_collision'):
        CHECKER.wheel_rows(path, members)


def test_unknown_platform_refused(monkeypatch):
    with pytest.raises(ValueError, match='wheel_platform_refused'):
        expected(monkeypatch, 'unknown')


def test_manifest_hash_and_profile_shape_are_finite(monkeypatch):
    with pytest.raises(ValueError, match='manifest_identity_refused'):
        CHECKER.manifest(MANIFEST.read_bytes() + b' ')
    for change in ['unknown_profile', 'missing_profile', 'missing_pair_member', 'third_pair_member', 'wrong_destination']:
        value = copy.deepcopy(INVENTORY)
        pairs = value['wheel_platform_pairs']
        if change == 'unknown_profile': pairs['unknown'] = copy.deepcopy(pairs['nt_crlf'])
        if change == 'missing_profile': pairs.pop('nt_crlf')
        if change == 'missing_pair_member': pairs['nt_crlf'].pop(RECORD)
        if change == 'third_pair_member': pairs['nt_crlf']['startup.pth'] = copy.deepcopy(pairs['nt_crlf'][METADATA])
        if change == 'wrong_destination': pairs['nt_crlf'][METADATA]['install_destination'] = 'other/METADATA'
        raw = json.dumps(value).encode()
        with monkeypatch.context() as patch:
            patch.setattr(CHECKER, 'MANIFEST_SHA', digest(raw))
            with pytest.raises(ValueError): CHECKER.manifest(raw)


def test_one_source_drift_still_refused(tmp_path):
    inputs = {**INVENTORY['modules'], **INVENTORY['build_inputs']}
    tree = ''.join(f"100644 blob {row['git_blob']}\t{name}\n" for name, row in inputs.items()).encode()
    for name in inputs:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / name).read_bytes())
    (tmp_path / 'src/attune_harness/__init__.py').write_bytes(b'changed\n')
    rows = CHECKER.source_rows(tmp_path, inputs, tree)
    assert len(rows) == 116
    assert [row['path'] for row in rows if not row['matched']] == ['src/attune_harness/__init__.py']


@pytest.mark.parametrize('platform', ['posix', 'nt'])
@pytest.mark.parametrize('wrong', [False, True])
def test_installed118_uses_same_profile_without_shared_import_mutation(tmp_path, capsys, platform, wrong):
    candidate = frozen_members(platform)
    site = tmp_path / 'site'
    for name, raw in candidate.items():
        path = site / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw if name != RECORD else b'installer rewrote record')
    script = (PLATFORM / 'windows_saved_store_build_preflight_v2.ps1').read_text()
    query, = re.findall(r"\$installedQuery = @'\n(.*?)\n'@", script, re.S)
    selected = ('nt' if platform == 'posix' else 'posix') if wrong else platform
    def query_exit(code):
        raise SystemExit(code)
    fake_sys = SimpleNamespace(argv=['-c', str(MANIFEST)], exit=query_exit)
    fake = {'sys': fake_sys, 'sysconfig': SimpleNamespace(get_paths=lambda: {'purelib': str(site)}),
            'os': SimpleNamespace(name=selected)}
    real_import = builtins.__import__
    def query_import(name, *args, **kwargs):
        return fake[name] if name in fake else real_import(name, *args, **kwargs)
    with pytest.raises(SystemExit) as result:
        exec(compile(query, 'profile-installed-query', 'exec'), {'__builtins__': dict(vars(builtins), __import__=query_import)})
    observed = json.loads(capsys.readouterr().out)
    assert result.value.code == (42 if wrong else 0)
    assert observed['wheel_platform'] == selected
    assert len(observed['rows']) == 118
    assert [row['path'] for row in observed['rows'] if not row['matched']] == ([METADATA] if wrong else [])
    assert observed['installer_rewritten_record_compared'] is False and observed['package_or_native_imported'] is False
    assert builtins.__import__ is real_import


def test_projector_delta_is_only_manifest_binding_and_csharp_unchanged():
    old = ast.parse((PLATFORM / 'project_windows_saved_store_build_v1.py').read_text())
    new = ast.parse((PLATFORM / 'project_windows_saved_store_build_v2.py').read_text())
    for tree in [old, new]:
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'MANIFEST_SHA' for t in node.targets):
                node.value = ast.Constant(value='same-reviewed-source-projection')
    assert ast.dump(old) == ast.dump(new)
    scripts = [(PLATFORM / f'windows_saved_store_build_preflight_v{n}.ps1').read_text() for n in [1, 2]]
    blocks = [re.findall(r"Add-Type -TypeDefinition @'\n(.*?)\n'@", script, re.S) for script in scripts]
    assert len(blocks[0]) == len(blocks[1]) == 1 and blocks[0] == blocks[1]
    pins = dict(re.findall(r"'([^']+)' = '([0-9a-f]{64})'", scripts[1]))
    for name, expected_sha in pins.items():
        assert digest((ROOT / name).read_bytes()) == expected_sha
    assert 'if: ${{ false }}' in (ROOT / '.github/workflows/windows-saved-store-reviewed-execution.yml').read_text()


@pytest.mark.parametrize('change', ['manifest', 'platform'])
def test_installed_query_refuses_changed_manifest_or_unknown_platform(tmp_path, change):
    script = (PLATFORM / 'windows_saved_store_build_preflight_v2.ps1').read_text()
    query, = re.findall(r"\$installedQuery = @'\n(.*?)\n'@", script, re.S)
    path = tmp_path / 'manifest.json'
    path.write_bytes(MANIFEST.read_bytes() + (b' ' if change == 'manifest' else b''))
    fake = {'sys': SimpleNamespace(argv=['-c', str(path)]),
            'os': SimpleNamespace(name='unknown' if change == 'platform' else 'posix')}
    real_import = builtins.__import__
    def query_import(name, *args, **kwargs):
        return fake[name] if name in fake else real_import(name, *args, **kwargs)
    with pytest.raises(ValueError, match='manifest_identity_refused' if change == 'manifest' else 'wheel_platform_refused'):
        exec(compile(query, 'profile-installed-query-negative', 'exec'), {'__builtins__': dict(vars(builtins), __import__=query_import)})
    assert builtins.__import__ is real_import
