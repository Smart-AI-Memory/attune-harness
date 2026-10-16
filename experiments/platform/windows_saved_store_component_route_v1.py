"""PROPOSAL: account-free fixed-component join to unchanged data/build functions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from types import ModuleType

ADAPTER_SHA = 'a1cb9a2818b3a42f45ebb744fc890017f0f1a5f7129b47a4416b2ab7a0bfd9c3'
PROTOCOL = {'helper.ps1': {'source': 'experiments/platform/windows_saved_store_gui_lease_helper_v4.ps1', 'sha256': '5786e2eefbb6e61f65ef4caaf17a4668ad7dd14ae8f552d72dffcc21845729bf', 'bytes': 11931}, 'fixture.ps1': {'source': 'experiments/platform/windows_saved_store_standard_user_gui_proposal_v3b3.ps1', 'sha256': '696879df5b141def393235708f3a2baf0e8c9bb1cdb24d125082b53bc81a5804', 'bytes': 53418}, 'original.py': {'source': 'experiments/platform/windows_saved_store_proof.py', 'sha256': 'b233497ffe18973eca3a4db29b2eca7ee5269c4ae2ef78429a8cf10db1ce7355', 'bytes': 44348}, 'namespace.py': {'source': 'experiments/platform/windows_saved_store_namespace_witness_v4.py', 'sha256': 'f326803457453fccf02b795144ef1a48986c4c7068eef87aa56d21591ddd643e', 'bytes': 14133}, 'driver.py': {'source': 'experiments/platform/windows_saved_store_combined_driver_v3.py', 'sha256': '7ceb7519b2df1cca15729e3b96b0c0eba91f86b26cab97cbafe82752ef347a09', 'bytes': 89937}, 'manifest.json': {'source': 'experiments/platform/windows_saved_store_source_manifest_v4.json', 'sha256': '6b33976fcc9e7c1bcf276f82c9d4e0ad1d795008a74fb3c4343d86a7573c430a', 'bytes': 54462}, 'requirements-workflow.lock': {'source': 'requirements-workflow.lock', 'sha256': '60ba53cfeba53c784331a689f948c5cbd046ed20f4e84fd6023eacf0ff656fad', 'bytes': 451}, 'requirements-voyage.lock': {'source': 'requirements-voyage.lock', 'sha256': '6a2f18db82d16ec3e8c8da55b282a3f7627b9ae025fb7cb11d14b6f7b512e441', 'bytes': 1401}, 'requirements-mcp.lock': {'source': 'requirements-mcp.lock', 'sha256': '50f956aff914ee8ca2e85e00e3cc35aa56fff07213b659d962d7c9d91be94735', 'bytes': 626}, 'requirements-tokens.lock': {'source': 'requirements-tokens.lock', 'sha256': '32fbeb94891432d45936d39b98513550e87405a278c3aaaabb714aa38c20de53', 'bytes': 180}, 'requirements-redis.lock': {'source': 'requirements-redis.lock', 'sha256': '84f43680576915e1e8716902d85acc6b2ae63a4451eb55f5eaddabbf9806c09c', 'bytes': 225}}
REPORTS = {'stage': 'component-stage.json', 'create': 'projection-created.json',
           'verify': 'projection-verified.json', 'build': 'projection-build.json',
           'wheel': 'wheel119.json'}
WHEEL_NAME = 'attune_harness-1.4.0-py3-none-any.whl'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load_adapter(repo):
    path = repo / 'experiments/platform/windows_saved_store_component_adapter_v1.py'
    with path.open('rb') as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024 or digest(raw) != ADAPTER_SHA:
        raise ValueError('adapter_source_refused')
    module = ModuleType('t2_component_adapter_join')
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def event_binding(context, event):
    actual, parents = context['actual_checkout'], context['parents']
    if actual != event['sha']:
        raise ValueError('caller_not_event_sha')
    if event['name'] == 'pull_request':
        import re
        if (any(re.fullmatch(r'[0-9a-f]{40}', event[k]) is None for k in ('head', 'base'))
                or parents != [event['base'], event['head']]):
            raise ValueError('caller_not_normal_event_merge')
    elif event['name'] != 'push':
        raise ValueError('caller_event_refused')
    return {'event': event['name'], 'event_sha': event['sha'], 'event_head': event['head'],
            'event_base': event['base'], 'actual_parents': parents,
            'component_claim_transfer': 'requires_separate_impact_review'}


def protocol_source(repo, row, projector):
    path = repo / row['source']
    for parent in path.parents:
        projector.regular(parent, directory=True)
        if parent == repo:
            break
    return projector.verified_bytes(path, row)


def stage_protocol(repo, target, projector):
    if target.exists() or target.is_symlink():
        raise ValueError('retained_protocol_refused')
    raw = {name: protocol_source(repo, row, projector) for name, row in PROTOCOL.items()}
    target.mkdir()
    for name, payload in raw.items():
        with (target / name).open('xb') as stream:
            stream.write(payload)
    return projector.verify(target, PROTOCOL)


def execute(repo, owned, mode, event):
    if (not sys.flags.isolated or not repo.is_absolute() or not owned.is_absolute()
            or owned != Path(os.environ['RUNNER_TEMP']) / 'saved-store-build-safe'
            or mode not in REPORTS):
        raise ValueError('finite_isolated_route_required')
    output = owned / REPORTS[mode]
    if output.exists() or output.is_symlink():
        raise ValueError('retained_route_report_refused')
    report = {'status': 'route_started', 'mode': mode, 'rows': [], 'source_rows': [],
              'backend_launch_attempted': False, 'backend_returned': False, 'backend_exit_code': None,
              'account_fixture_invoked': False, 'accounts_or_credentials_created': False,
              'gui_objects_created': False, 'proof_invoked': False, 'package_or_native_imported': False,
              'installed_admission': False, 'failure_type': None, 't2_d3_gate': 'unpassed',
              'production_port_allowed': False}
    def save():
        output.write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    save()
    try:
        adapter = load_adapter(repo)
        checker, projector, context = adapter.algorithms(repo)
        report['C'] = context
        report['event_binding'] = event_binding(context, event)
        save()
        component, protocol, projection = owned / 'component', owned / 'protocol', owned / 'source'
        if mode == 'stage':
            manifest = repo / 'experiments/platform/windows_saved_store_source_manifest_v4.json'
            driver = repo / 'experiments/platform/windows_saved_store_combined_driver_v3.py'
            admitted = adapter.stage(repo, component, checker.read(manifest), checker.read(driver))
            if admitted['C'] != context:
                raise ValueError('caller_changed_during_stage')
            report.update(admitted)
            report['event_binding'] = event_binding(admitted['C'], event)
            report['protocol_rows'] = stage_protocol(repo, protocol, projector)
            report['status'] = 'fixed_component_and_protocol_staged'
        else:
            projector.verify(protocol, PROTOCOL)
            raw = checker.read(protocol / 'manifest.json')
            value = adapter.inventory(raw)
            adapter.driver_binding(checker.read(protocol / 'driver.py'))
            inputs = {**value['modules'], **value['build_inputs']}
            projector.verify(component, inputs)
            report['source_rows'] = checker.source_rows(component, inputs, adapter.component_tree(repo))
            if len(report['source_rows']) != 116 or not all(row['matched'] for row in report['source_rows']):
                raise ValueError('fixed_component_drift_refused')
            if mode == 'create':
                report['rows'] = projector.create(component, projection, inputs)
                report['status'] = 'projection_created_and_verified'
            elif mode == 'verify':
                report['rows'] = projector.verify(projection, inputs)
                report['status'] = 'projection_verified'
            elif mode == 'build':
                report['rows'] = projector.verify(projection, inputs)
                projector.build_projection(projection, owned / 'wheel', inputs, report, save)
                report['status'] = 'projection_backend_returned'
            else:
                report.update(adapter.inspect_wheel(repo, owned / 'wheel' / WHEEL_NAME, raw))
                if report['C'] != context:
                    raise ValueError('caller_changed_during_wheel_check')
                report['wheel_platform'] = checker.os.name
                report['status'] = 'wheel_and_sources_verified'
    except Exception as error:
        report.update(status='component_route_refused', failure_type=type(error).__name__)
    finally:
        save()
    return 0 if report['status'] != 'component_route_refused' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--owned', required=True, type=Path)
    parser.add_argument('--mode', required=True, choices=tuple(REPORTS))
    args = parser.parse_args()
    event = {k: os.environ.get('T2_EVENT_' + v, '') for k, v in
             [('name', 'NAME'), ('sha', 'SHA'), ('head', 'HEAD'), ('base', 'BASE')]}
    return execute(args.repo, args.owned, args.mode, event)


if __name__ == '__main__':
    raise SystemExit(main())
