"""Account-free v2 entry; preserve the historical file/source/wheel checks."""
import hashlib
import re
from types import ModuleType

ENTRY_COUNT = 56
INPUT_PATH = 'experiments/platform/windows_saved_store_controller_v2/inputs.json'
INPUT_SHA = 'bde8f6184d407e2bc84e90d9e8e6932c0c59803dde34f9bef8ce52ed23a91496'
BASE_PATH = 'experiments/platform/windows_saved_store_ack_gate_v1.py'
BASE_SHA = '5322b81ab10bf83634685a245b535d6e1d06ff1682a941101f10116564450651'


def controls(repo):
    path = repo / BASE_PATH
    with path.open('rb') as stream:
        raw = stream.read(1048577)
    if len(raw) > 1048576 or hashlib.sha256(raw).hexdigest() != BASE_SHA:
        raise ValueError('historical_entry_controls_refused')
    module = ModuleType('fixed_historical_entry_controls')
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def admit(repo, owned, pins, wheel_hash, checkpoint=lambda value: None):
    base = controls(repo)
    base.require(repo.is_absolute() and owned.is_absolute() and type(pins) is dict and len(pins) == 56
            and len({name.casefold() for name in pins}) == 56, 'entry_finite56_refused')
    rows = []
    checkpoint({'status': 'entry_incomplete', 'runtime_rows': rows})
    for name, digest in pins.items():
        base.require(type(name) is str and re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*', name)
                and not {'.', '..'} & set(name.split('/'))
                and type(digest) is str and re.fullmatch(r'[0-9a-f]{64}', digest), 'entry_pin_refused')
        rows.append(base.inspect_file(repo / name, digest))
        checkpoint({'status': 'entry_incomplete', 'runtime_rows': rows})
    base.require(pins.get(INPUT_PATH) == INPUT_SHA, 'controller_definition_pin_refused')
    raw_inputs = base.read(repo / INPUT_PATH)
    base.require(hashlib.sha256(raw_inputs).hexdigest() == INPUT_SHA, 'controller_definition_changed')
    inputs = base.decode(raw_inputs)
    base.require(all(pins.get(row['source']) == row['sha256'] for row in inputs['locks'].values()),
                 'controller_dependency_pin_refused')
    adapter = base.bound_module(repo / 'experiments/platform/windows_saved_store_component_adapter_v1.py', base.ADAPTER_SHA, 't2_entry_adapter')
    checker, projector, context = adapter.algorithms(repo)
    stage = base.decode(base.read(owned / 'component-stage.json'))
    base.require(stage['C'] == context and stage['status'] == 'fixed_component_and_protocol_staged', 'entry_current_C_refused')
    raw = base.read(owned / 'protocol/manifest.json')
    manifest = adapter.inventory(raw)
    inputs = {**manifest['modules'], **manifest['build_inputs']}
    projector.verify(owned / 'component', inputs)
    source = checker.source_rows(owned / 'component', inputs, adapter.component_tree(repo))
    base.require(len(source) == 116 and all(row['matched'] is True for row in source), 'entry_source116_refused')
    checkpoint({'status': 'entry_incomplete', 'runtime_rows': rows, 'source_rows': source, 'C': context, 'K': stage['K']})
    wheel = owned / 'wheel/attune_harness-1.4.0-py3-none-any.whl'
    base.require(list(wheel.parent.iterdir()) == [wheel], 'entry_extra_wheel_refused')
    base.inspect_file(wheel, wheel_hash, 16 * 1024 * 1024)
    result = adapter.inspect_wheel(repo, wheel, raw)
    base.require(result['C'] == context and result['wheel_sha256'] == wheel_hash
            and len(result['wheel_rows']) == 119 and len(result['installed_expected_members']) == 118,
            'entry_wheel119_refused')
    return {'status': 'entry56_source116_wheel119_admitted', 'C': context, 'K': stage['K'],
            'runtime_rows': rows, 'source_rows': source, **result,
            'accounts_or_credentials_created': False, 't2_d3_passed': False, 'production_port_allowed': False}
