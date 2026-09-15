"""Frozen local E1 precursor; reports observed mechanics, never model value."""
import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import time
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def oracle(cell, protocol):
    """Derive metrics from artifacts and independent effect ledger, not worker claims."""
    spec, before, outcome = (read(cell / name) for name in ('spec.json', 'before.json', 'outcome.json'))
    effects_path = cell / 'effects.jsonl'
    effects = [json.loads(line) for line in effects_path.read_text().splitlines()] if effects_path.exists() else []
    counts = Counter(item['request_digest'] for item in effects)
    assert outcome['accepted'] == before['accepted']['submission'] == read(cell / 'request.json'), 'Constraints changed'
    assert outcome['requirement_revision'] == before['requirement_revision'], 'Requirement revision changed'
    duplicate_effects = sum(max(0, count - 1) for count in counts.values())
    assert duplicate_effects == 0, 'A request effect was repeated'
    original = before['events'][-1]
    snapshot = before['recovery']['source_snapshot']
    assert snapshot == {p.relative_to(cell / 'project').as_posix(): sha(p)
                        for p in (cell / 'project').glob('**/*.md')}, 'Accepted corpus changed'
    def checkpoint(record):
        payload = {k: v for k, v in record.items() if k != 'checkpoint_digest'}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'),
                                        ensure_ascii=True, allow_nan=False).encode()).hexdigest()
    assert checkpoint(before) == before['checkpoint_digest'], 'Invalid original checkpoint'
    for effect in effects:
        actual = hashlib.sha256(json.dumps(effect['turn'], sort_keys=True, separators=(',', ':'),
                                          ensure_ascii=True, allow_nan=False).encode()).hexdigest()
        assert effect['request_digest'] == actual, 'Effect request correlation changed'
    expected_phase = {'prepared': 'prepared', 'lost-ack': 'dispatching', 'saved-result': 'completed'}[spec['interruption']]
    assert original['phase'] == expected_phase, 'Interruption missed intended boundary'
    if spec['condition'] == 'attune-packet':
        assert outcome['status'] == 'operator_required' and outcome['document_outcome'] is None
        assert len(effects) == (0 if spec['interruption'] == 'prepared' else 1)
        visible = json.loads(outcome['sections']['current_state'])
        assert visible['sha256'] == sha(cell / 'before.json')
        assert visible['event'] == {k: original[k] for k in ('event_id', 'phase', 'state', 'effect_class')}
        assert outcome['sections']['next_action'].endswith(spec['to'])
    else:
        final = read(cell / 'run/record.json')
        assert checkpoint(final) == final['checkpoint_digest'], 'Invalid final checkpoint'
        assert final['status'] == outcome['status'] == 'completed'
        assert final['accepted'] == before['accepted']
        assert final['document_outcome'] == outcome['document_outcome'] == protocol['variants'][spec['variant']]
        assert final['verification']['passed'] is (outcome['document_outcome'] == 'verified')
        if spec['variant'] == 'no-results':
            assert final['retrieval_outcome'] == 'no_results'
        assert len(effects) == 2 and counts[original['request_digest']] == 1
        assert final['recovery']['assignments']['lead']['participant_id'] == spec['to']
        assert final['events'][:len(before['events']) - 1] == before['events'][:-1]
        if spec['interruption'] == 'saved-result':
            assert final['events'][len(before['events']) - 1] == original, 'Saved result changed'
        transferred = [item for item in effects if item['turn']['participant_id'] == spec['to']]
        assert len(transferred) == 1
        assert transferred[0]['turn']['continuation']['accepted_submission'] == before['accepted']['submission']
        assert transferred[0]['turn']['continuation']['artifacts'] == before['artifacts']
        if spec['interruption'] == 'lost-ack':
            assert {s['action'] for s in outcome['steps'] if s['status'] == 'blocked'} == {'resume', 'transfer'}
            assert len(final['recovery']['reconciliations']) == 1
    return {'constraints_lost': 0, 'duplicate_effects': duplicate_effects, 'false_document_verification': 0,
            'effects': len(effects), 'awaiting_operator_after_trial': spec['condition'] == 'attune-packet',
            'completed_review': outcome['status'] == 'completed',
            'explicit_reconciliation': spec['condition'] == 'harness-capsule' and spec['interruption'] == 'lost-ack'}


