"""Run the frozen E2 matrix against installed packages in independent cells."""
import argparse
import hashlib
import importlib.util
import json
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
spec = importlib.util.spec_from_file_location('e2_policy', HERE / 'policy.py')
policy = importlib.util.module_from_spec(spec); spec.loader.exec_module(policy)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def usable(result, cell):
    """Independent oracle checks files, not the cache's descriptor or seal."""
    value = result.get('target_result')
    if not isinstance(value, dict) or value.get('status') != 'retrieved':
        return False
    state = read(cell / 'extension-state/record.json')
    assert value['extension']['artifact_digest'] == state['artifact_digest'], 'Wrong artifact returned'
    assert value['query'] == 'quartz retention policy' and type(value['k']) is int and value['k'] == 3
    assert value['sources'], 'Empty retrieval is not the positive fixture result'
    for source in value['sources']:
        path = (cell / 'corpus' / source['path']).resolve()
        assert path.is_relative_to((cell / 'corpus').resolve()), 'Source escaped corpus'
        assert source['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest(), 'Source hash mismatch'
    return True


def run_matrix(python, missing_python, output):
    protocol_path = HERE / 'protocol.json'
    protocol, freeze = read(protocol_path), read(ROOT / 'docs/receipts/e2/freeze.json')
    assert sha(protocol_path) == freeze['protocol_sha256'], 'Frozen criteria changed'
    wheel = ROOT / 'dist/attune_harness-0.1.0.dev0-py3-none-any.whl'
    assert sha(wheel) == protocol['baseline_wheel_sha256'], 'Baseline artifact changed'
    output.mkdir()  # Never overwrite an earlier experimental run.
    write(output / 'protocol.json', protocol)
    source_hashes = {path.relative_to(ROOT).as_posix(): sha(path) for path in (
        HERE / 'protocol.json', HERE / 'policy.py', HERE / 'worker.py', HERE / 'participant.py',
        HERE / 'evaluate.py', ROOT / 'scripts/check_mcp_installed.py')}
    write(output / 'source-hashes.json', source_hashes)
    rows = []
    for adapter in protocol['adapters']:
        for condition in protocol['conditions']:
            for state_name in protocol['states']:
                cell = output / f'{len(rows):02}'
                cell.mkdir()
                chronology = []
                row = {'cell': cell.name, 'adapter': adapter, 'condition': condition, 'state': state_name}
                def worker(action, *, runtime=python, **kwargs):
                    command = [str(runtime), '-I', str(HERE / 'worker.py'), action, '--cell', str(cell), '--adapter', adapter]
                    for name, value in kwargs.items():
                        command += ['--' + name.replace('_', '-'), str(value)]
                    run = subprocess.run(command, cwd=cell, capture_output=True, text=True, timeout=20)
                    chronology.append({'action': action, 'runtime': str(runtime), 'arguments': command[4:],
                                       'exit': run.returncode, 'ended_ns': time.time_ns()})
                    if run.returncode:
                        write(cell / 'worker-failure.json', {'command': command, 'stdout': run.stdout, 'stderr': run.stderr})
                        raise AssertionError(f'{action} worker failed: {run.stderr}')
                try:
                    worker('setup')
                    worker('describe', output=cell / 'before.json')
                    worker('invoke', run_dir=cell / 'qualification-run', output=cell / 'qualification.json')
                    qualification = read(cell / 'qualification.json')
                    assert usable(qualification, cell), 'Healthy qualification did not return real evidence'
                    observation = {'descriptor': read(cell / 'before.json'), 'result': qualification['target_result']}
                    observation['digest'] = policy.fingerprint(observation)
                    write(cell / 'observation.json', observation)
                    worker('alter', state=state_name)
                    runtime = missing_python if state_name == 'dependency-missing' else python
                    worker('describe', runtime=runtime, output=cell / 'current.json')
                    def decision(observation_path, filename):
                        subprocess.run([str(python), '-I', str(HERE / 'policy.py'), '--condition', condition,
                            '--descriptor', str(cell / 'current.json'), '--observation', str(observation_path),
                            '--output', str(cell / filename)], check=True, cwd=cell, capture_output=True, text=True, timeout=5)
                        chronology.append({'action': 'decision', 'file': filename, 'sha256': sha(cell / filename), 'ended_ns': time.time_ns()})
                        return read(cell / filename)
                    predicted = decision(cell / 'observation.json', 'decision.json')
                    decision_hash = sha(cell / 'decision.json')
                    worker('invoke', runtime=runtime, run_dir=cell / 'oracle-run', output=cell / 'oracle.json')
                    assert decision_hash == sha(cell / 'decision.json'), 'Decision changed after oracle'
                    oracle = read(cell / 'oracle.json')
                    actual = usable(oracle, cell)
                    expected_error = {'advertised-but-broken': 'E2 seeded runtime failure', 'dependency-missing': 'attune-rag',
                                      'disabled': 'disabled', 'permission-denied': 'not granted'}
                    if state_name in expected_error:
                        assert not actual and expected_error[state_name] in json.dumps(oracle), 'Seeded failure not observed at the intended boundary'
                    else:
                        assert actual, 'Working or upgraded oracle unexpectedly failed'
                    row.update(decision=predicted, oracle_usable=actual, metrics=policy.score(predicted, actual),
                               descriptor_changed=policy.fingerprint(read(cell / 'before.json')) != policy.fingerprint(read(cell / 'current.json')),
                               target_dispatches={'qualification': qualification['target_dispatches'], 'oracle': oracle['target_dispatches']})
                    if state_name == 'upgraded':
                        refreshed = {'descriptor': read(cell / 'current.json'), 'result': oracle['target_result']}
                        refreshed['digest'] = policy.fingerprint(refreshed)
                        write(cell / 'fresh-observation.json', refreshed)
                        fresh_decision = decision(cell / 'fresh-observation.json', 'fresh-decision.json')
                        worker('invoke', runtime=runtime, run_dir=cell / 'requalified-run', output=cell / 'requalified.json')
                        requalified = read(cell / 'requalified.json')
                        row['upgrade'] = {'old_evidence_invalidated': predicted['status'] == 'needs_probe',
                                          'fresh_decision': fresh_decision, 'fresh_oracle_usable': usable(requalified, cell)}
                        row['target_dispatches']['requalified'] = requalified['target_dispatches']
                    row['evaluated'] = True
                except Exception as exc:
                    row.update(evaluated=False, infrastructure_error={'type': type(exc).__name__, 'detail': str(exc)})
                write(cell / 'chronology.json', chronology)
                write(cell / 'row.json', row)
                rows.append(row)
                print(f"{cell.name}: {adapter} / {condition} / {state_name}: " +
                      (f"{row['decision']['status']} -> usable={row['oracle_usable']}" if row['evaluated'] else 'INFRASTRUCTURE FAILURE'), flush=True)
    aggregates = {}
    for condition in protocol['conditions']:
        subset = [row for row in rows if row['condition'] == condition and row['evaluated']]
        aggregates[condition] = {'evaluated': len(subset),
            **{key: sum(row['metrics'][key] for row in subset) for key in (
                'false_usable_prediction', 'false_verified_availability_claim', 'unnecessary_rejection', 'deferred_usable_case')},
            'working_accepted': sum(row['state'] == 'working' and row['decision']['predicted_usable'] for row in subset),
            'upgrade_evidence_invalidated': sum(row.get('upgrade', {}).get('old_evidence_invalidated', False) for row in subset),
            'upgrade_requalification_usable': sum(row.get('upgrade', {}).get('fresh_oracle_usable', False)
                and row['upgrade']['fresh_decision']['predicted_usable'] for row in subset)}
    candidate = aggregates['version-bound-cache']
    if not all(row['evaluated'] for row in rows):
        disposition = 'inconclusive'
    else:
        disposition = ('adopt' if candidate['false_verified_availability_claim'] == candidate['unnecessary_rejection'] == 0
            and candidate['working_accepted'] == candidate['upgrade_evidence_invalidated'] == candidate['upgrade_requalification_usable'] == 2 else 'revise')
    for name, expected in source_hashes.items():
        assert sha(ROOT / name) == expected, 'Experiment source changed during evaluation'
    summary = {'experiment': 'E2', 'protocol_sha256': freeze['protocol_sha256'], 'baseline_wheel_sha256': sha(wheel),
               'rows': rows, 'aggregates': aggregates, 'disposition': disposition, 'provider_calls': 0,
               'production_sources_changed': False, 'temporal_or_statistical_generalization': False}
    write(output / 'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--missing-python', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    summary = run_matrix(args.python.absolute(), args.missing_python.absolute(), args.output.absolute())
    print(json.dumps({'disposition': summary['disposition'], 'aggregates': summary['aggregates']}, indent=2))
    if summary['disposition'] == 'inconclusive':
        raise SystemExit(1)
