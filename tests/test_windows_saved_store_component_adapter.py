"""Pure frozen-data controls. Never run Git, a backend, proof or Windows APIs."""
import ast
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / 'experiments/platform'
DATA = ROOT / 'tests/fixtures/windows_saved_store_component_v1'
spec = importlib.util.spec_from_file_location('t2_component_adapter', PLATFORM / 'windows_saved_store_component_adapter_v1.py')
ADAPTER = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ADAPTER)
MANIFEST = (PLATFORM / 'windows_saved_store_source_manifest_v4.json').read_bytes()
DRIVER = (PLATFORM / 'windows_saved_store_combined_driver_v3.py').read_bytes()
VALUE = ADAPTER.inventory(MANIFEST)
INPUTS = {**VALUE['modules'], **VALUE['build_inputs']}
METADATA = 'attune_harness-1.4.0.dist-info/METADATA'
RECORD = ADAPTER.RECORD


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()


def frozen_inputs():
    path = DATA / 'inputs-bde.zip'
    assert digest(path.read_bytes()) == 'c0c4ec0f8c274ec0782bc19844bf7a5cbdb600c4cb678ea70e3ad8773d703fe4'
    with zipfile.ZipFile(path) as archive:
        assert len(archive.infolist()) == 116 and set(archive.namelist()) == set(INPUTS)
        return {name: archive.read(name) for name in INPUTS}


class GitData:
    """Finite fake read-only Git transport; actual fixed bytes, no command run."""
    def __init__(self):
        self.inputs = frozen_inputs()
        self.objects = {row['git_blob']: self.inputs[name] for name, row in INPUTS.items()}
        self.controls = {}
        for name in ADAPTER.CONTROL_INPUTS:
            raw = (PLATFORM / name).read_bytes()
            self.controls['experiments/platform/' + name] = blob(raw)
            self.objects[blob(raw)] = raw
        self.head, self.tree = '1' * 40, '2' * 40
        self.fixed_tree = ADAPTER.K_TREE
        self.source_tree = (DATA / 'tree.txt').read_bytes()
        self.calls = []
        self.shallow_boundary = False
        self.raw_commit_override = None

    def __call__(self, caller, *args):
        self.calls.append(args)
        if args == ('rev-parse', 'HEAD'):
            return self.head.encode() + b'\n'
        if args == ('rev-parse', self.head + '^{tree}'):
            return self.tree.encode() + b'\n'
        if args == ('rev-list', '--parents', '-n', '1', self.head):
            if self.shallow_boundary:
                return self.head.encode() + b'\n'
            return (self.head + ' ' + '3' * 40 + ' ' + '4' * 40 + '\n').encode()
        if args == ('cat-file', 'commit', self.head):
            if self.raw_commit_override is not None:
                return self.raw_commit_override
            return ('tree ' + self.tree + '\nparent ' + '3' * 40 + '\nparent ' + '4' * 40
                    + '\nauthor Author <author@example.invalid> 0 +0000\n'
                    + 'committer Committer <committer@example.invalid> 0 +0000\n\nmessage\n').encode()
        if args == ('rev-parse', ADAPTER.K_COMMIT + '^{tree}'):
            return self.fixed_tree.encode() + b'\n'
        if args == ('ls-tree', '-r', ADAPTER.K_COMMIT, '--', *ADAPTER.SOURCE_PATHS):
            return self.source_tree
        if len(args) == 5 and args[:4] == ('ls-tree', '-z', self.head, '--'):
            name = args[4]
            return ('100644 blob ' + self.controls[name] + '\t' + name).encode() + b'\0'
        if args[:2] == ('cat-file', 'blob'):
            if args[2] not in self.objects:
                raise ValueError('missing_fixed_blob')
            return self.objects[args[2]]
        raise AssertionError(('Unexpected command', args))


@pytest.fixture
def route(tmp_path, monkeypatch):
    root = tmp_path.resolve()
    caller = root / 'current-C'
    caller.mkdir()
    transport = GitData()
    monkeypatch.setattr(ADAPTER, '_git', transport)
    return caller, root / 'fixed-K', transport


def stage(route):
    caller, component, _ = route
    return ADAPTER.stage(caller, component, MANIFEST, DRIVER)


