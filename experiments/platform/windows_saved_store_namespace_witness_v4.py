"""Review-only T2 adapter: added creation-chain and two-commit observations."""
import argparse
from contextlib import contextmanager
import hashlib
from importlib.metadata import distribution
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import types

ORIGINAL_SHA = 'b233497ffe18973eca3a4db29b2eca7ee5269c4ae2ef78429a8cf10db1ce7355'
SCRIPT = Path(__file__).absolute()
LIMIT = 1024 * 1024


def source_bytes(path, expected):
    with path.open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Source differs from its reviewed SHA-256')
    return raw


def load_original(path):
    raw = source_bytes(path, ORIGINAL_SHA)
    module = types.ModuleType('attune_saved_store_pinned_proof')
    module.__file__ = str(path)
    # Execute exactly the hashed bytes, rather than asking a loader to reread a
    # potentially different file. No original subprocess-dispatch helper runs.
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def installed_identity(adapter_sha):
    from attune_harness import windows_effects
    path = Path(windows_effects.__file__).resolve()
    dist = distribution('attune-harness')
    direct = dist.read_text('direct_url.json')
    if ('site-packages' not in path.parts or
            direct and json.loads(direct).get('dir_info', {}).get('editable')):
        raise ValueError('An installed noneditable wheel is required')
    return {'adapter_sha256': adapter_sha, 'original_sha256': ORIGINAL_SHA,
            'installed_native_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'distribution_version': dist.version, 'python_executable': str(Path(sys.executable).absolute())}


def emit(value):
    print(json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True), flush=True)


def save(original, path, value):
    raw = original.encode(value) + b'\n'
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def native(original, state, event_path=None):
    class WitnessNative(original.ProofNative):
        expected_store = None
        active_creation = None

        def flush(self, handle, where):
            row = super().flush(handle, where)
            state['flush_observations'].append(row)
            if self.active_creation is not None:
                self.active_creation['flush'] = row
            emit({'event': 'native_flush', 'role': state['role'], **row})
            if row['flags'] != 0 or row['returned_ntstatus'] != 0 or row['io_status'] != 0:
                raise RuntimeError('A required normal flush barrier was refused')
            return row

        @contextmanager
        def locked(self, parent):
            identity = self.api.metadata(parent)[0]['identity']
            if identity != self.expected_store:
                raise ValueError('The reopened store differs from the created store')
            with super().locked(parent) as lock:
                yield lock
    return WitnessNative(event_path)


def create(original, api, parent, name, label, state):
    state['phase'] = label
    parent_identity = api.api.metadata(parent)[0]['identity']
    handle = api.child(parent, name, create=True, directory=True)
    try:
        child_identity = api.api.metadata(handle)[0]['identity']
        row = {'stage': label, 'leaf': name, 'parent_identity': parent_identity,
               'child_identity': child_identity, 'private_acl': api.private_acl(handle)}
        state['creation_barriers'].append(row)
        api.active_creation = row
        try:
            api.flush(parent, label)
        finally:
            api.active_creation = None
        emit({'event': 'creation_barrier', **row})
        return handle
    except BaseException:
        api.api.k.CloseHandle(handle)
        raise


