"""PROPOSAL: data admission for one fixed T2 component and current controls.

No CLI, backend, package, fixture, account, GUI or proof execution. The reviewed
future caller must establish private owned parents/leases and bind this source.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess
import time
from types import ModuleType

K_COMMIT = 'bde059cf08924937948f4fb7c8347f88010a5bc4'
K_TREE = '5a510789aff476731f65788f74fb953e05968ef7'
K_SOURCE_TREE_SHA = '4c7854c36eaefc8022295fe7fc71947fa4c31237287adc69c8b3c749070c8282'
MANIFEST_SHA = '6b33976fcc9e7c1bcf276f82c9d4e0ad1d795008a74fb3c4343d86a7573c430a'
NATIVE_SHA = 'ec06940730803d3c6e00471e1a9eeb6962bf71474d1b043e49d62ffd2a6978a4'
DRIVER_SHA = '7ceb7519b2df1cca15729e3b96b0c0eba91f86b26cab97cbafe82752ef347a09'
CONTROL_INPUTS = {
    'check_windows_saved_store_account_inputs_v3.py': '7874a4819f18bf77dc0287b3895b0b05cceedec06d9cf3252d99e00f5b63555c',
    'project_windows_saved_store_build_v2.py': 'c8ca4eafe05f14028d6d930e81f0cf42fa4d90d5cb2582914c1468b75bf3e0d8',
}
SOURCE_PATHS = ('src/attune_harness', 'src/attune_voyage_plugin', 'LICENSE', 'README.md', 'pyproject.toml')
RECORD = 'attune_harness-1.4.0.dist-info/RECORD'
LIMIT = 1024 * 1024
ACCOUNT_EXECUTION = False


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def inventory(raw):
    # The complete finite manifest is fixed, including both coupled pairs.
    if len(raw) > LIMIT or digest(raw) != MANIFEST_SHA:
        raise ValueError('fixed_component_manifest_refused')
    value = json.loads(raw)
    if (value['schema_version'] != 4 or len(value['modules']) != 113
            or len(value['build_inputs']) != 3 or len(value['wheel_members']) != 119
            or value['modules']['src/attune_harness/windows_effects.py']['sha256'] != NATIVE_SHA):
        raise ValueError('fixed_component_shape_refused')
    return value


def driver_binding(raw):
    if len(raw) > LIMIT:
        raise ValueError('driver_identity_refused')
    tree = ast.parse(raw)
    values = [node.value.value for node in tree.body if isinstance(node, ast.Assign)
              and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
              and node.targets[0].id == 'NATIVE_SHA' and isinstance(node.value, ast.Constant)]
    if values != [NATIVE_SHA]:
        raise ValueError('driver_component_mismatch')
    if digest(raw) != DRIVER_SHA:
        raise ValueError('driver_identity_refused')


def _git(repo, *arguments):
    # Read-only data commands only; no fetch, checkout, hooks, backend or shell.
    result = subprocess.run(['git', '--no-replace-objects', *arguments], cwd=repo, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
    if result.returncode or len(result.stdout) > 65536:
        raise ValueError('git_fixed_data_refused')
    return result.stdout


def _plain_root(path):
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('absolute_plain_root_required')
    for parent in (path, *path.parents):
        value = parent.lstat()
        if (not stat.S_ISDIR(value.st_mode) or stat.S_ISLNK(value.st_mode)
                or getattr(value, 'st_file_attributes', 0) & 0x400):
            raise ValueError('root_alias_refused')


def raw_commit_parents(raw, actual_tree):
    """Read ordered parents from bounded raw bytes, including shallow heads."""
    if len(raw) > 65536 or b'\n\n' not in raw:
        raise ValueError('caller_commit_header_refused')
    trees, parents, previous = [], [], None
    for index, line in enumerate(raw.split(b'\n\n', 1)[0].split(b'\n')):
        if line.startswith(b' '):
            if previous is None or previous in (b'tree', b'parent'):
                raise ValueError('caller_commit_header_refused')
            continue
        key, separator, value = line.partition(b' ')
        if (not separator or re.fullmatch(rb'[a-z][a-z0-9-]*', key) is None
                or index == 0 and key != b'tree'):
            raise ValueError('caller_commit_header_refused')
        if key in (b'tree', b'parent'):
            if re.fullmatch(rb'[0-9a-f]{40}', value) is None:
                raise ValueError('caller_commit_header_refused')
            identity = value.decode('ascii')
            if key == b'tree':
                trees.append(identity)
            else:
                if identity in parents:
                    raise ValueError('caller_commit_header_refused')
                parents.append(identity)
        previous = key
    if trees != [actual_tree]:
        raise ValueError('caller_commit_tree_refused')
    return parents


def algorithms(caller):
    """Execute only two unchanged hash-bound data modules, read from current C."""
    _plain_root(caller)
    actual_head = _git(caller, 'rev-parse', 'HEAD').decode('ascii').strip()
    if re.fullmatch(r'[0-9a-f]{40}', actual_head) is None:
        raise ValueError('caller_commit_refused')
    actual_tree = _git(caller, 'rev-parse', actual_head + '^{tree}').decode('ascii').strip()
    if re.fullmatch(r'[0-9a-f]{40}', actual_tree) is None:
        raise ValueError('caller_provenance_refused')
    parents = raw_commit_parents(_git(caller, 'cat-file', 'commit', actual_head), actual_tree)
    loaded, rows = [], []
    for name, wanted in CONTROL_INPUTS.items():
        path = 'experiments/platform/' + name
        entry = _git(caller, 'ls-tree', '-z', actual_head, '--', path)
        records = entry.split(b'\0')
        if len(records) != 2 or records[1] != b'':
            raise ValueError('caller_control_tree_refused')
        metadata, actual = records[0].split(b'\t', 1)
        mode, kind, blob = metadata.decode('ascii').split()
        if (mode != '100644' or kind != 'blob' or actual.decode('ascii') != path
                or re.fullmatch(r'[0-9a-f]{40}', blob) is None):
            raise ValueError('caller_control_tree_refused')
        raw = _git(caller, 'cat-file', 'blob', blob)
        actual_blob = hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
        if digest(raw) != wanted or blob != actual_blob:
            raise ValueError('caller_control_identity_refused')
        module = ModuleType('t2_fixed_control_' + name.removesuffix('.py'))
        module.__file__ = str(caller / path)
        exec(compile(raw, module.__file__, 'exec'), module.__dict__)
        loaded.append(module)
        rows.append({'origin': 'current_C_Git_blob', 'path': path, 'git_blob': blob,
                     'sha256': wanted, 'execution': 'hash_bound_raw_bytes_in_memory'})
    return (*loaded, {'actual_checkout': actual_head, 'actual_tree': actual_tree,
                      'parents': parents, 'consumed_controls': rows,
                      'event_binding': 'not_implemented_by_this_data_adapter',
                      'product_impact_review': 'pending_explicit_comparison'})


def component_tree(caller):
    actual_tree = _git(caller, 'rev-parse', K_COMMIT + '^{tree}').decode('ascii').strip()
    if actual_tree != K_TREE:
        raise ValueError('fixed_commit_tree_refused')
    raw = _git(caller, 'ls-tree', '-r', K_COMMIT, '--', *SOURCE_PATHS)
    if digest(raw) != K_SOURCE_TREE_SHA:
        raise ValueError('fixed_source_tree_refused')
    return raw


def stage(caller, component, raw_manifest, raw_driver):
    """Create only fixed K source data; retain partial new output on failure."""
    value = inventory(raw_manifest)
    driver_binding(raw_driver)
    if (not component.is_absolute() or '..' in component.parts or component == caller
            or caller in component.parents or component in caller.parents):
        raise ValueError('component_caller_root_mix_refused')
    if component.exists() or component.is_symlink():
        raise ValueError('retained_component_refused')
    _plain_root(component.parent)
    checker, projector, controls = algorithms(caller)
    tree = component_tree(caller)
    inputs = {**value['modules'], **value['build_inputs']}
    # Pre-read every fixed blob before writing. No moving C/SRC or HEAD fallback.
    started, payloads = time.monotonic(), {}
    for name, row in inputs.items():
        if time.monotonic() - started >= 120:
            raise TimeoutError('fixed_component_read_budget')
        raw = _git(caller, 'cat-file', 'blob', row['git_blob'])
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
        if len(raw) != row['bytes'] or digest(raw) != row['sha256'] or blob != row['git_blob']:
            raise ValueError('fixed_blob_identity_refused')
        payloads[name] = raw
    component.mkdir()
    for name in sorted(projector.directories(inputs), key=lambda p: (len(Path(p).parts), p)):
        (component / name).mkdir()
    for name, raw in payloads.items():
        with (component / name).open('xb') as stream:
            stream.write(raw)
    projector.verify(component, inputs)
    rows = checker.source_rows(component, inputs, tree)
    if len(rows) != 116 or not all(row['matched'] for row in rows):
        raise ValueError('component_source_admission_refused')
    return {'status': 'component_source_data_admitted',
            'K': {'commit': K_COMMIT, 'tree': K_TREE, 'manifest_sha256': MANIFEST_SHA,
                  'source_tree_sha256': K_SOURCE_TREE_SHA, 'native_sha256': NATIVE_SHA,
                  'driver_sha256': DRIVER_SHA, 'root': str(component), 'source_rows': rows},
            'C': controls,
            'account_execution': False, 'backend_invoked': False, 'installed_admission': False,
            't2_d3_gate': 'unpassed', 'production_port_allowed': False}


def admitted_members(checker, raw_manifest):
    profile, members = checker.platform_members(inventory(raw_manifest))
    installed = {name: row for name, row in members.items() if name != RECORD}
    if len(members) != 119 or len(installed) != 118:
        raise ValueError('fixed_member_cardinality_refused')
    return profile, members, installed


def inspect_wheel(caller, path, raw_manifest):
    """Reuse full 119/RECORD algorithm; future caller must hold admitted object."""
    checker, projector, controls = algorithms(caller)
    profile, members, installed = admitted_members(checker, raw_manifest)
    projector.regular(path)
    rows = checker.wheel_rows(path, members)
    if len(rows) != 119 or not all(row['matched'] and row['record_matched'] for row in rows):
        raise ValueError('component_wheel_admission_refused')
    return {'C': controls, 'wheel_profile': profile, 'wheel_sha256': digest(checker.read(path, 16 * LIMIT)),
            'wheel_rows': rows, 'installed_expected_members': installed,
            'installed_admission': False, 'same_object_lease': 'future_caller_required',
            'account_execution': False, 't2_d3_gate': 'unpassed', 'production_port_allowed': False}