def test_positive_full116_and_distinct_current_provenance(route):
    result = stage(route)
    assert result['K']['commit'] == ADAPTER.K_COMMIT
    assert result['C']['actual_checkout'] == '1' * 40
    assert len(result['K']['source_rows']) == 116
    assert all(row['matched'] for row in result['K']['source_rows'])
    assert len(result['C']['consumed_controls']) == 2
    assert result['account_execution'] is False and result['installed_admission'] is False
    assert result['C']['product_impact_review'] == 'pending_explicit_comparison'
    assert result['C']['event_binding'] == 'not_implemented_by_this_data_adapter'


def test_unconsumed_current_product_change_keeps_same_K_and_records_new_C(route):
    caller, component, transport = route
    first = stage(route)
    transport.head, transport.tree = '5' * 40, '6' * 40
    (caller / 'unconsumed-product.txt').write_bytes(b'a later unrelated product file')
    second = ADAPTER.stage(caller, component.parent / 'same-K-next-C', MANIFEST, DRIVER)
    assert first['K']['source_rows'] == second['K']['source_rows']
    assert first['C']['actual_checkout'] != second['C']['actual_checkout']
    assert first['C']['actual_tree'] != second['C']['actual_tree']
    assert first['C']['consumed_controls'] == second['C']['consumed_controls']
    assert second['C']['product_impact_review'] == 'pending_explicit_comparison'


@pytest.mark.parametrize('where', ['equal', 'inside', 'ancestor'])
def test_mixed_component_and_caller_roots_refused(route, where):
    caller, component, _ = route
    candidate = {'equal': caller, 'inside': caller / 'component', 'ancestor': caller.parent}[where]
    with pytest.raises(ValueError, match='component_caller_root_mix_refused'):
        ADAPTER.stage(caller, candidate, MANIFEST, DRIVER)
    assert not component.exists()


def test_missing_fixed_blob_never_falls_back_to_current_source(route):
    caller, component, transport = route
    name = 'src/attune_harness/windows_effects.py'
    target = caller / name
    target.parent.mkdir(parents=True)
    target.write_bytes(transport.inputs[name])
    del transport.objects[INPUTS[name]['git_blob']]
    with pytest.raises(ValueError, match='missing_fixed_blob'):
        stage(route)
    assert not component.exists() and target.read_bytes() == transport.inputs[name]
    assert not any('HEAD' in args and 'ls-tree' in args for args in transport.calls)


def test_moving_C_bytes_cannot_replace_fixed_K_blob(route):
    _, component, transport = route
    name = 'src/attune_harness/windows_effects.py'
    transport.objects[INPUTS[name]['git_blob']] = b'moving caller SRC bytes'
    with pytest.raises(ValueError, match='fixed_blob_identity_refused'):
        stage(route)
    assert not component.exists()


@pytest.mark.parametrize('change', ['commit_tree', 'source_tree'])
def test_fixed_tree_identity_cannot_follow_C(route, change):
    _, component, transport = route
    if change == 'commit_tree':
        transport.fixed_tree = transport.tree
    else:
        transport.source_tree += b'100644 blob ' + b'0' * 40 + b'\tsrc/attune_harness/extra.py\n'
    with pytest.raises(ValueError, match='fixed_(commit|source)_tree_refused'):
        stage(route)
    assert not component.exists()


def test_changed_consumed_C_code_refused_before_source_writes(route):
    _, component, transport = route
    name = next(iter(transport.controls))
    changed = b'raise RuntimeError("unreviewed controller code")\n'
    transport.objects[transport.controls[name]] = changed
    with pytest.raises(ValueError, match='caller_control_identity_refused'):
        stage(route)
    assert not component.exists()


def test_FFC_driver_is_not_admitted_for_EC(route):
    caller, component, _ = route
    old = (PLATFORM / 'windows_saved_store_combined_driver_v2.py').read_bytes()
    with pytest.raises(ValueError, match='driver_component_mismatch'):
        ADAPTER.stage(caller, component, MANIFEST, old)
    assert not component.exists()


def test_driver_extra_code_is_not_admitted_even_with_EC_binding(route):
    caller, component, _ = route
    with pytest.raises(ValueError, match='driver_identity_refused'):
        ADAPTER.stage(caller, component, MANIFEST, DRIVER + b'\nprint("unreviewed")\n')
    assert not component.exists()