def validate(original, result):
    original.validate_token(result['token'], require_unelevated=True)
    original.validate_token(result['supervisor_token'], require_unelevated=True)
    if result['token']['user_sid'] != result['supervisor_token']['user_sid']:
        raise ValueError('Supervisor and worker used different primary users')
    if (result['witness_schema'] != 1 or result['experiment'] != 'native_saved_namespace_creation_v2'
            or result['status'] != 'observations_complete' or result['coverage'] != 'creation_chain_and_two_commits_only'
            or result['identity']['original_sha256'] != ORIGINAL_SHA
            or result['token_profile'] != 'existing-standard-primary-v1'
            or result['production_port_allowed'] is not False or result['power_loss_tested'] is not False
            or result['filesystem'] != 'NTFS'):
        raise ValueError('Incomplete or mislabeled namespace witness')
    rows = result['creation_barriers']
    expected = ('output_creation_parent', 'scratch_creation_parent', 'store_creation_parent')
    if tuple(row['stage'] for row in rows) != expected:
        raise ValueError('The ordered creation chain is incomplete')
    parent = result['anchor_identity']
    for row in rows:
        flush = row['flush']
        if (row['parent_identity'] != parent or flush['where'] != row['stage']
                or flush['flags'] != 0 or flush['returned_ntstatus'] != 0 or flush['io_status'] != 0):
            raise ValueError('A creation entry lacks its exact parent barrier')
        parent = row['child_identity']
    commits = result['commits']
    if ([c['result']['request_id'] for c in commits] != ['first', 'second'] or
            [c['result']['revision'] for c in commits] != [1, 2] or
            commits[0]['lock_identity'] != commits[1]['lock_identity'] or
            any(c['replayed'] is not False for c in commits) or
            result['final_counts'] != {'records': 2, 'history': 2, 'operations': 2}):
        raise ValueError('The two synthetic commits disagree')
    for commit in commits:
        if (commit['rename'] != {'returned_ntstatus': 0, 'io_status_block_status': 0} or
                [r['where'] for r in commit['flushes']] != ['prepared_file', 'replaced_file', 'parent_namespace']):
            raise ValueError('Missing complete original commit barriers')
    expected_flushes = [row['flush'] for row in rows] + [row for commit in commits for row in commit['flushes']]
    if result['flush_observations'] != expected_flushes:
        raise ValueError('The aggregate flush ledger differs from its creation and commit barriers')
    if any(row['flags'] != 0 or row['returned_ntstatus'] != 0 or row['io_status'] != 0
           for row in result['flush_observations']):
        raise ValueError('Every aggregate flush must be normal and successfully completed')
    gate = original.receipt_gate(result['flush_observations'])
    if result['durability_gate'] != gate or gate['status'] != 'requires_semantic_review':
        raise ValueError('The namespace witness cannot approve durability')
    if any(result[k] != 0 for k in ('paid_model_calls', 'provider_network_calls')):
        raise ValueError('The witness does not authorize provider activity')


def worker(original, args, identity, state):
    header = original.read_json(args.output / 'supervisor.json')
    if header['identity'] != identity or len(header['creation_barriers']) != 1:
        raise ValueError('Worker source/runtime identity differs from supervisor')
    state.update(anchor_identity=header['anchor_identity'], filesystem=header['filesystem'], supervisor_token=header['token'],
                 creation_barriers=header['creation_barriers'],
                 flush_observations=header['flush_observations'])
    api = native(original, state, args.output / 'worker-flush-observations.jsonl')
    state['token'] = api.require_standard(unelevated=True)
    with api.api.root({'root': str(args.output)}, check=False) as output:
        if api.api.metadata(output)[0]['identity'] != state['creation_barriers'][0]['child_identity']:
            raise ValueError('Worker output identity differs from its publication ledger')
        with api.api.owned(create(original, api, output, 'Scratch 雪', 'scratch_creation_parent', state)) as scratch:
            save(original, args.output / 'checkpoint-scratch.json', state)
            with api.api.owned(create(original, api, scratch, 'Private store 🧭', 'store_creation_parent', state)) as store:
                save(original, args.output / 'checkpoint-store.json', state)
                api.expected_store = api.api.metadata(store)[0]['identity']
                root = args.output / 'Scratch 雪' / 'Private store 🧭'
                state['phase'] = 'two_original_commits'
                state['commits'] = [original.mutate(api, root, key) for key in ('first', 'second')]
                final = api.read_state(store)
                original.assert_state(final)
                state['final_counts'] = {key: len(final[key]) for key in ('records', 'history', 'operations')}
    state.update(status='observations_complete', durability_gate=original.receipt_gate(state['flush_observations']))
    validate(original, state)
    save(original, args.output / 'receipt.json', state)
    emit({'status': state['status'], 'durability_gate': state['durability_gate']})
    return 0


