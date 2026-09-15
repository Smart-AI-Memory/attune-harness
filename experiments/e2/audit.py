"""Independently recalculate E2 outcomes from saved decisions and raw adapter calls."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def check(directory):
    summary, protocol = read(directory / 'summary.json'), read(directory / 'protocol.json')
    expected = set(itertools.product(protocol['adapters'], protocol['conditions'], protocol['states']))
    seen, totals, dispatches, runtime_locations = set(), {}, 0, set()
    for row in summary['rows']:
        identity = row['adapter'], row['condition'], row['state']
        assert identity in expected and identity not in seen and row['evaluated']
        seen.add(identity)
        cell = directory / row['cell']
        decision, oracle = read(cell / 'decision.json'), read(cell / 'oracle.json')
        assert decision == row['decision']
        chronology = read(cell / 'chronology.json')
        decision_index = next(i for i, item in enumerate(chronology) if item['action'] == 'decision')
        oracle_index = next(i for i, item in enumerate(chronology) if item['action'] == 'invoke'
                            and str(cell / 'oracle.json') in item['arguments'])
        assert decision_index < oracle_index
        assert hashlib.sha256((cell / 'decision.json').read_bytes()).hexdigest() == chronology[decision_index]['sha256']
        result = oracle.get('target_result')
        usable = isinstance(result, dict) and result.get('status') == 'retrieved'
        if usable:
            assert result['sources'] and result['extension']['artifact_digest'] == read(cell / 'extension-state/record.json')['artifact_digest']
            for source in result['sources']:
                path = (cell / 'corpus' / source['path']).resolve()
                assert path.is_relative_to((cell / 'corpus').resolve())
                assert hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256']
        assert usable == row['oracle_usable']
        measures = {'false_usable_prediction': int(decision['predicted_usable'] and not usable),
                    'false_verified_availability_claim': int(decision['verified_availability_claim'] and not usable),
                    'unnecessary_rejection': int(usable and decision['status'] in ('denied', 'unavailable', 'not_declared')),
                    'deferred_usable_case': int(usable and decision['status'] == 'needs_probe')}
        assert measures == row['metrics']
        aggregate = totals.setdefault(row['condition'], dict.fromkeys(measures, 0))
        for key, number in measures.items():
            aggregate[key] += number
        for name in ('qualification', 'oracle', *(['requalified'] if row['state'] == 'upgraded' else [])):
            raw = read(cell / f'{name}.json')
            runtime_locations.add(raw['harness_location'])
            assert '/site-packages/attune_harness/' in raw['harness_location'], 'Checkout code was used'
            record = raw.get('record', {})
            if row['adapter'] == 'command-review':
                actual_dispatches = sum(event.get('kind') == 'tool' and event.get('participant_id') == 'lead'
                    and event.get('action', {}).get('name') == 'evidence.search' for event in record.get('events', []))
            else:
                actual_dispatches = len(record.get('events', []))
                if raw.get('target_result'):
                    response = next(frame for frame in raw['frames'] if 'structuredContent' in frame.get('result', {}))
                    assert response['result']['structuredContent'] == raw['target_result']
                    assert json.loads(response['result']['content'][0]['text']) == raw['target_result']
            assert actual_dispatches == raw['target_dispatches'] == row['target_dispatches'][name]
            dispatches += actual_dispatches
        if row['state'] == 'upgraded':
            assert read(cell / 'before.json')['artifact'] != read(cell / 'current.json')['artifact']
            assert row['upgrade']['fresh_oracle_usable']
        if row['state'] == 'advertised-but-broken':
            assert read(cell / 'before.json') == read(cell / 'current.json'), 'Runtime fault changed a cache key'
    assert seen == expected
    for condition, values in totals.items():
        assert all(summary['aggregates'][condition][key] == number for key, number in values.items())
    assert summary['disposition'] == 'revise' and totals['version-bound-cache']['false_verified_availability_claim'] > 0
    return {'cells_audited': len(seen), 'aggregates_recomputed': totals, 'actual_target_dispatches': dispatches,
            'all_decisions_saved_before_oracles': True, 'installed_harness_locations': sorted(runtime_locations),
            'raw_source_and_artifact_checks_passed': True, 'provider_calls': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = check(args.directory.absolute())
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