def test_manifest_override_refused(route):
    caller, component, _ = route
    value = json.loads(MANIFEST)
    value['modules']['src/attune_harness/windows_effects.py']['sha256'] = 'f' * 64
    with pytest.raises(ValueError, match='fixed_component_manifest_refused'):
        ADAPTER.stage(caller, component, json.dumps(value).encode(), DRIVER)
    assert not component.exists()


def test_retained_component_is_not_rewritten(route):
    caller, component, _ = route
    component.mkdir()
    sentinel = component / 'old-receipt.json'
    sentinel.write_bytes(b'retained')
    with pytest.raises(ValueError, match='retained_component_refused'):
        stage(route)
    assert sentinel.read_bytes() == b'retained'


def test_driver_delta_is_only_native_binding_and_receipt_revision():
    old = ast.parse((PLATFORM / 'windows_saved_store_combined_driver_v2.py').read_bytes())
    new = ast.parse(DRIVER)
    replacements = 0
    for node in ast.walk(old):
        if isinstance(node, ast.Constant) and node.value in (
                'ffc46d2f054a7bcf6c95230551a87fb5c73d9992ecebdde9497d2226d0763139',
                'combined_saved_store_observations_v2'):
            node.value = {'ffc46d2f054a7bcf6c95230551a87fb5c73d9992ecebdde9497d2226d0763139':
                          ADAPTER.NATIVE_SHA, 'combined_saved_store_observations_v2':
                          'combined_saved_store_observations_v3'}[node.value]
            replacements += 1
    assert replacements == 2
    assert ast.dump(old, include_attributes=False) == ast.dump(new, include_attributes=False)


def wheel_members(platform):
    metadata = json.loads((ROOT / 'tests/fixtures/windows_saved_store_wheel_metadata_v1.json').read_text())['members_base64']
    members = {name: base64.b64decode(value) for name, value in metadata.items()}
    inputs = frozen_inputs()
    members.update({name.removeprefix('src/'): inputs[name] for name in VALUE['modules']})
    members['attune_harness-1.4.0.dist-info/licenses/LICENSE'] = inputs['LICENSE']
    if platform == 'nt':
        members[METADATA] = members[METADATA].replace(b'\n', b'\r\n')
    profile = {'posix': 'posix_lf', 'nt': 'nt_crlf'}[platform]
    record = json.loads((DATA / 'records.json').read_text())[profile]
    members[RECORD] = base64.b64decode(record['base64'])
    assert digest(members[RECORD]) == record['sha256']
    return members


def wheel(tmp_path, members):
    path = tmp_path / 'attune_harness-1.4.0-py3-none-any.whl'
    with zipfile.ZipFile(path, 'w') as archive:
        for name, raw in members.items():
            archive.writestr(name, raw)
    return path


@pytest.mark.parametrize('platform', ['posix', 'nt'])
def test_full119_and_carried118_profiles_remain_exact(route, monkeypatch, platform):
    caller, component, _ = route
    checker, projector, context = ADAPTER.algorithms(caller)
    # Replace this module's alias only; never mutate the shared stdlib os module.
    checker.os = SimpleNamespace(name=platform)
    monkeypatch.setattr(ADAPTER, 'algorithms', lambda actual: (checker, projector, context))
    result = ADAPTER.inspect_wheel(caller, wheel(component.parent, wheel_members(platform)), MANIFEST)
    assert len(result['wheel_rows']) == 119 and all(row['record_matched'] for row in result['wheel_rows'])
    assert len(result['installed_expected_members']) == 118
    assert result['installed_admission'] is False
    assert result['same_object_lease'] == 'future_caller_required'


@pytest.mark.parametrize('damage', ['wrong_pair', 'extra_pth', 'module_byte'])
def test_complete_wheel_refusals_survive_adapter(route, monkeypatch, damage):
    caller, component, _ = route
    checker, projector, context = ADAPTER.algorithms(caller)
    checker.os = SimpleNamespace(name='posix')
    monkeypatch.setattr(ADAPTER, 'algorithms', lambda actual: (checker, projector, context))
    members = wheel_members('nt' if damage == 'wrong_pair' else 'posix')
    if damage == 'extra_pth':
        members['startup.pth'] = b'import unreviewed\n'
    elif damage == 'module_byte':
        members['attune_harness/windows_effects.py'] += b'\n'
    with pytest.raises(ValueError, match='(component_wheel_admission|wheel_complete_inventory)_refused'):
        ADAPTER.inspect_wheel(caller, wheel(component.parent, members), MANIFEST)


