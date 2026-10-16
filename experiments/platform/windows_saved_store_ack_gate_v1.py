"""PROPOSAL: finite data-only consumer for one standard-user T2 dataset.

No native/account/GUI/provider calls. A complete result still requires semantic
review; it cannot enable production or qualify physical power-loss behavior.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
from types import ModuleType
import zipfile

ORIGINAL_SHA = 'b233497ffe18973eca3a4db29b2eca7ee5269c4ae2ef78429a8cf10db1ce7355'
NAMESPACE_SHA = 'f326803457453fccf02b795144ef1a48986c4c7068eef87aa56d21591ddd643e'
NATIVE_SHA = 'ec06940730803d3c6e00471e1a9eeb6962bf71474d1b043e49d62ffd2a6978a4'
MANIFEST_SHA = '6b33976fcc9e7c1bcf276f82c9d4e0ad1d795008a74fb3c4343d86a7573c430a'
DRIVER_SHA = '7ceb7519b2df1cca15729e3b96b0c0eba91f86b26cab97cbafe82752ef347a09'
ADAPTER_SHA = 'a1cb9a2818b3a42f45ebb744fc890017f0f1a5f7129b47a4416b2ab7a0bfd9c3'
TEXT = 'Remember acceptance — 雪 🧭'
STAGES = ('prepared', 'file_flushed', 'renamed', 'namespace_flushed', 'before_response')
BARRIERS = ('prepared_file', 'replaced_file', 'parent_namespace')
LIMIT = 8 * 1024 * 1024


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def zero(value):
    return type(value) is int and value == 0


def unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'duplicate_json_key')
        value[key] = item
    return value


def decode(raw):
    require(len(raw) <= LIMIT, 'bounded_json_required')
    return json.loads(raw, object_pairs_hook=unique_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_json')))


def read(path):
    with path.open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    require(len(raw) <= LIMIT, 'bounded_input_required')
    return raw


def inspect_file(path, wanted, limit=LIMIT):
    # Trusted-CI visible-object admission, not a hostile-filesystem primitive.
    for parent in path.parents:
        value = parent.lstat()
        require(stat.S_ISDIR(value.st_mode) and not getattr(value, 'st_file_attributes', 0) & 0x400,
                'entry_parent_refused')
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
            and not getattr(before, 'st_file_attributes', 0) & 0x400, 'entry_kind_refused')
    with path.open('rb') as stream:
        import os
        opened = os.fstat(stream.fileno())
        require((opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino)
                and opened.st_nlink == 1 and 0 < opened.st_size <= limit, 'entry_open_identity_refused')
        raw = stream.read(limit + 1)
        after = path.lstat()
        require((after.st_dev, after.st_ino) == (opened.st_dev, opened.st_ino)
                and len(raw) == opened.st_size, 'entry_changed_during_read')
    digest = hashlib.sha256(raw).hexdigest()
    require(wanted is None or digest == wanted, 'entry_hash_refused')
    return {'path': str(path), 'sha256': digest, 'plain_single_link': True}


def admit(repo, owned, pins, wheel_hash, checkpoint=lambda value: None):
    require(repo.is_absolute() and owned.is_absolute() and type(pins) is dict and len(pins) == 48
            and len({name.casefold() for name in pins}) == 48, 'entry_finite48_refused')
    rows = []
    checkpoint({'status': 'entry_incomplete', 'runtime_rows': rows})
    for name, digest in pins.items():
        require(type(name) is str and re.fullmatch(r'[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*', name)
                and not {'.', '..'} & set(name.split('/'))
                and type(digest) is str and re.fullmatch(r'[0-9a-f]{64}', digest), 'entry_pin_refused')
        rows.append(inspect_file(repo / name, digest))
        checkpoint({'status': 'entry_incomplete', 'runtime_rows': rows})
    adapter = bound_module(repo / 'experiments/platform/windows_saved_store_component_adapter_v1.py', ADAPTER_SHA, 't2_entry_adapter')
    checker, projector, context = adapter.algorithms(repo)
    stage = decode(read(owned / 'component-stage.json'))
    require(stage['C'] == context and stage['status'] == 'fixed_component_and_protocol_staged', 'entry_current_C_refused')
    raw = read(owned / 'protocol/manifest.json')
    manifest = adapter.inventory(raw)
    inputs = {**manifest['modules'], **manifest['build_inputs']}
    projector.verify(owned / 'component', inputs)
    source = checker.source_rows(owned / 'component', inputs, adapter.component_tree(repo))
    require(len(source) == 116 and all(row['matched'] is True for row in source), 'entry_source116_refused')
    checkpoint({'status': 'entry_incomplete', 'runtime_rows': rows, 'source_rows': source, 'C': context, 'K': stage['K']})
    wheel = owned / 'wheel/attune_harness-1.4.0-py3-none-any.whl'
    require(list(wheel.parent.iterdir()) == [wheel], 'entry_extra_wheel_refused')
    inspect_file(wheel, wheel_hash, 16 * 1024 * 1024)
    result = adapter.inspect_wheel(repo, wheel, raw)
    require(result['C'] == context and result['wheel_sha256'] == wheel_hash
            and len(result['wheel_rows']) == 119 and len(result['installed_expected_members']) == 118,
            'entry_wheel119_refused')
    return {'status': 'entry48_source116_wheel119_admitted', 'C': context, 'K': stage['K'],
            'runtime_rows': rows, 'source_rows': source, **result,
            'accounts_or_credentials_created': False, 't2_d3_passed': False, 'production_port_allowed': False}


def bound_module(path, wanted, name):
    raw = read(path)
    require(len(raw) <= LIMIT and hashlib.sha256(raw).hexdigest() == wanted, 'validator_source_refused')
    module = ModuleType(name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def normal(row, where=None, *, raw=False):
    keys = {'where', 'flags', 'returned_ntstatus', 'io_status'} | ({'pid'} if raw else set())
    require(type(row) is dict and set(row) == keys, 'flush_fields_refused')
    require(type(row['where']) is str and (where is None or row['where'] == where), 'flush_role_refused')
    require(all(zero(row[k]) for k in ('flags', 'returned_ntstatus', 'io_status')), 'normal_zero_flush_required')
    if raw:
        require(type(row['pid']) is int and 0 < row['pid'] < 2**32, 'raw_pid_refused')
    return {key: row[key] for key in ('where', 'flags', 'returned_ntstatus', 'io_status')}


def flushes(rows, expected):
    require(type(rows) is list and len(rows) == len(expected), 'flush_count_refused')
    return [normal(row, where) for row, where in zip(rows, expected)]


def private_acl(value):
    require(value['protected'] is True and value['owner_is_current_user'] is True, 'private_acl_refused')
    aces = value['aces']
    require(len(aces) == 2 and {a['principal'] for a in aces} == {'current_user', 'SYSTEM'}, 'private_aces_refused')
    require(all(zero(a['type']) and type(a['mask']) is int and a['mask'] == 0x1f01ff
                and type(a['flags']) is int and a['flags'] == 3 for a in aces), 'private_rights_refused')


def token(value, expected_sid):
    require(value['user_sid'] == expected_sid and value['administrators_enabled'] is False
            and value['token_is_elevated'] is False and value['integrity_sid'] == 'S-1-16-8192'
            and type(value['enabled_privileges']) is list
            and not set(value['enabled_privileges']) - {'SeChangeNotifyPrivilege'}, 'standard_primary_token_refused')


def state_bytes(keys):
    records = {key: {'request_id': key, 'text': TEXT, 'revision': index + 1}
               for index, key in enumerate(keys)}
    return json.dumps({'proof_schema': 1, 'records': records, 'history': keys, 'operations': records},
                      ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def ack(row, keys):
    require(row['replayed'] is False, 'new_commit_required')
    result = row['result']
    require(type(result) is dict and set(result) == {'request_id', 'text', 'revision'}
            and result['request_id'] == keys[-1] and result['text'] == TEXT
            and type(result['revision']) is int and result['revision'] == len(keys), 'ack_result_refused')
    renamed = row['rename']
    require(type(renamed) is dict and set(renamed) == {'returned_ntstatus', 'io_status_block_status'}
            and all(zero(v) for v in renamed.values()), 'ack_rename_status_refused')
    flushes(row['flushes'], BARRIERS)
    private_acl(row['acl'])
    raw = state_bytes(keys)
    require(type(row['bytes']) is int and row['bytes'] == len(raw)
            and row['sha256'] == hashlib.sha256(raw).hexdigest(), 'ack_afterimage_refused')
    return {'request_id': result['request_id'], 'revision': result['revision'],
            'sha256': row['sha256'], 'bytes': row['bytes']}


def raw_stream(files, name, expected):
    require(name in files, 'raw_stream_missing')
    lines = files[name].splitlines()
    require(len(lines) == len(expected), 'raw_stream_count_refused')
    result = [normal(decode(line), role, raw=True) for line, role in zip(lines, expected)]
    return result


def capture(value):
    require(all(value[k] is True for k in ('Started', 'RootExitConfirmed', 'StreamsCompleted'))
            and value['TimedOut'] is False and value['KillTreeRequested'] is False
            and value['FailureType'] is None and zero(value['ExitCode']), 'setup_capture_refused')
    for key in ('Stdout', 'Stderr'):
        require(value[key]['FailureType'] is None and zero(value[key]['DiscardedCharacters']), 'setup_stream_refused')


def process(value):
    require(value is not None and zero(value['ExitCode']) and value['PrimaryFailure'] is None
            and value['TeardownFailures'] == [], 'owned_process_refused')
    require(all(value[k] is True for k in ('ProcessCreated', 'JobAssigned', 'JobTerminationSucceeded',
            'WholeTreeEmptyConfirmed', 'RootExitConfirmed', 'TreeDisappearanceEstablished',
            'ControllerGuiUnchanged', 'Success')), 'owned_tree_cleanup_refused')


def cleanup(fixture):
    require(fixture['proposal_revision'] == 4 and fixture['success'] is True
            and fixture['setup_failure'] is None and fixture['issues'] == [], 'fixture_failed_or_unknown')
    require(fixture['account_disable'] in ('succeeded', 'already_absent')
            and fixture['account_remove'] in ('succeeded', 'already_absent')
            and fixture['fixture_root_remove'] == 'succeeded', 'account_or_root_cleanup_refused')
    require(all(fixture[k] is True for k in ('private_cleanup_succeeded', 'proof_tree_disappearance_established',
            'cleanup_tree_disappearance_established', 'gui_tree_disappearance_established',
            'gui_cleanup_succeeded', 'credential_disposed', 'anchor_setup_tree_disappearance_established',
            'runtime_admission_tree_disappearance_established')), 'cleanup_unknown')
    process(fixture['proof_run'])
    process(fixture['private_cleanup_run'])
    capture(fixture['anchor_setup_run'])
    capture(fixture['runtime_admission_run'])
    gui = fixture['gui_lease_process']
    require(gui['PrimaryFailure'] is None and gui['TeardownFailures'] == [], 'gui_process_failure')
    require(all(gui[k] is True for k in ('OpenGuiUnchanged', 'CloseGuiUnchanged', 'HelperSourceRetained',
            'SourceReleaseSucceeded', 'AncestorReleaseSucceeded', 'TreeDisappearanceEstablished')), 'gui_lease_cleanup_refused')
    require(gui['RetainedSourceSha256'] == '5786e2eefbb6e61f65ef4caaf17a4668ad7dd14ae8f552d72dffcc21845729bf', 'gui_source_refused')
    final = fixture['gui_lease_final']
    require(final['state'] == 'stopped' and final['failure'] is None
            and final['process_sid'] == fixture['controller_sid']
            and final['nonce'] == fixture['fixture_leaf'].removeprefix('AttuneT2Proof-')
            and final['station'] == 'AttuneT2-' + final['nonce'] and final['desktop'] == 'proof'
            and final['pid'] == gui['Pid'], 'gui_final_identity_refused')
    facts = final['gui']
    require(facts['PrimaryFailure'] is None and facts['TeardownFailures'] == []
            and facts['Ready'] is False and all(facts[k] is True for k in ('SetupThreadExited',
            'HelperStationRestored', 'HelperThreadDesktopUnchanged', 'DesktopClosed', 'StationClosed', 'DescriptorFreed')),
            'gui_final_cleanup_refused')


def consume(files, fixture, setup, driver, original, namespace, manifest):
    """Consume producer records; no synthetic cleanup result can qualify native cleanup."""
    cleanup(fixture)
    require(setup == fixture['anchor_setup'], 'setup_fixture_binding_refused')
    require(setup['status'] == 'anchor_published_requires_semantic_review'
            and setup['role'] == 'controller_anchor_setup' and setup['standard_user_proof'] is False
            and setup['handles_closed'] is True and setup['failure_type'] is None
            and setup['controller_sid'] == fixture['controller_sid']
            and setup['token']['user_sid'] == fixture['controller_sid']
            and setup['fixture_leaf'] == fixture['fixture_leaf']
            and setup['child_identity'] == setup['child_after']
            and setup['parent_identity'] == setup['parent_after'], 'anchor_setup_refused')
    normal(setup['flush'], 'fixture_anchor_parent')
    require(setup['K']['commit'] == 'bde059cf08924937948f4fb7c8347f88010a5bc4'
            and setup['K']['tree'] == '5a510789aff476731f65788f74fb953e05968ef7', 'setup_fixed_K_refused')
    require(driver['status'] == 'observation_processes_returned_zero'
            and driver['original_sha256'] == ORIGINAL_SHA and driver['namespace_sha256'] == NAMESPACE_SHA
            and driver['expected_native_sha256'] == NATIVE_SHA
            and driver['phases'] == [{'phase': 'namespace', 'status': 'returned', 'exit_code': 0},
                                     {'phase': 'primitive', 'status': 'returned', 'exit_code': 0}]
            and driver['production_port_allowed'] is False and driver['power_loss_tested'] is False,
            'combined_driver_refused')
    primitive = decode(files['primitive/receipt.json'])
    space = decode(files['receipt.json'])
    original.validate_receipt(primitive)
    namespace.validate(original, space)
    sid = fixture['account_sid']
    require(type(sid) is str and re.fullmatch(r'S-1-5-21-(?:[0-9]+-){3}[0-9]+', sid) is not None,
            'created_account_sid_refused')
    require(primitive['token_profile'] == 'existing-standard-primary-v1', 'primary_profile_refused')
    for facts in (primitive['token'], space['token'], space['supervisor_token']):
        token(facts, sid)
    require(space['anchor_identity'] == setup['child_identity'], 'namespace_anchor_binding_refused')
    require(space['identity']['installed_native_sha256'] == NATIVE_SHA
            and primitive['identity']['installed_native_sha256'] == NATIVE_SHA
            and primitive['identity']['experiment_sha256'] == ORIGINAL_SHA
            and space['identity']['adapter_sha256'] == NAMESPACE_SHA, 'native_source_binding_refused')
    for result in (primitive, space):
        require(result['durability_gate'] == original.receipt_gate(result['flush_observations'])
                and result['durability_gate']['status'] == 'requires_semantic_review', 'blocked_native_gate')
        for row in result['flush_observations']:
            normal(row)
    require(len(primitive['flush_observations']) == 50 and len(space['flush_observations']) == 9,
            'aggregate_row_count_refused')
    private_acl(primitive['private_acl'])
    witnessed = [dict(scope='primitive_initial', **ack(primitive['initial_commit'], ['first']))]
    require(primitive['initial_commit']['lock_identity'] == primitive['locking']['persistent_identity'], 'initial_lock_identity_refused')
    expected_streams = {'worker-flush-observations.jsonl', 'primitive/native-flush-observations.jsonl'}
    writer_names = set()
    cases = primitive['concurrency']
    by_identical = {case['identical_requests']: case for case in cases}
    for identical, label in ((False, 'Distinct writers'), (True, 'Same request')):
        results = []
        for index in range(8):
            name = f'primitive/writer-{label}-{index}.json'
            writer_names.add(name)
            row = decode(files[name])
            token(row['token'], sid)
            require(row['token'] == by_identical[identical]['tokens'][index], 'writer_token_binding_refused')
            require(type(row['replayed']) is bool, 'writer_replay_type_refused')
            results.append(row)
            log = name + '.native-flush-observations.jsonl'
            if row['replayed']:
                require(identical and row['flushes'] == [] and 'rename' not in row and log not in files,
                        'replay_new_barrier_claim_refused')
            else:
                expected_streams.add(log)
                require(raw_stream(files, log, BARRIERS) == row['flushes'], 'writer_raw_binding_refused')
        new = sorted((r for r in results if not r['replayed']), key=lambda r: r['result']['revision'])
        require(len(new) == (1 if identical else 8), 'writer_winner_count_refused')
        require(all(r['lock_identity'] == results[0]['lock_identity'] for r in results), 'writer_lock_identity_refused')
        keys = ['seed']
        for row in new:
            key = row['result']['request_id']
            require(key == 'shared-id' if identical else re.fullmatch(r'writer-[0-7]', key) is not None,
                    'writer_request_id_refused')
            require(key not in keys, 'duplicate_writer_request')
            keys.append(key)
            witnessed.append(dict(scope=label, **ack(row, keys.copy())))
        if identical:
            require(all(row['result'] == new[0]['result'] for row in results), 'same_id_result_conflict')
        else:
            require(set(keys[1:]) == {f'writer-{i}' for i in range(8)}, 'distinct_writer_missing')
        require(by_identical[identical]['flushes'] == [dict(where=w, flags=0, returned_ntstatus=0, io_status=0) for w in BARRIERS]
                + [f for row in results for f in row['flushes']], 'writer_aggregate_binding_refused')
    require({p for p in files if p.startswith('primitive/writer-') and p.endswith('.json')} == writer_names,
            'extra_or_missing_writer_record')
    for index, commit in enumerate(space['commits']):
        witnessed.append(dict(scope='namespace', **ack(commit, ['first', 'second'][:index + 1])))
    require(len(witnessed) == 12, 'finite_ack_count_refused')
    raw_stream(files, 'worker-flush-observations.jsonl', [r['where'] for r in space['flush_observations'][1:]])
    main_roles = ['store_creation_parent', *BARRIERS, *BARRIERS]
    main_roles += ['store_creation_parent', *BARRIERS] * 2
    for stage in STAGES:
        main_roles += ['store_creation_parent', *BARRIERS]
        if stage in STAGES[:2]:
            main_roles += BARRIERS
    raw_stream(files, 'primitive/native-flush-observations.jsonl', main_roles)
    for stage, roles in zip(STAGES, ((), BARRIERS[:1], BARRIERS[:1], BARRIERS, BARRIERS)):
        name = f'primitive/{stage}-marker.json.native-flush-observations.jsonl'
        require(decode(files[f'primitive/{stage}-marker.json'])['stage'] == stage, 'kill_boundary_marker_refused')
        if roles:
            expected_streams.add(name)
            raw_stream(files, name, roles)
        else:
            require(name not in files, 'preflush_kill_has_extra_rows')
    require({p for p in files if p.endswith('.jsonl')} == expected_streams, 'extra_or_missing_raw_stream')
    runtime = fixture['runtime_admission']
    require(runtime['archive_record_checked_before_install'] is True
            and runtime['installer_rewritten_record_compared'] is False
            and runtime['package_or_native_imported'] is False
            and runtime['wheel_platform'] == 'nt' and runtime['wheel_profile'] == 'nt_crlf'
            and len(runtime['rows']) == 118 and all(row['matched'] is True for row in runtime['rows']),
            'fixture_installed118_refused')
    expected = dict(manifest['wheel_members'])
    expected.update(manifest['wheel_platform_pairs']['nt_crlf'])
    expected = {name: row for name, row in expected.items() if not name.endswith('/RECORD')}
    observed = runtime['rows']
    require(len(expected) == 118 and {row['path'] for row in observed} == set(expected)
            and all(row['sha256'] == expected[row['path']]['sha256'] for row in observed),
            'fixture_installed118_identity_refused')
    return {'status': 'native_observations_complete_requires_semantic_review',
            'complete_ack_witnesses': witnessed, 'complete_ack_count': 12, 'true_writer_replays': 7,
            'raw_proof_flush_rows': 84, 'setup_parent_flush_rows': 1,
            'unobserved_rename_io': ['lock_seed', 'concurrency_seeds', 'crash_seeds', 'crash_retries'],
            'fresh_chain_claim': 'fixture anchor setup + namespace three links/two commits only',
            'primitive_enclosing_path_publication': 'unqualified; representative commit protocol only',
            'replay_establishes_new_barrier': False, 'power_loss_tested': False,
            't2_d3_passed': False, 'production_port_allowed': False}


def archive(path):
    require(path.stat().st_size <= 32 * 1024 * 1024, 'archive_size_refused')
    files, names, total = {}, set(), 0
    with zipfile.ZipFile(path) as source:
        require(len(source.infolist()) <= 2000, 'archive_member_count_refused')
        for info in source.infolist():
            name = info.filename
            item = PurePosixPath(name)
            key = name.rstrip('/').casefold()
            require(name and not item.is_absolute() and '\\' not in name and ':' not in name
                    and '\x00' not in name and '..' not in item.parts and key not in names,
                    'archive_path_refused')
            names.add(key)
            mode = info.external_attr >> 16
            require(not stat.S_ISLNK(mode), 'archive_link_refused')
            if info.is_dir():
                continue
            total += info.file_size
            require(info.file_size <= LIMIT and total <= 128 * 1024 * 1024, 'archive_expansion_refused')
            files[name] = source.read(info)  # reads full CRC before consuming JSON
    return files


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--protocol', required=True, type=Path)
    args = parser.parse_args(argv)
    require(not args.output.exists() and not args.output.is_symlink(), 'retained_gate_refused')
    result = {'status': 'consumer_started', 't2_d3_passed': False, 'production_port_allowed': False}
    try:
        original = bound_module(args.protocol / 'original.py', ORIGINAL_SHA, 't2_gate_original')
        namespace = bound_module(args.protocol / 'namespace.py', NAMESPACE_SHA, 't2_gate_namespace')
        fixture = decode(read(args.evidence / 'fixture.json'))
        setup = decode(read(args.evidence / 'anchor-setup.json'))
        driver = decode(read(args.evidence / 'combined-driver.json'))
        entry = decode(read(args.evidence.parent / 'account-entry.json'))
        caller = decode(read(args.evidence.parent / 'account-caller.json'))
        require(entry['status'] == 'entry48_source116_wheel119_admitted'
                and entry['C'] == setup['C'] and entry['K'] == setup['K']
                and len(entry['runtime_rows']) == 48 and len(entry['source_rows']) == 116
                and len(entry['wheel_rows']) == 119
                and all(row['matched'] is True and row['record_matched'] is True for row in entry['wheel_rows'])
                and caller['entry_completed'] is True and caller['fixture_returned_normally'] is True
                and caller['fixture_invocation_attempted'] is True
                and caller['failure_type'] is None
                and caller['wheel_closed'] is True and caller['sources_closed'] is True
                and caller['close_failures'] == [] and caller['wheel_sha256'] == entry['wheel_sha256'],
                'caller_entry_lease_or_origin_refused')
        raw = read(args.protocol / 'manifest.json')
        require(hashlib.sha256(raw).hexdigest() == MANIFEST_SHA, 'gate_manifest_refused')
        manifest = decode(raw)
        files = archive(args.evidence / 'observations.zip')
        result.update(consume(files, fixture, setup, driver, original, namespace, manifest))
        return_code = 0
    except Exception as error:
        result.update(status='native_observations_refused', failure_type=type(error).__name__)
        return_code = 1
    with args.output.open('x', encoding='ascii') as stream:
        stream.write(json.dumps(result, ensure_ascii=True, allow_nan=False, indent=2) + '\n')
    return return_code


if __name__ == '__main__':
    raise SystemExit(main())
