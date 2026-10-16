"""Pure caller/join controls; no proposed CLI, Git, backend or Windows execution."""
import ast
import copy
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
PS3 = PLATFORM / 'windows_saved_store_build_preflight_v3.ps1'
WORKFLOW = ROOT / '.github/workflows/windows-saved-store-component-build-safe-preflight.yml'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROUTE = load('t2_component_route_pure', PLATFORM / 'windows_saved_store_component_route_v1.py')
PROJECTOR = load('t2_component_existing_projection', PLATFORM / 'project_windows_saved_store_build_v2.py')


@pytest.mark.parametrize('damage', [None, 'sha', 'base', 'head', 'order', 'event'])
def test_actual_event_binding_accepts_current_merge_without_rebinding_K(damage):
    context = {'actual_checkout': '1' * 40, 'parents': ['2' * 40, '3' * 40]}
    event = {'name': 'pull_request', 'sha': '1' * 40, 'base': '2' * 40, 'head': '3' * 40}
    if damage in ('sha', 'base', 'head'):
        event[damage] = 'f' * 40
    elif damage == 'order':
        context['parents'].reverse()
    elif damage == 'event':
        event['name'] = 'workflow_dispatch'
    if damage:
        with pytest.raises(ValueError): ROUTE.event_binding(context, event)
    else:
        result = ROUTE.event_binding(context, event)
        assert result['actual_parents'] == context['parents']
        assert result['component_claim_transfer'] == 'requires_separate_impact_review'


def test_main_push_records_actual_parents_without_claiming_merge():
    context = {'actual_checkout': '1' * 40, 'parents': ['2' * 40]}
    result = ROUTE.event_binding(context, {'name': 'push', 'sha': '1' * 40, 'head': '', 'base': ''})
    assert result['actual_parents'] == ['2' * 40] and result['event'] == 'push'


@pytest.fixture
def protocol_inputs(tmp_path):
    repo, target = tmp_path / 'caller', tmp_path / 'protocol'
    repo.mkdir()
    fixture = ROOT / 'tests/fixtures/windows_saved_store_component_v1/protocol.zip'
    with zipfile.ZipFile(fixture) as archive:
        assert len(archive.infolist()) == 11 and set(archive.namelist()) == set(ROUTE.PROTOCOL)
        for leaf, row in ROUTE.PROTOCOL.items():
            raw = archive.read(leaf)
            assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256']
            path = repo / row['source']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    return repo, target


def test_protocol_materialization_uses_exact11_plain_owned_data(protocol_inputs):
    repo, target = protocol_inputs
    rows = ROUTE.stage_protocol(repo, target, PROJECTOR)
    assert len(rows) == 11 and set(r['path'] for r in rows) == set(ROUTE.PROTOCOL)
    assert PROJECTOR.verify(target, ROUTE.PROTOCOL) == rows


@pytest.mark.parametrize('damage', ['changed', 'missing', 'hardlink'])
def test_protocol_refusal_precedes_new_output(protocol_inputs, damage):
    repo, target = protocol_inputs
    path = repo / ROUTE.PROTOCOL['helper.ps1']['source']
    if damage == 'changed': path.write_bytes(path.read_bytes() + b'\n')
    elif damage == 'missing': path.rename(path.with_suffix('.retained'))
    else:
        import os
        os.link(path, path.with_suffix('.second-link'))
    with pytest.raises((ValueError, OSError)):
        ROUTE.stage_protocol(repo, target, PROJECTOR)
    assert not target.exists()


def test_event_refusal_cannot_reach_stage_or_backend(tmp_path, monkeypatch):
    owned = tmp_path / 'saved-store-build-safe'
    owned.mkdir()
    context = {'actual_checkout': '1' * 40, 'parents': ['2' * 40, '3' * 40]}
    calls = []
    adapter = SimpleNamespace(algorithms=lambda repo: (object(), object(), context),
                              stage=lambda *args: calls.append('stage'))
    monkeypatch.setattr(ROUTE, 'load_adapter', lambda repo: adapter)
    monkeypatch.setattr(ROUTE, 'sys', SimpleNamespace(flags=SimpleNamespace(isolated=True)))
    monkeypatch.setenv('RUNNER_TEMP', str(tmp_path))
    code = ROUTE.execute(tmp_path, owned, 'build', {'name': 'pull_request', 'sha': 'f' * 40,
                                                 'head': '3' * 40, 'base': '2' * 40})
    report = json.loads((owned / 'projection-build.json').read_text())
    assert code == 1 and not calls and report['backend_launch_attempted'] is False
    assert report['status'] == 'component_route_refused' and report['failure_type'] == 'ValueError'