def commit_bytes(tree, parents=('3' * 40, '4' * 40)):
    lines = ['tree ' + tree, *('parent ' + parent for parent in parents),
             'author Author <author@example.invalid> 0 +0000',
             'committer Committer <committer@example.invalid> 0 +0000']
    return ('\n'.join(lines) + '\n\nmessage\n').encode('ascii')


def test_shallow_boundary_does_not_hide_raw_merge_parents(route):
    caller, _, transport = route
    transport.shallow_boundary = True
    # Model the real failure: traversal reports a root while the raw commit
    # retains both ordered merge parents. The old adapter loses them here.
    assert transport(caller, 'rev-list', '--parents', '-n', '1', transport.head) == transport.head.encode() + b'\n'
    transport.calls.clear()
    result = stage(route)
    assert result['C']['parents'] == ['3' * 40, '4' * 40]
    assert ('cat-file', 'commit', transport.head) in transport.calls
    assert not any(args[0] == 'rev-list' for args in transport.calls)
    assert transport.calls.count(('rev-parse', 'HEAD')) == 1


@pytest.mark.parametrize('problem', [
    'missing_separator', 'missing_tree', 'duplicate_tree', 'invalid_tree',
    'mismatched_tree', 'invalid_parent', 'duplicate_parent', 'empty_parent',
    'malformed_parent_key', 'continued_parent', 'oversized_commit',
])
def test_bad_raw_headers_refuse_before_component_or_control_execution(route, problem):
    _, component, transport = route
    raw = commit_bytes(transport.tree)
    if problem == 'missing_separator':
        raw = raw.replace(b'\n\n', b'\n')
    elif problem == 'missing_tree':
        raw = raw.split(b'\n', 1)[1]
    elif problem == 'duplicate_tree':
        raw = b'tree ' + transport.tree.encode() + b'\n' + raw
    elif problem == 'invalid_tree':
        raw = raw.replace(transport.tree.encode(), b'Z' * 40, 1)
    elif problem == 'mismatched_tree':
        raw = raw.replace(transport.tree.encode(), b'8' * 40, 1)
    elif problem == 'invalid_parent':
        raw = raw.replace(b'parent ' + b'3' * 40, b'parent ' + b'X' * 40)
    elif problem == 'duplicate_parent':
        raw = raw.replace(b'parent ' + b'4' * 40, b'parent ' + b'3' * 40)
    elif problem == 'empty_parent':
        raw = raw.replace(b'parent ' + b'3' * 40, b'parent ')
    elif problem == 'malformed_parent_key':
        raw = raw.replace(b'parent ' + b'3' * 40, b'parent\t' + b'3' * 40)
    elif problem == 'continued_parent':
        raw = raw.replace(b'parent ' + b'4' * 40, b' parent ' + b'4' * 40)
    elif problem == 'oversized_commit':
        raw += b'x' * (65537 - len(raw))
    transport.raw_commit_override = raw
    with pytest.raises(ValueError, match='caller_commit_(header|tree)_refused'):
        stage(route)
    assert not component.exists()
    assert not any(args[:2] == ('cat-file', 'blob') for args in transport.calls)


def test_raw_parent_order_and_signature_body_boundary_are_preserved(route):
    _, _, transport = route
    transport.raw_commit_override = commit_bytes(transport.tree, ('4' * 40, '3' * 40)).replace(
        b'\n\nmessage\n', b'\ngpgsig -----BEGIN SIGNATURE-----\n parent ' + b'5' * 40
        + b'\n -----END SIGNATURE-----\n\nmessage\nparent ' + b'6' * 40 + b'\n')
    result = stage(route)
    assert result['C']['parents'] == ['4' * 40, '3' * 40]


def test_genuine_raw_root_records_no_parents_without_merge_claim(route):
    _, _, transport = route
    transport.raw_commit_override = commit_bytes(transport.tree, ())
    result = stage(route)
    assert result['C']['parents'] == []
    assert result['C']['event_binding'] == 'not_implemented_by_this_data_adapter'
    assert result['account_execution'] is False
