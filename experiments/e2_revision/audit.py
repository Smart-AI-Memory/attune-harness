"""Recompute revised E2 acceptance from raw files without importing its policy."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def check_raw(path, cell, descriptor_name='current.json'):
    raw = read(path)
    assert '/site-packages/attune_harness/' in raw['harness_location']
    record = raw.get('record')
    dispatches = 0
    if record:
        location = Path(record['record_path'])
        assert location.is_relative_to(cell), 'Record escaped its independent cell'
        assert read(location) == record, 'Raw record differs from durable record'
        if record['operation'] == 'review':
            selected = [e for e in record['events'] if e.get('kind') == 'tool'
                        and e.get('participant_id') == 'lead' and e.get('action', {}).get('name') == 'evidence.search']
        else:
            assert record['operation'] == 'mcp-session'
            selected = record['events']
        dispatches = len(selected)
    assert dispatches == raw['target_dispatches']
    result = raw.get('target_result')
    if result is None:
        return False, dispatches
    assert result['status'] == 'retrieved' and result['operation'] == 'retrieve'
    assert result['query'] == 'quartz retention policy' and type(result['k']) is int and result['k'] == 3
    descriptor = read(cell / descriptor_name)
    assert result['extension']['artifact_digest'] == descriptor['artifact']['digest']
    assert result['extension']['version'] == descriptor['artifact']['version']
    assert result['sources'] and len(selected) == 1 and selected[0]['result'] == result
    for source in result['sources']:
        file = (cell / 'corpus' / source['path']).resolve()
        assert file.is_relative_to(cell / 'corpus') and sha(file) == source['sha256']
    if record['operation'] == 'mcp-session':
        responses = [frame['result'] for frame in raw['frames'] if 'structuredContent' in frame.get('result', {})]
        assert len(responses) == 1 and responses[0]['structuredContent'] == result
        assert json.loads(responses[0]['content'][0]['text']) == result
    return True, dispatches


def check(directory):
    protocol = read(directory / 'protocol.json')
    assert protocol == read(ROOT / 'experiments/e2_revision/protocol.json')
    for name, expected_hash in read(ROOT / 'docs/receipts/e2-revision/freeze.json')['sha256'].items():
        assert sha(ROOT / name) == expected_hash, 'Frozen input changed'
    for name, expected_hash in read(directory / 'sources.json').items():
        assert sha(directory / 'sources' / name) == expected_hash, 'Archived source changed'
    wheel = ROOT / 'dist/attune_harness-0.1.0.dev0-py3-none-any.whl'
    assert sha(wheel) == protocol['baseline_wheel_sha256']
    with zipfile.ZipFile(wheel) as archive:
        engines = {Path(name).name: hashlib.sha256(archive.read(name)).hexdigest()
                   for name in archive.namelist() if name.startswith('attune_harness/') and name.endswith('.py')}
    expected = set(itertools.product(protocol['adapters'], protocol['conditions'], protocol['states']))
    seen, rows, dispatches = set(), read(directory / 'rows.json'), 0
    measures = {'baseline_false_verified': 0, 'revised_pre_call_claims': 0, 'revised_post_call_availability_claims': 0,
        'working_results_delivered': 0, 'upgrade_results_delivered': 0, 'upgraded_history_invalidated': 0,
        'broken_calls_visible': 0, 'guard_denials_without_consumer_invocation': 0,
        'post_success_faults_visible': 0, 'unnecessary_rejections': 0, 'false_observed_success': 0}
    for row in rows:
        key = row['adapter'], row['condition'], row['state']
        assert key in expected and key not in seen and row['evaluated'], 'Incomplete or duplicate matrix'
        seen.add(key)
        cell = directory / row['cell']
        assert read(cell / 'current.json')['engine_modules'] == engines
        chronology = read(cell / 'chronology.json')
        def step(name):
            matches = [i for i, item in enumerate(chronology) if item['action'] == name]
            assert len(matches) == 1, f'Missing/duplicate step {name}'
            return matches[0]
        ok, count = check_raw(cell / 'qualification.json', cell, 'before.json')
        assert ok
        dispatches += count
        if row['state'] == 'advertised-but-broken':
            assert read(cell / 'before.json') == read(cell / 'current.json')
        if row['state'] == 'upgraded':
            assert read(cell / 'before.json')['artifact'] != read(cell / 'current.json')['artifact']
        if row['state'] == 'dependency-missing':
            assert read(cell / 'current.json')['dependencies']['attune-rag'] is None
        if row['condition'] == 'version-bound-cache':
            decision = read(cell / 'decision.json')
            assert step('baseline-plan') < step('baseline-oracle')
            assert sha(cell / 'decision.json') == chronology[step('baseline-plan')]['output_sha256']
            usable, count = check_raw(cell / 'oracle.json', cell)
            dispatches += count
            assert usable is (row['state'] in ('working', 'upgraded'))
            measures['baseline_false_verified'] += int(decision['verified_availability_claim'] and not usable)
            continue
        for prefix in ('current', 'next') if row['state'] == 'working' else ('current',):
            decision, completion, raw = (read(cell / (prefix + '-' + name + '.json')) for name in ('decision', 'completion', 'raw'))
            assert step(prefix + '-plan') < step(prefix + '-before') < step(prefix + '-after') < step(prefix + '-finish') < step(prefix + '-oracle')
            assert sha(cell / (prefix + '-decision.json')) == chronology[step(prefix + '-plan')]['output_sha256']
            assert sha(cell / (prefix + '-completion.json')) == chronology[step(prefix + '-finish')]['output_sha256']
            assert completion['raw_digest'] == digest(raw)
            assert decision['descriptor_digest'] == digest(read(cell / (prefix + '-before.json')))
            assert read(cell / (prefix + '-before.json')) == read(cell / (prefix + '-after.json'))
            usable, count = check_raw(cell / (prefix + '-oracle.json'), cell)
            dispatches += count
            assert usable is (prefix == 'current' and row['state'] in ('working', 'upgraded'))
            measures['revised_pre_call_claims'] += int(decision['predicted_usable'] or decision['verified_availability_claim']
                                                      or decision['availability'] != 'unverified')
            measures['revised_post_call_availability_claims'] += int(completion['verified_availability_claim']
                                                                    or completion['availability'] != 'unverified')
            if decision['invocation_allowed']:
                assert step(prefix + '-before') < step(prefix + '-requested-invocation') < step(prefix + '-after')
                actual, count = check_raw(cell / (prefix + '-raw.json'), cell)
                dispatches += count
                assert actual == usable
                measures['false_observed_success'] += int(completion['status'] == 'observed_success' and not actual)
                delivered = completion['status'] == 'observed_success' and completion['result'] == raw['target_result'] and actual
                if prefix == 'next':
                    assert read(cell / 'current.json') == read(cell / 'post-success.json')
                    measures['post_success_faults_visible'] += int(decision['history_status'] == 'matching_success'
                        and completion['status'] == 'observed_failure' and completion['result'] is None and not actual)
                elif row['state'] in ('working', 'upgraded'):
                    measures['working_results_delivered' if row['state'] == 'working' else 'upgrade_results_delivered'] += int(delivered)
                    if row['state'] == 'upgraded':
                        measures['upgraded_history_invalidated'] += int(decision['history_status'] == 'stale')
                else:
                    assert row['state'] == 'advertised-but-broken'
                    measures['broken_calls_visible'] += int(completion['status'] == 'observed_failure' and completion['result'] is None)
            else:
                assert not any(item['action'] == prefix + '-requested-invocation' for item in chronology)
                assert raw['not_invoked'] and completion['status'] == 'not_invoked' and completion['result'] is None
                measures['unnecessary_rejections'] += int(usable)
                expected_status = 'unavailable' if row['state'] == 'dependency-missing' else 'denied'
                measures['guard_denials_without_consumer_invocation'] += int(decision['status'] == expected_status and not usable)
    assert seen == expected
    targets = {'baseline_false_verified': 2, 'revised_pre_call_claims': 0, 'revised_post_call_availability_claims': 0,
        'working_results_delivered': 2, 'upgrade_results_delivered': 2, 'upgraded_history_invalidated': 2,
        'broken_calls_visible': 2, 'guard_denials_without_consumer_invocation': 6,
        'post_success_faults_visible': 2, 'unnecessary_rejections': 0, 'false_observed_success': 0}
    return {'experiment': protocol['experiment'], 'cells_audited': len(seen), 'measures': measures,
        'auditor_sha256': sha(Path(__file__)),
        'frozen_targets': targets, 'actual_target_dispatches': dispatches,
        'disposition': 'adopt_narrowed_contract' if measures == targets else 'revise',
        'original_cache_disposition': 'revise', 'provider_calls': 0,
        'scope': 'Local call-bound evidence; no general availability cache or live-host qualification'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = check(args.directory.resolve())
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