def literal(script, name):
    value, = re.findall(r'\$' + name + " = @'\n(.*?)\n'@", script, re.S)
    return value


def test_capture_csharp_and_startup_query_are_byte_identical():
    old = (PLATFORM / 'windows_saved_store_build_preflight_v2.ps1').read_text()
    new = PS3.read_text()
    assert literal(old, 'query') == literal(new, 'query')
    assert re.findall(r"Add-Type -TypeDefinition @'\n(.*?)\n'@", old, re.S) == re.findall(r"Add-Type -TypeDefinition @'\n(.*?)\n'@", new, re.S)
    old_installed, new_installed = literal(old, 'installedQuery'), literal(new, 'installedQuery')
    assert old_installed.replace('fcf8365fc00aeade30d8bdfa4c4f3e0f5ea869aabb1fbc1ce80466c3b999ae5a',
                                 '6b33976fcc9e7c1bcf276f82c9d4e0ad1d795008a74fb3c4343d86a7573c430a') == new_installed


def test_actual_ps_caller_holds_one_wheel_path_through_startup():
    text = PS3.read_text()
    assert "'--mode','stage'" in text and "'--mode','build'" in text and "'--mode','wheel'" in text
    assert text.index('$wheelLease = [IO.File]::Open(') < text.index("Run-Recorded 'wheel-check'") < text.index("Run-Recorded 'startup-child'") < text.index('$wheelLease.Dispose()')
    assert '[IO.FileShare]::Read)' in text
    assert "'-Wheel',$wheelPath,'-WheelSha256',$wheelHash,'-StartupChild'" in text
    assert 'attune_harness-*.whl' not in text and '$wheel = $Wheel' in text
    assert "'helper.ps1'" in text or "'protocol/helper.ps1'" in text
    for forbidden in ['ExecuteApprovedFixture', 'ExecuteReviewedGuiLease', 'LogonUser', 'DllImport']:
        assert forbidden not in text


def assert_current_C_checkout(name, raw, wanted):
    # Unit data may be an exact CRLF checkout rendering. Runtime admission still
    # hashes raw Git blobs and accepts only the canonical wanted bytes.
    if hashlib.sha256(raw).hexdigest() == wanted:
        return
    path = Path(name)
    assert path.suffix in {'.py', '.ps1', '.yml', '.json', '.lock', '.txt'} or path.name == '.gitattributes'
    assert b'\r\n' in raw and b'\n' not in raw.replace(b'\r\n', b'')
    canonical = raw.replace(b'\r\n', b'\n')
    assert b'\r' not in canonical and hashlib.sha256(canonical).hexdigest() == wanted


def test_new_workflow_has_four_safe_cells_and_current_controller_origins():
    text = WORKFLOW.read_text()
    assert 'branches: [main]' in text and 'pull_request:' in text and 'workflow_dispatch' not in text
    assert 'ref:' not in text and 'fetch-depth: 0' in text and 'persist-credentials: false' in text
    assert text.count('os: [windows-2022, windows-2025]') == 1
    assert text.count("python: ['3.10', '3.12']") == 1 and 'timeout-minutes: 20' in text
    assert 'cancel-in-progress: false' in text and 'contents: read' in text
    assert "'src/attune_harness/**'" not in text
    assert '-ExecuteApprovedFixture' not in text and '-ExecuteReviewedGuiLease' not in text
    assert "windows_saved_store_build_preflight_v3.ps1" in text
    assert 'if: ${{ false }}' in (ROOT / '.github/workflows/windows-saved-store-reviewed-execution.yml').read_text()
    expected_block, = re.findall(r'\$expected = \[ordered\]@\{(.*?)\n          \}', text, re.S)
    expected = dict(re.findall(r"'([^']+)' = '([0-9a-f]{64})'", expected_block))
    assert len(expected) == len({n.casefold() for n in expected})
    for name, wanted in expected.items():
        assert_current_C_checkout(name, (ROOT / name).read_bytes(), wanted)


def test_old_component_coupled_jobs_are_explicitly_retired_with_intact_bodies():
    marker = '    # Retained FFC campaign; fixed-component successor owns new observations.\n    if: ${{ false }}\n'
    archive_path = ROOT / 'tests/fixtures/windows_saved_store_ffc_campaign_v1.zip'
    with zipfile.ZipFile(archive_path) as archive:
        for name in ['.github/workflows/windows-saved-store-platform-build-safe-preflight.yml',
                     '.github/workflows/windows-saved-store-cold-preflight.yml']:
            current = (ROOT / name).read_text()
            assert current.count(marker) == 1
            assert current.replace(marker, '') == archive.read(name).decode('utf-8')