def supervisor(original, args, identity, state):
    from attune_harness.windows import WindowsJob
    api = native(original, state)
    state['token'] = api.require_standard(unelevated=True)
    with api.api.root({'root': str(args.output.parent)}, check=False) as anchor:
        state['anchor_identity'] = api.api.metadata(anchor)[0]['identity']
        state['filesystem'] = 'NTFS'
        with api.api.owned(create(original, api, anchor, args.output.name, 'output_creation_parent', state)):
            save(original, args.output / 'supervisor.json', state)
            argv = [sys.executable, '-I', str(SCRIPT), '--worker', '--original', str(args.original),
                    '--original-sha256', ORIGINAL_SHA, '--expected-adapter-sha256', identity['adapter_sha256'],
                    '--output', str(args.output)]
            environment = {'SystemRoot': os.environ['SystemRoot'], 'TEMP': str(args.output),
                           'TMP': str(args.output), 'PYTHONUTF8': '1'}
            state['phase'] = 'bounded_worker'
            with (args.output / 'worker-stdout.log').open('xb') as stdout, (args.output / 'worker-stderr.log').open('xb') as stderr:
                with WindowsJob() as job:
                    process = job.launch(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                         cwd=str(args.output), environment=environment)
                    try:
                        code = process.wait(timeout=120)
                    except subprocess.TimeoutExpired:
                        job.stop(process)
                        raise TimeoutError('Namespace witness exceeded its 120-second worker bound') from None
            save(original, args.output / 'supervisor-exit.json', {
                'exit_code': code, 'identity': identity, 'worker_adapter': str(SCRIPT),
                'kill_on_job_close': True, 'coverage': state['coverage'], 'production_port_allowed': False})
            if code != 0:
                raise RuntimeError('Namespace witness worker failed; inspect its retained log')
            receipt = original.read_json(args.output / 'receipt.json')
            if receipt['identity'] != identity:
                raise ValueError('Final receipt source/runtime identity differs from supervisor')
            validate(original, receipt)
            emit({'status': receipt['status'], 'durability_gate': receipt['durability_gate']})
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--original-sha256', required=True, choices=(ORIGINAL_SHA,))
    parser.add_argument('--expected-adapter-sha256', required=True)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if os.name != 'nt':
        parser.error('Native Windows and an existing actual standard-primary token are required')
    if not args.output.is_absolute() or '..' in args.output.parts or not args.original.is_absolute():
        parser.error('Use absolute output/original paths without output traversal')
    source_bytes(SCRIPT, args.expected_adapter_sha256)
    original = load_original(args.original)
    identity = installed_identity(args.expected_adapter_sha256)
    state = {'witness_schema': 1, 'experiment': 'native_saved_namespace_creation_v2',
             'status': 'observations_in_progress', 'role': 'worker' if args.worker else 'supervisor',
             'phase': 'initialization', 'coverage': 'creation_chain_and_two_commits_only',
             'identity': identity, 'creation_barriers': [], 'flush_observations': [],
             'platform': {'os': platform.platform(), 'machine': platform.machine(), 'python': sys.version},
             'token_profile': 'existing-standard-primary-v1', 'paid_model_calls': 0,
             'provider_network_calls': 0, 'production_port_allowed': False, 'power_loss_tested': False}
    try:
        return worker(original, args, identity, state) if args.worker else supervisor(original, args, identity, state)
    except Exception as error:
        state.update(status='witness_failed', failure={'type': type(error).__name__, 'errno': getattr(error, 'errno', None)},
                     durability_gate={'status': 'unpassed', 'production_port_allowed': False, 'power_loss_tested': False})
        emit(state)
        # The supervisor may fail before its output-parent barrier; stdout is
        # then the retained diagnostic. Only the already-published worker writes.
        if args.worker:
            save(original, args.output / 'failure.json', state)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