def audit(output):
    protocol = read(HERE / 'protocol.json')
    assert sha(HERE / 'protocol.json') == read(ROOT / 'docs/receipts/phase5/e1-freeze.json')['protocol_sha256']
    for name, expected_hash in read(output / 'sources.json').items():
        assert sha(output / 'sources' / name) == expected_hash, 'Archived experiment source changed'
    wheel = ROOT / 'dist/attune_harness-0.1.0.dev0-py3-none-any.whl'
    assert sha(wheel) == protocol['baseline_wheel_sha256']
    with zipfile.ZipFile(wheel) as archive:
        expected_sources = {Path(name).name: hashlib.sha256(archive.read(name)).hexdigest()
                            for name in archive.namelist() if name.startswith('attune_harness/') and name.endswith('.py')}
    expected = set(itertools.product(protocol['conditions'], protocol['variants'], protocol['interruptions'],
                                    (tuple(d) for d in protocol['directions'])))
    seen, rows = set(), []
    for cell in sorted(output.glob('[0-9][0-9]')):
        spec = read(cell / 'spec.json')
        assert read(cell / 'runtime.json')['sources'] == expected_sources, 'Installed source differs from frozen wheel'
        if spec['condition'] == 'attune-packet':
            baseline = read(cell / 'packet-runtime.json')
            assert baseline['sha256'] == protocol['baseline_packet_sha256']
            assert baseline['attune_ai'] == protocol['baseline_attune_ai']
        key = (spec['condition'], spec['variant'], spec['interruption'], (spec['from'], spec['to']))
        assert key in expected and key not in seen, 'Missing, duplicate or unexpected cell'
        seen.add(key)
        rows.append({'cell': cell.name, **spec, **oracle(cell, protocol)})
    assert seen == expected, 'Incomplete matrix'
    aggregate = {condition: {key: sum(row[key] for row in rows if row['condition'] == condition)
                 for key in ('constraints_lost', 'duplicate_effects', 'false_document_verification',
                             'effects', 'awaiting_operator_after_trial', 'completed_review', 'explicit_reconciliation')}
                 for condition in protocol['conditions']}
    return {'experiment': protocol['experiment'], 'cells': len(rows), 'mechanical_checks': 'passed',
            'disposition': 'inconclusive', 'human_repair_seconds': None, 'model_correctness': None,
            'provider_calls': 0, 'aggregates': aggregate, 'rows': rows}


def run(python, baseline_python, output):
    protocol = read(HERE / 'protocol.json')
    assert sha(HERE / 'protocol.json') == read(ROOT / 'docs/receipts/phase5/e1-freeze.json')['protocol_sha256']
    wheel = ROOT / 'dist/attune_harness-0.1.0.dev0-py3-none-any.whl'
    assert sha(wheel) == protocol['baseline_wheel_sha256']
    with zipfile.ZipFile(wheel) as archive:
        expected_sources = {Path(name).name: hashlib.sha256(archive.read(name)).hexdigest()
                            for name in archive.namelist() if name.startswith('attune_harness/') and name.endswith('.py')}
    output.mkdir()
    source_hashes = {p.name: sha(p) for p in HERE.iterdir() if p.suffix in ('.py', '.json')}
    write(output / 'sources.json', source_hashes)
    (output / 'sources').mkdir()
    for name in source_hashes:
        (output / 'sources' / name).write_bytes((HERE / name).read_bytes())
    sequence = itertools.product(protocol['conditions'], protocol['variants'], protocol['interruptions'], protocol['directions'])
    for index, (condition, variant, interruption, direction) in enumerate(sequence):
        cell = output / f'{index:02}'
        cell.mkdir()
        write(cell / 'spec.json', {'condition': condition, 'variant': variant, 'interruption': interruption,
                                 'from': direction[0], 'to': direction[1]})
        history = []
        def worker(action, runtime=python, expected=0):
            result = subprocess.run([str(runtime), '-I', str(HERE / 'worker.py'), action, '--cell', str(cell)],
                                    cwd=cell, capture_output=True, text=True, timeout=30)
            history.append({'action': action, 'python': str(runtime), 'returncode': result.returncode,
                            'stdout': result.stdout, 'stderr': result.stderr, 'ended_ns': time.time_ns()})
            write(cell / 'processes.json', history)
            assert result.returncode == expected, f'{action}: {result.stderr}'
        worker('setup')
        assert read(cell / 'runtime.json')['sources'] == expected_sources, 'Installed Harness differs from wheel'
        worker('produce', expected=0 if interruption == 'lost-ack' else 71)
        (cell / 'before.json').write_bytes((cell / 'run/record.json').read_bytes())
        if condition == 'attune-packet':
            worker('pack', baseline_python)
            worker('unpack', baseline_python)
        else:
            worker('recover')
        write(cell / 'oracle.json', oracle(cell, protocol))
        print(f'{index:02}: {condition} / {variant} / {interruption} / {direction}: passed', flush=True)
    assert source_hashes == {name: sha(HERE / name) for name in source_hashes}, 'Experiment changed while running'
    result = audit(output)
    write(output / 'summary.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path)
    parser.add_argument('--baseline-python', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--audit-only', action='store_true')
    args = parser.parse_args()
    if args.audit_only:
        result = audit(args.output.absolute())
    else:
        if args.python is None or args.baseline_python is None:
            parser.error('Both installed Python interpreters are required')
        result = run(args.python.absolute(), args.baseline_python.absolute(), args.output.absolute())
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, indent=2))