@pytest.mark.parametrize('wrong_platform', [False, True])
def test_exact_new_installed_query_preserves118_and_refuses_wrong_pair(tmp_path, capsys, wrong_platform):
    import base64
    import builtins
    data = ROOT / 'tests/fixtures/windows_saved_store_component_v1'
    value = json.loads((PLATFORM / 'windows_saved_store_source_manifest_v4.json').read_bytes())
    with zipfile.ZipFile(data / 'inputs-bde.zip') as archive:
        members = {name.removeprefix('src/'): archive.read(name) for name in value['modules']}
        members['attune_harness-1.4.0.dist-info/licenses/LICENSE'] = archive.read('LICENSE')
    old_metadata = json.loads((ROOT / 'tests/fixtures/windows_saved_store_wheel_metadata_v1.json').read_text())['members_base64']
    members.update({name: base64.b64decode(raw) for name, raw in old_metadata.items()})
    members['attune_harness-1.4.0.dist-info/METADATA'] = members['attune_harness-1.4.0.dist-info/METADATA'].replace(b'\n', b'\r\n')
    site = tmp_path / 'site'
    for name, raw in members.items():
        target = site / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    def leave(code): raise SystemExit(code)
    replacements = {'sys': SimpleNamespace(argv=['-c', str(PLATFORM / 'windows_saved_store_source_manifest_v4.json')], exit=leave),
                    'os': SimpleNamespace(name='posix' if wrong_platform else 'nt'),
                    'sysconfig': SimpleNamespace(get_paths=lambda: {'purelib': str(site)})}
    original = builtins.__import__
    def scoped_import(name, *args, **kwargs):
        return replacements[name] if name in replacements else original(name, *args, **kwargs)
    with pytest.raises(SystemExit) as result:
        exec(compile(literal(PS3.read_text(), 'installedQuery'), 'component-installed-data-query', 'exec'),
             {'__builtins__': dict(vars(builtins), __import__=scoped_import)})
    observed = json.loads(capsys.readouterr().out)
    assert result.value.code == (42 if wrong_platform else 0)
    assert len(observed['rows']) == 118
    assert [row['path'] for row in observed['rows'] if not row['matched']] == (['attune_harness-1.4.0.dist-info/METADATA'] if wrong_platform else [])
    assert builtins.__import__ is original and observed['package_or_native_imported'] is False


@pytest.mark.parametrize('candidate,name,accepted', [
    (b'a\nb\n', 'input.py', True), (b'a\r\nb\r\n', 'input.py', True),
    (b'a\r\nb\n', 'input.py', False), (b'a\rb\r', 'input.py', False),
    (b'a\nb\nx', 'input.py', False), (b'a\r\nb\r\n', 'input.zip', False),
])
def test_checkout_rendering_does_not_accept_mixed_changed_or_binary_bytes(candidate, name, accepted):
    wanted = hashlib.sha256(b'a\nb\n').hexdigest()
    if accepted: assert_current_C_checkout(name, candidate, wanted)
    else:
        with pytest.raises(AssertionError): assert_current_C_checkout(name, candidate, wanted)


def assert_workflow_self_trigger_filters(text):
    # Parse only GitHub's indentation-bounded trigger mapping. This avoids
    # YAML 1.1 treating the key "on" as a boolean and never inspects job text.
    trigger, = re.findall(r'^on:\n(.*?)(?=^\S|\Z)', text, re.M | re.S)
    events = dict(re.findall(r'^  (pull_request|push):\n(.*?)(?=^  \S|\Z)', trigger, re.M | re.S))
    assert set(events) == {'pull_request', 'push'}
    for block in events.values():
        paths, = re.findall(r'^    paths:\n((?:      - \'[^\n]+\'\n)+)', block, re.M)
        values = re.findall(r"^      - '([^']+)'$", paths, re.M)
        assert '.github/workflows/windows-saved-store-component-build-safe-preflight.yml' in values


@pytest.mark.parametrize('missing_from', [None, 'pull_request', 'push'])
def test_workflow_change_triggers_both_events_and_each_omission_is_detected(missing_from):
    text = WORKFLOW.read_text()
    if missing_from is None:
        assert_workflow_self_trigger_filters(text)
    else:
        event, = re.findall(r'^  ' + missing_from + r':\n(.*?)(?=^  \S|^\S|\Z)', text, re.M | re.S)
        line = "      - '.github/workflows/windows-saved-store-component-build-safe-preflight.yml'\n"
        assert event.count(line) == 1
        changed = text.replace(event, event.replace(line, ''), 1)
        with pytest.raises(AssertionError):
            assert_workflow_self_trigger_filters(changed)
