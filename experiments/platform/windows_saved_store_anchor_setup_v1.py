"""PROPOSAL ONLY: controller setup barrier for one new fixture anchor.

Never an account/GUI launcher or production backend. Native execution requires
separate exact human approval of the future caller. Import has no native effect.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from types import ModuleType

ADAPTER_SHA = 'a1cb9a2818b3a42f45ebb744fc890017f0f1a5f7129b47a4416b2ab7a0bfd9c3'
ORIGINAL_SHA = 'b233497ffe18973eca3a4db29b2eca7ee5269c4ae2ef78429a8cf10db1ce7355'
MANIFEST_SHA = '6b33976fcc9e7c1bcf276f82c9d4e0ad1d795008a74fb3c4343d86a7573c430a'
NATIVE_SHA = 'ec06940730803d3c6e00471e1a9eeb6962bf71474d1b043e49d62ffd2a6978a4'
LIMIT = 1024 * 1024


def load_bound(path, expected, name):
    for parent in path.parents:
        value = parent.lstat()
        if not stat.S_ISDIR(value.st_mode) or getattr(value, 'st_file_attributes', 0) & 0x400:
            raise ValueError('setup_source_parent_refused')
    value = path.lstat()
    if (not stat.S_ISREG(value.st_mode) or value.st_nlink != 1
            or getattr(value, 'st_file_attributes', 0) & 0x400):
        raise ValueError('setup_source_kind_refused')
    with path.open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('setup_source_identity_refused')
    module = ModuleType(name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def require_identity(value):
    if (type(value) is not dict or set(value) != {'volume', 'file_id'}
            or type(value['volume']) is not int or not 0 <= value['volume'] < 2**64
            or type(value['file_id']) is not str
            or re.fullmatch(r'[0-9a-f]{32}', value['file_id']) is None):
        raise ValueError('setup_identity_refused')
    return value


def require_flush(row):
    if (type(row) is not dict or set(row) != {'where', 'flags', 'returned_ntstatus', 'io_status'}
            or row['where'] != 'fixture_anchor_parent'
            or any(type(row[k]) is not int or row[k] != 0
                   for k in ('flags', 'returned_ntstatus', 'io_status'))):
        raise ValueError('setup_normal_barrier_refused')


def publish(api, parent_path, leaf, state, checkpoint):
    """One native operation; fake handles suffice for pure ordering controls."""
    if re.fullmatch(r'AttuneT2Proof-[0-9a-f]{32}', leaf) is None:
        raise ValueError('setup_leaf_refused')
    # root retains every admitted ancestor until final membership/identity checks.
    with api.api.root({'root': str(parent_path)}, check=False) as parent:
        state['parent_identity'] = require_identity(api.api.metadata(parent)[0]['identity'])
        with api.api.owned(api.api.canonical_child(parent, leaf, directory=True, writable=True)) as child:
            state['child_identity'] = require_identity(api.api.metadata(child)[0]['identity'])
            state['phase'] = 'parent_normal_barrier'
            checkpoint()
            # Exact unchanged b233 ProofNative.flush: synchronous flags0; it
            # records both statuses even when native flush refuses.
            state['flush'] = api.flush(parent, 'fixture_anchor_parent')
            checkpoint()
            require_flush(state['flush'])
            state['parent_after'] = require_identity(api.api.metadata(parent)[0]['identity'])
            state['child_after'] = require_identity(api.api.metadata(child)[0]['identity'])
            if (state['parent_after'] != state['parent_identity']
                    or state['child_after'] != state['child_identity']
                    or leaf not in api.api.names(parent)):
                raise ValueError('setup_anchor_changed')
            state['phase'] = 'identities_rechecked_with_handles_retained'
            checkpoint()
    # Status changes only after all owned/ancestor close operations succeeded.
    state.update(status='anchor_published_requires_semantic_review', handles_closed=True,
                 phase='completed')
    checkpoint()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--owned', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--controller-sid', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if os.name != 'nt' or not sys.flags.isolated:
        raise ValueError('isolated_native_setup_required')
    owned = Path(os.environ['RUNNER_TEMP']) / 'saved-store-build-safe'
    if (args.owned != owned or any(not p.is_absolute() or '..' in p.parts
            for p in (args.repo, args.owned, args.fixture, args.output))
            or args.fixture.parent != Path(os.environ['ProgramData'])
            or args.output != owned / 'account-fixture/anchor-setup.json'
            or args.output.exists() or args.output.is_symlink()
            or re.fullmatch(r'S-1-5-21-(?:[0-9]+-){3}[0-9]+', args.controller_sid) is None):
        raise ValueError('finite_setup_paths_refused')
    report = {'schema': 1, 'role': 'controller_anchor_setup', 'standard_user_proof': False,
              'status': 'setup_started', 'phase': 'admission', 'handles_closed': False,
              'fixture_leaf': args.fixture.name, 'controller_sid': args.controller_sid,
              'anchor_premise': 'pre-existing canonical fixed-local NTFS ProgramData; no ancestor creation',
              'parent_identity': None, 'child_identity': None, 'flush': None,
              'parent_after': None, 'child_after': None, 'failure_type': None,
              'power_loss_tested': False, 't2_d3_passed': False, 'production_port_allowed': False}
    def save():
        args.output.write_text(json.dumps(report, ensure_ascii=True, allow_nan=False, indent=2) + '\n', encoding='ascii')
    with args.output.open('x', encoding='ascii') as stream:
        stream.write('{}\n')
    try:
        save()
        adapter = load_bound(args.repo / 'experiments/platform/windows_saved_store_component_adapter_v1.py', ADAPTER_SHA, 't2_anchor_adapter')
        checker, projector, context = adapter.algorithms(args.repo)
        stage = json.loads(checker.read(owned / 'component-stage.json'))
        if stage['C'] != context or stage['status'] != 'fixed_component_and_protocol_staged':
            raise ValueError('setup_current_origin_refused')
        raw = checker.read(owned / 'protocol/manifest.json')
        manifest = adapter.inventory(raw)
        inputs = {**manifest['modules'], **manifest['build_inputs']}
        projector.verify(owned / 'component', inputs)
        rows = checker.source_rows(owned / 'component', inputs, adapter.component_tree(args.repo))
        if len(rows) != 116 or not all(row['matched'] is True for row in rows):
            raise ValueError('setup_fixed_component_refused')
        report.update(C=context, K=stage['K'], source_rows=rows)
        original = load_bound(owned / 'protocol/original.py', ORIGINAL_SHA, 't2_anchor_original')
        if any(name == 'attune_harness' or name.startswith('attune_harness.') for name in sys.modules):
            raise ValueError('setup_package_prewarmed')
        sys.path.insert(0, str(owned / 'component/src'))
        from attune_harness import windows_effects
        native_path = Path(windows_effects.__file__)
        if (native_path != owned / 'component/src/attune_harness/windows_effects.py'
                or hashlib.sha256(native_path.read_bytes()).hexdigest() != NATIVE_SHA):
            raise ValueError('setup_import_origin_refused')
        api = original.ProofNative()
        report['token'] = api.token_facts()
        if report['token']['user_sid'] != args.controller_sid:
            raise ValueError('setup_controller_identity_refused')
        save()
        publish(api, args.fixture.parent, args.fixture.name, report, save)
        return 0
    except BaseException as error:
        report.update(status='setup_refused', failure_type=type(error).__name__)
        save()
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
